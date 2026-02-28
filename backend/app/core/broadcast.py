"""In-process WebSocket broadcaster for real-time log events."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class LogBroadcaster:
    """Fan-out log events to all connected WebSocket listeners."""

    def __init__(self) -> None:
        self._queues: set[asyncio.Queue[dict[str, object]]] = set()

    def publish(self, entry: dict[str, object]) -> None:
        """Non-blocking broadcast; drops silently if a subscriber's queue is full."""
        for q in list(self._queues):
            try:
                q.put_nowait(entry)
            except asyncio.QueueFull:
                pass

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[dict[str, object]]]:
        q: asyncio.Queue[dict[str, object]] = asyncio.Queue(maxsize=100)
        self._queues.add(q)
        try:
            yield q
        finally:
            self._queues.discard(q)


log_broadcaster = LogBroadcaster()
