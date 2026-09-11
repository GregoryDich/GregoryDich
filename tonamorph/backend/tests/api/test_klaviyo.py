"""§14 Klaviyo transport: payload shape, disabled without a key, failures never propagate."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
import pytest
import respx
from pydantic import SecretStr

from app.config import Settings
from app.services.klaviyo import (
    EVENTS_PATH,
    KLAVIYO_API_BASE,
    KLAVIYO_REVISION,
    METRICS,
    MORPH_COMPLETED,
    PROFILE_IMPORT_PATH,
    Event,
    KlaviyoClient,
    KlaviyoEvents,
    sample_events,
    seed_metrics,
)

EVENTS_URL = f"{KLAVIYO_API_BASE}{EVENTS_PATH}"


@pytest.fixture
def klaviyo_settings(settings: Settings) -> Settings:
    return settings.model_copy(update={"klaviyo_private_api_key": SecretStr("pk_test_secret")})


def _emitter(settings: Settings) -> KlaviyoEvents:
    return KlaviyoEvents(KlaviyoClient(settings), retry_delay_seconds=0.0)


def _body(route: respx.Route, index: int = -1) -> dict[str, Any]:
    return json.loads(route.calls[index].request.content)


def test_event_payload_is_the_create_event_body() -> None:
    user = uuid4()
    when = datetime(2026, 9, 11, 12, 0, tzinfo=UTC)
    event = Event(
        MORPH_COMPLETED,
        user,
        "a@b.c",
        {"job_id": "j1", "latency_ms": 1800},
        unique_id="morph_completed:j1",
        profile_properties={"morphs_total": 1},
        time=when,
    )
    payload = event.payload()
    data = payload["data"]
    assert data["type"] == "event"
    attributes = data["attributes"]
    assert attributes["metric"] == {
        "data": {"type": "metric", "attributes": {"name": "Morph Completed"}}
    }
    assert attributes["profile"] == {
        "data": {
            "type": "profile",
            "attributes": {
                "external_id": str(user),
                "email": "a@b.c",
                "properties": {"morphs_total": 1},
            },
        }
    }
    assert attributes["properties"] == {"job_id": "j1", "latency_ms": 1800}
    assert attributes["unique_id"] == "morph_completed:j1"
    assert attributes["time"] == "2026-09-11T12:00:00Z"

    anonymous = Event(MORPH_COMPLETED, user, None, {}).payload()["data"]["attributes"]
    assert anonymous["profile"]["data"]["attributes"] == {"external_id": str(user)}
    assert "unique_id" not in anonymous


@respx.mock
async def test_events_are_posted_with_the_private_key_and_revision(
    klaviyo_settings: Settings,
) -> None:
    route = respx.post(EVENTS_URL).mock(return_value=httpx.Response(202))
    events = _emitter(klaviyo_settings)
    user = uuid4()
    events.emit(Event("Signed Up", user, "a@b.c", {"source": "web"}, unique_id=f"signed_up:{user}"))
    assert events.pending == 1
    await events.flush()
    assert route.call_count == 1
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Klaviyo-API-Key pk_test_secret"
    assert request.headers["revision"] == KLAVIYO_REVISION
    assert request.headers["Content-Type"] == "application/json"
    assert _body(route)["data"]["attributes"]["metric"]["data"]["attributes"]["name"] == "Signed Up"
    assert events.pending == 0
    await events.aclose()


@respx.mock
async def test_disabled_without_a_key_sends_nothing(settings: Settings) -> None:
    route = respx.post(EVENTS_URL).mock(return_value=httpx.Response(202))
    events = _emitter(settings)
    assert settings.klaviyo_private_api_key.get_secret_value() == ""
    assert not events.enabled
    events.emit(Event("Signed Up", uuid4(), None, {}))
    assert events.pending == 0
    assert await events.send(Event("Signed Up", uuid4(), None, {})) is False
    await events.flush()
    assert not route.called
    await events.aclose()


@respx.mock
async def test_a_server_error_is_retried_once(klaviyo_settings: Settings) -> None:
    route = respx.post(EVENTS_URL).mock(side_effect=[httpx.Response(503), httpx.Response(202)])
    events = _emitter(klaviyo_settings)
    assert await events.send(Event("Signed Up", uuid4(), None, {})) is True
    assert route.call_count == 2
    await events.aclose()


@respx.mock
async def test_failures_are_logged_and_never_raised(
    klaviyo_settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    events = _emitter(klaviyo_settings)
    user = uuid4()

    respx.post(EVENTS_URL).mock(side_effect=httpx.ConnectError("unreachable"))
    with caplog.at_level(logging.WARNING, logger="tonamorph.klaviyo"):
        events.emit(Event("Morph Failed", user, None, {"error_code": "x"}))
        await events.flush()
    dropped = [r for r in caplog.records if r.getMessage() == "klaviyo event dropped after retry"]
    assert len(dropped) == 1 and dropped[0].metric == "Morph Failed"
    assert dropped[0].user_id == str(user)
    assert "pk_test_secret" not in caplog.text

    route = respx.post(EVENTS_URL).mock(return_value=httpx.Response(400))
    attempts_so_far = route.call_count
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="tonamorph.klaviyo"):
        assert await events.send(Event("Signed Up", user, None, {})) is False
    assert route.call_count == attempts_so_far + 1  # a 4xx is not retried
    assert any(r.getMessage() == "klaviyo refused the event" for r in caplog.records)
    await events.aclose()


async def test_schedule_outside_a_loop_drops_the_coroutine(klaviyo_settings: Settings) -> None:
    events = _emitter(klaviyo_settings)

    async def never() -> None:
        raise AssertionError("must not run")

    import asyncio

    def schedule_without_loop() -> None:
        events.schedule(never())

    await asyncio.to_thread(schedule_without_loop)
    assert events.pending == 0
    await events.aclose()


@respx.mock
async def test_seed_sends_one_event_per_metric_and_upserts_the_profile(
    klaviyo_settings: Settings,
) -> None:
    events = respx.post(EVENTS_URL).mock(return_value=httpx.Response(202))
    profiles = respx.post(f"{KLAVIYO_API_BASE}{PROFILE_IMPORT_PATH}").mock(
        return_value=httpx.Response(201)
    )
    assert await seed_metrics(klaviyo_settings, "founder@example.test") == len(METRICS)
    names = [
        json.loads(call.request.content)["data"]["attributes"]["metric"]["data"]["attributes"][
            "name"
        ]
        for call in events.calls
    ]
    assert names == list(METRICS)
    profile = json.loads(profiles.calls.last.request.content)["data"]
    assert profile["type"] == "profile"
    assert profile["attributes"]["email"] == "founder@example.test"
    assert [e.metric for e in sample_events(uuid4(), "x@y.z")] == list(METRICS)


async def test_seed_refuses_to_run_without_a_key(settings: Settings) -> None:
    with pytest.raises(RuntimeError, match="KLAVIYO_PRIVATE_API_KEY"):
        await seed_metrics(settings, "founder@example.test")
