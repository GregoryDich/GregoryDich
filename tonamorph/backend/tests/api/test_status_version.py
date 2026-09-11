"""§14 ``GET /v1/status`` and ``GET /v1/version``."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings, override_settings
from app.main import create_app
from app.services.factory import Services
from app.services.memory import MemoryStore


def finished_job(store: MemoryStore, user: UUID, *, succeed: bool, latency_ms: int) -> None:
    row = store.create_job(user, {}, {"input_name": "input.wav"}, None)
    store.start_job(row.id, "w")
    if succeed:
        store.complete_job(row.id, {})
    else:
        store.fail_job(row.id, {"code": "internal_error", "message": "boom"})
    row.started_at = row.finished_at - timedelta(milliseconds=latency_ms)  # type: ignore[operator]


def test_status_is_public_and_empty_at_first(client: TestClient) -> None:
    response = client.get("/v1/status")
    assert response.status_code == 200
    assert response.json() == {
        "components": {
            "api": "operational",
            "engine": "operational",
            "payments": "operational",
            "website": "operational",
        },
        "last_24h": {"morphs": 0, "success_rate": None, "p50_ms": None, "p95_ms": None},
    }
    assert "x-ratelimit-remaining" not in response.headers


def test_status_counts_the_last_24_hours(
    client: TestClient, store: MemoryStore, auth: dict[str, str]
) -> None:
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    store.adjust_credits(user, 100, "test", "top-up")
    for latency in (1000, 2000, 3000, 4000):
        finished_job(store, user, succeed=True, latency_ms=latency)
    finished_job(store, user, succeed=False, latency_ms=500)
    old = store.create_job(user, {}, {}, None)
    store.fail_job(old.id, {"code": "internal_error", "message": "old"})
    old.finished_at = datetime.now(UTC) - timedelta(hours=25)
    cancelled = store.create_job(user, {}, {}, None)
    store.cancel_job(cancelled.id, user)

    response = client.get("/v1/status", headers=auth)
    assert response.status_code == 200
    body = response.json()
    assert body["last_24h"] == {"morphs": 5, "success_rate": 0.8, "p50_ms": 2500, "p95_ms": 3850}
    assert body["components"]["engine"] == "operational"  # under twenty jobs: no judgement
    assert response.headers["x-ratelimit-remaining"]  # an authenticated read spends a token


def test_engine_is_degraded_below_ninety_percent_over_twenty_jobs(
    client: TestClient, store: MemoryStore
) -> None:
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    store.adjust_credits(user, 100, "test", "top-up")
    for i in range(20):
        finished_job(store, user, succeed=i % 5 != 0, latency_ms=1000)  # 16 of 20
    body = client.get("/v1/status").json()
    assert body["last_24h"]["morphs"] == 20 and body["last_24h"]["success_rate"] == 0.8
    assert body["components"]["engine"] == "degraded"


@pytest.fixture
def app_factory(settings: Settings) -> Iterator[Callable[[dict[str, Any]], TestClient]]:
    clients: list[TestClient] = []

    def build(update: dict[str, Any]) -> TestClient:
        configured = settings.model_copy(update=update)
        with override_settings(configured):
            client = TestClient(create_app(configured), raise_server_exceptions=False)
        clients.append(client)
        return client

    yield build
    for client in clients:
        client.close()


def test_engine_is_paused_in_maintenance_and_payments_unconfigured_without_a_secret(
    app_factory: Callable[[dict[str, Any]], TestClient],
) -> None:
    paused = app_factory({"maintenance_mode": True}).get("/v1/status").json()
    assert paused["components"]["engine"] == "paused"
    unconfigured = (
        app_factory(
            {"lemonsqueezy_webhook_secret": SecretStr(""), "paddle_webhook_secret": SecretStr("")}
        )
        .get("/v1/status")
        .json()
    )
    assert unconfigured["components"]["payments"] == "unconfigured"


def test_status_numbers_are_cached_for_a_minute(
    client: TestClient, app: FastAPI, services: Services, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0
    compute = services.quality.status_last_24h

    async def counted() -> Any:
        nonlocal calls
        calls += 1
        return await compute()

    monkeypatch.setattr(services.quality, "status_last_24h", counted)
    for _ in range(5):
        assert client.get("/v1/status").status_code == 200
    assert calls == 1
    app.state.stats_cache._expires_at = 0.0
    assert client.get("/v1/status").status_code == 200
    assert calls == 2


def test_version_comes_from_settings(
    app_factory: Callable[[dict[str, Any]], TestClient], client: TestClient
) -> None:
    assert client.get("/v1/version").json() == {
        "latest": "0.1.0",
        "min_supported": "0.1.0",
        "download_url": "http://localhost:3000/download",
        "notes_url": "http://localhost:3000/changelog",
    }
    configured = app_factory(
        {
            "plugin_latest_version": "1.2.3",
            "plugin_min_supported_version": "1.0.0",
            "auth_site_url": "https://tonamorph.com/",
        }
    )
    assert configured.get("/v1/version").json() == {
        "latest": "1.2.3",
        "min_supported": "1.0.0",
        "download_url": "https://tonamorph.com/download",
        "notes_url": "https://tonamorph.com/changelog",
    }


def test_plugin_versions_must_be_semantic() -> None:
    with pytest.raises(ValueError, match="plugin_latest_version"):
        Settings(_env_file=None, plugin_latest_version="latest")  # type: ignore[call-arg]
    assert Settings(_env_file=None, plugin_min_supported_version="0.1.0-beta.2")  # type: ignore[call-arg]
