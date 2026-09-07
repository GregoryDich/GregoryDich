"""Webhook idempotency ledger, purchases and subscriptions (§4, §12)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel

from app.services.supabase import SupabaseClient

PurchaseProvider = Literal["lemonsqueezy", "paddle"]
SubscriptionStatus = Literal["trialing", "active", "past_due", "paused", "cancelled", "expired"]


class PurchaseRecord(BaseModel):
    id: UUID
    user_id: UUID
    provider: PurchaseProvider
    provider_order_id: str
    plan_id: str | None = None
    credits: int
    amount_cents: int
    net_cents: int
    currency: str = "USD"
    referral_code: str | None = None
    idempotency_key: str
    created_at: datetime


class SubscriptionRecord(BaseModel):
    id: UUID
    user_id: UUID
    provider: PurchaseProvider
    provider_subscription_id: str
    plan_id: str | None = None
    status: SubscriptionStatus
    current_period_end: datetime | None = None
    cancelled_at: datetime | None = None


class PurchasesService(Protocol):
    """``record_purchase`` (purchase + grant + affiliate commission under one idempotency
    key) and the ``subscriptions`` table."""

    async def record_purchase(
        self,
        *,
        user_id: UUID,
        provider: PurchaseProvider,
        provider_order_id: str,
        plan_id: str,
        amount_cents: int,
        net_cents: int,
        referral_code: str | None,
        raw: dict[str, Any],
        idempotency_key: str,
    ) -> PurchaseRecord: ...

    async def upsert_subscription(
        self,
        *,
        user_id: UUID,
        provider: PurchaseProvider,
        provider_subscription_id: str,
        plan_id: str | None,
        status: SubscriptionStatus,
        current_period_end: datetime | None,
        cancelled_at: datetime | None,
        raw: dict[str, Any],
    ) -> SubscriptionRecord: ...

    async def find_subscription(
        self, provider: PurchaseProvider, provider_subscription_id: str
    ) -> SubscriptionRecord | None: ...


class SupabaseWebhookEventsService:
    """The ``webhook_events`` claim: an event is applied at most once, but a delivery that
    failed halfway can be retried.

    ``claim`` inserts the row; a row that already exists is a duplicate *unless* it carries
    an error, in which case the conditional update below re-takes it (one statement, so two
    concurrent retries cannot both win). Without that, a provider retry of a failed
    delivery would be answered ``duplicate`` and the paid event would be lost (§4).
    """

    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    async def claim(
        self, idempotency_key: str, provider: str, event_type: str, payload: dict[str, Any]
    ) -> bool:
        rows = await self._client.insert(
            "webhook_events",
            {
                "provider": provider,
                "event_name": event_type,
                "idempotency_key": idempotency_key,
                "payload": payload,
            },
            on_conflict="idempotency_key",
            resolution="ignore-duplicates",
        )
        if rows:
            return True
        retaken = await self._client.update(
            "webhook_events",
            {
                "provider": provider,
                "event_name": event_type,
                "payload": payload,
                "received_at": datetime.now(UTC).isoformat(),
                "processed_at": None,
                "error": None,
            },
            filters=[("idempotency_key", "eq", idempotency_key), ("error", "not.is", None)],
        )
        return bool(retaken)

    async def mark_processed(self, idempotency_key: str, error: str | None = None) -> None:
        await self._client.update(
            "webhook_events",
            {"processed_at": datetime.now(UTC).isoformat(), "error": error},
            filters=[("idempotency_key", "eq", idempotency_key)],
        )


class SupabasePurchasesService:
    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    async def record_purchase(
        self,
        *,
        user_id: UUID,
        provider: PurchaseProvider,
        provider_order_id: str,
        plan_id: str,
        amount_cents: int,
        net_cents: int,
        referral_code: str | None,
        raw: dict[str, Any],
        idempotency_key: str,
    ) -> PurchaseRecord:
        row = await self._client.rpc(
            "record_purchase",
            {
                "p_user_id": str(user_id),
                "p_provider": provider,
                "p_provider_order_id": provider_order_id,
                "p_plan_id": plan_id,
                "p_amount_cents": amount_cents,
                "p_net_cents": net_cents,
                "p_referral_code": referral_code,
                "p_raw": raw,
                "p_idempotency_key": idempotency_key,
            },
        )
        return PurchaseRecord.model_validate(row)

    async def upsert_subscription(
        self,
        *,
        user_id: UUID,
        provider: PurchaseProvider,
        provider_subscription_id: str,
        plan_id: str | None,
        status: SubscriptionStatus,
        current_period_end: datetime | None,
        cancelled_at: datetime | None,
        raw: dict[str, Any],
    ) -> SubscriptionRecord:
        rows = await self._client.upsert(
            "subscriptions",
            {
                "user_id": str(user_id),
                "provider": provider,
                "provider_subscription_id": provider_subscription_id,
                "plan_id": plan_id,
                "status": status,
                "current_period_end": (
                    current_period_end.isoformat() if current_period_end else None
                ),
                "cancelled_at": cancelled_at.isoformat() if cancelled_at else None,
                "raw": raw,
            },
            on_conflict="provider_subscription_id",
        )
        return SubscriptionRecord.model_validate(rows[0])

    async def find_subscription(
        self, provider: PurchaseProvider, provider_subscription_id: str
    ) -> SubscriptionRecord | None:
        rows = await self._client.select(
            "subscriptions",
            filters=[
                ("provider", "eq", provider),
                ("provider_subscription_id", "eq", provider_subscription_id),
            ],
            limit=1,
        )
        return SubscriptionRecord.model_validate(rows[0]) if rows else None


__all__ = [
    "PurchaseProvider",
    "PurchaseRecord",
    "PurchasesService",
    "SubscriptionRecord",
    "SubscriptionStatus",
    "SupabasePurchasesService",
    "SupabaseWebhookEventsService",
]
