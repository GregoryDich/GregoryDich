"""§3 — credit ledger."""

from fastapi import APIRouter, Query

from app.errors import NOT_IMPLEMENTED, ApiException
from app.schemas import LedgerPage

router = APIRouter(prefix="/credits", tags=["credits"])


@router.get("/ledger", response_model=LedgerPage)
async def ledger(
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
) -> LedgerPage:
    raise ApiException(NOT_IMPLEMENTED)
