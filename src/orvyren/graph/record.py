"""ORVYREN relation record (17 fields) and its conformance validator.

Source of truth: ``B2_GRAPHE_ETUDE.md`` §3.0 — the 17-field record adapted from
the 10-field MIMIR §11.2 record. Every relation written to the graph must
carry the 17 field groups below; :func:`validate_relation_record` returns the
machine-checkable rejection codes (empty tuple = conform).

Three attributes are never conflated (B2 §3.0, RC §2.3):
``epistemic_status`` (what we believe we know), ``lifecycle`` (where the
relation stands in its cycle), ``validation_status`` (did it pass the gate).
An ACTIVE relation may remain hypothetical.

Standard library only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Tuple

from orvyren.graph.catalog import (
    EPISTEMIC_STATUS,
    EXTRACT_METHOD,
    FAMILY_MECHANISM,
    FAMILY_STRUCTURE,
    LIFECYCLE,
    RELATION_CATALOG,
    SIGN_PRIOR,
    SYMMETRIC,
    VALIDATION_STATUS,
    KIND_CLASS,
    token_matches,
)

__all__ = [
    "ChainRef",
    "RelationRecord",
    "RELATION_RECORD_FIELD_GROUPS",
    "FIELD_GROUP_COUNT",
    "GRANT_PROOF_KINDS",
    "ONCHAIN_KINDS",
    "QUANTITY_KEYS",
    "parse_ts",
    "validate_relation_record",
    "record_as_dict",
    "record_from_dict",
]


def parse_ts(value: str) -> datetime:
    """Parse an ISO-8601 timestamp into an aware UTC datetime.

    A naive timestamp is taken as UTC (the project convention); ``Z`` is
    accepted. Raises ``ValueError`` on anything else — no silent rounding.
    """
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _parse_or_none(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return parse_ts(value)
    except (ValueError, TypeError):
        return None


@dataclass(frozen=True)
class ChainRef:
    """On-chain anchor of a fact (B2 §3.1: PIT clock is the block)."""

    chain_id: int
    block: int
    tx_hash: str


@dataclass(frozen=True)
class RelationRecord:
    """The 17-field ORVYREN relation record (B2 §3.0).

    Attributes are grouped exactly as the numbered field groups of the spec
    (see :data:`RELATION_RECORD_FIELD_GROUPS`); a group with several members
    counts once (``src, dst, src_kind, dst_kind`` is field 4).
    """

    # 1 — identity.
    relation_id: str
    # 2 / 3 — catalogue placement.
    family: str
    kind: str
    # 4 — typed references.
    src: str = ""
    dst: str = ""
    src_kind: str = ""
    dst_kind: str = ""
    # 5 / 6 — mechanism and sign.
    mechanism: str = ""
    sign_prior: str = "ambigu"
    # 7 — activation predicates and scope.
    conditions: str = ""
    regime_scope: str = ""
    horizon_scope: str = ""
    # 8 / 9 / 10 — three attributes never to conflate.
    epistemic_status: str = "REPORTED"
    lifecycle: str = "DISCOVERED"
    validation_status: str = "PENDING"
    # 11 — world validity (nullable = open/unknown).
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    # 12 — system time (append-only store).
    revision: int = 1
    inserted_at: str = ""
    superseded_by: Optional[str] = None
    # 13 — provenance and source family (INV-DEPENDENCE).
    provenance_refs: Tuple[str, ...] = ()
    source_family_id: str = ""
    # 14 — extraction trace.
    extract_method: str = "HUMAN"
    model_version: str = ""
    run_id: str = ""
    # 15 — on-chain anchor.
    chain_ref: Optional[ChainRef] = None
    # 16 — confidence in [0, 1], documented method.
    confidence: float = 0.0
    # 17 — family-specific payload.
    payload: Mapping[str, Any] = field(default_factory=dict)


#: The 17 field groups of B2 §3.0, in order (a group counts once).
RELATION_RECORD_FIELD_GROUPS: Tuple[Tuple[str, ...], ...] = (
    ("relation_id",),                                        # 1
    ("family",),                                             # 2
    ("kind",),                                               # 3
    ("src", "dst", "src_kind", "dst_kind"),                  # 4
    ("mechanism",),                                          # 5
    ("sign_prior",),                                         # 6
    ("conditions", "regime_scope", "horizon_scope"),         # 7
    ("epistemic_status",),                                   # 8
    ("lifecycle",),                                          # 9
    ("validation_status",),                                  # 10
    ("valid_from", "valid_to"),                              # 11
    ("revision", "inserted_at", "superseded_by"),            # 12
    ("provenance_refs", "source_family_id"),                 # 13
    ("extract_method", "model_version", "run_id"),           # 14
    ("chain_ref",),                                          # 15
    ("confidence",),                                         # 16
    ("payload",),                                            # 17
)

FIELD_GROUP_COUNT = 17

#: Family 4 kinds that must carry a grant proof (B2 §3.1: "toujours porter la
#: preuve d'octroi (event/ref)").
GRANT_PROOF_KINDS = frozenset({"AUTHORIZES", "REVOKES", "MEMBER_OF", "ALLOWS"})

#: Kinds whose facts are on-chain by construction (need chain_ref).
ONCHAIN_KINDS = frozenset({"MEMBER_OF"})  # B2 §3.2: "fait on-chain `AssignRoles`"

#: Payload keys that denote a quantity (family 2 golden rule: a quantity
#: without unit/date is invalid).
QUANTITY_KEYS = frozenset({"amount", "quantity", "montant", "weight", "poids",
                          "ltv", "lt", "supply_cap", "value"})

_MECHANISM_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def record_as_dict(record: RelationRecord) -> Dict[str, Any]:
    """Plain-dict view of a record (fingerprintable, nested chain_ref kept)."""
    out: Dict[str, Any] = {}
    for f in fields(record):
        value = getattr(record, f.name)
        if f.name == "chain_ref" and value is not None:
            value = {"chain_id": value.chain_id, "block": value.block,
                     "tx_hash": value.tx_hash}
        elif f.name == "provenance_refs":
            value = list(value)
        elif f.name == "payload":
            value = dict(value)
        out[f.name] = value
    return out


def record_from_dict(data: Mapping[str, Any]) -> RelationRecord:
    """Build a record from :func:`record_as_dict` output (fixtures, exports)."""
    chain = data.get("chain_ref")
    return RelationRecord(
        relation_id=data["relation_id"],
        family=data["family"],
        kind=data["kind"],
        src=data.get("src", ""),
        dst=data.get("dst", ""),
        src_kind=data.get("src_kind", ""),
        dst_kind=data.get("dst_kind", ""),
        mechanism=data.get("mechanism", ""),
        sign_prior=data.get("sign_prior", "ambigu"),
        conditions=data.get("conditions", ""),
        regime_scope=data.get("regime_scope", ""),
        horizon_scope=data.get("horizon_scope", ""),
        epistemic_status=data.get("epistemic_status", "REPORTED"),
        lifecycle=data.get("lifecycle", "DISCOVERED"),
        validation_status=data.get("validation_status", "PENDING"),
        valid_from=data.get("valid_from"),
        valid_to=data.get("valid_to"),
        revision=int(data.get("revision", 1)),
        inserted_at=data.get("inserted_at", ""),
        superseded_by=data.get("superseded_by"),
        provenance_refs=tuple(data.get("provenance_refs", ())),
        source_family_id=data.get("source_family_id", ""),
        extract_method=data.get("extract_method", "HUMAN"),
        model_version=data.get("model_version", ""),
        run_id=data.get("run_id", ""),
        chain_ref=ChainRef(**chain) if chain else None,
        confidence=float(data.get("confidence", 0.0)),
        payload=dict(data.get("payload", {})),
    )


def validate_relation_record(record: RelationRecord) -> Tuple[str, ...]:
    """Conformance check of a record against the catalogue.

    Returns rejection codes (``E_*``); an empty tuple means conform. Codes are
    stable identifiers — tests and the validation gate key on them.
    """
    errors = []

    def reject(code: str) -> None:
        errors.append(code)

    # -- Catalogue placement (fields 2, 3).
    spec = RELATION_CATALOG.get(record.kind)
    if spec is None:
        reject("E_KIND_UNKNOWN")
    else:
        if record.family != spec.family:
            reject("E_FAMILY_MISMATCH")
        # -- Typed references (field 4): subject/object kinds.
        if record.src_kind not in KIND_CLASS:
            reject("E_SRC_KIND_UNKNOWN")
        elif not any(token_matches(token, record.src_kind) for token in spec.subjects):
            reject("E_SRC_KIND_NOT_ALLOWED")
        if record.dst_kind not in KIND_CLASS:
            reject("E_DST_KIND_UNKNOWN")
        elif not any(token_matches(token, record.dst_kind) for token in spec.objects):
            reject("E_DST_KIND_NOT_ALLOWED")
        # SUPERSEDES: "toute entité → même type (révision précédente)".
        if record.kind == "SUPERSEDES" and record.src_kind != record.dst_kind:
            reject("E_SUPERSEDES_KIND_MISMATCH")

    # -- Enums (fields 6, 8, 9, 10, 14).
    if record.sign_prior not in SIGN_PRIOR:
        reject("E_SIGN_PRIOR_UNKNOWN")
    if record.epistemic_status not in EPISTEMIC_STATUS:
        reject("E_EPISTEMIC_STATUS_UNKNOWN")
    if record.lifecycle not in LIFECYCLE:
        reject("E_LIFECYCLE_UNKNOWN")
    if record.validation_status not in VALIDATION_STATUS:
        reject("E_VALIDATION_STATUS_UNKNOWN")
    if record.extract_method not in EXTRACT_METHOD:
        reject("E_EXTRACT_METHOD_UNKNOWN")
    if record.extract_method == "LLM_EXTRACT" and not (
            record.model_version and record.run_id):
        reject("E_LLM_EXTRACT_UNVERSIONED")

    # -- Mechanism label (field 5): non-empty upper-case label (B2 §3.0 cell
    #    is open-ended, so the vocabulary is documented, not closed).
    if not record.mechanism or not _MECHANISM_RE.match(record.mechanism):
        reject("E_MECHANISM_LABEL")

    # -- Family 3 golden rule (B2 §3.1): conditions and horizon are mandatory.
    if spec is not None and spec.family == FAMILY_MECHANISM:
        if not record.conditions.strip():
            reject("E_MECHANISM_CONDITIONS_MISSING")
        if not record.horizon_scope.strip():
            reject("E_MECHANISM_HORIZON_MISSING")

    # -- CORRELATES_WITH: "statut STATISTICAL obligatoire, jamais causal".
    if record.kind == "CORRELATES_WITH" and record.epistemic_status != "STATISTICAL":
        reject("E_CORRELATION_NOT_STATISTICAL")

    # -- Family 2 golden rule (B2 §3.1): a quantity without unit/date is
    #    invalid. Any numeric payload value is a quantity.
    if spec is not None and spec.family == FAMILY_STRUCTURE:
        has_quantity = any(isinstance(v, (int, float)) and not isinstance(v, bool)
                           for v in record.payload.values())
        if has_quantity:
            if "unit" not in record.payload or not record.payload.get("unit"):
                reject("E_QUANTITY_NO_UNIT")
            dated = bool(record.payload.get("as_of") or record.payload.get("date")
                         or record.valid_from)
            if not dated:
                reject("E_QUANTITY_NO_DATE")

    # -- Family 4 golden rule (B2 §3.1): always carry the grant proof.
    if record.kind in GRANT_PROOF_KINDS:
        if not record.provenance_refs and record.chain_ref is None:
            reject("E_NO_GRANT_PROOF")

    # -- On-chain facts need their chain anchor (B2 §3.1 clock = block).
    if record.kind in ONCHAIN_KINDS and record.chain_ref is None:
        reject("E_ONCHAIN_NO_CHAIN_REF")

    # -- Confidence (field 16) in [0, 1].
    if isinstance(record.confidence, bool) or not isinstance(
            record.confidence, (int, float)) or not 0.0 <= float(record.confidence) <= 1.0:
        reject("E_CONFIDENCE_RANGE")

    # -- Identity and system time (fields 1, 12).
    if not record.relation_id.strip():
        reject("E_RELATION_ID_EMPTY")
    if record.revision < 1:
        reject("E_REVISION_RANGE")
    if not record.inserted_at.strip():
        reject("E_INSERTED_AT_EMPTY")
    elif _parse_or_none(record.inserted_at) is None:
        reject("E_INSERTED_AT_UNPARSABLE")

    # -- Clocks (field 11): parseable ISO-8601 and a correctly ordered
    #    world-validity interval (null ends = open/unknown, B2 §1.3).
    if record.valid_from is not None and _parse_or_none(record.valid_from) is None:
        reject("E_VALID_FROM_UNPARSABLE")
    if record.valid_to is not None and _parse_or_none(record.valid_to) is None:
        reject("E_VALID_TO_UNPARSABLE")
    valid_from_ts = _parse_or_none(record.valid_from)
    valid_to_ts = _parse_or_none(record.valid_to)
    if valid_from_ts is not None and valid_to_ts is not None and valid_from_ts >= valid_to_ts:
        reject("E_VALIDITY_ORDER")

    # -- Direction/symmetry bookkeeping (B2 §3.2 "Sens"): a symmetric kind is
    #    stored once per unordered pair — src <= dst keeps the store dedupable.
    if spec is not None and spec.direction == SYMMETRIC and record.src > record.dst:
        reject("E_SYMMETRIC_ORDER")

    return tuple(errors)
