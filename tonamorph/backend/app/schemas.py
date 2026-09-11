"""Pydantic models mirroring docs/API_CONTRACT.md payloads (§1–§3, §5, §7, §11).

Field names and JSON shapes are the contract; do not rename without updating the
contract and every other component.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

StemName = Literal["bass", "drums", "other", "vocals"]
ALL_STEMS: tuple[StemName, ...] = ("bass", "drums", "other", "vocals")
DEFAULT_TRANSCRIBE: tuple[StemName, ...] = ("bass", "other", "vocals")

PlanKind = Literal["free", "credits", "subscription"]
JobState = Literal["queued", "running", "succeeded", "failed", "cancelled"]
JobStage = Literal["upload", "separate", "transcribe", "analyze", "package", "done"]
KeyMode = Literal["major", "minor"]
LedgerEntryType = Literal["grant", "reserve", "capture", "release", "refund", "expire", "adjust"]
PlanInterval = Literal["month", "year"]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- §1 Authentication -------------------------------------------------------------


class TokenRequest(ContractModel):
    email: str
    password: str


class RefreshRequest(ContractModel):
    refresh_token: str


class AuthUser(ContractModel):
    id: UUID
    email: str


class TokenResponse(ContractModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: Literal["bearer"] = "bearer"
    user: AuthUser


class AuthSession(ContractModel):
    """The tokens of ``TokenResponse`` without the user, for responses that carry the
    user separately."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: Literal["bearer"] = "bearer"


MAX_EMAIL_LENGTH = 254
"""RFC 5321 path limit; longer strings are not addresses and never reach GoTrue."""


def email_address(value: str) -> str:
    """Strip and shape-check an address (``local@domain``); GoTrue normalises the rest."""
    cleaned = value.strip()
    local, at, domain = cleaned.partition("@")
    if not at or not local or not domain or len(cleaned) > MAX_EMAIL_LENGTH:
        raise ValueError("must be an email address")
    return cleaned


class SignupRequest(ContractModel):
    email: str
    password: str = Field(min_length=1, max_length=256)

    _email = field_validator("email")(email_address)


class RecoverRequest(ContractModel):
    email: str

    _email = field_validator("email")(email_address)


class ResendRequest(ContractModel):
    email: str
    type: Literal["signup"] = "signup"

    _email = field_validator("email")(email_address)


SignupStatus = Literal["confirmation_pending", "session"]


class SignupResponse(ContractModel):
    """``session`` is set only when GoTrue issued one, i.e. email confirmation is disabled
    for the project; otherwise the account waits for the confirmation link."""

    status: SignupStatus
    user: AuthUser
    session: AuthSession | None = None


class AuthAck(ContractModel):
    status: Literal["ok"] = "ok"


class MeUser(ContractModel):
    """``referral_code`` is the code the account signed up with (an active
    ``referral_codes`` row at the time), ``marketing_opt_in`` the consent given then."""

    id: UUID
    email: str
    plan: PlanKind
    marketing_opt_in: bool = False
    referral_code: str | None = None


class CreditBalance(ContractModel):
    """The ``credit_balance`` composite type (§6); ``available = credits - reserved``."""

    credits: int
    reserved: int
    available: int


class Balance(CreditBalance):
    subscription_renews_at: datetime | None = None


class MeResponse(ContractModel):
    user: MeUser
    balance: Balance


class Profile(MeUser):
    """A ``profiles`` row as the services return it: the §1 user plus the deletion
    tombstone (`deleted_at`), which no response carries — a tombstoned profile is
    refused at authentication (§1 account deletion)."""

    deleted_at: datetime | None = None


class DeleteAccountRequest(ContractModel):
    """``confirm`` must equal the session's email address (case-insensitive)."""

    confirm: str = Field(min_length=1, max_length=MAX_EMAIL_LENGTH)


class DeleteAccountResponse(ContractModel):
    status: Literal["deleted"] = "deleted"


# --- §2 Jobs ---------------------------------------------------------------------------


