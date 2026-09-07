"""§4 — LemonSqueezy and Paddle webhooks (raw body first, then HMAC, then parsing).

Both providers land in the same flow: verify the signature over the raw bytes, claim the
event's idempotency key in ``webhook_events`` (a duplicate answers ``{"status":
"duplicate"}``), resolve the buyer and the plan, then record the purchase — which grants
the plan's credits and writes the affiliate commission under that same key, so a replay
can neither double-grant nor double-pay (§12, §13).

Subscription renewals grant perishable credits: the grant is issued here with
``expires_at`` = the end of the billing period, under the webhook's idempotency key, so
``record_purchase``'s own grant is a no-op and ``expire_credits()`` clears the remainder
at the period boundary (§13). Credit-pack grants never expire.
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

from app.dependencies import get_services
from app.errors import BAD_REQUEST, INVALID_SIGNATURE, NOT_FOUND, ApiException
from app.schemas import PlanKind, WebhookAck
from app.services.factory import Services
from app.services.plans import PlanRecord
from app.services.webhooks import PurchaseProvider, SubscriptionStatus

log = logging.getLogger("snapplay.webhooks")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

MAX_WEBHOOK_BYTES = 1024 * 1024
PADDLE_TOLERANCE_SECONDS = 300
LEMONSQUEEZY_PURCHASE_EVENTS = frozenset(
    {"order_created", "subscription_created", "subscription_payment_success"}
)
LEMONSQUEEZY_SUBSCRIPTION_EVENTS = frozenset(
    {
        "subscription_created",
        "subscription_payment_success",
        "subscription_cancelled",
        "subscription_expired",
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


def verify_lemonsqueezy(raw: bytes, header: str | None, secret: str) -> None:
    expected = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    if not header or not hmac.compare_digest(expected, header.strip().lower()):
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
    if not header:
        raise ApiException(INVALID_SIGNATURE)
    ts, h1 = parse_paddle_signature(header)
    current = now if now is not None else time.time()
    if abs(current - ts) > PADDLE_TOLERANCE_SECONDS:
        raise ApiException(INVALID_SIGNATURE, message="The signature timestamp is out of range.")
    expected = hmac.new(
        secret.encode("utf-8"), f"{ts}:".encode() + raw, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, h1.strip().lower()):
        raise ApiException(INVALID_SIGNATURE)


# --- payloads ------------------------------------------------------------------------------


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

    @property
    def idempotency_key(self) -> str:
        return f"{self.provider}:{self.event_type}:{self.event_id}"

    @property
    def is_purchase(self) -> bool:
        return self.order_id is not None and (
            self.provider == "lemonsqueezy"
            and self.event_type in LEMONSQUEEZY_PURCHASE_EVENTS
            or self.provider == "paddle"
            and self.event_type == "transaction.completed"
        )


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
    subscription_id = (
        event_id if event_type.startswith("subscription_") else None
    ) or _str_or_none(attributes.get("subscription_id"))
    return WebhookEvent(
        provider="lemonsqueezy",
        event_type=event_type,
        event_id=event_id,
        order_id=event_id,
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
    period = _mapping(data.get("current_billing_period"))
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
        subscription_id=_str_or_none(
            data.get("subscription_id") if is_transaction else data.get("id")
        ),
        subscription_status=PADDLE_STATUS.get(str(data.get("status") or "")),
        period_end=_timestamp(period.get("ends_at") or data.get("next_billed_at")),
        payload=dict(payload),
    )


# --- processing ------------------------------------------------------------------------------


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
    raise ApiException(NOT_FOUND, message="No account matches this purchase.")


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
    if event.is_purchase:
        plan = await resolve_plan(services, event)
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
        await services.purchases.record_purchase(
            user_id=user_id,
            provider=event.provider,
            provider_order_id=event.order_id,
            plan_id=plan.id,
            amount_cents=event.amount_cents,
            net_cents=event.net_cents,
            referral_code=event.referral_code,
            raw=event.payload,
            idempotency_key=event.idempotency_key,
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
        )
        await services.users.set_plan(
            user_id,
            plan_kind_for(subscription.status, subscription.current_period_end),
            subscription.current_period_end,
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


@router.post("/lemonsqueezy", response_model=WebhookAck)
async def lemonsqueezy(
    request: Request, services: Services = Depends(get_services)
) -> WebhookAck:
    raw = await _raw_body(request)
    verify_lemonsqueezy(
        raw,
        request.headers.get("x-signature"),
        services.settings.lemonsqueezy_webhook_secret.get_secret_value(),
    )
    event = parse_lemonsqueezy(_json(raw))
    if (
        event.event_type not in LEMONSQUEEZY_PURCHASE_EVENTS
        and event.event_type not in LEMONSQUEEZY_SUBSCRIPTION_EVENTS
    ):
        return WebhookAck(status="ok")
    return await process_event(services, event)


@router.post("/paddle", response_model=WebhookAck)
async def paddle(request: Request, services: Services = Depends(get_services)) -> WebhookAck:
    raw = await _raw_body(request)
    verify_paddle(
        raw,
        request.headers.get("paddle-signature"),
        services.settings.paddle_webhook_secret.get_secret_value(),
    )
    event = parse_paddle(_json(raw))
    if event.event_type not in (
        "transaction.completed",
        "subscription.activated",
        "subscription.updated",
        "subscription.canceled",
    ):
        return WebhookAck(status="ok")
    return await process_event(services, event)
