"""§3 — the deployment self-check for a paywall that would ship with no working buttons."""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest
from fastapi import FastAPI

from app.checks import log_checkout_configuration, main, unsellable_plans
from app.config import Settings
from app.services.factory import Services
from app.services.memory import MemoryStore
from app.services.plans import PlanRecord, unsellable_plan_ids

VARIANT = {"lemonsqueezy": "variant-1"}


@pytest.fixture
def services(app: FastAPI) -> Services:
    return app.state.services


@pytest.fixture
def store(services: Services) -> MemoryStore:
    assert services.memory is not None
    return services.memory


def test_a_freshly_seeded_catalogue_cannot_sell_anything(store: MemoryStore) -> None:
    """The seed leaves ``provider_variant_ids`` empty, so every paid plan resolves to
    ``checkout_url: null``. The free plan is not a problem: nobody buys it."""
    assert unsellable_plan_ids(store.plans.values()) == ["pack_50", "sub_monthly"]

    store.plans["pack_50"].provider_variant_ids = dict(VARIANT)
    assert unsellable_plan_ids(store.plans.values()) == ["sub_monthly"]

    store.plans["sub_monthly"].provider_variant_ids = dict(VARIANT)
    assert unsellable_plan_ids(store.plans.values()) == []

    # An inactive plan is not on sale, and a plan with no template never claimed to be.
    store.plans["pack_50"].provider_variant_ids = {}
    store.plans["pack_50"].active = False
    assert unsellable_plan_ids(store.plans.values()) == []
    assert unsellable_plan_ids([PlanRecord(id="p", name="P", credits=1, price_cents=100)]) == ["p"]


async def test_production_logs_an_error_naming_every_unsellable_plan(
    services: Services, settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    """Under ``ENV=production`` this is the alarm an operator must not be able to miss:
    an error-level record carrying exactly the plan ids nobody can buy."""
    settings.env = "production"
    with caplog.at_level(logging.DEBUG, logger="tonamorph.checks"):
        unconfigured = await log_checkout_configuration(services.plans, settings)

    assert unconfigured == ["pack_50", "sub_monthly"]
    record = next(r for r in caplog.records if r.name == "tonamorph.checks")
    assert record.levelno == logging.ERROR
    assert record.plan_ids == ["pack_50", "sub_monthly"]


async def test_a_configured_catalogue_logs_nothing(
    services: Services, store: MemoryStore, settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    settings.env = "production"
    for plan_id in ("pack_50", "sub_monthly"):
        store.plans[plan_id].provider_variant_ids = dict(VARIANT)
    with caplog.at_level(logging.DEBUG, logger="tonamorph.checks"):
        assert await log_checkout_configuration(services.plans, settings) == []
    assert [r for r in caplog.records if r.name == "tonamorph.checks"] == []


async def test_an_unreachable_plans_table_is_reported_not_fatal(
    services: Services, settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    """The check must not be able to take the API down on its own."""

    class Broken:
        async def list_active(self) -> list[PlanRecord]:
            raise RuntimeError("plans unreachable")

    with caplog.at_level(logging.ERROR, logger="tonamorph.checks"):
        assert await log_checkout_configuration(Broken(), settings) == []  # type: ignore[arg-type]
    assert "failed to run" in caplog.records[0].message


async def test_the_wired_services_expose_the_same_answer(services: Services) -> None:
    assert await unsellable_plans(services.plans) == ["pack_50", "sub_monthly"]


def test_the_operator_command_prints_a_report_and_exits_nonzero(
    settings: Settings, capsys: pytest.CaptureFixture[str]
) -> None:
    """``python -m app.checks`` is the pre-flight an operator can run before users hit the
    paywall; a non-zero exit lets a deployment gate on it."""
    assert main() == 1
    report: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert report["ok"] is False
    assert report["unsellable_plan_ids"] == ["pack_50", "sub_monthly"]
