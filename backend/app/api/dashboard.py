"""Dashboard stats endpoint."""
from __future__ import annotations

import asyncio
import logging
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.move_log import MoveLog
from app.models.rule import Rule
from app.models.setting import Setting
from app.schemas.dashboard import DashboardStats
from app.services.deluge import DelugeClient
from app.services.engine import evaluate_rule

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_RPC_TIMEOUT = 5.0


async def _settings_dict(db: AsyncSession) -> dict[str, str]:
    result = await db.execute(select(Setting))
    return {s.key: s.value for s in result.scalars().all()}


@router.get("", response_model=DashboardStats)
async def get_dashboard(db: AsyncSession = Depends(get_db)) -> DashboardStats:
    settings = await _settings_dict(db)
    host = settings.get("deluge_host", "")

    connected = False
    daemon_version: str | None = None
    error: str | None = None
    total_torrents: int | None = None
    matching_torrents: int | None = None

    if not host:
        error = "Deluge host is not configured."
    else:
        port_str = settings.get("deluge_port", "58846")
        try:
            port = int(port_str)
        except ValueError:
            error = f"Invalid port: {port_str!r}"
            port = 0

        if port:
            client = DelugeClient(
                host=host,
                port=port,
                username=settings.get("deluge_username", ""),
                password=settings.get("deluge_password", ""),
            )
            try:
                await asyncio.wait_for(client.connect(), timeout=_RPC_TIMEOUT)
                daemon_version = client.daemon_version
                torrents = await client.get_torrents()
                total_torrents = len(torrents)

                rules_result = await db.execute(
                    select(Rule)
                    .where(Rule.enabled.is_(True))
                    .order_by(Rule.priority, Rule.id)
                )
                rules = list(rules_result.scalars().all())

                matched_hashes: set[str] = set()
                for rule in rules:
                    if not rule.conditions:
                        continue
                    for torrent in torrents:
                        if torrent.hash in matched_hashes:
                            continue
                        if torrent.save_path == rule.destination:
                            continue
                        if evaluate_rule(rule, torrent):
                            matched_hashes.add(torrent.hash)
                matching_torrents = len(matched_hashes)

                await client.disconnect()
                connected = True
            except TimeoutError:
                error = f"Timeout connecting to {host}:{port}"
            except Exception as exc:
                msg = str(exc)
                password = settings.get("deluge_password", "")
                if password:
                    msg = msg.replace(password, "***")
                error = msg

    today = date.today().isoformat()
    moves_today_result = await db.execute(
        select(func.count(MoveLog.id)).where(
            func.date(MoveLog.created_at) == today,
            MoveLog.status == "success",
        )
    )
    moves_today: int = moves_today_result.scalar_one()

    moves_all_time_result = await db.execute(
        select(func.count(MoveLog.id)).where(MoveLog.status == "success")
    )
    moves_all_time: int = moves_all_time_result.scalar_one()

    return DashboardStats(
        connected=connected,
        daemon_version=daemon_version,
        error=error,
        total_torrents=total_torrents,
        matching_torrents=matching_torrents,
        moves_today=moves_today,
        moves_all_time=moves_all_time,
    )
