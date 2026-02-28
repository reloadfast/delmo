"""Unit tests for the dashboard stats endpoint."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.move_log import MoveLog
from app.models.setting import Setting
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.unit


async def _seed_setting(db: AsyncSession, key: str, value: str) -> None:
    db.add(Setting(key=key, value=value))
    await db.flush()


# ---------------------------------------------------------------------------
# GET /api/dashboard — no Deluge settings
# ---------------------------------------------------------------------------


async def test_dashboard_no_host_configured(client: AsyncClient) -> None:
    resp = await client.get("/api/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False
    assert body["error"] == "Deluge host is not configured."
    assert body["total_torrents"] is None
    assert body["matching_torrents"] is None
    assert body["moves_today"] == 0
    assert body["moves_all_time"] == 0


# ---------------------------------------------------------------------------
# GET /api/dashboard — Deluge unreachable
# ---------------------------------------------------------------------------


async def test_dashboard_deluge_unreachable(
    client: AsyncClient, db: AsyncSession
) -> None:
    await _seed_setting(db, "deluge_host", "127.0.0.1")
    await _seed_setting(db, "deluge_port", "58846")

    with patch(
        "app.api.dashboard.DelugeClient.connect",
        new_callable=AsyncMock,
        side_effect=ConnectionError("refused"),
    ):
        resp = await client.get("/api/dashboard")

    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False
    assert "refused" in body["error"]
    assert body["total_torrents"] is None


# ---------------------------------------------------------------------------
# GET /api/dashboard — DB stats counted correctly
# ---------------------------------------------------------------------------


async def test_dashboard_moves_today_counted(
    client: AsyncClient, db: AsyncSession
) -> None:
    today = datetime.now(tz=UTC)
    db.add(
        MoveLog(
            torrent_hash="h1",
            torrent_name="T1",
            source_path="/dl",
            destination_path="/dest",
            status="success",
            created_at=today,
        )
    )
    db.add(
        MoveLog(
            torrent_hash="h2",
            torrent_name="T2",
            source_path="/dl",
            destination_path="/dest",
            status="error",
            created_at=today,
        )
    )
    await db.flush()

    resp = await client.get("/api/dashboard")
    body = resp.json()
    assert body["moves_today"] == 1  # only success counted
    assert body["moves_all_time"] == 1


async def test_dashboard_moves_all_time(
    client: AsyncClient, db: AsyncSession
) -> None:
    for i in range(3):
        db.add(
            MoveLog(
                torrent_hash=f"h{i}",
                torrent_name=f"T{i}",
                source_path="/dl",
                destination_path="/dest",
                status="success",
            )
        )
    await db.flush()

    resp = await client.get("/api/dashboard")
    body = resp.json()
    assert body["moves_all_time"] == 3


# ---------------------------------------------------------------------------
# GET /api/dashboard — Deluge connected
# ---------------------------------------------------------------------------


async def test_dashboard_connected(client: AsyncClient, db: AsyncSession) -> None:
    await _seed_setting(db, "deluge_host", "127.0.0.1")
    await _seed_setting(db, "deluge_port", "58846")

    mock_torrent = MagicMock()
    mock_torrent.hash = "abc"
    mock_torrent.name = "Test"
    mock_torrent.save_path = "/dl"
    mock_torrent.files = []
    mock_torrent.tracker_domains = []

    with (
        patch(
            "app.api.dashboard.DelugeClient.connect", new_callable=AsyncMock
        ),
        patch(
            "app.api.dashboard.DelugeClient.get_torrents",
            new_callable=AsyncMock,
            return_value=[mock_torrent],
        ),
        patch(
            "app.api.dashboard.DelugeClient.disconnect", new_callable=AsyncMock
        ),
        patch(
            "app.api.dashboard.DelugeClient.daemon_version",
            new_callable=lambda: property(lambda self: "2.1.0"),
        ),
    ):
        resp = await client.get("/api/dashboard")

    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True
    assert body["total_torrents"] == 1
    assert body["matching_torrents"] == 0  # no rules defined
