"""§1 — current user and balance."""

from fastapi import APIRouter

from app.errors import NOT_IMPLEMENTED, ApiException
from app.schemas import MeResponse

router = APIRouter(tags=["me"])


@router.get("/me", response_model=MeResponse)
async def me() -> MeResponse:
    raise ApiException(NOT_IMPLEMENTED)
