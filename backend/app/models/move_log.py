from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MoveLog(Base):
    __tablename__ = "move_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    torrent_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    torrent_name: Mapped[str] = mapped_column(String, nullable=False)
    rule_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rule_name: Mapped[str | None] = mapped_column(String, nullable=True)
    source_path: Mapped[str] = mapped_column(String, nullable=False)
    destination_path: Mapped[str] = mapped_column(String, nullable=False)
    # "success" | "skipped" | "error"
    status: Mapped[str] = mapped_column(String, nullable=False, default="success")
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    def __repr__(self) -> str:
        return (
            f"MoveLog(id={self.id!r}, torrent={self.torrent_name!r}, "
            f"status={self.status!r})"
        )
