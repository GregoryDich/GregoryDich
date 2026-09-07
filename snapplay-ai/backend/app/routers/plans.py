"""§3 — plans with per-user checkout URLs."""

from fastapi import APIRouter

from app.errors import NOT_IMPLEMENTED, ApiException
from app.schemas import PlansResponse

router = APIRouter(tags=["plans"])


@router.get("/plans", response_model=PlansResponse)
async def plans() -> PlansResponse:
    raise ApiException(NOT_IMPLEMENTED)
