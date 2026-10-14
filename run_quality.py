#!/usr/bin/env python
"""ORVYREN-Core — build the quality report and the evidence graph (offline).

What it does, in order:

1. loads and validates the archived corpus (``corpus/usdc_observations.csv``);
2. measures hourly coverage and data-gate answers over the main window;
3. writes ``evidence/quality_report.json`` (totals, rejections, flags,
   coverage per venue, data-gate examples, provenance check);
4. rebuilds ``evidence/graph.sqlite``: four sources, every kept observation and
   demo claims whose references are real observations of the corpus;
5. verifies the provenance chain of every claim and prints a compact summary.

The evidence database is a *build artifact*: it is recreated from the corpus on
every run so that two runs on the same corpus hold the same content and the
same snapshot hash (the store itself only ever appends rows — see
``graph.store``; demo claims are dated by the corpus collection time for the
same reason).

Offline, standard library only. Run: ``python run_quality.py``
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from orvyren.graph import models  # noqa: E402
from orvyren.graph.models import Claim, Hypothesis, Relation, Source  # noqa: E402
from orvyren.graph.provenance import verify_all  # noqa: E402
from orvyren.graph.store import GraphStore  # noqa: E402
from orvyren.quality import checks, normalize  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
CORPUS_CSV = os.path.join(ROOT, "corpus", "usdc_observations.csv")
EVIDENCE_DIR = os.path.join(ROOT, "evidence")
REPORT_PATH = os.path.join(EVIDENCE_DIR, "quality_report.json")
DB_PATH = os.path.join(EVIDENCE_DIR, "graph.sqlite")

#: Static description of each graph source (mirrors corpus/manifest.json).
SOURCE_CATALOGUE = {
    "defillama": (
        "DeFiLlama (historical USDC prices)",
        "coins.llama.fi/prices/historical/{ts}/{coin}",
        "Aggregator: median multi-venue price; coverage and lag must be "
        "checked; public quota is not guaranteed.",
    ),
    "binance": (
        "Binance (USDC/USDT klines)",
        "api.binance.com/api/v3/klines",
        "USDC/USDT market: measures the price against another stablecoin, "
        "i.e. a relative dislocation, not an absolute one.",
    ),
    "bitstamp": (
        "Bitstamp (USDC/USD OHLC)",
        "www.bitstamp.net/api/v2/ohlc/usdcusd/",
        "Single marketplace: local depth and spreads; the observed "
        "dislocation may be venue-specific.",
    ),
    "defillama_supply": (
        "DeFiLlama (USDC circulating supply)",
        "stablecoins.llama.fi/stablecoincharts/all?stablecoin=2 "
        "(+ /Ethereum?stablecoin=2)",
        "Daily series, coarse granularity; covers observable on-chain "
        "supply only (aggregate and Ethereum views).",
    ),
}

#: Hours shown as data-gate examples in the report (window bounds, the depeg
#: low prints, the first Binance hour, and one hour PAST the archive where no
#: venue has an observation at all — the gate must refuse it).
GATE_EXAMPLE_HOURS = (
    "2023-03-09T00:00:00+00:00",   # first hour of the main window
    "2023-03-11T07:00:00+00:00",   # lowest Bitstamp close of the window
    "2023-03-11T08:00:00+00:00",   # lowest DeFiLlama price of the window
    "2023-03-11T15:00:00+00:00",   # first hour with a Binance USDC/USDT close
    "2023-03-15T00:00:00+00:00",   # closing bound of the main window
    "2023-03-16T00:00:00+00:00",   # past the archive: nothing archived, gate refuses
)


def _iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat()


def provenance_timestamp(fallback: str) -> str:
    """Timestamp attributed to the demo claims.

    It is the collection time of the corpus (``corpus/manifest.json``), not the
    run time, so that re-running the script on the same corpus yields the same
    claims — and therefore the same graph hash. The run time is recorded
    separately in the report (``generated_at``). Falls back to ``fallback``
    when the manifest is not readable.
    """
    manifest_path = os.path.join(ROOT, "corpus", "manifest.json")
    try:
        with open(manifest_path, "r", encoding="utf-8") as handle:
            collected_at = json.load(handle).get("collected_at")
        if isinstance(collected_at, str) and collected_at:
            return collected_at
    except (OSError, ValueError):
        pass
    return fallback


def build_sources(observations, now_iso: str) -> List[Source]:
    """One Source per source id, dated by the latest retrieval of its rows."""
    latest: Dict[str, str] = {}
    for observation in observations:
        previous = latest.get(observation.source_id)
        if previous is None or observation.retrieved_at > previous:
            latest[observation.source_id] = observation.retrieved_at
    sources = []
    for source_id in sorted(SOURCE_CATALOGUE):
        name, endpoint, limits = SOURCE_CATALOGUE[source_id]
        sources.append(Source(
            id=source_id,
            name=name,
            endpoint=endpoint,
            retrieved_at=latest.get(source_id, now_iso),
            limits=limits,
        ))
    return sources


def _lowest_observation(observations, venue: str,
                        start: datetime, end: datetime):
    candidates = [obs for obs in observations
                  if obs.venue == venue and start <= obs.ts_event <= end]
    return min(candidates, key=lambda obs: obs.value) if candidates else None


def _observation_at(observations, venue: str, moment: datetime):
    for observation in observations:
        if observation.venue == venue and observation.ts_event == moment:
            return observation
    return None


def build_claims(observations, created_at: str) -> List[Claim]:
    """Demo claims, each attached to real observations of the corpus."""
    claims: List[Claim] = []

    defs = [
        ("claim-defillama-low-main", "defillama",
         "DeFiLlama aggregated USDC price"),
        ("claim-bitstamp-low-main", "bitstamp",
         "Bitstamp USDC/USD close"),
        ("claim-binance-low-main", "binance",
         "Binance USDC/USDT close"),
    ]
    for claim_id, venue, label in defs:
        observation = _lowest_observation(
            observations, venue, checks.MAIN_WINDOW_START, checks.MAIN_WINDOW_END)
        if observation is None:
            raise SystemExit("no %s observation in the main window" % venue)
        text = ("%s reached its lowest hourly value of the main window on "
                "%s: %.5f (%s)." % (label, _iso(observation.ts_event),
                                    observation.value, observation.metric))
        claims.append(models.make_claim(
            claim_id, text, [models.observation_fingerprint(observation)],
            created_at))

    before = _observation_at(observations, "defillama_supply_aggregate",
                             datetime(2023, 3, 10, tzinfo=timezone.utc))
    after = _observation_at(observations, "defillama_supply_aggregate",
                            datetime(2023, 3, 11, tzinfo=timezone.utc))
    if before is None or after is None:
        raise SystemExit("missing supply observations for 2023-03-10 / 2023-03-11")
    change = after.value - before.value
    text = ("USDC circulating supply (DeFiLlama aggregate) fell from "
            "%.0f USD on 2023-03-10 to %.0f USD on 2023-03-11 (%.0f USD, "
            "%.2f%%), a supply contraction." % (before.value, after.value,
                                                change, 100.0 * change / before.value))
    claims.append(models.make_claim(
        "claim-supply-contraction", text,
        [models.observation_fingerprint(before),
         models.observation_fingerprint(after)],
        created_at))
    return claims


def main() -> int:
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    now_iso = _iso(datetime.now(timezone.utc))
    claims_created_at = provenance_timestamp(now_iso)

    # 1. normalise the corpus ------------------------------------------------
    observations, normalization = normalize.load_observations(CORPUS_CSV)

    # 2. coverage and data gate ---------------------------------------------
    coverage = checks.hourly_coverage(observations)
    gate_examples = []
    for hour_text in GATE_EXAMPLE_HOURS:
        hour = normalize.parse_timestamp(hour_text)
        gate_examples.append(checks.data_gate(observations, hour))

    # 3. evidence graph ------------------------------------------------------
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)  # build artifact: rebuilt from the corpus each run
    sources = build_sources(observations, now_iso)
    claims = build_claims(observations, claims_created_at)
    hypothesis = Hypothesis(
        id="H1-usdc-disclosure-disorder",
        statement=("USDC experienced a genuine market dislocation in March 2023, "
                   "visible in independent venue prices and in a contraction "
                   "of circulating supply."),
        state="UNDER_TEST",
        criteria_support=[
            "at least two independent venues print a price below 0.95 USD "
            "within the main window",
            "the aggregate circulating supply contracts day over day",
        ],
        criteria_refute=[
            "no independent venue prints a price below the 0.995 USD band",
            "the supply level is flat or rising across 2023-03-10 and 2023-03-11",
        ],
    )
    relations = [
        Relation(
            id="rel-" + models.fingerprint(
                {"src": claim.id, "dst": hypothesis.id, "kind": "supports"}),
            src=claim.id, dst=hypothesis.id, kind="supports")
        for claim in claims
    ]

    with GraphStore(DB_PATH) as store:
        for source in sources:
            store.insert_source(source)
        inserted = store.bulk_insert_observations(observations)
        for claim in claims:
            store.insert_claim(claim)
        store.insert_hypothesis(hypothesis)
        for relation in relations:
            store.insert_relation(relation)
        provenance = verify_all(store)
        snapshot = store.snapshot()
        linked_claims = store.claims_for_hypothesis(hypothesis.id)

    report = {
        "generated_at": now_iso,
        "corpus": {
            "csv": os.path.relpath(CORPUS_CSV, ROOT).replace(os.sep, "/"),
            "rows": normalization["total"],
            "kept": normalization["kept"],
            "rejected": len(normalization["rejected"]),
            "flagged": len(normalization["flagged"]),
        },
        "normalization": normalization,
        "coverage": coverage,
        "data_gate_examples": gate_examples,
        "graph": {
            "database": os.path.relpath(DB_PATH, ROOT).replace(os.sep, "/"),
            "sources": [source.id for source in sources],
            "observations_inserted": inserted,
            "claims_inserted": len(claims),
            "relations_inserted": len(relations),
            "counts": snapshot["counts"],
            "snapshot": snapshot,
        },
        "provenance": provenance,
        "claims": [
            {"id": claim.id, "text": claim.text, "refs": claim.refs,
             "created_at": claim.created_at, "fingerprint": claim.fingerprint}
            for claim in claims
        ],
        "hypotheses": [{
            "id": hypothesis.id,
            "statement": hypothesis.statement,
            "state": hypothesis.state,
            "criteria_support": hypothesis.criteria_support,
            "criteria_refute": hypothesis.criteria_refute,
            "claims": [claim.id for claim in linked_claims],
        }],
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    # 5. compact summary -----------------------------------------------------
    window = coverage["window"]
    per_venue = " | ".join(
        "%s %d/%d (%.1f%%)" % (venue, data["hours_covered"], data["hours_in_window"],
                               100.0 * data["coverage_ratio"])
        for venue, data in sorted(coverage["per_venue"].items()))
    rejects = ", ".join(
        "%s (row %s)" % (item["reason"], item["row"])
        for item in normalization["rejected"]) or "none"
    flags = ", ".join(
        "%s (row %s)" % (item["flag"], item["row"])
        for item in normalization["flagged"]) or "none"

    print("ORVYREN-Core - quality + graph build (run_quality.py)")
    print("corpus       : %s" % report["corpus"]["csv"])
    print("rows         : %d read | %d kept | %d rejected | %d flagged"
          % (normalization["total"], normalization["kept"],
             report["corpus"]["rejected"], report["corpus"]["flagged"]))
    print("rejected     : %s" % rejects)
    print("flagged      : %s" % flags)
    print("counts       : " + " | ".join(
        "%s=%d" % (venue, count)
        for venue, count in normalization["counts_by_venue"].items()))
    print("coverage     : %s -> %s (%d hours)"
          % (window["start"], window["end"], window["hours"]))
    print("  per venue  : %s" % per_venue)
    print("  gate-ready : %d hours with >= 2 independent venues (%d with 3)"
          % (coverage["hours_with_two_plus_independent_venues"],
             coverage["hours_with_three_independent_venues"]))
    for example in gate_examples:
        print("  gate %s : %s%s" % (
            example["hour"], example["status"],
            " (missing %s)" % ", ".join(example["missing"])
            if example["missing"] else ""))
    print("graph        : %s - %d sources, %d observations, %d claims, "
          "%d relations, 1 hypothesis"
          % (report["graph"]["database"], len(report["graph"]["sources"]),
             inserted, len(claims), len(relations)))
    print("provenance   : %d/%d claims verified (all refs resolve)"
          % (provenance["claims_checked"] - provenance["claims_failed"],
             provenance["claims_checked"]))
    print("snapshot     : %s hash %s" % (snapshot["graph_version"], snapshot["hash"]))
    print("report       : %s" % os.path.relpath(REPORT_PATH, ROOT).replace(os.sep, "/"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
