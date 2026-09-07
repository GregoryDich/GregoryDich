"""In-memory backend for tests and local development.

:class:`MemoryStore` reproduces ``db/migrations/0002_functions.sql`` function by function
— the same idempotency keys (``reserve:<job_id>``, ``signup:<user_id>``, …), the same
state machine, the same SQLSTATE-equivalent :class:`ApiException` codes — so the routers
behave identically on either backend. All state lives on the event-loop thread; every
mutating method is synchronous, which makes each one atomic with respect to the loop.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID, uuid4

from app.auth.api_keys import generate_api_key, hash_api_key, hashes_match, is_well_formed
from app.config import Settings
from app.errors import CONFLICT, INSUFFICIENT_CREDITS, NOT_FOUND, VALIDATION_ERROR, ApiException
from app.schemas import (
    ApiKeyCreateResponse,
    Balance,
    CreditBalance,
    JobOptions,
    JobResult,
    JobStatus,
    LedgerPage,
    MeUser,
    PlanKind,
)
from app.services.credits import ACTIVE_SUBSCRIPTION_STATUSES, ledger_page, parse_ledger_cursor
from app.services.events import EVENT_PROGRESS, TERMINAL_EVENTS, JobEvent, JobEventBus
from app.services.jobs import (
    DEFAULT_POLL_INTERVAL_SECONDS,
    JOB_CREDITS,
    EventsMode,
    job_status_from_record,
    progress_event,
    status_event,
    stream_job_events,
)
from app.services.plans import PlanRecord
from app.services.users import (
    SIGNUP_NOTE,
    SIGNUP_SOURCE,
    me_user_from_record,
    normalise_email,
    signup_idempotency_key,
)
from app.services.webhooks import (
    PurchaseProvider,
    PurchaseRecord,
    SubscriptionRecord,
    SubscriptionStatus,
)

LEMONSQUEEZY_TEMPLATE = (
    "https://snapplay.lemonsqueezy.com/checkout/buy/{variant_id}"
    "?checkout[custom][user_id]={user_id}&checkout[custom][ref]={ref}"
)
_POSITIVE = frozenset({"grant", "refund", "release"})
_NEGATIVE = frozenset({"reserve", "capture"})


def seed_plans() -> list[PlanRecord]:
    """The plan rows seeded by ``0001_schema.sql``."""
    return [
        PlanRecord(id="free", name="Free", credits=3, price_cents=0, sort_order=0),
        PlanRecord(
            id="pack_50",
            name="50 Credits",
            credits=50,
            price_cents=900,
            checkout_url_template=LEMONSQUEEZY_TEMPLATE,
            sort_order=1,
        ),
        PlanRecord(
            id="sub_monthly",
            name="Pro Monthly",
            credits=60,
            price_cents=799,
            interval="month",
            checkout_url_template=LEMONSQUEEZY_TEMPLATE,
            sort_order=2,
        ),
    ]


def _invalid_argument(detail: str) -> ApiException:
    return ApiException(VALIDATION_ERROR, message="invalid_argument", details={"detail": detail})


def _not_found(detail: str) -> ApiException:
    return ApiException(NOT_FOUND, message="not_found", details={"detail": detail})


def _conflict(detail: str) -> ApiException:
    return ApiException(CONFLICT, message="conflict", details={"detail": detail})


def _insufficient(available: int, requested: int) -> ApiException:
    return ApiException(
        INSUFFICIENT_CREDITS,
        message=f"You have {available} credits.",
        details={"available": available, "requested": requested},
    )


# --- rows -----------------------------------------------------------------------------------


@dataclass
class ProfileRow:
    id: UUID
    email: str | None
    created_at: datetime
    plan: PlanKind = "free"

    def as_record(self) -> dict[str, Any]:
        return {"id": self.id, "email": self.email, "plan": self.plan}


@dataclass
class AccountRow:
    user_id: UUID
    balance: int = 0
    reserved: int = 0

    def snapshot(self) -> CreditBalance:
        return CreditBalance(
            credits=self.balance, reserved=self.reserved, available=self.balance - self.reserved
        )


@dataclass
class LedgerRow:
    id: UUID
    seq: int
    user_id: UUID
    entry_type: str
    amount: int
    balance_after: int
    reserved_after: int
    job_id: UUID | None
    source: str | None
    idempotency_key: str | None
    note: str | None
    expires_at: datetime | None
    created_at: datetime

    def as_record(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class JobRow:
    id: UUID
    user_id: UUID
    created_at: datetime
    options: dict[str, Any]
    input_meta: dict[str, Any]
    idempotency_key: str | None
    status: str = "queued"
    stage: str = "upload"
    progress: float = 0.0
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    worker_ref: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    expires_at: datetime | None = None

    def as_record(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class ApiKeyRow:
    id: UUID
    user_id: UUID
    key_hash: str
    prefix: str
    name: str | None
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


@dataclass
class WebhookEventRow:
    id: UUID
    provider: str
    event_name: str
    idempotency_key: str
    payload: dict[str, Any]
    received_at: datetime
    processed_at: datetime | None = None
    error: str | None = None


@dataclass
class AffiliateRow:
    id: UUID
    user_id: UUID
    code: str
    commission_rate: Decimal
    active: bool = True


@dataclass
class ReferralCodeRow:
    id: UUID
    code: str
    affiliate_id: UUID
    uses: int = 0
    active: bool = True


@dataclass
class CommissionRow:
    id: UUID
    purchase_id: UUID
    affiliate_id: UUID
    referral_code_id: UUID
    rate: Decimal
    amount_cents: int
    created_at: datetime
    status: str = "pending"


# --- store ------------------------------------------------------------------------------------


@dataclass
class MemoryStore:
    settings: Settings
    profiles: dict[UUID, ProfileRow] = field(default_factory=dict)
    accounts: dict[UUID, AccountRow] = field(default_factory=dict)
    ledger: list[LedgerRow] = field(default_factory=list)
    jobs: dict[UUID, JobRow] = field(default_factory=dict)
    api_keys: dict[UUID, ApiKeyRow] = field(default_factory=dict)
    plans: dict[str, PlanRecord] = field(default_factory=dict)
    purchases: dict[UUID, PurchaseRecord] = field(default_factory=dict)
    subscriptions: dict[UUID, SubscriptionRecord] = field(default_factory=dict)
    webhook_events: dict[str, WebhookEventRow] = field(default_factory=dict)
    affiliates: dict[UUID, AffiliateRow] = field(default_factory=dict)
    referral_codes: dict[str, ReferralCodeRow] = field(default_factory=dict)
    commissions: dict[UUID, CommissionRow] = field(default_factory=dict)
    _seq: int = 0
    _ledger_keys: dict[str, LedgerRow] = field(default_factory=dict)
    _job_entries: dict[tuple[UUID, str], LedgerRow] = field(default_factory=dict)
    _keys_by_hash: dict[str, ApiKeyRow] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.plans:
            self.plans = {plan.id: plan for plan in seed_plans()}

    @staticmethod
    def now() -> datetime:
        return datetime.now(UTC)

    # --- ledger helpers (lock_credit_account / append_ledger) ------------------------------

    def _lock_account(self, user_id: UUID) -> AccountRow:
        account = self.accounts.get(user_id)
        if account is None:
            raise _not_found(f"credit account for user {user_id}")
        return account

    def _append(
        self,
        account: AccountRow,
        entry_type: str,
        amount: int,
        job_id: UUID | None,
        source: str | None,
        idempotency_key: str | None,
        note: str | None = None,
        expires_at: datetime | None = None,
    ) -> LedgerRow:
        if (
            (entry_type in _POSITIVE and amount <= 0)
            or (entry_type in _NEGATIVE and amount >= 0)
            or (entry_type == "expire" and amount > 0)
            or (entry_type == "adjust" and amount == 0)
        ):
            raise ValueError(f"ledger sign violation: {entry_type} {amount}")
        if account.balance < 0 or account.reserved < 0 or account.reserved > account.balance:
            raise ValueError("credit account invariant violated")
        self._seq += 1
        row = LedgerRow(
            id=uuid4(),
            seq=self._seq,
            user_id=account.user_id,
            entry_type=entry_type,
            amount=amount,
            balance_after=account.balance,
            reserved_after=account.reserved,
            job_id=job_id,
            source=source,
            idempotency_key=idempotency_key,
            note=note,
            expires_at=expires_at,
            created_at=self.now(),
        )
        self.ledger.append(row)
        if idempotency_key is not None:
            self._ledger_keys[idempotency_key] = row
        if job_id is not None:
            self._job_entries[(job_id, entry_type)] = row
        return row

    # --- credits (§6) -----------------------------------------------------------------------

    def reserve_credits(self, user_id: UUID, job_id: UUID, amount: int) -> CreditBalance:
        if amount <= 0:
            raise _invalid_argument("p_amount must be positive")
        account = self._lock_account(user_id)
        if (job_id, "reserve") in self._job_entries:
            return account.snapshot()
        available = account.balance - account.reserved
        if available < amount:
            raise _insufficient(available, amount)
        account.reserved += amount
        self._append(account, "reserve", -amount, job_id, f"job:{job_id}", f"reserve:{job_id}")
        return account.snapshot()

    def settle_reservation(self, job_id: UUID, success: bool) -> CreditBalance:
        reserve = self._job_entries.get((job_id, "reserve"))
        if reserve is None:
            raise _not_found(f"reservation for job {job_id}")
        account = self._lock_account(reserve.user_id)
        if (job_id, "capture") in self._job_entries or (job_id, "release") in self._job_entries:
            return account.snapshot()
        amount = -reserve.amount
        if success:
            account.balance -= amount
            account.reserved -= amount
            self._append(account, "capture", -amount, job_id, reserve.source, f"capture:{job_id}")
        else:
            account.reserved -= amount
            self._append(account, "release", amount, job_id, reserve.source, f"release:{job_id}")
        return account.snapshot()

    def grant_credits(
        self,
        user_id: UUID,
        amount: int,
        source: str,
        idempotency_key: str | None,
        note: str | None = None,
        expires_at: datetime | None = None,
    ) -> CreditBalance:
        if amount <= 0:
            raise _invalid_argument("p_amount must be positive")
        if idempotency_key is None:
            raise _invalid_argument("p_idempotency_key is required")
        account = self._lock_account(user_id)
        if idempotency_key in self._ledger_keys:
            return account.snapshot()
        account.balance += amount
        self._append(account, "grant", amount, None, source, idempotency_key, note, expires_at)
        return account.snapshot()

    def adjust_credits(
        self,
        user_id: UUID,
        amount: int,
        source: str,
        idempotency_key: str | None,
        note: str | None = None,
    ) -> CreditBalance:
        if amount == 0:
            raise _invalid_argument("p_amount must be non-zero")
        if idempotency_key is None:
            raise _invalid_argument("p_idempotency_key is required")
        account = self._lock_account(user_id)
        if idempotency_key in self._ledger_keys:
            return account.snapshot()
        available = account.balance - account.reserved
        if amount < 0 and available < -amount:
            raise _insufficient(available, -amount)
        account.balance += amount
        self._append(account, "adjust", amount, None, source, idempotency_key, note)
        return account.snapshot()

    def refund_job(self, job_id: UUID, reason: str) -> CreditBalance:
        capture = self._job_entries.get((job_id, "capture"))
        if capture is None:
            raise _not_found(f"capture for job {job_id}")
        account = self._lock_account(capture.user_id)
        if (job_id, "refund") in self._job_entries:
            return account.snapshot()
        amount = -capture.amount
        account.balance += amount
        self._append(account, "refund", amount, job_id, capture.source, f"refund:{job_id}", reason)
        return account.snapshot()

    def get_balance(self, user_id: UUID) -> CreditBalance:
        account = self.accounts.get(user_id)
        if account is None:
            return CreditBalance(credits=0, reserved=0, available=0)
        return account.snapshot()

    def expire_credits(self) -> int:
        now = self.now()
        due = [
            g
            for g in self.ledger
            if g.entry_type == "grant"
            and g.expires_at is not None
            and g.expires_at <= now
            and f"expire:{g.id}" not in self._ledger_keys
        ]
        due.sort(key=lambda g: (str(g.user_id), g.expires_at or now, g.seq))
        count = 0
        for grant in due:
            account = self._lock_account(grant.user_id)
            spent = -sum(
                r.amount
                for r in self.ledger
                if r.user_id == grant.user_id
                and r.seq > grant.seq
                and r.entry_type in ("capture", "adjust")
                and r.amount < 0
            )
            remaining = min(max(grant.amount - spent, 0), account.balance - account.reserved)
            account.balance -= remaining
            self._append(
                account,
                "expire",
                -remaining,
                None,
                grant.source,
                f"expire:{grant.id}",
                f"{remaining} of {grant.amount} credits expired",
            )
            count += 1
        return count

    def ledger_page(self, user_id: UUID, limit: int, cursor: int | None) -> LedgerPage:
        rows = [
            r.as_record()
            for r in reversed(self.ledger)
            if r.user_id == user_id and (cursor is None or r.seq < cursor)
        ]
        return ledger_page(rows[: limit + 1], limit)

    # --- jobs (§2, §10) -----------------------------------------------------------------------

    def create_job(
        self,
        user_id: UUID,
        options: dict[str, Any],
        input_meta: dict[str, Any],
        idempotency_key: str | None,
    ) -> JobRow:
        self._lock_account(user_id)
        if idempotency_key is not None:
            existing = self.find_job_by_key(user_id, idempotency_key)
            if existing is not None:
                return existing
        job = JobRow(
            id=uuid4(),
            user_id=user_id,
            created_at=self.now(),
            options=dict(options),
            input_meta=dict(input_meta),
            idempotency_key=idempotency_key,
        )
        self.jobs[job.id] = job
        try:
            self.reserve_credits(user_id, job.id, JOB_CREDITS)
        except ApiException:
            del self.jobs[job.id]  # the SQL transaction rolls the insert back
            raise
        return job

    def find_job_by_key(self, user_id: UUID, idempotency_key: str) -> JobRow | None:
        for job in self.jobs.values():
            if job.user_id == user_id and job.idempotency_key == idempotency_key:
                return job
        return None

    def _job(self, job_id: UUID) -> JobRow:
        job = self.jobs.get(job_id)
        if job is None:
            raise _not_found(f"job {job_id}")
        return job

    def start_job(self, job_id: UUID, worker_ref: str | None = None) -> JobRow:
        job = self._job(job_id)
        if job.status == "running":
            job.worker_ref = worker_ref or job.worker_ref
            return job
        if job.status != "queued":
            raise _conflict(f"job is {job.status}")
        job.status = "running"
        job.started_at = self.now()
        job.worker_ref = worker_ref or job.worker_ref
        return job

    def update_job_progress(self, job_id: UUID, stage: str | None, progress: float | None) -> JobRow:
        job = self._job(job_id)
        if job.status in ("queued", "running"):
            job.stage = stage or job.stage
            job.progress = min(max(progress if progress is not None else job.progress, 0.0), 1.0)
        return job

    def complete_job(self, job_id: UUID, result: dict[str, Any] | None) -> JobRow:
        job = self._job(job_id)
        if job.status == "succeeded":
            return job
        if job.status not in ("queued", "running"):
            raise _conflict(f"job is {job.status}")
        balance = self.settle_reservation(job_id, True)
        charged = -self._job_entries[(job_id, "capture")].amount
        now = self.now()
        raw_expiry = (result or {}).get("expires_at")
        expires_at = (
            datetime.fromisoformat(raw_expiry.replace("Z", "+00:00"))
            if isinstance(raw_expiry, str)
            else now + timedelta(hours=24)
        )
        job.status = "succeeded"
        job.stage = "done"
        job.progress = 1.0
        job.result = {
            "expires_at": expires_at.isoformat(),
            **(result or {}),
            "job_id": str(job.id),
            "credits_charged": charged,
            "balance_after": balance.credits,
        }
        job.error = None
        job.started_at = job.started_at or now
        job.finished_at = now
        job.expires_at = expires_at
        return job

    def fail_job(self, job_id: UUID, error: dict[str, Any] | None) -> JobRow:
        job = self._job(job_id)
        if job.status == "failed":
            return job
        if job.status not in ("queued", "running"):
            raise _conflict(f"job is {job.status}")
        self.settle_reservation(job_id, False)
        job.status = "failed"
        job.error = error or {"code": "internal_error", "message": "job failed"}
        job.finished_at = self.now()
        return job

    def cancel_job(self, job_id: UUID, user_id: UUID) -> JobRow:
        job = self.jobs.get(job_id)
        if job is None or job.user_id != user_id:
            raise _not_found(f"job {job_id}")
        if job.status == "cancelled":
            return job
        if job.status != "queued":
            raise _conflict(f"job is {job.status}")
        self.settle_reservation(job_id, False)
        job.status = "cancelled"
        job.finished_at = self.now()
        return job

    def reap_stale_jobs(self, timeout_seconds: int) -> list[UUID]:
        if timeout_seconds <= 0:
            raise _invalid_argument("p_timeout_seconds must be positive")
        cutoff = self.now() - timedelta(seconds=timeout_seconds)
        stale = [
            job.id
            for job in self.jobs.values()
            if job.status == "running" and (job.started_at or job.created_at) < cutoff
        ]
        for job_id in stale:
            self.fail_job(
                job_id,
                {
                    "code": "worker_timeout",
                    "message": f"no completion within {timeout_seconds} seconds",
                },
            )
        return stale

    # --- users --------------------------------------------------------------------------------

    def ensure_user(self, user_id: UUID, email: str) -> ProfileRow:
        profile = self.profiles.get(user_id)
        if profile is None:
            profile = ProfileRow(
                id=user_id, email=normalise_email(email) or None, created_at=self.now()
            )
            self.profiles[user_id] = profile
            self.accounts.setdefault(user_id, AccountRow(user_id=user_id))
            if self.settings.free_signup_credits > 0:
                self.grant_credits(
                    user_id,
                    self.settings.free_signup_credits,
                    SIGNUP_SOURCE,
                    signup_idempotency_key(user_id),
                    SIGNUP_NOTE,
                )
        elif profile.email is None and email:
            profile.email = normalise_email(email)
        return profile

    def find_profile_by_email(self, email: str) -> ProfileRow | None:
        wanted = normalise_email(email)
        return next((p for p in self.profiles.values() if p.email == wanted), None)

    def set_plan(self, user_id: UUID, plan: PlanKind, renews_at: datetime | None) -> ProfileRow:
        profile = self.profiles.get(user_id)
        if profile is None:
            raise _not_found(f"profile {user_id}")
        profile.plan = plan
        if renews_at is not None:
            for subscription in self.subscriptions.values():
                if (
                    subscription.user_id == user_id
                    and subscription.status in ACTIVE_SUBSCRIPTION_STATUSES
                ):
                    subscription.current_period_end = renews_at
        return profile

    def subscription_renews_at(self, user_id: UUID) -> datetime | None:
        ends = [
            s.current_period_end
            for s in self.subscriptions.values()
            if s.user_id == user_id
            and s.status in ACTIVE_SUBSCRIPTION_STATUSES
            and s.current_period_end is not None
        ]
        return max(ends) if ends else None

    # --- purchases, subscriptions, affiliates (§4, §12) -----------------------------------------

    def record_purchase(
        self,
        user_id: UUID,
        provider: PurchaseProvider,
        provider_order_id: str | None,
        plan_id: str,
        amount_cents: int | None,
        net_cents: int | None,
        referral_code: str | None,
        raw: dict[str, Any] | None,
        idempotency_key: str | None,
    ) -> PurchaseRecord:
        if idempotency_key is None or provider_order_id is None:
            raise _invalid_argument("p_idempotency_key and p_provider_order_id are required")
        self._lock_account(user_id)
        for purchase in self.purchases.values():
            if purchase.idempotency_key == idempotency_key or (
                purchase.provider == provider and purchase.provider_order_id == provider_order_id
            ):
                if purchase.user_id != user_id:
                    raise _conflict(
                        f"order {provider}:{provider_order_id} belongs to another user"
                    )
                return purchase
        plan = self.plans.get(plan_id)
        if plan is None:
            raise _not_found(f"plan {plan_id}")
        purchase = PurchaseRecord(
            id=uuid4(),
            user_id=user_id,
            provider=provider,
            provider_order_id=provider_order_id,
            plan_id=plan.id,
            credits=plan.credits,
            amount_cents=max(amount_cents or 0, 0),
            net_cents=max(net_cents or 0, 0),
            currency=plan.currency,
            referral_code=referral_code,
            idempotency_key=idempotency_key,
            created_at=self.now(),
        )
        self.purchases[purchase.id] = purchase
        if plan.credits > 0:
            self.grant_credits(
                user_id,
                plan.credits,
                f"{provider}:order:{provider_order_id}",
                idempotency_key,
                plan.name,
            )
        profile = self.profiles[user_id]
        if plan.interval is not None:
            profile.plan = "subscription"
        elif profile.plan == "free":
            profile.plan = "credits"
        if referral_code is not None:
            code = self.referral_codes.get(referral_code.lower())
            affiliate = self.affiliates.get(code.affiliate_id) if code else None
            if (
                code is not None
                and affiliate is not None
                and code.active
                and affiliate.active
                and affiliate.user_id != user_id
            ):
                commission = int(
                    (affiliate.commission_rate * purchase.net_cents).quantize(
                        Decimal(1), rounding=ROUND_HALF_UP
                    )
                )
                self.commissions[purchase.id] = CommissionRow(
                    id=uuid4(),
                    purchase_id=purchase.id,
                    affiliate_id=affiliate.id,
                    referral_code_id=code.id,
                    rate=affiliate.commission_rate,
                    amount_cents=commission,
                    created_at=self.now(),
                )
                code.uses += 1
        return purchase

    def add_affiliate(
        self, user_id: UUID, code: str, commission_rate: Decimal | float | str = "0.30"
    ) -> AffiliateRow:
        """An ``affiliates`` row plus its primary ``referral_codes`` row (the insert trigger)."""
        if code.lower() in self.referral_codes:
            raise _conflict(f"referral code {code} exists")
        affiliate = AffiliateRow(
            id=uuid4(), user_id=user_id, code=code, commission_rate=Decimal(str(commission_rate))
        )
        self.affiliates[affiliate.id] = affiliate
        self.referral_codes[code.lower()] = ReferralCodeRow(
            id=uuid4(), code=code, affiliate_id=affiliate.id
        )
        return affiliate

    def upsert_subscription(
        self,
        user_id: UUID,
        provider: PurchaseProvider,
        provider_subscription_id: str,
        plan_id: str | None,
        status: SubscriptionStatus,
        current_period_end: datetime | None,
        cancelled_at: datetime | None,
    ) -> SubscriptionRecord:
        existing = self.find_subscription(provider, provider_subscription_id)
        if existing is None:
            existing = SubscriptionRecord(
                id=uuid4(),
                user_id=user_id,
                provider=provider,
                provider_subscription_id=provider_subscription_id,
                plan_id=plan_id,
                status=status,
            )
            self.subscriptions[existing.id] = existing
        existing.user_id = user_id
        existing.plan_id = plan_id
        existing.status = status
        existing.current_period_end = current_period_end
        existing.cancelled_at = cancelled_at
        return existing

    def find_subscription(
        self, provider: PurchaseProvider, provider_subscription_id: str
    ) -> SubscriptionRecord | None:
        for subscription in self.subscriptions.values():
            if (
                subscription.provider == provider
                and subscription.provider_subscription_id == provider_subscription_id
            ):
                return subscription
        return None

    # --- API keys (§11) -------------------------------------------------------------------------

    def create_api_key(self, user_id: UUID, name: str | None) -> tuple[ApiKeyRow, str]:
        if user_id not in self.profiles:
            raise _not_found(f"profile {user_id}")
        plaintext, prefix, key_hash = generate_api_key()
        row = ApiKeyRow(
            id=uuid4(),
            user_id=user_id,
            key_hash=key_hash,
            prefix=prefix,
            name=name,
            created_at=self.now(),
        )
        self.api_keys[row.id] = row
        self._keys_by_hash[key_hash] = row
        return row, plaintext

    def authenticate_api_key(self, key_hash: str) -> UUID | None:
        row = self._keys_by_hash.get(key_hash)
        if row is None or row.revoked_at is not None or not hashes_match(row.key_hash, key_hash):
            return None
        row.last_used_at = self.now()
        return row.user_id

    def revoke_api_key(self, key_id: UUID, user_id: UUID) -> bool:
        row = self.api_keys.get(key_id)
        if row is None or row.user_id != user_id:
            return False
        row.revoked_at = row.revoked_at or self.now()
        return True

    # --- webhook events (§4) --------------------------------------------------------------------

    def claim_webhook_event(
        self, idempotency_key: str, provider: str, event_name: str, payload: dict[str, Any]
    ) -> bool:
        if idempotency_key in self.webhook_events:
            return False
        self.webhook_events[idempotency_key] = WebhookEventRow(
            id=uuid4(),
            provider=provider,
            event_name=event_name,
            idempotency_key=idempotency_key,
            payload=payload,
            received_at=self.now(),
        )
        return True

    def mark_webhook_processed(self, idempotency_key: str, error: str | None) -> None:
        row = self.webhook_events.get(idempotency_key)
        if row is not None:
            row.processed_at = self.now()
            row.error = error


# --- Protocol implementations -----------------------------------------------------------


class MemoryCreditsService:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    async def get_balance(self, user_id: UUID) -> Balance:
        balance = self._store.get_balance(user_id)
        return Balance(
            **balance.model_dump(),
            subscription_renews_at=self._store.subscription_renews_at(user_id),
        )

    async def reserve(self, user_id: UUID, job_id: UUID, amount: int = 1) -> CreditBalance:
        return self._store.reserve_credits(user_id, job_id, amount)

    async def settle(self, job_id: UUID, success: bool) -> CreditBalance:
        return self._store.settle_reservation(job_id, success)

    async def grant(
        self,
        user_id: UUID,
        amount: int,
        source: str,
        idempotency_key: str,
        note: str | None = None,
        expires_at: datetime | None = None,
    ) -> CreditBalance:
        return self._store.grant_credits(user_id, amount, source, idempotency_key, note, expires_at)

    async def refund_job(self, job_id: UUID, reason: str) -> CreditBalance:
        return self._store.refund_job(job_id, reason)

    async def ledger(self, user_id: UUID, limit: int = 50, cursor: str | None = None) -> LedgerPage:
        return self._store.ledger_page(user_id, limit, parse_ledger_cursor(cursor))


class MemoryJobsService:
    def __init__(
        self,
        store: MemoryStore,
        bus: JobEventBus,
        *,
        events_mode: EventsMode = "bus",
        poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> None:
        self._store = store
        self._bus = bus
        self._events_mode: EventsMode = events_mode
        self._poll_interval = poll_interval

    async def create(
        self, user_id: UUID, options: JobOptions, input_key: str, credits_reserved: int
    ) -> JobStatus:
        if credits_reserved != JOB_CREDITS:
            raise ValueError("create_job reserves exactly one credit per job")
        row = self._store.create_job(
            user_id,
            options.model_dump(mode="json"),
            {"input_name": input_key},
            options.idempotency_key,
        )
        return job_status_from_record(row.as_record())

    async def find_by_idempotency_key(self, user_id: UUID, key: str) -> JobStatus | None:
        row = self._store.find_job_by_key(user_id, key)
        return job_status_from_record(row.as_record()) if row else None

    async def get(self, job_id: UUID, user_id: UUID) -> JobStatus | None:
        row = self._store.jobs.get(job_id)
        if row is None or row.user_id != user_id:
            return None
        return job_status_from_record(row.as_record())

    async def _fetch(self, job_id: UUID) -> JobStatus | None:
        row = self._store.jobs.get(job_id)
        return job_status_from_record(row.as_record()) if row else None

    async def set_progress(self, job_id: UUID, stage: str, progress: float) -> None:
        row = self._store.jobs.get(job_id)
        if row is None:
            return
        if row.status == "queued":
            self._store.start_job(job_id)
        elif row.status != "running":
            return
        self._store.update_job_progress(job_id, stage, progress)
        self._bus.publish(job_id, EVENT_PROGRESS, progress_event(stage, progress)["data"])

    async def complete(self, job_id: UUID, result: JobResult) -> JobStatus:
        return self._finish(self._store.complete_job(job_id, result.model_dump(mode="json")))

    async def fail(self, job_id: UUID, code: str, message: str) -> JobStatus:
        return self._finish(self._store.fail_job(job_id, {"code": code, "message": message}))

    async def cancel(self, job_id: UUID, user_id: UUID) -> JobStatus:
        return self._finish(self._store.cancel_job(job_id, user_id))

    def _finish(self, row: JobRow) -> JobStatus:
        status = job_status_from_record(row.as_record())
        event = status_event(status)
        if event["event"] in TERMINAL_EVENTS:
            self._bus.publish(row.id, event["event"], event["data"])
        return status

    def events(self, job_id: UUID) -> AsyncIterator[JobEvent]:
        return stream_job_events(
            job_id, lambda: self._fetch(job_id), self._bus, self._events_mode, self._poll_interval
        )

    async def reap_stale(self, timeout_seconds: int) -> int:
        reaped = self._store.reap_stale_jobs(timeout_seconds)
        for job_id in reaped:
            self._finish(self._store.jobs[job_id])
        return len(reaped)


class MemoryStorageService:
    """Objects in a dict; ``signed_url`` returns ``memory://<path>?exp=<unix time>``."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    async def upload_bytes(self, path: str, data: bytes, content_type: str) -> str:
        self.objects[path] = (bytes(data), content_type)
        return path

    async def download_bytes(self, path: str) -> bytes:
        try:
            return self.objects[path][0]
        except KeyError:
            raise FileNotFoundError(path) from None

    async def signed_url(self, path: str, ttl_seconds: int) -> str:
        expires = int((datetime.now(UTC) + timedelta(seconds=ttl_seconds)).timestamp())
        return f"memory://{path}?exp={expires}"


