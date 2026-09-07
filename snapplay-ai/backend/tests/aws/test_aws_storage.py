"""S3StorageService: round-trip, presigned/CloudFront URL shape, R2 endpoint, key guard."""

from __future__ import annotations

import base64
import json
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

from app.config import Settings
from app.services.aws.storage import InvalidStorageKey, S3StorageService, validate_key

USER = str(uuid4())
JOB = str(uuid4())
BAD_KEYS = [
    "",
    "/jobs/{u}/{j}/input.wav",
    "jobs/{u}/{j}/../other.wav",
    "../jobs/{u}/{j}/input.wav",
    "jobs/{u}/../{j}/input.wav",
    "jobs\\{u}\\{j}\\input.wav",
    "jobs/{u}/{j}/input.wav\n",
    "jobs/{u}/{j}/in\x00put.wav",
    "jobs/{u}/{j}/in\x1bput.wav",
    "jobs/{u}/{j}/in put.wav",
    "jobs/{u}/{j}/.hidden",
    "jobs/{u}/{j}//input.wav",
    "jobs/{u}/{j}/",
    "jobs/{u}/{j}",
    "jobs/{u}/input.wav",
    "jobs/not-a-uuid/{j}/input.wav",
    "jobs/{u}/{J}/input.wav",
    "results/{u}/{j}/input.wav",
    "JOBS/{u}/{j}/input.wav",
    "jobs/{u}/{j}/" + "a" * 1024,
]

MakeSettings = Callable[..., Settings]
JobKey = Callable[[str], str]


async def test_upload_download_round_trip(
    storage: S3StorageService, s3: Any, job_key: JobKey
) -> None:
    key = job_key("input.wav")
    payload = b"RIFF" + bytes(range(256))

    assert await storage.upload_bytes(key, payload, "audio/wav") == key
    assert await storage.download_bytes(key) == payload
    assert s3.head_object(Bucket=storage.bucket, Key=key)["ContentType"] == "audio/wav"


async def test_download_missing_object_raises(storage: S3StorageService, job_key: JobKey) -> None:
    with pytest.raises(FileNotFoundError):
        await storage.download_bytes(job_key("missing.wav"))


async def test_presigned_url_shape(storage: S3StorageService, job_key: JobKey) -> None:
    key = job_key("stems/bass.wav")
    await storage.upload_bytes(key, b"x", "audio/wav")

    url = urlparse(await storage.signed_url(key, 3600))
    query = parse_qs(url.query)

    assert url.scheme == "https"
    assert url.hostname is not None and url.hostname.endswith(".amazonaws.com")
    assert url.path.endswith("/" + key)
    assert query["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"]
    assert query["X-Amz-Expires"] == ["3600"]
    assert query["X-Amz-Signature"] and query["X-Amz-Credential"]


async def test_signed_url_rejects_non_positive_ttl(
    storage: S3StorageService, job_key: JobKey
) -> None:
    with pytest.raises(ValueError):
        await storage.signed_url(job_key("x.wav"), 0)


async def test_endpoint_url_uses_path_style_and_round_trips(
    s3: Any, make_settings: MakeSettings, job_key: JobKey, r2_endpoint: str
) -> None:
    storage = S3StorageService(make_settings(s3_endpoint_url=r2_endpoint))
    key = job_key("input.flac")

    assert storage.endpoint_url == r2_endpoint
    assert storage._client.meta.endpoint_url == r2_endpoint
    url = await storage.signed_url(key, 60)
    assert url.startswith(f"{r2_endpoint}/{storage.bucket}/{key}?")

    await storage.upload_bytes(key, b"fLaC", "audio/flac")
    assert await storage.download_bytes(key) == b"fLaC"
    assert s3.head_object(Bucket=storage.bucket, Key=key)["ContentLength"] == 4


def test_missing_bucket_rejected(make_settings: MakeSettings) -> None:
    with pytest.raises(ValueError, match="S3_BUCKET"):
        S3StorageService(make_settings(s3_bucket=""))


def test_validate_key_accepts_job_keys() -> None:
    for name in ("input.wav", "stems/bass.wav", "score.mid", "a-b_c.d/e-f_g.h"):
        key = f"jobs/{USER}/{JOB}/{name}"
        assert validate_key(key) == key


@pytest.mark.parametrize("template", BAD_KEYS)
async def test_key_escape_attempts_rejected(
    storage: S3StorageService, s3: Any, template: str
) -> None:
    key = template.format(u=USER, j=JOB, J=JOB.upper())

    with pytest.raises(InvalidStorageKey):
        validate_key(key)
    with pytest.raises(InvalidStorageKey):
        await storage.upload_bytes(key, b"x", "audio/wav")
    with pytest.raises(InvalidStorageKey):
        await storage.download_bytes(key)
    with pytest.raises(InvalidStorageKey):
        await storage.signed_url(key, 60)
    assert "Contents" not in s3.list_objects_v2(Bucket=storage.bucket)


# --- CloudFront ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def rsa_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def rsa_pem(rsa_key: rsa.RSAPrivateKey) -> str:
    return _pem(rsa_key)


def _pem(key: Any) -> str:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


def _cloudfront(make_settings: MakeSettings, pem: str, **overrides: Any) -> S3StorageService:
    return S3StorageService(
        make_settings(
            cloudfront_domain="cdn.example.test",
            cloudfront_key_pair_id="K2JCJMDEHXQW5F",
            cloudfront_private_key=pem,
            **overrides,
        )
    )


def _cloudfront_b64decode(value: str) -> bytes:
    return base64.b64decode(value.replace("-", "+").replace("_", "=").replace("~", "/"))


async def test_cloudfront_signed_url(
    make_settings: MakeSettings, job_key: JobKey, rsa_key: rsa.RSAPrivateKey, rsa_pem: str
) -> None:
    storage = _cloudfront(make_settings, rsa_pem)
    key = job_key("stems/drums.wav")

    url = await storage.signed_url(key, 3600)
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https" and parsed.hostname == "cdn.example.test"
    assert parsed.path == "/" + key
    assert query["Key-Pair-Id"] == ["K2JCJMDEHXQW5F"]
    expires = int(query["Expires"][0])
    # The canned policy CloudFront reconstructs from the URL's Expires parameter.
    resource = f"https://cdn.example.test/{key}"
    policy = json.dumps(
        {"Statement": [{"Resource": resource, "Condition": {"DateLessThan": {"AWS:EpochTime": expires}}}]},
        separators=(",", ":"),
    ).encode()
    rsa_key.public_key().verify(
        _cloudfront_b64decode(query["Signature"][0]), policy, padding.PKCS1v15(), hashes.SHA1()
    )


async def test_cloudfront_pem_with_escaped_newlines(
    make_settings: MakeSettings, job_key: JobKey, rsa_pem: str
) -> None:
    storage = _cloudfront(make_settings, rsa_pem.replace("\n", "\\n"))
    url = await storage.signed_url(job_key("score.mid"), 60)
    assert url.startswith("https://cdn.example.test/jobs/")


def test_cloudfront_partial_config_rejected(make_settings: MakeSettings, rsa_pem: str) -> None:
    with pytest.raises(ValueError, match="CLOUDFRONT"):
        _cloudfront(make_settings, rsa_pem, cloudfront_key_pair_id="")


def test_cloudfront_non_rsa_key_rejected(make_settings: MakeSettings) -> None:
    with pytest.raises(ValueError, match="RSA"):
        _cloudfront(make_settings, _pem(ec.generate_private_key(ec.SECP256R1())))
