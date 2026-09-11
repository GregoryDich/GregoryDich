"""§4 provider refunds move credits: the unspent part of the purchase leaves the balance,
the pending commission is voided, a refunded subscription period ends, and nothing here
can run twice or touch a credit a job captured or still holds."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.services.memory import MemoryStore
from tests.api.test_webhooks import (
    PACK_VARIANT,
    PADDLE_PACK_PRICE,
    PADDLE_SUB_PRICE,
    SUB_VARIANT,
    ls_order,
    paddle_event,
)

pytestmark = pytest.mark.usefixtures("no_rate_limits")


@pytest.fixture(autouse=True)
def provider_variants(store: MemoryStore) -> None:
    store.plans["pack_50"].provider_variant_ids = {
        "lemonsqueezy": PACK_VARIANT,
        "paddle": PADDLE_PACK_PRICE,
    }
    store.plans["sub_monthly"].provider_variant_ids = {
        "lemonsqueezy": SUB_VARIANT,
        "paddle": PADDLE_SUB_PRICE,
    }


def paddle_adjustment(
    event_id: str,
    *,
    transaction_id: str = "txn_1",
    action: str = "refund",
    status: str = "approved",
) -> bytes:
    return json.dumps(
        {
            "event_id": event_id,
            "event_type": "adjustment.updated",
            "data": {
                "id": "adj_1",
                "action": action,
                "status": status,
                "reason": "requested_by_customer",
                "transaction_id": transaction_id,
                "totals": {"total": "900"},
            },
        }
    ).encode()


def morph(store: MemoryStore, user: UUID) -> None:
    """A captured job: one credit spent for good."""
    job = store.create_job(user, {}, {"input_name": "input.wav"}, None)
    store.start_job(job.id, "worker")
    store.complete_job(job.id, {})


def test_lemonsqueezy_order_refund_takes_back_the_unspent_credits(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    registered_user: UUID,
    sign_lemonsqueezy: Callable[[bytes, str], dict[str, str]],
    settings: Any,
) -> None:
    """min(purchase credits, available): captured credits are gone, a reserved one stays
    with its job, the commission is voided and the plan drops with the pack."""
    affiliate = uuid4()
    store.ensure_user(affiliate, "affiliate@example.test")
    store.add_affiliate(affiliate, "FRIEND")
    secret = settings.lemonsqueezy_webhook_secret.get_secret_value()
    sale = ls_order(registered_user, ref="friend", total=900, tax=100)
    assert client.post(
        "/v1/webhooks/lemonsqueezy", content=sale, headers=sign_lemonsqueezy(sale, secret)
    ).json() == {"status": "ok"}
    morph(store, registered_user)
    morph(store, registered_user)
    store.create_job(registered_user, {}, {"input_name": "input.wav"}, None)  # holds one
    assert store.get_balance(registered_user).model_dump() == {
        "credits": 51,
        "reserved": 1,
        "available": 50,
    }
    commission = next(iter(store.commissions.values()))
    assert commission.status == "pending"

    refund = ls_order(registered_user, event_name="order_refunded", total=900, tax=100)
    response = client.post(
        "/v1/webhooks/lemonsqueezy", content=refund, headers=sign_lemonsqueezy(refund, secret)
    )
    assert response.status_code == 200 and response.json() == {"status": "ok"}
    me = client.get("/v1/me", headers=auth).json()
    assert me["balance"] == {
        "credits": 1,
        "reserved": 1,
        "available": 0,
        "subscription_renews_at": None,
    }
    assert me["user"]["plan"] == "free"
    assert commission.status == "void"
    row = store._ledger_keys["refund:lemonsqueezy:ls-order-1"]
    assert row.entry_type == "adjust" and row.amount == -50
    assert row.source == "lemonsqueezy:order:ls-order-1"
    assert row.note == "Refunded at the provider"
    recorded = next(iter(store.purchase_refunds.values()))
    assert recorded.credits_removed == 50 and recorded.commission_voided is True

    # The provider retries the same event: a duplicate, and nothing moves.
    assert client.post(
        "/v1/webhooks/lemonsqueezy", content=refund, headers=sign_lemonsqueezy(refund, secret)
    ).json() == {"status": "duplicate"}
    assert store.get_balance(registered_user).credits == 1
    assert sum(1 for r in store.ledger if r.entry_type == "adjust") == 1

    ledger = client.get("/v1/credits/ledger", headers=auth).json()["entries"]
    assert ledger[0]["entry_type"] == "adjust" and ledger[0]["amount"] == -50


def test_a_subscription_period_refund_ends_the_subscription(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    registered_user: UUID,
    sign_lemonsqueezy: Callable[[bytes, str], dict[str, str]],
    settings: Any,
) -> None:
    """LemonSqueezy refunds a subscription period on its invoice, which is the id the
    purchase was recorded under: the period's credits come back, the subscription is
    cancelled as of now and the profile leaves the plan."""
    secret = settings.lemonsqueezy_webhook_secret.get_secret_value()
    period_end = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    invoice = ls_order(
        registered_user,
        event_id="ls-invoice-1",
        variant_id=SUB_VARIANT,
        event_name="subscription_payment_success",
        total=799,
        renews_at=period_end,
        subscription_id="ls-sub-1",
    )
    assert client.post(
        "/v1/webhooks/lemonsqueezy", content=invoice, headers=sign_lemonsqueezy(invoice, secret)
    ).json() == {"status": "ok"}
    me = client.get("/v1/me", headers=auth).json()
    assert me["balance"]["credits"] == 63 and me["user"]["plan"] == "subscription"
    assert me["balance"]["subscription_renews_at"] is not None

    refunded = ls_order(
        registered_user,
        event_id="ls-invoice-1",
        variant_id=SUB_VARIANT,
        event_name="subscription_payment_refunded",
        total=799,
        renews_at=period_end,
        subscription_id="ls-sub-1",
    )
    assert client.post(
        "/v1/webhooks/lemonsqueezy", content=refunded, headers=sign_lemonsqueezy(refunded, secret)
    ).json() == {"status": "ok"}
    me = client.get("/v1/me", headers=auth).json()
    assert me["balance"]["credits"] == 3 and me["user"]["plan"] == "free"
    assert me["balance"]["subscription_renews_at"] is None
    subscription = store.find_subscription("lemonsqueezy", "ls-sub-1")
    assert subscription is not None and subscription.status == "cancelled"
    assert subscription.cancelled_at is not None
    assert subscription.current_period_end is not None
    assert subscription.current_period_end <= datetime.now(UTC)


def test_a_paddle_chargeback_removes_what_is_left_and_applies_once(
    client: TestClient,
    store: MemoryStore,
    registered_user: UUID,
    sign_paddle: Callable[..., dict[str, str]],
    settings: Any,
) -> None:
    """The adjustment reaches us as ``adjustment.created`` and ``adjustment.updated``
    under different event ids; the purchase is refunded once whatever the delivery."""
    secret = settings.paddle_webhook_secret.get_secret_value()
    sale = paddle_event(registered_user, event_id="evt_txn")
    assert client.post(
        "/v1/webhooks/paddle", content=sale, headers=sign_paddle(sale, secret)
    ).json() == {"status": "ok"}
    store.adjust_credits(registered_user, -40, "test", f"drain:{uuid4()}")
    assert store.get_balance(registered_user).available == 13

    for event_id in ("evt_adj_created", "evt_adj_updated"):
        body = paddle_adjustment(event_id, action="chargeback")
        response = client.post(
            "/v1/webhooks/paddle", content=body, headers=sign_paddle(body, secret)
        )
        assert response.status_code == 200 and response.json() == {"status": "ok"}
    assert store.get_balance(registered_user).model_dump() == {
        "credits": 0,
        "reserved": 0,
        "available": 0,
    }
    refunds = list(store.purchase_refunds.values())
    assert len(refunds) == 1 and refunds[0].credits_removed == 13
    assert refunds[0].reason == "requested_by_customer"
    row = store._ledger_keys["refund:paddle:txn_1"]
    assert row.amount == -13 and row.note == "Refunded at the provider: requested_by_customer"

    # Credits that arrive later are not touched by yet another delivery.
    store.grant_credits(registered_user, 10, "support", f"support:{uuid4()}")
    late = paddle_adjustment("evt_adj_late")
    assert client.post(
        "/v1/webhooks/paddle", content=late, headers=sign_paddle(late, secret)
    ).json() == {"status": "ok"}
    assert store.get_balance(registered_user).credits == 10


def test_a_refund_naming_no_recorded_purchase_is_acknowledged_and_logged(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    registered_user: UUID,
    sign_lemonsqueezy: Callable[[bytes, str], dict[str, str]],
    settings: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A subscription checkout's ``order_refunded`` names an order nothing was granted
    under (the periods live under their invoices): the money moved at the provider, so
    the delivery is acknowledged, said out loud for reconciliation, and no credit moves."""
    secret = settings.lemonsqueezy_webhook_secret.get_secret_value()
    refund = ls_order(registered_user, event_id="ls-order-sub", event_name="order_refunded")
    with caplog.at_level(logging.WARNING, logger="tonamorph.webhooks"):
        response = client.post(
            "/v1/webhooks/lemonsqueezy", content=refund, headers=sign_lemonsqueezy(refund, secret)
        )
    assert response.status_code == 200 and response.json() == {"status": "ok"}
    warning = next(r for r in caplog.records if r.levelno == logging.WARNING)
    assert warning.order_id == "ls-order-sub" and warning.provider == "lemonsqueezy"
    assert client.get("/v1/me", headers=auth).json()["balance"]["credits"] == 3
    assert store.purchase_refunds == {}
    assert store.webhook_events["lemonsqueezy:order_refunded:ls-order-sub"].error is None
