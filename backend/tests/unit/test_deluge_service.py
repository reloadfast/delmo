"""Unit tests for the DelugeClient service layer."""
from unittest.mock import MagicMock

import pytest
from app.services.deluge import (
    DelugeClient,
    TorrentFile,
    _decode_keys,
    _extract_domain,
    _select_move_method,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Domain extraction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://tracker.example.com:1234/announce", "tracker.example.com"),
        ("http://tracker.example.com/announce", "tracker.example.com"),
        ("udp://tracker.example.com:6969", "tracker.example.com"),
        ("tracker.example.com", "tracker.example.com"),
        ("tracker.example.com:1234/announce", "tracker.example.com"),
        ("", ""),
    ],
)
def test_extract_domain(url: str, expected: str) -> None:
    assert _extract_domain(url) == expected


# ---------------------------------------------------------------------------
# Move method selection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "version,expected_method",
    [
        ("2.1.1", "core.move_storage"),
        ("2.0.0", "core.move_storage"),
        ("1.3.15", "core.move_torrent_data"),
        (None, "core.move_storage"),
        ("invalid", "core.move_storage"),
        ("3.0.0", "core.move_storage"),
    ],
)
def test_select_move_method(version: str | None, expected_method: str) -> None:
    assert _select_move_method(version) == expected_method


# ---------------------------------------------------------------------------
# TorrentFile extension extraction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path,expected_ext",
    [
        ("video/movie.mkv", ".mkv"),
        ("audio/track.FLAC", ".flac"),
        ("doc.pdf", ".pdf"),
        ("noextension", ""),
        ("path/to/file.tar.gz", ".gz"),
    ],
)
def test_torrent_file_extension(path: str, expected_ext: str) -> None:
    f = TorrentFile(path=path, size=0)
    assert f.extension == expected_ext


# ---------------------------------------------------------------------------
# DelugeClient — state helpers (no real RPC needed)
# ---------------------------------------------------------------------------


def _make_client_with_mock_rpc(
    version: str = "2.1.1",
) -> tuple[DelugeClient, MagicMock]:
    """Return a DelugeClient with a pre-injected mock RPC handle."""
    client = DelugeClient("localhost", 58846, "user", "pass")
    mock_rpc = MagicMock()
    mock_rpc.call = MagicMock(return_value=None)
    client._rpc = mock_rpc
    client._daemon_version = version
    client._move_method = _select_move_method(version)
    return client, mock_rpc


async def test_client_is_connected_when_rpc_set() -> None:
    client, _ = _make_client_with_mock_rpc()
    assert client.is_connected()


async def test_client_not_connected_initially() -> None:
    client = DelugeClient("localhost", 58846, "user", "pass")
    assert not client.is_connected()


async def test_client_disconnect_clears_rpc() -> None:
    client, mock_rpc = _make_client_with_mock_rpc()
    await client.disconnect()
    assert not client.is_connected()
    mock_rpc.disconnect.assert_called_once()


async def test_client_daemon_version_and_move_method() -> None:
    client, _ = _make_client_with_mock_rpc(version="2.1.1")
    assert client.daemon_version == "2.1.1"
    assert client.move_method == "core.move_storage"

    client2, _ = _make_client_with_mock_rpc(version="1.3.15")
    assert client2.move_method == "core.move_torrent_data"


# ---------------------------------------------------------------------------
# DelugeClient — get_torrents normalisation
# ---------------------------------------------------------------------------


async def test_get_torrents_normalises_fields() -> None:
    """get_torrents() correctly maps raw RPC data to TorrentInfo objects."""
    raw = {
        "abc123": {
            "name": "My Movie",
            "save_path": "/downloads",
            "files": [{"path": "movie.mkv", "size": 1_000_000_000}],
            "trackers": [{"url": "https://tracker.example.com/announce"}],
            "state": "Seeding",
            "progress": 100.0,
        }
    }
    client, mock_rpc = _make_client_with_mock_rpc()
    mock_rpc.call = MagicMock(return_value=raw)

    torrents = await client.get_torrents()
    assert len(torrents) == 1
    t = torrents[0]
    assert t.hash == "abc123"
    assert t.name == "My Movie"
    assert t.save_path == "/downloads"
    assert t.state == "Seeding"
    assert t.progress == 100.0
    assert len(t.files) == 1
    assert t.files[0].extension == ".mkv"
    assert "tracker.example.com" in t.tracker_domains


