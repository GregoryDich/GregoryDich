import io
import time
from collections.abc import Callable

import mido
import numpy as np
import pytest
import soundfile as sf

from app.config import Settings
from app.pipeline import PIPELINE_STAGES, PipelineError, get_pipeline
from app.pipeline.fake import run_pipeline
from app.schemas import PipelineOptions, PipelineResult


def test_get_pipeline_selects_fake(settings: Settings) -> None:
    assert get_pipeline(settings) is run_pipeline


def test_fake_pipeline_full_result(wav_5s: bytes) -> None:
    stages: list[tuple[str, float]] = []
    result = run_pipeline(wav_5s, PipelineOptions(), lambda stage, p: stages.append((stage, p)))

    assert isinstance(result, PipelineResult)
    assert [s.name for s in result.stems] == ["bass", "drums", "other", "vocals"]
    assert result.input.model_dump() == {
        "duration_seconds": 5.0,
        "sample_rate": 44100,
        "channels": 2,
        "truncated": False,
    }
    assert {stage for stage, _ in stages} <= set(PIPELINE_STAGES)
    assert stages[-1] == ("done", 1.0)
    assert all(0.0 <= p <= 1.0 for _, p in stages)
    assert all(b <= a for (_, a), (_, b) in zip(stages[1:], stages, strict=False))

    assert 110.0 <= result.analysis.bpm <= 130.0
    assert len(result.analysis.beats_seconds) >= 8
    assert set(result.analysis.downbeats_seconds) <= set(result.analysis.beats_seconds)
    assert len(result.analysis.key.scale_pitch_classes) == 7

    bass = result.stems[0]
    assert bass.root_midi is not None and bass.root_midi % 12 == 9  # A (55 Hz)
    assert bass.suggested_adsr is not None
    drums = result.stems[1]
    assert drums.slices is not None and drums.slices[0].midi_note == 36
    assert len(drums.transients_seconds) >= 8
    assert result.stems[2].slices is None

    mix, _ = sf.read(io.BytesIO(wav_5s), dtype="float32", always_2d=True)
    total = sum(
        sf.read(io.BytesIO(s.wav_bytes), dtype="float32", always_2d=True)[0] for s in result.stems
    )
    assert np.max(np.abs(total - mix)) < 2e-3

    assert [t.name for t in result.midi.tracks] == ["bass", "other", "vocals"]
    assert result.midi.ppq == 480 and result.midi.tracks[0].notes
    parsed = mido.MidiFile(file=io.BytesIO(result.midi.smf_bytes))
    assert parsed.type == 1 and len(parsed.tracks) == 4


def test_fake_pipeline_serialisation_hides_bytes(wav_5s: bytes) -> None:
    result = run_pipeline(wav_5s, PipelineOptions(), lambda *_: None)
    dumped = result.model_dump(mode="json")
    assert "wav_bytes" not in dumped["stems"][0]
    assert "smf_bytes" not in dumped["midi"]
    assert "slices" not in dumped["stems"][0]
    assert "slices" in dumped["stems"][1]


def test_fake_pipeline_truncates_and_resamples(make_wav: Callable[..., bytes]) -> None:
    result = run_pipeline(
        make_wav(seconds=3.0, sample_rate=48000, channels=1),
        PipelineOptions(stems=["bass", "drums"], transcribe=["bass", "drums"], max_seconds=2.0),
        lambda *_: None,
    )
    assert result.input.model_dump() == {
        "duration_seconds": 2.0,
        "sample_rate": 48000,
        "channels": 1,
        "truncated": True,
    }
    assert result.stems[0].sample_rate == 44100 and result.stems[0].channels == 1
    assert [t.channel for t in result.midi.tracks] == [0, 9]


def test_fake_pipeline_is_deterministic_and_fast(make_wav: Callable[..., bytes]) -> None:
    wav = make_wav(seconds=30.0)
    first = run_pipeline(wav, PipelineOptions(), lambda *_: None)
    started = time.perf_counter()
    second = run_pipeline(wav, PipelineOptions(), lambda *_: None)
    elapsed = time.perf_counter() - started
    assert first.model_dump_json() == second.model_dump_json()
    assert first.stems[0].wav_bytes == second.stems[0].wav_bytes
    assert elapsed < 2.0


def test_fake_pipeline_rejects_garbage() -> None:
    with pytest.raises(PipelineError) as info:
        run_pipeline(b"not audio", PipelineOptions(), lambda *_: None)
    assert info.value.code == "unsupported_media_type"
