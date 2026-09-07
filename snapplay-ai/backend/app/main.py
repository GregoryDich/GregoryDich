"""Application factory: ``uvicorn app.main:create_app --factory`` (or ``app.main:app``)."""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import Settings, get_settings
from app.errors import install_exception_handlers
from app.middleware.rate_limit import RateLimits
from app.routers import api_keys, auth, credits, health, jobs, me, plans, webhooks
from app.services.factory import build_services

API_PREFIX = "/v1"
REQUEST_ID_HEADER = "x-request-id"
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
request_log = logging.getLogger("snapplay.request")

_STANDARD_RECORD_KEYS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message",
    "asctime",
}


class JsonFormatter(logging.Formatter):
    """One JSON object per line; ``extra=`` fields are merged in, request id is implicit."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        request_id = request_id_var.get()
        if request_id:
            payload["request_id"] = request_id
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_KEYS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(settings: Settings) -> None:
    root = logging.getLogger()
    if not any(isinstance(h.formatter, JsonFormatter) for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
    root.setLevel(logging.DEBUG if settings.env == "development" else logging.INFO)
    logging.getLogger("uvicorn.access").disabled = True
    # sse-starlette logs every chunk it sends at DEBUG, which under ENV=development
    # would put whole JobResult bodies -- including signed stem and MIDI URLs -- into
    # the log. docs/SECURITY.md requires that response bodies never reach logs.
    logging.getLogger("sse_starlette.sse").setLevel(logging.INFO)


class RequestContextMiddleware:
    """Assigns/propagates ``X-Request-ID`` and writes one structured access-log line per
    HTTP request (method, path, status, duration; never headers or bodies)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = Headers(scope=scope).get(REQUEST_ID_HEADER, "")
        request_id = incoming if _REQUEST_ID_RE.match(incoming) else uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message).append(REQUEST_ID_HEADER, request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            request_log.info(
                "request",
                extra={
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            request_id_var.reset(token)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        await app.state.services.aclose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="SnapPlay AI API",
        version="2",
        docs_url="/docs" if settings.env != "production" else None,
        redoc_url=None,
        lifespan=_lifespan,
    )
    app.state.settings = settings
    app.state.services = build_services(settings)
    app.state.rate_limits = RateLimits(settings)
    app.dependency_overrides[get_settings] = lambda: settings

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials="*" not in settings.cors_allow_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "Retry-After", "X-RateLimit-Remaining"],
    )
    install_exception_handlers(app)

    app.include_router(health.router)
    for router in (
        health.router,
        auth.router,
        me.router,
        jobs.router,
        credits.router,
        plans.router,
        api_keys.router,
        webhooks.router,
    ):
        app.include_router(router, prefix=API_PREFIX)
    return app


app = create_app()
