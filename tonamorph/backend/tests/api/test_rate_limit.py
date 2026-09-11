"""§5 rate limits: 10 job submissions and 60 reads per minute, per principal."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.auth import Principal
from app.config import Settings
from app.errors import ApiException
from app.middleware.rate_limit import (
    _PRUNE_EVERY,
    ConcurrencyLimiter,
    RateLimits,
    TokenBucketLimiter,
    enforce,
)
from app.services.memory import MemoryStore


def test_eleventh_submission_in_a_minute_is_429(
    client: TestClient,
    submit: Callable[..., Any],
    store: MemoryStore,
    registered_user: UUID,
) -> None:
    store.grant_credits(registered_user, 20, "test", "top-up")
    for _ in range(10):
        assert submit(options={"idempotency_key": str(uuid4())}).status_code == 202
    limited = submit(options={"idempotency_key": str(uuid4())})
    assert limited.status_code == 429
    body = limited.json()["error"]
    assert body["code"] == "rate_limited"
    assert int(limited.headers["Retry-After"]) >= 1
    assert limited.headers["X-RateLimit-Remaining"] == "0"
    assert body["details"]["retry_after_seconds"] >= 1


def test_reads_report_the_remaining_budget(
    client: TestClient, auth: dict[str, str], registered_user: UUID
) -> None:
    first = client.get("/v1/me", headers=auth)
    second = client.get("/v1/me", headers=auth)
    assert int(first.headers["X-RateLimit-Remaining"]) == 58
    assert int(second.headers["X-RateLimit-Remaining"]) == 57


def test_budgets_are_per_principal(
    client: TestClient, auth: dict[str, str], mint_jwt: Callable[..., str], registered_user: UUID
) -> None:
    for _ in range(5):
        client.get("/v1/me", headers=auth)
    other = client.get("/v1/me", headers={"Authorization": f"Bearer {mint_jwt()}"})
    assert int(other.headers["X-RateLimit-Remaining"]) == 59


def test_token_bucket_refills_over_time() -> None:
    now = [0.0]
    limiter = TokenBucketLimiter(60, clock=lambda: now[0])
    for _ in range(60):
        assert limiter.acquire("user").allowed
    denied = limiter.acquire("user")
    assert not denied.allowed and denied.retry_after == 1
    now[0] += 1.0
    assert limiter.acquire("user").allowed


def test_enforce_raises_the_contract_error(settings: Settings) -> None:
    limits = RateLimits(settings.model_copy(update={"rate_limit_jobs_per_min": 1}))
    principal = Principal(user_id=uuid4(), email=None, via="jwt")
    assert enforce(limits.jobs, principal) == 0
    try:
        enforce(limits.jobs, principal)
    except ApiException as exc:
        assert exc.status == 429 and exc.headers is not None
        assert exc.headers["X-RateLimit-Remaining"] == "0"
    else:  # pragma: no cover - the second call must be rejected
        raise AssertionError("expected a rate_limited error")


def test_the_bucket_store_is_bounded_by_max_buckets() -> None:
    """M6: the pre-authentication budgets are keyed on values the caller chooses, so an
    attacker must not be able to grow the limiter itself."""
    now = [0.0]
    limiter = TokenBucketLimiter(1, max_buckets=64, clock=lambda: now[0])
    for index in range(5_000):
        limiter.acquire(f"email:{index}")
        assert len(limiter._buckets) <= 64
    assert len(limiter._buckets) <= 64


def test_pruning_keeps_the_buckets_that_are_still_spending() -> None:
    now = [0.0]
    limiter = TokenBucketLimiter(2, max_buckets=4, clock=lambda: now[0])
    assert limiter.acquire("victim").allowed
    assert limiter.acquire("victim").allowed
    assert not limiter.acquire("victim").allowed
    for index in range(100):
        limiter.acquire(f"spray:{index}")
    assert not limiter.acquire("victim").allowed, "an exhausted bucket must survive a flood"


def test_a_refilled_bucket_is_forgotten() -> None:
    now = [0.0]
    limiter = TokenBucketLimiter(60, clock=lambda: now[0])
    for index in range(_PRUNE_EVERY):
        limiter.acquire(f"user:{index}")
    assert len(limiter._buckets) == _PRUNE_EVERY
    now[0] += 60.0  # every one of them is back at capacity
    for _ in range(_PRUNE_EVERY):
        limiter.acquire("busy")
    assert list(limiter._buckets) == ["busy"]


def test_concurrency_limiter_hands_slots_back() -> None:
    limiter = ConcurrencyLimiter(max_per_key=2)
    first = limiter.acquire("user")
    second = limiter.acquire("user")
    assert first is not None and second is not None
    assert limiter.acquire("user") is None
    assert limiter.acquire("other") is not None, "the cap is per key"

    first.release()
    first.release()  # idempotent: the stream's finally and its background task both call it
    assert limiter.held("user") == 1
    second.release()
    assert limiter.held("user") == 0
    assert limiter._held == {"other": 1}, "keys are dropped once nothing is held"
