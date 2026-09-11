"""§1, §3 user referrals — "send a morph to a friend": every account owns a code, a friend
who signs up with it is linked and gets 3 + 2 credits, and the referrer earns 3 exactly
once, when the friend's first morph succeeds, at most ten friends per 30 days."""

from __future__ import annotations

import re
import time
from datetime import timedelta
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.services.memory import MemoryStore
from app.services.rewards import (
    REFERRAL_CODE_ALPHABET,
    REFERRAL_REWARD_CAP_PER_30_DAYS,
    referral_bonus_key,
    referral_reward_key,
)

pytestmark = pytest.mark.usefixtures("no_rate_limits")

CODE = re.compile(f"^[{REFERRAL_CODE_ALPHABET}]{{8}}$")


def sign_up(store: MemoryStore, email: str, data: dict[str, Any]) -> tuple[UUID, dict[str, str]]:
    """The website's supabase-js sign-up with ``options.data``; auto-confirmed."""
    store.gotrue.autoconfirm = True
    session = store.gotrue.signup(email, "secret-pw", redirect_to="x", data=data)
    return UUID(session["user"]["id"]), {"Authorization": f"Bearer {session['access_token']}"}


def morph(store: MemoryStore, user: UUID) -> UUID:
    job = store.create_job(user, {}, {"input_name": "input.wav"}, None)
    store.start_job(job.id, "worker")
    store.complete_job(job.id, {})
    return job.id


def test_me_carries_the_referral_code_and_its_url(
    client: TestClient, auth: dict[str, str], settings: Settings
) -> None:
    me = client.get("/v1/me", headers=auth).json()
    referral = me["referral"]
    assert CODE.match(referral["code"]), referral["code"]
    assert referral["url"] == f"{settings.auth_site_url}/m/{referral['code']}"
    assert referral["friends_joined"] == 0 and referral["morphs_earned"] == 0
    assert set(referral) == {"code", "url", "friends_joined", "morphs_earned"}
    # The code is the account's for good.
    assert client.get("/v1/me", headers=auth).json()["referral"]["code"] == referral["code"]


def test_a_friend_who_signs_up_with_the_code_is_linked_and_gets_the_bonus(
    client: TestClient, auth: dict[str, str], store: MemoryStore, registered_user: UUID
) -> None:
    code = client.get("/v1/me", headers=auth).json()["referral"]["code"]
    friend, friend_auth = sign_up(
        store, "friend@example.test", {"referral_code": f"  {code.lower()} "}
    )
    me = client.get("/v1/me", headers=friend_auth).json()
    assert me["balance"]["credits"] == 5  # 3 welcome + 2 for coming through a friend
    assert me["user"]["referral_code"] is None  # not an affiliate code
    assert store.profiles[friend].referred_by == registered_user
    bonus = store._ledger_keys[referral_bonus_key(friend)]
    assert bonus.amount == 2 and bonus.source == "referral_bonus"

    referrer = client.get("/v1/me", headers=auth).json()
    assert referrer["balance"]["credits"] == 3  # nothing at sign-up: anti-farming
    assert referrer["referral"] == {
        "code": code,
        "url": referrer["referral"]["url"],
        "friends_joined": 1,
        "morphs_earned": 0,
    }


def test_an_affiliate_code_still_wins_and_unknown_or_own_codes_are_ignored(
    client: TestClient, auth: dict[str, str], store: MemoryStore, registered_user: UUID
) -> None:
    store.add_affiliate(registered_user, "GREG30")
    affiliated, affiliated_auth = sign_up(store, "a@example.test", {"referral_code": "greg30"})
    me = client.get("/v1/me", headers=affiliated_auth).json()
    assert me["user"]["referral_code"] == "GREG30" and me["balance"]["credits"] == 3
    assert store.profiles[affiliated].referred_by is None

    unknown, unknown_auth = sign_up(store, "u@example.test", {"referral_code": "ZZZZZZZZ"})
    assert client.get("/v1/me", headers=unknown_auth).json()["balance"]["credits"] == 3
    assert store.profiles[unknown].referred_by is None
    assert client.get("/v1/me", headers=auth).json()["referral"]["friends_joined"] == 0

    # A generated code never spells an affiliate code, in any case.
    assert all(code.lower() not in store.referral_codes for code in store.user_referral_codes)


