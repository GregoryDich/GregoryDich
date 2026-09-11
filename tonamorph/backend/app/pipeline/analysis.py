"""Musical analysis shared by every pipeline backend (contract §2 ``analysis`` / §7).

Everything here is numpy; ``librosa`` (ISC) is used for tempo when installed, with an
onset-autocorrelation estimate as the fallback. No GPL component is involved. Key finding is
Krumhansl–Schmuckler template matching over a chroma from a plain STFT, stem roots come
from duration-weighted note statistics (melodic stems) or an energy-weighted pitch
track (bass), and ``suggest_adsr`` mirrors the plugin's ``Envelope.h`` (§8) per note.

All frame-indexed helpers take ``frame_rate`` (frames per second) so callers may use
any hop; the defaults match the 2048/512 STFT used by the fake and real backends.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import NamedTuple

import numpy as np

from app.schemas import Adsr, KeyInfo, KeyMode, Slice

log = logging.getLogger("tonamorph.pipeline.analysis")

TARGET_SR = 44100
FRAME = 2048
HOP = 512
FRAME_RATE = TARGET_SR / HOP
EPS = 1e-9
BPM_MIN = 60.0
BPM_MAX = 200.0
BPM_PRIOR = 120.0
ONSET_MIN_GAP_SECONDS = 0.05
SLICE_MIN_GAP_SECONDS = 0.05
MAX_SLICES = 64
FIRST_SLICE_NOTE = 36
ENVELOPE_HOP_SECONDS = 0.01
SILENCE_LEVEL = 10 ** (-60.0 / 20.0)
NOTE_TAIL_SECONDS = 2.0

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


class Note(NamedTuple):
    """A transcribed note before tick quantisation (see :mod:`app.pipeline.midi_export`)."""

    start_seconds: float
    duration_seconds: float
    pitch: int
    velocity: int


@dataclass(frozen=True)
class Tempo:
    bpm: float
    confidence: float
    beats_seconds: list[float] | None
    """Beat positions from the detector, or ``None`` when only the tempo is known."""
    method: str


# --- windows, frames, spectra ------------------------------------------------------------


def hann(length: int) -> np.ndarray:
    return (0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(length) / length)).astype(np.float32)


def autocorr(x: np.ndarray) -> np.ndarray:
    n = x.shape[-1]
    nfft = 1 << (2 * n - 1).bit_length()
    spec = np.fft.rfft(x, n=nfft, axis=-1)
    power = np.abs(spec)
    np.square(power, out=power)
    return np.fft.irfft(power, n=nfft, axis=-1)[..., :n]


def frames(x: np.ndarray, frame: int = FRAME, hop: int = HOP) -> np.ndarray:
    """Centered frames of ``x`` (…, n) as a strided view (…, F, frame); frame f is centered
    on sample f*hop. ``frame`` must be a multiple of ``hop``."""
    pad = frame // 2
    n_frames = 1 + x.shape[-1] // hop
    padded = np.pad(x, [(0, 0)] * (x.ndim - 1) + [(pad, pad + frame)])
    view = np.lib.stride_tricks.sliding_window_view(padded, frame, axis=-1)
    return view[..., : n_frames * hop : hop, :]


_WINDOW = hann(FRAME)
_PITCH_WINDOW = hann(PITCH_FRAME)
_PITCH_WINDOW_ACF = autocorr(_PITCH_WINDOW.astype(np.float64))
_PITCH_WINDOW_ACF = (_PITCH_WINDOW_ACF / _PITCH_WINDOW_ACF[0]).astype(np.float32)


def stft_freqs(sample_rate: int = TARGET_SR, frame: int = FRAME) -> np.ndarray:
    return np.fft.rfftfreq(frame, 1.0 / sample_rate).astype(np.float32)


def stft_magnitude(x: np.ndarray, frame: int = FRAME, hop: int = HOP) -> np.ndarray:
    """Hann-window magnitude spectrogram (F × bins) of ``x`` (n,) or (channels, n),
    averaged over channels."""
    x = np.atleast_2d(np.asarray(x, dtype=np.float32))
    window = _WINDOW if frame == FRAME else hann(frame)
    mag: np.ndarray | None = None
    for channel in x:
        spec = np.abs(np.fft.rfft(frames(channel, frame, hop) * window, axis=-1))
        mag = spec if mag is None else mag + spec
    assert mag is not None
    return (mag / x.shape[0]).astype(np.float32)


def spectral_flux(mag: np.ndarray) -> np.ndarray:
    """Half-wave rectified log-magnitude difference per frame; index f is centred on f*hop."""
    lm = np.log1p(10.0 * mag)
    diff = np.diff(lm, axis=0, prepend=lm[:1])
    return np.maximum(diff, 0.0).sum(axis=1)


# --- tempo ------------------------------------------------------------------------------


def fold_bpm(bpm: float) -> float:
    """Octave-fold ``bpm`` into [BPM_MIN, BPM_MAX]."""
    while bpm < BPM_MIN:
        bpm *= 2.0
    while bpm > BPM_MAX:
        bpm /= 2.0
    return bpm


def estimate_tempo_from_flux(
    flux: np.ndarray, frame_rate: float = FRAME_RATE
) -> tuple[float, float]:
    """(bpm, confidence) from the onset envelope's autocorrelation with a log-normal
    prior centred on :data:`BPM_PRIOR`; the pure-numpy fallback."""
    x = flux - flux.mean()
    n = x.size
    lag_min = int(frame_rate * 60.0 / BPM_MAX)
    lag_max = min(int(frame_rate * 60.0 / BPM_MIN), n - 2)
    if n < 8 or lag_max <= lag_min or float(np.abs(x).max()) < EPS:
        return BPM_PRIOR, 0.0
    acf = autocorr(x)
    acf = acf / max(float(acf[0]), EPS)
    lags = np.arange(lag_min, lag_max + 1)
    bpms = 60.0 * frame_rate / lags
    prior = np.exp(-0.5 * (np.log2(bpms / BPM_PRIOR)) ** 2)
    idx = int(np.argmax(acf[lags] * prior))
    lag = int(lags[idx])
    y0, y1, y2 = acf[lag - 1], acf[lag], acf[lag + 1]
    denom = y0 - 2.0 * y1 + y2
    shift = 0.5 * (y0 - y2) / denom if abs(denom) > EPS else 0.0
    shift = float(np.clip(shift, -0.5, 0.5))
    bpm = 60.0 * frame_rate / (lag + shift)
    return round(float(bpm), 2), round(float(np.clip(y1, 0.0, 1.0)), 3)


def tempo_confidence(flux: np.ndarray, bpm: float, frame_rate: float = FRAME_RATE) -> float:
    """Normalised onset autocorrelation at the beat period of ``bpm``."""
    x = flux - flux.mean()
    lag = int(round(frame_rate * 60.0 / bpm))
    if x.size < 8 or lag < 1 or lag >= x.size or float(np.abs(x).max()) < EPS:
        return 0.0
    acf = autocorr(x)
    return round(float(np.clip(acf[lag] / max(float(acf[0]), EPS), 0.0, 1.0)), 3)


def _tempo_librosa(mono: np.ndarray, sample_rate: int) -> Tempo | None:
    try:
        import librosa
    except ImportError:
        return None
    tempo, beats = librosa.beat.beat_track(y=mono, sr=sample_rate, units="time")
    bpm = float(np.atleast_1d(tempo)[0])
    if not math.isfinite(bpm) or bpm <= 0:
        return None
    return Tempo(
        bpm=bpm,
        confidence=-1.0,
        beats_seconds=[float(b) for b in np.atleast_1d(beats)],
        method="librosa",
    )


def estimate_tempo(
    mono: np.ndarray,
    sample_rate: int,
    flux: np.ndarray,
    frame_rate: float = FRAME_RATE,
) -> Tempo:
    """librosa → numpy. ``flux`` is the mix onset envelope used for the fallback and for
    confidence when the detector reports none."""
    for detector in (_tempo_librosa,):
        try:
            tempo = detector(mono, sample_rate)
        except Exception as exc:  # a broken optional extra must not fail the job
            log.warning("tempo detector %s failed: %s", detector.__name__, exc)
            continue
        if tempo is None:
            continue
        bpm = fold_bpm(tempo.bpm)
        beats = tempo.beats_seconds if math.isclose(bpm, tempo.bpm) else None
        confidence = (
            tempo.confidence if tempo.confidence >= 0 else tempo_confidence(flux, bpm, frame_rate)
        )
        return Tempo(round(bpm, 2), confidence, beats, tempo.method)
    bpm, confidence = estimate_tempo_from_flux(flux, frame_rate)
    return Tempo(bpm, confidence, None, "numpy")


# --- beats and downbeats ---------------------------------------------------------------


def _pick_downbeats(beats: list[float], strengths: list[float]) -> list[float]:
    if not beats:
        return []
    offset = max(range(min(4, len(beats))), key=lambda o: sum(strengths[o::4]))
    return beats[offset::4]


def track_beats(
    flux: np.ndarray, bpm: float, duration: float, frame_rate: float = FRAME_RATE
) -> tuple[list[float], list[float]]:
    """(downbeats, beats): a beat grid at ``bpm`` phase-aligned to the onset envelope,
    downbeats on the strongest of the four phases."""
    period = 60.0 * frame_rate / bpm
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
    seconds = positions / frame_rate
    beats = [round(float(s), 3) for s in seconds[seconds < duration]]
    if not beats:
        return [], []
    strengths = [float(flux[min(int(round(p)), n - 1)]) for p in positions[: len(beats)]]
    return _pick_downbeats(beats, strengths), beats


def beats_and_downbeats(
    tempo: Tempo, flux: np.ndarray, duration: float, frame_rate: float = FRAME_RATE
) -> tuple[list[float], list[float]]:
    """Detector beats when available (downbeats by onset strength), else a grid."""
    if not tempo.beats_seconds:
        return track_beats(flux, tempo.bpm, duration, frame_rate)
    beats = sorted({round(b, 3) for b in tempo.beats_seconds if 0.0 <= b < duration})
    if not beats:
        return track_beats(flux, tempo.bpm, duration, frame_rate)
    n = flux.size
    strengths = [float(flux[min(int(round(b * frame_rate)), n - 1)]) if n else 0.0 for b in beats]
    return _pick_downbeats(beats, strengths), beats


# --- key ---------------------------------------------------------------------------------


def scale_pitch_classes(root_pc: int, mode: KeyMode) -> list[int]:
    intervals = MAJOR_INTERVALS if mode == "major" else MINOR_INTERVALS
    return [(root_pc + i) % 12 for i in intervals]


def chroma_from_magnitude(mag: np.ndarray, freqs: np.ndarray) -> np.ndarray:
    """12-bin pitch-class profile from a magnitude spectrogram (F × bins), 55 Hz–5 kHz."""
    band = (freqs >= 55.0) & (freqs <= 5000.0)
    pcs = (np.round(69.0 + 12.0 * np.log2(freqs[band] / 440.0)).astype(int)) % 12
    weights = mag[:, band].mean(axis=0) if mag.shape[0] else np.zeros(int(band.sum()))
    return np.bincount(pcs, weights=weights, minlength=12)


def estimate_key_from_chroma(chroma: np.ndarray) -> KeyInfo:
    """Krumhansl–Schmuckler: the (root, mode) whose profile correlates best with ``chroma``."""
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
    return KeyInfo(
        root=NOTE_NAMES[root],
        mode=mode,  # type: ignore[arg-type]
        root_midi=48 + root,
        confidence=round(float(np.clip(r, 0.0, 1.0)), 3),
        scale_pitch_classes=scale_pitch_classes(root, mode),  # type: ignore[arg-type]
    )


def estimate_key(x: np.ndarray, sample_rate: int = TARGET_SR) -> KeyInfo:
    mag = stft_magnitude(x)
    return estimate_key_from_chroma(chroma_from_magnitude(mag, stft_freqs(sample_rate)))


# --- onsets -----------------------------------------------------------------------------


def pick_onsets(
    flux: np.ndarray,
    frame_rate: float = FRAME_RATE,
    min_gap_seconds: float = ONSET_MIN_GAP_SECONDS,
) -> list[int]:
    """Frame indices of local flux maxima above mean + std, at least ``min_gap`` apart."""
    if flux.size < 3 or float(flux.max()) < EPS:
        return []
    threshold = float(flux.mean() + flux.std())
    rising = flux[1:-1] > flux[:-2]
    falling = flux[1:-1] >= flux[2:]
    above = flux[1:-1] > threshold
    candidates = np.nonzero(rising & falling & above)[0] + 1
    min_gap = max(1, int(min_gap_seconds * frame_rate))
    onsets: list[int] = []
    for f in candidates.tolist():
        if onsets and f - onsets[-1] < min_gap:
            if flux[f] > flux[onsets[-1]]:
                onsets[-1] = f
            continue
        onsets.append(f)
    return onsets


def frames_to_seconds(indices: list[int], frame_rate: float = FRAME_RATE) -> list[float]:
    return [round(f / frame_rate, 3) for f in indices]


# --- pitch tracking ---------------------------------------------------------------------


def track_pitch(
    mono: np.ndarray, fmin: float, fmax: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-frame (midi, voiced, rms) at :data:`FRAME_RATE` from the window-corrected
    autocorrelation of the 4x decimated 44.1 kHz signal; the first local maximum within
    90 % of the strongest one wins so that the fundamental beats its sub-harmonics."""
    usable = mono.shape[0] - mono.shape[0] % PITCH_DECIMATION
    x = mono[:usable].reshape(-1, PITCH_DECIMATION).mean(axis=1, dtype=np.float32)
    framed = frames(x, PITCH_FRAME, PITCH_HOP)
    rms = np.sqrt(np.einsum("ij,ij->i", framed, framed) / PITCH_FRAME + EPS)
    acf = autocorr(framed * _PITCH_WINDOW)
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


