import json
from pathlib import Path

import pytest

from app.pipeline.fake import run_pipeline as fake_pipeline
from app.schemas import PipelineOptions
from scripts import benchmark_modal as bench


def test_synthetic_clips_are_decodable_wavs() -> None:
    clips = bench.synthetic_clips(2, seconds=2.0)
    assert [c.name for c in clips] == ["synthetic-01", "synthetic-02"]
    assert all(c.audio[:4] == b"RIFF" for c in clips)
    assert clips[0].audio != clips[1].audio


def test_measure_reports_stage_timeline_and_result_summary() -> None:
    clip = bench.synthetic_clip("m", seconds=3.0)
    m = bench.measure(clip, fake_pipeline, PipelineOptions())
    assert m.clip == "m" and m.total_seconds > 0 and m.audio_seconds == 3.0
    assert set(m.stage_seconds) <= set(bench.PIPELINE_STAGES)
    assert "separate" in m.stage_seconds and all(v >= 0 for v in m.stage_seconds.values())
    assert [s["name"] for s in m.stems] == ["bass", "drums", "other", "vocals"]
    assert m.midi_notes["bass"] > 0 and m.bpm > 0 and m.key
    assert bench.Measurement(**m.to_dict()) == m


def test_summarise_percentiles_and_budget_verdict() -> None:
    def fixed(total: float, sep: float) -> bench.Measurement:
        return bench.Measurement("c", total, {"separate": sep}, 5.0, [], {}, 120.0, "C major")

    report = bench.summarise(
        [fixed(1.0, 0.5), fixed(1.5, 0.7), fixed(3.0, 2.0)], budget_seconds=2.0
    )
    assert report.runs == 3 and report.total_p50 == 1.5 and report.total_p95 > 2.0
    assert report.stage_p50["separate"] == 0.7 and report.slowest[0] == ("c", 3.0)
    assert not report.within_budget
    text = bench.format_report(report)
    assert "OVER BUDGET" in text and "separate" in text
    assert bench.summarise([fixed(0.4, 0.1)], budget_seconds=2.0).within_budget


def test_cli_runs_the_fake_pipeline_locally(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "report.json"
    code = bench.main(
        [
            "--local",
            "--pipeline",
            "fake",
            "--synthetic",
            "2",
            "--seconds",
            "2",
            "--repeat",
            "1",
            "--json",
            str(out),
            "--budget",
            "60",
        ]
    )
    assert code == 0
    printed = capsys.readouterr().out
    assert "cold start" in printed and "WITHIN BUDGET" in printed
    payload = json.loads(out.read_text())
    assert payload["runs"] == 2 and payload["within_budget"] is True
    assert {m["clip"] for m in payload["measurements"]} == {"synthetic-01", "synthetic-02"}


def test_cli_fails_when_over_budget() -> None:
    assert (
        bench.main(
            [
                "--local",
                "--pipeline",
                "fake",
                "--synthetic",
                "1",
                "--seconds",
                "1",
                "--repeat",
                "1",
                "--budget",
                "0.000001",
            ]
        )
        == 1
    )
    assert (
        bench.main(
            [
                "--local",
                "--pipeline",
                "fake",
                "--synthetic",
                "1",
                "--seconds",
                "1",
                "--repeat",
                "1",
                "--budget",
                "0.000001",
                "--no-fail",
            ]
        )
        == 0
    )


def test_load_clips_walks_directories_and_filters_by_suffix(tmp_path: Path) -> None:
    (tmp_path / "a.wav").write_bytes(bench.synthetic_clip("a", 1.0).audio)
    (tmp_path / "notes.txt").write_text("not audio")
    clips = bench.load_clips([tmp_path])
    assert [c.name for c in clips] == ["a.wav"]
    with pytest.raises(SystemExit):
        bench.load_clips([tmp_path / "notes.txt"])
