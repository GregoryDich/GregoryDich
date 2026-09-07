"""§5 rate limits: 10 job submissions and 60 reads per minute, per principal."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.auth import Principal
from app.config import Settings
from app.errors import ApiException
from app.middleware.rate_limit import RateLimits, TokenBucketLimiter, enforce
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
