import numpy as np
import pytest

from app.pipeline import analysis
from app.pipeline.analysis import (
    DEFAULT_ADSR,
    Note,
    bass_root_from_audio,
    drum_slices,
    estimate_key,
    estimate_tempo,
    estimate_tempo_from_flux,
    root_from_notes,
    scale_pitch_classes,
    slices_to_notes,
    spectral_flux,
    stem_root,
    stft_magnitude,
    suggest_adsr,
)
from app.pipeline.audio_io import decode_audio
from app.schemas import KeyInfo

SR = 44100


def _hz(midi: int) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _progression(chords: list[list[int]], seconds_per_chord: float = 1.0) -> np.ndarray:
    n = int(seconds_per_chord * SR)
    t = np.arange(n) / SR
    parts = []
    for chord in chords:
        x = np.zeros(n)
        for midi in chord:
            for harmonic, gain in ((1, 1.0), (2, 0.3), (3, 0.1)):
                x += gain * np.sin(2 * np.pi * _hz(midi) * harmonic * t)
        parts.append(x)
    x = np.concatenate(parts)
    return (0.5 * x / np.max(np.abs(x))).astype(np.float32)


C_MAJOR = [[48, 60, 64, 67], [53, 65, 69, 72], [55, 67, 71, 74], [48, 60, 64, 67]]
A_MINOR = [[45, 57, 60, 64], [50, 62, 65, 69], [52, 64, 68, 71], [45, 57, 60, 64]]


def test_key_detection_c_major() -> None:
    key = estimate_key(_progression(C_MAJOR), SR)
    assert (key.root, key.mode) == ("C", "major")
    assert key.root_midi == 48
    assert key.scale_pitch_classes == [0, 2, 4, 5, 7, 9, 11]
    assert key.confidence > 0.5


def test_key_detection_a_minor() -> None:
    key = estimate_key(_progression(A_MINOR), SR)
    assert (key.root, key.mode) == ("A", "minor")
    assert key.root_midi == 57
    assert key.scale_pitch_classes == [9, 11, 0, 2, 4, 5, 7]


def test_key_of_silence_is_neutral() -> None:
    key = estimate_key(np.zeros(SR, dtype=np.float32), SR)
    assert key.confidence == 0.0 and (key.root, key.mode) == ("C", "major")


def test_scale_pitch_classes() -> None:
    assert scale_pitch_classes(5, "minor") == [5, 7, 8, 10, 0, 1, 3]
    assert scale_pitch_classes(7, "major") == [7, 9, 11, 0, 2, 4, 6]


def _pluck(
    seconds: float = 1.4, attack: float = 0.005, sustain: float = 0.3, hold_until: float = 0.9
) -> np.ndarray:
    t = np.arange(int(seconds * SR)) / SR
    env = np.where(t < attack, t / attack, sustain + (1 - sustain) * np.exp(-(t - attack) / 0.06))
    env = np.where(t >= hold_until, sustain * np.exp(-(t - hold_until) / 0.04), env)
    return (env * np.sin(2 * np.pi * 220.0 * t)).astype(np.float32)


def test_suggested_adsr_on_pluck() -> None:
    adsr = suggest_adsr(_pluck(), SR, "other")
    assert adsr.attack_ms <= 30.0
    assert 0.2 <= adsr.sustain <= 0.4
    assert 50.0 <= adsr.decay_ms <= 800.0
    assert 50.0 <= adsr.release_ms <= 600.0


def test_suggested_adsr_per_onset_and_silence() -> None:
    pluck = _pluck(seconds=1.0, hold_until=0.6)
    signal = np.concatenate([pluck, pluck, pluck])
    adsr = suggest_adsr(signal, SR, "bass", onsets_seconds=[0.0, 1.0, 2.0])
    assert adsr.attack_ms <= 30.0 and 0.2 <= adsr.sustain <= 0.4
    assert suggest_adsr(np.zeros(SR, dtype=np.float32), SR, "bass") == DEFAULT_ADSR["bass"]


def test_drum_slices_gap_and_limit() -> None:
    slices = drum_slices([0.0, 0.02, 0.5, 1.0, 1.04, 1.5], duration=2.0)
    assert [s.start_seconds for s in slices] == [0.0, 0.5, 1.0, 1.5]
    assert [s.end_seconds for s in slices] == [0.5, 1.0, 1.5, 2.0]
    assert [s.midi_note for s in slices] == [36, 37, 38, 39]
    many = drum_slices([i * 0.1 for i in range(100)], duration=10.0)
    assert len(many) == 64 and many[-1].midi_note == 99
    notes = slices_to_notes(slices)
    assert notes[0] == Note(0.0, 0.5, 36, 100)


def test_tempo_estimators_agree_on_clicks(synthetic_wav: bytes) -> None:
    decoded = decode_audio(synthetic_wav, 10.0)
    mono = decoded.samples.mean(axis=0)
    flux = spectral_flux(stft_magnitude(mono))
    bpm, confidence = estimate_tempo_from_flux(flux)
    assert abs(bpm - 120.0) <= 3.0 and confidence > 0.0
    tempo = estimate_tempo(mono, SR, flux)
    assert tempo.method in {"aubio", "librosa", "numpy"}
    assert abs(tempo.bpm - 120.0) <= 3.0
    downbeats, beats = analysis.beats_and_downbeats(tempo, flux, decoded.duration_seconds)
    assert len(beats) >= 6 and set(downbeats) <= set(beats)


def test_roots() -> None:
    assert root_from_notes([]) == (None, None)
    notes = [Note(0.0, 2.0, 45, 100), Note(2.0, 0.5, 52, 90), Note(2.5, 0.5, 57, 90)]
    root, confidence = root_from_notes(notes)
    assert root == 45 and confidence == pytest.approx(2.5 / 3.0, abs=1e-3)

    t = np.arange(2 * SR) / SR
    bass = (0.5 * np.sin(2 * np.pi * 55.0 * t)).astype(np.float32)
    root, confidence = bass_root_from_audio(bass)
    assert root == 33 and confidence is not None and confidence > 0.9

    key = KeyInfo(root="F", mode="minor", root_midi=53, confidence=0.8, scale_pitch_classes=[])
    assert stem_root("drums", notes, bass, key) == (None, None)
    assert stem_root("vocals", [], bass, key) == (53, 0.0)
    assert stem_root("other", notes, bass, key) == (45, pytest.approx(2.5 / 3.0, abs=1e-3))
