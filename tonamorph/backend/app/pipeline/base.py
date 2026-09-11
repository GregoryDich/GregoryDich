"""Pipeline interface shared by the API and the GPU workers (docs/API_CONTRACT.md §7)."""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from typing import Protocol

from app.config import Settings
from app.schemas import PipelineOptions, PipelineResult

STAGE_UPLOAD = "upload"
STAGE_SEPARATE = "separate"
STAGE_TRANSCRIBE = "transcribe"
STAGE_ANALYZE = "analyze"
STAGE_PACKAGE = "package"
STAGE_DONE = "done"
PIPELINE_STAGES: tuple[str, ...] = (
    STAGE_UPLOAD,
    STAGE_SEPARATE,
    STAGE_TRANSCRIBE,
    STAGE_ANALYZE,
    STAGE_PACKAGE,
    STAGE_DONE,
)

ProgressCallback = Callable[[str, float], None]
"""``progress(stage, fraction)``: ``stage`` from :data:`PIPELINE_STAGES`, ``0 <= fraction <= 1``."""


class PipelineError(RuntimeError):
    """Raised by a pipeline for input it cannot process.

    ``code`` is a §5 error code (``unsupported_media_type`` for undecodable audio,
    ``internal_error`` otherwise) so callers can map it to a job error without guessing.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class RunPipeline(Protocol):
    """Signature of ``run_pipeline`` implemented by every backend module."""

    def __call__(
        self,
        audio_bytes: bytes,
        options: PipelineOptions,
        progress: ProgressCallback,
    ) -> PipelineResult: ...


def get_pipeline(settings: Settings) -> RunPipeline:
    """Return the ``run_pipeline`` callable for ``settings.tonamorph_pipeline``.

    Backends live in ``app.pipeline.<name>`` and expose a module-level ``run_pipeline``.
    A backend that is not installed raises ``RuntimeError`` at selection time rather
    than on the first job.
    """
    name = settings.tonamorph_pipeline
    try:
        module = import_module(f"app.pipeline.{name}")
    except ImportError as exc:
        raise RuntimeError(f"pipeline backend {name!r} is not available: {exc}") from exc
    run = getattr(module, "run_pipeline", None)
    if run is None:
        raise RuntimeError(f"app.pipeline.{name} does not define run_pipeline")
    return run
