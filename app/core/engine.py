from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.core.curriculum import DayInfo, load_curriculum
from app.core.prompts import (
    COMPLETION_REPLY,
    DEFAULT_QUESTION_DAYS,
    END_KEYWORDS,
    FALLBACK_QUESTION,
    FALLBACK_WORK_QUESTION,
    PHASES,
    WELCOME_TEMPLATE,
    humanize_objective,
    question_template,
)
from app.domain.candidate import CandidateProfile
from app.domain.interview import EngineTurn, Feedback, InterviewState, Question, TranscriptEntry


class InterviewEngine:
    """Deterministic interview state machine (M1).

    M2+ swaps the question source for the adaptive Director/Grader/Prober
    agents without changing the contract, state shape, or invariants.
    """

    def __init__(
        self,
        curriculum: dict[int, DayInfo] | None = None,
        curriculum_path: Path | None = None,
        default_questions: int = settings.default_questions,
        max_turns: int = settings.max_turns,
    ) -> None:
        self.default_questions = default_questions
        self.max_turns = max_turns
        self.curriculum = (
            curriculum if curriculum is not None else load_curriculum(curriculum_path)
        )

    # -- lifecycle -------------------------------------------------------

    def start(self, state: InterviewState, candidate: CandidateProfile) -> str:
        state.candidate = candidate
        state.plan = [
            {"day": d, "type": "concept", "difficulty": "L1"}
            for d in self._question_days()
        ]
        welcome = WELCOME_TEMPLATE.format(name=candidate.display_name)
        state.transcript.append(TranscriptEntry(role="interviewer", text=welcome))
        return welcome

    def process(self, state: InterviewState, message: str) -> EngineTurn:
        state.turn_count += 1
        state.transcript.append(
            TranscriptEntry(role="candidate", text=message, meta={"turn": state.turn_count})
        )

        normalized = " ".join(message.lower().split())
        force_wrap = (
            state.turn_count >= self.max_turns
            or len(state.asked) >= self.default_questions
            or normalized in END_KEYWORDS
        )

        if force_wrap:
            return self._wrap_up(state, reason="completed")

        return self._ask_next(state)

    # -- interview flow ----------------------------------------------------

    def _question_days(self) -> list[int]:
        days = [d for d in DEFAULT_QUESTION_DAYS if d in self.curriculum]
        return days or list(DEFAULT_QUESTION_DAYS)

    def _ask_next(self, state: InterviewState) -> EngineTurn:
        days = self._question_days()
        question = Question(
            day=days[len(state.asked)],
            text="",
            difficulty="L1",
            type="concept",
        )
        question.text = self._build_question(question.day, state)
        state.asked.append(question)
        if question.day not in state.covered_days:
            state.covered_days.append(question.day)
        state.transcript.append(
            TranscriptEntry(role="interviewer", text=question.text, day=question.day)
        )
        state.phase = self._phase_for(len(state.asked))
        return EngineTurn(reply=question.text)

    def _build_question(self, day_no: int, state: InterviewState) -> str:
        day = self.curriculum.get(day_no)
        if day is None:
            return FALLBACK_QUESTION.format(day=day_no)
        objective = day.objectives[0] if day.objectives else ""
        stem = humanize_objective(objective.rstrip(".").strip())
        if not stem:
            return FALLBACK_WORK_QUESTION.format(day=day_no, title=day.title)
        return question_template(day=day_no, title=day.title, stem=stem)

    @staticmethod
    def _phase_for(question_index: int) -> str:
        for phase, (lo, hi) in PHASES.items():
            if lo <= question_index <= hi:
                return phase
        return "wrapup"

    # -- completion ---------------------------------------------------------

    def _wrap_up(self, state: InterviewState, reason: str) -> EngineTurn:
        state.status = "completed"
        state.phase = "wrapup"
        state.completed_reason = reason
        feedback = self._build_feedback(state)
        state.report = feedback
        state.transcript.append(
            TranscriptEntry(role="interviewer", text=COMPLETION_REPLY)
        )
        return EngineTurn(reply=COMPLETION_REPLY, done=True, feedback=feedback)

    def _build_feedback(self, state: InterviewState) -> Feedback:
        """Deterministic, honest M1 feedback from measurable signals only.
        The RAG-grounded Grader + Reporter (M2-M4) replace the heuristics."""
        n = len(state.asked)
        covered = len(state.covered_days)
        early = state.completed_reason in {None, ""} or (
            len(state.asked) < self.default_questions
        )
        answers = [t.text for t in state.transcript if t.role == "candidate"]
        avg_len = sum(len(a) for a in answers) / max(len(answers), 1)

        summary = (
            f"Practice interview completed after {n} questions across {covered} "
            f"curriculum days."
        )
        strengths = ["Engaged with every question asked."]
        if avg_len >= 120:
            strengths.append("Provided detailed, substantive answers.")
        gaps: list[str] = []
        if early:
            gaps.append(
                "The interview was ended before the full question plan — a full "
                "run gives a more reliable assessment."
            )
        if avg_len < 60:
            gaps.append(
                "Answers were on the shorter side — expand with your reasoning "
                "and the engineering decisions behind each answer."
            )
        if not gaps:
            gaps.append(
                "Deeper per-topic assessment needs a longer run — aim for the "
                "full question sequence next time."
            )
        next_steps = [
            "Revisit your cohort notes on the days covered in this run.",
            "Run another practice interview to broaden topic coverage.",
            "Rehearse explaining each mission in terms of the decisions you made and what you would improve.",
        ]
        return Feedback(
            summary=summary, strengths=strengths, gaps=gaps, next=next_steps
        )
