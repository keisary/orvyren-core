"""Normalisation and validation of archived corpus rows (ORVYREN-Core).

Every row of the archived CSV is either kept or rejected *explicitly*: the
loader never drops a row silently. Rows that parse but look suspicious are
kept and reported as flagged, so an auditor can decide what to do with them.

Rules
-----
* missing or non-numeric ``value``            -> REJECTED
* non-finite ``value`` (``nan`` / ``inf``)    -> REJECTED
* metric whose unit is not declared           -> REJECTED
* missing venue, or unparsable timestamp      -> REJECTED
* price outside [0.50, 1.50]                  -> FLAG_PRICE_RANGE (kept)
* duplicate ``(venue, metric, ts_event)``     -> FLAG_DUPLICATE  (kept)

Only ``REJECTED`` rows leave the returned observation list; flagged rows stay
in it and are listed in the report, which is what makes the decision auditable.

Conventions
-----------
* ``row`` in the report is the 1-based physical line number of the CSV file
  (line 1 is the header), so any finding maps back to an exact line.
* ``ts_event`` is a timezone-aware UTC ``datetime``; a timestamp without an
  explicit offset is read as UTC. ``retrieved_at`` keeps the raw archive
  string.
* ``source_id`` is derived from the venue through ``VENUE_SOURCES`` so that
  observations resolve to a source row in the graph store.

Standard library only.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

__all__ = [
    "METRIC_UNITS",
    "PRICE_METRICS",
    "PRICE_RANGE",
    "VENUE_SOURCES",
    "REJECTED",
    "FLAG_PRICE_RANGE",
    "FLAG_DUPLICATE",
    "Observation",
    "parse_timestamp",
    "load_observations",
]

# --- metric units -----------------------------------------------------------

#: Declared unit of every metric name accepted by the corpus.
METRIC_UNITS = {
    "price_usd": "usd",                  # DeFiLlama aggregated historical price
    "close_usd": "usd",                  # Bitstamp USDC/USD hourly close
    "close_usdcusdt": "usdc_per_usdt",   # Binance pair: a relative price
    "circulating_usd": "usd",            # DeFiLlama circulating supply
}

#: Metrics that are prices (and therefore subject to PRICE_RANGE).
PRICE_METRICS: Tuple[str, ...] = ("price_usd", "close_usd", "close_usdcusdt")

#: Plausible hourly USDC price band; anything outside is flagged, not deleted.
PRICE_RANGE: Tuple[float, float] = (0.50, 1.50)

# --- venue -> graph source id ----------------------------------------------

#: Venue column value -> source id used by ``graph.store``. The two supply
#: venues share one source (same provider, same endpoint family), which keeps
#: the demo graph at four independent sources.
VENUE_SOURCES = {
    "defillama": "defillama",
    "binance": "binance",
    "bitstamp": "bitstamp",
    "defillama_supply_aggregate": "defillama_supply",
    "defillama_supply_ethereum": "defillama_supply",
}

# --- finding kinds ----------------------------------------------------------

REJECTED = "REJECTED"
FLAG_PRICE_RANGE = "FLAG_PRICE_RANGE"
FLAG_DUPLICATE = "FLAG_DUPLICATE"


@dataclass(frozen=True)
class Observation:
    """One normalised corpus observation.

    ``ts_event`` is when the value was measured (UTC), ``retrieved_at`` is
    when the collector fetched it (raw ISO-8601 string of the archive).
    """

    venue: str
    metric: str
    ts_event: datetime
    value: float
    extra: str
    retrieved_at: str
    source_id: str

    @property
    def unit(self) -> str:
        """Declared unit of the metric (see ``METRIC_UNITS``)."""
        return METRIC_UNITS[self.metric]

    @property
    def ts_event_iso(self) -> str:
        """Event timestamp as an ISO-8601 UTC string."""
        return self.ts_event.astimezone(timezone.utc).isoformat()

    @property
    def is_price(self) -> bool:
        """True when the metric is a price (subject to the price band)."""
        return self.metric in PRICE_METRICS


def parse_timestamp(raw: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 string into an aware UTC datetime.

    Returns ``None`` when the text is empty or not parsable. A timestamp
    without an explicit offset is interpreted as UTC.
    """
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        ts = datetime.fromisoformat(text)
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _reject(report: dict, row_no: int, reason: str) -> None:
    report["rejected"].append({"row": row_no, "reason": reason})


