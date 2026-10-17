#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — replay frozen corpus + block anchors (W7, B7 §c.4).

Admissible sources for a replay run: the **frozen corpus** (``corpus/`` + W1/W3
series, manifest ``replay/corpus_v1.manifest.json``: paths + ``sha256`` +
size) and **fixed blocks** (``replay/blocks_v1.json``: one anchor per day — a
table declared absent until it is built: never invented).
**No ``latest``** in a replay run: any chain access goes through an explicit
pinned block (:func:`require_pinned_block`).

The engine refuses to start when a manifest hash does not match the disk;
series gaps are detected, never silently filled (:func:`find_gaps`).
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import json
import os
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

DEFAULT_MANIFEST = os.path.join(REPO_ROOT, "replay", "corpus_v1.manifest.json")
DEFAULT_BLOCKS = os.path.join(REPO_ROOT, "replay", "blocks_v1.json")

#: Maximum normal gap between two observations of the same hourly series.
MAX_GAP_MINUTES = 90.0

#: Price metrics usable as the reference series of a window.
PRICE_VENUES = ("defillama", "bitstamp", "binance")


class CorpusError(RuntimeError):
    """Invalid frozen corpus (hash mismatch, missing anchor, gap...)."""


# --- helpers -----------------------------------------------------------------

def sha256_file(path: str) -> str:
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def _parse_utc(stamp: str) -> _dt.datetime:
    text = str(stamp).replace("Z", "+00:00")
    parsed = _dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_dt.timezone.utc)
    return parsed.astimezone(_dt.timezone.utc)


# --- manifest ----------------------------------------------------------------

