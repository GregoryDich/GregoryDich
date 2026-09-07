"""Deployment self-checks for configuration no migration can seed (§3).

`plans.provider_variant_ids` holds the operator's LemonSqueezy variant / Paddle price
ids. Until they are filled in, `build_checkout_url` returns ``None`` for every paid plan,
``GET /v1/plans`` answers ``"checkout_url": null``, and the plugin's paywall opens with no
buttons — the API is healthy, the tests pass and nobody can pay. These checks are the
alarm: :func:`log_checkout_configuration` runs at startup (error level under
``ENV=production``), and ``python -m app.checks`` runs the same check on demand, printing
one JSON object and exiting non-zero, so a deployment can gate on it before users see the
paywall.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys

from app.config import Settings, get_settings
from app.services.plans import PlansService, unsellable_plan_ids

log = logging.getLogger("snapplay.checks")


async def unsellable_plans(plans: PlansService) -> list[str]:
    """Active paid plans with no usable checkout URL, by plan id."""
    return unsellable_plan_ids(await plans.list_active())


async def log_checkout_configuration(plans: PlansService, settings: Settings) -> list[str]:
    """Report the paid plans nobody can buy, and return their ids.

    Production logs this at error level: a paid plan without a checkout URL is a shipped
    paywall with no buttons. Elsewhere it is a warning, and under ``ENV=test`` a debug
    line, so a fresh checkout of this repository still boots and still runs its tests.
    A check that cannot run at all (the plans table unreachable) is reported rather than
    allowed to take the process down.
    """
    try:
        unconfigured = await unsellable_plans(plans)
    except Exception:
        log.error("checkout configuration check failed to run", exc_info=True)
        return []
    if not unconfigured:
        return []
    if settings.env == "production":
        level = logging.ERROR
    elif settings.env == "test":
        level = logging.DEBUG
    else:
        level = logging.WARNING
    log.log(
        level,
        "paid plans have no checkout URL and cannot be bought",
        extra={"plan_ids": unconfigured, "fix": "set plans.provider_variant_ids"},
    )
    return unconfigured


def main() -> int:
    """``python -m app.checks``: 0 when every paid plan is sellable, 1 otherwise."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    settings = get_settings()
    from app.services.factory import build_services

    services = build_services(settings)

    async def _run() -> list[str]:
        try:
            return await unsellable_plans(services.plans)
        finally:
            await services.aclose()

    unconfigured = asyncio.run(_run())
    print(
        json.dumps(
            {
                "check": "checkout_configured",
                "ok": not unconfigured,
                "unsellable_plan_ids": unconfigured,
                "fix": "set plans.provider_variant_ids for these plans",
            }
        )
    )
    return 1 if unconfigured else 0


if __name__ == "__main__":
    sys.exit(main())
