"""SqsDispatch and the worker-side helpers against moto SQS."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import pytest

from app.config import Settings
from app.errors import WORKER_UNAVAILABLE, ApiException
from app.schemas import PipelineOptions
from app.services.aws.queue import (
    SqsDispatch,
    VisibilityExtender,
    decode_job_message,
    delete_message,
    encode_job_message,
    extend_visibility,
    receive_messages,
)

OPTIONS = PipelineOptions(stems=["bass", "drums"], transcribe=["bass"], drum_slices=False)
MISSING_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789012/does-not-exist"

MakeSettings = Callable[..., Settings]
JobKey = Callable[[str], str]


@pytest.fixture
def dispatcher(make_settings: MakeSettings) -> Callable[[str], SqsDispatch]:
    return lambda queue_url: SqsDispatch(make_settings(sqs_job_queue_url=queue_url))


def expected_body(job_id: Any, user_id: Any, input_key: str) -> dict[str, Any]:
    return {
        "job_id": str(job_id),
        "user_id": str(user_id),
        "input_key": input_key,
        "options": {
            "stems": ["bass", "drums"],
            "transcribe": ["bass"],
            "drum_slices": False,
            "target_root_midi": 48,
            "max_seconds": 60.0,
        },
    }


def queue_counts(sqs: Any, queue_url: str) -> tuple[str, str]:
    attributes = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
    )["Attributes"]
    return (
        attributes["ApproximateNumberOfMessages"],
        attributes["ApproximateNumberOfMessagesNotVisible"],
    )


async def test_dispatch_standard_round_trip(
    sqs: Any, standard_queue: str, dispatcher: Callable[[str], SqsDispatch], job_key: JobKey
) -> None:
    service = dispatcher(standard_queue)
    job_id, user_id, input_key = uuid4(), uuid4(), job_key("input.wav")
    assert service.fifo is False

    await service.dispatch(job_id, user_id, input_key, OPTIONS)
    messages = receive_messages(sqs, standard_queue, wait_seconds=0)

    assert len(messages) == 1
    message = messages[0]
    assert json.loads(message["Body"]) == expected_body(job_id, user_id, input_key)
    assert "MessageGroupId" not in message["Attributes"]
    decoded = decode_job_message(message["Body"])
    assert (decoded.job_id, decoded.user_id, decoded.input_key) == (job_id, user_id, input_key)
    assert decoded.options == OPTIONS
    assert queue_counts(sqs, standard_queue) == ("0", "1")

    delete_message(sqs, standard_queue, message["ReceiptHandle"])
    assert queue_counts(sqs, standard_queue) == ("0", "0")


async def test_dispatch_fifo_round_trip_and_dedup(
    sqs: Any, fifo_queue: str, dispatcher: Callable[[str], SqsDispatch], job_key: JobKey
) -> None:
    service = dispatcher(fifo_queue)
    job_id, user_id, input_key = uuid4(), uuid4(), job_key("input.wav")
    assert service.fifo is True

    await service.dispatch(job_id, user_id, input_key, OPTIONS)
    await service.dispatch(job_id, user_id, input_key, OPTIONS)
    messages = receive_messages(sqs, fifo_queue, max_messages=10, wait_seconds=0)

    assert len(messages) == 1
    message = messages[0]
    assert json.loads(message["Body"]) == expected_body(job_id, user_id, input_key)
    assert message["Attributes"]["MessageGroupId"] == str(job_id)
    assert message["Attributes"]["MessageDeduplicationId"] == str(job_id)


async def test_cancel_is_not_supported(
    standard_queue: str, dispatcher: Callable[[str], SqsDispatch]
) -> None:
    assert await dispatcher(standard_queue).cancel(uuid4()) is False


async def test_dispatch_failure_maps_to_worker_unavailable(
    dispatcher: Callable[[str], SqsDispatch], job_key: JobKey
) -> None:
    with pytest.raises(ApiException) as info:
        await dispatcher(MISSING_QUEUE_URL).dispatch(uuid4(), uuid4(), job_key("x.wav"), OPTIONS)
    assert info.value.code == WORKER_UNAVAILABLE
    assert info.value.status == 503


def test_missing_queue_url_rejected(make_settings: MakeSettings) -> None:
    with pytest.raises(ValueError, match="SQS_JOB_QUEUE_URL"):
        SqsDispatch(make_settings(sqs_job_queue_url=""))


@pytest.mark.parametrize(
    "body",
    [
        "not json",
        "[]",
        '{"job_id": "x"}',
        json.dumps({"job_id": str(uuid4()), "user_id": "nope", "input_key": "k", "options": {}}),
        json.dumps(
            {
                "job_id": str(uuid4()),
                "user_id": str(uuid4()),
                "input_key": "k",
                "options": {"stems": []},
            }
        ),
    ],
)
def test_decode_rejects_malformed(body: str) -> None:
    with pytest.raises(ValueError):
        decode_job_message(body)


def test_encode_decode_symmetry() -> None:
    job_id, user_id = uuid4(), uuid4()
    decoded = decode_job_message(encode_job_message(job_id, user_id, "jobs/a/b/c", OPTIONS))
    assert decoded.job_id == job_id and decoded.user_id == user_id
    assert decoded.input_key == "jobs/a/b/c" and decoded.options == OPTIONS


async def test_extend_visibility_changes_message_visibility(
    sqs: Any, standard_queue: str, dispatcher: Callable[[str], SqsDispatch], job_key: JobKey
) -> None:
    await dispatcher(standard_queue).dispatch(uuid4(), uuid4(), job_key("x.wav"), OPTIONS)
    first = receive_messages(sqs, standard_queue, wait_seconds=0)
    assert len(first) == 1 and first[0]["Attributes"]["ApproximateReceiveCount"] == "1"
    assert receive_messages(sqs, standard_queue, wait_seconds=0) == []

    extend_visibility(sqs, standard_queue, first[0]["ReceiptHandle"], 0)
    time.sleep(0.01)

    again = receive_messages(sqs, standard_queue, wait_seconds=0)
    assert len(again) == 1
    assert again[0]["MessageId"] == first[0]["MessageId"]
    assert again[0]["Attributes"]["ApproximateReceiveCount"] == "2"


async def test_visibility_extender_keeps_message_hidden(
    sqs: Any, dispatcher: Callable[[str], SqsDispatch], job_key: JobKey
) -> None:
    queue_url = sqs.create_queue(
        QueueName="snapplay-jobs-short", Attributes={"VisibilityTimeout": "1"}
    )["QueueUrl"]
    await dispatcher(queue_url).dispatch(uuid4(), uuid4(), job_key("x.wav"), OPTIONS)
    (message,) = receive_messages(sqs, queue_url, wait_seconds=0)

    with VisibilityExtender(
        sqs, queue_url, message["ReceiptHandle"], visibility_seconds=30, interval_seconds=0.2
    ) as extender:
        time.sleep(1.3)
        assert receive_messages(sqs, queue_url, wait_seconds=0) == []
    assert extender.extensions >= 1 and extender.failures == 0

    extend_visibility(sqs, queue_url, message["ReceiptHandle"], 0)
    time.sleep(0.01)
    assert len(receive_messages(sqs, queue_url, wait_seconds=0)) == 1


def test_visibility_extender_survives_failures(sqs: Any, standard_queue: str) -> None:
    with VisibilityExtender(
        sqs, standard_queue, "bogus-receipt-handle", visibility_seconds=30, interval_seconds=0.05
    ) as extender:
        time.sleep(0.3)
    assert extender.failures >= 1 and extender.extensions == 0


def test_visibility_extender_rejects_bad_intervals(sqs: Any, standard_queue: str) -> None:
    with pytest.raises(ValueError):
        VisibilityExtender(sqs, standard_queue, "rh", visibility_seconds=0)
    with pytest.raises(ValueError):
        VisibilityExtender(sqs, standard_queue, "rh", interval_seconds=0)


async def test_message_lands_in_dlq_after_three_receives(
    sqs: Any,
    queue_with_dlq: tuple[str, str],
    dispatcher: Callable[[str], SqsDispatch],
    job_key: JobKey,
) -> None:
    queue_url, dlq_url = queue_with_dlq
    job_id = uuid4()
    await dispatcher(queue_url).dispatch(job_id, uuid4(), job_key("x.wav"), OPTIONS)

    for attempt in (1, 2, 3):
        time.sleep(0.01)
        (message,) = receive_messages(sqs, queue_url, wait_seconds=0)
        assert message["Attributes"]["ApproximateReceiveCount"] == str(attempt)
        assert receive_messages(sqs, dlq_url, wait_seconds=0) == []

    time.sleep(0.01)
    assert receive_messages(sqs, queue_url, wait_seconds=0) == []
    dead = receive_messages(sqs, dlq_url, wait_seconds=0)
    assert len(dead) == 1
    assert decode_job_message(dead[0]["Body"]).job_id == job_id
