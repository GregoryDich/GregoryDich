import io
import shutil
from collections.abc import Callable

import numpy as np
import pytest
import soundfile as sf

from app.pipeline import audio_io
from app.pipeline.audio_io import (
    decode_audio,
    decode_bytes,
    match_channels,
    peak_db,
    resample,
    rms_db,
    to_stereo,
    truncate,
    wav_bytes,
)
from app.pipeline.base import PipelineError


def test_truncation_and_resample(make_wav: Callable[..., bytes]) -> None:
    decoded = decode_audio(make_wav(seconds=3.0, sample_rate=48000, channels=1), max_seconds=2.0)
    assert decoded.info.model_dump() == {
        "duration_seconds": 2.0,
        "sample_rate": 48000,
        "channels": 1,
        "truncated": True,
    }
    assert decoded.sample_rate == 44100
    assert decoded.samples.shape == (1, 88200) and decoded.samples.dtype == np.float32
    assert decoded.duration_seconds == pytest.approx(2.0)


def test_stereo_input_is_kept(make_wav: Callable[..., bytes]) -> None:
    decoded = decode_audio(make_wav(seconds=1.0), max_seconds=60.0)
    assert decoded.info.channels == 2 and decoded.info.truncated is False
    assert decoded.samples.shape == (2, 44100)


def test_resample_lengths() -> None:
    assert resample(np.zeros((2, 48000), dtype=np.float32), 48000, 44100).shape == (2, 44100)
    assert resample(np.zeros((1, 22050), dtype=np.float32), 22050, 44100).shape == (1, 44100)
    assert resample(np.zeros((1, 96001), dtype=np.float32), 96000, 44100).shape == (1, 44100)
    same = np.ones((1, 10), dtype=np.float32)
    assert resample(same, 44100, 44100) is same
    t = np.arange(48000) / 48000
    tone = np.sin(2 * np.pi * 440.0 * t).astype(np.float32)[None]
    resampled = resample(tone, 48000, 44100)[0]
    t_out = np.arange(44100) / 44100
    assert np.max(np.abs(resampled[100:-100] - np.sin(2 * np.pi * 440.0 * t_out)[100:-100])) < 0.05


def test_truncate() -> None:
    data = np.zeros((1000, 2), dtype=np.float32)
    kept, truncated = truncate(data, 100, 5.0)
    assert kept.shape[0] == 500 and truncated
    kept, truncated = truncate(data, 100, 20.0)
    assert kept.shape[0] == 1000 and not truncated


def test_channels() -> None:
    mono = np.ones((1, 4), dtype=np.float32)
    assert to_stereo(mono).shape == (2, 4)
    assert to_stereo(np.ones((3, 4), dtype=np.float32)).shape == (2, 4)
    assert match_channels(np.ones((2, 4), dtype=np.float32), 1).shape == (1, 4)
    assert match_channels(mono, 2).shape == (2, 4)


def test_undecodable_input() -> None:
    for payload in (b"", b"not audio at all"):
        with pytest.raises(PipelineError) as info:
            decode_bytes(payload)
        assert info.value.code == "unsupported_media_type"


def test_levels_and_wav_round_trip() -> None:
    t = np.arange(44100) / 44100
    tone = np.sin(2 * np.pi * 440.0 * t).astype(np.float32)[None]
    assert peak_db(tone) == pytest.approx(0.0, abs=0.01)
    assert rms_db(tone) == pytest.approx(-3.01, abs=0.02)
    assert peak_db(np.zeros((1, 10), dtype=np.float32)) == -120.0
    encoded = wav_bytes(np.repeat(tone, 2, axis=0), 44100)
    data, sr = sf.read(io.BytesIO(encoded), dtype="float32", always_2d=True)
    assert sr == 44100 and data.shape == (44100, 2)
    assert np.max(np.abs(data[:, 0] - tone[0])) < 1e-3


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_ffmpeg_fallback(monkeypatch: pytest.MonkeyPatch, make_wav: Callable[..., bytes]) -> None:
    wav = make_wav(seconds=1.0, sample_rate=48000, channels=2)

    def broken_read(*args: object, **kwargs: object) -> object:
        raise RuntimeError("libsndfile refused")

    monkeypatch.setattr(audio_io.sf, "read", broken_read)
    data, sr = decode_bytes(wav)
    assert sr == 48000 and data.shape == (48000, 2) and data.dtype == np.float32
    assert float(np.abs(data).max()) > 0.1
