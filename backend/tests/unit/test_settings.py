"""Unit tests for the settings CRUD endpoints."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.unit


async def test_get_settings_empty(client: AsyncClient) -> None:
    """GET /api/settings returns an empty data dict when no settings exist."""
    resp = await client.get("/api/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert isinstance(body["data"], dict)


async def test_patch_settings_single(client: AsyncClient) -> None:
    """PATCH /api/settings upserts a single key."""
    resp = await client.patch(
        "/api/settings", json={"updates": {"polling_interval_seconds": "120"}}
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["polling_interval_seconds"] == "120"


async def test_patch_settings_multiple(client: AsyncClient) -> None:
    """PATCH /api/settings upserts multiple keys in one call."""
    payload = {
        "updates": {
            "deluge_host": "192.168.1.10",
            "deluge_port": "58846",
        }
    }
    resp = await client.patch("/api/settings", json=payload)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["deluge_host"] == "192.168.1.10"
    assert data["deluge_port"] == "58846"


async def test_patch_settings_idempotent(client: AsyncClient) -> None:
    """Patching the same key twice keeps the latest value."""
    await client.patch("/api/settings", json={"updates": {"deluge_host": "first"}})
    resp = await client.patch(
        "/api/settings", json={"updates": {"deluge_host": "second"}}
    )
    assert resp.json()["data"]["deluge_host"] == "second"


async def test_patch_settings_returns_full_map(client: AsyncClient) -> None:
    """PATCH response includes all settings, not just the patched ones."""
    await client.patch("/api/settings", json={"updates": {"key_a": "a"}})
    resp = await client.patch("/api/settings", json={"updates": {"key_b": "b"}})
    data = resp.json()["data"]
    assert "key_a" in data
    assert "key_b" in data


async def test_patch_settings_rejects_empty_key(client: AsyncClient) -> None:
    """PATCH rejects payloads with empty string keys."""
    resp = await client.patch("/api/settings", json={"updates": {"": "value"}})
    assert resp.status_code == 422


async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
