"""§14 growth events end to end: every hook fires exactly once, with the properties the
GTM plan lists, and never on the request's critical path."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
import respx
from httpx import ASGITransport
from pydantic import SecretStr

from app.config import Settings, override_settings
from app.main import create_app
from app.pipeline.base import PipelineError
from app.schemas import JobResult
from app.services.factory import Services
from app.services.klaviyo import EVENTS_PATH, KLAVIYO_API_BASE
from app.services.memory import MemoryStore
from tests.api.conftest import USER_EMAIL, lemonsqueezy_headers, paddle_headers
from tests.api.test_webhooks import (
    PACK_VARIANT,
    PADDLE_SUB_PRICE,
    SUB_VARIANT,
    ls_order,
    paddle_event,
)

EVENTS_URL = f"{KLAVIYO_API_BASE}{EVENTS_PATH}"
PLUGIN_HEADERS = {
    "X-Plugin-Version": "0.1.0",
    "X-Host": "Ableton Live 12",
    "X-Plugin-OS": "macOS 15",
}


@pytest.fixture
def live_settings(settings: Settings) -> Settings:
    return settings.model_copy(update={"klaviyo_private_api_key": SecretStr("pk_test_secret")})


@pytest.fixture
async def live(live_settings: Settings) -> AsyncIterator[tuple[httpx.AsyncClient, Services]]:
    """The app on the test's own loop, so the background deliveries can be awaited."""
    with override_settings(live_settings):
        app = create_app(live_settings)
        services: Services = app.state.services
        services.klaviyo.retry_delay_seconds = 0.0
        limits = app.state.rate_limits
        limits.jobs.capacity = limits.reads.capacity = 10_000.0
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://api.test"
        ) as client:
            yield client, services
        await services.aclose()


@pytest.fixture
def events_route() -> respx.Route:
    return respx.post(EVENTS_URL).mock(return_value=httpx.Response(202))


def sent(route: respx.Route) -> list[dict[str, Any]]:
    """``(metric, properties, unique_id, profile)`` of every event delivered so far."""
    out = []
    for call in route.calls:
        attributes = json.loads(call.request.content)["data"]["attributes"]
        out.append(
            {
                "metric": attributes["metric"]["data"]["attributes"]["name"],
                "properties": attributes["properties"],
                "unique_id": attributes.get("unique_id"),
                "profile": attributes["profile"]["data"]["attributes"],
            }
        )
    return out


def by_metric(route: respx.Route, metric: str) -> list[dict[str, Any]]:
    return [e for e in sent(route) if e["metric"] == metric]


async def finish_job(client: httpx.AsyncClient, auth: dict[str, str], wav: bytes) -> dict[str, Any]:
    accepted = await client.post(
        "/v1/jobs", files={"audio": ("clip.wav", wav, "audio/wav")}, headers=auth
    )
    assert accepted.status_code == 202, accepted.text
    job_id = accepted.json()["job_id"]
    body: dict[str, Any] = {}

    async def done() -> bool:
        nonlocal body
        body = (await client.get(f"/v1/jobs/{job_id}", headers=auth)).json()
        return body["status"] not in ("queued", "running")

    deadline = time.monotonic() + 30
    while not await done():
        assert time.monotonic() < deadline
        await asyncio.sleep(0.05)
    return body


@respx.mock
async def test_signed_up_fires_once_on_first_sight(
    live: tuple[httpx.AsyncClient, Services],
    events_route: respx.Route,
    mint_jwt: Callable[..., str],
) -> None:
    client, services = live
    user = uuid4()
    auth = {"Authorization": f"Bearer {mint_jwt(str(user), email=USER_EMAIL)}"}
    for _ in range(3):
        assert (await client.get("/v1/me", headers=auth)).status_code == 200
    await services.klaviyo.flush()

    signed = by_metric(events_route, "Signed Up")
    assert len(signed) == 1
    event = signed[0]
    # An API-first token: this service created the profile, so the source is the plugin.
    assert event["properties"] == {
        "user_id": str(user),
        "source": "plugin",
        "referral_code": None,
        "utm_source": None,
        "utm_medium": None,
        "utm_campaign": None,
        "utm_content": None,
        "utm_term": None,
        "marketing_opt_in": False,
    }
    assert event["unique_id"] == f"signed_up:{user}"
    assert event["profile"]["external_id"] == str(user)
    assert event["profile"]["email"] == USER_EMAIL
    assert event["profile"]["properties"]["signup_source"] == "plugin"
    assert event["profile"]["properties"]["plan"] == "free"
    assert event["profile"]["properties"]["cohort_week"].startswith("20")
    assert services.memory is not None
    assert services.memory.profiles[user].first_seen_at is not None