def test_the_referrer_is_rewarded_once_when_the_friends_first_morph_succeeds(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    registered_user: UUID,
    wav_5s: bytes,
) -> None:
    code = client.get("/v1/me", headers=auth).json()["referral"]["code"]
    friend, friend_auth = sign_up(store, "friend@example.test", {"referral_code": code})

    accepted = client.post(
        "/v1/jobs", files={"audio": ("clip.wav", wav_5s, "audio/wav")}, headers=friend_auth
    )
    assert accepted.status_code == 202, accepted.text
    job_id = accepted.json()["job_id"]
    deadline = time.monotonic() + 30
    body = client.get(f"/v1/jobs/{job_id}", headers=friend_auth).json()
    while body["status"] in ("queued", "running"):
        assert time.monotonic() < deadline, body
        time.sleep(0.05)
        body = client.get(f"/v1/jobs/{job_id}", headers=friend_auth).json()
    assert body["status"] == "succeeded"

    referrer = client.get("/v1/me", headers=auth).json()
    assert referrer["balance"]["credits"] == 6
    assert referrer["referral"]["morphs_earned"] == 3
    reward = store._ledger_keys[referral_reward_key(friend)]
    assert reward.user_id == registered_user and reward.amount == 3
    assert reward.source == "referral" and reward.note == "A friend's first morph"

    # A second morph, and a replay of the first completion, earn nothing more.
    morph(store, friend)
    row = store.jobs[UUID(job_id)]
    store.complete_job(row.id, row.result)
    assert client.get("/v1/me", headers=auth).json()["balance"]["credits"] == 6
    assert sum(1 for r in store.ledger if r.source == "referral") == 1


def test_a_failed_first_morph_earns_nothing_until_one_succeeds(
    store: MemoryStore, registered_user: UUID
) -> None:
    code = store.user_referral_code_of(registered_user)
    assert code is not None
    friend, _ = sign_up(store, "friend@example.test", {"referral_code": code})
    failed = store.create_job(friend, {}, {}, None)
    store.fail_job(failed.id, {"code": "worker_timeout", "message": "late"})
    assert store.get_balance(registered_user).credits == 3
    morph(store, friend)
    assert store.get_balance(registered_user).credits == 6


def test_rewards_are_capped_at_ten_friends_per_thirty_days(
    store: MemoryStore, registered_user: UUID
) -> None:
    code = store.user_referral_code_of(registered_user)
    assert code is not None
    first: UUID | None = None
    for i in range(REFERRAL_REWARD_CAP_PER_30_DAYS + 1):
        friend, _ = sign_up(store, f"friend{i}@example.test", {"referral_code": code})
        first = first or friend
        morph(store, friend)
    assert store.get_balance(registered_user).credits == 3 + 3 * REFERRAL_REWARD_CAP_PER_30_DAYS
    summary = store.user_referral_summary(registered_user)
    assert summary is not None and summary.friends_joined == 11 and summary.morphs_earned == 30

    # Once the window has moved on, the next friend is rewarded again.
    assert first is not None
    store._ledger_keys[referral_reward_key(first)].created_at -= timedelta(days=31)
    late, _ = sign_up(store, "late@example.test", {"referral_code": code})
    morph(store, late)
    assert store.get_balance(registered_user).credits == 36


def test_a_deleted_referrer_earns_nothing_and_their_code_stops_working(
    store: MemoryStore, registered_user: UUID
) -> None:
    code = store.user_referral_code_of(registered_user)
    assert code is not None
    friend, _ = sign_up(store, "friend@example.test", {"referral_code": code})
    store.delete_user_account(registered_user)
    morph(store, friend)
    assert referral_reward_key(friend) not in store._ledger_keys
    orphan, _ = sign_up(store, "orphan@example.test", {"referral_code": code})
    assert store.profiles[orphan].referred_by is None
    assert store.get_balance(orphan).credits == 3
