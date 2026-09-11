"""Settings validation (§1, §4): what production refuses to start without."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from app.config import Settings

PRODUCTION: dict[str, Any] = {
    "_env_file": None,
    "env": "production",
    "supabase_url": "https://project.supabase.co",
    "supabase_jwt_secret": "a-real-jwt-secret",
    "storage_backend": "s3",
    "tonamorph_pipeline": "aws",
    "lemonsqueezy_webhook_secret": "ls-secret",
    "paddle_webhook_secret": "paddle-secret",
    "auth_site_url": "https://tonamorph.com",
}


def test_production_requires_at_least_one_webhook_secret() -> None:
    """An empty secret is still used as an HMAC key, so anyone could sign their own
    purchase events: production must not start with neither. One is enough, because a
    provider without a secret answers 404 instead of verifying against "" (§4)."""
    with pytest.raises(ValidationError) as info:
        Settings(**{**PRODUCTION, "lemonsqueezy_webhook_secret": "", "paddle_webhook_secret": ""})
    assert "LEMONSQUEEZY_WEBHOOK_SECRET or PADDLE_WEBHOOK_SECRET is required" in str(info.value)

    only_paddle = Settings(**{**PRODUCTION, "lemonsqueezy_webhook_secret": ""})
    assert only_paddle.paddle_webhook_secret.get_secret_value() == "paddle-secret"
    only_lemonsqueezy = Settings(**{**PRODUCTION, "paddle_webhook_secret": ""})
    assert only_lemonsqueezy.lemonsqueezy_webhook_secret.get_secret_value() == "ls-secret"

    settings = Settings(**PRODUCTION)
    assert settings.lemonsqueezy_webhook_secret.get_secret_value() == "ls-secret"


@pytest.mark.parametrize(
    "site_url",
    [
        "http://localhost:3000",
        "http://tonamorph.com",
        "https://localhost",
        "https://127.0.0.1:3000",
        "https://app.localhost",
        "tonamorph.com",
        "",
    ],
)
def test_production_refuses_a_local_or_plain_http_site_url(site_url: str) -> None:
    """Emailed confirmation and recovery links land on ``AUTH_SITE_URL`` (§1); the default
    points at a developer machine and would send every new user to a dead link."""
    with pytest.raises(ValidationError) as info:
        Settings(**{**PRODUCTION, "auth_site_url": site_url})
    assert "AUTH_SITE_URL must be an https URL that is not localhost" in str(info.value)


def test_production_accepts_a_public_https_site_url() -> None:
    assert Settings(**PRODUCTION).auth_site_url == "https://tonamorph.com"
    assert Settings(**{**PRODUCTION, "auth_site_url": "https://www.tonamorph.com/"}).auth_site_url


def test_worker_role_skips_the_api_only_checks() -> None:
    """The GPU worker builds ``Settings()`` too: it never serves webhooks or emailed
    links, so it must start without the secrets and the site URL — while everything
    else production requires still applies to it."""
    worker = Settings(
        **{
            **PRODUCTION,
            "service_role": "worker",
            "lemonsqueezy_webhook_secret": "",
            "paddle_webhook_secret": "",
            "auth_site_url": "http://localhost:3000",
        }
    )
    assert worker.service_role == "worker"
    with pytest.raises(ValidationError) as info:
        Settings(**{**PRODUCTION, "service_role": "worker", "supabase_url": ""})
    assert "SUPABASE_URL is required" in str(info.value)
    assert Settings(_env_file=None).service_role == "api"


def test_development_still_starts_without_payment_secrets() -> None:
    settings = Settings(
        _env_file=None, env="development", lemonsqueezy_webhook_secret="", paddle_webhook_secret=""
    )
    assert settings.paddle_webhook_secret.get_secret_value() == ""
    assert settings.maintenance_mode is False
