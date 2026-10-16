"""Graph objects and canonical fingerprinting (ORVYREN-Core).

Objects
-------
``Source``        where a measurement came from (provider, endpoint, limits);
``Observation``   re-exported from :mod:`orvyren.quality.normalize`;
``Claim``         a statement, attached to observations through ``refs``;
``Relation``      a directed edge between two graph objects;
``Hypothesis``    a statement under test, with support/refutation criteria;
``DecisionNode``  a step of a decision, with its payload and references.

Fingerprints
------------
``fingerprint(obj)`` is the first 16 hex chars of the SHA-256 of a canonical
JSON serialisation (``sort_keys=True``, ``separators=(",", ":")``), so equal
content gives an equal fingerprint whatever the key order. Observation ids and
claim fingerprints are content addresses: they can be recomputed by an auditor
from the content alone, without trusting the store.

Standard library only.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Sequence

from orvyren.quality.normalize import Observation  # noqa: F401  (re-exported)

__all__ = [
    "Observation",
    "Source",
    "Claim",
    "Relation",
    "Hypothesis",
    "DecisionNode",
    "FINGERPRINT_LENGTH",
    "canonical_json",
    "fingerprint",
    "observation_fingerprint",
    "claim_fingerprint",
    "make_claim",
    "HYPOTHESIS_STATES",
    "RELATION_SUPPORT_KINDS",
]

#: Fingerprints are truncated to this many hex characters.
FINGERPRINT_LENGTH = 16

#: Lifecycle of a hypothesis (architecture: CREATED -> ... -> ARCHIVED).
HYPOTHESIS_STATES = ("CREATED", "UNDER_TEST", "SUPPORTED", "REFUTED", "ARCHIVED")

#: Relation kinds that attach a claim to a hypothesis.
RELATION_SUPPORT_KINDS = ("supports", "refutes")


def _json_default(value: Any) -> Any:
    """Serialise non-JSON-native values deterministically."""
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    if dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    if isinstance(value, tuple):
        return list(value)
    raise TypeError("not JSON-serialisable: %r" % (value,))


def canonical_json(obj: Any) -> str:
    """Canonical JSON text of ``obj`` (sorted keys, no spaces)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=_json_default)


def fingerprint(obj: Any) -> str:
    """Stable 16-hex-char fingerprint of ``obj`` (see module docstring)."""
    digest = hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()
    return digest[:FINGERPRINT_LENGTH]


def observation_fingerprint(observation: Observation) -> str:
    """Content id of an observation (venue, metric, event time, value...)."""
    return fingerprint({
        "venue": observation.venue,
        "metric": observation.metric,
        "ts_event": observation.ts_event_iso,
        "value": observation.value,
        "extra": observation.extra,
        "retrieved_at": observation.retrieved_at,
        "source_id": observation.source_id,
    })


def claim_fingerprint(claim_id: str, text: str, refs: Sequence[str],
                      created_at: str) -> str:
    """Content fingerprint of a claim (refs order is part of the content)."""
    return fingerprint({
        "id": claim_id,
        "text": text,
        "refs": list(refs),
        "created_at": created_at,
    })


def make_claim(claim_id: str, text: str, refs: Sequence[str],
               created_at: str) -> "Claim":
    """Build a claim with its fingerprint already computed."""
    return Claim(
        id=claim_id,
        text=text,
        refs=list(refs),
        created_at=created_at,
        fingerprint=claim_fingerprint(claim_id, text, refs, created_at),
    )


@dataclass(frozen=True)
class Source:
    """A data source of the archive."""

    id: str
    name: str
    endpoint: str
    retrieved_at: str
    limits: str


@dataclass(frozen=True)
class Claim:
    """A statement attached to observations through ``refs``.

    ``refs`` are observation ids (see :func:`observation_fingerprint`). A
    claim with no observation reference is refused by the store: no figure
    circulates without a traceable parent.
    """

    id: str
    text: str
    refs: List[str] = field(default_factory=list)
    created_at: str = ""
    fingerprint: str = ""


@dataclass(frozen=True)
class Relation:
    """A directed, typed edge between two graph objects.

    ``source_family_id`` and ``extract_method`` (B2 §3.0 fields 13–14, lot
    L1.3) carry the retroactive columns: which source family produced the edge
    (INV-DEPENDENCE) and how it was extracted (RULE / ONCHAIN_READ /
    LLM_EXTRACT / HUMAN). Legacy rows use the empty string.
    """

    id: str
    src: str
    dst: str
    kind: str
    source_family_id: str = ""
    extract_method: str = ""


@dataclass(frozen=True)
class Hypothesis:
    """A statement under test, with its support/refutation criteria."""

    id: str
    statement: str
    state: str
    criteria_support: List[str] = field(default_factory=list)
    criteria_refute: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class DecisionNode:
    """A step of a decision: an action kind, a payload and its references."""

    id: str
    kind: str
    payload: Dict[str, Any] = field(default_factory=dict)
    refs: List[str] = field(default_factory=list)
