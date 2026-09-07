"""Token buckets and stream slots (§5; docs/SECURITY.md §6).

Budgets are keyed by the authenticated identity — the JWT ``sub`` or the API key's owner
— which is only known after authentication, so enforcement is a route dependency that
runs right after :func:`app.dependencies.get_principal`. A rejected request answers
``429 rate_limited`` with ``Retry-After`` and ``X-RateLimit-Remaining``; accepted
requests carry the remaining budget in ``X-RateLimit-Remaining``.

Two budgets are not keyed by a principal, because there is none yet or because the
request costs more than one token:

* ``auth`` bounds ``/v1/auth/token`` and ``/v1/auth/refresh`` per submitted credential
  (see :func:`auth_bucket_key`). Its keys come from the request, so the store is capped
  and evicts least-recently-used buckets rather than growing without limit.
* ``streams`` caps how many SSE / WebSocket event streams one principal may hold open
  at once; a stream costs a read token to open but then lives for minutes.
"""

from __future__ import annotations

import hashlib
import math
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

from fastapi import Depends, Request, Response

from app.auth import Principal
from app.config import Settings
from app.dependencies import get_optional_principal, get_principal
from app.errors import rate_limited

LimitKind = Literal["jobs", "reads"]
AuthCredential = Literal["email", "refresh_token"]
REMAINING_HEADER = "X-RateLimit-Remaining"
_PRUNE_EVERY = 1024
MAX_BUCKETS = 100_000
"""Bucket ceiling per limiter; the least recently used bucket is dropped beyond it."""
AUTH_ATTEMPTS_PER_MIN = 10
"""Pre-authentication attempts per credential per minute (docs/SECURITY.md §6)."""
AUTH_MAX_BUCKETS = 10_000
"""Attacker-chosen keys, so this store stays small: ~1 MB at 10k buckets."""
MAX_CONCURRENT_STREAMS = 5
"""Event streams one principal may hold open at once (§2 SSE and WebSocket)."""
STREAM_RETRY_AFTER_SECONDS = 5


@dataclass(frozen=True, slots=True)
class Decision:
    allowed: bool
    remaining: int
    retry_after: int


class TokenBucketLimiter:
    """``per_minute`` tokens of capacity refilled continuously at ``per_minute / 60`` per
    second; one token per request.

    ``max_buckets`` bounds the store: refilled buckets are dropped first (they are
    indistinguishable from a new one), and if the ceiling still holds, the least
    recently used bucket goes. Memory therefore cannot be grown without limit by a
    caller who controls the key, which is the case for the pre-authentication budgets.
    """

    def __init__(
        self,
        per_minute: int,
        *,
        max_buckets: int = MAX_BUCKETS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if per_minute <= 0:
            raise ValueError("per_minute must be positive")
        if max_buckets <= 0:
            raise ValueError("max_buckets must be positive")
        self.capacity = float(per_minute)
        self.rate = per_minute / 60.0
        self.max_buckets = max_buckets
        self._clock = clock
        self._buckets: OrderedDict[str, tuple[float, float]] = OrderedDict()
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
        self._buckets.move_to_end(key)
        self._calls += 1
        if self._calls % _PRUNE_EVERY == 0 or len(self._buckets) > self.max_buckets:
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
        while len(self._buckets) > self.max_buckets:
            self._buckets.popitem(last=False)


class StreamSlot:
    """One held stream. ``release`` is idempotent, so the stream's ``finally`` and the
    response's background task may both call it."""

    __slots__ = ("_key", "_limiter", "_released")

    def __init__(self, limiter: ConcurrencyLimiter, key: str) -> None:
        self._limiter = limiter
        self._key = key
        self._released = False

    def release(self) -> None:
        if not self._released:
            self._released = True
            self._limiter.release(self._key)


class ConcurrencyLimiter:
    """Counts what one key holds open right now; keys vanish at zero, so the store is
    bounded by the number of live connections."""

    def __init__(self, max_per_key: int) -> None:
        if max_per_key <= 0:
            raise ValueError("max_per_key must be positive")
        self.max_per_key = max_per_key
        self._held: dict[str, int] = {}

    def held(self, key: str) -> int:
        return self._held.get(key, 0)

    def acquire(self, key: str) -> StreamSlot | None:
        """A slot to release when the stream ends, or ``None`` when the key is at its
        ceiling."""
        current = self._held.get(key, 0)
        if current >= self.max_per_key:
            return None
        self._held[key] = current + 1
        return StreamSlot(self, key)

    def release(self, key: str) -> None:
        remaining = self._held.get(key, 0) - 1
        if remaining > 0:
            self._held[key] = remaining
        else:
            self._held.pop(key, None)


class RateLimits:
    def __init__(self, settings: Settings, *, clock: Callable[[], float] = time.monotonic) -> None:
        self.jobs = TokenBucketLimiter(settings.rate_limit_jobs_per_min, clock=clock)
        self.reads = TokenBucketLimiter(settings.rate_limit_reads_per_min, clock=clock)
        self.auth = TokenBucketLimiter(
            AUTH_ATTEMPTS_PER_MIN, max_buckets=AUTH_MAX_BUCKETS, clock=clock
        )
        self.streams = ConcurrencyLimiter(MAX_CONCURRENT_STREAMS)

    def limiter(self, kind: LimitKind) -> TokenBucketLimiter:
        return self.jobs if kind == "jobs" else self.reads


def auth_bucket_key(kind: AuthCredential, value: str) -> str:
    """Bucket key for a credential submitted before there is any principal.

    The value is normalised and hashed: a key is then a fixed 32 characters whatever the
    client sent, and a refresh token never sits in memory as a dictionary key.
    """
    normalised = value.strip().lower() if kind == "email" else value.strip()
    digest = hashlib.sha256(normalised.encode("utf-8", "replace")).hexdigest()[:32]
    return f"{kind}:{digest}"


def enforce_key(limiter: TokenBucketLimiter, key: str) -> int:
    """Consume one token for ``key`` and return the remaining budget, or raise 429."""
    decision = limiter.acquire(key)
    if not decision.allowed:
        raise rate_limited(decision.retry_after, 0)
    return decision.remaining


def enforce(limiter: TokenBucketLimiter, principal: Principal) -> int:
    """Consume one token for ``principal`` and return the remaining budget, or raise 429."""
    return enforce_key(limiter, str(principal.user_id))


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
    "AUTH_ATTEMPTS_PER_MIN",
    "MAX_CONCURRENT_STREAMS",
    "REMAINING_HEADER",
    "STREAM_RETRY_AFTER_SECONDS",
    "AuthCredential",
    "ConcurrencyLimiter",
    "Decision",
    "LimitKind",
    "RateLimits",
    "StreamSlot",
    "TokenBucketLimiter",
    "auth_bucket_key",
    "enforce",
    "enforce_key",
    "optional_read_limit",
    "rate_limit",
]
