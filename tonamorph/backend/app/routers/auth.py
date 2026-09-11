"""§1 — GoTrue proxy so the plugin only ever talks to this host: password and refresh
grants, and the account lifecycle (sign-up, confirmation resend, recovery, logout).

What the proxy discloses is deliberate and asymmetric: ``/signup`` answers ``409`` for an
address that already has an account, because a user who forgot they have one would
otherwise wait for a confirmation email that never comes; ``/token``, ``/recover`` and
``/resend`` never distinguish a known address from an unknown one. Every route that takes
an address draws on the same per-address budget as password guessing, so the disclosure
on ``/signup`` costs an enumerator :data:`AUTH_ATTEMPTS_PER_MIN` probes per address per
minute, and none of the mail-sending routes can be driven as a spam relay.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, Protocol

from fastapi import APIRouter, Depends, Request

from app.auth import Principal
from app.config import Settings
from app.dependencies import credentials_of, get_services, get_session_principal
from app.errors import CONFLICT, INTERNAL_ERROR, UNAUTHORIZED, ApiException
from app.middleware.rate_limit import (
    AuthCredential,
    RateLimits,
    auth_bucket_key,
    enforce_key,
    rate_limit,
)
from app.schemas import (
    AuthAck,
    AuthSession,
    AuthUser,
    RecoverRequest,
    RefreshRequest,
    ResendRequest,
    SignupRequest,
    SignupResponse,
    TokenRequest,
    TokenResponse,
)
from app.services.factory import Services
from app.services.memory import MemoryAuthService
from app.services.supabase import ACCOUNT_EXISTS_MESSAGE, INVALID_CREDENTIALS_MESSAGE

log = logging.getLogger("tonamorph.auth")
router = APIRouter(prefix="/auth", tags=["auth"])

PASSWORD_GRANT = "password"
REFRESH_GRANT = "refresh_token"
CONFIRM_PATH = "/auth/confirm"
RESET_PASSWORD_PATH = "/auth/reset-password"
"""Website routes GoTrue's emailed links land on, under ``Settings.auth_site_url``."""
NOT_CONFIGURED_MESSAGE = "Authentication is not configured."


class AuthProvider(Protocol):
    """The GoTrue calls of :class:`app.services.supabase.SupabaseClient`, also implemented
    by :class:`app.services.memory.MemoryAuthService`. Every method returns GoTrue's JSON
    or raises the mapped :class:`ApiException`."""

    async def auth_grant(self, grant_type: str, payload: Mapping[str, Any]) -> dict[str, Any]: ...

    async def auth_signup(
        self, email: str, password: str, *, redirect_to: str
    ) -> dict[str, Any]: ...

    async def auth_recover(self, email: str, *, redirect_to: str) -> None: ...

    async def auth_resend(self, email: str, kind: str, *, redirect_to: str) -> None: ...

    async def auth_logout(self, access_token: str) -> None: ...


def auth_provider(services: Services) -> AuthProvider:
    """GoTrue through Supabase, or its in-memory stand-in whenever the data backend is
    the memory store (tests, and local development without a Supabase project)."""
    if services.memory is not None:
        return MemoryAuthService(services.memory.gotrue)
    if services.supabase is None:
        raise ApiException(UNAUTHORIZED, message=NOT_CONFIGURED_MESSAGE)
    return services.supabase


def site_link(settings: Settings, path: str) -> str:
    return settings.auth_site_url.rstrip("/") + path


def limit_attempts(request: Request, kind: AuthCredential, value: str) -> None:
    """Bound pre-authentication attempts on the credential being tried, or raise 429.

    Keyed on the submitted credential — the email for a password grant, the refresh
    token for a refresh — and not on the client address. This route proxies GoTrue, so
    every attempt already reaches the provider from one address; behind the load
    balancer the peer address here is the balancer's, which would make an IP bucket a
    single global bucket that an attacker can use to lock every user out, and the only
    per-client alternative, ``X-Forwarded-For``, is client-supplied and so evadable at
    will. The email is what an attacker cannot vary while still attacking a given
    account, so it is what the bucket is keyed on; volumetric abuse spread across many
    accounts stays with the ingress WAF (docs/SECURITY.md §6).
    """
    limits: RateLimits = request.app.state.rate_limits
    enforce_key(limits.auth, auth_bucket_key(kind, value))


def _auth_user(record: Mapping[str, Any]) -> AuthUser:
    return AuthUser(id=record["id"], email=str(record.get("email") or ""))


