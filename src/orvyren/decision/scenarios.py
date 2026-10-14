#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core - pre-registered scenario classification H1/H2/H3 (decision/scenarios.py).

This module turns the read-only corpus (``corpus/usdc_observations.csv``) into
the three pre-registered hypothesis verdicts of FREEZE_V1.md section 2. The
thresholds below are frozen BEFORE looking at the results; none of them is
fitted to the data. Reading order of the module mirrors that document.

Definitions (prices are USD per 1 USDC; deviation measures how far BELOW peg):

    deviation_pct(v) = (1.00 - v) / 1.00 * 100

H1 "local liquidity perturbation"
    support    : a >1.0% deviation on a single independent venue while the
                 aggregator stays within 0.5% of peg, and a return to within
                 0.1% of peg in less than 12 h;
    refutation : a >1.0% deviation persisting more than 12 h on at least two
                 independent venues (measured on contiguous hourly episodes).

H2 "broad stress on asset or issuer"
    support    : a >1.0% deviation simultaneously (same hour) on at least two
                 independent venues AND a circulating supply drop > 1% within
                 24 h;
    refutation : signals isolated to at most one venue AND no 24 h supply move.

H3 "data or market artifact"
    support    : structural inconsistency (duplicate conflicting rows,
                 non-positive values, non-UTC timestamps) or an unexplained
                 divergence between two sources of distinct nature (a venue
                 dislocation that neither another venue nor the aggregator
                 corroborates);
    refutation : at least two independent, time-concordant sources confirm the
                 movement.

Independent venues are the two exchanges (Bitstamp, Binance); DeFiLlama is the
aggregator (FREEZE_V1.md D3) and is never counted as an "independent venue".

