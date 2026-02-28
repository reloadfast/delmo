"""Unit tests for rule preview endpoints."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.setting import Setting
from httpx import AsyncClient
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.unit


def _make_torrent(
    name: str,
    save_path: str,
    extensions: list[str] | None = None,
    tracker_domains: list[str] | None = None,
) -> MagicMock:
    t = MagicMock()
    t.hash = name.lower().replace(" ", "_")
    t.name = name
    t.save_path = save_path
    t.tracker_domains = tracker_domains or []
    files = []
    for ext in extensions or []:
        f = MagicMock()
        f.extension = ext
        files.append(f)
    t.files = files
    return t


async def _seed(db: AsyncSession, key: str, value: str) -> None:
    """Upsert a setting so repeated seeding across tests never violates the unique key."""
    stmt = (
        sqlite_insert(Setting)
        .values(key=key, value=value)
        .on_conflict_do_update(index_elements=["key"], set_={"value": value})
    )
    await db.execute(stmt)
    await db.flush()


# ---------------------------------------------------------------------------
# GET /api/rules/{id}/preview
# ---------------------------------------------------------------------------


async def test_preview_rule_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/rules/9999/preview")
    assert resp.status_code == 404


async def test_preview_rule_no_host(client: AsyncClient) -> None:
    # Create a rule first
    r = await client.post(
        "/api/rules",
        json={
            "name": "R",
            "destination": "/dest",
            "conditions": [{"condition_type": "extension", "value": "mkv"}],
        },
    )
    rule_id = r.json()["id"]
    resp = await client.get(f"/api/rules/{rule_id}/preview")
    assert resp.status_code == 503


async def test_preview_rule_deluge_unreachable(
    client: AsyncClient, db: AsyncSession
) -> None:
    await _seed(db, "deluge_host", "127.0.0.1")
    r = await client.post(
        "/api/rules",
        json={
            "name": "R",
            "destination": "/dest",
            "conditions": [{"condition_type": "extension", "value": "mkv"}],
        },
    )
    rule_id = r.json()["id"]
    with patch(
        "app.api.rules.DelugeClient.connect",
        new_callable=AsyncMock,
        side_effect=ConnectionError("refused"),
    ):
        resp = await client.get(f"/api/rules/{rule_id}/preview")
    assert resp.status_code == 503


async def test_preview_rule_returns_matches(
    client: AsyncClient, db: AsyncSession
) -> None:
    await _seed(db, "deluge_host", "127.0.0.1")
    r = await client.post(
        "/api/rules",
        json={
            "name": "MKV",
            "destination": "/videos",
            "conditions": [{"condition_type": "extension", "value": "mkv"}],
        },
    )
    rule_id = r.json()["id"]

    torrents = [
        _make_torrent("Movie A", "/dl", extensions=[".mkv"]),
        _make_torrent("Audio B", "/dl", extensions=[".mp3"]),
        _make_torrent("Already moved", "/videos", extensions=[".mkv"]),
    ]

    with (
        patch("app.api.rules.DelugeClient.connect", new_callable=AsyncMock),
        patch(
            "app.api.rules.DelugeClient.get_torrents",
            new_callable=AsyncMock,
            return_value=torrents,
        ),
        patch("app.api.rules.DelugeClient.disconnect", new_callable=AsyncMock),
    ):
        resp = await client.get(f"/api/rules/{rule_id}/preview")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_torrents"] == 3
    assert len(body["matched"]) == 1
    assert body["matched"][0]["name"] == "Movie A"


# ---------------------------------------------------------------------------
# POST /api/rules/preview
# ---------------------------------------------------------------------------


async def test_preview_eval_no_host(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/rules/preview",
        json={"conditions": [{"condition_type": "extension", "value": "mkv"}]},
    )
    assert resp.status_code == 503


async def test_preview_eval_returns_matches(
    client: AsyncClient, db: AsyncSession
) -> None:
    await _seed(db, "deluge_host", "127.0.0.1")

    torrents = [
        _make_torrent("Movie A", "/dl", extensions=[".mkv"]),
        _make_torrent("Audio B", "/dl", extensions=[".mp3"]),
    ]

    with (
        patch("app.api.rules.DelugeClient.connect", new_callable=AsyncMock),
        patch(
            "app.api.rules.DelugeClient.get_torrents",
            new_callable=AsyncMock,
            return_value=torrents,
        ),
        patch("app.api.rules.DelugeClient.disconnect", new_callable=AsyncMock),
    ):
        resp = await client.post(
            "/api/rules/preview",
            json={"conditions": [{"condition_type": "extension", "value": "mkv"}]},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_torrents"] == 2
    assert len(body["matched"]) == 1
    assert body["matched"][0]["name"] == "Movie A"


async def test_preview_eval_empty_conditions(
    client: AsyncClient, db: AsyncSession
) -> None:
    await _seed(db, "deluge_host", "127.0.0.1")
    torrents = [_make_torrent("T", "/dl", extensions=[".mkv"])]

    with (
        patch("app.api.rules.DelugeClient.connect", new_callable=AsyncMock),
        patch(
            "app.api.rules.DelugeClient.get_torrents",
            new_callable=AsyncMock,
            return_value=torrents,
        ),
        patch("app.api.rules.DelugeClient.disconnect", new_callable=AsyncMock),
    ):
        resp = await client.post("/api/rules/preview", json={"conditions": []})

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["matched"]) == 0


async def test_preview_eval_tracker_condition(
    client: AsyncClient, db: AsyncSession
) -> None:
    await _seed(db, "deluge_host", "127.0.0.1")
    torrents = [
        _make_torrent("T1", "/dl", tracker_domains=["tracker.example.com"]),
        _make_torrent("T2", "/dl", tracker_domains=["other.net"]),
    ]

    with (
        patch("app.api.rules.DelugeClient.connect", new_callable=AsyncMock),
        patch(
            "app.api.rules.DelugeClient.get_torrents",
            new_callable=AsyncMock,
            return_value=torrents,
        ),
        patch("app.api.rules.DelugeClient.disconnect", new_callable=AsyncMock),
    ):
        resp = await client.post(
            "/api/rules/preview",
            json={"conditions": [{"condition_type": "tracker", "value": "example"}]},
        )

    body = resp.json()
    assert len(body["matched"]) == 1
    assert body["matched"][0]["name"] == "T1"
