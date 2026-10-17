"""Hourly coverage and the data gate for the main corpus window (ORVYREN-Core).

What this module answers, with measurements instead of assumptions:

* how many hours of the main window (2023-03-09T00:00Z -> 2023-03-15T00:00Z)
  each venue actually covers;
* how many hours carry a price from at least two *independent* venues
  (DeFiLlama, Binance, Bitstamp) — the count a decision may rely on;

NOTE on wording: here "independent" means each of the three price producers
is counted separately from the others. The decision layer
(``decision/scenarios.py``) reserves "independent venues" for the two
exchanges and treats DeFiLlama as an aggregator (FREEZE_V1 D3) — the two
counts answer different questions ("was there multi-source data?" vs "did
two exchanges corroborate?") and must not be conflated when reading reports.
* :func:`data_gate` — for one hour, may a decision be taken on this data?

Window convention: both bounds are counted as hour slots, because the
collector archived an observation at the closing bound (the main window holds
6 full days + the closing hour = 145 slots). A window of half-open type would
silently drop the last archived hour.

Standard library only.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from orvyren.quality.normalize import PRICE_METRICS, Observation

__all__ = [
    "MAIN_WINDOW_START",
    "MAIN_WINDOW_END",
    "INDEPENDENT_PRICE_VENUES",
    "MIN_INDEPENDENT_VENUES",
    "hour_floor",
    "window_hours",
    "hours_by_venue",
    "hourly_coverage",
    "hours_with_min_venues",
    "data_gate",
]

MAIN_WINDOW_START = datetime(2023, 3, 9, 0, 0, tzinfo=timezone.utc)
MAIN_WINDOW_END = datetime(2023, 3, 15, 0, 0, tzinfo=timezone.utc)

#: Venues whose price is treated as an independent measurement.
INDEPENDENT_PRICE_VENUES: Tuple[str, ...] = ("defillama", "binance", "bitstamp")

#: Minimum number of independent venues required for the gate to be OK.
MIN_INDEPENDENT_VENUES = 2


def hour_floor(ts: datetime) -> datetime:
    """Floor a timestamp to its UTC hour.

    A naive timestamp is read as UTC (same convention as
    ``normalize.parse_timestamp``) — never as local wall time, which would
    make the result machine-dependent.
    """
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


def window_hours(
    start: datetime = MAIN_WINDOW_START,
    end: datetime = MAIN_WINDOW_END,
) -> List[datetime]:
    """Every hour slot of the window, both bounds included."""
    start_h = hour_floor(start)
    end_h = hour_floor(end)
    hours = []
    current = start_h
    while current <= end_h:
        hours.append(current)
        current += timedelta(hours=1)
    return hours


def hours_by_venue(
    observations: Iterable[Observation],
    start: datetime = MAIN_WINDOW_START,
    end: datetime = MAIN_WINDOW_END,
) -> Dict[str, set]:
    """Map each venue seen in the window to the set of hours it covers."""
    start_h = hour_floor(start)
    end_h = hour_floor(end)
    per_venue: Dict[str, set] = {}
    for observation in observations:
        hour = hour_floor(observation.ts_event)
        if hour < start_h or hour > end_h:
            continue
        per_venue.setdefault(observation.venue, set()).add(hour)
    return per_venue


def _venue_observations(observations: Iterable[Observation], start: datetime,
                        end: datetime) -> Dict[str, List[Observation]]:
    start_h = hour_floor(start)
    end_h = hour_floor(end)
    per_venue: Dict[str, List[Observation]] = {}
    for observation in observations:
        hour = hour_floor(observation.ts_event)
        if hour < start_h or hour > end_h:
            continue
        per_venue.setdefault(observation.venue, []).append(observation)
    return per_venue


def hourly_coverage(
    observations: Iterable[Observation],
    start: datetime = MAIN_WINDOW_START,
    end: datetime = MAIN_WINDOW_END,
) -> Dict[str, object]:
    """Measure the hourly coverage of the window, per venue and combined.

    Returns a JSON-ready dict:

    ``window``        window bounds and number of hour slots;
    ``per_venue``     hours covered / hours in window, ratio, first and last
                      hour, observation count and metrics seen;
    ``hours_by_independent_venue_count``  how many hours carry exactly 1, 2 or
                      3 independent-venue prices;
    ``hours_with_two_plus_independent_venues``  the headline number.
    """
    hours = window_hours(start, end)
    n_hours = len(hours)
    per_venue = _venue_observations(observations, start, end)

    coverage: Dict[str, object] = {}
    for venue, obs_list in sorted(per_venue.items()):
        venue_hours = {hour_floor(o.ts_event) for o in obs_list}
        coverage[venue] = {
            "hours_covered": len(venue_hours),
            "hours_in_window": n_hours,
            "coverage_ratio": round(len(venue_hours) / n_hours, 4),
            "first_hour": min(venue_hours).isoformat(),
            "last_hour": max(venue_hours).isoformat(),
            "observations": len(obs_list),
            "metrics": sorted({o.metric for o in obs_list}),
        }

    by_count: Dict[int, int] = {}
    multi_venue_hours: List[datetime] = []
    for hour in hours:
        present = _independent_venues_at(per_venue, hour)
        by_count[len(present)] = by_count.get(len(present), 0) + 1
        if len(present) >= MIN_INDEPENDENT_VENUES:
            multi_venue_hours.append(hour)

    return {
        "window": {
            "start": hour_floor(start).isoformat(),
            "end": hour_floor(end).isoformat(),
            "hours": n_hours,
        },
        "per_venue": coverage,
        "independent_price_venues": list(INDEPENDENT_PRICE_VENUES),
        "hours_by_independent_venue_count": {
            str(k): by_count.get(k, 0) for k in sorted(by_count)
        },
        "hours_with_two_plus_independent_venues": len(multi_venue_hours),
        "hours_with_three_independent_venues": by_count.get(
            len(INDEPENDENT_PRICE_VENUES), 0),
        "first_two_venue_hour": multi_venue_hours[0].isoformat() if multi_venue_hours else None,
        "last_two_venue_hour": multi_venue_hours[-1].isoformat() if multi_venue_hours else None,
    }


def _independent_venues_at(per_venue: Dict[str, List[Observation]],
                           hour: datetime) -> List[str]:
    """Independent price venues holding a price observation at ``hour``."""
    present = set()
    for venue in INDEPENDENT_PRICE_VENUES:
        for observation in per_venue.get(venue, ()):
            if observation.metric in PRICE_METRICS and hour_floor(observation.ts_event) == hour:
                present.add(venue)
                break
    return sorted(present)


def hours_with_min_venues(
    observations: Iterable[Observation],
    min_venues: int = MIN_INDEPENDENT_VENUES,
    start: datetime = MAIN_WINDOW_START,
    end: datetime = MAIN_WINDOW_END,
) -> List[datetime]:
    """Hours of the window with at least ``min_venues`` independent prices."""
    per_venue = _venue_observations(observations, start, end)
    return [
        hour for hour in window_hours(start, end)
        if len(_independent_venues_at(per_venue, hour)) >= min_venues
    ]


def data_gate(
    observations: Iterable[Observation],
    hour: datetime,
) -> Dict[str, object]:
    """May a decision rely on the data of ``hour``?

    ``OK`` requires a price from at least ``MIN_INDEPENDENT_VENUES``
    independent venues at that hour; otherwise ``INSUFFICIENT`` and
    ``missing`` names the independent venues with no price at that hour.
    The answer is deterministic and reads only the observations it is given.
    """
    target = hour_floor(hour)
    per_venue = _venue_observations(observations, target, target)
    present = _independent_venues_at(per_venue, target)
    missing = [venue for venue in INDEPENDENT_PRICE_VENUES if venue not in present]
    status = "OK" if len(present) >= MIN_INDEPENDENT_VENUES else "INSUFFICIENT"
    return {
        "hour": target.isoformat(),
        "status": status,
        "missing": missing,
        "venues_present": present,
    }
