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
import re
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from orvyren.graph import models
from orvyren.graph.catalog import EXTRACT_METHOD, KIND_CLASS
from orvyren.graph.models import (Claim, DecisionNode, Hypothesis, Observation,
                                  Relation, Source)
from orvyren.graph.provenance import snapshot_hash
from orvyren.graph.record import (ChainRef, RelationRecord,
                                  validate_relation_record)
from orvyren.quality.normalize import parse_timestamp

__all__ = ["GraphStore", "SCHEMA_VERSION", "GRAPH_VERSION"]

#: v3 (graph-v2 schema): the 17-field relation record is persisted, and the
#: nodes/events/provenance tables make the graph queryable. v2 databases are
#: migrated additively on open (no UPDATE/DELETE; old rows get safe defaults).
SCHEMA_VERSION = 3
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

#: Canonical on-chain node ids: ``addr|asset|market|role|param:eip155:<chain>:<id>``.
_NODE_CHAIN_RE = re.compile(r"^(?:addr|asset|market|role|param):eip155:(\d+):(.+)$")

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
    family           TEXT NOT NULL DEFAULT '',
    kind             TEXT NOT NULL,
    src              TEXT NOT NULL,
    dst              TEXT NOT NULL,
    src_kind         TEXT NOT NULL DEFAULT '',
    dst_kind         TEXT NOT NULL DEFAULT '',
    mechanism        TEXT NOT NULL DEFAULT '',
    sign_prior       TEXT NOT NULL DEFAULT 'ambigu',
    conditions       TEXT NOT NULL DEFAULT '',
    regime_scope     TEXT NOT NULL DEFAULT '',
    horizon_scope    TEXT NOT NULL DEFAULT '',
    epistemic_status TEXT NOT NULL DEFAULT 'REPORTED',
    lifecycle        TEXT NOT NULL DEFAULT 'DISCOVERED',
    validation_status TEXT NOT NULL DEFAULT 'PENDING',
    valid_from       TEXT,
    valid_to         TEXT,
    valid_from_block INTEGER,
    valid_to_block   INTEGER,
    superseded_by    TEXT,
    provenance_refs  TEXT NOT NULL DEFAULT '[]',
    source_family_id TEXT NOT NULL DEFAULT '',
    extract_method   TEXT NOT NULL DEFAULT '',
    model_version    TEXT NOT NULL DEFAULT '',
    run_id           TEXT NOT NULL DEFAULT '',
    chain_id         INTEGER,
    block_number     INTEGER,
    block_hash       TEXT,
    tx_hash          TEXT,
    log_index        INTEGER,
    finality         TEXT NOT NULL DEFAULT 'FINALIZED',
    confidence       REAL NOT NULL DEFAULT 0.0,
    payload          TEXT NOT NULL DEFAULT '{}',
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

-- Graph v2 (schema v3): first-class nodes and events. The existing
-- observations/claims/relations tables remain the proof layer; these tables
-- make the world layer queryable without rewriting the legacy rows.

CREATE TABLE IF NOT EXISTS nodes (
    row_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id      TEXT NOT NULL,
    revision     INTEGER NOT NULL,
    kind         TEXT NOT NULL,
    node_class   TEXT NOT NULL,
    chain_id     INTEGER,
    address      TEXT,
    canonical_key TEXT NOT NULL,
    label        TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'ACTIVE',
    valid_from   TEXT,
    valid_to     TEXT,
    inserted_at  TEXT NOT NULL,
    payload      TEXT NOT NULL DEFAULT '{}',
    UNIQUE (node_id, revision)
);

