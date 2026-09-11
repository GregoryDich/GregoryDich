"""infra/worker-entrypoint.sh: mode dispatch and the fail-fast on a missing SDK, run
with a stand-in ``python`` on PATH that only knows the modules named in FAKE_MODULES."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ENTRYPOINT = Path(__file__).resolve().parents[3] / "infra" / "worker-entrypoint.sh"

FAKE_PYTHON = """#!/bin/sh
# ``python -c "import X"`` succeeds only for modules listed in FAKE_MODULES; any other
# invocation is the exec'd worker and prints what it was asked to run.
if [ "$1" = "-c" ]; then
    module=$(printf '%s' "$2" | sed 's/^import //')
    case " ${FAKE_MODULES:-} " in
        *" $module "*) exit 0 ;;
        *) echo "ModuleNotFoundError: No module named '$module'" >&2; exit 1 ;;
    esac
fi
echo "EXEC: $* SERVICE_ROLE=${SERVICE_ROLE:-unset}"
"""


@pytest.fixture
def run_entrypoint(tmp_path: Path):
    shim = tmp_path / "python"
    shim.write_text(FAKE_PYTHON)
    shim.chmod(0o755)

    def _run(mode: str | None, modules: str, *args: str) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "FAKE_MODULES": modules}
        env.pop("SERVICE_ROLE", None)
        if mode is None:
            env.pop("WORKER_MODE", None)
        else:
            env["WORKER_MODE"] = mode
        return subprocess.run(
            ["sh", str(ENTRYPOINT), *args], env=env, capture_output=True, text=True, timeout=30
        )

    return _run


def test_script_parses() -> None:
    for shell in ("sh", "bash"):
        subprocess.run([shell, "-n", str(ENTRYPOINT)], check=True)


def test_default_mode_is_aws_and_exports_service_role(run_entrypoint) -> None:
    result = run_entrypoint(None, "boto3", "--once")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "EXEC: -m worker.aws_worker --once SERVICE_ROLE=worker"


def test_runpod_mode_runs_the_handler_when_the_sdk_is_present(run_entrypoint) -> None:
    result = run_entrypoint("runpod", "boto3 runpod")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "EXEC: -u -m worker.runpod_handler SERVICE_ROLE=worker"


def test_missing_sdk_fails_fast_with_a_clear_message(run_entrypoint) -> None:
    result = run_entrypoint("runpod", "boto3")
    assert result.returncode == 65
    assert result.stdout == ""
    assert "WORKER_MODE=runpod needs the Python package 'runpod'" in result.stderr
    assert "No module named 'runpod'" in result.stderr
    assert "requirements-workers.txt" in result.stderr


def test_unknown_mode_is_rejected(run_entrypoint) -> None:
    result = run_entrypoint("lambda", "boto3 runpod")
    assert result.returncode == 64
    assert "unknown WORKER_MODE 'lambda'" in result.stderr