def segment_notes(
    midi: np.ndarray,
    voiced: np.ndarray,
    rms: np.ndarray,
    min_frames: int = 3,
    frame_rate: float = FRAME_RATE,
) -> list[Note]:
    """Runs of equal voiced pitch → notes; velocity from the run's mean RMS."""
    notes: list[Note] = []
    level = float(rms.max()) if rms.size else 0.0
    start = -1
    pitch = -1

    def close(end: int) -> None:
        length = end - start
        if length >= min_frames:
            loudness = float(rms[start:end].mean()) / max(level, EPS)
            velocity = int(np.clip(round(20 + 107 * math.sqrt(loudness)), 1, 127))
            notes.append(
                Note(
                    start_seconds=round(start / frame_rate, 3),
                    duration_seconds=round(length / frame_rate, 3),
                    pitch=pitch,
                    velocity=velocity,
                )
            )

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


# --- per-stem root -----------------------------------------------------------------------


def _weighted_median(values: np.ndarray, weights: np.ndarray) -> int:
    order = np.argsort(values, kind="stable")
    cumulative = np.cumsum(weights[order])
    return int(values[order][int(np.searchsorted(cumulative, 0.5 * cumulative[-1]))])


def root_from_notes(notes: list[Note]) -> tuple[int | None, float | None]:
    """Duration-weighted median pitch; confidence = share of note time in its pitch class."""
    if not notes:
        return None, None
    pitches = np.array([n.pitch for n in notes])
    durations = np.array([max(n.duration_seconds, EPS) for n in notes])
    root = _weighted_median(pitches, durations)
    share = durations[pitches % 12 == root % 12].sum() / durations.sum()
    return root, round(float(share), 3)


