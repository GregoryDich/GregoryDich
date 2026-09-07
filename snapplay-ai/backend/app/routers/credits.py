"""§3 — credit ledger, paged with the monotonic ``seq`` cursor."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth import Principal
from app.dependencies import get_principal, get_services
from app.middleware.rate_limit import rate_limit
from app.schemas import LedgerPage
from app.services.factory import Services

router = APIRouter(prefix="/credits", tags=["credits"])


@router.get("/ledger", response_model=LedgerPage, dependencies=[Depends(rate_limit("reads"))])
async def ledger(
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
    principal: Principal = Depends(get_principal),
    services: Services = Depends(get_services),
) -> LedgerPage:
    return await services.credits.ledger(principal.user_id, limit=limit, cursor=cursor)
