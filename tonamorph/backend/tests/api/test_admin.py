"""§15 — the founder's read-only support lookup: absent without a key, guarded by a
constant-time compare and one shared budget, audited without the address it was asked
for, and answering the overview plus the last 20 jobs and ledger entries."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings, override_settings
from app.main import create_app
from app.routers.admin import ADMIN_REQUESTS_PER_MIN
from app.services.memory import MemoryStore
from tests.api.conftest import USER_EMAIL

ADMIN_KEY = "test-admin-key-not-for-production"


@pytest.fixture
def admin_client(settings: Settings) -> Iterator[tuple[TestClient, MemoryStore]]:
    """An app with ``ADMIN_API_KEY`` set; the plain ``client`` fixture has none."""
    admin_settings = settings.model_copy(update={"admin_api_key": SecretStr(ADMIN_KEY)})
    with override_settings(admin_settings):
        app = create_app(admin_settings)
        limits = app.state.rate_limits
        limits.jobs.capacity = limits.reads.capacity = 10_000.0
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, app.state.services.memory


def app_log_text(caplog: pytest.LogCaptureFixture) -> str:
    """Everything the API's own loggers recorded (the test client's ``httpx`` line echoes
    the URL it requested and is not production logging), lower-cased."""
    return "\n".join(
        repr(record.__dict__)
        for record in caplog.records
        if record.name.startswith("tonamorph")
    ).lower()


def morph(store: MemoryStore, user: UUID) -> UUID:
    job = store.create_job(user, {}, {"input_name": "input.wav"}, None)
    store.start_job(job.id, "worker")
    store.complete_job(
        job.id,
        {
            "input": {
                "duration_seconds": 5.0,
                "sample_rate": 44100,
                "channels": 2,
                "truncated": False,
            },
            "analysis": {
                "bpm": 120.0,
                "bpm_confidence": 0.9,
                "key": {
                    "root": "F",
                    "mode": "minor",
                    "root_midi": 53,
                    "confidence": 0.8,
                    "scale_pitch_classes": [5, 7, 8, 10, 0, 1, 3],
                },
                "downbeats_seconds": [],
                "beats_seconds": [],
            },
            "stems": [
                {
                    "name": "bass",
                    "url": "memory://jobs/x/bass.wav?exp=1",
                    "sample_rate": 44100,
                    "channels": 2,
                    "duration_seconds": 5.0,
                    "peak_db": -3.0,
                    "rms_db": -18.0,
                    "transients_seconds": [],
                }
            ],
            "midi": {"url": "memory://jobs/x/score.mid?exp=1", "bpm": 120.0, "tracks": []},
        },
    )
    return job.id


def test_the_route_does_not_exist_without_a_key(client: TestClient) -> None:
    response = client.get(f"/v1/admin/users/{uuid4()}", headers={"X-Admin-Key": "anything"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_a_wrong_or_missing_key_is_401(
    admin_client: tuple[TestClient, MemoryStore], caplog: pytest.LogCaptureFixture
) -> None:
    client, _ = admin_client
    target = f"/v1/admin/users/{uuid4()}"
    with caplog.at_level(logging.WARNING, logger="tonamorph.admin"):
        assert client.get(target).status_code == 401
        assert client.get(target, headers={"X-Admin-Key": ADMIN_KEY + "x"}).status_code == 401
        assert client.get(target, headers={b"X-Admin-Key": "é".encode()}).status_code == 401
    assert all("rejected" in r.getMessage() for r in caplog.records if r.name == "tonamorph.admin")


def test_lookup_by_id_and_by_email_answers_the_overview_and_history(
    admin_client: tuple[TestClient, MemoryStore],
    mint_jwt: Callable[..., str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    client, store = admin_client
    user = uuid4()
    auth = {"Authorization": f"Bearer {mint_jwt(str(user), email=USER_EMAIL)}"}
    assert client.get("/v1/me", headers=auth).status_code == 200
    store.record_purchase(user, "paddle", "txn_a", "pack_50", 900, 800, None, {}, "paddle:txn:a")
    jobs = [morph(store, user) for _ in range(25)]
    store.record_job_feedback(jobs[0], user, "up", None, None, 900)
    store.record_job_feedback(jobs[1], user, "down", "bleed", None, None)
    store.submit_nps(user, 8, None)
    store.create_api_key(user, "ci")
    key, _ = store.create_api_key(user, "old")
    store.revoke_api_key(key.id, user)
    friend = uuid4()
    store.handle_new_user(
        friend, "friend@example.test", {"referral_code": store.user_referral_code_of(user)}
    )

    with caplog.at_level(logging.INFO, logger="tonamorph.admin"):
        response = client.get(f"/v1/admin/users/{user}", headers={"X-Admin-Key": ADMIN_KEY})
    assert response.status_code == 200, response.text
    body = response.json()
    overview = body["user"]
    assert overview["user_id"] == str(user) and overview["email"] == USER_EMAIL
    assert overview["plan"] == "credits" and overview["deleted_at"] is None
    # 3 + 50 - 25 + 1 (the thumbs-down refund)
    assert overview["balance"] == 29 and overview["reserved"] == 0
    assert overview["morphs_total"] == 25 and overview["last_morph_at"] is not None
    assert overview["purchases"] == 1 and overview["refunds"] == 0
    assert overview["api_keys"] == 1 and overview["nps_score"] == 8
    assert overview["feedback_up"] == 1 and overview["feedback_down"] == 1
    assert overview["feedback_refunds"] == 1
    assert overview["referral_code"] == store.user_referral_code_of(user)
    assert overview["referred_by"] is None and overview["friends_joined"] == 1
    assert len(body["jobs"]) == 20 and len(body["ledger"]) == 20
    assert body["jobs"][0]["job_id"] == str(jobs[-1])  # newest first
    assert all(s["url"] is None for job in body["jobs"] for s in job["result"]["stems"])
    assert all(job["result"]["midi"]["url"] is None for job in body["jobs"])
    assert body["ledger"][0]["entry_type"] == "refund"

    by_email = client.get(
        f"/v1/admin/users/{USER_EMAIL.upper()}", headers={"X-Admin-Key": ADMIN_KEY}
    )
    assert by_email.status_code == 200 and by_email.json()["user"]["user_id"] == str(user)

    audit = [r for r in caplog.records if r.getMessage() == "admin lookup"]
    assert [(r.lookup, r.outcome) for r in audit] == [("id", "ok"), ("email", "ok")]
    assert all(r.user_id == str(user) for r in audit)
    # Neither the audit line nor the access log carries the address it was asked for.
    assert USER_EMAIL not in app_log_text(caplog)
    access = [r for r in caplog.records if r.name == "tonamorph.request"]
    assert {r.path for r in access} >= {"/v1/admin/users/{subject}"}
    assert all(r.path != f"/v1/admin/users/{USER_EMAIL.upper()}" for r in access)


def test_an_unknown_subject_is_404_and_the_budget_is_shared(
    admin_client: tuple[TestClient, MemoryStore], caplog: pytest.LogCaptureFixture
) -> None:
    client, _ = admin_client
    headers = {"X-Admin-Key": ADMIN_KEY}
    with caplog.at_level(logging.INFO, logger="tonamorph.admin"):
        missing = client.get("/v1/admin/users/nobody@example.test", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["error"]["message"] == "No account matches."
    assert "nobody@example.test" not in app_log_text(caplog)
    record = next(r for r in caplog.records if r.getMessage() == "admin lookup")
    assert (record.lookup, record.outcome) == ("email", "not_found")

    statuses: list[int] = [missing.status_code]
    for _ in range(ADMIN_REQUESTS_PER_MIN):
        statuses.append(client.get(f"/v1/admin/users/{uuid4()}", headers=headers).status_code)
    assert statuses[:ADMIN_REQUESTS_PER_MIN] == [404] * ADMIN_REQUESTS_PER_MIN
    assert statuses[-1] == 429
    # A wrong key spends the same budget: guessing is throttled like use.
    assert client.get(f"/v1/admin/users/{uuid4()}", headers={"X-Admin-Key": "x"}).status_code == 429


def test_admin_key_never_appears_in_settings_repr(settings: Settings) -> None:
    admin_settings = settings.model_copy(update={"admin_api_key": SecretStr(ADMIN_KEY)})
    assert ADMIN_KEY not in repr(admin_settings)
    assert admin_settings.admin_api_key.get_secret_value() == ADMIN_KEY


def test_production_starts_without_an_admin_key(settings: Settings) -> None:
    """The lookup is optional: a deployment without it simply has no admin route."""
    base: dict[str, Any] = {
        "_env_file": None,
        "env": "production",
        "supabase_url": "https://x.supabase.co",
        "supabase_jwt_secret": "s",
        "auth_site_url": "https://tonamorph.com",
        "lemonsqueezy_webhook_secret": "w",
        "tonamorph_pipeline": "aws",
        "storage_backend": "s3",
    }
    assert Settings(**base).admin_api_key.get_secret_value() == ""
