# -*- coding: utf-8 -*-
"""``tools`` — the v1 tool registry of the research agents (W2 lot L2.2).

The registry is an **allow-list**, never a deny-list: only explicitly
registered names are callable, and ``execute_intent`` — the action tool of the
policy layer — can never be registered (DOC2 §5.2.5: "never exposed to
research agents"; boundary rule of DOC4 W2). Research agents read, they never
act.

The seven v1 tools are **offline and deterministic**: each one answers from
fixtures injected at construction time (no network, no LLM, no computation).
The frozen fixture schema (the committed run inputs and the seed script follow
it verbatim) is::

    {
      "prices":    {"<venue>|<symbol>": [observation, ...]},
      "supply":    {"<asset>": [observation, ...]},
      "chain":     {"<chain_id>|<address>": [observation, ...]},
      "documents": {"<url>": "<raw text>"},
      "signals":   {"<signal_id>": {"value": ..., "unit": "...", "method_ref": "..."}},
      "snapshot":  {...}
    }

Lookup keys (one composite key per tool, no search, no fuzzy match):
``read_prices`` -> ``venue|symbol`` · ``read_supply`` -> ``asset`` ·
``read_chain`` -> ``chain_id|address`` · ``fetch_document`` -> ``url`` ·
``compute_signal`` -> ``signal_id`` · ``graph_query`` -> ``snapshot``.
Extra args (``from`` / ``to`` windows) are **ignored**: the window is already
archived in the fixture (the fixture IS the archived retrieval).

Two hygiene rules are enforced by construction, not by convention:

- ``fetch_document`` never returns interpretable content — the raw text is
  wrapped between the spotlighting delimiters
  (:func:`contracts.wrap_untrusted`) and the instruction-like flags are
  reported as **visible data** (:func:`contracts.scan_untrusted_flags`),
  never filtered away;
- ``compute_signal`` copies a **precomputed** value + unit + method reference
  out of the fixture — no figure of this layer is computed by an LLM.

Failure contract: missing data -> ``ToolResult(ok=False, status="FAILED",
error="E_TOOL_NO_DATA")``. Unknown tool name -> ``KeyError("E_TOOL_UNKNOWN")``.

Standard library only.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple

from orvyren.agents import contracts
from orvyren.agents.journal import AgentJournal

__all__ = [
    "FORBIDDEN_TOOL",
    "TOOL_NAMES",
    "NO_DATA_CODE",
    "ToolRegistry",
    "build_v1_registry",
    "FailingTool",
    "ReadPricesTool",
    "ReadSupplyTool",
    "ReadChainTool",
    "FetchDocumentTool",
    "ComputeSignalTool",
    "GraphQueryTool",
    "JournalWriteTool",
]

#: The policy-layer action tool — refused at registration time, for ever.
FORBIDDEN_TOOL = "execute_intent"

#: The seven v1 tools, in the frozen order of DOC2 §5.2.5 (``execute_intent``
#: is deliberately absent from this tuple).
TOOL_NAMES: Tuple[str, ...] = (
    "read_prices",
    "read_supply",
    "read_chain",
    "fetch_document",
    "compute_signal",
    "graph_query",
    "journal_write",
)

#: Error code of the single failure contract of a fixture-backed tool.
NO_DATA_CODE = "E_TOOL_NO_DATA"


# ---------------------------------------------------------------------------
# Small helpers (fixture plumbing).
# ---------------------------------------------------------------------------
def _bucket(fixtures: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    """The fixture sub-mapping of one tool (empty mapping when absent)."""
    value = fixtures.get(key) if isinstance(fixtures, Mapping) else None
    return value if isinstance(value, Mapping) else {}


def _no_data() -> contracts.ToolResult:
    """The one failure contract of a fixture tool: the data is not archived."""
    return contracts.ToolResult(ok=False, status="FAILED", error=NO_DATA_CODE)


def _observations(rows: Any) -> Tuple[Dict[str, Any], ...]:
    """Verbatim copy of the fixture rows (mappings only, order preserved)."""
    if not isinstance(rows, (list, tuple)):
        return ()
    return tuple(dict(row) for row in rows if isinstance(row, Mapping))


def _text(args: Mapping[str, Any], key: str) -> str:
    """One lookup fragment of ``args`` as text (missing -> empty string)."""
    value = (args or {}).get(key, "")
    return "" if value is None else str(value)


# ---------------------------------------------------------------------------
# The registry (allow-list).
# ---------------------------------------------------------------------------
class ToolRegistry:
    """Closed allow-list of the tools a research agent may call.

    ``register`` refuses ``execute_intent`` (by name **and** by tool ``name``),
    refuses a name/tool mismatch and refuses a tool without a callable
    ``run``. ``get`` raises :class:`KeyError` ``E_TOOL_UNKNOWN`` for any name
    that was not explicitly registered — an unknown tool is never a silent
    no-op.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, contracts.Tool] = {}

    # -- writes ------------------------------------------------------------
    def register(self, name: str, tool: Any) -> Any:
        """Add one tool to the allow-list; returns the tool for chaining."""
        clean = str(name or "").strip()
        aliased = str(getattr(tool, "name", "") or "").strip()
        if clean == FORBIDDEN_TOOL or aliased == FORBIDDEN_TOOL:
            raise ValueError(
                "E_TOOL_FORBIDDEN: execute_intent is never exposed to research agents")
        if not clean:
            raise ValueError("E_TOOL_NAME: a tool name is required")
        if aliased and aliased != clean:
            raise ValueError("E_TOOL_NAME_MISMATCH: %r != %r" % (aliased, clean))
        if not callable(getattr(tool, "run", None)):
            raise ValueError("E_TOOL_CONTRACT: %s has no callable run()" % clean)
        self._tools[clean] = tool
        return tool

    # -- reads -------------------------------------------------------------
    def get(self, name: str) -> Any:
        """The registered tool, or :class:`KeyError` ``E_TOOL_UNKNOWN``."""
        clean = str(name or "").strip()
        if clean not in self._tools:
            raise KeyError("E_TOOL_UNKNOWN: %s" % clean)
        return self._tools[clean]

    def has(self, name: str) -> bool:
        """True when the name is in the allow-list (no exception raised)."""
        return str(name or "").strip() in self._tools

    def names(self) -> Tuple[str, ...]:
        """Registered names, in registration order (the allow-list itself)."""
        return tuple(self._tools)

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: object) -> bool:
        return str(name or "").strip() in self._tools


