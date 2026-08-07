from __future__ import annotations

import inspect
import re
import time
from typing import Protocol

from app.core.agent_engine import AgenticInterviewEngine
from app.core.engine import InterviewEngine
from app.core.prompts import RESUME_REPLY
from app.domain.candidate import CandidateProfile
from app.domain.interview import EngineTurn, InterviewState
from app.state.repository import SessionRepository
from app.state.serialization import from_stored, to_stored

_CTRL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


async def _maybe_await(value):
    """Engines may expose async (M2 agentic) or sync (M1) lifecycle methods."""
    return await value if inspect.isawaitable(value) else value


class SessionNotFoundError(Exception):
    """Turn on a sessionId that never started."""


class SessionExpiredError(Exception):
    """Session existed but TTL-expired."""


class SessionCompletedError(Exception):
    """Message sent after the interview already completed."""

    def __init__(self, report) -> None:
        super().__init__("Interview already completed.")
        self.report = report


class InterviewService:
    """Use-case layer: session lifecycle rules over repository + engine.

    The HTTP layer stays thin (parsing + status mapping); all interview
    semantics live here so M2's agent engine slots in without touching routes.
    """

    def __init__(
        self,
        store: SessionRepository,
        engine: InterviewEngine | AgenticInterviewEngine,
        clock=time.time,
    ) -> None:
        self._store = store
        self._engine = engine
        self._clock = clock

    async def start(self, session_id: str, candidate: CandidateProfile) -> EngineTurn:
        row = await self._store.get(session_id)
        if row is not None and row.expired:
            raise SessionExpiredError
        if row is not None:
            state = from_stored(row)
            if state.status == "completed":
                raise SessionCompletedError(state.report)
            return EngineTurn(reply=RESUME_REPLY)

        state = InterviewState(session_id=session_id)
        reply = await _maybe_await(self._engine.start(state, candidate))
        await self._store.create(to_stored(session_id, state, self._clock()))
        return EngineTurn(reply=reply)

    async def turn(self, session_id: str, message: str) -> EngineTurn:
        row = await self._store.get(session_id)
        if row is None:
            raise SessionNotFoundError
        if row.expired:
            raise SessionExpiredError

        state = from_stored(row)
        if state.status == "completed":
            raise SessionCompletedError(state.report)

        message = _CTRL_CHARS.sub(" ", message).strip()
        turn = await _maybe_await(self._engine.process(state, message))
        await self._store.save(to_stored(session_id, state, row.created_at))
        return turn
