"""Director agent: next-move planning with code-enforced invariants.

M3: the Director is now belief-driven. Invariants (>= 8 questions, >= 4
distinct days, no repeats until the plan is exhausted, follow-up depth <= 2)
stay enforced in code (PLANNING.md 9.3). Topic order is profile-aware (probe
days pulled forward); difficulty comes from the belief state with seniority
bias and recent-score escalation; question type follows the interview phase.
`decide` picks the next action (new question / follow-up / hint) from the
latest grade's signals. All decisions are deterministic — no LLM call.
"""

from __future__ import annotations

from app.core.belief import adjusted_difficulty, difficulty_for
from app.core.curriculum import DayInfo
from app.core.prompts import DEFAULT_QUESTION_DAYS, HINT_KEYWORDS, PHASES
from app.core.profile import ProfileAnalysis, prior_for_day
from app.domain.candidate import CandidateProfile
from app.domain.interview import InterviewState, Question

TERSE_ANSWERS = {
    "yes", "yeah", "yep", "yup", "ok", "okay", "k", "no", "nope",
    "nah", "sure", "maybe", "perhaps", "idk", "dunno", "fine", "good",
    "correct", "right", "true", "n/a", "na",
}

_TYPE_BY_PHASE = {"warmup": "concept", "core": "apply", "scenario": "design"}

HINT_AFTER_HONESTY_DEPTH = 3.0
FOLLOWUP_DEPTH_CAP = 2
FOLLOWUP_DEPTH_THRESHOLD = 3.5


class Director:
    """Plans and serves the next move, honoring coverage minimums."""

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

    def next_question(
        self,
        state: InterviewState,
        analysis: ProfileAnalysis,
        belief_state: dict[str, dict[str, float]],
        candidate: CandidateProfile,
    ) -> Question:
        """Next uncovered day from the plan with belief-driven difficulty and
        phase-appropriate type."""
        day = self._next_day(state)
        position = len(state.asked) + 1
        return self._question(day, position, state, belief_state, candidate)

    def decide(
        self,
        state: InterviewState,
        grade,
        answer: str,
        use_llm: bool = False,
    ) -> str:
        """Next action: 'ask_new' | 'follow_up' | 'hint'.

        Follow-ups fire on strong deterministic signals (terse answer,
        overclaim, vagueness, detected mistakes) and — in LLM mode — on
        shallow depth; never on a clean answer, so the 8-question minimum
        is always met. Hints fire when the candidate is stuck ('I don't
        know' / explicit hint request). Max 2 consecutive probes."""
        meta = state.meta
        if meta.get("consecutive_probes", 0) >= FOLLOWUP_DEPTH_CAP:
            return "ask_new"
        normalized = answer.strip().lower()
        if normalized in TERSE_ANSWERS:
            return "follow_up"
        if normalized in HINT_KEYWORDS or _asks_for_hint(normalized):
            return "hint"
        if grade is None:
            return "ask_new"
        if grade.honesty_bonus > 0 and grade.depth < HINT_AFTER_HONESTY_DEPTH:
            return "hint"
        if grade.overclaim or grade.vague or grade.mistakes:
            return "follow_up"
        if use_llm and grade.weighted_score < FOLLOWUP_DEPTH_THRESHOLD:
            return "follow_up"
        return "ask_new"

    # -- internals ----------------------------------------------------------

    def _next_day(self, state: InterviewState) -> int:
        asked_days = {q.day for q in state.asked}
        plan_days = [p["day"] for p in state.plan]
        for day in plan_days:
            if day not in asked_days:
                return day
        for day in self._core_days:
            if day not in asked_days:
                return day
        return plan_days[0] if plan_days else self._core_days[0]

    def _question(
        self,
        day: int,
        position: int,
        state: InterviewState,
        belief_state: dict[str, dict[str, float]],
        candidate: CandidateProfile,
    ) -> Question:
        prior = prior_for_day(candidate, day)
        entry = belief_state.get(str(day)) or {"mastery": prior, "confidence": 0.4}
        base = difficulty_for(
            entry["mastery"], candidate.member.yearsExperience or 0, entry["confidence"]
        )
        difficulty = adjusted_difficulty(
            base, list(state.meta.get("recent_scores", []))
        )
        return Question(
            day=day,
            text="",
            difficulty=difficulty,
            type=_TYPE_BY_PHASE.get(self._phase_for(position), "concept"),
        )

    @staticmethod
    def _phase_for(position: int) -> str:
        for phase, (lo, hi) in PHASES.items():
            if lo <= position <= hi:
                return phase
        return "wrapup"


def _asks_for_hint(normalized: str) -> bool:
    return any(
        marker in normalized
        for marker in (
            "i'm stuck",
            "im stuck",
            "i am stuck",
            "i'm lost",
            "im lost",
            "stuck on",
            "help me out",
        )
    )
