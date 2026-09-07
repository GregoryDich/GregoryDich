"""Job dispatch selected by ``SNAPPLAY_PIPELINE`` (§7, §10).

``fake`` / ``local`` run ``run_pipeline`` in the API process's default thread pool and
report progress through :class:`JobsService` (which fans out to the event bus);
``modal`` and ``runpod`` hand the job to a remote worker through their SDK / HTTP API;
``aws`` is :class:`app.services.aws.queue.SqsDispatch`, wired by the factory.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

import httpx

from app.config import Settings
from app.errors import INTERNAL_ERROR, WORKER_UNAVAILABLE, ApiException
from app.pipeline.base import PipelineError, RunPipeline, get_pipeline
from app.schemas import PipelineOptions
from app.services import CreditsService, JobsService, StorageService
from app.services.jobs import package_result

log = logging.getLogger("snapplay.dispatch")

MODAL_CLASS_NAME = "SnapPlayWorker"
"""Modal class declared in ``worker/modal_app.py``; its ``run`` method takes one job."""
RUNPOD_API_BASE = "https://api.runpod.ai/v2"


def job_message(
    job_id: UUID, user_id: UUID, input_key: str, options: PipelineOptions
) -> dict[str, Any]:
    """The payload every remote worker receives (same shape as the SQS message, §10)."""
    return {
        "job_id": str(job_id),
        "user_id": str(user_id),
        "input_key": input_key,
        "options": options.model_dump(mode="json"),
    }


class _Cancelled(Exception):
    """Raised inside the pipeline thread once the job has been cancelled."""


class LocalDispatch:
    def __init__(
        self,
        settings: Settings,
        *,
        jobs: JobsService,
        storage: StorageService,
        credits: CreditsService,
        run_pipeline: RunPipeline | None = None,
    ) -> None:
        self._settings = settings
        self._jobs = jobs
        self._storage = storage
        self._credits = credits
        self._run: RunPipeline = (
            run_pipeline if run_pipeline is not None else get_pipeline(settings)
        )
        self._tasks: set[asyncio.Task[None]] = set()
        self._cancelled: set[UUID] = set()
        self._active: set[UUID] = set()

    async def dispatch(
        self, job_id: UUID, user_id: UUID, input_key: str, options: PipelineOptions
    ) -> None:
        task = asyncio.create_task(
            self._process(job_id, user_id, input_key, options), name=f"job-{job_id}"
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def cancel(self, job_id: UUID) -> bool:
        """Stops the pipeline at its next progress report. ``False`` once it has started."""
        self._cancelled.add(job_id)
        return job_id not in self._active

    async def aclose(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _process(
        self, job_id: UUID, user_id: UUID, input_key: str, options: PipelineOptions
    ) -> None:
        loop = asyncio.get_running_loop()
        try:
            audio = await self._storage.download_bytes(input_key)
        except Exception:
            log.exception("job input unavailable", extra={"job_id": str(job_id)})
            await self._fail(job_id, INTERNAL_ERROR, "The job input could not be read.")
            return

        updates: asyncio.Queue[tuple[str, float] | None] = asyncio.Queue()

        def progress(stage: str, fraction: float) -> None:
            if job_id in self._cancelled:
                raise _Cancelled()
            loop.call_soon_threadsafe(updates.put_nowait, (stage, fraction))

        pump = asyncio.create_task(self._pump(job_id, updates))
        self._active.add(job_id)
        failure: tuple[str, str] | None = None
        result = None
        try:
            result = await loop.run_in_executor(None, self._run, audio, options, progress)
        except _Cancelled:
            pass
        except PipelineError as exc:
            failure = (exc.code, exc.message)
        except Exception:
            log.exception("pipeline crashed", extra={"job_id": str(job_id)})
            failure = (INTERNAL_ERROR, "The pipeline failed.")
        finally:
            updates.put_nowait(None)
            await pump
            self._active.discard(job_id)

        if job_id in self._cancelled:
            self._cancelled.discard(job_id)
            return
        if failure is not None or result is None:
            await self._fail(job_id, *(failure or (INTERNAL_ERROR, "The pipeline failed.")))
            return
        try:
            job_result = await package_result(
                job_id,
                user_id,
                result,
                storage=self._storage,
                credits=self._credits,
                signed_url_ttl_seconds=self._settings.signed_url_ttl_seconds,
            )
            await self._jobs.complete(job_id, job_result)
        except Exception:
            log.exception("result packaging failed", extra={"job_id": str(job_id)})
            await self._fail(job_id, INTERNAL_ERROR, "The job result could not be stored.")

    async def _pump(self, job_id: UUID, updates: asyncio.Queue[tuple[str, float] | None]) -> None:
        while (item := await updates.get()) is not None:
            try:
                await self._jobs.set_progress(job_id, *item)
            except Exception:
                log.warning("progress update failed", extra={"job_id": str(job_id)})

    async def _fail(self, job_id: UUID, code: str, message: str) -> None:
        try:
            await self._jobs.fail(job_id, code, message)
        except ApiException as exc:  # already cancelled or finished: nothing to release
            log.info("fail_job rejected", extra={"job_id": str(job_id), "code": exc.code})


class ModalDispatch:
    def __init__(self, settings: Settings) -> None:
        self._app_name = settings.modal_app_name
        self._calls: dict[UUID, str] = {}

    async def dispatch(
        self, job_id: UUID, user_id: UUID, input_key: str, options: PipelineOptions
    ) -> None:
        try:
            import modal  # noqa: PLC0415 — optional dependency, only needed on this path
        except ImportError as exc:
            raise ApiException(WORKER_UNAVAILABLE, message="Modal SDK is not installed.") from exc
        if not self._app_name:
            raise ApiException(WORKER_UNAVAILABLE, message="MODAL_APP_NAME is not configured.")
        message = job_message(job_id, user_id, input_key, options)
        try:
            worker = modal.Cls.from_name(self._app_name, MODAL_CLASS_NAME)()
            call = await worker.run.spawn.aio(
                message["job_id"],
                message["options"],
                user_id=message["user_id"],
                input_key=message["input_key"],
            )
        except Exception as exc:
            log.warning("modal spawn failed", extra={"job_id": str(job_id)}, exc_info=exc)
            raise ApiException(WORKER_UNAVAILABLE, message="Modal worker unavailable.") from exc
        self._calls[job_id] = call.object_id

    async def cancel(self, job_id: UUID) -> bool:
        call_id = self._calls.pop(job_id, None)
        if call_id is None:
            return False
        try:
            import modal  # noqa: PLC0415

            await modal.FunctionCall.from_id(call_id).cancel.aio()
        except Exception as exc:
            log.warning("modal cancel failed", extra={"job_id": str(job_id)}, exc_info=exc)
            return False
        return True


class RunPodDispatch:
    def __init__(self, settings: Settings, *, http: httpx.AsyncClient | None = None) -> None:
        self._endpoint_id = settings.runpod_endpoint_id
        self._api_key = settings.runpod_api_key.get_secret_value()
        self._http = http
        self._runs: dict[UUID, str] = {}

    @property
    def configured(self) -> bool:
        return bool(self._endpoint_id and self._api_key)

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=30.0)
        return self._http

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()

    async def dispatch(
        self, job_id: UUID, user_id: UUID, input_key: str, options: PipelineOptions
    ) -> None:
        if not self.configured:
            raise ApiException(
                WORKER_UNAVAILABLE, message="RUNPOD_ENDPOINT_ID / RUNPOD_API_KEY are not set."
            )
        try:
            response = await self._client().post(
                f"{RUNPOD_API_BASE}/{self._endpoint_id}/run",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"input": job_message(job_id, user_id, input_key, options)},
            )
        except httpx.HTTPError as exc:
            raise ApiException(WORKER_UNAVAILABLE, message="RunPod unreachable.") from exc
        if response.status_code >= 400:
            log.warning("runpod run rejected", extra={"status": response.status_code})
            raise ApiException(WORKER_UNAVAILABLE, message="RunPod rejected the job.")
        run_id = response.json().get("id") if response.content else None
        if isinstance(run_id, str):
            self._runs[job_id] = run_id

    async def cancel(self, job_id: UUID) -> bool:
        run_id = self._runs.pop(job_id, None)
        if run_id is None or not self.configured:
            return False
        try:
            response = await self._client().post(
                f"{RUNPOD_API_BASE}/{self._endpoint_id}/cancel/{run_id}",
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
        except httpx.HTTPError:
            return False
        return response.status_code < 400


__all__ = [
    "MODAL_CLASS_NAME",
    "RUNPOD_API_BASE",
    "LocalDispatch",
    "ModalDispatch",
    "RunPodDispatch",
    "job_message",
]
