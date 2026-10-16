#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — bounded action catalogues: 8 DAO + 4 desk (W3 lot L3.5).

Spec: B3_DECISION_ETUDE.md §d.2-d.4 (DOC2 §5.4.5). An action is never a free
order — it is a **bounded intent** (asset, amount, destination, function,
expiration) that the policy may refuse. Every action carries its template:
epistemic trigger, economic trigger, bounds, cost, expected effect and
applicability ("exécutable on-chain" or "simulée" — demonstration honesty).
No action opens new exposure during a stress episode (reduce / convert /
repay / withdraw only — the bound the policy service can verify).

The catalogue DATA lives in ``config/actions_v1.yaml`` — the source of truth of
the parameters, loaded with the strict stdlib mini-YAML reader of W4
(``orvyren.policy.miniyaml``). This module carries the semantics: closed
applicability enum, per-action applicability check, bounded sizing, template
validation. The catalogue is versioned and executions cite the version
(INV-AUTH). Fail-closed: any template violation raises — a malformed action
never enters the catalogue.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from orvyren.policy.miniyaml import load_file as _load_yaml_file

CATALOG_VERSION = "catalog/v1"
CATALOG_SCHEMA = "orvyren-actions-catalog/v1"

DAO_PERSONA = "DAO"
DESK_PERSONA = "desk"

APPLICABILITY_ON_CHAIN = "on-chain"
APPLICABILITY_SIMULATED = "simulated"
APPLICABILITY_ESCALATE = "escalate (pas une action de l'agent)"
APPLICABILITY_DEFAULT = "default (état par défaut)"

#: The closed applicability enum — never a free string.
APPLICABILITY_LABELS = (APPLICABILITY_ON_CHAIN, APPLICABILITY_SIMULATED,
                        APPLICABILITY_ESCALATE, APPLICABILITY_DEFAULT)

_HERE = os.path.dirname(os.path.abspath(__file__))
#: The parameter file (repo root / config / actions_v1.yaml).
DEFAULT_CATALOG_PATH = os.path.normpath(
    os.path.join(_HERE, "..", "..", "..", "config", "actions_v1.yaml"))

_REQUIRED_FIELDS = ("action_id", "persona", "name", "epistemic_trigger",
                    "economic_trigger", "bounds", "cost", "expected_effect",
                    "applicability", "precedent")


@dataclass(frozen=True)
class ActionRecord:
    """One bounded action of a persona catalogue (B3 §d.2/d.3 template)."""

    action_id: str
    persona: str
    name: str
    epistemic_trigger: str
    economic_trigger: str
    bounds: str
    cost: str
    expected_effect: str
    applicability: str
    precedent: str
    version: str = CATALOG_VERSION


def load_catalog(path: Optional[str] = None) -> Tuple[ActionRecord, ...]:
    """Load ``config/actions_v1.yaml`` — the parameter source of truth.

    Fail-closed: bad schema/version, empty template field, unknown
    applicability, persona mismatch, duplicate id or broken 8+4 counts all
    raise ``ValueError`` with an explicit code.
    """
    data = _load_yaml_file(path or DEFAULT_CATALOG_PATH)
    if not isinstance(data, dict):
        raise ValueError("E_CATALOG_ROOT_NOT_A_MAPPING")
    schema = str(data.get("schema") or "")
    if schema != CATALOG_SCHEMA:
        raise ValueError("E_CATALOG_SCHEMA:%s" % schema)
    version = str(data.get("catalog_version") or "").strip()
    if version != CATALOG_VERSION:
        raise ValueError("E_CATALOG_VERSION:%s" % version)

    records: List[ActionRecord] = []
    seen = set()
    for section, persona in (("persona_dao", DAO_PERSONA),
                             ("persona_desk", DESK_PERSONA)):
        entries = data.get(section)
        if not isinstance(entries, list):
            raise ValueError("E_CATALOG_SECTION:%s" % section)
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ValueError("E_CATALOG_ENTRY:%s[%d]" % (section, index))
            missing = [field for field in _REQUIRED_FIELDS
                       if not str(entry.get(field, "")).strip()]
            if missing:
                raise ValueError("E_CATALOG_FIELD_MISSING:%s[%d]:%s"
                                 % (section, index, ",".join(missing)))
            record = ActionRecord(
                action_id=str(entry["action_id"]).strip(),
                persona=str(entry["persona"]).strip(),
                name=str(entry["name"]).strip(),
                epistemic_trigger=str(entry["epistemic_trigger"]).strip(),
                economic_trigger=str(entry["economic_trigger"]).strip(),
                bounds=str(entry["bounds"]).strip(),
                cost=str(entry["cost"]).strip(),
                expected_effect=str(entry["expected_effect"]).strip(),
                applicability=str(entry["applicability"]).strip(),
                precedent=str(entry["precedent"]).strip(),
                version=version,
            )
            if record.persona != persona:
                raise ValueError("E_CATALOG_PERSONA:%s:%s"
                                 % (record.action_id, record.persona))
            if record.applicability not in APPLICABILITY_LABELS:
                raise ValueError("E_CATALOG_APPLICABILITY:%s:%s"
                                 % (record.action_id, record.applicability))
            if record.action_id in seen:
                raise ValueError("E_CATALOG_DUPLICATE_ID:%s" % record.action_id)
            seen.add(record.action_id)
            records.append(record)

    dao = [r for r in records if r.persona == DAO_PERSONA]
    desk = [r for r in records if r.persona == DESK_PERSONA]
    if len(dao) != 8 or len(desk) != 4:
        raise ValueError("E_CATALOG_COUNTS:dao=%d,desk=%d" % (len(dao), len(desk)))
    return tuple(records)


