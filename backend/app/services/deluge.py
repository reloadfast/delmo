"""
Deluge RPC client wrapper.

All interaction with the Deluge daemon goes through DelugeClient.
Credentials are read from the Settings store — never hardcoded or from env vars.
Passwords are never logged.
"""
from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class TorrentFile:
    path: str
    size: int

    @property
    def extension(self) -> str:
        """Return lowercase extension including the dot, e.g. '.mkv'."""
        parts = self.path.rsplit(".", 1)
        return f".{parts[1].lower()}" if len(parts) == 2 else ""


@dataclass
class TorrentInfo:
    hash: str
    name: str
    save_path: str
    state: str
    progress: float
    files: list[TorrentFile] = field(default_factory=list)
    tracker_domains: list[str] = field(default_factory=list)


@dataclass
class ConnectionStatus:
    connected: bool
    daemon_version: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Helper — domain extraction
# ---------------------------------------------------------------------------

_DOMAIN_RE = re.compile(r"^(?:https?://)?([^/:]+)", re.IGNORECASE)


def _extract_domain(tracker_url: str) -> str:
    """Return the hostname from a tracker announce URL.

    Handles http/https/udp schemes and bare hostnames (no scheme).
    """
    if not tracker_url:
        return ""
    try:
        url = tracker_url if "://" in tracker_url else f"http://{tracker_url}"
        parsed = urlparse(url)
        return (parsed.hostname or "").lower()
    except Exception:
        m = _DOMAIN_RE.match(tracker_url)
        return m.group(1).lower() if m else ""


# ---------------------------------------------------------------------------
# Move method detection
# ---------------------------------------------------------------------------

_MOVE_METHOD_CACHE: dict[str, str] = {}


def _select_move_method(daemon_version: str | None) -> str:
    """
    Return the correct RPC method name for moving torrent storage.

    Deluge 2.x uses `core.move_storage`; older versions use `core.move_torrent_data`.
    Falls back to `core.move_storage` when version cannot be parsed.
    """
    if daemon_version is None:
        return "core.move_storage"
    cached = _MOVE_METHOD_CACHE.get(daemon_version)
    if cached:
        return cached
    try:
        major = int(daemon_version.split(".")[0])
        method = "core.move_storage" if major >= 2 else "core.move_torrent_data"
    except (ValueError, IndexError):
        method = "core.move_storage"
    _MOVE_METHOD_CACHE[daemon_version] = method
    return method


# ---------------------------------------------------------------------------
# DelugeClient
# ---------------------------------------------------------------------------

_TORRENT_KEYS = [
    "name",
    "save_path",
    "files",
    "trackers",
    "state",
    "progress",
]


