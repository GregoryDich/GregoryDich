"""The PostgREST services must call the exact SQL functions from db/migrations (§6)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
import respx

from app.config import Settings
from app.schemas import JobOptions
from app.services.api_keys import SupabaseApiKeysService
from app.services.credits import SupabaseCreditsService
from app.services.events import JobEventBus
from app.services.jobs import SERVER_IDEMPOTENCY_PREFIX, SupabaseJobsService
from app.services.plans import SupabasePlansService, build_checkout_url
from app.services.supabase import SupabaseClient
from app.services.users import SupabaseUsersService
from app.services.webhooks import SupabasePurchasesService, SupabaseWebhookEventsService

BASE = "http://supabase.test"
BALANCE = {"credits": 3, "reserved": 1, "available": 2}


@pytest.fixture
def supabase(settings: Settings) -> SupabaseClient:
    return SupabaseClient(settings, backoff_seconds=0.0)


def rpc(name: str, payload: Any) -> respx.Route:
    return respx.post(f"{BASE}/rest/v1/rpc/{name}").mock(
        return_value=httpx.Response(200, json=payload)
    )


def sent(route: respx.Route) -> dict[str, Any]:
    return json.loads(route.calls.last.request.content)


@respx.mock
async def test_credit_rpc_names_and_parameters(supabase: SupabaseClient) -> None:
    credits = SupabaseCreditsService(supabase)
    user, job = uuid4(), uuid4()

    balance_route = rpc("get_balance", BALANCE)
    respx.get(f"{BASE}/rest/v1/subscriptions").mock(
        return_value=httpx.Response(200, json=[{"current_period_end": "2026-10-01T00:00:00Z"}])
    )
    balance = await credits.get_balance(user)
    assert balance.available == 2 and balance.subscription_renews_at is not None
    assert sent(balance_route) == {"p_user_id": str(user)}

    reserve = rpc("reserve_credits", BALANCE)
    await credits.reserve(user, job, 1)
    assert sent(reserve) == {"p_user_id": str(user), "p_job_id": str(job), "p_amount": 1}

    settle = rpc("settle_reservation", BALANCE)
    await credits.settle(job, True)
    assert sent(settle) == {"p_job_id": str(job), "p_success": True}

    grant = rpc("grant_credits", BALANCE)
    expires = datetime(2026, 10, 1, tzinfo=UTC)
    await credits.grant(user, 60, "paddle:order:1", "paddle:txn:1", "Pro Monthly", expires)
    assert sent(grant) == {
        "p_user_id": str(user),
        "p_amount": 60,
        "p_source": "paddle:order:1",
        "p_idempotency_key": "paddle:txn:1",
        "p_note": "Pro Monthly",
        "p_expires_at": expires.isoformat(),
    }

    refund = rpc("refund_job", BALANCE)
    await credits.refund_job(job, "support")
    assert sent(refund) == {"p_job_id": str(job), "p_reason": "support"}
    await supabase.aclose()


@respx.mock
async def test_ledger_paging_uses_seq(supabase: SupabaseClient) -> None:
    user = uuid4()
    rows = [
        {
            "id": str(uuid4()),
            "seq": seq,
            "created_at": "2026-09-01T00:00:00Z",
            "entry_type": "grant",
            "amount": 1,
            "balance_after": seq,
            "reserved_after": 0,
            "job_id": None,
            "source": "test",
            "note": None,
        }
        for seq in (5, 4, 3)
    ]
    route = respx.get(f"{BASE}/rest/v1/credit_ledger").mock(
        return_value=httpx.Response(200, json=rows)
    )
    page = await SupabaseCreditsService(supabase).ledger(user, limit=2, cursor="9")
    assert [entry.balance_after for entry in page.entries] == [5, 4]
    assert page.next_cursor == "4"
    params = route.calls.last.request.url.params
    assert params["user_id"] == f"eq.{user}" and params["seq"] == "lt.9"
    assert params["order"] == "seq.desc" and params["limit"] == "3"
    await supabase.aclose()


@respx.mock
async def test_job_rpcs(supabase: SupabaseClient) -> None:
    jobs = SupabaseJobsService(supabase, JobEventBus())
    user, job = uuid4(), uuid4()
    row = {
        "id": str(job),
        "user_id": str(user),
        "status": "queued",
        "stage": "upload",
        "progress": 0.0,
        "created_at": "2026-09-01T00:00:00Z",
    }
    create = rpc("create_job", row)
    options = JobOptions(idempotency_key="client-key")
    status = await jobs.create(user, options, "input.flac", 1)
    assert str(status.job_id) == str(job) and status.status == "queued"
    body = sent(create)
    assert body["p_user_id"] == str(user) and body["p_idempotency_key"] == "client-key"
    assert body["p_input_meta"] == {"input_name": "input.flac"}
    assert body["p_options"]["stems"] == ["bass", "drums", "other", "vocals"]

    start = rpc("start_job", {**row, "status": "running"})
    progress = rpc("update_job_progress", {**row, "status": "running", "progress": 0.4})
    await jobs.set_progress(job, "separate", 0.4)
    assert sent(start) == {"p_job_id": str(job), "p_worker_ref": None}
    assert sent(progress) == {"p_job_id": str(job), "p_stage": "separate", "p_progress": 0.4}

    fail = rpc("fail_job", {**row, "status": "failed", "error": {"code": "x", "message": "y"}})
    await jobs.fail(job, "x", "y")
    assert sent(fail) == {"p_job_id": str(job), "p_error": {"code": "x", "message": "y"}}

    cancel = rpc("cancel_job", {**row, "status": "cancelled"})
    await jobs.cancel(job, user)
    assert sent(cancel) == {"p_job_id": str(job), "p_user_id": str(user)}

    reap = rpc("reap_stale_jobs", 2)
    assert await jobs.reap_stale(180) == 2
    assert sent(reap) == {"p_timeout_seconds": 180}
    await supabase.aclose()


@respx.mock
async def test_api_key_rpcs(supabase: SupabaseClient) -> None:
    keys = SupabaseApiKeysService(supabase)
    user, key_id = uuid4(), uuid4()
    plaintext = "tm_live_" + "a1" * 16
    create = rpc(
        "create_api_key", [{"id": str(key_id), "prefix": plaintext[:12], "plaintext": plaintext}]
    )
    created = await keys.create(user, "ci")
    assert created.key == plaintext and created.prefix == plaintext[:12]
    assert sent(create) == {"p_user_id": str(user), "p_name": "ci"}

    resolve = rpc("authenticate_api_key", str(user))
    assert await keys.resolve(plaintext) == user
    from app.auth.api_keys import hash_api_key

    assert sent(resolve) == {"p_key_hash": hash_api_key(plaintext)}
    assert await keys.resolve("not-a-key") is None

    revoke = rpc("revoke_api_key", True)
    assert await keys.revoke(user, key_id) is True
    assert sent(revoke) == {"p_key_id": str(key_id), "p_user_id": str(user)}
    await supabase.aclose()


@respx.mock
async def test_record_purchase_rpc(supabase: SupabaseClient) -> None:
    purchases = SupabasePurchasesService(supabase)
    user = uuid4()
    route = rpc(
        "record_purchase",
        {
            "id": str(uuid4()),
            "user_id": str(user),
            "provider": "lemonsqueezy",
            "provider_order_id": "order-1",
            "plan_id": "pack_50",
            "credits": 50,
            "amount_cents": 900,
            "net_cents": 800,
            "currency": "USD",
            "referral_code": "friend",
            "idempotency_key": "lemonsqueezy:order_created:1",
            "created_at": "2026-09-01T00:00:00Z",
        },
    )
    purchase = await purchases.record_purchase(
        user_id=user,
        provider="lemonsqueezy",
        provider_order_id="order-1",
        plan_id="pack_50",
        amount_cents=900,
        net_cents=800,
        referral_code="friend",
        raw={"meta": {}},
        idempotency_key="lemonsqueezy:order_created:1",
    )
    assert purchase.credits == 50
    assert set(sent(route)) == {
        "p_user_id",
        "p_provider",
        "p_provider_order_id",
        "p_plan_id",
        "p_amount_cents",
        "p_net_cents",
        "p_referral_code",
        "p_raw",
        "p_idempotency_key",
    }
    await supabase.aclose()


@respx.mock
async def test_webhook_claim_is_one_locking_rpc_carrying_the_lease(
    supabase: SupabaseClient, settings: Settings
) -> None:
    """The claim is ``claim_webhook_event`` and nothing else: the decision (duplicate,
    failed-and-retryable, or a stale claim past its lease) is taken in SQL under the row
    lock, so two workers cannot both reclaim the same stranded event (§4)."""
    events = SupabaseWebhookEventsService(supabase, settings.webhook_claim_lease_seconds)
    route = respx.post(f"{BASE}/rest/v1/rpc/claim_webhook_event").mock(
        side_effect=[httpx.Response(200, json=True), httpx.Response(200, json=False)]
    )
    assert await events.claim("k", "paddle", "transaction.completed", {"event_id": "e"}) is True
    assert sent(route) == {
        "p_idempotency_key": "k",
        "p_provider": "paddle",
        "p_event_name": "transaction.completed",
        "p_payload": {"event_id": "e"},
        "p_lease_seconds": settings.webhook_claim_lease_seconds,
    }
    assert await events.claim("k", "paddle", "transaction.completed", {"event_id": "e"}) is False
    await supabase.aclose()


@respx.mock
async def test_subscription_upsert_never_clears_a_stored_referral_code(
    supabase: SupabaseClient,
) -> None:
    """An event without a ``ref`` must leave the code the checkout stored alone: PostgREST
    builds the upsert's column list from the payload keys, so the column is omitted (§12)."""
    purchases = SupabasePurchasesService(supabase)
    user = uuid4()
    row = {
        "id": str(uuid4()),
        "user_id": str(user),
        "provider": "lemonsqueezy",
        "provider_subscription_id": "ls-sub-1",
        "plan_id": "sub_monthly",
        "status": "active",
        "referral_code": "friend",
    }
    route = respx.post(f"{BASE}/rest/v1/subscriptions").mock(
        return_value=httpx.Response(201, json=[row])
    )
    kwargs: dict[str, Any] = {
        "user_id": user,
        "provider": "lemonsqueezy",
        "provider_subscription_id": "ls-sub-1",
        "plan_id": "sub_monthly",
        "status": "active",
        "current_period_end": None,
        "cancelled_at": None,
        "raw": {},
    }
    subscription = await purchases.upsert_subscription(referral_code="friend", **kwargs)
    assert subscription.referral_code == "friend"
    assert sent(route)["referral_code"] == "friend"

    await purchases.upsert_subscription(referral_code=None, **kwargs)
    assert "referral_code" not in sent(route)
    assert route.calls.last.request.url.params["on_conflict"] == "provider_subscription_id"
    await supabase.aclose()


