#!/usr/bin/env python3
"""Generates the bundled demo morph (GTM Appendix B §1): a 4-bar, 120 BPM, A-minor clip
already "morphed" into the plugin's own cache/result format, so the keyboard plays before
sign-in and without spending a credit.

Output (into the directory given as the only argument):
    bass.wav, drums.wav, other.wav, vocals.wav   44.1 kHz, 16-bit, mono, <= 4 s each
    score.mid                                    SMF type 1, PPQ 480, 4 bars
    result.json                                  contract §2 JobResult with "demo": true

Everything is deterministic (fixed seed, no timestamps), and a file is rewritten only when
its bytes change, so a reconfigure does not touch the build. Requires numpy; soundfile is
used when importable, otherwise the standard-library `wave` module writes the WAVs.

Usage: generate_demo.py <output-dir>
"""
from __future__ import annotations

import io
import json
import math
import struct
import sys
import wave
from pathlib import Path

import numpy as np

try:  # soundfile is preferred; `wave` produces byte-identical 16-bit PCM files.
    import soundfile as sf
except ImportError:  # pragma: no cover - depends on the configure machine
    sf = None

SAMPLE_RATE = 44100
BPM = 120.0
BEAT = 60.0 / BPM            # 0.5 s
BAR = 4 * BEAT               # 2.0 s
PPQ = 480
KEY_ROOT_MIDI = 57           # A3
A_MINOR = [9, 11, 0, 2, 4, 5, 7]
EXPIRES_AT = "2999-01-01T00:00:00Z"

rng = np.random.RandomState(20260911)


# ---------------------------------------------------------------------------- synthesis
def midi_to_hz(note: float) -> float:
    return 440.0 * 2.0 ** ((note - 69.0) / 12.0)


def seconds(n: float) -> np.ndarray:
    return np.arange(int(round(n * SAMPLE_RATE)), dtype=np.float64) / SAMPLE_RATE


def adsr(length: int, attack: float, decay: float, sustain: float, release: float, hold: float) -> np.ndarray:
    """Envelope over `length` samples: note held for `hold` seconds, then released."""
    t = np.arange(length) / SAMPLE_RATE
    env = np.ones(length)
    a = t < attack
    env[a] = t[a] / max(attack, 1e-6)
    d = (t >= attack) & (t < attack + decay)
    env[d] = 1.0 - (1.0 - sustain) * (t[d] - attack) / max(decay, 1e-6)
    s = (t >= attack + decay) & (t < hold)
    env[s] = sustain
    r = t >= hold
    env[r] = sustain * np.exp(-(t[r] - hold) / max(release, 1e-6) * 5.0)
    return env


def place(buffer: np.ndarray, start_seconds: float, signal: np.ndarray) -> None:
    start = int(round(start_seconds * SAMPLE_RATE))
    end = min(len(buffer), start + len(signal))
    if end > start:
        buffer[start:end] += signal[: end - start]


def one_pole_lowpass(x: np.ndarray, cutoff_hz: float) -> np.ndarray:
    alpha = 1.0 - math.exp(-2.0 * math.pi * cutoff_hz / SAMPLE_RATE)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):  # short signals only; keeps the script dependency-free
        acc += alpha * (v - acc)
        y[i] = acc
    return y


def soft_clip(x: np.ndarray) -> np.ndarray:
    return np.tanh(x)


def normalise(x: np.ndarray, peak_db: float) -> np.ndarray:
    peak = float(np.max(np.abs(x))) or 1.0
    return x / peak * (10.0 ** (peak_db / 20.0))


# Bass: sub sine + saw harmonics, one phrase of 2 bars (root A2 = 45).
BASS_ROOT = 45
BASS_PATTERN = [(0, 45), (1, 45), (2, 48), (3, 45), (4, 50), (5, 48), (6, 52), (7, 43)]  # (beat, midi)


