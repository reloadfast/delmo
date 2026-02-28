"""Unit tests for the rule evaluation engine."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.models.rule import Rule, RuleCondition
from app.services.deluge import TorrentFile, TorrentInfo
from app.services.engine import (
    _matches_extension,
    _matches_tracker,
    evaluate_rule,
    execute_moves,
    find_matches,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _torrent(
    hash_: str = "abc",
    save_path: str = "/downloads",
    files: list[str] | None = None,
    trackers: list[str] | None = None,
) -> TorrentInfo:
    return TorrentInfo(
        hash=hash_,
        name=f"Torrent-{hash_}",
        save_path=save_path,
        state="Seeding",
        progress=100.0,
        files=[TorrentFile(path=p, size=1000) for p in (files or [])],
        tracker_domains=trackers or [],
    )


def _rule(
    id_: int = 1,
    priority: int = 100,
    enabled: bool = True,
    destination: str = "/dest",
    conditions: list[tuple[str, str]] | None = None,
) -> Rule:
    rule = Rule(
        id=id_, name=f"Rule-{id_}", priority=priority,
        enabled=enabled, destination=destination,
    )
    rule.conditions = [
        RuleCondition(id=i, rule_id=id_, condition_type=ct, value=val)
        for i, (ct, val) in enumerate(conditions or [], start=1)
    ]
    return rule


# ---------------------------------------------------------------------------
# _matches_extension
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "files,needle,expected",
    [
        (["movie.mkv"], ".mkv", True),
        (["movie.mkv"], "mkv", True),     # without dot
        (["movie.MKV"], ".mkv", True),    # case insensitive via TorrentFile.extension
        (["movie.mp4"], ".mkv", False),
        ([], ".mkv", False),
        (["noext"], ".mkv", False),
    ],
)
def test_matches_extension(files: list[str], needle: str, expected: bool) -> None:
    t = _torrent(files=files)
    assert _matches_extension(t, needle) is expected


# ---------------------------------------------------------------------------
# _matches_tracker
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "trackers,needle,expected",
    [
        (["tracker.example.com"], "example.com", True),
        (["tracker.example.com"], "EXAMPLE", True),     # case insensitive
        (["tracker.other.com"], "example.com", False),
        ([], "example.com", False),
        (["tracker.example.com"], "example", True),     # substring match
    ],
)
def test_matches_tracker(trackers: list[str], needle: str, expected: bool) -> None:
    t = _torrent(trackers=trackers)
    assert _matches_tracker(t, needle) is expected


# ---------------------------------------------------------------------------
# evaluate_rule
# ---------------------------------------------------------------------------


def test_evaluate_rule_extension_match() -> None:
    rule = _rule(conditions=[("extension", ".mkv")])
    t = _torrent(files=["movie.mkv"])
    assert evaluate_rule(rule, t) is True


def test_evaluate_rule_tracker_match() -> None:
    rule = _rule(conditions=[("tracker", "example.com")])
    t = _torrent(trackers=["tracker.example.com"])
    assert evaluate_rule(rule, t) is True


def test_evaluate_rule_no_conditions() -> None:
    rule = _rule(conditions=[])
    t = _torrent(files=["movie.mkv"])
    assert evaluate_rule(rule, t) is False


def test_evaluate_rule_or_logic() -> None:
    """Either condition matching returns True."""
    rule = _rule(conditions=[("extension", ".mkv"), ("tracker", "other.com")])
    t = _torrent(files=["movie.mkv"], trackers=["nope.com"])
    assert evaluate_rule(rule, t) is True


def test_evaluate_rule_no_match() -> None:
    rule = _rule(conditions=[("extension", ".mkv"), ("tracker", "example.com")])
    t = _torrent(files=["audio.flac"], trackers=["nope.com"])
    assert evaluate_rule(rule, t) is False


# ---------------------------------------------------------------------------
# find_matches
# ---------------------------------------------------------------------------


def test_find_matches_basic() -> None:
    rules = [_rule(id_=1, conditions=[("extension", ".mkv")])]
    torrents = [_torrent(hash_="t1", files=["movie.mkv"])]
    matches = find_matches(rules, torrents)
    assert len(matches) == 1
    assert matches[0][0].hash == "t1"


def test_find_matches_idempotency_guard() -> None:
    """Skip torrents already at destination."""
    rules = [_rule(id_=1, destination="/dest", conditions=[("extension", ".mkv")])]
    torrents = [_torrent(hash_="t1", save_path="/dest", files=["movie.mkv"])]
    assert find_matches(rules, torrents) == []


def test_find_matches_disabled_rule_skipped() -> None:
    rules = [_rule(id_=1, enabled=False, conditions=[("extension", ".mkv")])]
    torrents = [_torrent(hash_="t1", files=["movie.mkv"])]
    assert find_matches(rules, torrents) == []


def test_find_matches_rule_without_conditions_skipped() -> None:
    rules = [_rule(id_=1, conditions=[])]
    torrents = [_torrent(hash_="t1", files=["movie.mkv"])]
    assert find_matches(rules, torrents) == []


def test_find_matches_first_match_wins() -> None:
    """A torrent matches only the first (highest priority) applicable rule."""
    rule1 = _rule(
        id_=1, priority=10, destination="/high", conditions=[("extension", ".mkv")]
    )
    rule2 = _rule(
        id_=2, priority=50, destination="/low", conditions=[("extension", ".mkv")]
    )
    torrents = [_torrent(hash_="t1", files=["movie.mkv"])]
    matches = find_matches([rule2, rule1], torrents)  # order should be sorted
    assert len(matches) == 1
    assert matches[0][1].destination == "/high"


def test_find_matches_priority_ordering() -> None:
    """Lower priority number wins over higher number."""
    rule_low_prio = _rule(
        id_=1, priority=10, destination="/prio10", conditions=[("extension", ".mkv")]
    )
    rule_high_prio = _rule(
        id_=2, priority=200, destination="/prio200",
        conditions=[("extension", ".mkv")],
    )
    torrents = [_torrent(hash_="t1", files=["movie.mkv"])]
    matches = find_matches([rule_high_prio, rule_low_prio], torrents)
    assert matches[0][1].destination == "/prio10"


def test_find_matches_empty_inputs() -> None:
    assert find_matches([], []) == []
    assert find_matches([_rule(conditions=[("extension", ".mkv")])], []) == []
    assert find_matches([], [_torrent()]) == []


def test_find_matches_multiple_torrents_different_rules() -> None:
    rule_video = _rule(
        id_=1, destination="/videos", conditions=[("extension", ".mkv")]
    )
    rule_audio = _rule(
        id_=2, priority=50, destination="/music", conditions=[("extension", ".flac")]
    )
    torrents = [
        _torrent(hash_="v1", files=["film.mkv"]),
        _torrent(hash_="a1", files=["song.flac"]),
    ]
    matches = find_matches([rule_video, rule_audio], torrents)
    assert len(matches) == 2
    matched_hashes = {t.hash for t, _ in matches}
    assert "v1" in matched_hashes
    assert "a1" in matched_hashes


# ---------------------------------------------------------------------------
# execute_moves
# ---------------------------------------------------------------------------


async def test_execute_moves_success() -> None:
    rule = _rule(id_=1, destination="/dest", conditions=[("extension", ".mkv")])
    torrent = _torrent(hash_="t1", save_path="/src", files=["movie.mkv"])
    mock_client = MagicMock()
    mock_client.move_torrent = AsyncMock()

    results = await execute_moves([(torrent, rule)], mock_client)
    assert len(results) == 1
    assert results[0]["status"] == "success"
    assert results[0]["torrent_hash"] == "t1"
    assert results[0]["destination_path"] == "/dest"
    assert results[0]["error_message"] is None
    mock_client.move_torrent.assert_called_once_with("t1", "/dest")


async def test_execute_moves_error() -> None:
    rule = _rule(id_=1, destination="/dest", conditions=[("extension", ".mkv")])
    torrent = _torrent(hash_="t1", save_path="/src", files=["movie.mkv"])
    mock_client = MagicMock()
    mock_client.move_torrent = AsyncMock(side_effect=RuntimeError("RPC failed"))

    results = await execute_moves([(torrent, rule)], mock_client)
    assert results[0]["status"] == "error"
    assert "RPC failed" in str(results[0]["error_message"])


async def test_execute_moves_empty() -> None:
    mock_client = MagicMock()
    results = await execute_moves([], mock_client)
    assert results == []
