#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — corpus figé du rejeu + ancres de blocs (W7, B7 §c.4).

Sources admissibles d'un run de rejeu : **corpus figé** (``corpus/`` + séries
W1/W3, manifeste ``replay/corpus_v1.manifest.json`` : chemins + ``sha256`` +
taille) et **blocs fixes** (``replay/blocks_v1.json`` : une ancre par jour —
table déclarée absente tant qu'elle n'est pas construite : jamais inventée).
**Aucun ``latest``** dans un run de rejeu : tout accès chaîne passe par un bloc
explicite épinglé (:func:`require_pinned_block`).

Le moteur refuse de démarrer si un hash du manifeste ne correspond pas au
disque ; les trous de série sont détectés, jamais comblés en silence
(:func:`find_gaps`).
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import json
import os
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

DEFAULT_MANIFEST = os.path.join(REPO_ROOT, "replay", "corpus_v1.manifest.json")
DEFAULT_BLOCKS = os.path.join(REPO_ROOT, "replay", "blocks_v1.json")

#: Écart maximal normal entre deux observations d'une même série horaire.
MAX_GAP_MINUTES = 90.0

#: Métriques de prix utilisables comme série de référence d'une fenêtre.
PRICE_VENUES = ("defillama", "bitstamp", "binance")


class CorpusError(RuntimeError):
    """Corpus figé invalide (hash non concordant, ancre manquante, trou...)."""


# --- utilitaires -------------------------------------------------------------

def sha256_file(path: str) -> str:
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def _parse_utc(stamp: str) -> _dt.datetime:
    text = str(stamp).replace("Z", "+00:00")
    parsed = _dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_dt.timezone.utc)
    return parsed.astimezone(_dt.timezone.utc)


# --- manifeste ---------------------------------------------------------------

