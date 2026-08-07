"""M2 interview core: profile-aware, graded, agent-rendered engine.

Same contract as the M1 `InterviewEngine` (start/process over
`InterviewState`), so the service layer and routes are unchanged: the
Director plans, the Grader scores each answer into the belief state, the
Interviewer renders, and the Reporter writes the final feedback. When the
LLM is offline (mock provider) every agent degrades to a deterministic
fallback and the interview still satisfies the hard minimums
(>= 8 questions, >= 4 days, valid feedback).
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.agents.director import Director
from app.agents.grader import Grader
from app.agents.interviewer import Interviewer
from app.agents.reporter import Reporter
from app.config import settings
from app.core.curriculum import DayInfo, load_curriculum
from app.core.llm import LLMGateway
from app.core.prompts import COMPLETION_REPLY, END_KEYWORDS, PHASES
from app.core.profile import ProfileAnalysis, analyze_profile
from app.domain.candidate import CandidateProfile
from app.domain.interview import EngineTurn, InterviewState, TranscriptEntry
from app.infrastructure.llm_mock import MockLLMProvider

logger = logging.getLogger("viva.engine")


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
        self._director = Director(self.curriculum, default_questions)
        self._interviewer = Interviewer(self._gateway, use_llm)
        self._grader = Grader(self._gateway, use_llm)
        self._reporter = Reporter(
            self._gateway, use_llm, default_questions=default_questions
        )

    # -- lifecycle -------------------------------------------------------

    async def start(self, state: InterviewState, candidate: CandidateProfile) -> str:
        state.candidate = candidate
        state.plan = self._director.build_plan(analyze_profile(candidate))
        welcome = await self._interviewer.render_welcome(candidate)
        state.transcript.append(TranscriptEntry(role="interviewer", text=welcome))
        return welcome

    async def process(self, state: InterviewState, message: str) -> EngineTurn:
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
            return await self._wrap_up(state, reason="completed")

        if state.asked:
            await self._grade_answer(state, message)

        return await self._ask_next(state)

    # -- interview flow ----------------------------------------------------

    async def _grade_answer(self, state: InterviewState, message: str) -> None:
        question = state.asked[-1]
        grade = await self._grader.grade(
            question,
            message,
            self.curriculum.get(question.day),
            state.candidate,
        )
        state.belief.setdefault(str(question.day), []).append(grade.weighted_score)

    async def _ask_next(self, state: InterviewState) -> EngineTurn:
        question = self._director.next_question(state)
        candidate = state.candidate
        question.text = await self._interviewer.render_question(
            question,
            self.curriculum.get(question.day),
            candidate,
            phase=self._phase_for(len(state.asked) + 1),
            position=len(state.asked) + 1,
            total=self.default_questions,
        )
        state.asked.append(question)
        if question.day not in state.covered_days:
            state.covered_days.append(question.day)
        state.transcript.append(
            TranscriptEntry(role="interviewer", text=question.text, day=question.day)
        )
        state.phase = self._phase_for(len(state.asked))
        return EngineTurn(reply=question.text)

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
