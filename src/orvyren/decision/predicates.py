#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — predicate catalogue P for RDOF v1 (W3 lot L3.2).

Spec: B3_DECISION_ETUDE.md §b.2 (DOC2 §5.4.3, FREEZE_V2 C2). A predicate is an
observable fact that is already instrumented, with **registered thresholds**
that partition its outcomes into classes, a temporal step, a **measured cost**
(queries + seconds, W3-A measurements of 2026-10-15) and a perimeter. RDOF
chooses among these; the effects of their outcomes are computed by
re-classification (``rdof.py``), never hard-coded here.

Costs are the measured values of B3 §b.2 ("Costs" paragraph): ~0.4-0.7 s per
sequential ``eth_call`` on ``eth.drpc.org``, ~0.36 s on blastapi; corpus-backed
predicates cost 0 s of network (they read the frozen corpus) but may carry a
*decision delay* — the time until their verdict is actually obtainable
(e.g. persistence can only be read once the window has run its course).

Offline discipline: predicates that need chain reads are declared with
``offline_evaluable=False`` and an explicit reason — they are listed in every
RDOF dossier as excluded, never silently dropped.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from orvyren.decision.scenarios import (  # noqa: F401  (reuse of frozen helpers)
    Observation,
    DEVIATION_ALERT_PCT,
    INDEPENDENT_VENUES,
    PERSISTENCE_HOURS_LIMIT,
    SUPPLY_DROP_PCT,
    SUPPLY_METRIC,
    SUPPLY_VENUE,
    SUPPLY_WINDOW_HOURS,
    _HOUR,
    _alert_observations,
    _price_series,
    _supply_series,
    contiguous_episodes,
    deviation_exceeds,
    observations_in_window,
    parse_window_bound,
)

PREDICATE_CATALOG_V1 = "predicates/v1"

# Measured costs (B3 §b.2 "Costs", W3-A run of 2026-10-15).
ETH_CALL_SECONDS = 0.65          # sequential eth_call ~0.4-0.7 s on eth.drpc.org
ETH_CALL_SECONDS_BLASTAPI = 0.36  # ~0.36 s on blastapi


@dataclass(frozen=True)
class Predicate:
    """One instrumented observable with registered thresholds (B3 §b.2)."""

    predicate_id: str
    ref: str                      # source of the registration (spec section)
    name: str
    measure: str                  # what is read
    source: str                   # where it is read from
    temporal_step: str
    cost_queries: int
    cost_seconds: float           # measured network/compute seconds
    decision_delay_seconds: float  # 0 = verdict immediately obtainable
    decision_delay_note: str
    thresholds: Tuple[float, ...]
    class_labels: Tuple[str, ...]
    case_scope: Tuple[str, ...]   # case ids this predicate applies to
    offline_evaluable: bool
    offline_reason: str = ""      # filled when offline_evaluable is False

    def class_of(self, value: float) -> str:
        """Class label of a measured value under the registered thresholds."""
        if self.predicate_id == "P-6.3":
            # the measure is a signed change (negative = drop): the drop is
            # |value| and the first registered threshold is the drop threshold.
            return (self.class_labels[1] if -value >= self.thresholds[0]
                    else self.class_labels[0])
        if self.predicate_id == "P-PERS":
            # the labels are "<=12 h" / ">12 h": a span of EXACTLY 12 h belongs
            # to the first class. The generic strict '<' loop below would file
            # it under ">12 h", contradicting the label and the "<=12 h"
            # injector (which deliberately produces exactly 12 h spans).
            return (self.class_labels[0] if value <= self.thresholds[0]
                    else self.class_labels[1])
        for index, threshold in enumerate(self.thresholds):
            if value < threshold:
                return self.class_labels[index]
        return self.class_labels[-1]


