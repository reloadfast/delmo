"""Tests exercising connection/torrent endpoints via the real test DB."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.unit


async def test_connection_status_real_db_no_host(client: AsyncClient) -> None:
    """With real test DB (deluge_host empty by default), returns 'not configured'."""
    resp = await client.get("/api/connection/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False
    assert body["error"] is not None


async def test_torrents_real_db_no_host(client: AsyncClient) -> None:
    """With real test DB, GET /api/torrents returns 503 when host not configured."""
    resp = await client.get("/api/torrents")
    assert resp.status_code == 503


async def test_connection_status_invalid_port_in_db(client: AsyncClient) -> None:
    """connection_status returns error when port setting is not a valid integer."""
    # Patch settings to return a bad port without mocking _settings_dict path
    settings = {
        "deluge_host": "192.168.1.10",
        "deluge_port": "notanumber",
        "deluge_username": "",
        "deluge_password": "",
    }
    with patch(
        "app.api.connection._settings_dict",
        new=AsyncMock(return_value=settings),
    ):
        resp = await client.get("/api/connection/status")

    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False
    assert body["error"] is not None


async def test_connection_status_generic_exception(client: AsyncClient) -> None:
    """Generic exceptions during connect are caught and returned as errors."""
    settings = {
        "deluge_host": "192.168.1.10",
        "deluge_port": "58846",
        "deluge_username": "u",
        "deluge_password": "p",
    }
    mock_client = MagicMock()
    mock_client.connect = AsyncMock(side_effect=RuntimeError("Unexpected RPC error"))
    mock_client.disconnect = AsyncMock()

    settings_mock = AsyncMock(return_value=settings)
    with patch("app.api.connection._settings_dict", new=settings_mock), \
         patch("app.api.connection.DelugeClient", return_value=mock_client):
        resp = await client.get("/api/connection/status")

    body = resp.json()
    assert body["connected"] is False
    assert body["error"]  # password masking may alter message; just check non-empty


async def test_connection_test_timeout(client: AsyncClient) -> None:
    """Timeout during test_connection is reported correctly."""
    mock_client = MagicMock()
    mock_client.connect = AsyncMock(side_effect=TimeoutError())
    mock_client.disconnect = AsyncMock()

    with patch("app.api.connection.DelugeClient", return_value=mock_client):
        resp = await client.post(
            "/api/connection/test",
            json={"host": "192.168.1.10", "port": 58846},
        )

    body = resp.json()
    assert body["connected"] is False
    assert "Timeout" in body["error"] or "timeout" in body["error"].lower()
