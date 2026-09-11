"""``TONAMORPH_PIPELINE=local``: the GPU pipeline in-process (contract §7).

Importing this module checks that the GPU extras (torch, demucs, basic-pitch,
onnxruntime) are installed, so :func:`app.pipeline.get_pipeline` rejects the backend
at selection time with an install hint instead of failing on the first job.
"""

from app.pipeline.separation import require_extras as _require_separation
from app.pipeline.transcription import require_extras as _require_transcription

_require_separation()
_require_transcription()

from app.pipeline.real import run_pipeline, warm_up  # noqa: E402

__all__ = ["run_pipeline", "warm_up"]
