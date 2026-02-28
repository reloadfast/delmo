from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    pass


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    conditions: Mapped[list[RuleCondition]] = relationship(
        "RuleCondition",
        back_populates="rule",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"Rule(id={self.id!r}, name={self.name!r}, priority={self.priority!r})"


class RuleCondition(Base):
    __tablename__ = "rule_conditions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False
    )
    condition_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # "extension" | "tracker"
    value: Mapped[str] = mapped_column(String, nullable=False)

    rule: Mapped[Rule] = relationship("Rule", back_populates="conditions")

    def __repr__(self) -> str:
        return (
            f"RuleCondition(id={self.id!r}, type={self.condition_type!r}, "
            f"value={self.value!r})"
        )
