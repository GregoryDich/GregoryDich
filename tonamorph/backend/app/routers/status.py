"""§14 — the public status summary and the plugin release channel."""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Depends, Request

from app.config import Settings, get_settings
from app.dependencies import get_services
from app.middleware.rate_limit import optional_read_limit
from app.schemas import (
    EngineState,
    PaymentsState,
    StatusComponents,
    StatusLast24h,
    StatusResponse,
    VersionResponse,
)
from app.services.factory import Services
from app.services.quality import DEGRADED_MIN_JOBS, DEGRADED_SUCCESS_RATE, Last24hStats

router = APIRouter(tags=["status"])

STATUS_CACHE_SECONDS = 60.0
DOWNLOAD_PATH = "/download"
CHANGELOG_PATH = "/changelog"


class StatsCache:
    """The last-24 h numbers, refreshed at most once per :data:`STATUS_CACHE_SECONDS`.
    Concurrent misses wait for one refresh rather than each querying the database."""

    def __init__(self, ttl_seconds: float = STATUS_CACHE_SECONDS) -> None:
        self.ttl_seconds = ttl_seconds
        self._value: Last24hStats | None = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    async def get(self, services: Services) -> Last24hStats:
        if self._value is not None and time.monotonic() < self._expires_at:
            return self._value
        async with self._lock:
            if self._value is None or time.monotonic() >= self._expires_at:
                self._value = await services.quality.status_last_24h()
                self._expires_at = time.monotonic() + self.ttl_seconds
            return self._value


def stats_cache(request: Request) -> StatsCache:
    cache = getattr(request.app.state, "stats_cache", None)
    if cache is None:
        cache = request.app.state.stats_cache = StatsCache()
    return cache


def engine_state(settings: Settings, stats: Last24hStats) -> EngineState:
    """``paused`` under ``MAINTENANCE_MODE``; ``degraded`` once enough jobs finished to
    judge and fewer than 90 % of them succeeded; ``operational`` otherwise."""
    if settings.maintenance_mode:
        return "paused"
    rate = stats.success_rate
    if stats.morphs >= DEGRADED_MIN_JOBS and rate is not None and rate < DEGRADED_SUCCESS_RATE:
        return "degraded"
    return "operational"


def payments_state(settings: Settings) -> PaymentsState:
    configured = (
        settings.lemonsqueezy_webhook_secret.get_secret_value()
        or settings.paddle_webhook_secret.get_secret_value()
    )
    return "operational" if configured else "unconfigured"


@router.get("/status", response_model=StatusResponse, dependencies=[Depends(optional_read_limit)])
async def service_status(
    request: Request,
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_settings),
) -> StatusResponse:
    stats = await stats_cache(request).get(services)
    return StatusResponse(
        components=StatusComponents(
            engine=engine_state(settings, stats), payments=payments_state(settings)
        ),
        last_24h=StatusLast24h(
            morphs=stats.morphs,
            success_rate=stats.success_rate,
            p50_ms=stats.p50_ms,
            p95_ms=stats.p95_ms,
        ),
    )


@router.get("/version", response_model=VersionResponse)
async def version(settings: Settings = Depends(get_settings)) -> VersionResponse:
    site = settings.auth_site_url.rstrip("/")
    return VersionResponse(
        latest=settings.plugin_latest_version,
        min_supported=settings.plugin_min_supported_version,
        download_url=site + DOWNLOAD_PATH,
        notes_url=site + CHANGELOG_PATH,
    )