async def test_get_torrents_handles_empty() -> None:
    client, mock_rpc = _make_client_with_mock_rpc()
    mock_rpc.call = MagicMock(return_value={})
    assert await client.get_torrents() == []


async def test_get_torrents_deduplicates_tracker_domains() -> None:
    raw = {
        "abc123": {
            "name": "Test",
            "save_path": "/dl",
            "files": [],
            "trackers": [
                {"url": "https://tracker.example.com/announce"},
                {"url": "http://tracker.example.com/announce2"},
            ],
            "state": "Seeding",
            "progress": 100.0,
        }
    }
    client, mock_rpc = _make_client_with_mock_rpc()
    mock_rpc.call = MagicMock(return_value=raw)

    torrents = await client.get_torrents()
    assert torrents[0].tracker_domains.count("tracker.example.com") == 1


async def test_get_torrents_bytes_keys_decoded() -> None:
    """Tracker domains are extracted even when msgpack returns bytes keys."""
    raw = {
        b"abc123": {
            b"name": b"My Movie",
            b"save_path": b"/downloads",
            b"files": [{b"path": b"movie.mkv", b"size": 1_000_000_000}],
            b"trackers": [{b"url": b"https://tracker.example.com/announce"}],
            b"state": b"Seeding",
            b"progress": 100.0,
        }
    }
    client, mock_rpc = _make_client_with_mock_rpc()
    mock_rpc.call = MagicMock(return_value=raw)

    torrents = await client.get_torrents()
    assert len(torrents) == 1
    assert torrents[0].name == "My Movie"
    assert "tracker.example.com" in torrents[0].tracker_domains


# ---------------------------------------------------------------------------
# _decode_keys
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "obj,expected",
    [
        ({b"key": b"val"}, {"key": "val"}),
        ({b"nested": {b"k": b"v"}}, {"nested": {"k": "v"}}),
        ([b"a", b"b"], ["a", "b"]),
        ("already_str", "already_str"),
        (42, 42),
        ({b"list": [{b"url": b"http://example.com"}]}, {"list": [{"url": "http://example.com"}]}),
    ],
)
def test_decode_keys(obj: object, expected: object) -> None:
    assert _decode_keys(obj) == expected


async def test_get_torrents_handles_missing_fields() -> None:
    """Torrents with missing optional fields are handled gracefully."""
    raw = {"xyz": {"name": "Sparse", "save_path": "/dl", "state": "Paused"}}
    client, mock_rpc = _make_client_with_mock_rpc()
    mock_rpc.call = MagicMock(return_value=raw)

    torrents = await client.get_torrents()
    assert len(torrents) == 1
    assert torrents[0].files == []
    assert torrents[0].tracker_domains == []


async def test_get_torrents_single_file_empty_path_fallback() -> None:
    """Single-file torrents where Deluge returns path='' use the torrent name instead."""
    raw = {
        "abc123": {
            "name": "debian-12.iso",
            "save_path": "/downloads",
            "files": [{"path": "", "size": 900_000_000}],
            "trackers": [],
            "state": "Seeding",
            "progress": 100.0,
        }
    }
    client, mock_rpc = _make_client_with_mock_rpc()
    mock_rpc.call = MagicMock(return_value=raw)

    torrents = await client.get_torrents()
    assert torrents[0].files[0].path == "debian-12.iso"
    assert torrents[0].files[0].extension == ".iso"


# ---------------------------------------------------------------------------
# DelugeClient — move_torrent
# ---------------------------------------------------------------------------


async def test_move_torrent_uses_configured_method() -> None:
    client, mock_rpc = _make_client_with_mock_rpc(version="2.1.1")
    await client.move_torrent("abc123", "/new/path")
    mock_rpc.call.assert_called_with("core.move_storage", "abc123", "/new/path")


async def test_get_status_connected() -> None:
    client, mock_rpc = _make_client_with_mock_rpc(version="2.1.1")
    mock_rpc.call = MagicMock(return_value="2.1.1")
    status = await client.get_status()
    assert status.connected
    assert status.daemon_version == "2.1.1"


async def test_get_status_not_connected() -> None:
    client = DelugeClient("localhost", 58846, "user", "pass")
    status = await client.get_status()
    assert not status.connected
    assert status.error is not None
