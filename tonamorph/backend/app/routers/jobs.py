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
from starlette.background import BackgroundTask
from starlette.websockets import WebSocketDisconnect

from app.auth import Principal
from app.config import Settings, get_settings
from app.dependencies import authenticate, get_principal, get_services
from app.errors import (
    INSUFFICIENT_CREDITS,
    NOT_FOUND,
    UNSUPPORTED_MEDIA_TYPE,
    VALIDATION_ERROR,
    ApiException,
    rate_limited,
)
from app.middleware.body_limit import payload_too_large
from app.middleware.rate_limit import (
    STREAM_RETRY_AFTER_SECONDS,
    ConcurrencyLimiter,
    StreamSlot,
    enforce,
    rate_limit,
)
from app.schemas import JobOptions, JobsPage, JobStatus, JobSubmitResponse, PipelineOptions
from app.services.events import TERMINAL_EVENTS
from app.services.factory import Services
from app.services.jobs import JOB_CREDITS, input_storage_key

log = logging.getLogger("tonamorph.jobs")
router = APIRouter(prefix="/jobs", tags=["jobs"])

SSE_PING_SECONDS = 5
CHUNK_BYTES = 64 * 1024
WS_UNAUTHORIZED = 4401
"""WebSocket close code for a rejected token (application range, mirrors HTTP 401)."""
WS_RATE_LIMITED = 4429
"""WebSocket close code for an exhausted budget (mirrors HTTP 429)."""
SERVICE_UNAVAILABLE = "service_unavailable"
"""§5 code for ``MAINTENANCE_MODE``: the service is up, submissions are paused."""
MAINTENANCE_RETRY_AFTER_SECONDS = 300
MAINTENANCE_MESSAGE = "New jobs are paused for maintenance; retry in a few minutes."

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
    """Read the upload in chunks, aborting with 413 the moment the cap is passed.

    Defence in depth behind :class:`app.middleware.body_limit.BodyLimitMiddleware`,
    which already bounded the whole request: this bounds the audio part alone.
    """
    chunks: list[bytes] = []
    total = 0
    while chunk := await upload.read(CHUNK_BYTES):
        total += len(chunk)
        if total > max_bytes:
            raise payload_too_large(max_bytes)
        chunks.append(chunk)
    return b"".join(chunks)


async def refuse_in_maintenance(settings: Settings = Depends(get_settings)) -> None:
    """``503 service_unavailable`` with ``Retry-After`` while ``MAINTENANCE_MODE`` is set;
    runs before the jobs budget so the refusal costs the caller nothing."""
    if settings.maintenance_mode:
        raise ApiException(
            SERVICE_UNAVAILABLE,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            MAINTENANCE_MESSAGE,
            details={"retry_after_seconds": MAINTENANCE_RETRY_AFTER_SECONDS},
            headers={"Retry-After": str(MAINTENANCE_RETRY_AFTER_SECONDS)},
        )


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=JobSubmitResponse,
    dependencies=[Depends(refuse_in_maintenance), Depends(rate_limit("jobs"))],
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

    try:
        job = await services.jobs.create(
            principal.user_id, job_options, f"input.{extension}", JOB_CREDITS
        )
    except ApiException as exc:
        if exc.code == INSUFFICIENT_CREDITS:  # the paywall moment (§14 Credits Exhausted)
            services.growth.credits_refused(principal.user_id, principal.email)
        raise
    input_key = input_storage_key(principal.user_id, job.job_id, f"input.{extension}")
    pipeline_options = PipelineOptions.from_job_options(
        job_options, services.settings.max_input_seconds
    )
    try:
        await services.storage.upload_bytes(input_key, data, AUDIO_CONTENT_TYPES[extension])
        await services.dispatch.dispatch(
            job.job_id, principal.user_id, input_key, pipeline_options
        )
    except ApiException as exc:
        # The reservation must not outlive a failed hand-off.
        await services.jobs.fail(job.job_id, exc.code, exc.message)
        raise
    except Exception:
        log.exception("job hand-off failed", extra={"job_id": str(job.job_id)})
        await services.jobs.fail(
            job.job_id, "internal_error", "The job could not be handed to a worker."
        )
        raise
    balance = await services.credits.get_balance(principal.user_id)
    return JobSubmitResponse(
        job_id=job.job_id,
        credits_reserved=JOB_CREDITS,
        balance=balance.model_dump(include={"credits", "reserved", "available"}),
    )


@router.get("", response_model=JobsPage, dependencies=[Depends(rate_limit("reads"))])
async def list_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    principal: Principal = Depends(get_principal),
    services: Services = Depends(get_services),
) -> JobsPage:
    """The caller's jobs, newest first; ``next_cursor`` is opaque (§2)."""
    return await services.jobs.list(principal.user_id, limit=limit, cursor=cursor)


async def _job_or_404(services: Services, job_id: UUID, user_id: UUID) -> JobStatus:
    job = await services.jobs.get(job_id, user_id)
    if job is None:
        raise ApiException(NOT_FOUND, message="Job not found.")
    return job


@router.get("/{job_id}", response_model=JobStatus, dependencies=[Depends(rate_limit("reads"))])
async def get_job(
    job_id: UUID,
    principal: Principal = Depends(get_principal),
    services: Services = Depends(get_services),
) -> JobStatus:
    return await _job_or_404(services, job_id, principal.user_id)


def hold_stream(request: Request | WebSocket, principal: Principal) -> StreamSlot:
    """Claim one of the principal's concurrent event streams, or raise 429.

    Opening a stream costs a single read token but then holds a connection — and, in
    poll mode, one PostgREST query per second — for as long as the client keeps it, so
    the number held at once is capped as well as the rate at which they are opened.
    """
    streams: ConcurrencyLimiter = request.app.state.rate_limits.streams
    slot = streams.acquire(str(principal.user_id))
    if slot is None:
        raise rate_limited(STREAM_RETRY_AFTER_SECONDS, 0)
    return slot


@router.get("/{job_id}/events", dependencies=[Depends(rate_limit("reads"))])
async def job_events(
    request: Request,
    job_id: UUID,
    principal: Principal = Depends(get_principal),
    services: Services = Depends(get_services),
) -> EventSourceResponse:
    """SSE stream of ``progress`` events ending with ``result`` or ``error`` (§2)."""
    await _job_or_404(services, job_id, principal.user_id)
    slot = hold_stream(request, principal)

    async def publish() -> AsyncIterator[ServerSentEvent]:
        try:
            async for event in services.jobs.events(job_id):
                if await request.is_disconnected():
                    return
                yield ServerSentEvent(event=event["event"], data=json.dumps(event["data"]))
                if event["event"] in TERMINAL_EVENTS:
                    return
        finally:
            # Runs on a client abort too: sse-starlette throws into the suspended
            # generator when the disconnect watcher fires.
            slot.release()

    return EventSourceResponse(
        publish(),
        ping=SSE_PING_SECONDS,
        ping_message_factory=lambda: ServerSentEvent(comment="ping"),
        # Releases the slot even if the response is torn down before the generator
        # ever starts; releasing twice is a no-op.
        background=BackgroundTask(slot.release),
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
            raise ApiException(NOT_FOUND, message="Job not found.")
        slot = hold_stream(websocket, principal)
    except ApiException as exc:
        code = (
            WS_RATE_LIMITED
            if exc.status == status.HTTP_429_TOO_MANY_REQUESTS
            else WS_UNAUTHORIZED
        )
        await websocket.close(code=code, reason=exc.code)
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
    finally:
        slot.release()


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
