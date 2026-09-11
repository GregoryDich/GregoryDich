"""Wiring of the service implementations selected by :class:`Settings` (§7, §10).

Data backend: in-memory when ``ENV=test`` or ``SUPABASE_URL`` is unset, PostgREST
otherwise. Storage follows ``STORAGE_BACKEND``; dispatch follows ``TONAMORPH_PIPELINE``.
The AWS implementations are imported lazily so the package stays importable without
the aws subpackage's dependencies on the other paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.auth.jwt import JwtVerifier
from app.config import Settings
from app.services import (
    ApiKeysService,
    CreditsService,
    DispatchService,
    JobsService,
    StorageService,
    UsersService,
    WebhookEventsService,
)
from app.services.api_keys import SupabaseApiKeysService
from app.services.credits import SupabaseCreditsService
from app.services.dispatch import LocalDispatch, ModalDispatch, RunPodDispatch
from app.services.events import JobEventBus
from app.services.jobs import EventsMode, SupabaseJobsService
from app.services.memory import (
    MemoryApiKeysService,
    MemoryCreditsService,
    MemoryJobsService,
    MemoryPlansService,
    MemoryPurchasesService,
    MemoryStorageService,
    MemoryStore,
    MemoryUsersService,
    MemoryWebhookEventsService,
)
from app.services.plans import PlansService, SupabasePlansService
from app.services.storage import SupabaseStorageService
from app.services.supabase import SupabaseClient
from app.services.users import SupabaseUsersService
from app.services.webhooks import (
    PurchasesService,
    SupabasePurchasesService,
    SupabaseWebhookEventsService,
)

DataBackend = Literal["memory", "supabase"]
LOCAL_PIPELINES: frozenset[str] = frozenset({"fake", "local"})


def data_backend(settings: Settings) -> DataBackend:
    if settings.env == "test" or not settings.supabase_url:
        return "memory"
    return "supabase"


def events_mode(settings: Settings) -> EventsMode:
    """In-process bus when the pipeline runs inside the API, DB polling otherwise."""
    return "bus" if settings.tonamorph_pipeline in LOCAL_PIPELINES else "poll"


@dataclass
class Services:
    settings: Settings
    jwt: JwtVerifier
    bus: JobEventBus
    supabase: SupabaseClient | None
    memory: MemoryStore | None
    credits: CreditsService
    jobs: JobsService
    storage: StorageService
    users: UsersService
    api_keys: ApiKeysService
    webhook_events: WebhookEventsService
    purchases: PurchasesService
    plans: PlansService
    dispatch: DispatchService

    async def aclose(self) -> None:
        closer = getattr(self.dispatch, "aclose", None)
        if closer is not None:
            await closer()
        if self.supabase is not None:
            await self.supabase.aclose()


def build_storage(settings: Settings, client: SupabaseClient | None) -> StorageService:
    backend = settings.storage_backend
    if backend == "memory":
        return MemoryStorageService()
    if backend == "supabase":
        if client is None:
            raise RuntimeError("STORAGE_BACKEND=supabase requires SUPABASE_URL")
        return SupabaseStorageService(client, settings.storage_bucket)
    from app.services.aws.storage import S3StorageService

    return S3StorageService(settings)


def build_dispatch(
    settings: Settings, *, jobs: JobsService, storage: StorageService, credits: CreditsService
) -> DispatchService:
    pipeline = settings.tonamorph_pipeline
    if pipeline in LOCAL_PIPELINES:
        return LocalDispatch(settings, jobs=jobs, storage=storage, credits=credits)
    if pipeline == "modal":
        return ModalDispatch(settings)
    if pipeline == "runpod":
        return RunPodDispatch(settings)
    from app.services.aws.queue import SqsDispatch

    return SqsDispatch(settings)


def build_services(settings: Settings) -> Services:
    bus = JobEventBus()
    client = SupabaseClient(settings) if settings.supabase_url else None
    mode = events_mode(settings)
    store: MemoryStore | None = None
    if data_backend(settings) == "memory":
        store = MemoryStore(settings)
        credits: CreditsService = MemoryCreditsService(store)
        jobs: JobsService = MemoryJobsService(store, bus, events_mode=mode)
        users: UsersService = MemoryUsersService(store)
        api_keys: ApiKeysService = MemoryApiKeysService(store)
        webhook_events: WebhookEventsService = MemoryWebhookEventsService(store)
        purchases: PurchasesService = MemoryPurchasesService(store)
        plans: PlansService = MemoryPlansService(store)
    else:
        assert client is not None
        credits = SupabaseCreditsService(client)
        jobs = SupabaseJobsService(client, bus, events_mode=mode)
        users = SupabaseUsersService(client, settings)
        api_keys = SupabaseApiKeysService(client)
        webhook_events = SupabaseWebhookEventsService(
            client, settings.webhook_claim_lease_seconds
        )
        purchases = SupabasePurchasesService(client)
        plans = SupabasePlansService(client)
    storage = build_storage(settings, client)
    dispatch = build_dispatch(settings, jobs=jobs, storage=storage, credits=credits)
    return Services(
        settings=settings,
        jwt=JwtVerifier(settings),
        bus=bus,
        supabase=client,
        memory=store,
        credits=credits,
        jobs=jobs,
        storage=storage,
        users=users,
        api_keys=api_keys,
        webhook_events=webhook_events,
        purchases=purchases,
        plans=plans,
        dispatch=dispatch,
    )


__all__ = [
    "LOCAL_PIPELINES",
    "DataBackend",
    "Services",
    "build_dispatch",
    "build_services",
    "build_storage",
    "data_backend",
    "events_mode",
]
