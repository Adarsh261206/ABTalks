"""Interviewer agent: renders the Director's decision in a human voice.

Single responsibility (PLANNING.md Phase 8.2/9.1): *how to say it*. Uses the
LLM when online; falls back to the deterministic M1 templates so mock mode
never produces garbage. The candidate never sees scores or internal analysis.
"""

from __future__ import annotations

import logging

from app.core.curriculum import DayInfo
from app.core.llm import LLMGateway, LLMGatewayError
from app.core.prompts import (
    INTERVIEWER_QUESTION_USER,
    INTERVIEWER_SYSTEM,
    INTERVIEWER_WELCOME_USER,
    WELCOME_TEMPLATE,
    humanize_objective,
    question_template,
)
from app.domain.candidate import CandidateProfile
from app.domain.interview import Question

logger = logging.getLogger("viva.agents.interviewer")


class Interviewer:
    """Renders welcome and questions; LLM first, deterministic fallback."""

    def __init__(self, gateway: LLMGateway, use_llm: bool = False) -> None:
        self._gateway = gateway
        self._use_llm = use_llm

    async def render_welcome(self, candidate: CandidateProfile) -> str:
        if self._use_llm:
            try:
                return await self._gateway.chat(
                    [
                        {"role": "system", "content": INTERVIEWER_SYSTEM},
                        {
                            "role": "user",
                            "content": INTERVIEWER_WELCOME_USER.format(
                                profile=_profile_summary(candidate)
                            ),
                        },
                    ],
                    temperature=0.4,
                    max_tokens=120,
                )
            except LLMGatewayError as exc:
                logger.warning("interviewer welcome fell back to template: %s", exc)
        return WELCOME_TEMPLATE.format(name=candidate.display_name)

    async def render_question(
        self,
        question: Question,
        day: DayInfo | None,
        candidate: CandidateProfile,
        phase: str,
        position: int,
        total: int,
    ) -> str:
        if self._use_llm:
            try:
                return await self._gateway.chat(
                    [
                        {"role": "system", "content": INTERVIEWER_SYSTEM},
                        {
                            "role": "user",
                            "content": INTERVIEWER_QUESTION_USER.format(
                                phase=phase,
                                position=position,
                                total=total,
                                profile=_profile_summary(candidate),
                                day=question.day,
                                title=day.title if day else "",
                                day_type=day.type if day else "concept",
                                objectives="; ".join(day.objectives) if day else "",
                            ),
                        },
                    ],
                    temperature=0.4,
                    max_tokens=300,
                )
            except LLMGatewayError as exc:
                logger.warning("interviewer question fell back to template: %s", exc)
        return self._fallback_question(question, day)

    def _fallback_question(self, question: Question, day: DayInfo | None) -> str:
        if day is None:
            return f"Let's talk about Day {question.day}. What did you build that day?"
        objective = day.objectives[0] if day.objectives else ""
        stem = humanize_objective(objective.rstrip(".").strip())
        if not stem:
            return f"Let's talk about Day {question.day} — {day.title}. Tell me about your work on it."
        return question_template(day=question.day, title=day.title, stem=stem)


def _profile_summary(candidate: CandidateProfile) -> str:
    missions = ", ".join(
        f"Day {m.day} ({'passed' if m.passed else ('skipped' if m.skipped else 'failed')}, "
        f"{m.attempts} attempts)"
        for m in sorted(candidate.missions, key=lambda m: m.day)
    )
    signals = candidate.signals
    signal_text = (
        f"commitDays={signals.commitDays}, missionsCompleted={signals.missionsCompleted}, "
        f"missionsFirstTry={signals.missionsFirstTry}"
        if signals
        else "no signals"
    )
    return (
        f"Name: {candidate.display_name}; Role: {candidate.member.jobRole}; "
        f"Years experience: {candidate.member.yearsExperience}. "
        f"Signals: {signal_text}. Missions: {missions or 'none'}"
    )