@respx.mock
async def test_users_ensure_grants_signup_credits_once(
    supabase: SupabaseClient, settings: Settings
) -> None:
    users = SupabaseUsersService(supabase, settings)
    user = uuid4()
    profile = {"id": str(user), "email": "a@b.c", "plan": "free"}
    respx.get(f"{BASE}/rest/v1/profiles").mock(
        side_effect=[httpx.Response(200, json=[]), httpx.Response(200, json=[profile])]
    )
    respx.post(f"{BASE}/rest/v1/profiles").mock(return_value=httpx.Response(201, json=[profile]))
    respx.post(f"{BASE}/rest/v1/credit_accounts").mock(return_value=httpx.Response(201, json=[]))
    grant = rpc("grant_credits", BALANCE)
    created = await users.ensure(user, "A@B.c")
    assert created.email == "a@b.c" and created.plan == "free"
    assert sent(grant)["p_idempotency_key"] == f"signup:{user}"
    assert sent(grant)["p_amount"] == settings.free_signup_credits
    await supabase.aclose()


@respx.mock
async def test_plans_are_read_from_the_table(supabase: SupabaseClient) -> None:
    plans = SupabasePlansService(supabase)
    respx.get(f"{BASE}/rest/v1/plans").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": "pack_50",
                    "name": "50 Credits",
                    "credits": 50,
                    "price_cents": 900,
                    "currency": "USD",
                    "interval": None,
                    "provider_variant_ids": {"lemonsqueezy": "v1"},
                    "checkout_url_template": (
                        "https://shop.test/buy/{variant_id}?u={user_id}&ref={ref}"
                    ),
                    "active": True,
                    "sort_order": 1,
                }
            ],
        )
    )
    plan = await plans.find_by_variant("lemonsqueezy", "v1")
    assert plan is not None and plan.credits == 50
    user = uuid4()
    expected = f"https://shop.test/buy/v1?u={user}&ref=friend"
    assert build_checkout_url(plan, user, "friend") == expected
    assert build_checkout_url(plan, None, None) == "https://shop.test/buy/v1"
    await supabase.aclose()