def synth_bass(length_seconds: float) -> np.ndarray:
    out = np.zeros(int(length_seconds * SAMPLE_RATE))
    for beat, note in BASS_PATTERN:
        hold = BEAT * 0.8
        t = seconds(hold + 0.25)
        f = midi_to_hz(note)
        sub = np.sin(2 * np.pi * f * t)
        saw = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 9))
        env = adsr(len(t), 0.005, 0.12, 0.75, 0.08, hold)
        tone = one_pole_lowpass(0.6 * sub + 0.35 * saw, 900.0) * env
        place(out, beat * BEAT, tone)
    return normalise(soft_clip(out * 1.2), -3.0)


# Drums: kick / snare / hat over 2 bars, 16 eighth-note slices.
def synth_kick() -> np.ndarray:
    t = seconds(0.35)
    freq = 40.0 + 120.0 * np.exp(-t * 28.0)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    return np.sin(phase) * np.exp(-t * 9.0) * 1.0


def synth_snare() -> np.ndarray:
    t = seconds(0.22)
    noise = rng.uniform(-1.0, 1.0, len(t))
    noise = noise - one_pole_lowpass(noise, 1500.0)  # crude high-pass
    body = np.sin(2 * np.pi * 185.0 * t) * np.exp(-t * 30.0)
    return (0.7 * noise * np.exp(-t * 18.0) + 0.5 * body) * 0.8


def synth_hat(open_hat: bool) -> np.ndarray:
    t = seconds(0.18 if open_hat else 0.07)
    noise = rng.uniform(-1.0, 1.0, len(t))
    noise = noise - one_pole_lowpass(noise, 6000.0)
    return noise * np.exp(-t * (14.0 if open_hat else 60.0)) * 0.35


DRUM_HITS = []  # (eighth index, kind)
for bar in range(2):
    base = bar * 8
    DRUM_HITS += [(base + 0, "kick"), (base + 2, "snare"), (base + 3, "kick"), (base + 4, "kick"),
                  (base + 6, "snare"), (base + 7, "kick" if bar else "hat_open")]
    DRUM_HITS += [(base + i, "hat") for i in range(8)]


def synth_drums(length_seconds: float) -> np.ndarray:
    out = np.zeros(int(length_seconds * SAMPLE_RATE))
    kick, snare, hat, hat_open = synth_kick(), synth_snare(), synth_hat(False), synth_hat(True)
    for eighth, kind in DRUM_HITS:
        sample = {"kick": kick, "snare": snare, "hat": hat, "hat_open": hat_open}[kind]
        place(out, eighth * BEAT / 2, sample)
    return normalise(soft_clip(out), -2.0)


# Pad ("other"): detuned saws on an A-minor triad, slow attack (root A2 = 45).
PAD_ROOT = 45
PAD_CHORD = [45, 48, 52, 57]


def synth_pad(length_seconds: float) -> np.ndarray:
    t = seconds(length_seconds)
    out = np.zeros_like(t)
    for note in PAD_CHORD:
        f = midi_to_hz(note)
        for detune in (-0.4, 0.0, 0.4):
            fd = f * 2.0 ** (detune / 12.0 / 10.0)
            out += sum(np.sin(2 * np.pi * fd * k * t + 0.1 * k) / k for k in range(1, 12)) / 3.0
    env = adsr(len(t), 0.35, 0.5, 0.85, 0.5, length_seconds - 0.6)
    lfo = 1.0 + 0.04 * np.sin(2 * np.pi * 0.4 * t)
    return normalise(one_pole_lowpass(out, 2200.0) * env * lfo, -6.0)


# Vocal-like formant stem: harmonic series shaped by vowel formants "ah" -> "oo" (root A3 = 57).
VOCAL_ROOT = 57
FORMANTS_AH = [(700.0, 90.0, 1.0), (1200.0, 110.0, 0.5), (2600.0, 160.0, 0.25)]
FORMANTS_OO = [(300.0, 70.0, 1.0), (870.0, 100.0, 0.35), (2250.0, 150.0, 0.15)]


