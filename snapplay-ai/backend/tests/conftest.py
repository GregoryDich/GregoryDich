"""Shared fixtures: isolated settings, app/client, HS256 JWT minting, synthetic WAV."""

from __future__ import annotations

import io
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
import numpy as np
import pytest
import soundfile as sf
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings, override_settings
from app.main import create_app

TEST_JWT_SECRET = "test-jwt-secret-not-for-production"


@pytest.fixture
def settings() -> Iterator[Settings]:
    """Fully offline settings; ``_env_file=None`` ignores any developer ``.env``."""
    test_settings = Settings(
        _env_file=None,
        env="test",
        supabase_url="http://supabase.test",
        supabase_service_role_key="service-role-test",
        supabase_anon_key="anon-test",
        supabase_jwt_secret=TEST_JWT_SECRET,
        storage_backend="memory",
        snapplay_pipeline="fake",
        lemonsqueezy_webhook_secret="ls-test-secret",
        paddle_webhook_secret="paddle-test-secret",
        cors_allow_origins=["http://localhost:3000"],
    )
    with override_settings(test_settings):
        yield test_settings


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def mint_jwt() -> Callable[..., str]:
    """``mint_jwt(sub=None, *, expires_in=3600, aud="authenticated", secret=..., **claims)``
    returns an HS256 token accepted by the Supabase-style verifier."""

    def _mint(
        sub: str | None = None,
        *,
        expires_in: int = 3600,
        aud: str = "authenticated",
        secret: str = TEST_JWT_SECRET,
        email: str = "user@example.test",
        **claims: Any,
    ) -> str:
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": sub or str(uuid4()),
            "aud": aud,
            "email": email,
            "role": "authenticated",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
            **claims,
        }
        return jwt.encode(payload, secret, algorithm="HS256")

    return _mint


@pytest.fixture
def make_wav() -> Callable[..., bytes]:
    """``make_wav(seconds=5.0, sample_rate=44100, channels=2, bpm=120.0, bass_hz=55.0)``
    returns a WAV: a bass tone, a mid-band pad, and noise hits on every beat."""

    def _make(
        seconds: float = 5.0,
        sample_rate: int = 44100,
        channels: int = 2,
        bpm: float = 120.0,
        bass_hz: float = 55.0,
    ) -> bytes:
        n = int(seconds * sample_rate)
        t = np.arange(n, dtype=np.float64) / sample_rate
        bass = 0.4 * np.sin(2 * np.pi * bass_hz * t) * (1.0 + 0.2 * np.sin(2 * np.pi * 0.5 * t))
        pad = 0.15 * (np.sin(2 * np.pi * 220.0 * t) + np.sin(2 * np.pi * 329.63 * t))
        rng = np.random.default_rng(12345)
        noise = rng.standard_normal(n)
        beat = np.zeros(n)
        hit_len = int(0.03 * sample_rate)
        decay = np.exp(-np.arange(hit_len) / (0.005 * sample_rate))
        for start in np.arange(0.0, seconds, 60.0 / bpm):
            i = int(start * sample_rate)
            stop = min(i + hit_len, n)
            beat[i:stop] += 0.5 * decay[: stop - i] * noise[i:stop]
        mono = bass + pad + beat
        mono = (0.8 * mono / np.max(np.abs(mono))).astype(np.float32)
        data = np.repeat(mono[:, None], channels, axis=1)
        buf = io.BytesIO()
        sf.write(buf, data, sample_rate, format="WAV", subtype="PCM_16")
        return buf.getvalue()

    return _make


@pytest.fixture
def wav_5s(make_wav: Callable[..., bytes]) -> bytes:
    return make_wav(seconds=5.0)
