"""S3-compatible object storage for job inputs and results (contract §10).

Objects live under ``jobs/<user_id>/<job_id>/``; :func:`validate_key` refuses every
other key so a caller can never read or write outside a job's own prefix. Read URLs
are S3 presigned GETs, or CloudFront signed URLs (canned policy) when the CloudFront
settings are configured. boto3 is synchronous, so each call runs in a worker thread.
"""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from botocore.signers import CloudFrontSigner
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.config import Settings

MAX_KEY_LENGTH = 1024  # S3 limit
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
# jobs/<user uuid>/<job uuid>/<one or more segments>; a segment is [A-Za-z0-9._-] and
# cannot start with a dot, which rules out ".", "..", hidden files, "//", backslashes,
# whitespace, control characters, absolute paths and any other prefix.
_KEY_RE = re.compile(rf"jobs/{_UUID}/{_UUID}(?:/[A-Za-z0-9_-][A-Za-z0-9._-]*)+")
_MISSING_OBJECT_CODES = frozenset({"NoSuchKey", "404"})


class InvalidStorageKey(ValueError):
    """The key would escape ``jobs/<user_id>/<job_id>/`` or contains unsafe characters."""


def validate_key(path: str) -> str:
    """Return ``path`` unchanged when it is a well-formed job object key, else raise
    :class:`InvalidStorageKey`. Ids must be the canonical lowercase ``str(uuid)``."""
    if len(path) > MAX_KEY_LENGTH or _KEY_RE.fullmatch(path) is None:
        raise InvalidStorageKey("storage key must be jobs/<user_id>/<job_id>/<name>")
    return path


def _normalise_pem(pem: str) -> str:
    # Secret managers often deliver multi-line PEMs with literal "\n" sequences.
    if "\n" not in pem and "\\n" in pem:
        pem = pem.replace("\\n", "\n")
    return pem


class _CloudFrontUrls:
    """Signs ``https://<domain>/<key>`` with a canned policy (RSA-SHA1, PKCS#1 v1.5),
    the only scheme CloudFront accepts for signed URLs."""

    def __init__(self, domain: str, key_pair_id: str, private_key_pem: str) -> None:
        self.domain = domain.removeprefix("https://").strip("/")
        key = serialization.load_pem_private_key(
            _normalise_pem(private_key_pem).encode("utf-8"), password=None
        )
        if not isinstance(key, rsa.RSAPrivateKey):
            raise ValueError("CLOUDFRONT_PRIVATE_KEY must be an RSA private key")
        self._key = key
        self._signer = CloudFrontSigner(key_pair_id, self._rsa_sign)

    @classmethod
    def from_settings(cls, settings: Settings) -> _CloudFrontUrls | None:
        pem = settings.cloudfront_private_key.get_secret_value()
        values = (settings.cloudfront_domain, settings.cloudfront_key_pair_id, pem)
        if not any(values):
            return None
        if not all(values):
            raise ValueError(
                "CLOUDFRONT_DOMAIN, CLOUDFRONT_KEY_PAIR_ID and CLOUDFRONT_PRIVATE_KEY "
                "must be configured together"
            )
        return cls(settings.cloudfront_domain, settings.cloudfront_key_pair_id, pem)

    def _rsa_sign(self, message: bytes) -> bytes:
        return self._key.sign(message, padding.PKCS1v15(), hashes.SHA1())

    def sign(self, key: str, ttl_seconds: int) -> str:
        expires = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        return self._signer.generate_presigned_url(
            f"https://{self.domain}/{key}", date_less_than=expires
        )


class S3StorageService:
    """:class:`app.services.StorageService` on S3, Cloudflare R2 or any S3-compatible
    store. ``S3_ENDPOINT_URL`` switches to that endpoint with path-style addressing."""

    def __init__(self, settings: Settings, *, client: Any | None = None) -> None:
        if not settings.s3_bucket:
            raise ValueError("S3_BUCKET is required for the s3 storage backend")
        self.bucket = settings.s3_bucket
        self.endpoint_url = settings.s3_endpoint_url or None
        self._client = client if client is not None else self._make_client(settings)
        self._cloudfront = _CloudFrontUrls.from_settings(settings)

    @staticmethod
    def _make_client(settings: Settings) -> Any:
        endpoint_url = settings.s3_endpoint_url or None
        config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path" if endpoint_url else "auto"},
            retries={"max_attempts": 3, "mode": "standard"},
        )
        return boto3.client(
            "s3", region_name=settings.aws_region, endpoint_url=endpoint_url, config=config
        )

    async def upload_bytes(self, path: str, data: bytes, content_type: str) -> str:
        key = validate_key(path)
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    async def download_bytes(self, path: str) -> bytes:
        """Raises :class:`FileNotFoundError` when the object does not exist."""
        return await asyncio.to_thread(self._get_object_bytes, validate_key(path))

    def _get_object_bytes(self, key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in _MISSING_OBJECT_CODES:
                raise FileNotFoundError(key) from exc
            raise
        with response["Body"] as body:
            return body.read()

    async def signed_url(self, path: str, ttl_seconds: int) -> str:
        key = validate_key(path)
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if self._cloudfront is not None:
            return self._cloudfront.sign(key, ttl_seconds)
        # Presigning is offline, but credential resolution may hit the instance metadata
        # service on first use, so keep it off the event loop too.
        return await asyncio.to_thread(
            self._client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=ttl_seconds,
        )


__all__ = ["InvalidStorageKey", "MAX_KEY_LENGTH", "S3StorageService", "validate_key"]
