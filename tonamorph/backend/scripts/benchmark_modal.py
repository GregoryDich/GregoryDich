"""Benchmark the real GPU pipeline against the 2.0 s budget (contract §7).

The first run of ``app/pipeline/real.py`` with torch loaded happens here, not in a
customer's session. It runs the pipeline over a set of clips inside the production worker
image on Modal (``worker.modal_app.build_image``) or, with ``--local``, in this process,
and prints p50/p95 per stage plus the cold-start time.

    python -m scripts.benchmark_modal --clips ~/clips --gpu A10G --repeat 3
    python -m scripts.benchmark_modal --synthetic 5 --seconds 30 --local --pipeline fake

Exit status is 1 when p95 of the total is over the budget (``--no-fail`` disables that).
The licence gate is bypassed for the benchmark only (``ALLOW_UNLICENSED_SEPARATION_MODEL``);
see docs/ARCHITECTURE.md "Separation model and licence" before shipping the model it loads.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.pipeline.base import PIPELINE_STAGES, STAGE_DONE  # noqa: E402
from app.schemas import PipelineOptions, PipelineResult  # noqa: E402

DEFAULT_BUDGET_SECONDS = 2.0
AUDIO_SUFFIXES = {".wav", ".flac", ".mp3", ".ogg", ".aiff", ".aif", ".m4a"}
BENCH_APP_NAME = "tonamorph-benchmark"
RunPipeline = Callable[[bytes, PipelineOptions, Callable[[str, float], None]], PipelineResult]


@dataclass(frozen=True)
class Clip:
    name: str
    audio: bytes


@dataclass
class Measurement:
    clip: str
    total_seconds: float
    stage_seconds: dict[str, float]
    audio_seconds: float
    stems: list[dict[str, Any]]
    midi_notes: dict[str, int]
    bpm: float
    key: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Report:
    budget_seconds: float
    cold_start_seconds: float | None
    runs: int
    total_p50: float
    total_p95: float
    stage_p50: dict[str, float]
    stage_p95: dict[str, float]
    slowest: list[tuple[str, float]]
    measurements: list[Measurement] = field(default_factory=list)

    @property
    def within_budget(self) -> bool:
        return self.total_p95 <= self.budget_seconds


def synthetic_clip(name: str, seconds: float, sample_rate: int = 44100, bpm: float = 120.0) -> Clip:
    """Bass tone + pad + noise hits on every beat, stereo WAV — the same material the
    test-suite uses, so a benchmark run proves plumbing before real clips exist."""
    import soundfile as sf

    n = int(seconds * sample_rate)
    t = np.arange(n, dtype=np.float64) / sample_rate
    bass = 0.4 * np.sin(2 * np.pi * 55.0 * t) * (1.0 + 0.2 * np.sin(2 * np.pi * 0.5 * t))
    pad = 0.15 * (np.sin(2 * np.pi * 220.0 * t) + np.sin(2 * np.pi * 329.63 * t))
    rng = np.random.default_rng(hash(name) & 0xFFFF)
    noise = rng.standard_normal(n)
    beat = np.zeros(n)
    hit_len = int(0.03 * sample_rate)
    decay = np.exp(-np.arange(hit_len) / (0.005 * sample_rate))
    for start in np.arange(0.0, seconds, 60.0 / bpm):
        i = int(start * sample_rate)
        stop = min(i + hit_len, n)
        beat[i:stop] += 0.5 * decay[: stop - i] * noise[i:stop]
    mono = bass + pad + beat
    mono = (0.8 * mono / np.max(np.abs(mono))).astype(np.float32)
    buffer = io.BytesIO()
    sf.write(buffer, np.repeat(mono[:, None], 2, axis=1), sample_rate, format="WAV")
    return Clip(name=name, audio=buffer.getvalue())


def synthetic_clips(count: int, seconds: float) -> list[Clip]:
    return [synthetic_clip(f"synthetic-{i + 1:02d}", seconds) for i in range(count)]


def load_clips(paths: Iterable[Path]) -> list[Clip]:
    clips: list[Clip] = []
    for path in paths:
        if path.is_dir():
            clips.extend(load_clips(sorted(p for p in path.iterdir() if p.is_file())))
        elif path.suffix.lower() in AUDIO_SUFFIXES:
            clips.append(Clip(name=path.name, audio=path.read_bytes()))
    if not clips:
        raise SystemExit("no audio clips found (wav, flac, mp3, ogg, aiff, m4a)")
    return clips


def measure(clip: Clip, run_pipeline: RunPipeline, options: PipelineOptions) -> Measurement:
    """One pipeline run with a stage-boundary timeline taken from the progress callback:
    a stage lasts from its first report until the next stage's first report."""
    started_at: dict[str, float] = {}

    def progress(stage: str, _fraction: float) -> None:
        started_at.setdefault(stage, perf_counter())

    started = perf_counter()
    result = run_pipeline(clip.audio, options, progress)
    finished = perf_counter()
    started_at.setdefault(STAGE_DONE, finished)

    ordered = [s for s in PIPELINE_STAGES if s in started_at]
    stage_seconds: dict[str, float] = {}
    for current, following in zip(ordered, ordered[1:], strict=False):
        stage_seconds[current] = round(started_at[following] - started_at[current], 4)
    return Measurement(
        clip=clip.name,
        total_seconds=round(finished - started, 4),
        stage_seconds=stage_seconds,
        audio_seconds=result.input.duration_seconds,
        stems=[
            {"name": s.name, "peak_db": s.peak_db, "rms_db": s.rms_db, "root_midi": s.root_midi}
            for s in result.stems
        ],
        midi_notes={t.name: len(t.notes) for t in result.midi.tracks},
        bpm=result.analysis.bpm,
        key=f"{result.analysis.key.root} {result.analysis.key.mode}",
    )


