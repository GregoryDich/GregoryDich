"""``api_keys`` rows over PostgREST (§11); hashing lives in ``app.auth.api_keys``."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.auth.api_keys import hash_api_key, is_well_formed
from app.errors import INTERNAL_ERROR, ApiException
from app.schemas import ApiKeyCreateResponse
from app.services.supabase import SupabaseClient


class SupabaseApiKeysService:
    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    async def create(self, user_id: UUID, name: str) -> ApiKeyCreateResponse:
        rows = await self._client.rpc(
            "create_api_key", {"p_user_id": str(user_id), "p_name": name}
        )
        if not isinstance(rows, list) or not rows:
            raise ApiException(INTERNAL_ERROR, message="API key could not be created.")
        row = rows[0]
        return ApiKeyCreateResponse(
            id=row["id"],
            name=name,
            prefix=row["prefix"],
            key=row["plaintext"],
            created_at=datetime.now(UTC),
        )

    async def revoke(self, user_id: UUID, key_id: UUID) -> bool:
        revoked = await self._client.rpc(
            "revoke_api_key", {"p_key_id": str(key_id), "p_user_id": str(user_id)}
        )
        return bool(revoked)

    async def resolve(self, plaintext: str) -> UUID | None:
        if not is_well_formed(plaintext):
            return None
        owner = await self._client.rpc(
            "authenticate_api_key", {"p_key_hash": hash_api_key(plaintext)}
        )
        return UUID(str(owner)) if owner else None


__all__ = ["SupabaseApiKeysService"]
