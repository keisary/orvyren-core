#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core - baseline A0: fixed aggregator-threshold rule (decision/baseline.py).

A0 is the adversary of the project (FREEZE_V1.md D6/D7): one fixed rule, one
threshold, no hypotheses and no provenance machinery. It exists to be measured
-- in particular its false-signal rate on the control window -- so that the
decision engine's added value can be compared against something honest.

FROZEN RULE (D6):
    "If the aggregator price (venue=defillama) is below 0.99 for 2 consecutive
     hourly observations, reduce the exposure by 100 USDC; otherwise NO-ACTION."

Reading conventions, fixed here and never renegotiated after seeing results:

  * the rule only ever reads the aggregator series (DeFiLlama median price);
  * ONE signal = ONE exposure reduction of 100 USDC. A signal fires on the
    observation that completes two consecutive hourly observations below 0.99;
    a maximal run of consecutive observations below 0.99 (an "episode") yields
    exactly ONE signal, so a persistent dislocation cannot trigger duplicate
    actions;
  * an episode is broken by any observation >= 0.99 or by a gap of more than
    1 h in the hourly series (contiguity is required, not assumed);
  * every signal on the control window is a FALSE signal by construction: the
    control window (15-18 Feb 2023) contains no known dislocation, so any
    action the rule demands there is a false positive (D7).

Output shape (fixed):
    {"rule", "signals_main", "signals_control", "false_signals_control"}
"""

from orvyren.decision.scenarios import (
    AGGREGATOR_VENUE,
    contiguous_episodes,
    deviation_pct,
    load_observations,
    observations_in_window,
)

AGGREGATOR_METRIC = "price_usd"
BASELINE_THRESHOLD = 0.99
CONSECUTIVE_OBSERVATIONS = 2
REDUCTION_USDC = 100.0

RULE_TEXT = (
    "If the aggregator price (venue=defillama) is below 0.99 for 2 consecutive hourly "
    "observations, reduce the exposure by 100 USDC; otherwise NO-ACTION (FREEZE_V1.md D6). "
    "One signal per episode of consecutive observations below 0.99, fired on the second "
    "observation; episodes are broken by 1 h gaps."
)


def _bounds(window):
    """Accept (start, end), [start, end] or {"start": ..., "end": ...}."""
    if isinstance(window, dict):
        return window["start"], window["end"]
    if isinstance(window, (tuple, list)) and len(window) == 2:
        return window[0], window[1]
    raise TypeError(f"window must be a 2-tuple or a dict with start/end, got {type(window)!r}")


def detect_signals(observations, window_start, window_end):
    """Apply the frozen A0 rule to one window; returns the list of signals."""
    series = sorted(
        [
            o
            for o in observations_in_window(observations, window_start, window_end)
            if o.venue == AGGREGATOR_VENUE and o.metric == AGGREGATOR_METRIC
        ],
        key=lambda o: o.ts,
    )
    signals = []
    for episode in contiguous_episodes(series, lambda o: o.value < BASELINE_THRESHOLD):
        if len(episode) < CONSECUTIVE_OBSERVATIONS:
            continue
        trigger = episode[1]          # the observation completing 2 consecutive hours
        first = episode[0]
        worst = min(episode, key=lambda o: o.value)
        signals.append(
            {
                "triggered_at_utc": trigger.timestamp_utc,
                "venue": AGGREGATOR_VENUE,
                "trigger_value": trigger.value,
                "trigger_deviation_pct": round(deviation_pct(trigger.value), 6),
                "consecutive_observations": CONSECUTIVE_OBSERVATIONS,
                "episode": {
                    "start_utc": first.timestamp_utc,
                    "end_utc": episode[-1].timestamp_utc,
                    "observations": len(episode),
                    "min_value": worst.value,
                    "min_value_utc": worst.timestamp_utc,
                },
                "action": {
                    "type": "reduce_exposure",
                    "amount_usdc": REDUCTION_USDC,
                },
                "evidence_refs": [first.ref(), trigger.ref()],
            }
        )
    return signals


def run_baseline(csv_path, main_window, control_window=None, observations=None):
    """Run A0 on the main window and (optionally) the control window.

    Returns the fixed output shape; ``false_signals_control`` counts every
    signal emitted on the control window, since no dislocation is known there.
    """
    corpus = observations if observations is not None else load_observations(csv_path)
    main_start, main_end = _bounds(main_window)
    signals_main = detect_signals(corpus, main_start, main_end)

    signals_control = []
    if control_window is not None:
        control_start, control_end = _bounds(control_window)
        signals_control = detect_signals(corpus, control_start, control_end)

    return {
        "rule": RULE_TEXT,
        "signals_main": signals_main,
        "signals_control": signals_control,
        "false_signals_control": len(signals_control),
    }
