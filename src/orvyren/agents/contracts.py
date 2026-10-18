"""Frozen exchange contracts of the agent layer (W2, lots L2.2–L2.7).

Every inter-agent interaction in MA-B travels as one of these records through
**serializable objects** (JSON files in the run directory) — never through
shared memory (B1 §4, DOC2 §5.2.1 rule 2). This module is the frozen hub for:

- ``loop.py``   — the bounded loop (states, budgets, stop conditions);
- ``llm.py``    — backends (recorded / live) returning :class:`LLMResult`;
- ``tools.py``  — the v1 tool registry returning :class:`ToolResult`;
- ``worker.py`` — the two separate processes exchanging plans / packets /
  critique reports through files.

Schemas (JSON, closed enums; validators live in ``prompts.py``):
- ``orvyren/orch/v1``  — orchestrator output: at most ONE research task;
- ``orvyren/crit/v1``  — adversarial critique report;
- ``orvyren/canon/v1`` — document canonicaliser output.

Field names follow the frozen studies verbatim (B1 §4.5/§5.2–5.4) so journal
lines, job files and tests share one vocabulary. Standard library only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple

__all__ = [
    "ROLES",
    "LOOP_STATES",
    "STOP_CONDITIONS",
    "DEFAULT_BUDGET_LIMITS",
    "Budget",
    "BudgetUsage",
    "LLMResult",
    "LLMBackend",
    "ToolResult",
    "Tool",
    "ToolCall",
    "ToolTurn",
    "TOOLCALL_SCHEMA_ID",
    "TOOLCALL_SOURCES",
    "validate_toolcall_output",
    "ResearchTask",
    "ResearchPlan",
    "EvidencePacket",
    "CritiqueFinding",
    "CritiqueReport",
    "LoopOutcome",
    "canonical_json",
    "content_hash",
    "ObservedRefs",
    "contains_digit",
    "wrap_untrusted",
    "scan_untrusted_flags",
    "CANON_EXTRACTIONS",
    "UNTRUSTED_OPEN",
    "UNTRUSTED_CLOSE",
    "validate_orchestrator_output",
    "validate_critique_output",
    "ORCH_SCHEMA_ID",
    "CRIT_SCHEMA_ID",
    "validate_canon_output",
]

# ---------------------------------------------------------------------------
# Enums and frozen defaults (DOC2 §5.2.4, FREEZE_V2 A5).
# ---------------------------------------------------------------------------
#: Agent roles of the MA-B minimal topology (DOC2 §5.2.1).
ROLES: Tuple[str, ...] = ("orchestrator", "explorer", "critic", "canonicalizer")

#: Fixed bounded graph — not a free ReAct loop (DOC2 §5.2.4).
LOOP_STATES: Tuple[str, ...] = (
    "IDLE", "PLANNING", "EXECUTING", "RECOVERING", "DONE", "ABORTED",
)

#: The five stop conditions, verbatim (B1 §4.2).
STOP_CONDITIONS: Tuple[str, ...] = (
    "ARRET-1",  # no task left with positive value in the plan
    "ARRET-2",  # a budget counter is exhausted
    "ARRET-3",  # validation impossible -> fail-closed
    "ARRET-4",  # posterior mass sufficient (upper guard-rail only)
    "ARRET-5",  # no research is worth its cost (NetVoI <= 0)
)

#: Frozen per-decision ceilings (DOC2 §5.2.4 table): LLM calls, tool calls,
#: wall seconds, USD. Versioned parameters, never hidden constants — a run
#: may tighten them, never widen them.
DEFAULT_BUDGET_LIMITS: Mapping[str, float] = {
    "llm_calls": 30,
    "tool_calls": 12,
    "wall_seconds": 600,
    "cost_usd": 0.10,
}


def canonical_json(obj: Any) -> str:
    """Canonical JSON text (sorted keys, no spaces) — the project convention."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def content_hash(obj: Any) -> str:
    """SHA-256 of the canonical serialisation (content-addressed store keys)."""
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Observed references (P0-6): a claim may only cite what was really observed.
# ---------------------------------------------------------------------------
class ObservedRefs:
    """Run-scoped ledger of the references actually observed by the tools.

    A claim is only usable when every reference it cites belongs to this set —
    the references really returned by tool observations (``source_ref`` /
    ``ref`` / ``url`` rows), plus the snapshot ref and the explicitly
    authorised sources of the run. An unknown reference is **refused** (the
    claim is rejected and stays visible in the journal); it is never silently
    replaced by a look-alike source.

    A perfectly hash-chained journal does not make a claim true: this ledger is
    the missing comparison between what a claim cites and what the run
    actually saw.
    """

    def __init__(self, authorized: Any = ()) -> None:
        self._refs: set = set()
        self.add_many(authorized)

    def add(self, ref: Any) -> None:
        """Register one observed reference (blank strings are ignored)."""
        text = str(ref or "").strip()
        if text:
            self._refs.add(text)

    def add_many(self, refs: Any) -> None:
        """Register a batch of observed references."""
        for ref in refs or ():
            self.add(ref)

    def __contains__(self, ref: Any) -> bool:
        return str(ref or "").strip() in self._refs

    def __len__(self) -> int:
        return len(self._refs)

    def all(self) -> Tuple[str, ...]:
        """Every observed reference, sorted (immutable view)."""
        return tuple(sorted(self._refs))

    def unknown(self, refs: Any) -> Tuple[str, ...]:
        """The cited references never observed (order preserved, de-duplicated).

        The single comparison point of the provenance contract: the caller
        rejects (or quarantines) a claim as soon as this tuple is non-empty.
        """
        missing: List[str] = []
        for ref in refs or ():
            text = str(ref or "").strip()
            if text and text not in self._refs and text not in missing:
                missing.append(text)
        return tuple(missing)


