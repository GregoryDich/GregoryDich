"""End-to-end smoke test of a live Tonamorph deployment (docs/LAUNCH_CHECKLIST.md §2.3).

Proves from the outside that the pieces the first live day depends on fit together: GoTrue
creates a confirmed account and the sign-up trigger grants 3 credits, the API signs it in,
accepts a clip, runs it to four stems and a MIDI file, charges exactly one credit, answers
the public status and version routes, and deletes the account into a tombstone that
refuses the still-valid token.

    export TONAMORPH_API_URL=https://api.<domain>
    export SUPABASE_URL=https://<ref>.supabase.co
    export SUPABASE_SERVICE_ROLE_KEY=<service_role key>      # never printed
    python -m scripts.live_smoke                              # synthesises a 5 s clip
    python -m scripts.live_smoke --audio ~/clips/loop.wav
    python -m scripts.live_smoke --pipeline-expect fake       # staging with the CPU stub
    python -m scripts.live_smoke --keep-user                  # leave the account behind

One PASS / FAIL / SKIP line per step; exit status 1 when any step failed. The throwaway
account (``smoke+<timestamp>@<domain>``) is deleted at the end even when an earlier step
failed, unless ``--keep-user`` is given. Tokens and keys never appear in the output.

The flow is a set of methods on :class:`SmokeRun` over injected httpx clients, so
``tests/test_live_smoke.py`` runs the same code against the in-process app.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import secrets
import sys
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

import httpx

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas import JobResult, StatusResponse, VersionResponse  # noqa: E402
from scripts.benchmark_modal import synthetic_clip  # noqa: E402

Outcome = Literal["PASS", "FAIL", "SKIP"]
PipelineExpectation = Literal["fake", "real"]
Download = Callable[[str], bytes]

REQUIRED_ENV = ("TONAMORPH_API_URL", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
SYNTHETIC_SECONDS = 5.0
FREE_CREDITS = 3
STEM_NAMES = ["bass", "drums", "other", "vocals"]
TIMEOUTS: dict[str, float] = {"fake": 60.0, "real": 600.0}
"""Seconds a job may take: the CPU stub finishes in seconds; a real worker may have to
boot a container and load the model first (contract §7 cold start)."""
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0", "testserver"})
FALLBACK_DOMAIN = "example.com"


class StepFailed(Exception):
    """A step's own verdict; the message is the detail column (never a secret)."""


@dataclass(frozen=True)
class Step:
    name: str
    outcome: Outcome
    detail: str

    @property
    def ok(self) -> bool:
        return self.outcome != "FAIL"


def smoke_email(api_url: str, now: datetime | None = None) -> str:
    """``smoke+<UTC timestamp>@<domain>``: the API host without a leading ``api.`` label,
    or ``example.com`` for localhost, bare hosts and IP addresses. Nothing is ever sent to
    it — the account is created already confirmed."""
    host = (urlsplit(api_url).hostname or "").lower()
    domain = host.removeprefix("api.")
    if (
        not domain
        or domain in LOCAL_HOSTS
        or "." not in domain
        or all(part.isdigit() for part in domain.split("."))
        or ":" in domain
    ):
        domain = FALLBACK_DOMAIN
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%d%H%M%S")
    return f"smoke+{stamp}@{domain}"


def service_headers(service_role_key: str) -> dict[str, str]:
    """What GoTrue's admin API expects from a server-side caller."""
    return {"apikey": service_role_key, "Authorization": f"Bearer {service_role_key}"}


def describe_error(exc: BaseException) -> str:
    """``TypeName: message`` with query strings cut off — a signed URL carries its token
    in the query, and httpx puts URLs into some messages."""
    text = re.sub(r"\?[^\s'\"]*", "?…", str(exc))
    text = re.sub(r"Bearer \S+", "Bearer …", text)
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


def api_error(response: httpx.Response) -> str:
    """The §5 error envelope's code and message, or the bare status."""
    try:
        error = response.json().get("error") or {}
    except ValueError:
        error = {}
    code = error.get("code") if isinstance(error, dict) else None
    message = error.get("message") if isinstance(error, dict) else None
    if code:
        return f"HTTP {response.status_code} {code}: {message or ''}".rstrip(": ")
    return f"HTTP {response.status_code}"


