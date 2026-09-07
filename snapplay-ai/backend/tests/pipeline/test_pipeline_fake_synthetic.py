import io

import mido

from app.pipeline import PIPELINE_STAGES
from app.pipeline.fake import run_pipeline
from app.schemas import PipelineOptions


def test_fake_pipeline_on_bass_and_clicks(synthetic_wav: bytes) -> None:
    stages: list[tuple[str, float]] = []
    result = run_pipeline(
        synthetic_wav, PipelineOptions(max_seconds=10.0), lambda s, p: stages.append((s, p))
    )

    assert abs(result.analysis.bpm - 120.0) <= 3.0
    assert result.analysis.bpm_confidence > 0.0
    assert [s.name for s in result.stems] == ["bass", "drums", "other", "vocals"]
    assert result.input.duration_seconds == 4.0 and result.input.truncated is False

    bass = result.stems[0]
    assert bass.root_midi is not None and abs(bass.root_midi - 33) <= 1
    assert bass.root_confidence is not None and bass.root_confidence > 0.5
    assert bass.suggested_adsr is not None

    drums = result.stems[1]
    assert drums.slices is not None and drums.slices[0].midi_note == 36
    assert len(drums.transients_seconds) >= 6

    parsed = mido.MidiFile(file=io.BytesIO(result.midi.smf_bytes))
    assert parsed.type == 1 and parsed.ticks_per_beat == 480
    assert [t.name for t in result.midi.tracks] == ["bass", "other", "vocals"]
    assert len(parsed.tracks) == 4

    assert {s for s, _ in stages} <= set(PIPELINE_STAGES)
    assert stages[0] == ("separate", 0.0) and stages[-1] == ("done", 1.0)
    order = {s: i for i, s in enumerate(PIPELINE_STAGES)}
    assert all(order[b] >= order[a] for (a, _), (b, _) in zip(stages, stages[1:], strict=False))
