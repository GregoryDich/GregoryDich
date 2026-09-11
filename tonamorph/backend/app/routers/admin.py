"""§15 — the founder's read-only support lookup.

Guarded by ``ADMIN_API_KEY``: the route does not exist (``404``) while the key is unset,
every attempt — right or wrong — spends the one shared admin budget before the key is
compared in constant time, and each lookup leaves one audit line that names the user id
it resolved and never the address it was asked for.
"""

from __future__ import annotations

import hmac
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.dependencies import get_services
from app.errors import NOT_FOUND, UNAUTHORIZED, ApiException
from app.middleware.rate_limit import TokenBucketLimiter, enforce_key
from app.schemas import AdminUserResponse
from app.services.factory import Services
from app.services.jobs import without_signed_urls

log = logging.getLogger("tonamorph.admin")
router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_KEY_HEADER = "x-admin-key"
USERS_PATH_PREFIX = "/admin/users/"
USERS_PATH_TEMPLATE = "/admin/users/{subject}"
"""The subject may be an email address, so the access log records the template
(``app.main.loggable_path``); the audit line here names the resolved user id only."""
ADMIN_REQUESTS_PER_MIN = 30
"""One budget for the whole route, whoever calls: bounds key guessing as much as use."""
ADMIN_HISTORY_LIMIT = 20
"""Jobs and ledger entries returned with an overview, newest first."""
INVALID_ADMIN_KEY_MESSAGE = "Invalid admin key."
USER_NOT_FOUND_MESSAGE = "No account matches."


def admin_limiter(request: Request) -> TokenBucketLimiter:
    limiter = getattr(request.app.state, "admin_limits", None)
    if limiter is None:
        limiter = request.app.state.admin_limits = TokenBucketLimiter(ADMIN_REQUESTS_PER_MIN)
    return limiter


async def require_admin(request: Request, services: Services = Depends(get_services)) -> None:
    """``404`` while no key is configured, ``429`` over budget, ``401`` for a wrong key."""
    secret = services.settings.admin_api_key.get_secret_value()
    if not secret:
        raise ApiException(NOT_FOUND)
    enforce_key(admin_limiter(request), "admin")
    presented = request.headers.get(ADMIN_KEY_HEADER, "")
    if not presented or not hmac.compare_digest(
        secret.encode("utf-8"), presented.encode("utf-8", "replace")
    ):
        log.warning("admin key rejected", extra={"path": request.url.path})
        raise ApiException(UNAUTHORIZED, message=INVALID_ADMIN_KEY_MESSAGE)


def parse_subject(subject: str) -> tuple[UUID | None, str | None]:
    """``(user_id, email)``: a UUID is a user id, anything else an email address."""
    try:
        return UUID(subject.strip()), None
    except ValueError:
        return None, subject


@router.get(
    "/users/{subject}", response_model=AdminUserResponse, dependencies=[Depends(require_admin)]
)
async def user_overview(
    subject: str, services: Services = Depends(get_services)
) -> AdminUserResponse:
    """The support view row plus the last 20 jobs (no object URLs) and ledger entries."""
    user_id, email = parse_subject(subject)
    lookup = "id" if user_id is not None else "email"
    overview = await services.support.overview(user_id=user_id, email=email)
    if overview is None:
        log.info("admin lookup", extra={"lookup": lookup, "outcome": "not_found"})
        raise ApiException(NOT_FOUND, message=USER_NOT_FOUND_MESSAGE)
    jobs = await services.jobs.list(overview.user_id, limit=ADMIN_HISTORY_LIMIT)
    ledger = await services.credits.ledger(overview.user_id, limit=ADMIN_HISTORY_LIMIT)
    log.info(
        "admin lookup",
        extra={"lookup": lookup, "outcome": "ok", "user_id": str(overview.user_id)},
    )
    return AdminUserResponse(
        user=overview,
        jobs=[without_signed_urls(job) for job in jobs.jobs],
        ledger=ledger.entries,
    )