def read_sse(lines: Iterator[str]) -> Iterator[tuple[str, Any]]:
    """``(event, data)`` per SSE block; comment lines (the ``: ping`` heartbeats) are dropped."""
    event = "message"
    data: list[str] = []
    for raw in lines:
        line = raw.rstrip("\r")
        if line.startswith(":"):
            continue
        if line == "":
            if data:
                yield event, json.loads("\n".join(data))
            event, data = "message", []
            continue
        name, _, value = line.partition(":")
        value = value.removeprefix(" ")
        if name == "event":
            event = value
        elif name == "data":
            data.append(value)
    if data:
        yield event, json.loads("\n".join(data))


@dataclass
class SmokeRun:
    """The flow over two HTTP clients: ``api`` (the deployment, base URL set) and
    ``supabase`` (GoTrue, base URL and service-role headers set). ``download`` fetches a
    signed object URL; ``audio_seconds`` is the clip length when it is known (a
    synthesised clip), which lets the ``fake`` expectation check the reported duration."""

    api: httpx.Client
    supabase: httpx.Client
    download: Download
    audio: bytes
    expect: PipelineExpectation = "real"
    timeout_seconds: float | None = None
    keep_user: bool = False
    audio_seconds: float | None = None
    email: str = field(default_factory=lambda: smoke_email(""))
    poll_interval: float = 1.0
    steps: list[Step] = field(default_factory=list)

    password: str = field(default_factory=lambda: secrets.token_urlsafe(24), repr=False)
    user_id: str | None = field(default=None, init=False)
    access_token: str | None = field(default=None, init=False, repr=False)
    job_id: str | None = field(default=None, init=False)
    job: dict[str, Any] | None = field(default=None, init=False)
    result: JobResult | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.timeout_seconds is None:
            self.timeout_seconds = TIMEOUTS[self.expect]

    # --- driver -----------------------------------------------------------------------------

    def run(self) -> list[Step]:
        """Every step in order. A failure skips the steps that depend on it; the public
        routes are still checked, and the account is still cleaned up."""
        chain: Sequence[tuple[str, Callable[[], str]]] = (
            ("health", self.check_health),
            ("create_user", self.create_user),
            ("sign_in", self.sign_in),
            ("me_fresh", self.check_fresh_account),
            ("submit_job", self.submit_job),
            ("job_finished", self.wait_for_job),
            ("result_shape", self.check_result_shape),
            ("stems_download", self.check_stems),
            ("midi_parses", self.check_midi),
            ("ledger_capture", self.check_ledger),
        )
        aborted = False
        for name, step in chain:
            if aborted:
                self.steps.append(Step(name, "SKIP", "an earlier step failed"))
                continue
            aborted = not self._step(name, step)
        self._step("status", self.check_status)
        self._step("version", self.check_version)
        self._cleanup()
        return self.steps

    def _step(self, name: str, step: Callable[[], str]) -> bool:
        try:
            detail = step()
        except StepFailed as exc:
            self.steps.append(Step(name, "FAIL", str(exc)))
            return False
        except Exception as exc:  # a transport error or a surprise in the payload
            self.steps.append(Step(name, "FAIL", describe_error(exc)))
            return False
        self.steps.append(Step(name, "PASS", detail))
        return True

    def _cleanup(self) -> None:
        if self.keep_user:
            reason = f"--keep-user: {self.email} stays ({self.user_id or 'not created'})"
            self.steps.append(Step("delete_user", "SKIP", reason))
            self.steps.append(Step("tombstone", "SKIP", "--keep-user"))
            return
        if self.user_id is None:
            self.steps.append(Step("delete_user", "SKIP", "no account was created"))
            self.steps.append(Step("tombstone", "SKIP", "no account was created"))
            return
        if not self._step("delete_user", self.delete_user):
            self.steps.append(Step("tombstone", "SKIP", "the account was not deleted"))
            return
        if self.access_token is None:
            self.steps.append(Step("tombstone", "SKIP", "no session to test with"))
            return
        self._step("tombstone", self.check_tombstone)

    # --- helpers ----------------------------------------------------------------------------

    def _auth(self) -> dict[str, str]:
        if self.access_token is None:
            raise StepFailed("not signed in")
        return {"Authorization": f"Bearer {self.access_token}"}

    @staticmethod
    def _expect(response: httpx.Response, status: int, what: str) -> Any:
        if response.status_code != status:
            raise StepFailed(f"{what}: expected HTTP {status}, got {api_error(response)}")
        try:
            return response.json()
        except ValueError as exc:
            raise StepFailed(f"{what}: the body is not JSON") from exc

    # --- steps ------------------------------------------------------------------------------

    def check_health(self) -> str:
        body = self._expect(self.api.get("/v1/health"), 200, "GET /v1/health")
        if body != {"status": "ok"}:
            raise StepFailed(f"GET /v1/health answered {body!r}")
        return 'GET /v1/health -> 200 {"status": "ok"}'

    def create_user(self) -> str:
        """``POST /auth/v1/admin/users`` with ``email_confirm``: the account can sign in at
        once and no email is sent. The insert fires ``on_auth_user_created`` (§6)."""
        response = self.supabase.post(
            "/auth/v1/admin/users",
            json={"email": self.email, "password": self.password, "email_confirm": True},
        )
        if not response.is_success:
            try:
                message = response.json().get("msg") or response.json().get("error_code")
            except ValueError:
                message = None
            raise StepFailed(f"GoTrue admin API answered HTTP {response.status_code}: {message}")
        user_id = response.json().get("id")
        if not isinstance(user_id, str) or not user_id:
            raise StepFailed("GoTrue answered without a user id")
        self.user_id = user_id
        return f"{self.email} created confirmed, user {user_id}"

    def sign_in(self) -> str:
        body = self._expect(
            self.api.post("/v1/auth/token", json={"email": self.email, "password": self.password}),
            200,
            "POST /v1/auth/token",
        )
        token = body.get("access_token")
        if not isinstance(token, str) or not token or not body.get("refresh_token"):
            raise StepFailed("the token response carries no access/refresh token")
        signed_in_as = (body.get("user") or {}).get("id")
        if signed_in_as != self.user_id:
            raise StepFailed(f"signed in as {signed_in_as}, expected {self.user_id}")
        self.access_token = token
        return f"session issued, expires_in {body.get('expires_in')}s"

    def check_fresh_account(self) -> str:
        body = self._expect(self.api.get("/v1/me", headers=self._auth()), 200, "GET /v1/me")
        user = body.get("user") or {}
        balance = body.get("balance") or {}
        expected = {"credits": FREE_CREDITS, "reserved": 0, "available": FREE_CREDITS}
        seen = {k: balance.get(k) for k in expected}
        if seen != expected:
            raise StepFailed(
                f"balance {seen} — the sign-up trigger did not grant {FREE_CREDITS} credits"
            )
        if user.get("plan") != "free":
            raise StepFailed(f"plan {user.get('plan')!r}, expected 'free'")
        if user.get("email", "").lower() != self.email.lower():
            raise StepFailed(f"profile email {user.get('email')!r} != {self.email!r}")
        missing = [k for k in ("marketing_opt_in", "referral_code") if k not in user]
        if missing:
            raise StepFailed(f"user object lacks {missing} (contract §1)")
        if not isinstance(user["marketing_opt_in"], bool):
            raise StepFailed("marketing_opt_in is not a boolean")
        return (
            f"{FREE_CREDITS} credits, plan free, marketing_opt_in={user['marketing_opt_in']}, "
            f"referral_code={user['referral_code']!r}"
        )

    def submit_job(self) -> str:
        response = self.api.post(
            "/v1/jobs",
            files={"audio": ("smoke.wav", self.audio, "audio/wav")},
            headers=self._auth(),
        )
        body = self._expect(response, 202, "POST /v1/jobs")
        balance = body.get("balance") or {}
        if body.get("status") != "queued" or body.get("credits_reserved") != 1:
            raise StepFailed(f"unexpected acceptance: {body}")
        if balance.get("reserved") != 1 or balance.get("available") != FREE_CREDITS - 1:
            raise StepFailed(f"balance after submit {balance}, expected reserved 1, available 2")
        self.job_id = str(body["job_id"])
        return f"job {self.job_id} queued, {len(self.audio) / 1024:.0f} KB uploaded, 1 reserved"

    def wait_for_job(self) -> str:
        """Follow ``/events`` (SSE) to a terminal event; poll ``GET /v1/jobs/{id}`` instead
        when the stream cannot be opened or ends early (a proxy that buffers SSE)."""
        assert self.timeout_seconds is not None
        started = time.monotonic()
        deadline = started + self.timeout_seconds
        stages: list[str] = []
        transport = "SSE"
        status: dict[str, Any] | None = None
        try:
            status = self._follow_events(deadline, stages)
        except (httpx.HTTPError, ValueError, OSError) as exc:
            self.steps.append(
                Step("events_stream", "SKIP", f"SSE unavailable: {describe_error(exc)}")
            )
        if status is None:
            transport = "polling"
            status = self._poll(deadline)
        elapsed = time.monotonic() - started
        self.job = status
        if status.get("status") != "succeeded":
            error = status.get("error") or {}
            raise StepFailed(
                f"job ended {status.get('status')} after {elapsed:.1f}s: "
                f"{error.get('code')} {error.get('message') or ''}".rstrip()
            )
        seen = " > ".join(dict.fromkeys(stages)) if stages else "no progress events"
        return f"succeeded in {elapsed:.1f}s via {transport} ({seen})"

    def _follow_events(self, deadline: float, stages: list[str]) -> dict[str, Any] | None:
        remaining = max(deadline - time.monotonic(), 1.0)
        with self.api.stream(
            "GET",
            f"/v1/jobs/{self.job_id}/events",
            headers=self._auth(),
            timeout=httpx.Timeout(10.0, read=remaining),
        ) as response:
            if response.status_code != 200:
                raise StepFailed(f"GET /v1/jobs/{{id}}/events: {api_error(response)}")
            for event, data in read_sse(response.iter_lines()):
                if event == "progress":
                    stages.append(str(data.get("stage")))
                elif event == "result":
                    return data
                elif event == "error":
                    return {"status": "failed", "error": data}
        return None

    def _poll(self, deadline: float) -> dict[str, Any]:
        while True:
            body = self._expect(
                self.api.get(f"/v1/jobs/{self.job_id}", headers=self._auth()),
                200,
                "GET /v1/jobs/{id}",
            )
            if body.get("status") not in ("queued", "running"):
                return body
            if time.monotonic() > deadline:
                raise StepFailed(
                    f"job still {body.get('status')} (stage {body.get('stage')}) after "
                    f"{self.timeout_seconds:.0f}s"
                )
            time.sleep(self.poll_interval)

    def check_result_shape(self) -> str:
        assert self.job is not None
        try:
            result = JobResult.model_validate(self.job.get("result"))
        except Exception as exc:
            raise StepFailed(f"result does not match the §2 JobResult shape: {exc}") from exc
        names = [stem.name for stem in result.stems]
        if names != STEM_NAMES:
            raise StepFailed(f"stems {names}, expected {STEM_NAMES}")
        if any(not stem.url for stem in result.stems) or not result.midi.url:
            raise StepFailed("a stem or the MIDI file has no signed URL")
        if result.credits_charged != 1 or result.balance_after != FREE_CREDITS - 1:
            raise StepFailed(
                f"credits_charged {result.credits_charged}, balance_after {result.balance_after}"
            )
        if result.expires_at <= datetime.now(UTC):
            raise StepFailed(f"expires_at {result.expires_at.isoformat()} is already past")
        notes = {track.name: len(track.notes) for track in result.midi.tracks}
        if self.expect == "fake" and self.audio_seconds is not None:
            if abs(result.input.duration_seconds - self.audio_seconds) > 0.1:
                raise StepFailed(
                    f"input.duration_seconds {result.input.duration_seconds} for a "
                    f"{self.audio_seconds}s clip"
                )
            if not notes.get("bass"):
                raise StepFailed("the fake pipeline transcribed no bass notes from the bass tone")
        self.result = result
        key = result.analysis.key
        return (
            f"4 stems, MIDI notes {notes}, {result.analysis.bpm:.1f} BPM, "
            f"{key.root} {key.mode}, expires {result.expires_at.isoformat(timespec='minutes')}"
        )

    def check_stems(self) -> str:
        assert self.result is not None
        sizes: list[str] = []
        for stem in self.result.stems:
            assert stem.url is not None
            try:
                data = self.download(stem.url)
            except Exception as exc:
                raise StepFailed(f"{stem.name}: download failed ({describe_error(exc)})") from exc
            if len(data) <= 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
                raise StepFailed(f"{stem.name}: {len(data)} bytes that are not a WAV file")
            sizes.append(f"{stem.name} {len(data) / 1024:.0f} KB")
        return "signed URLs downloadable: " + ", ".join(sizes)

    def check_midi(self) -> str:
        import mido

        assert self.result is not None and self.result.midi.url is not None
        try:
            data = self.download(self.result.midi.url)
        except Exception as exc:
            raise StepFailed(f"MIDI download failed ({describe_error(exc)})") from exc
        try:
            midi = mido.MidiFile(file=io.BytesIO(data))
        except Exception as exc:
            raise StepFailed(f"mido could not parse the file: {describe_error(exc)}") from exc
        note_ons = sum(
            1 for track in midi.tracks for m in track if m.type == "note_on" and m.velocity > 0
        )
        if not midi.tracks:
            raise StepFailed("the MIDI file has no tracks")
        return (
            f"{len(data)} bytes, {len(midi.tracks)} tracks, {note_ons} note-ons, {midi.length:.1f}s"
        )

    def check_ledger(self) -> str:
        body = self._expect(
            self.api.get("/v1/credits/ledger", params={"limit": 50}, headers=self._auth()),
            200,
            "GET /v1/credits/ledger",
        )
        entries = [e for e in body.get("entries", []) if e.get("job_id") == self.job_id]
        kinds = sorted(e["entry_type"] for e in entries)
        captures = [e for e in entries if e["entry_type"] == "capture"]
        if len(captures) != 1 or captures[0]["amount"] != -1:
            raise StepFailed(
                f"ledger rows for the job: {kinds}, expected exactly one capture of -1"
            )
        if any(e["entry_type"] in ("release", "refund") for e in entries):
            raise StepFailed(f"the job's credit came back: {kinds}")
        me = self._expect(self.api.get("/v1/me", headers=self._auth()), 200, "GET /v1/me")
        balance = {k: me["balance"].get(k) for k in ("credits", "reserved", "available")}
        expected = {"credits": FREE_CREDITS - 1, "reserved": 0, "available": FREE_CREDITS - 1}
        if balance != expected:
            raise StepFailed(f"balance after the job {balance}, expected {expected}")
        return (
            f"rows {kinds}, one capture of -1, "
            f"balance {expected['credits']}/0/{expected['available']}"
        )

    def check_status(self) -> str:
        body = self._expect(self.api.get("/v1/status"), 200, "GET /v1/status")
        try:
            status = StatusResponse.model_validate(body)
        except Exception as exc:
            raise StepFailed(f"not the §14 shape: {exc}") from exc
        parts = status.components
        return (
            f"api {parts.api}, engine {parts.engine}, payments {parts.payments}, "
            f"last_24h morphs {status.last_24h.morphs}"
        )

    def check_version(self) -> str:
        body = self._expect(self.api.get("/v1/version"), 200, "GET /v1/version")
        try:
            version = VersionResponse.model_validate(body)
        except Exception as exc:
            raise StepFailed(f"not the §14 shape: {exc}") from exc
        return (
            f"latest {version.latest}, min_supported {version.min_supported}, "
            f"{version.download_url}"
        )

    def delete_user(self) -> str:
        if self.access_token is None:
            # No session to call DELETE /v1/me with: the dashboard path, which the
            # on_auth_user_deleted trigger turns into the same tombstone (§6).
            response = self.supabase.delete(f"/auth/v1/admin/users/{self.user_id}")
            if not response.is_success and response.status_code != 404:
                raise StepFailed(f"GoTrue admin delete answered HTTP {response.status_code}")
            return f"{self.email} deleted through the GoTrue admin API (no session)"
        body = self._expect(
            self.api.request(
                "DELETE", "/v1/me", json={"confirm": self.email}, headers=self._auth()
            ),
            200,
            "DELETE /v1/me",
        )
        if body != {"status": "deleted"}:
            raise StepFailed(f"DELETE /v1/me answered {body!r}")
        return f"{self.email} deleted through DELETE /v1/me"

    def check_tombstone(self) -> str:
        response = self.api.get("/v1/me", headers=self._auth())
        if response.status_code != 401:
            raise StepFailed(f"the deleted account still answers: {api_error(response)}")
        return f"GET /v1/me with the old token -> {api_error(response)}"


