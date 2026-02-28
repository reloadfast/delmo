"""Unit tests for the scheduler service."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services import scheduler as sched_module
from app.services.scheduler import (
    _get_interval,
    reschedule,
    run_poll_cycle,
    start_scheduler,
    stop_scheduler,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _get_interval
# ---------------------------------------------------------------------------


def test_get_interval_default() -> None:
    assert _get_interval(None) == 300


def test_get_interval_valid() -> None:
    assert _get_interval({"polling_interval_seconds": "60"}) == 60


def test_get_interval_invalid_falls_back() -> None:
    assert _get_interval({"polling_interval_seconds": "bad"}) == 300


def test_get_interval_minimum_enforced() -> None:
    assert _get_interval({"polling_interval_seconds": "5"}) == 10


# ---------------------------------------------------------------------------
# start / stop / reschedule
# ---------------------------------------------------------------------------


def test_start_stop_scheduler() -> None:
    # Ensure clean state
    sched_module._scheduler = None
    start_scheduler()
    assert sched_module._scheduler is not None
    stop_scheduler()
    assert sched_module._scheduler is None


def test_start_scheduler_idempotent() -> None:
    sched_module._scheduler = None
    start_scheduler()
    first = sched_module._scheduler
    start_scheduler()  # should not replace
    assert sched_module._scheduler is first
    stop_scheduler()


def test_stop_scheduler_noop_when_not_running() -> None:
    sched_module._scheduler = None
    stop_scheduler()  # should not raise
    assert sched_module._scheduler is None


def test_reschedule_noop_when_not_running() -> None:
    sched_module._scheduler = None
    reschedule(60)  # should not raise


def test_reschedule_when_running() -> None:
    sched_module._scheduler = None
    start_scheduler()
    reschedule(120)  # should not raise
    stop_scheduler()


# ---------------------------------------------------------------------------
# run_poll_cycle
# ---------------------------------------------------------------------------


async def test_run_poll_cycle_no_host() -> None:
    """Cycle exits early when Deluge host is not configured."""
    settings = {"deluge_host": "", "deluge_port": "58846"}
    with patch.object(sched_module, "_load_settings", AsyncMock(return_value=settings)):
        # Should not raise
        await run_poll_cycle()


async def test_run_poll_cycle_invalid_port() -> None:
    settings = {"deluge_host": "192.168.1.10", "deluge_port": "notanumber"}
    with patch.object(sched_module, "_load_settings", AsyncMock(return_value=settings)):
        await run_poll_cycle()


async def test_run_poll_cycle_load_settings_error() -> None:
    with patch.object(
        sched_module,
        "_load_settings",
        AsyncMock(side_effect=RuntimeError("DB error")),
    ):
        await run_poll_cycle()  # should not raise


async def test_run_poll_cycle_success() -> None:
    """Full cycle with mocked Deluge client — no actual RPC calls."""
    from app.services.deluge import TorrentInfo

    settings = {
        "deluge_host": "192.168.1.10",
        "deluge_port": "58846",
        "deluge_username": "u",
        "deluge_password": "p",
    }
    mock_torrent = TorrentInfo(
        hash="abc", name="Movie", save_path="/dl",
        state="Seeding", progress=100.0, files=[], tracker_domains=[],
    )
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.disconnect = AsyncMock()
    mock_client.get_torrents = AsyncMock(return_value=[mock_torrent])

    with (
        patch.object(sched_module, "_load_settings", AsyncMock(return_value=settings)),
        patch.object(sched_module, "_load_rules", AsyncMock(return_value=[])),
        patch.object(sched_module, "_write_logs", AsyncMock()),
        patch("app.services.scheduler.DelugeClient", return_value=mock_client),
    ):
        await run_poll_cycle()

    mock_client.connect.assert_called_once()
    mock_client.get_torrents.assert_called_once()
    mock_client.disconnect.assert_called_once()


async def test_run_poll_cycle_connect_error() -> None:
    settings = {
        "deluge_host": "192.168.1.10",
        "deluge_port": "58846",
        "deluge_username": "u",
        "deluge_password": "p",
    }
    mock_client = MagicMock()
    mock_client.connect = AsyncMock(side_effect=ConnectionError("refused"))
    mock_client.disconnect = AsyncMock()

    with (
        patch.object(sched_module, "_load_settings", AsyncMock(return_value=settings)),
        patch("app.services.scheduler.DelugeClient", return_value=mock_client),
    ):
        await run_poll_cycle()  # should not raise; logs error

    mock_client.disconnect.assert_called_once()