# ---------------------------------------------------------------------------
# Budget (L2.2): four counters, checked before every call (B1 §4.3).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Budget:
    """Per-decision ceilings. ``of_defaults()`` returns the frozen limits."""

    llm_calls: float = DEFAULT_BUDGET_LIMITS["llm_calls"]
    tool_calls: float = DEFAULT_BUDGET_LIMITS["tool_calls"]
    wall_seconds: float = DEFAULT_BUDGET_LIMITS["wall_seconds"]
    cost_usd: float = DEFAULT_BUDGET_LIMITS["cost_usd"]

    def to_dict(self) -> Dict[str, float]:
        return dict(asdict(self))

    @classmethod
    def of_defaults(cls) -> "Budget":
        return cls()


@dataclass
class BudgetUsage:
    """Mutable usage of the four counters (one instance per run)."""

    llm_calls: float = 0.0
    tool_calls: float = 0.0
    wall_seconds: float = 0.0
    cost_usd: float = 0.0

    def spend_llm(self, cost_usd: float = 0.0) -> None:
        self.llm_calls += 1
        self.cost_usd += max(0.0, float(cost_usd))

    def spend_tool(self) -> None:
        self.tool_calls += 1

    def spend_wall(self, seconds: float) -> None:
        self.wall_seconds += max(0.0, float(seconds))

    def exhausted(self, budget: Budget) -> List[str]:
        """Counters already at/over their ceiling (names, stable order)."""
        out: List[str] = []
        if self.llm_calls >= budget.llm_calls:
            out.append("llm_calls")
        if self.tool_calls >= budget.tool_calls:
            out.append("tool_calls")
        if self.wall_seconds >= budget.wall_seconds:
            out.append("wall_seconds")
        if self.cost_usd >= budget.cost_usd:
            out.append("cost_usd")
        return out

    def remaining(self, budget: Budget) -> Dict[str, float]:
        return {
            "llm_calls": max(0.0, budget.llm_calls - self.llm_calls),
            "tool_calls": max(0.0, budget.tool_calls - self.tool_calls),
            "wall_seconds": max(0.0, budget.wall_seconds - self.wall_seconds),
            "cost_usd": max(0.0, budget.cost_usd - self.cost_usd),
        }

    def to_dict(self) -> Dict[str, float]:
        return dict(asdict(self))