def _flag(report: dict, row_no: int, flag: str, detail: str) -> None:
    report["flagged"].append({"row": row_no, "flag": flag, "detail": detail})


def load_observations(csv_path: str) -> Tuple[List[Observation], Dict[str, object]]:
    """Load and validate the archived corpus CSV.

    Returns ``(observations, report)`` where ``observations`` contains every
    row that parsed successfully (including flagged ones) and ``report`` is a
    JSON-ready dict with ``total``, ``kept``, ``rejected``, ``flagged``,
    ``counts_by_venue`` and ``counts_by_metric``.

    ``counts_by_venue`` / ``counts_by_metric`` count the *kept* observations.
    """
    observations: List[Observation] = []
    report: Dict[str, object] = {
        "total": 0,
        "kept": 0,
        "rejected": [],
        "flagged": [],
        "counts_by_venue": {},
        "counts_by_metric": {},
    }
    seen_keys = set()
    count_venue: Dict[str, int] = {}
    count_metric: Dict[str, int] = {}

    with open(csv_path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_no, row in enumerate(reader, start=2):
            report["total"] += 1  # type: ignore[operator]

            raw_value = (row.get("value") or "").strip()
            if not raw_value:
                _reject(report, row_no, "missing_value")
                continue
            try:
                value = float(raw_value)
            except ValueError:
                _reject(report, row_no, "non_numeric_value:%s" % raw_value)
                continue
            if not math.isfinite(value):
                _reject(report, row_no, "non_finite_value:%s" % raw_value)
                continue

            venue = (row.get("venue") or "").strip()
            if not venue:
                _reject(report, row_no, "missing_field:venue")
                continue

            metric = (row.get("metric") or "").strip()
            if metric not in METRIC_UNITS:
                _reject(report, row_no, "unknown_metric_unit:%s" % (metric or "<empty>"))
                continue

            ts_event = parse_timestamp(row.get("timestamp_utc"))
            if ts_event is None:
                _reject(report, row_no, "invalid_timestamp:%s"
                        % ((row.get("timestamp_utc") or "").strip() or "<empty>"))
                continue

            observation = Observation(
                venue=venue,
                metric=metric,
                ts_event=ts_event,
                value=value,
                extra=(row.get("extra") or "").strip(),
                retrieved_at=(row.get("retrieved_at") or "").strip(),
                source_id=VENUE_SOURCES.get(venue, venue),
            )

            key = (venue, metric, ts_event)
            if key in seen_keys:
                _flag(report, row_no, FLAG_DUPLICATE,
                      "duplicate of earlier row for %s|%s|%s"
                      % (venue, metric, observation.ts_event_iso))
            seen_keys.add(key)

            if metric in PRICE_METRICS and not (PRICE_RANGE[0] <= value <= PRICE_RANGE[1]):
                _flag(report, row_no, FLAG_PRICE_RANGE,
                      "%s outside [%s, %s]" % (value, PRICE_RANGE[0], PRICE_RANGE[1]))

            observations.append(observation)
            count_venue[venue] = count_venue.get(venue, 0) + 1
            count_metric[metric] = count_metric.get(metric, 0) + 1

    report["kept"] = len(observations)
    report["counts_by_venue"] = dict(sorted(count_venue.items()))
    report["counts_by_metric"] = dict(sorted(count_metric.items()))
    return observations, report