def bass_root_from_audio(mono: np.ndarray) -> tuple[int | None, float | None]:
    """Energy-weighted low pitch estimate from the autocorrelation pitch track."""
    fmin, fmax = PITCH_RANGE_HZ["bass"]
    midi, voiced, rms = track_pitch(mono, fmin, fmax)
    if not voiced.any():
        return None, None
    pitches = midi[voiced]
    energy = np.square(rms[voiced].astype(np.float64))
    pc_energy = np.bincount(pitches % 12, weights=energy, minlength=12)
    root_pc = int(np.argmax(pc_energy))
    in_class = pitches % 12 == root_pc
    root = _weighted_median(pitches[in_class], energy[in_class])
    return root, round(float(pc_energy[root_pc] / max(pc_energy.sum(), EPS)), 3)


def stem_root(
    name: str, notes: list[Note], mono: np.ndarray, key: KeyInfo
) -> tuple[int | None, float | None]:
    """Contract ``root_midi`` / ``root_confidence`` for one stem; drums have none and a
    stem with nothing to measure falls back to the global key root at confidence 0."""
    if name == "drums":
        return None, None
    if name == "bass":
        root, confidence = bass_root_from_audio(mono)
    else:
        root, confidence = root_from_notes(notes)
    if root is None:
        return key.root_midi, 0.0
    return root, confidence


