"""Point-in-time graph export for the audit packet (W1 lot L1.6).

Builds two deterministic, self-hashed artefacts from a record set and an
``as_of`` moment (the W6-audit contract):

- ``graph_snapshot.json`` — the PIT-frozen records (world validity ∩
  knowledge clock, i.e. :func:`orvyren.graph.queries.q4_pit_state`), with
  counts by kind/family and a SHA-256 ``snapshot_hash`` over its frozen
  content;
- ``provenance.json`` — for every provenance origin present in the snapshot,
  the full walk (decision → claims → observations → sources) with per-hop
  fingerprints and a SHA-256 ``provenance_hash``.

A ``MANIFEST.sha256`` file (``sha256sum``-compatible) rides along, so a third
party can re-verify both artefacts byte-for-byte without trusting us. Output
is pure and deterministic: same records + same ``as_of`` → same bytes.

Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from orvyren.graph.models import canonical_json
from orvyren.graph.queries import (_PROVENANCE_KINDS, q4_pit_state,
                                   q6_provenance_walk)
from orvyren.graph.record import RelationRecord, record_as_dict

__all__ = [
    "SNAPSHOT_SCHEMA",
    "PROVENANCE_SCHEMA",
    "build_snapshot",
    "build_provenance",
    "snapshot_sha256",
    "write_snapshot_dir",
]

SNAPSHOT_SCHEMA = "orvyren/graph-snapshot/v1"
PROVENANCE_SCHEMA = "orvyren/graph-provenance/v1"

#: Generator stamp written into every artefact (traceability, not behaviour).
GENERATOR = "orvyren.graph.export/1"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def snapshot_sha256(snapshot: Mapping[str, Any]) -> str:
    """SHA-256 over the frozen content (hash fields excluded)."""
    frozen = {key: value for key, value in snapshot.items()
              if key not in ("snapshot_hash",)}
    return _sha256_text(canonical_json(frozen))


def _counts(records: Sequence[RelationRecord]) -> Dict[str, Any]:
    by_kind: Dict[str, int] = {}
    by_family: Dict[str, int] = {}
    for record in records:
        by_kind[record.kind] = by_kind.get(record.kind, 0) + 1
        by_family[record.family] = by_family.get(record.family, 0) + 1
    return {"records": len(records),
            "by_kind": dict(sorted(by_kind.items())),
            "by_family": dict(sorted(by_family.items()))}


def build_snapshot(records: Sequence[RelationRecord], case_id: str,
                   as_of: str) -> Dict[str, Any]:
    """PIT-frozen snapshot of ``case_id`` at ``as_of``, self-hashed."""
    pit = q4_pit_state(records, as_of)
    snapshot = {
        "schema": SNAPSHOT_SCHEMA,
        "case_id": case_id,
        "as_of": as_of,
        "generator": GENERATOR,
        "counts": _counts(pit),
        "records": [record_as_dict(record) for record in pit],
    }
    snapshot["snapshot_hash"] = snapshot_sha256(snapshot)
    return snapshot


def build_provenance(records: Sequence[RelationRecord], case_id: str,
                     as_of: str) -> Dict[str, Any]:
    """Provenance chains of every origin visible in the PIT snapshot."""
    pit = q4_pit_state(records, as_of)
    origins = sorted({record.src for record in pit
                      if record.kind in _PROVENANCE_KINDS})
    chains: List[Dict[str, Any]] = []
    for origin in origins:
        walk = q6_provenance_walk(pit, origin)
        if walk["chain"]:
            chains.append(walk)
    provenance = {
        "schema": PROVENANCE_SCHEMA,
        "case_id": case_id,
        "as_of": as_of,
        "generator": GENERATOR,
        "chains": chains,
        "origins": len(chains),
        "hashes_complete": all(chain["hashes_complete"] for chain in chains)
                           and bool(chains) if chains else True,
    }
    provenance["provenance_hash"] = _sha256_text(
        canonical_json({key: value for key, value in provenance.items()
                        if key != "provenance_hash"}))
    return provenance


def _write_json(path: str, payload: Mapping[str, Any]) -> None:
    # newline="\n": platform-stable bytes (a Windows CRLF would break the
    # sha256sum -c round trip and every cross-platform digest check).
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write("\n")


def write_snapshot_dir(records: Sequence[RelationRecord], case_id: str,
                       as_of: str, out_dir: str) -> Dict[str, str]:
    """Write ``graph_snapshot.json`` + ``provenance.json`` + ``MANIFEST.sha256``.

    Returns the three paths. The manifest lists the two artefact digests in
    ``sha256sum`` format, so ``sha256sum -c MANIFEST.sha256`` re-verifies.
    """
    os.makedirs(out_dir, exist_ok=True)
    snapshot = build_snapshot(records, case_id, as_of)
    provenance = build_provenance(records, case_id, as_of)
    snapshot_path = os.path.join(out_dir, "graph_snapshot.json")
    provenance_path = os.path.join(out_dir, "provenance.json")
    _write_json(snapshot_path, snapshot)
    _write_json(provenance_path, provenance)
    manifest_path = os.path.join(out_dir, "MANIFEST.sha256")
    lines = []
    for path in (snapshot_path, provenance_path):
        with open(path, "rb") as handle:
            lines.append("%s  %s" % (hashlib.sha256(handle.read()).hexdigest(),
                                     os.path.basename(path)))
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    return {"snapshot": snapshot_path, "provenance": provenance_path,
            "manifest": manifest_path,
            "snapshot_hash": snapshot["snapshot_hash"],
            "provenance_hash": provenance["provenance_hash"]}
