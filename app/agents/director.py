"""Director agent: next-move planning with code-enforced invariants.

M3: the Director is now belief-driven. Invariants (>= 8 questions, >= 4
distinct days, no repeats until the plan is exhausted, follow-up depth <= 2)
stay enforced in code (PLANNING.md 9.3). Interview rules: the pool is the
candidate's COMPLETED curriculum days only — failed, skipped, and
not-started days are never asked about (they surface as record-based
diagnostics in the report instead). Topic order is profile-aware: the
warm-up opens on the highest-prior completed day (easiest), then the
remaining completed days struggle-first (low mastery / failed-then-passed /
multiple-attempt), then recently completed days; difficulty comes from the
belief state with seniority bias and recent-score escalation; question type
follows the interview phase. M11: the interview is evidence-driven, not
question-count-driven — there is no fixed length. `decide` closes a day
once its evidence record is terminal (verified / sufficient /
needs_validation) and reports `wrap_up` when every completed day is; open
days keep gathering evidence through follow-up probes. All decisions are
deterministic — no LLM call.
"""

from __future__ import annotations

from app.core.belief import adjusted_difficulty, difficulty_for
from app.core.curriculum import DayInfo
from app.core.evidence import HINT_CAP, TERMINAL_STATES, day_closed, plan_complete, record_for
from app.core.prompts import HINT_KEYWORDS, PHASES
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

    def build_plan(self, analysis: ProfileAnalysis) -> list[dict]:
        """Profile-aware question sequence over the COMPLETED-day pool.

        The pool is `analysis.completed_days` (passed missions) only: failed,
        skipped, and not-started curriculum days are never asked about. The
        warm-up is the completed day with the highest mastery prior (easiest,
        comfortable open); the rest are ordered struggle-first — lower prior
        (failed-then-passed, low mastery, multiple attempts) before recently
        completed days (later curriculum position used as the recency proxy,
        since the mission record carries no completion timestamps). No
        duplicates."""
        pool = sorted(
            analysis.completed_days,
            key=lambda d: (analysis.priors.get(d, 0.5), d),
        )
        ordered: list[int] = []
        if pool:
            warmup = pool[-1]
            ordered.append(warmup)
            ordered.extend(pool[:-1])
        return [{"day": d, "type": "concept", "difficulty": "L1"} for d in ordered]

    def next_question(
        self,
        state: InterviewState,
        analysis: ProfileAnalysis,
        belief_state: dict[str, dict[str, float]],
        candidate: CandidateProfile,
    ) -> Question | None:
        """Next uncovered pool day with belief-driven difficulty and
        phase-appropriate type; None when the completed-day pool is
        exhausted (the engine then wraps up the interview)."""
        day = self._next_day(state)
        if day is None:
            return None
        position = len(state.asked) + 1
        return self._question(day, position, state, belief_state, candidate)

    def decide(
        self,
        state: InterviewState,
        grade,
        answer: str,
        use_llm: bool = False,
    ) -> str:
        """Next action: 'ask_new' | 'follow_up' | 'hint' | 'wrap_up'.

        The day's evidence record has already been advanced by the engine:
        a terminal state (verified / sufficient / needs_validation) means
        the day is done — move to the next open day, or `wrap_up` when
        every completed day is closed. An open day always gathers more
        evidence: terse answers, overclaims, vagueness, and mistakes probe
        with follow-ups; stuck/honest candidates get a hint (at most one
        per day). Max 2 probes per day, enforced by the evidence machine."""
        day = state.asked[-1].day if state.asked else None
        if grade is None or day is None:
            return "ask_new"
        record = record_for(state, day)
        if record["state"] in TERMINAL_STATES:
            return "wrap_up" if plan_complete(state) else "ask_new"
        normalized = answer.strip().lower()
        if normalized in TERSE_ANSWERS:
            return "follow_up"
        if normalized in HINT_KEYWORDS or _asks_for_hint(normalized):
            return "hint" if record["hints"] < HINT_CAP else "follow_up"
        if grade.honesty_bonus > 0 and grade.depth < HINT_AFTER_HONESTY_DEPTH:
            return "hint" if record["hints"] < HINT_CAP else "follow_up"
        if grade.overclaim or grade.vague or grade.mistakes:
            return "follow_up"
        if use_llm and grade.weighted_score < FOLLOWUP_DEPTH_THRESHOLD:
            return "follow_up"
        return "follow_up"

    # -- internals ----------------------------------------------------------

    def _next_day(self, state: InterviewState) -> int | None:
        asked_days = {q.day for q in state.asked}
        for day in (p["day"] for p in state.plan):
            if day not in asked_days and not day_closed(state, day):
                return day
        return None

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
