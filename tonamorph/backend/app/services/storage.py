"""Supabase Storage backend for job objects (§2); S3 lives in ``app.services.aws``."""

from __future__ import annotations

from app.services.supabase import SupabaseClient


class SupabaseStorageService:
    def __init__(self, client: SupabaseClient, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    async def upload_bytes(self, path: str, data: bytes, content_type: str) -> str:
        return await self._client.storage_upload(self._bucket, path, data, content_type)

    async def download_bytes(self, path: str) -> bytes:
        return await self._client.storage_download(self._bucket, path)

    async def signed_url(self, path: str, ttl_seconds: int) -> str:
        return await self._client.storage_signed_url(self._bucket, path, ttl_seconds)


__all__ = ["SupabaseStorageService"]
