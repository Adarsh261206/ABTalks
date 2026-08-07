"""Belief state: per-day mastery updates and difficulty mapping (M3).

PLANNING.md Phase 9.4/9.9/9.12: mastery blends the profile prior with live
graded answers (m = 0.7 * m_prev + 0.3 * score/5); confidence grows with
each probe on a day; difficulty derives from mastery plus seniority bias,
then is adjusted by recent scores (two strong answers escalate, two weak
answers de-escalate). Pure arithmetic — no LLM — so adaptation is
deterministic and testable.
"""

from __future__ import annotations

from typing import Any

from app.core.profile import ProfileAnalysis

MASTERY_PRIOR_WEIGHT = 0.7
MASTERY_LIVE_WEIGHT = 0.3
CONFIDENCE_STEP = 0.25
CONFIDENCE_FLOOR = 0.4
CONFIDENCE_CAP = 1.0

L1_MAX_MASTERY = 0.4
L2_MAX_MASTERY = 0.7

SENIOR_YEARS_L2 = 8
SENIOR_YEARS_L3 = 15
BIAS_CONFIDENCE_CEILING = 0.6

ESCALATE_SCORE = 4.5
DEESCALATE_SCORE = 2.5

DIFFICULTY_LADDER = ("L1", "L2", "L3")


def init_belief_state(analysis: ProfileAnalysis) -> dict[str, dict[str, float]]:
    """Per-day mastery vector initialized from the profile priors."""
    return {
        str(day): {"mastery": prior, "confidence": CONFIDENCE_FLOOR}
        for day, prior in analysis.priors.items()
    }


def ensure_day(
    belief_state: dict[str, dict[str, float]], day: int, prior: float
) -> dict[str, float]:
    """Return (creating if needed) the belief entry for a day."""
    key = str(day)
    if key not in belief_state:
        belief_state[key] = {"mastery": prior, "confidence": CONFIDENCE_FLOOR}
    return belief_state[key]


def update_belief(
    belief_state: dict[str, dict[str, float]],
    day: int,
    weighted_score: float,
    prior: float,
) -> None:
    """Bayesian-ish weighted update per PLANNING.md 9.12: mastery moves toward
    the normalized live score; confidence grows with every probe."""
    entry = ensure_day(belief_state, day, prior)
    normalized = max(0.0, min(1.0, weighted_score / 5.0))
    entry["mastery"] = (
        MASTERY_PRIOR_WEIGHT * entry["mastery"] + MASTERY_LIVE_WEIGHT * normalized
    )
    entry["confidence"] = min(
        CONFIDENCE_CAP, entry["confidence"] + CONFIDENCE_STEP
    )


def difficulty_for(
    mastery: float, years: int = 0, confidence: float = CONFIDENCE_CAP
) -> str:
    """Difficulty tier from mastery; seniority biases the starting tiers
    (low-confidence entries) up to at most L2 so genuinely weak days stay
    in teaching mode (PLANNING.md 9.4)."""
    if mastery <= L1_MAX_MASTERY:
        tier = "L1"
    elif mastery <= L2_MAX_MASTERY:
        tier = "L2"
    else:
        tier = "L3"
    if confidence < BIAS_CONFIDENCE_CEILING and tier == "L1":
        if years >= SENIOR_YEARS_L2 and mastery >= L1_MAX_MASTERY:
            tier = "L2"
    return tier


def adjusted_difficulty(base: str, recent_scores: list[float]) -> str:
    """Escalate after two strong answers; de-escalate after two weak ones
    (PLANNING.md 9.9)."""
    if len(recent_scores) >= 2 and all(
        s >= ESCALATE_SCORE for s in recent_scores[-2:]
    ):
        return _shift(base, +1)
    if len(recent_scores) >= 2 and all(
        s <= DEESCALATE_SCORE for s in recent_scores[-2:]
    ):
        return _shift(base, -1)
    return base


def _shift(tier: str, delta: int) -> str:
    index = DIFFICULTY_LADDER.index(tier) + delta
    index = max(0, min(len(DIFFICULTY_LADDER) - 1, index))
    return DIFFICULTY_LADDER[index]