def _p(predicate_id, ref, name, measure, source, temporal_step, cost_queries,
       cost_seconds, thresholds, class_labels, case_scope, offline_evaluable,
       decision_delay_seconds=0.0, decision_delay_note="", offline_reason=""):
    return Predicate(
        predicate_id=predicate_id, ref=ref, name=name, measure=measure,
        source=source, temporal_step=temporal_step, cost_queries=cost_queries,
        cost_seconds=cost_seconds, decision_delay_seconds=decision_delay_seconds,
        decision_delay_note=decision_delay_note, thresholds=thresholds,
        class_labels=class_labels, case_scope=case_scope,
        offline_evaluable=offline_evaluable, offline_reason=offline_reason)


#: The v1 instrumented predicates (B3 §b.2 table + DOC2 §5.4.3 list; all were
#: executed on 2026-10-15 — the chain-backed ones through the W3-A data layer).
CATALOG_V1: Tuple[Predicate, ...] = (
    _p("P-1.2", "W2-B 1.2 / B3 §b.2", "inter-venue dispersion",
       "sigma_disp (bps) between independent venues",
       "corpus: defillama+bitstamp+binance series", "hourly",
       0, 0.0, (100.0, 300.0), ("<100 bps", ">=100 bps", ">=300 bps"),
       ("usdc-2023-03",), True),
    _p("P-1.3", "W2-B 1.3 / B3 §b.2", "oracle/market divergence",
       "Delta (bps) = oracle vs market median",
       "rpc: Chainlink latestRoundData + venue median (archive)", "hourly",
       2, ETH_CALL_SECONDS, (100.0,), ("<100 bps", ">=100 bps"),
       ("usdc-2023-03", "rseth-2026-04"), False,
       offline_reason="needs archive eth_call; the frozen corpus carries no "
                      "Chainlink venue (series live in evidence/episode_*.json)"),
    _p("P-1.4", "W2-B 1.4-1.5 / B3 §b.2", "realizable discount ladder",
       "realizable discount by size step (get_dy)",
       "rpc: Curve/Aave quoters (archive)", "per size step",
       4, ETH_CALL_SECONDS, (), ("discount per step",),
       ("steth-2022-06", "rseth-2026-04"), False,
       offline_reason="needs archive eth_call to the pool quoter"),
    _p("P-2.2", "W2-B 2.2 / B3 §b.2", "supply-cap saturation ratio",
       "S/supplyCap classes", "rpc: Pool.getReserveData (archive)", "per block",
       1, ETH_CALL_SECONDS, (95.0, 99.0), ("<95 %", ">=95 %", ">=99 %"),
       ("rseth-2026-04",), False,
       offline_reason="needs archive eth_call; measured value (99,9989 %) lives "
                      "in evidence/episode_rseth_2026-04.json"),
    _p("P-2.5", "W2-B 2.5 / B3 §b.2", "reserve freeze flag",
       "isFrozen bit 57", "rpc: Pool.getReserveData (archive)", "per block",
       1, ETH_CALL_SECONDS, (), ("0", "1"),
       ("rseth-2026-04",), False,
       offline_reason="needs archive eth_call; measured transition (block "
                      "24 908 723) lives in evidence/episode_rseth_2026-04.json"),
    _p("P-5.1", "W2-B 5.1-5.2 / B3 §b.2", "cross-chain mint invariant",
       "locked(ETH) >= minted(remote chains)", "rpc: multi-chain reads (archive)",
       "per block", 6, ETH_CALL_SECONDS, (), ("holds", "violated"),
       ("rseth-2026-04",), False,
       offline_reason="needs multi-chain archive reads"),
    _p("P-6.3", "W2-B 6.3 / B3 §b.2", "24 h circulating supply drop",
       "max 24 h drop of circulating supply (%)",
       "corpus: defillama_supply_aggregate", "daily",
       1, ETH_CALL_SECONDS, (SUPPLY_DROP_PCT,), ("<1 %", ">=1 %"),
       ("usdc-2023-03",), True),
    _p("P-PERS", "B3 §b.2 micro-exemple (i)", "deviation persistence",
       "max alert episode span (h) across independent venues",
       "corpus: venue price series already in hand", "hourly",
       0, 0.0, (PERSISTENCE_HOURS_LIMIT,), ("<=12 h", ">12 h"),
       ("usdc-2023-03",), True,
       decision_delay_note="verdict only obtainable once the episode has run: "
                           "wait ~6 h after the first alert for a 12 h span"),
)

