from __future__ import annotations

import time
from collections import deque
from typing import Callable


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__("Rate limit exceeded.")
        self.retry_after = retry_after


class RateLimiter:
    """Sliding-window rate limiter per key (IP). Clock-injectable for tests."""

    def __init__(
        self,
        limit: int,
        window_seconds: int = 60,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}

    def check(self, key: str) -> None:
        now = self._clock()
        window = self._hits.setdefault(key, deque())
        while window and now - window[0] > self._window:
            window.popleft()
        if len(window) >= self._limit:
            retry_after = max(1, int(self._window - (now - window[0])) + 1)
            raise RateLimitExceeded(retry_after=retry_after)
        window.append(now)

    def reset(self) -> None:
        self._hits.clear()