def measure_many(
    clips: Sequence[Clip], run_pipeline: RunPipeline, options: PipelineOptions, repeat: int
) -> list[Measurement]:
    return [measure(clip, run_pipeline, options) for _ in range(repeat) for clip in clips]


def _percentile(values: Sequence[float], q: float) -> float:
    return (
        round(float(np.percentile(np.asarray(values, dtype=np.float64), q)), 4) if values else 0.0
    )


def summarise(
    measurements: Sequence[Measurement],
    *,
    budget_seconds: float = DEFAULT_BUDGET_SECONDS,
    cold_start_seconds: float | None = None,
) -> Report:
    totals = [m.total_seconds for m in measurements]
    stages = [s for s in PIPELINE_STAGES if any(s in m.stage_seconds for m in measurements)]
    per_stage = {
        s: [m.stage_seconds[s] for m in measurements if s in m.stage_seconds] for s in stages
    }
    slowest = sorted(((m.clip, m.total_seconds) for m in measurements), key=lambda x: -x[1])[:3]
    return Report(
        budget_seconds=budget_seconds,
        cold_start_seconds=cold_start_seconds,
        runs=len(measurements),
        total_p50=_percentile(totals, 50),
        total_p95=_percentile(totals, 95),
        stage_p50={s: _percentile(v, 50) for s, v in per_stage.items()},
        stage_p95={s: _percentile(v, 95) for s, v in per_stage.items()},
        slowest=slowest,
        measurements=list(measurements),
    )


def format_report(report: Report) -> str:
    lines = [f"runs: {report.runs}   budget: {report.budget_seconds:.2f}s"]
    if report.cold_start_seconds is not None:
        lines.append(f"cold start (container + model load): {report.cold_start_seconds:.1f}s")
    lines.append(f"{'stage':<12}{'p50':>9}{'p95':>9}")
    for stage in report.stage_p50:
        lines.append(f"{stage:<12}{report.stage_p50[stage]:>8.3f}s{report.stage_p95[stage]:>8.3f}s")
    lines.append(f"{'total':<12}{report.total_p50:>8.3f}s{report.total_p95:>8.3f}s")
    if report.slowest:
        lines.append(
            "slowest: " + ", ".join(f"{name} {secs:.2f}s" for name, secs in report.slowest)
        )
    verdict = "WITHIN BUDGET" if report.within_budget else "OVER BUDGET"
    lines.append(
        f"verdict: {verdict} (p95 {report.total_p95:.2f}s vs {report.budget_seconds:.2f}s)"
    )
    return "\n".join(lines)


