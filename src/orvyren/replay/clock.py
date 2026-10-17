#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — simulated replay clock (W7, B7 §c.3).

``ReplayClock``: simulated time ``t_sim`` is **strictly monotonic** and driven
by corpus events; any object carrying ``event_time > t_sim`` is
**inadmissible** (INV-PIT) — attempting to admit a future object **aborts the
run** (``PITViolation``) and the incident is recorded (one PIT audit per run).
Every produced artifact must carry a dual timestamp: ``ts_sim`` (simulated
time — used for PIT) and ``ts_wall`` (real time — used for the execution
audit). Confusing the two is the classic failure mode.

``from_window()``: ``t_sim_start`` = window opening **minus the 24 h
initialisation band** (data embargo, B7 §d.2.2); the initialisation window
"warms up" state, it never decides anything.
"""

from __future__ import annotations

import datetime as _dt
import time as _time
from typing import Iterable, List, Optional, Sequence


class PITViolation(RuntimeError):
    """A future object admitted into a past reasoning step — the run is aborted.

    The message never contains sensitive data; it identifies the object, its
    timestamp and the current simulated instant.
    """


def _parse_utc(stamp: str) -> _dt.datetime:
    text = str(stamp).replace("Z", "+00:00")
    parsed = _dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_dt.timezone.utc)
    return parsed.astimezone(_dt.timezone.utc)


def _format_utc(moment: _dt.datetime) -> str:
    return moment.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ReplayClock:
    """Simulated clock: strictly monotonic, event-driven, with a PIT guard."""

    def __init__(self, *, t_sim_start_utc: str, t_sim_end_utc: str, run_id: str,
                 step_hours: float = 1.0, init_band_hours: int = 0) -> None:
        start = _parse_utc(t_sim_start_utc) - _dt.timedelta(hours=init_band_hours)
        end = _parse_utc(t_sim_end_utc)
        if end <= start:
            raise ValueError("empty or inverted replay window: %s → %s"
                             % (t_sim_start_utc, t_sim_end_utc))
        self._t_sim = start
        self._t_sim_window_start = start
        self._t_sim_end = end
        self._step = _dt.timedelta(hours=float(step_hours))
        self.run_id = run_id
        self.step_index = 0
        self._wall_start = _time.time()
        self._incidents: List[dict] = []

    # -- constructors -------------------------------------------------------
    @classmethod
    def from_window(cls, window, *, run_id: str, step_hours: float = 1.0,
                    init_band_hours: int = 24) -> "ReplayClock":
        """From an ``evaluation.windows.Window``: opening minus the band.

        The 24 h initialisation band is the frozen data embargo
        (B7 §d.2.2): it feeds state, never the decision.
        """
        return cls(t_sim_start_utc=window.start_utc, t_sim_end_utc=window.end_utc,
                   run_id=run_id, step_hours=step_hours, init_band_hours=init_band_hours)

    # -- readers ------------------------------------------------------------
    @property
    def t_sim(self) -> _dt.datetime:
        return self._t_sim

    def t_sim_iso(self) -> str:
        return _format_utc(self._t_sim)

    def t_wall_iso(self) -> str:
        return _format_utc(_dt.datetime.now(_dt.timezone.utc))

    def t_wall_elapsed_s(self) -> float:
        return round(_time.time() - self._wall_start, 3)

    def window(self) -> dict:
        return {"t_sim_start_utc": _format_utc(self._t_sim_window_start),
                "t_sim_end_utc": _format_utc(self._t_sim_end)}

    def incidents(self) -> List[dict]:
        """PIT audit for the run: every attempt to admit a future object is written."""
        return list(self._incidents)

    # -- time advance -------------------------------------------------------
    def advance(self, hours: Optional[float] = None) -> str:
        """Advance one step (default: the configured one), never past the end."""
        delta = _dt.timedelta(hours=float(hours)) if hours is not None else self._step
        if delta <= _dt.timedelta(0):
            raise ValueError("a clock step must be strictly positive")
        new = self._t_sim + delta
        if new > self._t_sim_end:
            new = self._t_sim_end
        if new == self._t_sim:
            raise ValueError("clock already at end of window (%s)" % self.t_sim_iso())
        self._t_sim = new
        self.step_index += 1
        return self.t_sim_iso()

    def step_to_next(self, event_stamps: Sequence[str]) -> Optional[str]:
        """Advance to the next admissible event (timestamp > current).

        This is the "corpus-event-driven" form (B7 §c.3): we jump straight to
        the next event, with no simulated gaps.
        Returns the new instant, or ``None`` if no event remains.
        """
        current = self._t_sim
        upcoming = sorted(_parse_utc(stamp) for stamp in event_stamps
                          if _parse_utc(stamp) > current)
        if not upcoming:
            return None
        target = min(upcoming[0], self._t_sim_end)
        if target == self._t_sim:
            return None
        self._t_sim = target
        self.step_index += 1
        return self.t_sim_iso()

    # -- PIT guard ----------------------------------------------------------
    def admissible(self, event_time_utc: str) -> bool:
        return _parse_utc(event_time_utc) <= self._t_sim

    def admit(self, event_time_utc: str, *, what: str = "object") -> None:
        """Admit an object if ``event_time ≤ t_sim``; otherwise abort the run.

        The incident is logged in the PIT audit before raising: the run stays
        inspectable, but it is **invalid** (B7 §c.3).
        """
        if self.admissible(event_time_utc):
            return
        incident = {"kind": "PIT_VIOLATION", "run_id": self.run_id,
                    "t_sim_utc": self.t_sim_iso(),
                    "event_time_utc": _format_utc(_parse_utc(event_time_utc)),
                    "what": what}
        self._incidents.append(incident)
        raise PITViolation(
            "PIT_VIOLATION: %s dated %s > t_sim %s — run aborted (INV-PIT)"
            % (what, incident["event_time_utc"], incident["t_sim_utc"]))

    def audit(self, *, extra: Optional[dict] = None) -> dict:
        """PIT audit report for the run (one file per run on the caller side)."""
        return {"run_id": self.run_id,
                "window": self.window(),
                "steps": self.step_index,
                "violations": self.incidents(),
                "valid": not self._incidents,
                "ts_wall_utc": self.t_wall_iso(),
                **(extra or {})}
