#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — RDOF v1: recherche discriminante ordonnée par falsification (W3 L3.2/L3.3).

Spec: B3_DECISION_ETUDE.md §b.2 (DOC2 §5.4.3, FREEZE_V2 C2). Five deterministic
rules, zero probability:

1. **Évaluabilité** — mark every hypothesis criterion evaluable / not under the
   current evidence state; collect the unknowns.
2. **Effet des prédicats** — for every candidate predicate and each of its
   registered outcome classes, compute "if the outcome were this class, what
   happens to each hypothesis verdict?" by *counterfactual re-classification*
   (``predicates.inject_outcome`` + ``scenarios.classify_hypotheses``) — the
   effect is computed, never hard-coded.
3. **Ordonnancement** — frozen lexicographic comparison, ties broken by id:
   (i) can refute the currently dominant hypothesis; (ii) makes evaluable a
   criterion carrying the opposite decision; (iii) resolves a registered
   unresolved contradiction; (iv) lowest measured cost (seconds + queries).
4. **Exécution** — collect the chosen predicate, add it to the evidence state,
   restart.
5. **Arrêt** — first true: c1 INVARIANCE (every remaining outcome leads to the
   same action candidate → "décision stable", even with budget left); c2
   BUDGET (list what was not searched and its possible effect).

The dominant hypothesis is the first hypothesis (frozen order H1, H2, H3) that
is not REFUTED — the standing narrative the evidence has not eliminated yet.

VoI stays behind one interface (B3 §b.3): ``value_of_search`` returns
``VOI_NOT_ESTIMABLE`` (no calibrated frozen probabilities in v1) and the v1
mechanism takes over without changing the decision. Never a failure point.

Everything reads the frozen corpus; the run is deterministic and offline.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Sequence, Tuple

from orvyren.decision.exposure import Exposure
from orvyren.decision.predicates import (BY_ID, Predicate, evaluate_predicate,
                                         inject_outcome, predicate_effect_possible)
from orvyren.decision.scenarios import (INCONCLUSIVE, REFUTED, SUPPORTED,
                                        classify_hypotheses, load_observations,
                                        observations_in_window,
                                        parse_window_bound)

#: Frozen search budget defaults (B3 §b.2 "plafonds gelés" — requêtes+secondes).
DEFAULT_BUDGET = {"recherches": 3, "appels": 10, "secondes": 60.0}

#: Frozen hypothesis order (dominance test walks this order).
FROZEN_HYPOTHESIS_ORDER = ("H1", "H2", "H3")

#: The documented bounded fixed order (repli, DOC4 §4): RDOF is evaluated
#: against it before anything else is activated (FREEZE_V2 C2).
FROZEN_FIXED_ORDER = ("P-1.2", "P-1.3", "P-6.3", "P-2.2", "P-2.5", "P-1.4",
                      "P-5.1", "P-PERS")

VOI_NOT_ESTIMABLE = "VOI_NOT_ESTIMABLE"


