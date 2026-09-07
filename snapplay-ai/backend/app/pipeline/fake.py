"""Deterministic CPU pipeline (``SNAPPLAY_PIPELINE=fake``).

Produces the full §7 result shape from real signal processing so that every downstream
component (upload, MIDI export, plugin parsing) can be exercised offline: STFT band and
transient masks for stems (the four masks sum to one, so the stems sum to the mix), then
the same tempo, key, pitch-tracking, onset, ADSR and MIDI code the real backend uses
(:mod:`app.pipeline.analysis`, :mod:`app.pipeline.midi_export`). No randomness anywhere.

Large work buffers are allocated once per run and reused across stems: fresh memory is
the dominant cost on small hosts, not the FFTs themselves.
"""

from __future__ import annotations

import numpy as np

from app.pipeline.analysis import (
    EPS,
    FRAME,
    FRAME_RATE,
    HOP,
    PITCH_RANGE_HZ,
    TARGET_SR,
    Note,
    chroma_from_magnitude,
    drum_slices,
    estimate_key_from_chroma,
    estimate_tempo_from_flux,
    frames,
    frames_to_seconds,
    hann,
    pick_onsets,
    segment_notes,
    slices_to_notes,
    spectral_flux,
    stem_root,
    stft_freqs,
    suggest_adsr,
    track_beats,
    track_pitch,
)
from app.pipeline.audio_io import decode_audio, peak_db, rms_db, wav_bytes
from app.pipeline.base import (
    STAGE_ANALYZE,
    STAGE_DONE,
    STAGE_PACKAGE,
    STAGE_SEPARATE,
    STAGE_TRANSCRIBE,
    ProgressCallback,
)
from app.pipeline.midi_export import build_midi
from app.schemas import Adsr, Analysis, PipelineOptions, PipelineResult, Slice, StemResult

_WINDOW = hann(FRAME)
_WINDOW_SQ = _WINDOW * _WINDOW
_FREQS = stft_freqs(TARGET_SR, FRAME)


