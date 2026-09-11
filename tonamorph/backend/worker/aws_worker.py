"""SQS consumer for the ECS GPU service (contract §10): ``python -m worker.aws_worker``.

Models are warmed up (``warm_up_pipeline``) before the first poll, so a cold worker
never holds a message while it downloads weights. Each received message is then made
invisible for the full ``SQS_VISIBILITY_SECONDS`` before any work starts — the queue's
own timeout may be shorter and the timer thread's first reset is one interval away —
and kept invisible by that thread while the job runs. Long-polls ``SQS_JOB_QUEUE_URL``
(``WaitTimeSeconds=20``) and finishes with ``complete_job`` or ``fail_job`` (both
idempotent) followed by ``DeleteMessage``. Input the pipeline
rejects fails the job and deletes the message; any other failure leaves the message
in the queue so SQS redelivers it and moves it to the DLQ after
``SQS_MAX_RECEIVE_COUNT`` (3) receives — the job is marked failed on the last attempt,
and the reaper releases the credit of anything that slips through.

Options: ``--once`` polls a single time, ``--max-messages N`` exits after N messages;
SIGTERM/SIGINT finish the current job and stop.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import socket
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.config import Settings, get_settings
from app.errors import INTERNAL_ERROR
from app.pipeline import PipelineError
from app.pipeline.base import RunPipeline
from app.services.aws.queue import (
    VisibilityExtender,
    decode_job_message,
    delete_message,
    extend_visibility,
    receive_messages,
)
from worker.common import (
    INTERNAL_ERROR_MESSAGE,
    JobSpec,
    WorkerServices,
    build_services,
    current_status,
    execute_job,
    fail_job,
    is_terminal,
    load_pipeline,
    warm_up_pipeline,
)

log = logging.getLogger("tonamorph.worker.aws")

DEFAULT_WAIT_SECONDS = 20
DEFAULT_VISIBILITY_SECONDS = 300
DEFAULT_MAX_RECEIVE_COUNT = 3

OUTCOME_SUCCEEDED = "succeeded"
OUTCOME_FAILED = "failed"
OUTCOME_RETRY = "retry"
OUTCOME_SKIPPED = "skipped"
OUTCOME_DROPPED = "dropped"


@dataclass(frozen=True)
class WorkerConfig:
    queue_url: str
    wait_seconds: int = DEFAULT_WAIT_SECONDS
    visibility_seconds: int = DEFAULT_VISIBILITY_SECONDS
    max_receive_count: int = DEFAULT_MAX_RECEIVE_COUNT
    extend_interval_seconds: float | None = None
    worker_ref: str = field(default_factory=socket.gethostname)

    @classmethod
    def from_env(cls, settings: Settings) -> WorkerConfig:
        if not settings.sqs_job_queue_url:
            raise ValueError("SQS_JOB_QUEUE_URL is required for the aws worker")
        return cls(
            queue_url=settings.sqs_job_queue_url,
            visibility_seconds=int(
                os.environ.get("SQS_VISIBILITY_SECONDS", DEFAULT_VISIBILITY_SECONDS)
            ),
            max_receive_count=int(
                os.environ.get("SQS_MAX_RECEIVE_COUNT", DEFAULT_MAX_RECEIVE_COUNT)
            ),
        )


def _receive_count(message: dict[str, Any]) -> int:
    try:
        return max(1, int(message.get("Attributes", {}).get("ApproximateReceiveCount", 1)))
    except (TypeError, ValueError):
        return 1


def _claim(sqs: Any, config: WorkerConfig, receipt: str) -> None:
    """Hide the message for the full window now, before the job (and on a cold worker
    with ``--no-warm-up``, the model load) starts; the extender takes over from there."""
    try:
        extend_visibility(sqs, config.queue_url, receipt, config.visibility_seconds)
    except Exception as exc:
        log.warning("could not claim message visibility up front", exc_info=exc)


def _release(sqs: Any, config: WorkerConfig, receipt: str) -> None:
    """Make the message visible again immediately so the retry (or the DLQ move) does
    not wait for the visibility timeout."""
    try:
        extend_visibility(sqs, config.queue_url, receipt, 0)
    except Exception as exc:
        log.warning("could not reset message visibility", exc_info=exc)


async def process_message(
    message: dict[str, Any],
    *,
    sqs: Any,
    config: WorkerConfig,
    services: WorkerServices,
    settings: Settings,
    run: RunPipeline,
) -> str:
    """Handle one received message; returns one of the ``OUTCOME_*`` strings."""
    receipt = message["ReceiptHandle"]
    attempt = _receive_count(message)
    try:
        job = decode_job_message(message["Body"])
    except (KeyError, ValueError) as exc:
        log.error("dropping malformed job message: %s", exc)
        delete_message(sqs, config.queue_url, receipt)
        return OUTCOME_DROPPED
    spec = JobSpec(
        job_id=job.job_id, user_id=job.user_id, options=job.options, input_key=job.input_key
    )
    log_extra = {"job_id": str(spec.job_id), "attempt": attempt}
    outcome = OUTCOME_RETRY
    _claim(sqs, config, receipt)
    extender = VisibilityExtender(
        sqs,
        config.queue_url,
        receipt,
        visibility_seconds=config.visibility_seconds,
        interval_seconds=config.extend_interval_seconds,
    )
    with extender:
        try:
            status = await current_status(services.jobs, spec)
            if is_terminal(status):
                assert status is not None
                log.info("skipping job already %s", status.status, extra=log_extra)
                outcome = OUTCOME_SKIPPED
            else:
                await execute_job(
                    services, settings, spec, run, worker_ref=config.worker_ref
                )
                outcome = OUTCOME_SUCCEEDED
        except PipelineError as exc:
            log.warning("job rejected: %s (%s)", exc.message, exc.code, extra=log_extra)
            await fail_job(services.jobs, spec.job_id, exc.code, exc.message)
            outcome = OUTCOME_FAILED
        except Exception as exc:
            log.error("job attempt %d failed", attempt, extra=log_extra, exc_info=exc)
            if attempt >= config.max_receive_count:
                try:
                    await fail_job(
                        services.jobs, spec.job_id, INTERNAL_ERROR, INTERNAL_ERROR_MESSAGE
                    )
                except Exception as fail_exc:
                    log.error("fail_job failed", extra=log_extra, exc_info=fail_exc)
            outcome = OUTCOME_RETRY
    if outcome == OUTCOME_RETRY:
        _release(sqs, config, receipt)
    else:
        delete_message(sqs, config.queue_url, receipt)
    return outcome


async def run_loop(
    *,
    sqs: Any,
    config: WorkerConfig,
    services: WorkerServices,
    settings: Settings,
    run: RunPipeline,
    once: bool = False,
    max_messages: int | None = None,
    stop: asyncio.Event | None = None,
) -> int:
    """Poll until stopped; returns the number of messages handled."""
    stop = stop if stop is not None else asyncio.Event()
    handled = 0
    while not stop.is_set():
        messages = await asyncio.to_thread(
            receive_messages, sqs, config.queue_url, 1, config.wait_seconds
        )
        for message in messages:
            await process_message(
                message, sqs=sqs, config=config, services=services, settings=settings, run=run
            )
            handled += 1
            if max_messages is not None and handled >= max_messages:
                return handled
        if once:
            break
    return handled


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="worker.aws_worker", description=__doc__)
    parser.add_argument("--once", action="store_true", help="poll once, then exit")
    parser.add_argument(
        "--max-messages", type=int, default=None, help="exit after handling this many messages"
    )
    parser.add_argument("--no-warm-up", action="store_true", help="skip model warm-up")
    args = parser.parse_args(argv)
    if args.max_messages is not None and args.max_messages < 1:
        parser.error("--max-messages must be >= 1")
    return args


async def _serve(
    *,
    sqs: Any,
    config: WorkerConfig,
    services: WorkerServices,
    settings: Settings,
    run: RunPipeline,
    once: bool,
    max_messages: int | None,
) -> int:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    return await run_loop(
        sqs=sqs,
        config=config,
        services=services,
        settings=settings,
        run=run,
        once=once,
        max_messages=max_messages,
        stop=stop,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    os.environ.setdefault("SERVICE_ROLE", "worker")
    settings = get_settings()
    try:
        config = WorkerConfig.from_env(settings)
    except ValueError as exc:
        log.error("%s", exc)
        return 64
    import boto3

    sqs = boto3.client("sqs", region_name=settings.aws_region)
    services = build_services(settings)
    run = load_pipeline(settings)
    if not args.no_warm_up:
        warm_up_pipeline(settings)
    log.info(
        "worker %s polling %s (pipeline=%s)",
        config.worker_ref,
        config.queue_url,
        settings.tonamorph_pipeline,
    )
    handled = asyncio.run(
        _serve(
            sqs=sqs,
            config=config,
            services=services,
            settings=settings,
            run=run,
            once=args.once,
            max_messages=args.max_messages,
        )
    )
    log.info("worker stopped after %d message(s)", handled)
    return 0


if __name__ == "__main__":
    sys.exit(main())
