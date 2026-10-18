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

The registry is **mode-unified** (P0-1): the tool code above is unique and only
its data provider changes — :func:`build_registry` selects it:

- ``"fixture"`` -> :class:`orvyren.agents.tool_sources.FixtureSource` (the
  seven v1 tools, ``compute_signal`` included — simulated data, labelled);
- ``"live"`` -> :class:`orvyren.agents.tool_sources.LiveSource`: the real
  graph tools of :mod:`orvyren.agents.graph_tools` (Q1–Q8) + the measured
  corpus series, with provenance; **no** ``compute_signal`` (a precomputed
  signal is a fixture-only decision) and ``read_chain`` honestly
  ``UNAVAILABLE`` (``E_TOOL_NO_LIVE_SOURCE``);
- ``"replay"`` -> the live tool set enveloped in
  :class:`orvyren.agents.tool_sources.ReplaySource`: recorded responses only
  (``E_TOOL_NOT_RECORDED:<key>`` on a miss, never a simulation).

``build_v1_registry`` stays as the fixture wrapper of
``build_registry(mode="fixture", ...)``. The full mode contract lives in
:mod:`orvyren.agents.tool_sources`.

**Memory is opt-in** (``build_registry(..., memory=...)``, wired by
``worker._build_tools`` behind ``run_agents.py --memory``): attaching an
:class:`orvyren.agents.memory.FTSMemory` adds one ``memory_recall`` tool and
remembers every successful tool observation. Without it the allow-list,
the payloads and the recorded prompts stay exactly as before — which is what
keeps the sealed store replaying bit for bit.

Standard library only.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple

from orvyren.agents import contracts
from orvyren.agents.journal import AgentJournal
from orvyren.agents.memory import refs_from_observations
from orvyren.agents.tool_sources import (
    MODES,
    NO_DATA_CODE,
    FixtureSource,
    LiveSource,
    RecordingTool,
    ReplaySource,
    ToolResponseStore,
    SourceTool,
)

__all__ = [
    "FORBIDDEN_TOOL",
    "TOOL_NAMES",
    "LIVE_TOOL_NAMES",
    "MEMORY_TOOL_NAME",
    "MEMORY_TOOL_SPEC",
    "MEMORY_QUERY_MAX_CHARS",
    "MEMORY_K_MIN",
    "MEMORY_K_MAX",
    "MEMORY_DEFAULT_K",
    "MODES",
    "NO_DATA_CODE",
    "ToolRegistry",
    "build_registry",
    "build_v1_registry",
    "FailingTool",
    "MemoryRecallTool",
    "ObservationMemory",
    "RememberingTool",
    "observation_memory_id",
    "observation_refs",
    "observation_text",
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

#: The live/replay registry names (P0-1): the v1 set minus ``compute_signal``
#: plus the two real graph tools (``graph_path``, ``graph_snapshot``).
LIVE_TOOL_NAMES: Tuple[str, ...] = (
    "read_prices",
    "read_supply",
    "read_chain",
    "fetch_document",
    "graph_query",
    "graph_path",
    "graph_snapshot",
    "journal_write",
)

#: Name of the OPTIONAL memory tool. It is registered **only** when an
#: :class:`orvyren.agents.memory.FTSMemory` is attached to the registry
#: (``--memory``): by default the allow-list — and therefore every recorded
#: prompt that lists it — is byte-identical to the pre-memory run.
MEMORY_TOOL_NAME = "memory_recall"

#: Longest accepted recall query (chars, trimmed check + raw length bound).
MEMORY_QUERY_MAX_CHARS = 200

#: Closed bounds of ``memory_recall.k`` (P1-1: ``k`` is a real bound, and a
#: negative/zero/huge value is refused instead of silently unbounding the
#: search — ``LIMIT -1`` in SQLite means unlimited).
MEMORY_K_MIN = 1
MEMORY_K_MAX = 10
MEMORY_DEFAULT_K = 5

#: OpenAI-style spec of ``memory_recall`` (English, closed object). The bound
#: values are duplicated in the schema for the provider: the CODE re-checks
#: them, the schema only documents them.
MEMORY_TOOL_SPEC: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": MEMORY_TOOL_NAME,
        "description": (
            "Recall earlier observations of this run from the local FTS memory. "
            "Returns at most k entries, each with the evidence refs of the "
            "observation it came from. The search is lexical (SQLite FTS5) over "
            "the remembered summaries: pass a few keywords, not a question."),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": MEMORY_QUERY_MAX_CHARS,
                    "description": "Keywords looked for in remembered observations.",
                },
                "k": {
                    "type": "integer",
                    "minimum": MEMORY_K_MIN,
                    "maximum": MEMORY_K_MAX,
                    "default": MEMORY_DEFAULT_K,
                    "description": "Maximum number of entries returned (1..10).",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}