# ---------------------------------------------------------------------------
# The seven v1 tools.
# ---------------------------------------------------------------------------
class ReadPricesTool:
    """``read_prices`` — archived venue prices, keyed ``venue|symbol``.

    Read-only; returns the fixture observations **verbatim** (source, timestamp
    and value included as archived). Extra args (``from``/``to``) are ignored —
    the window is already archived.
    """

    name = "read_prices"

    def __init__(self, fixtures: Mapping[str, Any]) -> None:
        self._fixtures = fixtures

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 20.0) -> contracts.ToolResult:
        key = "%s|%s" % (_text(args, "venue"), _text(args, "symbol"))
        observations = _observations(_bucket(self._fixtures, "prices").get(key))
        if not observations:
            return _no_data()
        return contracts.ToolResult(ok=True, status="OK", observations=observations)


class ReadSupplyTool:
    """``read_supply`` — archived supply observations, keyed ``asset``."""

    name = "read_supply"

    def __init__(self, fixtures: Mapping[str, Any]) -> None:
        self._fixtures = fixtures

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 20.0) -> contracts.ToolResult:
        observations = _observations(
            _bucket(self._fixtures, "supply").get(_text(args, "asset")))
        if not observations:
            return _no_data()
        return contracts.ToolResult(ok=True, status="OK", observations=observations)


class ReadChainTool:
    """``read_chain`` — archived on-chain observations, keyed ``chain_id|address``."""

    name = "read_chain"

    def __init__(self, fixtures: Mapping[str, Any]) -> None:
        self._fixtures = fixtures

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 30.0) -> contracts.ToolResult:
        key = "%s|%s" % (_text(args, "chain_id"), _text(args, "address"))
        observations = _observations(_bucket(self._fixtures, "chain").get(key))
        if not observations:
            return _no_data()
        return contracts.ToolResult(ok=True, status="OK", observations=observations)


