"""Append-only SQLite store for the evidence graph (ORVYREN-Core).

Design rules
------------
* **Append-only.** A revision never updates a row: it inserts a new row with a
  higher revision number for the same logical id. SQLite triggers refuse
  ``UPDATE`` and ``DELETE`` on every table, so the guarantee does not depend
  on the discipline of callers.
* **Content addresses.** Observations are keyed by their content fingerprint
  (``models.observation_fingerprint``); re-inserting the same observation
  creates a new revision, it does not overwrite.
* **Reads return the current revision** (the highest revision of each logical
  id), so callers get a consistent view without knowing the history.
* ``schema_version`` records the schema generation of the database file.

Standard library only (``sqlite3``).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from orvyren.graph import models
from orvyren.graph.catalog import EXTRACT_METHOD
from orvyren.graph.models import (Claim, DecisionNode, Hypothesis, Observation,
                                  Relation, Source)
from orvyren.graph.provenance import snapshot_hash
from orvyren.quality.normalize import parse_timestamp

__all__ = ["GraphStore", "SCHEMA_VERSION", "GRAPH_VERSION"]

#: v2 (lot L1.3): relations gain the retroactive columns ``source_family_id``
#: and ``extract_method`` (B2 §3.0 fields 13–14). Older files are migrated
#: additively on open.
SCHEMA_VERSION = 2
GRAPH_VERSION = "orvyren-graph-v1"

#: (table, logical-id column) in the order used for snapshots.
_TABLES = (
    ("sources", "source_id"),
    ("observations", "observation_id"),
    ("claims", "claim_id"),
    ("relations", "relation_id"),
    ("hypotheses", "hypothesis_id"),
    ("decision_nodes", "node_id"),
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    row_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id    TEXT NOT NULL,
    revision     INTEGER NOT NULL,
    name         TEXT NOT NULL,
    endpoint     TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    limits       TEXT NOT NULL,
    inserted_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS observations (
    row_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_id TEXT NOT NULL,
    revision       INTEGER NOT NULL,
    venue          TEXT NOT NULL,
    metric         TEXT NOT NULL,
    ts_event       TEXT NOT NULL,
    value          REAL NOT NULL,
    extra          TEXT NOT NULL,
    retrieved_at   TEXT NOT NULL,
    source_id      TEXT NOT NULL,
    inserted_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claims (
    row_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id    TEXT NOT NULL,
    revision    INTEGER NOT NULL,
    text        TEXT NOT NULL,
    refs        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    inserted_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS relations (
    row_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    relation_id      TEXT NOT NULL,
    revision         INTEGER NOT NULL,
    src              TEXT NOT NULL,
    dst              TEXT NOT NULL,
    kind             TEXT NOT NULL,
    source_family_id TEXT NOT NULL DEFAULT '',
    extract_method   TEXT NOT NULL DEFAULT '',
    inserted_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hypotheses (
    row_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    hypothesis_id    TEXT NOT NULL,
    revision         INTEGER NOT NULL,
    statement        TEXT NOT NULL,
    state            TEXT NOT NULL,
    criteria_support TEXT NOT NULL,
    criteria_refute  TEXT NOT NULL,
    inserted_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decision_nodes (
    row_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id     TEXT NOT NULL,
    revision    INTEGER NOT NULL,
    kind        TEXT NOT NULL,
    payload     TEXT NOT NULL,
    refs        TEXT NOT NULL,
    inserted_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_observations_id  ON observations(observation_id);
CREATE INDEX IF NOT EXISTS idx_observations_src ON observations(source_id);
CREATE INDEX IF NOT EXISTS idx_observations_hour ON observations(ts_event);
CREATE INDEX IF NOT EXISTS idx_sources_id       ON sources(source_id);
CREATE INDEX IF NOT EXISTS idx_claims_id        ON claims(claim_id);
CREATE INDEX IF NOT EXISTS idx_relations_dst    ON relations(dst);
CREATE INDEX IF NOT EXISTS idx_hypotheses_id    ON hypotheses(hypothesis_id);
"""

