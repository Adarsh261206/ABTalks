"""Profile analyzer: candidate signals -> per-day mastery priors.

Deterministic inference (PLANNING.md Phase 9.12 / 17.8): attempts, first-try
rate, skipped and failed days, and role seniority produce a per-day mastery
prior (0-1) plus the days worth probing. No LLM — pure arithmetic so the
behavior is reproducible and unit-testable.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.candidate import CandidateProfile, Mission

_STRONG_ROLE_HINTS = (
    "senior",
    "lead",
    "architect",
    "principal",
    "staff",
    "manager",
    "engineer",
)
_NON_TECH_ROLE_HINTS = (
    "hr",
    "marketing",
    "sales",
    "operations",
    "analyst",
    "recruiter",
    "finance",
    "accountant",
    "researcher",
    "manager",
    "business",
)
_SKIPPED_PRIOR = 0.2
_FAILED_PRIOR = 0.3
_PASSED_BASE_PRIOR = 0.7
_MISSING_PRIOR = 0.2
_MIN_PRIOR = 0.05
_MAX_PRIOR = 0.95


class ProfileAnalysis(BaseModel):
    """Output of `analyze_profile`: priors for every curriculum day,
    days to probe (failed/skipped/high-attempt), and a coarse profile type."""

    priors: dict[int, float] = Field(default_factory=dict)
    probe_days: list[int] = Field(default_factory=list)
    profile_type: str = "average"


def analyze_profile(candidate: CandidateProfile) -> ProfileAnalysis:
    """Infer per-day mastery priors and probe days from the candidate record."""
    missions = {m.day: m for m in candidate.missions}
    first_try_ratio = _first_try_ratio(candidate)
    years = candidate.member.yearsExperience or 0
    seniority_bonus = _seniority_bonus(years, candidate.member.jobRole)

    priors = {
        day: _clamp(_prior_for(mission, first_try_ratio) + seniority_bonus)
        for day, mission in missions.items()
    }
    probe_days = sorted(
        day
        for day, mission in missions.items()
        if _is_probe_day(mission)
    )

    return ProfileAnalysis(
        priors=priors,
        probe_days=probe_days,
        profile_type=_classify(missions, first_try_ratio, candidate),
    )


def prior_for_day(candidate: CandidateProfile, day: int) -> float:
    """Mastery prior for a single day (used for days missing from missions,
    which are treated as skipped per the spec)."""
    missions = {m.day: m for m in candidate.missions}
    mission = missions.get(day)
    first_try_ratio = _first_try_ratio(candidate)
    bonus = _seniority_bonus(
        candidate.member.yearsExperience or 0, candidate.member.jobRole
    )
    if mission is None:
        return _clamp(_MISSING_PRIOR + bonus)
    return _clamp(_prior_for(mission, first_try_ratio) + bonus)


def _prior_for(mission: Mission, first_try_ratio: float) -> float:
    if mission.skipped:
        return _SKIPPED_PRIOR
    if not mission.passed:
        return _FAILED_PRIOR
    prior = _PASSED_BASE_PRIOR - 0.05 * max(mission.attempts - 1, 0)
    if first_try_ratio >= 0.5:
        prior += 0.05
    return prior


def _first_try_ratio(candidate: CandidateProfile) -> float:
    signals = candidate.signals
    if signals is None or signals.missionsCompleted <= 0:
        return 0.0
    return signals.missionsFirstTry / signals.missionsCompleted


def _seniority_bonus(years: int, role: str) -> float:
    bonus = 0.0
    if years >= 10:
        bonus += 0.15
    elif years >= 5:
        bonus += 0.1
    role_lower = role.lower()
    if any(hint in role_lower for hint in _STRONG_ROLE_HINTS):
        bonus += 0.05
    return bonus


def _is_probe_day(mission: Mission) -> bool:
    return mission.skipped or not mission.passed or mission.attempts >= 4


def _classify(
    missions: dict[int, Mission], first_try_ratio: float, candidate: CandidateProfile
) -> str:
    role_lower = candidate.member.jobRole.lower()
    if any(hint in role_lower for hint in _NON_TECH_ROLE_HINTS):
        return "non_technical"

    passed = [m for m in missions.values() if m.passed]
    failed = [m for m in missions.values() if not m.passed and not m.skipped]
    if not missions:
        return "average"
    pass_ratio = len(passed) / len(missions)
    avg_attempts = sum(m.attempts for m in passed) / max(len(passed), 1)

    if pass_ratio < 0.5 or len(failed) >= 3:
        return "struggling"
    if avg_attempts >= 3 and pass_ratio >= 0.5:
        return "grinder"
    if pass_ratio >= 0.8 and first_try_ratio >= 0.5:
        return "strong"
    return "average"


def _clamp(value: float) -> float:
    return max(_MIN_PRIOR, min(_MAX_PRIOR, value))
