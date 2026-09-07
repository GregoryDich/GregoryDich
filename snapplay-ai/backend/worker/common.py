"""Job execution shared by the SQS, Modal and RunPod entry points.

The transport (queue message, Modal call, RunPod request) is parsed into a
:class:`JobSpec`; :func:`execute_job` then marks the job running, fetches the input,
runs the pipeline in a worker thread while relaying progress to ``JobsService``,
uploads every stem and the MIDI file under ``jobs/<user_id>/<job_id>/``, signs their
URLs and calls ``JobsService.complete``. Bad input surfaces as
:class:`app.pipeline.PipelineError`; anything else propagates so the transport can
decide between failing the job and letting the queue retry.

Services come from ``app.services.factory.build_services`` (imported lazily) and are
only used through the Protocols in :mod:`app.services`.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import logging
import threading
from collections.abc import Mapping
from concurrent.futures import Future
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Any, Protocol
from uuid import UUID

from pydantic import ValidationError

from app.config import Settings, get_settings
from app.errors import INTERNAL_ERROR
from app.pipeline import PipelineError, get_pipeline
from app.pipeline.base import STAGE_SEPARATE, RunPipeline
from app.schemas import JobResult, JobStatus, PipelineOptions, PipelineResult, StemResult
from app.services import JobsService, StorageService

log = logging.getLogger("snapplay.worker")

WAV_CONTENT_TYPE = "audio/wav"
MIDI_CONTENT_TYPE = "audio/midi"
MIDI_FILENAME = "score.mid"
PROGRESS_MIN_STEP = 0.05
DOWNLOAD_TIMEOUT_SECONDS = 30.0
INTERNAL_ERROR_MESSAGE = "The worker could not process this job."
TERMINAL_STATES = frozenset({"succeeded", "failed", "cancelled"})


class WorkerServices(Protocol):
    """The slice of the wired service bundle a worker needs."""

    jobs: JobsService
    storage: StorageService


@dataclass(frozen=True)
class JobSpec:
    """One job as the transports describe it (contract §10 message shape)."""

    job_id: UUID
    user_id: UUID
    options: PipelineOptions
    input_key: str | None = None
    credits_reserved: int = 1

    @property
    def prefix(self) -> str:
        return f"jobs/{self.user_id}/{self.job_id}"

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> JobSpec:
        """Parse ``{job_id, user_id, options, input_key?, credits_reserved?}``; ``options``
        is the §7 ``PipelineOptions`` JSON. Raises :class:`ValueError` when malformed."""
        try:
            input_key = payload.get("input_key")
            return cls(
                job_id=UUID(str(payload["job_id"])),
                user_id=UUID(str(payload["user_id"])),
                options=PipelineOptions.model_validate(payload.get("options") or {}),
                input_key=str(input_key) if input_key else None,
                credits_reserved=int(payload.get("credits_reserved", 1)),
            )
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            raise ValueError(f"malformed job payload: {exc}") from exc


def build_services(settings: Settings) -> WorkerServices:
    """The production service bundle (Supabase jobs + configured storage), imported
    lazily so this module stays importable without the backend implementations."""
    try:
        from app.services.factory import build_services as factory
    except ImportError as exc:
        raise RuntimeError(
            "app.services.factory.build_services is required to run a worker"
        ) from exc
    services = factory(settings)
    missing = [name for name in ("jobs", "storage") if not hasattr(services, name)]
    if missing:
        raise RuntimeError(f"service bundle lacks {', '.join(missing)}")
    return services


def load_pipeline(settings: Settings) -> RunPipeline:
    """``run_pipeline`` for ``SNAPPLAY_PIPELINE``, warning when a GPU worker runs the
    fake backend."""
    run = get_pipeline(settings)
    if settings.snapplay_pipeline == "fake":
        log.warning("SNAPPLAY_PIPELINE=fake: this worker runs the deterministic CPU stub")
    return run


def warm_up_pipeline(settings: Settings) -> None:
    """Call the backend's ``warm_up`` (model loading) when it defines one."""
    from importlib import import_module

    module = import_module(f"app.pipeline.{settings.snapplay_pipeline}")
    warm = getattr(module, "warm_up", None)
    if callable(warm):
        started = perf_counter()
        warm()
        log.info("pipeline warm-up took %.1fs", perf_counter() - started)


