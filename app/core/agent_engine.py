"""M2/M3 interview core: profile-aware, belief-driven, agent-rendered engine.

Same contract as the M1 `InterviewEngine` (start/process over
`InterviewState`), so the service layer and routes are unchanged. M3 flow
per turn: grade the last answer -> update the belief state -> the Director
decides (new question / follow-up / hint) -> the Interviewer renders.
Every agent degrades to a deterministic fallback offline, and the hard
minimums (>= 8 questions, >= 4 days, valid feedback) hold in both modes.
Interview rules (M3/M9): questions come ONLY from the candidate's completed
curriculum days. M11: the interview is evidence-driven, not
question-count-driven — every completed day is assessed until its evidence
record is terminal (verified / sufficient / needs_validation), and the run
ends when all completed days are closed. Strong answers close a day with
fewer questions; weak answers generate follow-up probes until enough
evidence exists. There is no fixed interview length: the completed-day pool
sets the scope, the per-day evidence state machine sets the length, and
max_turns is only a runaway guard.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.agents.director import Director
from app.agents.grader import Grader, ProbeTarget, build_probe_target
from app.agents.interviewer import Interviewer
from app.agents.reporter import Reporter
from app.config import settings
from app.core.belief import init_belief_state, update_belief
from app.core.curriculum import DayInfo, load_curriculum
from app.core.evidence import evaluate as evaluate_evidence
from app.core.evidence import record_for
from app.core.llm import LLMGateway
from app.core.prompts import COMPLETION_REPLY, END_KEYWORDS, PHASES
from app.core.profile import ProfileAnalysis, analyze_profile, prior_for_day
from app.domain.candidate import CandidateProfile
from app.domain.interview import EngineTurn, InterviewState, TranscriptEntry
from app.infrastructure.llm_mock import MockLLMProvider

logger = logging.getLogger("viva.engine")

RECENT_SCORES_KEEP = 2
MAX_OVERCLAIMS = 5


class AgenticInterviewEngine:
    """Async engine protocol-compatible with the M1 InterviewEngine."""

    def __init__(
        self,
        curriculum: dict[int, DayInfo] | None = None,
        curriculum_path: Path | None = None,
        gateway: LLMGateway | None = None,
        use_llm: bool | None = None,
        default_questions: int = settings.default_questions,
        max_turns: int = settings.max_turns,
    ) -> None:
        self.curriculum = (
            curriculum if curriculum is not None else load_curriculum(curriculum_path)
        )
        self.default_questions = default_questions
        self.max_turns = max_turns
        self._gateway = gateway or LLMGateway(primary=MockLLMProvider())
        if use_llm is None:
            use_llm = not self._gateway.uses_mock_primary
        self._use_llm = use_llm
        self._director = Director(self.curriculum, default_questions)
        self._interviewer = Interviewer(self._gateway, use_llm)
        self._grader = Grader(self._gateway, use_llm)
        self._reporter = Reporter(
            self._gateway, use_llm, default_questions=default_questions
        )

    # -- lifecycle -------------------------------------------------------

    async def start(self, state: InterviewState, candidate: CandidateProfile) -> str:
        state.candidate = candidate
        analysis = analyze_profile(candidate)
        state.plan = self._director.build_plan(analysis)
        state.belief_state = init_belief_state(analysis)
        welcome = await self._interviewer.render_welcome(candidate)
        state.transcript.append(TranscriptEntry(role="interviewer", text=welcome))
        return welcome

    async def process(self, state: InterviewState, message: str) -> EngineTurn:
        state.turn_count += 1
        state.transcript.append(
            TranscriptEntry(role="candidate", text=message, meta={"turn": state.turn_count})
        )

        normalized = " ".join(message.lower().split())
        # max_turns is a runaway guard only — the evidence state machine
        # ends the run naturally when every completed day is closed, so a
        # 31-day pool needs (and gets) far more than 50 turns.
        force_wrap = state.turn_count >= self.max_turns or normalized in END_KEYWORDS
        if force_wrap:
            return await self._wrap_up(state, reason="completed")

        grade = await self._grade_answer(state, message) if state.asked else None
        if grade is not None and state.asked:
            day = state.asked[-1].day
            record = record_for(state, day)
            missing = (
                grade.evidence.concepts_missing
                if grade.evidence is not None
                else []
            )
            terminal = evaluate_evidence(
                record, grade.weighted_score, missing, grade.overclaim, grade.vague
            )
            if terminal is not None:
                self._stamp_evidence(state, day, terminal, record["close_reason"])

        action = self._director.decide(state, grade, message, use_llm=self._use_llm)

        if action == "hint":
            return await self._give_hint(state)
        if action == "follow_up" and grade is not None:
            return await self._ask_followup(state, grade, message)
        if action == "wrap_up":
            return await self._wrap_up(state, reason="evidence_complete")

        return await self._ask_next(state)

    # -- interview flow ----------------------------------------------------

    async def _grade_answer(
        self, state: InterviewState, message: str
    ) -> GradeResult | None:
        question = state.asked[-1]
        grade = await self._grader.grade(
            question,
            message,
            self.curriculum.get(question.day),
            state.candidate,
        )
        state.belief.setdefault(str(question.day), []).append(grade.weighted_score)
        prior = prior_for_day(state.candidate, question.day)
        before = state.belief_state.get(str(question.day), {}).get("mastery", prior)
        update_belief(state.belief_state, question.day, grade.weighted_score, prior)
        after = state.belief_state[str(question.day)]["mastery"]
        bundle = grade.evidence
        if bundle is not None:
            bundle.mastery_delta = round(after - before, 4)
            reasoning = state.meta.setdefault("reasoning", [])
            reasoning.append(bundle.model_dump())
            if len(reasoning) > 12:
                del reasoning[: len(reasoning) - 12]
            state.meta.setdefault("day_evidence", {})[str(question.day)] = {
                "module": bundle.module,
                "objective": bundle.learning_objective,
                "detected": bundle.concepts_detected,
                "missing": bundle.concepts_missing,
                "retrieval_confidence": bundle.retrieval_confidence,
                "score": round(grade.weighted_score, 2),
            }
        meta = state.meta
        recent = list(meta.get("recent_scores", []))
        recent.append(grade.weighted_score)
        meta["recent_scores"] = recent[-RECENT_SCORES_KEEP:]
        if grade.overclaim and len(meta.get("overclaims", [])) < MAX_OVERCLAIMS:
            meta.setdefault("overclaims", []).append(
                {"day": question.day, "evidence": grade.overclaim_evidence}
            )
        meta["last_grade"] = {
            "day": question.day,
            "weighted": grade.weighted_score,
            "overclaim": grade.overclaim,
            "vague": grade.vague,
            "retrieval_confidence": bundle.retrieval_confidence if bundle else 0.0,
            "grading_confidence": bundle.grading_confidence if bundle else 0.0,
        }
        return grade

    async def _ask_next(self, state: InterviewState) -> EngineTurn:
        question = self._director.next_question(
            state, self._analyze(state), state.belief_state, state.candidate
        )
        if question is None:
            # Every completed curriculum day is closed (or the pool is
            # empty): the interview is complete. The length was set by the
            # evidence, not a fixed question count.
            return await self._wrap_up(state, reason="plan_exhausted")
        question.text = await self._interviewer.render_question(
            question,
            self.curriculum.get(question.day),
            state.candidate,
            phase=self._phase_for(len(state.asked) + 1),
            position=len(state.asked) + 1,
            total=self._plan_size(state),
        )
        state.asked.append(question)
        if question.day not in state.covered_days:
            state.covered_days.append(question.day)
        state.transcript.append(
            TranscriptEntry(role="interviewer", text=question.text, day=question.day)
        )
        state.phase = self._phase_for(len(state.asked))
        state.meta["consecutive_probes"] = 0
        state.meta["hints_given"] = 0
        state.meta["last_decision"] = {
            "action": "ask_new",
            "day": question.day,
            "difficulty": question.difficulty,
            "type": question.type,
        }
        return EngineTurn(reply=question.text)

    async def _ask_followup(
        self, state: InterviewState, grade: GradeResult, message: str
    ) -> EngineTurn:
        question = state.asked[-1]
        record_for(state, question.day)["probes"] += 1
        target: ProbeTarget = build_probe_target(grade, message, question.day)
        reply = await self._interviewer.render_followup(
            target, self.curriculum.get(question.day), state.candidate
        )
        meta = state.meta
        meta["consecutive_probes"] = meta.get("consecutive_probes", 0) + 1
        meta["followups_total"] = meta.get("followups_total", 0) + 1
        meta["last_decision"] = {
            "action": "follow_up",
            "day": question.day,
            "kind": target.kind,
            "target": target.target,
        }
        if "last_grade" in meta:
            meta["last_grade"]["followup_reason"] = target.followup_reason
        reasoning = state.meta.get("reasoning")
        if reasoning and reasoning[-1].get("curriculum_day") == question.day:
            reasoning[-1]["followup_reason"] = target.followup_reason
        state.transcript.append(
            TranscriptEntry(
                role="interviewer",
                text=reply,
                day=question.day,
                meta={
                    "kind": target.kind,
                    "action": "follow_up",
                    "followup_reason": target.followup_reason,
                    "missing_concepts": target.missing_concepts,
                },
            )
        )
        return EngineTurn(reply=reply)

    async def _give_hint(self, state: InterviewState) -> EngineTurn:
        question = state.asked[-1] if state.asked else None
        if question is not None:
            record_for(state, question.day)["hints"] += 1
        difficulty = question.difficulty if question else "L1"
        reply = await self._interviewer.render_hint(
            self.curriculum.get(question.day) if question else None, difficulty
        )
        state.meta["hints_given"] = state.meta.get("hints_given", 0) + 1
        state.meta["last_decision"] = {"action": "hint", "day": question.day if question else None}
        state.transcript.append(
            TranscriptEntry(
                role="interviewer",
                text=reply,
                day=question.day if question else None,
                meta={"action": "hint"},
            )
        )
        return EngineTurn(reply=reply)

    # -- completion ---------------------------------------------------------

    async def _wrap_up(self, state: InterviewState, reason: str) -> EngineTurn:
        state.status = "completed"
        state.phase = "wrapup"
        state.completed_reason = reason
        feedback = await self._reporter.report(
            state, self._analyze(state), self.curriculum
        )
        state.report = feedback
        state.transcript.append(
            TranscriptEntry(role="interviewer", text=COMPLETION_REPLY)
        )
        return EngineTurn(reply=COMPLETION_REPLY, done=True, feedback=feedback)

    # -- helpers -------------------------------------------------------------

    def _plan_size(self, state: InterviewState) -> int:
        """The interview scope: the completed-day pool. There is no fixed
        question count — every completed day gets assessed, and the run
        ends when all of them carry terminal evidence."""
        return max(len(state.plan), 1)

    def _stamp_evidence(self, state: InterviewState, day: int, status: str, reason: str | None) -> None:
        """Attach the day's terminal evidence state to its question entry so
        the report can distinguish observed from estimated mastery without
        exposing internal state through the API (additive transcript meta)."""
        for entry in reversed(state.transcript):
            if (
                entry.role == "interviewer"
                and entry.day == day
                and entry.meta.get("action") is None
            ):
                entry.meta["evidence"] = status
                if reason:
                    entry.meta["evidence_reason"] = reason
                break

    def _analyze(self, state: InterviewState) -> ProfileAnalysis:
        candidate = state.candidate
        if candidate is None:
            return ProfileAnalysis()
        return analyze_profile(candidate)

    @staticmethod
    def _phase_for(question_index: int) -> str:
        for phase, (lo, hi) in PHASES.items():
            if lo <= question_index <= hi:
                return phase
        return "wrapup"
