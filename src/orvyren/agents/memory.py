# -*- coding: utf-8 -*-
"""``memory`` — minimal FTS memory with mandatory refs (M9, 10 h slice).

A tiny searchable memory for the agent loop: one entry = one text + its
``refs`` to evidence (relation ids, ref ids, snapshot hashes). The rule of the
journal applies verbatim here: **an entry without refs cannot be used** —
:func:`FTSMemory.remember` refuses it (``E_MEMORY_NO_REFS``) and
:func:`FTSMemory.recall` never returns anything else.

Search is SQLite FTS5 (``unicode61``) over the entry text. The user/query
string is tokenised and re-quoted into the MATCH expression, so an FTS
operator or a quote can never change the query syntax. Ordering is
deterministic (``rank, memory_id``).

Standard library only (``sqlite3``).
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

__all__ = [
    "MemoryEntry",
    "FTSMemory",
    "E_MEMORY_NO_REFS",
    "refs_from_observations",
    "OBSERVATION_REF_KEYS",
]

#: An entry without refs is refused: it cannot be used (B1 §3.4 rule).
E_MEMORY_NO_REFS = "E_MEMORY_NO_REFS"

#: Observation keys whose values are evidence references worth remembering.
OBSERVATION_REF_KEYS: Tuple[str, ...] = (
    "relation_id", "ref_id", "graph_hash", "snapshot_ref",
)

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True)
class MemoryEntry:
    """One remembered entry — always with its refs."""

    memory_id: str
    text: str
    refs: Tuple[str, ...] = ()
    kind: str = "OBSERVATION"
    ts_utc: str = ""
    rank: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"memory_id": self.memory_id, "text": self.text,
                "refs": list(self.refs), "kind": self.kind,
                "ts_utc": self.ts_utc, "rank": self.rank}


def refs_from_observations(observations: Iterable[Mapping[str, Any]]
                           ) -> Tuple[str, ...]:
    """Evidence refs found in tool observations (stable order, no duplicate)."""
    refs: List[str] = []
    for observation in observations or ():
        if not isinstance(observation, Mapping):
            continue
        for key in OBSERVATION_REF_KEYS:
            value = observation.get(key)
            if isinstance(value, str) and value.strip():
                if value not in refs:
                    refs.append(value)
    return tuple(refs)


class FTSMemory:
    """In-memory (or file) FTS5 memory: ``remember`` / ``recall`` / ``refs_of``.

    ``remember`` requires refs; ``recall`` returns only entries that carry
    them (which is all of them by construction). The FTS query is rebuilt from
    bare tokens — the stored text can never be interpreted as query syntax.
    """

    def __init__(self, path: str = ":memory:") -> None:
        self.con = sqlite3.connect(path)
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS memory ("
            "memory_id TEXT PRIMARY KEY, kind TEXT, body TEXT, refs TEXT, "
            "ts_utc TEXT)")
        self.con.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5("
            "body, memory_id UNINDEXED, tokenize='unicode61')")
        self.con.commit()

    # -- writes ------------------------------------------------------------
    def remember(self, memory_id: str, text: str, refs: Sequence[str],
                 *, kind: str = "OBSERVATION", ts_utc: str = "") -> MemoryEntry:
        """Store one entry; without refs it is refused (never usable)."""
        clean_refs = tuple(str(ref).strip() for ref in refs or ()
                           if str(ref).strip())
        if not clean_refs:
            raise ValueError("%s: %s" % (E_MEMORY_NO_REFS, memory_id))
        entry = MemoryEntry(
            memory_id=str(memory_id), text=str(text), refs=clean_refs,
            kind=str(kind or "OBSERVATION"),
            ts_utc=str(ts_utc) or datetime.now(timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"))
        self.con.execute(
            "INSERT OR REPLACE INTO memory VALUES (?,?,?,?,?)",
            (entry.memory_id, entry.kind, entry.text,
             json.dumps(list(entry.refs)), entry.ts_utc))
        self.con.execute(
            "INSERT OR REPLACE INTO memory_fts(body, memory_id) VALUES (?,?)",
            (entry.text, entry.memory_id))
        self.con.commit()
        return entry

    # -- reads -------------------------------------------------------------
    @staticmethod
    def _match_expression(query: str) -> str:
        """Tokens of ``query`` re-quoted — FTS syntax cannot be injected."""
        tokens = _TOKEN_RE.findall(str(query or ""))
        return " OR ".join('"%s"' % token.replace('"', '""')
                           for token in tokens)

    def recall(self, query: str, k: int = 5) -> Tuple[MemoryEntry, ...]:
        """FTS search — deterministic order (rank, memory_id)."""
        match = self._match_expression(query)
        if not match:
            return ()
        rows = self.con.execute(
            "SELECT m.memory_id, m.kind, m.body, m.refs, m.ts_utc, f.rank "
            "FROM memory_fts f JOIN memory m ON m.memory_id = f.memory_id "
            "WHERE memory_fts MATCH ? ORDER BY f.rank, m.memory_id LIMIT ?",
            (match, int(k))).fetchall()
        return tuple(MemoryEntry(
            memory_id=row[0], kind=row[1], text=row[2],
            refs=tuple(json.loads(row[3])), ts_utc=row[4], rank=float(row[5]))
            for row in rows)

    def refs_of(self, memory_id: str) -> Tuple[str, ...]:
        """The refs of one entry (empty tuple when unknown)."""
        row = self.con.execute(
            "SELECT refs FROM memory WHERE memory_id = ?", (memory_id,)
        ).fetchone()
        return tuple(json.loads(row[0])) if row else ()

    def entries(self) -> Tuple[MemoryEntry, ...]:
        """Every stored entry, stable order (memory_id)."""
        rows = self.con.execute(
            "SELECT memory_id, kind, body, refs, ts_utc FROM memory "
            "ORDER BY memory_id").fetchall()
        return tuple(MemoryEntry(
            memory_id=row[0], kind=row[1], text=row[2],
            refs=tuple(json.loads(row[3])), ts_utc=row[4]) for row in rows)

    def count(self) -> int:
        return int(self.con.execute("SELECT COUNT(*) FROM memory").fetchone()[0])