CREATE TABLE IF NOT EXISTS node_aliases (
    alias_id     TEXT PRIMARY KEY,
    node_id      TEXT NOT NULL,
    alias        TEXT NOT NULL,
    source_id    TEXT NOT NULL,
    valid_from   TEXT,
    valid_to     TEXT,
    confidence   REAL NOT NULL DEFAULT 0.0,
    inserted_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    event_id         TEXT PRIMARY KEY,
    event_type       TEXT NOT NULL,
    chain_id         INTEGER,
    block_number     INTEGER,
    block_hash       TEXT,
    tx_hash          TEXT,
    log_index        INTEGER,
    event_time       TEXT,
    publication_time TEXT,
    observation_time TEXT NOT NULL,
    effective_time   TEXT,
    valid_from       TEXT,
    valid_to         TEXT,
    actors           TEXT NOT NULL DEFAULT '[]',
    targets          TEXT NOT NULL DEFAULT '[]',
    magnitude        REAL,
    actual           REAL,
    expected         REAL,
    surprise         REAL,
    status           TEXT NOT NULL DEFAULT 'CONFIRMED',
    payload          TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS event_observations (
    event_id       TEXT NOT NULL,
    observation_id TEXT NOT NULL,
    relation       TEXT NOT NULL,
    source_id      TEXT NOT NULL,
    confidence     REAL NOT NULL DEFAULT 0.0,
    inserted_at    TEXT NOT NULL,
    PRIMARY KEY (event_id, observation_id, relation)
);

CREATE TABLE IF NOT EXISTS relation_provenance (
    relation_id      TEXT NOT NULL,
    revision         INTEGER NOT NULL,
    ref_id           TEXT NOT NULL,
    ref_kind         TEXT NOT NULL,
    source_family_id TEXT NOT NULL DEFAULT '',
    extract_method   TEXT NOT NULL DEFAULT '',
    run_id           TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (relation_id, revision, ref_id)
);

CREATE TABLE IF NOT EXISTS source_families (
    source_family_id TEXT PRIMARY KEY,
    description      TEXT NOT NULL,
    independence     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ingestion_watermarks (
    source_id       TEXT PRIMARY KEY,
    last_block      INTEGER NOT NULL,
    last_block_hash TEXT,
    last_ts         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'OK'
);

CREATE TABLE IF NOT EXISTS graph_snapshots (
    snapshot_id  TEXT PRIMARY KEY,
    as_of        TEXT,
    as_of_block  INTEGER,
    graph_hash   TEXT NOT NULL,
    counts       TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_observations_id  ON observations(observation_id);
CREATE INDEX IF NOT EXISTS idx_observations_src ON observations(source_id);
CREATE INDEX IF NOT EXISTS idx_observations_hour ON observations(ts_event);
CREATE INDEX IF NOT EXISTS idx_sources_id       ON sources(source_id);
CREATE INDEX IF NOT EXISTS idx_claims_id        ON claims(claim_id);
CREATE INDEX IF NOT EXISTS idx_relations_dst    ON relations(dst);
CREATE INDEX IF NOT EXISTS idx_hypotheses_id    ON hypotheses(hypothesis_id);
CREATE INDEX IF NOT EXISTS idx_nodes_kind       ON nodes(kind);
CREATE INDEX IF NOT EXISTS idx_nodes_class      ON nodes(node_class);
CREATE INDEX IF NOT EXISTS idx_nodes_chain_addr ON nodes(chain_id, address);
CREATE INDEX IF NOT EXISTS idx_nodes_label      ON nodes(label);
CREATE INDEX IF NOT EXISTS idx_alias_node       ON node_aliases(node_id);
CREATE INDEX IF NOT EXISTS idx_events_type_time ON events(event_type, event_time);
CREATE INDEX IF NOT EXISTS idx_events_chain_block ON events(chain_id, block_number);
CREATE INDEX IF NOT EXISTS idx_events_tx        ON events(chain_id, tx_hash);
CREATE INDEX IF NOT EXISTS idx_rel_prov_ref     ON relation_provenance(ref_id);
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
            for table in ("nodes", "node_aliases", "events", "event_observations",
                          "relation_provenance", "graph_snapshots"):
                self.connection.executescript(
                    _APPEND_ONLY_TRIGGERS.format(table=table))
            row = self.connection.execute(
                "SELECT MAX(version) FROM schema_version").fetchone()
            if row[0] is None or int(row[0]) < SCHEMA_VERSION:
                self.connection.execute(
                    "INSERT OR IGNORE INTO schema_version (version, applied_at) "
                    "VALUES (?, ?)", (SCHEMA_VERSION, _now_iso()))

    def _migrate_relation_columns(self) -> None:
        """Additive migration from the v1/v2 relations table to schema v3.

        SQLite ``ALTER TABLE ADD COLUMN`` is append-only; every new column is
        nullable or carries a safe default, so legacy rows stay readable. The
        old ``insert_relation`` path keeps working with defaults; the new
        ``insert_relation_record`` writes the full 17-field record.
        """
        existing = {row["name"] for row in self.connection.execute(
            "PRAGMA table_info(relations)")}
        columns = (
            ("source_family_id", "TEXT NOT NULL DEFAULT ''"),
            ("extract_method", "TEXT NOT NULL DEFAULT ''"),
            ("family", "TEXT NOT NULL DEFAULT ''"),
            ("src_kind", "TEXT NOT NULL DEFAULT ''"),
            ("dst_kind", "TEXT NOT NULL DEFAULT ''"),
            ("mechanism", "TEXT NOT NULL DEFAULT ''"),
            ("sign_prior", "TEXT NOT NULL DEFAULT 'ambigu'"),
            ("conditions", "TEXT NOT NULL DEFAULT ''"),
            ("regime_scope", "TEXT NOT NULL DEFAULT ''"),
            ("horizon_scope", "TEXT NOT NULL DEFAULT ''"),
            ("epistemic_status", "TEXT NOT NULL DEFAULT 'REPORTED'"),
            ("lifecycle", "TEXT NOT NULL DEFAULT 'DISCOVERED'"),
            ("validation_status", "TEXT NOT NULL DEFAULT 'PENDING'"),
            ("valid_from", "TEXT"),
            ("valid_to", "TEXT"),
            ("valid_from_block", "INTEGER"),
            ("valid_to_block", "INTEGER"),
            ("superseded_by", "TEXT"),
            ("provenance_refs", "TEXT NOT NULL DEFAULT '[]'"),
            ("model_version", "TEXT NOT NULL DEFAULT ''"),
            ("run_id", "TEXT NOT NULL DEFAULT ''"),
            ("chain_id", "INTEGER"),
            ("block_number", "INTEGER"),
            ("block_hash", "TEXT"),
            ("tx_hash", "TEXT"),
            ("log_index", "INTEGER"),
            ("finality", "TEXT NOT NULL DEFAULT 'FINALIZED'"),
            ("confidence", "REAL NOT NULL DEFAULT 0.0"),
            ("payload", "TEXT NOT NULL DEFAULT '{}'"),
        )
        for column, ddl in columns:
            if column not in existing:
                self.connection.execute(
                    "ALTER TABLE relations ADD COLUMN %s %s" % (column, ddl))
        for statement in (
            # Do not create a manual index on (src, kind) / (dst, kind) on the
            # append-only table: MiniMax measured x117-139 slower Q1 at 50k/100k
            # (the manual index defeats SQLite's automatic (lifecycle, src)
            # covering index). Materialize `edge_current` before indexing it.
            "CREATE INDEX IF NOT EXISTS idx_rel_current_v2 ON relations(relation_id, inserted_at)",
            "CREATE INDEX IF NOT EXISTS idx_rel_valid_v2 ON relations(valid_from, valid_to)",
        ):
            self.connection.execute(statement)

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

        Legacy path: it writes the historical columns only. New code should use
        :meth:`insert_relation_record`, which persists the full 17-field record.
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

    # -- graph-v2 writes -----------------------------------------------------

    @staticmethod
    def _ref_kind(ref_id: str) -> str:
        """Best-effort kind of a provenance reference (stable prefixes)."""
        for prefix, kind in (("obs:", "OBSERVATION"), ("claim:", "CLAIM"),
                             ("doc:", "DOCUMENT"), ("event:", "EVENT"),
                             ("hyp:", "HYPOTHESE"), ("src:", "SOURCE")):
            if ref_id.startswith(prefix):
                return kind
        return "UNKNOWN"

    def _ensure_node(self, node_id: str, kind: str) -> None:
        """Insert a canonical node if absent; never overwrite an existing one."""
        if not node_id:
            return
        kind = kind or "UNKNOWN"
        node_class = KIND_CLASS.get(kind, kind)
        chain_id = None
        address = None
        match = _NODE_CHAIN_RE.match(node_id)
        if match:
            chain_id = int(match.group(1))
            address = match.group(2).lower()
        self.connection.execute(
            "INSERT OR IGNORE INTO nodes (node_id, revision, kind, node_class, "
            "chain_id, address, canonical_key, label, status, inserted_at, payload) "
            "VALUES (?, 1, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, '{}')",
            (node_id, kind, node_class, chain_id, address, node_id, node_id,
             _now_iso()))

    def insert_node(self, node_id: str, kind: str, node_class: Optional[str] = None,
                    chain_id: Optional[int] = None, address: Optional[str] = None,
                    label: Optional[str] = None, payload: Optional[Mapping[str, Any]] = None,
                    status: str = "ACTIVE", valid_from: Optional[str] = None,
                    valid_to: Optional[str] = None) -> int:
        """Append a revision of a graph node; returns the new row id."""
        if not node_id.strip():
            raise ValueError("node_id is empty")
        revision = self._next_revision("nodes", "node_id", node_id)
        body = json.dumps(dict(payload or {}), sort_keys=True, default=str)
        cursor = self.connection.execute(
            "INSERT INTO nodes (node_id, revision, kind, node_class, chain_id, "
            "address, canonical_key, label, status, valid_from, valid_to, "
            "inserted_at, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (node_id, revision, kind or "UNKNOWN",
             node_class or KIND_CLASS.get(kind, kind) or "UNKNOWN",
             chain_id, address.lower() if address else None, node_id,
             label or node_id, status, valid_from, valid_to, _now_iso(), body))
        self.connection.commit()
        return int(cursor.lastrowid)

    def insert_event(self, event: Mapping[str, Any]) -> int:
        """Insert one first-class event. ``event_id`` and ``event_type`` are required."""
        event_id = str(event.get("event_id", "")).strip()
        event_type = str(event.get("event_type", "")).strip()
        observation_time = str(event.get("observation_time", "")).strip()
        if not event_id or not event_type or not observation_time:
            raise ValueError("event_id, event_type and observation_time are required")
        actors = event.get("actors", [])
        targets = event.get("targets", [])
        payload = event.get("payload", {})
        cursor = self.connection.execute(
            "INSERT INTO events (event_id, event_type, chain_id, block_number, "
            "block_hash, tx_hash, log_index, event_time, publication_time, "
            "observation_time, effective_time, valid_from, valid_to, actors, "
            "targets, magnitude, actual, expected, surprise, status, payload) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (event_id, event_type, event.get("chain_id"), event.get("block_number"),
             event.get("block_hash"), event.get("tx_hash"), event.get("log_index"),
             event.get("event_time"), event.get("publication_time"),
             observation_time, event.get("effective_time"), event.get("valid_from"),
             event.get("valid_to"),
             actors if isinstance(actors, str) else json.dumps(list(actors), default=str),
             targets if isinstance(targets, str) else json.dumps(list(targets), default=str),
             event.get("magnitude"), event.get("actual"), event.get("expected"),
             event.get("surprise"), event.get("status", "CONFIRMED"),
             payload if isinstance(payload, str) else json.dumps(dict(payload), sort_keys=True,
                                                                  default=str)))
        self.connection.commit()
        return int(cursor.lastrowid)

    def insert_relation_record(self, record: RelationRecord) -> int:
        """Persist a validated 17-field relation record and its provenance.

        Raises ``ValueError`` with the stable ``E_*`` codes when the record does
        not conform to the catalogue. This is the writer the graph pipeline and
        the tests should use; ``insert_relation`` stays as the legacy path.
        """
        errors = validate_relation_record(record)
        if errors:
            raise ValueError("invalid relation record: %s" % ", ".join(errors))
        self._ensure_node(record.src, record.src_kind)
        self._ensure_node(record.dst, record.dst_kind)
        revision = self._next_revision("relations", "relation_id", record.relation_id)
        refs = json.dumps(list(record.provenance_refs))
        body = json.dumps(dict(record.payload), sort_keys=True, default=str)
        chain_ref = record.chain_ref
        cursor = self.connection.execute(
            "INSERT INTO relations (relation_id, revision, family, kind, src, dst, "
            "src_kind, dst_kind, mechanism, sign_prior, conditions, regime_scope, "
            "horizon_scope, epistemic_status, lifecycle, validation_status, "
            "valid_from, valid_to, valid_from_block, valid_to_block, superseded_by, "
            "provenance_refs, source_family_id, extract_method, model_version, run_id, "
            "chain_id, block_number, block_hash, tx_hash, log_index, finality, "
            "confidence, payload, inserted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
            "?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (record.relation_id, revision, record.family, record.kind, record.src,
             record.dst, record.src_kind, record.dst_kind, record.mechanism,
             record.sign_prior, record.conditions, record.regime_scope,
             record.horizon_scope, record.epistemic_status, record.lifecycle,
             record.validation_status, record.valid_from, record.valid_to,
             record.payload.get("valid_from_block"), record.payload.get("valid_to_block"),
             record.superseded_by, refs, record.source_family_id, record.extract_method,
             record.model_version, record.run_id,
             chain_ref.chain_id if chain_ref else None,
             chain_ref.block if chain_ref else None,
             None, chain_ref.tx_hash if chain_ref else None,
             record.payload.get("log_index"),
             str(record.payload.get("finality", "FINALIZED")),
             float(record.confidence), body, record.inserted_at))
        for ref in record.provenance_refs:
            self.connection.execute(
                "INSERT OR IGNORE INTO relation_provenance (relation_id, revision, "
                "ref_id, ref_kind, source_family_id, extract_method, run_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (record.relation_id, revision, ref, self._ref_kind(ref),
                 record.source_family_id, record.extract_method, record.run_id))
        self.connection.commit()
        return int(cursor.lastrowid)

    def insert_source_family(self, source_family_id: str, description: str,
                             independence: str) -> None:
        """Register a source family once (idempotent)."""
        self.connection.execute(
            "INSERT OR IGNORE INTO source_families (source_family_id, description, "
            "independence) VALUES (?, ?, ?)",
            (source_family_id, description, independence))
        self.connection.commit()

    def set_watermark(self, source_id: str, last_block: int,
                      last_block_hash: Optional[str] = None,
                      last_ts: Optional[str] = None,
                      status: str = "OK") -> None:
        """Upsert the ingestion watermark of a source (the only mutable table)."""
        self.connection.execute(
            "INSERT INTO ingestion_watermarks (source_id, last_block, last_block_hash, "
            "last_ts, status) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(source_id) DO UPDATE SET last_block=excluded.last_block, "
            "last_block_hash=excluded.last_block_hash, last_ts=excluded.last_ts, "
            "status=excluded.status",
            (source_id, int(last_block), last_block_hash, last_ts or _now_iso(), status))
        self.connection.commit()

    def record_graph_snapshot(self, snapshot_id: str,
                              as_of: Optional[str] = None,
                              as_of_block: Optional[int] = None,
                              graph_hash: Optional[str] = None) -> int:
        """Persist a graph snapshot reference (append-only)."""
        snapshot = self.snapshot_v2()
        counts = json.dumps(snapshot["counts"], sort_keys=True)
        cursor = self.connection.execute(
            "INSERT INTO graph_snapshots (snapshot_id, as_of, as_of_block, graph_hash, "
            "counts, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (snapshot_id, as_of, as_of_block, graph_hash or str(snapshot["hash"]),
             counts, _now_iso()))
        self.connection.commit()
        return int(cursor.lastrowid)

    def graph_counts(self) -> Dict[str, int]:
        """Current logical counts of the graph-v2 world tables."""
        counts: Dict[str, int] = {
            "nodes": int(self.connection.execute(
                "SELECT COUNT(DISTINCT node_id) FROM nodes").fetchone()[0]),
            "events": int(self.connection.execute(
                "SELECT COUNT(DISTINCT event_id) FROM events").fetchone()[0]),
            "relation_provenance": int(self.connection.execute(
                "SELECT COUNT(DISTINCT relation_id) FROM relation_provenance").fetchone()[0]),
        }
        counts["relations"] = self.current_row_count("relations")
        return counts

    def node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Current revision of a node, as a plain dict."""
        row = self._latest_row("nodes", "node_id", node_id)
        return dict(row) if row is not None else None

    def event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """A first-class event, as a plain dict."""
        row = self.connection.execute(
            "SELECT * FROM events WHERE event_id = ?", (event_id,)).fetchone()
        return dict(row) if row is not None else None

    def relation_record_by_id(self, relation_id: str) -> Optional[RelationRecord]:
        """Current revision as a ``RelationRecord`` (legacy rows may be partial)."""
        row = self._latest_row("relations", "relation_id", relation_id)
        if row is None:
            return None
        chain_ref = None
        if row["chain_id"] is not None and row["block_number"] is not None:
            chain_ref = ChainRef(chain_id=int(row["chain_id"]),
                                 block=int(row["block_number"]),
                                 tx_hash=row["tx_hash"] or "")
        return RelationRecord(
            relation_id=row["relation_id"], family=row["family"], kind=row["kind"],
            src=row["src"], dst=row["dst"], src_kind=row["src_kind"],
            dst_kind=row["dst_kind"], mechanism=row["mechanism"],
            sign_prior=row["sign_prior"], conditions=row["conditions"],
            regime_scope=row["regime_scope"], horizon_scope=row["horizon_scope"],
            epistemic_status=row["epistemic_status"], lifecycle=row["lifecycle"],
            validation_status=row["validation_status"], valid_from=row["valid_from"],
            valid_to=row["valid_to"], revision=int(row["revision"]),
            inserted_at=row["inserted_at"], superseded_by=row["superseded_by"],
            provenance_refs=tuple(json.loads(row["provenance_refs"] or "[]")),
            source_family_id=row["source_family_id"],
            extract_method=row["extract_method"], model_version=row["model_version"],
            run_id=row["run_id"], chain_ref=chain_ref,
            confidence=float(row["confidence"]),
            payload=json.loads(row["payload"] or "{}"))

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

        This legacy snapshot covers the six proof-layer tables. Use
        :meth:`snapshot_v2` when the world layer (nodes/events/provenance) must
        be part of the hash.
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

    def snapshot_v2(self) -> Dict[str, object]:
        """Snapshot the proof layer + the world layer (nodes/events/provenance)."""
        rows = list(self._current_rows())
        current_nodes = self.connection.execute(
            "SELECT * FROM nodes WHERE row_id IN "
            "(SELECT MAX(row_id) FROM nodes GROUP BY node_id) ORDER BY node_id")
        for row in current_nodes:
            payload = dict(row)
            payload["_table"] = "nodes"
            rows.append(payload)
        for row in self.connection.execute(
                "SELECT * FROM events ORDER BY event_id"):
            payload = dict(row)
            payload["_table"] = "events"
            rows.append(payload)
        for row in self.connection.execute(
                "SELECT * FROM relation_provenance "
                "ORDER BY relation_id, revision, ref_id"):
            payload = dict(row)
            payload["_table"] = "relation_provenance"
            rows.append(payload)
        return {
            "graph_version": GRAPH_VERSION,
            "schema_version": SCHEMA_VERSION,
            "hash": snapshot_hash(rows),
            "counts": self.graph_counts(),
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
