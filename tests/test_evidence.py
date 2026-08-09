"""M11 tests: the per-day evidence state machine (app/core/evidence.py)."""

from app.core.evidence import (
    ANSWER_CAP,
    EVIDENCE_NEEDS_VALIDATION,
    EVIDENCE_SUFFICIENT,
    EVIDENCE_VERIFIED,
    PROBE_CAP,
    day_closed,
    evaluate,
    new_record,
    plan_complete,
    record_for,
)
from app.domain.interview import InterviewState


def _record(**overrides):
    record = new_record()
    record.update(overrides)
    return record


def test_strong_single_answer_verifies_day():
    record = new_record()
    assert evaluate(record, 4.6, [], False, False) == EVIDENCE_VERIFIED
    assert record["state"] == EVIDENCE_VERIFIED
    assert "4.6" in record["close_reason"]
    assert record["answers"] == 1


def test_clean_answer_at_sufficient_score_closes_day():
    record = new_record()
    assert evaluate(record, 3.6, [], False, False) == EVIDENCE_SUFFICIENT
    assert record["close_reason"] and "3.6" in record["close_reason"]


def test_weak_answer_keeps_day_open_for_more_evidence():
    record = new_record()
    assert evaluate(record, 2.5, [], False, False) is None
    assert record["state"] == "open"
    assert record["answers"] == 1


def test_missing_concepts_block_verification_but_not_sufficient():
    strong = new_record()
    assert evaluate(strong, 4.6, ["chunk"], False, False) == EVIDENCE_SUFFICIENT
    clean = new_record()
    assert evaluate(clean, 4.6, [], False, False) == EVIDENCE_VERIFIED


def test_flagged_answer_stays_open_for_more_evidence():
    overclaim = new_record()
    assert evaluate(overclaim, 4.6, [], True, False) is None
    overclaim["probes"] += 1
    assert evaluate(overclaim, 3.6, [], False, False) == EVIDENCE_SUFFICIENT
    vague = new_record()
    assert evaluate(vague, 4.2, [], False, True) is None


def test_hint_means_needs_validation_even_for_strong_answers():
    record = new_record()
    record["hints"] = 1
    assert evaluate(record, 4.8, [], False, False) == EVIDENCE_NEEDS_VALIDATION
    assert "hint" in record["close_reason"]


def test_repeated_weak_answers_exhaust_probing_budget():
    record = new_record()
    assert evaluate(record, 2.0, ["a"], False, False) is None
    record["probes"] += 1
    assert evaluate(record, 2.4, ["b"], False, False) is None
    record["probes"] += 1
    assert evaluate(record, 2.9, ["c"], False, False) == EVIDENCE_NEEDS_VALIDATION
    assert record["state"] == EVIDENCE_NEEDS_VALIDATION
    assert record["probes"] == PROBE_CAP


def test_answer_cap_guards_against_unbounded_answers():
    record = new_record()
    for _ in range(ANSWER_CAP - 1):
        assert evaluate(record, 2.0, ["x"], False, False) is None
    assert evaluate(record, 2.0, ["x"], False, False) == EVIDENCE_NEEDS_VALIDATION


def test_probe_then_strong_answer_closes_sufficient():
    record = new_record()
    record["probes"] = 1
    assert evaluate(record, 2.0, ["missing"], False, False) is None
    record["probes"] += 1
    assert evaluate(record, 3.8, [], False, False) == EVIDENCE_SUFFICIENT


def test_probe_then_consistent_strong_coverage_verifies():
    record = new_record()
    record["probes"] = 1
    assert evaluate(record, 4.4, [], True, False) is None  # flagged -> open
    record["probes"] += 1
    assert evaluate(record, 4.0, [], False, False) == EVIDENCE_VERIFIED
    assert "average" in record["close_reason"]


def test_record_for_persists_in_state_meta():
    state = InterviewState(session_id="s")
    first = record_for(state, 7)
    first["probes"] += 1
    assert record_for(state, 7) is first
    assert record_for(state, 12) is not first
    assert "day_evidence_status" in state.meta


def test_day_closed_reflects_terminal_state():
    state = InterviewState(session_id="s")
    assert day_closed(state, 7) is False
    record_for(state, 7)["state"] = EVIDENCE_VERIFIED
    assert day_closed(state, 7) is True


def test_plan_complete_requires_every_day_terminal():
    state = InterviewState(session_id="s")
    state.plan = [{"day": 7, "difficulty": "L1", "type": "concept"}, {"day": 12, "difficulty": "L2", "type": "scenario"}]
    assert plan_complete(state) is False
    record_for(state, 7)["state"] = EVIDENCE_SUFFICIENT
    record_for(state, 12)["state"] = EVIDENCE_NEEDS_VALIDATION
    assert plan_complete(state) is True


def test_empty_plan_is_trivially_complete():
    state = InterviewState(session_id="s")
    state.plan = []
    assert plan_complete(state) is True
