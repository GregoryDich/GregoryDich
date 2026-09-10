from typing import Any

import pytest

from app.config import Settings
from app.observability import init_sentry, scrub_event


def test_disabled_without_dsn(settings: Settings) -> None:
    assert settings.sentry_dsn == ""
    assert init_sentry(settings, role="api") is False


def test_dsn_must_be_https() -> None:
    with pytest.raises(ValueError, match="https"):
        Settings(sentry_dsn="http://key@example.ingest.sentry.io/1")  # type: ignore[call-arg]


def test_scrub_event_drops_request_data_and_user_details() -> None:
    event: dict[str, Any] = {
        "request": {
            "url": "https://api.example/v1/jobs",
            "method": "POST",
            "headers": {"Authorization": "Bearer secret"},
            "cookies": "sb=1",
            "data": {"audio": "..."},
            "query_string": "token=abc",
        },
        "user": {"id": "u1", "email": "a@b.c", "ip_address": "1.2.3.4"},
    }
    scrubbed = scrub_event(event)
    assert scrubbed["request"] == {"url": "https://api.example/v1/jobs", "method": "POST"}
    assert scrubbed["user"] == {"id": "u1"}
    assert scrub_event({"user": {"email": "x"}})["user"] == {}


def test_events_leave_scrubbed_and_tagged(settings: Settings) -> None:
    sentry_sdk = pytest.importorskip("sentry_sdk")
    captured: list[dict[str, Any]] = []
    configured = settings.model_copy(
        update={"sentry_dsn": "https://key@example.ingest.sentry.io/1"}
    )
    assert init_sentry(configured, role="worker", transport=captured.append) is True
    try:
        with sentry_sdk.new_scope() as scope:
            scope.set_user({"id": "u1", "email": "a@b.c"})
            scope.set_context("request", {"headers": {"Authorization": "x"}})
            sentry_sdk.capture_message("benchmark failure")
        sentry_sdk.flush(timeout=2.0)
    finally:
        sentry_sdk.get_global_scope().set_client(None)

    events = [
        e for e in captured if isinstance(e, dict) and e.get("message") == "benchmark failure"
    ]
    assert events, captured
    event = events[0]
    assert event["tags"]["role"] == "worker"
    assert event["environment"] == configured.env
    assert event["user"] == {"id": "u1"}
    assert "headers" not in (event.get("request") or {})
