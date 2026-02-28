"""WebSocket endpoint: GET /api/ws/logs — streams new MoveLog entries."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.broadcast import log_broadcaster

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["ws"])


@router.websocket("/logs")
async def ws_logs(websocket: WebSocket) -> None:
    """Stream new MoveLog entries as JSON to connected clients."""
    await websocket.accept()
    logger.info("WebSocket log client connected.")
    async with log_broadcaster.subscribe() as queue:
        try:
            while True:
                entry = await queue.get()
                await websocket.send_text(json.dumps(entry, default=str))
        except WebSocketDisconnect:
            logger.info("WebSocket log client disconnected.")
