"""Move log read API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.move_log import MoveLog
from app.schemas.move_log import MoveLogSchema

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=list[MoveLogSchema])
async def list_logs(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[MoveLogSchema]:
    """Return move log entries, newest first."""
    q = select(MoveLog).order_by(MoveLog.created_at.desc()).offset(offset).limit(limit)
    if status is not None:
        q = q.where(MoveLog.status == status)
    result = await db.execute(q)
    logs = result.scalars().all()
    return [MoveLogSchema.model_validate(entry) for entry in logs]
