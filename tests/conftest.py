from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.engine import InterviewEngine
from app.main import create_app
from app.state.store import SqliteSessionStore

CANDIDATE = {
    "member": {
        "id": "CAND-010",
        "name": "Gerald Combs",
        "jobRole": "IT Support Specialist",
        "yearsExperience": 20,
        "education": "AAS Information Technology",
        "status": "COMPLETED",
    },
    "missions": [
        {"day": 7, "title": "Embeddings Explained", "passed": True, "attempts": 5},
        {"day": 8, "title": "Vector Databases Overview", "passed": False, "attempts": 4},
        {"day": 12, "title": "Prompt Engineering Fundamentals", "passed": True, "attempts": 5},
        {"day": 22, "title": "Multi-Agent Orchestration", "passed": False, "attempts": 3},
    ],
    "signals": {"commitDays": 22, "missionsCompleted": 23, "missionsFirstTry": 1},
}


@pytest.fixture()
def app_factory(tmp_path: Path):
    def _factory(
        ttl_hours: float = 2.0,
        rate_limiter=None,
    ) -> tuple[TestClient, SqliteSessionStore]:
        store = SqliteSessionStore(db_path=tmp_path / "test.db", ttl_hours=ttl_hours)
        app = create_app(store=store, engine=InterviewEngine(), rate_limiter=rate_limiter)
        client = TestClient(app)
        client.__enter__()
        return client, store

    yield _factory


@pytest.fixture()
def client(app_factory) -> TestClient:
    client, _ = app_factory()
    return client


@pytest.fixture()
def candidate() -> dict:
    return CANDIDATE


@pytest.fixture()
def start_interview():
    def _start(client: TestClient, session_id: str = "sess-1"):
        return client.post(
            "/api/interview",
            json={"sessionId": session_id, "candidate": CANDIDATE},
        )

    return _start


@pytest.fixture()
def turn():
    def _turn(client: TestClient, message: str, session_id: str = "sess-1"):
        return client.post("/api/interview", json={"sessionId": session_id, "message": message})

    return _turn
