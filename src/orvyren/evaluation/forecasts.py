#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — prévisions gelées : format, hachage, chaînage (G1/G6).

Source normative : B7 §a.4 (schéma JSON de la prévision), §a.5 (règles
opposables), §a.6 (stockage append-only), DOC2 §5.8.1.

Règles opposables implémentées :

* **append-only** : une prévision n'est jamais réécrite ni supprimée ; le
  fichier JSONL est chaîné par ``prev_hash`` (même mécanique que
  ``audit.jsonl`` et le journal d'agents) ;
* **empreinte** : ``sha256`` auto-porté, recalculé à chaque vérification ;
* **modification de ``p`` interdite après gel** : un identifiant qui existe
  déjà ne peut pas être ré-enregistré avec un contenu différent — l'écriture
  est refusée (et non silencieusement remplacée) ;
* **gel d'abord** : l'écriture exige un paquet ``frozen/G1..G6.sha256``
  présent et concordant (porte :func:`orvyren.evaluation.windows.verify_frozen_package`) ;
* **``p`` n'est jamais produite par un LLM** : le champ ``p_origin`` doit
  décrire le calcul déterministe ou le prior documenté (source citée).
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from typing import Dict, List, Optional, Sequence

from orvyren.evaluation import windows as windows_mod

SCHEMA = "orvyren.forecast.v1"
GENESIS_HASH = "0" * 64

HORIZON_H_CLASS = "H_class"
HORIZON_T = "T"
HORIZON_KINDS = (HORIZON_H_CLASS, HORIZON_T)

REQUIRED_FIELDS = (
    "schema",
    "forecast_id",
    "run_id",
    "episode_id",
    "set",
    "persona",
    "statement",
    "resolution_rule_id",
    "horizon",
    "p",
    "p_origin",
    "y_definition",
    "observation_state_at_freeze",
    "refs",
    "signed_by",
    "sha256",
    "prev_hash",
)

#: Emplacement canonique du paquet de gel (B7 §c.4 : ``frozen/Gx.sha256``).
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class ForecastError(ValueError):
    """Prévision invalide, dupliquée ou modification interdite."""


def default_frozen_dir() -> str:
    return os.path.join(REPO_ROOT, "frozen")


def canonical_bytes(record: Dict) -> bytes:
    """Sérialisation canonique : clés triées, séparateurs compacts, UTF-8, LF."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def record_hash(record: Dict) -> str:
    """Empreinte auto-portée : SHA-256 du record, champ ``sha256`` mis à zéro."""
    clone = dict(record)
    clone["sha256"] = GENESIS_HASH
    return hashlib.sha256(canonical_bytes(clone)).hexdigest()


def _validate(record: Dict) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        raise ForecastError(f"champs obligatoires manquants : {missing}")
    if record["schema"] != SCHEMA:
        raise ForecastError(f"schéma attendu {SCHEMA!r}, reçu {record['schema']!r}")
    if not isinstance(record["p"], (int, float)) or not 0.0 <= float(record["p"]) <= 1.0:
        raise ForecastError(f"p hors [0, 1] : {record['p']!r}")
    if not str(record["statement"]).strip():
        raise ForecastError("énoncé vide : une prévision sans énoncé n'est pas falsifiable")
    if not str(record["p_origin"]).strip():
        raise ForecastError("p_origin vide : l'origine de p doit être écrite (calcul ou prior cité)")
    if not str(record["resolution_rule_id"]).strip():
        raise ForecastError("resolution_rule_id vide")
    horizon = record["horizon"]
    if horizon.get("kind") not in HORIZON_KINDS:
        raise ForecastError(f"horizon.kind attendu dans {HORIZON_KINDS}, reçu {horizon.get('kind')!r}")
    for key in ("t_frozen_utc", "resolve_not_before_utc"):
        if not horizon.get(key):
            raise ForecastError(f"horizon.{key} manquant")
    if windows_mod.parse_utc(horizon["resolve_not_before_utc"]) <= windows_mod.parse_utc(horizon["t_frozen_utc"]):
        raise ForecastError("resolve_not_before_utc doit être postérieur à t_frozen_utc")
    if record["set"] not in windows_mod.SETS:
        raise ForecastError(f"set attendu dans {windows_mod.SETS}, reçu {record['set']!r}")
    signed = record["signed_by"]
    if not isinstance(signed, dict) or not signed.get("role"):
        raise ForecastError("signed_by.role manquant : une prévision non signée n'est pas gelée")


def build_forecast(
    forecast_id: str,
    run_id: str,
    episode_id: str,
    set_label: str,
    persona: str,
    statement: str,
    resolution_rule_id: str,
    t_frozen_utc: str,
    resolve_not_before_utc: str,
    p: float,
    p_origin: str,
    y_definition: Dict,
    observation_state_at_freeze: Dict,
    refs: Optional[Dict] = None,
    signed_by: Optional[Dict] = None,
    horizon_kind: str = HORIZON_H_CLASS,
    horizon_hours: Optional[float] = None,
    t_end_utc: Optional[str] = None,
) -> Dict:
    """Construit une prévision complète (``sha256`` calculé, ``prev_hash`` à GENESIS).

    ``prev_hash`` et ``sha256`` sont posés ici à leur valeur initiale ; c'est
    :func:`append_forecast` qui fixe le chaînage réel au moment de l'écriture.
    ``t_end_utc`` n'est requis que pour l'horizon ``T`` (fin de fenêtre).
    """
    horizon = {
        "kind": horizon_kind,
        "hours": horizon_hours,
        "t_frozen_utc": t_frozen_utc,
        "resolve_not_before_utc": resolve_not_before_utc,
    }
    if t_end_utc is not None:
        horizon["t_end_utc"] = t_end_utc
    record = {
        "schema": SCHEMA,
        "forecast_id": forecast_id,
        "run_id": run_id,
        "episode_id": episode_id,
        "set": set_label,
        "persona": persona,
        "statement": statement,
        "resolution_rule_id": resolution_rule_id,
        "horizon": horizon,
        "p": float(p),
        "p_origin": p_origin,
        "y_definition": y_definition,
        "observation_state_at_freeze": observation_state_at_freeze,
        "refs": refs or {"hypothesis_ids": [], "branch_ids": [], "observation_ids": []},
        "signed_by": signed_by or {"role": "gel-g6", "name": "<à signer>"},
        "sha256": GENESIS_HASH,
        "prev_hash": GENESIS_HASH,
    }
    _validate(record)
    record["sha256"] = record_hash(record)
    return record


def load_forecasts(path: str) -> List[Dict]:
    """Charge un fichier JSONL de prévisions (lignes vides ignorées)."""
    if not os.path.isfile(path):
        return []
    records: List[Dict] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                records.append(json.loads(text))
            except json.JSONDecodeError as exc:  # ligne corrompue = refus explicite
                raise ForecastError(f"{path}:{line_number} : JSON illisible ({exc})") from exc
    return records


def verify_forecast_chain(records: Sequence[Dict], path: str = "<mémoire>") -> List[str]:
    """Vérifie chaînage + empreintes ; renvoie la liste des identifiants.

    Une seule divergence suffit à lever : un fichier de prévisions dont la
    chaîne est cassée n'est pas exploitable (B7 §a.5).
    """
    previous = GENESIS_HASH
    ids: List[str] = []
    for index, record in enumerate(records, start=1):
        expected = record_hash(record)
        if record.get("sha256") != expected:
            raise ForecastError(
                f"{path} ligne {index} : empreinte non concordante "
                f"({record.get('sha256')} ≠ {expected}) — fichier modifié ?"
            )
        if record.get("prev_hash") != previous:
            raise ForecastError(
                f"{path} ligne {index} : chaînage cassé (prev_hash {record.get('prev_hash')} ≠ {previous})"
            )
        previous = record["sha256"]
        ids.append(record["forecast_id"])
    return ids


def append_forecast(
    path: str,
    record: Dict,
    frozen_dir: Optional[str] = None,
    require_frozen: bool = True,
) -> Dict:
    """Écrit une prévision en fin de fichier, après contrôle du gel et du chaînage.

    Refus explicites : paquet de gel absent/non concordant, champs invalides,
    identifiant déjà gelé (append-only : ``p`` ne se modifie jamais), chaîne
    existante cassée.
    """
    if require_frozen:
        windows_mod.verify_frozen_package(frozen_dir or default_frozen_dir())
    _validate(record)
    existing = load_forecasts(path)
    verify_forecast_chain(existing, path=path)
    for prior in existing:
        if prior["forecast_id"] == record["forecast_id"]:
            if prior["sha256"] == record_hash(record):
                raise ForecastError(f"prévision déjà gelée (identique) : {record['forecast_id']}")
            raise ForecastError(
                f"modification interdite : la prévision {record['forecast_id']} existe déjà "
                "avec un contenu différent (p ne se modifie jamais après gel)"
            )
    final = dict(record)
    final["prev_hash"] = existing[-1]["sha256"] if existing else GENESIS_HASH
    final["sha256"] = record_hash(final)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(final, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    return final


def find_forecast(records: Sequence[Dict], forecast_id: str) -> Dict:
    for record in records:
        if record["forecast_id"] == forecast_id:
            return record
    raise ForecastError(f"prévision inconnue : {forecast_id}")
