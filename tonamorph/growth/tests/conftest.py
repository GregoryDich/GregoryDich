"""Shared fixtures: isolated environment, respx routers and Tonamorph fixtures.

No test may reach the network: every router is created with ``assert_all_mocked=True`` so an
unmocked request raises instead of leaving the sandbox.
"""

from __future__ import annotations

import io
import json
import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import httpx
import mido
import numpy as np
import pytest
import respx
import soundfile as sf
from fastmcp import Client

from mcp_server.config import Settings
from mcp_server.state import Store

TONAMORPH_URL = "https://api.tonamorph.test"
STORAGE_URL = "https://storage.tonamorph.test"
ELEVENLABS_URL = "https://elevenlabs.test"
META_GRAPH_URL = "https://graph.meta.test"
META_UPLOAD_URL = "https://rupload.meta.test"
TIKTOK_URL = "https://tiktok.test"
YOUTUBE_URL = "https://youtube.test"
JOB_ID = "6f1c2a0e-9d2b-4f7e-8a0c-1b2c3d4e5f60"


def make_wav_bytes(seconds: float = 2.0, freq: float = 110.0, sr: int = 44100) -> bytes:
    t = np.arange(int(sr * seconds)) / sr
    x = (0.4 * np.sin(2 * np.pi * freq * t) * np.exp(-((t % 0.5) * 4))).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, np.stack([x, x], axis=1), sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def make_midi_bytes() -> bytes:
    mf = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mf.tracks.append(track)
    track.append(mido.MetaMessage("track_name", name="bass"))
    track.append(mido.Message("note_on", note=41, velocity=100, time=0))
    track.append(mido.Message("note_off", note=41, velocity=0, time=480))
    buf = io.BytesIO()
    mf.save(file=buf)
    return buf.getvalue()


def _notes(count: int, pitches: list[int], step: float = 0.5) -> list[dict[str, Any]]:
    return [
        {
            "start_seconds": round(i * step, 3),
            "duration_seconds": round(step * 0.8, 3),
            "start_ticks": int(i * step * 480 * 2),
            "duration_ticks": int(step * 0.8 * 480 * 2),
            "pitch": pitches[i % len(pitches)],
            "velocity": 100,
        }
        for i in range(count)
    ]


def make_job_result(job_id: str = JOB_ID, duration: float = 30.0) -> dict[str, Any]:
    """A contract §2 JobResult: bass is the clear winner, vocals are silent, drums untranscribed."""

    def stem(name: str, rms: float) -> dict[str, Any]:
        return {
            "name": name,
            "url": f"{STORAGE_URL}/jobs/u/{job_id}/{name}.wav",
            "format": "wav",
            "sample_rate": 44100,
            "channels": 2,
            "duration_seconds": duration,
            "root_midi": 41,
            "root_confidence": 0.8,
            "peak_db": -3.0,
            "rms_db": rms,
            "transients_seconds": [0.0, 0.5],
            "suggested_adsr": {"attack_ms": 2, "decay_ms": 120, "sustain": 0.8, "release_ms": 180},
        }

    drums = stem("drums", -16.0)
    drums["slices"] = [{"start_seconds": 0.0, "end_seconds": 0.48, "midi_note": 36}]
    return {
        "job_id": job_id,
        "credits_charged": 1,
        "balance_after": 41,
        "input": {
            "duration_seconds": duration,
            "sample_rate": 44100,
            "channels": 2,
            "truncated": False,
        },
        "analysis": {
            "bpm": 124.0,
            "bpm_confidence": 0.91,
            "key": {
                "root": "F",
                "mode": "minor",
                "root_midi": 53,
                "confidence": 0.82,
                "scale_pitch_classes": [5, 7, 8, 10, 0, 1, 3],
            },
            "downbeats_seconds": [0.0, 1.935],
            "beats_seconds": [0.0, 0.484],
        },
        "stems": [stem("bass", -18.0), drums, stem("other", -24.0), stem("vocals", -60.0)],
        "midi": {
            "url": f"{STORAGE_URL}/jobs/u/{job_id}/score.mid",
            "ppq": 480,
            "bpm": 124.0,
            "tracks": [
                {"name": "bass", "channel": 0, "notes": _notes(60, [41, 44, 46, 48, 41, 53])},
                {"name": "other", "channel": 1, "notes": _notes(300, [60, 72, 84, 96, 108], 0.1)},
                {"name": "vocals", "channel": 2, "notes": _notes(20, [65, 67])},
            ],
        },
        "expires_at": "2026-09-07T12:00:00Z",
    }


def job_status(
    job_id: str = JOB_ID, result: dict[str, Any] | None = None, **extra: Any
) -> dict[str, Any]:
    status = {
        "job_id": job_id,
        "status": "succeeded" if result else "running",
        "stage": "done" if result else "separate",
        "progress": 1.0 if result else 0.4,
        "created_at": "2026-09-06T10:00:00Z",
        "result": result,
    }
    status.update(extra)
    return status


def sse_body(events: list[tuple[str, dict[str, Any]]]) -> bytes:
    """Encode (event, data) pairs the way contract §2 describes, with heartbeat comments."""
    chunks = [": ping\n\n"]
    for event, data in events:
        chunks.append(f"event: {event}\ndata: {json.dumps(data)}\n\n")
        chunks.append(": ping\n\n")
    return "".join(chunks).encode()