# --- reporting and CLI -------------------------------------------------------------------------


def format_report(steps: Sequence[Step]) -> str:
    width = max((len(s.name) for s in steps), default=4)
    lines = [f"{'STEP':<{width}}  RESULT  DETAIL"]
    lines.extend(f"{s.name:<{width}}  {s.outcome:<6}  {s.detail}" for s in steps)
    passed = sum(1 for s in steps if s.outcome == "PASS")
    failed = sum(1 for s in steps if s.outcome == "FAIL")
    verdict = "SMOKE PASS" if failed == 0 else "SMOKE FAIL"
    skipped = len(steps) - passed - failed
    lines.append(f"{verdict}: {passed} passed, {failed} failed, {skipped} skipped")
    return "\n".join(lines)


def exit_code(steps: Sequence[Step]) -> int:
    return 0 if all(s.ok for s in steps) else 1


def load_audio(path: Path | None) -> tuple[bytes, float | None]:
    """The clip to submit and its length when known: a file as given, else the synthetic
    bass + pad + beat clip the benchmark uses."""
    if path is not None:
        return path.read_bytes(), None
    return synthetic_clip("smoke", SYNTHETIC_SECONDS).audio, SYNTHETIC_SECONDS


def fetch_object(client: httpx.Client, url: str) -> bytes:
    response = client.get(url)
    if response.status_code != 200:
        raise StepFailed(f"HTTP {response.status_code} from storage")
    return response.content


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="live_smoke", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--audio", type=Path, help="clip to submit (default: a synthetic 5 s WAV)")
    parser.add_argument(
        "--pipeline-expect",
        choices=["fake", "real"],
        default="real",
        help="fake: the CPU stub (short timeout, deterministic checks); real: a GPU worker",
    )
    parser.add_argument(
        "--timeout", type=float, help="seconds to wait for the job (default per pipeline)"
    )
    parser.add_argument(
        "--keep-user", action="store_true", help="do not delete the throwaway account"
    )
    return parser


