"""§3 — plans; ``checkout_url`` carries the caller's user id and any referral code."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth import Principal
from app.dependencies import get_optional_principal, get_services
from app.middleware.rate_limit import optional_read_limit
from app.schemas import PlansResponse
from app.services.factory import Services
from app.services.plans import REFERRAL_CODE_PATTERN, build_checkout_url

router = APIRouter(tags=["plans"])


@router.get("/plans", response_model=PlansResponse, dependencies=[Depends(optional_read_limit)])
async def plans(
    # A referral code, and nothing else: the value is interpolated into the checkout URL.
    ref: str | None = Query(default=None, max_length=64, pattern=REFERRAL_CODE_PATTERN),
    principal: Principal | None = Depends(get_optional_principal),
    services: Services = Depends(get_services),
) -> PlansResponse:
    user_id = principal.user_id if principal is not None else None
    return PlansResponse(
        plans=[
            plan.to_plan_info(build_checkout_url(plan, user_id, ref))
            for plan in await services.plans.list_active()
        ]
    )
