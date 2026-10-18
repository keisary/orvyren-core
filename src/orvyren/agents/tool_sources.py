# -*- coding: utf-8 -*-
"""``tool_sources`` — mode-specific data providers behind ONE tool code (P0-1).

Before this module, a "live" agent reasoned on frozen fixtures: the worker
built the fixture registry while the real graph registry was never used. The
fix is architectural: **one** set of tools, and only the *data provider* changes
with the run mode. The three modes are a frozen contract:

``LIVE``
    Real sources only. ``graph_query`` / ``graph_path`` / ``graph_snapshot``
    delegate to the real read-only graph API (the ``graph_tools`` classes,
    schema v3 — never duplicated here); ``read_prices`` / ``read_supply`` read
    the **measured** corpus series archived on disk; ``fetch_document`` reads
    the archived corpus documents. Constraints: point-in-time arguments are
    the caller's, the deadline budget is enforced by the graph tools, and every
    observation carries a deterministic ``source_ref`` plus its row-level
    ``refs`` (P0-6 provenance). Two honest refusals live here: ``read_chain``
    answers ``UNAVAILABLE`` / ``E_TOOL_NO_LIVE_SOURCE`` (no RPC collector in
    this wave) and ``compute_signal`` does not exist (a precomputed signal is a
    hard FIXTURE-only decision — it is never silently substituted).

``REPLAY``
    Recorded responses of those same interfaces
    (``store_dir/tool_responses.jsonl``), keyed ``content_hash(tool, args)``.
    A recorded hit is served **bit-identical**; a miss is
    ``ToolResult(ok=False, status="FAILED", error="E_TOOL_NOT_RECORDED:<key>")``
    — never a silent simulation, never a fallback to another source.

``FIXTURE``
    Explicitly labelled simulated data (tests, scripted seed) read **verbatim**
    out of the frozen fixture buckets — the legacy v1 behaviour, unchanged.

Measured corpus shapes (verified on disk 2026-10-18, the loader is
shape-driven — no guessing):

- bare list of bars — ``corpus/raw/<source>/*.json``:
  ``[{"timestamp_utc": ..., "price"|"close": ..., "retrieved_at": ...}, ...]``
  (supply archives use ``{"date_utc": ..., "circulating_usd": ...}`` bars);
- flat document with an observation list — ``corpus/series/usd0pp_2025-01.json``:
  ``{"asset": ..., "contract": ..., "observations": [{"ts", "price_usd", "unix"}]}``;
- windowed unified series — ``corpus/series/calm_windows.json``:
  ``{"windows": {"<label>": {"sources": {"<venue>": {"observations": [...]}}}}}``.

Matching rule for ``prices(venue, symbol)`` / ``supply(asset)`` (documented,
deterministic): a bar track is bound to *tokens* declared by its archive (doc
``asset``/``symbol``/``pair``/``contract`` values, window source keys, the
``raw/<source>/`` directory name, file-stem words minus date/window words).
A query matches when its normalised form (lowercase alphanumerics only) equals
one of the track's tokens. Matching is **fail-closed per dimension**: a track
that declares no venue is reachable only with an empty venue argument (and
symmetrically for the symbol) — the source never claims a binding the archive
does not declare (e.g. the ``usd0pp`` series declares its asset but no venue:
``prices("", "usd0pp")`` reaches it, ``prices("defillama", "usd0pp")`` does
not). Price tracks never answer ``read_supply`` and supply tracks never answer
``read_prices``; a bar archived twice (unified series + raw archive) is
returned once, first archive in sorted path order.

Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from orvyren.agents import contracts

__all__ = [
    "MODES",
    "NO_DATA_CODE",
    "NO_LIVE_SOURCE_CODE",
    "NOT_RECORDED_CODE",
    "TOOL_STORE_FILE",
    "canonical_args",
    "response_key",
    "ToolResponseStore",
    "FixtureSource",
    "LiveSource",
    "ReplaySource",
    "RecordingTool",
    "ReplayedTool",
    "SourceTool",
]

#: The three modes of the unified registry (the mode contract above).
MODES: Tuple[str, ...] = ("fixture", "live", "replay")

#: The one failure contract of a fixture-backed tool: the data is not archived.
NO_DATA_CODE = "E_TOOL_NO_DATA"

#: Honest refusal of a tool whose live collector does not exist yet.
NO_LIVE_SOURCE_CODE = "E_TOOL_NO_LIVE_SOURCE"

#: REPLAY miss: the call was never recorded — never simulated.
NOT_RECORDED_CODE = "E_TOOL_NOT_RECORDED"

#: File name of the tool-response store inside a store directory.
TOOL_STORE_FILE = "tool_responses.jsonl"


# ---------------------------------------------------------------------------
# Content-addressed call keys.
# ---------------------------------------------------------------------------
def canonical_args(args: Any) -> Dict[str, Any]:
    """Plain-JSON view of tool args (tuples -> lists, sorted by hashing)."""
    if isinstance(args, Mapping):
        return {str(key): canonical_args(value) for key, value in args.items()}
    if isinstance(args, (list, tuple)):
        return [canonical_args(value) for value in args]
    if isinstance(args, (str, int, float, bool)) or args is None:
        return args
    return str(args)

def response_key(tool_name: str, args: Any) -> str:
    """``content_hash`` of one canonical call: ``(tool_name, args)``.

    The deadline is deliberately **not** part of the key: it is execution
    budget, not data. The key addresses the response, so a REPLAY serves the
    exact bytes a LIVE run recorded for the same call.
    """
    return contracts.content_hash({"tool": str(tool_name or ""),
                                  "args": canonical_args(args or {})})


class ToolResponseStore:
    """Append-only store of recorded tool responses (``tool_responses.jsonl``).

    One JSON line per recorded call: ``{"key", "tool", "args", "result"}``.
    The first recorded response of a key wins (later identical calls are not
    appended), so a replay is a pure function of the call sequence and the
    recorded data — never of re-execution.
    """

    def __init__(self, store_dir: str) -> None:
        self.root = str(store_dir or "")
        self.path = os.path.join(self.root, TOOL_STORE_FILE)
        self._by_key: Optional[Dict[str, contracts.ToolResult]] = None

    # -- storage -----------------------------------------------------------
    def _load(self) -> Dict[str, contracts.ToolResult]:
        if self._by_key is not None:
            return self._by_key
        index: Dict[str, contracts.ToolResult] = {}
        if self.root and os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except ValueError:
                        continue  # a torn line is skipped, never invented
                    key = str(entry.get("key") or "")
                    if key and key not in index:
                        index[key] = _result_from_dict(entry.get("result"))
        self._by_key = index
        return index

    def record(self, tool_name: str, args: Any,
               result: contracts.ToolResult) -> str:
        """Append one response; returns its key (first response wins)."""
        key = response_key(tool_name, args)
        index = self._load()
        if key in index:
            return key
        if self.root:
            os.makedirs(self.root, exist_ok=True)
        entry = {"key": key, "tool": str(tool_name or ""),
                 "args": canonical_args(args or {}),
                 "result": result.to_dict()}
        with open(self.path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        index[key] = result
        return key

    def lookup(self, key: str) -> Optional[contracts.ToolResult]:
        """The recorded response of ``key``, or ``None`` (nothing is faked)."""
        return self._load().get(str(key))

    def keys(self) -> Tuple[str, ...]:
        """Every recorded key (sorted — the store is a set of calls)."""
        return tuple(sorted(self._load()))


def _result_from_dict(payload: Any) -> contracts.ToolResult:
    """Rebuild one :class:`contracts.ToolResult` bit-identically."""
    data = payload if isinstance(payload, Mapping) else {}
    observations = tuple(dict(row) for row in (data.get("observations") or ())
                         if isinstance(row, Mapping))
    return contracts.ToolResult(
        ok=bool(data.get("ok")), status=str(data.get("status") or "OK"),
        observations=observations, error=str(data.get("error") or ""))


def _no_data() -> contracts.ToolResult:
    """The one failure contract of a data tool: the data is not archived."""
    return contracts.ToolResult(ok=False, status="FAILED", error=NO_DATA_CODE)


# ---------------------------------------------------------------------------
# FIXTURE mode: verbatim simulated data (legacy v1 behaviour, unchanged).
# ---------------------------------------------------------------------------
class FixtureSource:
    """FIXTURE mode: reads the frozen fixture buckets **verbatim**.

    The fixture schema (committed run inputs, scripted seed)::

        {"prices": {"<venue>|<symbol>": [row, ...]},
         "supply": {"<asset>": [row, ...]},
         "chain": {"<chain_id>|<address>": [row, ...]},
         "documents": {"<url>": "<raw text>"},
         "signals": {"<signal_id>": {"value", "unit", "method_ref"}},
         "snapshot": {...}}

    Every method keeps the legacy v1 semantics exactly: one composite lookup
    key, observations copied verbatim, missing data -> ``E_TOOL_NO_DATA``,
    ``document`` wraps its payload as untrusted (never interpretable) and
    ``signal`` copies a **precomputed** value + unit + method reference.
    """

    def __init__(self, fixtures: Any) -> None:
        self._fixtures = fixtures if isinstance(fixtures, Mapping) else {}

    # -- bucket plumbing ---------------------------------------------------
    def _bucket(self, key: str) -> Mapping[str, Any]:
        value = self._fixtures.get(key)
        return value if isinstance(value, Mapping) else {}

    @staticmethod
    def _rows(rows: Any) -> Tuple[Dict[str, Any], ...]:
        if not isinstance(rows, (list, tuple)):
            return ()
        return tuple(dict(row) for row in rows if isinstance(row, Mapping))

    # -- the data tools ----------------------------------------------------
    def prices(self, venue: str, symbol: str) -> contracts.ToolResult:
        """Archived venue prices, keyed ``venue|symbol`` (verbatim rows)."""
        observations = self._rows(self._bucket("prices").get("%s|%s" % (venue, symbol)))
        if not observations:
            return _no_data()
        return contracts.ToolResult(ok=True, status="OK", observations=observations)

    def supply(self, asset: str) -> contracts.ToolResult:
        """Archived supply observations, keyed ``asset`` (verbatim rows)."""
        observations = self._rows(self._bucket("supply").get(str(asset)))
        if not observations:
            return _no_data()
        return contracts.ToolResult(ok=True, status="OK", observations=observations)

    def chain(self, chain_id: str, address: str) -> contracts.ToolResult:
        """Archived on-chain observations, keyed ``chain_id|address``."""
        observations = self._rows(
            self._bucket("chain").get("%s|%s" % (chain_id, address)))
        if not observations:
            return _no_data()
        return contracts.ToolResult(ok=True, status="OK", observations=observations)

    def document(self, url: str) -> contracts.ToolResult:
        """One archived raw document, wrapped as untrusted (never bare text)."""
        raw = self._bucket("documents").get(str(url))
        if not url or not isinstance(raw, str):
            return _no_data()
        return contracts.ToolResult(ok=True, status="OK", observations=(
            _document_observation(str(url), raw),))

    def signal(self, signal_id: str) -> contracts.ToolResult:
        """A **precomputed** signal copy (value + unit + method ref)."""
        row = self._bucket("signals").get(str(signal_id))
        if not isinstance(row, Mapping):
            return _no_data()
        if not str(row.get("unit", "")).strip() or not str(row.get("method_ref", "")).strip():
            return _no_data()
        if "value" not in row:
            return _no_data()
        value = row.get("value")
        if value is None or isinstance(value, bool) or (
                isinstance(value, str) and not value.strip()):
            return _no_data()
        return contracts.ToolResult(ok=True, status="OK", observations=(dict(row),))

    def snapshot(self) -> contracts.ToolResult:
        """The frozen snapshot of the fixture (the point-in-time boundary)."""
        snapshot = self._fixtures.get("snapshot")
        if not isinstance(snapshot, Mapping) or not snapshot:
            return _no_data()
        return contracts.ToolResult(ok=True, status="OK",
                                    observations=(dict(snapshot),))


def _document_observation(url: str, raw: str) -> Dict[str, Any]:
    """One archived document as one untrusted observation (legacy shape)."""
    return {
        "url": url,
        "untrusted": True,
        "content": contracts.wrap_untrusted(raw, url),
        "untrusted_flags": contracts.scan_untrusted_flags(raw),
        "content_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    }


# ---------------------------------------------------------------------------
# Measured corpus series (LIVE price/supply bars).
# ---------------------------------------------------------------------------
#: Bar field that marks a track as supply data (never answered by prices).
_SUPPLY_KEYS = ("circulating_usd", "circulating", "supply", "total_supply", "issued")

#: Bar field that marks a track as price data (never answered by supply).
_PRICE_KEYS = ("price", "price_usd", "close", "high", "low", "value")

#: Archive keys that declare a venue binding.
_VENUE_KEYS = ("venue", "source", "exchange", "market")

#: Archive keys that declare a symbol/asset binding.
_SYMBOL_KEYS = ("asset", "symbol", "pair", "contract", "instrument")

#: File-stem words that never carry a symbol (windows, shapes, dates, months).
_STEM_NOISE = frozenset((
    "main", "control", "calm", "window", "windows", "ohlc", "klines", "price",
    "prices", "series", "circulating", "aggregate", "hourly", "statement",
    "reference", "raw", "data", "obs", "observations", "snapshot",
    "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct",
    "nov", "dec",
))

#: Identifier keys whose values become ``graph:``-prefixed provenance refs.
_ROW_ID_KEYS = ("relation_id", "node_id", "event_id")


def _norm(value: Any) -> str:
    """Normalised lookup token: lowercase alphanumerics only."""
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _url_token(value: Any) -> str:
    """Normalised URL form (scheme, ``www.`` and trailing ``/`` ignored)."""
    text = str(value or "").strip()
    for prefix in ("https://", "http://"):
        if text.lower().startswith(prefix):
            text = text[len(prefix):]
    text = text.strip().rstrip("/")
    if text.lower().startswith("www."):
        text = text[4:]
    return _norm(text)


def _stem_tokens(relpath: str) -> Tuple[str, ...]:
    """Symbol-ish words of a file stem (dates and shape words dropped)."""
    stem = os.path.splitext(os.path.basename(relpath))[0]
    tokens: List[str] = []
    for word in stem.replace("-", "_").replace(".", "_").split("_"):
        clean = word.strip()
        if not clean or len(clean) < 2 or clean.isdigit() or clean.lower() in _STEM_NOISE:
            continue
        if clean not in tokens:
            tokens.append(clean)
    return tuple(tokens)


def _kind_of(rows: Sequence[Mapping[str, Any]]) -> str:
    """``supply`` / ``price`` / ``other`` from the real bar fields."""
    for row in rows:
        if any(key in row for key in _SUPPLY_KEYS):
            return "supply"
    for row in rows:
        if any(key in row for key in _PRICE_KEYS):
            return "price"
    return "other"


class _Track:
    """One measured series: rows + the bindings its archive declares."""

    __slots__ = ("relpath", "kind", "venues", "symbols", "rows")

    def __init__(self, relpath: str, kind: str, venues: Sequence[str],
                 symbols: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
        self.relpath = relpath.replace("\\", "/")
        self.kind = kind
        self.venues = tuple(dict.fromkeys(venues))
        self.symbols = tuple(dict.fromkeys(symbols))
        self.rows = tuple(rows)

    def matches(self, venue: str = "", symbol: str = "") -> bool:
        """Strict token matching: a query dimension must match a declared
        token; a dimension the archive does not declare is reachable only
        with an empty query (never claim a binding the data lacks)."""
        want_venue, want_symbol = _norm(venue), _norm(symbol)
        if want_venue and want_venue not in {_norm(v) for v in self.venues}:
            return False
        if want_symbol and want_symbol not in {_norm(s) for s in self.symbols}:
            return False
        return True


def _track_rows(relpath: str, rows: Sequence[Mapping[str, Any]],
                venues: Sequence[str], symbols: Sequence[str]) -> Optional[_Track]:
    if not rows:
        return None
    kind = _kind_of(rows)
    if kind == "other":
        return None  # not a series of bars (e.g. an archived document)
    venue_tokens = list(venues)
    symbol_tokens = list(symbols)
    for row in rows[:1]:  # row-level declared bindings
        for key in _VENUE_KEYS:
            if str(row.get(key) or "").strip():
                venue_tokens.append(str(row[key]).strip())
        for key in _SYMBOL_KEYS:
            if str(row.get(key) or "").strip():
                symbol_tokens.append(str(row[key]).strip())
    for word in _stem_tokens(relpath):
        symbol_tokens.append(word)
    return _Track(relpath, kind, venue_tokens, symbol_tokens, rows)


def _tracks_from_document(relpath: str, doc: Any) -> List[_Track]:
    """Real on-disk shapes -> bar tracks (see the module docstring)."""
    tracks: List[_Track] = []
    parts = relpath.replace("\\", "/").split("/")
    if isinstance(doc, list):  # bare list of bars (corpus/raw/<source>/*.json)
        rows = [dict(row) for row in doc if isinstance(row, Mapping)]
        venues = [parts[-2]] if len(parts) >= 3 and parts[0] == "raw" else []
        track = _track_rows(relpath, rows, venues, [])
        return [track] if track else []
    if not isinstance(doc, Mapping):
        return []
    if isinstance(doc.get("observations"), list):  # flat document (usd0pp_*)
        rows = [dict(row) for row in doc["observations"] if isinstance(row, Mapping)]
        venues = [str(doc[key]).strip() for key in _VENUE_KEYS
                  if str(doc.get(key) or "").strip()]
        symbols = [str(doc[key]).strip() for key in _SYMBOL_KEYS
                   if str(doc.get(key) or "").strip()]
        track = _track_rows(relpath, rows, venues, symbols)
        return [track] if track else []
    windows = doc.get("windows")
    if isinstance(windows, Mapping):  # windowed unified series (calm_windows)
        for label in sorted(windows):
            window = windows.get(label)
            sources = window.get("sources") if isinstance(window, Mapping) else None
            if not isinstance(sources, Mapping):
                continue
            for venue in sorted(sources):
                bundle = sources.get(venue)
                rows = bundle.get("observations") if isinstance(bundle, Mapping) else None
                rows = [dict(row) for row in rows or () if isinstance(row, Mapping)]
                track = _track_rows(relpath, rows, [str(venue)], [])
                if track:
                    tracks.append(track)
    return tracks


class LiveSource:
    """LIVE mode: real sources — graph API + measured corpus (see contract).

    ``graph_query`` / ``graph_path`` / ``graph_snapshot`` delegate to the real
    ``graph_tools`` tools (their strict arg validation and deadline enforcement
    are reused verbatim, never duplicated) and stamp every observation with a
    deterministic ``source_ref`` and its row-level ``refs`` so the P0-6 ledger
    records what was really observed::

        source_ref = "graph:<query>:<sha256 of the canonical response[:16]>"
        refs       = ["graph:<relation_id|node_id|event_id>", ...]

    ``prices`` / ``supply`` read the measured corpus series; ``document`` reads
    the archived corpus document of a **declared manifest endpoint** (wrapped
    as untrusted, exactly like the fixture tool — an unarchived URL is
    ``E_TOOL_NO_DATA``, never a look-alike file); ``chain`` is honestly
    ``UNAVAILABLE`` (no RPC collector in this wave) and there is **no**
    ``signal``: a precomputed signal is a FIXTURE-only decision.
    """

    def __init__(self, *, db: Optional[str] = None, api: Any = None,
                 corpus_dir: str = "corpus",
                 documents_dir: Optional[str] = None) -> None:
        from orvyren.agents import graph_tools
        self.db = db
        self.api = api
        self.corpus_dir = str(corpus_dir or "corpus")
        self.documents_dir = str(documents_dir or os.path.join(self.corpus_dir, "raw"))
        self._graph_query_tool = graph_tools.GraphQueryTool(db=db, api=api)
        self._graph_path_tool = graph_tools.GraphPathTool(db=db, api=api)
        self._graph_snapshot_tool = graph_tools.GraphSnapshotTool(db=db, api=api)
        self._tracks: Optional[Tuple[_Track, ...]] = None

    # -- provenance --------------------------------------------------------
    def _stamp(self, result: contracts.ToolResult, label: str) -> contracts.ToolResult:
        """Deterministic ``source_ref`` + row ``refs`` on graph observations."""
        if not result.ok or not result.observations:
            return result
        stamped: List[Dict[str, Any]] = []
        for observation in result.observations:
            row = dict(observation)
            digest = contracts.content_hash(row)[:16]
            source_ref = "graph:%s:%s" % (label, digest)
            refs = [source_ref]
            for ref in _row_refs(row):
                if ref not in refs:
                    refs.append(ref)
            row["source_ref"] = source_ref
            row["refs"] = refs
            stamped.append(row)
        return contracts.ToolResult(ok=True, status="OK",
                                    observations=tuple(stamped))

    # -- the real graph (graph_tools, delegated) ---------------------------
    def graph_query(self, args: Mapping[str, Any], *,
                    deadline_s: float = 20.0) -> contracts.ToolResult:
        """Q1/Q4/Q6/Q7/Q8 from the real graph API (``graph_tools``)."""
        args = dict(args or {})
        result = self._graph_query_tool.run(args, deadline_s=deadline_s)
        return self._stamp(result, str(args.get("query") or "").strip() or "query")

    def graph_path(self, args: Mapping[str, Any], *,
                   deadline_s: float = 20.0) -> contracts.ToolResult:
        """Bounded dependency paths (Q2) from the real graph API."""
        result = self._graph_path_tool.run(dict(args or {}), deadline_s=deadline_s)
        return self._stamp(result, "Q2")

    def graph_snapshot(self, args: Mapping[str, Any], *,
                       deadline_s: float = 20.0) -> contracts.ToolResult:
        """Hash + counts of the real graph slice (``graph_tools``)."""
        result = self._graph_snapshot_tool.run(dict(args or {}), deadline_s=deadline_s)
        return self._stamp(result, "snapshot")

    # -- measured corpus ---------------------------------------------------
    def _series(self) -> Tuple[_Track, ...]:
        """Every bar track of the corpus (``series/`` + ``raw/``, sorted)."""
        if self._tracks is not None:
            return self._tracks
        tracks: List[_Track] = []
        roots = (os.path.join(self.corpus_dir, "series"),
                 os.path.join(self.corpus_dir, "raw"))
        for root in roots:
            if not os.path.isdir(root):
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames.sort()
                for name in sorted(filenames):
                    if not name.endswith(".json"):
                        continue
                    path = os.path.join(dirpath, name)
                    relpath = os.path.relpath(path, self.corpus_dir)
                    try:
                        with open(path, "r", encoding="utf-8") as handle:
                            doc = json.load(handle)
                    except (OSError, ValueError):
                        continue  # an unreadable archive is never invented
                    tracks.extend(_tracks_from_document(relpath, doc))
        self._tracks = tuple(tracks)
        return self._tracks

    def _bars(self, kind: str, venue: str, symbol: str) -> Tuple[Dict[str, Any], ...]:
        """Matching bars, verbatim + provenance; a bar archived twice -> once."""
        rows: List[Dict[str, Any]] = []
        seen: set = set()
        for track in self._series():
            if track.kind != kind or not track.matches(venue=venue, symbol=symbol):
                continue
            for index, row in enumerate(track.rows):
                identity = contracts.content_hash(row)
                if identity in seen:
                    continue
                seen.add(identity)
                copied = dict(row)
                digest = identity[:16]
                source_ref = "corpus:%s:%s" % (track.relpath, digest)
                copied["source_ref"] = source_ref
                copied["refs"] = [source_ref]
                rows.append(copied)
        return tuple(rows)

    def prices(self, venue: str, symbol: str) -> contracts.ToolResult:
        """Measured venue prices from the corpus series (verbatim bars)."""
        observations = self._bars("price", venue, symbol)
        if not observations:
            return _no_data()
        return contracts.ToolResult(ok=True, status="OK", observations=observations)

    def supply(self, asset: str) -> contracts.ToolResult:
        """Measured supply bars from the corpus series (verbatim bars)."""
        observations = self._bars("supply", "", asset)
        if not observations:
            return _no_data()
        return contracts.ToolResult(ok=True, status="OK", observations=observations)

    def chain(self, chain_id: str, address: str) -> contracts.ToolResult:
        """No RPC collector in this wave — an honest refusal, never fake rows."""
        return contracts.ToolResult(
            ok=False, status="UNAVAILABLE",
            error="%s:read_chain(%s|%s)" % (NO_LIVE_SOURCE_CODE, chain_id, address))

    def document(self, url: str) -> contracts.ToolResult:
        """One archived corpus document (manifest file), wrapped as untrusted."""
        path = self._document_path(str(url or ""))
        if not path:
            return _no_data()
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                raw = handle.read()
        except OSError:
            return _no_data()
        observation = _document_observation(str(url), raw)
        relpath = os.path.relpath(path, self.corpus_dir).replace("\\", "/")
        digest = contracts.content_hash({"url": str(url), "sha": observation["content_sha256"]})[:16]
        source_ref = "corpus:%s:%s" % (relpath, digest)
        observation["source_ref"] = source_ref
        observation["refs"] = [source_ref, str(url)]
        return contracts.ToolResult(ok=True, status="OK", observations=(observation,))

    def _document_path(self, url: str) -> Optional[str]:
        """The archived file of one URL (declared corpus manifest endpoints).

        Fail-closed on purpose: a URL the corpus never archived is
        ``E_TOOL_NO_DATA`` — the source never serves a look-alike file whose
        name merely resembles the URL.
        """
        wanted = _url_token(url)
        if not wanted:
            return None
        for manifest_name in ("manifest.json", "calm_manifest.json"):
            manifest = os.path.join(self.corpus_dir, manifest_name)
            if not os.path.exists(manifest):
                continue
            try:
                with open(manifest, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except (OSError, ValueError):
                continue
            for entry in (data.get("sources") or ()) if isinstance(data, Mapping) else ():
                if not isinstance(entry, Mapping):
                    continue
                if _url_token(entry.get("endpoint")) != wanted:
                    continue
                candidate = self._resolve_archive(str(entry.get("file") or ""))
                if candidate:
                    return candidate
        return None

    def _resolve_archive(self, relative: str) -> Optional[str]:
        """A manifest ``file`` entry -> a readable path (repo- or corpus-rooted)."""
        if not relative:
            return None
        candidates = (relative,
                      os.path.join(os.path.dirname(self.corpus_dir), relative),
                      os.path.join(self.corpus_dir, relative))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None


def _row_refs(row: Mapping[str, Any]) -> Tuple[str, ...]:
    """``graph:``-prefixed row identifiers present in one response row."""
    refs: List[str] = []

    def _walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                if key in _ROW_ID_KEYS and str(item or "").strip():
                    ref = "graph:%s" % str(item).strip()
                    if ref not in refs:
                        refs.append(ref)
                _walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                _walk(item)

    _walk(row)
    return tuple(refs)


# ---------------------------------------------------------------------------
# REPLAY mode + recording (same store, both directions).
# ---------------------------------------------------------------------------
class ReplayedTool:
    """Registry adapter: serves the recorded response of one tool's calls."""

    def __init__(self, inner: Any, replay: "ReplaySource") -> None:
        self.inner = inner
        self.name = str(getattr(inner, "name", "") or "")
        self._replay = replay

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 20.0) -> contracts.ToolResult:
        # ``deadline_s`` is execution budget, not data: the recorded response
        # is what the call observed, whatever budget framed it.
        return self._replay.run(self.name, dict(args or {}))


