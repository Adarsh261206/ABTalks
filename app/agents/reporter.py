"""Reporter agent: final spec feedback from grades + priors (v1).

Aggregates per-day weighted scores recorded in the belief state, merges in
the profile analysis (probe days, priors), and produces the spec feedback
{summary, strengths, gaps, next}. LLM-written when online with a
deterministic fallback so the contract fields are always valid and never
empty (PLANNING.md edge case 93).
"""

from __future__ import annotations

import logging
import statistics

from pydantic import BaseModel, Field

from app.core.curriculum import DayInfo
from app.core.llm import LLMGateway, LLMGatewayError
from app.core.prompts import REPORTER_SYSTEM
from app.core.profile import ProfileAnalysis
from app.domain.interview import Feedback, InterviewState

logger = logging.getLogger("viva.agents.reporter")

_STRENGTH_THRESHOLD = 4.0
_GAP_THRESHOLD = 3.0


class _ReporterOutput(BaseModel):
    summary: str
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    next: list[str] = Field(default_factory=list)


class Reporter:
    """Writes the interview feedback; LLM first, deterministic fallback."""

    def __init__(
        self,
        gateway: LLMGateway,
        use_llm: bool = False,
        default_questions: int = 8,
    ) -> None:
        self._gateway = gateway
        self._use_llm = use_llm
        self._default_questions = default_questions

    async def report(
        self,
        state: InterviewState,
        analysis: ProfileAnalysis,
        curriculum: dict[int, DayInfo],
    ) -> Feedback:
        if self._use_llm:
            try:
                output = await self._gateway.structured(
                    [
                        {"role": "system", "content": REPORTER_SYSTEM},
                        {
                            "role": "user",
                            "content": self._prompt(state, analysis, curriculum),
                        },
                    ],
                    schema=_ReporterOutput,
                    temperature=0.0,
                )
                assert isinstance(output, _ReporterOutput)
                fallback = self._fallback(state, analysis, curriculum)
                return Feedback(
                    summary=output.summary or fallback.summary,
                    strengths=output.strengths or fallback.strengths,
                    gaps=output.gaps or fallback.gaps,
                    next=output.next or fallback.next,
                )
            except (LLMGatewayError, AssertionError) as exc:
                logger.warning("reporter fell back to deterministic feedback: %s", exc)
        return self._fallback(state, analysis, curriculum)

    # -- LLM path ---------------------------------------------------------

    def _prompt(
        self,
        state: InterviewState,
        analysis: ProfileAnalysis,
        curriculum: dict[int, DayInfo],
    ) -> str:
        transcript = "\n".join(
            f"{t.role}: {t.text[:400]}" for t in state.transcript[-20:]
        )
        grades = _grade_summary(state)
        return (
            f"Interview transcript (last turns):\n{transcript or 'empty'}\n\n"
            f"Per-day grade averages (0-5 weighted): {grades or 'none'}\n\n"
            f"Profile priors (0-1 mastery estimate from record): "
            f"{_priors_summary(analysis)}\n"
            f"Days flagged in the record for review: "
            f"{analysis.probe_days or 'none'}\n\n"
            f"Covered days: {state.covered_days}. Questions asked: {len(state.asked)}."
        )

    # -- deterministic fallback ---------------------------------------------

    def _fallback(
        self,
        state: InterviewState,
        analysis: ProfileAnalysis,
        curriculum: dict[int, DayInfo],
    ) -> Feedback:
        avgs = _grade_summary(state)
        n = len(state.asked)
        covered = list(state.covered_days)
        early = n < self._default_questions

        strengths: list[str] = []
        for day, avg in sorted(avgs.items(), key=lambda kv: kv[1], reverse=True):
            if avg >= _STRENGTH_THRESHOLD:
                strengths.append(f"Strong command of Day {day} — {_title(day, curriculum)}.")
            if len(strengths) >= 3:
                break
        if not strengths:
            strengths = ["Engaged with every question asked."]

        gaps: list[str] = []
        for day, avg in sorted(avgs.items(), key=lambda kv: kv[1]):
            if avg < _GAP_THRESHOLD:
                gaps.append(
                    f"Day {day} — {_title(day, curriculum)}: answers lacked depth and precision."
                )
            if len(gaps) >= 3:
                break
        for day in analysis.probe_days:
            if day not in covered:
                gaps.append(
                    f"Day {day} — {_title(day, curriculum)}: flagged in your record "
                    "but not discussed this run."
                )
            if len(gaps) >= 3:
                break
        if early and len(gaps) < 3:
            gaps.append(
                "The interview was ended before the full question plan — a full "
                "run gives a more reliable assessment."
            )
        if not gaps:
            gaps.append(
                "Deeper per-topic assessment needs a longer run — aim for the "
                "full question sequence next time."
            )

        next_steps: list[str] = []
        for day, avg in sorted(avgs.items(), key=lambda kv: kv[1]):
            if avg < _GAP_THRESHOLD:
                next_steps.append(
                    f"Revisit Day {day} — {_title(day, curriculum)}: walk through your "
                    "implementation step by step and explain the trade-offs you made."
                )
            if len(next_steps) >= 2:
                break
        for day in analysis.probe_days:
            if day not in covered:
                next_steps.append(
                    f"Book a review session on Day {day} — {_title(day, curriculum)}: "
                    "your mission record shows it needs reinforcement."
                )
            if len(next_steps) >= 3:
                break
        if not next_steps:
            next_steps = [
                "Revisit your cohort notes on the days covered in this run.",
                "Run another practice interview to broaden topic coverage.",
                "Rehearse explaining each mission in terms of the decisions you made and what you would improve.",
            ]

        summary = f"Practice interview completed after {n} questions across {len(covered)} curriculum days."
        if gaps and "full question plan" not in gaps[0]:
            summary += " A few areas need reinforcement — see the gaps below."
        elif strengths and len(strengths) >= 2:
            summary += " Overall you demonstrated solid command of the topics covered."
        elif early:
            summary += " Ending early leaves the assessment incomplete — a full run is more reliable."

        return Feedback(
            summary=summary,
            strengths=strengths,
            gaps=gaps,
            next=next_steps,
        )


def _grade_summary(state: InterviewState) -> dict[int, float]:
    return {
        int(day): round(statistics.mean(scores), 2)
        for day, scores in state.belief.items()
        if scores
    }


def _priors_summary(analysis: ProfileAnalysis) -> str:
    return "; ".join(
        f"Day {day}: {prior:.2f}" for day, prior in sorted(analysis.priors.items())
    )


def _title(day: int, curriculum: dict[int, DayInfo]) -> str:
    info = curriculum.get(day)
    return info.title if info else f"Day {day}"
