"""Director agent: next-move planning with code-enforced invariants.

M2 scope: a deterministic planner. Invariants (>= 8 questions, >= 4 distinct
days, no repeats until the plan is exhausted) are enforced in code, never by
prompt (PLANNING.md Phase 9.3). Topic order is profile-aware: probe days
(failed / skipped / high-attempt missions) are pulled forward after the
warm-up day. M3 replaces the topic choice with an LLM decision while keeping
these invariants.
"""

from __future__ import annotations

from app.core.curriculum import DayInfo
from app.core.prompts import DEFAULT_QUESTION_DAYS
from app.core.profile import ProfileAnalysis
from app.domain.interview import InterviewState, Question


class Director:
    """Plans and serves the next question, honoring coverage minimums."""

    def __init__(self, curriculum: dict[int, DayInfo], default_questions: int = 8) -> None:
        self._curriculum = curriculum
        self.default_questions = default_questions
        self._core_days = self._resolve_core_days()

    def _resolve_core_days(self) -> list[int]:
        days = [d for d in DEFAULT_QUESTION_DAYS if d in self._curriculum]
        return days or sorted(self._curriculum) or list(DEFAULT_QUESTION_DAYS)

    def build_plan(self, analysis: ProfileAnalysis) -> list[dict]:
        """Profile-aware question sequence: warm-up day first, then probe
        days (failed/skipped/high-attempt), then remaining core days, then
        any extra curriculum days. No duplicates."""
        probes = [d for d in analysis.probe_days if d in self._curriculum]
        ordered: list[int] = []
        core = list(self._core_days)
        if core:
            ordered.append(core[0])
        for d in core[1:]:
            if d in probes:
                ordered.append(d)
        for d in core[1:]:
            if d not in ordered:
                ordered.append(d)
        for d in sorted(self._curriculum):
            if d not in ordered:
                ordered.append(d)
        return [{"day": d, "type": "concept", "difficulty": "L1"} for d in ordered]

    def next_question(self, state: InterviewState) -> Question:
        """First planned day not yet covered; falls back to any unasked day
        when the plan is exhausted (long sessions, max_turns guard)."""
        asked_days = {q.day for q in state.asked}
        plan_days = [p["day"] for p in state.plan]
        for day in plan_days:
            if day not in asked_days:
                return self._question(day)
        for day in self._core_days:
            if day not in asked_days:
                return self._question(day)
        return self._question(plan_days[0] if plan_days else self._core_days[0])

    def _question(self, day: int) -> Question:
        return Question(day=day, text="", difficulty="L1", type="concept")
