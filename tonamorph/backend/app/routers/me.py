"""§1 — current user and balance, the account export and account deletion."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from fastapi import APIRouter, Depends, Request, Response

from app.auth import Principal
from app.dependencies import get_principal, get_services, get_session_principal
from app.errors import NOT_FOUND, VALIDATION_ERROR, ApiException
from app.middleware.rate_limit import TokenBucketLimiter, enforce_key, rate_limit
from app.schemas import (
    PLUGIN_IDENTITY_MAX_CHARS,
    PLUGIN_VERSION_MAX_CHARS,
    AccountExport,
    DeleteAccountRequest,
    DeleteAccountResponse,
    MeResponse,
    MeUser,
)
from app.services.factory import Services
from app.services.users import normalise_email, purge_user_objects

log = logging.getLogger("tonamorph.me")
router = APIRouter(tags=["me"])

EXPORTS_PER_MIN = 1
"""On top of the reads budget: an export walks every table the user has rows in (§1)."""
EXPORT_FILENAME = "account-export.json"
PLUGIN_VERSION_HEADER = "x-plugin-version"
HOST_HEADER = "x-host"
PLUGIN_OS_HEADER = "x-plugin-os"
"""Optional headers the plugin sends on ``GET /v1/me`` (§1): the first request from a new
version/host pair is the ``Plugin Installed`` event (§14)."""
_PLUGIN_VERSION = re.compile(r"^[0-9A-Za-z][0-9A-Za-z.+_-]*$")
_PRINTABLE = re.compile(r"^[\x20-\x7e]+$")


@dataclass(frozen=True, slots=True)
class PluginIdentity:
    plugin_version: str
    host: str
    os: str | None


def plugin_identity(request: Request) -> PluginIdentity | None:
    """The plugin's self-description from the request headers, or ``None`` when it is
    absent or not the printable, bounded ASCII the ``plugin_installs`` row admits — a
    malformed header is ignored, never an error on the account route."""
    version = request.headers.get(PLUGIN_VERSION_HEADER, "").strip()
    host = request.headers.get(HOST_HEADER, "").strip()
    os_name = request.headers.get(PLUGIN_OS_HEADER, "").strip() or None
    if (
        not version
        or not host
        or len(version) > PLUGIN_VERSION_MAX_CHARS
        or not _PLUGIN_VERSION.match(version)
        or len(host) > PLUGIN_IDENTITY_MAX_CHARS
        or not _PRINTABLE.match(host)
    ):
        return None
    if os_name is not None and (
        len(os_name) > PLUGIN_IDENTITY_MAX_CHARS or not _PRINTABLE.match(os_name)
    ):
        os_name = None
    return PluginIdentity(plugin_version=version, host=host, os=os_name)


async def note_plugin_seen(services: Services, principal: Principal, request: Request) -> None:
    """Record the version/host pair and emit ``Plugin Installed`` the first time; a
    failure here is logged and never fails the account route."""
    identity = plugin_identity(request)
    if identity is None:
        return
    try:
        fresh = await services.quality.touch_plugin_install(
            principal.user_id, identity.plugin_version, identity.host, identity.os
        )
    except ApiException as exc:
        log.warning(
            "plugin install could not be recorded",
            extra={"user_id": str(principal.user_id), "code": exc.code},
        )
        return
    if fresh:
        services.growth.plugin_installed(
            principal.user_id,
            principal.email,
            plugin_version=identity.plugin_version,
            host=identity.host,
            os=identity.os,
        )


def export_limiter(request: Request) -> TokenBucketLimiter:
    """The per-user export bucket, created with the app it belongs to on first use so
    every app instance (each test builds one) gets its own."""
    limiter = getattr(request.app.state, "export_limits", None)
    if limiter is None:
        limiter = request.app.state.export_limits = TokenBucketLimiter(EXPORTS_PER_MIN)
    return limiter


@router.get("/me", response_model=MeResponse, dependencies=[Depends(rate_limit("reads"))])
async def me(
    request: Request,
    principal: Principal = Depends(get_principal),
    services: Services = Depends(get_services),
) -> MeResponse:
    user = await services.users.get(principal.user_id)
    if user is None:
        if principal.via == "api_key":
            raise ApiException(NOT_FOUND, message="Profile not found.")
        user = await services.users.ensure(principal.user_id, principal.email or "")
    balance = await services.credits.get_balance(principal.user_id)
    await note_plugin_seen(services, principal, request)
    return MeResponse(
        user=MeUser(
            id=user.id,
            email=user.email,
            plan=user.plan,
            marketing_opt_in=user.marketing_opt_in,
            referral_code=user.referral_code,
        ),
        balance=balance,
    )


@router.get(
    "/me/export", response_model=AccountExport, dependencies=[Depends(rate_limit("reads"))]
)
async def export_account(
    request: Request,
    response: Response,
    principal: Principal = Depends(get_session_principal),
    services: Services = Depends(get_services),
) -> AccountExport:
    """Everything held about the caller as one JSON document (GDPR Art. 15 / Art. 20)."""
    enforce_key(export_limiter(request), str(principal.user_id))
    export = await services.users.export(principal.user_id)
    response.headers["Content-Disposition"] = f'attachment; filename="{EXPORT_FILENAME}"'
    return export


@router.delete(
    "/me", response_model=DeleteAccountResponse, dependencies=[Depends(rate_limit("reads"))]
)
async def delete_account(
    body: DeleteAccountRequest,
    principal: Principal = Depends(get_session_principal),
    services: Services = Depends(get_services),
) -> DeleteAccountResponse:
    """GDPR Art. 17 with the accounting records kept (docs/SECURITY.md, data-subject
    rights): objects first, then the data tombstone, then the identity."""
    if normalise_email(body.confirm) != normalise_email(principal.email or ""):
        raise ApiException(
            VALIDATION_ERROR,
            details={
                "errors": [
                    {
                        "loc": ["body", "confirm"],
                        "msg": "must be the account's email address",
                        "type": "value_error",
                    }
                ]
            },
        )
    await purge_user_objects(services.storage, principal.user_id)
    await services.users.delete_account(principal.user_id)
    return DeleteAccountResponse()
