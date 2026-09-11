"""In-memory backend for tests and local development.

:class:`MemoryStore` reproduces ``db/migrations/0002_functions.sql`` function by function
— the same idempotency keys (``reserve:<job_id>``, ``signup:<user_id>``, …), the same
state machine, the same SQLSTATE-equivalent :class:`ApiException` codes — so the routers
behave identically on either backend. All state lives on the event-loop thread; every
mutating method is synchronous, which makes each one atomic with respect to the loop.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from collections.abc import AsyncIterator, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID, uuid4

import jwt

from app.auth.api_keys import generate_api_key, hash_api_key, hashes_match, is_well_formed
from app.auth.jwt import AUDIENCE, HS_ALGORITHMS
from app.config import Settings
from app.errors import (
    CONFLICT,
    INSUFFICIENT_CREDITS,
    NOT_FOUND,
    UNAUTHORIZED,
    VALIDATION_ERROR,
    ApiException,
)
from app.schemas import (
    FEEDBACK_NOTE_MAX_CHARS,
    NPS_COMMENT_MAX_CHARS,
    PLUGIN_IDENTITY_MAX_CHARS,
    PLUGIN_VERSION_MAX_CHARS,
    AccountExport,
    AffiliateExport,
    ApiKeyCreateResponse,
    ApiKeyInfo,
    Balance,
    CommissionExport,
    CreditBalance,
    FeedbackReason,
    JobFeedbackRequest,
    JobOptions,
    JobResult,
    JobsPage,
    JobStatus,
    LedgerPage,
    PlanKind,
    Profile,
    PurchaseExport,
    ReferralCodeExport,
    SubscriptionExport,
)
from app.services.credits import (
    ACTIVE_SUBSCRIPTION_STATUSES,
    ledger_entry_from_record,
    ledger_page,
    parse_ledger_cursor,
)
from app.services.events import EVENT_PROGRESS, TERMINAL_EVENTS, JobEvent, JobEventBus
from app.services.growth import GrowthHooks, SignupFacts
from app.services.jobs import (
    DEFAULT_POLL_INTERVAL_SECONDS,
    JOB_CREDITS,
    EventsMode,
    JobFinishedHook,
    job_status_from_record,
    jobs_page,
    notify_finished,
    parse_job_cursor,
    progress_event,
    status_event,
    stream_job_events,
    without_signed_urls,
)
from app.services.plans import PlanRecord
from app.services.quality import (
    AUTO_REFUND_FREE_LIFETIME,
    AUTO_REFUND_LOOKBACK_DAYS,
    AUTO_REFUND_WINDOW_HOURS,
    NPS_COOLDOWN_DAYS,
    FeedbackRecord,
    Last24hStats,
    NpsRecord,
    UserFacts,
    auto_refund_allowance,
    auto_refund_reason,
    elapsed_ms,
    percentile,
)
from app.services.supabase import (
    ACCOUNT_EXISTS_MESSAGE,
    EMAIL_NOT_CONFIRMED_MESSAGE,
    INVALID_CREDENTIALS_MESSAGE,
)
from app.services.users import (
    SIGNUP_NOTE,
    SIGNUP_SOURCE,
    UNFINISHED_JOBS_MESSAGE,
    exported_user_from_record,
    normalise_email,
    profile_from_record,
    signup_idempotency_key,
)
from app.services.webhooks import (
    PurchaseProvider,
    PurchaseRecord,
    SubscriptionRecord,
    SubscriptionStatus,
)

LEMONSQUEEZY_TEMPLATE = (
    "https://tonamorph.lemonsqueezy.com/checkout/buy/{variant_id}"
    "?checkout[custom][user_id]={user_id}&checkout[custom][ref]={ref}"
)
_POSITIVE = frozenset({"grant", "refund", "release"})
_NEGATIVE = frozenset({"reserve", "capture"})
QUEUED_TIMEOUT_FACTOR = 10
"""Default queued grace as a multiple of the running timeout (``reap_stale_jobs``)."""
GOTRUE_MIN_PASSWORD_LENGTH = 6
"""GoTrue's default password policy, with its wording (``GOTRUE_PASSWORD_MIN_LENGTH``)."""
GOTRUE_ACCESS_TOKEN_SECONDS = 3600
_PBKDF2_ROUNDS = 20_000
DELETION_SOURCE = "account_deletion"
DELETION_NOTE = "Account deleted; remaining credits forfeited"
ACTIVE_JOB_STATUSES = frozenset({"queued", "running"})
UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")
SIGNUP_META_TEXT_LIMIT = 100


def tombstone_email(user_id: UUID) -> str:
    """What ``delete_user_account`` leaves in ``profiles.email`` (§1)."""
    return f"deleted+{user_id}@invalid"


def deletion_idempotency_key(user_id: UUID) -> str:
    return f"deletion:{user_id}"


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
    deleted_at: datetime | None = None
    referral_code: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_content: str | None = None
    utm_term: str | None = None
    marketing_opt_in: bool = False
    terms_accepted_at: datetime | None = None
    first_seen_at: datetime | None = None

    def as_record(self) -> dict[str, Any]:
        return dict(self.__dict__)


def signup_meta_text(meta: Mapping[str, Any], key: str) -> str | None:
    """``signup_meta_text`` of 0004: trimmed, empty → null, capped at 100 characters."""
    value = meta.get(key)
    text = str(value).strip() if value is not None else ""
    return text[:SIGNUP_META_TEXT_LIMIT] or None