class DelugeClient:
    """
    Async wrapper around the synchronous `deluge_client.DelugeRPCClient`.

    All blocking RPC calls are dispatched to the default thread-pool executor
    so they do not stall the asyncio event loop.

    Usage::

        async with DelugeClient(host, port, username, password) as client:
            torrents = await client.get_torrents()
    """

    def __init__(self, host: str, port: int, username: str, password: str) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password  # never logged
        self._rpc: Any = None  # deluge_client.DelugeRPCClient instance
        self._daemon_version: str | None = None
        self._move_method: str = "core.move_storage"

    # ── Connection lifecycle ─────────────────────────────────────────────────

    async def connect(self) -> None:
        """Connect and authenticate. Retries up to 3 times with backoff."""
        from deluge_client import (
            DelugeRPCClient,  # type: ignore[import-untyped,unused-ignore]
        )

        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                loop = asyncio.get_running_loop()
                rpc = await loop.run_in_executor(
                    None,
                    lambda: DelugeRPCClient(
                        self._host, self._port, self._username, self._password
                    ),
                )
                await loop.run_in_executor(None, rpc.connect)
                self._rpc = rpc
                self._daemon_version = await self._fetch_daemon_version()
                self._move_method = _select_move_method(self._daemon_version)
                logger.info(
                    "Connected to Deluge %s at %s:%s",
                    self._daemon_version,
                    self._host,
                    self._port,
                )
                return
            except Exception as exc:
                last_error = exc
                pw = self._password
                masked_exc = str(exc).replace(pw, "***") if pw else str(exc)
                logger.warning("Connect attempt %d failed: %s", attempt, masked_exc)
                if attempt < 3:
                    await asyncio.sleep(2**attempt)

        raise ConnectionError(
            f"Failed to connect to Deluge at {self._host}:{self._port} "
            f"after 3 attempts: {last_error}"
        ) from last_error

    async def disconnect(self) -> None:
        if self._rpc is not None:
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._rpc.disconnect)
            except Exception:  # noqa: S110 — intentional: disconnect best-effort
                logger.debug("Disconnect RPC call failed (ignored).")
            self._rpc = None
            logger.info("Disconnected from Deluge.")

    def is_connected(self) -> bool:
        return self._rpc is not None

    async def __aenter__(self) -> DelugeClient:
        await self.connect()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.disconnect()

    # ── Internal helpers ─────────────────────────────────────────────────────

    async def _call(self, method: str, *args: Any) -> Any:
        """Run a synchronous RPC call in the thread executor."""
        if self._rpc is None:
            raise RuntimeError("Not connected to Deluge daemon.")
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, lambda: self._rpc.call(method, *args)
        )

    async def _fetch_daemon_version(self) -> str | None:
        try:
            info = await self._call("daemon.info")
            return str(info) if info else None
        except Exception:
            return None

    # ── Public API ───────────────────────────────────────────────────────────

    @property
    def daemon_version(self) -> str | None:
        return self._daemon_version

    @property
    def move_method(self) -> str:
        return self._move_method

    async def get_status(self) -> ConnectionStatus:
        """Check liveness and return a ConnectionStatus."""
        if not self.is_connected():
            return ConnectionStatus(connected=False, error="Not connected.")
        try:
            version = await self._fetch_daemon_version()
            return ConnectionStatus(connected=True, daemon_version=version)
        except Exception as exc:
            return ConnectionStatus(connected=False, error=str(exc))

    async def get_torrents(self) -> list[TorrentInfo]:
        """Fetch and normalise all torrents from the Deluge daemon."""
        raw: dict[str, dict[str, Any]] = await self._call(
            "core.get_torrents_status", {}, _TORRENT_KEYS
        )
        results: list[TorrentInfo] = []
        for torrent_hash, data in raw.items():
            files = [
                TorrentFile(path=f.get("path", ""), size=f.get("size", 0))
                for f in (data.get("files") or [])
            ]
            tracker_domains = list(
                {
                    _extract_domain(t.get("url", ""))
                    for t in (data.get("trackers") or [])
                    if t.get("url")
                }
            )
            results.append(
                TorrentInfo(
                    hash=torrent_hash,
                    name=data.get("name", ""),
                    save_path=data.get("save_path", ""),
                    state=data.get("state", ""),
                    progress=float(data.get("progress", 0.0)),
                    files=files,
                    tracker_domains=tracker_domains,
                )
            )
        return results

    async def move_torrent(self, torrent_hash: str, destination: str) -> None:
        """
        Move torrent storage to *destination* via the version-appropriate RPC method.

        Tries `core.move_storage` first; if the daemon raises `MethodNotFound`
        (Deluge 1.x), retries with `core.move_torrent_data`.
        """
        try:
            await self._call(self._move_method, torrent_hash, destination)
        except Exception as exc:
            exc_name = type(exc).__name__
            exc_msg = str(exc).lower()
            if "MethodNotFound" in exc_name or "not found" in exc_msg:
                fallback = (
                    "core.move_torrent_data"
                    if self._move_method == "core.move_storage"
                    else "core.move_storage"
                )
                logger.warning(
                    "Method %s not found; retrying with %s",
                    self._move_method,
                    fallback,
                )
                self._move_method = fallback
                await self._call(self._move_method, torrent_hash, destination)
            else:
                raise


# ---------------------------------------------------------------------------
# Module-level shared client (managed by lifespan)
# ---------------------------------------------------------------------------

_shared_client: DelugeClient | None = None


def get_shared_client() -> DelugeClient | None:
    return _shared_client


def set_shared_client(client: DelugeClient | None) -> None:
    global _shared_client
    _shared_client = client


@asynccontextmanager
async def build_client_from_settings(
    settings: dict[str, str],
) -> AsyncGenerator[DelugeClient, None]:
    """Context manager that builds a DelugeClient from the settings dict."""
    host = settings.get("deluge_host", "")
    port_str = settings.get("deluge_port", "58846")
    username = settings.get("deluge_username", "")
    password = settings.get("deluge_password", "")

    if not host:
        raise ValueError("Deluge host is not configured.")

    try:
        port = int(port_str)
    except ValueError as err:
        raise ValueError(f"Invalid Deluge port: {port_str!r}") from err

    client = DelugeClient(host, port, username, password)
    try:
        await client.connect()
        yield client
    finally:
        await client.disconnect()
