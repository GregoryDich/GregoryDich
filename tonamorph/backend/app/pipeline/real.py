"""The GPU pipeline (contract §7): Demucs v4 → Basic Pitch → analysis → package.

Selected as ``TONAMORPH_PIPELINE=local`` (see :mod:`app.pipeline.local`) and run by the
serverless / queue workers. Stage names and progress fractions follow
:data:`app.pipeline.base.PIPELINE_STAGES`; every stage is timed and logged, and a run
over the 2.0 s budget is logged as a warning with the per-stage breakdown.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter

import numpy as np

from app.pipeline import separation, transcription
from app.pipeline.analysis import (
    FRAME_RATE,
    TARGET_SR,
    Note,
    beats_and_downbeats,
    chroma_from_magnitude,
    drum_slices,
    estimate_key_from_chroma,
    estimate_tempo,
    frames_to_seconds,
    pick_onsets,
    slices_to_notes,
    spectral_flux,
    stem_root,
    stft_freqs,
    stft_magnitude,
    suggest_adsr,
)
from app.pipeline.audio_io import (
    decode_audio,
    match_channels,
    peak_db,
    rms_db,
    to_stereo,
    wav_bytes,
)
from app.pipeline.base import (
    STAGE_ANALYZE,
    STAGE_DONE,
    STAGE_PACKAGE,
    STAGE_SEPARATE,
    STAGE_TRANSCRIBE,
    PipelineError,
    ProgressCallback,
)
from app.pipeline.midi_export import build_midi
from app.schemas import Adsr, Analysis, PipelineOptions, PipelineResult, Slice, StemResult

log = logging.getLogger("tonamorph.pipeline.real")

BUDGET_SECONDS = 2.0
MIN_INPUT_SECONDS = 0.1


class StageTimer:
    """Per-stage wall-clock timings with a budget check at the end."""

    def __init__(self) -> None:
        self.timings: dict[str, float] = {}
        self._started = perf_counter()

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        started = perf_counter()
        try:
            yield
        finally:
            elapsed = perf_counter() - started
            self.timings[name] = elapsed
            log.info("pipeline stage %s took %.0f ms", name, 1000.0 * elapsed)

    def finish(self, audio_seconds: float) -> float:
        total = perf_counter() - self._started
        breakdown = ", ".join(f"{k}={1000.0 * v:.0f}ms" for k, v in self.timings.items())
        if total > BUDGET_SECONDS:
            log.warning(
                "pipeline took %.2fs for %.1fs of audio, over the %.1fs budget (%s)",
                total,
                audio_seconds,
                BUDGET_SECONDS,
                breakdown,
            )
        else:
            log.info(
                "pipeline took %.2fs for %.1fs of audio (%s)", total, audio_seconds, breakdown
            )
        return total


def warm_up() -> None:
    """Load both models and run them once; called by the workers at start-up."""
    separation.warm_up()
    transcription.warm_up()


def run_pipeline(
    audio_bytes: bytes,
    options: PipelineOptions,
    progress: ProgressCallback,
) -> PipelineResult:
    timer = StageTimer()
    progress(STAGE_SEPARATE, 0.0)
    with timer.stage("decode"):
        decoded = decode_audio(audio_bytes, options.max_seconds)
    mix = decoded.samples
    n_channels = mix.shape[0]
    duration = mix.shape[1] / TARGET_SR
    if duration < MIN_INPUT_SECONDS:
        raise PipelineError(
            "unsupported_media_type", f"audio is shorter than {MIN_INPUT_SECONDS:.1f} s"
        )
    progress(STAGE_SEPARATE, 0.05)

    with timer.stage("separate"):
        sources = separation.separate(to_stereo(mix))
    stem_audio = {name: match_channels(sources[name], n_channels) for name in options.stems}
    stem_mono = {name: y.mean(axis=0, dtype=np.float32) for name, y in stem_audio.items()}
    progress(STAGE_SEPARATE, 0.45)

    progress(STAGE_TRANSCRIBE, 0.45)
    melodic = [n for n in options.transcribe if n in options.stems and n != "drums"]
    notes: dict[str, list[Note]] = {}
    with timer.stage("transcribe"):
        if melodic:
            notes = transcription.transcribe({n: stem_audio[n] for n in melodic}, TARGET_SR)
    progress(STAGE_TRANSCRIBE, 0.65)

    progress(STAGE_ANALYZE, 0.65)
    with timer.stage("analyze"):
        mono = mix.mean(axis=0, dtype=np.float32)
        mag = stft_magnitude(mix)
        flux = spectral_flux(mag)
        tempo = estimate_tempo(mono, TARGET_SR, flux, FRAME_RATE)
        downbeats, beats = beats_and_downbeats(tempo, flux, duration, FRAME_RATE)
        key = estimate_key_from_chroma(chroma_from_magnitude(mag, stft_freqs(TARGET_SR)))
        analysis = Analysis(
            bpm=tempo.bpm,
            bpm_confidence=tempo.confidence,
            key=key,
            downbeats_seconds=downbeats,
            beats_seconds=beats,
        )
        transients: dict[str, list[float]] = {}
        adsr: dict[str, Adsr] = {}
        roots: dict[str, tuple[int | None, float | None]] = {}
        for name in options.stems:
            onsets = pick_onsets(spectral_flux(stft_magnitude(stem_mono[name])), FRAME_RATE)
            transients[name] = frames_to_seconds(onsets, FRAME_RATE)
            adsr[name] = suggest_adsr(stem_mono[name], TARGET_SR, name, transients[name])
            roots[name] = stem_root(name, notes.get(name, []), stem_mono[name], key)
        slices: list[Slice] = drum_slices(transients.get("drums", []), duration)
    log.info("tempo %.2f bpm via %s (confidence %.2f)", tempo.bpm, tempo.method, tempo.confidence)
    progress(STAGE_ANALYZE, 0.85)

    progress(STAGE_PACKAGE, 0.85)
    with timer.stage("package"):
        stems: list[StemResult] = []
        for name in options.stems:
            y = stem_audio[name]
            root_midi, root_confidence = roots[name]
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
        midi = build_midi(notes, list(options.transcribe), tempo.bpm)
    progress(STAGE_PACKAGE, 0.98)

    timer.finish(duration)
    progress(STAGE_DONE, 1.0)
    return PipelineResult(input=decoded.info, analysis=analysis, stems=stems, midi=midi)


__all__ = ["BUDGET_SECONDS", "StageTimer", "run_pipeline", "warm_up"]