@respx.mock
async def test_signed_up_fires_at_sign_up_with_the_form_metadata(
    live: tuple[httpx.AsyncClient, Services], events_route: respx.Route
) -> None:
    client, services = live
    store = services.memory
    assert store is not None
    affiliate = uuid4()
    store.ensure_user(affiliate, "affiliate@example.test")
    store.add_affiliate(affiliate, "FRIEND")
    store.gotrue.autoconfirm = True
    # The website signs up with metadata; the trigger copies it onto the profile.
    original = store.gotrue.signup

    def signup_with_meta(email: str, password: str, **kwargs: Any) -> dict[str, Any]:
        return original(
            email,
            password,
            data={"referral_code": "friend", "utm_source": "tiktok", "marketing_opt_in": True},
            **kwargs,
        )

    store.gotrue.signup = signup_with_meta  # type: ignore[method-assign]
    response = await client.post(
        "/v1/auth/signup", json={"email": "new@example.test", "password": "hunter22"}
    )
    assert response.status_code == 201, response.text
    user = response.json()["user"]["id"]
    token = response.json()["session"]["access_token"]
    assert (
        await client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
    ).status_code == 200
    await services.klaviyo.flush()

    signed = by_metric(events_route, "Signed Up")
    assert len(signed) == 1
    assert signed[0]["properties"]["source"] == "web"
    assert signed[0]["properties"]["referral_code"] == "FRIEND"
    assert signed[0]["properties"]["utm_source"] == "tiktok"
    assert signed[0]["properties"]["marketing_opt_in"] is True
    assert signed[0]["profile"]["external_id"] == user
    # The other sign-up-time events for that user: none.
    assert [e["metric"] for e in sent(events_route)] == ["Signed Up"]


@respx.mock
async def test_plugin_installed_fires_once_per_version_and_host(
    live: tuple[httpx.AsyncClient, Services],
    events_route: respx.Route,
    mint_jwt: Callable[..., str],
) -> None:
    client, services = live
    user = uuid4()
    auth = {"Authorization": f"Bearer {mint_jwt(str(user), email=USER_EMAIL)}"}
    assert (await client.get("/v1/me", headers=auth)).status_code == 200  # no headers: nothing
    for _ in range(2):
        assert (await client.get("/v1/me", headers={**auth, **PLUGIN_HEADERS})).status_code == 200
    upgraded = {**PLUGIN_HEADERS, "X-Plugin-Version": "0.2.0"}
    assert (await client.get("/v1/me", headers={**auth, **upgraded})).status_code == 200
    malformed = {**auth, b"X-Plugin-Version": "0.1.0é".encode(), b"X-Host": b"Live"}
    assert (await client.get("/v1/me", headers=malformed)).status_code == 200  # type: ignore[arg-type]
    await services.klaviyo.flush()

    installs = by_metric(events_route, "Plugin Installed")
    assert [e["properties"] for e in installs] == [
        {"os": "macOS 15", "daw": "Ableton Live 12", "plugin_version": "0.1.0"},
        {"os": "macOS 15", "daw": "Ableton Live 12", "plugin_version": "0.2.0"},
    ]
    assert installs[0]["unique_id"] == f"plugin_installed:{user}:0.1.0:Ableton Live 12"
    assert installs[0]["profile"]["properties"]["daw"] == "Ableton Live 12"
    store = services.memory
    assert store is not None
    row = store.plugin_installs[(user, "0.1.0", "Ableton Live 12")]
    assert row.last_seen_at >= row.first_seen_at and row.os == "macOS 15"


