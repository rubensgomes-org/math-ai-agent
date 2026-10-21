"""In-memory per-client rate limiting."""

import math
import time
from collections import deque
from collections.abc import Callable

# Bounds memory when many distinct clients call once.
_MAX_TRACKED_CLIENTS = 10_000


class SlidingWindowRateLimiter:
    """Allow at most ``limit`` calls per client within ``window_seconds``.

    State is per process, so each replica keeps its own counts.
    """

    def __init__(
        self,
        limit: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._clock = clock
        self._calls: dict[str, deque[float]] = {}

    def try_acquire(self, client: str) -> int | None:
        """Record a call and return None, or the seconds until a retry."""
        now = self._clock()
        if len(self._calls) >= _MAX_TRACKED_CLIENTS:
            self._forget_idle_clients(now)
        calls = self._calls.setdefault(client, deque())
        while calls and now - calls[0] >= self._window_seconds:
            calls.popleft()
        if len(calls) >= self._limit:
            return math.ceil(self._window_seconds - (now - calls[0]))
        calls.append(now)
        return None

    def _forget_idle_clients(self, now: float) -> None:
        self._calls = {
            client: calls
            for client, calls in self._calls.items()
            if calls and now - calls[-1] < self._window_seconds
        }
