"""SQS job queue (contract §10): the API enqueues, ``worker/aws_worker.py`` consumes.

The message body is ``{"job_id", "user_id", "input_key", "options"}`` as JSON. On a
FIFO queue the job id serves as both deduplication id and message group: a retried
dispatch of the same job is dropped by SQS, and jobs never block each other.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import ValidationError

from app.config import Settings
from app.errors import WORKER_UNAVAILABLE, ApiException
from app.schemas import PipelineOptions

log = logging.getLogger("tonamorph.aws.queue")


@dataclass(frozen=True, slots=True)
class JobMessage:
    job_id: UUID
    user_id: UUID
    input_key: str
    options: PipelineOptions


def encode_job_message(
    job_id: UUID, user_id: UUID, input_key: str, options: PipelineOptions
) -> str:
    return json.dumps(
        {
            "job_id": str(job_id),
            "user_id": str(user_id),
            "input_key": input_key,
            "options": options.model_dump(mode="json"),
        },
        separators=(",", ":"),
    )


def decode_job_message(body: str) -> JobMessage:
    """Parse a queue message body; raises :class:`ValueError` for anything malformed."""
    try:
        payload = json.loads(body)
        return JobMessage(
            job_id=UUID(payload["job_id"]),
            user_id=UUID(payload["user_id"]),
            input_key=str(payload["input_key"]),
            options=PipelineOptions.model_validate(payload["options"]),
        )
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise ValueError("malformed job message") from exc


class SqsDispatch:
    """:class:`app.services.DispatchService` that enqueues jobs on ``SQS_JOB_QUEUE_URL``."""

    def __init__(self, settings: Settings, *, client: Any | None = None) -> None:
        if not settings.sqs_job_queue_url:
            raise ValueError("SQS_JOB_QUEUE_URL is required for the aws pipeline")
        self.queue_url = settings.sqs_job_queue_url
        self.fifo = self.queue_url.endswith(".fifo")
        self._client = (
            client if client is not None else boto3.client("sqs", region_name=settings.aws_region)
        )

    async def dispatch(
        self, job_id: UUID, user_id: UUID, input_key: str, options: PipelineOptions
    ) -> None:
        params: dict[str, Any] = {
            "QueueUrl": self.queue_url,
            "MessageBody": encode_job_message(job_id, user_id, input_key, options),
        }
        if self.fifo:
            params["MessageDeduplicationId"] = str(job_id)
            params["MessageGroupId"] = str(job_id)
        try:
            await asyncio.to_thread(self._client.send_message, **params)
        except (BotoCoreError, ClientError) as exc:
            log.warning("sqs send_message failed", extra={"job_id": str(job_id)}, exc_info=exc)
            raise ApiException(WORKER_UNAVAILABLE) from exc

    async def cancel(self, job_id: UUID) -> bool:
        # SQS cannot withdraw a queued message; the worker re-reads the job status before
        # processing and skips jobs that were cancelled meanwhile.
        return False


# --- Consumer helpers (worker/aws_worker.py) -------------------------------------------


def receive_messages(
    client: Any, queue_url: str, max_messages: int = 1, wait_seconds: int = 20
) -> list[dict[str, Any]]:
    """Long-poll up to ``max_messages``; each dict carries ``Body``, ``ReceiptHandle`` and
    ``Attributes`` (including ``ApproximateReceiveCount``)."""
    response = client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=max_messages,
        WaitTimeSeconds=wait_seconds,
        MessageSystemAttributeNames=["All"],
    )
    return response.get("Messages", [])


def extend_visibility(client: Any, queue_url: str, receipt_handle: str, seconds: int) -> None:
    """Hide the message for another ``seconds`` from now (``0`` makes it visible again)."""
    client.change_message_visibility(
        QueueUrl=queue_url, ReceiptHandle=receipt_handle, VisibilityTimeout=seconds
    )


def delete_message(client: Any, queue_url: str, receipt_handle: str) -> None:
    client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)


class VisibilityExtender:
    """Keeps a message invisible while the worker processes it.

    A daemon thread resets the visibility timeout to ``visibility_seconds`` every
    ``interval_seconds`` (default: a third of the timeout) so a job that outlives the
    queue's timeout is not redelivered to a second worker. Failures are counted and
    logged but never interrupt processing.
    """

    def __init__(
        self,
        client: Any,
        queue_url: str,
        receipt_handle: str,
        *,
        visibility_seconds: int = 300,
        interval_seconds: float | None = None,
    ) -> None:
        if visibility_seconds <= 0:
            raise ValueError("visibility_seconds must be positive")
        self._interval = (
            interval_seconds if interval_seconds is not None else visibility_seconds / 3
        )
        if self._interval <= 0:
            raise ValueError("interval_seconds must be positive")
        self._client = client
        self._queue_url = queue_url
        self._receipt_handle = receipt_handle
        self._visibility_seconds = visibility_seconds
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name="sqs-visibility-extender", daemon=True
        )
        self.extensions = 0
        self.failures = 0

    def __enter__(self) -> VisibilityExtender:
        self._thread.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.stop()

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join()

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                extend_visibility(
                    self._client, self._queue_url, self._receipt_handle, self._visibility_seconds
                )
                self.extensions += 1
            except (BotoCoreError, ClientError) as exc:
                self.failures += 1
                log.warning("sqs change_message_visibility failed", exc_info=exc)


__all__ = [
    "JobMessage",
    "SqsDispatch",
    "VisibilityExtender",
    "decode_job_message",
    "delete_message",
    "encode_job_message",
    "extend_visibility",
    "receive_messages",
]
