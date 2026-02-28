"""Unit tests for the rules CRUD API."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# GET /api/rules
# ---------------------------------------------------------------------------


async def test_list_rules_empty(client: AsyncClient) -> None:
    resp = await client.get("/api/rules")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_rules_returns_sorted_by_priority(client: AsyncClient) -> None:
    await client.post(
        "/api/rules",
        json={"name": "Low priority", "priority": 200, "destination": "/low"},
    )
    await client.post(
        "/api/rules",
        json={"name": "High priority", "priority": 10, "destination": "/high"},
    )
    resp = await client.get("/api/rules")
    rules = resp.json()
    assert rules[0]["priority"] <= rules[1]["priority"]


# ---------------------------------------------------------------------------
# POST /api/rules
# ---------------------------------------------------------------------------


async def test_create_rule_minimal(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/rules",
        json={"name": "Video Rule", "destination": "/videos"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Video Rule"
    assert body["destination"] == "/videos"
    assert body["enabled"] is True
    assert body["priority"] == 100
    assert body["conditions"] == []
    assert "id" in body


async def test_create_rule_with_conditions(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/rules",
        json={
            "name": "MKV Rule",
            "destination": "/media/videos",
            "priority": 10,
            "conditions": [
                {"condition_type": "extension", "value": ".mkv"},
                {"condition_type": "tracker", "value": "example.com"},
            ],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["conditions"]) == 2
    types = {c["condition_type"] for c in body["conditions"]}
    assert types == {"extension", "tracker"}


async def test_create_rule_missing_name_returns_422(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/rules",
        json={"destination": "/videos"},
    )
    assert resp.status_code == 422


async def test_create_rule_missing_destination_returns_422(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/rules",
        json={"name": "Oops"},
    )
    assert resp.status_code == 422


async def test_create_rule_invalid_condition_type_returns_422(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/api/rules",
        json={
            "name": "Bad Rule",
            "destination": "/x",
            "conditions": [{"condition_type": "invalid", "value": ".mkv"}],
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /api/rules/{id}
# ---------------------------------------------------------------------------


async def test_patch_rule_name(client: AsyncClient) -> None:
    create = await client.post(
        "/api/rules", json={"name": "Old Name", "destination": "/dl"}
    )
    rule_id = create.json()["id"]

    resp = await client.patch(f"/api/rules/{rule_id}", json={"name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["destination"] == "/dl"  # unchanged


async def test_patch_rule_enabled(client: AsyncClient) -> None:
    create = await client.post(
        "/api/rules", json={"name": "Rule", "destination": "/dl"}
    )
    rule_id = create.json()["id"]

    resp = await client.patch(f"/api/rules/{rule_id}", json={"enabled": False})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


async def test_patch_rule_replaces_conditions(client: AsyncClient) -> None:
    create = await client.post(
        "/api/rules",
        json={
            "name": "Rule",
            "destination": "/dl",
            "conditions": [{"condition_type": "extension", "value": ".mkv"}],
        },
    )
    rule_id = create.json()["id"]

    resp = await client.patch(
        f"/api/rules/{rule_id}",
        json={
            "conditions": [
                {"condition_type": "tracker", "value": "example.com"},
                {"condition_type": "extension", "value": ".flac"},
            ]
        },
    )
    assert resp.status_code == 200
    cond_types = {c["condition_type"] for c in resp.json()["conditions"]}
    assert cond_types == {"tracker", "extension"}
    assert len(resp.json()["conditions"]) == 2


async def test_patch_rule_not_found(client: AsyncClient) -> None:
    resp = await client.patch("/api/rules/99999", json={"name": "x"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/rules/{id}
# ---------------------------------------------------------------------------


async def test_delete_rule(client: AsyncClient) -> None:
    create = await client.post(
        "/api/rules", json={"name": "ToDelete", "destination": "/del"}
    )
    rule_id = create.json()["id"]

    resp = await client.delete(f"/api/rules/{rule_id}")
    assert resp.status_code == 204

    # Confirm it's gone
    list_resp = await client.get("/api/rules")
    ids = [r["id"] for r in list_resp.json()]
    assert rule_id not in ids


async def test_delete_rule_not_found(client: AsyncClient) -> None:
    resp = await client.delete("/api/rules/99999")
    assert resp.status_code == 404
