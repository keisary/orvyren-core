#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — horloge simulée du rejeu (W7, B7 §c.3).

``ReplayClock`` : le temps simulé ``t_sim`` est **strictement monotone** et
piloté par les événements du corpus ; tout objet portant ``event_time > t_sim``
est **inadmissible** (INV-PIT) — la tentative d'admission d'un objet futur
**abandonne le run** (``PITViolation``) et l'incident est écrit (un audit PIT
par run). Double horodatage obligatoire dans chaque artefact produit :
``ts_sim`` (temps simulé — sert à PIT) et ``ts_wall`` (temps réel — sert à
l'audit d'exécution). Confondre les deux est la faille classique.

``from_window()`` : ``t_sim_start`` = ouverture de fenêtre **moins la bande
d'initialisation de 24 h** (embargo de données, B7 §d.2.2) ; la fenêtre
d'initialisation sert à « réchauffer » l'état, jamais à décider.
"""

from __future__ import annotations

import datetime as _dt
import time as _time
from typing import Iterable, List, Optional, Sequence


class PITViolation(RuntimeError):
    """Objet futur admis dans un raisonnement passé — le run est abandonné.

    Le message ne contient jamais de données sensibles ; il identifie l'objet,
    son horodatage et l'instant simulé courant.
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
    """Horloge simulée : monotone stricte, événementielle, à garde PIT."""

    def __init__(self, *, t_sim_start_utc: str, t_sim_end_utc: str, run_id: str,
                 step_hours: float = 1.0, init_band_hours: int = 0) -> None:
        start = _parse_utc(t_sim_start_utc) - _dt.timedelta(hours=init_band_hours)
        end = _parse_utc(t_sim_end_utc)
        if end <= start:
            raise ValueError("fenêtre de rejeu vide ou inversée : %s → %s"
                             % (t_sim_start_utc, t_sim_end_utc))
        self._t_sim = start
        self._t_sim_window_start = start
        self._t_sim_end = end
        self._step = _dt.timedelta(hours=float(step_hours))
        self.run_id = run_id
        self.step_index = 0
        self._wall_start = _time.time()
        self._incidents: List[dict] = []

    # -- constructeurs ------------------------------------------------------
    @classmethod
    def from_window(cls, window, *, run_id: str, step_hours: float = 1.0,
                    init_band_hours: int = 24) -> "ReplayClock":
        """Depuis une ``evaluation.windows.Window`` : ouverture moins la bande.

        La bande d'initialisation de 24 h est l'embargo de données gelé
        (B7 §d.2.2) : elle nourrit l'état, jamais la décision.
        """
        return cls(t_sim_start_utc=window.start_utc, t_sim_end_utc=window.end_utc,
                   run_id=run_id, step_hours=step_hours, init_band_hours=init_band_hours)

    # -- lectures -----------------------------------------------------------
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
        """Audit PIT du run : chaque tentative d'admission future est écrite."""
        return list(self._incidents)

    # -- avance du temps ----------------------------------------------------
    def advance(self, hours: Optional[float] = None) -> str:
        """Avance d'un pas (défaut : le pas configuré), jamais au-delà de fin."""
        delta = _dt.timedelta(hours=float(hours)) if hours is not None else self._step
        if delta <= _dt.timedelta(0):
            raise ValueError("un pas d'horloge doit être strictement positif")
        new = self._t_sim + delta
        if new > self._t_sim_end:
            new = self._t_sim_end
        if new == self._t_sim:
            raise ValueError("horloge déjà à la fin de fenêtre (%s)" % self.t_sim_iso())
        self._t_sim = new
        self.step_index += 1
        return self.t_sim_iso()

    def step_to_next(self, event_stamps: Sequence[str]) -> Optional[str]:
        """Avance au prochain événement admissible (horodatage > courant).

        C'est la forme « pilotée par les événements du corpus » (B7 §c.3) :
        on saute directement à l'événement suivant, sans trous simulés.
        Renvoie le nouvel instant, ou ``None`` si aucun événement restant.
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

    # -- garde PIT ----------------------------------------------------------
    def admissible(self, event_time_utc: str) -> bool:
        return _parse_utc(event_time_utc) <= self._t_sim

    def admit(self, event_time_utc: str, *, what: str = "objet") -> None:
        """Admet un objet si ``event_time ≤ t_sim`` ; sinon abandonne le run.

        L'incident est consigné dans l'audit PIT avant de lever : le run
        redevient inspectable, mais il est **invalide** (B7 §c.3).
        """
        if self.admissible(event_time_utc):
            return
        incident = {"kind": "PIT_VIOLATION", "run_id": self.run_id,
                    "t_sim_utc": self.t_sim_iso(),
                    "event_time_utc": _format_utc(_parse_utc(event_time_utc)),
                    "what": what}
        self._incidents.append(incident)
        raise PITViolation(
            "PIT_VIOLATION: %s daté %s > t_sim %s — run abandonné (INV-PIT)"
            % (what, incident["event_time_utc"], incident["t_sim_utc"]))

    def audit(self, *, extra: Optional[dict] = None) -> dict:
        """Rapport d'audit PIT du run (un fichier par run côté appelant)."""
        return {"run_id": self.run_id,
                "window": self.window(),
                "steps": self.step_index,
                "violations": self.incidents(),
                "valid": not self._incidents,
                "ts_wall_utc": self.t_wall_iso(),
                **(extra or {})}
