"""Deterministic CPU pipeline (``SNAPPLAY_PIPELINE=fake``).

Produces the full §7 result shape from real signal processing so that every downstream
component (upload, MIDI export, plugin parsing) can be exercised offline: STFT band and
transient masks for stems (the four masks sum to one, so the stems sum to the mix), an
autocorrelation tempo estimate, Krumhansl–Schmuckler key finding, autocorrelation pitch
tracking for the note events, onset peak-picking for transients/slices, ADSR heuristics,
16-bit WAV via soundfile and a type-1 SMF via mido. No randomness anywhere.

Large work buffers are allocated once per run and reused across stems: fresh memory is
the dominant cost on small hosts, not the FFTs themselves.
"""

from __future__ import annotations

import io
import math

import mido
import numpy as np
import soundfile as sf

from app.pipeline.base import (
    STAGE_ANALYZE,
    STAGE_DONE,
    STAGE_PACKAGE,
    STAGE_SEPARATE,
    STAGE_TRANSCRIBE,
    PipelineError,
    ProgressCallback,
)
from app.schemas import (
    Adsr,
    Analysis,
    InputInfo,
    KeyInfo,
    MidiInfo,
    MidiNote,
    MidiTrack,
    PipelineOptions,
    PipelineResult,
    Slice,
    StemResult,
)

TARGET_SR = 44100
FRAME = 2048
HOP = 512
PPQ = 480
FRAME_RATE = TARGET_SR / HOP
EPS = 1e-9
DB_FLOOR = -120.0
MAX_SLICES = 92  # MIDI notes 36..127

# Pitch tracking runs on a 4x decimated signal with a proportionally smaller frame/hop so
# its frame index f still sits at f * HOP / TARGET_SR seconds.
PITCH_DECIMATION = 4
PITCH_SR = TARGET_SR // PITCH_DECIMATION
PITCH_FRAME = FRAME // 2
PITCH_HOP = HOP // PITCH_DECIMATION

NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
MAJOR_INTERVALS = (0, 2, 4, 5, 7, 9, 11)
MINOR_INTERVALS = (0, 2, 3, 5, 7, 8, 10)
# Krumhansl–Kessler tonal hierarchies.
KK_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KK_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

PITCH_RANGE_HZ: dict[str, tuple[float, float]] = {
    "bass": (30.0, 400.0),
    "other": (60.0, 1000.0),
    "vocals": (70.0, 1000.0),
}
DEFAULT_ADSR: dict[str, Adsr] = {
    "bass": Adsr(attack_ms=5.0, decay_ms=200.0, sustain=0.7, release_ms=150.0),
    "drums": Adsr(attack_ms=1.0, decay_ms=120.0, sustain=0.0, release_ms=80.0),
    "other": Adsr(attack_ms=10.0, decay_ms=300.0, sustain=0.6, release_ms=250.0),
    "vocals": Adsr(attack_ms=15.0, decay_ms=250.0, sustain=0.7, release_ms=300.0),
}


def _hann(length: int) -> np.ndarray:
    return (0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(length) / length)).astype(np.float32)


def _autocorr(x: np.ndarray) -> np.ndarray:
    n = x.shape[-1]
    nfft = 1 << (2 * n - 1).bit_length()
    spec = np.fft.rfft(x, n=nfft, axis=-1)
    power = np.abs(spec)
    np.square(power, out=power)
    return np.fft.irfft(power, n=nfft, axis=-1)[..., :n]


_WINDOW = _hann(FRAME)
_WINDOW_SQ = _WINDOW * _WINDOW
_FREQS = np.fft.rfftfreq(FRAME, 1.0 / TARGET_SR).astype(np.float32)
_PITCH_WINDOW = _hann(PITCH_FRAME)
_PITCH_WINDOW_ACF = _autocorr(_PITCH_WINDOW.astype(np.float64))
_PITCH_WINDOW_ACF = (_PITCH_WINDOW_ACF / _PITCH_WINDOW_ACF[0]).astype(np.float32)


