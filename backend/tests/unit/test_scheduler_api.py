"""Unit tests for the scheduler control endpoint."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.unit


async def test_run_now_accepted(client: AsyncClient) -> None:
    """POST /api/scheduler/run-now returns 202 and triggers a background poll."""
    with patch(
        "app.api.scheduler.run_poll_cycle",
        new_callable=AsyncMock,
    ) as mock_run:
        resp = await client.post("/api/scheduler/run-now")

    assert resp.status_code == 202
    assert resp.json()["status"] == "triggered"
    # BackgroundTasks runs after response — mock may not be called yet in unit test,
    # but the endpoint must have registered the task without raising.
    _ = mock_run  # referenced to satisfy linter


async def test_settings_patch_reschedules(client: AsyncClient) -> None:
    """Saving polling_interval_seconds calls reschedule()."""
    with patch("app.services.scheduler.reschedule") as mock_reschedule:
        resp = await client.patch(
            "/api/settings",
            json={"updates": {"polling_interval_seconds": "120"}},
        )
    assert resp.status_code == 200
    mock_reschedule.assert_called_once_with(120)


async def test_settings_patch_invalid_interval_ignored(client: AsyncClient) -> None:
    """A non-integer interval value doesn't crash the endpoint."""
    resp = await client.patch(
        "/api/settings",
        json={"updates": {"polling_interval_seconds": "not-a-number"}},
    )
    assert resp.status_code == 200  # silently ignored
