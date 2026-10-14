"""Provenance: chain verification and snapshot hashing (ORVYREN-Core).

Two guarantees live here:

* :func:`verify_chain` — every reference of a claim must resolve to an
  observation that exists in the store, and that observation's source must
  exist too. A reference that does not resolve is reported, never ignored.
* :func:`snapshot_hash` — a stable SHA-256 over given graph rows, so a
  snapshot can be frozen and re-hashed later by an auditor.

Standard library only. This module depends on ``graph.models`` only; the
store is consumed through a small duck-typed interface (see :func:`verify_chain`),
which keeps the dependency direction clean.
"""

from __future__ import annotations

import hashlib
from typing import Dict, Iterable, List, Mapping, Sequence

from orvyren.graph import models

__all__ = ["snapshot_hash", "verify_chain", "verify_all"]

#: Row keys that carry storage mechanics rather than content; they are left
#: out of the hash so the digest depends only on logical content.
_VOLATILE_ROW_KEYS = ("row_id", "inserted_at")


def snapshot_hash(rows: Iterable[Mapping[str, object]]) -> str:
    """Stable SHA-256 (hex) over ``rows``.

    Rows are canonicalised (sorted keys, compact separators); keys listed in
    ``_VOLATILE_ROW_KEYS`` are dropped. The caller is responsible for passing
    rows in a deterministic order (the store orders by logical id), so the
    same content always yields the same digest.
    """
    payload: List[Dict[str, object]] = []
    for row in rows:
        payload.append({k: v for k, v in dict(row).items()
                        if k not in _VOLATILE_ROW_KEYS})
    return hashlib.sha256(models.canonical_json(payload).encode("utf-8")).hexdigest()


def verify_chain(claim_id: str, store) -> Dict[str, object]:
    """Verify that every reference of ``claim_id`` resolves.

    ``store`` must provide ``claim_by_id(claim_id)``,
    ``observation_by_id(observation_id)`` and ``has_source(source_id)``.

    Returns ``{"ok": bool, "missing": [refs], "checked": int, "error": str|None}``.
    A reference is *missing* when no observation carries that id, or when the
    observation's source does not exist in the store.
    """
    claim = store.claim_by_id(claim_id)
    if claim is None:
        return {"ok": False, "missing": [], "checked": 0, "error": "claim_not_found"}

    missing: List[str] = []
    for ref in claim.refs:
        if ref in missing:
            continue
        observation = store.observation_by_id(ref)
        if observation is None or not store.has_source(observation.source_id):
            missing.append(ref)

    return {
        "ok": not missing,
        "missing": missing,
        "checked": len(claim.refs),
        "error": None,
    }


def verify_all(store, claim_ids: Sequence[str] = ()) -> Dict[str, object]:
    """Verify the provenance chain of every claim of the store.

    ``claim_ids`` may restrict the check to selected claims. Returns a summary
    plus the per-claim results, in the order given or, by default, sorted by
    claim id.
    """
    if not claim_ids:
        claim_ids = [claim.id for claim in store.all_claims()]
    results = [dict(verify_chain(claim_id, store), claim_id=claim_id)
               for claim_id in claim_ids]
    return {
        "ok": all(result["ok"] for result in results),
        "claims_checked": len(results),
        "claims_failed": sum(1 for result in results if not result["ok"]),
        "results": results,
    }
