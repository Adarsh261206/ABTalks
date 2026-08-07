"""Unit tests for the refactored layers: repositories, serialization,
services, providers and the LLM gateway."""

from __future__ import annotations

import asyncio
import json
import time

import pytest
from pydantic import BaseModel, Field

from app.core.curriculum import load_curriculum
from app.core.llm import LLMGateway, LLMGatewayError
from app.core.prompts import humanize_objective, question_template
from app.domain.candidate import CandidateProfile
from app.domain.interview import EngineTurn, Feedback, InterviewState, Question, TranscriptEntry
from app.infrastructure.llm import LLMError
from app.infrastructure.llm_mock import MockLLMProvider
from app.services.locks import SessionLockRegistry
from app.services.ratelimit import RateLimiter, RateLimitExceeded
from app.state.memory_store import InMemorySessionStore
from app.state.repository import StoredSession
from app.state.serialization import from_stored, to_stored
from app.state.store import SqliteSessionStore

CANDIDATE = CandidateProfile(
    member={"id": "C1", "name": "Gerald Combs", "jobRole": "IT Support Specialist"}
)


# ---------------------------------------------------------------- repositories

@pytest.mark.asyncio
async def test_sqlite_store_roundtrip(tmp_path):
    store = SqliteSessionStore(db_path=tmp_path / "t.db", ttl_hours=2.0)
    await store.init()
    row = StoredSession(
        session_id="s1", candidate_json="{}", state_json="{}",
        transcript_json="[]", status="active", report_json=None,
        created_at=time.time(), updated_at=time.time(), turn_count=0,
    )
    await store.create(row)
    loaded = await store.get("s1")
    assert loaded is not None and loaded.session_id == "s1"
    row.turn_count = 3
    await store.save(row)
    assert (await store.get("s1")).turn_count == 3
    await store.close()


@pytest.mark.asyncio
async def test_sqlite_store_ttl_expiry(tmp_path):
    store = SqliteSessionStore(db_path=tmp_path / "t.db", ttl_hours=0)
    await store.init()
    row = StoredSession(
        session_id="s1", candidate_json="{}", state_json="{}",
        transcript_json="[]", status="active", report_json=None,
        created_at=time.time(), updated_at=time.time(), turn_count=0,
    )
    await store.create(row)
    time.sleep(0.05)
    loaded = await store.get("s1")
    assert loaded is not None and loaded.expired is True
    assert await store.get("s1") is None
    await store.close()


@pytest.mark.asyncio
async def test_memory_store_mirrors_sqlite_semantics():
    store = InMemorySessionStore(ttl_hours=0)
    row = StoredSession(
        session_id="s1", candidate_json="{}", state_json="{}",
        transcript_json="[]", status="active", report_json=None,
        created_at=time.time(), updated_at=time.time(), turn_count=0,
    )
    await store.create(row)
    time.sleep(0.05)
    assert (await store.get("s1")).expired is True
    assert await store.get("s1") is None


# ------------------------------------------------------------- serialization

def test_serialization_roundtrip_preserves_state():
    state = InterviewState(session_id="s1")
    state.candidate = CANDIDATE
    state.transcript = [
        TranscriptEntry(role="interviewer", text="Welcome, Gerald Combs.", day=None),
        TranscriptEntry(role="candidate", text="I built a RAG pipeline.", day=None),
    ]
    state.asked = [Question(day=7, text="Walk me through embeddings.", difficulty="L1", type="concept")]
    state.covered_days = [7]
    state.report = Feedback(summary="Done.", strengths=["x"], gaps=["y"], next=["z"])
    state.status = "completed"

    stored = to_stored("s1", state, created_at=100.0)
    restored = from_stored(stored)

    assert restored.session_id == "s1"
    assert restored.status == "completed"
    assert len(restored.transcript) == 2
    assert restored.transcript[1].text == "I built a RAG pipeline."
    assert restored.asked[0].day == 7
    assert restored.covered_days == [7]
    assert restored.report.summary == "Done."
    assert restored.candidate.member.name == "Gerald Combs"


# ------------------------------------------------------------------- services

def test_rate_limiter_sliding_window():
    now = [1000.0]
    limiter = RateLimiter(limit=3, window_seconds=60, clock=lambda: now[0])
    for _ in range(3):
        limiter.check("ip")
    with pytest.raises(RateLimitExceeded):
        limiter.check("ip")
    now[0] += 61
    limiter.check("ip")  # window slid


