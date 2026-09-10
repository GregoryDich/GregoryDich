"""§4 payment webhooks and §12/§13 affiliate and subscription policies."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.services.memory import MemoryStore

pytestmark = pytest.mark.usefixtures("no_rate_limits")

PACK_VARIANT = "ls-variant-pack"
SUB_VARIANT = "ls-variant-sub"
PADDLE_PACK_PRICE = "pri_pack"
PADDLE_SUB_PRICE = "pri_sub"


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


def ls_order(
    user_id: UUID,
    *,
    event_id: str = "ls-order-1",
    variant_id: str = PACK_VARIANT,
    ref: str | None = None,
    total: int = 900,
    tax: int = 0,
    event_name: str = "order_created",
    renews_at: str | None = None,
    subscription_id: str | None = None,
) -> bytes:
    custom: dict[str, Any] = {"user_id": str(user_id)}
    if ref is not None:
        custom["ref"] = ref
    attributes: dict[str, Any] = {
        "user_email": "player@example.test",
        "total": total,
        "tax": tax,
        "status": "active" if event_name.startswith("subscription") else "paid",
        "renews_at": renews_at,
        "first_order_item": {"variant_id": variant_id},
        "variant_id": variant_id,
    }
    if subscription_id is not None:
        attributes["subscription_id"] = subscription_id
    return json.dumps(
        {
            "meta": {"event_name": event_name, "custom_data": custom},
            "data": {"id": event_id, "type": "orders", "attributes": attributes},
        }
    ).encode()


def paddle_event(
    user_id: UUID | None,
    *,
    event_id: str = "evt_1",
    event_type: str = "transaction.completed",
    price_id: str = PADDLE_PACK_PRICE,
    total: int = 900,
    earnings: int = 800,
    email: str | None = None,
    status: str = "active",
    period_end: str | None = None,
    subscription_id: str | None = None,
    ref: str | None = None,
) -> bytes:
    custom: dict[str, Any] = {}
    if user_id is not None:
        custom["user_id"] = str(user_id)
    if ref is not None:
        custom["ref"] = ref
    data: dict[str, Any] = {
        "id": subscription_id or "txn_1",
        "status": status,
        "custom_data": custom,
        "customer": {"email": email} if email else {},
        "items": [{"price": {"id": price_id}}],
        "details": {"totals": {"total": str(total), "earnings": str(earnings), "fee": "100"}},
    }
    if period_end:
        data["current_billing_period"] = {"ends_at": period_end}
    if event_type.startswith("subscription"):
        data["id"] = subscription_id or "sub_1"
    elif subscription_id:
        data["subscription_id"] = subscription_id
    return json.dumps({"event_id": event_id, "event_type": event_type, "data": data}).encode()


def test_lemonsqueezy_order_grants_credits(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    registered_user: UUID,
    sign_lemonsqueezy: Callable[[bytes, str], dict[str, str]],
    settings: Any,
) -> None:
    body = ls_order(registered_user)
    secret = settings.lemonsqueezy_webhook_secret.get_secret_value()
    response = client.post(
        "/v1/webhooks/lemonsqueezy", content=body, headers=sign_lemonsqueezy(body, secret)
    )
    assert response.status_code == 200 and response.json() == {"status": "ok"}

    me = client.get("/v1/me", headers=auth).json()
    assert me["balance"]["credits"] == 53 and me["user"]["plan"] == "credits"
    assert len(store.purchases) == 1


def test_lemonsqueezy_invalid_signature_is_401(
    client: TestClient, store: MemoryStore, registered_user: UUID
) -> None:
    body = ls_order(registered_user)
    response = client.post(
        "/v1/webhooks/lemonsqueezy", content=body, headers={"X-Signature": "00" * 32}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_signature"
    assert store.purchases == {}
    assert client.post("/v1/webhooks/lemonsqueezy", content=body).status_code == 401


def test_duplicate_webhook_grants_exactly_once(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    registered_user: UUID,
    sign_lemonsqueezy: Callable[[bytes, str], dict[str, str]],
    settings: Any,
) -> None:
    body = ls_order(registered_user)
    headers = sign_lemonsqueezy(body, settings.lemonsqueezy_webhook_secret.get_secret_value())
    first = client.post("/v1/webhooks/lemonsqueezy", content=body, headers=headers)
    second = client.post("/v1/webhooks/lemonsqueezy", content=body, headers=headers)
    assert first.json() == {"status": "ok"}
    assert second.status_code == 200 and second.json() == {"status": "duplicate"}
    assert client.get("/v1/me", headers=auth).json()["balance"]["credits"] == 53
    assert len(store.purchases) == 1
    assert sum(1 for row in store.ledger if row.entry_type == "grant") == 2  # signup + pack


def test_user_resolved_by_email_when_custom_data_is_absent(
    client: TestClient,
    store: MemoryStore,
    registered_user: UUID,
    sign_paddle: Callable[..., dict[str, str]],
    settings: Any,
) -> None:
    body = paddle_event(None, email="player@example.test")
    headers = sign_paddle(body, settings.paddle_webhook_secret.get_secret_value())
    response = client.post("/v1/webhooks/paddle", content=body, headers=headers)
    assert response.status_code == 200 and response.json() == {"status": "ok"}
    assert next(iter(store.purchases.values())).user_id == registered_user


def test_paddle_rejects_a_stale_timestamp(
    client: TestClient,
    store: MemoryStore,
    registered_user: UUID,
    sign_paddle: Callable[..., dict[str, str]],
    settings: Any,
) -> None:
    body = paddle_event(registered_user)
    stale = sign_paddle(
        body, settings.paddle_webhook_secret.get_secret_value(), int(time.time()) - 600
    )
    response = client.post("/v1/webhooks/paddle", content=body, headers=stale)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_signature"
    assert store.purchases == {}


def test_paddle_rejects_a_wrong_digest_and_malformed_header(
    client: TestClient, registered_user: UUID, settings: Any
) -> None:
    body = paddle_event(registered_user)
    ts = int(time.time())
    wrong_digest = {"Paddle-Signature": f"ts={ts};h1={'0' * 64}"}
    assert client.post("/v1/webhooks/paddle", content=body, headers=wrong_digest).status_code == 401
    assert (
        client.post(
            "/v1/webhooks/paddle", content=body, headers={"Paddle-Signature": "garbage"}
        ).status_code
        == 401
    )


def test_subscription_renewal_grants_expiring_credits(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    registered_user: UUID,
    sign_lemonsqueezy: Callable[[bytes, str], dict[str, str]],
    settings: Any,
) -> None:
    """§13: subscription credits carry the billing period's end as their expiry."""
    period_end = datetime.now(UTC) + timedelta(days=30)
    body = ls_order(
        registered_user,
        event_id="ls-invoice-1",
        variant_id=SUB_VARIANT,
        event_name="subscription_payment_success",
        total=799,
        renews_at=period_end.isoformat(),
        subscription_id="ls-sub-1",
    )
    headers = sign_lemonsqueezy(body, settings.lemonsqueezy_webhook_secret.get_secret_value())
    assert client.post("/v1/webhooks/lemonsqueezy", content=body, headers=headers).json() == {
        "status": "ok"
    }

    grants = [row for row in store.ledger if row.entry_type == "grant" and row.amount == 60]
    assert len(grants) == 1 and grants[0].expires_at is not None
    assert abs((grants[0].expires_at - period_end).total_seconds()) < 1

    me = client.get("/v1/me", headers=auth).json()
    assert me["user"]["plan"] == "subscription"
    assert me["balance"]["credits"] == 63
    assert me["balance"]["subscription_renews_at"] is not None

    # The cron helper takes the remainder back once the period has passed.
    grants[0].expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert store.expire_credits() == 1
    assert client.get("/v1/me", headers=auth).json()["balance"]["credits"] == 3


