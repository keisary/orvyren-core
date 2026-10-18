#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — outcomes : résolveur déterministe, formats chaînés.

Source normative : B7 §a.2 (trois producteurs), §a.3 (fenêtres et états),
§a.4 (schéma JSON de l'outcome), §a.5 (règles opposables), §a.7 (ce qui n'est
pas un outcome), DOC2 §5.8.1.

Trois règles de résolution, chacune gelée par identifiant :

* ``sustained_depeg_v1`` — « dépeg soutenu » (R3 M2 / B7 §0.2) : écart
  ``> ecart_pct`` **persistant ≥ persistance_obs observations** de la grille,
  contiguïté exigée (gap ≤ ``max_gap_minutes``). Paramètres portés par le
  forecast (``y_definition``), pas inventés ici ;
* ``calm_window_v1`` — critère CALME gelé (B7 §d.1) : ``max|P_t − 1| < 0,5 %``
  sur toute la fenêtre ; échec → reclassé STRESS (le résultat est un échec de
  l'énoncé, pas un ajustement de l'énoncé).

Gardes de code (testées) :

* **``resolve_not_before``** : un outcome ne peut pas être écrit avant
  l'horizon de résolution (``ResolutionTooEarly``) — B7 §a.5.5 ;
* **liaison par empreinte** : ``forecast_hash`` doit correspondre à l'empreinte
  recalculée de la prévision sur disque, sinon l'outcome est rejeté ;
* **append-only + chaînage** ``prev_hash`` (même mécanique que les prévisions) ;
* **corrections** : nouveau outcome avec ``supersedes: <outcome_id>`` — les
  deux restent visibles (B7 §a.5.3).

``resolution_time`` est l'horodatage de la **fenêtre de résolution** (pas
l'heure d'exécution du job) ; ``written_at_utc`` est l'heure d'écriture réelle ;
les deux sont distincts et publiés.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from typing import Dict, List, Optional, Sequence, Tuple

from orvyren.evaluation import forecasts as forecasts_mod
from orvyren.evaluation import windows as windows_mod

SCHEMA = "orvyren.outcome.v1"

RULE_SUSTAINED_DEPEG = "sustained_depeg_v1"
RULE_CALM_WINDOW = "calm_window_v1"
RULES = (RULE_SUSTAINED_DEPEG, RULE_CALM_WINDOW)

RESOLVER_MODE_DETERMINISTIC = "deterministic"
RESOLVER_VERSION = "outcomes-v1"

REQUIRED_FIELDS = (
    "schema",
    "outcome_id",
    "forecast_id",
    "forecast_hash",
    "horizon",
    "y",
    "observed",
    "resolution_rule_id",
    "resolver",
    "evidence_refs",
    "written_at_utc",
    "prev_hash",
    "supersedes",
)


class OutcomeError(ValueError):
    """Outcome invalide (champs, y, liaison, chaîne)."""


class ResolutionTooEarly(RuntimeError):
    """Tentative d'écriture d'un outcome avant ``resolve_not_before`` : refus."""


def canonical_bytes(record: Dict) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


# --- résolution : les règles ------------------------------------------------


def _series_in_window(series: Sequence[Tuple[str, float]], start: _dt.datetime, end: _dt.datetime):
    points = []
    for stamp, price in series:
        moment = windows_mod.parse_utc(stamp)
        if start <= moment <= end:
            points.append((moment, float(price)))
    points.sort(key=lambda pair: pair[0])
    return points