BY_ID: Dict[str, Predicate] = {p.predicate_id: p for p in CATALOG_V1}


def _synthetic(moment: dt.datetime, venue: str, metric: str, value: float) -> "Observation":
    """One synthetic counterfactual row (analysis only — never persisted)."""
    return Observation(timestamp_utc=moment.isoformat(), ts=moment, venue=venue,
                       metric=metric, value=value, extra="counterfactual",
                       retrieved_at="counterfactual")


# ---------------------------------------------------------------------------
# Offline evaluation (reads the frozen corpus only)
# ---------------------------------------------------------------------------

def _max_24h_supply_drop(observations, window_start, window_end, horizon):
    supply = _supply_series(
        observations_in_window(observations, window_start, min(horizon, window_end)),
        SUPPLY_VENUE)
    best = None
    for previous, current in zip(supply, supply[1:]):
        if previous.value <= 0:
            # non-positive supply row: flagged by H3's integrity check, and the
            # ratio below would divide by zero (crash) on exactly the corrupt
            # data the case is designed to detect
            continue
        delta_hours = (current.ts - previous.ts).total_seconds() / _HOUR
        if 0 < delta_hours <= SUPPLY_WINDOW_HOURS:
            change = (current.value - previous.value) / previous.value * 100.0
            if best is None or change < best["drop_pct"]:
                best = {"drop_pct": change, "from": previous, "to": current}
    return best


def _max_persistence_span(observations, window_start, window_end, horizon):
    in_window = observations_in_window(
        observations, window_start, min(horizon, window_end))
    best = None
    for venue in INDEPENDENT_VENUES:
        for episode in contiguous_episodes(
                _price_series(in_window, venue),
                lambda o: deviation_exceeds(o.value, DEVIATION_ALERT_PCT)):
            span = (episode[-1].ts - episode[0].ts).total_seconds() / _HOUR
            if best is None or span > best["span_hours"]:
                best = {"span_hours": span, "venue": venue,
                        "start": episode[0], "end": episode[-1]}
    return best


def evaluate_predicate(predicate_id, observations, window_start, window_end,
                       horizon=None):
    """Collect predicate ``predicate_id`` from the frozen corpus (offline).

    Returns ``{"predicate_id", "value", "class", "refs": [...], "detail"}``.
    Deterministic: same corpus + same bounds -> same result. Chain-backed
    predicates raise ``ValueError("E_NOT_OFFLINE_EVALUABLE")`` — callers must
    check ``offline_evaluable`` first (RDOF lists them as excluded instead).
    """
    start = parse_window_bound(window_start) if isinstance(window_start, str) else window_start
    end = parse_window_bound(window_end) if isinstance(window_end, str) else window_end
    horizon = parse_window_bound(horizon) if isinstance(horizon, str) else (horizon or end)
    predicate = BY_ID[predicate_id]
    if not predicate.offline_evaluable:
        raise ValueError("E_NOT_OFFLINE_EVALUABLE: %s" % predicate_id)

    if predicate_id == "P-6.3":
        best = _max_24h_supply_drop(observations, start, end, horizon)
        if best is None:
            return {"predicate_id": predicate_id, "value": None, "class": None,
                    "refs": [], "detail": "no computable 24 h supply change"}
        return {
            "predicate_id": predicate_id, "value": round(best["drop_pct"], 6),
            "class": predicate.class_of(best["drop_pct"]),
            "refs": [best["from"].ref(), best["to"].ref()],
            "detail": "drop from %s to %s (%s)" % (
                best["from"].timestamp_utc, best["to"].timestamp_utc,
                predicate.source),
        }
    if predicate_id == "P-PERS":
        best = _max_persistence_span(observations, start, end, horizon)
        if best is None:
            return {"predicate_id": predicate_id, "value": None, "class": None,
                    "refs": [], "detail": "no alert episode found"}
        return {
            "predicate_id": predicate_id,
            "value": round(best["span_hours"], 4),
            "class": predicate.class_of(best["span_hours"]),
            "refs": [best["start"].ref(), best["end"].ref()],
            "detail": "longest episode: %s, %s -> %s" % (
                best["venue"], best["start"].timestamp_utc, best["end"].timestamp_utc),
        }
    raise ValueError("E_PREDICATE_EVALUATOR_MISSING: %s" % predicate_id)


