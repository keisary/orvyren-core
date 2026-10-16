#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — registre des fenêtres DEV/EVAL et embargos (G3).

Sources normatives : B7 §d.1 (tableau définitif des jeux), §d.2 (les quatre
embargos + vérification mécanique), FREEZE_V2 §7 (G1–G4), DOC2 §5.8.4.

Quatre embargos, quatre vérificateurs :

1. **paramètres** — aucune constante de G1–G6 n'est modifiable après la
   première exécution EVAL (contrôlé par :func:`verify_frozen_package` +
   :func:`eval_run_gate`) ;
2. **données (24 h)** — la bande de 24 h précédant chaque fenêtre EVAL est
   retirée du DEV (:func:`data_embargo_violations`) ;
3. **inspection** — les fenêtres EVAL ne sont ni inspectées ni utilisées pour
   régler quoi que ce soit (hors périmètre du code : engagement écrit en G3) ;
4. **calibration croisée** — les mois servant à calibrer des seuils (quantiles)
   ne peuvent chevaucher une fenêtre CALME d'évaluation
   (:func:`cross_calibration_violations`).

Une fenêtre n'est enregistrée ici **que si sa source est traçable** (fichier du
dépôt ou décision gelée citée). Ce qui n'est pas dérivable est listé
``À FIGER — NOT DONE`` avec le motif, jamais inventé.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

SET_DEV = "dev"
SET_EVAL = "eval"
SETS = (SET_DEV, SET_EVAL)

KIND_STRESS = "stress"
KIND_CALME = "calme"
KIND_TEMOIN = "temoin"

#: Bande d'embargo de données avant chaque fenêtre EVAL (B7 §d.2.2).
DATA_EMBARGO_HOURS = 24

#: Noms canoniques du paquet de gel (frozen/Gx.sha256, format sha256sum).
FROZEN_FILES = ("G1", "G2", "G3", "G4", "G5", "G6")

#: Mention obligatoire d'une ré-exécution EVAL forcée (B7 §d.2.5).
FORCED_RERUN_MENTION = "évaluation ré-exécutée (invalide pour la revendication)"


class WindowError(ValueError):
    """Fenêtre mal formée ou chevauchement interdit."""


class FreezeGateError(RuntimeError):
    """Paquet de gel absent, incomplet ou non concordant — écriture refusée."""


def parse_utc(stamp: str) -> _dt.datetime:
    """Horodatage ISO-8601 (``Z`` ou offset) → ``datetime`` UTC conscient."""
    text = stamp.replace("Z", "+00:00")
    parsed = _dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_dt.timezone.utc)
    return parsed.astimezone(_dt.timezone.utc)


def format_utc(moment: _dt.datetime) -> str:
    """``datetime`` UTC → horodatage canonique ``YYYY-MM-DDTHH:MM:SSZ``."""
    return moment.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_parse = parse_utc  # alias interne historique


@dataclass(frozen=True)
class Window:
    """Fenêtre d'évaluation : bornes UTC, jeu, rôle, provenance."""

    window_id: str
    episode_id: str
    set_label: str
    kind: str
    start_utc: str
    end_utc: str
    sources: Tuple[str, ...]
    role: str
    note: str = ""

    def __post_init__(self):
        if self.set_label not in SETS:
            raise WindowError(f"jeu inconnu : {self.set_label!r}")
        if _parse(self.end_utc) <= _parse(self.start_utc):
            raise WindowError(f"fenêtre vide ou inversée : {self.window_id}")

    @property
    def start(self) -> _dt.datetime:
        return _parse(self.start_utc)

    @property
    def end(self) -> _dt.datetime:
        return _parse(self.end_utc)

    def overlaps(self, other: "Window") -> bool:
        """Chevauchement d'intervalles **fermés** (bornes incluses)."""
        return self.start < other.end and other.start < self.end

    def intersects(self, start_utc: str, end_utc: str) -> bool:
        start, end = _parse(start_utc), _parse(end_utc)
        return self.start < end and start < self.end

    def duration_hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600.0


# --- registre ----------------------------------------------------------------
# Toute ligne cite sa source : B7 §d.1 (tableau des jeux) ou fichier du dépôt.
# Aucune fenêtre EVAL « calme 2025–2026 » n'est enregistrée : sa liste exacte
# est un point ouvert du gel (B7 Q6) — voir PENDING_WINDOWS ci-dessous.