# ---------------------------------------------------------------------------
# LLM plumbing (L2.5/L2.6): one result record, one backend protocol.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LLMResult:
    """One LLM call, fully accounted (B1 §3.4 columns; replay reuses it).

    ``prompt_hash`` / ``response_hash`` key the immutable content store; in
    replay mode ``ts_utc`` and ``latency_ms`` are the **recorded** values so a
    journaled run hashes identically across replays (B1 §6.2).
    """

    ok: bool
    raw: str = ""
    data: Optional[Dict[str, Any]] = None
    error: str = ""
    provider: str = ""
    model: str = ""
    model_version_pinned: str = ""
    temperature: float = 0.0
    tokens_in: int = 0
    cached_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    prompt_hash: str = ""
    response_hash: str = ""
    ts_utc: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return dict(asdict(self))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LLMResult":
        return cls(**{k: data[k] for k in data if k in cls.__dataclass_fields__})


class LLMBackend:
    """Protocol of an LLM backend (recorded store, live API, test fake).

    Implementations MUST be side-effect free apart from their own accounting:
    prompts in, :class:`LLMResult` out. No backend may execute, sign or touch
    the policy layer.
    """

    def complete(self, *, role: str, role_version: str, schema_id: str,
                 system_prompt: str, payload: Mapping[str, Any],
                 tools: Optional[Tuple[Mapping[str, Any], ...]] = None
                 ) -> LLMResult:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Tool registry (L2.2 support): contract of one tool call.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ToolResult:
    """Outcome of one tool call. ``status`` ∈ OK | FAILED | UNAVAILABLE."""

    ok: bool
    status: str = "OK"
    observations: Tuple[Dict[str, Any], ...] = ()
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"ok": self.ok, "status": self.status,
                "observations": list(self.observations), "error": self.error}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ToolResult":
        return cls(ok=bool(data.get("ok")), status=str(data.get("status", "OK")),
                   observations=tuple(data.get("observations", ())),
                   error=str(data.get("error", "")))


class Tool:
    """Protocol of a registry tool: name + deterministic run."""

    name: str = ""

    def run(self, args: Mapping[str, Any], *, deadline_s: float = 20.0) -> ToolResult:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Tool calling (M8): one proposed call, one tooled turn (native or JSON).
# ---------------------------------------------------------------------------
#: Strict-JSON fallback envelope (the model answers with this when the
#: provider does not emit native ``tool_calls``).
TOOLCALL_SCHEMA_ID = "orvyren/toolcall/v1"

#: Provenance of a proposed call: how the model expressed it.
TOOLCALL_SOURCES: Tuple[str, ...] = ("native", "json_strict")


@dataclass(frozen=True)
class ToolCall:
    """One tool call proposed by the model.

    ``source`` ∈ :data:`TOOLCALL_SOURCES`: ``native`` when the provider
    returned OpenAI-style ``tool_calls``; ``json_strict`` when the call was
    recovered from the strict JSON envelope (the fallback path — always
    journaled, never silent).
    """

    call_id: str
    name: str
    args: Dict[str, Any] = field(default_factory=dict)
    source: str = "native"

    def to_dict(self) -> Dict[str, Any]:
        return {"call_id": self.call_id, "name": self.name,
                "args": dict(self.args), "source": self.source}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ToolCall":
        return cls(call_id=str(data.get("call_id", "")),
                   name=str(data.get("name", "")),
                   args=dict(data.get("args") or {}),
                   source=str(data.get("source", "native")))


