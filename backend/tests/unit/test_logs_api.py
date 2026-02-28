"""Unit tests for the move logs API."""
from __future__ import annotations

import pytest
from app.models.move_log import MoveLog
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.unit


async def test_list_logs_empty(client: AsyncClient) -> None:
    resp = await client.get("/api/logs")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_logs_returns_entries(client: AsyncClient, db: AsyncSession) -> None:
    db.add(
        MoveLog(
            torrent_hash="abc123",
            torrent_name="Test Movie",
            rule_id=1,
            rule_name="Video Rule",
            source_path="/downloads",
            destination_path="/videos",
            status="success",
        )
    )
    await db.flush()

    resp = await client.get("/api/logs")
    assert resp.status_code == 200
    logs = resp.json()
    assert len(logs) >= 1
    entry = next(e for e in logs if e["torrent_hash"] == "abc123")
    assert entry["status"] == "success"
    assert entry["torrent_name"] == "Test Movie"
    assert entry["rule_name"] == "Video Rule"


async def test_list_logs_limit_param(client: AsyncClient, db: AsyncSession) -> None:
    for i in range(5):
        db.add(
            MoveLog(
                torrent_hash=f"hash{i}",
                torrent_name=f"Torrent {i}",
                source_path="/dl",
                destination_path="/dest",
                status="success",
            )
        )
    await db.flush()

    resp = await client.get("/api/logs?limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) <= 2


async def test_list_logs_invalid_limit(client: AsyncClient) -> None:
    resp = await client.get("/api/logs?limit=0")
    assert resp.status_code == 422
