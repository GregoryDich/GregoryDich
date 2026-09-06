#!/bin/sh
# Selects the worker process from WORKER_MODE:
#   aws    - SQS consumer for the ECS GPU service (default)
#   runpod - RunPod serverless handler
# Extra arguments are passed through to the selected module.
set -eu

case "${WORKER_MODE:-aws}" in
    aws)
        exec python -m worker.aws_worker "$@"
        ;;
    runpod)
        exec python -u -m worker.runpod_handler "$@"
        ;;
    *)
        echo "worker-entrypoint: unknown WORKER_MODE '${WORKER_MODE}' (expected aws or runpod)" >&2
        exit 64
        ;;
esac
