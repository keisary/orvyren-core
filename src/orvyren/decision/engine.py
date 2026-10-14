#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core - decision engine: candidate action, NO-ACTION or INCONCLUSIVE.

PRE-REGISTERED DECISION RULE (frozen with the team before any evaluation; the
text below is quoted verbatim in every output's rationale):

  1. H2 SUPPORTED and available_to_move(...) > 0
         -> ACTION_RECOMMENDED. The action is the bounded demonstration
            transfer of FREEZE_V1.md D8: 100 USDC of test USDC from wallet
            "treasury" to wallet "reserve"; amount = min(100, available_to_move).
  2. H1 SUPPORTED and H2 REFUTED
         -> NO_ACTION. Documented justification: the dislocation stayed local
            to one venue with a pegged aggregate, so the registered evidence
            does not justify reducing exposure on the asset itself.
  3. Otherwise, when the hypotheses are decidable (no missing series)
         -> NO_ACTION: no registered criterion justifies an exposure reduction.
  4. Any required series missing (a verdict is INCONCLUSIVE with
     missing_inputs)
         -> INCONCLUSIVE, missing_inputs listed, action = null. The engine
            never guesses and never produces an action on incomplete evidence.

"available_to_move > 0" is the demonstration exposure envelope of
``exposure.py``: the treasury can only move USDC above its reserve floor, and
never more than the registered action size.

No number leaves this module without a provenance reference: every price,
supply figure or duration quoted in ``rationale`` comes from a verdict's
``evidence_refs``, which point back at the frozen corpus rows
(timestamp_utc, venue, value). ``calibration`` is null in V1 (no forecast
outcomes have been settled yet).
"""

from orvyren.decision.exposure import Exposure, available_to_move
from orvyren.decision.scenarios import (
    AGGREGATE_TOLERANCE_PCT,
    DEVIATION_ALERT_PCT,
    PEG_REFERENCE,
    PERSISTENCE_HOURS_LIMIT,
    RECOVERY_HOURS_LIMIT,
    RECOVERY_TOLERANCE_PCT,
    REFUTED,
    SUPPORTED,
    SUPPLY_DROP_PCT,
    SUPPLY_WINDOW_HOURS,
    corpus_sha256,
    classify_hypotheses,
    load_observations,
    observations_in_window,
    parse_window_bound,
    window_summary,
)

ACTION_RECOMMENDED = "ACTION_RECOMMENDED"
NO_ACTION = "NO_ACTION"
INCONCLUSIVE = "INCONCLUSIVE"
DECISION_VERDICTS = (ACTION_RECOMMENDED, NO_ACTION, INCONCLUSIVE)

DEFAULT_CASE_ID = "usdc-2023-03"

RULE_TEXT = (
    "Pre-registered decision rule (frozen before evaluation): H2 SUPPORTED and "
    "available_to_move > 0 -> ACTION_RECOMMENDED (bounded 100 USDC test transfer, D8); "
    "H1 SUPPORTED and H2 REFUTED -> NO_ACTION (local perturbation, no exposure reduction); "
    "missing required series -> INCONCLUSIVE with missing_inputs."
)


def _fmt(value, digits=4):
    return f"{value:.{digits}f}"


def _dedupe_refs(refs):
    """Stable de-duplication of provenance references (timestamp, venue, value)."""
    seen, unique = set(), []
    for ref in refs:
        key = (ref.get("timestamp_utc"), ref.get("venue"), ref.get("value"))
        if key not in seen:
            seen.add(key)
            unique.append(ref)
    return unique


def _inputs_summary(csv_path, observations, in_window, envelope):
    """Counts and extents of the corpus actually used, plus the frozen parameters."""
    sources = []
    for venue, metric in sorted({(o.venue, o.metric) for o in in_window}):
        rows = [o for o in in_window if o.venue == venue and o.metric == metric]
        rows.sort(key=lambda o: o.ts)
        sources.append(
            {
                "venue": venue,
                "metric": metric,
                "observations": len(rows),
                "first_timestamp_utc": rows[0].timestamp_utc,
                "last_timestamp_utc": rows[-1].timestamp_utc,
                "min_value": min(o.value for o in rows),
                "max_value": max(o.value for o in rows),
            }
        )
    return {
        "corpus": {
            "path": str(csv_path),
            "sha256": corpus_sha256(csv_path),
            "observations_in_file": len(observations),
            "observations_in_window": len(in_window),
        },
        "sources": sources,
        "peg_reference_usd": PEG_REFERENCE,
        "exposure_parameters": envelope.as_dict(),
        "pre_registered_thresholds": {
            "deviation_alert_pct": DEVIATION_ALERT_PCT,
            "aggregate_tolerance_pct": AGGREGATE_TOLERANCE_PCT,
            "recovery_tolerance_pct": RECOVERY_TOLERANCE_PCT,
            "recovery_hours_limit": RECOVERY_HOURS_LIMIT,
            "persistence_hours_limit": PERSISTENCE_HOURS_LIMIT,
            "supply_drop_pct": SUPPLY_DROP_PCT,
            "supply_window_hours": SUPPLY_WINDOW_HOURS,
        },
    }


def _hypothesis_line(verdict):
    """One rationale bullet per hypothesis, citing only computed numbers."""
    hid = verdict["hypothesis_id"]
    label = verdict["label"]
    outcome = verdict["verdict"]
    if hid == "H1":
        computed = verdict["criteria_evaluated"][1]["computed"]
        episodes = computed["persistent_episodes"]
        spans = ", ".join(f"{e['venue']} {_fmt(e['span_hours'], 1)} h" for e in episodes)
        support = verdict["criteria_evaluated"][0]["computed"]
        details = (
            f" (persistent episodes: {spans})" if spans else " (no episode longer than 12 h)"
        )
        if outcome == REFUTED:
            text = (
                f"H1 {label}: {outcome}. The deviation did not stay local: > {DEVIATION_ALERT_PCT}% "
                f"persisted more than {_fmt(PERSISTENCE_HOURS_LIMIT, 0)} h on "
                f"{computed['persistent_venue_count']} independent venues{details}, while the aggregator "
                f"fell to {support['aggregator_min_value']} "
                f"({_fmt(support['aggregator_min_deviation_pct'], 4)}%), beyond the "
                f"{AGGREGATE_TOLERANCE_PCT}% tolerance"
            )
        elif outcome == SUPPORTED:
            text = f"H1 {label}: {outcome}. A single venue deviated while the aggregate stayed pegged"
        else:
            text = f"H1 {label}: {outcome}. The registered criteria are not decisive on this window"
        return text + "."
    if hid == "H2":
        computed = verdict["criteria_evaluated"][0]["computed"]
        minima = [
            f"{venue} {_fmt(m['value'], 5)} at {m['timestamp_utc']} ({_fmt(m['deviation_pct'], 4)}%)"
            for venue, m in computed["venue_minima"].items()
            if m["value"] is not None
        ]
        text = (
            f"H2 {label}: {outcome}. "
            f"{computed['simultaneous_alert_hours']} simultaneous hourly observation(s) more than "
            f"{DEVIATION_ALERT_PCT}% below peg on {len(computed['venues_with_alerts'])} independent venues "
            f"({', '.join(computed['venues_with_alerts'])})"
        )
        if computed["simultaneous_first_utc"]:
            text += (
                f" from {computed['simultaneous_first_utc']} to {computed['simultaneous_last_utc']}"
            )
        if minima:
            text += f"; deepest: {'; '.join(minima)}"
        if computed["max_24h_supply_drop_pct"] is not None:
            text += (
                f"; circulating supply moved {_fmt(computed['max_24h_supply_drop_pct'], 4)}% in "
                f"{_fmt(SUPPLY_WINDOW_HOURS, 0)} h "
                f"({computed['max_24h_supply_drop_from_utc']} -> {computed['max_24h_supply_drop_to_utc']}), "
                f"threshold {SUPPLY_DROP_PCT}%"
            )
        if verdict["missing_inputs"]:
            text += f"; missing inputs: {', '.join(verdict['missing_inputs'])}"
        return text + "."
    computed = verdict["criteria_evaluated"][1]["computed"]
    if outcome == REFUTED:
        return (
            f"H3 {label}: {outcome}. "
            f"{len(computed['concordant_venues'])} independent sources ({', '.join(computed['concordant_venues'])}) "
            f"were concordant over {computed['simultaneous_alert_hours']} simultaneous hour(s); no structural "
            f"inconsistency and no unexplained divergence was found in the corpus."
        )
    if outcome == SUPPORTED:
        return f"H3 {label}: {outcome}. A structural inconsistency or an unexplained divergence was detected."
    return f"H3 {label}: {outcome}. The registered criteria are not decisive on this window."


def _build_decision(verdicts, envelope, available, plan):
    """Apply the pre-registered decision rule; returns the decision dict."""
    h1, h2, h3 = verdicts["H1"], verdicts["H2"], verdicts["H3"]
    rationale = [RULE_TEXT]

    missing_inputs = []
    if h2["verdict"] == INCONCLUSIVE or h2["missing_inputs"]:
        for verdict in (h1, h2, h3):
            for item in verdict["missing_inputs"]:
                if item not in missing_inputs:
                    missing_inputs.append(item)

    action = None
    if h2["verdict"] == SUPPORTED and available > 0:
        verdict_name = ACTION_RECOMMENDED
        action = {
            "type": "transfer",
            "asset": "USDC (test)",
            "amount_usdc": available,
            "from_wallet": "treasury",
            "to_wallet": "reserve",
        }
        rationale.append(
            f"Rule 1 fires: H2 is {SUPPORTED} and available_to_move = min({_fmt(envelope.action_usdc, 1)}, "
            f"{_fmt(envelope.exposure_usdc, 1)} - {_fmt(envelope.floor_usdc, 1)}) = {_fmt(available, 4)} USDC > 0, "
            f"so the bounded demonstration action of FREEZE_V1 D8 is recommended: transfer of "
            f"{_fmt(available, 4)} USDC (test) from wallet 'treasury' to wallet 'reserve'."
        )
    elif h2["verdict"] == SUPPORTED and available <= 0:
        verdict_name = NO_ACTION
        rationale.append(
            f"H2 is {SUPPORTED} but available_to_move = {_fmt(available, 4)} USDC: the reserve floor "
            f"({_fmt(envelope.floor_usdc, 1)} USDC) leaves nothing to move, so NO_ACTION is returned "
            f"instead of a forced transfer."
        )
    elif h2["verdict"] == REFUTED:
        verdict_name = NO_ACTION
        if h1["verdict"] == SUPPORTED:
            rationale.append(
                f"Rule 2 fires: H1 is {SUPPORTED} and H2 is {REFUTED}, so the documented justification "
                f"applies -- the dislocation stayed local (one venue, pegged aggregate) and the registered "
                f"evidence does not justify reducing exposure on the asset. NO_ACTION."
            )
        else:
            rationale.append(
                f"Rule 3 fires: H2 is {REFUTED} and no criterion supports a bounded exposure reduction "
                f"(H1 {h1['verdict']}, H3 {h3['verdict']}). NO_ACTION."
            )
    else:
        verdict_name = INCONCLUSIVE
        rationale.append(
            "Rule 4 fires: a required series is missing, so H2 cannot be fully evaluated and the engine "
            "returns INCONCLUSIVE rather than guessing. No action is produced."
        )

    rationale.extend(_hypothesis_line(verdict) for verdict in (h1, h2, h3))

    if plan["has_control_gap"]:
        rationale.append(
            "Coverage note: this case window has no observations for at least one independent venue, "
            "which is why some criteria are not evaluable."
        )

    conditions = [
        "Any execution must first be authorized by the deterministic policy service "
        "(src/orvyren/policy, FREEZE_V1 D9): Base Sepolia chain 84532, allowlisted test-USDC asset, "
        "allowlisted reserve recipient, <= 100 USDC per transaction, <= 300 USDC cumulative, "
        "24 h permission, idempotent intent_id.",
        "Test assets only; no mainnet funds (FREEZE_V1 D5/D8).",
        "The decision is scoped to the frozen corpus revision (sha256 recorded in inputs_summary) and to "
        "the recorded window; new observations outside it invalidate the case.",
        "Contract-level verification of the asset was not possible from this corpus (no contract field); "
        "it remains an open check before any mainnet-grade claim.",
    ]

    limits = [
        "Exposure parameters are demonstration values, not a real portfolio: "
        f"{_fmt(envelope.exposure_usdc, 1)} USDC exposure, {_fmt(envelope.floor_usdc, 1)} USDC floor, "
        f"{_fmt(envelope.action_usdc, 1)} USDC action.",
        "Corpus coverage is uneven: " + "; ".join(
            f"{source['venue']} {source['observations']} observation(s)"
            for source in plan["sources"]
        ) + "; the control window has no exchange observations.",
        "The aggregator is a multi-venue median with possible lag; the supply series is daily and covers "
        "observable on-chain supply only.",
        "H2 identifies stress consistent with an asset/issuer event; price and supply data alone do not "
        "attribute it between the asset and its issuer.",
        "This engine produces a decision candidate only and never executes; the baseline A0 comparison "
        "lives in evidence/baseline_report.json.",
    ]

    provenance = _dedupe_refs(
        [ref for verdict in (h1, h2, h3) for ref in verdict["evidence_refs"]]
    )

    return {
        "verdict": verdict_name,
        "action": action,
        "rationale": rationale,
        "conditions": conditions,
        "limits": limits,
        "provenance": provenance,
        "missing_inputs": missing_inputs,
    }


def run_case(csv_path, window_start, window_end, case_id=DEFAULT_CASE_ID,
             window_label="main", exposure=None):
    """Evaluate one case window and return the JSON-serialisable decision record.

    Deterministic: identical corpus + identical window -> byte-identical
    serialisation (no wall-clock, no random, dict order fixed by construction).
    """
    start = parse_window_bound(window_start)
    end = parse_window_bound(window_end)
    observations = load_observations(csv_path)
    in_window = observations_in_window(observations, start, end)
    verdicts = classify_hypotheses(observations, start, end)

    envelope = exposure if exposure is not None else Exposure()
    available = envelope.available_to_move()

    inputs_summary = _inputs_summary(csv_path, observations, in_window, envelope)
    plan = {
        "sources": inputs_summary["sources"],
        "has_control_gap": any(
            not any(o.venue == venue for o in in_window)
            for venue in ("bitstamp", "binance")
        ),
    }
    decision = _build_decision(verdicts, envelope, available, plan)

    return {
        "case": case_id,
        "window": window_summary(start, end, window_label),
        "inputs_summary": inputs_summary,
        "hypothesis_verdicts": verdicts,
        "decision": decision,
        "calibration": None,
    }
