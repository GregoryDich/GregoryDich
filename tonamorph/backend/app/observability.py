"""Error reporting (Sentry), enabled only when ``SENTRY_DSN`` is set.

docs/SECURITY.md forbids request bodies, headers and tokens in any log; the same rule
applies to error reports, so every event is scrubbed before it leaves the process and
performance tracing stays off. Both the API and the GPU workers call :func:`init_sentry`
once at start-up; the ``role`` tag tells the two apart in one Sentry project, and the
plugin's opt-in crash reports (§14) arrive through the API under ``role=plugin``.
"""

from __future__ import annotations

import logging
import os
from typing import Any
from uuid import UUID

from app.config import Settings
from app.schemas import CrashReport

log = logging.getLogger("tonamorph.observability")

RELEASE_ENV = "TONAMORPH_RELEASE"
_SCRUBBED_REQUEST_KEYS = ("headers", "cookies", "data", "query_string")
PLUGIN_ROLE = "plugin"
BACKTRACE_ATTACHMENT = "backtrace.txt"
_FINGERPRINT_LINE_CHARS = 200


def scrub_event(event: dict[str, Any], _hint: dict[str, Any] | None = None) -> dict[str, Any]:
    """Drops everything that could carry a credential or user audio metadata: request
    headers, cookies, bodies and query strings, plus the user block except its id."""
    request = event.get("request")
    if isinstance(request, dict):
        for key in _SCRUBBED_REQUEST_KEYS:
            request.pop(key, None)
    user = event.get("user")
    if isinstance(user, dict):
        event["user"] = {"id": user["id"]} if "id" in user else {}
    return event


def init_sentry(settings: Settings, *, role: str, **overrides: Any) -> bool:
    """Initialises the SDK when a DSN is configured; returns whether reporting is on.
    ``overrides`` reach ``sentry_sdk.init`` (tests pass a capturing transport)."""
    if not settings.sentry_dsn:
        return False
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.env,
        release=os.environ.get(RELEASE_ENV) or None,
        send_default_pii=False,
        max_request_body_size="never",
        traces_sample_rate=0.0,
        profiles_sample_rate=0.0,
        before_send=scrub_event,
        **overrides,
    )
    sentry_sdk.set_tag("role", role)
    log.info("error reporting enabled", extra={"role": role, "environment": settings.env})
    return True


def first_backtrace_line(backtrace: str) -> str:
    """The first non-blank line, bounded: the crash's own words for grouping."""
    for line in backtrace.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:_FINGERPRINT_LINE_CHARS]
    return ""


def report_plugin_crash(report: CrashReport, *, user_id: UUID | None) -> None:
    """Forward a plugin crash report (§14) to Sentry as an error-level message tagged
    ``role=plugin``, ``plugin_version``, ``host`` and ``os``, with the backtrace as an
    attachment (attachments are not truncated the way context strings are). Grouped by
    platform, version and the backtrace's first line. Without Sentry the report is
    logged at warning level, without the backtrace body."""
    import sentry_sdk

    headline = first_backtrace_line(report.backtrace)
    facts = {
        "plugin_version": report.plugin_version,
        "host": report.host,
        "os": report.os,
        "occurred_at": report.occurred_at.isoformat(),
        "backtrace_bytes": len(report.backtrace.encode("utf-8")),
        "user_id": str(user_id) if user_id is not None else None,
    }
    if not sentry_sdk.is_initialized():
        log.warning("plugin crash reported; error reporting is disabled", extra=facts)
        return
    with sentry_sdk.new_scope() as scope:
        scope.set_tag("role", PLUGIN_ROLE)
        scope.set_tag("plugin_version", report.plugin_version)
        scope.set_tag("host", report.host)
        scope.set_tag("os", report.os)
        if user_id is not None:
            scope.set_user({"id": str(user_id)})
        scope.set_context("crash", facts)
        scope.fingerprint = [PLUGIN_ROLE, report.os, report.host, report.plugin_version, headline]
        scope.add_attachment(
            bytes=report.backtrace.encode("utf-8"),
            filename=BACKTRACE_ATTACHMENT,
            content_type="text/plain",
        )
        sentry_sdk.capture_message(
            f"Plugin crash ({report.host}, {report.os}, {report.plugin_version}): {headline}",
            level="error",
        )
