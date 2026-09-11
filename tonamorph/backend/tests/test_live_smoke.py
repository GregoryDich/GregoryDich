"""``scripts/live_smoke.py`` against the in-process app: the same flow the founder runs
against a live deployment, with the memory backend behind the API and a mock transport
standing in for GoTrue's admin API."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.services.factory import Services
from app.services.memory import MemoryStore, tombstone_email
from scripts import live_smoke
from scripts.live_smoke import SmokeRun, Step, format_report, smoke_email

SERVICE_ROLE_KEY = "service-role-test"  # the ``settings`` fixture's key


@pytest.fixture
def services(app: FastAPI) -> Services:
    return app.state.services


@pytest.fixture
def store(services: Services) -> MemoryStore:
    assert services.memory is not None
    return services.memory


@pytest.fixture
def gotrue_handler(store: MemoryStore) -> Callable[[httpx.Request], httpx.Response]:
    """GoTrue's admin API over :class:`MemoryGoTrue`: ``POST /auth/v1/admin/users``
    creates the account confirmed at once and runs the sign-up trigger, as on Supabase.
    The service-role headers are required exactly as GoTrue requires them."""

    def handler(request: httpx.Request) -> httpx.Response:
        if (
            request.headers.get("apikey") != SERVICE_ROLE_KEY
            or request.headers.get("authorization") != f"Bearer {SERVICE_ROLE_KEY}"
        ):
            return httpx.Response(401, json={"msg": "Invalid authentication credentials"})
        if request.method == "POST" and request.url.path == "/auth/v1/admin/users":
            body = json.loads(request.content)
            assert body["email_confirm"] is True
            record = store.gotrue.signup(body["email"], body["password"], redirect_to="")
            store.gotrue.confirm(body["email"])
            return httpx.Response(200, json=record)
        if request.method == "DELETE" and request.url.path.startswith("/auth/v1/admin/users/"):
            store.gotrue.admin_delete_user(UUID(request.url.path.rsplit("/", 1)[1]))
            return httpx.Response(200, json={})
        return httpx.Response(404, json={"msg": "not found"})

    return handler


@pytest.fixture
def gotrue_admin(
    gotrue_handler: Callable[[httpx.Request], httpx.Response], settings: Settings
) -> Iterator[httpx.Client]:
    with httpx.Client(
        transport=httpx.MockTransport(gotrue_handler),
        base_url=settings.supabase_url,
        headers=live_smoke.service_headers(SERVICE_ROLE_KEY),
    ) as supabase:
        yield supabase


@pytest.fixture
def download(services: Services) -> Callable[[str], bytes]:
    """Resolves the memory backend's ``memory://<path>?exp=`` signed URLs."""

    def _download(url: str) -> bytes:
        assert url.startswith("memory://"), url
        path = url.removeprefix("memory://").split("?", 1)[0]
        return services.storage.objects[path][0]  # type: ignore[attr-defined]

    return _download


@pytest.fixture
def smoke(
    client: TestClient,
    gotrue_admin: httpx.Client,
    download: Callable[[str], bytes],
    wav_5s: bytes,
) -> SmokeRun:
    return SmokeRun(
        api=client,
        supabase=gotrue_admin,
        download=download,
        audio=wav_5s,
        audio_seconds=5.0,
        expect="fake",
        email=smoke_email(str(client.base_url)),
        poll_interval=0.05,
    )


def outcomes(steps: list[Step]) -> dict[str, str]:
    return {s.name: s.outcome for s in steps}


def test_the_whole_flow_passes_and_leaves_a_tombstone(
    smoke: SmokeRun, store: MemoryStore, services: Services
) -> None:
    steps = smoke.run()
    report = format_report(steps)
    assert outcomes(steps) == {
        "health": "PASS",
        "create_user": "PASS",
        "sign_in": "PASS",
        "me_fresh": "PASS",
        "submit_job": "PASS",
        "job_finished": "PASS",
        "result_shape": "PASS",
        "stems_download": "PASS",
        "midi_parses": "PASS",
        "ledger_capture": "PASS",
        "status": "PASS",
        "version": "PASS",
        "delete_user": "PASS",
        "tombstone": "PASS",
    }, report
    assert live_smoke.exit_code(steps) == 0
    assert "via SSE" in next(s.detail for s in steps if s.name == "job_finished")
    assert smoke.email.startswith("smoke+") and smoke.email.endswith("@example.com")

    user = UUID(smoke.user_id or "")
    assert user not in store.gotrue.users
    profile = store.profiles[user]
    assert profile.deleted_at is not None and profile.email == tombstone_email(user)
    assert not any(
        path.startswith(f"jobs/{user}/")
        for path in services.storage.objects  # type: ignore[attr-defined]
    )
    captures = [r for r in store.ledger if r.user_id == user and r.entry_type == "capture"]
    assert len(captures) == 1 and captures[0].amount == -1

    assert smoke.access_token and smoke.access_token not in report
    assert smoke.password not in report and SERVICE_ROLE_KEY not in report
    assert "memory://" not in report  # object URLs are access tokens too
    assert report.endswith("SMOKE PASS: 14 passed, 0 failed, 0 skipped")