Every verdict carries ``evidence_refs`` -- the observations actually used, as
``{timestamp_utc, venue, value}`` -- and ``missing_inputs``. A hypothesis whose
required series is absent is INCONCLUSIVE with the missing input named; it is
never guessed, and no number is produced without a provenance reference.
"""

import csv
import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# scenario.py -> decision -> orvyren -> src -> <repository root>
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# --- pre-registered constants (FREEZE_V1.md section 2: do not modify) -------
PEG_REFERENCE = 1.0              # par value the stablecoin is measured against
DEVIATION_ALERT_PCT = 1.0        # "ecart > 1 %"
AGGREGATE_TOLERANCE_PCT = 0.5    # "agregat < 0,5 % sous l'ancrage"
RECOVERY_TOLERANCE_PCT = 0.1     # "retour a +/- 0,1 %"
RECOVERY_HOURS_LIMIT = 12.0      # "... en moins de 12 h"
PERSISTENCE_HOURS_LIMIT = 12.0   # "persistant ... pendant > 12 h"
SUPPLY_DROP_PCT = 1.0            # "baisse de l'offre en circulation > 1 %"
SUPPLY_WINDOW_HOURS = 24.0       # "... en 24 h"
CONCORDANCE_WINDOW_HOURS = 2.0   # +/- window used to test source corroboration

MAX_HOURLY_GAP = timedelta(hours=1)   # a run breaks when an hourly gap appears

# --- corpus schema ----------------------------------------------------------
INDEPENDENT_VENUES = ("bitstamp", "binance")
AGGREGATOR_VENUE = "defillama"
PRICE_METRICS = ("price_usd", "close_usd", "close_usdcusdt")
SUPPLY_VENUE = "defillama_supply_aggregate"
SUPPLY_CROSS_CHECK_VENUE = "defillama_supply_ethereum"
SUPPLY_METRIC = "circulating_usd"
DEFAULT_CORPUS_RELPATH = os.path.join("corpus", "usdc_observations.csv")

# --- verdict vocabulary -----------------------------------------------------
SUPPORTED = "SUPPORTED"
REFUTED = "REFUTED"
INCONCLUSIVE = "INCONCLUSIVE"

_HOUR = 3600.0


def deviation_pct(value):
    """Distance below peg of a USD price, in percent (positive means below 1.00)."""
    return (PEG_REFERENCE - value) / PEG_REFERENCE * 100.0


def deviation_exceeds(value, threshold_pct):
    """True iff the value sits STRICTLY more than ``threshold_pct`` below peg.

    The comparison is evaluated in value space (``value < peg * (1 - pct/100)``)
    instead of comparing computed percentages: float arithmetic turns a value
    sitting exactly on the decimal boundary (0.99 for the 1% alert, present in
    the corpus) into "1.0000000000000009 %", which would wrongly count as an
    alert. Boundary values are excluded, exactly as "> 1%" reads.
    """
    return value < PEG_REFERENCE * (1.0 - threshold_pct / 100.0)


def within_tolerance(value, tolerance_pct):
    """True iff the value sits within +/- ``tolerance_pct`` of peg (boundary included)."""
    return abs(value - PEG_REFERENCE) <= PEG_REFERENCE * tolerance_pct / 100.0 + 1e-12


@dataclass(frozen=True)
class Observation:
    """One immutable corpus row (a measured value with its retrieval metadata)."""

    timestamp_utc: str      # event time, exactly as recorded in the corpus
    ts: datetime            # parsed, UTC-normalised event time
    venue: str
    metric: str
    value: float
    extra: str = ""
    retrieved_at: str = ""

    def ref(self):
        """Provenance reference of this observation: (timestamp, venue, value)."""
        return {
            "timestamp_utc": self.timestamp_utc,
            "venue": self.venue,
            "value": self.value,
        }


# ---------------------------------------------------------------------------
# corpus loading and window helpers
# ---------------------------------------------------------------------------

def resolve_corpus_path(csv_path):
    """Resolve a corpus path: absolute or cwd-relative first, then repo-relative."""
    if os.path.isabs(csv_path) or os.path.exists(csv_path):
        return csv_path
    candidate = os.path.join(_REPO_ROOT, csv_path)
    return candidate if os.path.exists(candidate) else csv_path


def load_observations(csv_path):
    """Load and validate the corpus; rows are immutable and sorted.

    Malformed rows raise ``ValueError`` with the file and line number: the
    engine prefers a loud failure over silently reasoning on bad data.
    """
    resolved = resolve_corpus_path(csv_path)
    observations = []
    with open(resolved, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"timestamp_utc", "venue", "metric", "value", "extra", "retrieved_at"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{resolved}: missing required column(s): {sorted(missing)}")
        for line_number, row in enumerate(reader, start=2):
            try:
                ts = datetime.fromisoformat(row["timestamp_utc"])
                value = float(row["value"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{resolved}:{line_number}: malformed observation ({exc})") from exc
            if ts.tzinfo is None:
                raise ValueError(f"{resolved}:{line_number}: timestamp is not timezone-aware")
            observations.append(
                Observation(
                    timestamp_utc=row["timestamp_utc"],
                    ts=ts.astimezone(timezone.utc),
                    venue=(row["venue"] or "").strip(),
                    metric=(row["metric"] or "").strip(),
                    value=value,
                    extra=row.get("extra", "") or "",
                    retrieved_at=row.get("retrieved_at", "") or "",
                )
            )
    observations.sort(key=lambda o: (o.venue, o.metric, o.ts))
    return observations


def corpus_sha256(csv_path):
    """SHA-256 of the corpus file, for the audit trail (provenance of inputs).

    The digest is computed over the LF-normalised bytes (CRLF collapsed to LF)
    so that the same logical corpus hashes identically on every platform: a
    Windows checkout with ``core.autocrlf`` writes CRLF to disk, and a raw
    bytes digest would then disagree with the repository copy. A reviewer on
    any platform can therefore reproduce the recorded digest with
    ``sha256sum`` after LF-normalising the file (which ``.gitattributes``
    already enforces for text files in this repository).
    """
    resolved = resolve_corpus_path(csv_path)
    with open(resolved, "rb") as handle:
        raw = handle.read()
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def parse_window_bound(value):
    """Accept an ISO-8601 string or a datetime; return a UTC-aware datetime."""
    if isinstance(value, datetime):
        moment = value
    elif isinstance(value, str):
        moment = datetime.fromisoformat(value.strip())
    else:
        raise TypeError(f"window bound must be a datetime or ISO-8601 string, got {type(value)!r}")
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def window_summary(window_start, window_end, label="main"):
    """JSON-serialisable window descriptor (bounds are inclusive)."""
    start = parse_window_bound(window_start)
    end = parse_window_bound(window_end)
    if start > end:
        raise ValueError(f"window start {start.isoformat()} is after window end {end.isoformat()}")
    return {
        "label": label,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "inclusive_bounds": True,
        "duration_hours": (end - start).total_seconds() / _HOUR,
        "timezone": "UTC",
    }


def observations_in_window(observations, window_start, window_end):
    """Inclusive window filter; bounds may be datetimes or ISO-8601 strings."""
    start = parse_window_bound(window_start)
    end = parse_window_bound(window_end)
    return [o for o in observations if start <= o.ts <= end]


def contiguous_episodes(series, predicate, max_gap=MAX_HOURLY_GAP):
    """Maximal runs of consecutive hourly observations satisfying ``predicate``.

    A run is broken as soon as the predicate is false OR the gap to the
    previous retained observation exceeds ``max_gap``: a "run" therefore
    always means consecutive hourly observations, never points stitched
    across a hole in the series.
    """
    episodes, current, last = [], [], None
    for observation in series:
        if predicate(observation):
            if current and (observation.ts - last.ts) > max_gap:
                episodes.append(current)
                current = []
            current.append(observation)
            last = observation
        elif current:
            episodes.append(current)
            current = []
    if current:
        episodes.append(current)
    return episodes


def integrity_flags(observations):
    """Structural inconsistencies detectable from the corpus itself.

    Checks: duplicate rows for the same (venue, metric, timestamp) with
    conflicting values, non-positive values and timestamps that are not UTC.
    Contract/unit checks need a contract field this corpus does not carry;
    that gap is reported by the caller, never silently ignored.
    """
    flags, seen = [], {}
    for observation in observations:
        key = (observation.venue, observation.metric, observation.timestamp_utc)
        previous = seen.get(key)
        if previous is not None and previous.value != observation.value:
            flags.append(
                {
                    "type": "duplicate_conflicting_observation",
                    "venue": observation.venue,
                    "metric": observation.metric,
                    "timestamp_utc": observation.timestamp_utc,
                    "values": [previous.value, observation.value],
                }
            )
        seen[key] = observation
        if observation.value <= 0:
            flags.append(
                {
                    "type": "non_positive_value",
                    "venue": observation.venue,
                    "metric": observation.metric,
                    "timestamp_utc": observation.timestamp_utc,
                    "value": observation.value,
                }
            )
        offset = observation.ts.utcoffset()
        if offset is None or offset != timedelta(0):
            flags.append(
                {
                    "type": "timestamp_not_utc",
                    "venue": observation.venue,
                    "metric": observation.metric,
                    "timestamp_utc": observation.timestamp_utc,
                }
            )
    return flags


# ---------------------------------------------------------------------------
# series helpers
# ---------------------------------------------------------------------------

def _price_series(observations, venue):
    return sorted(
        [o for o in observations if o.venue == venue and o.metric in PRICE_METRICS],
        key=lambda o: o.ts,
    )


def _supply_series(observations, venue):
    return sorted(
        [o for o in observations if o.venue == venue and o.metric == SUPPLY_METRIC],
        key=lambda o: o.ts,
    )


def _alert_observations(series):
    """Observations deviating more than the pre-registered 1% alert threshold."""
    return [o for o in series if deviation_exceeds(o.value, DEVIATION_ALERT_PCT)]


def _max_deviation_observation(series):
    return max(series, key=lambda o: deviation_pct(o.value)) if series else None


def _verdict(hypothesis_id, label, statement, support_spec, refutation_spec,
             criteria, evidence_refs, missing_inputs, details):
    """Assemble a verdict dict; the verdict follows the pre-registered logic.

    SUPPORTED wins over REFUTED; a criterion whose inputs are missing is not
    evaluable and can never fire. If neither criterion fires and an input is
    missing -> INCONCLUSIVE (missing_inputs listed); if nothing is missing the
    verdict is INCONCLUSIVE because the registered criteria do not resolve it.
    """
    if any(c["criterion"] == "support" and c["met"] for c in criteria):
        verdict = SUPPORTED
    elif any(c["criterion"] == "refutation" and c["met"] for c in criteria):
        verdict = REFUTED
    else:
        verdict = INCONCLUSIVE
    return {
        "hypothesis_id": hypothesis_id,
        "label": label,
        "statement": statement,
        "verdict": verdict,
        "support_criterion": support_spec,
        "refutation_criterion": refutation_spec,
        "criteria_evaluated": criteria,
        "evidence_refs": evidence_refs,
        "missing_inputs": missing_inputs,
        "details": details,
    }


# ---------------------------------------------------------------------------
# H1 - local liquidity perturbation
# ---------------------------------------------------------------------------

def _classify_h1(venue_series, aggregator_series):
    evidence, missing = [], []
    present_venues = [v for v in INDEPENDENT_VENUES if venue_series.get(v)]
    for venue in INDEPENDENT_VENUES:
        if not venue_series.get(venue):
            missing.append(f"{venue} hourly price series (independent venue)")

    # --- support side ------------------------------------------------------
    venue_profile = {}
    for venue in present_venues:
        series = venue_series[venue]
        max_dev = _max_deviation_observation(series)
        alerts = _alert_observations(series)
        first_alert = alerts[0] if alerts else None
        recovery, recovery_hours = None, None
        if first_alert is not None:
            for observation in series:
                if observation.ts > first_alert.ts and within_tolerance(observation.value, RECOVERY_TOLERANCE_PCT):
                    recovery, recovery_hours = observation, (observation.ts - first_alert.ts).total_seconds() / _HOUR
                    break
        venue_profile[venue] = {
            "max_deviation_pct": round(deviation_pct(max_dev.value), 6) if max_dev else None,
            "first_alert": first_alert,
            "recovery": recovery,
            "recovery_hours": recovery_hours,
        }
        for observation in (max_dev, first_alert, recovery):
            if observation is not None and observation.ref() not in evidence:
                evidence.append(observation.ref())

    aggregator_min = _max_deviation_observation(aggregator_series)
    if aggregator_min is not None and aggregator_min.ref() not in evidence:
        evidence.append(aggregator_min.ref())

    single_venue_alert = any(p["first_alert"] is not None for p in venue_profile.values())
    aggregator_within_tolerance = (
        not deviation_exceeds(aggregator_min.value, AGGREGATE_TOLERANCE_PCT) if aggregator_min else None
    )
    recovered_fast = any(
        p["recovery_hours"] is not None and p["recovery_hours"] < RECOVERY_HOURS_LIMIT
        for p in venue_profile.values()
    )
    support_evaluable = bool(present_venues) and aggregator_min is not None
    support_met = bool(support_evaluable and single_venue_alert and aggregator_within_tolerance and recovered_fast)
    support_computed = {
        "venue_deviations_above_threshold": [
            {
                "venue": v,
                "first_alert_utc": p["first_alert"].timestamp_utc if p["first_alert"] else None,
                "max_deviation_pct": p["max_deviation_pct"],
                "recovery_utc": p["recovery"].timestamp_utc if p["recovery"] else None,
                "recovery_hours": round(p["recovery_hours"], 4) if p["recovery_hours"] is not None else None,
            }
            for v, p in venue_profile.items()
        ],
        "alert_threshold_pct": DEVIATION_ALERT_PCT,
        "aggregator_min_value": aggregator_min.value if aggregator_min else None,
        "aggregator_min_deviation_pct": round(deviation_pct(aggregator_min.value), 6) if aggregator_min else None,
        "aggregator_tolerance_pct": AGGREGATE_TOLERANCE_PCT,
        "aggregator_within_tolerance": aggregator_within_tolerance,
        "recovery_limit_hours": RECOVERY_HOURS_LIMIT,
        "recovered_within_limit": recovered_fast,
    }

    # --- refutation side ---------------------------------------------------
    persistent = []
    for venue in present_venues:
        for episode in contiguous_episodes(venue_series[venue], lambda o: deviation_exceeds(o.value, DEVIATION_ALERT_PCT)):
            span_hours = (episode[-1].ts - episode[0].ts).total_seconds() / _HOUR
            if span_hours > PERSISTENCE_HOURS_LIMIT:
                persistent.append(
                    {
                        "venue": venue,
                        "start": episode[0],
                        "end": episode[-1],
                        "span_hours": span_hours,
                        "observations": len(episode),
                    }
                )
                for observation in (episode[0], episode[-1]):
                    if observation.ref() not in evidence:
                        evidence.append(observation.ref())
    persistent_venues = sorted({p["venue"] for p in persistent})
    refutation_evaluable = len(present_venues) >= 2
    refutation_met = refutation_evaluable and len(persistent_venues) >= 2

    criteria = [
        {
            "criterion": "support",
            "met": support_met,
            "evaluable": support_evaluable,
            "spec": (
                "deviation > 1.0% on a single independent venue while the aggregator stays within "
                "0.5% of peg, and recovery to within 0.1% of peg in less than 12 h"
            ),
            "computed": support_computed,
            "evidence_refs": [r for r in evidence if r["venue"] in set(present_venues) | {AGGREGATOR_VENUE}],
        },
        {
            "criterion": "refutation",
            "met": refutation_met,
            "evaluable": refutation_evaluable,
            "spec": "deviation > 1.0% persisting more than 12 h on at least two independent venues",
            "computed": {
                "persistence_limit_hours": PERSISTENCE_HOURS_LIMIT,
                "persistent_episodes": [
                    {
                        "venue": p["venue"],
                        "start_utc": p["start"].timestamp_utc,
                        "end_utc": p["end"].timestamp_utc,
                        "span_hours": round(p["span_hours"], 4),
                        "observations": p["observations"],
                    }
                    for p in persistent
                ],
                "persistent_venue_count": len(persistent_venues),
            },
            "evidence_refs": [
                ref
                for p in persistent
                for ref in (p["start"].ref(), p["end"].ref())
            ],
        },
    ]
    details = {
        "independent_venues_present": present_venues,
        "aggregator_present": aggregator_min is not None,
    }
    return _verdict(
        "H1",
        "local liquidity perturbation",
        "The dislocation is a local liquidity perturbation: one venue moves while the aggregate stays pegged, and it recovers quickly.",
        "deviation > 1% on ONE venue, aggregate within 0.5% of peg, recovery to +/-0.1% in less than 12 h",
        "deviation > 1% persisting more than 12 h on >= 2 independent venues",
        criteria,
        evidence,
        missing,
        details,
    )


# ---------------------------------------------------------------------------
# H2 - broad stress on asset or issuer
# ---------------------------------------------------------------------------

def _supply_changes(supply_series):
    """24 h supply changes on consecutive daily observations (order preserved)."""
    changes = []
    for previous, current in zip(supply_series, supply_series[1:]):
        delta_hours = (current.ts - previous.ts).total_seconds() / _HOUR
        if 0 < delta_hours <= SUPPLY_WINDOW_HOURS:
            changes.append(
                {
                    "from": previous,
                    "to": current,
                    "hours": delta_hours,
                    "change_pct": (current.value - previous.value) / previous.value * 100.0,
                }
            )
    return changes


def _simultaneous_alert_hours(venue_series, min_venues=2):
    """Hours where at least ``min_venues`` venues are simultaneously > 1% below peg.

    Alerts are counted per hour instead of intersecting the alert sets: with
    more than two venues present, an intersection would silently require
    *every* venue to alert, while the pre-registered criterion is "at least
    two independent venues". With exactly two venues both behaviours agree.
    """
    alert_sets = {
        venue: {o.ts for o in _alert_observations(series)}
        for venue, series in venue_series.items()
        if series
    }
    if len(alert_sets) < min_venues:
        return [], alert_sets
    per_hour = {}
    for hours in alert_sets.values():
        for hour in hours:
            per_hour[hour] = per_hour.get(hour, 0) + 1
    shared = sorted(hour for hour, count in per_hour.items() if count >= min_venues)
    return shared, alert_sets


def _classify_h2(venue_series, supply_series, supply_cross_series):
    evidence, missing = [], []
    present_venues = [v for v in INDEPENDENT_VENUES if venue_series.get(v)]
    for venue in INDEPENDENT_VENUES:
        if not venue_series.get(venue):
            missing.append(f"{venue} hourly price series (independent venue)")
    if not supply_series:
        missing.append(
            f"{SUPPLY_VENUE} daily circulating supply series (metric={SUPPLY_METRIC}) "
            "required for the 24 h supply-change criterion"
        )

    simultaneous_hours, alert_sets = _simultaneous_alert_hours(venue_series)
    venue_minima = {}
    for venue in present_venues:
        minima = _max_deviation_observation(venue_series[venue])
        venue_minima[venue] = minima
        if minima is not None:
            evidence.append(minima.ref())
    for hour in simultaneous_hours:
        for venue in present_venues:
            for observation in venue_series[venue]:
                if observation.ts == hour:
                    evidence.append(observation.ref())
                    break

    changes = _supply_changes(supply_series)
    biggest_drop = min(changes, key=lambda c: c["change_pct"]) if changes else None
    drop_above_threshold = biggest_drop is not None and biggest_drop["change_pct"] < -SUPPLY_DROP_PCT
    if biggest_drop is not None:
        for observation in (biggest_drop["from"], biggest_drop["to"]):
            evidence.append(observation.ref())

    # cross-check series (different nature: Ethereum-only supply); reported, never decisive
    cross_changes = _supply_changes(supply_cross_series) if supply_cross_series else []
    cross_biggest_drop = min(cross_changes, key=lambda c: c["change_pct"]) if cross_changes else None

    concurrent_alerts = len([v for v in present_venues if alert_sets.get(v)]) >= 2
    support_evaluable = len(present_venues) >= 2 and bool(supply_series)
    support_met = bool(support_evaluable and len(simultaneous_hours) >= 1 and drop_above_threshold)
    support_computed = {
        "simultaneous_alert_hours": len(simultaneous_hours),
        "simultaneous_first_utc": simultaneous_hours[0].isoformat() if simultaneous_hours else None,
        "simultaneous_last_utc": simultaneous_hours[-1].isoformat() if simultaneous_hours else None,
        "venues_with_alerts": sorted(v for v in present_venues if alert_sets.get(v)),
        "alert_threshold_pct": DEVIATION_ALERT_PCT,
        "venue_minima": {
            venue: {
                "value": minima.value if minima else None,
                "timestamp_utc": minima.timestamp_utc if minima else None,
                "deviation_pct": round(deviation_pct(minima.value), 6) if minima else None,
            }
            for venue, minima in venue_minima.items()
        },
        "supply_window_hours": SUPPLY_WINDOW_HOURS,
        "supply_drop_threshold_pct": SUPPLY_DROP_PCT,
        "max_24h_supply_drop_pct": round(biggest_drop["change_pct"], 6) if biggest_drop else None,
        "max_24h_supply_drop_from_utc": biggest_drop["from"].timestamp_utc if biggest_drop else None,
        "max_24h_supply_drop_to_utc": biggest_drop["to"].timestamp_utc if biggest_drop else None,
        "supply_drop_above_threshold": drop_above_threshold,
        "supply_cross_check": {
            "venue": SUPPLY_CROSS_CHECK_VENUE,
            "max_24h_drop_pct": round(cross_biggest_drop["change_pct"], 6) if cross_biggest_drop else None,
            "from_utc": cross_biggest_drop["from"].timestamp_utc if cross_biggest_drop else None,
            "to_utc": cross_biggest_drop["to"].timestamp_utc if cross_biggest_drop else None,
        },
    }

    venues_with_alerts = [v for v in present_venues if alert_sets.get(v)]
    refutation_evaluable = len(present_venues) >= 2 and bool(supply_series)
    refutation_met = bool(
        refutation_evaluable and len(venues_with_alerts) <= 1 and not drop_above_threshold
    )
    criteria = [
        {
            "criterion": "support",
            "met": support_met,
            "evaluable": support_evaluable,
            "spec": (
                "deviation > 1% simultaneously on >= 2 independent venues AND circulating "
                "supply drop > 1% within 24 h"
            ),
            "computed": support_computed,
            "evidence_refs": list(evidence),
        },
        {
            "criterion": "refutation",
            "met": refutation_met,
            "evaluable": refutation_evaluable,
            "spec": "signals isolated to at most one venue AND no 24 h supply change",
            "computed": {
                "venues_with_alerts": venues_with_alerts,
                "max_24h_supply_drop_pct": support_computed["max_24h_supply_drop_pct"],
                "supply_drop_above_threshold": drop_above_threshold,
            },
            "evidence_refs": [],
        },
    ]
    details = {
        "independent_venues_present": present_venues,
        "supply_series_present": bool(supply_series),
        "supply_observations": len(supply_series),
        "concurrent_alerts": concurrent_alerts,
    }
    return _verdict(
        "H2",
        "broad stress on asset or issuer",
        "The dislocation reflects broad stress on the asset or its issuer, not a local venue effect.",
        "deviation > 1% simultaneously on >= 2 independent venues AND circulating supply drop > 1% in 24 h",
        "signals isolated to one venue AND no supply evolution",
        criteria,
        evidence,
        missing,
        details,
    )


# ---------------------------------------------------------------------------
# H3 - data or market artifact
# ---------------------------------------------------------------------------

def _classify_h3(in_window_observations, venue_series, aggregator_series):
    evidence, missing = [], []
    present_venues = [v for v in INDEPENDENT_VENUES if venue_series.get(v)]
    for venue in INDEPENDENT_VENUES:
        if not venue_series.get(venue):
            missing.append(f"{venue} hourly price series (independent venue)")

    flags = integrity_flags(in_window_observations)
    for flag in flags:
        evidence.append(
            {
                "timestamp_utc": flag.get("timestamp_utc"),
                "venue": flag.get("venue"),
                "value": flag.get("value", flag.get("values")),
            }
        )

    # unexplained divergence: a venue alert that no other venue corroborates
    # (+/- 2 h) while the aggregator stays within the +/-0.1% recovery band.
    divergence = []
    for venue in present_venues:
        others = [v for v in present_venues if v != venue]
        for observation in _alert_observations(venue_series[venue]):
            corroborated = any(
                any(
                    abs((other.ts - observation.ts).total_seconds()) <= CONCORDANCE_WINDOW_HOURS * _HOUR
                    and deviation_exceeds(other.value, DEVIATION_ALERT_PCT)
                    for other in venue_series[other_venue]
                )
                for other_venue in others
            )
            nearest_aggregate = min(
                aggregator_series,
                key=lambda o: abs((o.ts - observation.ts).total_seconds()),
                default=None,
            )
            aggregator_calm = (
                nearest_aggregate is not None
                and abs((nearest_aggregate.ts - observation.ts).total_seconds()) <= _HOUR
                and within_tolerance(nearest_aggregate.value, RECOVERY_TOLERANCE_PCT)
            )
            if not corroborated and aggregator_calm:
                divergence.append({"venue": venue, "observation": observation, "aggregator": nearest_aggregate})
                if observation.ref() not in evidence:
                    evidence.append(observation.ref())
                if nearest_aggregate is not None and nearest_aggregate.ref() not in evidence:
                    evidence.append(nearest_aggregate.ref())

    support_met = bool(flags) or bool(divergence)

    simultaneous_hours, alert_sets = _simultaneous_alert_hours(venue_series)
    concordant_venues = sorted(v for v in present_venues if alert_sets.get(v) and len(simultaneous_hours) >= 1)
    for hour in (simultaneous_hours[0], simultaneous_hours[-1]) if simultaneous_hours else []:
        for venue in concordant_venues:
            for observation in venue_series[venue]:
                if observation.ts == hour and observation.ref() not in evidence:
                    evidence.append(observation.ref())
                    break
    refutation_evaluable = len(present_venues) >= 2
    refutation_met = bool(refutation_evaluable and len(concordant_venues) >= 2 and not support_met)

    criteria = [
        {
            "criterion": "support",
            "met": support_met,
            "evaluable": True,
            "spec": (
                "unit/contract/timestamp inconsistency, or an unexplained divergence between two "
                "sources of distinct nature"
            ),
            "computed": {
                "structural_flags": flags,
                "unexplained_divergences": [
                    {
                        "venue": d["venue"],
                        "timestamp_utc": d["observation"].timestamp_utc,
                        "venue_value": d["observation"].value,
                        "aggregator_value": d["aggregator"].value if d["aggregator"] else None,
                    }
                    for d in divergence
                ],
                "checks_not_possible": [
                    "contract-level verification: this corpus carries no contract/address field",
                ],
            },
            "evidence_refs": list(evidence),
        },
        {
            "criterion": "refutation",
            "met": refutation_met,
            "evaluable": refutation_evaluable,
            "spec": "at least 2 independent concordant sources confirm the movement",
            "computed": {
                "concordant_venues": concordant_venues,
                "simultaneous_alert_hours": len(simultaneous_hours),
            },
            "evidence_refs": [
                ref
                for hour in (simultaneous_hours[0], simultaneous_hours[-1]) if simultaneous_hours
                for ref in [
                    next(
                        (o.ref() for o in venue_series[venue] if o.ts == hour),
                        None,
                    )
                    for venue in concordant_venues
                ]
                if ref is not None
            ],
        },
    ]
    details = {
        "independent_venues_present": present_venues,
        "structural_flag_count": len(flags),
        "unexplained_divergence_count": len(divergence),
        "concordant_venue_count": len(concordant_venues),
    }
    return _verdict(
        "H3",
        "data or market artifact",
        "The observed movement is a data or market artifact rather than a genuine dislocation.",
        "unit/contract/timestamp inconsistency or unexplained divergence between two sources of distinct nature",
        "at least two independent concordant sources",
        criteria,
        evidence,
        missing,
        details,
    )


# ---------------------------------------------------------------------------
# public entry point
# ---------------------------------------------------------------------------

def classify_hypotheses(observations, window_start, window_end):
    """Classify H1, H2, H3 over one window; returns ``{"H1": ..., "H2": ..., "H3": ...}``.

    The result is JSON-serialisable and deterministic: same inputs, same output.
    """
    start = parse_window_bound(window_start)
    end = parse_window_bound(window_end)
    in_window = observations_in_window(observations, start, end)

    venue_series = {venue: _price_series(in_window, venue) for venue in INDEPENDENT_VENUES}
    aggregator_series = _price_series(in_window, AGGREGATOR_VENUE)
    supply_series = _supply_series(in_window, SUPPLY_VENUE)
    supply_cross_series = _supply_series(in_window, SUPPLY_CROSS_CHECK_VENUE)

    return {
        "H1": _classify_h1(venue_series, aggregator_series),
        "H2": _classify_h2(venue_series, supply_series, supply_cross_series),
        "H3": _classify_h3(in_window, venue_series, aggregator_series),
    }
