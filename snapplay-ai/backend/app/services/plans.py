"""Plans (§3): the ``plans`` table and per-caller checkout URLs."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.schemas import PlanInfo, PlanInterval
from app.services.supabase import SupabaseClient

CHECKOUT_PROVIDERS: tuple[str, ...] = ("lemonsqueezy", "paddle")


class PlanRecord(BaseModel):
    """A ``plans`` row; ``provider_variant_ids`` maps provider → variant / price id."""

    id: str
    name: str
    credits: int
    price_cents: int
    currency: str = "USD"
    interval: PlanInterval | None = None
    provider_variant_ids: dict[str, str] = {}
    checkout_url_template: str | None = None
    active: bool = True
    sort_order: int = 0

    @field_validator("provider_variant_ids", mode="before")
    @classmethod
    def _stringify(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): str(v) for k, v in value.items() if v is not None}
        return value or {}

    def variant_id(self, provider: str) -> str | None:
        return self.provider_variant_ids.get(provider)

    def to_plan_info(self, checkout_url: str | None) -> PlanInfo:
        return PlanInfo(
            id=self.id,
            name=self.name,
            credits=self.credits,
            price_usd=self.price_cents / 100,
            interval=self.interval,
            checkout_url=checkout_url,
        )


class PlansService(Protocol):
    async def list_active(self) -> list[PlanRecord]: ...

    async def get(self, plan_id: str) -> PlanRecord | None: ...

    async def find_by_variant(self, provider: str, variant_id: str) -> PlanRecord | None:
        """The plan whose ``provider_variant_ids[provider]`` equals ``variant_id``."""
        ...


def build_checkout_url(plan: PlanRecord, user_id: UUID | None, ref: str | None) -> str | None:
    """Fill ``{variant_id}``, ``{user_id}`` and ``{ref}`` in the plan's template and drop
    query parameters left empty (an anonymous caller gets no ``user_id`` parameter, §3).
    ``None`` when the plan has no template or needs a variant id that is not configured."""
    template = plan.checkout_url_template
    if not template:
        return None
    variant = next((plan.variant_id(p) for p in CHECKOUT_PROVIDERS if plan.variant_id(p)), None)
    if "{variant_id}" in template and not variant:
        return None
    url = (
        template.replace("{variant_id}", variant or "")
        .replace("{user_id}", str(user_id) if user_id else "")
        .replace("{ref}", ref or "")
    )
    base, _, query = url.partition("?")
    kept = [pair for pair in query.split("&") if pair and pair.partition("=")[2] != ""]
    return f"{base}?{'&'.join(kept)}" if kept else base


class SupabasePlansService:
    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    async def list_active(self) -> list[PlanRecord]:
        rows = await self._client.select(
            "plans", filters=[("active", "eq", True)], order="sort_order.asc"
        )
        return [PlanRecord.model_validate(row) for row in rows]

    async def get(self, plan_id: str) -> PlanRecord | None:
        rows = await self._client.select("plans", filters=[("id", "eq", plan_id)], limit=1)
        return PlanRecord.model_validate(rows[0]) if rows else None

    async def find_by_variant(self, provider: str, variant_id: str) -> PlanRecord | None:
        for plan in await self.list_active():
            if plan.variant_id(provider) == variant_id:
                return plan
        return None


__all__ = [
    "CHECKOUT_PROVIDERS",
    "PlanRecord",
    "PlansService",
    "SupabasePlansService",
    "build_checkout_url",
]