def synth_vocal(length_seconds: float) -> np.ndarray:
    t = seconds(length_seconds)
    f0 = midi_to_hz(VOCAL_ROOT) * (1.0 + 0.006 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1.0, t / 0.5))
    phase = 2 * np.pi * np.cumsum(f0) / SAMPLE_RATE
    morph = np.clip((t - 0.6) / (length_seconds - 1.0), 0.0, 1.0)
    out = np.zeros_like(t)
    for k in range(1, 36):
        fk = f0 * k
        gain = np.zeros_like(t)
        for (fa, ba, ga), (fo, bo, go) in zip(FORMANTS_AH, FORMANTS_OO):
            centre = fa + (fo - fa) * morph
            width = ba + (bo - ba) * morph
            amp = ga + (go - ga) * morph
            gain += amp * np.exp(-0.5 * ((fk - centre) / width) ** 2)
        gain *= 1.0 / (1.0 + (fk / 3000.0) ** 2)
        out += gain * np.sin(k * phase)
    env = adsr(len(t), 0.08, 0.3, 0.8, 0.25, length_seconds - 0.35)
    return normalise(out * env, -4.0)


# ---------------------------------------------------------------------------- MIDI score
def bass_notes(bars: int) -> list[dict]:
    """The two-bar bass phrase repeated across `bars` bars."""
    notes = []
    for repeat in range(bars // 2):
        for beat, midi in BASS_PATTERN:
            notes.append(note_dict(repeat * 2 * BAR + beat * BEAT, BEAT * 0.8, midi, 100))
    return notes


def pad_notes(bars: int) -> list[dict]:
    chords = [[45, 48, 52], [41, 45, 48], [48, 52, 55], [43, 47, 50]]  # Am F C G
    notes = []
    for bar in range(bars):
        for midi in chords[bar % len(chords)]:
            notes.append(note_dict(bar * BAR, BAR * 0.95, midi, 80))
    return notes


def vocal_notes() -> list[dict]:
    melody = [(0.0, 57, 1.5), (2.0, 60, 1.0), (3.0, 59, 0.5), (3.5, 57, 1.5),
              (5.0, 55, 0.75), (5.75, 57, 0.75), (6.5, 60, 1.5)]
    return [note_dict(start, duration, midi, 96) for start, midi, duration in melody]


def note_dict(start: float, duration: float, pitch: int, velocity: int) -> dict:
    return {
        "start_seconds": round(start, 4),
        "duration_seconds": round(duration, 4),
        "start_ticks": ticks(start),
        "duration_ticks": ticks(duration),
        "pitch": pitch,
        "velocity": velocity,
    }


def ticks(secs: float) -> int:
    return int(round(secs * BPM / 60.0 * PPQ))


def varint(value: int) -> bytes:
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.append(0x80 | (value & 0x7F))
        value >>= 7
    return bytes(reversed(out))


def midi_track(events: list[tuple[int, bytes]]) -> bytes:
    body = bytearray()
    last = 0
    for tick, data in sorted(events, key=lambda e: e[0]):
        body += varint(tick - last) + data
        last = tick
    body += varint(0) + b"\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(body)) + bytes(body)


def write_smf(tracks: list[dict]) -> bytes:
    tempo = int(round(60_000_000 / BPM))
    conductor = [(0, b"\xff\x51\x03" + tempo.to_bytes(3, "big")), (0, b"\xff\x58\x04\x04\x02\x18\x08")]
    chunks = [midi_track(conductor)]
    for track in tracks:
        name = track["name"].encode()
        events = [(0, b"\xff\x03" + varint(len(name)) + name)]
        channel = track["channel"]
        for note in track["notes"]:
            on = note["start_ticks"]
            off = on + max(1, note["duration_ticks"])
            events.append((on, bytes([0x90 | channel, note["pitch"], note["velocity"]])))
            events.append((off, bytes([0x80 | channel, note["pitch"], 0])))
        chunks.append(midi_track(events))
    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(chunks), PPQ)
    return header + b"".join(chunks)


# ---------------------------------------------------------------------------- packaging
def to_int16(x: np.ndarray) -> np.ndarray:
    return np.clip(np.round(x * 32767.0), -32768, 32767).astype(np.int16)


def wav_bytes(x: np.ndarray) -> bytes:
    pcm = to_int16(x)
    buffer = io.BytesIO()
    if sf is not None:
        sf.write(buffer, pcm, SAMPLE_RATE, subtype="PCM_16", format="WAV")
        return buffer.getvalue()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(pcm.tobytes())
    return buffer.getvalue()


def db(value: float) -> float:
    return round(20.0 * math.log10(max(value, 1e-9)), 2)


