"""Error reporting (Sentry), enabled only when ``SENTRY_DSN`` is set.

docs/SECURITY.md forbids request bodies, headers and tokens in any log; the same rule
applies to error reports, so every event is scrubbed before it leaves the process and
performance tracing stays off. Both the API and the GPU workers call :func:`init_sentry`
once at start-up; the ``role`` tag tells the two apart in one Sentry project.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from app.config import Settings

log = logging.getLogger("tonamorph.observability")

RELEASE_ENV = "TONAMORPH_RELEASE"
_SCRUBBED_REQUEST_KEYS = ("headers", "cookies", "data", "query_string")


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