DEV_WINDOWS: Tuple[Window, ...] = (
    Window(
        window_id="dev-usdc-2023-03",
        episode_id="usdc-2023-03",
        set_label=SET_DEV,
        kind=KIND_STRESS,
        start_utc="2023-03-10T00:00:00Z",
        end_utc="2023-03-14T00:00:00Z",
        sources=("evidence/episode_usdc_2023-03.json", "corpus/usdc_observations.csv"),
        role="Episode de développement n°1 (B7 §d.1) : régler les seuils, déboguer, mesurer les coûts ; contamination assumée.",
    ),
    Window(
        window_id="dev-usdc-2023-02-temoin",
        episode_id="usdc-2023-02",
        set_label=SET_DEV,
        kind=KIND_TEMOIN,
        start_utc="2023-02-15T00:00:00Z",
        end_utc="2023-02-18T00:00:00Z",
        sources=("corpus/usdc_observations.csv", "corpus/manifest.json"),
        role="Fenêtre témoin de la règle gelée AX0 (FREEZE_V1 D7 ; baseline_report.json : 0 signal).",
        note=(
            "Critère CALME gelé (max|P−1| < 0,5 %) NON satisfait sur cette fenêtre : "
            "reclassée STRESS par application mécanique du critère (B7 §d.1) — mesure dans frozen/G3."
        ),
    ),
    Window(
        window_id="dev-steth-2022-06",
        episode_id="steth-2022-06",
        set_label=SET_DEV,
        kind=KIND_STRESS,
        start_utc="2022-05-09T00:00:00Z",
        end_utc="2022-07-31T00:00:00Z",
        sources=("evidence/episode_steth_2022-06.json",),
        role="Backtest long DEV (B7 §d.1) : contrôle de longue série, non-régression des seuils.",
    ),
    Window(
        window_id="dev-steth-2022-05-calme",
        episode_id="steth-2022-06",
        set_label=SET_DEV,
        kind=KIND_CALME,
        start_utc="2022-05-01T00:00:00Z",
        end_utc="2022-05-08T00:00:00Z",
        sources=("evidence/episode_steth_2022-06.json",),
        role="Fenêtre calme DEV sur la série de décote réalisable stETH (critère CALME gelé satisfait — mesure dans frozen/G3).",
    ),
)

EVAL_WINDOWS: Tuple[Window, ...] = (
    Window(
        window_id="eval-rseth-2026-04",
        episode_id="rseth-2026-04",
        set_label=SET_EVAL,
        kind=KIND_STRESS,
        start_utc="2026-04-17T00:00:00Z",
        end_utc="2026-04-21T00:00:00Z",
        sources=("evidence/episode_rseth_2026-04.json", "B7 §d.1"),
        role="EVALUATION n°1 (principale) — exécution unique après gel ; abstention post-gel = réponse attendue.",
    ),
    Window(
        window_id="eval-usd0pp-2025-01",
        episode_id="usd0pp-2025-01",
        set_label=SET_EVAL,
        kind=KIND_STRESS,
        start_utc="2025-01-08T00:00:00Z",
        end_utc="2025-01-31T00:00:00Z",
        sources=("B7 §d.1",),
        role="EVALUATION n°2 (secondaire) — mécanisme différent (débasement contractuel) ; contamination probable assumée.",
        note="Série de prix à assembler hors dépôt (W3-C) : l'exécution EVAL est conditionnée par la garde de gel.",
    ),
)

#: Fenêtres non enregistrées faute de source dérivable — NOT DONE, motif écrit.
PENDING_WINDOWS: Tuple[dict, ...] = (
    {
        "window_id": "eval-calme-2025-2026 (≥ 6)",
        "status": "NOT DONE",
        "reason": (
            "Liste exacte et bornes des fenêtres CALME EVAL à figer (B7 Q6 / FREEZE_V2 §11.5) : "
            "exige le critère CALME appliqué à des séries 2025–2026 non encore archivées dans le dépôt. "
            "Aucune fenêtre n'est inventée."
        ),
    },
    {
        "window_id": "dev-calme-2022-2023 (≥ 6)",
        "status": "PARTIEL",
        "reason": (
            "Une seule fenêtre calme DEV est dérivable aujourd'hui (dev-steth-2022-05-calme, critère satisfait). "
            "La fenêtre témoin USDC échoue au critère CALME gelé (reclassée STRESS). "
            "Les fenêtres calmes restantes dépendent d'un chantier de collecte (R3 §C.8)."
        ),
    },
)


# --- embargos ----------------------------------------------------------------


def overlap_violations(windows: Sequence[Window]) -> List[Tuple[str, str]]:
    """Chevauchements interdits au sein d'un même jeu (R3 §B.3 : fenêtres appariées disjointes)."""
    pairs: List[Tuple[str, str]] = []
    for i, left in enumerate(windows):
        for right in windows[i + 1 :]:
            if left.overlaps(right):
                pairs.append((left.window_id, right.window_id))
    return pairs


def check_no_overlap(windows: Sequence[Window]) -> None:
    """Lève :class:`WindowError` si deux fenêtres du jeu se chevauchent."""
    pairs = overlap_violations(windows)
    if pairs:
        raise WindowError(f"chevauchement de fenêtres interdit : {pairs}")