def local_pipeline(name: str) -> RunPipeline:
    os.environ.setdefault("ALLOW_UNLICENSED_SEPARATION_MODEL", "1")
    from app.config import Settings
    from app.pipeline import get_pipeline

    settings = Settings(tonamorph_pipeline=name)  # type: ignore[call-arg]
    return get_pipeline(settings)


def run_local(
    clips: Sequence[Clip], pipeline: str, options: PipelineOptions, repeat: int
) -> Report:
    run_pipeline = local_pipeline(pipeline)
    started = perf_counter()
    measure(clips[0], run_pipeline, options)  # warm-up: model load and first kernels
    cold_start = perf_counter() - started
    return summarise(
        measure_many(clips, run_pipeline, options, repeat), cold_start_seconds=cold_start
    )


def run_remote(
    clips: Sequence[Clip],
    gpu: str,
    options: PipelineOptions,
    repeat: int,
    separation_model: str | None,
) -> Report:
    """Runs :func:`measure_many` inside the production worker image on Modal."""
    import modal

    from worker import modal_app

    env = {"ENV": "development", "ALLOW_UNLICENSED_SEPARATION_MODEL": "1"}
    if separation_model:
        env["SEPARATION_MODEL"] = separation_model
    image = modal_app.build_image().env(env).add_local_python_source("scripts")
    volume = modal.Volume.from_name(modal_app.MODEL_CACHE_VOLUME, create_if_missing=True)
    app = modal.App(BENCH_APP_NAME)

    @app.function(image=image, gpu=gpu, timeout=1800, volumes={modal_app.MODEL_CACHE_DIR: volume})
    def bench(
        payload: list[tuple[str, bytes]], options_json: str, runs: int
    ) -> list[dict[str, Any]]:
        from app.pipeline import real
        from scripts.benchmark_modal import Clip as RemoteClip
        from scripts.benchmark_modal import measure_many as remote_measure_many

        real.warm_up()
        if not payload:
            return []
        parsed = PipelineOptions.model_validate_json(options_json)
        remote_clips = [RemoteClip(name=n, audio=a) for n, a in payload]
        return [
            m.to_dict() for m in remote_measure_many(remote_clips, real.run_pipeline, parsed, runs)
        ]

    with app.run():
        started = perf_counter()
        bench.remote([], options.model_dump_json(), 0)  # container boot + model load only
        cold_start = perf_counter() - started
        raw = bench.remote([(c.name, c.audio) for c in clips], options.model_dump_json(), repeat)
    return summarise([Measurement(**m) for m in raw], cold_start_seconds=cold_start)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--clips", nargs="+", type=Path, help="audio files or directories")
    source.add_argument("--synthetic", type=int, metavar="N", help="generate N synthetic clips")
    parser.add_argument("--seconds", type=float, default=30.0, help="length of synthetic clips")
    parser.add_argument("--repeat", type=int, default=3, help="runs per clip after warm-up")
    parser.add_argument("--gpu", default=os.environ.get("TONAMORPH_MODAL_GPU", "A10G"))
    parser.add_argument("--separation-model", default=os.environ.get("SEPARATION_MODEL") or None)
    parser.add_argument("--local", action="store_true", help="run in this process instead of Modal")
    parser.add_argument(
        "--pipeline", default="local", choices=["local", "fake"], help="with --local"
    )
    parser.add_argument("--budget", type=float, default=DEFAULT_BUDGET_SECONDS)
    parser.add_argument("--json", type=Path, help="write the full report as JSON")
    parser.add_argument("--no-fail", action="store_true", help="exit 0 even when over budget")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.repeat < 1:
        raise SystemExit("--repeat must be at least 1")
    clips = (
        load_clips(args.clips) if args.clips else synthetic_clips(args.synthetic or 3, args.seconds)
    )
    options = PipelineOptions()
    if args.local:
        report = run_local(clips, args.pipeline, options, args.repeat)
    else:
        report = run_remote(clips, args.gpu, options, args.repeat, args.separation_model)
    report.budget_seconds = args.budget
    print(format_report(report))
    if args.json:
        payload = {k: v for k, v in asdict(report).items()}
        payload["within_budget"] = report.within_budget
        args.json.write_text(json.dumps(payload, indent=2))
    return 0 if report.within_budget or args.no_fail else 1


if __name__ == "__main__":
    sys.exit(main())