class ProgressReporter:
    """Bridges the pipeline's synchronous progress callback, invoked on the worker
    thread, to ``JobsService.set_progress`` on the event loop.

    Updates are coalesced (a new stage, at least :data:`PROGRESS_MIN_STEP` of progress,
    or completion) and serialised so the job row never moves backwards; failures are
    logged and never interrupt the pipeline.
    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        jobs: JobsService,
        job_id: UUID,
        min_step: float = PROGRESS_MIN_STEP,
    ) -> None:
        self._loop = loop
        self._jobs = jobs
        self._job_id = job_id
        self._min_step = min_step
        self._last: tuple[str, float] | None = None
        self._pending: set[Future[None]] = set()
        self._guard = threading.Lock()
        self._order = asyncio.Lock()
        self.reported: list[tuple[str, float]] = []

    def __call__(self, stage: str, fraction: float) -> None:
        fraction = min(max(float(fraction), 0.0), 1.0)
        with self._guard:
            last = self._last
            if (
                last is not None
                and last[0] == stage
                and fraction < 1.0
                and fraction - last[1] < self._min_step
            ):
                return
            self._last = (stage, fraction)
            self.reported.append((stage, fraction))
            future = asyncio.run_coroutine_threadsafe(self._report(stage, fraction), self._loop)
            self._pending.add(future)
        future.add_done_callback(self._discard)

    def _discard(self, future: Future[None]) -> None:
        with self._guard:
            self._pending.discard(future)

    async def _report(self, stage: str, fraction: float) -> None:
        async with self._order:
            try:
                await self._jobs.set_progress(self._job_id, stage, fraction)
            except Exception as exc:
                log.warning(
                    "progress update failed",
                    extra={"job_id": str(self._job_id), "stage": stage},
                    exc_info=exc,
                )

    async def drain(self) -> None:
        with self._guard:
            pending = list(self._pending)
        if pending:
            await asyncio.gather(*(asyncio.wrap_future(f) for f in pending))


async def current_status(jobs: JobsService, spec: JobSpec) -> JobStatus | None:
    return await jobs.get(spec.job_id, spec.user_id)


def is_terminal(status: JobStatus | None) -> bool:
    return status is not None and status.status in TERMINAL_STATES


async def load_audio(
    payload: Mapping[str, Any], spec: JobSpec, storage: StorageService
) -> bytes:
    """The input audio from ``audio_bytes``, ``audio_base64``, ``audio_url`` or the
    storage object at ``input_key`` (in that order of preference)."""
    raw = payload.get("audio_bytes")
    if isinstance(raw, bytes | bytearray) and raw:
        return bytes(raw)
    encoded = payload.get("audio_base64")
    if isinstance(encoded, str) and encoded:
        try:
            return base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise PipelineError("unsupported_media_type", "audio_base64 is not base64") from exc
    url = payload.get("audio_url")
    if isinstance(url, str) and url:
        return await download_url(url)
    if spec.input_key:
        return await storage.download_bytes(spec.input_key)
    raise ValueError("job payload carries no audio (audio_bytes, audio_base64, audio_url, input_key)")


async def download_url(url: str) -> bytes:
    import httpx

    async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT_SECONDS, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


async def publish_result(
    storage: StorageService, settings: Settings, spec: JobSpec, result: PipelineResult
) -> JobResult:
    """Upload stems and MIDI under ``spec.prefix``, sign their URLs and build the
    ``JobResult`` handed to ``JobsService.complete``.

    ``credits_charged`` is the reservation and ``balance_after`` a placeholder: the
    ``complete_job`` function settles the reservation and stores the real values.
    """
    ttl = settings.signed_url_ttl_seconds
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl)

    async def upload_stem(stem: StemResult) -> StemResult:
        if stem.wav_bytes is None:
            raise RuntimeError(f"pipeline returned no audio for stem {stem.name!r}")
        path = f"{spec.prefix}/{stem.name}.wav"
        await storage.upload_bytes(path, stem.wav_bytes, WAV_CONTENT_TYPE)
        url = await storage.signed_url(path, ttl)
        return stem.model_copy(update={"url": url, "wav_bytes": None})

    async def upload_midi() -> str:
        if result.midi.smf_bytes is None:
            raise RuntimeError("pipeline returned no MIDI file")
        path = f"{spec.prefix}/{MIDI_FILENAME}"
        await storage.upload_bytes(path, result.midi.smf_bytes, MIDI_CONTENT_TYPE)
        return await storage.signed_url(path, ttl)

    *stems, midi_url = await asyncio.gather(*(upload_stem(s) for s in result.stems), upload_midi())
    return JobResult(
        job_id=spec.job_id,
        credits_charged=spec.credits_reserved,
        balance_after=0,
        input=result.input,
        analysis=result.analysis,
        stems=list(stems),
        midi=result.midi.model_copy(update={"url": midi_url, "smf_bytes": None}),
        expires_at=expires_at,
    )


async def execute_job(
    services: WorkerServices,
    settings: Settings,
    spec: JobSpec,
    run: RunPipeline,
    *,
    audio_bytes: bytes | None = None,
    worker_ref: str = "",
) -> JobResult:
    """Run ``spec`` end to end and record its success.

    Raises :class:`PipelineError` for input the pipeline rejects and lets every other
    exception propagate; the caller marks the job failed or lets the queue retry.
    """
    jobs, storage = services.jobs, services.storage
    started = perf_counter()
    log_extra = {"job_id": str(spec.job_id), "worker_ref": worker_ref}
    await jobs.set_progress(spec.job_id, STAGE_SEPARATE, 0.0)
    if audio_bytes is None:
        if not spec.input_key:
            raise ValueError("job has neither input bytes nor an input_key")
        audio_bytes = await storage.download_bytes(spec.input_key)
    reporter = ProgressReporter(asyncio.get_running_loop(), jobs, spec.job_id)
    reporter._last = (STAGE_SEPARATE, 0.0)
    result = await asyncio.to_thread(run, audio_bytes, spec.options, reporter)
    await reporter.drain()
    job_result = await publish_result(storage, settings, spec, result)
    await jobs.complete(spec.job_id, job_result)
    log.info(
        "job succeeded",
        extra={**log_extra, "duration_ms": round(1000.0 * (perf_counter() - started), 1)},
    )
    return job_result


async def fail_job(jobs: JobsService, job_id: UUID, code: str, message: str) -> None:
    await jobs.fail(job_id, code, message)
    log.info("job failed", extra={"job_id": str(job_id), "code": code})


def error_for(exc: BaseException) -> tuple[str, str]:
    """The §5 error recorded on the job for ``exc``."""
    if isinstance(exc, PipelineError):
        return exc.code, exc.message
    return INTERNAL_ERROR, INTERNAL_ERROR_MESSAGE


async def run_job(
    payload: Mapping[str, Any],
    *,
    settings: Settings | None = None,
    services: WorkerServices | None = None,
    run: RunPipeline | None = None,
    worker_ref: str = "",
) -> dict[str, Any]:
    """Serverless entry (Modal, RunPod): run one job from its request payload.

    Returns ``{"job_id", "status": "succeeded", "result": <JobResult JSON>}`` or
    ``{"job_id", "status": "failed", "error": {"code", "message"}}`` for input the
    pipeline rejects. Any other failure marks the job failed (there is no queue to
    retry it) and re-raises so the platform reports the request as failed.
    """
    settings = settings if settings is not None else get_settings()
    services = services if services is not None else build_services(settings)
    run = run if run is not None else load_pipeline(settings)
    spec = JobSpec.from_payload(payload)
    try:
        audio = await load_audio(payload, spec, services.storage)
        result = await execute_job(
            services, settings, spec, run, audio_bytes=audio, worker_ref=worker_ref
        )
    except PipelineError as exc:
        await fail_job(services.jobs, spec.job_id, exc.code, exc.message)
        return {
            "job_id": str(spec.job_id),
            "status": "failed",
            "error": {"code": exc.code, "message": exc.message},
        }
    except Exception as exc:
        log.error("job crashed", extra={"job_id": str(spec.job_id)}, exc_info=exc)
        code, message = error_for(exc)
        try:
            await fail_job(services.jobs, spec.job_id, code, message)
        except Exception as fail_exc:
            log.error("fail_job failed", extra={"job_id": str(spec.job_id)}, exc_info=fail_exc)
        raise
    return {
        "job_id": str(spec.job_id),
        "status": "succeeded",
        "result": result.model_dump(mode="json"),
    }


def run_job_sync(payload: Mapping[str, Any], **kwargs: Any) -> dict[str, Any]:
    return asyncio.run(run_job(payload, **kwargs))


__all__ = [
    "INTERNAL_ERROR_MESSAGE",
    "MIDI_CONTENT_TYPE",
    "MIDI_FILENAME",
    "PROGRESS_MIN_STEP",
    "TERMINAL_STATES",
    "WAV_CONTENT_TYPE",
    "JobSpec",
    "ProgressReporter",
    "WorkerServices",
    "build_services",
    "current_status",
    "download_url",
    "error_for",
    "execute_job",
    "fail_job",
    "is_terminal",
    "load_audio",
    "load_pipeline",
    "publish_result",
    "run_job",
    "run_job_sync",
    "warm_up_pipeline",
]