def test_pack_credits_never_expire(
    client: TestClient,
    store: MemoryStore,
    registered_user: UUID,
    sign_lemonsqueezy: Callable[[bytes, str], dict[str, str]],
    settings: Any,
) -> None:
    body = ls_order(registered_user)
    headers = sign_lemonsqueezy(body, settings.lemonsqueezy_webhook_secret.get_secret_value())
    client.post("/v1/webhooks/lemonsqueezy", content=body, headers=headers)
    pack_grant = next(row for row in store.ledger if row.amount == 50)
    assert pack_grant.expires_at is None
    assert store.expire_credits() == 0


def test_affiliate_commission_is_written_once_under_replay(
    client: TestClient,
    store: MemoryStore,
    registered_user: UUID,
    sign_lemonsqueezy: Callable[[bytes, str], dict[str, str]],
    settings: Any,
) -> None:
    affiliate_user = uuid4()
    store.ensure_user(affiliate_user, "affiliate@example.test")
    store.add_affiliate(affiliate_user, "FRIEND")

    body = ls_order(registered_user, ref="friend", total=900, tax=100)
    headers = sign_lemonsqueezy(body, settings.lemonsqueezy_webhook_secret.get_secret_value())
    assert client.post("/v1/webhooks/lemonsqueezy", content=body, headers=headers).json() == {
        "status": "ok"
    }
    assert client.post("/v1/webhooks/lemonsqueezy", content=body, headers=headers).json() == {
        "status": "duplicate"
    }

    assert len(store.commissions) == 1
    commission = next(iter(store.commissions.values()))
    assert commission.amount_cents == 240  # 30 % of the 800-cent net
    assert store.referral_codes["friend"].uses == 1


