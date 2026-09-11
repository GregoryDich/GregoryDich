"""§4 — LemonSqueezy and Paddle webhooks (raw body first, then HMAC, then parsing).

Both providers land in the same flow: verify the signature over the raw bytes, claim the
event's idempotency key in ``webhook_events`` (an already-processed event answers
``{"status": "duplicate"}``), resolve the buyer and the plan, then record the purchase —
which grants the plan's credits and writes the affiliate commission under that same key,
so a replay can neither double-grant nor double-pay (§12, §13). One sale reaches
``record_purchase`` through exactly one event (``purchase_grants_credits``); the others
only move subscription and plan state. An event whose application fails stays claimable,
so the provider's retry runs it again instead of being answered "duplicate", and a claim
whose holder was killed mid-apply expires after ``WEBHOOK_CLAIM_LEASE_SECONDS``.

The affiliate ``ref`` of a subscription payment is taken from the event, then from the
code the checkout stored on the subscription: a store that does not forward
``custom_data`` onto ``subscription_payment_success`` must not cost the affiliate the
commission (§12).

Subscription renewals grant perishable credits: the grant is issued here with
``expires_at`` = the end of the billing period, under the webhook's idempotency key, so
``record_purchase``'s own grant is a no-op and ``expire_credits()`` clears the remainder
at the period boundary (§13). Credit-pack grants never expire.

Three growth events leave from here (§14): ``Purchase Completed`` for the paying event,
``Subscription Cancelled`` for a cancellation, and ``Refund Issued`` for a provider refund
or chargeback — Paddle ``adjustment.*`` once approved, LemonSqueezy ``order_refunded`` —
which is attributed through the purchase it names and changes no credits here.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import SecretStr

from app.dependencies import get_services
from app.errors import BAD_REQUEST, INVALID_SIGNATURE, NOT_FOUND, ApiException
from app.schemas import PlanKind, WebhookAck
from app.services.factory import Services
from app.services.plans import PlanRecord
from app.services.webhooks import PurchaseProvider, SubscriptionStatus

log = logging.getLogger("tonamorph.webhooks")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

MAX_WEBHOOK_BYTES = 1024 * 1024
PADDLE_TOLERANCE_SECONDS = 300
# LemonSqueezy sends three events for one subscription checkout — order_created (an
# order), subscription_created (the subscription) and subscription_payment_success (an
# invoice) — each with a different data.id. Only one of them may grant credits and pay a
# commission: the order event owns one-off packs, the invoice event owns every
# subscription period, first one included. See ``purchase_grants_credits``.
LEMONSQUEEZY_ORDER_EVENT = "order_created"
LEMONSQUEEZY_INVOICE_EVENT = "subscription_payment_success"
LEMONSQUEEZY_PURCHASE_EVENTS = frozenset({LEMONSQUEEZY_ORDER_EVENT, LEMONSQUEEZY_INVOICE_EVENT})
# Events whose ``data`` is the subscription object itself, so data.id is its provider id.
LEMONSQUEEZY_SUBSCRIPTION_OBJECT_EVENTS = frozenset(
    {"subscription_created", "subscription_cancelled", "subscription_expired"}
)
LEMONSQUEEZY_SUBSCRIPTION_EVENTS = LEMONSQUEEZY_SUBSCRIPTION_OBJECT_EVENTS | {
    LEMONSQUEEZY_INVOICE_EVENT
}
LEMONSQUEEZY_REFUND_EVENT = "order_refunded"
LEMONSQUEEZY_RENEWAL_REASON = "renewal"
PADDLE_PURCHASE_EVENT = "transaction.completed"
PADDLE_ADJUSTMENT_EVENTS = frozenset({"adjustment.created", "adjustment.updated"})
PADDLE_REFUND_ACTIONS = frozenset({"refund", "chargeback"})
PADDLE_APPROVED = "approved"
PADDLE_RENEWAL_ORIGIN = "subscription_recurring"
PADDLE_HANDLED_EVENTS = frozenset(
    {
        PADDLE_PURCHASE_EVENT,
        "subscription.activated",
        "subscription.updated",
        "subscription.canceled",
        *PADDLE_ADJUSTMENT_EVENTS,
    }
)
LEMONSQUEEZY_STATUS: dict[str, SubscriptionStatus] = {
    "on_trial": "trialing",
    "active": "active",
    "past_due": "past_due",
    "paused": "paused",
    "cancelled": "cancelled",
    "expired": "expired",
    "unpaid": "past_due",
}
PADDLE_STATUS: dict[str, SubscriptionStatus] = {
    "trialing": "trialing",
    "active": "active",
    "past_due": "past_due",
    "paused": "paused",
    "canceled": "cancelled",
}
ACTIVE_PLAN_STATUSES = frozenset({"trialing", "active", "past_due", "paused"})


# --- signatures --------------------------------------------------------------------------


def _digests_match(expected: str, provided: str) -> bool:
    """Constant-time comparison over bytes: ``compare_digest`` raises ``TypeError`` on a
    ``str`` holding non-ASCII, and a header is attacker-controlled text."""
    return hmac.compare_digest(
        expected.encode("utf-8"), provided.strip().lower().encode("utf-8")
    )


def _require_secret(secret: str) -> None:
    """An unset provider secret must never be used as an HMAC key: with ``""`` anyone can
    sign their own events, so the endpoint rejects the delivery instead (§4)."""
    if not secret:
        raise ApiException(INVALID_SIGNATURE)


def verify_lemonsqueezy(raw: bytes, header: str | None, secret: str) -> None:
    _require_secret(secret)
    expected = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    if not header or not _digests_match(expected, header):
        raise ApiException(INVALID_SIGNATURE)


def parse_paddle_signature(header: str) -> tuple[int, str]:
    parts = dict(
        item.split("=", 1) for item in header.split(";") if "=" in item and item.count("=") >= 1
    )
    ts, h1 = parts.get("ts"), parts.get("h1")
    if not ts or not h1 or not ts.isdigit():
        raise ApiException(INVALID_SIGNATURE)
    return int(ts), h1


def verify_paddle(raw: bytes, header: str | None, secret: str, *, now: float | None = None) -> None:
    _require_secret(secret)
    if not header:
        raise ApiException(INVALID_SIGNATURE)
    ts, h1 = parse_paddle_signature(header)
    current = now if now is not None else time.time()
    if abs(current - ts) > PADDLE_TOLERANCE_SECONDS:
        raise ApiException(INVALID_SIGNATURE, message="The signature timestamp is out of range.")
    expected = hmac.new(
        secret.encode("utf-8"), f"{ts}:".encode() + raw, hashlib.sha256
    ).hexdigest()
    if not _digests_match(expected, h1):
        raise ApiException(INVALID_SIGNATURE)


# --- payloads ------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RefundInfo:
    """A provider refund or chargeback that was approved: the sale it reverses (its
    provider order id), the money, and the provider's reason. ``reference`` names the
    adjustment itself, so the event created for it and the update to it count once."""

    order_id: str | None
    amount_cents: int
    reason: str | None
    reference: str


@dataclass(frozen=True, slots=True)
class WebhookEvent:
    """One provider event, normalised."""

    provider: PurchaseProvider
    event_type: str
    event_id: str
    order_id: str | None
    variant_id: str | None
    plan_id: str | None
    user_id: UUID | None
    email: str | None
    referral_code: str | None
    amount_cents: int
    net_cents: int
    subscription_id: str | None
    subscription_status: SubscriptionStatus | None
    period_end: datetime | None
    payload: dict[str, Any]
    is_renewal: bool = False
    refund: RefundInfo | None = None

    @property
    def idempotency_key(self) -> str:
        return f"{self.provider}:{self.event_type}:{self.event_id}"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _int(value: Any) -> int:
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def _uuid(value: Any) -> UUID | None:
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _str_or_none(value: Any) -> str | None:
    return str(value) if value not in (None, "") else None


def parse_lemonsqueezy(payload: Mapping[str, Any]) -> WebhookEvent:
    meta = _mapping(payload.get("meta"))
    data = _mapping(payload.get("data"))
    attributes = _mapping(data.get("attributes"))
    custom = _mapping(meta.get("custom_data"))
    event_type = str(meta.get("event_name") or "")
    event_id = _str_or_none(data.get("id"))
    if not event_type or event_id is None:
        raise ApiException(BAD_REQUEST, message="Unrecognised webhook payload.")
    first_item = _mapping(attributes.get("first_order_item"))
    variant_id = _str_or_none(first_item.get("variant_id") or attributes.get("variant_id"))
    total = _int(attributes.get("total"))
    tax = _int(attributes.get("tax"))
    status = LEMONSQUEEZY_STATUS.get(str(attributes.get("status") or ""))
    # A subscription-invoice payload names its subscription in the attributes; only the
    # subscription events carry the subscription itself as ``data``.
    subscription_id = _str_or_none(attributes.get("subscription_id")) or (
        event_id if event_type in LEMONSQUEEZY_SUBSCRIPTION_OBJECT_EVENTS else None
    )
    refund: RefundInfo | None = None
    if event_type == LEMONSQUEEZY_REFUND_EVENT:
        refund = RefundInfo(
            order_id=event_id,
            amount_cents=_int(attributes.get("refunded_amount")) or total,
            reason=None,
            reference=f"lemonsqueezy:order:{event_id}",
        )
    return WebhookEvent(
        provider="lemonsqueezy",
        event_type=event_type,
        event_id=event_id,
        # The sale's identity: the order id, or the invoice id of a subscription period.
        order_id=event_id if event_type in LEMONSQUEEZY_PURCHASE_EVENTS else None,
        variant_id=variant_id,
        plan_id=_str_or_none(custom.get("plan_id")),
        user_id=_uuid(custom.get("user_id")),
        email=_str_or_none(attributes.get("user_email")),
        referral_code=_str_or_none(custom.get("ref")),
        amount_cents=total,
        net_cents=max(total - tax, 0),
        subscription_id=subscription_id,
        subscription_status=status,
        period_end=_timestamp(attributes.get("renews_at") or attributes.get("ends_at")),
        payload=dict(payload),
        is_renewal=str(attributes.get("billing_reason") or "") == LEMONSQUEEZY_RENEWAL_REASON,
        refund=refund,
    )


def parse_paddle(payload: Mapping[str, Any]) -> WebhookEvent:
    data = _mapping(payload.get("data"))
    custom = _mapping(data.get("custom_data"))
    event_type = str(payload.get("event_type") or "")
    event_id = _str_or_none(payload.get("event_id"))
    if not event_type or event_id is None:
        raise ApiException(BAD_REQUEST, message="Unrecognised webhook payload.")
    items = data.get("items")
    price_id: str | None = None
    if isinstance(items, list) and items:
        first = _mapping(items[0])
        price_id = _str_or_none(_mapping(first.get("price")).get("id") or first.get("price_id"))
    totals = _mapping(_mapping(data.get("details")).get("totals"))
    total = _int(totals.get("total"))
    earnings = _int(totals.get("earnings")) or max(total - _int(totals.get("fee")), 0)
    is_transaction = event_type.startswith("transaction.")
    is_adjustment = event_type in PADDLE_ADJUSTMENT_EVENTS
    period = _mapping(data.get("current_billing_period"))
    refund: RefundInfo | None = None
    if (
        is_adjustment
        and str(data.get("status") or "") == PADDLE_APPROVED
        and str(data.get("action") or "") in PADDLE_REFUND_ACTIONS
    ):
        refund = RefundInfo(
            order_id=_str_or_none(data.get("transaction_id")),
            amount_cents=_int(_mapping(data.get("totals")).get("total")),
            reason=_str_or_none(data.get("reason")),
            reference=f"paddle:adjustment:{_str_or_none(data.get('id')) or event_id}",
        )
    if is_adjustment:
        subscription_id: str | None = None
    elif is_transaction:
        subscription_id = _str_or_none(data.get("subscription_id"))
    else:
        subscription_id = _str_or_none(data.get("id"))
    return WebhookEvent(
        provider="paddle",
        event_type=event_type,
        event_id=event_id,
        order_id=_str_or_none(data.get("id")) if is_transaction else None,
        variant_id=price_id,
        plan_id=_str_or_none(custom.get("plan_id")),
        user_id=_uuid(custom.get("user_id")),
        email=_str_or_none(_mapping(data.get("customer")).get("email") or custom.get("email")),
        referral_code=_str_or_none(custom.get("ref")),
        amount_cents=total,
        net_cents=earnings,
        subscription_id=subscription_id,
        subscription_status=(
            None if is_adjustment else PADDLE_STATUS.get(str(data.get("status") or ""))
        ),
        period_end=_timestamp(period.get("ends_at") or data.get("next_billed_at")),
        payload=dict(payload),
        is_renewal=str(data.get("origin") or "") == PADDLE_RENEWAL_ORIGIN,
        refund=refund,
    )


# --- processing ------------------------------------------------------------------------------


def purchase_grants_credits(event: WebhookEvent, plan: PlanRecord) -> bool:
    """Whether this event is the one that pays for ``plan`` — the single event per sale
    that grants credits and writes the affiliate commission (§4, §13).

    Paddle bills every period as its own transaction. LemonSqueezy splits a subscription
    checkout over three events with three different ``data.id`` values, so the plan decides:
    a one-off pack is paid for by its order, a subscription period by its invoice. Every
    other event only updates subscription and plan state.
    """
    if event.order_id is None:
        return False
    if event.provider == "paddle":
        return event.event_type == PADDLE_PURCHASE_EVENT
    return event.event_type == (
        LEMONSQUEEZY_INVOICE_EVENT if plan.interval is not None else LEMONSQUEEZY_ORDER_EVENT
    )


def plan_kind_for(status: SubscriptionStatus, period_end: datetime | None) -> PlanKind:
    """A cancelled subscription keeps its plan until the period ends (§13)."""
    if status in ACTIVE_PLAN_STATUSES:
        return "subscription"
    if status == "cancelled" and period_end is not None and period_end > datetime.now(UTC):
        return "subscription"
    return "free"


async def resolve_user(services: Services, event: WebhookEvent) -> UUID:
    if event.user_id is not None and await services.users.get(event.user_id) is not None:
        return event.user_id
    if event.email:
        user = await services.users.find_by_email(event.email)
        if user is not None:
            return user.id
    if event.refund is not None and event.refund.order_id is not None:
        # A Paddle adjustment names neither the customer's email nor the checkout's
        # custom data, only the transaction it reverses.
        purchase = await services.purchases.find_purchase(event.provider, event.refund.order_id)
        if purchase is not None:
            return purchase.user_id
    raise ApiException(NOT_FOUND, message="No account matches this purchase.")


async def resolve_referral_code(services: Services, event: WebhookEvent) -> str | None:
    """The affiliate code this sale pays a commission on (§12).

    A subscription period is billed by its own event, and a store that does not forward
    the checkout's ``custom_data`` onto ``subscription_payment_success`` sends that event
    without a ``ref``. Taking the event at its word would silently drop the commission of
    every renewal — and of the first payment too — for a sale an affiliate did bring in,
    so the code kept on the subscription by the checkout event that started it is used
    instead.

    When the subscription itself is unknown here, the code cannot be established either
    way; that is logged with the subscription id so an operator can reconcile the sale
    against the provider. A known subscription that carries no code is simply a sale
    without an affiliate and is silent.
    """
    if event.referral_code is not None or event.subscription_id is None:
        return event.referral_code
    subscription = await services.purchases.find_subscription(
        event.provider, event.subscription_id
    )
    if subscription is None:
        log.warning(
            "subscription payment has no referral code and no stored subscription",
            extra={
                "provider": event.provider,
                "event_type": event.event_type,
                "subscription_id": event.subscription_id,
            },
        )
        return None
    if subscription.referral_code is not None:
        log.info(
            "referral code recovered from the stored subscription",
            extra={
                "provider": event.provider,
                "event_type": event.event_type,
                "subscription_id": event.subscription_id,
            },
        )
    return subscription.referral_code


async def resolve_plan(services: Services, event: WebhookEvent) -> PlanRecord:
    if event.variant_id:
        plan = await services.plans.find_by_variant(event.provider, event.variant_id)
        if plan is not None:
            return plan
    if event.plan_id:
        plan = await services.plans.get(event.plan_id)
        if plan is not None:
            return plan
    raise ApiException(NOT_FOUND, message="No plan matches this purchase.")


async def process_event(services: Services, event: WebhookEvent) -> WebhookAck:
    """Claim the event, apply it, then close the claim.

    ``mark_processed`` with an error keeps the row and leaves it claimable, so the
    provider's retry of a delivery that failed halfway re-runs it — a paid event is never
    answered "duplicate" without having been applied. A claim that was never closed at
    all, because the process died between claim and completion, expires after
    ``WEBHOOK_CLAIM_LEASE_SECONDS`` and is taken over by the next retry. Only an event
    that was applied without error is a duplicate.
    """
    if not await services.webhook_events.claim(
        event.idempotency_key, event.provider, event.event_type, event.payload
    ):
        return WebhookAck(status="duplicate")
    try:
        await _apply(services, event)
    except ApiException as exc:
        await services.webhook_events.mark_processed(event.idempotency_key, exc.code)
        raise
    except Exception:
        await services.webhook_events.mark_processed(event.idempotency_key, "internal_error")
        raise
    await services.webhook_events.mark_processed(event.idempotency_key)
    return WebhookAck(status="ok")


async def _apply(services: Services, event: WebhookEvent) -> None:
    user_id = await resolve_user(services, event)
    plan: PlanRecord | None = None
    if event.order_id is not None:
        plan = await resolve_plan(services, event)
    if plan is not None and purchase_grants_credits(event, plan):
        assert event.order_id is not None
        if plan.interval is not None and plan.credits > 0 and event.period_end is not None:
            # Subscription credits expire with the billing period; the grant is issued
            # under the webhook key so record_purchase's own grant is a no-op (§13).
            await services.credits.grant(
                user_id,
                plan.credits,
                f"{event.provider}:order:{event.order_id}",
                event.idempotency_key,
                plan.name,
                event.period_end,
            )
        purchase = await services.purchases.record_purchase(
            user_id=user_id,
            provider=event.provider,
            provider_order_id=event.order_id,
            plan_id=plan.id,
            amount_cents=event.amount_cents,
            net_cents=event.net_cents,
            referral_code=await resolve_referral_code(services, event),
            raw=event.payload,
            idempotency_key=event.idempotency_key,
        )
        services.growth.purchase_completed(
            user_id,
            event.email,
            plan=plan,
            price_usd=event.amount_cents / 100,
            credits=purchase.credits,
            is_renewal=event.is_renewal,
            referral_code=purchase.referral_code,
            unique_id=f"purchase_completed:{event.idempotency_key}",
        )

    if event.subscription_id and event.subscription_status is not None:
        subscription = await services.purchases.upsert_subscription(
            user_id=user_id,
            provider=event.provider,
            provider_subscription_id=event.subscription_id,
            plan_id=plan.id if plan is not None else None,
            status=event.subscription_status,
            current_period_end=event.period_end,
            cancelled_at=(
                datetime.now(UTC) if event.subscription_status == "cancelled" else None
            ),
            # Kept from whichever event of the checkout carries it; an event without one
            # never clears what is stored, so a later renewal can still be attributed.
            referral_code=event.referral_code,
            raw=event.payload,
        )
        await services.users.set_plan(
            user_id,
            plan_kind_for(subscription.status, subscription.current_period_end),
            subscription.current_period_end,
        )
        if event.subscription_status == "cancelled":
            services.growth.subscription_cancelled(
                user_id,
                event.email,
                plan_id=subscription.plan_id,
                period_end=subscription.current_period_end,
                unique_id=f"subscription_cancelled:{event.idempotency_key}",
            )

    if event.refund is not None:
        services.growth.refund_issued(
            user_id,
            event.email,
            amount_usd=event.refund.amount_cents / 100,
            reason=event.refund.reason,
            unique_id=f"refund_issued:{event.refund.reference}",
        )
    log.info(
        "webhook processed",
        extra={
            "provider": event.provider,
            "event_type": event.event_type,
            "user_id": str(user_id),
        },
    )


async def _raw_body(request: Request) -> bytes:
    raw = await request.body()
    if len(raw) > MAX_WEBHOOK_BYTES:
        raise ApiException(BAD_REQUEST, message="The webhook payload is too large.")
    return raw


def _json(raw: bytes) -> Mapping[str, Any]:
    import json

    try:
        payload = json.loads(raw)
    except ValueError as exc:
        raise ApiException(BAD_REQUEST, message="The webhook body is not JSON.") from exc
    if not isinstance(payload, Mapping):
        raise ApiException(BAD_REQUEST, message="The webhook body is not an object.")
    return payload


UNCONFIGURED_PROVIDER_MESSAGE = "This payment provider is not configured."


def configured_secret(secret: SecretStr) -> str:
    """The provider's webhook secret, or ``404 not_found`` when it is unset: a route with
    no secret is not an open door but a provider this deployment does not sell through
    (§4). Nothing is read from the body before this check."""
    value = secret.get_secret_value()
    if not value:
        raise ApiException(NOT_FOUND, message=UNCONFIGURED_PROVIDER_MESSAGE)
    return value


@router.post("/lemonsqueezy", response_model=WebhookAck)
async def lemonsqueezy(
    request: Request, services: Services = Depends(get_services)
) -> WebhookAck:
    secret = configured_secret(services.settings.lemonsqueezy_webhook_secret)
    raw = await _raw_body(request)
    verify_lemonsqueezy(raw, request.headers.get("x-signature"), secret)
    event = parse_lemonsqueezy(_json(raw))
    if (
        event.event_type not in LEMONSQUEEZY_PURCHASE_EVENTS
        and event.event_type not in LEMONSQUEEZY_SUBSCRIPTION_EVENTS
        and event.event_type != LEMONSQUEEZY_REFUND_EVENT
    ):
        return WebhookAck(status="ok")
    return await process_event(services, event)


@router.post("/paddle", response_model=WebhookAck)
async def paddle(request: Request, services: Services = Depends(get_services)) -> WebhookAck:
    secret = configured_secret(services.settings.paddle_webhook_secret)
    raw = await _raw_body(request)
    verify_paddle(raw, request.headers.get("paddle-signature"), secret)
    event = parse_paddle(_json(raw))
    if event.event_type not in PADDLE_HANDLED_EVENTS:
        return WebhookAck(status="ok")
    if event.event_type in PADDLE_ADJUSTMENT_EVENTS and event.refund is None:
        # Pending, rejected or reversed adjustments and credits move nothing here.
        return WebhookAck(status="ok")
    return await process_event(services, event)
