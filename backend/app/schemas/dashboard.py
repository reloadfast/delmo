from __future__ import annotations

from pydantic import BaseModel


class DashboardStats(BaseModel):
    connected: bool
    daemon_version: str | None = None
    error: str | None = None
    total_torrents: int | None = None
    matching_torrents: int | None = None
    moves_today: int
    moves_all_time: int
