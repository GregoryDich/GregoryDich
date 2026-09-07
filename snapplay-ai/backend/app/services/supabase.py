"""Async Supabase client over httpx: PostgREST, Storage and GoTrue (§1, §2, §6).

Every data-plane call uses the service-role key (RLS is bypassed, so callers scope rows
themselves); the GoTrue proxy uses the anon key. Filters are built from
``(column, operator, value)`` triples into query parameters — user input is never
interpolated into a filter string — and PostgREST error payloads are mapped from their
SQLSTATE to :class:`app.errors.ApiException`. Transport failures and 5xx responses are
retried with exponential backoff.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx

from app.config import Settings
from app.errors import (
    CONFLICT,
    INSUFFICIENT_CREDITS,
    INTERNAL_ERROR,
    NOT_FOUND,
    UNAUTHORIZED,
    VALIDATION_ERROR,
    ApiException,
)

log = logging.getLogger("snapplay.supabase")

Filter = tuple[str, str, Any]
"""``(column, operator, value)``; ``operator`` is a PostgREST operator such as ``eq``."""

# SQLSTATE → (§5 error code, HTTP status). 42501 (forbidden) has no §5 code of its own.
SQLSTATE_ERRORS: dict[str, tuple[str, int]] = {
    "P0402": (INSUFFICIENT_CREDITS, 402),
    "P0404": (NOT_FOUND, 404),
    "P0409": (CONFLICT, 409),
    "42501": (UNAUTHORIZED, 403),
    "22023": (VALIDATION_ERROR, 422),
    "23505": (CONFLICT, 409),
}
RETRY_STATUSES = frozenset({500, 502, 503, 504})
_LIST_RESERVED = ',.:()"\\ '


def _encode_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _quote_list_item(value: Any) -> str:
    text = _encode_value(value)
    if any(ch in text for ch in _LIST_RESERVED):
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def encode_filters(filters: Iterable[Filter]) -> dict[str, str]:
    """PostgREST query parameters for ``filters``. Single-value operators take the
    remainder of the parameter verbatim, so values need no quoting there; ``in`` lists
    quote items containing reserved characters."""
    params: dict[str, str] = {}
    for column, operator, value in filters:
        if operator == "in":
            items = ",".join(_quote_list_item(item) for item in value)
            params[column] = f"in.({items})"
        else:
            params[column] = f"{operator}.{_encode_value(value)}"
    return params


def _parse_detail(detail: Any) -> dict[str, Any] | None:
    """``"available=0 requested=1"`` → ``{"available": 0, "requested": 1}``."""
    if not isinstance(detail, str) or not detail:
        return None
    parsed: dict[str, Any] = {}
    for token in detail.split():
        key, sep, raw = token.partition("=")
        if not sep or not key:
            return {"detail": detail}
        parsed[key] = int(raw) if raw.lstrip("-").isdigit() else raw
    return parsed


def postgrest_error(status: int, payload: Any) -> ApiException:
    """Map a PostgREST / PostgreSQL error response to the §5 envelope."""
    body: Mapping[str, Any] = payload if isinstance(payload, Mapping) else {}
    sqlstate = str(body.get("code") or "")
    mapped = SQLSTATE_ERRORS.get(sqlstate)
    if mapped is None:
        log.error(
            "unmapped postgrest error", extra={"status": status, "sqlstate": sqlstate or None}
        )
        return ApiException(INTERNAL_ERROR, message="Database request failed.")
    code, http_status = mapped
    details = _parse_detail(body.get("details"))
    message: str | None = None
    if code == INSUFFICIENT_CREDITS and details and isinstance(details.get("available"), int):
        message = f"You have {details['available']} credits."
    elif isinstance(body.get("message"), str) and body["message"] not in (code, ""):
        message = body["message"]
    return ApiException(code, http_status, message, details)


class SupabaseClient:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        max_attempts: int = 3,
        backoff_seconds: float = 0.2,
        timeout_seconds: float = 15.0,
    ) -> None:
        if not settings.supabase_url:
            raise ValueError("SUPABASE_URL is required for the Supabase client")
        self.base_url = settings.supabase_url.rstrip("/")
        service_key = settings.supabase_service_role_key.get_secret_value()
        self._service_headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}
        self._anon_headers = {"apikey": settings.supabase_anon_key}
        self._max_attempts = max(1, max_attempts)
        self._backoff = backoff_seconds
        self._http = httpx.AsyncClient(
            base_url=self.base_url, timeout=timeout_seconds, transport=transport
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    # --- transport ----------------------------------------------------------------------

    async def _send(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, str] | None = None,
        json: Any = None,
        content: bytes | None = None,
    ) -> httpx.Response:
        response: httpx.Response | None = None
        for attempt in range(self._max_attempts):
            if attempt:
                await asyncio.sleep(self._backoff * 2 ** (attempt - 1))
            try:
                response = await self._http.request(
                    method, path, headers=dict(headers), params=params, json=json, content=content
                )
            except httpx.TransportError as exc:
                log.warning(
                    "supabase request failed",
                    extra={"method": method, "path": path, "attempt": attempt + 1},
                    exc_info=exc,
                )
                if attempt + 1 == self._max_attempts:
                    raise ApiException(INTERNAL_ERROR, message="Database unavailable.") from exc
                continue
            if response.status_code not in RETRY_STATUSES:
                return response
        assert response is not None
        return response

    @staticmethod
    def _payload(response: httpx.Response) -> Any:
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return None

    def _check(self, response: httpx.Response) -> Any:
        payload = self._payload(response)
        if response.is_success:
            return payload
        if response.status_code >= 500:
            log.error("supabase server error", extra={"status": response.status_code})
            raise ApiException(INTERNAL_ERROR, message="Database unavailable.")
        raise postgrest_error(response.status_code, payload)

    # --- PostgREST --------------------------------------------------------------------------

    async def rpc(self, name: str, params: Mapping[str, Any]) -> Any:
        """``POST /rest/v1/rpc/<name>``; ``params`` are the SQL function's named arguments."""
        response = await self._send(
            "POST",
            f"/rest/v1/rpc/{quote(name, safe='')}",
            headers={**self._service_headers, "Content-Type": "application/json"},
            json=dict(params),
        )
        return self._check(response)

    async def select(
        self,
        table: str,
        *,
        filters: Sequence[Filter] = (),
        columns: str = "*",
        order: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        params = {"select": columns, **encode_filters(filters)}
        if order:
            params["order"] = order
        if limit is not None:
            params["limit"] = str(limit)
        response = await self._send(
            "GET", f"/rest/v1/{quote(table, safe='')}", headers=self._service_headers, params=params
        )
        rows = self._check(response)
        return list(rows) if isinstance(rows, list) else []

    async def insert(
        self,
        table: str,
        rows: Mapping[str, Any] | Sequence[Mapping[str, Any]],
        *,
        on_conflict: str | None = None,
        resolution: str | None = None,
    ) -> list[dict[str, Any]]:
        """Insert and return the stored rows. ``resolution`` is ``ignore-duplicates`` or
        ``merge-duplicates`` (an upsert on ``on_conflict``); ignored duplicates are simply
        absent from the returned list."""
        prefer = ["return=representation"]
        params: dict[str, str] = {}
        if resolution:
            prefer.append(f"resolution={resolution}")
        if on_conflict:
            params["on_conflict"] = on_conflict
        response = await self._send(
            "POST",
            f"/rest/v1/{quote(table, safe='')}",
            headers={
                **self._service_headers,
                "Content-Type": "application/json",
                "Prefer": ", ".join(prefer),
            },
            params=params,
            json=[dict(row) for row in rows] if isinstance(rows, Sequence) else dict(rows),
        )
        stored = self._check(response)
        return list(stored) if isinstance(stored, list) else []

    async def upsert(
        self, table: str, rows: Mapping[str, Any] | Sequence[Mapping[str, Any]], *, on_conflict: str
    ) -> list[dict[str, Any]]:
        return await self.insert(
            table, rows, on_conflict=on_conflict, resolution="merge-duplicates"
        )

    async def update(
        self, table: str, values: Mapping[str, Any], *, filters: Sequence[Filter]
    ) -> list[dict[str, Any]]:
        if not filters:
            raise ValueError("update requires at least one filter")
        response = await self._send(
            "PATCH",
            f"/rest/v1/{quote(table, safe='')}",
            headers={
                **self._service_headers,
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            params=encode_filters(filters),
            json=dict(values),
        )
        rows = self._check(response)
        return list(rows) if isinstance(rows, list) else []

    # --- Storage ------------------------------------------------------------------------------

    @staticmethod
    def _object_path(bucket: str, path: str) -> str:
        return f"{quote(bucket, safe='')}/{quote(path, safe='/')}"

    async def storage_upload(self, bucket: str, path: str, data: bytes, content_type: str) -> str:
        response = await self._send(
            "PUT",
            f"/storage/v1/object/{self._object_path(bucket, path)}",
            headers={**self._service_headers, "Content-Type": content_type, "x-upsert": "true"},
            content=data,
        )
        self._check_storage(response)
        return path

    async def storage_download(self, bucket: str, path: str) -> bytes:
        response = await self._send(
            "GET",
            f"/storage/v1/object/{self._object_path(bucket, path)}",
            headers=self._service_headers,
        )
        self._check_storage(response)
        return response.content

    async def storage_signed_url(self, bucket: str, path: str, expires_in: int) -> str:
        response = await self._send(
            "POST",
            f"/storage/v1/object/sign/{self._object_path(bucket, path)}",
            headers={**self._service_headers, "Content-Type": "application/json"},
            json={"expiresIn": int(expires_in)},
        )
        payload = self._check_storage(response)
        signed = payload.get("signedURL") if isinstance(payload, Mapping) else None
        if not isinstance(signed, str) or not signed:
            raise ApiException(INTERNAL_ERROR, message="Storage did not return a signed URL.")
        if signed.startswith("http"):
            return signed
        return f"{self.base_url}/storage/v1/{signed.lstrip('/')}"

    def _check_storage(self, response: httpx.Response) -> Any:
        payload = self._payload(response)
        if response.is_success:
            return payload
        if response.status_code == 404:
            raise ApiException(NOT_FOUND, message="Object not found.")
        log.error("supabase storage error", extra={"status": response.status_code})
        raise ApiException(INTERNAL_ERROR, message="Storage request failed.")

    # --- GoTrue -----------------------------------------------------------------------------

    async def auth_grant(self, grant_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        """``POST /auth/v1/token?grant_type=<grant_type>`` with the anon key. Every 4xx
        becomes ``401 unauthorized`` so wrong email and wrong password are indistinguishable."""
        response = await self._send(
            "POST",
            "/auth/v1/token",
            headers={**self._anon_headers, "Content-Type": "application/json"},
            params={"grant_type": grant_type},
            json=dict(payload),
        )
        body = self._payload(response)
        if response.is_success and isinstance(body, dict):
            return body
        if 400 <= response.status_code < 500:
            raise ApiException(UNAUTHORIZED, message="Invalid credentials.")
        log.error("gotrue error", extra={"status": response.status_code})
        raise ApiException(INTERNAL_ERROR, message="Authentication service unavailable.")


__all__ = [
    "RETRY_STATUSES",
    "SQLSTATE_ERRORS",
    "Filter",
    "SupabaseClient",
    "encode_filters",
    "postgrest_error",
]
