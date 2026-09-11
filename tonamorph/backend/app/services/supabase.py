"""Async Supabase client over httpx: PostgREST, Storage and GoTrue (§1, §2, §6).

Every data-plane call uses the service-role key (RLS is bypassed, so callers scope rows
themselves); the GoTrue proxy uses the anon key. Filters are built from
``(column, operator, value)`` triples into query parameters — user input is never
interpolated into a filter string — and PostgREST error payloads are mapped from their
SQLSTATE to :class:`app.errors.ApiException`.

Retrying is opt-in per call (``_send(..., retry=...)``): a transport failure or a 5xx
gives no evidence about whether the request committed, so only calls that are safe to
apply twice are replayed. See :data:`IDEMPOTENT_RPCS`.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any
from urllib.parse import quote
from uuid import UUID

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
    rate_limited,
)

log = logging.getLogger("tonamorph.supabase")

Filter = tuple[str, str, Any]
"""``(column, operator, value)``; ``operator`` is a PostgREST operator such as ``eq``.
A logical group is ``("or" | "and", <same>, [Filter, ...])`` — build it with
:func:`any_of` / :func:`all_of`."""
LOGICAL_OPERATORS = frozenset({"or", "and"})

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

# RPCs a failed request may be repeated on. Each one is either a pure read, or converges
# on the same rows when applied twice:
#   get_balance, authenticate_api_key  read-only (the latter only stamps last_used_at).
#   reserve_credits, settle_reservation, refund_job
#                                      the ledger row is keyed `<entry_type>:<job_id>`;
#                                      a second call finds it and returns the balance.
#   grant_credits, record_purchase     refuse to act twice under the caller's
#                                      idempotency key (`purchases` is also unique on
#                                      (provider, provider_order_id)).
#   start_job, complete_job, fail_job  return the row unchanged once the job already
#                                      holds the target status.
#   update_job_progress                writes absolute stage/progress values.
#   revoke_api_key                     `revoked_at = coalesce(revoked_at, now())`.
#   reap_stale_jobs                    fails whatever is still stale; a second sweep
#                                      finds nothing left to do.
#   delete_user_account                a tombstoned profile answers with its existing
#                                      account_deletions row and changes nothing.
#   record_job_feedback                one row per job (upsert); the refund it may run is
#                                      keyed `refund:<job_id>` like any refund_job call.
#   touch_plugin_install               a replay finds the row and only re-stamps last_seen_at.
#   user_facts, status_last_24h        read-only.
#   apply_purchase_refund              one purchase_refunds row per purchase; a replay answers
#                                      with the recorded outcome and moves nothing.
#   grant_week1_gifts                  every gift is keyed `gift:week1:<user>`; a second run
#                                      finds nothing left to grant.
#   user_referral_summary              read-only but for assigning a missing code, which a
#                                      unique constraint keeps to one per profile.
# Deliberately absent:
#   submit_nps      a replay of an insert that committed answers P0409 (one answer per 30
#                   days), which would report a recorded answer as refused.
#   create_job      inserts a job and reserves a credit, so a replay charges twice and
#                   strands the first reservation in `queued` forever — unless the call
#                   carries an idempotency key, which `rpc_is_retryable` checks for.
#   create_api_key  every call mints a new key.
#   cancel_job      accepts `queued` only, so a replay answers 409 for a cancellation
#                   that in fact succeeded.
#   claim_webhook_event
#                   a replay of a claim that in fact committed is answered "not claimed",
#                   which would acknowledge a paid event nothing applied. Letting the
#                   delivery fail instead leaves the claim to expire with its lease, and
#                   the provider's next retry applies it (§4).
IDEMPOTENT_RPCS: frozenset[str] = frozenset(
    {
        "apply_purchase_refund",
        "authenticate_api_key",
        "complete_job",
        "delete_user_account",
        "fail_job",
        "get_balance",
        "grant_credits",
        "grant_week1_gifts",
        "reap_stale_jobs",
        "record_job_feedback",
        "record_purchase",
        "refund_job",
        "reserve_credits",
        "revoke_api_key",
        "settle_reservation",
        "start_job",
        "status_last_24h",
        "touch_plugin_install",
        "update_job_progress",
        "user_facts",
        "user_referral_summary",
    }
)


def rpc_is_retryable(name: str, params: Mapping[str, Any]) -> bool:
    """Whether ``name`` may be re-sent after a transport failure or a 5xx."""
    if name == "create_job":
        return params.get("p_idempotency_key") is not None
    return name in IDEMPOTENT_RPCS


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


def any_of(*filters: Filter) -> Filter:
    """A PostgREST ``or=(...)`` group of ``filters``."""
    return ("or", "or", list(filters))


def all_of(*filters: Filter) -> Filter:
    """A PostgREST ``and(...)`` group, for nesting inside :func:`any_of`."""
    return ("and", "and", list(filters))


def _encode_condition(column: str, operator: str, value: Any) -> str:
    """One condition inside a logical group, where every value is a list item and so
    needs the same quoting as an ``in`` list."""
    if operator in LOGICAL_OPERATORS:
        inner = ",".join(_encode_condition(*item) for item in value)
        return f"{operator}({inner})"
    if operator == "in":
        items = ",".join(_quote_list_item(item) for item in value)
        return f"{column}.in.({items})"
    return f"{column}.{operator}.{_quote_list_item(value)}"


def encode_filters(filters: Iterable[Filter]) -> dict[str, str]:
    """PostgREST query parameters for ``filters``. Single-value operators take the
    remainder of the parameter verbatim, so values need no quoting there; ``in`` lists
    and the conditions inside a logical group quote items containing reserved
    characters."""
    params: dict[str, str] = {}
    for column, operator, value in filters:
        if operator in LOGICAL_OPERATORS:
            inner = ",".join(_encode_condition(*item) for item in value)
            params[operator] = f"({inner})"
        elif operator == "in":
            items = ",".join(_quote_list_item(item) for item in value)
            params[column] = f"in.({items})"
        else:
            params[column] = f"{operator}.{_encode_value(value)}"
    return params


ACCOUNT_EXISTS_MESSAGE = "An account with this email already exists."
EMAIL_NOT_CONFIRMED_MESSAGE = "Confirm your email address before signing in."
INVALID_CREDENTIALS_MESSAGE = "Invalid credentials."
AUTH_UNAVAILABLE_MESSAGE = "Authentication service unavailable."
SIGNUP_REFUSED_MESSAGE = "Sign-up was refused."
SIGNUP_DISABLED_MESSAGE = "Sign-ups are disabled."
GOTRUE_RETRY_AFTER_SECONDS = 60
"""``Retry-After`` for a GoTrue 429; GoTrue sends none of its own."""
# GoTrue ``error_code`` values (older releases send only ``msg``; see gotrue_error_code).
ACCOUNT_EXISTS_CODES = frozenset({"user_already_exists", "email_exists"})
FORWARDED_SIGNUP_CODES = frozenset({"weak_password", "validation_failed"})
"""Refusals whose ``msg`` is GoTrue's own wording about the submitted values (password
policy, address format) and so is safe and useful to forward."""

CREDIT_COUNTERS = ("available", "requested")
"""The only DETAIL fields ever forwarded to a client (§5 ``insufficient_credits``)."""


def credit_counters(detail: Any) -> dict[str, int] | None:
    """``"available=0 requested=1"`` → ``{"available": 0, "requested": 1}``.

    Only the two integer counters survive; every other token of the DETAIL string is
    dropped, so nothing that PostgreSQL puts there can reach the client.
    """
    if not isinstance(detail, str) or not detail:
        return None
    parsed: dict[str, int] = {}
    for token in detail.split():
        key, sep, raw = token.partition("=")
        if sep and key in CREDIT_COUNTERS and raw.lstrip("-").isdigit():
            parsed[key] = int(raw)
    return parsed or None


def postgrest_error(status: int, payload: Any) -> ApiException:
    """Map a PostgREST / PostgreSQL error response to the §5 envelope.

    PostgreSQL's own ``message`` and ``details`` name constraints, columns and the
    offending values (23505 reports ``Key (email)=(a@b.test) already exists.``), so they
    are logged here and never returned: the client gets the generic sentence for the
    mapped §5 code, and the only details forwarded are the credit counters §2 requires.
    """
    body: Mapping[str, Any] = payload if isinstance(payload, Mapping) else {}
    sqlstate = str(body.get("code") or "")
    mapped = SQLSTATE_ERRORS.get(sqlstate)
    raw = {
        "status": status,
        "sqlstate": sqlstate or None,
        "db_message": body.get("message"),
        "db_details": body.get("details"),
        "db_hint": body.get("hint"),
    }
    if mapped is None:
        log.error("unmapped postgrest error", extra=raw)
        return ApiException(INTERNAL_ERROR, message="Database request failed.")
    code, http_status = mapped
    log.info("postgrest error", extra={**raw, "code": code})
    if code != INSUFFICIENT_CREDITS:
        return ApiException(code, http_status)
    details = credit_counters(body.get("details"))
    available = details.get("available") if details else None
    message = f"You have {available} credits." if available is not None else None
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
        retry: bool,
        headers: Mapping[str, str],
        params: Mapping[str, str] | None = None,
        json: Any = None,
        content: bytes | None = None,
    ) -> httpx.Response:
        """Send one request, replaying it on a transport failure or a 5xx only when
        ``retry`` says applying it twice is safe."""
        attempts = self._max_attempts if retry else 1
        response: httpx.Response | None = None
        for attempt in range(attempts):
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
                if attempt + 1 == attempts:
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
            retry=rpc_is_retryable(name, params),
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
            "GET",
            f"/rest/v1/{quote(table, safe='')}",
            retry=True,
            headers=self._service_headers,
            params=params,
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
            # A plain insert would add a second row on a replay; a conflict resolution
            # makes it converge on the row that is already there.
            retry=bool(resolution and on_conflict),
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
            # Literal values under a filter: the same PATCH twice leaves the same rows.
            retry=True,
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
            retry=True,  # x-upsert: the same bytes land at the same key.
            headers={**self._service_headers, "Content-Type": content_type, "x-upsert": "true"},
            content=data,
        )
        self._check_storage(response)
        return path

    async def storage_download(self, bucket: str, path: str) -> bytes:
        response = await self._send(
            "GET",
            f"/storage/v1/object/{self._object_path(bucket, path)}",
            retry=True,
            headers=self._service_headers,
        )
        self._check_storage(response)
        return response.content

    async def storage_signed_url(self, bucket: str, path: str, expires_in: int) -> str:
        response = await self._send(
            "POST",
            f"/storage/v1/object/sign/{self._object_path(bucket, path)}",
            retry=True,  # signing mints a token; it stores nothing.
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
    #
    # Every call goes out with the anon key and is never replayed: a repeat spends the
    # caller's budget against GoTrue's own per-IP lockout twice, may burn a rotated
    # refresh token, and for sign-up would send a second confirmation email.

    async def _auth_request(
        self,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
        json: Any = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        return await self._send(
            "POST",
            path,
            retry=False,
            headers={**self._anon_headers, **(headers or {}), "Content-Type": "application/json"},
            params=params,
            json=json,
        )

    async def auth_grant(self, grant_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        """``POST /auth/v1/token?grant_type=<grant_type>``. Every 4xx becomes
        ``401 unauthorized`` so wrong email and wrong password are indistinguishable;
        only ``email_not_confirmed`` keeps its own message, since GoTrue answers it after
        the password check and so it reaches nobody who could not already sign in."""
        response = await self._auth_request(
            "/auth/v1/token", params={"grant_type": grant_type}, json=dict(payload)
        )
        body = self._payload(response)
        if response.is_success and isinstance(body, dict):
            return body
        if 400 <= response.status_code < 500:
            if gotrue_error_code(body) == "email_not_confirmed":
                raise ApiException(UNAUTHORIZED, message=EMAIL_NOT_CONFIRMED_MESSAGE)
            raise ApiException(UNAUTHORIZED, message=INVALID_CREDENTIALS_MESSAGE)
        log.error("gotrue error", extra={"status": response.status_code})
        raise ApiException(INTERNAL_ERROR, message=AUTH_UNAVAILABLE_MESSAGE)

    async def auth_signup(self, email: str, password: str, *, redirect_to: str) -> dict[str, Any]:
        """``POST /auth/v1/signup?redirect_to=<redirect_to>``; returns GoTrue's body — a
        session when the project auto-confirms, else the bare user. Refusals are mapped by
        :func:`signup_error`."""
        response = await self._auth_request(
            "/auth/v1/signup",
            params={"redirect_to": redirect_to},
            json={"email": email, "password": password},
        )
        body = self._payload(response)
        if response.is_success and isinstance(body, dict):
            return body
        if 400 <= response.status_code < 500:
            raise signup_error(response.status_code, body)
        log.error("gotrue signup error", extra={"status": response.status_code})
        raise ApiException(INTERNAL_ERROR, message=AUTH_UNAVAILABLE_MESSAGE)

    async def auth_recover(self, email: str, *, redirect_to: str) -> None:
        """``POST /auth/v1/recover?redirect_to=<redirect_to>``; see :meth:`_mail_outcome`."""
        response = await self._auth_request(
            "/auth/v1/recover", params={"redirect_to": redirect_to}, json={"email": email}
        )
        self._mail_outcome(response, "recover")

    async def auth_resend(self, email: str, kind: str, *, redirect_to: str) -> None:
        """``POST /auth/v1/resend?redirect_to=<redirect_to>``; see :meth:`_mail_outcome`."""
        response = await self._auth_request(
            "/auth/v1/resend",
            params={"redirect_to": redirect_to},
            json={"email": email, "type": kind},
        )
        self._mail_outcome(response, "resend")

    def _mail_outcome(self, response: httpx.Response, call: str) -> None:
        """Enumeration guard for the email-sending calls: GoTrue answers an unknown address
        with ``200`` but a known one may get ``429 over_email_send_rate_limit``, so every
        4xx is logged and swallowed and the caller answers ``ok`` either way. Only a 5xx —
        the service itself failing — is reported."""
        if response.is_success:
            return
        if 400 <= response.status_code < 500:
            log.info(
                "gotrue refused mail",
                extra={
                    "call": call,
                    "status": response.status_code,
                    "error_code": gotrue_error_code(self._payload(response)),
                },
            )
            return
        log.error("gotrue mail error", extra={"call": call, "status": response.status_code})
        raise ApiException(INTERNAL_ERROR, message=AUTH_UNAVAILABLE_MESSAGE)

    async def auth_logout(self, access_token: str) -> None:
        """``POST /auth/v1/logout?scope=local`` as the user: revokes the session's refresh
        token. A 4xx means GoTrue no longer knows the session, which is the wanted end
        state; only a 5xx is an error."""
        response = await self._auth_request(
            "/auth/v1/logout",
            params={"scope": "local"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code < 500:
            return
        log.error("gotrue logout error", extra={"status": response.status_code})
        raise ApiException(INTERNAL_ERROR, message=AUTH_UNAVAILABLE_MESSAGE)

    async def auth_admin_delete_user(self, user_id: UUID) -> None:
        """``DELETE /auth/v1/admin/users/{id}`` with the service-role key (§1 account
        deletion): removes the login, its identities and sessions. A 404 means it is
        already gone, which is the wanted end state; the call is replayable, so a
        transport failure or a 5xx is retried unlike the anon-key calls above."""
        response = await self._send(
            "DELETE",
            f"/auth/v1/admin/users/{quote(str(user_id), safe='')}",
            retry=True,
            headers=self._service_headers,
        )
        if response.is_success or response.status_code == 404:
            return
        log.error(
            "gotrue admin delete error",
            extra={"status": response.status_code, "user_id": str(user_id)},
        )
        raise ApiException(INTERNAL_ERROR, message=AUTH_UNAVAILABLE_MESSAGE)


def gotrue_error_code(payload: Any) -> str:
    """GoTrue's ``error_code``, or for releases that predate it a code derived from the
    message (``"User already registered"``, ``"Email not confirmed"``)."""
    body: Mapping[str, Any] = payload if isinstance(payload, Mapping) else {}
    code = str(body.get("error_code") or "")
    if code:
        return code
    message = str(body.get("msg") or body.get("error_description") or "").lower()
    if "already registered" in message:
        return "user_already_exists"
    if "not confirmed" in message:
        return "email_not_confirmed"
    return ""


def signup_error(status: int, payload: Any) -> ApiException:
    """Map a GoTrue sign-up refusal to §5. Existence is disclosed here on purpose — a
    user who forgot they have an account would otherwise wait for a confirmation email
    that never comes — and the per-address rate limit on the route bounds probing."""
    body: Mapping[str, Any] = payload if isinstance(payload, Mapping) else {}
    code = gotrue_error_code(body)
    if status == 429:
        return rate_limited(GOTRUE_RETRY_AFTER_SECONDS)
    if code in ACCOUNT_EXISTS_CODES:
        return ApiException(CONFLICT, message=ACCOUNT_EXISTS_MESSAGE)
    if code == "signup_disabled":
        return ApiException(VALIDATION_ERROR, message=SIGNUP_DISABLED_MESSAGE)
    if code in FORWARDED_SIGNUP_CODES:
        message = str(body.get("msg") or "") or SIGNUP_REFUSED_MESSAGE
        return ApiException(VALIDATION_ERROR, message=message)
    log.info("gotrue signup refused", extra={"status": status, "error_code": code or None})
    return ApiException(VALIDATION_ERROR, message=SIGNUP_REFUSED_MESSAGE)


__all__ = [
    "ACCOUNT_EXISTS_MESSAGE",
    "AUTH_UNAVAILABLE_MESSAGE",
    "EMAIL_NOT_CONFIRMED_MESSAGE",
    "IDEMPOTENT_RPCS",
    "INVALID_CREDENTIALS_MESSAGE",
    "LOGICAL_OPERATORS",
    "RETRY_STATUSES",
    "SQLSTATE_ERRORS",
    "Filter",
    "SupabaseClient",
    "all_of",
    "any_of",
    "credit_counters",
    "encode_filters",
    "gotrue_error_code",
    "postgrest_error",
    "rpc_is_retryable",
    "signup_error",
]
