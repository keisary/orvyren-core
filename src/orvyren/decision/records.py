#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — registration of the falsifiable hypotheses (W3 lot L3.1).

Wires the decision onto the **W2 hypothesis registry**
(``orvyren.branches.hypotheses``): every case hypothesis is registered with
**mandatory S (support)** and **R (refutation)** criteria — never a silent
``p∅`` — and every criterion points at an **instrumented predicate** of the
catalogue (``predicates.BY_ID``). A number produced by an agent therefore never
triggers a criterion: a criterion that references no instrumented predicate is
**refused** (fail-closed, code ``E_SPEC_UNREGISTERED_PREDICATE``).

``p`` stays a frozen **ordinal label** (never a number); it is ``None`` until a
freeze has fixed it. The provenance date is the case freeze date (FREEZE_V2,
2026-10-15) — a constant, so the replay stays deterministic to the byte.

Standard library only.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from orvyren.branches.hypotheses import (Criterion, HypothesisRecord,
                                         HypothesisRegistry,
                                         validate_hypothesis)
from orvyren.decision.predicates import BY_ID

__all__ = [
    "FROZEN_HYPOTHESIS_ORDER",
    "REGISTRATION_DATE",
    "CRITERION_PREDICATES",
    "build_hypothesis_record",
    "register_case_hypotheses",
    "E_REG_NO_SUPPORT",
    "E_REG_NO_REFUTATION",
    "E_REG_UNREGISTERED_PREDICATE",
]

#: Frozen hypothesis order of the case (dominance walk order, B3 §b.2).
FROZEN_HYPOTHESIS_ORDER = ("H1", "H2", "H3")

#: Case freeze date (FREEZE_V2, 2026-10-15) — constant for replayability.
REGISTRATION_DATE = "2026-10-15T00:00:00Z"

E_REG_NO_SUPPORT = "E_SPEC_NO_SUPPORT_CRITERION"
E_REG_NO_REFUTATION = "E_SPEC_NO_REFUTATION_CRITERION"
E_REG_UNREGISTERED_PREDICATE = "E_SPEC_UNREGISTERED_PREDICATE"

#: Frozen criterion -> instrumented predicate mapping of the USDC case (B3 §b.2,
#: DOC2 §5.4.3): inter-venue dispersion, persistence, 24 h supply drop,
#: oracle/market divergence (two sources of distinct nature).
CRITERION_PREDICATES: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "H1": {"soutien": ("P-1.2", "P-PERS"), "refutation": ("P-PERS", "P-1.2")},
    "H2": {"soutien": ("P-1.2", "P-6.3"), "refutation": ("P-6.3", "P-1.2")},
    "H3": {"soutien": ("P-1.3",), "refutation": ("P-1.2",)},
}

_FENETRE = "case window (D1); 1 h step, H_class=6h (C6)"


def _resolve_predicates(hypothesis_id: str, side: str,
                        criteria_map: Mapping[str, Mapping[str, Sequence[str]]],
                        registered_predicates: Sequence[str]) -> Tuple[str, ...]:
    """Every predicate of a criterion must be instrumented (registry)."""
    ids = tuple(criteria_map.get(hypothesis_id, {}).get(side, ()))
    if not ids:
        raise ValueError("%s:%s" % (
            E_REG_NO_SUPPORT if side == "soutien" else E_REG_NO_REFUTATION,
            hypothesis_id))
    unknown = [p for p in ids if p not in registered_predicates]
    if unknown:
        raise ValueError("%s:%s:%s" % (E_REG_UNREGISTERED_PREDICATE, hypothesis_id,
                                       ",".join(unknown)))
    return ids


def build_hypothesis_record(verdict: Mapping[str, Any], case_id: str,
                            registered_predicates: Sequence[str],
                            criteria_map: Optional[Mapping[str, Mapping[str, Sequence[str]]]] = None,
                            date: str = REGISTRATION_DATE,
                            auteur: str = "decision-engine",
                            modele: str = "RDOF v1") -> HypothesisRecord:
    """Build the W2 registry record of one hypothesis from its verdict.

    The verdict (``scenarios.classify_hypotheses`` output) carries the
    pre-registered S/R specifications; the record carries them as registry
    criteria pointing at instrumented predicates. Raises ``ValueError`` when a
    criterion is missing or references a non-instrumented source.
    """
    hypothesis_id = str(verdict["hypothesis_id"])
    criteria_map = CRITERION_PREDICATES if criteria_map is None else criteria_map
    support_spec = str(verdict.get("support_criterion") or "").strip()
    refutation_spec = str(verdict.get("refutation_criterion") or "").strip()
    if not support_spec:
        raise ValueError("%s:%s" % (E_REG_NO_SUPPORT, hypothesis_id))
    if not refutation_spec:
        raise ValueError("%s:%s" % (E_REG_NO_REFUTATION, hypothesis_id))

    criteres = []
    for side, spec in (("soutien", support_spec), ("refutation", refutation_spec)):
        ids = _resolve_predicates(hypothesis_id, side, criteria_map,
                                  registered_predicates)
        sources = tuple(BY_ID[p].source for p in ids if p in BY_ID)
        criteres.append(Criterion(nom=side, predicat=", ".join(ids), seuil=spec,
                                  sources=sources or ("instrumented predicates",),
                                  fenetre=_FENETRE))
    record = HypothesisRecord(
        id="HYP-%s-%s" % (case_id.upper(), hypothesis_id),
        case_id=case_id,
        enonce=str(verdict.get("statement") or "").strip(),
        criteres=tuple(criteres),
        preuves_pour=(),
        preuves_contre=(),
        inconnues=tuple(str(item) for item in (verdict.get("missing_inputs") or ())),
        etat="CREATED",
        p=None,
        p_gel_ref="",
        histoire=(),
        provenance={"auteur": auteur, "modele": modele, "date": date},
        relations=(),
    )
    return record


def register_case_hypotheses(registry: HypothesisRegistry, case_id: str,
                             verdicts: Mapping[str, Mapping[str, Any]],
                             registered_predicates: Sequence[str],
                             criteria_map: Optional[Mapping[str, Mapping[str, Sequence[str]]]] = None,
                             date: str = REGISTRATION_DATE,
                             auteur: str = "decision-engine",
                             modele: str = "RDOF v1") -> Tuple[HypothesisRecord, ...]:
    """Validate and register every case hypothesis in the W2 registry.

    Any non-falsifiable hypothesis (missing S or R criterion, or a criterion
    not backed by an instrumented predicate) raises ``ValueError`` — never a
    silent ``p∅`` hypothesis in the registry.
    """
    records = []
    for hypothesis_id in FROZEN_HYPOTHESIS_ORDER:
        verdict = verdicts[hypothesis_id]
        record = build_hypothesis_record(verdict, case_id, registered_predicates,
                                         criteria_map, date, auteur, modele)
        errors = validate_hypothesis(record)
        if errors:
            raise ValueError("record %s: %s" % (record.id, ",".join(errors)))
        registry.create(record)
        records.append(record)
    return tuple(records)
