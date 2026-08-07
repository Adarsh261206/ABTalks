from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator


class SessionLockRegistry:
    """Per-session async locks. A concurrent duplicate turn on the same
    session yields `acquired=False` (route answers 409)."""

    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}

    @asynccontextmanager
    async def acquire(self, session_id: str) -> AsyncIterator[bool]:
        lock = self._locks.setdefault(session_id, asyncio.Lock())
        if lock.locked():
            yield False
            return
        async with lock:
            yield True
