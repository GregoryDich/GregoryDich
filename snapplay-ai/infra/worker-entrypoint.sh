#!/bin/sh
# Selects the worker process from WORKER_MODE:
#   aws    - SQS consumer for the ECS GPU service (default)
#   runpod - RunPod serverless handler
# Extra arguments are passed through to the selected module. A mode whose SDK is not
# installed (backend/requirements-workers.txt) fails here with exit 65 instead of a
# traceback from inside the worker.
set -eu

export SERVICE_ROLE="${SERVICE_ROLE:-worker}"

require_module() {
    module="$1"
    mode="$2"
    if ! error=$(python -c "import $module" 2>&1); then
        echo "worker-entrypoint: WORKER_MODE=$mode needs the Python package '$module', which this image cannot import:" >&2
        echo "$error" | tail -n 1 >&2
        echo "worker-entrypoint: pip install -r requirements-workers.txt, or build the image with INSTALL_WORKER_SDKS=1" >&2
        exit 65
    fi
}

case "${WORKER_MODE:-aws}" in
    aws)
        require_module boto3 aws
        exec python -m worker.aws_worker "$@"
        ;;
    runpod)
        require_module runpod runpod
        exec python -u -m worker.runpod_handler "$@"
        ;;
    *)
        echo "worker-entrypoint: unknown WORKER_MODE '${WORKER_MODE}' (expected aws or runpod)" >&2
        exit 64
        ;;
esac
