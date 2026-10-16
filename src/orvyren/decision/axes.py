#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — three axes + double price convention (W3: règle généralisée, L3.6).

Spec: B3_DECISION_ETUDE.md §e.1 (DOC2 §5.4.6, FREEZE_V2 C5). The three output
axes are **separate and never fused**:

- ``epistemic_verdict``    in {CONCLUANT, INCONCLUSIVE} + what is missing;
- ``economic_action``      in the bounded-action enum, or null;
- ``authorization_verdict`` in {ALLOW, DENY, REQUIRE_APPROVAL} — independent
  of the other two ("DENY de politique" != "échec épistémique").

Double price convention (frozen, FREEZE_V2 C5): **alert on the low; decision
on close + low** — exposed here as ONE parameter (``PRICE_CONVENTION``) and
tested; the measured gap between conventions is reported wherever a threshold
decides.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Sequence

from orvyren.decision.abstention import (build_inconclusive,
                                         detect_conditions,
                                         escalate_vs_no_action,
                                         what_would_change_entries)
from orvyren.decision.catalog import CATALOG_VERSION, bounded_size
from orvyren.decision.exposure import Exposure
from orvyren.decision.predicates import BY_ID
from orvyren.decision.rdof import (FROZEN_HYPOTHESIS_ORDER, action_candidate,
                                   rdof_run)
from orvyren.decision.scenarios import (SUPPORTED, classify_hypotheses,
                                        integrity_flags, observations_in_window,
                                        parse_window_bound)

PRICE_CONVENTION_VERSION = "convention/v1"
#: The frozen double convention — one parameter, cited everywhere a threshold decides.
PRICE_CONVENTION = {
    "alert_reading": "low",
    "decision_readings": ("close", "low"),
    "ref": "FREEZE_V2 C5 / DOC2 §5.4.6 — alerte sur le low ; décision sur close + low",
}

#: FREEZE_V2 C5 froze the convention: when two admissible readings would give
#: two verdicts, the frozen convention RESOLVES it by being applied — A5 only
#: fires when no frozen convention exists (B3 §c.2). The measured gap is still
#: reported everywhere a threshold decides (DOC2 §5.4.6).
FROZEN_CONVENTION_APPLIES = True

ECONOMIC_ACTIONS = ("CONSERVER", "CONVERTIR/TRANSFÉRER", "CÉDER(x*)",
                    "RÉDUIRE(x*)", "HEDGER(x*)", "RAPATRIER", "ESCALADER")

_AXES_KIND_TO_ECONOMIC = {
    "ACTION_RECOMMENDED": "CONVERTIR/TRANSFÉRER",
    "NO_ACTION": "CONSERVER",
    "INCONCLUSIVE": None,
    "ESCALATE": "ESCALADER",
}


def _parse_low(observation) -> Optional[float]:
    for part in (observation.extra or "").split(";"):
        part = part.strip()
        if part.startswith("low="):
            try:
                return float(part[4:])
            except ValueError:
                return None
    return None


def convention_divergence_bps(observations, window_start, window_end):
    """Measured gap (bps) between the close and low readings, per venue.

    Spec note (DOC2 §5.4.6): the measured gap between conventions on Bitstamp
    for 11/03/2023 exceeds most thresholds — the convention is a decision
    object, not a detail. Computed from the frozen corpus, never hard-coded.
    """
    start = parse_window_bound(window_start) if isinstance(window_start, str) else window_start
    end = parse_window_bound(window_end) if isinstance(window_end, str) else window_end
    best = None
    for observation in observations_in_window(observations, start, end):
        low = _parse_low(observation)
        if low is None:
            continue
        gap_bps = (observation.value - low) / low * 10000.0
        if best is None or gap_bps > best["gap_bps"]:
            best = {"venue": observation.venue, "timestamp_utc": observation.timestamp_utc,
                    "close": observation.value, "low": low, "gap_bps": round(gap_bps, 2)}
    return best


def _substitute_low_readings(observations):
    """A variant evidence set where alerted rows are read at their low."""
    from orvyren.decision.scenarios import Observation
    out = []
    for observation in observations:
        low = _parse_low(observation)
        if low is not None and low < observation.value:
            out.append(Observation(timestamp_utc=observation.timestamp_utc,
                                   ts=observation.ts, venue=observation.venue,
                                   metric=observation.metric, value=low,
                                   extra=observation.extra,
                                   retrieved_at=observation.retrieved_at))
        else:
            out.append(observation)
    return out


def verdicts_under_conventions(observations, window_start, window_end):
    """Verdicts under the close reading vs the low reading (A5 detector)."""
    close_verdicts = classify_hypotheses(observations, window_start, window_end)
    low_verdicts = classify_hypotheses(_substitute_low_readings(observations),
                                       window_start, window_end)
    comparison = {
        hypothesis_id: {
            "close": close_verdicts[hypothesis_id]["verdict"],
            "low": low_verdicts[hypothesis_id]["verdict"],
        }
        for hypothesis_id in FROZEN_HYPOTHESIS_ORDER
    }
    ambiguous = any(entry["close"] != entry["low"] for entry in comparison.values())
    return {"close": {h: v["verdict"] for h, v in close_verdicts.items()},
            "low": {h: v["verdict"] for h, v in low_verdicts.items()},
            "per_hypothesis": comparison, "ambiguous": ambiguous}


