"""Bitemporal clocks and as-of queries over relation records (B2 §1.3).

Two query modes, formally distinct (documented and tested):

1. **"The world at T"** — :func:`world_at`: records whose world-validity
   interval contains T (``valid_from <= T < valid_to``; null ends are open).
   Rebuilds the real state (exposure on 2026-04-18 17:35).
2. **"What was known at T"** — :func:`known_at`: the latest revision of each
   relation whose ``inserted_at <= T``. Serves replayed (PIT) decisions.
3. **The PIT decision set** — :func:`pit_at`: the intersection used by the
   decision engine — *the state of the world as it could be known*. This is
   the INV-PIT invariant of the cross review: *changing the future, or a
   revision published after ``as_of``, never changes a past decision*.

On-chain, the PIT clock is the block: a fact anchored in ``ChainRef`` is
replayable exactly (block monotonicity gives PIT by construction). The
``ts_published`` clock of documents (B2 §1.3) belongs to the document object
of the extraction pipeline (W2) and is not modelled here.

Standard library only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Tuple, Union

from orvyren.graph.record import RelationRecord, parse_ts

__all__ = ["AsOf", "world_at", "known_at", "pit_at"]

#: An as-of moment: ISO-8601 text or datetime (naive = UTC).
AsOf = Union[str, datetime]


def _t(value: AsOf) -> datetime:
    """Normalise an as-of moment to an aware UTC datetime."""
    if isinstance(value, str):
        return parse_ts(value)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _covers(record: RelationRecord, moment: datetime) -> bool:
    """True when ``moment`` is inside [valid_from, valid_to) (null = open)."""
    if record.valid_from is not None and parse_ts(record.valid_from) > moment:
        return False
    if record.valid_to is not None and moment >= parse_ts(record.valid_to):
        return False
    return True


def _latest_known(records: Iterable[RelationRecord],
                  moment: datetime) -> Tuple[RelationRecord, ...]:
    """Latest revision of each relation whose inserted_at <= moment."""
    latest = {}
    for record in records:
        if parse_ts(record.inserted_at) > moment:
            continue
        current = latest.get(record.relation_id)
        if current is None or record.revision > current.revision:
            latest[record.relation_id] = record
    return tuple(latest[key] for key in sorted(latest))


def world_at(records: Iterable[RelationRecord],
             as_of: AsOf) -> Tuple[RelationRecord, ...]:
    """Mode 1 — "the world at T": every revision valid at T."""
    moment = _t(as_of)
    return tuple(r for r in records if _covers(r, moment))


def known_at(records: Iterable[RelationRecord],
             as_of: AsOf) -> Tuple[RelationRecord, ...]:
    """Mode 2 — "what was known at T": latest revision known at T."""
    return _latest_known(records, _t(as_of))


def pit_at(records: Iterable[RelationRecord],
           as_of: AsOf) -> Tuple[RelationRecord, ...]:
    """Mode 3 — PIT decision set: state of the world as knowable at T.

    The intersection (B2 §1.3 SQL): latest revision known at T, then the
    world-validity filter. INV-PIT holds by construction: records inserted
    after T, and revisions published after T, are invisible at T.
    """
    moment = _t(as_of)
    return tuple(r for r in _latest_known(records, moment) if _covers(r, moment))
