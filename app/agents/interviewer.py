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
    FOLLOWUP_USER,
    HINT_USER,
    INTERVIEWER_QUESTION_USER,
    INTERVIEWER_SYSTEM,
    INTERVIEWER_WELCOME_USER,
    WELCOME_TEMPLATE,
    humanize_objective,
    question_template,
)
from app.domain.candidate import CandidateProfile
from app.domain.interview import Question
from app.agents.grader import ProbeTarget

logger = logging.getLogger("viva.agents.interviewer")


class Interviewer:
    """Renders welcome, questions, follow-ups and hints; LLM first,
    deterministic fallback."""

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
                                difficulty=question.difficulty,
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

    async def render_followup(
        self,
        target: ProbeTarget,
        day: DayInfo | None,
        candidate: CandidateProfile,
    ) -> str:
        if self._use_llm:
            try:
                return await self._gateway.chat(
                    [
                        {"role": "system", "content": INTERVIEWER_SYSTEM},
                        {
                            "role": "user",
                            "content": FOLLOWUP_USER.format(
                                answer=target.ref_quote,
                                kind=target.kind,
                                target=target.target,
                                ref_day=target.ref_day,
                                objective=target.objective or "unavailable",
                                detected=", ".join(target.detected_concepts) or "none",
                                missing=", ".join(target.missing_concepts) or "none",
                                followup_reason=target.followup_reason
                                or "no explicit reason",
                            ),
                        },
                    ],
                    temperature=0.4,
                    max_tokens=300,
                )
            except LLMGatewayError as exc:
                logger.warning("interviewer follow-up fell back to template: %s", exc)
        return self._fallback_followup(target, day)

    async def render_hint(
        self,
        day: DayInfo | None,
        difficulty: str,
    ) -> str:
        if self._use_llm:
            try:
                return await self._gateway.chat(
                    [
                        {"role": "system", "content": INTERVIEWER_SYSTEM},
                        {
                            "role": "user",
                            "content": HINT_USER.format(
                                day=day.day if day else "?",
                                title=day.title if day else "",
                                difficulty=difficulty,
                                objectives="; ".join(day.objectives) if day else "",
                            ),
                        },
                    ],
                    temperature=0.3,
                    max_tokens=200,
                )
            except LLMGatewayError as exc:
                logger.warning("interviewer hint fell back to template: %s", exc)
        day_label = f"Day {day.day}" if day else "this topic"
        objective = day.objectives[0].rstrip(".") if day and day.objectives else ""
        if objective:
            return (
                f"Here's a starting point for {day_label}: think about {objective.lower()}. "
                "Take your time — I'll wait."
            )
        return (
            f"Here's a starting point for {day_label}: focus on the core ideas from "
            "your cohort notes. Take your time — I'll wait."
        )

    def _fallback_question(self, question: Question, day: DayInfo | None) -> str:
        if day is None:
            return f"Let's talk about Day {question.day}. What did you build that day?"
        objective = day.objectives[0] if day.objectives else ""
        stem = humanize_objective(objective.rstrip(".").strip())
        if not stem:
            return f"Let's talk about Day {question.day} — {day.title}. Tell me about your work on it."
        return question_template(day=question.day, title=day.title, stem=stem)

    @staticmethod
    def _fallback_followup(target: ProbeTarget, day: DayInfo | None) -> str:
        day_label = f"Day {target.ref_day}" if target.ref_day else "this"
        if target.kind == "challenge":
            return (
                f"Hold on — you said \"{target.ref_quote}\". Let's slow down on "
                f"{day_label}. Your mission record shows this wasn't completed — "
                "walk me through the parts you actually built and where you got stuck."
            )
        if target.kind == "probe" and target.missing_concepts:
            missing = ", ".join(target.missing_concepts[:2])
            return (
                f"Good start on {day_label} — you covered "
                f"{', '.join(target.detected_concepts[:2]) or 'the basics'}. "
                f"The objective expects {missing} too — walk me through your "
                f"understanding of that part."
            )
        if target.kind == "clarify":
            return (
                f"You said \"{target.ref_quote}\" — could you be more concrete? "
                "Tell me the specific steps, not just the topic."
            )
        if target.kind == "verify":
            return (
                f"Let's stress-test that: {target.target}. How would you defend "
                f"that choice for {day_label}?"
            )
        return (
            f"You mentioned {target.target} — walk me through how you approached "
            f"it and what you measured."
        )


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