def test_subscription_cancellation_keeps_the_plan_until_the_period_ends(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    registered_user: UUID,
    sign_paddle: Callable[..., dict[str, str]],
    settings: Any,
) -> None:
    secret = settings.paddle_webhook_secret.get_secret_value()
    period_end = (datetime.now(UTC) + timedelta(days=10)).isoformat()
    activated = paddle_event(
        registered_user,
        event_id="evt_sub_active",
        event_type="subscription.activated",
        price_id=PADDLE_SUB_PRICE,
        period_end=period_end,
        subscription_id="sub_42",
    )
    client.post("/v1/webhooks/paddle", content=activated, headers=sign_paddle(activated, secret))
    assert client.get("/v1/me", headers=auth).json()["user"]["plan"] == "subscription"

    cancelled = paddle_event(
        registered_user,
        event_id="evt_sub_cancel",
        event_type="subscription.canceled",
        price_id=PADDLE_SUB_PRICE,
        status="canceled",
        period_end=period_end,
        subscription_id="sub_42",
    )
    client.post("/v1/webhooks/paddle", content=cancelled, headers=sign_paddle(cancelled, secret))
    assert client.get("/v1/me", headers=auth).json()["user"]["plan"] == "subscription"

    expired = paddle_event(
        registered_user,
        event_id="evt_sub_expired",
        event_type="subscription.canceled",
        price_id=PADDLE_SUB_PRICE,
        status="canceled",
        period_end=(datetime.now(UTC) - timedelta(days=1)).isoformat(),
        subscription_id="sub_42",
    )
    client.post("/v1/webhooks/paddle", content=expired, headers=sign_paddle(expired, secret))
    assert client.get("/v1/me", headers=auth).json()["user"]["plan"] == "free"
    assert store.find_subscription("paddle", "sub_42") is not None


