"""§2 event streams: SSE (the plugin's path) and the WebSocket used by web clients."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.schemas import JobResult
from app.services.memory import MemoryStore

pytestmark = pytest.mark.usefixtures("no_rate_limits")


def read_sse(lines: Iterator[str]) -> Iterator[tuple[str, dict[str, Any] | None]]:
    """Yield ``(event, data)`` per SSE block; comment lines surface as ``(":", None)``."""
    event = "message"
    data: list[str] = []
    for raw in lines:
        line = raw.rstrip("\r")
        if line.startswith(":"):
            yield ":", None
            continue
        if line == "":
            if data:
                yield event, json.loads("\n".join(data))
            event, data = "message", []
            continue
        field, _, value = line.partition(":")
        value = value.removeprefix(" ")
        if field == "event":
            event = value
        elif field == "data":
            data.append(value)
    if data:
        yield event, json.loads("\n".join(data))


def test_sse_stream_yields_progress_then_result_and_ends(
    client: TestClient,
    auth: dict[str, str],
    submit: Callable[..., Any],
    registered_user: UUID,
) -> None:
    job_id = submit().json()["job_id"]
    events: list[tuple[str, dict[str, Any] | None]] = []
    with client.stream("GET", f"/v1/jobs/{job_id}/events", headers=auth) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        for event in read_sse(response.iter_lines()):
            if event[0] == ":":
                continue
            events.append(event)
            if event[0] in ("result", "error"):
                break

    names = [name for name, _ in events]
    assert names[-1] == "result" and names.count("result") == 1
    assert set(names[:-1]) == {"progress"}
    for _, payload in events[:-1]:
        assert payload is not None
        assert payload["stage"] in {
            "upload",
            "separate",
            "transcribe",
            "analyze",
            "package",
            "done",
        }
        assert 0.0 <= payload["progress"] <= 1.0
    result_payload = events[-1][1]
    assert result_payload is not None and result_payload["status"] == "succeeded"
    assert JobResult.model_validate(result_payload["result"]).credits_charged == 1


def test_sse_of_a_finished_job_replays_the_result(
    client: TestClient,
    auth: dict[str, str],
    submit: Callable[..., Any],
    poll_job: Callable[[str], dict[str, Any]],
    registered_user: UUID,
) -> None:
    job_id = submit().json()["job_id"]
    poll_job(job_id)
    with client.stream("GET", f"/v1/jobs/{job_id}/events", headers=auth) as response:
        events = [e for e in read_sse(response.iter_lines()) if e[0] != ":"]
    assert [name for name, _ in events] == ["result"]


def test_sse_reports_a_failed_job_as_an_error_event(
    client: TestClient, auth: dict[str, str], store: MemoryStore, queued_job: str
) -> None:
    store.start_job(UUID(queued_job))
    store.fail_job(UUID(queued_job), {"code": "worker_timeout", "message": "no completion"})
    with client.stream("GET", f"/v1/jobs/{queued_job}/events", headers=auth) as response:
        events = [e for e in read_sse(response.iter_lines()) if e[0] != ":"]
    assert events == [("error", {"code": "worker_timeout", "message": "no completion"})]


def test_sse_requires_authentication(client: TestClient, queued_job: str) -> None:
    assert client.get(f"/v1/jobs/{queued_job}/events").status_code == 401


def test_websocket_streams_the_same_payloads(
    client: TestClient, access_token: str, submit: Callable[..., Any], registered_user: UUID
) -> None:
    job_id = submit().json()["job_id"]
    received: list[dict[str, Any]] = []
    with client.websocket_connect(f"/v1/jobs/{job_id}/ws?token={access_token}") as socket:
        while True:
            message = json.loads(socket.receive_text())
            received.append(message)
            if message["event"] in ("result", "error"):
                break
    assert received[-1]["event"] == "result"
    assert received[-1]["data"]["status"] == "succeeded"
    assert all(m["event"] == "progress" for m in received[:-1])


def test_websocket_rejects_a_bad_token(client: TestClient, queued_job: str) -> None:
    with pytest.raises(Exception):  # noqa: B017 — starlette raises on the close frame
        with client.websocket_connect(f"/v1/jobs/{queued_job}/ws?token=nope") as socket:
            socket.receive_text()
