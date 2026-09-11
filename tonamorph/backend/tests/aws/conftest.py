"""moto-backed AWS fixtures. Nothing here reaches the network: every test runs inside
``mock_aws`` with fake credentials and an explicit default region."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from typing import Any
from uuid import uuid4

import boto3
import pytest
from moto import mock_aws

from app.config import Settings
from app.services.aws.storage import S3StorageService

REGION = "us-east-1"
BUCKET = "tonamorph-test"
# A Cloudflare R2-style endpoint moto intercepts once listed in MOTO_S3_CUSTOM_ENDPOINTS.
R2_ENDPOINT = "https://r2.example.test"

FAKE_AWS_ENV = {
    "AWS_DEFAULT_REGION": REGION,
    "AWS_ACCESS_KEY_ID": "testing",
    "AWS_SECRET_ACCESS_KEY": "testing",
    "AWS_SECURITY_TOKEN": "testing",
    "AWS_SESSION_TOKEN": "testing",
}


def pytest_configure(config: pytest.Config) -> None:
    # moto reads this when it first imports its S3 routes, which happens on the first
    # mock_aws() start — after this hook — so the custom endpoint is always registered.
    os.environ.setdefault("MOTO_S3_CUSTOM_ENDPOINTS", R2_ENDPOINT)


@pytest.fixture(autouse=True)
def aws_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key, value in FAKE_AWS_ENV.items():
        monkeypatch.setenv(key, value)
    for key in ("AWS_PROFILE", "AWS_ENDPOINT_URL", "AWS_ENDPOINT_URL_S3", "AWS_ENDPOINT_URL_SQS"):
        monkeypatch.delenv(key, raising=False)
    with mock_aws():
        yield


@pytest.fixture
def make_settings() -> Callable[..., Settings]:
    """``make_settings(**overrides)``: offline settings for the s3 backend."""

    def _make(**overrides: Any) -> Settings:
        base: dict[str, Any] = {
            "_env_file": None,
            "env": "test",
            "aws_region": REGION,
            "s3_bucket": BUCKET,
            "storage_backend": "s3",
        }
        return Settings(**{**base, **overrides})

    return _make


@pytest.fixture
def job_key() -> Callable[[str], str]:
    """``job_key(name)``: a well-formed ``jobs/<user_id>/<job_id>/<name>`` key."""
    return lambda name="input.wav": f"jobs/{uuid4()}/{uuid4()}/{name}"


@pytest.fixture
def r2_endpoint() -> str:
    return R2_ENDPOINT


@pytest.fixture
def s3() -> Any:
    client = boto3.client("s3", region_name=REGION)
    client.create_bucket(Bucket=BUCKET)
    return client


@pytest.fixture
def storage(s3: Any, make_settings: Callable[..., Settings]) -> S3StorageService:
    return S3StorageService(make_settings())


@pytest.fixture
def sqs() -> Any:
    return boto3.client("sqs", region_name=REGION)


@pytest.fixture
def standard_queue(sqs: Any) -> str:
    return sqs.create_queue(QueueName="tonamorph-jobs", Attributes={"VisibilityTimeout": "60"})[
        "QueueUrl"
    ]


@pytest.fixture
def fifo_queue(sqs: Any) -> str:
    return sqs.create_queue(
        QueueName="tonamorph-jobs.fifo",
        Attributes={"FifoQueue": "true", "VisibilityTimeout": "60"},
    )["QueueUrl"]


@pytest.fixture
def queue_with_dlq(sqs: Any) -> tuple[str, str]:
    """``(queue_url, dlq_url)``: zero visibility timeout so every receive redelivers,
    redrive after 3 receives — the production queue's policy (INFRA_INTERFACES)."""
    dlq_url = sqs.create_queue(QueueName="tonamorph-jobs-dlq")["QueueUrl"]
    dlq_arn = sqs.get_queue_attributes(QueueUrl=dlq_url, AttributeNames=["QueueArn"])[
        "Attributes"
    ]["QueueArn"]
    queue_url = sqs.create_queue(
        QueueName="tonamorph-jobs-redrive",
        Attributes={
            "VisibilityTimeout": "0",
            "RedrivePolicy": f'{{"deadLetterTargetArn":"{dlq_arn}","maxReceiveCount":3}}',
        },
    )["QueueUrl"]
    return queue_url, dlq_url