def sustained_depeg_v1(
    series: Sequence[Tuple[str, float]],
    t_from_utc: str,
    t_to_utc: str,
    ecart_pct: float = 1.0,
    persistance_obs: int = 2,
    max_gap_minutes: float = 90.0,
    peg: float = 1.0,
) -> dict:
    """Règle ``sustained_depeg_v1`` : ``y = 1`` ssi un dépeg soutenu est observé.

    Un « dépeg soutenu » = ``persistance_obs`` observations **consécutives**
    (gap ≤ ``max_gap_minutes``) avec écart ``(peg − prix)/peg · 100 > ecart_pct``,
    dans la fenêtre ``[t_from, t_to]``. Déterministe : le même corpus donne le
    même résultat, bit à bit.
    """
    if persistance_obs < 2:
        raise OutcomeError("persistance_obs ≥ 2 exigée (« soutenu » = au moins deux observations)")
    start, end = windows_mod.parse_utc(t_from_utc), windows_mod.parse_utc(t_to_utc)
    if end < start:
        raise OutcomeError("fenêtre de résolution inversée")
    points = _series_in_window(series, start, end)
    if not points:
        raise OutcomeError(f"aucune observation dans la fenêtre {t_from_utc} → {t_to_utc} : non résoluble")
    worst_utc, worst_price = min(points, key=lambda pair: pair[1])
    max_discount_pct = (peg - worst_price) / peg * 100.0
    gaps = _dt.timedelta(minutes=max_gap_minutes)
    runs: List[List[Tuple[_dt.datetime, float]]] = []
    current: List[Tuple[_dt.datetime, float]] = []
    previous: Optional[_dt.datetime] = None
    for moment, price in points:
        discount = (peg - price) / peg * 100.0
        contiguous = previous is not None and (moment - previous) <= gaps
        if discount > ecart_pct and (not current or contiguous):
            current.append((moment, price))
        elif discount > ecart_pct:
            if len(current) >= persistance_obs:
                runs.append(current)
            current = [(moment, price)]
        else:
            if len(current) >= persistance_obs:
                runs.append(current)
            current = []
        previous = moment
    if len(current) >= persistance_obs:
        runs.append(current)
    y = 1 if runs else 0
    first = runs[0] if runs else None
    return {
        "y": y,
        "resolution_rule_id": RULE_SUSTAINED_DEPEG,
        "observed": {
            "rule": RULE_SUSTAINED_DEPEG,
            "ecart_pct": ecart_pct,
            "persistance_obs": persistance_obs,
            "max_gap_minutes": max_gap_minutes,
            "n_observations": len(points),
            "min_price": worst_price,
            "max_discount_pct": round(max_discount_pct, 6),
            "first_violation_utc": windows_mod.format_utc(worst_utc),
            "sustained_runs": len(runs),
            "longest_run_obs": max((len(run) for run in runs), default=0),
            "first_sustained_utc": windows_mod.format_utc(first[-1][0]) if first else None,
        },
        "evidence_refs": [f"observation:{windows_mod.format_utc(moment)}" for moment, _ in points],
    }


def calm_window_v1(
    series: Sequence[Tuple[str, float]],
    t_from_utc: str,
    t_to_utc: str,
    tolerance_pct: float = 0.5,
    peg: float = 1.0,
) -> dict:
    """Règle ``calm_window_v1`` : critère CALME gelé ``max|P_t − 1| < 0,5 %``.

    ``y = 1`` ssi la fenêtre est **entièrement** calme au sens du critère
    (échec → reclassement STRESS, résultat publié tel quel — jamais un
    ajustement rétroactif du critère).
    """
    start, end = windows_mod.parse_utc(t_from_utc), windows_mod.parse_utc(t_to_utc)
    if end < start:
        raise OutcomeError("fenêtre de résolution inversée")
    points = _series_in_window(series, start, end)
    if not points:
        raise OutcomeError(f"aucune observation dans la fenêtre {t_from_utc} → {t_to_utc} : non résoluble")
    worst_moment, worst_price = max(points, key=lambda pair: abs(pair[1] - peg))
    max_dev_pct = abs(worst_price - peg) / peg * 100.0
    return {
        "y": 1 if max_dev_pct < tolerance_pct else 0,
        "resolution_rule_id": RULE_CALM_WINDOW,
        "observed": {
            "rule": RULE_CALM_WINDOW,
            "tolerance_pct": tolerance_pct,
            "n_observations": len(points),
            "max_abs_deviation_pct": round(max_dev_pct, 6),
            "worst_observation_utc": windows_mod.format_utc(worst_moment),
            "worst_price": worst_price,
        },
        "evidence_refs": [f"observation:{windows_mod.format_utc(moment)}" for moment, _ in points],
    }


_RESOLVERS = {
    RULE_SUSTAINED_DEPEG: sustained_depeg_v1,
    RULE_CALM_WINDOW: calm_window_v1,
}


# --- résolution d'une prévision ---------------------------------------------