class FetchDocumentTool:
    """``fetch_document`` — one archived raw document, wrapped as untrusted.

    The payload is **never interpreted**: it is delimited by
    :func:`contracts.wrap_untrusted`, stamped with its origin and returned with
    the instruction-like flags found by
    :func:`contracts.scan_untrusted_flags` (a journal-able flag, never a
    silent filter). The bare text is not returned at all.
    """

    name = "fetch_document"

    def __init__(self, fixtures: Mapping[str, Any]) -> None:
        self._fixtures = fixtures

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 30.0) -> contracts.ToolResult:
        url = _text(args, "url")
        raw = _bucket(self._fixtures, "documents").get(url)
        if not url or not isinstance(raw, str):
            return _no_data()
        observation = {
            "url": url,
            "untrusted": True,
            "content": contracts.wrap_untrusted(raw, url),
            "untrusted_flags": contracts.scan_untrusted_flags(raw),
            "content_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        }
        return contracts.ToolResult(ok=True, status="OK", observations=(observation,))


class ComputeSignalTool:
    """``compute_signal`` — a **precomputed** signal (value + unit + method ref).

    The tool computes nothing: it copies the archived value, its unit and its
    method reference. A fixture entry without a non-empty ``value``,
    ``unit`` and ``method_ref`` is refused (fail-closed: a signal without unit
    or method is not usable evidence).
    """

    name = "compute_signal"

    def __init__(self, fixtures: Mapping[str, Any]) -> None:
        self._fixtures = fixtures

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 5.0) -> contracts.ToolResult:
        row = _bucket(self._fixtures, "signals").get(_text(args, "signal_id"))
        if not isinstance(row, Mapping):
            return _no_data()
        if not str(row.get("unit", "")).strip() or not str(row.get("method_ref", "")).strip():
            return _no_data()
        if "value" not in row:
            return _no_data()
        return contracts.ToolResult(ok=True, status="OK", observations=(dict(row),))


class GraphQueryTool:
    """``graph_query`` — the frozen snapshot of the fixture (read-only).

    The snapshot is the point-in-time boundary of the decision; args are not
    used to re-derive it (the fixture is already frozen), so the same run
    always reads the same graph state.
    """

    name = "graph_query"

    def __init__(self, fixtures: Mapping[str, Any]) -> None:
        self._fixtures = fixtures

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 5.0) -> contracts.ToolResult:
        snapshot = self._fixtures.get("snapshot") if isinstance(self._fixtures, Mapping) else None
        if not isinstance(snapshot, Mapping) or not snapshot:
            return _no_data()
        return contracts.ToolResult(ok=True, status="OK",
                                    observations=(dict(snapshot),))


class _ToolClock:
    """Minimal default clock of the registry tools (journal timestamps only).

    The bounded loop never uses this class — it receives its clock by
    injection (:class:`orvyren.agents.loop.BoundedLoop`). This one only stamps
    ``journal_write`` lines when the caller pins no ``ts_utc`` argument.
    """

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()