def me_body(available: int = 41, credits: int = 42, reserved: int = 1) -> dict[str, Any]:
    """``GET /v1/me`` (contract §1) as the credit guard reads it."""
    return {
        "user": {"id": "11111111-2222-3333-4444-555555555555", "email": "growth@tonamorph.test",
                 "plan": "credits"},
        "balance": {"credits": credits, "reserved": reserved, "available": available},
    }


def mock_me(router: respx.Router, available: int = 41) -> respx.Route:
    return router.get(f"{TONAMORPH_URL}/v1/me").mock(
        return_value=httpx.Response(200, json=me_body(available))
    )


def mock_tonamorph(
    router: respx.Router, result: dict[str, Any], *, sse: bool = True, available: int = 41
) -> dict[str, respx.Route]:
    """Mock the whole job lifecycle: balance, submit, SSE (or polling), poll, downloads."""
    routes = {
        "me": mock_me(router, available),
        "submit": router.post(f"{TONAMORPH_URL}/v1/jobs").mock(
            return_value=httpx.Response(
                202,
                json={
                    "job_id": result["job_id"],
                    "status": "queued",
                    "credits_reserved": 1,
                    "balance": {"credits": 42, "reserved": 1, "available": 41},
                },
            )
        ),
        "poll": router.get(f"{TONAMORPH_URL}/v1/jobs/{result['job_id']}").mock(
            return_value=httpx.Response(200, json=job_status(result["job_id"], result))
        ),
        "midi": router.get(result["midi"]["url"]).mock(
            return_value=httpx.Response(200, content=make_midi_bytes())
        ),
    }
    if sse:
        routes["events"] = router.get(f"{TONAMORPH_URL}/v1/jobs/{result['job_id']}/events").mock(
            return_value=httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=sse_body(
                    [
                        ("progress", {"stage": "separate", "progress": 0.35}),
                        ("result", job_status(result["job_id"], result)),
                    ]
                ),
            )
        )
    else:
        routes["events"] = router.get(f"{TONAMORPH_URL}/v1/jobs/{result['job_id']}/events").mock(
            return_value=httpx.Response(
                404, json={"error": {"code": "not_found", "message": "no stream"}}
            )
        )
    wav = make_wav_bytes()
    for stem in result["stems"]:
        routes[f"stem:{stem['name']}"] = router.get(stem["url"]).mock(
            return_value=httpx.Response(200, content=wav)
        )
    return routes


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    values = {
        "TONAMORPH_API_URL": TONAMORPH_URL,
        "TONAMORPH_API_KEY": "tm_live_testtesttesttesttesttesttest",
        "TONAMORPH_POLL_INTERVAL_SECONDS": "0",
        "TONAMORPH_JOB_TIMEOUT_SECONDS": "5",
        "GROWTH_DB_PATH": str(tmp_path / "growth.db"),
        "GROWTH_WORK_DIR": str(tmp_path / "work"),
        "LICENSED_CLIPS_DIR": str(tmp_path / "clips"),
        "FMA_API_KEY": "fma-test",
        "FMA_API_URL": "https://fma.test/api/get",
        "ELEVENLABS_API_KEY": "el-test",
        "ELEVENLABS_API_URL": ELEVENLABS_URL,
        "REMOTION_DIR": str(tmp_path / "no-remotion"),
        "FFMPEG_BIN": os.environ.get("FFMPEG_BIN", "ffmpeg"),
        "META_GRAPH_API_URL": META_GRAPH_URL,
        "META_UPLOAD_API_URL": META_UPLOAD_URL,
        "META_API_VERSION": "v21.0",
        "META_IG_USER_ID": "1789",
        "META_IG_ACCESS_TOKEN": "ig-token",
        "META_PAGE_ID": "4242",
        "META_PAGE_ACCESS_TOKEN": "page-token",
        "TIKTOK_API_URL": TIKTOK_URL,
        "TIKTOK_ACCESS_TOKEN": "tt-token",
        "YOUTUBE_API_URL": YOUTUBE_URL,
        "YOUTUBE_ACCESS_TOKEN": "yt-token",
        "PUBLISH_POLL_INTERVAL_SECONDS": "0",
        "PUBLISH_POLL_ATTEMPTS": "3",
        "GROWTH_LANDING_URL": "https://tonamorph.test/get",
        "GROWTH_UTM_CAMPAIGN": "ugc_shorts",
        "GROWTH_UTM_MEDIUM": "social",
        "GROWTH_REFERRAL_CODE": "growth-bot",
        "GROWTH_CREDIT_FLOOR": "0",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    (tmp_path / "clips").mkdir()
    (tmp_path / "work").mkdir()
    return values


@pytest.fixture
def settings(env: dict[str, str]) -> Settings:
    return Settings()


@pytest.fixture
def store(settings: Settings) -> Store:
    return Store(settings.growth_db_path)


@pytest.fixture
def clip_file(settings: Settings) -> Path:
    """A licensed clip with the per-file manifest sidecar that establishes its rights."""
    path = settings.licensed_clips_dir / "loop.wav"
    path.write_bytes(make_wav_bytes())
    path.with_suffix(".json").write_text(
        json.dumps(
            {"title": "Night Loop", "license": "operator-licensed", "attribution": "in-house"}
        )
    )
    return path


@pytest.fixture
def router() -> Iterator[respx.Router]:
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as mock:
        yield mock


@pytest.fixture
async def mcp_client(env: dict[str, str]) -> AsyncIterator[Client]:
    from mcp_server.server import mcp

    async with Client(mcp) as client:
        yield client