# --- envelope and ADSR ---------------------------------------------------------------------


def rms_envelope(
    mono: np.ndarray, sample_rate: int, hop_seconds: float = ENVELOPE_HOP_SECONDS
) -> np.ndarray:
    hop = max(1, int(sample_rate * hop_seconds))
    n_hops = int(math.ceil(mono.shape[0] / hop))
    padded = np.zeros(n_hops * hop, dtype=np.float32)
    padded[: mono.shape[0]] = mono
    blocks = padded.reshape(n_hops, hop)
    return np.sqrt(np.einsum("ij,ij->i", blocks, blocks) / hop)


def _segment_adsr(seg: np.ndarray) -> tuple[int, int, float, int] | None:
    """(attack, decay, sustain, release) of one envelope segment in hops."""
    audible = np.nonzero(seg > SILENCE_LEVEL)[0]
    if audible.size < 2:
        return None
    region = seg[audible[0] : audible[-1] + 1]
    peak_i = int(np.argmax(region))
    peak = float(region[peak_i])
    attack = int(np.nonzero(region >= 0.9 * peak)[0][0])
    third = region.size // 3
    middle = region[third : region.size - third] if third > 0 else region
    sustain = float(np.clip(np.median(middle) / peak, 0.0, 1.0))
    level = sustain * peak
    after_peak = region[peak_i:]
    below = np.nonzero(after_peak <= level)[0]
    decay = int(below[0]) if below.size else after_peak.size
    above = np.nonzero(region > level)[0]
    last_above = int(above[-1]) if above.size else peak_i
    release = region.size - 1 - last_above
    return attack, decay, sustain, release


