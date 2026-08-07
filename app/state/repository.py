from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class StoredSession:
    """Persistence row for one interview session (JSON payloads)."""

    session_id: str
    candidate_json: str
    state_json: str
    transcript_json: str
    status: str
    report_json: str | None
    created_at: float
    updated_at: float
    turn_count: int
    expired: bool = False


class SessionRepository(Protocol):
    """Persistence contract for interview sessions.

    Implementations: SqliteSessionStore (production) and
    InMemorySessionStore (tests / mock mode).
    """

    async def get(self, session_id: str) -> StoredSession | None:
        """Load a session. Stale active sessions are expired (deleted) and
        returned with `expired=True` so callers can answer 404 with a hint."""
        ...

    async def create(self, session: StoredSession) -> None:
        ...

    async def save(self, session: StoredSession) -> None:
        ...

    async def cleanup_expired(self) -> int:
        """Delete stale active sessions; returns the number removed."""
        ...

    async def close(self) -> None:
        ...
