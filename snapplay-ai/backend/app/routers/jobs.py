"""§2 — job submission, status, SSE/WS events, cancellation."""

from uuid import UUID

from fastapi import APIRouter, File, Form, UploadFile, WebSocket, status

from app.errors import NOT_IMPLEMENTED, ApiException
from app.schemas import JobStatus, JobSubmitResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=JobSubmitResponse)
async def submit_job(
    audio: UploadFile = File(...),
    options: str | None = Form(default=None),
) -> JobSubmitResponse:
    raise ApiException(NOT_IMPLEMENTED)


@router.get("/{job_id}", response_model=JobStatus)
async def get_job(job_id: UUID) -> JobStatus:
    raise ApiException(NOT_IMPLEMENTED)


@router.get("/{job_id}/events")
async def job_events(job_id: UUID) -> None:
    raise ApiException(NOT_IMPLEMENTED)


@router.websocket("/{job_id}/ws")
async def job_ws(websocket: WebSocket, job_id: UUID) -> None:
    await websocket.close(code=1011, reason=NOT_IMPLEMENTED)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_job(job_id: UUID) -> None:
    raise ApiException(NOT_IMPLEMENTED)
