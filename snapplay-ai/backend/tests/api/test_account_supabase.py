"""The PostgREST / GoTrue calls behind job listing, key listing, the account export and
account deletion (§1, §2, §11) — what is sent, and what is never selected."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
import pytest
import respx

from app.config import Settings
from app.errors import ApiException
from app.services.api_keys import API_KEY_INFO_COLUMNS, SupabaseApiKeysService
from app.services.events import JobEventBus
from app.services.jobs import SupabaseJobsService, encode_job_cursor
from app.services.supabase import (
    SupabaseClient,
    all_of,
    any_of,
    encode_filters,
    rpc_is_retryable,
)
from app.services.users import EXPORT_PAGE_ROWS, UNFINISHED_JOBS_MESSAGE, SupabaseUsersService

BASE = "http://supabase.test"


@pytest.fixture
def supabase(settings: Settings) -> SupabaseClient:
    return SupabaseClient(settings, backoff_seconds=0.0)


def job_row(user: Any, stamp: str) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "user_id": str(user),
        "status": "succeeded",
        "stage": "done",
        "progress": 1.0,
        "created_at": stamp,
    }


def test_logical_filter_groups_are_encoded_with_quoted_values() -> None:
    stamp = datetime(2026, 9, 1, 12, 0, 0, 123456, tzinfo=UTC)
    params = encode_filters(
        [
            ("user_id", "eq", "u1"),
            any_of(
                ("created_at", "lt", stamp),
                all_of(("created_at", "eq", stamp), ("id", "lt", "j1")),
            ),
        ]
    )
    assert params == {
        "user_id": "eq.u1",
        "or": (
            '(created_at.lt."2026-09-01T12:00:00.123456+00:00",'
            'and(created_at.eq."2026-09-01T12:00:00.123456+00:00",id.lt.j1))'
        ),
    }


@respx.mock
async def test_job_listing_orders_by_the_keyset_and_pages_with_it(
    supabase: SupabaseClient,
) -> None:
    jobs = SupabaseJobsService(supabase, JobEventBus())
    user = uuid4()
    rows = [job_row(user, f"2026-09-0{d}T00:00:00.5+00:00") for d in (3, 2, 1)]
    route = respx.get(f"{BASE}/rest/v1/jobs").mock(return_value=httpx.Response(200, json=rows))

    page = await jobs.list(user, limit=2)
    assert [str(j.job_id) for j in page.jobs] == [rows[0]["id"], rows[1]["id"]]
    params = route.calls.last.request.url.params
    assert params["user_id"] == f"eq.{user}" and "or" not in params
    assert params["order"] == "created_at.desc,id.desc" and params["limit"] == "3"
    assert page.next_cursor == encode_job_cursor(page.jobs[1])
    assert page.next_cursor == f"2026-09-02T00:00:00.500000Z_{rows[1]['id']}"

    await jobs.list(user, limit=2, cursor=page.next_cursor)
    params = route.calls.last.request.url.params
    assert params["or"] == (
        '(created_at.lt."2026-09-02T00:00:00.500000+00:00",'
        f'and(created_at.eq."2026-09-02T00:00:00.500000+00:00",id.lt.{rows[1]["id"]}))'
    )

    with pytest.raises(ApiException) as info:
        await jobs.list(user, cursor="2026-09-02T00:00:00.500000Z_not-a-uuid")
    assert info.value.status == 422
    with pytest.raises(ApiException):
        await jobs.list(user, cursor="42")
    await supabase.aclose()


@respx.mock
async def test_api_key_listing_never_selects_the_hash(supabase: SupabaseClient) -> None:
    keys = SupabaseApiKeysService(supabase)
    user = uuid4()
    row = {
        "id": str(uuid4()),
        "name": "ci",
        "prefix": "sp_live_ab12",
        "created_at": "2026-09-01T00:00:00Z",
        "last_used_at": None,
        "revoked_at": None,
    }
    route = respx.get(f"{BASE}/rest/v1/api_keys").mock(return_value=httpx.Response(200, json=[row]))
    listed = await keys.list(user)
    assert [k.prefix for k in listed] == ["sp_live_ab12"]
    params = route.calls.last.request.url.params
    assert params["select"] == API_KEY_INFO_COLUMNS and "key_hash" not in params["select"]
    assert params["user_id"] == f"eq.{user}" and params["order"] == "created_at.desc"
    await supabase.aclose()


@respx.mock
async def test_profile_rows_carry_the_signup_metadata(
    supabase: SupabaseClient, settings: Settings
) -> None:
    users = SupabaseUsersService(supabase, settings)
    user = uuid4()
    respx.get(f"{BASE}/rest/v1/profiles").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": str(user),
                    "email": "a@b.c",
                    "plan": "free",
                    "referral_code": "GREG30",
                    "marketing_opt_in": True,
                    "deleted_at": None,
                }
            ],
        )
    )
    profile = await users.get(user)
    assert profile is not None and profile.referral_code == "GREG30"
    assert profile.marketing_opt_in is True and profile.deleted_at is None
    await supabase.aclose()


@respx.mock
async def test_delete_account_runs_the_function_then_deletes_the_login(
    supabase: SupabaseClient, settings: Settings
) -> None:
    users = SupabaseUsersService(supabase, settings)
    user = uuid4()
    rpc = respx.post(f"{BASE}/rest/v1/rpc/delete_user_account").mock(
        return_value=httpx.Response(
            200,
            json={
                "user_id": str(user),
                "requested_at": "2026-09-01T00:00:00Z",
                "ledger_rows_kept": 4,
            },
        )
    )
    admin = respx.delete(f"{BASE}/auth/v1/admin/users/{user}").mock(
        return_value=httpx.Response(200, json={})
    )
    await users.delete_account(user)
    assert json.loads(rpc.calls.last.request.content) == {"p_user_id": str(user)}
    headers = admin.calls.last.request.headers
    assert headers["apikey"] == "service-role-test"
    assert headers["authorization"] == "Bearer service-role-test"
    assert rpc_is_retryable("delete_user_account", {"p_user_id": str(user)})

    # A login already gone is the wanted end state; a provider outage is not.
    admin.mock(return_value=httpx.Response(404, json={"msg": "user not found"}))
    await users.delete_account(user)
    admin.mock(return_value=httpx.Response(503))
    with pytest.raises(ApiException) as info:
        await users.delete_account(user)
    assert info.value.status == 500 and admin.calls.call_count == 5

    # An unfinished job: the function's P0409 becomes the contract's 409 with its message.
    rpc.mock(return_value=httpx.Response(400, json={"code": "P0409", "message": "conflict"}))
    with pytest.raises(ApiException) as info:
        await users.delete_account(user)
    assert info.value.status == 409 and info.value.message == UNFINISHED_JOBS_MESSAGE
    assert admin.calls.call_count == 5
    await supabase.aclose()


@respx.mock
async def test_export_reads_every_table_and_pages_past_the_row_cap(
    supabase: SupabaseClient, settings: Settings
) -> None:
    users = SupabaseUsersService(supabase, settings)
    user, affiliate_id, purchase_id = uuid4(), uuid4(), uuid4()

    respx.get(f"{BASE}/rest/v1/profiles").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": str(user),
                    "email": "a@b.c",
                    "plan": "credits",
                    "created_at": "2026-01-01T00:00:00Z",
                    "deleted_at": None,
                }
            ],
        )
    )
    respx.post(f"{BASE}/rest/v1/rpc/get_balance").mock(
        return_value=httpx.Response(200, json={"credits": 5, "reserved": 0, "available": 5})
    )

    def subscriptions(request: httpx.Request) -> httpx.Response:
        if request.url.params["select"] == "current_period_end":
            return httpx.Response(200, json=[{"current_period_end": "2026-10-01T00:00:00Z"}])
        return httpx.Response(
            200,
            json=[
                {
                    "id": str(uuid4()),
                    "user_id": str(user),
                    "provider": "paddle",
                    "provider_subscription_id": "sub-1",
                    "plan_id": "sub_monthly",
                    "status": "active",
                    "current_period_end": "2026-10-01T00:00:00Z",
                    "cancelled_at": None,
                    "referral_code": None,
                    "raw": {"secret": "payload"},
                    "created_at": "2026-09-01T00:00:00Z",
                }
            ],
        )

    respx.get(f"{BASE}/rest/v1/subscriptions").mock(side_effect=subscriptions)

    def ledger_entry(seq: int) -> dict[str, Any]:
        return {
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

    def ledger(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        assert params["order"] == "seq.asc" and params["limit"] == str(EXPORT_PAGE_ROWS)
        if "seq" not in params:
            rows = [ledger_entry(i) for i in range(1, EXPORT_PAGE_ROWS + 1)]
            return httpx.Response(200, json=rows)
        assert params["seq"] == f"gt.{EXPORT_PAGE_ROWS}"
        return httpx.Response(200, json=[ledger_entry(EXPORT_PAGE_ROWS + 1)])

    ledger_route = respx.get(f"{BASE}/rest/v1/credit_ledger").mock(side_effect=ledger)
    respx.get(f"{BASE}/rest/v1/jobs").mock(
        return_value=httpx.Response(200, json=[job_row(user, "2026-09-01T00:00:00Z")])
    )
    respx.get(f"{BASE}/rest/v1/purchases").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": str(purchase_id),
                    "user_id": str(user),
                    "provider": "lemonsqueezy",
                    "provider_order_id": "ord-1",
                    "plan_id": "pack_50",
                    "credits": 50,
                    "amount_cents": 900,
                    "net_cents": 800,
                    "currency": "USD",
                    "referral_code": "friend",
                    "raw": {"customer_email": "a@b.c"},
                    "idempotency_key": "lemonsqueezy:order_created:1",
                    "created_at": "2026-09-01T00:00:00Z",
                }
            ],
        )
    )
    keys_route = respx.get(f"{BASE}/rest/v1/api_keys").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": str(uuid4()),
                    "name": "ci",
                    "prefix": "sp_live_ab12",
                    "created_at": "2026-09-01T00:00:00Z",
                    "last_used_at": None,
                    "revoked_at": None,
                }
            ],
        )
    )
    respx.get(f"{BASE}/rest/v1/affiliates").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": str(affiliate_id),
                    "user_id": str(user),
                    "code": "GREG30",
                    "commission_rate": "0.3000",
                    "payout_details": {"paypal": "a@b.c"},
                    "active": True,
                    "created_at": "2026-09-01T00:00:00Z",
                }
            ],
        )
    )
    codes_route = respx.get(f"{BASE}/rest/v1/referral_codes").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": str(uuid4()),
                    "code": "GREG30",
                    "affiliate_id": str(affiliate_id),
                    "uses": 2,
                    "active": True,
                    "created_at": "2026-09-01T00:00:00Z",
                }
            ],
        )
    )
    respx.get(f"{BASE}/rest/v1/affiliate_commissions").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": str(uuid4()),
                    "purchase_id": str(purchase_id),
                    "affiliate_id": str(affiliate_id),
                    "rate": "0.3000",
                    "amount_cents": 240,
                    "status": "pending",
                    "paid_at": None,
                    "created_at": "2026-09-01T00:00:00Z",
                }
            ],
        )
    )

    export = await users.export(user)
    assert export.user.email == "a@b.c" and export.user.plan == "credits"
    assert export.balance.available == 5 and export.balance.subscription_renews_at is not None
    assert len(export.ledger) == EXPORT_PAGE_ROWS + 1 and ledger_route.calls.call_count == 2
    assert [e.balance_after for e in export.ledger][:2] == [1, 2]
    assert len(export.jobs) == 1 and export.jobs[0].status == "succeeded"
    assert export.purchases[0].provider_order_id == "ord-1"
    assert export.subscriptions[0].provider_subscription_id == "sub-1"
    assert export.api_keys[0].prefix == "sp_live_ab12"
    assert keys_route.calls.last.request.url.params["select"] == API_KEY_INFO_COLUMNS
    assert codes_route.calls.last.request.url.params["affiliate_id"] == f"eq.{affiliate_id}"
    assert export.affiliate is not None and export.affiliate.commission_rate == 0.3
    assert export.affiliate.commissions[0].amount_cents == 240
    dumped = export.model_dump_json()
    assert "payload" not in dumped and "customer_email" not in dumped and "sp_live_ab12" in dumped

    respx.get(f"{BASE}/rest/v1/profiles").mock(return_value=httpx.Response(200, json=[]))
    with pytest.raises(ApiException) as info:
        await users.export(user)
    assert info.value.status == 404
    await supabase.aclose()
