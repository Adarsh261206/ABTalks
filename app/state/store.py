from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import aiosqlite


@dataclass
class StoredSession:
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


class SessionStore:
    """SQLite-backed session store. Survives restarts; TTL-expires stale active sessions."""

    def __init__(self, db_path: Path, ttl_hours: float) -> None:
        self._db_path = db_path
        self._ttl_seconds = ttl_hours * 3600
        self._conn: aiosqlite.Connection | None = None

    async def init(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA busy_timeout=5000")
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                candidate_json TEXT NOT NULL,
                state_json TEXT NOT NULL,
                transcript_json TEXT NOT NULL,
                status TEXT NOT NULL,
                report_json TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                turn_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status, updated_at)"
        )
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def create(self, session: StoredSession) -> None:
        assert self._conn is not None
        await self._conn.execute(
            """
            INSERT INTO sessions
                (id, candidate_json, state_json, transcript_json, status,
                 report_json, created_at, updated_at, turn_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.session_id,
                session.candidate_json,
                session.state_json,
                session.transcript_json,
                session.status,
                session.report_json,
                session.created_at,
                session.updated_at,
                session.turn_count,
            ),
        )
        await self._conn.commit()

    async def get(self, session_id: str) -> StoredSession | None:
        """Load a session. Stale active sessions are expired (deleted) and returned
        with `expired=True` so the caller can answer 404 with an `expired` hint."""
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        row = await cur.fetchone()
        if row is None:
            return None
        now = time.time()
        if row["status"] == "active" and now - row["updated_at"] > self._ttl_seconds:
            await self._conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await self._conn.commit()
            return StoredSession(
                session_id=row["id"],
                candidate_json=row["candidate_json"],
                state_json=row["state_json"],
                transcript_json=row["transcript_json"],
                status=row["status"],
                report_json=row["report_json"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                turn_count=row["turn_count"],
                expired=True,
            )
        return StoredSession(
            session_id=row["id"],
            candidate_json=row["candidate_json"],
            state_json=row["state_json"],
            transcript_json=row["transcript_json"],
            status=row["status"],
            report_json=row["report_json"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            turn_count=row["turn_count"],
        )

    async def save(self, session: StoredSession) -> None:
        assert self._conn is not None
        await self._conn.execute(
            """
            UPDATE sessions SET
                candidate_json = ?, state_json = ?, transcript_json = ?,
                status = ?, report_json = ?, updated_at = ?, turn_count = ?
            WHERE id = ?
            """,
            (
                session.candidate_json,
                session.state_json,
                session.transcript_json,
                session.status,
                session.report_json,
                session.updated_at,
                session.turn_count,
                session.session_id,
            ),
        )
        await self._conn.commit()

    async def cleanup_expired(self) -> int:
        """Delete stale active sessions; returns the number removed."""
        assert self._conn is not None
        now = time.time()
        cutoff = now - self._ttl_seconds
        cur = await self._conn.execute(
            "DELETE FROM sessions WHERE status = 'active' AND updated_at < ?", (cutoff,)
        )
        await self._conn.commit()
        return cur.rowcount or 0