class JournalWriteTool:
    """``journal_write`` — appends ONE line to the caller's journal.

    Writes into **its own** journal (the :class:`AgentJournal` injected at
    construction) through :meth:`AgentJournal.append_dict`, and returns the new
    ``journal_id`` in the observations. Line identity (``run_id``, ``agent_id``,
    ``step_index``, ``ts_utc``, ``role_version``, ...) may be pinned through
    ``args`` so a replay reproduces the line; unbound fields get non-empty
    defaults. A missing ``content`` is the data error (``E_TOOL_NO_DATA``) and
    a mistyped ``refs`` / ``step_index`` is refused (``E_TOOL_ARGS_TYPE`` — a
    bare string would be iterated character by character); a non-conforming
    line is still appended and reported ``REJECTED`` /
    ``QUARANTINED`` by the journal — the refusal stays visible.
    """

    name = "journal_write"

    def __init__(self, journal: AgentJournal, *, clock: Any = None,
                 prefix: str = "jw") -> None:
        self._journal = journal
        self._clock = clock or _ToolClock()
        self._prefix = str(prefix or "jw")
        self._counter = 0

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 2.0) -> contracts.ToolResult:
        supplied = dict(args or {})
        content = str(supplied.pop("content", "") or "")
        if not content.strip():
            return _no_data()
        kind = str(supplied.pop("kind", "") or "REFLECTION")
        refs = supplied.pop("refs", ())
        if refs is not None and not isinstance(refs, (list, tuple)):
            # A bare string would be iterated character by character and pollute
            # the journal refs with one-character "references".
            return contracts.ToolResult(ok=False, status="FAILED",
                                        error="E_TOOL_ARGS_TYPE:refs")
        if "step_index" in supplied and (isinstance(supplied["step_index"], bool)
                                         or not isinstance(supplied["step_index"], int)):
            return contracts.ToolResult(ok=False, status="FAILED",
                                        error="E_TOOL_ARGS_TYPE:step_index")
        self._counter += 1
        # Unknown keys are NOT dropped here: the journal quarantines them, so
        # the refusal stays visible ("never a filter that deletes silently",
        # B1 §5.6) — the tool never edits a line into validity.
        data = dict(supplied)
        data.setdefault("journal_id", "%s-%s" % (
            self._prefix,
            contracts.content_hash({"n": self._counter, "kind": kind,
                                    "content": content})[:16]))
        defaults = {"run_id": "unbound", "episode_id": "unbound",
                    "agent_id": "orchestrator", "role_version": "tool-jw/v1",
                    "step_index": self._counter - 1, "ts_utc": self._clock.now_iso()}
        for key, value in defaults.items():
            data.setdefault(key, value)
        data.update({"kind": kind, "content": content,
                     "refs": tuple(str(ref) for ref in (refs or ()))})
        entry = self._journal.append_dict(data)
        return contracts.ToolResult(ok=True, status="OK", observations=(
            {"journal_id": entry.journal_id, "status": entry.status,
             "step_index": entry.step_index, "kind": entry.kind},))


#: Registry name -> tool class, in the frozen v1 order.
_TOOL_CLASSES: Tuple[Tuple[str, type], ...] = (
    ("read_prices", ReadPricesTool),
    ("read_supply", ReadSupplyTool),
    ("read_chain", ReadChainTool),
    ("fetch_document", FetchDocumentTool),
    ("compute_signal", ComputeSignalTool),
    ("graph_query", GraphQueryTool),
)


class FailingTool:
    """Test double: a source that is down (B1 §4.4, "failed tool").

    ``fail_times=None`` fails on every call; ``fail_times=n`` fails the first
    ``n`` calls then answers once (used to script retry-then-recover paths).
    ``calls`` counts the attempts, so a test can assert the retry ceiling.
    """

    def __init__(self, name: str = "failing_tool", *,
                 error: str = "E_TOOL_UPSTREAM", fail_times: Optional[int] = None,
                 status: str = "FAILED") -> None:
        self.name = str(name)
        self.calls = 0
        self._error = str(error)
        self._fail_times = None if fail_times is None else int(fail_times)
        self._status = str(status)

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 20.0) -> contracts.ToolResult:
        self.calls += 1
        if self._fail_times is None or self.calls <= self._fail_times:
            return contracts.ToolResult(ok=False, status=self._status,
                                        error=self._error)
        return contracts.ToolResult(ok=True, status="OK", observations=(
            {"tool": self.name, "attempt": self.calls},))


def build_v1_registry(*, fixtures: Mapping[str, Any],
                      journal: AgentJournal) -> ToolRegistry:
    """Build the v1 allow-list on the frozen fixtures (worker entry point).

    Registers exactly the seven v1 tools (``TOOL_NAMES``) — ``execute_intent``
    is not registerable. ``fixtures`` follows the frozen schema documented in
    this module's docstring; ``journal`` is the journal ``journal_write``
    appends to (one journal per agent process, B1 §3.4).
    """
    registry = ToolRegistry()
    for name, tool_class in _TOOL_CLASSES:
        registry.register(name, tool_class(fixtures))
    registry.register("journal_write", JournalWriteTool(journal))
    return registry