def test_unknown_user_is_404_and_unhandled_events_are_acknowledged(
    client: TestClient,
    store: MemoryStore,
    registered_user: UUID,
    sign_lemonsqueezy: Callable[[bytes, str], dict[str, str]],
    settings: Any,
) -> None:
    secret = settings.lemonsqueezy_webhook_secret.get_secret_value()
    orphan = json.dumps(
        {
            "meta": {"event_name": "order_created", "custom_data": {"user_id": str(uuid4())}},
            "data": {
                "id": "ls-orphan",
                "attributes": {"first_order_item": {"variant_id": PACK_VARIANT}},
            },
        }
    ).encode()
    response = client.post(
        "/v1/webhooks/lemonsqueezy", content=orphan, headers=sign_lemonsqueezy(orphan, secret)
    )
    assert response.status_code == 404
    assert store.webhook_events["lemonsqueezy:order_created:ls-orphan"].error == "not_found"

    ignored = json.dumps(
        {"meta": {"event_name": "license_key_created"}, "data": {"id": "lk-1"}}
    ).encode()
    assert client.post(
        "/v1/webhooks/lemonsqueezy", content=ignored, headers=sign_lemonsqueezy(ignored, secret)
    ).json() == {"status": "ok"}
    assert len(store.purchases) == 0


def test_one_lemonsqueezy_sale_grants_and_pays_once_across_its_three_events(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    registered_user: UUID,
    sign_lemonsqueezy: Callable[[bytes, str], dict[str, str]],
    settings: Any,
) -> None:
    """§4: one subscription checkout, three events, three different ``data.id`` values.

    Only the invoice event pays for the period: the order and the subscription event carry
    the same sale under a different id and must not grant credits or pay a commission
    again.
    """
    affiliate_user = uuid4()
    store.ensure_user(affiliate_user, "affiliate@example.test")
    store.add_affiliate(affiliate_user, "FRIEND")
    secret = settings.lemonsqueezy_webhook_secret.get_secret_value()
    period_end = datetime.now(UTC) + timedelta(days=30)
    common = {
        "variant_id": SUB_VARIANT,
        "ref": "friend",
        "total": 900,
        "tax": 100,
        "renews_at": period_end.isoformat(),
        "subscription_id": "ls-sub-9",
    }
    sequence = [
        ls_order(registered_user, event_id="ls-order-9", event_name="order_created", **common),
        ls_order(
            registered_user, event_id="ls-sub-9", event_name="subscription_created", **common
        ),
        ls_order(
            registered_user,
            event_id="ls-invoice-9",
            event_name="subscription_payment_success",
            **common,
        ),
    ]
    for body in sequence:
        response = client.post(
            "/v1/webhooks/lemonsqueezy", content=body, headers=sign_lemonsqueezy(body, secret)
        )
        assert response.status_code == 200 and response.json() == {"status": "ok"}

    assert len(store.purchases) == 1
    assert client.get("/v1/me", headers=auth).json()["balance"]["credits"] == 63
    commissions = list(store.commissions.values())
    assert len(commissions) == 1 and commissions[0].amount_cents == 240
    assert store.referral_codes["friend"].uses == 1
    assert len(store.subscriptions) == 1
    assert store.find_subscription("lemonsqueezy", "ls-sub-9") is not None


def test_renewal_grants_again_for_the_next_period(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    registered_user: UUID,
    sign_lemonsqueezy: Callable[[bytes, str], dict[str, str]],
    settings: Any,
) -> None:
    """Each period is its own invoice, so a renewal grants once more (§13)."""
    secret = settings.lemonsqueezy_webhook_secret.get_secret_value()
    for invoice, days in (("ls-invoice-a", 30), ("ls-invoice-b", 60)):
        body = ls_order(
            registered_user,
            event_id=invoice,
            variant_id=SUB_VARIANT,
            event_name="subscription_payment_success",
            total=799,
            renews_at=(datetime.now(UTC) + timedelta(days=days)).isoformat(),
            subscription_id="ls-sub-renew",
        )
        assert client.post(
            "/v1/webhooks/lemonsqueezy", content=body, headers=sign_lemonsqueezy(body, secret)
        ).json() == {"status": "ok"}

    assert len(store.purchases) == 2
    assert client.get("/v1/me", headers=auth).json()["balance"]["credits"] == 123
    assert len(store.subscriptions) == 1