_APPEND_ONLY_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table}
BEGIN SELECT RAISE(ABORT, 'append-only table: {table}'); END;
CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table}
BEGIN SELECT RAISE(ABORT, 'append-only table: {table}'); END;
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class GraphStore:
    """SQLite-backed, append-only evidence graph.

    ``path`` is a file path or ``":memory:"`` (tests). Use it as a context
    manager, or call :meth:`close` explicitly.
    """

    def __init__(self, path: str = ":memory:") -> None:
        self.path = path
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self._init_schema()

    # -- lifecycle -----------------------------------------------------------

    def __enter__(self) -> "GraphStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying connection."""
        self.connection.close()

    def _init_schema(self) -> None:
        with self.connection:
            self.connection.executescript(_SCHEMA)
            self._migrate_relation_columns()
            for table, _ in _TABLES:
                self.connection.executescript(
                    _APPEND_ONLY_TRIGGERS.format(table=table))
            row = self.connection.execute(
                "SELECT COUNT(*) FROM schema_version").fetchone()
            if row[0] == 0:
                self.connection.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (SCHEMA_VERSION, _now_iso()))

    def _migrate_relation_columns(self) -> None:
        """Additive migration for pre-L1.3 databases (columns added in v2)."""
        existing = {row["name"] for row in self.connection.execute(
            "PRAGMA table_info(relations)")}
        for column in ("source_family_id", "extract_method"):
            if column not in existing:
                self.connection.execute(
                    "ALTER TABLE relations ADD COLUMN %s TEXT NOT NULL DEFAULT ''"
                    % column)

    # -- internal helpers ----------------------------------------------------

    def _next_revision(self, table: str, id_column: str, logical_id: str) -> int:
        row = self.connection.execute(
            "SELECT COALESCE(MAX(revision), 0) + 1 FROM %s WHERE %s = ?"
            % (table, id_column), (logical_id,)).fetchone()
        return int(row[0])

    def _latest_row(self, table: str, id_column: str, logical_id: str):
        return self.connection.execute(
            "SELECT * FROM %s WHERE %s = ? ORDER BY revision DESC, row_id DESC "
            "LIMIT 1" % (table, id_column), (logical_id,)).fetchone()

    def _table_row_counts(self) -> Dict[str, int]:
        counts = {}
        for table, _ in _TABLES:
            counts[table] = int(self.connection.execute(
                "SELECT COUNT(*) FROM %s" % table).fetchone()[0])
        return counts

    def _current_rows(self) -> List[Dict[str, object]]:
        """Current revision of every logical row, in deterministic order."""
        rows: List[Dict[str, object]] = []
        for table, id_column in _TABLES:
            sql = ("SELECT * FROM %s WHERE row_id IN "
                   "(SELECT MAX(row_id) FROM %s GROUP BY %s) ORDER BY %s"
                   % (table, table, id_column, id_column))
            for row in self.connection.execute(sql):
                payload = dict(row)
                payload["_table"] = table
                rows.append(payload)
        return rows

    # -- writes (append-only) ------------------------------------------------

    def insert_source(self, source: Source) -> int:
        """Append a revision of ``source``; returns the new row id."""
        revision = self._next_revision("sources", "source_id", source.id)
        cursor = self.connection.execute(
            "INSERT INTO sources (source_id, revision, name, endpoint, "
            "retrieved_at, limits, inserted_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (source.id, revision, source.name, source.endpoint,
             source.retrieved_at, source.limits, _now_iso()))
        self.connection.commit()
        return int(cursor.lastrowid)

    def _insert_observation_row(self, observation: Observation,
                                source_id: Optional[str]) -> int:
        observation_id = models.observation_fingerprint(observation)
        revision = self._next_revision("observations", "observation_id", observation_id)
        cursor = self.connection.execute(
            "INSERT INTO observations (observation_id, revision, venue, metric, "
            "ts_event, value, extra, retrieved_at, source_id, inserted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (observation_id, revision, observation.venue, observation.metric,
             observation.ts_event_iso, observation.value, observation.extra,
             observation.retrieved_at, source_id or observation.source_id,
             _now_iso()))
        return int(cursor.lastrowid)

    def insert_observation(self, observation: Observation,
                           source_id: Optional[str] = None) -> int:
        """Append a revision of ``observation``; returns the new row id.

        The logical id is the content fingerprint of the observation, so the
        same measurement always maps to the same id.
        """
        row_id = self._insert_observation_row(observation, source_id)
        self.connection.commit()
        return row_id

    def bulk_insert_observations(self, observations: Iterable[Observation]) -> int:
        """Append many observations in one transaction; returns the count.

        Same append-only semantics as :meth:`insert_observation`; the single
        transaction is a speed detail for the corpus load, not a behaviour
        change.
        """
        count = 0
        with self.connection:
            for observation in observations:
                self._insert_observation_row(observation, None)
                count += 1
        return count

    def insert_claim(self, claim: Claim) -> int:
        """Append a revision of ``claim``; returns the new row id.

        A claim without any observation reference is refused: no figure
        circulates without a traceable parent (architecture invariant).
        """
        if not claim.refs:
            raise ValueError("claim %s has no observation reference" % claim.id)
        fingerprint = claim.fingerprint or models.claim_fingerprint(
            claim.id, claim.text, claim.refs, claim.created_at)
        revision = self._next_revision("claims", "claim_id", claim.id)
        cursor = self.connection.execute(
            "INSERT INTO claims (claim_id, revision, text, refs, created_at, "
            "fingerprint, inserted_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (claim.id, revision, claim.text, json.dumps(list(claim.refs)),
             claim.created_at, fingerprint, _now_iso()))
        self.connection.commit()
        return int(cursor.lastrowid)

    def insert_relation(self, relation: Relation) -> int:
        """Append a revision of ``relation``; returns the new row id.

        ``source_family_id`` and ``extract_method`` (L1.3) are persisted; a
        non-empty ``extract_method`` must be one of the closed vocabulary
        (B2 §3.0 field 14).
        """
        if relation.extract_method and relation.extract_method not in EXTRACT_METHOD:
            raise ValueError("unknown extract_method: %s" % relation.extract_method)
        revision = self._next_revision("relations", "relation_id", relation.id)
        cursor = self.connection.execute(
            "INSERT INTO relations (relation_id, revision, src, dst, kind, "
            "source_family_id, extract_method, inserted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (relation.id, revision, relation.src, relation.dst, relation.kind,
             relation.source_family_id, relation.extract_method, _now_iso()))
        self.connection.commit()
        return int(cursor.lastrowid)

    def insert_hypothesis(self, hypothesis: Hypothesis) -> int:
        """Append a revision of ``hypothesis``; returns the new row id."""
        revision = self._next_revision("hypotheses", "hypothesis_id", hypothesis.id)
        cursor = self.connection.execute(
            "INSERT INTO hypotheses (hypothesis_id, revision, statement, state, "
            "criteria_support, criteria_refute, inserted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (hypothesis.id, revision, hypothesis.statement, hypothesis.state,
             json.dumps(list(hypothesis.criteria_support)),
             json.dumps(list(hypothesis.criteria_refute)), _now_iso()))
        self.connection.commit()
        return int(cursor.lastrowid)

    def insert_decision_node(self, node: DecisionNode) -> int:
        """Append a revision of ``node``; returns the new row id."""
        revision = self._next_revision("decision_nodes", "node_id", node.id)
        cursor = self.connection.execute(
            "INSERT INTO decision_nodes (node_id, revision, kind, payload, refs, "
            "inserted_at) VALUES (?, ?, ?, ?, ?, ?)",
            (node.id, revision, node.kind, json.dumps(node.payload),
             json.dumps(list(node.refs)), _now_iso()))
        self.connection.commit()
        return int(cursor.lastrowid)

    # -- reads (current revision) --------------------------------------------

    def relation_by_id(self, relation_id: str) -> Optional[Relation]:
        """Current revision of a relation, or ``None`` (columns of L1.3 read)."""
        row = self._latest_row("relations", "relation_id", relation_id)
        if row is None:
            return None
        return Relation(id=row["relation_id"], src=row["src"], dst=row["dst"],
                        kind=row["kind"],
                        source_family_id=row["source_family_id"],
                        extract_method=row["extract_method"])

    def claim_by_id(self, claim_id: str) -> Optional[Claim]:
        """Current revision of a claim, or ``None``."""
        row = self._latest_row("claims", "claim_id", claim_id)
        if row is None:
            return None
        return Claim(id=row["claim_id"], text=row["text"],
                     refs=json.loads(row["refs"]), created_at=row["created_at"],
                     fingerprint=row["fingerprint"])

    def observation_by_id(self, observation_id: str) -> Optional[Observation]:
        """Current revision of an observation, or ``None``."""
        row = self._latest_row("observations", "observation_id", observation_id)
        if row is None:
            return None
        return self._observation_from_row(row)

    def source_by_id(self, source_id: str) -> Optional[Source]:
        """Current revision of a source, or ``None``."""
        row = self._latest_row("sources", "source_id", source_id)
        if row is None:
            return None
        return Source(id=row["source_id"], name=row["name"],
                      endpoint=row["endpoint"], retrieved_at=row["retrieved_at"],
                      limits=row["limits"])

    def has_source(self, source_id: str) -> bool:
        """True when a source with this id exists in the store."""
        return self.source_by_id(source_id) is not None

    def hypothesis_by_id(self, hypothesis_id: str) -> Optional[Hypothesis]:
        """Current revision of a hypothesis, or ``None``."""
        row = self._latest_row("hypotheses", "hypothesis_id", hypothesis_id)
        if row is None:
            return None
        return Hypothesis(id=row["hypothesis_id"], statement=row["statement"],
                          state=row["state"],
                          criteria_support=json.loads(row["criteria_support"]),
                          criteria_refute=json.loads(row["criteria_refute"]))

    def all_claims(self) -> List[Claim]:
        """Every current claim, ordered by claim id."""
        ids = [row[0] for row in self.connection.execute(
            "SELECT DISTINCT claim_id FROM claims ORDER BY claim_id")]
        return [claim for claim in (self.claim_by_id(cid) for cid in ids)
                if claim is not None]

    def claims_for_hypothesis(self, hypothesis_id: str) -> List[Claim]:
        """Claims attached to a hypothesis through supports/refutes relations."""
        kinds = models.RELATION_SUPPORT_KINDS
        placeholders = ",".join("?" for _ in kinds)
        sql = ("SELECT DISTINCT r.src FROM relations r "
               "WHERE r.kind IN (%s) AND r.dst = ? "
               "AND r.row_id = (SELECT MAX(row_id) FROM relations "
               "                WHERE relation_id = r.relation_id) "
               "ORDER BY r.src" % placeholders)
        claim_ids = [row[0] for row in
                     self.connection.execute(sql, (*kinds, hypothesis_id))]
        return [claim for claim in (self.claim_by_id(cid) for cid in claim_ids)
                if claim is not None]

    def observations_for_claim(self, claim_id: str) -> List[Observation]:
        """Observations referenced by a claim (missing refs are omitted)."""
        claim = self.claim_by_id(claim_id)
        if claim is None:
            return []
        found = [self.observation_by_id(ref) for ref in claim.refs]
        observations = [obs for obs in found if obs is not None]
        observations.sort(key=lambda obs: (obs.ts_event, obs.venue, obs.metric))
        return observations

    # -- snapshots -----------------------------------------------------------

    def current_row_count(self, table: str) -> int:
        """Number of current (latest revision) rows of ``table``."""
        id_column = dict(_TABLES)[table]
        sql = ("SELECT COUNT(*) FROM (SELECT MAX(row_id) AS r FROM %s "
               "GROUP BY %s)" % (table, id_column))
        return int(self.connection.execute(sql).fetchone()[0])

    def snapshot(self) -> Dict[str, object]:
        """Freeze the current graph: version, stable hash and counts.

        ``counts`` counts logical entities (current revision per id);
        ``rows_total`` counts every physical row, superseded revisions
        included — that is what an append-only store looks like.
        """
        rows = self._current_rows()
        counts = {}
        for table, _ in _TABLES:
            counts[table] = sum(1 for row in rows if row["_table"] == table)
        return {
            "graph_version": GRAPH_VERSION,
            "schema_version": SCHEMA_VERSION,
            "hash": snapshot_hash(rows),
            "counts": counts,
            "rows_total": self._table_row_counts(),
        }

    # -- misc ----------------------------------------------------------------

    def _observation_from_row(self, row: Mapping[str, object]) -> Observation:
        return Observation(
            venue=row["venue"],
            metric=row["metric"],
            ts_event=parse_timestamp(row["ts_event"]),
            value=float(row["value"]),
            extra=row["extra"],
            retrieved_at=row["retrieved_at"],
            source_id=row["source_id"],
        )
