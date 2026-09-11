import io
import logging

import mido
import numpy as np
import pytest

from app.config import Settings
from app.pipeline import get_pipeline, real, separation, transcription
from app.pipeline.analysis import PITCH_RANGE_HZ, Note, segment_notes, track_pitch
from app.pipeline.transcription import postprocess_notes
from app.schemas import PipelineOptions, PipelineResult

GPU_EXTRAS = separation.is_available() and transcription.is_available()


def test_gpu_modules_import_lazily() -> None:
    assert callable(real.run_pipeline) and callable(separation.separate)
    assert callable(transcription.transcribe)


@pytest.mark.skipif(separation.is_available(), reason="torch and demucs are installed")
def test_local_backend_rejected_without_extras() -> None:
    with pytest.raises(RuntimeError, match="requirements-gpu.txt"):
        get_pipeline(Settings(_env_file=None, tonamorph_pipeline="local"))
    with pytest.raises(ImportError, match="requirements-gpu.txt"):
        separation.load_model()


@pytest.mark.skipif(transcription.is_available(), reason="basic-pitch is installed")
def test_transcription_missing_extras_hint() -> None:
    with pytest.raises(ImportError, match="basic-pitch"):
        transcription.load_model()


def test_postprocess_notes() -> None:
    events = [
        (0.0, 0.5, 60, 0.5, None),
        (0.6, 0.62, 62, 0.9, None),  # shorter than 40 ms: dropped
        (1.0, 1.5, 12, 1.0, None),  # clamped to 21
        (0.2, 0.3, 120, 0.0, None),  # clamped to 108, minimum velocity 20
    ]
    notes = postprocess_notes(events)
    assert notes == [
        Note(0.0, 0.5, 60, 96),
        Note(0.2, 0.1, 108, 20),
        Note(1.0, 0.5, 21, 127),
    ]


def test_stage_timer_warns_over_budget(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(real, "BUDGET_SECONDS", 0.0)
    timer = real.StageTimer()
    with timer.stage("decode"):
        pass
    with caplog.at_level(logging.INFO, logger="tonamorph.pipeline.real"):
        timer.finish(4.0)
    assert "decode" in timer.timings
    assert any(r.levelno == logging.WARNING and "budget" in r.message for r in caplog.records)


def _cpu_separate(mix: np.ndarray) -> dict[str, np.ndarray]:
    """Stand-in for Demucs: low-pass the mix into ``bass`` by moving average, leave the
    remainder in ``drums`` and silence elsewhere."""
    kernel = np.ones(64, dtype=np.float32) / 64
    bass = np.stack([np.convolve(ch, kernel, mode="same") for ch in mix]).astype(np.float32)
    return {
        "drums": (mix - bass).astype(np.float32),
        "bass": bass,
        "other": np.zeros_like(mix),
        "vocals": np.zeros_like(mix),
    }


def _cpu_transcribe(stems: dict[str, np.ndarray], sample_rate: int) -> dict[str, list[Note]]:
    out = {}
    for name, audio in stems.items():
        fmin, fmax = PITCH_RANGE_HZ[name]
        out[name] = segment_notes(*track_pitch(audio.mean(axis=0), fmin, fmax))
    return out


def test_real_pipeline_orchestration_with_cpu_stages(
    monkeypatch: pytest.MonkeyPatch, synthetic_wav: bytes
) -> None:
    monkeypatch.setattr(real.separation, "separate", _cpu_separate)
    monkeypatch.setattr(real.transcription, "transcribe", _cpu_transcribe)
    stages: list[tuple[str, float]] = []
    result = real.run_pipeline(
        synthetic_wav, PipelineOptions(max_seconds=10.0), lambda s, p: stages.append((s, p))
    )
    assert isinstance(result, PipelineResult)
    assert [s.name for s in result.stems] == ["bass", "drums", "other", "vocals"]
    assert abs(result.analysis.bpm - 120.0) <= 3.0
    bass = result.stems[0]
    assert bass.root_midi is not None and abs(bass.root_midi - 33) <= 1
    assert result.stems[1].slices is not None and result.stems[1].slices[0].midi_note == 36
    assert result.stems[2].root_midi == result.analysis.key.root_midi  # silent stem fallback
    assert [t.name for t in result.midi.tracks] == ["bass", "other", "vocals"]
    parsed = mido.MidiFile(file=io.BytesIO(result.midi.smf_bytes))
    assert parsed.type == 1 and len(parsed.tracks) == 4
    assert stages[0] == ("separate", 0.0) and stages[-1] == ("done", 1.0)
    assert all(0.0 <= p <= 1.0 for _, p in stages)


def test_real_pipeline_rejects_short_and_bad_input(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.pipeline.base import PipelineError

    with pytest.raises(PipelineError) as info:
        real.run_pipeline(b"garbage", PipelineOptions(), lambda *_: None)
    assert info.value.code == "unsupported_media_type"
    monkeypatch.setattr(real.separation, "separate", _cpu_separate)
    from app.pipeline.audio_io import wav_bytes

    blip = wav_bytes(np.zeros((1, 1000), dtype=np.float32), 44100)
    with pytest.raises(PipelineError) as info:
        real.run_pipeline(blip, PipelineOptions(), lambda *_: None)
    assert info.value.code == "unsupported_media_type"


@pytest.mark.skipif(not GPU_EXTRAS, reason="GPU extras (torch, demucs, basic-pitch) missing")
def test_real_pipeline_end_to_end(synthetic_wav: bytes) -> None:
    result = real.run_pipeline(synthetic_wav, PipelineOptions(max_seconds=10.0), lambda *_: None)
    assert [s.name for s in result.stems] == ["bass", "drums", "other", "vocals"]
    assert result.midi.smf_bytes and all(s.wav_bytes for s in result.stems)
