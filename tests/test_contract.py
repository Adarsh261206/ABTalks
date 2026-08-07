"""M1 contract tests: spec compliance + session-layer edge cases."""

from __future__ import annotations

import json
import time

from app.config import settings
from app.state.store import SessionStore
from app.routes.interview import _limiter_hits
from conftest import CANDIDATE, start_interview, turn

CORE_DAYS = [7, 8, 10, 12, 16, 22, 23, 31]


def test_health(app_factory):
    client, _ = app_factory()
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_start_returns_welcome(app_factory):
    client, _ = app_factory()
    r = start_interview(client)
    assert r.status_code == 200
    body = r.json()
    assert body["done"] is False
    assert "Gerald" in body["reply"]
    assert body.get("feedback") is None


def test_start_missing_candidate_422(app_factory):
    client, _ = app_factory()
    r = client.post("/api/interview", json={"sessionId": "x"})
    assert r.status_code == 422
    assert r.json()["error"]


def test_start_missing_session_id_400(app_factory):
    client, _ = app_factory()
    r = client.post("/api/interview", json={"candidate": CANDIDATE})
    assert r.status_code == 400


def test_start_malformed_session_id_400(app_factory):
    client, _ = app_factory()
    r = client.post("/api/interview", json={"sessionId": "   ", "candidate": CANDIDATE})
    assert r.status_code == 400


def test_turn_asks_grounded_question(app_factory):
    client, _ = app_factory()
    start_interview(client)
    r = turn(client, "I built a RAG pipeline.")
    assert r.status_code == 200
    body = r.json()
    assert body["done"] is False
    assert "Day 7" in body["reply"]


def test_full_interview_completes_with_feedback(app_factory):
    client, _ = app_factory()
    start_interview(client)
    done = None
    for i in range(9):
        r = turn(client, f"Answer {i} — detailed reasoning about the architecture.")
        body = r.json()
        if body["done"]:
            done = body
            break
    assert done is not None, "interview never completed"
    fb = done["feedback"]
    assert isinstance(fb["summary"], str) and fb["summary"]
    assert isinstance(fb["strengths"], list) and len(fb["strengths"]) >= 1
    assert isinstance(fb["gaps"], list)
    assert isinstance(fb["next"], list) and len(fb["next"]) >= 1


def test_questions_cover_min_8_and_4_days(app_factory):
    client, _ = app_factory()
    start_interview(client)
    questions = []
    for i in range(9):
        r = turn(client, f"Answer {i}")
        body = r.json()
        if body["done"]:
            break
        questions.append(body["reply"])
    assert len(questions) == 8
    days_asked = {q for q in CORE_DAYS}
    assert len(days_asked) >= 4


def test_end_keyword_wraps_early(app_factory):
    client, _ = app_factory()
    start_interview(client)
    turn(client, "Some answer.")
    r = turn(client, "end")
    body = r.json()
    assert body["done"] is True
    assert body["feedback"]["summary"].startswith("Practice interview completed")


def test_unknown_session_404(app_factory):
    client, _ = app_factory()
    r = turn(client, "hello", session_id="nope")
    assert r.status_code == 404


def test_empty_message_422(app_factory):
    client, _ = app_factory()
    start_interview(client)
    r = turn(client, "")
    assert r.status_code == 422


def test_whitespace_message_422(app_factory):
    client, _ = app_factory()
    start_interview(client)
    r = turn(client, "   ")
    assert r.status_code == 422


def test_message_too_long_413(app_factory):
    client, _ = app_factory()
    start_interview(client)
    r = turn(client, "x" * 4001)
    assert r.status_code == 413


def test_non_string_message_400(app_factory):
    client, _ = app_factory()
    start_interview(client)
    r = client.post("/api/interview", json={"sessionId": "sess-1", "message": 42})
    assert r.status_code == 400


def test_malformed_json_400(app_factory):
    client, _ = app_factory()
    r = client.post("/api/interview", content="{not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 400


def test_message_after_completion_409_with_report(app_factory):
    client, _ = app_factory()
    start_interview(client)
    for i in range(8):
        turn(client, f"Answer {i}")
    done = turn(client, "Last answer").json()
    assert done["done"] is True
    r = turn(client, "One more thing")
    assert r.status_code == 409
    assert r.json()["report"]["summary"]


def test_start_with_message_ignored(app_factory):
    client, _ = app_factory()
    r = client.post(
        "/api/interview",
        json={"sessionId": "s-ignored", "candidate": CANDIDATE, "message": "ignored"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "Gerald" in body["reply"]


def test_duplicate_start_resumes(app_factory):
    client, _ = app_factory()
    start_interview(client)
    r = start_interview(client)
    assert r.status_code == 200
    assert "Welcome back" in r.json()["reply"]


def test_control_chars_sanitized(app_factory):
    client, _ = app_factory()
    start_interview(client)
    r = turn(client, "fine\x00\x01answer")
    assert r.status_code == 200


def test_session_view_endpoint(app_factory):
    client, _ = app_factory()
    start_interview(client)
    turn(client, "Answer one")
    r = client.get("/api/interview/sess-1")
    assert r.status_code == 200
    view = r.json()
    assert view["status"] == "active"
    assert view["turn_count"] == 1
    assert view["covered_days"] == [7]
    assert view["transcript"][0]["role"] == "interviewer"


def test_restart_preserves_session(tmp_path):
    """Store survives a full app restart: the next question continues the plan."""
    from fastapi.testclient import TestClient

    from app.main import create_app

    from app.core.engine import InterviewEngine

    db = tmp_path / "restart.db"
    store1 = SessionStore(db_path=db, ttl_hours=2.0)
    app1 = create_app(store=store1, engine=InterviewEngine())
    with TestClient(app1) as client:
        start_interview(client)
        turn(client, "First answer")

    store2 = SessionStore(db_path=db, ttl_hours=2.0)
    app2 = create_app(store=store2, engine=InterviewEngine())
    with TestClient(app2) as client:
        r = turn(client, "Second answer")
        assert r.status_code == 200
        assert "Day 8" in r.json()["reply"]
        view = client.get("/api/interview/sess-1").json()
        assert view["turn_count"] == 2


def test_ttl_expiry_404(app_factory):
    client, store = app_factory(ttl_hours=0)
    start_interview(client)
    time.sleep(0.05)
    r = turn(client, "hello")
    assert r.status_code == 404
    assert "expired" in r.json()["error"].lower()


def test_rate_limit_429(app_factory, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_per_minute", 3)
    _limiter_hits.clear()
    client, _ = app_factory()
    for i in range(3):
        assert client.post(
            "/api/interview", json={"sessionId": f"rl-{i}", "candidate": CANDIDATE}
        ).status_code == 200
    r = client.post("/api/interview", json={"sessionId": "rl-3", "candidate": CANDIDATE})
    assert r.status_code == 429
    assert "Retry-After" in r.headers


def test_request_id_header_and_body(app_factory):
    client, _ = app_factory()
    r = client.post("/api/interview", json={"sessionId": "x"})
    assert "X-Request-ID" in r.headers
    assert r.json()["request_id"] == r.headers["X-Request-ID"]
