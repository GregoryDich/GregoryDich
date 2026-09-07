"""§2 — job submission, status, SSE / WebSocket events and cancellation.

Order of operations (docs/SECURITY.md §7): authenticate → validate (magic bytes, size,
``options``) → idempotency lookup → store the input → ``create_job`` (which reserves one
credit) → dispatch. A rejected upload therefore never creates a reservation.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, WebSocket, status
from fastapi.responses import Response
from pydantic import ValidationError
from sse_starlette.sse import EventSourceResponse, ServerSentEvent
from starlette.websockets import WebSocketDisconnect

from app.auth import Principal
from app.dependencies import authenticate, get_principal, get_services
from app.errors import (
    PAYLOAD_TOO_LARGE,
    UNSUPPORTED_MEDIA_TYPE,
    VALIDATION_ERROR,
    ApiException,
)
from app.middleware.rate_limit import enforce, rate_limit
from app.schemas import JobOptions, JobStatus, JobSubmitResponse, PipelineOptions
from app.services.events import TERMINAL_EVENTS
from app.services.jobs import JOB_CREDITS, input_storage_key
from app.services.factory import Services

log = logging.getLogger("snapplay.jobs")
router = APIRouter(prefix="/jobs", tags=["jobs"])

SSE_PING_SECONDS = 5
CHUNK_BYTES = 64 * 1024
WS_UNAUTHORIZED = 4401
"""WebSocket close code for a rejected token (application range, mirrors HTTP 401)."""

AUDIO_CONTENT_TYPES: dict[str, str] = {
    "flac": "audio/flac",
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "ogg": "audio/ogg",
    "aiff": "audio/aiff",
}


def sniff_audio(head: bytes) -> str | None:
    """The container extension implied by ``head``'s magic bytes, or ``None`` (§2, 415).

    Recognises FLAC, RIFF/WAVE, MP3 (ID3 tag or an MPEG-1 layer III frame sync), Ogg and
    AIFF/AIFC. The filename and the client's ``Content-Type`` are never consulted.
    """
    if len(head) < 4:
        return None
    if head.startswith(b"fLaC"):
        return "flac"
    if head.startswith(b"RIFF") and head[8:12] == b"WAVE":
        return "wav"
    if head.startswith(b"OggS"):
        return "ogg"
    if head.startswith(b"FORM") and head[8:12] in (b"AIFF", b"AIFC"):
        return "aiff"
    if head.startswith(b"ID3") or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "mp3"
    return None


def parse_options(raw: str | None) -> JobOptions:
    """``options`` multipart field → :class:`JobOptions`; anything else is 422."""
    if raw is None or raw.strip() == "":
        return JobOptions()
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        raise ApiException(
            VALIDATION_ERROR,
            details={
                "errors": [
                    {"loc": ["body", "options"], "msg": "not valid JSON", "type": "value_error"}
                ]
            },
        ) from exc
    if not isinstance(payload, dict):
        raise ApiException(
            VALIDATION_ERROR,
            details={
                "errors": [
                    {"loc": ["body", "options"], "msg": "must be an object", "type": "type_error"}
                ]
            },
        )
    try:
        return JobOptions.model_validate(payload)
    except ValidationError as exc:
        raise ApiException(
            VALIDATION_ERROR,
            details={
                "errors": [
                    {
                        "loc": ["body", "options", *(str(p) for p in err["loc"])],
                        "msg": err["msg"],
                        "type": err["type"],
                    }
                    for err in exc.errors()
                ]
            },
        ) from exc


async def read_upload(upload: UploadFile, max_bytes: int) -> bytes:
    """Read the upload in chunks, aborting with 413 the moment the cap is passed."""
    chunks: list[bytes] = []
    total = 0
    while chunk := await upload.read(CHUNK_BYTES):
        total += len(chunk)
        if total > max_bytes:
            raise ApiException(
                PAYLOAD_TOO_LARGE,
                message=f"The upload exceeds {max_bytes} bytes.",
                details={"max_bytes": max_bytes},
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=JobSubmitResponse,
    dependencies=[Depends(rate_limit("jobs"))],
)
async def submit_job(
    audio: UploadFile = File(...),
    options: str | None = Form(default=None),
    principal: Principal = Depends(get_principal),
    services: Services = Depends(get_services),
) -> JobSubmitResponse:
    job_options = parse_options(options)
    data = await read_upload(audio, services.settings.max_upload_bytes)
    extension = sniff_audio(data[:16])
    if extension is None:
        raise ApiException(
            UNSUPPORTED_MEDIA_TYPE,
            message="Upload a FLAC, WAV, MP3, OGG or AIFF file.",
        )

    if job_options.idempotency_key:
        existing = await services.jobs.find_by_idempotency_key(
            principal.user_id, job_options.idempotency_key
        )
        if existing is not None:
            balance = await services.credits.get_balance(principal.user_id)
            return JobSubmitResponse(
                job_id=existing.job_id,
                credits_reserved=JOB_CREDITS,
                balance=balance.model_dump(include={"credits", "reserved", "available"}),
            )

    job = await services.jobs.create(
        principal.user_id, job_options, f"input.{extension}", JOB_CREDITS
    )
    input_key = input_storage_key(principal.user_id, job.job_id, f"input.{extension}")
    await services.storage.upload_bytes(input_key, data, AUDIO_CONTENT_TYPES[extension])
    pipeline_options = PipelineOptions.from_job_options(
        job_options, services.settings.max_input_seconds
    )
    try:
        await services.dispatch.dispatch(
            job.job_id, principal.user_id, input_key, pipeline_options
        )
    except ApiException:
        await services.jobs.fail(
            job.job_id, "worker_unavailable", "No worker is available; retry later."
        )
        raise
    balance = await services.credits.get_balance(principal.user_id)
    return JobSubmitResponse(
        job_id=job.job_id,
        credits_reserved=JOB_CREDITS,
        balance=balance.model_dump(include={"credits", "reserved", "available"}),
    )


async def _job_or_404(services: Services, job_id: UUID, user_id: UUID) -> JobStatus:
    job = await services.jobs.get(job_id, user_id)
    if job is None:
        raise ApiException("not_found", message="Job not found.")
    return job


@router.get("/{job_id}", response_model=JobStatus, dependencies=[Depends(rate_limit("reads"))])
async def get_job(
    job_id: UUID,
    principal: Principal = Depends(get_principal),
    services: Services = Depends(get_services),
) -> JobStatus:
    return await _job_or_404(services, job_id, principal.user_id)


@router.get("/{job_id}/events", dependencies=[Depends(rate_limit("reads"))])
async def job_events(
    request: Request,
    job_id: UUID,
    principal: Principal = Depends(get_principal),
    services: Services = Depends(get_services),
) -> EventSourceResponse:
    """SSE stream of ``progress`` events ending with ``result`` or ``error`` (§2)."""
    await _job_or_404(services, job_id, principal.user_id)

    async def publish() -> AsyncIterator[ServerSentEvent]:
        async for event in services.jobs.events(job_id):
            if await request.is_disconnected():
                return
            yield ServerSentEvent(event=event["event"], data=json.dumps(event["data"]))
            if event["event"] in TERMINAL_EVENTS:
                return

    return EventSourceResponse(
        publish(), ping=SSE_PING_SECONDS, ping_message_factory=lambda: ServerSentEvent(comment="ping")
    )


@router.websocket("/{job_id}/ws")
async def job_ws(
    websocket: WebSocket, job_id: UUID, token: str | None = Query(default=None)
) -> None:
    """Same payloads as SSE, as JSON text frames; ``?token=`` carries the access token."""
    services: Services = websocket.app.state.services
    try:
        principal = await authenticate(services, bearer=token)
        enforce(websocket.app.state.rate_limits.reads, principal)
        job = await services.jobs.get(job_id, principal.user_id)
        if job is None:
            raise ApiException("not_found", message="Job not found.")
    except ApiException as exc:
        await websocket.close(code=WS_UNAUTHORIZED, reason=exc.code)
        return

    await websocket.accept()
    try:
        async for event in services.jobs.events(job_id):
            await websocket.send_text(json.dumps(event))
            if event["event"] in TERMINAL_EVENTS:
                break
        await websocket.close()
    except WebSocketDisconnect:
        pass


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit("reads"))],
)
async def cancel_job(
    job_id: UUID,
    principal: Principal = Depends(get_principal),
    services: Services = Depends(get_services),
) -> Response:
    await _job_or_404(services, job_id, principal.user_id)
    await services.jobs.cancel(job_id, principal.user_id)
    await services.dispatch.cancel(job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