# ---------------------------------------------------------------------------
# Small helpers (arg parsing, fixture plumbing).
# ---------------------------------------------------------------------------
def _source_of(fixtures_or_source: Any) -> Any:
    """The data provider behind a tool: a source, or the frozen fixtures.

    Every tool constructor accepts either a prepared source
    (:class:`FixtureSource` / :class:`LiveSource`) or the legacy fixtures
    mapping — the tool code is unique, only the provider changes (P0-1).
    """
    if isinstance(fixtures_or_source, Mapping):
        return FixtureSource(fixtures_or_source)
    return fixtures_or_source


def _text(args: Mapping[str, Any], key: str) -> str:
    """One lookup fragment of ``args`` as text (missing -> empty string)."""
    value = (args or {}).get(key, "")
    return "" if value is None else str(value)


def _fixture_refs(fixtures: Any) -> Tuple[str, ...]:
    """Every source reference archived in a fixture payload (P0-6 seed).

    The archived rows are the observed sources of a fixture run: seeding the
    reference ledger from them keeps claim validation strict with no
    hand-maintained allow-list — anything the fixtures really archive is
    citable, anything else is not.
    """
    refs: List[str] = []

    def _collect(value: Any) -> None:
        if isinstance(value, Mapping):
            for key in ("source_ref", "ref", "url", "method_ref"):
                ref = value.get(key)
                if ref and str(ref) not in refs:
                    refs.append(str(ref))
            declared = value.get("refs")  # a snapshot declares its own refs
            if isinstance(declared, (list, tuple)):
                for ref in declared:
                    if ref and str(ref) not in refs:
                        refs.append(str(ref))
            for item in value.values():
                _collect(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                _collect(item)

    for key in ("prices", "supply", "chain", "documents", "signals", "snapshot"):
        bucket = (fixtures or {}).get(key) if isinstance(fixtures, Mapping) else None
        if key == "documents" and isinstance(bucket, Mapping):
            for url in bucket:  # a document is cited by its URL
                if str(url) not in refs:
                    refs.append(str(url))
        else:
            _collect(bucket)
    return tuple(refs)


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
    """``read_prices`` — venue prices from the source, keyed ``venue|symbol``.

    Read-only; returns the source observations **verbatim** (source, timestamp
    and value included as archived). Extra args (``from``/``to``) are ignored —
    the window is already archived. The provider is a :class:`FixtureSource`
    (frozen fixtures) or a :class:`LiveSource` (measured corpus): same tool
    code, only the data provider changes (P0-1).
    """

    name = "read_prices"

    def __init__(self, source: Any) -> None:
        self._source = _source_of(source)

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 20.0) -> contracts.ToolResult:
        return self._source.prices(_text(args, "venue"), _text(args, "symbol"))


class ReadSupplyTool:
    """``read_supply`` — supply observations from the source, keyed ``asset``."""

    name = "read_supply"

    def __init__(self, source: Any) -> None:
        self._source = _source_of(source)

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 20.0) -> contracts.ToolResult:
        return self._source.supply(_text(args, "asset"))