class JobOptions(ContractModel):
    """The ``options`` multipart field of ``POST /v1/jobs``; every key is optional."""

    client_sample_rate: int | None = Field(default=None, gt=0)
    stems: list[StemName] = Field(default_factory=lambda: list(ALL_STEMS), min_length=1)
    transcribe: list[StemName] = Field(default_factory=lambda: list(DEFAULT_TRANSCRIBE))
    drum_slices: bool = True
    target_root_midi: int = Field(default=48, ge=0, le=127)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("stems", "transcribe")
    @classmethod
    def _unique(cls, value: list[StemName]) -> list[StemName]:
        seen: list[StemName] = []
        for stem in value:
            if stem not in seen:
                seen.append(stem)
        return seen


class JobSubmitResponse(ContractModel):
    job_id: UUID
    status: Literal["queued"] = "queued"
    credits_reserved: int
    balance: CreditBalance


class JobError(ContractModel):
    code: str
    message: str


class ProgressEvent(ContractModel):
    """Payload of the SSE/WS ``progress`` event."""

    stage: JobStage
    progress: float = Field(ge=0.0, le=1.0)


class InputInfo(ContractModel):
    duration_seconds: float
    sample_rate: int
    channels: int
    truncated: bool


class KeyInfo(ContractModel):
    root: str
    mode: KeyMode
    root_midi: int = Field(ge=0, le=127)
    confidence: float = Field(ge=0.0, le=1.0)
    scale_pitch_classes: list[int]


class Analysis(ContractModel):
    bpm: float
    bpm_confidence: float = Field(ge=0.0, le=1.0)
    key: KeyInfo
    downbeats_seconds: list[float]
    beats_seconds: list[float]


class Adsr(ContractModel):
    attack_ms: float
    decay_ms: float
    sustain: float = Field(ge=0.0, le=1.0)
    release_ms: float


class Slice(ContractModel):
    start_seconds: float
    end_seconds: float
    midi_note: int = Field(ge=0, le=127)


class StemResult(ContractModel):
    """One stem. ``url`` is filled by the API layer after upload; ``wav_bytes`` is the
    encoded WAV produced by the pipeline and is never serialised. ``slices`` is only
    emitted for ``drums`` when ``drum_slices`` was requested."""

    name: StemName
    url: str | None = None
    format: Literal["wav"] = "wav"
    sample_rate: int
    channels: int
    duration_seconds: float
    root_midi: int | None = Field(default=None, ge=0, le=127)
    root_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    peak_db: float
    rms_db: float
    transients_seconds: list[float]
    suggested_adsr: Adsr | None = None
    slices: list[Slice] | None = Field(default=None, exclude_if=lambda v: v is None)
    wav_bytes: bytes | None = Field(default=None, exclude=True, repr=False)


class MidiNote(ContractModel):
    start_seconds: float
    duration_seconds: float
    start_ticks: int
    duration_ticks: int
    pitch: int = Field(ge=0, le=127)
    velocity: int = Field(ge=1, le=127)


class MidiTrack(ContractModel):
    name: str
    channel: int = Field(ge=0, le=15)
    notes: list[MidiNote]


class MidiInfo(ContractModel):
    """The ``midi`` block of JobResult. ``smf_bytes`` is the Standard MIDI File produced
    by the pipeline and is never serialised; ``url`` is set after upload."""

    url: str | None = None
    ppq: int = 480
    bpm: float
    tracks: list[MidiTrack]
    smf_bytes: bytes | None = Field(default=None, exclude=True, repr=False)


MidiResult = MidiInfo


class JobResult(ContractModel):
    job_id: UUID
    credits_charged: int
    balance_after: int
    input: InputInfo
    analysis: Analysis
    stems: list[StemResult]
    midi: MidiInfo
    expires_at: datetime


class JobStatus(ContractModel):
    job_id: UUID
    status: JobState
    stage: JobStage
    progress: float = Field(ge=0.0, le=1.0)
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: JobError | None = None
    result: JobResult | None = None


class JobsPage(ContractModel):
    """``GET /v1/jobs``: newest first; ``next_cursor`` is opaque (``jobs.encode_job_cursor``)."""

    jobs: list[JobStatus]
    next_cursor: str | None = None


# --- §3 Credits and plans ---------------------------------------------------------------


class LedgerEntry(ContractModel):
    id: UUID
    created_at: datetime
    entry_type: LedgerEntryType
    amount: int
    balance_after: int
    job_id: UUID | None = None
    source: str | None = None
    note: str | None = None


class LedgerPage(ContractModel):
    entries: list[LedgerEntry]
    next_cursor: str | None = None


