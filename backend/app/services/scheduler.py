"""
APScheduler polling job.

A single AsyncIOScheduler runs in the background. Every `polling_interval_seconds`
seconds (from the Settings store) it:
  1. Reads the polling interval and Deluge credentials from the DB.
  2. Connects to Deluge, fetches all torrents.
  3. Loads enabled rules.
  4. Evaluates rules → executes moves.
  5. Writes MoveLog entries.
  6. Disconnects.
"""
from __future__ import annotations

import logging
from typing import Any

from apscheduler.schedulers.asyncio import (  # type: ignore[import-untyped,unused-ignore]
    AsyncIOScheduler,
)
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.move_log import MoveLog
from app.models.rule import Rule
from app.models.setting import Setting
from app.services.deluge import DelugeClient
from app.services.engine import execute_moves, find_matches

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None

_DEFAULT_INTERVAL = 300  # seconds


async def _load_settings() -> dict[str, str]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Setting))
        return {s.key: s.value for s in result.scalars().all()}


async def _load_rules() -> list[Rule]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Rule).order_by(Rule.priority, Rule.id)
        )
        return list(result.scalars().all())


async def _write_logs(results: list[dict[str, Any]]) -> None:
    if not results:
        return
    async with AsyncSessionLocal() as session:
        for entry in results:
            session.add(MoveLog(**entry))
        await session.commit()


async def run_poll_cycle() -> None:
    """Single poll cycle: connect → evaluate rules → move → log."""
    logger.info("Poll cycle started.")
    try:
        settings = await _load_settings()
    except Exception as exc:
        logger.error("Failed to load settings for poll cycle: %s", exc)
        return

    host = settings.get("deluge_host", "")
    if not host:
        logger.debug("Deluge host not configured — skipping poll cycle.")
        return

    port_str = settings.get("deluge_port", "58846")
    try:
        port = int(port_str)
    except ValueError:
        logger.warning("Invalid Deluge port %r — skipping poll cycle.", port_str)
        return

    client = DelugeClient(
        host=host,
        port=port,
        username=settings.get("deluge_username", ""),
        password=settings.get("deluge_password", ""),
    )
    try:
        await client.connect()
        torrents = await client.get_torrents()
        rules = await _load_rules()
        matches = find_matches(rules, torrents)
        if matches:
            logger.info("Rule engine found %d move(s) to execute.", len(matches))
        results = await execute_moves(matches, client)
        await _write_logs(results)
    except Exception as exc:
        logger.error("Poll cycle error: %s", exc)
    finally:
        await client.disconnect()

    logger.info("Poll cycle complete.")


def _get_interval(settings: dict[str, str] | None = None) -> int:
    if settings is None:
        return _DEFAULT_INTERVAL
    try:
        return max(10, int(settings.get("polling_interval_seconds", _DEFAULT_INTERVAL)))
    except ValueError:
        return _DEFAULT_INTERVAL


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        run_poll_cycle,
        trigger="interval",
        seconds=_DEFAULT_INTERVAL,
        id="poll_cycle",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("Scheduler started (interval=%ds).", _DEFAULT_INTERVAL)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped.")


def reschedule(interval_seconds: int) -> None:
    """Update the polling interval at runtime."""
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.reschedule_job(
        "poll_cycle",
        trigger="interval",
        seconds=max(10, interval_seconds),
    )
    logger.info("Scheduler rescheduled to %ds.", interval_seconds)