class ReadChainTool:
    """``read_chain`` — on-chain observations, keyed ``chain_id|address``.

    FIXTURE answers from the archived rows; LIVE answers an honest
    ``UNAVAILABLE`` / ``E_TOOL_NO_LIVE_SOURCE`` (no RPC collector yet).
    """

    name = "read_chain"

    def __init__(self, source: Any) -> None:
        self._source = _source_of(source)

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 30.0) -> contracts.ToolResult:
        return self._source.chain(_text(args, "chain_id"), _text(args, "address"))


class FetchDocumentTool:
    """``fetch_document`` — one archived raw document, wrapped as untrusted.

    The payload is **never interpreted**: it is delimited by
    :func:`contracts.wrap_untrusted`, stamped with its origin and returned with
    the instruction-like flags found by
    :func:`contracts.scan_untrusted_flags` (a journal-able flag, never a
    silent filter). The bare text is not returned at all. FIXTURE reads the
    fixture bucket; LIVE reads the archived corpus document.
    """

    name = "fetch_document"

    def __init__(self, source: Any) -> None:
        self._source = _source_of(source)

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 30.0) -> contracts.ToolResult:
        return self._source.document(_text(args, "url"))


class ComputeSignalTool:
    """``compute_signal`` — a **precomputed** signal (value + unit + method ref).

    The tool computes nothing: it copies the archived value, its unit and its
    method reference. A fixture entry without a non-empty ``value``,
    ``unit`` and ``method_ref`` is refused (fail-closed: a signal without unit
    or method is not usable evidence). FIXTURE-only by contract: a precomputed
    signal is a hard decision and is never substituted in LIVE/REPLAY.
    """

    name = "compute_signal"

    def __init__(self, source: Any) -> None:
        self._source = _source_of(source)

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 5.0) -> contracts.ToolResult:
        return self._source.signal(_text(args, "signal_id"))


class GraphQueryTool:
    """``graph_query`` — the frozen snapshot of the fixture (read-only).

    The snapshot is the point-in-time boundary of the decision; args are not
    used to re-derive it (the fixture is already frozen), so the same run
    always reads the same graph state. This fixture tool is **not** registered
    in LIVE/REPLAY mode — there the real ``graph_tools`` tools answer from the
    graph API (P0-1).
    """

    name = "graph_query"

    def __init__(self, source: Any) -> None:
        self._source = _source_of(source)

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 5.0) -> contracts.ToolResult:
        return self._source.snapshot()


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
                 prefix: str = "jw",
                 observed: Optional[contracts.ObservedRefs] = None) -> None:
        self._journal = journal
        self._clock = clock or _ToolClock()
        self._prefix = str(prefix or "jw")
        self._counter = 0
        self._observed = observed

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 2.0) -> contracts.ToolResult:
        supplied = dict(args or {})
        content = str(supplied.pop("content", "") or "")
        if not content.strip():
            return contracts.ToolResult(ok=False, status="FAILED",
                                        error=NO_DATA_CODE)
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
        # P0-6 provenance contract: a claim may only cite references really
        # observed by this run. An unknown reference is refused — the line is
        # still appended (status REJECTED, motif kept), the refusal stays
        # visible, and the reference is never replaced by a look-alike source.
        reject_reason = ""
        if self._observed is not None:
            unknown = self._observed.unknown(refs or ())
            if unknown:
                reject_reason = "E_REF_NOT_OBSERVED: %s" % ", ".join(unknown)
        entry = self._journal.append_dict(data, reject_reason=reject_reason)
        return contracts.ToolResult(ok=True, status="OK", observations=(
            {"journal_id": entry.journal_id, "status": entry.status,
             "step_index": entry.step_index, "kind": entry.kind},))


# ---------------------------------------------------------------------------
# Memory wiring (M9): remember every observation, recall it with a tool.
# ---------------------------------------------------------------------------
#: Observation keys carrying a *real* evidence reference. Nothing synthetic is
#: added here: the loop's journal adds ``observation:<tool>`` as a fallback,
#: but such a marker is not evidence, and an entry without evidence refs
#: cannot be used — the memory refuses it instead of storing noise.
_OBSERVATION_REF_KEYS: Tuple[str, ...] = (
    "source_ref", "ref", "url", "method_ref",
)