def _soft_edge(freqs: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """1 below ``lo``, raised-cosine to 0 at ``hi``."""
    x = np.clip((freqs - lo) / max(hi - lo, EPS), 0.0, 1.0)
    return (0.5 + 0.5 * np.cos(np.pi * x)).astype(np.float32)


_BASS_MASK = _soft_edge(_FREQS, 200.0, 250.0)
_VOCAL_BAND = (1.0 - _soft_edge(_FREQS, 250.0, 350.0)) * _soft_edge(_FREQS, 3400.0, 4200.0)


# --- decode -------------------------------------------------------------------------------


def _decode(audio_bytes: bytes, max_seconds: float) -> tuple[np.ndarray, InputInfo]:
    try:
        data, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32", always_2d=True)
    except (sf.LibsndfileError, RuntimeError, ValueError, TypeError) as exc:
        raise PipelineError("unsupported_media_type", f"cannot decode audio: {exc}") from exc
    if data.shape[0] == 0:
        raise PipelineError("unsupported_media_type", "audio contains no samples")
    max_frames = int(max_seconds * sr)
    truncated = data.shape[0] > max_frames
    data = data[:max_frames, :2]
    info = InputInfo(
        duration_seconds=round(data.shape[0] / sr, 3),
        sample_rate=int(sr),
        channels=int(data.shape[1]),
        truncated=truncated,
    )
    audio = np.ascontiguousarray(data.T)  # (channels, samples)
    if sr != TARGET_SR:
        n_out = int(round(audio.shape[1] * TARGET_SR / sr))
        t_in = np.arange(audio.shape[1], dtype=np.float64) / sr
        t_out = np.arange(n_out, dtype=np.float64) / TARGET_SR
        audio = np.stack([np.interp(t_out, t_in, ch).astype(np.float32) for ch in audio])
    return audio, info


# --- STFT ---------------------------------------------------------------------------------


def _frames(x: np.ndarray, frame: int = FRAME, hop: int = HOP) -> np.ndarray:
    """Centered frames of ``x`` (…, n) as a strided view (…, F, frame); frame f is centered
    on sample f*hop. ``frame`` must be a multiple of ``hop``."""
    pad = frame // 2
    n_frames = 1 + x.shape[-1] // hop
    padded = np.pad(x, [(0, 0)] * (x.ndim - 1) + [(pad, pad + frame)])
    view = np.lib.stride_tricks.sliding_window_view(padded, frame, axis=-1)
    return view[..., : n_frames * hop : hop, :]


def _stft(x: np.ndarray, frames_buf: np.ndarray) -> np.ndarray:
    """Hann STFT of ``x`` (ch, n) → (ch, F, bins) complex64; ``frames_buf`` (ch, F, FRAME) is
    scratch space that the caller keeps for :func:`_istft`."""
    np.copyto(frames_buf, _frames(x))
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


def _spectral_flux(mag: np.ndarray) -> np.ndarray:
    """Half-wave rectified log-magnitude difference per frame; index f is centred on f*HOP."""
    lm = np.log1p(10.0 * mag)
    diff = np.diff(lm, axis=0, prepend=lm[:1])
    return np.maximum(diff, 0.0).sum(axis=1)


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


# --- tempo, beats, key ---------------------------------------------------------------------


def _estimate_tempo(flux: np.ndarray) -> tuple[float, float]:
    """(bpm, confidence) from the onset envelope with a log-normal prior centred on 120."""
    x = flux - flux.mean()
    n = x.size
    lag_min = int(FRAME_RATE * 60.0 / 200.0)
    lag_max = min(int(FRAME_RATE * 60.0 / 60.0), n - 2)
    if n < 8 or lag_max <= lag_min or float(np.abs(x).max()) < EPS:
        return 120.0, 0.0
    acf = _autocorr(x)
    acf = acf / max(float(acf[0]), EPS)
    lags = np.arange(lag_min, lag_max + 1)
    bpms = 60.0 * FRAME_RATE / lags
    prior = np.exp(-0.5 * (np.log2(bpms / 120.0)) ** 2)
    idx = int(np.argmax(acf[lags] * prior))
    lag = int(lags[idx])
    y0, y1, y2 = acf[lag - 1], acf[lag], acf[lag + 1]
    denom = y0 - 2.0 * y1 + y2
    shift = 0.5 * (y0 - y2) / denom if abs(denom) > EPS else 0.0
    shift = float(np.clip(shift, -0.5, 0.5))
    bpm = 60.0 * FRAME_RATE / (lag + shift)
    return round(float(bpm), 2), round(float(np.clip(y1, 0.0, 1.0)), 3)


def _beats(flux: np.ndarray, bpm: float, duration: float) -> tuple[list[float], list[float]]:
    period = 60.0 * FRAME_RATE / bpm
    n = flux.size
    if n == 0:
        return [], []
    best_phase, best_score = 0, -1.0
    for phase in range(int(math.ceil(period))):
        idx = np.arange(phase, n, period).astype(int)
        idx = idx[idx < n]
        score = float(flux[idx].sum()) if idx.size else 0.0
        if score > best_score:
            best_phase, best_score = phase, score
    positions = np.arange(best_phase, n, period)
    seconds = positions * HOP / TARGET_SR
    beats = [round(float(s), 3) for s in seconds[seconds < duration]]
    if not beats:
        return [], []
    strengths = [float(flux[min(int(round(p)), n - 1)]) for p in positions[: len(beats)]]
    offset = max(range(min(4, len(beats))), key=lambda o: sum(strengths[o::4]))
    return beats[offset::4], beats


def _estimate_key(mag: np.ndarray) -> KeyInfo:
    band = (_FREQS >= 55.0) & (_FREQS <= 5000.0)
    freqs = _FREQS[band]
    pcs = (np.round(69.0 + 12.0 * np.log2(freqs / 440.0)).astype(int)) % 12
    weights = mag[:, band].mean(axis=0) if mag.shape[0] else np.zeros(freqs.size)
    chroma = np.bincount(pcs, weights=weights, minlength=12)
    if chroma.sum() < EPS or chroma.std() < EPS:
        return KeyInfo(
            root="C",
            mode="major",
            root_midi=48,
            confidence=0.0,
            scale_pitch_classes=list(MAJOR_INTERVALS),
        )
    chroma = (chroma - chroma.mean()) / chroma.std()
    best = (-2.0, 0, "major")
    for mode, profile in (("major", KK_MAJOR), ("minor", KK_MINOR)):
        prof = (profile - profile.mean()) / profile.std()
        for root in range(12):
            r = float(np.dot(chroma, np.roll(prof, root)) / 12.0)
            if r > best[0]:
                best = (r, root, mode)
    r, root, mode = best
    intervals = MAJOR_INTERVALS if mode == "major" else MINOR_INTERVALS
    return KeyInfo(
        root=NOTE_NAMES[root],
        mode=mode,  # type: ignore[arg-type]
        root_midi=48 + root,
        confidence=round(float(np.clip(r, 0.0, 1.0)), 3),
        scale_pitch_classes=[(root + i) % 12 for i in intervals],
    )


# --- onsets, envelope, ADSR ------------------------------------------------------------------


def _pick_onsets(flux: np.ndarray, min_gap_seconds: float = 0.05) -> list[int]:
    if flux.size < 3 or float(flux.max()) < EPS:
        return []
    threshold = float(flux.mean() + flux.std())
    rising = flux[1:-1] > flux[:-2]
    falling = flux[1:-1] >= flux[2:]
    above = flux[1:-1] > threshold
    candidates = np.nonzero(rising & falling & above)[0] + 1
    min_gap = max(1, int(min_gap_seconds * FRAME_RATE))
    onsets: list[int] = []
    for f in candidates.tolist():
        if onsets and f - onsets[-1] < min_gap:
            if flux[f] > flux[onsets[-1]]:
                onsets[-1] = f
            continue
        onsets.append(f)
    return onsets


def _suggest_adsr(env: np.ndarray, onsets: list[int], name: str) -> Adsr:
    if not onsets or env.size == 0:
        return DEFAULT_ADSR[name]
    ms_per_frame = 1000.0 * HOP / TARGET_SR
    attacks: list[float] = []
    decays: list[float] = []
    sustains: list[float] = []
    bounds = onsets[1:] + [min(env.size, onsets[-1] + int(2.0 * FRAME_RATE))]
    for start, end in zip(onsets, bounds, strict=True):
        seg = env[start:end]
        if seg.size < 2:
            continue
        peak_i = int(np.argmax(seg[: max(1, min(seg.size, int(0.1 * FRAME_RATE)))]))
        peak = float(seg[peak_i])
        if peak < EPS:
            continue
        tail = seg[peak_i:]
        sustain = float(np.clip(np.median(tail) / peak, 0.0, 1.0))
        below = np.nonzero(tail <= peak * max(sustain, 0.05))[0]
        decay_frames = int(below[0]) if below.size else tail.size
        attacks.append(max(peak_i, 1) * ms_per_frame)
        decays.append(max(decay_frames, 1) * ms_per_frame)
        sustains.append(sustain)
    if not attacks:
        return DEFAULT_ADSR[name]
    last = env[onsets[-1] :]
    peak = float(last.max()) if last.size else 0.0
    quiet = np.nonzero(last <= peak * 0.1)[0] if peak > EPS else np.array([])
    release = (int(quiet[0]) if quiet.size else last.size) * ms_per_frame
    return Adsr(
        attack_ms=round(float(np.clip(np.median(attacks), 1.0, 100.0)), 1),
        decay_ms=round(float(np.clip(np.median(decays), 10.0, 2000.0)), 1),
        sustain=round(float(np.median(sustains)), 3),
        release_ms=round(float(np.clip(release, 20.0, 2000.0)), 1),
    )


def _db(value: float) -> float:
    return round(max(20.0 * math.log10(value), DB_FLOOR), 2) if value > 0 else DB_FLOOR


# --- pitch tracking ------------------------------------------------------------------------


def _track_pitch(
    mono: np.ndarray, fmin: float, fmax: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-frame (midi, voiced, rms) from the window-corrected autocorrelation of the 4x
    decimated signal; the first local maximum within 90 % of the strongest one wins so
    that the fundamental beats its sub-harmonics."""
    usable = mono.shape[0] - mono.shape[0] % PITCH_DECIMATION
    x = mono[:usable].reshape(-1, PITCH_DECIMATION).mean(axis=1, dtype=np.float32)
    frames = _frames(x, PITCH_FRAME, PITCH_HOP)
    rms = np.sqrt(np.einsum("ij,ij->i", frames, frames) / PITCH_FRAME + EPS)
    acf = _autocorr(frames * _PITCH_WINDOW)
    lag_min = max(2, int(PITCH_SR / fmax))
    lag_max = min(int(PITCH_SR / fmin), PITCH_FRAME // 2)
    norm = acf[:, lag_min : lag_max + 1] / (acf[:, :1] + EPS)
    norm /= _PITCH_WINDOW_ACF[lag_min : lag_max + 1]
    inner = norm[:, 1:-1]
    strong = inner >= 0.9 * norm.max(axis=1, keepdims=True)
    is_peak = (inner >= norm[:, :-2]) & (inner >= norm[:, 2:]) & strong
    has_peak = is_peak.any(axis=1)
    best = np.where(has_peak, np.argmax(is_peak, axis=1) + 1, np.argmax(norm, axis=1))
    rows = np.arange(norm.shape[0])
    peak = norm[rows, best]
    y0 = norm[rows, np.maximum(best - 1, 0)]
    y2 = norm[rows, np.minimum(best + 1, norm.shape[1] - 1)]
    denom = y0 - 2.0 * peak + y2
    safe = np.where(np.abs(denom) > EPS, denom, 1.0)
    shift = np.where(np.abs(denom) > EPS, 0.5 * (y0 - y2) / safe, 0.0)
    lag = lag_min + best + np.clip(shift, -0.5, 0.5)
    f0 = PITCH_SR / lag
    midi = np.clip(np.round(69.0 + 12.0 * np.log2(f0 / 440.0)), 0, 127).astype(int)
    if midi.size >= 3:
        stacked = np.stack([midi[:-2], midi[1:-1], midi[2:]])
        midi = np.concatenate([midi[:1], np.median(stacked, axis=0).astype(int), midi[-1:]])
    level = float(rms.max())
    voiced = (peak > 0.5) & (rms > max(0.03 * level, 1e-4))
    return midi, voiced, rms


def _segment_notes(
    midi: np.ndarray, voiced: np.ndarray, rms: np.ndarray, min_frames: int = 3
) -> list[tuple[int, int, int, int]]:
    """Runs of equal voiced pitch → (start_frame, n_frames, pitch, velocity)."""
    notes: list[tuple[int, int, int, int]] = []
    level = float(rms.max()) if rms.size else 0.0
    start = -1
    pitch = -1

    def close(end: int) -> None:
        length = end - start
        if length >= min_frames:
            loudness = float(rms[start:end].mean()) / max(level, EPS)
            velocity = int(np.clip(round(20 + 107 * math.sqrt(loudness)), 1, 127))
            notes.append((start, length, pitch, velocity))

    for f in range(midi.size):
        if voiced[f] and midi[f] == pitch:
            continue
        if start >= 0:
            close(f)
        if voiced[f]:
            start, pitch = f, int(midi[f])
        else:
            start, pitch = -1, -1
    if start >= 0:
        close(midi.size)
    return notes


def _stem_root(notes: list[tuple[int, int, int, int]]) -> tuple[int | None, float | None]:
    if not notes:
        return None, None
    weights = np.zeros(12)
    by_midi: dict[int, float] = {}
    for _, length, pitch, _ in notes:
        weights[pitch % 12] += length
        by_midi[pitch] = by_midi.get(pitch, 0.0) + length
    root_pc = int(np.argmax(weights))
    root_midi = max((m for m in by_midi if m % 12 == root_pc), key=lambda m: (by_midi[m], -m))
    return root_midi, round(float(weights[root_pc] / weights.sum()), 3)


# --- packaging ------------------------------------------------------------------------------


def _wav_bytes(audio: np.ndarray) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, np.clip(audio.T, -1.0, 1.0), TARGET_SR, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def _smf_bytes(bpm: float, tracks: list[MidiTrack]) -> bytes:
    mf = mido.MidiFile(type=1, ticks_per_beat=PPQ)
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))
    meta.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    meta.append(mido.MetaMessage("end_of_track", time=0))
    mf.tracks.append(meta)
    for track in tracks:
        events: list[tuple[int, int, str, int, int]] = []
        for note in track.notes:
            events.append((note.start_ticks, 1, "note_on", note.pitch, note.velocity))
            events.append((note.start_ticks + note.duration_ticks, 0, "note_off", note.pitch, 0))
        events.sort()
        mt = mido.MidiTrack()
        mt.append(mido.MetaMessage("track_name", name=track.name, time=0))
        last = 0
        for tick, _, kind, pitch, velocity in events:
            mt.append(
                mido.Message(
                    kind, note=pitch, velocity=velocity, channel=track.channel, time=tick - last
                )
            )
            last = tick
        mt.append(mido.MetaMessage("end_of_track", time=0))
        mf.tracks.append(mt)
    buf = io.BytesIO()
    mf.save(file=buf)
    return buf.getvalue()


def _ticks(seconds: float, bpm: float) -> int:
    return int(round(seconds * bpm / 60.0 * PPQ))


def _seconds(frame: int) -> float:
    return round(frame * HOP / TARGET_SR, 3)


# --- entry point ---------------------------------------------------------------------------


def run_pipeline(
    audio_bytes: bytes,
    options: PipelineOptions,
    progress: ProgressCallback,
) -> PipelineResult:
    progress(STAGE_SEPARATE, 0.0)
    audio, info = _decode(audio_bytes, options.max_seconds)
    n_channels, n_samples = audio.shape
    duration = n_samples / TARGET_SR

    frames_buf = np.empty((n_channels, 1 + n_samples // HOP, FRAME), dtype=np.float32)
    spec = _stft(audio, frames_buf)  # (ch, F, bins)
    spec_buf = np.empty_like(spec)
    mono_mag = np.abs(spec[0])
    for channel in spec[1:]:
        mono_mag += np.abs(channel)
    mono_mag /= n_channels
    flux = _spectral_flux(mono_mag)
    masks = _masks(_transient_weight(flux))
    progress(STAGE_SEPARATE, 0.2)

    stem_audio: dict[str, np.ndarray] = {}
    for i, name in enumerate(options.stems):
        np.multiply(spec, masks[name], out=spec_buf)
        stem_audio[name] = _istft(spec_buf, n_samples, frames_buf)
        progress(STAGE_SEPARATE, 0.2 + 0.15 * (i + 1) / len(options.stems))
    del spec_buf, frames_buf

    progress(STAGE_TRANSCRIBE, 0.4)
    raw_notes: dict[str, list[tuple[int, int, int, int]]] = {}
    for i, name in enumerate(options.stems):
        if name in PITCH_RANGE_HZ:
            fmin, fmax = PITCH_RANGE_HZ[name]
            midi, voiced, rms = _track_pitch(stem_audio[name].mean(axis=0), fmin, fmax)
            raw_notes[name] = _segment_notes(midi, voiced, rms)
        progress(STAGE_TRANSCRIBE, 0.4 + 0.2 * (i + 1) / len(options.stems))

    progress(STAGE_ANALYZE, 0.65)
    bpm, bpm_confidence = _estimate_tempo(flux)
    downbeats, beats = _beats(flux, bpm, duration)
    analysis = Analysis(
        bpm=bpm,
        bpm_confidence=bpm_confidence,
        key=_estimate_key(mono_mag),
        downbeats_seconds=downbeats,
        beats_seconds=beats,
    )
    onsets: dict[str, list[int]] = {}
    adsr: dict[str, Adsr] = {}
    for name in options.stems:
        stem_mag = mono_mag * masks[name]
        onsets[name] = _pick_onsets(_spectral_flux(stem_mag))
        envelope = np.sqrt(np.einsum("ij,ij->i", stem_mag, stem_mag))
        adsr[name] = _suggest_adsr(envelope, onsets[name], name)
    drum_hits = onsets.get("drums", [])[:MAX_SLICES]
    drum_ends = drum_hits[1:] + [int(duration * FRAME_RATE)]
    drum_slices = [
        Slice(
            start_seconds=_seconds(start),
            end_seconds=round(min(end * HOP / TARGET_SR, duration), 3),
            midi_note=36 + i,
        )
        for i, (start, end) in enumerate(zip(drum_hits, drum_ends, strict=True))
    ]
    progress(STAGE_ANALYZE, 0.8)

    progress(STAGE_PACKAGE, 0.85)
    stems: list[StemResult] = []
    for name in options.stems:
        y = stem_audio[name]
        root_midi, root_confidence = _stem_root(raw_notes.get(name, []))
        stems.append(
            StemResult(
                name=name,
                sample_rate=TARGET_SR,
                channels=int(y.shape[0]),
                duration_seconds=round(duration, 3),
                root_midi=root_midi,
                root_confidence=root_confidence,
                peak_db=_db(float(np.abs(y).max())),
                rms_db=_db(float(np.sqrt(np.mean(y**2)))),
                transients_seconds=[_seconds(f) for f in onsets[name]],
                suggested_adsr=adsr[name],
                slices=drum_slices if name == "drums" and options.drum_slices else None,
                wav_bytes=_wav_bytes(y),
            )
        )

    tracks: list[MidiTrack] = []
    for name in options.transcribe:
        if name not in options.stems:
            continue
        if name == "drums":
            channel = 9
            events = [
                (start, max(1, end - start), 36 + i, 100)
                for i, (start, end) in enumerate(zip(drum_hits, drum_ends, strict=True))
            ]
        else:
            channel = min(len([t for t in tracks if t.channel != 9]), 15)
            events = raw_notes.get(name, [])
        notes = []
        for start_f, length_f, pitch, velocity in events:
            start_s = start_f * HOP / TARGET_SR
            dur_s = length_f * HOP / TARGET_SR
            notes.append(
                MidiNote(
                    start_seconds=round(start_s, 3),
                    duration_seconds=round(dur_s, 3),
                    start_ticks=_ticks(start_s, bpm),
                    duration_ticks=max(1, _ticks(dur_s, bpm)),
                    pitch=pitch,
                    velocity=velocity,
                )
            )
        tracks.append(MidiTrack(name=name, channel=channel, notes=notes))
    midi = MidiInfo(ppq=PPQ, bpm=bpm, tracks=tracks, smf_bytes=_smf_bytes(bpm, tracks))
    progress(STAGE_PACKAGE, 0.95)

    progress(STAGE_DONE, 1.0)
    return PipelineResult(input=info, analysis=analysis, stems=stems, midi=midi)