def resolve_forecast(
    forecast: Dict,
    series: Sequence[Tuple[str, float]],
    now_utc: Optional[str] = None,
    code_hash: Optional[str] = None,
    supersedes: Optional[str] = None,
) -> Dict:
    """Résout une prévision gelée → outcome (non encore chaîné).

    Refus : empreinte de la prévision non concordante ; ``now`` antérieur à
    ``resolve_not_before_utc`` ; règle inconnue ; fenêtre sans observation.
    """
    expected_hash = forecasts_mod.record_hash(forecast)
    if forecast.get("sha256") != expected_hash:
        raise OutcomeError(
            f"prévision {forecast.get('forecast_id')} : empreinte non concordante "
            f"({forecast.get('sha256')} ≠ {expected_hash}) — liaison par empreinte rompue"
        )
    horizon = forecast["horizon"]
    resolve_not_before = windows_mod.parse_utc(horizon["resolve_not_before_utc"])
    reference_now = windows_mod.parse_utc(now_utc) if now_utc else _dt.datetime.now(_dt.timezone.utc)
    if reference_now < resolve_not_before:
        raise ResolutionTooEarly(
            f"prévision {forecast['forecast_id']} : resolve_not_before = "
            f"{horizon['resolve_not_before_utc']} > {windows_mod.format_utc(reference_now)} — "
            "un outcome ne s'écrit jamais avant l'horizon (garde de code, B7 §a.5.5)"
        )
    rule_id = forecast["resolution_rule_id"]
    resolver = _RESOLVERS.get(rule_id)
    if resolver is None:
        raise OutcomeError(f"règle de résolution inconnue : {rule_id!r} (connues : {RULES})")
    definition = forecast.get("y_definition", {})
    kwargs = {"peg": definition.get("peg", 1.0)}
    for key in ("ecart_pct", "persistance_obs", "max_gap_minutes", "tolerance_pct"):
        if key in definition:
            kwargs[key] = definition[key]
    t_frozen = horizon["t_frozen_utc"]
    if horizon["kind"] == forecasts_mod.HORIZON_T:
        t_to = horizon.get("t_end_utc") or horizon["resolve_not_before_utc"]
    else:
        t_to = horizon["resolve_not_before_utc"]
    outcome_of_rule = resolver(series, t_frozen, t_to, **kwargs)
    outcome = {
        "schema": SCHEMA,
        "outcome_id": f"{forecast['forecast_id']}.{horizon['kind'].lower()}",
        "forecast_id": forecast["forecast_id"],
        "forecast_hash": forecast["sha256"],
        "horizon": {
            "kind": horizon["kind"],
            "t_resolution_window_utc": horizon["resolve_not_before_utc"],
            "t_from_utc": t_frozen,
            "t_to_utc": t_to,
        },
        "y": outcome_of_rule["y"],
        "observed": outcome_of_rule["observed"],
        "resolution_rule_id": rule_id,
        "resolver": {
            "mode": RESOLVER_MODE_DETERMINISTIC,
            "version": RESOLVER_VERSION,
            "code_hash": code_hash,
        },
        "evidence_refs": outcome_of_rule["evidence_refs"],
        "written_at_utc": windows_mod.format_utc(reference_now),
        "prev_hash": forecasts_mod.GENESIS_HASH,
        "supersedes": supersedes,
    }
    return outcome


def outcome_hash(record: Dict) -> str:
    """Empreinte d'un outcome (le champ ``signature`` s'auto-exclut)."""
    body = {key: value for key, value in record.items() if key != "signature"}
    return hashlib.sha256(canonical_bytes(body)).hexdigest()


def load_outcomes(path: str) -> List[Dict]:
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
            except json.JSONDecodeError as exc:
                raise OutcomeError(f"{path}:{line_number} : JSON illisible ({exc})") from exc
    return records


def verify_outcome_chain(records: Sequence[Dict], path: str = "<mémoire>") -> List[str]:
    """Vérifie le chaînage ``prev_hash`` des outcomes (l'empreinte d'un outcome
    est celle de son contenu JSONL, recalculable par un tiers)."""
    previous = forecasts_mod.GENESIS_HASH
    ids: List[str] = []
    for index, record in enumerate(records, start=1):
        if record.get("prev_hash") != previous:
            raise OutcomeError(
                f"{path} ligne {index} : chaînage cassé (prev_hash {record.get('prev_hash')} ≠ {previous})"
            )
        previous = outcome_hash(record)
        if record.get("signature") and record["signature"] != previous:
            raise OutcomeError(
                f"{path} ligne {index} : signature d'outcome non concordante")
        ids.append(record["outcome_id"])
    return ids


