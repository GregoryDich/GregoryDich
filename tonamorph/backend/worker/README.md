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
| torch / torchaudio | 2.6.0+cu124 (`requirements-gpu.txt`, `download.pytorch.org/whl/cu124`) |
| demucs | 4.0.1 (`SEPARATION_MODEL` weights are downloaded to `TORCH_HOME` on first use; licence gate below) |
| basic-pitch | 0.4.0 installed with `--no-deps` (its Linux default backend is TensorFlow); the bundled ONNX model is selected explicitly |
| onnxruntime-gpu | 1.20.2 (CUDA 12.x / cuDNN 9 build; CUDA execution provider, TensorRT when its runtime is present) |
| librosa | 0.11.0 for tempo/beat tracking (a numpy estimator is the fallback; no GPL component) |
| runpod / modal | `requirements-workers.txt`, installed when the image is built with `INSTALL_WORKER_SDKS=1` (default) |
| system | `ffmpeg` (decode fallback), `libsndfile1`, 2 GiB `/dev/shm` (Basic Pitch scratch files) |

Persist `TORCH_HOME` (`/home/worker/.cache/torch` in the ECS image) so cold starts
do not re-download the Demucs weights.

**Licence gate.** With `ENV=production` a worker whose `SEPARATION_MODEL` is not
recorded as licensed for commercial use exits at start-up with
`SEPARATION_MODEL 'htdemucs' weights are not licensed for commercial use; set
SEPARATION_MODEL to a licensed model or ALLOW_UNLICENSED_SEPARATION_MODEL=1 for internal
testing`. The check runs in `worker/common.py::load_pipeline` (before torch is imported)
and again in `separation.load_model()`, so `--no-warm-up` does not bypass it.

## Environment

Everything from `backend/.env.example` applies; a worker needs at least
`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, the storage settings and
`TONAMORPH_PIPELINE=local` (the in-process GPU pipeline; `fake` runs the CPU stub and
is logged as a warning). Pipeline tuning:

| variable | default | effect |
|----------|---------|--------|
| `TONAMORPH_DEVICE` | `cuda` if available | torch device for Demucs |
| `TONAMORPH_FP16` | `1` | fp16 autocast on CUDA (`0` disables) |
| `TONAMORPH_TRT` | unset | `1` tries `torch.compile` with the TensorRT backend (`torch_tensorrt`), then the default backend, falling back to eager |
| `SEPARATION_MODEL` | `htdemucs` | separation model (`app/pipeline/separation.py` `SEPARATION_MODELS`) |
| `ALLOW_UNLICENSED_SEPARATION_MODEL` | unset | `1` lets a production worker load research-only weights; internal testing only, logged as a warning |
| `SERVICE_ROLE` | `worker` (set by the image, entrypoint and task definitions) | tells the shared `Settings` this process is a worker, not the API |
| `TONAMORPH_DEMUCS_SEGMENT` | model maximum (7.8 s) | shorter chunks to save GPU memory |
| `TONAMORPH_BASIC_PITCH_MODEL` | bundled ONNX model | alternative Basic Pitch model path |

## Entry points (INFRA_INTERFACES)

### `python -m worker.aws_worker` — `WORKER_MODE=aws` (ECS)

Consumes `SQS_JOB_QUEUE_URL` with `boto3` (`ReceiveMessage`, `WaitTimeSeconds=20`,
one message at a time). Message body: `{"job_id", "user_id", "input_key", "options"}`
where `options` is the §7 `PipelineOptions` JSON (`app.services.aws.queue`). Models are
warmed up before the first poll; each received message is first hidden for the full
`SQS_VISIBILITY_SECONDS` (300) — before the status check and the job, so a queue
configured with a shorter timeout cannot redeliver it during a slow first job — and a
timer thread keeps resetting the timeout while the job runs. Outcomes:

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

App `tonamorph-worker`, class `TonamorphWorker` (image: CUDA 12.4 + ffmpeg +
`requirements.txt` + `requirements-gpu.txt`, GPU from `TONAMORPH_MODAL_GPU` (default
`A10G`), 60 s timeout, `TONAMORPH_MODAL_MIN_CONTAINERS` warm containers, secrets from
`TONAMORPH_MODAL_SECRETS` (default `tonamorph-supabase`), model cache on the
`tonamorph-model-cache` volume). `@modal.enter()` warms both models. The API calls

```python
worker = modal.Cls.from_name("tonamorph-worker", "TonamorphWorker")()
worker.run.remote(job_id, options, audio_bytes=None, audio_url=None,
                  user_id=..., input_key=None, credits_reserved=1)
```

and receives `{"job_id", "status": "succeeded", "result": <JobResult JSON>}` or
`{"status": "failed", "error": {"code", "message"}}`.

### `python -u -m worker.runpod_handler` — `WORKER_MODE=runpod`

`runpod.serverless.start` with `handler(event)`; `event["input"]` is
`{"job_id", "user_id", "options", "audio_base64" | "audio_url" | "input_key",
"credits_reserved"?}` and the return value has the same shape as the Modal method.
