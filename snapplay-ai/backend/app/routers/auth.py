"""§1 — GoTrue password-grant proxy so the plugin only ever talks to this host."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.dependencies import get_services
from app.errors import UNAUTHORIZED, ApiException
from app.middleware.rate_limit import AuthCredential, RateLimits, auth_bucket_key, enforce_key
from app.schemas import AuthUser, RefreshRequest, TokenRequest, TokenResponse
from app.services.factory import Services

router = APIRouter(prefix="/auth", tags=["auth"])

PASSWORD_GRANT = "password"
REFRESH_GRANT = "refresh_token"


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


def _token_response(payload: dict[str, object]) -> TokenResponse:
    user = payload.get("user")
    if not isinstance(user, dict) or not user.get("id"):
        raise ApiException(UNAUTHORIZED, message="Invalid credentials.")
    return TokenResponse(
        access_token=str(payload.get("access_token") or ""),
        refresh_token=str(payload.get("refresh_token") or ""),
        expires_in=int(payload.get("expires_in") or 0),
        user=AuthUser(id=user["id"], email=str(user.get("email") or "")),
    )


async def _grant(services: Services, grant_type: str, body: dict[str, object]) -> TokenResponse:
    if services.supabase is None:
        raise ApiException(UNAUTHORIZED, message="Authentication is not configured.")
    return _token_response(await services.supabase.auth_grant(grant_type, body))


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