def authorization_via_policy(amount_usdc, reserve_recipient, created_at=None,
                             now=None, action="transfer", asset=None,
                             chain_id=None, intent_id=None):
    """Evaluate the bounded intent through the deterministic policy service.

    Returns ``{"verdict", "reasons", "intent_id"}`` — or an explicit
    not-evaluated marker when no recipient is configured (never a guessed
    verdict).
    """
    if not reserve_recipient:
        return {"verdict": None, "reasons": ["no reserve recipient configured — "
                                             "authorization not evaluated"],
                "intent_id": None, "evaluated": False}
    from orvyren.policy import ALLOWED_ASSET, ALLOWED_CHAIN_ID, Intent, default_config, evaluate
    moment = created_at or dt.datetime.now(dt.timezone.utc)
    intent = Intent(
        intent_id=intent_id or ("decision-%s" % moment.strftime("%Y%m%dT%H%M%SZ")),
        action=action,
        chain_id=chain_id or ALLOWED_CHAIN_ID,
        asset=asset or ALLOWED_ASSET,
        amount=float(amount_usdc),
        recipient=reserve_recipient,
        created_at=moment,
        justification="ORVYREN decision dossier — bounded A-D1 demonstration transfer",
    )
    config = default_config(reserve_recipient)
    decision = evaluate(intent, config, now=now or moment)
    return {"verdict": decision.verdict, "reasons": list(decision.reasons),
            "intent_id": intent.intent_id, "evaluated": True}


def build_dossier(case_id, observations, window_start, window_end,
                  rdof=None, reserve_recipient=None, policy_now=None,
                  exposure=None, integrity=None):
    """Assemble the enriched decision dossier: 3 axes + RDOF + abstention.

    Keeps the v0 fields untouched (the caller merges this payload into the
    existing decision record) — the three axes are ADDED, never fused into a
    single verdict.
    """
    envelope = exposure if exposure is not None else Exposure()
    available = envelope.available_to_move()
    if rdof is None:
        rdof = rdof_run(observations, window_start, window_end, case_id=case_id,
                        exposure=envelope)
    verdicts = classify_hypotheses(observations, window_start, window_end)
    flags = list(integrity) if integrity is not None else integrity_flags(observations)

    supported = [h for h in FROZEN_HYPOTHESIS_ORDER
                 if verdicts[h]["verdict"] == SUPPORTED]
    epistemic_verdict = "CONCLUANT" if supported else "INCONCLUSIVE"

    kind = rdof["final_action_candidate"]["kind"]
    economic_action = _AXES_KIND_TO_ECONOMIC[kind]
    x_star = bounded_size(envelope.action_usdc, available, envelope.action_usdc)

    # Axis 3 — authorization (independent from the other two axes)
    authorization = {"verdict": None, "evaluated": False,
                     "note": "no executable economic action" if economic_action
                     not in ("CONVERTIR/TRANSFÉRER",) else "not evaluated"}
    if economic_action in ("CONVERTIR/TRANSFÉRER",):
        authorization = authorization_via_policy(
            x_star, reserve_recipient, created_at=policy_now, now=policy_now)

    conventions = verdicts_under_conventions(observations, window_start, window_end)
    conditions = detect_conditions(
        verdicts, integrity_flags=flags, rdof_result=rdof,
        policy_verdict=authorization.get("verdict"),
        convention_ambiguous=(conventions["ambiguous"]
                              and not FROZEN_CONVENTION_APPLIES))

    abstention_payload = None
    if epistemic_verdict == "INCONCLUSIVE":
        candidates = []
        for entry in rdof.get("not_searched", []):
            predicate = BY_ID.get(entry["predicate_id"])
            if predicate is not None and predicate.offline_evaluable:
                candidates.append({"predicate_id": predicate.predicate_id,
                                   "name": predicate.name,
                                   "source": predicate.source,
                                   "cost_queries": predicate.cost_queries,
                                   "cost_seconds": predicate.cost_seconds})
        escalade = escalate_vs_no_action(
            conclusive=False,
            bounded_potential_loss=True,
            budget_exhausted=(rdof.get("stop_rule") == "c2"),
            survivors_opposite_costly=False,
            integrity_ok=not flags)
        abstention_payload = build_inconclusive(
            verdicts, conditions,
            what_would_change_entries(candidates, verdicts),
            decision_delta={
                "si_H2_soutenue": "candidat A-D1 (convertir/transférer, x* borné)",
                "si_H2_refutee": "NO_ACTION documenté (A-D7) — ne rien faire est alors optimal",
            },
            budget={"consomme": rdof["budget"]["consomme"],
                    "limites": rdof["budget"]["limites"],
                    "reste": {"recherches": rdof["budget"]["limites"]["recherches"]
                              - rdof["budget"]["consomme"]["recherches"]},
                    "raison_arret": rdof["stop"]},
            escalade=escalade if escalade["sortie"] == "ESCALATE" else None)

    axes = {
        "axes_version": "axes/v1",
        "epistemic_verdict": epistemic_verdict,
        "economic_action": economic_action,
        "authorization_verdict": authorization.get("verdict"),
        "x_star_usdc": x_star,
        "supported_hypotheses": supported,
        "authorization_detail": authorization,
        "conditions_declenchees": conditions["conditions"],
        "separation_note": ("3 axes never fused: DENY de politique != échec "
                            "épistémique ; INCONCLUSIVE != NO-ACTION (B3 §c.2)"),
    }
    return {
        "axes": axes,
        "rdof": rdof,
        "abstention": abstention_payload,
        "action_catalog_version": CATALOG_VERSION,
        "price_convention": dict(PRICE_CONVENTION, version=PRICE_CONVENTION_VERSION,
                                 measured_gap=convention_divergence_bps(
                                     observations, window_start, window_end),
                                 verdicts_under_conventions=conventions),
    }