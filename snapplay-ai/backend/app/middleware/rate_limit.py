"""Per-principal token buckets (§5; docs/SECURITY.md §6).

Budgets are keyed by the authenticated identity — the JWT ``sub`` or the API key's owner
— which is only known after authentication, so enforcement is a route dependency that
runs right after :func:`app.dependencies.get_principal`. A rejected request answers
``429 rate_limited`` with ``Retry-After`` and ``X-RateLimit-Remaining``; accepted
requests carry the remaining budget in ``X-RateLimit-Remaining``.
"""

from __future__ import annotations

import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

from fastapi import Depends, Request, Response

from app.auth import Principal
from app.config import Settings
from app.dependencies import get_optional_principal, get_principal
from app.errors import rate_limited

LimitKind = Literal["jobs", "reads"]
REMAINING_HEADER = "X-RateLimit-Remaining"
_PRUNE_EVERY = 1024


@dataclass(frozen=True, slots=True)
class Decision:
    allowed: bool
    remaining: int
    retry_after: int


class TokenBucketLimiter:
    """``per_minute`` tokens of capacity refilled continuously at ``per_minute / 60`` per
    second; one token per request."""

    def __init__(self, per_minute: int, *, clock: Callable[[], float] = time.monotonic) -> None:
        if per_minute <= 0:
            raise ValueError("per_minute must be positive")
        self.capacity = float(per_minute)
        self.rate = per_minute / 60.0
        self._clock = clock
        self._buckets: dict[str, tuple[float, float]] = {}
        self._calls = 0

    def acquire(self, key: str) -> Decision:
        now = self._clock()
        tokens, updated = self._buckets.get(key, (self.capacity, now))
        tokens = min(self.capacity, tokens + max(now - updated, 0.0) * self.rate)
        if tokens >= 1.0:
            tokens -= 1.0
            decision = Decision(True, int(tokens), 0)
        else:
            decision = Decision(False, 0, max(1, math.ceil((1.0 - tokens) / self.rate)))
        self._buckets[key] = (tokens, now)
        self._calls += 1
        if self._calls % _PRUNE_EVERY == 0:
            self._prune(now)
        return decision

    def _prune(self, now: float) -> None:
        full = [
            key
            for key, (tokens, updated) in self._buckets.items()
            if tokens + (now - updated) * self.rate >= self.capacity
        ]
        for key in full:
            del self._buckets[key]


class RateLimits:
    def __init__(self, settings: Settings, *, clock: Callable[[], float] = time.monotonic) -> None:
        self.jobs = TokenBucketLimiter(settings.rate_limit_jobs_per_min, clock=clock)
        self.reads = TokenBucketLimiter(settings.rate_limit_reads_per_min, clock=clock)

    def limiter(self, kind: LimitKind) -> TokenBucketLimiter:
        return self.jobs if kind == "jobs" else self.reads


def enforce(limiter: TokenBucketLimiter, principal: Principal) -> int:
    """Consume one token for ``principal`` and return the remaining budget, or raise 429."""
    decision = limiter.acquire(str(principal.user_id))
    if not decision.allowed:
        raise rate_limited(decision.retry_after, 0)
    return decision.remaining


def rate_limit(kind: LimitKind) -> Callable[..., Awaitable[None]]:
    """Dependency enforcing the ``kind`` budget for the authenticated caller."""

    async def dependency(
        request: Request, response: Response, principal: Principal = Depends(get_principal)
    ) -> None:
        limits: RateLimits = request.app.state.rate_limits
        response.headers[REMAINING_HEADER] = str(enforce(limits.limiter(kind), principal))

    return dependency


async def optional_read_limit(
    request: Request,
    response: Response,
    principal: Principal | None = Depends(get_optional_principal),
) -> None:
    """Read budget for routes that are public but attach the caller when authenticated."""
    if principal is not None:
        limits: RateLimits = request.app.state.rate_limits
        response.headers[REMAINING_HEADER] = str(enforce(limits.reads, principal))


__all__ = [
    "REMAINING_HEADER",
    "Decision",
    "LimitKind",
    "RateLimits",
    "TokenBucketLimiter",
    "enforce",
    "optional_read_limit",
    "rate_limit",
]
