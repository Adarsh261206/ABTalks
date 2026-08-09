"""M11 evidence state machine: per-day interview evidence.

The interview is evidence-driven, not question-count-driven. Every
completed curriculum day accumulates an evidence record (answers, probes,
hints, flags) and closes with a terminal state:

- verified:           a clean answer at 4.5+ (single) or a 4.2+ average
                      with a clean latest answer and no missing expected
                      concepts — full interview verification
- sufficient:         a clean answer at 3.5+ — enough evidence to stop
                      short of full verification; missing concepts lower
                      the score (accuracy is recall-driven) and surface in
                      the report gaps, they do not block closure
- needs_validation:   a hint was needed (mastery not independently
                      confirmed), or the probing budget was exhausted —
                      the run now has enough evidence to say the day must
                      be re-validated

"Clean" means the answer carries no overclaim or vagueness flags (and for
verification, no missing expected concepts). A day still open after a
graded answer keeps gathering evidence through follow-up probes; strong
answers close a day with fewer questions, weak answers keep probing. The
run ends when every completed day is terminal (plan_complete). No LLM
involvement — fully deterministic.
"""

from __future__ import annotations

from typing import Any

EVIDENCE_VERIFIED = "verified"
EVIDENCE_SUFFICIENT = "sufficient"
EVIDENCE_NEEDS_VALIDATION = "needs_validation"

TERMINAL_STATES = frozenset(
    {EVIDENCE_VERIFIED, EVIDENCE_SUFFICIENT, EVIDENCE_NEEDS_VALIDATION}
)

# Max adaptive follow-up probes per day before the day must close.
PROBE_CAP = 2
# Max graded answers per day before the day must close.
ANSWER_CAP = 3
# A single clean answer at this score is full verification.
VERIFY_SINGLE_SCORE = 4.5
# Two or more answers average at this score for full verification.
VERIFY_AVG_SCORE = 4.2
# A clean answer at this score is sufficient evidence.
SUFFICIENT_SCORE = 3.5
# Hints are teaching support: any hint means the day cannot be certified.
HINT_CAP = 1


def new_record() -> dict[str, Any]:
    """Fresh evidence record for one curriculum day."""
    return {
        "answers": 0,
        "probes": 0,
        "hints": 0,
        "scores": [],
        "clean": [],
        "state": "open",
        "close_reason": None,
    }


def record_for(state, day: int) -> dict[str, Any]:
    """The evidence record for a day, created on first touch. Persisted in
    `state.meta` so the report and later turns can always read it."""
    statuses = state.meta.setdefault("day_evidence_status", {})
    return statuses.setdefault(str(day), new_record())


def evaluate(
    record: dict[str, Any],
    score: float,
    missing: list[str],
    overclaim: bool,
    vague: bool,
) -> str | None:
    """Advance the record with one graded answer. Returns the terminal
    state when the day closes, or None while evidence is still being
    gathered. `missing` are the expected concepts the answer did not
    address — they block full verification (the score already absorbed
    them) and are reported as gaps."""
    record["answers"] += 1
    record["scores"].append(score)
    flag_free = not overclaim and not vague
    clean = flag_free and not missing
    record["clean"].append(clean)

    if record["hints"] > 0:
        # A hint is teaching support: the answer was not independent, so
        # the day can be certified only as needs_validation.
        record["state"] = EVIDENCE_NEEDS_VALIDATION
        record["close_reason"] = "a hint was needed — mastery not independently confirmed"
        return record["state"]

    n = record["answers"]
    latest = score
    avg = sum(record["scores"]) / n

    if n == 1 and latest >= VERIFY_SINGLE_SCORE and clean:
        record["state"] = EVIDENCE_VERIFIED
        record["close_reason"] = f"single answer scored {latest:.1f} — no follow-ups needed"
        return record["state"]
    if n >= 2 and avg >= VERIFY_AVG_SCORE and latest >= SUFFICIENT_SCORE and flag_free:
        record["state"] = EVIDENCE_VERIFIED
        record["close_reason"] = f"average {avg:.1f} across {n} clean answers"
        return record["state"]
    if latest >= SUFFICIENT_SCORE and flag_free:
        record["state"] = EVIDENCE_SUFFICIENT
        record["close_reason"] = f"answer scored {latest:.1f} — sufficient evidence"
        return record["state"]
    if record["probes"] >= PROBE_CAP or n >= ANSWER_CAP:
        record["state"] = EVIDENCE_NEEDS_VALIDATION
        record["close_reason"] = "repeated weak answers exhausted the probing budget"
        return record["state"]
    return None


def day_closed(state, day: int) -> bool:
    return record_for(state, day)["state"] in TERMINAL_STATES


def plan_complete(state) -> bool:
    return all(day_closed(state, item["day"]) for item in state.plan)
