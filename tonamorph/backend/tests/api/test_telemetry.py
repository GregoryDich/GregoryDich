"""§14 ``POST /v1/telemetry/crash``: budgets, validation and what reaches Sentry."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.observability import init_sentry
from app.routers.telemetry import ANONYMOUS_CRASHES_PER_HOUR
from app.schemas import MAX_BACKTRACE_BYTES

REPORT: dict[str, Any] = {
    "plugin_version": "0.1.0",
    "os": "macOS 15.1",
    "host": "Ableton Live 12",
    "occurred_at": "2026-09-11T12:00:00Z",
    "backtrace": "EXC_BAD_ACCESS\n  0 Tonamorph  StemVoice::renderNextBlock\n  1 Ableton Live",
    "opted_in": True,
}


def test_anonymous_reports_are_accepted_within_a_strict_budget(client: TestClient) -> None:
    for _ in range(ANONYMOUS_CRASHES_PER_HOUR):
        response = client.post("/v1/telemetry/crash", json=REPORT)
        assert response.status_code == 202 and response.json() == {"status": "accepted"}
    refused = client.post("/v1/telemetry/crash", json=REPORT)
    assert refused.status_code == 429 and refused.json()["error"]["code"] == "rate_limited"
    assert int(refused.headers["Retry-After"]) >= 1
    assert refused.headers["X-RateLimit-Remaining"] == "0"


def test_a_session_spends_the_reads_budget_instead(
    client: TestClient, auth: dict[str, str]
) -> None:
    remaining = None
    for _ in range(ANONYMOUS_CRASHES_PER_HOUR + 1):
        response = client.post("/v1/telemetry/crash", json=REPORT, headers=auth)
        assert response.status_code == 202
        remaining = int(response.headers["X-RateLimit-Remaining"])
    assert remaining is not None and remaining >= 50
    bad_token = client.post(
        "/v1/telemetry/crash", json=REPORT, headers={"Authorization": "Bearer nope"}
    )
    assert bad_token.status_code == 401


@pytest.mark.parametrize(
    "change",
    [
        {"opted_in": False},
        {"opted_in": "yes"},
        {"backtrace": "x" * (MAX_BACKTRACE_BYTES + 1)},
        {"backtrace": ""},
        {"plugin_version": "v" * 33},
        {"occurred_at": "yesterday"},
        {"audio": "AAAA"},
    ],
)
def test_reports_are_validated(client: TestClient, change: dict[str, Any]) -> None:
    body = {**REPORT, **change}
    response = client.post("/v1/telemetry/crash", json=body)
    assert response.status_code == 422 and response.json()["error"]["code"] == "validation_error"


def test_without_sentry_the_report_is_logged_without_the_backtrace(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="tonamorph.observability"):
        assert client.post("/v1/telemetry/crash", json=REPORT).status_code == 202
    record = next(r for r in caplog.records if r.levelno == logging.WARNING)
    assert record.plugin_version == "0.1.0" and record.host == "Ableton Live 12"
    assert record.os == "macOS 15.1" and record.backtrace_bytes == len(REPORT["backtrace"])
    assert record.user_id is None
    assert "EXC_BAD_ACCESS" not in caplog.text


@pytest.fixture
def sentry_envelopes(settings: Settings) -> Iterator[list[Any]]:
    sentry_sdk = pytest.importorskip("sentry_sdk")
    from sentry_sdk.transport import Transport

    captured: list[Any] = []

    class Capturing(Transport):
        def capture_envelope(self, envelope: Any) -> None:
            captured.append(envelope)

    configured = settings.model_copy(
        update={"sentry_dsn": "https://key@example.ingest.sentry.io/1"}
    )
    assert init_sentry(configured, role="api", transport=Capturing()) is True
    try:
        yield captured
    finally:
        sentry_sdk.get_global_scope().set_client(None)


def test_with_sentry_the_report_is_a_tagged_message_with_the_backtrace_attached(
    client: TestClient, auth: dict[str, str], registered_user: Any, sentry_envelopes: list[Any]
) -> None:
    import sentry_sdk

    assert client.post("/v1/telemetry/crash", json=REPORT, headers=auth).status_code == 202
    sentry_sdk.flush(timeout=2.0)
    envelope = next(e for e in sentry_envelopes if e.get_event() is not None)
    event = envelope.get_event()
    assert event["level"] == "error"
    assert event["message"].startswith("Plugin crash (Ableton Live 12, macOS 15.1, 0.1.0)")
    assert event["tags"]["role"] == "plugin"
    assert event["tags"]["plugin_version"] == "0.1.0"
    assert event["tags"]["host"] == "Ableton Live 12" and event["tags"]["os"] == "macOS 15.1"
    assert event["user"] == {"id": str(registered_user)}
    assert event["fingerprint"] == [
        "plugin",
        "macOS 15.1",
        "Ableton Live 12",
        "0.1.0",
        "EXC_BAD_ACCESS",
    ]
    attachments = [item for item in envelope.items if item.type == "attachment"]
    assert len(attachments) == 1
    assert attachments[0].headers["filename"] == "backtrace.txt"
    assert attachments[0].payload.get_bytes() == REPORT["backtrace"].encode()
    assert "headers" not in (event.get("request") or {})