def signup_meta_bool(meta: Mapping[str, Any], key: str) -> bool:
    value = meta.get(key)
    if isinstance(value, bool):
        return value
    return isinstance(value, str) and value.strip().lower() == "true"


def signup_meta_timestamp(meta: Mapping[str, Any], key: str) -> datetime | None:
    value = meta.get(key)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


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
    created_at: datetime
    active: bool = True
    payout_details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReferralCodeRow:
    id: UUID
    code: str
    affiliate_id: UUID
    created_at: datetime
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
    paid_at: datetime | None = None


@dataclass
class AccountDeletionRow:
    user_id: UUID
    requested_at: datetime
    ledger_rows_kept: int


@dataclass
class JobFeedbackRow:
    job_id: UUID
    user_id: UUID
    rating: str
    reason: str | None
    note: str | None
    drop_to_ready_ms: int | None
    created_at: datetime
    updated_at: datetime
    refunded: bool = False

    def as_record(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class NpsRow:
    id: UUID
    user_id: UUID
    score: int
    comment: str | None
    created_at: datetime

    def as_record(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class PluginInstallRow:
    user_id: UUID
    plugin_version: str
    host: str
    os: str | None
    first_seen_at: datetime
    last_seen_at: datetime


@dataclass
class GoTrueUserRow:
    """An ``auth.users`` row as the in-memory GoTrue keeps it."""

    id: UUID
    email: str
    password_hash: str
    created_at: datetime
    confirmed_at: datetime | None = None
    confirmation_sent_at: datetime | None = None
    recovery_sent_at: datetime | None = None

    def as_record(self) -> dict[str, Any]:
        """The user object GoTrue returns: the fields the auth router reads."""
        return {
            "id": str(self.id),
            "aud": AUDIENCE,
            "role": "authenticated",
            "email": self.email,
            "email_confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "confirmation_sent_at": (
                self.confirmation_sent_at.isoformat() if self.confirmation_sent_at else None
            ),
            "identities": [{"provider": "email", "user_id": str(self.id)}],
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class SentMail:
    """One email GoTrue would have sent; ``kind`` is ``signup`` or ``recovery``."""

    kind: str
    email: str
    redirect_to: str


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"{salt.hex()}${digest.hex()}"


def _password_matches(stored: str, password: str) -> bool:
    salt_hex, _, digest_hex = stored.partition("$")
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return hmac.compare_digest(digest.hex(), digest_hex)


@dataclass
class MemoryGoTrue:
    """Stand-in for Supabase Auth so the sign-up → confirm → sign-in flow runs without a
    network. Tests and local development only: passwords are PBKDF2 in a dict, tokens are
    HS256 under ``SUPABASE_JWT_SECRET`` (the app's own verifier accepts them), and "sent"
    emails land in :attr:`outbox`. Method results mirror GoTrue's JSON and the errors
    :class:`SupabaseClient` maps them to, so the router behaves identically on either.
    ``autoconfirm`` is ``GOTRUE_MAILER_AUTOCONFIRM``: a session at sign-up instead of a
    confirmation email.
    """

    settings: Settings
    autoconfirm: bool = False
    on_user_created: Callable[[UUID, str, Mapping[str, Any]], object] | None = None
    """The ``on_auth_user_created`` trigger: called with the new row's id, email and
    ``raw_user_meta_data`` before the sign-up answer is returned."""
    users: dict[UUID, GoTrueUserRow] = field(default_factory=dict)
    refresh_tokens: dict[str, UUID] = field(default_factory=dict)
    outbox: list[SentMail] = field(default_factory=list)

    @staticmethod
    def now() -> datetime:
        return datetime.now(UTC)

    def find_by_email(self, email: str) -> GoTrueUserRow | None:
        wanted = normalise_email(email)
        return next((u for u in self.users.values() if u.email == wanted), None)

    def signup(
        self,
        email: str,
        password: str,
        *,
        redirect_to: str,
        data: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """GoTrue's three answers: a session (auto-confirm), the new user with a
        confirmation email on its way, or — for an address that already has a confirmed
        account and no auto-confirm — an obfuscated user with no identities and no email,
        which is how GoTrue itself avoids disclosing the account. ``data`` is the
        supabase-js ``options.data`` that lands in ``raw_user_meta_data``."""
        if len(password) < GOTRUE_MIN_PASSWORD_LENGTH:
            raise ApiException(
                VALIDATION_ERROR,
                message=f"Password should be at least {GOTRUE_MIN_PASSWORD_LENGTH} characters.",
            )
        address = normalise_email(email)
        existing = self.find_by_email(address)
        if existing is not None and existing.confirmed_at is not None:
            if self.autoconfirm:
                raise ApiException(CONFLICT, message=ACCOUNT_EXISTS_MESSAGE)
            return {
                "id": str(uuid4()),
                "aud": AUDIENCE,
                "role": "",
                "email": address,
                "confirmation_sent_at": self.now().isoformat(),
                "identities": [],
            }
        if existing is not None:
            self._send(existing, "signup", redirect_to)
            return existing.as_record()
        user = GoTrueUserRow(
            id=uuid4(), email=address, password_hash=_hash_password(password), created_at=self.now()
        )
        self.users[user.id] = user
        if self.on_user_created is not None:
            self.on_user_created(user.id, user.email, dict(data or {}))
        if self.autoconfirm:
            user.confirmed_at = user.created_at
            return self._session(user)
        self._send(user, "signup", redirect_to)
        return user.as_record()

    def confirm(self, email: str) -> GoTrueUserRow:
        """What clicking the confirmation link does."""
        user = self.find_by_email(email)
        if user is None:
            raise _not_found(f"auth user {normalise_email(email)}")
        user.confirmed_at = user.confirmed_at or self.now()
        return user

    def password_grant(self, email: str, password: str) -> dict[str, Any]:
        user = self.find_by_email(email)
        if user is None or not _password_matches(user.password_hash, password):
            raise ApiException(UNAUTHORIZED, message=INVALID_CREDENTIALS_MESSAGE)
        if user.confirmed_at is None:
            raise ApiException(UNAUTHORIZED, message=EMAIL_NOT_CONFIRMED_MESSAGE)
        return self._session(user)

    def refresh_grant(self, refresh_token: str) -> dict[str, Any]:
        """Rotates: the presented token is spent whether or not a new one is issued."""
        user_id = self.refresh_tokens.pop(refresh_token, None)
        user = self.users.get(user_id) if user_id is not None else None
        if user is None:
            raise ApiException(UNAUTHORIZED, message=INVALID_CREDENTIALS_MESSAGE)
        return self._session(user)

    def recover(self, email: str, *, redirect_to: str) -> None:
        user = self.find_by_email(email)
        if user is not None:
            self._send(user, "recovery", redirect_to)

    def resend(self, email: str, kind: str, *, redirect_to: str) -> None:
        user = self.find_by_email(email)
        if kind == "signup" and user is not None and user.confirmed_at is None:
            self._send(user, "signup", redirect_to)

    def logout(self, access_token: str) -> None:
        """Revokes every refresh token of the token's user; an unverifiable token is a
        session GoTrue no longer knows, which is already the wanted state."""
        try:
            claims = jwt.decode(
                access_token, self._secret(), algorithms=list(HS_ALGORITHMS), audience=AUDIENCE
            )
        except jwt.PyJWTError:
            return
        self._revoke_sessions(UUID(str(claims.get("sub"))))

    def admin_delete_user(self, user_id: UUID) -> None:
        """``DELETE /auth/v1/admin/users/{id}``: the login and its sessions go; an unknown
        id is already the wanted state."""
        self.users.pop(user_id, None)
        self._revoke_sessions(user_id)

    def _revoke_sessions(self, user_id: UUID) -> None:
        for token in [t for t, owner in self.refresh_tokens.items() if owner == user_id]:
            del self.refresh_tokens[token]

    def _send(self, user: GoTrueUserRow, kind: str, redirect_to: str) -> None:
        if kind == "signup":
            user.confirmation_sent_at = self.now()
        else:
            user.recovery_sent_at = self.now()
        self.outbox.append(SentMail(kind=kind, email=user.email, redirect_to=redirect_to))

    def _secret(self) -> str:
        secret = self.settings.supabase_jwt_secret.get_secret_value()
        if not secret:
            raise ApiException(UNAUTHORIZED, message="Authentication is not configured.")
        return secret

    def _session(self, user: GoTrueUserRow) -> dict[str, Any]:
        secret = self._secret()
        now = self.now()
        claims: dict[str, Any] = {
            "sub": str(user.id),
            "aud": AUDIENCE,
            "email": user.email,
            "role": "authenticated",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=GOTRUE_ACCESS_TOKEN_SECONDS)).timestamp()),
        }
        base = self.settings.supabase_url.rstrip("/")
        if base:
            claims["iss"] = f"{base}/auth/v1"
        refresh_token = secrets.token_urlsafe(32)
        self.refresh_tokens[refresh_token] = user.id
        return {
            "access_token": jwt.encode(claims, secret, algorithm=HS_ALGORITHMS[0]),
            "token_type": "bearer",
            "expires_in": GOTRUE_ACCESS_TOKEN_SECONDS,
            "refresh_token": refresh_token,
            "user": user.as_record(),
        }