@dataclass(frozen=True)
class ToolTurn:
    """One tooled turn: calls proposed, tools executed, final strict JSON.

    ``mode`` ∈ :data:`TOOLCALL_SOURCES` is how the calls arrived;
    ``fallback_motif`` is **non-empty whenever the native path was abandoned**
    (that fallback is journaled — it is never a silent downgrade). ``llm``
    carries every :class:`LLMResult` of the turn as dicts, so a recorded turn
    and its replay can be compared field by field.
    """

    mode: str = "native"
    fallback_motif: str = ""
    calls: Tuple[ToolCall, ...] = ()
    results: Tuple[Dict[str, Any], ...] = ()
    final: Optional[Dict[str, Any]] = None
    llm: Tuple[Dict[str, Any], ...] = ()
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {"mode": self.mode, "fallback_motif": self.fallback_motif,
                "calls": [c.to_dict() for c in self.calls],
                "results": [dict(r) for r in self.results],
                "final": self.final,
                "llm": [dict(line) for line in self.llm],
                "errors": list(self.errors)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ToolTurn":
        return cls(
            mode=str(data.get("mode", "")),
            fallback_motif=str(data.get("fallback_motif", "")),
            calls=tuple(ToolCall.from_dict(c) for c in data.get("calls", ())
                        if isinstance(c, Mapping)),
            results=tuple(dict(r) for r in data.get("results", ())
                          if isinstance(r, Mapping)),
            final=(dict(data["final"]) if isinstance(data.get("final"), Mapping)
                   else None),
            llm=tuple(dict(line) for line in data.get("llm", ())
                      if isinstance(line, Mapping)),
            errors=tuple(str(e) for e in data.get("errors", ())))


# ---------------------------------------------------------------------------
# Exchange objects (serializable; JSON field names follow B1 §5 verbatim).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResearchTask:
    """One research task of the plan (B1 §4.5): falsifiable, one tool."""

    question: str
    outil: str
    args: Dict[str, Any] = field(default_factory=dict)
    critere_discriminant: str = ""
    branches_concernees: Tuple[str, ...] = ()
    cout_max: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"question": self.question, "outil": self.outil, "args": dict(self.args),
                "critere_discriminant": self.critere_discriminant,
                "branches_concernees": list(self.branches_concernees),
                "cout_max": dict(self.cout_max)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ResearchTask":
        return cls(question=str(data.get("question", "")),
                   outil=str(data.get("outil", "")),
                   args=dict(data.get("args") or {}),
                   critere_discriminant=str(data.get("critere_discriminant", "")),
                   branches_concernees=tuple(data.get("branches_concernees") or ()),
                   cout_max=dict(data.get("cout_max") or {}))


@dataclass(frozen=True)
class ResearchPlan:
    """Orchestrator output ``orvyren/orch/v1`` — one task or a clean stop."""

    schema_id: str = "orvyren/orch/v1"
    lacune_id: str = ""
    task: Optional[ResearchTask] = None
    stop: bool = True
    motif_stop: str = ""
    non_recherche: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {"$schema": self.schema_id, "lacune_id": self.lacune_id,
                "tache": self.task.to_dict() if self.task else None,
                "stop": self.stop, "motif_stop": self.motif_stop or None,
                "non_recherche": list(self.non_recherche)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ResearchPlan":
        task = data.get("tache")
        return cls(schema_id=str(data.get("$schema", "orvyren/orch/v1")),
                   lacune_id=str(data.get("lacune_id", "")),
                   task=ResearchTask.from_dict(task) if isinstance(task, Mapping) else None,
                   stop=bool(data.get("stop", True)),
                   motif_stop=str(data.get("motif_stop") or ""),
                   non_recherche=tuple(data.get("non_recherche") or ()))

    @classmethod
    def stopped(cls, motif: str, non_recherche: Tuple[str, ...] = ()) -> "ResearchPlan":
        return cls(stop=True, motif_stop=motif, non_recherche=tuple(non_recherche))


@dataclass(frozen=True)
class EvidencePacket:
    """The serializable evidence bundle the critic receives (B1 §4, DOC2 §5.2.1)."""

    packet_id: str
    snapshot_ref: str = ""
    refs: Tuple[str, ...] = ()
    claims: Tuple[Dict[str, Any], ...] = ()
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"packet_id": self.packet_id, "snapshot_ref": self.snapshot_ref,
                "refs": list(self.refs), "claims": [dict(c) for c in self.claims],
                "summary": self.summary}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvidencePacket":
        return cls(packet_id=str(data.get("packet_id", "")),
                   snapshot_ref=str(data.get("snapshot_ref", "")),
                   refs=tuple(data.get("refs") or ()),
                   claims=tuple(data.get("claims") or ()),
                   summary=str(data.get("summary", "")))


#: Closed enums of the critique schema (B1 §5.3).
CRITIQUE_VERDICTS: Tuple[str, ...] = ("TENABLE", "FRAGILE", "INCOHERENTE")
CRITIQUE_FINDING_TYPES: Tuple[str, ...] = (
    "CONTRADICTION", "UNITE", "OBSOLESCENCE", "PIT", "DEPENDANCE", "ALTERNATIVE", "MANQUE",
)
CRITIQUE_GRAVITES: Tuple[str, ...] = ("BLOQUANT", "MAJEUR", "MINEUR")


@dataclass(frozen=True)
class CritiqueFinding:
    """One objection — an objection without ``refs`` is invalid (B1 §5.3)."""

    type: str
    gravite: str
    enonce: str
    refs: Tuple[str, ...] = ()
    test_discriminant: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "gravite": self.gravite, "enonce": self.enonce,
                "refs": list(self.refs), "test_discriminant": self.test_discriminant}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CritiqueFinding":
        return cls(type=str(data.get("type", "")), gravite=str(data.get("gravite", "")),
                   enonce=str(data.get("enonce", "")),
                   refs=tuple(data.get("refs") or ()),
                   test_discriminant=str(data.get("test_discriminant", "")))