@respx.mock
async def test_morph_completed_carries_latency_credits_and_analysis(
    live: tuple[httpx.AsyncClient, Services],
    events_route: respx.Route,
    mint_jwt: Callable[..., str],
    make_wav: Callable[..., bytes],
) -> None:
    client, services = live
    user = uuid4()
    auth = {"Authorization": f"Bearer {mint_jwt(str(user), email=USER_EMAIL)}"}
    finished = await finish_job(client, auth, make_wav(seconds=3.0))
    assert finished["status"] == "succeeded"
    await services.klaviyo.flush()

    completed = by_metric(events_route, "Morph Completed")
    assert len(completed) == 1
    event = completed[0]
    props = event["properties"]
    assert props["job_id"] == finished["job_id"]
    assert props["credits_charged"] == 1 and props["balance_after"] == 2
    assert props["morphs_total"] == 1
    assert isinstance(props["latency_ms"], int) and props["latency_ms"] >= 0
    assert props["bpm"] == finished["result"]["analysis"]["bpm"]
    key = finished["result"]["analysis"]["key"]
    assert props["key"] == f"{key['root']} {key['mode']}"
    assert event["unique_id"] == f"morph_completed:{finished['job_id']}"
    assert event["profile"]["email"] == USER_EMAIL
    assert event["profile"]["properties"]["morphs_total"] == 1
    assert event["profile"]["properties"]["credits_available"] == 2
    assert event["profile"]["properties"]["last_morph_at"] == finished["finished_at"]
    assert not by_metric(events_route, "Credits Exhausted")

    # A replayed complete_job is idempotent in the store and deduplicated by unique_id.
    store = services.memory
    assert store is not None
    row = store.jobs[UUID(finished["job_id"])]
    await services.jobs.complete(row.id, JobResult.model_validate(row.result))
    await services.klaviyo.flush()
    replays = by_metric(events_route, "Morph Completed")
    assert len(replays) == 2 and replays[0]["unique_id"] == replays[1]["unique_id"]


@respx.mock
async def test_credits_exhausted_when_the_capture_leaves_zero(
    live: tuple[httpx.AsyncClient, Services],
    events_route: respx.Route,
    mint_jwt: Callable[..., str],
    make_wav: Callable[..., bytes],
) -> None:
    client, services = live
    store = services.memory
    assert store is not None
    store.plans["pack_50"].provider_variant_ids = {"lemonsqueezy": PACK_VARIANT}
    store.plans["sub_monthly"].provider_variant_ids = {"lemonsqueezy": SUB_VARIANT}
    user = uuid4()
    auth = {"Authorization": f"Bearer {mint_jwt(str(user), email=USER_EMAIL)}"}
    assert (await client.get("/v1/me", headers=auth)).status_code == 200
    store.adjust_credits(user, -2, "test", f"drain:{uuid4()}")
    finished = await finish_job(client, auth, make_wav(seconds=3.0))
    assert finished["status"] == "succeeded" and finished["result"]["balance_after"] == 0
    await services.klaviyo.flush()

    exhausted = by_metric(events_route, "Credits Exhausted")
    assert len(exhausted) == 1
    props = exhausted[0]["properties"]
    assert props["plan"] == "free"
    assert props["checkout_url_pack_50"].startswith("https://tonamorph.lemonsqueezy.com/")
    assert f"checkout[custom][user_id]={user}" in props["checkout_url_pack_50"]
    assert f"checkout[custom][user_id]={user}" in props["checkout_url_sub_monthly"]
    today = datetime.now(UTC).date().isoformat()
    assert exhausted[0]["unique_id"] == f"credits_exhausted:{user}:{today}"
    assert exhausted[0]["profile"]["properties"] == {"plan": "free", "credits_available": 0}


@respx.mock
async def test_credits_exhausted_when_a_reservation_is_refused(
    live: tuple[httpx.AsyncClient, Services],
    events_route: respx.Route,
    mint_jwt: Callable[..., str],
    wav_5s: bytes,
) -> None:
    client, services = live
    store = services.memory
    assert store is not None
    user = uuid4()
    auth = {"Authorization": f"Bearer {mint_jwt(str(user), email=USER_EMAIL)}"}
    assert (await client.get("/v1/me", headers=auth)).status_code == 200
    store.adjust_credits(user, -3, "test", f"drain:{uuid4()}")
    refused = await client.post(
        "/v1/jobs", files={"audio": ("clip.wav", wav_5s, "audio/wav")}, headers=auth
    )
    assert refused.status_code == 402
    await services.klaviyo.flush()
    exhausted = by_metric(events_route, "Credits Exhausted")
    assert len(exhausted) == 1 and exhausted[0]["profile"]["email"] == USER_EMAIL
    assert exhausted[0]["properties"]["plan"] == "free"