class PlanInfo(ContractModel):
    id: str
    name: str
    credits: int
    price_usd: float
    interval: PlanInterval | None = None
    checkout_url: str | None = None


class PlansResponse(ContractModel):
    plans: list[PlanInfo]


# --- §4 Webhooks ---------------------------------------------------------------------------


class WebhookAck(ContractModel):
    status: Literal["ok", "duplicate"]


# --- §5 Errors ----------------------------------------------------------------------------


class ErrorBody(ContractModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorEnvelope(ContractModel):
    error: ErrorBody


# --- §7 Pipeline interface -------------------------------------------------------------


class PipelineOptions(ContractModel):
    stems: list[StemName] = Field(default_factory=lambda: list(ALL_STEMS), min_length=1)
    transcribe: list[StemName] = Field(default_factory=lambda: list(DEFAULT_TRANSCRIBE))
    drum_slices: bool = True
    target_root_midi: int = Field(default=48, ge=0, le=127)
    max_seconds: float = Field(default=60.0, gt=0)

    @classmethod
    def from_job_options(cls, options: JobOptions, max_seconds: float) -> PipelineOptions:
        return cls(
            stems=options.stems,
            transcribe=options.transcribe,
            drum_slices=options.drum_slices,
            target_root_midi=options.target_root_midi,
            max_seconds=max_seconds,
        )


class PipelineResult(ContractModel):
    """JobResult minus job_id/credits/urls; stems carry ``wav_bytes`` and ``midi`` carries
    ``smf_bytes`` until the API layer uploads them and fills the URLs."""

    input: InputInfo
    analysis: Analysis
    stems: list[StemResult]
    midi: MidiInfo


# --- §11 API keys ------------------------------------------------------------------------


class ApiKeyCreateRequest(ContractModel):
    name: str = Field(default="default", min_length=1, max_length=64)


class ApiKeyCreateResponse(ContractModel):
    """Returned exactly once; ``key`` is the plaintext ``tm_live_<32 chars>``."""

    id: UUID
    name: str
    prefix: str
    key: str
    created_at: datetime


class ApiKeyInfo(ContractModel):
    """What ``api_keys`` stores besides the hash: never the secret or its digest."""

    id: UUID
    name: str | None = None
    prefix: str
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


class ApiKeysResponse(ContractModel):
    keys: list[ApiKeyInfo]


# --- §1 Account export (GDPR Art. 15 / Art. 20) ---------------------------------------------


class PurchaseExport(ContractModel):
    id: UUID
    provider: str
    provider_order_id: str
    plan_id: str | None = None
    credits: int
    amount_cents: int
    net_cents: int
    currency: str
    referral_code: str | None = None
    created_at: datetime


class SubscriptionExport(ContractModel):
    id: UUID
    provider: str
    provider_subscription_id: str
    plan_id: str | None = None
    status: str
    current_period_end: datetime | None = None
    cancelled_at: datetime | None = None
    referral_code: str | None = None
    created_at: datetime | None = None


class ReferralCodeExport(ContractModel):
    code: str
    uses: int
    active: bool
    created_at: datetime


class CommissionExport(ContractModel):
    id: UUID
    purchase_id: UUID
    rate: float
    amount_cents: int
    status: str
    paid_at: datetime | None = None
    created_at: datetime


class AffiliateExport(ContractModel):
    code: str
    commission_rate: float
    active: bool
    payout_details: dict[str, Any]
    created_at: datetime
    referral_codes: list[ReferralCodeExport]
    commissions: list[CommissionExport]


class ExportedUser(MeUser):
    created_at: datetime
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_content: str | None = None
    utm_term: str | None = None
    terms_accepted_at: datetime | None = None


class AccountExport(ContractModel):
    """Everything the service holds about one user. Job results keep their analysis but
    carry no signed URLs; audio itself is never retained beyond 24 h (docs/SECURITY.md)."""

    exported_at: datetime
    user: ExportedUser
    balance: Balance
    ledger: list[LedgerEntry]
    jobs: list[JobStatus]
    purchases: list[PurchaseExport]
    subscriptions: list[SubscriptionExport]
    api_keys: list[ApiKeyInfo]
    affiliate: AffiliateExport | None = None


# --- Health --------------------------------------------------------------------------------


class HealthResponse(ContractModel):
    status: Literal["ok"] = "ok"
