from __future__ import annotations

import time

from app.state.repository import StoredSession


class InMemorySessionStore:
    """In-memory SessionRepository for tests and mock/demo mode.
    Mirrors SqliteSessionStore semantics exactly (TTL expiry included)."""

    def __init__(self, ttl_hours: float = 2.0) -> None:
        self._ttl_seconds = ttl_hours * 3600
        self._sessions: dict[str, StoredSession] = {}

    async def init(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def create(self, session: StoredSession) -> None:
        self._sessions[session.session_id] = session

    async def get(self, session_id: str) -> StoredSession | None:
        row = self._sessions.get(session_id)
        if row is None:
            return None
        now = time.time()
        if row.status == "active" and now - row.updated_at > self._ttl_seconds:
            del self._sessions[session_id]
            return StoredSession(**{**row.__dict__, "expired": True})
        return row

    async def save(self, session: StoredSession) -> None:
        self._sessions[session.session_id] = session

    async def cleanup_expired(self) -> int:
        now = time.time()
        stale = [
            sid
            for sid, row in self._sessions.items()
            if row.status == "active" and now - row.updated_at > self._ttl_seconds
        ]
        for sid in stale:
            del self._sessions[sid]
        return len(stale)