@respx.mock
async def test_morph_failed_carries_the_error_and_stage(
    live: tuple[httpx.AsyncClient, Services],
    events_route: respx.Route,
    mint_jwt: Callable[..., str],
    wav_5s: bytes,
) -> None:
    client, services = live
    user = uuid4()
    auth = {"Authorization": f"Bearer {mint_jwt(str(user), email=USER_EMAIL)}"}

    def rejecting(*_: object) -> Any:
        raise PipelineError("unsupported_media_type", "cannot decode")

    services.dispatch._run = rejecting  # type: ignore[attr-defined]
    finished = await finish_job(client, auth, wav_5s)
    assert finished["status"] == "failed"
    await services.klaviyo.flush()

    failed = by_metric(events_route, "Morph Failed")
    assert len(failed) == 1
    assert failed[0]["properties"] == {
        "job_id": finished["job_id"],
        "error_code": "unsupported_media_type",
        "stage": finished["stage"],
        "latency_ms": failed[0]["properties"]["latency_ms"],
    }
    assert failed[0]["unique_id"] == f"morph_failed:{finished['job_id']}"
    assert not by_metric(events_route, "Morph Completed")


@respx.mock
async def test_reaped_jobs_are_morph_failed_too(
    live: tuple[httpx.AsyncClient, Services],
    events_route: respx.Route,
    mint_jwt: Callable[..., str],
) -> None:
    client, services = live
    store = services.memory
    assert store is not None
    user = uuid4()
    auth = {"Authorization": f"Bearer {mint_jwt(str(user), email=USER_EMAIL)}"}
    assert (await client.get("/v1/me", headers=auth)).status_code == 200
    job = store.create_job(user, {}, {"input_name": "input.wav"}, None)
    store.start_job(job.id, "dead-worker")
    job.started_at = datetime.now(UTC) - timedelta(hours=1)
    assert await services.jobs.reap_stale(180) == 1
    await services.klaviyo.flush()
    failed = by_metric(events_route, "Morph Failed")
    assert len(failed) == 1 and failed[0]["properties"]["error_code"] == "worker_timeout"


@respx.mock
async def test_purchase_and_cancellation_events_from_webhooks(
    live: tuple[httpx.AsyncClient, Services],
    events_route: respx.Route,
    mint_jwt: Callable[..., str],
    live_settings: Settings,
) -> None:
    client, services = live
    store = services.memory
    assert store is not None
    store.plans["pack_50"].provider_variant_ids = {"lemonsqueezy": PACK_VARIANT}
    store.plans["sub_monthly"].provider_variant_ids = {
        "lemonsqueezy": SUB_VARIANT,
        "paddle": PADDLE_SUB_PRICE,
    }
    user = uuid4()
    auth = {"Authorization": f"Bearer {mint_jwt(str(user), email=USER_EMAIL)}"}
    assert (await client.get("/v1/me", headers=auth)).status_code == 200
    ls_secret = live_settings.lemonsqueezy_webhook_secret.get_secret_value()

    body = ls_order(user, ref="friend", total=900, tax=100)
    for _ in range(2):  # a replay is a duplicate: one purchase, one event
        response = await client.post(
            "/v1/webhooks/lemonsqueezy", content=body, headers=lemonsqueezy_headers(body, ls_secret)
        )
        assert response.status_code == 200
    await services.klaviyo.flush()
    purchases = by_metric(events_route, "Purchase Completed")
    assert len(purchases) == 1
    assert purchases[0]["properties"] == {
        "plan_id": "pack_50",
        "price_usd": 9.0,
        "credits": 50,
        "is_renewal": False,
        "referral_code": "friend",
    }
    assert purchases[0]["unique_id"] == "purchase_completed:lemonsqueezy:order_created:ls-order-1"
    assert purchases[0]["profile"]["properties"] == {"plan": "credits"}

    period_end = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    paddle_secret = live_settings.paddle_webhook_secret.get_secret_value()
    cancelled = paddle_event(
        user,
        event_id="evt_cancel",
        event_type="subscription.canceled",
        price_id=PADDLE_SUB_PRICE,
        status="canceled",
        period_end=period_end,
        subscription_id="sub_9",
    )
    response = await client.post(
        "/v1/webhooks/paddle", content=cancelled, headers=paddle_headers(cancelled, paddle_secret)
    )
    assert response.status_code == 200
    await services.klaviyo.flush()
    ended = by_metric(events_route, "Subscription Cancelled")
    assert len(ended) == 1
    assert ended[0]["properties"]["plan_id"] is None  # no order on a cancellation event
    assert ended[0]["properties"]["period_end"] is not None
    assert ended[0]["unique_id"] == "subscription_cancelled:paddle:subscription.canceled:evt_cancel"