class MemoryUsersService:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    async def get(self, user_id: UUID) -> MeUser | None:
        row = self._store.profiles.get(user_id)
        return me_user_from_record(row.as_record()) if row else None

    async def find_by_email(self, email: str) -> MeUser | None:
        row = self._store.find_profile_by_email(email)
        return me_user_from_record(row.as_record()) if row else None

    async def ensure(self, user_id: UUID, email: str) -> MeUser:
        return me_user_from_record(self._store.ensure_user(user_id, email).as_record())

    async def set_plan(self, user_id: UUID, plan: PlanKind, renews_at: datetime | None) -> MeUser:
        return me_user_from_record(self._store.set_plan(user_id, plan, renews_at).as_record())


class MemoryApiKeysService:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    async def create(self, user_id: UUID, name: str) -> ApiKeyCreateResponse:
        row, plaintext = self._store.create_api_key(user_id, name)
        return ApiKeyCreateResponse(
            id=row.id, name=name, prefix=row.prefix, key=plaintext, created_at=row.created_at
        )

    async def revoke(self, user_id: UUID, key_id: UUID) -> bool:
        return self._store.revoke_api_key(key_id, user_id)

    async def resolve(self, plaintext: str) -> UUID | None:
        if not is_well_formed(plaintext):
            return None
        return self._store.authenticate_api_key(hash_api_key(plaintext))