def observation_refs(result: contracts.ToolResult) -> Tuple[str, ...]:
    """The evidence refs of one tool result (stable order, no duplicate).

    Top-level ``source_ref`` / ``ref`` / ``url`` / ``method_ref`` plus the
    per-row ``refs`` a source declares, plus the nested keys scanned by
    :func:`orvyren.agents.memory.refs_from_observations` (``relation_id``,
    ``ref_id``, ``graph_hash``, ``snapshot_ref`` inside the rows of an API
    response). These are the ``refs`` a memory entry carries — never a
    fabricated ``observation:<tool>`` placeholder.
    """
    refs: List[str] = []

    def _add(value: Any) -> None:
        if isinstance(value, str) and value.strip() and value not in refs:
            refs.append(value)

    for observation in result.observations or ():
        if not isinstance(observation, Mapping):
            continue
        for key in _OBSERVATION_REF_KEYS:
            _add(observation.get(key))
        declared = observation.get("refs")
        if isinstance(declared, (list, tuple)):
            for ref in declared:
                _add(ref)
    for ref in refs_from_observations(result.observations or ()):
        _add(ref)
    return tuple(refs)


def observation_text(tool_name: str, observations: Any, limit: int = 800) -> str:
    """Bounded summary of one observation set — the ``text`` of a memory entry.

    Canonical JSON keeps the summary deterministic (same observation, same
    text) and bounded: a memory entry is a searchable digest of what was
    observed, not a copy of the whole payload.
    """
    payload = {
        "tool": str(tool_name or ""),
        "observations": [dict(item) if isinstance(item, Mapping) else item
                         for item in (observations or ())],
    }
    try:
        text = contracts.canonical_json(payload)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        text = str(payload)
    return text[:max(1, int(limit))]


def observation_memory_id(role: str, run_id: str, step_index: int) -> str:
    """Deterministic memory id of one observation: ``sha256(role|run_id|step)``.

    The step index is the index of the recorded observation in the run, so the
    id is a pure function of the call sequence: replaying a run produces the
    very same ids (``remember`` replaces by ``memory_id``, it never duplicates).
    """
    raw = "%s|%s|%d" % (str(role or ""), str(run_id or ""), int(step_index))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ObservationMemory:
    """Remembers every successful tool observation of a run (``--memory``).

    One entry per observation: ``text`` = bounded summary of the observed
    payload, ``refs`` = the observation's own evidence refs, ``memory_id`` =
    :func:`observation_memory_id`. A failed tool call leaves no entry (an
    error is not an observation) and a result without any evidence ref is not
    remembered (an entry without refs cannot be used). A memory write never
    breaks a tool call: the failure is journaled as a visible ``ERROR`` line
    and the tool result travels unchanged.
    """

    def __init__(self, memory: Any, *, role: str = "orchestrator",
                 run_id: str = "", clock: Any = None,
                 journal: Any = None) -> None:
        self.memory = memory
        self.role = str(role or "")
        self.run_id = str(run_id or "")
        self.journal = journal
        self._clock = clock
        self._step = 0

    def _now_iso(self) -> str:
        now_iso = getattr(self._clock, "now_iso", None)
        if callable(now_iso):
            return str(now_iso())
        return datetime.now(timezone.utc).isoformat()

    def _journal_failure(self, step: int, exc: Exception) -> None:
        """One visible ``ERROR`` line — a failed remember is never silent."""
        if self.journal is None:
            return
        try:
            self.journal.append_dict({
                "journal_id": "mem-%s-%s-%04d" % (self.run_id or "run",
                                                  self.role or "agent", step),
                "run_id": self.run_id, "episode_id": "", "agent_id": self.role,
                "role_version": "memory/v1", "step_index": step,
                "ts_utc": self._now_iso(), "kind": "ERROR", "refs": (),
                "content": "E_MEMORY_WRITE: %s" % type(exc).__name__})
        except Exception:  # the journal must never break the tool either
            pass

    def record(self, tool_name: str, result: contracts.ToolResult) -> Any:
        """Remember one tool observation; returns the entry or ``None``."""
        if result is None or not result.ok:
            return None
        refs = observation_refs(result)
        if not refs:
            return None
        step = self._step
        self._step += 1
        try:
            return self.memory.remember(
                observation_memory_id(self.role, self.run_id, step),
                observation_text(tool_name, result.observations), refs,
                kind="TOOL_RESULT", ts_utc=self._now_iso())
        except Exception as exc:
            self._journal_failure(step, exc)
            return None


