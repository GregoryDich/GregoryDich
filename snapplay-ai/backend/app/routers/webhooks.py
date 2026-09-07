"""§4 — payment provider webhooks (raw body is needed for HMAC verification)."""

from fastapi import APIRouter, Request

from app.errors import NOT_IMPLEMENTED, ApiException
from app.schemas import WebhookAck

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/lemonsqueezy", response_model=WebhookAck)
async def lemonsqueezy(request: Request) -> WebhookAck:
    raise ApiException(NOT_IMPLEMENTED)


@router.post("/paddle", response_model=WebhookAck)
async def paddle(request: Request) -> WebhookAck:
    raise ApiException(NOT_IMPLEMENTED)
