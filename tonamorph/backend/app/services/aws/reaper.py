"""Stale-job reaper and first-week gifts (contract §10, §3):
``python -m app.services.aws.reaper``.

EventBridge runs this as a one-off task in the API image every few minutes. It fails
jobs left ``running`` longer than ``JOB_TIMEOUT_SECONDS`` (``worker_timeout``) and
releases their credit reservations through ``JobsService.reap_stale`` — on Supabase
the ``reap_stale_jobs`` function — so a dead worker never silently consumes a credit.
The same tick runs ``grant_week1_gifts()`` and emits ``Gift Granted`` (§14) for every
account it gifted; the pg_cron line in ``db/README.md`` grants the same credits on a
deployment without this task, only without the event.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Protocol
from uuid import UUID

from app.config import Settings, get_settings
from app.services import JobsService
from app.services.rewards import RewardsService

log = logging.getLogger("tonamorph.aws.reaper")


class GiftHooks(Protocol):
    """The growth hook the gift step fires (``GrowthHooks.gift_granted``)."""

    def gift_granted(self, user_id: UUID) -> None: ...


class ServiceBundle(Protocol):
    """The slice of the wired services this task needs."""

    jobs: JobsService
    rewards: RewardsService
    growth: GiftHooks


async def _flush_events(services: object) -> None:
    """Events are background tasks; a one-off process waits for them before its loop ends."""
    flush = getattr(getattr(services, "klaviyo", None), "flush", None)
    if flush is not None:
        await flush()


async def reap_once(services: ServiceBundle, timeout_seconds: int) -> int:
    """Reap once and return the number of jobs failed. Each reaped job is a ``Morph
    Failed`` event (§14)."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    reaped = await services.jobs.reap_stale(timeout_seconds)
    log.info("reaped %d stale job(s) running longer than %ds", reaped, timeout_seconds)
    await _flush_events(services)
    return reaped


async def grant_gifts_once(services: ServiceBundle) -> int:
    """Run ``grant_week1_gifts()`` and tell each gifted account (``Gift Granted``);
    returns how many were gifted. A second run within the hour finds nothing left."""
    gifted = await services.rewards.grant_week1_gifts()
    for user_id in gifted:
        services.growth.gift_granted(user_id)
    log.info("granted %d first-week gift(s)", len(gifted))
    await _flush_events(services)
    return len(gifted)


async def run_once(services: ServiceBundle, timeout_seconds: int) -> tuple[int, int]:
    """One maintenance tick: ``(jobs reaped, gifts granted)``."""
    return await reap_once(services, timeout_seconds), await grant_gifts_once(services)


def build_services(settings: Settings) -> ServiceBundle:
    """The production service bundle, imported lazily so the module stays importable
    without the backend implementations."""
    from app.services.factory import build_services as factory

    return factory(settings)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    settings = get_settings()
    asyncio.run(run_once(build_services(settings), settings.job_timeout_seconds))
    return 0


if __name__ == "__main__":
    sys.exit(main())
