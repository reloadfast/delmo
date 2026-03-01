"""Connection health-check and test endpoints."""
import asyncio
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.connection import ConnectionStatusResponse, ConnectionTestRequest
from app.services.deluge import DelugeClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/connection", tags=["connection"])

_RPC_TIMEOUT = 5.0  # seconds


async def _settings_dict(db: AsyncSession) -> dict[str, str]:
    from sqlalchemy import select

    from app.models.setting import Setting

    result = await db.execute(select(Setting))
    return {s.key: s.value for s in result.scalars().all()}


@router.get("/status", response_model=ConnectionStatusResponse)
async def connection_status(
    db: AsyncSession = Depends(get_db),
) -> ConnectionStatusResponse:
    """
    Check live connectivity to the configured Deluge daemon.
    Returns connected=false with an error message on any failure.
    """
    settings = await _settings_dict(db)
    host = settings.get("deluge_host", "")
    if not host:
        return ConnectionStatusResponse(
            connected=False, error="Deluge host is not configured."
        )

    port_str = settings.get("deluge_port", "58846")
    try:
        port = int(port_str)
    except ValueError:
        return ConnectionStatusResponse(
            connected=False, error=f"Invalid port: {port_str!r}"
        )

    client = DelugeClient(
        host=host,
        port=port,
        username=settings.get("deluge_username", ""),
        password=settings.get("deluge_password", ""),
    )
    try:
        await asyncio.wait_for(client.connect(), timeout=_RPC_TIMEOUT)
        version = client.daemon_version
        label_plugin = await client.check_label_plugin()
        await client.disconnect()
        return ConnectionStatusResponse(
            connected=True,
            daemon_version=version,
            label_plugin_available=label_plugin,
        )
    except TimeoutError:
        return ConnectionStatusResponse(
            connected=False,
            error=f"Timeout after {_RPC_TIMEOUT:.0f}s connecting to {host}:{port}",
        )
    except ConnectionError as exc:
        msg = str(exc)
        # Mask any accidental password leakage
        password = settings.get("deluge_password", "")
        if password:
            msg = msg.replace(password, "***")
        return ConnectionStatusResponse(connected=False, error=msg)
    except Exception as exc:
        msg = str(exc)
        password = settings.get("deluge_password", "")
        if password:
            msg = msg.replace(password, "***")
        return ConnectionStatusResponse(connected=False, error=msg)


@router.post("/test", response_model=ConnectionStatusResponse)
async def test_connection(
    payload: ConnectionTestRequest,
) -> ConnectionStatusResponse:
    """
    Test connectivity using credentials from the request body (not saved settings).
    Used by the Settings page to verify before saving.
    """
    client = DelugeClient(
        host=payload.host,
        port=payload.port,
        username=payload.username,
        password=payload.password,
    )
    try:
        await asyncio.wait_for(client.connect(), timeout=_RPC_TIMEOUT)
        version = client.daemon_version
        await client.disconnect()
        return ConnectionStatusResponse(connected=True, daemon_version=version)
    except TimeoutError:
        return ConnectionStatusResponse(
            connected=False,
            error=f"Timeout after {_RPC_TIMEOUT:.0f}s connecting to "
            f"{payload.host}:{payload.port}",
        )
    except Exception as exc:
        msg = str(exc)
        if payload.password:
            msg = msg.replace(payload.password, "***")
        return ConnectionStatusResponse(connected=False, error=msg)
