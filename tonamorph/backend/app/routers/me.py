"""§1 — current user and balance, the account export and account deletion."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from app.auth import Principal
from app.dependencies import get_principal, get_services, get_session_principal
from app.errors import NOT_FOUND, VALIDATION_ERROR, ApiException
from app.middleware.rate_limit import TokenBucketLimiter, enforce_key, rate_limit
from app.schemas import (
    AccountExport,
    DeleteAccountRequest,
    DeleteAccountResponse,
    MeResponse,
    MeUser,
)
from app.services.factory import Services
from app.services.users import normalise_email, purge_user_objects

router = APIRouter(tags=["me"])

EXPORTS_PER_MIN = 1
"""On top of the reads budget: an export walks every table the user has rows in (§1)."""
EXPORT_FILENAME = "account-export.json"


def export_limiter(request: Request) -> TokenBucketLimiter:
    """The per-user export bucket, created with the app it belongs to on first use so
    every app instance (each test builds one) gets its own."""
    limiter = getattr(request.app.state, "export_limits", None)
    if limiter is None:
        limiter = request.app.state.export_limits = TokenBucketLimiter(EXPORTS_PER_MIN)
    return limiter


@router.get("/me", response_model=MeResponse, dependencies=[Depends(rate_limit("reads"))])
async def me(
    principal: Principal = Depends(get_principal), services: Services = Depends(get_services)
) -> MeResponse:
    user = await services.users.get(principal.user_id)
    if user is None:
        if principal.via == "api_key":
            raise ApiException(NOT_FOUND, message="Profile not found.")
        user = await services.users.ensure(principal.user_id, principal.email or "")
    balance = await services.credits.get_balance(principal.user_id)
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
