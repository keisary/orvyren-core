#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — abstention A1-A5, enriched INCONCLUSIVE format, ESCALATE vs NO-ACTION (W3 L3.4).

Spec: B3_DECISION_ETUDE.md §c.2-c.4 (DOC2 §5.4.4, FREEZE_V2 C3). Five
no-probability conditions; the enriched format makes abstention a **research
plan** ("what is missing, where to get it, what it would change") instead of a
mute refusal; the ESCALATE vs NO-ACTION decision is a deterministic table.

Structural note (B3 §c.2): A4 is an **authorization** abstention (axis 3),
never confused with A1-A3, which are **epistemic** (axis 1). "DENY de
politique" != "échec épistémique" ; "INCONCLUSIVE" != "NO-ACTION".
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

A1 = "A1 (entrée requise absente)"
A2 = "A2 (contradiction non résolue)"
A3 = "A3 (décision non identifiable sous budget)"
A4 = "A4 (hors enveloppe / politique)"
A5 = "A5 (convention de mesure ambiguë)"

CONDITION_CODES = {"A1": A1, "A2": A2, "A3": A3, "A4": A4, "A5": A5}


# ---------------------------------------------------------------------------
# A1-A5 detection (B3 §c.2 — each test is operational and probability-free)
# ---------------------------------------------------------------------------

def detect_conditions(verdicts, integrity_flags=(), rdof_result=None,
                      policy_verdict=None, convention_ambiguous=False):
    """Return the triggered abstention conditions with their evidence.

    - A1: any required input missing from any verdict (missing_inputs non-empty);
    - A2: unresolved contradiction — integrity flags (conflicting duplicate,
      non-positive value, non-UTC timestamp) or an unexplained divergence left
      open by H3's structural check;
    - A3: budget exhausted (RDOF stop c2) while >= 2 hypotheses survive;
    - A4: the preferred action violated the envelope or the policy
      (DENY / REQUIRE_APPROVAL) — an *authorization* condition;
    - A5: two admissible measurement readings give different verdicts.
    """
    triggered = []
    evidence: Dict[str, List[str]] = {}

    missing = sorted({item for verdict in verdicts.values()
                      for item in verdict.get("missing_inputs", [])})
    if missing:
        triggered.append("A1")
        evidence["A1"] = missing

    contradiction = []
    for flag in integrity_flags:
        contradiction.append("integrity flag: %s (%s)" % (
            flag.get("type"), flag.get("timestamp_utc")))
    h3 = verdicts.get("H3")
    if h3 is not None:
        computed = h3["criteria_evaluated"][0]["computed"]
        for divergence in computed.get("unexplained_divergences", []):
            contradiction.append(
                "unexplained divergence %s at %s (venue %s vs aggregator %s)" % (
                    divergence.get("venue"), divergence.get("timestamp_utc"),
                    divergence.get("venue_value"), divergence.get("aggregator_value")))
    if contradiction:
        triggered.append("A2")
        evidence["A2"] = contradiction

    if rdof_result is not None and rdof_result.get("stop_rule") == "c2":
        survivors = [h for h, verdict in verdicts.items()
                     if verdict["verdict"] != "REFUTED"]
        if len(survivors) >= 2:
            triggered.append("A3")
            evidence["A3"] = [
                "budget exhausted with >= 2 surviving hypotheses: %s" % ", ".join(sorted(survivors))]

    if policy_verdict in ("DENY", "REQUIRE_APPROVAL"):
        triggered.append("A4")
        evidence["A4"] = ["policy verdict: %s (authorization axis, never mixed "
                          "with the epistemic conditions)" % policy_verdict]

    if convention_ambiguous:
        triggered.append("A5")
        evidence["A5"] = ["close vs low readings give different verdicts and no "
                          "frozen convention resolves it"]

    return {"conditions": triggered,
            "labels": [CONDITION_CODES[code] for code in triggered],
            "evidence": evidence}


# ---------------------------------------------------------------------------
# Enriched INCONCLUSIVE output (B3 §c.3)
# ---------------------------------------------------------------------------

