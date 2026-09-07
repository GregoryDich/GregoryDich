"""SnapPlay API client (contract §2 jobs, §5 errors, §11 API keys).

Authenticates with ``X-API-Key``, submits multipart jobs, follows the SSE event stream to the
``result`` event and falls back to polling ``GET /v1/jobs/{id}`` when the stream is unavailable
or ends early.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import mimetypes
import uuid
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field

StemName = Literal["bass", "drums", "other", "vocals"]
JobState = Literal["queued", "running", "succeeded", "failed", "cancelled"]
_IDEMPOTENCY_NAMESPACE = uuid.UUID("2d0f7f6e-2d3b-4d0e-9a41-5c1a8b7f9c11")
_RETRYABLE_STATUSES = {429, 503}


class SnapPlayApiError(RuntimeError):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(f"{status} {code}: {message}")
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}


class _Model(BaseModel):
    model_config = ConfigDict(extra="allow")


class JobOptions(BaseModel):
    """``options`` JSON of ``POST /v1/jobs`` (all optional per contract)."""

    model_config = ConfigDict(extra="forbid")

    client_sample_rate: int | None = None
    stems: list[StemName] | None = None
    transcribe: list[StemName] | None = None
    drum_slices: bool | None = None
    target_root_midi: int | None = Field(default=None, ge=0, le=127)
    idempotency_key: str | None = None


class Balance(_Model):
    credits: int
    reserved: int
    available: int


class JobAccepted(_Model):
    job_id: str
    status: JobState
    credits_reserved: int
    balance: Balance | None = None


class InputInfo(_Model):
    duration_seconds: float
    sample_rate: int
    channels: int
    truncated: bool = False


class KeyInfo(_Model):
    root: str
    mode: str
    root_midi: int
    confidence: float
    scale_pitch_classes: list[int] = Field(default_factory=list)


class Analysis(_Model):
    bpm: float
    bpm_confidence: float | None = None
    key: KeyInfo | None = None
    downbeats_seconds: list[float] = Field(default_factory=list)
    beats_seconds: list[float] = Field(default_factory=list)


class Adsr(_Model):
    attack_ms: float
    decay_ms: float
    sustain: float
    release_ms: float


class Slice(_Model):
    start_seconds: float
    end_seconds: float
    midi_note: int


class Stem(_Model):
    name: StemName
    url: str
    format: str = "wav"
    sample_rate: int
    channels: int
    duration_seconds: float
    root_midi: int | None = None
    root_confidence: float | None = None
    peak_db: float | None = None
    rms_db: float | None = None
    transients_seconds: list[float] = Field(default_factory=list)
    suggested_adsr: Adsr | None = None
    slices: list[Slice] | None = None


class MidiNote(_Model):
    start_seconds: float
    duration_seconds: float
    start_ticks: int
    duration_ticks: int
    pitch: int
    velocity: int


class MidiTrack(_Model):
    name: str
    channel: int = 0
    notes: list[MidiNote] = Field(default_factory=list)


class MidiResult(_Model):
    url: str
    ppq: int = 480
    bpm: float
    tracks: list[MidiTrack] = Field(default_factory=list)


class JobResult(_Model):
    job_id: str
    credits_charged: int
    balance_after: int | None = None
    input: InputInfo
    analysis: Analysis
    stems: list[Stem]
    midi: MidiResult
    expires_at: str

    def track_for(self, stem_name: str) -> MidiTrack | None:
        return next((t for t in self.midi.tracks if t.name == stem_name), None)


class JobError(_Model):
    code: str
    message: str


class JobStatus(_Model):
    job_id: str
    status: JobState
    stage: str | None = None
    progress: float = 0.0
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error: JobError | None = None
    result: JobResult | None = None


def idempotency_key_for(audio_bytes: bytes, options: JobOptions) -> str:
    """Deterministic UUID per (clip bytes, options): re-posting never charges twice (§2)."""
    payload = options.model_dump(exclude_none=True, exclude={"idempotency_key"})
    digest = hashlib.sha256(audio_bytes).hexdigest() + json.dumps(payload, sort_keys=True)
    return str(uuid.uuid5(_IDEMPOTENCY_NAMESPACE, digest))


def _raise_for_error(response: httpx.Response) -> None:
    if response.status_code < 400:
        return
    code, message, details = "http_error", response.reason_phrase or "", {}
    try:
        body = response.json()
        err = body.get("error", {}) if isinstance(body, dict) else {}
        code = err.get("code", code)
        message = err.get("message", message)
        details = err.get("details", {}) or {}
    except ValueError:
        pass
    raise SnapPlayApiError(response.status_code, code, message, details)


def _parse_sse(lines: list[str]) -> tuple[str, str] | None:
    """Return (event, data) for one complete SSE block, ignoring comment lines."""
    event = "message"
    data: list[str] = []
    for line in lines:
        if not line or line.startswith(":"):
            continue
        field, _, value = line.partition(":")
        value = value.removeprefix(" ")
        if field == "event":
            event = value
        elif field == "data":
            data.append(value)
    if not data:
        return None
    return event, "\n".join(data)


class SnapPlayClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        http: httpx.AsyncClient | None = None,
        poll_interval: float = 2.0,
        timeout: float = 600.0,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._headers = {"X-API-Key": api_key, "Accept": "application/json"}
        self._http = http or httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=120.0))
        self._owns_http = http is None
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.max_retries = max_retries

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> SnapPlayClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Send, honouring ``Retry-After`` on 429/503 up to ``max_retries`` times (§5)."""
        for attempt in range(self.max_retries + 1):
            response = await self._http.request(method, url, headers=self._headers, **kwargs)
            if response.status_code in _RETRYABLE_STATUSES and attempt < self.max_retries:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else 1.0
                await asyncio.sleep(delay)
                continue
            _raise_for_error(response)
            return response
        raise AssertionError("unreachable")

    async def submit_job(
        self, audio_bytes: bytes, filename: str, options: JobOptions | None = None
    ) -> JobAccepted:
        opts = options or JobOptions()
        if opts.idempotency_key is None:
            opts = opts.model_copy(
                update={"idempotency_key": idempotency_key_for(audio_bytes, opts)}
            )
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        response = await self._request(
            "POST",
            f"{self.base_url}/v1/jobs",
            files={"audio": (Path(filename).name, audio_bytes, mime)},
            data={"options": json.dumps(opts.model_dump(exclude_none=True))},
        )
        return JobAccepted.model_validate(response.json())

    async def get_job(self, job_id: str) -> JobStatus:
        response = await self._request("GET", f"{self.base_url}/v1/jobs/{job_id}")
        return JobStatus.model_validate(response.json())

    async def follow_events(self, job_id: str) -> JobStatus | None:
        """Consume the SSE stream; None when it ends without a terminal event."""
        url = f"{self.base_url}/v1/jobs/{job_id}/events"
        headers = {**self._headers, "Accept": "text/event-stream"}
        try:
            async with self._http.stream("GET", url, headers=headers) as response:
                if response.status_code >= 400:
                    return None
                block: list[str] = []
                async for line in response.aiter_lines():
                    if line.strip() == "":
                        parsed = _parse_sse(block)
                        block = []
                        if parsed is None:
                            continue
                        event, data = parsed
                        if event == "result":
                            return JobStatus.model_validate(json.loads(data))
                        if event == "error":
                            err = JobError.model_validate(json.loads(data))
                            raise SnapPlayApiError(200, err.code, err.message)
                        continue
                    block.append(line.rstrip("\r"))
                parsed = _parse_sse(block)
                if parsed and parsed[0] == "result":
                    return JobStatus.model_validate(json.loads(parsed[1]))
        except httpx.HTTPError:
            return None
        return None

    async def wait_for_result(self, job_id: str) -> JobStatus:
        """SSE first, then poll until ``succeeded``/``failed``; raises on failure or timeout."""
        deadline = asyncio.get_running_loop().time() + self.timeout
        status = await self.follow_events(job_id)
        while status is None or status.status in ("queued", "running"):
            if asyncio.get_running_loop().time() > deadline:
                raise TimeoutError(f"job {job_id} did not finish within {self.timeout:.0f}s")
            await asyncio.sleep(self.poll_interval)
            status = await self.get_job(job_id)
        if status.status != "succeeded" or status.result is None:
            err = status.error or JobError(code="job_failed", message=f"job status {status.status}")
            raise SnapPlayApiError(200, err.code, err.message)
        return status

    async def download(self, url: str, dest: Path) -> Path:
        """Stream a signed asset URL to ``dest`` (signed URLs carry no API key)."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with self._http.stream("GET", url) as response:
            _raise_for_error(response)
            with dest.open("wb") as fh:
                async for chunk in response.aiter_bytes():
                    fh.write(chunk)
        return dest