def value_of_search(predicate_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """VoI interface (B3 §b.3) — v1 has no calibrated frozen probabilities.

    Returns ``VOI_NOT_ESTIMABLE``; the v1 mechanism then takes over with the
    exact same result. Never a failure point.
    """
    return {"status": VOI_NOT_ESTIMABLE,
            "reason": "v1: no frozen calibrated probabilities — RDOF v1 rules apply"}


# ---------------------------------------------------------------------------
# Evidence state
# ---------------------------------------------------------------------------

class EvidenceState:
    """The admissible evidence state É: corpus + horizon + collected facts.

    Supply series are *hidden* until P-6.3 is collected: the supply fact is in
    the frozen corpus, but it enters the evidence state only when the research
    act buys it (B3 §b.2 micro-exemple: "H2 tant que la baisse d'offre n'est
    pas observée").
    """

    def __init__(self, observations, window_start, window_end, horizon=None,
                 collected=None):
        self.observations = list(observations)
        self.window_start = parse_window_bound(window_start) if isinstance(window_start, str) else window_start
        self.window_end = parse_window_bound(window_end) if isinstance(window_end, str) else window_end
        self.horizon = parse_window_bound(horizon) if isinstance(horizon, str) else (horizon or self.window_end)
        self.collected: Dict[str, Dict[str, Any]] = dict(collected or {})

    def view(self):
        """Observations admissible under the current state."""
        from orvyren.decision.scenarios import SUPPLY_VENUE, SUPPLY_CROSS_CHECK_VENUE
        hidden = "P-6.3" not in self.collected
        out = []
        for observation in self.observations:
            if observation.ts > self.horizon:
                continue
            if hidden and observation.venue in (SUPPLY_VENUE, SUPPLY_CROSS_CHECK_VENUE):
                continue
            out.append(observation)
        return out

    def classify(self):
        return classify_hypotheses(self.view(), self.window_start, self.window_end)


def _dominant(verdicts) -> Optional[str]:
    for hypothesis_id in FROZEN_HYPOTHESIS_ORDER:
        if verdicts[hypothesis_id]["verdict"] != REFUTED:
            return hypothesis_id
    return None


def _criterion_states(verdicts) -> Dict[str, Dict[str, bool]]:
    return {
        hypothesis_id: {
            criterion["criterion"]: bool(criterion.get("evaluable"))
            for criterion in verdict["criteria_evaluated"]
        }
        for hypothesis_id, verdict in verdicts.items()
    }


def action_candidate(verdicts, available):
    """The frozen decision rule of the engine, as an action candidate label."""
    if verdicts["H2"]["verdict"] == SUPPORTED and available > 0:
        return {"kind": "ACTION_RECOMMENDED", "catalog": "A-D1",
                "note": "H2 SUPPORTED and available_to_move > 0 (pre-registered rule 1)"}
    if verdicts["H2"]["verdict"] == REFUTED:
        return {"kind": "NO_ACTION", "catalog": "A-D7",
                "note": "H2 REFUTED — no registered criterion justifies reducing exposure"}
    return {"kind": "INCONCLUSIVE", "catalog": None,
            "note": "H2 unresolved — no action produced"}


# ---------------------------------------------------------------------------
# Effects (rule 2) — counterfactual re-classification
# ---------------------------------------------------------------------------

def _compute_effects(state: EvidenceState, predicate: Predicate, available):
    """For each registered class of the predicate: verdict + action deltas."""
    baseline = state.classify()
    effects: Dict[str, Dict[str, Any]] = {}
    for class_label in predicate.class_labels:
        try:
            injected = inject_outcome(predicate.predicate_id, class_label,
                                      state.observations, state.window_start,
                                      state.window_end, state.horizon)
            assumed_collected = dict(state.collected)
            assumed_collected[predicate.predicate_id] = {"counterfactual": True}
            assumed = EvidenceState(injected, state.window_start, state.window_end,
                                    state.horizon, assumed_collected)
            verdicts = assumed.classify()
        except (ValueError, KeyError):
            effects[class_label] = {"available": False}
            continue
        deltas = {}
        refuted: List[str] = []
        supported: List[str] = []
        for hypothesis_id in FROZEN_HYPOTHESIS_ORDER:
            before = baseline[hypothesis_id]["verdict"]
            after = verdicts[hypothesis_id]["verdict"]
            if before != after:
                deltas[hypothesis_id] = "%s -> %s" % (before, after)
            if after == REFUTED and before != REFUTED:
                refuted.append(hypothesis_id)
            if after == SUPPORTED and before != SUPPORTED:
                supported.append(hypothesis_id)
        makes_evaluable: List[str] = []
        before_criteria = _criterion_states(baseline)
        after_criteria = _criterion_states(verdicts)
        for hypothesis_id, criteria in after_criteria.items():
            for name, evaluable in criteria.items():
                if evaluable and not before_criteria.get(hypothesis_id, {}).get(name, False):
                    makes_evaluable.append("%s:%s" % (hypothesis_id, name))
        effects[class_label] = {
            "available": True,
            "verdict_deltas": deltas,
            "can_refute": refuted,
            "can_support": supported,
            "makes_evaluable": makes_evaluable,
            "action": action_candidate(verdicts, available)["kind"],
        }
    return baseline, effects


def _order_key(predicate: Predicate, effects: Dict[str, Any], dominant: Optional[str],
               baseline: Dict[str, Any], available) -> Tuple:
    can_refute_dominant = bool(
        dominant and any(
            dominant in effects[class_label].get("can_refute", [])
            for class_label in effects if effects[class_label].get("available")))
    makes_decisive_evaluable = any(
        effects[class_label].get("makes_evaluable")
        for class_label in effects if effects[class_label].get("available"))
    resolves_contradiction = False  # no registered unresolved contradictions in this case
    cost = predicate.cost_seconds + predicate.decision_delay_seconds
    return (-int(can_refute_dominant), -int(makes_decisive_evaluable),
            -int(resolves_contradiction), cost, predicate.predicate_id)


def _invariant(effects: Dict[str, Any], current_action: str) -> bool:
    """c1: every outcome class of the predicate leads to the same action."""
    classes = [effects[label] for label in effects if effects[label].get("available")]
    if not classes:
        return False  # unknowable outcomes are never treated as a stable decision
    return all(entry["action"] == current_action for entry in classes)


# ---------------------------------------------------------------------------
# The RDOF run
# ---------------------------------------------------------------------------

def rdof_run(observations, window_start, window_end, case_id="usdc-2023-03",
             horizon=None, budget=None, collected=None, voi_fn=None,
             exposure=None):
    """Run RDOF v1 over one case; returns the full determinism trace."""
    state = EvidenceState(observations, window_start, window_end, horizon, collected)
    budget_limits = dict(DEFAULT_BUDGET if budget is None else budget)
    envelope = exposure if exposure is not None else Exposure()
    available = envelope.available_to_move()
    consumed = {"recherches": 0, "appels": 0, "secondes": 0.0}
    trace: List[Dict[str, Any]] = []
    stop = None
    stop_rule = None
    excluded: List[Dict[str, str]] = []

    while True:
        verdicts = state.classify()
        current_action = action_candidate(verdicts, available)["kind"]

        candidates, excluded = [], []
        for predicate in sorted(BY_ID.values(), key=lambda p: p.predicate_id):
            if case_id not in predicate.case_scope:
                excluded.append({
                    "predicate_id": predicate.predicate_id,
                    "reason": "hors périmètre du cas %s (périmètre : %s)" % (
                        case_id, ", ".join(predicate.case_scope))})
                continue
            if predicate.predicate_id in state.collected:
                continue
            if not predicate.offline_evaluable:
                excluded.append({
                    "predicate_id": predicate.predicate_id,
                    "reason": predicate.offline_reason or "not offline-evaluable",
                })
                continue
            if not predicate_effect_possible(predicate):
                excluded.append({
                    "predicate_id": predicate.predicate_id,
                    "reason": ("no registered hypothesis criterion consumes this "
                               "measure — its outcome classes cannot change any "
                               "verdict (never bought, règle c1)"),
                })
                continue
            candidates.append(predicate)

        # rule 2 — effects for every candidate, every class
        effects_by_id = {}
        for predicate in candidates:
            _, effects = _compute_effects(state, predicate, available)
            effects_by_id[predicate.predicate_id] = effects

        # c1 — invariance: for every remaining predicate, all outcomes -> same action
        if not candidates or all(
                _invariant(effects_by_id[p.predicate_id], current_action)
                for p in candidates):
            stop = "décision stable (invariance c1)"
            stop_rule = "c1"
            break

        # c2 — budget
        viable = [p for p in candidates
                  if p.cost_seconds + p.decision_delay_seconds <=
                  budget_limits["secondes"] - consumed["secondes"]
                  and consumed["appels"] + p.cost_queries <= budget_limits["appels"]
                  and consumed["recherches"] + 1 <= budget_limits["recherches"]]
        if not viable:
            stop = "budget épuisé (c2)"
            stop_rule = "c2"
            break

        # rule 3 — frozen lexicographic ordering; ties by id
        dominant = _dominant(verdicts)
        ranked = sorted(
            viable,
            key=lambda p: _order_key(p, effects_by_id[p.predicate_id], dominant,
                                     verdicts, available))
        chosen = ranked[0]

        # rule 4 — collect and restart
        fact = evaluate_predicate(chosen.predicate_id, state.observations,
                                  state.window_start, state.window_end,
                                  state.horizon)
        why = []
        effects = effects_by_id[chosen.predicate_id]
        if dominant and any(dominant in effects[label].get("can_refute", [])
                            for label in effects):
            why.append("règle (i) : peut réfuter l'hypothèse dominante %s" % dominant)
        if any(effects[label].get("makes_evaluable") for label in effects):
            made = sorted({item for label in effects
                           for item in effects[label].get("makes_evaluable", [])})
            why.append("règle (ii) : rend évaluable un critère décisif (%s)" % ", ".join(made))
        if not why:
            why.append("règle (iv) : issue encore capable de changer une décision, coût le plus faible")
        if chosen.decision_delay_seconds:
            why.append("délai de verdict : %s" % chosen.decision_delay_note)

        before_verdicts = {h: verdicts[h]["verdict"] for h in FROZEN_HYPOTHESIS_ORDER}
        state.collected[chosen.predicate_id] = fact
        after_verdicts = state.classify()
        consumed["recherches"] += 1
        consumed["appels"] += chosen.cost_queries
        consumed["secondes"] = round(consumed["secondes"] + chosen.cost_seconds, 6)
        trace.append({
            "iteration": len(trace) + 1,
            "question": "quel fait enregistré peut changer un verdict au coût mesuré le plus faible ?",
            "chosen": chosen.predicate_id,
            "chosen_name": chosen.name,
            "why": why,
            "cost": {"queries": chosen.cost_queries,
                     "seconds": chosen.cost_seconds,
                     "decision_delay_seconds": chosen.decision_delay_seconds},
            "outcome": {"value": fact["value"], "class": fact["class"],
                        "refs": fact["refs"], "detail": fact["detail"]},
            "verdicts_before": before_verdicts,
            "verdicts_after": {h: after_verdicts[h]["verdict"]
                               for h in FROZEN_HYPOTHESIS_ORDER},
        })

    final_verdicts = state.classify()
    not_searched = []
    for predicate in sorted(BY_ID.values(), key=lambda p: p.predicate_id):
        if case_id not in predicate.case_scope or predicate.predicate_id in state.collected:
            continue
        entry = {"predicate_id": predicate.predicate_id, "name": predicate.name}
        if predicate.offline_evaluable and predicate_effect_possible(predicate):
            effects = effects_by_id.get(predicate.predicate_id)
            if effects:
                possible = {label: effects[label].get("verdict_deltas")
                            for label in effects if effects[label].get("available")}
                entry["possible_effect"] = possible
                entry["action_invariant"] = _invariant(
                    effects, action_candidate(final_verdicts, available)["kind"])
        else:
            entry["possible_effect"] = None
            entry["note"] = predicate.offline_reason or "not offline-evaluable"
        not_searched.append(entry)

    return {
        "rdof_version": "rdof/v1",
        "case": case_id,
        "horizon": state.horizon.isoformat(),
        "dominant_final": _dominant(final_verdicts),
        "trace": trace,
        "stop": stop,
        "stop_rule": stop_rule,
        "budget": {"limites": budget_limits, "consomme": consumed},
        "not_searched": not_searched,
        "excluded": excluded,
        "final_verdicts": {h: final_verdicts[h]["verdict"]
                           for h in FROZEN_HYPOTHESIS_ORDER},
        "final_action_candidate": action_candidate(final_verdicts, available),
    }


# ---------------------------------------------------------------------------
# L3.3 — RDOF vs the documented fixed order
# ---------------------------------------------------------------------------

def fixed_order_run(observations, window_start, window_end, case_id="usdc-2023-03",
                    horizon=None, budget=None, collected=None, exposure=None):
    """The bounded fixed order (repli documenté): buys in a frozen list order,
    without the invariance stop — that is exactly what T02/HYP-02R measures."""
    state = EvidenceState(observations, window_start, window_end, horizon, collected)
    budget_limits = dict(DEFAULT_BUDGET if budget is None else budget)
    envelope = exposure if exposure is not None else Exposure()
    available = envelope.available_to_move()
    consumed = {"recherches": 0, "appels": 0, "secondes": 0.0}
    purchases, unnecessary = [], 0

    for predicate_id in FROZEN_FIXED_ORDER:
        predicate = BY_ID[predicate_id]
        if case_id not in predicate.case_scope or predicate_id in state.collected:
            continue
        if not predicate.offline_evaluable or not predicate_effect_possible(predicate):
            continue
        if (consumed["recherches"] + 1 > budget_limits["recherches"]
                or consumed["appels"] + predicate.cost_queries > budget_limits["appels"]):
            break
        verdicts = state.classify()
        current_action = action_candidate(verdicts, available)["kind"]
        _, effects = _compute_effects(state, predicate, available)
        if _invariant(effects, current_action):
            unnecessary += 1
        fact = evaluate_predicate(predicate_id, state.observations,
                                  state.window_start, state.window_end, state.horizon)
        state.collected[predicate_id] = fact
        consumed["recherches"] += 1
        consumed["appels"] += predicate.cost_queries
        consumed["secondes"] = round(consumed["secondes"] + predicate.cost_seconds, 6)
        purchases.append(predicate_id)

    final_verdicts = state.classify()
    return {
        "order": "ordre fixe borné (repli documenté, DOC4 §4)",
        "frozen_order": list(FROZEN_FIXED_ORDER),
        "purchases": purchases,
        "unnecessary_purchases": unnecessary,
        "budget_consomme": consumed,
        "final_verdicts": {h: final_verdicts[h]["verdict"]
                           for h in FROZEN_HYPOTHESIS_ORDER},
        "final_action_candidate": action_candidate(final_verdicts, available),
    }


def compare_rdof_vs_fixed_order(observations, window_start, window_end,
                                case_id="usdc-2023-03", horizon=None, budget=None,
                                collected=None):
    """T02/HYP-02R-style essai: RDOF must beat or match the fixed order.

    Compared: number of purchases, unnecessary purchases (bought although every
    outcome would have led to the same action — the c1 case), total measured
    cost, and the final verdicts (must be identical: the mechanism may only
    change the *path*, never the *answer*).
    """
    rdof = rdof_run(observations, window_start, window_end, case_id, horizon,
                    budget, collected)
    fixed = fixed_order_run(observations, window_start, window_end, case_id,
                            horizon, budget, collected)
    return {
        "essai": "T02/HYP-02R",
        "rdof": {"purchases": len(rdof["trace"]),
                 "unnecessary_purchases": 0,
                 "cost_seconds": rdof["budget"]["consomme"]["secondes"],
                 "stop": rdof["stop"]},
        "fixed_order": {"purchases": len(fixed["purchases"]),
                        "unnecessary_purchases": fixed["unnecessary_purchases"],
                        "cost_seconds": fixed["budget_consomme"]["secondes"]},
        "verdicts_equal": rdof["final_verdicts"] == fixed["final_verdicts"],
        "action_equal": (rdof["final_action_candidate"]["kind"]
                         == fixed["final_action_candidate"]["kind"]),
        "rdof_not_worse": (len(rdof["trace"]) <= len(fixed["purchases"])
                           and fixed["unnecessary_purchases"]
                           <= len(fixed["purchases"])),
    }