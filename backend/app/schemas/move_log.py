from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MoveLogSchema(BaseModel):
    id: int
    torrent_hash: str
    torrent_name: str
    rule_id: int | None
    rule_name: str | None
    source_path: str
    destination_path: str
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
