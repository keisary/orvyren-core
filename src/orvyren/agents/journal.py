"""``agent_journal`` — append-only private reasoning journal (B1 §3.4).

One line = one reasoning event. The journal is **separate from the evidence
graph**, append-only and **chained by hash** (``prev_hash``): a modified line
breaks the chain. Its payload (full prompt + raw response) lives in an
immutable content store keyed by ``prompt_hash`` / ``response_hash``.

Promotion rules (DOC4 L2.3, B3 R1):
- journal -> graph promotion happens **only through deterministic
  validators** — :func:`promote` never writes anything, it emits candidates
  for a W1 validator to consume;
- an entry without ``refs`` cannot be *used* (B1 §3.4: absence of reference
  does not invalidate a reflection but blocks its use);
- an LLM-proposed branch carries **zero weight** (:func:`branch_weight`)
  until validated — no decision figure ever comes from an LLM
  (:func:`deterministic_validator` ``no_number_ok``).

Standard library only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, fields, replace
from typing import Any, Dict, Mapping, Tuple

__all__ = [
    "JournalEntry",
    "ValidationResult",
    "Promotion",
    "AgentJournal",
    "JOURNAL_KINDS",
    "JOURNAL_STATUSES",
    "PROPOSAL_KINDS",
    "GENESIS_HASH",
    "deterministic_validator",
    "entry_hash",
    "branch_weight",
]

# --------------------------------------------------------------------------
# Enums (B1 §3.4).
# --------------------------------------------------------------------------
#: Event kinds of the reasoning loop.
JOURNAL_KINDS: Tuple[str, ...] = (
    "PLAN", "TOOL_CALL", "TOOL_RESULT", "OBSERVATION_REF", "REFLECTION",
    "HYPOTHESIS_PROPOSED", "BRANCH_UPDATE", "CRITIQUE", "DECISION_DRAFT",
    "STOP", "ERROR",
)

#: Line statuses: ``QUARANTINED`` = unknown fields (kept visible, never used).
JOURNAL_STATUSES: Tuple[str, ...] = (
    "PROPOSED", "ACCEPTED", "REJECTED", "QUARANTINED",
)

#: Kinds that *propose* something usable (branch/hypothesis/decision): their
#: text must carry no figure (B3 R1 — decision figures come from refs).
PROPOSAL_KINDS = frozenset({"HYPOTHESIS_PROPOSED", "BRANCH_UPDATE", "DECISION_DRAFT"})

#: First line of a chain.
GENESIS_HASH = "0" * 64


# --------------------------------------------------------------------------
# Line schema (B1 §3.4 table).
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class JournalEntry:
    """One ``agent_journal`` line (the 21 columns of B1 §3.4)."""

    journal_id: str
    run_id: str
    episode_id: str
    agent_id: str
    role_version: str
    step_index: int
    ts_utc: str
    kind: str
    content: str
    refs: Tuple[str, ...] = ()
    status: str = "PROPOSED"
    validation: Mapping[str, Any] = field(default_factory=dict)
    llm: Mapping[str, Any] = field(default_factory=dict)
    prompt_hash: str = ""
    response_hash: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cached_in: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    prev_hash: str = GENESIS_HASH


@dataclass(frozen=True)
class ValidationResult:
    """The deterministic validator verdict (B1 §3.4 ``validation`` column)."""

    schema_ok: bool
    no_number_ok: bool
    provenance_ok: bool
    motif: str = ""

    @property
    def ok(self) -> bool:
        return self.schema_ok and self.no_number_ok and self.provenance_ok

    def to_dict(self) -> Dict[str, Any]:
        return {"schema_ok": self.schema_ok, "no_number_ok": self.no_number_ok,
                "provenance_ok": self.provenance_ok, "motif": self.motif}


@dataclass(frozen=True)
class Promotion:
    """A graph-write candidate emitted by :func:`AgentJournal.promote`.

    Carries no write: a W1 validator consumes it. ``weight`` is the branch
    weight — always 0.0 for LLM-origin entries (B3 rule R1).
    """

    journal_id: str
    ref: str
    weight: float
    agent_id: str


# --------------------------------------------------------------------------
# Hashing and validation.
# --------------------------------------------------------------------------
def entry_hash(entry: JournalEntry) -> str:
    """SHA-256 of the canonical serialisation (prev_hash excluded)."""
    payload = {f.name: getattr(entry, f.name) for f in fields(entry)
               if f.name != "prev_hash"}
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def deterministic_validator(entry: JournalEntry) -> ValidationResult:
    """The deterministic gate of B1 §3.4 / B3 R1 — no LLM involved.

    - ``schema_ok``: required columns present, enums closed, and an LLM line
      pins its prompt/response hashes (reproducibility);
    - ``no_number_ok``: a proposal line (``PROPOSAL_KINDS``) carries no figure
      in its text — decision figures arrive through ``refs`` to observations;
    - ``provenance_ok``: role version present, and an LLM line documents its
      provider / model / pinned version / temperature.
    """
    if (not entry.journal_id.strip() or not entry.agent_id.strip()
            or not entry.ts_utc.strip() or entry.kind not in JOURNAL_KINDS
            or entry.status not in JOURNAL_STATUSES or entry.step_index < 0):
        return ValidationResult(False, True, False, "schema: missing or closed field")
    if entry.llm and not (entry.prompt_hash and entry.response_hash):
        return ValidationResult(False, True, False,
                                "schema: LLM line without prompt/response hash")
    no_number_ok = True
    if entry.kind in PROPOSAL_KINDS and any(ch.isdigit() for ch in entry.content):
        no_number_ok = False
    provenance_ok = bool(entry.role_version.strip())
    if entry.llm:
        provenance_ok = provenance_ok and all(
            str(entry.llm.get(key, "")).strip()
            for key in ("provider", "model", "model_version_pinned", "temperature"))
    if not no_number_ok:
        return ValidationResult(False, False, provenance_ok,
                                "no_number: a proposal carries a figure")
    if not provenance_ok:
        return ValidationResult(True, True, False, "provenance: incomplete")
    return ValidationResult(True, True, True)


def branch_weight(entry: JournalEntry) -> float:
    """Branch weight of a journal line: **0.0 for LLM-origin** (B3 R1)."""
    return 0.0 if entry.llm else 1.0


# --------------------------------------------------------------------------
# The journal.
# --------------------------------------------------------------------------
class AgentJournal:
    """Append-only, hash-chained journal (B1 §3.4 storage policy).

    There is no update and no delete API: a corrected view is a new line.
    :meth:`verify_chain` recomputes the chain — any rewritten line breaks it.
    """

    def __init__(self) -> None:
        self._entries: list = []

    # -- reads -------------------------------------------------------------
    def entries(self) -> Tuple[JournalEntry, ...]:
        """Immutable view of the lines (nothing can be edited in place)."""
        return tuple(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def verify_chain(self) -> Tuple[bool, str]:
        """Recompute ``prev_hash`` chaining (a modified line breaks it)."""
        previous = GENESIS_HASH
        for index, entry in enumerate(self._entries):
            if entry.prev_hash != previous:
                return False, "chain broken at line %d (%s)" % (index, entry.journal_id)
            previous = entry_hash(entry)
        return True, ""

    # -- append ------------------------------------------------------------
    def append_dict(self, data: Mapping[str, Any]) -> JournalEntry:
        """Append one line from a mapping.

        Unknown keys quarantine the line (status ``QUARANTINED``, keys listed
        in the motif) — the line stays visible but can never be used.
        """
        known = {f.name for f in fields(JournalEntry)}
        extra = sorted(set(data) - known)
        payload = {key: value for key, value in data.items() if key in known}
        entry = JournalEntry(**payload)
        verdict = deterministic_validator(entry)
        if extra:
            entry = replace(entry, status="QUARANTINED",
                            validation=dict(
                                verdict.to_dict(),
                                motif="quarantine: unknown fields %s" % ", ".join(extra)))
        else:
            entry = replace(entry,
                            status="PROPOSED" if verdict.ok else "REJECTED",
                            validation=verdict.to_dict())
        previous = entry_hash(self._entries[-1]) if self._entries else GENESIS_HASH
        entry = replace(entry, prev_hash=previous)
        self._entries.append(entry)
        return entry

    # -- promotion (journal -> graph candidates) ---------------------------
    def promote(self, entry: JournalEntry,
                validator=deterministic_validator) -> Tuple[Promotion, ...]:
        """Emit graph-write candidates — **never writes** (DOC4 L2.3).

        Promotion requires an explicit deterministic ``validator`` that
        accepts the line, an ``ACCEPTED``/``PROPOSED`` status and non-empty
        ``refs`` (a line without refs cannot be used). LLM branches get
        weight 0.0 (:func:`branch_weight`).
        """
        if entry not in self._entries:
            raise ValueError("E_JOURNAL_NOT_IN_STORE: %s" % entry.journal_id)
        if entry.status not in ("PROPOSED", "ACCEPTED"):
            raise ValueError("E_JOURNAL_PROMOTION_STATUS: %s" % entry.status)
        if not entry.refs:
            raise ValueError("E_JOURNAL_PROMOTION_NO_REFS")
        verdict = validator(entry)
        if not verdict.ok:
            raise ValueError("E_JOURNAL_PROMOTION_REFUSED: %s" % verdict.motif)
        weight = branch_weight(entry)
        return tuple(Promotion(journal_id=entry.journal_id, ref=ref,
                               weight=weight, agent_id=entry.agent_id)
                     for ref in entry.refs)
