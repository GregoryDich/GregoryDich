"""Fixtures for the HTTP API tests: an authenticated client over the in-memory backend."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import Callable, Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.factory import Services
from app.services.memory import MemoryStore

USER_EMAIL = "player@example.test"


@pytest.fixture
def services(app: FastAPI) -> Services:
    return app.state.services


@pytest.fixture
def store(services: Services) -> MemoryStore:
    assert services.memory is not None
    return services.memory


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def access_token(mint_jwt: Callable[..., str], user_id: UUID) -> str:
    return mint_jwt(str(user_id), email=USER_EMAIL)


@pytest.fixture
def auth(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def registered_user(client: TestClient, auth: dict[str, str], user_id: UUID) -> UUID:
    """A user the API has seen once, so the profile and the signup grant exist."""
    assert client.get("/v1/me", headers=auth).status_code == 200
    return user_id


@pytest.fixture
def submit(
    client: TestClient, auth: dict[str, str], wav_5s: bytes
) -> Callable[..., Any]:
    """``submit(audio=None, options=None, headers=None)`` posts a multipart job."""

    def _submit(
        audio: bytes | None = None,
        options: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        filename: str = "clip.wav",
        content_type: str = "audio/wav",
    ) -> Any:
        data = {"options": json.dumps(options)} if options is not None else None
        return client.post(
            "/v1/jobs",
            files={"audio": (filename, audio if audio is not None else wav_5s, content_type)},
            data=data,
            headers=headers if headers is not None else auth,
        )

    return _submit


@pytest.fixture
def poll_job(client: TestClient, auth: dict[str, str]) -> Callable[[str], dict[str, Any]]:
    """Poll ``GET /v1/jobs/{id}`` until the job leaves ``queued``/``running``."""

    def _poll(job_id: str, timeout: float = 30.0) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while True:
            body = client.get(f"/v1/jobs/{job_id}", headers=auth).json()
            if body["status"] not in ("queued", "running"):
                return body
            if time.monotonic() > deadline:
                raise AssertionError(f"job {job_id} did not finish: {body['status']}")
            time.sleep(0.05)

    return _poll


@pytest.fixture
def drain_credits(store: MemoryStore) -> Callable[[UUID], None]:
    """Spend every available credit so the next submission hits 402."""

    def _drain(user: UUID) -> None:
        balance = store.get_balance(user)
        if balance.available:
            store.adjust_credits(user, -balance.available, "test", f"drain:{uuid4()}")

    return _drain


def lemonsqueezy_headers(body: bytes, secret: str) -> dict[str, str]:
    return {
        "X-Signature": hmac.new(secret.encode(), body, hashlib.sha256).hexdigest(),
        "Content-Type": "application/json",
    }


def paddle_headers(body: bytes, secret: str, ts: int | None = None) -> dict[str, str]:
    stamp = ts if ts is not None else int(time.time())
    digest = hmac.new(secret.encode(), f"{stamp}:".encode() + body, hashlib.sha256).hexdigest()
    return {"Paddle-Signature": f"ts={stamp};h1={digest}", "Content-Type": "application/json"}


@pytest.fixture
def sign_lemonsqueezy() -> Callable[[bytes, str], dict[str, str]]:
    return lemonsqueezy_headers


@pytest.fixture
def sign_paddle() -> Callable[..., dict[str, str]]:
    return paddle_headers


@pytest.fixture
def queued_job(store: MemoryStore, registered_user: UUID) -> str:
    """A job that is never dispatched, so it stays ``queued`` and cancellable."""
    from app.schemas import JobOptions

    row = store.create_job(
        registered_user, JobOptions().model_dump(mode="json"), {"input_name": "input.wav"}, None
    )
    return str(row.id)


@pytest.fixture
def no_rate_limits(app: FastAPI) -> Iterator[None]:
    """Raise both budgets far above any single test's traffic."""
    limits = app.state.rate_limits
    original = (limits.jobs.capacity, limits.reads.capacity)
    limits.jobs.capacity = limits.reads.capacity = 10_000.0
    yield
    limits.jobs.capacity, limits.reads.capacity = original
