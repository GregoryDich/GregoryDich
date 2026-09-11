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
    referral_code: str | None = None
    """The affiliate code of the checkout that started this subscription, kept so a
    renewal whose ``custom_data`` lost it can still be attributed (§12)."""


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
        referral_code: str | None,
        raw: dict[str, Any],
    ) -> SubscriptionRecord: ...

    async def find_subscription(
        self, provider: PurchaseProvider, provider_subscription_id: str
    ) -> SubscriptionRecord | None: ...

    async def find_purchase(
        self, provider: PurchaseProvider, provider_order_id: str
    ) -> PurchaseRecord | None:
        """The sale a provider refund or chargeback names (§4 ``Refund Issued``)."""
        ...


class SupabaseWebhookEventsService:
    """The ``webhook_events`` claim: an event is applied at most once, but a delivery that
    failed halfway — or whose holder died — can be retried.

    ``claim`` is the ``claim_webhook_event`` function of ``db/migrations/0002_functions.sql``
    and nothing else: insert, and on conflict take the existing row ``for update`` and
    decide under that lock. A row that already exists is a duplicate *unless*

    * it carries an error — this delivery is the retry that has to run it. Without that, a
      provider retry of a failed delivery would be answered ``duplicate`` and the paid
      event would be lost (§4). Two retries of the same failed event may therefore run at
      once; what makes that safe is that every mutation underneath is keyed by the same
      idempotency key, so the second one grants and pays nothing.
    * it was claimed longer than ``lease_seconds`` ago and never closed at all — the
      process holding it was killed mid-apply. The reclaim re-stamps ``received_at`` while
      holding the row lock, so of two workers reclaiming the same stale event exactly one
      wins and the other sees a claim inside its lease.
    """

    def __init__(self, client: SupabaseClient, lease_seconds: int) -> None:
        self._client = client
        self._lease_seconds = lease_seconds

    async def claim(
        self, idempotency_key: str, provider: str, event_type: str, payload: dict[str, Any]
    ) -> bool:
        claimed = await self._client.rpc(
            "claim_webhook_event",
            {
                "p_idempotency_key": idempotency_key,
                "p_provider": provider,
                "p_event_name": event_type,
                "p_payload": payload,
                "p_lease_seconds": self._lease_seconds,
            },
        )
        return bool(claimed)

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
        referral_code: str | None,
        raw: dict[str, Any],
    ) -> SubscriptionRecord:
        row: dict[str, Any] = {
            "user_id": str(user_id),
            "provider": provider,
            "provider_subscription_id": provider_subscription_id,
            "plan_id": plan_id,
            "status": status,
            "current_period_end": (current_period_end.isoformat() if current_period_end else None),
            "cancelled_at": cancelled_at.isoformat() if cancelled_at else None,
            "raw": raw,
        }
        # PostgREST builds the upsert's column list from the keys present, so leaving
        # referral_code out of an event that carries none keeps the code the checkout
        # event stored instead of overwriting it with null (§12).
        if referral_code is not None:
            row["referral_code"] = referral_code
        rows = await self._client.upsert(
            "subscriptions", row, on_conflict="provider_subscription_id"
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

    async def find_purchase(
        self, provider: PurchaseProvider, provider_order_id: str
    ) -> PurchaseRecord | None:
        rows = await self._client.select(
            "purchases",
            filters=[
                ("provider", "eq", provider),
                ("provider_order_id", "eq", provider_order_id),
            ],
            limit=1,
        )
        return PurchaseRecord.model_validate(rows[0]) if rows else None


__all__ = [
    "PurchaseProvider",
    "PurchaseRecord",
    "PurchasesService",
    "SubscriptionRecord",
    "SubscriptionStatus",
    "SupabasePurchasesService",
    "SupabaseWebhookEventsService",
]
