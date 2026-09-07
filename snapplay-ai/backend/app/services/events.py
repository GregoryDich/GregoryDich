"""In-process fan-out of job events to SSE / WebSocket subscribers (§2).

Publishers never block: each subscriber owns an unbounded ``asyncio.Queue`` and a stream
ends once it has delivered a terminal (``result`` / ``error``) event. Events are not
buffered for future subscribers — a new stream starts from the job's current row.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

EVENT_PROGRESS = "progress"
EVENT_RESULT = "result"
EVENT_ERROR = "error"
TERMINAL_EVENTS = frozenset({EVENT_RESULT, EVENT_ERROR})

JobEvent = dict[str, Any]
"""``{"event": "progress" | "result" | "error", "data": <payload>}``."""


class JobEventBus:
    def __init__(self) -> None:
        self._subscribers: dict[UUID, set[asyncio.Queue[JobEvent]]] = {}

    def publish(self, job_id: UUID, event: str, data: Any) -> None:
        for queue in list(self._subscribers.get(job_id, ())):
            queue.put_nowait({"event": event, "data": data})

    @asynccontextmanager
    async def subscription(self, job_id: UUID) -> AsyncIterator[asyncio.Queue[JobEvent]]:
        queue: asyncio.Queue[JobEvent] = asyncio.Queue()
        self._subscribers.setdefault(job_id, set()).add(queue)
        try:
            yield queue
        finally:
            subscribers = self._subscribers.get(job_id)
            if subscribers is not None:
                subscribers.discard(queue)
                if not subscribers:
                    del self._subscribers[job_id]

    def subscriber_count(self, job_id: UUID) -> int:
        return len(self._subscribers.get(job_id, ()))


__all__ = [
    "EVENT_ERROR",
    "EVENT_PROGRESS",
    "EVENT_RESULT",
    "TERMINAL_EVENTS",
    "JobEvent",
    "JobEventBus",
]