class RememberingTool:
    """One registry tool wrapped so its successful observation is remembered.

    The wrapped result travels **verbatim** (same observations, same error):
    memory is an add-on of the run, never a rewrite of what the tool answered.
    """

    def __init__(self, tool: Any, recorder: ObservationMemory) -> None:
        self._tool = tool
        self._recorder = recorder
        self.name = str(getattr(tool, "name", "") or "")

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 20.0) -> contracts.ToolResult:
        result = self._tool.run(args, deadline_s=deadline_s)
        self._recorder.record(self.name, result)
        return result


class MemoryRecallTool:
    """``memory_recall`` — lexical recall over the run's FTS memory.

    Args are a **closed** object (``query``, ``k``) and both bounds are
    enforced by this code, not by the caller: an empty or oversized ``query``
    and a ``k`` outside 1..10 are refused with an ``E_TOOL_ARGS_*`` error —
    the same refusal mechanism as the graph tools (``ToolResult(ok=False)``),
    so a refusal is never a silent execution. The FTS search itself is
    bounded by ``k`` (never ``LIMIT -1``).
    """

    name = MEMORY_TOOL_NAME

    def __init__(self, memory: Any) -> None:
        self._memory = memory

    def _errors(self, args: Mapping[str, Any]) -> List[str]:
        errors = ["E_TOOL_ARGS_UNKNOWN:%s" % key
                  for key in sorted(set(args) - {"query", "k"})]
        query = args.get("query")
        if query is None:
            errors.append("E_TOOL_ARGS_REQUIRED:query")
        elif not isinstance(query, str):
            errors.append("E_TOOL_ARGS_TYPE:query")
        elif not query.strip():
            errors.append("E_TOOL_ARGS_RANGE:query[1..%d]" % MEMORY_QUERY_MAX_CHARS)
        elif len(query) > MEMORY_QUERY_MAX_CHARS:
            errors.append("E_TOOL_ARGS_RANGE:query[1..%d]" % MEMORY_QUERY_MAX_CHARS)
        k = args.get("k")
        if k is not None:
            if isinstance(k, bool) or not isinstance(k, int):
                errors.append("E_TOOL_ARGS_TYPE:k")
            elif k < MEMORY_K_MIN or k > MEMORY_K_MAX:
                errors.append("E_TOOL_ARGS_RANGE:k[%d..%d]"
                              % (MEMORY_K_MIN, MEMORY_K_MAX))
        return errors

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 5.0) -> contracts.ToolResult:
        supplied = dict(args or {})
        errors = self._errors(supplied)
        if errors:
            return contracts.ToolResult(ok=False, status="FAILED",
                                        error=";".join(errors))
        query = str(supplied.get("query")).strip()
        k = supplied.get("k")
        k = MEMORY_DEFAULT_K if k is None else int(k)
        try:
            entries = self._memory.recall(query, k)
        except ValueError as exc:  # E_MEMORY_K / a refused bound: fail-closed
            return contracts.ToolResult(ok=False, status="FAILED", error=str(exc))
        return contracts.ToolResult(ok=True, status="OK", observations=tuple(
            {"memory_id": entry.memory_id, "refs": list(entry.refs),
             "text": entry.text} for entry in entries))