def build_inconclusive(verdicts, conditions, what_would_change, decision_delta,
                       budget, escalade=None):
    """The enriched INCONCLUSIVE payload — an actionable research plan.

    ``what_would_change`` is MANDATORY (B3 §c.3): each entry names the missing
    fact, the hypotheses it affects, the predicate that would buy it, where,
    and its estimated cost — never "données insuffisantes" in prose.
    """
    if not what_would_change:
        raise ValueError(
            "E_WHAT_WOULD_CHANGE_REQUIRED: INCONCLUSIVE must enumerate what "
            "would change the verdict (B3 §c.3)")
    return {
        "epistemic_verdict": "INCONCLUSIVE",
        "conditions_declenchees": list(conditions["conditions"]),
        "conditions_labels": list(conditions["labels"]),
        "missing_inputs": [item for code in conditions["conditions"]
                           for item in conditions["evidence"].get(code, [])],
        "what_would_change_the_verdict": list(what_would_change),
        "decision_delta": dict(decision_delta),
        "budget": dict(budget),
        "escalade": escalade,
        "action": None,
    }


# ---------------------------------------------------------------------------
# ESCALATE vs NO-ACTION (B3 §c.4 — deterministic table, explicit differences)
# ---------------------------------------------------------------------------

def escalate_vs_no_action(conclusive, action_passes_threshold=None,
                          action_out_of_envelope=False, policy_verdict=None,
                          only_human_channel=False, bounded_potential_loss=None,
                          budget_exhausted=False, survivors_opposite_costly=False,
                          integrity_ok=True):
    """Deterministic implementation of the B3 §c.4 table.

    Returns ``{"sortie": "NO-ACTION"|"ESCALATE", "motif", "row"}`` with the
    spec row it implements. "Attendre" is never "ne pas agir": NO-ACTION is
    justified as the best feasible action, with its computed motive.
    """
    if not integrity_ok:
        return {"sortie": "ESCALATE", "row": "c.4/6",
                "motif": "integrity failure: a decisive proof is invalid — "
                         "never produces an action (INV-INTEGRITY)"}
    if conclusive:
        if action_out_of_envelope or policy_verdict == "REQUIRE_APPROVAL":
            return {"sortie": "ESCALATE", "row": "c.4/2",
                    "motif": "decided action outside the envelope / approval "
                             "required — dossier ready to sign (A4)"}
        if only_human_channel:
            return {"sortie": "ESCALATE", "row": "c.4/3",
                    "motif": "the decisive fact is only obtainable through a "
                             "non-instrumented channel — the agent cannot buy it"}
        if action_passes_threshold is False:
            return {"sortie": "NO-ACTION", "row": "c.4/1",
                    "motif": "no feasible action passes the economic threshold; "
                             "waiting creates no new obligation"}
        return {"sortie": "NO-ACTION", "row": "c.4/1",
                "motif": "best feasible action evaluated; documented decision"}
    # INCONCLUSIVE paths
    if survivors_opposite_costly:
        return {"sortie": "ESCALATE", "row": "c.4/5",
                "motif": "surviving hypotheses prescribe opposite actions and "
                         "the wrong one is costly — fragile posterior"}
    if bounded_potential_loss and budget_exhausted:
        return {"sortie": "NO-ACTION", "row": "c.4/4",
                "motif": "INCONCLUSIVE (A1/A2) with bounded potential loss and "
                         "exhausted budget — cost asymmetry favours waiting "
                         "(Chow), logged as an abstention"}
    return {"sortie": "ESCALATE", "row": "c.4/5",
            "motif": "INCONCLUSIVE without a bounded-loss argument — escalate "
                     "rather than wait blindly"}


def what_would_change_entries(missing_predicates, verdicts):
    """Enumerate the research plan entries from candidate predicates.

    ``missing_predicates``: iterable of predicate records (id, name, source,
    cost_queries, cost_seconds). Entries name the affected hypotheses when the
    predicate's registered scope intersects a non-refuted hypothesis.
    """
    entries = []
    survivors = sorted(h for h, verdict in verdicts.items()
                       if verdict["verdict"] != "REFUTED")
    for predicate in missing_predicates:
        entries.append({
            "fait": predicate["name"],
            "hypotheses_affectees": survivors,
            "predicat": predicate["predicate_id"],
            "cible": predicate.get("source", ""),
            "cout_estime": "%d requête(s), < %.1f s" % (
                predicate.get("cost_queries", 1),
                max(predicate.get("cost_seconds", 0.65), 0.5)),
        })
    return entries