class MemoryWebhookEventsService:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    async def claim(
        self, idempotency_key: str, provider: str, event_type: str, payload: dict[str, Any]
    ) -> bool:
        return self._store.claim_webhook_event(idempotency_key, provider, event_type, payload)

    async def mark_processed(self, idempotency_key: str, error: str | None = None) -> None:
        self._store.mark_webhook_processed(idempotency_key, error)


class MemoryPurchasesService:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    async def record_purchase(
        self,
        *,
        user_id: UUID,
        provider: PurchaseProvider,
        provider_order_id: str,
        plan_id: str,
        amount_cents: int,
        net_cents: int,
        referral_code: str | None,
        raw: dict[str, Any],
        idempotency_key: str,
    ) -> PurchaseRecord:
        return self._store.record_purchase(
            user_id,
            provider,
            provider_order_id,
            plan_id,
            amount_cents,
            net_cents,
            referral_code,
            raw,
            idempotency_key,
        )

    async def upsert_subscription(
        self,
        *,
        user_id: UUID,
        provider: PurchaseProvider,
        provider_subscription_id: str,
        plan_id: str | None,
        status: SubscriptionStatus,
        current_period_end: datetime | None,
        cancelled_at: datetime | None,
        raw: dict[str, Any],
    ) -> SubscriptionRecord:
        return self._store.upsert_subscription(
            user_id,
            provider,
            provider_subscription_id,
            plan_id,
            status,
            current_period_end,
            cancelled_at,
        )

    async def find_subscription(
        self, provider: PurchaseProvider, provider_subscription_id: str
    ) -> SubscriptionRecord | None:
        return self._store.find_subscription(provider, provider_subscription_id)


class MemoryPlansService:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    async def list_active(self) -> list[PlanRecord]:
        plans = [p for p in self._store.plans.values() if p.active]
        return sorted(plans, key=lambda p: (p.sort_order, p.id))

    async def get(self, plan_id: str) -> PlanRecord | None:
        return self._store.plans.get(plan_id)

    async def find_by_variant(self, provider: str, variant_id: str) -> PlanRecord | None:
        for plan in await self.list_active():
            if plan.variant_id(provider) == variant_id:
                return plan
        return None


__all__ = [
    "LEMONSQUEEZY_TEMPLATE",
    "AffiliateRow",
    "ApiKeyRow",
    "CommissionRow",
    "JobRow",
    "LedgerRow",
    "MemoryApiKeysService",
    "MemoryCreditsService",
    "MemoryJobsService",
    "MemoryPlansService",
    "MemoryPurchasesService",
    "MemoryStorageService",
    "MemoryStore",
    "MemoryUsersService",
    "MemoryWebhookEventsService",
    "ProfileRow",
    "ReferralCodeRow",
    "WebhookEventRow",
    "seed_plans",
]
