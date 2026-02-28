"""Torrent listing endpoint."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.torrent import TorrentFileSchema, TorrentSchema
from app.services.deluge import DelugeClient, TorrentInfo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/torrents", tags=["torrents"])


async def _settings_dict(db: AsyncSession) -> dict[str, str]:
    from sqlalchemy import select

    from app.models.setting import Setting

    result = await db.execute(select(Setting))
    return {s.key: s.value for s in result.scalars().all()}


def _torrent_to_schema(t: TorrentInfo) -> TorrentSchema:
    return TorrentSchema(
        hash=t.hash,
        name=t.name,
        save_path=t.save_path,
        state=t.state,
        progress=t.progress,
        files=[
            TorrentFileSchema(path=f.path, size=f.size, extension=f.extension)
            for f in t.files
        ],
        tracker_domains=t.tracker_domains,
    )


@router.get("", response_model=list[TorrentSchema])
async def list_torrents(db: AsyncSession = Depends(get_db)) -> list[TorrentSchema]:
    """
    Fetch normalised torrent list from Deluge.
    Returns HTTP 503 if Deluge is not reachable.
    """
    settings = await _settings_dict(db)
    host = settings.get("deluge_host", "")
    if not host:
        raise HTTPException(status_code=503, detail="Deluge host not configured.")

    port_str = settings.get("deluge_port", "58846")
    try:
        port = int(port_str)
    except ValueError as err:
        raise HTTPException(
            status_code=503, detail=f"Invalid port: {port_str!r}"
        ) from err

    client = DelugeClient(
        host=host,
        port=port,
        username=settings.get("deluge_username", ""),
        password=settings.get("deluge_password", ""),
    )
    try:
        await client.connect()
        torrents = await client.get_torrents()
        await client.disconnect()
        return [_torrent_to_schema(t) for t in torrents]
    except Exception as exc:
        msg = str(exc)
        password = settings.get("deluge_password", "")
        if password:
            msg = msg.replace(password, "***")
        logger.warning("Failed to fetch torrents: %s", msg)
        raise HTTPException(status_code=503, detail=msg) from exc