def load_manifest(path: str = DEFAULT_MANIFEST, *, verify: bool = True) -> dict:
    """Charge le manifeste du corpus ; vérifie chaque ``sha256`` contre le disque.

    Règle du producteur (``scripts/build_corpus_v1_manifest.py``) : digest des
    **octets bruts** de chaque fichier. Tout écart ⇒ refus (B7 §c.4).
    """
    if not os.path.isfile(path):
        raise CorpusError("manifeste du corpus absent : %s" % path)
    with open(path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    files = manifest.get("files") or []
    if not files:
        raise CorpusError("manifeste du corpus vide : %s" % path)
    checked: List[dict] = []
    for entry in files:
        rel = entry.get("path")
        digest = entry.get("sha256")
        target = rel if os.path.isabs(str(rel)) else os.path.join(REPO_ROOT, rel)
        if not os.path.isfile(target):
            raise CorpusError("fichier du corpus absent : %s" % rel)
        actual = sha256_file(target)
        if verify and actual != digest:
            raise CorpusError("corpus modifié : %s (%s ≠ %s)" % (rel, actual, digest))
        checked.append({"path": rel, "sha256": actual, "bytes": entry.get("bytes")})
    manifest["files"] = checked
    manifest["manifest_sha256"] = sha256_file(path)
    return manifest


# --- séries ------------------------------------------------------------------

def series_from_corpus_csv(path: str, *, venue: str = "defillama",
                           metric: str = "price_usd",
                           start_utc: Optional[str] = None,
                           end_utc: Optional[str] = None) -> List[Tuple[str, float]]:
    """Série ``(timestamp_utc, valeur)`` triée depuis ``corpus/*.csv``."""
    points: List[Tuple[str, float]] = []
    start = _parse_utc(start_utc) if start_utc else None
    end = _parse_utc(end_utc) if end_utc else None
    with open(path, "r", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if str(row.get("venue", "")).strip() != venue:
                continue
            if str(row.get("metric", "")).strip() != metric:
                continue
            stamp = str(row.get("timestamp_utc", "")).strip()
            if not stamp:
                continue
            moment = _parse_utc(stamp)
            if start and moment < start:
                continue
            if end and moment > end:
                continue
            points.append((stamp, float(row["value"])))
    points.sort(key=lambda item: _parse_utc(item[0]))
    return points


def series_from_episode(path: str) -> List[Tuple[str, float]]:
    """Série ``(timestamp_utc, valeur)`` depuis ``evidence/episode_*.json``.

    Deux formes supportées, jamais devinées au-delà :

    * ``series`` = **liste** de dicts ``{<horodatage>, <valeur>}`` (clés
      ``t_utc``/``timestamp_utc``/... × ``price_usd``/``price``/``value``) ;
    * ``series`` = **dict** horodaté (stETH/rsETH : ``{"2022-05-01T00:00:00Z":
      {...}}``) — valeur par priorité : ``price_eth_per_steth`` (décote
      réalisable Curve), ``discount.1.price_eth_per_steth``, ``price_usd``,
      ``market.median``, ``value``.

    Un fichier qui ne s'y prête pas lève : jamais de série inventée.
    """
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    series = payload.get("series")
    if not series:
        raise CorpusError("aucune série exploitable dans %s" % path)
    stamp_keys = ("t_utc", "timestamp_utc", "utc", "t", "timestamp")
    value_keys = ("price_usd", "price", "value", "price_reference_usd")
    points: List[Tuple[str, float]] = []
    if isinstance(series, list):
        for item in series:
            if not isinstance(item, dict):
                continue
            stamp = next((item[key] for key in stamp_keys if key in item and item[key]), None)
            value = next((item[key] for key in value_keys
                          if key in item and isinstance(item[key], (int, float))), None)
            if stamp is None or value is None:
                continue
            points.append((str(stamp), float(value)))
    elif isinstance(series, dict):
        for stamp, item in series.items():
            if not isinstance(item, dict):
                if isinstance(item, (int, float)):
                    points.append((str(stamp), float(item)))
                continue
            value = None
            if isinstance(item.get("price_eth_per_steth"), (int, float)):
                value = float(item["price_eth_per_steth"])
            elif isinstance(item.get("discount"), dict):
                by_size = item["discount"].get("1") or item["discount"].get(1)
                if isinstance(by_size, dict) and isinstance(by_size.get("price_eth_per_steth"),
                                                             (int, float)):
                    value = float(by_size["price_eth_per_steth"])
            if value is None:
                value = next((item[key] for key in ("price_usd", "price", "value")
                              if isinstance(item.get(key), (int, float))), None)
            if value is None and isinstance(item.get("market"), dict):
                median = item["market"].get("median")
                if isinstance(median, (int, float)):
                    value = float(median)
            if value is None:
                continue
            points.append((str(stamp), float(value)))
    else:
        raise CorpusError("forme de série non supportée dans %s (type %s)"
                          % (path, type(series).__name__))
    if not points:
        raise CorpusError("série non reconnue dans %s (clés inattendues)" % path)
    points.sort(key=lambda item: _parse_utc(item[0]))
    return points


def window_series(window, *, venue: str = "defillama") -> Tuple[str, List[Tuple[str, float]]]:
    """Série de référence d'une fenêtre DEV/EVAL, selon ses sources déclarées.

    Dispatch explicite : corpus CSV pour les épisodes USDC ; épisode JSON sinon.
    Chaque source est tentée dans l'ordre déclaré ; un échec n'interrompt pas
    la tentative suivante mais est consigné. Renvoie ``(source_label, points)`` ;
    jamais de fenêtre silencieusement vide.
    """
    attempts: List[str] = []
    for rel in window.sources:
        target = rel if os.path.isabs(rel) else os.path.join(REPO_ROOT, rel)
        try:
            if target.endswith(".csv"):
                points = series_from_corpus_csv(target, venue=venue,
                                                start_utc=window.start_utc,
                                                end_utc=window.end_utc)
                if points:
                    return (rel, points)
                attempts.append("%s: aucun point dans la fenêtre" % rel)
            elif target.endswith(".json") and "episode" in os.path.basename(target):
                points = series_from_episode(target)
                start, end = _parse_utc(window.start_utc), _parse_utc(window.end_utc)
                points = [(stamp, value) for stamp, value in points
                          if start <= _parse_utc(stamp) <= end]
                if points:
                    return (rel, points)
                attempts.append("%s: aucun point dans la fenêtre" % rel)
            else:
                attempts.append("%s: type de source non reconnu" % rel)
        except CorpusError as exc:
            attempts.append("%s: %s" % (rel, exc))
    raise CorpusError("aucune source de série résolue pour la fenêtre %s (%s)"
                      % (window.window_id, " · ".join(attempts)))


def find_gaps(points: Sequence[Tuple[str, float]],
              max_gap_minutes: float = MAX_GAP_MINUTES) -> List[dict]:
    """Trous d'une série : écarts > ``max_gap_minutes`` entre observations.

    Un trou n'est jamais comblé ; l'appelant décide (déclarer, ou refuser).
    """
    gaps: List[dict] = []
    previous: Optional[_dt.datetime] = None
    for stamp, _value in points:
        moment = _parse_utc(stamp)
        if previous is not None:
            delta_minutes = (moment - previous).total_seconds() / 60.0
            if delta_minutes > max_gap_minutes:
                gaps.append({"after_utc": previous.strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "before_utc": moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "gap_minutes": round(delta_minutes, 1)})
        previous = moment
    return gaps


def require_continuous(points: Sequence[Tuple[str, float]],
                       *, label: str = "série",
                       max_gap_minutes: float = MAX_GAP_MINUTES) -> None:
    """Refuse une série trouée (par défaut) — jamais de comblement silencieux."""
    gaps = find_gaps(points, max_gap_minutes)
    if gaps:
        raise CorpusError("%s : %d trou(s) détecté(s), premier %s → %s (%.1f min)"
                          % (label, len(gaps), gaps[0]["after_utc"], gaps[0]["before_utc"],
                             gaps[0]["gap_minutes"]))


# --- ancres de blocs ---------------------------------------------------------

def load_block_anchors(path: str = DEFAULT_BLOCKS) -> Optional[dict]:
    """Table d'ancres de blocs ``replay/blocks_v1.json`` — ou ``None`` si absente.

    Déclarée absente tant qu'elle n'est pas construite (B7 : « une ancre par
    jour, résolue par dichotomie, cachée ») : aucune ancre n'est inventée.
    """
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise CorpusError("table d'ancres illisible : %s" % path)
    return payload


def block_for(anchors: Optional[dict], stamp_utc: str) -> Optional[int]:
    """Ancre de bloc pour un horodatage (jour le plus proche déjà résolu)."""
    if not anchors:
        return None
    day = _parse_utc(stamp_utc).strftime("%Y-%m-%d")
    direct = anchors.get(day)
    if isinstance(direct, int):
        return direct
    resolved = sorted(key for key in anchors if key <= day and isinstance(anchors[key], int))
    return anchors[resolved[-1]] if resolved else None


def require_pinned_block(block: object, *, context: str = "lecture chaîne") -> int:
    """Garde-fou « aucun ``latest`` » : le bloc doit être un entier explicite."""
    if isinstance(block, int) and not isinstance(block, bool):
        return block
    if isinstance(block, str) and block.isdigit():
        return int(block)
    raise CorpusError("bloc non épinglé (%r) pour : %s — un run de rejeu n'utilise "
                      "jamais « latest » (B7 §c.4)" % (block, context))