@dataclass(frozen=True)
class CritiqueReport:
    """Critique output ``orvyren/crit/v1`` (B1 §5.3)."""

    schema_id: str = "orvyren/crit/v1"
    verdict_lecture: str = "TENABLE"
    findings: Tuple[CritiqueFinding, ...] = ()
    preuves_manquantes: Tuple[str, ...] = ()
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"$schema": self.schema_id, "verdict_lecture": self.verdict_lecture,
                "findings": [f.to_dict() for f in self.findings],
                "preuves_manquantes": list(self.preuves_manquantes), "note": self.note}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CritiqueReport":
        return cls(schema_id=str(data.get("$schema", "orvyren/crit/v1")),
                   verdict_lecture=str(data.get("verdict_lecture", "TENABLE")),
                   findings=tuple(CritiqueFinding.from_dict(f)
                                  for f in data.get("findings", ()) if isinstance(f, Mapping)),
                   preuves_manquantes=tuple(data.get("preuves_manquantes") or ()),
                   note=str(data.get("note", "")))


# ---------------------------------------------------------------------------
# Loop outcome (L2.2): what the bounded loop returns to its caller.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LoopOutcome:
    """Final result of one bounded run (DOC2 §5.2.4 forced-abstention rule).

    ``state`` ∈ DONE/ABORTED; ``stop_condition`` ∈ STOP_CONDITIONS or empty;
    ``non_recherche`` lists what was NOT searched for lack of budget — the
    decision dossier is obliged to carry it (§5.4). ``critique_verdict`` is
    the last critic verdict when a critique round ran. ``reflexion`` carries
    the deterministic ACH evidence matrix built by ``agents.reflexion`` from
    the run hypotheses and the accepted claims (optional — default empty, so
    no existing key or caller ever breaks).
    """

    state: str = "DONE"
    stop_condition: str = ""
    motif: str = ""
    non_recherche: Tuple[str, ...] = ()
    budget_used: Dict[str, float] = field(default_factory=dict)
    critique_verdict: str = ""
    inconclusive: bool = False
    reflexion: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dict(asdict(self))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LoopOutcome":
        return cls(**{k: data[k] for k in data if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Untrusted content (B1 §5.6, DOC2 §5.2.5 hygiene): delimit + flag, never obey.
# ---------------------------------------------------------------------------
#: Spotlighting delimiters (Microsoft pattern, B1 §5.1): external content is
#: ALWAYS wrapped; an agent never reads it bare, and text inside is data only.
UNTRUSTED_OPEN = "<UNTRUSTED-CONTENT>"
UNTRUSTED_CLOSE = "</UNTRUSTED-CONTENT>"

#: Extraction verdicts of the canonicaliser schema (B1 §5.4).
CANON_EXTRACTIONS: Tuple[str, ...] = ("OK", "ABSENT", "AMBIGU")

#: Instruction-like patterns (FR/EN) flagged by :func:`scan_untrusted_flags`.
#: Detection is a VISIBLE journal flag, never a filter that silently drops.
_INJECTION_PATTERNS: Tuple[Tuple[str, str], ...] = (
    ("override_instructions", r"(?i)(ignore\s+(all\s+)?(previous|prior)\s+instructions"
                                r"|ignore[sz]?\s+les\s+instructions|oublie\s+les\s+instructions)"),
    ("action_tool_mention", r"(?i)(execute_intent|execute_tx|transfer|virement|"
                            r"0x[0-9a-fA-F]{40})"),
    ("amount_proposal", r"(?i)(transf[eè]re|envoie|send|pay)\s+[0-9]"),
    ("hypothesis_injection", r"(?i)(nouvelle\s+hypoth[eè]se|new\s+hypothesis|"
                             r"HYP-[0-9]+)"),
    ("budget_change", r"(?i)(budget\s*[:=]\s*[0-9]|augmente\s+le\s+budget|increase\s+budget)"),
    ("fake_agent_json", r'(?i)("\$schema"\s*:\s*"orvyren/|"verdict_lecture"\s*:)'),
)


def contains_digit(text: str) -> bool:
    """True when the text carries any digit — the "no digits" rule."""
    return any(ch.isdigit() for ch in str(text))


def wrap_untrusted(text: str, source_url: str = "") -> str:
    """Wrap external content between explicit delimiters (spotlighting).

    The wrapper never interprets the payload: it only delimits it and stamps
    its origin, so the system prompts can state that the delimited content is
    UNTRUSTED DATA, never an instruction (B1 §5.6)."""
    source = " source=%r" % (source_url,) if source_url else ""
    body = str(text).replace(UNTRUSTED_OPEN, "[UNTRUSTED-CONTENT-OPEN]")
    body = body.replace(UNTRUSTED_CLOSE, "[UNTRUSTED-CONTENT-CLOSE]")
    return "%s%s\n%s\n%s" % (UNTRUSTED_OPEN, source, body, UNTRUSTED_CLOSE)


def scan_untrusted_flags(text: str) -> List[str]:
    """Instruction-like flags found in external content (journal them)."""
    import re
    found: List[str] = []
    for flag, pattern in _INJECTION_PATTERNS:
        if re.search(pattern, str(text)):
            found.append(flag)
    return found


# ---------------------------------------------------------------------------
# Schema validators (closed enums, unknown fields rejected — B1 §5.1/§5.5).
# ---------------------------------------------------------------------------
def _check_closed(data: Mapping[str, Any], allowed: Tuple[str, ...]) -> List[str]:
    errors: List[str] = []
    unknown = sorted(set(data) - set(allowed))
    if unknown:
        errors.append("unknown fields: %s" % ", ".join(unknown))
    return errors


def _check_closed_in(data: Mapping[str, Any], allowed: Tuple[str, ...],
                     prefix: str = "") -> List[str]:
    """Closed-field check whose errors name the offending field (G-18).

    ``_check_closed`` is kept for the other validators; the orchestrator
    re-prompt needs messages a model can act on, so every message here names
    the field (``tache.question``) and states the rule.
    """
    return ["%s%s: field not allowed by the schema (closed fields: %s)"
            % (prefix, name, ", ".join(allowed))
            for name in sorted(set(data) - set(allowed))]


ORCH_SCHEMA_ID = "orvyren/orch/v1"
CRIT_SCHEMA_ID = "orvyren/crit/v1"

#: Closed fields of an ``orvyren/orch/v1`` payload / of one task.
_ORCH_KEYS: Tuple[str, ...] = ("$schema", "lacune_id", "tache", "stop",
                               "motif_stop", "non_recherche")
_TASK_KEYS: Tuple[str, ...] = ("question", "outil", "args",
                               "critere_discriminant", "branches_concernees",
                               "cout_max")


def validate_orchestrator_output(data: Mapping[str, Any]) -> Tuple[bool, List[str]]:
    """Validate an ``orvyren/orch/v1`` payload (B1 §5.2 controls).

    Closed fields; a task needs a question ≤ 240 chars **without any digit**,
    a tool name, dict args and a discriminant criterion; a stop needs a
    motif. The tool allow-list membership is checked by the caller (the
    registry, not the schema).

    Every error is **actionable**: it names the offending field and states the
    rule, in English, so the single re-prompt carries a fix the model can
    apply (``tache.critere_discriminant: no digit allowed — …``). The texts
    feed the ``erreurs_validation`` payload of that re-prompt and the
    ``quarantine_reason`` of the journal line, never a frozen document.
    """
    errors: List[str] = _check_closed_in(data, _ORCH_KEYS)
    if data.get("$schema") != ORCH_SCHEMA_ID:
        errors.append('$schema: expected exactly "%s"' % ORCH_SCHEMA_ID)
    if not isinstance(data.get("stop"), bool):
        errors.append("stop: expected a boolean (true or false)")
    if not isinstance(data.get("non_recherche", []), (list, tuple)):
        errors.append("non_recherche: expected a list of questions (strings)")
    if data.get("stop") is True:
        if not str(data.get("motif_stop") or "").strip():
            errors.append("motif_stop: required when stop=true — state why no task is left")
    elif data.get("stop") is False:
        task = data.get("tache")
        if not isinstance(task, Mapping):
            errors.append("tache: required when stop=false — an object with %s"
                          % ", ".join(_TASK_KEYS))
        else:
            errors += _check_closed_in(task, _TASK_KEYS, prefix="tache.")
            question = str(task.get("question", ""))
            if not question.strip() or len(question) > 240:
                errors.append("tache.question: non-empty text of ≤ 240 characters")
            if contains_digit(question):
                errors.append("tache.question: ≤ 240 characters, no digit — "
                              "figures come from refs, ask the question qualitatively")
            if contains_digit(str(task.get("critere_discriminant", ""))):
                errors.append("tache.critere_discriminant: no digit allowed — "
                              "state the criterion qualitatively, figures come from refs")
            if not str(task.get("outil", "")).strip():
                errors.append("tache.outil: missing or not in the allow-list")
            if not isinstance(task.get("args"), Mapping):
                errors.append("tache.args: expected a JSON object of tool arguments")
            if not isinstance(task.get("branches_concernees", []), (list, tuple)):
                errors.append("tache.branches_concernees: expected a list of hypothesis ids")
    else:
        errors.append("stop: missing — expected a boolean (true or false)")
    return (not errors), errors


def validate_critique_output(data: Mapping[str, Any]) -> Tuple[bool, List[str]]:
    """Validate an ``orvyren/crit/v1`` payload (B1 §5.3).

    An objection **without refs is invalid** (no causal justification).

    Messages name the field and the rule (G-18): the critique re-prompt gets a
    fix it can apply, not a bare rejection.
    """
    errors: List[str] = _check_closed_in(data, ("$schema", "verdict_lecture", "findings",
                                                "preuves_manquantes", "note"))
    if data.get("$schema") != CRIT_SCHEMA_ID:
        errors.append('$schema: expected exactly "%s"' % CRIT_SCHEMA_ID)
    if data.get("verdict_lecture") not in CRITIQUE_VERDICTS:
        errors.append("verdict_lecture: must be one of %s" % (CRITIQUE_VERDICTS,))
    findings = data.get("findings")
    if not isinstance(findings, (list, tuple)):
        errors.append("findings: expected a list")
    else:
        for index, finding in enumerate(findings):
            if not isinstance(finding, Mapping):
                errors.append("findings[%d]: expected a JSON object" % index)
                continue
            errors += _check_closed_in(
                finding, ("type", "gravite", "enonce", "refs", "test_discriminant"),
                prefix="findings[%d]." % index)
            if finding.get("type") not in CRITIQUE_FINDING_TYPES:
                errors.append("findings[%d].type: must be one of %s"
                              % (index, CRITIQUE_FINDING_TYPES))
            if finding.get("gravite") not in CRITIQUE_GRAVITES:
                errors.append("findings[%d].gravite: must be one of %s"
                              % (index, CRITIQUE_GRAVITES))
            if not str(finding.get("enonce", "")).strip() or len(str(finding.get("enonce"))) > 240:
                errors.append("findings[%d].enonce: non-empty text of ≤ 240 characters" % index)
            refs = finding.get("refs")
            if not isinstance(refs, (list, tuple)) or not refs:
                errors.append("findings[%d].refs: objection without refs is invalid — "
                              "cite at least one reference" % index)
    if not isinstance(data.get("preuves_manquantes", []), (list, tuple)):
        errors.append("preuves_manquantes: expected a list")
    return (not errors), errors


def validate_canon_output(data: Mapping[str, Any]) -> Tuple[bool, List[str]]:
    """Validate an ``orvyren/canon/v1`` payload (B1 §5.4).

    The canonicaliser only copies fields; ``champs_inconnus`` is carried
    through (quarantined downstream, never used)."""
    errors = _check_closed(data, ("$schema", "champs", "champs_inconnus"))
    if data.get("$schema") != "orvyren/canon/v1":
        errors.append("bad $schema")
    champs = data.get("champs")
    if not isinstance(champs, (list, tuple)):
        errors.append("champs must be a list")
    else:
        for index, champ in enumerate(champs):
            if not isinstance(champ, Mapping):
                errors.append("champ %d is not an object" % index)
                continue
            errors += ["champ %d: %s" % (index, e) for e in _check_closed(
                champ, ("nom", "valeur_brute", "unite", "passage",
                        "source_url", "ts_publication", "extraction"))]
            if not str(champ.get("nom", "")).strip():
                errors.append("champ %d: nom missing" % index)
            if champ.get("extraction") not in CANON_EXTRACTIONS:
                errors.append("champ %d: extraction not in %s" % (index, CANON_EXTRACTIONS))
    if not isinstance(data.get("champs_inconnus", []), (list, tuple)):
        errors.append("champs_inconnus must be a list")
    return (not errors), errors


def validate_toolcall_output(data: Mapping[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a ``orvyren/toolcall/v1`` fallback envelope (M8).

    Closed fields everywhere (``additionalProperties=false`` semantics):
    the envelope carries ``$schema`` and ``calls``; each call carries exactly
    ``name`` (non-empty) and ``args`` (a mapping). The tool-name allow-list
    and the per-tool argument schemas are checked by the caller (the
    registry + spec), never by this schema alone.
    """
    errors = _check_closed(data, ("$schema", "calls"))
    if data.get("$schema") != TOOLCALL_SCHEMA_ID:
        errors.append("bad $schema")
    calls = data.get("calls")
    if not isinstance(calls, (list, tuple)):
        errors.append("calls must be a list")
        return (not errors), errors
    for index, call in enumerate(calls):
        if not isinstance(call, Mapping):
            errors.append("call %d is not an object" % index)
            continue
        errors += ["call %d: %s" % (index, e) for e in _check_closed(
            call, ("name", "args"))]
        if not str(call.get("name", "")).strip():
            errors.append("call %d: name missing" % index)
        if not isinstance(call.get("args"), Mapping):
            errors.append("call %d: args must be a mapping" % index)
    return (not errors), errors
