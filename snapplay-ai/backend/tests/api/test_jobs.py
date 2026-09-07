"""§2 job lifecycle: validation, credits, idempotency, cancellation."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.formparsers import MultiPartParser
from starlette.requests import ClientDisconnect
from starlette.types import Message, Receive, Scope, Send

from app.middleware.body_limit import MULTIPART_OVERHEAD_BYTES, BodyLimitMiddleware
from app.schemas import JobResult
from app.services.factory import Services
from app.services.memory import MemoryStore

pytestmark = pytest.mark.usefixtures("no_rate_limits")


def test_new_user_starts_with_three_credits(client: TestClient, auth: dict[str, str]) -> None:
    body = client.get("/v1/me", headers=auth).json()
    assert body["balance"] == {
        "credits": 3,
        "reserved": 0,
        "available": 3,
        "subscription_renews_at": None,
    }
    assert body["user"]["plan"] == "free"


def test_full_job_lifecycle_charges_exactly_one_credit(
    client: TestClient,
    auth: dict[str, str],
    submit: Callable[..., Any],
    poll_job: Callable[[str], dict[str, Any]],
    make_wav: Callable[..., bytes],
    registered_user: UUID,
) -> None:
    accepted = submit(audio=make_wav(seconds=3.0))
    assert accepted.status_code == 202
    body = accepted.json()
    assert body["status"] == "queued" and body["credits_reserved"] == 1
    assert body["balance"] == {"credits": 3, "reserved": 1, "available": 2}

    finished = poll_job(body["job_id"])
    assert finished["status"] == "succeeded"
    assert finished["stage"] == "done" and finished["progress"] == 1.0

    result = JobResult.model_validate(finished["result"])
    assert str(result.job_id) == body["job_id"]
    assert result.credits_charged == 1 and result.balance_after == 2
    assert [stem.name for stem in result.stems] == ["bass", "drums", "other", "vocals"]
    assert all(stem.url and stem.url.startswith("memory://") for stem in result.stems)
    assert result.midi.url and result.midi.url.startswith(f"memory://jobs/{registered_user}/")
    assert "/score.mid?exp=" in result.midi.url
    assert result.input.duration_seconds == pytest.approx(3.0, abs=0.05)

    balance = client.get("/v1/me", headers=auth).json()["balance"]
    assert balance["credits"] == 2 and balance["reserved"] == 0 and balance["available"] == 2

    entries = client.get("/v1/credits/ledger", headers=auth).json()["entries"]
    assert [e["entry_type"] for e in entries] == ["capture", "reserve", "grant"]
    assert [e["amount"] for e in entries] == [-1, -1, 3]
    assert entries[0]["balance_after"] == 2


def test_uploaded_input_and_results_live_under_the_job_prefix(
    submit: Callable[..., Any],
    poll_job: Callable[[str], dict[str, Any]],
    services: Services,
    registered_user: UUID,
) -> None:
    job_id = submit().json()["job_id"]
    poll_job(job_id)
    prefix = f"jobs/{registered_user}/{job_id}/"
    stored = sorted(k.removeprefix(prefix) for k in services.storage.objects)  # type: ignore[attr-defined]
    assert stored == ["bass.wav", "drums.wav", "input.wav", "other.wav", "score.mid", "vocals.wav"]


def test_insufficient_credits_returns_402_without_creating_a_job(
    submit: Callable[..., Any],
    drain_credits: Callable[[UUID], None],
    store: MemoryStore,
    registered_user: UUID,
) -> None:
    drain_credits(registered_user)
    response = submit()
    assert response.status_code == 402
    body = response.json()["error"]
    assert body["code"] == "insufficient_credits" and body["details"]["available"] == 0
    assert store.jobs == {}


def test_idempotent_resubmit_returns_the_same_job_without_a_second_charge(
    client: TestClient,
    auth: dict[str, str],
    submit: Callable[..., Any],
    store: MemoryStore,
    registered_user: UUID,
) -> None:
    options = {"idempotency_key": str(uuid4())}
    first = submit(options=options)
    second = submit(options=options)
    assert first.status_code == second.status_code == 202
    assert first.json()["job_id"] == second.json()["job_id"]
    assert len(store.jobs) == 1
    assert sum(1 for row in store.ledger if row.entry_type == "reserve") == 1


def test_unsupported_media_type(submit: Callable[..., Any], registered_user: UUID) -> None:
    response = submit(audio=b"just some text, definitely not audio", filename="notes.txt")
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media_type"


def test_oversize_upload_is_rejected(
    submit: Callable[..., Any], services: Services, registered_user: UUID
) -> None:
    oversize = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * services.settings.max_upload_bytes
    response = submit(audio=oversize)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_invalid_options_are_422(submit: Callable[..., Any], registered_user: UUID) -> None:
    assert submit(options={"stems": ["tuba"]}).status_code == 422
    assert submit(options={"target_root_midi": 300}).status_code == 422
    assert submit(options={"unknown": 1}).status_code == 422


def test_job_of_another_user_is_404(
    client: TestClient,
    submit: Callable[..., Any],
    mint_jwt: Callable[..., str],
    registered_user: UUID,
) -> None:
    job_id = submit().json()["job_id"]
    other = {"Authorization": f"Bearer {mint_jwt()}"}
    assert client.get(f"/v1/jobs/{job_id}", headers=other).status_code == 404
    assert client.delete(f"/v1/jobs/{job_id}", headers=other).status_code == 404


def test_cancel_queued_job_releases_the_reservation(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    queued_job: str,
) -> None:
    job = queued_job
    assert client.delete(f"/v1/jobs/{job}", headers=auth).status_code == 204
    assert store.jobs[UUID(job)].status == "cancelled"
    balance = client.get("/v1/me", headers=auth).json()["balance"]
    assert balance == {
        "credits": 3,
        "reserved": 0,
        "available": 3,
        "subscription_renews_at": None,
    }


def test_cancel_running_and_finished_jobs_conflict(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    queued_job: str,
    submit: Callable[..., Any],
    poll_job: Callable[[str], dict[str, Any]],
) -> None:
    running = queued_job
    store.start_job(UUID(running))
    conflict = client.delete(f"/v1/jobs/{running}", headers=auth)
    assert conflict.status_code == 409 and conflict.json()["error"]["code"] == "conflict"

    finished = submit().json()["job_id"]
    poll_job(finished)
    assert client.delete(f"/v1/jobs/{finished}", headers=auth).status_code == 409


def test_dispatch_failure_releases_the_reservation(
    client: TestClient,
    auth: dict[str, str],
    submit: Callable[..., Any],
    services: Services,
    monkeypatch: pytest.MonkeyPatch,
    registered_user: UUID,
) -> None:
    from app.errors import WORKER_UNAVAILABLE, ApiException

    async def unavailable(*_: object, **__: object) -> None:
        raise ApiException(WORKER_UNAVAILABLE)

    monkeypatch.setattr(services.dispatch, "dispatch", unavailable)
    response = submit()
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "worker_unavailable"
    balance = client.get("/v1/me", headers=auth).json()["balance"]
    assert balance == {
        "credits": 3,
        "reserved": 0,
        "available": 3,
        "subscription_renews_at": None,
    }


def _spy_on_multipart(monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    """Record whether starlette's multipart parser ever ran — i.e. whether the request
    body was consumed (and parts over 1 MB spooled to disk) before the rejection."""
    parsed: list[bool] = []
    original = MultiPartParser.parse

    async def spy(self: MultiPartParser) -> Any:
        parsed.append(True)
        return await original(self)

    monkeypatch.setattr(MultiPartParser, "parse", spy)
    return parsed


def _over_the_wire_cap(services: Services) -> bytes:
    return b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * (
        services.settings.max_upload_bytes + MULTIPART_OVERHEAD_BYTES
    )


def test_unauthenticated_upload_is_rejected_before_the_body_is_read(
    client: TestClient, services: Services, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M5: the 401 used to arrive only after every byte had been parsed and spooled."""
    parsed = _spy_on_multipart(monkeypatch)
    response = client.post(
        "/v1/jobs",
        files={"audio": ("clip.wav", _over_the_wire_cap(services), "audio/wav")},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
    assert parsed == [], "the body must not be parsed for a request without credentials"


def test_oversized_upload_is_rejected_before_the_body_is_read(
    submit: Callable[..., Any],
    services: Services,
    registered_user: UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parsed = _spy_on_multipart(monkeypatch)
    response = submit(audio=_over_the_wire_cap(services))
    assert response.status_code == 413
    body = response.json()["error"]
    assert body["code"] == "payload_too_large"
    assert body["details"]["max_bytes"] == services.settings.max_upload_bytes
    assert parsed == [], "Content-Length above the cap must be refused before parsing"


async def test_a_body_without_content_length_is_cut_off_at_the_cap() -> None:
    """A chunked body (or a lying Content-Length) is counted as it streams: the app is
    unwound and the answer is 413 long before the whole payload has been received."""
    reached_app = False

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        nonlocal reached_app
        reached_app = True
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                raise ClientDisconnect
            if not message.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 202, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    limited = BodyLimitMiddleware(app, max_upload_bytes=64 * 1024)
    chunk = b"\x00" * 16 * 1024
    offered = 0

    async def receive() -> Message:
        nonlocal offered
        offered += len(chunk)
        return {"type": "http.request", "body": chunk, "more_body": True}

    messages: list[Message] = []

    async def send(message: Message) -> None:
        messages.append(message)

    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/v1/jobs",
        "headers": [(b"authorization", b"Bearer token")],  # no content-length at all
    }
    await limited(scope, receive, send)

    assert reached_app is True
    assert messages[0]["status"] == 413
    assert json.loads(messages[1]["body"])["error"]["code"] == "payload_too_large"
    assert offered <= 64 * 1024 + MULTIPART_OVERHEAD_BYTES + len(chunk)


async def test_the_cap_lets_a_legal_upload_through() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        while (await receive()).get("more_body"):
            pass
        await send({"type": "http.response.start", "status": 202, "headers": []})
        await send({"type": "http.response.body", "body": b"{}"})

    limited = BodyLimitMiddleware(app, max_upload_bytes=64 * 1024)
    body = b"\x00" * 60 * 1024
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/v1/jobs",
        "headers": [
            (b"authorization", b"Bearer token"),
            (b"content-length", str(len(body)).encode()),
        ],
    }

    async def receive() -> Message:
        return {"type": "http.request", "body": body, "more_body": False}

    messages: list[Message] = []

    async def send(message: Message) -> None:
        messages.append(message)

    await limited(scope, receive, send)
    assert messages[0]["status"] == 202