#: The versioned catalogue (loaded from ``config/actions_v1.yaml`` at import).
CATALOG: Tuple[ActionRecord, ...] = load_catalog()
DAO_ACTIONS: Tuple[ActionRecord, ...] = tuple(a for a in CATALOG
                                              if a.persona == DAO_PERSONA)
DESK_ACTIONS: Tuple[ActionRecord, ...] = tuple(a for a in CATALOG
                                               if a.persona == DESK_PERSONA)


def catalog_for(persona: str) -> Tuple[ActionRecord, ...]:
    if persona == DAO_PERSONA:
        return DAO_ACTIONS
    if persona == DESK_PERSONA:
        return DESK_ACTIONS
    raise ValueError("E_PERSONA_UNKNOWN: %r" % persona)


def bounded_size(x_max: float, depth_eps: float, x_threshold: float) -> float:
    """x* = min(x_max_rôle, profondeur d'exécution mesurée, taille au seuil
    économique) — B3 §d.1. Never negative."""
    return max(0.0, min(x_max, depth_eps, x_threshold))


def check_applicability(record: ActionRecord,
                        context: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Per-action applicability check in a given context.

    Returns ``{"applicable": bool, "motif": str, "action": record}`` — never
    raises: an inapplicable action is decision information, not a system error.
    """
    context = context or {}
    if record.applicability == APPLICABILITY_ESCALATE:
        return {"applicable": False, "action": record,
                "motif": "escalade humaine — jamais une action de l'agent (B3 §d.4)"}
    if (record.applicability == APPLICABILITY_SIMULATED
            and not context.get("allow_simulation")):
        return {"applicable": False, "action": record,
                "motif": "simulée hors enveloppe — jamais exécutée sans opt-in déclaré"}
    if (record.applicability == APPLICABILITY_ON_CHAIN
            and context.get("abstentions_actives")):
        return {"applicable": False, "action": record,
                "motif": "conditions d'abstention actives — levées d'abord (DOC2 §5.4.5)"}
    return {"applicable": True, "action": record, "motif": "applicable"}


def validate_catalog(catalog: Sequence[ActionRecord] = CATALOG) -> List[str]:
    """Template completeness (used by the test bench): every field present."""
    problems = []
    required = ("action_id", "persona", "name", "epistemic_trigger",
                "economic_trigger", "bounds", "cost", "expected_effect",
                "applicability", "precedent")
    for action in catalog:
        for field_name in required:
            if not str(getattr(action, field_name)).strip():
                problems.append("%s: empty %s" % (action.action_id, field_name))
        if action.version != CATALOG_VERSION:
            problems.append("%s: version mismatch %s" % (action.action_id, action.version))
        if action.applicability not in APPLICABILITY_LABELS:
            problems.append("%s: unknown applicability %s"
                            % (action.action_id, action.applicability))
    return problems


def records_as_dicts(catalog: Sequence[ActionRecord] = CATALOG) -> List[Dict]:
    return [
        {"action_id": a.action_id, "persona": a.persona, "name": a.name,
         "epistemic_trigger": a.epistemic_trigger,
         "economic_trigger": a.economic_trigger, "bounds": a.bounds,
         "cost": a.cost, "expected_effect": a.expected_effect,
         "applicability": a.applicability, "precedent": a.precedent,
         "version": a.version}
        for a in catalog
    ]
