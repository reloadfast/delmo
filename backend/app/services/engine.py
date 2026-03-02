"""
Rule evaluation engine.

Evaluates rules against a list of TorrentInfo objects and returns (torrent, rule)
pairs that match. A rule matches if ANY of its conditions match (OR logic).

Condition types:
  extension — any file in the torrent has the given extension (e.g. ".mkv")
  tracker   — any tracker domain contains the given value (case-insensitive substring)
  label     — torrent label exactly equals the value (case-insensitive); requires
               the Deluge Label plugin to be active

Idempotency guard: skip if torrent.save_path already equals rule.destination.
require_complete: if set on a rule, skip torrents that are not fully downloaded.
dry_run: if set on a rule, log the intended move but skip the actual RPC call.
"""
from __future__ import annotations

import logging

from app.models.rule import Rule
from app.services.deluge import DelugeClient, TorrentInfo

logger = logging.getLogger(__name__)


def _matches_extension(torrent: TorrentInfo, value: str) -> bool:
    """True if any file's extension equals *value* (case-insensitive, dot-prefixed)."""
    needle = value.lower()
    if not needle.startswith("."):
        needle = f".{needle}"
    return any(f.extension == needle for f in torrent.files)


def _matches_tracker(torrent: TorrentInfo, value: str) -> bool:
    """True if any tracker domain contains *value* as a substring (case-insensitive)."""
    needle = value.lower()
    return any(needle in domain for domain in torrent.tracker_domains)


def _matches_label(torrent: TorrentInfo, value: str) -> bool:
    """True if the torrent's label exactly equals *value* (case-insensitive).

    Requires the Deluge Label plugin to be active; when the plugin is absent
    torrent.label is always "" so label conditions will simply never match.
    """
    return torrent.label.lower() == value.lower()


def evaluate_rule(rule: Rule, torrent: TorrentInfo) -> bool:
    """Return True if *torrent* satisfies at least one condition of *rule*."""
    for condition in rule.conditions:
        if condition.condition_type == "extension":
            if _matches_extension(torrent, condition.value):
                return True
        elif condition.condition_type == "tracker":
            if _matches_tracker(torrent, condition.value):
                return True
        elif condition.condition_type == "label":
            if _matches_label(torrent, condition.value):
                return True
    return False


def find_matches(
    rules: list[Rule],
    torrents: list[TorrentInfo],
    *,
    pause_if_downloading: bool = False,
) -> list[tuple[TorrentInfo, Rule]]:
    """
    Return a list of (torrent, rule) pairs where the rule matches the torrent.

    Rules are evaluated in priority order (lowest first). Each torrent is matched
    against only the first matching rule (first-match wins). Torrents already at
    the rule destination are skipped (idempotency guard).

    If *pause_if_downloading* is True and any torrent is currently in
    "Downloading" state, the entire engine run is skipped and an empty list is
    returned.
    """
    if pause_if_downloading and any(t.state == "Downloading" for t in torrents):
        logger.info(
            "pause_if_downloading is enabled and a torrent is downloading"
            " — skipping rule evaluation."
        )
        return []

    sorted_rules = sorted(
        [r for r in rules if r.enabled], key=lambda r: (r.priority, r.id)
    )
    matches: list[tuple[TorrentInfo, Rule]] = []
    matched_hashes: set[str] = set()

    for rule in sorted_rules:
        if not rule.conditions:
            continue
        for torrent in torrents:
            if torrent.hash in matched_hashes:
                continue
            if torrent.save_path.rstrip("/") == rule.destination.rstrip("/"):
                # Already in place — skip (idempotency)
                continue
            if rule.require_complete and torrent.progress < 100.0:
                continue
            if evaluate_rule(rule, torrent):
                matches.append((torrent, rule))
                matched_hashes.add(torrent.hash)

    return matches


async def execute_moves(
    matches: list[tuple[TorrentInfo, Rule]],
    client: DelugeClient,
) -> list[dict[str, object]]:
    """
    Execute move RPC calls for each (torrent, rule) pair.

    Returns a list of result dicts suitable for writing to MoveLog.
    Does NOT write to DB — that is the scheduler's responsibility so it can
    batch-commit in its own session.
    """
    results: list[dict[str, object]] = []
    for torrent, rule in matches:
        entry: dict[str, object] = {
            "torrent_hash": torrent.hash,
            "torrent_name": torrent.name,
            "rule_id": rule.id,
            "rule_name": rule.name,
            "source_path": torrent.save_path,
            "destination_path": rule.destination,
        }
        if rule.dry_run:
            entry["status"] = "dry_run"
            entry["error_message"] = None
            logger.info(
                "[dry-run] Would move %r → %r (rule %r)",
                torrent.name,
                rule.destination,
                rule.name,
            )
        else:
            try:
                await client.move_torrent(torrent.hash, rule.destination)
                entry["status"] = "success"
                entry["error_message"] = None
                logger.info(
                    "Moved %r → %r (rule %r)",
                    torrent.name,
                    rule.destination,
                    rule.name,
                )
            except Exception as exc:
                entry["status"] = "error"
                entry["error_message"] = str(exc)
                logger.warning(
                    "Failed to move %r (rule %r): %s",
                    torrent.name,
                    rule.name,
                    exc,
                )
        results.append(entry)
    return results
