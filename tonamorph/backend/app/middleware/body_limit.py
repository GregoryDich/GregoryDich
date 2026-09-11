"""Request-body limits applied before the body is read (docs/SECURITY.md §7).

FastAPI parses a multipart body *before* any dependency runs, and starlette's
``MultiPartParser`` enforces no total size and spools every part above 1 MB to disk. So
without this middleware an unauthenticated client can make the process consume — and
spool — arbitrarily large bodies on ``POST /v1/jobs`` and collect a ``401`` afterwards;
enough concurrent uploads fill the disk. The ingress is configured to reject oversized
requests too, but the application does not depend on it being there.

Three gates run before the first byte reaches the parser:

1. an upload route without credentials is ``401`` immediately;
2. a ``Content-Length`` above the route's cap is ``413``;
3. the body is counted as it streams, so a missing or lying ``Content-Length``
   (chunked transfer) is cut off at that same cap.

The handler keeps its own byte counter as defence in depth (§2 still owns the
``413`` for a file that is under the wire cap but over ``MAX_UPLOAD_BYTES``).
"""

from __future__ import annotations

from collections.abc import Iterable

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.dependencies import API_KEY_HEADER, bearer_token
from app.errors import PAYLOAD_TOO_LARGE, UNAUTHORIZED, ApiException

MULTIPART_OVERHEAD_BYTES = 8 * 1024
"""Head-room over ``MAX_UPLOAD_BYTES`` for the multipart boundaries and part headers."""
DEFAULT_MAX_BYTES = 1024 * 1024
"""Cap for every other route; they take small JSON documents only."""
UPLOAD_PATHS = frozenset({"/v1/jobs"})
"""Routes that accept a file, and therefore the larger cap plus the credentials gate."""


def payload_too_large(max_bytes: int) -> ApiException:
    """The §5 ``413`` envelope, quoting the limit that applies to the payload itself."""
    return ApiException(
        PAYLOAD_TOO_LARGE,
        message=f"The upload exceeds {max_bytes} bytes.",
        details={"max_bytes": max_bytes},
    )


def _content_length(headers: Headers) -> int | None:
    raw = headers.get("content-length")
    if raw is None or not raw.isdigit():
        return None
    return int(raw)


def _has_credentials(headers: Headers) -> bool:
    return bool(bearer_token(headers.get("authorization")) or headers.get(API_KEY_HEADER))


async def _respond(scope: Scope, send: Send, exc: ApiException) -> None:
    await exc.response()(scope, _no_receive, send)


async def _no_receive() -> Message:  # pragma: no cover - a JSONResponse never receives
    return {"type": "http.disconnect"}


class BodyLimitMiddleware:
    """Bounds the request body of every HTTP request; see the module docstring."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_upload_bytes: int,
        max_other_bytes: int = DEFAULT_MAX_BYTES,
        upload_paths: Iterable[str] = UPLOAD_PATHS,
    ) -> None:
        self.app = app
        self._max_upload_bytes = max_upload_bytes
        self._max_other_bytes = max_other_bytes
        self._upload_paths = frozenset(upload_paths)

    def _route_limits(self, scope: Scope) -> tuple[int, int, bool]:
        """``(wire cap, cap quoted to the client, is an upload route)``."""
        path = scope.get("path", "").rstrip("/") or "/"
        if path in self._upload_paths:
            return (
                self._max_upload_bytes + MULTIPART_OVERHEAD_BYTES,
                self._max_upload_bytes,
                True,
            )
        return self._max_other_bytes, self._max_other_bytes, False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        wire_limit, reported_limit, is_upload = self._route_limits(scope)
        headers = Headers(scope=scope)
        if is_upload and not _has_credentials(headers):
            await _respond(scope, send, ApiException(UNAUTHORIZED))
            return
        declared = _content_length(headers)
        if declared is not None and declared > wire_limit:
            await _respond(scope, send, payload_too_large(reported_limit))
            return

        total = 0
        rejected = False
        started = False

        async def receive_counted() -> Message:
            nonlocal total, rejected
            message = await receive()
            if rejected or message["type"] != "http.request":
                return message
            total += len(message.get("body", b""))
            if total <= wire_limit:
                return message
            rejected = True
            if not started:
                await _respond(scope, send, payload_too_large(reported_limit))
            # Unwind the handler: starlette turns this into a ClientDisconnect.
            return {"type": "http.disconnect"}

        async def send_unless_rejected(message: Message) -> None:
            nonlocal started
            if rejected:
                return
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive_counted, send_unless_rejected)
        except Exception:
            if not rejected:
                raise


__all__ = [
    "DEFAULT_MAX_BYTES",
    "MULTIPART_OVERHEAD_BYTES",
    "UPLOAD_PATHS",
    "BodyLimitMiddleware",
    "payload_too_large",
]
