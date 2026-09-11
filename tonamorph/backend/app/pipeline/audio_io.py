"""Decoding, resampling, truncation, level helpers and WAV encoding (contract §7).

Decoding goes through soundfile (libsndfile: FLAC, WAV, OGG, AIFF and, with libsndfile
>= 1.1, MP3); an ``ffmpeg`` subprocess is the fallback for containers libsndfile does
not know. Resampling to 44.1 kHz uses torchaudio when torch is installed, otherwise
scipy's polyphase filter, otherwise linear interpolation — the best available without
turning any of them into a hard dependency.
"""

from __future__ import annotations

import io
import json
import math
import shutil
import subprocess
from dataclasses import dataclass

import numpy as np
import soundfile as sf

from app.pipeline.base import PipelineError
from app.schemas import InputInfo

TARGET_SR = 44100
MAX_CHANNELS = 2
DB_FLOOR = -120.0
FFMPEG_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class DecodedAudio:
    """``samples`` is ``(channels, samples)`` float32 at ``sample_rate``; ``info`` reports
    the source file as the contract's ``input`` block."""

    samples: np.ndarray
    sample_rate: int
    info: InputInfo

    @property
    def duration_seconds(self) -> float:
        return self.samples.shape[1] / self.sample_rate


# --- decoding --------------------------------------------------------------------------


def decode_bytes(audio_bytes: bytes) -> tuple[np.ndarray, int]:
    """``(frames × channels float32, sample_rate)`` for any supported container.

    Raises :class:`PipelineError` (``unsupported_media_type``) when neither libsndfile
    nor ffmpeg can decode the bytes.
    """
    if not audio_bytes:
        raise PipelineError("unsupported_media_type", "audio payload is empty")
    try:
        data, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32", always_2d=True)
    except (sf.LibsndfileError, RuntimeError, ValueError, TypeError) as exc:
        data, sr = _ffmpeg_decode(audio_bytes, str(exc))
    if data.shape[0] == 0:
        raise PipelineError("unsupported_media_type", "audio contains no samples")
    return data, int(sr)


def _ffmpeg_decode(audio_bytes: bytes, soundfile_error: str) -> tuple[np.ndarray, int]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None or ffprobe is None:
        raise PipelineError(
            "unsupported_media_type", f"cannot decode audio: {soundfile_error}"
        )
    try:
        probe = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=sample_rate,channels",
                "-of",
                "json",
                "-i",
                "pipe:0",
            ],
            input=audio_bytes,
            capture_output=True,
            timeout=FFMPEG_TIMEOUT_SECONDS,
            check=False,
        )
        streams = json.loads(probe.stdout or b"{}").get("streams") or []
        if probe.returncode != 0 or not streams:
            raise PipelineError(
                "unsupported_media_type", f"cannot decode audio: {soundfile_error}"
            )
        sr = int(streams[0]["sample_rate"])
        channels = min(int(streams[0]["channels"]), MAX_CHANNELS)
        if sr <= 0 or channels <= 0:
            raise PipelineError("unsupported_media_type", "audio stream has no channels")
        decoded = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                "pipe:0",
                "-vn",
                "-f",
                "f32le",
                "-acodec",
                "pcm_f32le",
                "-ac",
                str(channels),
                "-ar",
                str(sr),
                "pipe:1",
            ],
            input=audio_bytes,
            capture_output=True,
            timeout=FFMPEG_TIMEOUT_SECONDS,
            check=False,
        )
    except (subprocess.SubprocessError, OSError, KeyError, ValueError) as exc:
        raise PipelineError("unsupported_media_type", f"cannot decode audio: {exc}") from exc
    if decoded.returncode != 0 or not decoded.stdout:
        raise PipelineError("unsupported_media_type", "ffmpeg could not decode the audio")
    raw = np.frombuffer(decoded.stdout, dtype="<f4")
    frames = raw.shape[0] // channels
    return raw[: frames * channels].reshape(frames, channels).copy(), sr


# --- shaping --------------------------------------------------------------------------


def truncate(data: np.ndarray, sample_rate: int, max_seconds: float) -> tuple[np.ndarray, bool]:
    """Keep the first ``max_seconds`` of ``data`` (frames × channels); reports truncation."""
    max_frames = max(1, int(max_seconds * sample_rate))
    truncated = data.shape[0] > max_frames
    return data[:max_frames], truncated


