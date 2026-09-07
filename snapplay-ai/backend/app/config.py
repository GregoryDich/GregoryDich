"""Application settings (docs/API_CONTRACT.md §1, §4, §7, §10, §11, §12).

Every value comes from the environment (or a ``.env`` file in the working directory).
Secrets are ``SecretStr`` so they never appear in logs or reprs; call
``.get_secret_value()`` where the raw value is needed.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

StorageBackend = Literal["supabase", "s3", "memory"]
PipelineBackend = Literal["fake", "local", "modal", "runpod", "aws"]
Environment = Literal["development", "test", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    env: Environment = "development"

    # Supabase (auth + Postgres)
    supabase_url: str = ""
    supabase_service_role_key: SecretStr = SecretStr("")
    supabase_anon_key: str = ""
    supabase_jwt_secret: SecretStr = SecretStr("")
    supabase_jwks_url: str = ""

    # Storage
    storage_backend: StorageBackend = "memory"
    storage_bucket: str = "jobs"
    signed_url_ttl_seconds: int = Field(default=86400, gt=0)

    # AWS production path
    aws_region: str = "us-east-1"
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    cloudfront_domain: str = ""
    cloudfront_key_pair_id: str = ""
    cloudfront_private_key: SecretStr = SecretStr("")
    sqs_job_queue_url: str = ""
    sqs_dlq_url: str = ""
    job_timeout_seconds: int = Field(default=180, gt=0)

    # Payment webhooks
    lemonsqueezy_webhook_secret: SecretStr = SecretStr("")
    paddle_webhook_secret: SecretStr = SecretStr("")
    webhook_claim_lease_seconds: int = Field(default=300, gt=0)
    """How long a claimed but unfinished webhook delivery blocks its retries (§4).

    A process killed between claiming an event and marking it done leaves the claim
    behind; past this lease the provider's retry may take it over. Keep it above the
    longest a delivery can legitimately take to apply, and below the provider's retry
    window, so a stranded paid event is recovered rather than lost."""

    # Pipeline
    snapplay_pipeline: PipelineBackend = "fake"
    modal_app_name: str = "snapplay-worker"
    runpod_endpoint_id: str = ""
    runpod_api_key: SecretStr = SecretStr("")

    # Limits and product rules
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    max_input_seconds: float = Field(default=60.0, gt=0)
    free_signup_credits: int = Field(default=3, ge=0)
    rate_limit_jobs_per_min: int = Field(default=10, gt=0)
    rate_limit_reads_per_min: int = Field(default=60, gt=0)
    affiliate_commission_rate: float = Field(default=0.30, ge=0, le=1)

    # Browser origins allowed by CORS; "*" allows any origin.
    cors_allow_origins: list[str] = ["*"]

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _check_production(self) -> Settings:
        if self.env != "production":
            return self
        problems: list[str] = []
        if not self.supabase_url:
            problems.append("SUPABASE_URL is required")
        if not (self.supabase_jwt_secret.get_secret_value() or self.supabase_jwks_url):
            problems.append("SUPABASE_JWT_SECRET or SUPABASE_JWKS_URL is required")
        if not self.lemonsqueezy_webhook_secret.get_secret_value():
            problems.append("LEMONSQUEEZY_WEBHOOK_SECRET is required")
        if not self.paddle_webhook_secret.get_secret_value():
            problems.append("PADDLE_WEBHOOK_SECRET is required")
        if self.snapplay_pipeline == "fake":
            problems.append("SNAPPLAY_PIPELINE=fake is not allowed")
        if self.storage_backend == "memory":
            problems.append("STORAGE_BACKEND=memory is not allowed")
        if problems:
            raise ValueError("invalid production configuration: " + "; ".join(problems))
        return self

    @property
    def jwt_verification_configured(self) -> bool:
        return bool(self.supabase_jwt_secret.get_secret_value() or self.supabase_jwks_url)


_override: Settings | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide settings; FastAPI dependency (``Depends(get_settings)``)."""
    return _override if _override is not None else Settings()


def set_settings_override(settings: Settings | None) -> None:
    """Replace (or with ``None`` restore) the settings returned by :func:`get_settings`."""
    global _override
    _override = settings
    get_settings.cache_clear()


@contextmanager
def override_settings(settings: Settings) -> Iterator[Settings]:
    """Scoped :func:`set_settings_override` for tests."""
    previous = _override
    set_settings_override(settings)
    try:
        yield settings
    finally:
        set_settings_override(previous)
