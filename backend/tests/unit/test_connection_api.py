"""Unit tests for connection and torrent API endpoints with mocked DelugeClient."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.deluge import TorrentFile, TorrentInfo
from httpx import AsyncClient

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _settings_patch(settings: dict[str, str]):  # type: ignore[return]
    """Patch the _settings_dict helper used by both connection and torrent routers."""
    return patch(
        "app.api.connection._settings_dict",
        new=AsyncMock(return_value=settings),
    )


def _settings_patch_torrents(settings: dict[str, str]):  # type: ignore[return]
    return patch(
        "app.api.torrents._settings_dict",
        new=AsyncMock(return_value=settings),
    )


_CONFIGURED_SETTINGS = {
    "deluge_host": "192.168.1.10",
    "deluge_port": "58846",
    "deluge_username": "admin",
    "deluge_password": "secret",
}

_UNCONFIGURED_SETTINGS = {
    "deluge_host": "",
    "deluge_port": "58846",
    "deluge_username": "",
    "deluge_password": "",
}


# ---------------------------------------------------------------------------
# GET /api/connection/status
# ---------------------------------------------------------------------------


async def test_connection_status_not_configured(client: AsyncClient) -> None:
    with _settings_patch(_UNCONFIGURED_SETTINGS):
        resp = await client.get("/api/connection/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False
    assert "not configured" in body["error"].lower()


async def test_connection_status_connected(client: AsyncClient) -> None:
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.disconnect = AsyncMock()
    mock_client.daemon_version = "2.1.1"
    mock_client.check_label_plugin = AsyncMock(return_value=True)

    with _settings_patch(_CONFIGURED_SETTINGS), patch(
        "app.api.connection.DelugeClient", return_value=mock_client
    ):
        resp = await client.get("/api/connection/status")

    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True
    assert body["daemon_version"] == "2.1.1"
    assert body["error"] is None
    assert body["label_plugin_available"] is True


async def test_connection_status_connect_error(client: AsyncClient) -> None:
    mock_client = MagicMock()
    mock_client.connect = AsyncMock(side_effect=ConnectionError("Connection refused"))
    mock_client.disconnect = AsyncMock()

    with _settings_patch(_CONFIGURED_SETTINGS), patch(
        "app.api.connection.DelugeClient", return_value=mock_client
    ):
        resp = await client.get("/api/connection/status")

    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False
    assert body["error"] is not None


async def test_connection_status_masks_password(client: AsyncClient) -> None:
    mock_client = MagicMock()
    mock_client.connect = AsyncMock(
        side_effect=ConnectionError("auth failed: secret in error")
    )
    mock_client.disconnect = AsyncMock()

    with _settings_patch(_CONFIGURED_SETTINGS), patch(
        "app.api.connection.DelugeClient", return_value=mock_client
    ):
        resp = await client.get("/api/connection/status")

    body = resp.json()
    assert "secret" not in (body.get("error") or "")


# ---------------------------------------------------------------------------
# POST /api/connection/test
# ---------------------------------------------------------------------------


async def test_connection_test_success(client: AsyncClient) -> None:
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.disconnect = AsyncMock()
    mock_client.daemon_version = "2.1.1"

    with patch("app.api.connection.DelugeClient", return_value=mock_client):
        resp = await client.post(
            "/api/connection/test",
            json={
                "host": "192.168.1.10",
                "port": 58846,
                "username": "u",
                "password": "p",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True
    assert body["daemon_version"] == "2.1.1"


async def test_connection_test_missing_host(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/connection/test",
        json={"host": "", "port": 58846},
    )
    assert resp.status_code == 422


async def test_connection_test_failure(client: AsyncClient) -> None:
    mock_client = MagicMock()
    mock_client.connect = AsyncMock(side_effect=Exception("Auth failed"))
    mock_client.disconnect = AsyncMock()

    with patch("app.api.connection.DelugeClient", return_value=mock_client):
        resp = await client.post(
            "/api/connection/test",
            json={"host": "192.168.1.10", "port": 58846},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False
    assert "Auth failed" in body["error"]


# ---------------------------------------------------------------------------
# GET /api/torrents
# ---------------------------------------------------------------------------


async def test_torrents_not_configured(client: AsyncClient) -> None:
    with _settings_patch_torrents(_UNCONFIGURED_SETTINGS):
        resp = await client.get("/api/torrents")
    assert resp.status_code == 503


async def test_torrents_returns_list(client: AsyncClient) -> None:
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.disconnect = AsyncMock()
    mock_client.get_torrents = AsyncMock(
        return_value=[
            TorrentInfo(
                hash="abc123",
                name="Test Movie",
                save_path="/downloads",
                state="Seeding",
                progress=100.0,
                files=[TorrentFile(path="movie.mkv", size=1_000_000_000)],
                tracker_domains=["tracker.example.com"],
            )
        ]
    )

    with _settings_patch_torrents(_CONFIGURED_SETTINGS), patch(
        "app.api.torrents.DelugeClient", return_value=mock_client
    ):
        resp = await client.get("/api/torrents")

    assert resp.status_code == 200
    torrents = resp.json()
    assert len(torrents) == 1
    assert torrents[0]["hash"] == "abc123"
    assert torrents[0]["name"] == "Test Movie"
    assert torrents[0]["files"][0]["extension"] == ".mkv"
    assert "tracker.example.com" in torrents[0]["tracker_domains"]


async def test_torrents_connect_error_returns_503(client: AsyncClient) -> None:
    mock_client = MagicMock()
    mock_client.connect = AsyncMock(side_effect=Exception("Connection refused"))
    mock_client.disconnect = AsyncMock()

    with _settings_patch_torrents(_CONFIGURED_SETTINGS), patch(
        "app.api.torrents.DelugeClient", return_value=mock_client
    ):
        resp = await client.get("/api/torrents")

    assert resp.status_code == 503


async def test_torrents_invalid_port(client: AsyncClient) -> None:
    bad_settings = {**_CONFIGURED_SETTINGS, "deluge_port": "notanumber"}
    with _settings_patch_torrents(bad_settings):
        resp = await client.get("/api/torrents")
    assert resp.status_code == 503