def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    env = os.environ if env is None else env
    missing = [name for name in REQUIRED_ENV if not env.get(name)]
    if missing:
        print(f"live_smoke: set {', '.join(missing)}", file=sys.stderr)
        return 2
    api_url = env["TONAMORPH_API_URL"].rstrip("/")
    supabase_url = env["SUPABASE_URL"].rstrip("/")
    audio, audio_seconds = load_audio(args.audio)
    email = smoke_email(api_url)
    print(f"target {api_url}  auth {supabase_url}  account {email}")
    with (
        httpx.Client(base_url=api_url, timeout=httpx.Timeout(30.0)) as api,
        httpx.Client(
            base_url=supabase_url,
            headers=service_headers(env["SUPABASE_SERVICE_ROLE_KEY"]),
            timeout=httpx.Timeout(30.0),
        ) as supabase,
        httpx.Client(timeout=httpx.Timeout(60.0), follow_redirects=True) as objects,
    ):
        run = SmokeRun(
            api=api,
            supabase=supabase,
            download=lambda url: fetch_object(objects, url),
            audio=audio,
            audio_seconds=audio_seconds,
            expect=args.pipeline_expect,
            timeout_seconds=args.timeout,
            keep_user=args.keep_user,
            email=email,
        )
        steps = run.run()
    print(format_report(steps))
    return exit_code(steps)


if __name__ == "__main__":
    sys.exit(main())
