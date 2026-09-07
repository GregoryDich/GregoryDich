# GPU worker

The audio pipeline of contract §7 (Demucs v4 `htdemucs` → Basic Pitch → analysis →
package) packaged for the three deployment paths of §10. All entry points share
`worker/common.py`: parse the job, mark it running, fetch the input, run
`run_pipeline` in a thread while relaying progress, upload `bass.wav`, `drums.wav`,
`other.wav`, `vocals.wav` and `score.mid` to `jobs/<user_id>/<job_id>/`, sign the
URLs and call `complete_job` / `fail_job` (both idempotent) through the job service.

## Image requirements

| component | requirement |
|-----------|-------------|
| CUDA | 12.x runtime with cuDNN (`nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04`, see `infra/Dockerfile.worker`) |
| Python | 3.11 |
| torch | 2.x with CUDA (`requirements-gpu.txt`) |
| demucs | ≥ 4.0.1 (`htdemucs` weights are downloaded to `TORCH_HOME` on first use) |
| basic-pitch | ≥ 0.4 with the bundled ONNX model |
| onnxruntime-gpu | ≥ 1.17 (TensorRT and CUDA execution providers) |
| aubio | ≥ 0.4.9 for tempo/beat tracking (librosa or a numpy estimator are the fallbacks) |
| system | `ffmpeg` (decode fallback), `libsndfile1`, 2 GiB `/dev/shm` (Basic Pitch scratch files) |

Persist `TORCH_HOME` (`/home/worker/.cache/torch` in the ECS image) so cold starts
do not re-download the Demucs weights.

## Environment

Everything from `backend/.env.example` applies; a worker needs at least
`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, the storage settings and
`SNAPPLAY_PIPELINE=local` (the in-process GPU pipeline; `fake` runs the CPU stub and
is logged as a warning). Pipeline tuning:

| variable | default | effect |
|----------|---------|--------|
| `SNAPPLAY_DEVICE` | `cuda` if available | torch device for Demucs |
| `SNAPPLAY_FP16` | `1` | fp16 autocast on CUDA (`0` disables) |
| `SNAPPLAY_TRT` | unset | `1` tries `torch.compile` with the TensorRT backend (`torch_tensorrt`), then the default backend, falling back to eager |
| `SNAPPLAY_DEMUCS_MODEL` | `htdemucs` | Demucs model name |
| `SNAPPLAY_DEMUCS_SEGMENT` | model maximum (7.8 s) | shorter chunks to save GPU memory |
| `SNAPPLAY_BASIC_PITCH_MODEL` | bundled ONNX model | alternative Basic Pitch model path |

## Entry points (INFRA_INTERFACES)

### `python -m worker.aws_worker` — `WORKER_MODE=aws` (ECS)

Consumes `SQS_JOB_QUEUE_URL` with `boto3` (`ReceiveMessage`, `WaitTimeSeconds=20`,
one message at a time). Message body: `{"job_id", "user_id", "input_key", "options"}`
where `options` is the §7 `PipelineOptions` JSON (`app.services.aws.queue`). While a
job runs a timer thread resets the visibility timeout to `SQS_VISIBILITY_SECONDS`
(300). Outcomes:

* success → `complete_job`, `DeleteMessage`;
* input the pipeline rejects (`PipelineError`) → `fail_job`, `DeleteMessage`;
* job already `succeeded`/`failed`/`cancelled` → `DeleteMessage`, nothing else;
* any other failure → the message is made visible again and *not* deleted, so SQS
  redelivers it; on receive number `SQS_MAX_RECEIVE_COUNT` (3) the job is failed with
  `internal_error` and the message is left for the DLQ redrive.

`--once` polls a single time, `--max-messages N` exits after N messages,
`--no-warm-up` skips model loading at start-up. SIGTERM/SIGINT finish the current job
before exiting (ECS `stopTimeout` is 120 s).

### `modal deploy -m worker.modal_app` — Modal

App `snapplay-worker`, class `SnapPlayWorker` (image: CUDA 12.4 + ffmpeg +
`requirements.txt` + `requirements-gpu.txt`, GPU from `SNAPPLAY_MODAL_GPU` (default
`A10G`), 60 s timeout, `SNAPPLAY_MODAL_MIN_CONTAINERS` warm containers, secrets from
`SNAPPLAY_MODAL_SECRETS` (default `snapplay-supabase`), model cache on the
`snapplay-model-cache` volume). `@modal.enter()` warms both models. The API calls

```python
worker = modal.Cls.from_name("snapplay-worker", "SnapPlayWorker")()
worker.run.remote(job_id, options, audio_bytes=None, audio_url=None,
                  user_id=..., input_key=None, credits_reserved=1)
```

and receives `{"job_id", "status": "succeeded", "result": <JobResult JSON>}` or
`{"status": "failed", "error": {"code", "message"}}`.

### `python -u -m worker.runpod_handler` — `WORKER_MODE=runpod`

`runpod.serverless.start` with `handler(event)`; `event["input"]` is
`{"job_id", "user_id", "options", "audio_base64" | "audio_url" | "input_key",
"credits_reserved"?}` and the return value has the same shape as the Modal method.