def stem_info(name: str, audio: np.ndarray, root_midi: int, transients: list[float], adsr_ms: dict,
              slices: list[dict] | None = None) -> dict:
    info = {
        "name": name,
        "url": None,
        "format": "wav",
        "sample_rate": SAMPLE_RATE,
        "channels": 1,
        "duration_seconds": round(len(audio) / SAMPLE_RATE, 4),
        "root_midi": root_midi,
        "root_confidence": 0.9,
        "peak_db": db(float(np.max(np.abs(audio)))),
        "rms_db": db(float(np.sqrt(np.mean(audio ** 2)))),
        "transients_seconds": [round(t, 4) for t in transients],
        "suggested_adsr": adsr_ms,
    }
    if slices is not None:
        info["slices"] = slices
    return info


def write_if_changed(path: Path, data: bytes) -> None:
    if path.exists() and path.read_bytes() == data:
        return
    path.write_bytes(data)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)

    bass = synth_bass(2 * BAR)
    drums = synth_drums(2 * BAR)
    pad = synth_pad(1.5 * BAR)
    vocal = synth_vocal(2.5)

    drum_slices = [{"start_seconds": round(i * BEAT / 2, 4), "end_seconds": round((i + 1) * BEAT / 2, 4),
                    "midi_note": 36 + i} for i in range(16)]

    tracks = [
        {"name": "bass", "channel": 0, "notes": bass_notes(4)},
        {"name": "other", "channel": 1, "notes": pad_notes(4)},
        {"name": "vocals", "channel": 2, "notes": vocal_notes()},
    ]

    result = {
        "job_id": "demo",
        "demo": True,
        "credits_charged": 0,
        "balance_after": 0,
        "input": {"duration_seconds": 4 * BAR, "sample_rate": SAMPLE_RATE, "channels": 1, "truncated": False},
        "analysis": {
            "bpm": BPM,
            "bpm_confidence": 0.98,
            "key": {"root": "A", "mode": "minor", "root_midi": KEY_ROOT_MIDI, "confidence": 0.93,
                    "scale_pitch_classes": A_MINOR},
            "downbeats_seconds": [round(bar * BAR, 4) for bar in range(4)],
            "beats_seconds": [round(beat * BEAT, 4) for beat in range(16)],
        },
        "stems": [
            stem_info("bass", bass, BASS_ROOT, [beat * BEAT for beat, _ in BASS_PATTERN],
                      {"attack_ms": 4.0, "decay_ms": 120.0, "sustain": 0.75, "release_ms": 90.0}),
            stem_info("drums", drums, 36, [i * BEAT / 2 for i in range(16)],
                      {"attack_ms": 1.0, "decay_ms": 80.0, "sustain": 1.0, "release_ms": 40.0}, drum_slices),
            stem_info("other", pad, PAD_ROOT, [0.0],
                      {"attack_ms": 350.0, "decay_ms": 500.0, "sustain": 0.85, "release_ms": 500.0}),
            stem_info("vocals", vocal, VOCAL_ROOT, [0.0],
                      {"attack_ms": 80.0, "decay_ms": 300.0, "sustain": 0.8, "release_ms": 250.0}),
        ],
        "midi": {"url": None, "ppq": PPQ, "bpm": BPM, "tracks": tracks},
        "expires_at": EXPIRES_AT,
    }

    write_if_changed(out_dir / "bass.wav", wav_bytes(bass))
    write_if_changed(out_dir / "drums.wav", wav_bytes(drums))
    write_if_changed(out_dir / "other.wav", wav_bytes(pad))
    write_if_changed(out_dir / "vocals.wav", wav_bytes(vocal))
    write_if_changed(out_dir / "score.mid", write_smf(tracks))
    write_if_changed(out_dir / "result.json", (json.dumps(result, indent=2) + "\n").encode())

    total = sum((out_dir / name).stat().st_size
                for name in ("bass.wav", "drums.wav", "other.wav", "vocals.wav", "score.mid", "result.json"))
    print(f"demo morph: {total} bytes in {out_dir}")
    return 0 if total < 1_500_000 else 1


if __name__ == "__main__":
    sys.exit(main())