def _soft_edge(freqs: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """1 below ``lo``, raised-cosine to 0 at ``hi``."""
    x = np.clip((freqs - lo) / max(hi - lo, EPS), 0.0, 1.0)
    return (0.5 + 0.5 * np.cos(np.pi * x)).astype(np.float32)


_BASS_MASK = _soft_edge(_FREQS, 200.0, 250.0)
_VOCAL_BAND = (1.0 - _soft_edge(_FREQS, 250.0, 350.0)) * _soft_edge(_FREQS, 3400.0, 4200.0)


# --- STFT ---------------------------------------------------------------------------------


def _stft(x: np.ndarray, frames_buf: np.ndarray) -> np.ndarray:
    """Hann STFT of ``x`` (ch, n) → (ch, F, bins) complex64; ``frames_buf`` (ch, F, FRAME) is
    scratch space that the caller keeps for :func:`_istft`."""
    np.copyto(frames_buf, frames(x))
    frames_buf *= _WINDOW
    return np.fft.rfft(frames_buf, axis=-1)


def _istft(spec: np.ndarray, n_samples: int, frames_buf: np.ndarray) -> np.ndarray:
    """Inverse of :func:`_stft` (Hann analysis + synthesis, squared-window normalisation)."""
    np.fft.irfft(spec, n=FRAME, axis=-1, out=frames_buf)
    frames_buf *= _WINDOW
    n_frames = frames_buf.shape[-2]
    ratio = FRAME // HOP
    rows = n_frames + ratio - 1
    out = np.zeros(frames_buf.shape[:-2] + (rows, HOP), dtype=np.float32)
    norm = np.zeros((rows, HOP), dtype=np.float32)
    for j in range(ratio):
        out[..., j : j + n_frames, :] += frames_buf[..., :, j * HOP : (j + 1) * HOP]
        norm[j : j + n_frames] += _WINDOW_SQ[j * HOP : (j + 1) * HOP]
    out /= np.maximum(norm, 1e-3)
    pad = FRAME // 2
    return out.reshape(frames_buf.shape[:-2] + (rows * HOP,))[..., pad : pad + n_samples]


def _transient_weight(flux: np.ndarray) -> np.ndarray:
    scale = float(np.percentile(flux, 95)) if flux.size else 0.0
    t = np.clip(flux / (scale + EPS), 0.0, 1.0).astype(np.float32)
    decayed = t.copy()
    if t.size > 1:
        decayed[1:] = np.maximum(decayed[1:], 0.6 * t[:-1])
    if t.size > 2:
        decayed[2:] = np.maximum(decayed[2:], 0.36 * t[:-2])
    return decayed


def _masks(transient: np.ndarray) -> dict[str, np.ndarray]:
    """Per-(frame, bin) masks that sum to exactly one."""
    bass = np.broadcast_to(_BASS_MASK, (transient.shape[0], _BASS_MASK.shape[0]))
    rest = 1.0 - bass
    t = transient[:, None]
    drums = rest * t
    vocals = rest * (1.0 - t) * _VOCAL_BAND
    other = rest - drums - vocals
    return {"bass": bass, "drums": drums, "vocals": vocals, "other": other}


# --- entry point ---------------------------------------------------------------------------


def run_pipeline(
    audio_bytes: bytes,
    options: PipelineOptions,
    progress: ProgressCallback,
) -> PipelineResult:
    progress(STAGE_SEPARATE, 0.0)
    decoded = decode_audio(audio_bytes, options.max_seconds)
    audio = decoded.samples
    n_channels, n_samples = audio.shape
    duration = n_samples / TARGET_SR

    frames_buf = np.empty((n_channels, 1 + n_samples // HOP, FRAME), dtype=np.float32)
    spec = _stft(audio, frames_buf)  # (ch, F, bins)
    spec_buf = np.empty_like(spec)
    mono_mag = np.abs(spec[0])
    for channel in spec[1:]:
        mono_mag += np.abs(channel)
    mono_mag /= n_channels
    flux = spectral_flux(mono_mag)
    masks = _masks(_transient_weight(flux))
    progress(STAGE_SEPARATE, 0.2)

    stem_audio: dict[str, np.ndarray] = {}
    for i, name in enumerate(options.stems):
        np.multiply(spec, masks[name], out=spec_buf)
        stem_audio[name] = _istft(spec_buf, n_samples, frames_buf)
        progress(STAGE_SEPARATE, 0.2 + 0.15 * (i + 1) / len(options.stems))
    del spec_buf, frames_buf
    stem_mono = {name: y.mean(axis=0) for name, y in stem_audio.items()}

    progress(STAGE_TRANSCRIBE, 0.4)
    notes: dict[str, list[Note]] = {}
    for i, name in enumerate(options.stems):
        if name in PITCH_RANGE_HZ:
            fmin, fmax = PITCH_RANGE_HZ[name]
            notes[name] = segment_notes(*track_pitch(stem_mono[name], fmin, fmax))
        progress(STAGE_TRANSCRIBE, 0.4 + 0.2 * (i + 1) / len(options.stems))

    progress(STAGE_ANALYZE, 0.65)
    bpm, bpm_confidence = estimate_tempo_from_flux(flux, FRAME_RATE)
    downbeats, beats = track_beats(flux, bpm, duration, FRAME_RATE)
    key = estimate_key_from_chroma(chroma_from_magnitude(mono_mag, _FREQS))
    analysis = Analysis(
        bpm=bpm,
        bpm_confidence=bpm_confidence,
        key=key,
        downbeats_seconds=downbeats,
        beats_seconds=beats,
    )
    transients: dict[str, list[float]] = {}
    adsr: dict[str, Adsr] = {}
    for name in options.stems:
        onsets = pick_onsets(spectral_flux(mono_mag * masks[name]), FRAME_RATE)
        transients[name] = frames_to_seconds(onsets, FRAME_RATE)
        adsr[name] = suggest_adsr(stem_mono[name], TARGET_SR, name, transients[name])
    slices: list[Slice] = drum_slices(transients.get("drums", []), duration)
    progress(STAGE_ANALYZE, 0.8)

    progress(STAGE_PACKAGE, 0.85)
    stems: list[StemResult] = []
    for name in options.stems:
        y = stem_audio[name]
        root_midi, root_confidence = stem_root(name, notes.get(name, []), stem_mono[name], key)
        stems.append(
            StemResult(
                name=name,
                sample_rate=TARGET_SR,
                channels=int(y.shape[0]),
                duration_seconds=round(duration, 3),
                root_midi=root_midi,
                root_confidence=root_confidence,
                peak_db=peak_db(y),
                rms_db=rms_db(y),
                transients_seconds=transients[name],
                suggested_adsr=adsr[name],
                slices=slices if name == "drums" and options.drum_slices else None,
                wav_bytes=wav_bytes(y, TARGET_SR),
            )
        )
    if "drums" in options.stems:
        notes["drums"] = slices_to_notes(slices)
    midi = build_midi(notes, list(options.transcribe), bpm)
    progress(STAGE_PACKAGE, 0.95)

    progress(STAGE_DONE, 1.0)
    return PipelineResult(input=decoded.info, analysis=analysis, stems=stems, midi=midi)
