"""§14 — opt-in plugin crash reports, forwarded to Sentry under ``role=plugin``."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from app.auth import Principal
from app.dependencies import get_optional_principal
from app.middleware.rate_limit import (
    REMAINING_HEADER,
    RateLimits,
    TokenBucketLimiter,
    enforce,
    enforce_key,
)
from app.observability import report_plugin_crash
from app.schemas import CrashReport, TelemetryAck

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

ANONYMOUS_CRASHES_PER_HOUR = 5
"""Reports without a session, per client address: a crash before sign-in is real, an
unauthenticated flood is not. Behind a load balancer the address is the balancer's own,
so anonymous reports then share one budget — a signed-in plugin spends its reads budget."""
ANONYMOUS_MAX_BUCKETS = 10_000


def anonymous_limiter(request: Request) -> TokenBucketLimiter:
    limiter = getattr(request.app.state, "crash_limits", None)
    if limiter is None:
        limiter = request.app.state.crash_limits = TokenBucketLimiter(
            ANONYMOUS_CRASHES_PER_HOUR / 60,
            capacity=ANONYMOUS_CRASHES_PER_HOUR,
            max_buckets=ANONYMOUS_MAX_BUCKETS,
        )
    return limiter


@router.post("/crash", status_code=status.HTTP_202_ACCEPTED, response_model=TelemetryAck)
async def crash(
    request: Request,
    response: Response,
    body: CrashReport,
    principal: Principal | None = Depends(get_optional_principal),
) -> TelemetryAck:
    """Accepts the report once the budget allows, then hands it to Sentry as a message
    tagged ``role=plugin``, ``plugin_version``, ``host`` and ``os`` with the backtrace
    attached; with Sentry disabled the report is logged without the backtrace body."""
    if principal is not None:
        limits: RateLimits = request.app.state.rate_limits
        remaining = enforce(limits.reads, principal)
    else:
        address = request.client.host if request.client is not None else "unknown"
        remaining = enforce_key(anonymous_limiter(request), address)
    response.headers[REMAINING_HEADER] = str(remaining)
    report_plugin_crash(body, user_id=principal.user_id if principal is not None else None)
    return TelemetryAck()
