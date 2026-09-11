"""Stale-job reaper (contract §10): ``python -m app.services.aws.reaper``.

EventBridge runs this as a one-off task in the API image every few minutes. It fails
jobs left ``running`` longer than ``JOB_TIMEOUT_SECONDS`` (``worker_timeout``) and
releases their credit reservations through ``JobsService.reap_stale`` — on Supabase
the ``reap_stale_jobs`` function — so a dead worker never silently consumes a credit.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Protocol

from app.config import Settings, get_settings
from app.services import JobsService

log = logging.getLogger("tonamorph.aws.reaper")


class ServiceBundle(Protocol):
    """The slice of the wired services the reaper needs."""

    jobs: JobsService


async def reap_once(services: ServiceBundle, timeout_seconds: int) -> int:
    """Reap once and return the number of jobs failed."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    reaped = await services.jobs.reap_stale(timeout_seconds)
    log.info("reaped %d stale job(s) running longer than %ds", reaped, timeout_seconds)
    return reaped


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
    asyncio.run(reap_once(build_services(settings), settings.job_timeout_seconds))
    return 0


if __name__ == "__main__":
    sys.exit(main())