def data_embargo_violations(
    dev_windows: Sequence[Window],
    eval_windows: Sequence[Window],
    band_hours: int = DATA_EMBARGO_HOURS,
) -> List[dict]:
    """Embargo de données : la bande ``[start − 24 h, start]`` de chaque fenêtre
    EVAL ne doit croiser **aucune** fenêtre DEV (B7 §d.2.2)."""
    violations: List[dict] = []
    for eval_window in eval_windows:
        band_start = eval_window.start - _dt.timedelta(hours=band_hours)
        for dev_window in dev_windows:
            if dev_window.start < eval_window.start and dev_window.end > band_start:
                violations.append(
                    {
                        "eval_window": eval_window.window_id,
                        "dev_window": dev_window.window_id,
                        "band": [band_start.strftime("%Y-%m-%dT%H:%M:%SZ"), eval_window.start_utc],
                        "rule": f"bande de {band_hours} h retirée du DEV",
                    }
                )
    return violations


def cross_calibration_violations(
    calibration_periods: Sequence[str],
    eval_calm_windows: Sequence[Window],
) -> List[dict]:
    """Embargo de calibration croisée (B7 §d.2.4).

    ``calibration_periods`` : mois déclarés pour la calibration des seuils, au
    format ``"YYYY-MM"`` (mois entier). Une fenêtre CALME EVAL (tout ou partie
    de son intervalle) tombant dans un mois de calibration = violation : la
    calibration « verrait » le jeu d'évaluation.
    """
    violations: List[dict] = []
    for period in calibration_periods:
        if not re.fullmatch(r"\d{4}-\d{2}", period):
            raise WindowError(f"période de calibration attendue au format YYYY-MM : {period!r}")
        year, month = int(period[:4]), int(period[5:7])
        period_start = _dt.datetime(year, month, 1, tzinfo=_dt.timezone.utc)
        period_end = _dt.datetime(year + (month // 12), (month % 12) + 1, 1, tzinfo=_dt.timezone.utc)
        for window in eval_calm_windows:
            if window.start < period_end and period_start < window.end:
                violations.append(
                    {
                        "calibration_period": period,
                        "eval_window": window.window_id,
                        "rule": "les quantiles de revendication sont calculés hors des fenêtres CALME EVAL",
                    }
                )
    return violations


# --- porte de gel ------------------------------------------------------------


def _normalized_bytes(path: str) -> bytes:
    with open(path, "rb") as handle:
        raw = handle.read()
    return raw.replace(b"\r\n", b"\n")


def sha256_file(path: str) -> str:
    """SHA-256 des octets du fichier, CRLF normalisés en LF (portabilité)."""
    return hashlib.sha256(_normalized_bytes(path)).hexdigest()


def _read_sha256sum(manifest_path: str) -> List[Tuple[str, str]]:
    entries: List[Tuple[str, str]] = []
    with open(manifest_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                raise FreezeGateError(f"ligne sha256sum illisible dans {manifest_path}: {line!r}")
            digest, name = parts[0].lower(), parts[1].strip().lstrip("*")
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise FreezeGateError(f"empreinte invalide dans {manifest_path}: {digest!r}")
            entries.append((digest, name))
    return entries


def verify_frozen_package(frozen_dir: str, required: Sequence[str] = FROZEN_FILES) -> dict:
    """Vérifie ``frozen/Gx.sha256`` : présence, lisibilité, concordance.

    Renvoie ``{nom: sha256}`` quand tout concorde ; lève
    :class:`FreezeGateError` avec le détail du premier écart (gel absent,
    incomplet ou modifié → toute écriture d'évaluation est refusée).
    """
    if not os.path.isdir(frozen_dir):
        raise FreezeGateError(f"paquet de gel absent : {frozen_dir} (G1–G6 requis avant toute écriture)")
    hashes: dict = {}
    for name in required:
        manifest = os.path.join(frozen_dir, f"{name}.sha256")
        if not os.path.isfile(manifest):
            raise FreezeGateError(f"manifeste de gel manquant : {manifest}")
        entries = _read_sha256sum(manifest)
        if not entries:
            raise FreezeGateError(f"manifeste de gel vide : {manifest}")
        for digest, referenced in entries:
            target = referenced if os.path.isabs(referenced) else os.path.join(frozen_dir, referenced)
            if not os.path.isfile(target):
                raise FreezeGateError(f"{manifest} référence un fichier absent : {referenced}")
            actual = sha256_file(target)
            if actual != digest:
                raise FreezeGateError(
                    f"empreinte non concordante pour {referenced} : {actual} ≠ {digest} (gel modifié ?)"
                )
            hashes[name] = actual
    return hashes


def eval_run_gate(frozen_dir: str, lock_path: Optional[str] = None, force: bool = False) -> Optional[str]:
    """Porte d'exécution EVAL (B7 §d.2.5) : refus sans gel ; refus de la
    deuxième exécution sans ``force`` ; mention obligatoire si ``force``.

    Renvoie ``None`` en cas de première exécution possible, ou la **mention
    obligatoire** à écrire en tête de rapport quand ``force`` est utilisé.
    """
    verify_frozen_package(frozen_dir)
    if lock_path and os.path.exists(lock_path):
        if not force:
            raise FreezeGateError(
                f"verrou d'évaluation présent ({lock_path}) : deuxième exécution interdite sans --force "
                "(le jeu EVAL est brûlé après la première exécution)"
            )
        return FORCED_RERUN_MENTION
    return None
