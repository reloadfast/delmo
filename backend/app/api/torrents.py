"""Torrent listing endpoint."""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.torrent import TorrentFileSchema, TorrentSchema
from app.services.deluge import _TORRENT_KEYS, DelugeClient, TorrentInfo, _decode_keys

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


@router.get("/debug/raw", response_model=list[dict[str, Any]], include_in_schema=False)
async def raw_torrent_debug(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    """
    Return the first 3 torrents' raw decoded data from Deluge, before normalisation.
    Used to diagnose file/tracker structure differences across Deluge versions.
    NOT included in the OpenAPI schema.
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
        raw: dict[str, Any] = await client._call(  # noqa: SLF001
            "core.get_torrents_status", {}, _TORRENT_KEYS
        )
        raw = _decode_keys(raw)
        await client.disconnect()
    except Exception as exc:
        msg = str(exc)
        password = settings.get("deluge_password", "")
        if password:
            msg = msg.replace(password, "***")
        raise HTTPException(status_code=503, detail=msg) from exc

    sample = list(raw.items())[:3]
    return [
        {"hash": h, **{k: v for k, v in d.items() if k != "password"}}
        for h, d in sample
    ]