@respx.mock
async def test_refund_issued_is_attributed_through_the_purchase(
    live: tuple[httpx.AsyncClient, Services],
    events_route: respx.Route,
    mint_jwt: Callable[..., str],
    live_settings: Settings,
) -> None:
    client, services = live
    store = services.memory
    assert store is not None
    store.plans["pack_50"].provider_variant_ids = {"paddle": "pri_pack"}
    user = uuid4()
    auth = {"Authorization": f"Bearer {mint_jwt(str(user), email=USER_EMAIL)}"}
    assert (await client.get("/v1/me", headers=auth)).status_code == 200
    secret = live_settings.paddle_webhook_secret.get_secret_value()
    sale = paddle_event(user, event_id="evt_txn", price_id="pri_pack")
    assert (
        await client.post("/v1/webhooks/paddle", content=sale, headers=paddle_headers(sale, secret))
    ).status_code == 200

    def adjustment(event_id: str, status: str) -> bytes:
        return json.dumps(
            {
                "event_id": event_id,
                "event_type": "adjustment.updated",
                "data": {
                    "id": "adj_1",
                    "action": "refund",
                    "status": status,
                    "reason": "requested_by_customer",
                    "transaction_id": "txn_1",
                    "totals": {"total": "900"},
                },
            }
        ).encode()

    pending = adjustment("evt_adj_pending", "pending_approval")
    approved = adjustment("evt_adj_approved", "approved")
    for body in (pending, approved, approved):
        response = await client.post(
            "/v1/webhooks/paddle", content=body, headers=paddle_headers(body, secret)
        )
        assert response.status_code == 200, response.text
    await services.klaviyo.flush()

    refunds = by_metric(events_route, "Refund Issued")
    assert len(refunds) == 1
    assert refunds[0]["properties"] == {"amount_usd": 9.0, "reason": "requested_by_customer"}
    assert refunds[0]["unique_id"] == "refund_issued:paddle:adjustment:adj_1"
    assert refunds[0]["profile"]["external_id"] == str(user)
    assert refunds[0]["profile"]["email"] == USER_EMAIL
    # The money moved at the provider; the credits did not move here.
    assert store.get_balance(user).credits == 53


@respx.mock
async def test_nps_submitted(
    live: tuple[httpx.AsyncClient, Services],
    events_route: respx.Route,
    mint_jwt: Callable[..., str],
) -> None:
    client, services = live
    user = uuid4()
    auth = {"Authorization": f"Bearer {mint_jwt(str(user), email=USER_EMAIL)}"}
    response = await client.post(
        "/v1/nps", json={"score": 9, "comment": "  love it  "}, headers=auth
    )
    assert response.status_code == 201, response.text
    await services.klaviyo.flush()
    nps = by_metric(events_route, "NPS Submitted")
    assert len(nps) == 1
    assert nps[0]["properties"] == {"score": 9, "comment": "love it"}
    assert nps[0]["unique_id"] == f"nps_submitted:{response.json()['id']}"
    assert nps[0]["profile"]["properties"] == {"nps_score": 9}


@respx.mock
async def test_a_klaviyo_outage_never_reaches_the_caller(
    live: tuple[httpx.AsyncClient, Services],
    mint_jwt: Callable[..., str],
    make_wav: Callable[..., bytes],
) -> None:
    client, services = live
    respx.post(EVENTS_URL).mock(side_effect=httpx.ConnectError("klaviyo down"))
    user = uuid4()
    auth = {"Authorization": f"Bearer {mint_jwt(str(user), email=USER_EMAIL)}"}
    assert (await client.get("/v1/me", headers={**auth, **PLUGIN_HEADERS})).status_code == 200
    finished = await finish_job(client, auth, make_wav(seconds=3.0))
    assert finished["status"] == "succeeded"
    assert (await client.post("/v1/nps", json={"score": 3}, headers=auth)).status_code == 201
    await services.klaviyo.flush()
    assert services.klaviyo.pending == 0


def test_disabled_emitter_costs_nothing(store: MemoryStore, services: Services) -> None:
    """The default test settings carry no key: hooks return before building anything."""
    assert not services.growth.enabled and not services.klaviyo.enabled
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    services.growth.credits_refused(user, "a@b.c")
    services.growth.nps_submitted(user, "a@b.c", score=1, comment=None, response_id=uuid4())
    assert services.klaviyo.pending == 0