def test_keep_user_leaves_the_account_behind(smoke: SmokeRun, store: MemoryStore) -> None:
    smoke.keep_user = True
    steps = smoke.run()
    assert outcomes(steps)["delete_user"] == "SKIP" and outcomes(steps)["tombstone"] == "SKIP"
    assert live_smoke.exit_code(steps) == 0
    user = UUID(smoke.user_id or "")
    assert user in store.gotrue.users and store.profiles[user].deleted_at is None
    assert store.get_balance(user).credits == 2


def test_falls_back_to_polling_when_the_event_stream_is_unavailable(
    smoke: SmokeRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_stream(*args: object, **kwargs: object) -> object:
        raise httpx.ReadError("proxy closed the stream")

    monkeypatch.setattr(smoke.api, "stream", no_stream)
    steps = smoke.run()
    assert outcomes(steps)["events_stream"] == "SKIP"
    assert outcomes(steps)["job_finished"] == "PASS"
    assert "via polling" in next(s.detail for s in steps if s.name == "job_finished")
    assert live_smoke.exit_code(steps) == 0


def test_a_failed_step_skips_its_dependants_but_not_the_public_routes(
    smoke: SmokeRun, settings: Settings
) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"msg": "database error creating user"})

    with httpx.Client(
        transport=httpx.MockTransport(refuse), base_url=settings.supabase_url
    ) as broken:
        smoke.supabase = broken
        steps = smoke.run()
    seen = outcomes(steps)
    assert seen["health"] == "PASS" and seen["create_user"] == "FAIL"
    assert {seen[n] for n in ("sign_in", "me_fresh", "submit_job", "ledger_capture")} == {"SKIP"}
    assert seen["status"] == "PASS" and seen["version"] == "PASS"
    assert seen["delete_user"] == "SKIP" and seen["tombstone"] == "SKIP"
    assert live_smoke.exit_code(steps) == 1
    detail = next(s.detail for s in steps if s.name == "create_user")
    assert "HTTP 500" in detail and "database error creating user" in detail


def test_a_wrong_service_role_key_fails_before_anything_is_created(
    smoke: SmokeRun,
    store: MemoryStore,
    settings: Settings,
    gotrue_handler: Callable[[httpx.Request], httpx.Response],
) -> None:
    with httpx.Client(
        transport=httpx.MockTransport(gotrue_handler),
        base_url=settings.supabase_url,
        headers=live_smoke.service_headers("not-the-key"),
    ) as wrong:
        smoke.supabase = wrong
        steps = smoke.run()
    assert outcomes(steps)["create_user"] == "FAIL"
    assert "HTTP 401" in next(s.detail for s in steps if s.name == "create_user")
    assert not store.gotrue.users
    assert "not-the-key" not in format_report(steps)


def test_smoke_email_uses_the_deployment_domain() -> None:
    at = datetime(2026, 9, 11, 12, 30, 45, tzinfo=UTC)
    assert smoke_email("https://api.tonamorph.com", at) == "smoke+20260911123045@tonamorph.com"
    assert smoke_email("https://tonamorph.com/", at) == "smoke+20260911123045@tonamorph.com"
    assert smoke_email("http://localhost:8000", at) == "smoke+20260911123045@example.com"
    assert smoke_email("http://10.0.0.5:8080", at) == "smoke+20260911123045@example.com"
    assert smoke_email("http://testserver", at) == "smoke+20260911123045@example.com"


def test_main_refuses_to_start_without_the_three_variables(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = live_smoke.main([], env={"TONAMORPH_API_URL": "https://api.example.com"})
    assert code == 2
    err = capsys.readouterr().err
    assert "SUPABASE_URL" in err and "SUPABASE_SERVICE_ROLE_KEY" in err


def test_error_descriptions_never_carry_a_query_string_or_bearer_token() -> None:
    exc = httpx.ConnectError("failed for https://x.supabase.co/storage/v1/sign/a.wav?token=abc.def")
    text = live_smoke.describe_error(exc)
    assert "token=abc" not in text and text.startswith("ConnectError:")
    assert "Bearer …" in live_smoke.describe_error(ValueError("header Bearer eyJhbGci.x.y bad"))