def resample(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    """Resample ``x`` (channels × samples) to exactly ``round(n · sr_out / sr_in)`` samples."""
    x = np.asarray(x, dtype=np.float32)
    if sr_in == sr_out:
        return x
    n_out = int(round(x.shape[-1] * sr_out / sr_in))
    if x.shape[-1] == 0 or n_out == 0:
        return np.zeros(x.shape[:-1] + (n_out,), dtype=np.float32)
    y = _resample_backend(x, sr_in, sr_out)
    if y.shape[-1] > n_out:
        y = y[..., :n_out]
    elif y.shape[-1] < n_out:
        y = np.pad(y, [(0, 0)] * (y.ndim - 1) + [(0, n_out - y.shape[-1])])
    return np.ascontiguousarray(y, dtype=np.float32)


def _resample_backend(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    try:
        import torch
        import torchaudio.functional as taf
    except ImportError:
        pass
    else:
        with torch.inference_mode():
            return taf.resample(torch.from_numpy(x), sr_in, sr_out).numpy()
    try:
        from scipy.signal import resample_poly
    except ImportError:
        pass
    else:
        g = math.gcd(sr_in, sr_out)
        return resample_poly(x, sr_out // g, sr_in // g, axis=-1).astype(np.float32)
    return _resample_linear(x, sr_in, sr_out)


def _resample_linear(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    n_out = int(round(x.shape[-1] * sr_out / sr_in))
    t_in = np.arange(x.shape[-1], dtype=np.float64) / sr_in
    t_out = np.arange(n_out, dtype=np.float64) / sr_out
    flat = x.reshape(-1, x.shape[-1])
    out = np.stack([np.interp(t_out, t_in, ch) for ch in flat]).astype(np.float32)
    return out.reshape(x.shape[:-1] + (n_out,))


def to_stereo(x: np.ndarray) -> np.ndarray:
    """(channels × samples) → (2 × samples): mono is duplicated, extra channels dropped."""
    if x.shape[0] == 2:
        return x
    if x.shape[0] == 1:
        return np.repeat(x, 2, axis=0)
    return x[:2]


def match_channels(x: np.ndarray, channels: int) -> np.ndarray:
    """Fold ``x`` (channels × samples) to ``channels`` by averaging or duplication."""
    if x.shape[0] == channels:
        return x
    if channels == 1:
        return x.mean(axis=0, keepdims=True, dtype=np.float32)
    return to_stereo(x)


def decode_audio(
    audio_bytes: bytes, max_seconds: float, target_sr: int = TARGET_SR
) -> DecodedAudio:
    """Decode, keep at most two channels and ``max_seconds``, resample to ``target_sr``."""
    data, sr = decode_bytes(audio_bytes)
    data, truncated = truncate(data[:, :MAX_CHANNELS], sr, max_seconds)
    info = InputInfo(
        duration_seconds=round(data.shape[0] / sr, 3),
        sample_rate=sr,
        channels=int(data.shape[1]),
        truncated=truncated,
    )
    samples = resample(np.ascontiguousarray(data.T), sr, target_sr)
    return DecodedAudio(samples=samples, sample_rate=target_sr, info=info)


# --- levels and encoding ---------------------------------------------------------------


def db(value: float) -> float:
    """Linear amplitude → dBFS, floored at :data:`DB_FLOOR`."""
    return round(max(20.0 * math.log10(value), DB_FLOOR), 2) if value > 0 else DB_FLOOR


def peak_db(x: np.ndarray) -> float:
    return db(float(np.abs(x).max())) if x.size else DB_FLOOR


def rms_db(x: np.ndarray) -> float:
    return db(float(np.sqrt(np.mean(np.square(x, dtype=np.float64))))) if x.size else DB_FLOOR


def wav_bytes(x: np.ndarray, sample_rate: int = TARGET_SR, subtype: str = "PCM_16") -> bytes:
    """Encode ``x`` (channels × samples) as a WAV file."""
    buf = io.BytesIO()
    sf.write(buf, np.clip(x.T, -1.0, 1.0), sample_rate, format="WAV", subtype=subtype)
    return buf.getvalue()


__all__ = [
    "DB_FLOOR",
    "MAX_CHANNELS",
    "TARGET_SR",
    "DecodedAudio",
    "db",
    "decode_audio",
    "decode_bytes",
    "match_channels",
    "peak_db",
    "resample",
    "rms_db",
    "to_stereo",
    "truncate",
    "wav_bytes",
]