def test_a_failed_delivery_is_retried_and_credits_exactly_once(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    registered_user: UUID,
    sign_lemonsqueezy: Callable[[bytes, str], dict[str, str]],
    settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§4: an event that failed halfway must not be answered ``duplicate`` on retry — the
    customer has paid, and the provider's retry is the only remaining delivery."""
    body = ls_order(registered_user)
    headers = sign_lemonsqueezy(body, settings.lemonsqueezy_webhook_secret.get_secret_value())
    grant_credits = store.grant_credits
    calls: list[int] = []

    def failing_grant(*args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("ledger unavailable")
        return grant_credits(*args, **kwargs)

    monkeypatch.setattr(store, "grant_credits", failing_grant)
    first = client.post("/v1/webhooks/lemonsqueezy", content=body, headers=headers)
    assert first.status_code == 500
    assert store.purchases == {}
    assert client.get("/v1/me", headers=auth).json()["balance"]["credits"] == 3

    retry = client.post("/v1/webhooks/lemonsqueezy", content=body, headers=headers)
    assert retry.status_code == 200 and retry.json() == {"status": "ok"}
    assert len(store.purchases) == 1
    assert client.get("/v1/me", headers=auth).json()["balance"]["credits"] == 53

    again = client.post("/v1/webhooks/lemonsqueezy", content=body, headers=headers)
    assert again.json() == {"status": "duplicate"}
    assert client.get("/v1/me", headers=auth).json()["balance"]["credits"] == 53


def test_an_unset_webhook_secret_rejects_every_delivery(
    client: TestClient,
    store: MemoryStore,
    registered_user: UUID,
    sign_lemonsqueezy: Callable[[bytes, str], dict[str, str]],
    sign_paddle: Callable[..., dict[str, str]],
    settings: Any,
) -> None:
    """An empty secret must not be used as an HMAC key: anyone could sign their own
    events and grant themselves credits. A provider without a secret is one this
    deployment does not sell through, so its route is ``404`` and reads nothing (§4)."""
    settings.lemonsqueezy_webhook_secret = SecretStr("")
    settings.paddle_webhook_secret = SecretStr("")
    body = ls_order(registered_user)
    forged = client.post(
        "/v1/webhooks/lemonsqueezy", content=body, headers=sign_lemonsqueezy(body, "")
    )
    assert forged.status_code == 404
    assert forged.json()["error"]["code"] == "not_found"

    paddle_body = paddle_event(registered_user)
    assert (
        client.post(
            "/v1/webhooks/paddle", content=paddle_body, headers=sign_paddle(paddle_body, "")
        ).status_code
        == 404
    )
    assert store.purchases == {} and store.webhook_events == {}


def test_a_non_ascii_signature_header_is_401(
    client: TestClient, store: MemoryStore, registered_user: UUID
) -> None:
    """``hmac.compare_digest`` raises ``TypeError`` on non-ASCII ``str``; a header is
    attacker-controlled text and must never reach a 500."""
    body = ls_order(registered_user)
    # Sent as raw bytes, the way a client can: the header reaches the app as text.
    response = client.post(
        "/v1/webhooks/lemonsqueezy", content=body, headers={b"X-Signature": "é".encode()}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_signature"

    paddle_body = paddle_event(registered_user)
    stamped = client.post(
        "/v1/webhooks/paddle",
        content=paddle_body,
        headers={b"Paddle-Signature": f"ts={int(time.time())};h1=é".encode()},
    )
    assert stamped.status_code == 401
    assert stamped.json()["error"]["code"] == "invalid_signature"
    assert store.purchases == {}


def test_a_claim_stranded_by_a_hard_kill_is_reclaimed_after_the_lease(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    registered_user: UUID,
    sign_lemonsqueezy: Callable[[bytes, str], dict[str, str]],
    settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§4: a process killed between claiming an event and closing the claim (OOM, SIGKILL,
    eviction) leaves a row with neither ``processed_at`` nor ``error``. Answering the
    provider's retry ``duplicate`` for such a row loses a sale that was paid for and never
    applied, so a claim older than the lease is reclaimable — but not one inside it."""
    body = ls_order(registered_user)
    headers = sign_lemonsqueezy(body, settings.lemonsqueezy_webhook_secret.get_secret_value())
    key = "lemonsqueezy:order_created:ls-order-1"

    def killed(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("process killed mid-apply")

    # The kill is simulated by its effect on the row: the apply never finishes and the
    # claim is never closed either way.
    monkeypatch.setattr(store, "mark_webhook_processed", lambda *a, **k: None)
    monkeypatch.setattr(store, "record_purchase", killed)
    killed_delivery = client.post("/v1/webhooks/lemonsqueezy", content=body, headers=headers)
    assert killed_delivery.status_code == 500
    monkeypatch.undo()
    claim = store.webhook_events[key]
    assert claim.processed_at is None and claim.error is None
    assert store.purchases == {}

    # Inside the lease the claim stands: a delivery still being applied is not stranded.
    assert client.post("/v1/webhooks/lemonsqueezy", content=body, headers=headers).json() == {
        "status": "duplicate"
    }
    assert store.purchases == {}
    assert client.get("/v1/me", headers=auth).json()["balance"]["credits"] == 3

    claim.received_at -= timedelta(seconds=settings.webhook_claim_lease_seconds + 1)
    assert client.post("/v1/webhooks/lemonsqueezy", content=body, headers=headers).json() == {
        "status": "ok"
    }
    assert len(store.purchases) == 1
    assert client.get("/v1/me", headers=auth).json()["balance"]["credits"] == 53

    # And exactly once: the reclaim closed the claim, so the next retry is a duplicate.
    assert client.post("/v1/webhooks/lemonsqueezy", content=body, headers=headers).json() == {
        "status": "duplicate"
    }
    assert len(store.purchases) == 1
    assert client.get("/v1/me", headers=auth).json()["balance"]["credits"] == 53


def test_two_workers_cannot_both_reclaim_the_same_stale_event(
    client: TestClient,
    store: MemoryStore,
    registered_user: UUID,
    sign_lemonsqueezy: Callable[[bytes, str], dict[str, str]],
    settings: Any,
) -> None:
    """The reclaim re-stamps the claim, so the second caller finds it inside the lease.
    In SQL that decision is taken under ``for update``; here nothing awaits in between."""
    body = ls_order(registered_user)
    headers = sign_lemonsqueezy(body, settings.lemonsqueezy_webhook_secret.get_secret_value())
    client.post("/v1/webhooks/lemonsqueezy", content=body, headers=headers)
    claim = store.webhook_events["lemonsqueezy:order_created:ls-order-1"]
    claim.processed_at = None
    claim.received_at -= timedelta(seconds=settings.webhook_claim_lease_seconds + 1)

    def reclaim() -> bool:
        return store.claim_webhook_event(
            claim.idempotency_key, "lemonsqueezy", "order_created", {"meta": {}, "data": {}}
        )

    assert (reclaim(), reclaim()) == (True, False)


def test_a_subscription_payment_without_custom_data_keeps_the_commission(
    client: TestClient,
    store: MemoryStore,
    registered_user: UUID,
    sign_lemonsqueezy: Callable[[bytes, str], dict[str, str]],
    settings: Any,
) -> None:
    """§12: a store that does not forward the checkout's ``custom_data`` onto
    ``subscription_payment_success`` sends the paying event without a ``ref``. The code
    the checkout stored on the subscription pays the affiliate instead of being dropped."""
    affiliate_user = uuid4()
    store.ensure_user(affiliate_user, "affiliate@example.test")
    store.add_affiliate(affiliate_user, "FRIEND")
    secret = settings.lemonsqueezy_webhook_secret.get_secret_value()
    period_end = (datetime.now(UTC) + timedelta(days=30)).isoformat()

    created = ls_order(
        registered_user,
        event_id="ls-sub-nc",
        variant_id=SUB_VARIANT,
        event_name="subscription_created",
        ref="friend",
        renews_at=period_end,
        subscription_id="ls-sub-nc",
    )
    assert client.post(
        "/v1/webhooks/lemonsqueezy", content=created, headers=sign_lemonsqueezy(created, secret)
    ).json() == {"status": "ok"}
    assert store.find_subscription("lemonsqueezy", "ls-sub-nc").referral_code == "friend"

    invoice = ls_order(
        registered_user,
        event_id="ls-invoice-nc",
        variant_id=SUB_VARIANT,
        event_name="subscription_payment_success",
        total=900,
        tax=100,
        renews_at=period_end,
        subscription_id="ls-sub-nc",
    )
    assert client.post(
        "/v1/webhooks/lemonsqueezy", content=invoice, headers=sign_lemonsqueezy(invoice, secret)
    ).json() == {"status": "ok"}

    assert next(iter(store.purchases.values())).referral_code == "friend"
    commissions = list(store.commissions.values())
    assert len(commissions) == 1 and commissions[0].amount_cents == 240
    assert store.referral_codes["friend"].uses == 1


def test_an_unattributable_subscription_payment_is_logged_with_its_subscription_id(
    client: TestClient,
    store: MemoryStore,
    registered_user: UUID,
    sign_lemonsqueezy: Callable[[bytes, str], dict[str, str]],
    settings: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When neither the event nor a stored subscription carries the code, the sale is
    attributed to nobody — and that is said out loud, with the subscription id, so an
    operator can reconcile it against the provider (§12)."""
    secret = settings.lemonsqueezy_webhook_secret.get_secret_value()
    invoice = ls_order(
        registered_user,
        event_id="ls-invoice-orphan",
        variant_id=SUB_VARIANT,
        event_name="subscription_payment_success",
        total=900,
        tax=100,
        renews_at=(datetime.now(UTC) + timedelta(days=30)).isoformat(),
        subscription_id="ls-sub-orphan",
    )
    with caplog.at_level(logging.WARNING, logger="snapplay.webhooks"):
        assert client.post(
            "/v1/webhooks/lemonsqueezy", content=invoice, headers=sign_lemonsqueezy(invoice, secret)
        ).json() == {"status": "ok"}

    warning = next(r for r in caplog.records if r.levelno == logging.WARNING)
    assert warning.subscription_id == "ls-sub-orphan"
    assert warning.provider == "lemonsqueezy"
    assert len(store.purchases) == 1 and store.commissions == {}


def test_a_provider_without_a_secret_is_404_while_the_other_keeps_selling(
    client: TestClient,
    store: MemoryStore,
    registered_user: UUID,
    sign_lemonsqueezy: Callable[[bytes, str], dict[str, str]],
    sign_paddle: Callable[..., dict[str, str]],
    settings: Any,
) -> None:
    """One configured provider is enough to sell through (§4): the other's route is a
    closed door, not one that verifies against an empty key."""
    settings.paddle_webhook_secret = SecretStr("")
    paddle_body = paddle_event(registered_user)
    closed = client.post(
        "/v1/webhooks/paddle", content=paddle_body, headers=sign_paddle(paddle_body, "")
    )
    assert closed.status_code == 404 and closed.json()["error"]["code"] == "not_found"

    body = ls_order(registered_user)
    secret = settings.lemonsqueezy_webhook_secret.get_secret_value()
    accepted = client.post(
        "/v1/webhooks/lemonsqueezy", content=body, headers=sign_lemonsqueezy(body, secret)
    )
    assert accepted.status_code == 200 and accepted.json() == {"status": "ok"}
    assert len(store.purchases) == 1