# ---------------------------------------------------------------------------
# Counterfactual injectors ("if the outcome were this one" — B3 §b.2, step 2)
# ---------------------------------------------------------------------------

def inject_outcome(predicate_id, class_label, observations, window_start,
                   window_end, horizon=None):
    """Return a copy of ``observations`` realizing ``class_label`` for the predicate.

    Counterfactual analysis of "what if the outcome were this class" (B3 §b.2
    step 2) — the injected rows are synthetic and only ever used to re-classify
    hypotheses; they are never written anywhere.
    """
    from orvyren.decision.scenarios import Observation
    predicate = BY_ID[predicate_id]
    if class_label not in predicate.class_labels:
        raise ValueError("E_CLASS_UNKNOWN: %s/%s" % (predicate_id, class_label))
    start = parse_window_bound(window_start) if isinstance(window_start, str) else window_start
    end = parse_window_bound(window_end) if isinstance(window_end, str) else window_end
    horizon = parse_window_bound(horizon) if isinstance(horizon, str) else (horizon or end)
    kept = [o for o in observations]

    if predicate_id == "P-6.3":
        # replace the whole aggregate series with a synthetic pair realizing
        # the class drop (a partial edit would leave the real -7.17 % pair in
        # place and no class would differ)
        anchor = max((o for o in kept
                      if o.venue == SUPPLY_VENUE and o.ts <= horizon),
                     key=lambda o: o.ts, default=None)
        base_value = anchor.value if anchor is not None else 4.2e10
        drop_target = 5.0 if class_label == ">=1 %" else SUPPLY_DROP_PCT / 2.0
        moment = horizon
        previous_ts = moment - dt.timedelta(hours=SUPPLY_WINDOW_HOURS)
        previous_value = base_value / (1.0 - drop_target / 100.0)
        kept = [o for o in kept if not (o.venue == SUPPLY_VENUE
                                        and start <= o.ts <= end)]
        kept.append(_synthetic(previous_ts, SUPPLY_VENUE, SUPPLY_METRIC,
                               previous_value))
        kept.append(_synthetic(moment, SUPPLY_VENUE, SUPPLY_METRIC, base_value))
        return kept

    if predicate_id == "P-PERS":
        # extend (">12 h") or snap back ("<=12 h") the alert episodes
        for venue in INDEPENDENT_VENUES:
            venue_series = _price_series(kept, venue)
            episodes = contiguous_episodes(
                venue_series,
                lambda o: deviation_exceeds(o.value, DEVIATION_ALERT_PCT))
            for episode in episodes:
                first, last = episode[0], episode[-1]
                if class_label == ">12 h":
                    target = first.ts + dt.timedelta(hours=PERSISTENCE_HOURS_LIMIT + 2.0)
                    moment = max(last.ts, target - dt.timedelta(hours=1.0))
                    while moment <= end:
                        kept.append(_synthetic(moment, venue, last.metric,
                                               last.value))
                        moment += dt.timedelta(hours=1.0)
                        if moment > target + dt.timedelta(hours=2.0):
                            break
                else:
                    # recovered <= 12 h: keep the episode's first 12 hours (the
                    # observed simultaneity is evidence in hand — a counterfactual
                    # never erases observations), snap the rest back to peg.
                    cutoff = first.ts + dt.timedelta(hours=PERSISTENCE_HOURS_LIMIT)
                    for index, observation in enumerate(kept):
                        if (observation.venue == venue
                                and cutoff < observation.ts <= last.ts):
                            kept[index] = _synthetic(
                                observation.ts, observation.venue,
                                observation.metric, 1.0)
        return kept

    # predicates without an injector: the outcome cannot be simulated offline
    return kept


def predicate_effect_possible(predicate: Predicate) -> bool:
    """True when at least one class of the predicate can be injected offline."""
    return predicate.predicate_id in ("P-6.3", "P-PERS")
