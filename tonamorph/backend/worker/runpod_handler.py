"""RunPod serverless handler (contract §7, ``TONAMORPH_PIPELINE=runpod``):
``python -u -m worker.runpod_handler``.

The request ``input`` is ``{job_id, user_id, options, audio_base64 | audio_url |
input_key, credits_reserved?}``; the handler runs the job, uploads the results under
``jobs/<user_id>/<job_id>/`` and returns ``{"job_id", "status", "result" | "error"}``
(see :func:`worker.common.run_job`). ``runpod`` is imported only in :func:`main`.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

from app.config import Settings
from app.errors import BAD_REQUEST
from app.pipeline.base import RunPipeline
from worker.common import WorkerServices, run_job_sync, warm_up_pipeline

log = logging.getLogger("tonamorph.worker.runpod")


def handler(
    event: dict[str, Any],
    *,
    settings: Settings | None = None,
    services: WorkerServices | None = None,
    run: RunPipeline | None = None,
) -> dict[str, Any]:
    payload = event.get("input") if isinstance(event, dict) else None
    if not isinstance(payload, dict):
        return {"status": "failed", "error": {"code": BAD_REQUEST, "message": "missing input"}}
    try:
        return run_job_sync(
            payload,
            settings=settings,
            services=services,
            run=run,
            worker_ref=f"runpod:{os.environ.get('RUNPOD_POD_ID', '')}",
        )
    except ValueError as exc:
        return {"status": "failed", "error": {"code": BAD_REQUEST, "message": str(exc)}}


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    try:
        import runpod
    except ImportError:
        log.error("the runpod package is required: pip install runpod")
        return 64
    from app.config import get_settings

    os.environ.setdefault("SERVICE_ROLE", "worker")
    settings = get_settings()
    warm_up_pipeline(settings)
    log.info("runpod worker ready (pipeline=%s)", settings.tonamorph_pipeline)
    runpod.serverless.start({"handler": handler})
    return 0


if __name__ == "__main__":
    sys.exit(main())