def _with_memory(registry: ToolRegistry, memory: Any, *,
                 journal: Optional[AgentJournal], role: str, run_id: str,
                 clock: Any = None) -> ToolRegistry:
    """Same allow-list plus ``memory_recall`` and one rememberer per tool.

    ``journal_write`` is not wrapped: it is the run's own output sink (its
    "observation" is a journal id, not a fact about the world), and
    ``memory_recall`` is not wrapped either — a recall must never re-remember
    its own hits.
    """
    recorder = ObservationMemory(memory, role=role, run_id=run_id,
                                 clock=clock, journal=journal)
    with_memory = ToolRegistry()
    for name in registry.names():
        tool = registry.get(name)
        if name in (MEMORY_TOOL_NAME, "journal_write"):
            with_memory.register(name, tool)
        else:
            with_memory.register(name, RememberingTool(tool, recorder))
    with_memory.register(MEMORY_TOOL_NAME, MemoryRecallTool(memory))
    return with_memory


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


def _build_fixture_registry(*, fixtures: Mapping[str, Any],
                            journal: AgentJournal,
                            observed: Optional[contracts.ObservedRefs] = None
                            ) -> ToolRegistry:
    """The v1 allow-list on the frozen fixtures (FIXTURE mode internals)."""
    ledger = observed if observed is not None \
        else contracts.ObservedRefs(_fixture_refs(fixtures))
    registry = ToolRegistry()
    source = FixtureSource(fixtures)
    for name, tool_class in _TOOL_CLASSES:
        registry.register(name, tool_class(source))
    registry.register("journal_write", JournalWriteTool(journal, observed=ledger))
    return registry


def _mode_registry(*, mode: str, journal: AgentJournal,
                   observed: Optional[contracts.ObservedRefs] = None,
                   fixtures: Optional[Mapping[str, Any]] = None,
                   source: Any = None, store_dir: Optional[str] = None,
                   record_dir: Optional[str] = None,
                   db: Optional[str] = None, api: Any = None
                   ) -> ToolRegistry:
    """Build the mode-selected registry (P0-1); ``mode`` picks the providers.

    ``mode="fixture"``
        The v1 allow-list (``TOOL_NAMES``): simulated, explicitly labelled
        fixtures; ``compute_signal`` is part of it. ``build_v1_registry`` is
        this branch.
    ``mode="live"``
        The real allow-list (``LIVE_TOOL_NAMES``): the measured corpus
        (``read_prices`` / ``read_supply`` / ``fetch_document``), the real
        graph tools of :mod:`orvyren.agents.graph_tools` behind
        ``graph_query`` / ``graph_path`` / ``graph_snapshot`` (delegated, never
        duplicated), an honest ``UNAVAILABLE`` ``read_chain`` and
        ``journal_write``. **No** ``compute_signal`` and **no** fixture
        snapshot tool. Every graph observation carries a deterministic
        ``source_ref`` + row ``refs``. When ``record_dir`` is set, every
        response is recorded there (feeding a later REPLAY).
    ``mode="replay"``
        The live tool set enveloped in
        :class:`orvyren.agents.tool_sources.ReplaySource`: recorded responses
        served bit-identically, ``E_TOOL_NOT_RECORDED:<key>`` on a miss, never
        a silent simulation (``store_dir`` is required).

    ``source`` injects a prepared data source (tests, custom collectors);
    ``db`` / ``api`` configure the real graph API (``api`` defaults to
    :mod:`orvyren.graph.api`). ``execute_intent`` is not registerable in any
    mode (research agents read, they never act). An unknown mode raises
    :class:`ValueError` — it never falls back to another mode.
    """
    clean = str(mode or "").strip().lower()
    if clean not in MODES:
        raise ValueError("E_TOOL_MODE_UNKNOWN: %r" % mode)
    if clean == "fixture":
        return _build_fixture_registry(fixtures=fixtures, journal=journal,
                                       observed=observed)
    if clean == "replay" and not store_dir:
        raise ValueError("E_TOOL_REPLAY_STORE: replay mode needs store_dir")
    live = source if source is not None else LiveSource(db=db, api=api)
    ledger = observed if observed is not None else contracts.ObservedRefs()
    registry = ToolRegistry()
    for tool in (ReadPricesTool(live), ReadSupplyTool(live),
                 ReadChainTool(live), FetchDocumentTool(live)):
        registry.register(tool.name, tool)
    for name, method in (("graph_query", "graph_query"),
                         ("graph_path", "graph_path"),
                         ("graph_snapshot", "graph_snapshot")):
        registry.register(name, SourceTool(name, live, method))
    registry.register("journal_write", JournalWriteTool(journal, observed=ledger))
    if clean == "replay":
        return _wrap_registry(registry, ReplaySource(live, store_dir).wrap)
    if record_dir:
        store = ToolResponseStore(record_dir)
        return _wrap_registry(registry,
                              lambda tool: RecordingTool(tool, store))
    return registry