def _validate_outcome(record: Dict) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        raise OutcomeError(f"champs obligatoires manquants : {missing}")
    if record["schema"] != SCHEMA:
        raise OutcomeError(f"schéma attendu {SCHEMA!r}, reçu {record['schema']!r}")
    if record["y"] not in (0, 1):
        raise OutcomeError(f"y hors {{0, 1}} : {record['y']!r}")
    if not record["evidence_refs"]:
        raise OutcomeError("evidence_refs vide : un outcome sans preuve n'est pas recevable")
    forecast_hash = record.get("forecast_hash")
    if not isinstance(forecast_hash, str) or len(forecast_hash) != 64 or any(
            ch not in "0123456789abcdef" for ch in forecast_hash):
        raise OutcomeError("forecast_hash invalide (sha256 hex attendu)")
    horizon = record.get("horizon")
    if not isinstance(horizon, dict) or not horizon.get("t_resolution_window_utc"):
        raise OutcomeError("horizon.t_resolution_window_utc manquant : resolution non datée")
    if record["resolver"].get("mode") != RESOLVER_MODE_DETERMINISTIC:
        raise OutcomeError(
            "mode de résolution non déterministe : les outcomes 'operator' se publient séparément (B7 §a.2)"
        )


def check_link(forecast: Dict, outcome: Dict) -> None:
    """Liaison prévision ↔ outcome par empreinte (B7 §a.5.1) — rejet si rompue."""
    fresh = forecasts_mod.record_hash(forecast)
    if forecast.get("sha256") != fresh:
        raise OutcomeError(f"prévision {forecast.get('forecast_id')} : empreinte non concordante (disque)")
    if outcome["forecast_id"] != forecast["forecast_id"]:
        raise OutcomeError("identifiants de prévision différents")
    if outcome["forecast_hash"] != forecast["sha256"]:
        raise OutcomeError(
            f"forecast_hash non concordant : {outcome['forecast_hash']} ≠ {forecast['sha256']} — outcome rejeté"
        )


def append_outcome(
    path: str,
    outcome: Dict,
    frozen_dir: Optional[str] = None,
    require_frozen: bool = True,
) -> Dict:
    """Écrit un outcome en fin de fichier (chaînage ``prev_hash``).

    Comme pour les prévisions : append-only, refus explicites ; le paquet de
    gel est vérifié quand ``require_frozen`` (défaut — un outcome d'évaluation
    postérieur à un gel modifié serait un résultat invalide).
    """
    if require_frozen:
        windows_mod.verify_frozen_package(frozen_dir or forecasts_mod.default_frozen_dir())
    _validate_outcome(outcome)
    horizon = outcome.get("horizon") if isinstance(outcome.get("horizon"), dict) else {}
    resolution_window = horizon.get("t_resolution_window_utc")
    written_at = outcome.get("written_at_utc")
    try:
        resolution_moment = windows_mod.parse_utc(resolution_window) if resolution_window else None
        written_moment = windows_mod.parse_utc(written_at) if written_at else None
    except (TypeError, ValueError) as exc:
        raise OutcomeError("horizon/written_at illisible: %s" % exc) from exc
    if resolution_moment is not None and written_moment is not None:
        if written_moment < resolution_moment:
            raise ResolutionTooEarly(
                "outcome écrit avant resolve_not_before: written_at=%s, horizon=%s"
                % (written_at, resolution_window))
    existing = load_outcomes(path)
    verify_outcome_chain(existing, path=path)
    if any(prior["outcome_id"] == outcome["outcome_id"] for prior in existing):
        raise OutcomeError(f"outcome déjà écrit : {outcome['outcome_id']} (append-only ; utiliser supersedes)")
    if outcome.get("supersedes"):
        known = {prior["outcome_id"] for prior in existing}
        if outcome["supersedes"] not in known:
            raise OutcomeError(f"supersedes référence un outcome inconnu : {outcome['supersedes']}")
    final = dict(outcome)
    final["prev_hash"] = outcome_hash(existing[-1]) if existing else forecasts_mod.GENESIS_HASH
    final["signature"] = outcome_hash(final)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(final, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    return final


def build_superseding_outcome(
    previous: Dict,
    forecast: Dict,
    series: Sequence[Tuple[str, float]],
    now_utc: Optional[str] = None,
    code_hash: Optional[str] = None,
) -> Dict:
    """Correction : nouveau outcome référençant ``supersedes`` (B7 §a.5.3)."""
    corrected = resolve_forecast(forecast, series, now_utc=now_utc, code_hash=code_hash, supersedes=previous["outcome_id"])
    corrected["outcome_id"] = f"{previous['outcome_id']}.correction"
    return corrected