class ReplaySource:
    """REPLAY mode: recorded responses only (``inner`` is never consulted).

    Every call ``(tool_name, canonical args)`` is content-addressed; a recorded
    hit is served **bit-identical** and a miss fails closed with
    ``E_TOOL_NOT_RECORDED:<key>`` — REPLAY never simulates what LIVE never
    recorded. ``inner`` is the live interface that produced the recording; it
    is kept for provenance and is never a fallback.
    """

    def __init__(self, inner: Any, store_dir: str) -> None:
        self.inner = inner
        self.store = ToolResponseStore(store_dir)

    def run(self, tool_name: str, args: Mapping[str, Any], *,
            deadline_s: float = 20.0) -> contracts.ToolResult:
        key = response_key(tool_name, args)
        recorded = self.store.lookup(key)
        if recorded is None:
            return contracts.ToolResult(
                ok=False, status="FAILED", error="%s:%s" % (NOT_RECORDED_CODE, key))
        return recorded

    def wrap(self, tool: Any) -> ReplayedTool:
        """One registry tool enveloped in this replay source."""
        return ReplayedTool(tool, self)


class RecordingTool:
    """Registry adapter: records every live response into the call store.

    This is what makes a LIVE run re-playable: the store this writes is the
    store :class:`ReplaySource` reads.
    """

    def __init__(self, inner: Any, store: ToolResponseStore) -> None:
        self.inner = inner
        self.name = str(getattr(inner, "name", "") or "")
        self.store = store

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 20.0) -> contracts.ToolResult:
        result = self.inner.run(dict(args or {}), deadline_s=deadline_s)
        self.store.record(self.name, dict(args or {}), result)
        return result


class SourceTool:
    """Registry adapter: one tool name bound to one source method.

    Used for the three graph tools of LIVE/REPLAY: the real tool code lives in
    :mod:`orvyren.agents.graph_tools` (owned by :class:`LiveSource`), this
    adapter only binds the registry name to it.
    """

    def __init__(self, name: str, source: Any, method: str,
                 deadline_s: float = 20.0) -> None:
        self.name = str(name)
        self._source = source
        self._method = str(method)
        self._deadline_s = float(deadline_s)

    def run(self, args: Mapping[str, Any], *,
            deadline_s: Optional[float] = None) -> contracts.ToolResult:
        budget = self._deadline_s if deadline_s is None else float(deadline_s)
        return getattr(self._source, self._method)(dict(args or {}),
                                                  deadline_s=budget)