def suggest_adsr(
    mono: np.ndarray,
    sample_rate: int,
    name: str,
    onsets_seconds: list[float] | None = None,
) -> Adsr:
    """Envelope.h semantics per note (contract §8), aggregated by median over notes.

    Attack: onset (first 10 ms hop above -60 dBFS) to 90 % of the peak. Sustain: median
    RMS of the middle third of the audible region relative to the peak. Decay: peak until
    the envelope first falls to the sustain level. Release: last hop above the sustain
    level until the envelope drops below -60 dBFS or the note ends. Clamped to attack
    1–2000 ms, decay 1–4000 ms, sustain 0–1, release 5–5000 ms.
    """
    env = rms_envelope(mono, sample_rate)
    hop_ms = 1000.0 * ENVELOPE_HOP_SECONDS
    hops_per_second = 1.0 / ENVELOPE_HOP_SECONDS
    if env.size == 0 or float(env.max()) <= SILENCE_LEVEL:
        return DEFAULT_ADSR.get(name, DEFAULT_ADSR["other"])
    starts = sorted({int(t * hops_per_second) for t in (onsets_seconds or []) if t >= 0})
    starts = [s for s in starts if s < env.size]
    if not starts:
        bounds = [(0, env.size)]
    else:
        tail = int(NOTE_TAIL_SECONDS * hops_per_second)
        ends = starts[1:] + [min(env.size, starts[-1] + tail)]
        bounds = list(zip(starts, ends, strict=True))
    measured = [m for m in (_segment_adsr(env[a:b]) for a, b in bounds) if m is not None]
    if not measured:
        return DEFAULT_ADSR.get(name, DEFAULT_ADSR["other"])
    attack, decay, sustain, release = (np.median([m[i] for m in measured]) for i in range(4))
    return Adsr(
        attack_ms=round(float(np.clip(attack * hop_ms, 1.0, 2000.0)), 1),
        decay_ms=round(float(np.clip(decay * hop_ms, 1.0, 4000.0)), 1),
        sustain=round(float(np.clip(sustain, 0.0, 1.0)), 3),
        release_ms=round(float(np.clip(release * hop_ms, 5.0, 5000.0)), 1),
    )


