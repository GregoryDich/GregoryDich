"""Modal deployment of the GPU pipeline (contract §7, ``SNAPPLAY_PIPELINE=modal``).

Deploy from ``backend/`` with ``modal deploy -m worker.modal_app`` (or
``modal deploy backend/worker/modal_app.py`` from the repository root). The app is
named ``snapplay-worker``; the API calls
``modal.Cls.from_name("snapplay-worker", "SnapPlayWorker")().run``.

Configuration (read at deploy time): ``SNAPPLAY_MODAL_GPU`` (default ``A10G``),
``SNAPPLAY_MODAL_MIN_CONTAINERS`` (default ``0``), ``SNAPPLAY_MODAL_SECRETS``
(comma-separated Modal secret names, default ``snapplay-supabase``). Every ``modal``
import is deferred so the module imports where Modal is not installed.
"""

from __future__ import annotations

import os
import sys
from importlib.util import find_spec
from pathlib import Path
from typing import Any

APP_NAME = "snapplay-worker"
CLASS_NAME = "SnapPlayWorker"
DEFAULT_GPU = "A10G"
TIMEOUT_SECONDS = 60
CUDA_IMAGE = "nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04"
BASIC_PITCH_PIN = "basic-pitch==0.4.0"
MODEL_CACHE_VOLUME = "snapplay-model-cache"
MODEL_CACHE_DIR = "/root/.cache"
BACKEND_DIR = Path(__file__).resolve().parents[1]


def _gpu() -> str:
    return os.environ.get("SNAPPLAY_MODAL_GPU", "").strip() or DEFAULT_GPU


def _min_containers() -> int:
    return max(0, int(os.environ.get("SNAPPLAY_MODAL_MIN_CONTAINERS", "0") or 0))


def _secret_names() -> list[str]:
    raw = os.environ.get("SNAPPLAY_MODAL_SECRETS", "snapplay-supabase")
    return [name.strip() for name in raw.split(",") if name.strip()]


def run_job_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Run one job inside the container; see :func:`worker.common.run_job`."""
    from worker.common import run_job_sync

    return run_job_sync(payload, worker_ref=f"modal:{os.environ.get('MODAL_TASK_ID', '')}")


def build_image() -> Any:
    """The worker container image; shared with ``scripts/benchmark_modal.py`` so the
    benchmark measures exactly what production runs."""
    import modal

    return (
        modal.Image.from_registry(CUDA_IMAGE, add_python="3.11")
        .apt_install("ffmpeg", "libsndfile1")
        .pip_install_from_requirements(str(BACKEND_DIR / "requirements.txt"))
        .pip_install_from_requirements(str(BACKEND_DIR / "requirements-gpu.txt"))
        # basic-pitch's own dependency list installs TensorFlow on Linux; its runtime
        # dependencies are in requirements-gpu.txt and the ONNX model runs on
        # onnxruntime-gpu (see infra/Dockerfile.worker).
        .pip_install(BASIC_PITCH_PIN, extra_options="--no-deps")
        .env(
            {
                "SNAPPLAY_PIPELINE": "local",
                "SERVICE_ROLE": "worker",
                "TORCH_HOME": f"{MODEL_CACHE_DIR}/torch",
                "PYTHONUNBUFFERED": "1",
            }
        )
        .add_local_python_source("app", "worker")
    )


def build_app() -> tuple[Any, type]:
    """Create the Modal app and worker class; requires ``modal`` to be installed."""
    import modal

    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    image = build_image()
    app = modal.App(APP_NAME)
    volume = modal.Volume.from_name(MODEL_CACHE_VOLUME, create_if_missing=True)

    @app.cls(
        image=image,
        gpu=_gpu(),
        timeout=TIMEOUT_SECONDS,
        min_containers=_min_containers(),
        secrets=[modal.Secret.from_name(name) for name in _secret_names()],
        volumes={MODEL_CACHE_DIR: volume},
    )
    class SnapPlayWorker:
        @modal.enter()
        def warm_up(self) -> None:
            from app.config import get_settings
            from worker.common import warm_up_pipeline

            warm_up_pipeline(get_settings())

        @modal.method()
        def run(
            self,
            job_id: str,
            options: dict[str, Any],
            audio_bytes: bytes | None = None,
            audio_url: str | None = None,
            *,
            user_id: str,
            input_key: str | None = None,
            credits_reserved: int = 1,
        ) -> dict[str, Any]:
            """Process one job from raw bytes, a URL or the storage object at
            ``input_key``; uploads results under ``jobs/<user_id>/<job_id>/`` and returns
            ``{"job_id", "status", "result" | "error"}``."""
            return run_job_payload(
                {
                    "job_id": job_id,
                    "user_id": user_id,
                    "options": options,
                    "audio_bytes": audio_bytes,
                    "audio_url": audio_url,
                    "input_key": input_key,
                    "credits_reserved": credits_reserved,
                }
            )

    SnapPlayWorker.__name__ = CLASS_NAME
    return app, SnapPlayWorker


if find_spec("modal") is not None:
    app, SnapPlayWorker = build_app()
else:
    app = None
    SnapPlayWorker = None

__all__ = [
    "APP_NAME",
    "CLASS_NAME",
    "DEFAULT_GPU",
    "TIMEOUT_SECONDS",
    "SnapPlayWorker",
    "app",
    "build_app",
    "build_image",
    "run_job_payload",
]
