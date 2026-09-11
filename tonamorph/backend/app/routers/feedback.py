"""§2 result feedback with the bounded auto-refund, and §14 NPS."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.auth import Principal
from app.dependencies import get_principal, get_services
from app.errors import CONFLICT, NOT_FOUND, ApiException
from app.middleware.rate_limit import rate_limit
from app.schemas import (
    CreditBalance,
    JobFeedbackRequest,
    JobFeedbackResponse,
    NpsRequest,
    NpsResponse,
)
from app.services.factory import Services

router = APIRouter(tags=["feedback"])

JOB_NOT_FOUND_MESSAGE = "Job not found."
JOB_UNFINISHED_MESSAGE = "Rate a finished job."
NPS_COOLDOWN_MESSAGE = "You already answered within the last 30 days."


@router.post(
    "/jobs/{job_id}/feedback",
    status_code=status.HTTP_201_CREATED,
    response_model=JobFeedbackResponse,
    dependencies=[Depends(rate_limit("reads"))],
)
async def job_feedback(
    job_id: UUID,
    body: JobFeedbackRequest,
    principal: Principal = Depends(get_principal),
    services: Services = Depends(get_services),
) -> JobFeedbackResponse:
    """One row per job, refreshed on every call. A thumbs-down on a succeeded job within
    24 h, for any reason but ``slow``, refunds the credit inside the GTM §2.6 bounds; the
    decision is taken in one database transaction (``record_job_feedback``)."""
    try:
        record = await services.quality.record_feedback(job_id, principal.user_id, body)
    except ApiException as exc:
        if exc.code == NOT_FOUND:
            raise ApiException(NOT_FOUND, message=JOB_NOT_FOUND_MESSAGE) from exc
        if exc.code == CONFLICT:
            raise ApiException(CONFLICT, message=JOB_UNFINISHED_MESSAGE) from exc
        raise
    balance = await services.credits.get_balance(principal.user_id)
    return JobFeedbackResponse(
        refunded=record.refunded,
        balance=CreditBalance(**balance.model_dump(include={"credits", "reserved", "available"})),
    )


@router.post(
    "/nps",
    status_code=status.HTTP_201_CREATED,
    response_model=NpsResponse,
    dependencies=[Depends(rate_limit("reads"))],
)
async def submit_nps(
    body: NpsRequest,
    principal: Principal = Depends(get_principal),
    services: Services = Depends(get_services),
) -> NpsResponse:
    try:
        record = await services.quality.submit_nps(principal.user_id, body.score, body.comment)
    except ApiException as exc:
        if exc.code == CONFLICT:
            raise ApiException(CONFLICT, message=NPS_COOLDOWN_MESSAGE) from exc
        raise
    services.growth.nps_submitted(
        principal.user_id,
        principal.email,
        score=record.score,
        comment=record.comment,
        response_id=record.id,
    )
    return NpsResponse(
        id=record.id, score=record.score, comment=record.comment, created_at=record.created_at
    )
