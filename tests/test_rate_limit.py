"""Unit tests for :mod:`math_ai_agent.rate_limit`."""

# pylint: disable=protected-access

from math_ai_agent import rate_limit
from math_ai_agent.rate_limit import SlidingWindowRateLimiter


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_allows_calls_up_to_the_limit_then_returns_retry_after():
    clock = _Clock()
    limiter = SlidingWindowRateLimiter(2, 60, clock)
    assert limiter.try_acquire("a") is None
    clock.now = 10
    assert limiter.try_acquire("a") is None
    clock.now = 20
    assert limiter.try_acquire("a") == 40


def test_allows_again_after_the_window_passes():
    clock = _Clock()
    limiter = SlidingWindowRateLimiter(1, 60, clock)
    limiter.try_acquire("a")
    clock.now = 60
    assert limiter.try_acquire("a") is None


def test_counts_each_client_separately():
    limiter = SlidingWindowRateLimiter(1, 60, _Clock())
    assert limiter.try_acquire("a") is None
    assert limiter.try_acquire("b") is None
    assert limiter.try_acquire("a") is not None


def test_forgets_idle_clients_when_tracking_too_many(monkeypatch):
    monkeypatch.setattr(rate_limit, "_MAX_TRACKED_CLIENTS", 2)
    clock = _Clock()
    limiter = SlidingWindowRateLimiter(1, 60, clock)
    limiter.try_acquire("a")
    limiter.try_acquire("b")
    clock.now = 61
    limiter.try_acquire("c")
    assert set(limiter._calls) == {"c"}