# --- store ------------------------------------------------------------------------------------


@dataclass
class MemoryStore:
    settings: Settings
    gotrue: MemoryGoTrue = field(init=False)
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
    account_deletions: dict[UUID, AccountDeletionRow] = field(default_factory=dict)
    job_feedback: dict[UUID, JobFeedbackRow] = field(default_factory=dict)
    nps_responses: list[NpsRow] = field(default_factory=list)
    plugin_installs: dict[tuple[UUID, str, str], PluginInstallRow] = field(default_factory=dict)
    _seq: int = 0
    _ledger_keys: dict[str, LedgerRow] = field(default_factory=dict)
    _job_entries: dict[tuple[UUID, str], LedgerRow] = field(default_factory=dict)
    _keys_by_hash: dict[str, ApiKeyRow] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.gotrue = MemoryGoTrue(self.settings, on_user_created=self.handle_new_user)
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

    def perishable_pool(self, user_id: UUID) -> int:
        """The balance held in credits that expire. Expiring credits are spent before
        non-expiring ones (§13), so a capture takes from the pool first and only the
        overflow touches permanent credits."""
        pool = 0
        for row in self.ledger:
            if row.user_id != user_id:
                continue
            if row.entry_type == "grant" and row.expires_at is not None:
                pool += row.amount
            elif row.entry_type == "expire" or (
                row.amount < 0 and row.entry_type in ("capture", "adjust")
            ):
                pool = max(pool + row.amount, 0)
        return pool

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
            # Grants expire in expires_at order, so this one is the head of the perishable
            # pool: every credit spent so far came off it, and what is left for it is the
            # pool minus the perishable grants queued behind it.
            behind = sum(
                g.amount
                for g in self.ledger
                if g.user_id == grant.user_id
                and g.entry_type == "grant"
                and g.expires_at is not None
                and (g.expires_at, g.seq) > (grant.expires_at, grant.seq)
                and f"expire:{g.id}" not in self._ledger_keys
            )
            pool = self.perishable_pool(grant.user_id)
            remaining = min(
                max(pool - behind, 0), grant.amount, account.balance - account.reserved
            )
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

    def user_jobs(self, user_id: UUID) -> list[JobRow]:
        """The user's jobs newest first, ties broken by id as the SQL keyset does."""
        rows = [job for job in self.jobs.values() if job.user_id == user_id]
        return sorted(rows, key=lambda job: (job.created_at, job.id), reverse=True)

    def jobs_page(
        self, user_id: UUID, limit: int, cursor: tuple[datetime, UUID] | None
    ) -> JobsPage:
        rows = [
            job.as_record()
            for job in self.user_jobs(user_id)
            if cursor is None or (job.created_at, job.id) < cursor
        ]
        return jobs_page(rows[: limit + 1], limit)

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

    def update_job_progress(
        self, job_id: UUID, stage: str | None, progress: float | None
    ) -> JobRow:
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

    def reap_stale_jobs(
        self, timeout_seconds: int, queued_timeout_seconds: int | None = None
    ) -> list[UUID]:
        """Fail and release jobs whose worker never finished — and jobs a worker never
        picked up. A message lost before ``start_job`` (crash, malformed body, dead-letter
        queue) would otherwise hold its reservation forever, permanently lowering the
        owner's usable balance. Queued jobs get the longer grace, since a queue backlog is
        not yet a failure."""
        if timeout_seconds <= 0:
            raise _invalid_argument("p_timeout_seconds must be positive")
        queued_timeout = (
            timeout_seconds * QUEUED_TIMEOUT_FACTOR
            if queued_timeout_seconds is None
            else queued_timeout_seconds
        )
        if queued_timeout <= 0:
            raise _invalid_argument("p_queued_timeout_seconds must be positive")
        now = self.now()
        running_cutoff = now - timedelta(seconds=timeout_seconds)
        queued_cutoff = now - timedelta(seconds=queued_timeout)
        stale = [
            job.id
            for job in self.jobs.values()
            if (job.status == "running" and (job.started_at or job.created_at) < running_cutoff)
            or (job.status == "queued" and job.created_at < queued_cutoff)
        ]
        for job_id in stale:
            seconds = timeout_seconds if self.jobs[job_id].status == "running" else queued_timeout
            self.fail_job(
                job_id,
                {
                    "code": "worker_timeout",
                    "message": f"no completion within {seconds} seconds",
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

    def handle_new_user(
        self, user_id: UUID, email: str, raw_user_meta_data: Mapping[str, Any]
    ) -> ProfileRow:
        """``handle_new_user`` of 0004: the profile, the account and the welcome grant of
        :meth:`ensure_user`, plus the sign-up metadata — the referral code only when it
        names an active code, spelled as that code is."""
        if user_id in self.profiles:
            return self.profiles[user_id]
        profile = self.ensure_user(user_id, email)
        wanted = signup_meta_text(raw_user_meta_data, "referral_code")
        code = self.referral_codes.get(wanted.lower()) if wanted else None
        profile.referral_code = code.code if code is not None and code.active else None
        for key in UTM_KEYS:
            setattr(profile, key, signup_meta_text(raw_user_meta_data, key))
        profile.marketing_opt_in = signup_meta_bool(raw_user_meta_data, "marketing_opt_in")
        profile.terms_accepted_at = signup_meta_timestamp(raw_user_meta_data, "terms_accepted_at")
        return profile

    def find_profile_by_email(self, email: str) -> ProfileRow | None:
        wanted = normalise_email(email)
        return next((p for p in self.profiles.values() if p.email == wanted), None)

    def mark_first_seen(self, user_id: UUID) -> ProfileRow | None:
        """The conditional ``update profiles set first_seen_at = now() where first_seen_at
        is null`` of the PostgREST backend: the row for the one call that stamped it."""
        profile = self.profiles.get(user_id)
        if profile is None or profile.deleted_at is not None or profile.first_seen_at is not None:
            return None
        profile.first_seen_at = self.now()
        return profile

    def delete_user_account(self, user_id: UUID) -> AccountDeletionRow:
        """``delete_user_account`` of 0004_account_deletion.sql: refuses while a job is
        queued or running, forfeits the remaining credits through the ledger, deletes the
        API keys, scrubs the jobs, keeps ledger, purchases and commissions, revokes the
        referral codes and tombstones the profile. A repeat returns the recorded row."""
        profile = self.profiles.get(user_id)
        if profile is None:
            raise _not_found(f"profile {user_id}")
        if profile.deleted_at is not None:
            return self.account_deletions[user_id]
        active = sum(
            1
            for job in self.jobs.values()
            if job.user_id == user_id and job.status in ACTIVE_JOB_STATUSES
        )
        if active:
            raise _conflict(f"{active} unfinished jobs")
        account = self.accounts.get(user_id)
        if account is not None and account.balance - account.reserved > 0:
            self.adjust_credits(
                user_id,
                -(account.balance - account.reserved),
                DELETION_SOURCE,
                deletion_idempotency_key(user_id),
                DELETION_NOTE,
            )
        for key_id in [k.id for k in self.api_keys.values() if k.user_id == user_id]:
            row = self.api_keys.pop(key_id)
            self._keys_by_hash.pop(row.key_hash, None)
        for job in self.jobs.values():
            if job.user_id == user_id:
                job.options = {}
                job.input_meta = {}
                job.result = None
                job.worker_ref = None
                job.idempotency_key = None
        for affiliate in self.affiliates.values():
            if affiliate.user_id == user_id:
                affiliate.active = False
                affiliate.payout_details = {}
                for code in self.referral_codes.values():
                    if code.affiliate_id == affiliate.id:
                        code.active = False
        # Free text is the person; the ratings and scores are the books (0005).
        for feedback in self.job_feedback.values():
            if feedback.user_id == user_id:
                feedback.note = None
        for answer in self.nps_responses:
            if answer.user_id == user_id:
                answer.comment = None
        for key in [k for k in self.plugin_installs if k[0] == user_id]:
            del self.plugin_installs[key]
        profile.email = tombstone_email(user_id)
        for key in UTM_KEYS:
            setattr(profile, key, None)
        profile.marketing_opt_in = False
        profile.deleted_at = self.now()
        deletion = AccountDeletionRow(
            user_id=user_id,
            requested_at=profile.deleted_at,
            ledger_rows_kept=sum(1 for row in self.ledger if row.user_id == user_id),
        )
        self.account_deletions[user_id] = deletion
        return deletion

    def export_account(self, user_id: UUID) -> AccountExport:
        profile = self.profiles.get(user_id)
        if profile is None:
            raise _not_found(f"profile {user_id}")
        affiliate: AffiliateExport | None = None
        row = next((a for a in self.affiliates.values() if a.user_id == user_id), None)
        if row is not None:
            affiliate = AffiliateExport(
                code=row.code,
                commission_rate=float(row.commission_rate),
                active=row.active,
                payout_details=dict(row.payout_details),
                created_at=row.created_at,
                referral_codes=[
                    ReferralCodeExport(
                        code=c.code, uses=c.uses, active=c.active, created_at=c.created_at
                    )
                    for c in self.referral_codes.values()
                    if c.affiliate_id == row.id
                ],
                commissions=[
                    CommissionExport(
                        id=c.id,
                        purchase_id=c.purchase_id,
                        rate=float(c.rate),
                        amount_cents=c.amount_cents,
                        status=c.status,
                        paid_at=c.paid_at,
                        created_at=c.created_at,
                    )
                    for c in self.commissions.values()
                    if c.affiliate_id == row.id
                ],
            )
        balance = self.get_balance(user_id)
        return AccountExport(
            exported_at=self.now(),
            user=exported_user_from_record(profile.as_record()),
            balance=Balance(
                **balance.model_dump(), subscription_renews_at=self.subscription_renews_at(user_id)
            ),
            ledger=[
                ledger_entry_from_record(r.as_record()) for r in self.ledger if r.user_id == user_id
            ],
            jobs=[
                without_signed_urls(job_status_from_record(job.as_record()))
                for job in self.user_jobs(user_id)
            ],
            purchases=[
                PurchaseExport.model_validate(p.model_dump(exclude={"user_id", "idempotency_key"}))
                for p in sorted(self.purchases.values(), key=lambda p: p.created_at)
                if p.user_id == user_id
            ],
            # SubscriptionRecord carries no created_at; the memory backend exports none.
            subscriptions=[
                SubscriptionExport.model_validate(sub.model_dump(exclude={"user_id"}))
                for sub in self.subscriptions.values()
                if sub.user_id == user_id
            ],
            api_keys=self.api_key_infos(user_id),
            affiliate=affiliate,
        )

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
            try:
                self.grant_credits(
                    user_id,
                    plan.credits,
                    f"{provider}:order:{provider_order_id}",
                    idempotency_key,
                    plan.name,
                )
            except Exception:
                del self.purchases[purchase.id]  # the SQL transaction rolls the insert back
                raise
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
            id=uuid4(),
            user_id=user_id,
            code=code,
            commission_rate=Decimal(str(commission_rate)),
            created_at=self.now(),
        )
        self.affiliates[affiliate.id] = affiliate
        self.referral_codes[code.lower()] = ReferralCodeRow(
            id=uuid4(), code=code, affiliate_id=affiliate.id, created_at=self.now()
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
        referral_code: str | None = None,
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
        # As in the PostgREST upsert: an event without a code leaves the stored one alone.
        if referral_code is not None:
            existing.referral_code = referral_code
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

    def find_purchase(
        self, provider: PurchaseProvider, provider_order_id: str
    ) -> PurchaseRecord | None:
        for purchase in self.purchases.values():
            if purchase.provider == provider and purchase.provider_order_id == provider_order_id:
                return purchase
        return None

    # --- quality loops (0005: feedback, auto-refund, NPS, plugin installs, status) --------------

    def _auto_refunds(self, user_id: UUID, since: datetime | None) -> int:
        return sum(
            1
            for row in self.ledger
            if row.user_id == user_id
            and row.entry_type == "refund"
            and (row.note or "").startswith(auto_refund_reason(None)[: -len("unspecified")])
            and (since is None or row.created_at >= since)
        )

    def refund_job_for_feedback(self, job_id: UUID, user_id: UUID, reason: str | None) -> bool:
        """``refund_job_for_feedback`` of 0005: the GTM §2.6 rule and its abuse bounds,
        decided under the account lock; ``True`` when the job's credit is (now) back."""
        job = self.jobs.get(job_id)
        if job is None or job.user_id != user_id:
            raise _not_found(f"job {job_id}")
        self._lock_account(user_id)
        if (job_id, "refund") in self._job_entries:
            return True
        now = self.now()
        if (
            job.status != "succeeded"
            or job.finished_at is None
            or job.finished_at < now - timedelta(hours=AUTO_REFUND_WINDOW_HOURS)
            or reason == "slow"
        ):
            return False
        since = now - timedelta(days=AUTO_REFUND_LOOKBACK_DAYS)
        captured = sum(
            1
            for row in self.ledger
            if row.user_id == user_id and row.entry_type == "capture" and row.created_at >= since
        )
        if self._auto_refunds(user_id, since) >= auto_refund_allowance(captured):
            return False
        never_purchased = not any(p.user_id == user_id for p in self.purchases.values())
        if never_purchased and self._auto_refunds(user_id, None) >= AUTO_REFUND_FREE_LIFETIME:
            return False
        self.refund_job(job_id, auto_refund_reason(reason))  # type: ignore[arg-type]
        return True

    def record_job_feedback(
        self,
        job_id: UUID,
        user_id: UUID,
        rating: str,
        reason: str | None,
        note: str | None,
        drop_to_ready_ms: int | None,
    ) -> JobFeedbackRow:
        """``record_job_feedback`` of 0005: one row per job, refreshed on every call; a
        thumbs-down runs :meth:`refund_job_for_feedback`."""
        if rating not in ("up", "down"):
            raise _invalid_argument("p_rating must be up or down")
        if reason is not None and reason not in FeedbackReason.__args__:  # type: ignore[attr-defined]
            raise _invalid_argument("p_reason is not a feedback reason")
        if note is not None and len(note) > FEEDBACK_NOTE_MAX_CHARS:
            raise _invalid_argument(f"p_note must be at most {FEEDBACK_NOTE_MAX_CHARS} characters")
        if drop_to_ready_ms is not None and drop_to_ready_ms < 0:
            raise _invalid_argument("p_drop_to_ready_ms must not be negative")
        job = self.jobs.get(job_id)
        if job is None or job.user_id != user_id:
            raise _not_found(f"job {job_id}")
        if job.status in ACTIVE_JOB_STATUSES:
            raise _conflict(f"job is {job.status}")
        now = self.now()
        row = self.job_feedback.get(job_id)
        if row is None:
            row = JobFeedbackRow(
                job_id=job_id,
                user_id=user_id,
                rating=rating,
                reason=reason,
                note=note,
                drop_to_ready_ms=drop_to_ready_ms,
                created_at=now,
                updated_at=now,
            )
            self.job_feedback[job_id] = row
        else:
            row.rating = rating
            row.reason = reason
            row.note = note
            if drop_to_ready_ms is not None:
                row.drop_to_ready_ms = drop_to_ready_ms
            row.updated_at = now
        if rating == "down" and self.refund_job_for_feedback(job_id, user_id, reason):
            row.refunded = True
        return row

    def submit_nps(self, user_id: UUID, score: int, comment: str | None) -> NpsRow:
        """``submit_nps`` of 0005: one answer per user per 30 days."""
        if not 0 <= score <= 10:
            raise _invalid_argument("p_score must be between 0 and 10")
        if comment is not None and len(comment) > NPS_COMMENT_MAX_CHARS:
            raise _invalid_argument(f"p_comment must be at most {NPS_COMMENT_MAX_CHARS} characters")
        if user_id not in self.profiles:
            raise _not_found(f"profile {user_id}")
        now = self.now()
        cooldown = now - timedelta(days=NPS_COOLDOWN_DAYS)
        if any(r.user_id == user_id and r.created_at >= cooldown for r in self.nps_responses):
            raise _conflict("nps answered within 30 days")
        row = NpsRow(id=uuid4(), user_id=user_id, score=score, comment=comment, created_at=now)
        self.nps_responses.append(row)
        return row

    def touch_plugin_install(
        self, user_id: UUID, plugin_version: str, host: str, os: str | None
    ) -> bool:
        """``touch_plugin_install`` of 0005: ``True`` for a new ``(version, host)`` pair."""
        if not plugin_version or len(plugin_version) > PLUGIN_VERSION_MAX_CHARS:
            raise _invalid_argument("p_plugin_version is required")
        if not host or len(host) > PLUGIN_IDENTITY_MAX_CHARS:
            raise _invalid_argument("p_host is required")
        if os is not None and len(os) > PLUGIN_IDENTITY_MAX_CHARS:
            raise _invalid_argument("p_os is too long")
        if user_id not in self.profiles:
            raise _not_found(f"profile {user_id}")
        key = (user_id, plugin_version, host)
        now = self.now()
        existing = self.plugin_installs.get(key)
        if existing is not None:
            existing.last_seen_at = now
            existing.os = os or existing.os
            return False
        self.plugin_installs[key] = PluginInstallRow(
            user_id=user_id,
            plugin_version=plugin_version,
            host=host,
            os=os,
            first_seen_at=now,
            last_seen_at=now,
        )
        return True

    def user_facts(self, user_id: UUID) -> UserFacts | None:
        """``user_facts`` of 0005."""
        profile = self.profiles.get(user_id)
        if profile is None:
            return None
        finished = sorted(
            job.finished_at
            for job in self.jobs.values()
            if job.user_id == user_id and job.status == "succeeded" and job.finished_at is not None
        )
        return UserFacts(
            email=profile.email,
            plan=profile.plan,
            morphs_total=len(finished),
            first_morph_at=finished[0] if finished else None,
            last_morph_at=finished[-1] if finished else None,
            has_purchased=any(p.user_id == user_id for p in self.purchases.values()),
        )

    def status_last_24h(self) -> Last24hStats:
        """``status_last_24h()`` of 0005 over the jobs that finished in the window."""
        since = self.now() - timedelta(hours=24)
        finished = [
            job
            for job in self.jobs.values()
            if job.finished_at is not None
            and job.finished_at >= since
            and job.status in ("succeeded", "failed")
        ]
        latencies = [
            float(elapsed_ms(job.started_at, job.created_at, job.finished_at))
            for job in finished
            if job.status == "succeeded" and job.finished_at is not None
        ]
        p50, p95 = percentile(latencies, 0.5), percentile(latencies, 0.95)
        return Last24hStats(
            morphs=len(finished),
            succeeded=sum(1 for job in finished if job.status == "succeeded"),
            failed=sum(1 for job in finished if job.status == "failed"),
            p50_ms=int(round(p50)) if p50 is not None else None,
            p95_ms=int(round(p95)) if p95 is not None else None,
        )

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

    def api_key_infos(self, user_id: UUID) -> list[ApiKeyInfo]:
        rows = sorted(
            (k for k in self.api_keys.values() if k.user_id == user_id),
            key=lambda k: (k.created_at, k.id),
            reverse=True,
        )
        return [
            ApiKeyInfo(
                id=k.id,
                name=k.name,
                prefix=k.prefix,
                created_at=k.created_at,
                last_used_at=k.last_used_at,
                revoked_at=k.revoked_at,
            )
            for k in rows
        ]

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
        """``claim_webhook_event`` of 0002_functions.sql, rule for rule.

        An event is claimed once; a row that failed to apply (``error`` set) stays
        claimable so the provider's retry runs it instead of getting ``duplicate``, and a
        claim older than ``WEBHOOK_CLAIM_LEASE_SECONDS`` that was never closed at all is
        taken over — its holder was killed mid-apply, and without this the paid event is
        answered ``duplicate`` forever.

        Where the SQL takes the row ``for update`` before deciding, this method decides
        and re-stamps ``received_at`` without awaiting: no other task can observe or
        change the row in between, so two reclaims of the same stale event cannot both
        win here either.
        """
        existing = self.webhook_events.get(idempotency_key)
        if existing is not None:
            if existing.error is not None:
                return True
            lease = timedelta(seconds=self.settings.webhook_claim_lease_seconds)
            if existing.processed_at is not None or existing.received_at > self.now() - lease:
                return False
            existing.received_at = self.now()
            return True
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


class MemoryAuthService:
    """The ``auth_*`` calls of :class:`SupabaseClient` over :class:`MemoryGoTrue`."""

    def __init__(self, gotrue: MemoryGoTrue) -> None:
        self._gotrue = gotrue

    async def auth_grant(self, grant_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if grant_type == "password":
            return self._gotrue.password_grant(
                str(payload.get("email") or ""), str(payload.get("password") or "")
            )
        if grant_type == "refresh_token":
            return self._gotrue.refresh_grant(str(payload.get("refresh_token") or ""))
        raise ApiException(UNAUTHORIZED, message=INVALID_CREDENTIALS_MESSAGE)

    async def auth_signup(self, email: str, password: str, *, redirect_to: str) -> dict[str, Any]:
        return self._gotrue.signup(email, password, redirect_to=redirect_to)

    async def auth_recover(self, email: str, *, redirect_to: str) -> None:
        self._gotrue.recover(email, redirect_to=redirect_to)

    async def auth_resend(self, email: str, kind: str, *, redirect_to: str) -> None:
        self._gotrue.resend(email, kind, redirect_to=redirect_to)

    async def auth_logout(self, access_token: str) -> None:
        self._gotrue.logout(access_token)


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
        on_finished: JobFinishedHook | None = None,
    ) -> None:
        self._store = store
        self._bus = bus
        self._events_mode: EventsMode = events_mode
        self._poll_interval = poll_interval
        self._on_finished = on_finished

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

    async def list(self, user_id: UUID, limit: int = 20, cursor: str | None = None) -> JobsPage:
        return self._store.jobs_page(user_id, limit, parse_job_cursor(cursor))

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
        notify_finished(self._on_finished, status, row.user_id)
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

    async def delete_prefix(self, prefix: str) -> int:
        doomed = [path for path in self.objects if path.startswith(prefix)]
        for path in doomed:
            del self.objects[path]
        return len(doomed)


class MemoryUsersService:
    def __init__(self, store: MemoryStore, *, growth: GrowthHooks | None = None) -> None:
        self._store = store
        self._growth = growth

    async def get(self, user_id: UUID) -> Profile | None:
        row = self._store.profiles.get(user_id)
        return profile_from_record(row.as_record()) if row else None

    async def find_by_email(self, email: str) -> Profile | None:
        row = self._store.find_profile_by_email(email)
        return profile_from_record(row.as_record()) if row else None

    async def ensure(self, user_id: UUID, email: str) -> Profile:
        created = user_id not in self._store.profiles
        row = self._store.ensure_user(user_id, email)
        if row.first_seen_at is None and row.deleted_at is None:
            await self.first_sight(user_id, "plugin" if created else "web")
        return profile_from_record(row.as_record())

    async def first_sight(self, user_id: UUID, source: str) -> bool:
        row = self._store.mark_first_seen(user_id)
        if row is None:
            return False
        if self._growth is not None:
            self._growth.signed_up(SignupFacts.from_record(row.as_record()), source)  # type: ignore[arg-type]
        return True

    async def set_plan(self, user_id: UUID, plan: PlanKind, renews_at: datetime | None) -> Profile:
        return profile_from_record(self._store.set_plan(user_id, plan, renews_at).as_record())

    async def export(self, user_id: UUID) -> AccountExport:
        return self._store.export_account(user_id)

    async def delete_account(self, user_id: UUID) -> None:
        try:
            self._store.delete_user_account(user_id)
        except ApiException as exc:
            if exc.code == CONFLICT:
                raise ApiException(CONFLICT, message=UNFINISHED_JOBS_MESSAGE) from exc
            raise
        self._store.gotrue.admin_delete_user(user_id)


class MemoryApiKeysService:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    async def create(self, user_id: UUID, name: str) -> ApiKeyCreateResponse:
        row, plaintext = self._store.create_api_key(user_id, name)
        return ApiKeyCreateResponse(
            id=row.id, name=name, prefix=row.prefix, key=plaintext, created_at=row.created_at
        )

    async def list(self, user_id: UUID) -> list[ApiKeyInfo]:
        return self._store.api_key_infos(user_id)

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
        referral_code: str | None,
        raw: dict[str, Any],
    ) -> SubscriptionRecord:
        del raw  # the memory backend keeps no provider payloads
        return self._store.upsert_subscription(
            user_id,
            provider,
            provider_subscription_id,
            plan_id,
            status,
            current_period_end,
            cancelled_at,
            referral_code,
        )

    async def find_subscription(
        self, provider: PurchaseProvider, provider_subscription_id: str
    ) -> SubscriptionRecord | None:
        return self._store.find_subscription(provider, provider_subscription_id)

    async def find_purchase(
        self, provider: PurchaseProvider, provider_order_id: str
    ) -> PurchaseRecord | None:
        return self._store.find_purchase(provider, provider_order_id)


class MemoryQualityService:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    async def record_feedback(
        self, job_id: UUID, user_id: UUID, feedback: JobFeedbackRequest
    ) -> FeedbackRecord:
        row = self._store.record_job_feedback(
            job_id,
            user_id,
            feedback.rating,
            feedback.reason,
            feedback.note,
            feedback.drop_to_ready_ms,
        )
        return FeedbackRecord.model_validate(row.as_record())

    async def submit_nps(self, user_id: UUID, score: int, comment: str | None) -> NpsRecord:
        return NpsRecord.model_validate(self._store.submit_nps(user_id, score, comment).as_record())

    async def touch_plugin_install(
        self, user_id: UUID, plugin_version: str, host: str, os: str | None
    ) -> bool:
        return self._store.touch_plugin_install(user_id, plugin_version, host, os)

    async def user_facts(self, user_id: UUID) -> UserFacts | None:
        return self._store.user_facts(user_id)

    async def status_last_24h(self) -> Last24hStats:
        return self._store.status_last_24h()


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
    "ACTIVE_JOB_STATUSES",
    "DELETION_NOTE",
    "DELETION_SOURCE",
    "LEMONSQUEEZY_TEMPLATE",
    "AccountDeletionRow",
    "AffiliateRow",
    "ApiKeyRow",
    "CommissionRow",
    "GoTrueUserRow",
    "JobFeedbackRow",
    "JobRow",
    "LedgerRow",
    "MemoryApiKeysService",
    "MemoryAuthService",
    "MemoryCreditsService",
    "MemoryGoTrue",
    "MemoryJobsService",
    "MemoryPlansService",
    "MemoryPurchasesService",
    "MemoryQualityService",
    "MemoryStorageService",
    "MemoryStore",
    "MemoryUsersService",
    "MemoryWebhookEventsService",
    "NpsRow",
    "PluginInstallRow",
    "ProfileRow",
    "ReferralCodeRow",
    "SentMail",
    "WebhookEventRow",
    "deletion_idempotency_key",
    "seed_plans",
    "signup_meta_bool",
    "signup_meta_text",
    "signup_meta_timestamp",
    "tombstone_email",
]
