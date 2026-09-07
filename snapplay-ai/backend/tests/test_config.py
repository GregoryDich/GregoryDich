"""Settings validation (§1): what production refuses to start without."""

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
    "snapplay_pipeline": "aws",
    "lemonsqueezy_webhook_secret": "ls-secret",
    "paddle_webhook_secret": "paddle-secret",
}


def test_production_requires_both_webhook_secrets() -> None:
    """An empty secret is still used as an HMAC key, so anyone could sign their own
    purchase events: production must not start without both (§4)."""
    with pytest.raises(ValidationError) as info:
        Settings(**{**PRODUCTION, "lemonsqueezy_webhook_secret": "", "paddle_webhook_secret": ""})
    message = str(info.value)
    assert "LEMONSQUEEZY_WEBHOOK_SECRET is required" in message
    assert "PADDLE_WEBHOOK_SECRET is required" in message

    with pytest.raises(ValidationError) as info:
        Settings(**{**PRODUCTION, "paddle_webhook_secret": ""})
    assert "PADDLE_WEBHOOK_SECRET is required" in str(info.value)

    settings = Settings(**PRODUCTION)
    assert settings.lemonsqueezy_webhook_secret.get_secret_value() == "ls-secret"


def test_development_still_starts_without_payment_secrets() -> None:
    settings = Settings(
        _env_file=None, env="development", lemonsqueezy_webhook_secret="", paddle_webhook_secret=""
    )
    assert settings.paddle_webhook_secret.get_secret_value() == ""