@respx.mock
async def test_create_job_survives_a_retry_without_reserving_twice(
    supabase: SupabaseClient,
) -> None:
    """M1: a 502 on the way out used to make the client POST ``create_job`` again, so
    two jobs were inserted and two credits reserved while only the second was ever
    dispatched — the first stayed ``queued`` holding a credit for good."""
    jobs = SupabaseJobsService(supabase, JobEventBus())
    user = uuid4()
    inserted: dict[str, dict[str, Any]] = {}
    attempts = 0

    def create_job(request: httpx.Request) -> httpx.Response:
        """The SQL function: an existing key returns its job, anything else inserts."""
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(502)
        key = json.loads(request.content)["p_idempotency_key"]
        assert key is not None, "create_job must always carry an idempotency key"
        if key not in inserted:
            inserted[key] = {
                "id": str(uuid4()),
                "user_id": str(user),
                "status": "queued",
                "stage": "upload",
                "progress": 0.0,
                "created_at": "2026-09-01T00:00:00Z",
            }
        return httpx.Response(200, json=inserted[key])

    respx.post(f"{BASE}/rest/v1/rpc/create_job").mock(side_effect=create_job)
    status = await jobs.create(user, JobOptions(), "input.wav", 1)

    assert attempts == 2, "the transport failure is retried"
    assert len(inserted) == 1, "the retry must not insert a second job"
    assert str(status.job_id) == next(iter(inserted.values()))["id"]
    await supabase.aclose()


@respx.mock
async def test_create_job_prefers_the_client_idempotency_key(supabase: SupabaseClient) -> None:
    jobs = SupabaseJobsService(supabase, JobEventBus())
    row = {
        "id": str(uuid4()),
        "status": "queued",
        "stage": "upload",
        "progress": 0.0,
        "created_at": "2026-09-01T00:00:00Z",
    }
    generated = rpc("create_job", row)
    await jobs.create(uuid4(), JobOptions(), "input.wav", 1)
    key = sent(generated)["p_idempotency_key"]
    assert key.startswith(SERVER_IDEMPOTENCY_PREFIX)
    UUID(key.removeprefix(SERVER_IDEMPOTENCY_PREFIX))

    await jobs.create(uuid4(), JobOptions(idempotency_key="client-key"), "input.wav", 1)
    assert sent(generated)["p_idempotency_key"] == "client-key"
    await supabase.aclose()
