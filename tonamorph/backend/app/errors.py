"""Error codes and the JSON error envelope (docs/API_CONTRACT.md §5).

Every non-2xx response has the body ``{"error": {"code", "message", "details"}}``.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas import ErrorBody, ErrorEnvelope

log = logging.getLogger("tonamorph.errors")

# Contract §5 code table.
BAD_REQUEST = "bad_request"
UNAUTHORIZED = "unauthorized"
TOKEN_EXPIRED = "token_expired"
INVALID_SIGNATURE = "invalid_signature"
INSUFFICIENT_CREDITS = "insufficient_credits"
NOT_FOUND = "not_found"
CONFLICT = "conflict"
PAYLOAD_TOO_LARGE = "payload_too_large"
UNSUPPORTED_MEDIA_TYPE = "unsupported_media_type"
VALIDATION_ERROR = "validation_error"
RATE_LIMITED = "rate_limited"
INTERNAL_ERROR = "internal_error"
WORKER_UNAVAILABLE = "worker_unavailable"

STATUS_BY_CODE: dict[str, int] = {
    BAD_REQUEST: 400,
    UNAUTHORIZED: 401,
    TOKEN_EXPIRED: 401,
    INVALID_SIGNATURE: 401,
    INSUFFICIENT_CREDITS: 402,
    NOT_FOUND: 404,
    CONFLICT: 409,
    PAYLOAD_TOO_LARGE: 413,
    UNSUPPORTED_MEDIA_TYPE: 415,
    VALIDATION_ERROR: 422,
    RATE_LIMITED: 429,
    INTERNAL_ERROR: 500,
    WORKER_UNAVAILABLE: 503,
}

# First code listed for each status in §5; used when translating framework exceptions.
CODE_BY_STATUS: dict[int, str] = {
    400: BAD_REQUEST,
    401: UNAUTHORIZED,
    402: INSUFFICIENT_CREDITS,
    404: NOT_FOUND,
    409: CONFLICT,
    413: PAYLOAD_TOO_LARGE,
    415: UNSUPPORTED_MEDIA_TYPE,
    422: VALIDATION_ERROR,
    429: RATE_LIMITED,
    500: INTERNAL_ERROR,
    503: WORKER_UNAVAILABLE,
}

DEFAULT_MESSAGES: dict[str, str] = {
    BAD_REQUEST: "Bad request.",
    UNAUTHORIZED: "Authentication required.",
    TOKEN_EXPIRED: "The access token has expired.",
    INVALID_SIGNATURE: "Invalid signature.",
    INSUFFICIENT_CREDITS: "Insufficient credits.",
    NOT_FOUND: "Not found.",
    CONFLICT: "Conflict.",
    PAYLOAD_TOO_LARGE: "The uploaded file is too large.",
    UNSUPPORTED_MEDIA_TYPE: "Unsupported media type.",
    VALIDATION_ERROR: "Validation error.",
    RATE_LIMITED: "Too many requests.",
    INTERNAL_ERROR: "Internal server error.",
    WORKER_UNAVAILABLE: "No worker is available; retry later.",
}


class ApiException(Exception):
    """An error that serialises to the §5 envelope.

    ``status`` defaults to the contract status for ``code``; ``message`` defaults to a
    generic sentence. ``headers`` are added to the response (e.g. ``Retry-After``).
    """

    def __init__(
        self,
        code: str,
        status: int | None = None,
        message: str | None = None,
        details: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.code = code
        self.status = status if status is not None else STATUS_BY_CODE.get(code, 500)
        self.message = message if message is not None else DEFAULT_MESSAGES.get(code, code)
        self.details = dict(details) if details is not None else None
        self.headers = dict(headers) if headers is not None else None
        super().__init__(f"{self.status} {self.code}: {self.message}")

    def envelope(self) -> ErrorEnvelope:
        return ErrorEnvelope(
            error=ErrorBody(code=self.code, message=self.message, details=self.details)
        )

    def response(self) -> JSONResponse:
        return JSONResponse(
            status_code=self.status,
            content=self.envelope().model_dump(mode="json"),
            headers=self.headers,
        )


def rate_limited(retry_after_seconds: int, remaining: int = 0) -> ApiException:
    """429 with the ``Retry-After`` / ``X-RateLimit-Remaining`` headers required by §5."""
    return ApiException(
        RATE_LIMITED,
        details={"retry_after_seconds": retry_after_seconds},
        headers={
            "Retry-After": str(retry_after_seconds),
            "X-RateLimit-Remaining": str(remaining),
        },
    )


async def _handle_api_exception(_: Request, exc: ApiException) -> JSONResponse:
    return exc.response()


async def _handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"loc": list(err.get("loc", ())), "msg": err.get("msg", ""), "type": err.get("type", "")}
        for err in exc.errors()
    ]
    return ApiException(VALIDATION_ERROR, details={"errors": errors}).response()


async def _handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = CODE_BY_STATUS.get(exc.status_code)
    if code is None:
        code = BAD_REQUEST if exc.status_code < 500 else INTERNAL_ERROR
    detail = exc.detail if isinstance(exc.detail, str) else None
    headers = dict(exc.headers) if exc.headers else None
    return ApiException(code, exc.status_code, detail, headers=headers).response()


async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    log.error(
        "unhandled exception",
        exc_info=exc,
        extra={"method": request.method, "path": request.url.path},
    )
    return ApiException(INTERNAL_ERROR).response()


def install_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiException, _handle_api_exception)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _handle_unexpected)