# --- drum slices -------------------------------------------------------------------------


def drum_slices(
    onsets_seconds: list[float],
    duration: float,
    min_gap_seconds: float = SLICE_MIN_GAP_SECONDS,
    max_slices: int = MAX_SLICES,
) -> list[Slice]:
    """Consecutive onset-to-onset regions mapped to MIDI notes from C1 (36) upwards."""
    starts: list[float] = []
    for t in sorted(onsets_seconds):
        if t < 0 or t >= duration or (starts and t - starts[-1] < min_gap_seconds):
            continue
        starts.append(t)
        if len(starts) == max_slices:
            break
    ends = starts[1:] + [duration]
    return [
        Slice(
            start_seconds=round(start, 3),
            end_seconds=round(min(end, duration), 3),
            midi_note=FIRST_SLICE_NOTE + i,
        )
        for i, (start, end) in enumerate(zip(starts, ends, strict=True))
    ]


def slices_to_notes(slices: list[Slice], velocity: int = 100) -> list[Note]:
    return [
        Note(
            start_seconds=s.start_seconds,
            duration_seconds=round(max(s.end_seconds - s.start_seconds, 0.01), 3),
            pitch=s.midi_note,
            velocity=velocity,
        )
        for s in slices
    ]


__all__ = [
    "DEFAULT_ADSR",
    "FIRST_SLICE_NOTE",
    "FRAME",
    "FRAME_RATE",
    "HOP",
    "MAJOR_INTERVALS",
    "MAX_SLICES",
    "MINOR_INTERVALS",
    "NOTE_NAMES",
    "PITCH_RANGE_HZ",
    "TARGET_SR",
    "Note",
    "Tempo",
    "autocorr",
    "bass_root_from_audio",
    "beats_and_downbeats",
    "chroma_from_magnitude",
    "drum_slices",
    "estimate_key",
    "estimate_key_from_chroma",
    "estimate_tempo",
    "estimate_tempo_from_flux",
    "fold_bpm",
    "frames",
    "frames_to_seconds",
    "hann",
    "pick_onsets",
    "rms_envelope",
    "root_from_notes",
    "scale_pitch_classes",
    "segment_notes",
    "slices_to_notes",
    "spectral_flux",
    "stem_root",
    "stft_freqs",
    "stft_magnitude",
    "suggest_adsr",
    "tempo_confidence",
    "track_beats",
    "track_pitch",
]
