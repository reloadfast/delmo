"""Scheduler control endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks

from app.services.scheduler import run_poll_cycle

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.post("/run-now", status_code=202)
async def run_now(background_tasks: BackgroundTasks) -> dict[str, str]:
    """Trigger an immediate poll cycle in the background."""
    logger.info("Manual run-now triggered via API.")
    background_tasks.add_task(run_poll_cycle)
    return {"status": "triggered"}