def load_manifest(path: str = DEFAULT_MANIFEST, *, verify: bool = True) -> dict:
    """Load the corpus manifest; check every ``sha256`` against the disk.

    Producer rule (``scripts/build_corpus_v1_manifest.py``): digest of each
    file's **raw bytes**. Any mismatch ⇒ refusal (B7 §c.4).
    """
    if not os.path.isfile(path):
        raise CorpusError("corpus manifest missing: %s" % path)
    with open(path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    files = manifest.get("files") or []
    if not files:
        raise CorpusError("empty corpus manifest: %s" % path)
    checked: List[dict] = []
    for entry in files:
        rel = entry.get("path")
        digest = entry.get("sha256")
        if not isinstance(rel, str) or not rel.strip():
            raise CorpusError("corpus manifest entry without a usable path: %r" % (entry,))
        target = rel if os.path.isabs(rel) else os.path.join(REPO_ROOT, rel)
        if not os.path.isfile(target):
            raise CorpusError("corpus file missing: %s" % rel)
        actual = sha256_file(target)
        if verify and actual != digest:
            raise CorpusError("corpus modified: %s (%s ≠ %s)" % (rel, actual, digest))
        checked.append({"path": rel, "sha256": actual, "bytes": entry.get("bytes")})
    manifest["files"] = checked
    manifest["manifest_sha256"] = sha256_file(path)
    return manifest


# --- series ------------------------------------------------------------------

def series_from_corpus_csv(path: str, *, venue: str = "defillama",
                           metric: str = "price_usd",
                           start_utc: Optional[str] = None,
                           end_utc: Optional[str] = None) -> List[Tuple[str, float]]:
    """Sorted ``(timestamp_utc, value)`` series from ``corpus/*.csv``."""
    points: List[Tuple[str, float]] = []
    start = _parse_utc(start_utc) if start_utc else None
    end = _parse_utc(end_utc) if end_utc else None
    with open(path, "r", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if str(row.get("venue", "")).strip() != venue:
                continue
            if str(row.get("metric", "")).strip() != metric:
                continue
            stamp = str(row.get("timestamp_utc", "")).strip()
            if not stamp:
                continue
            moment = _parse_utc(stamp)
            if start and moment < start:
                continue
            if end and moment > end:
                continue
            points.append((stamp, float(row["value"])))
    points.sort(key=lambda item: _parse_utc(item[0]))
    return points


def series_from_episode(path: str) -> List[Tuple[str, float]]:
    """``(timestamp_utc, value)`` series from ``evidence/episode_*.json``.

    Two supported shapes, never guessed beyond them:

    * ``series`` = **list** of dicts ``{<timestamp>, <value>}`` (keys
      ``t_utc``/``timestamp_utc``/... × ``price_usd``/``price``/``value``);
    * ``series`` = timestamped **dict** (stETH/rsETH:
      ``{"2022-05-01T00:00:00Z": {...}}``) — value by priority:
      ``price_eth_per_steth`` (realisable Curve discount),
      ``discount.1.price_eth_per_steth``, ``price_usd``, ``market.median``,
      ``value``.

    A file that does not fit raises: never an invented series.
    """
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    series = payload.get("series")
    if not series:
        raise CorpusError("no usable series in %s" % path)
    stamp_keys = ("t_utc", "timestamp_utc", "utc", "t", "timestamp")
    value_keys = ("price_usd", "price", "value", "price_reference_usd")
    points: List[Tuple[str, float]] = []
    if isinstance(series, list):
        for item in series:
            if not isinstance(item, dict):
                continue
            stamp = next((item[key] for key in stamp_keys if key in item and item[key]), None)
            value = next((item[key] for key in value_keys
                          if key in item and isinstance(item[key], (int, float))), None)
            if stamp is None or value is None:
                continue
            points.append((str(stamp), float(value)))
    elif isinstance(series, dict):
        for stamp, item in series.items():
            if not isinstance(item, dict):
                if isinstance(item, (int, float)):
                    points.append((str(stamp), float(item)))
                continue
            value = None
            if isinstance(item.get("price_eth_per_steth"), (int, float)):
                value = float(item["price_eth_per_steth"])
            elif isinstance(item.get("discount"), dict):
                by_size = item["discount"].get("1") or item["discount"].get(1)
                if isinstance(by_size, dict) and isinstance(by_size.get("price_eth_per_steth"),
                                                             (int, float)):
                    value = float(by_size["price_eth_per_steth"])
            if value is None:
                value = next((item[key] for key in ("price_usd", "price", "value")
                              if isinstance(item.get(key), (int, float))), None)
            if value is None and isinstance(item.get("market"), dict):
                median = item["market"].get("median")
                if isinstance(median, (int, float)):
                    value = float(median)
            if value is None:
                continue
            points.append((str(stamp), float(value)))
    else:
        raise CorpusError("unsupported series shape in %s (type %s)"
                          % (path, type(series).__name__))
    if not points:
        raise CorpusError("unrecognised series in %s (unexpected keys)" % path)
    points.sort(key=lambda item: _parse_utc(item[0]))
    return points


def window_series(window, *, venue: str = "defillama") -> Tuple[str, List[Tuple[str, float]]]:
    """Reference series of a DEV/EVAL window, from its declared sources.

    Explicit dispatch: CSV corpus for the USDC episodes; episode JSON otherwise.
    Each source is tried in declared order; a failure does not stop the next
    attempt but is recorded. Returns ``(source_label, points)``; never a
    silently empty window.
    """
    attempts: List[str] = []
    for rel in window.sources:
        target = rel if os.path.isabs(rel) else os.path.join(REPO_ROOT, rel)
        try:
            if target.endswith(".csv"):
                points = series_from_corpus_csv(target, venue=venue,
                                                start_utc=window.start_utc,
                                                end_utc=window.end_utc)
                if points:
                    return (rel, points)
                attempts.append("%s: no point in the window" % rel)
            elif target.endswith(".json") and "episode" in os.path.basename(target):
                points = series_from_episode(target)
                start, end = _parse_utc(window.start_utc), _parse_utc(window.end_utc)
                points = [(stamp, value) for stamp, value in points
                          if start <= _parse_utc(stamp) <= end]
                if points:
                    return (rel, points)
                attempts.append("%s: no point in the window" % rel)
            else:
                attempts.append("%s: unrecognised source type" % rel)
        except CorpusError as exc:
            attempts.append("%s: %s" % (rel, exc))
    raise CorpusError("no series source resolved for window %s (%s)"
                      % (window.window_id, " · ".join(attempts)))


def find_gaps(points: Sequence[Tuple[str, float]],
              max_gap_minutes: float = MAX_GAP_MINUTES) -> List[dict]:
    """Gaps in a series: deltas > ``max_gap_minutes`` between observations.

    A gap is never filled; the caller decides (declare it, or refuse).
    """
    gaps: List[dict] = []
    previous: Optional[_dt.datetime] = None
    for stamp, _value in points:
        moment = _parse_utc(stamp)
        if previous is not None:
            delta_minutes = (moment - previous).total_seconds() / 60.0
            if delta_minutes > max_gap_minutes:
                gaps.append({"after_utc": previous.strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "before_utc": moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "gap_minutes": round(delta_minutes, 1)})
        previous = moment
    return gaps


def require_continuous(points: Sequence[Tuple[str, float]],
                       *, label: str = "series",
                       max_gap_minutes: float = MAX_GAP_MINUTES) -> None:
    """Refuse a gapped series (the default) — never a silent fill."""
    gaps = find_gaps(points, max_gap_minutes)
    if gaps:
        raise CorpusError("%s: %d gap(s) detected, first %s → %s (%.1f min)"
                          % (label, len(gaps), gaps[0]["after_utc"], gaps[0]["before_utc"],
                             gaps[0]["gap_minutes"]))


# --- block anchors -----------------------------------------------------------

def load_block_anchors(path: str = DEFAULT_BLOCKS) -> Optional[dict]:
    """Block anchor table ``replay/blocks_v1.json`` — or ``None`` if absent.

    Declared absent until it is built (B7: "one anchor per day, resolved by
    bisection, cached"): no anchor is invented.
    """
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise CorpusError("unreadable anchor table: %s" % path)
    return payload


def block_for(anchors: Optional[dict], stamp_utc: str) -> Optional[int]:
    """Block anchor for a timestamp (closest already-resolved day)."""
    if not anchors:
        return None
    day = _parse_utc(stamp_utc).strftime("%Y-%m-%d")
    direct = anchors.get(day)
    if isinstance(direct, int) and not isinstance(direct, bool):
        return direct
    resolved = sorted(key for key in anchors
                      if key <= day and isinstance(anchors[key], int)
                      and not isinstance(anchors[key], bool))
    return anchors[resolved[-1]] if resolved else None


def require_pinned_block(block: object, *, context: str = "chain read") -> int:
    """The "no ``latest``" guard: the block must be an explicit integer."""
    if isinstance(block, int) and not isinstance(block, bool):
        return block
    if isinstance(block, str) and block.isdigit():
        return int(block)
    raise CorpusError("unpinned block (%r) for: %s — a replay run never uses "
                      "“latest” (B7 §c.4)" % (block, context))