def _token_response(payload: Mapping[str, Any]) -> TokenResponse:
    user = payload.get("user")
    if not isinstance(user, dict) or not user.get("id"):
        raise ApiException(UNAUTHORIZED, message=INVALID_CREDENTIALS_MESSAGE)
    return TokenResponse(
        access_token=str(payload.get("access_token") or ""),
        refresh_token=str(payload.get("refresh_token") or ""),
        expires_in=int(payload.get("expires_in") or 0),
        user=_auth_user(user),
    )


def signup_response(payload: Mapping[str, Any]) -> SignupResponse:
    """Interpret GoTrue's sign-up body: a session when the project auto-confirms, else
    the bare user awaiting its confirmation link. An address that already has a
    confirmed account gets, from GoTrue, a fabricated user with no ``identities`` and no
    email; that is answered ``409`` like the explicit refusal, for the reason in the
    module docstring."""
    if "access_token" in payload:
        token = _token_response(payload)
        return SignupResponse(
            status="session",
            user=token.user,
            session=AuthSession(
                access_token=token.access_token,
                refresh_token=token.refresh_token,
                expires_in=token.expires_in,
            ),
        )
    if not payload.get("id"):
        raise ApiException(INTERNAL_ERROR, message="Unexpected sign-up response.")
    if payload.get("identities") == []:
        raise ApiException(CONFLICT, message=ACCOUNT_EXISTS_MESSAGE)
    return SignupResponse(status="confirmation_pending", user=_auth_user(payload))


async def _grant(services: Services, grant_type: str, body: dict[str, object]) -> TokenResponse:
    return _token_response(await auth_provider(services).auth_grant(grant_type, body))


@router.post("/token", response_model=TokenResponse)
async def token(
    request: Request, body: TokenRequest, services: Services = Depends(get_services)
) -> TokenResponse:
    limit_attempts(request, "email", body.email)
    return await _grant(
        services, PASSWORD_GRANT, {"email": body.email, "password": body.password}
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request, body: RefreshRequest, services: Services = Depends(get_services)
) -> TokenResponse:
    limit_attempts(request, "refresh_token", body.refresh_token)
    return await _grant(services, REFRESH_GRANT, {"refresh_token": body.refresh_token})


@router.post("/signup", response_model=SignupResponse, status_code=201)
async def signup(
    request: Request, body: SignupRequest, services: Services = Depends(get_services)
) -> SignupResponse:
    limit_attempts(request, "email", body.email)
    payload = await auth_provider(services).auth_signup(
        body.email, body.password, redirect_to=site_link(services.settings, CONFIRM_PATH)
    )
    response = signup_response(payload)
    # The trigger has created the profile by now; this is the earliest the account can be
    # met, so Signed Up (§14) fires here rather than at the first plugin sign-in. The
    # account exists whatever happens to the stamp, so a failure is logged, not answered.
    try:
        await services.users.first_sight(response.user.id, "web")
    except ApiException as exc:
        log.warning(
            "first sight could not be recorded at sign-up",
            extra={"user_id": str(response.user.id), "code": exc.code},
        )
    return response


@router.post("/recover", response_model=AuthAck)
async def recover(
    request: Request, body: RecoverRequest, services: Services = Depends(get_services)
) -> AuthAck:
    """Always ``ok``: whether the address has an account is never disclosed here."""
    limit_attempts(request, "email", body.email)
    await auth_provider(services).auth_recover(
        body.email, redirect_to=site_link(services.settings, RESET_PASSWORD_PATH)
    )
    return AuthAck()


@router.post("/resend", response_model=AuthAck)
async def resend(
    request: Request, body: ResendRequest, services: Services = Depends(get_services)
) -> AuthAck:
    """Always ``ok``, as for ``/recover``."""
    limit_attempts(request, "email", body.email)
    await auth_provider(services).auth_resend(
        body.email, body.type, redirect_to=site_link(services.settings, CONFIRM_PATH)
    )
    return AuthAck()


@router.post("/logout", response_model=AuthAck, dependencies=[Depends(rate_limit("reads"))])
async def logout(
    request: Request,
    principal: Principal = Depends(get_session_principal),
    services: Services = Depends(get_services),
) -> AuthAck:
    """Revoke the session's refresh token at GoTrue. The access token stays valid until
    it expires — it is a signed JWT nothing consults GoTrue about — so the client must
    still discard it, which the plugin does."""
    del principal  # verified; the raw bearer token is what GoTrue needs
    bearer, _ = credentials_of(request)
    assert bearer is not None  # a session principal is only ever built from one
    await auth_provider(services).auth_logout(bearer)
    return AuthAck()