def build_registry(*, mode: str, journal: AgentJournal,
                   observed: Optional[contracts.ObservedRefs] = None,
                   fixtures: Optional[Mapping[str, Any]] = None,
                   source: Any = None, store_dir: Optional[str] = None,
                   record_dir: Optional[str] = None,
                   db: Optional[str] = None, api: Any = None,
                   memory: Any = None, memory_role: str = "orchestrator",
                   memory_run_id: str = "", clock: Any = None
                   ) -> ToolRegistry:
    """Build the ONE registry of the run (P0-1); ``mode`` picks the providers.

    The mode contract (fixture / live / replay, the calls they serve and the
    way they fail) is documented on :func:`_mode_registry`; this entry point
    only adds the **optional memory wiring**:

    ``memory=None`` (default)
        Exactly the mode's allow-list — the historical behaviour, unchanged:
        no ``FTSMemory`` instance, no extra tool, no extra prompt entry.
    ``memory=<FTSMemory>``
        The same allow-list **plus** ``memory_recall`` (closed args
        ``query``/``k``, bounds enforced by the code) and one
        :class:`RememberingTool` per data tool: every successful observation is
        stored with its evidence refs and a deterministic
        ``sha256(memory_role|memory_run_id|step)`` id, so a replay produces
        the same entries. ``journal_write`` and ``memory_recall`` are never
        wrapped (the run's own output sink, and a recall must not re-remember
        its own hits).
    """
    registry = _mode_registry(mode=mode, journal=journal, observed=observed,
                              fixtures=fixtures, source=source,
                              store_dir=store_dir, record_dir=record_dir,
                              db=db, api=api)
    if memory is None:
        return registry
    return _with_memory(registry, memory, journal=journal, role=memory_role,
                        run_id=memory_run_id, clock=clock)


#: Tools that are OUTPUT SINKS of the run itself, never replayable data
#: sources: a replayed run must still journal its claims (the P0-6 provenance
#: validation and the audit trail live in that journal).
_UNWRAPPED_IN_REPLAY: Tuple[str, ...] = ("journal_write",)


def _wrap_registry(registry: ToolRegistry, wrap: Any) -> ToolRegistry:
    """Same allow-list, same order, every data tool enveloped (replay/record).

    ``journal_write`` is never enveloped: it writes the run's own journal, it
    does not answer from a data source — replaying over it would silently drop
    the claims and the provenance trail of the replayed run.
    """
    wrapped = ToolRegistry()
    for name in registry.names():
        tool = registry.get(name)
        wrapped.register(name, tool if name in _UNWRAPPED_IN_REPLAY else wrap(tool))
    return wrapped


def build_v1_registry(*, fixtures: Mapping[str, Any],
                      journal: AgentJournal,
                      observed: Optional[contracts.ObservedRefs] = None
                      ) -> ToolRegistry:
    """Legacy entry point — ``build_registry(mode="fixture", ...)``.

    Registers exactly the seven v1 tools (``TOOL_NAMES``) — ``execute_intent``
    is not registerable. ``fixtures`` follows the frozen schema documented in
    this module's docstring; ``journal`` is the journal ``journal_write``
    appends to (one journal per agent process, B1 §3.4).

    ``observed`` is the run-scoped ledger of observed references (P0-6):
    ``journal_write`` refuses a claim citing a reference outside it. When it
    is omitted, the ledger is derived from the fixtures themselves (the
    archived rows ARE the observed sources of a fixture run) — validation is
    never silently switched off.
    """
    return build_registry(mode="fixture", journal=journal, observed=observed,
                          fixtures=fixtures)
