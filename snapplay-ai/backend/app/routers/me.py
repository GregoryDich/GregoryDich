"""§1 — current user and balance."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import Principal
from app.dependencies import get_principal, get_services
from app.errors import NOT_FOUND, ApiException
from app.middleware.rate_limit import rate_limit
from app.schemas import MeResponse, MeUser
from app.services.factory import Services

router = APIRouter(tags=["me"])


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
        user=MeUser(id=user.id, email=user.email, plan=user.plan), balance=balance
    )
