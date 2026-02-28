"""Unit tests for the WebSocket log-feed endpoint and broadcaster."""
from __future__ import annotations

import asyncio
import json

import pytest
from app.core.broadcast import LogBroadcaster
from app.main import app
from starlette.testclient import TestClient

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Broadcaster unit tests (pure async, no HTTP)
# ---------------------------------------------------------------------------


async def test_broadcaster_publish_received() -> None:
    broadcaster = LogBroadcaster()
    entry = {"id": 42, "status": "success", "torrent_name": "Test"}
    async with broadcaster.subscribe() as queue:
        broadcaster.publish(entry)
        received = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert received == entry


async def test_broadcaster_multiple_subscribers() -> None:
    broadcaster = LogBroadcaster()
    entry = {"id": 1}
    async with broadcaster.subscribe() as q1, broadcaster.subscribe() as q2:
        broadcaster.publish(entry)
        r1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        r2 = await asyncio.wait_for(q2.get(), timeout=1.0)
    assert r1 == entry
    assert r2 == entry


async def test_broadcaster_queue_full_drops_silently() -> None:
    """publish() must not raise when a subscriber queue is full."""
    broadcaster = LogBroadcaster()
    async with broadcaster.subscribe() as queue:
        # Fill the queue to capacity
        for i in range(queue.maxsize):
            broadcaster.publish({"id": i})
        # One more must not raise
        broadcaster.publish({"id": 999})
    assert True  # no exception


async def test_broadcaster_unsubscribe_cleans_up() -> None:
    broadcaster = LogBroadcaster()
    async with broadcaster.subscribe():
        assert len(broadcaster._queues) == 1
    assert len(broadcaster._queues) == 0


# ---------------------------------------------------------------------------
# WebSocket endpoint connectivity (sync TestClient)
# ---------------------------------------------------------------------------


def test_ws_logs_connection_accepted() -> None:
    """Verify the WS endpoint accepts connections and handles disconnect."""
    with TestClient(app) as client:
        with client.websocket_connect("/api/ws/logs") as ws:
            ws.close()


def test_ws_logs_receives_broadcast() -> None:
    """Broadcast a message via log_broadcaster and confirm WS client receives it."""
    from app.core.broadcast import log_broadcaster

    with TestClient(app) as client:
        with client.websocket_connect("/api/ws/logs") as ws:
            entry = {"id": 7, "status": "success", "torrent_name": "LiveTest"}
            log_broadcaster.publish(entry)
            raw = ws.receive_text()
            received = json.loads(raw)
            assert received["id"] == 7
            assert received["status"] == "success"