def test_lock_registry_serializes_duplicate_turn():
    async def run():
        registry = SessionLockRegistry()
        async with registry.acquire("s1") as acquired:
            assert acquired is True
            async with registry.acquire("s1") as again:
                assert again is False
        async with registry.acquire("s1") as after:
            assert after is True

    asyncio.run(run())


# --------------------------------------------------------------------- prompts

def test_humanize_objective_mapping():
    assert humanize_objective("Understand how text is converted into vector embeddings") == (
        "Walk me through how text is converted into vector embeddings"
    )
    assert humanize_objective("Build a query router that decides between sql, vector search") == (
        "Walk me through how you built a query router that decides between sql, vector search"
    )
    assert humanize_objective("Evaluate retrieval accuracy using a diverse set of questions") == (
        "How did you evaluate retrieval accuracy using a diverse set of questions"
    )
    assert question_template(7, "Embeddings Explained", "Walk me through how you embedded") == (
        "Let's talk about Day 7 — Embeddings Explained. Walk me through how you embedded?"
    )


# ---------------------------------------------------------------- curriculum

def test_curriculum_loads_real_file():
    days = load_curriculum()
    assert len(days) == 31
    assert days[7].title == "Embeddings Explained"
    assert days[31].type == "CAPSTONE"
    assert days[7].objectives


# --------------------------------------------------------- llm providers/gateway

class _Decision(BaseModel):
    action: str = Field(...)
    day: int = Field(...)


async def _no_sleep(_seconds: float) -> None:
    return None


class _FailingProvider:
    name = "flaky"

    def __init__(self, fail_times: int) -> None:
        self._failures = fail_times
        self._calls = 0

    async def chat(self, messages, temperature=0.2, max_tokens=None) -> str:
        self._calls += 1
        if self._calls <= self._failures:
            raise LLMError("provider down")
        return "ok"

    async def structured(self, messages, schema, temperature=0.0):
        self._calls += 1
        if self._calls <= self._failures:
            raise LLMError("provider down")
        return _Decision(action="ask_new", day=7)


@pytest.mark.asyncio
async def test_mock_provider_chat_and_structured():
    provider = MockLLMProvider(chat_replies=["Hello there."])
    assert await provider.chat([{"role": "user", "content": "hi"}]) == "Hello there."
    result = await provider.structured([], _Decision)
    assert result.action == "mock" and result.day == 0


@pytest.mark.asyncio
async def test_gateway_retries_transient_failure():
    provider = _FailingProvider(fail_times=2)
    gateway = LLMGateway(primary=provider, sleep=_no_sleep)
    assert await gateway.chat([{"role": "user", "content": "hi"}]) == "ok"
    assert provider._calls == 3


@pytest.mark.asyncio
async def test_gateway_uses_fallback_after_retries():
    provider = _FailingProvider(fail_times=99)
    fallback = MockLLMProvider(chat_replies=["fallback"])
    gateway = LLMGateway(primary=provider, fallback=fallback, sleep=_no_sleep)
    assert await gateway.chat([]) == "fallback"
    assert fallback.chat_calls == 1


@pytest.mark.asyncio
async def test_gateway_raises_when_everything_fails():
    provider = _FailingProvider(fail_times=99)
    gateway = LLMGateway(primary=provider, sleep=_no_sleep)
    with pytest.raises(LLMGatewayError):
        await gateway.chat([])


@pytest.mark.asyncio
async def test_gateway_structured_reprompts_on_invalid_json():
    calls = []

    class _FakeProvider:
        name = "fake"

        async def structured(self, messages, schema, temperature=0.0):
            calls.append(len(messages))
            if len(messages) == 1:
                raise LLMError("invalid JSON from provider")
            return _Decision(action="ask_new", day=7)

        async def chat(self, messages, temperature=0.2, max_tokens=None):
            return ""

    gateway = LLMGateway(primary=_FakeProvider(), sleep=_no_sleep)
    result = await gateway.structured([{"role": "user", "content": "go"}], _Decision)
    assert result.day == 7
    assert len(calls) == 2
    assert calls[1] == 2  # original + repair message
