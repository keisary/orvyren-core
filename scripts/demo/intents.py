#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — kit de démo testnet : intent v1 (schéma B5 §b.1).

Un *intent* est une **demande structurée**, jamais un paiement, jamais du
calldata. Le schéma v1 (B5 §b.1) est un sur-ensemble du code existant
(``orvyren.policy.Intent``) :

``schema_version, intent_id, idempotency_key, chain_id, account, action,
asset, amount (CHAÎNE décimale), amount_base_units, recipient, function,
params, expiry, created_at, justification, policy_version, source``

Règles de validation déterministes (aucune réparation, aucun champ inconnu) :

1. champs inconnus rejetés, types stricts, ``amount`` en notation décimale à
   point (jamais scientifique) ;
2. ``amount_base_units`` recalculé depuis ``amount`` + décimales du jeton
   (USDC = 6, valeur du contrat lue par RPC quand disponible) ;
3. adresses normalisées en minuscules — **aucune réparation** ;
4. ``action`` ∈ catalogue ; couple (action, fonction, params) contraint :
   ``transfer`` impose ``transfer(address,uint256)`` et ``params.to == recipient`` ;
5. ``expiry > now`` et ``expiry ≤ now + TTL`` (TTL démo : 15 min par défaut) ;
6. ``idempotency_key`` absent du registre (contrôlé par le préflight P4) ;
7. l'intent **n'est pas** du calldata : le calldata est construit après ALLOW.

``idempotency_key = keccak256(JSON canonique SANS intent_id ni created_at)``.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

try:  # paquet (``demo.intents``)
    from . import common
except ImportError:  # exécution directe : python scripts/demo/intents.py
    import os as _os
    import sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    import common  # type: ignore  # noqa: E402

SCHEMA_VERSION = "intent/v1"

ACTIONS_AUTONOMES = ("transfer",)
ACTIONS_SOUS_APPROBATION = ("swap", "approve", "change_policy", "revoke")
ACTIONS_CONNUES = ACTIONS_AUTONOMES + ACTIONS_SOUS_APPROBATION

#: Registre v1 action -> (cible, signature, opération) — B4 P4.
ACTION_REGISTRY = {
    "transfer": {"target": "asset", "function": common.TRANSFER_SIGNATURE, "operation": "CALL"},
    "swap": {"target": None, "function": None, "operation": "CALL"},
    "approve": {"target": None, "function": None, "operation": "CALL"},
    "change_policy": {"target": None, "function": None, "operation": "CALL"},
    "revoke": {"target": None, "function": None, "operation": "CALL"},
}

ALLOWED_FIELDS = (
    "schema_version", "intent_id", "idempotency_key", "chain_id", "account",
    "action", "asset", "amount", "amount_base_units", "recipient", "function",
    "params", "expiry", "created_at", "justification", "policy_version", "source",
)

CATALOGUE_ACTIONS = ACTIONS_CONNUES


class IntentError(Exception):
    """Intent invalide (schéma, type, décimale, adresse, échéance)."""


def amount_to_base_units(amount: str, decimals: int) -> int:
    """Convertit une chaîne décimale ASCII en unités de base (entier, jamais flottant).

    ``"50.0"`` + 6 décimales → ``50000000``. Refuse la notation scientifique,
    les valeurs négatives/nulles et plus de décimales que le jeton n'en a.
    """
    if not isinstance(amount, str):
        raise IntentError("amount doit être une chaîne décimale ASCII, reçu {!r}".format(type(amount).__name__))
    text = amount.strip()
    if not text or "e" in text.lower() or text.startswith(("+", "-")):
        raise IntentError("notation non décimale refusée: {!r}".format(amount))
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise IntentError("amount illisible: {!r}".format(amount)) from exc
    if value != value.to_integral_value() and -value.as_tuple().exponent > int(decimals):
        raise IntentError("amount {!r} a plus de {} décimales".format(amount, decimals))
    scaled = value.scaleb(int(decimals))
    if scaled != scaled.to_integral_value():
        raise IntentError("amount {!r} n'est pas représentable en {} décimales".format(amount, decimals))
    units = int(scaled)
    if units <= 0:
        raise IntentError("amount doit être > 0, reçu {!r}".format(amount))
    return units


def base_units_to_amount(units: int, decimals: int) -> str:
    """Inverse de :func:`amount_to_base_units` (représentation décimale stable)."""
    scaled = Decimal(int(units)).scaleb(-int(decimals))
    text = format(scaled, "f")
    return text


def compute_idempotency_key(intent: Dict[str, Any]) -> str:
    """``keccak256(JSON canonique sans intent_id ni created_at)`` (B5 §b.1)."""
    payload = {key: value for key, value in intent.items()
               if key not in ("intent_id", "created_at", "idempotency_key")}
    return "0x" + common.keccak256_hex(common.canonical_json(payload).encode("utf-8"))


def build_transfer_intent(*, chain_id: int, account: str, asset: str, amount: str,
                          recipient: str, expiry_minutes: int, decimals: int = 6,
                          justification: str = "", policy_version: str = "v1.0",
                          source: Optional[Dict[str, Any]] = None,
                          created_at: Optional[str] = None) -> Dict[str, Any]:
    """Construit un intent v1 ``transfer`` (schéma B5 §b.1) — non signé, non autorisé."""
    created = created_at or common.utc_now()
    units = amount_to_base_units(amount, decimals)
    recipient_norm = common.normalize_address(recipient, "recipient")
    intent: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "intent_id": common.ulid(),
        "chain_id": int(chain_id),
        "account": common.normalize_address(account, "account"),
        "action": "transfer",
        "asset": common.normalize_address(asset, "asset"),
        "amount": str(amount),
        "amount_base_units": str(units),
        "recipient": recipient_norm,
        "function": common.TRANSFER_SIGNATURE,
        "params": {"to": recipient_norm, "value": str(units)},
        "expiry": (common.parse_rfc3339(created) + timedelta(minutes=int(expiry_minutes)))
                  .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "created_at": created,
        "justification": str(justification)[:200],
        "policy_version": policy_version,
        "source": dict(source or {}),
    }
    intent["idempotency_key"] = compute_idempotency_key(intent)
    return intent


def build_action_intent(*, action: str, chain_id: int, account: str, asset: str,
                        amount: str = "1.0", recipient: Optional[str] = None,
                        expiry_minutes: int = 15, decimals: int = 6,
                        justification: str = "", policy_version: str = "v1.0",
                        source: Optional[Dict[str, Any]] = None,
                        created_at: Optional[str] = None) -> Dict[str, Any]:
    """Intent v1 d'une action non-``transfer`` (swap/approve/change_policy/revoke).

    Les actions sous approbation n'ont pas de fonction scopée en v1 : le champ
    ``function`` reste vide et le schéma l'exige explicitement.
    """
    if action not in ACTIONS_CONNUES:
        raise IntentError("action inconnue: {!r}".format(action))
    created = created_at or common.utc_now()
    units = amount_to_base_units(amount, decimals)
    target = common.normalize_address(recipient or account, "recipient")
    intent: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "intent_id": common.ulid(),
        "chain_id": int(chain_id),
        "account": common.normalize_address(account, "account"),
        "action": action,
        "asset": common.normalize_address(asset, "asset"),
        "amount": str(amount),
        "amount_base_units": str(units),
        "recipient": target,
        "function": "",
        "params": {},
        "expiry": (common.parse_rfc3339(created) + timedelta(minutes=int(expiry_minutes)))
                  .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "created_at": created,
        "justification": str(justification)[:200],
        "policy_version": policy_version,
        "source": dict(source or {}),
    }
    intent["idempotency_key"] = compute_idempotency_key(intent)
    return intent


def validate_intent(intent: Dict[str, Any], *, now: Optional[str] = None,
                    ttl_minutes: int = 15, decimals: int = 6,
                    require_key: bool = True) -> Tuple[bool, List[Dict[str, str]]]:
    """Validation déterministe du schéma v1. Retourne ``(ok, erreurs)``.

    Chaque erreur : ``{"code", "field", "detail"}`` — codes stables.
    """
    errors: List[Dict[str, str]] = []

    def fail(code: str, field: str, detail: str) -> None:
        errors.append({"code": code, "field": field, "detail": detail})

    if not isinstance(intent, dict):
        return False, [{"code": "SCHEMA_TYPE", "field": "<root>", "detail": "intent doit être un objet"}]

    for key in intent:
        if key not in ALLOWED_FIELDS:
            fail("SCHEMA_UNKNOWN_FIELD", key, "champ inconnu refusé")

    for field in ("schema_version", "intent_id", "chain_id", "account", "action", "asset",
                  "amount", "amount_base_units", "recipient", "function", "params",
                  "expiry", "created_at"):
        if field not in intent:
            fail("SCHEMA_MISSING", field, "champ obligatoire absent")

    if intent.get("schema_version") != SCHEMA_VERSION:
        fail("SCHEMA_VERSION", "schema_version", "attendu {}".format(SCHEMA_VERSION))

    action = intent.get("action")
    if action not in ACTIONS_CONNUES:
        fail("ACTION_UNKNOWN", "action", "action hors catalogue v1: {!r}".format(action))

    for field in ("account", "asset", "recipient"):
        value = intent.get(field)
        if not common.is_address(value):
            fail("SCHEMA_ADDRESS", field, "adresse mal formée: {!r}".format(value))
        elif value != common.normalize_address(value):
            fail("SCHEMA_ADDRESS", field, "adresse non normalisée (minuscules attendues)")

    chain_id = intent.get("chain_id")
    if not isinstance(chain_id, int) or isinstance(chain_id, bool) or chain_id <= 0:
        fail("SCHEMA_TYPE", "chain_id", "entier positif attendu")

    amount = intent.get("amount")
    if not isinstance(amount, str):
        fail("SCHEMA_TYPE", "amount", "chaîne décimale attendue (jamais un flottant)")
    else:
        try:
            units = amount_to_base_units(amount, decimals)
        except IntentError as exc:
            fail("SCHEMA_AMOUNT", "amount", str(exc))
            units = None
        if units is not None:
            declared = intent.get("amount_base_units")
            if not isinstance(declared, str) or not declared.isdigit():
                fail("SCHEMA_TYPE", "amount_base_units", "chaîne entière attendue")
            elif int(declared) != units:
                fail("AMOUNT_BASE_UNITS_MISMATCH", "amount_base_units",
                     "déclaré {} ≠ recalculé {}".format(declared, units))

    params = intent.get("params")
    if not isinstance(params, dict):
        fail("SCHEMA_TYPE", "params", "objet attendu")
    function = intent.get("function")
    if action == "transfer":
        if function != common.TRANSFER_SIGNATURE:
            fail("FUNCTION_NOT_ALLOWED", "function",
                 "transfer impose {}".format(common.TRANSFER_SIGNATURE))
        if isinstance(params, dict):
            if params.get("to") != intent.get("recipient"):
                fail("PARAMS_RECIPIENT_MISMATCH", "params.to",
                     "params.to doit égaler recipient")
            if str(params.get("value")) != str(intent.get("amount_base_units")):
                fail("PARAMS_VALUE_MISMATCH", "params.value",
                     "params.value doit égaler amount_base_units")
    else:
        if function not in ("", None):
            fail("FUNCTION_NOT_ALLOWED", "function",
                 "aucune fonction scopée pour l'action {!r} en v1".format(action))

    try:
        expiry = common.parse_rfc3339(intent.get("expiry"))
        created = common.parse_rfc3339(intent.get("created_at"))
        moment = common.parse_rfc3339(now) if now else common.utc_now_dt()
        if expiry <= moment:
            fail("INTENT_EXPIRED", "expiry", "expiry dépassée ({})".format(intent.get("expiry")))
        if expiry > moment + timedelta(minutes=int(ttl_minutes)):
            fail("INTENT_TTL_TOO_LONG", "expiry",
                 "expiry au-delà de now + {} min".format(ttl_minutes))
        if created > moment + timedelta(seconds=60):
            fail("INTENT_NOT_YET_VALID", "created_at", "created_at dans le futur")
    except ValueError as exc:
        fail("SCHEMA_TIME", "expiry", "horodatage illisible: {}".format(exc))

    if require_key:
        key = intent.get("idempotency_key")
        if not isinstance(key, str) or len(key) != 66 or not key.startswith("0x"):
            fail("SCHEMA_MISSING", "idempotency_key", "clé d'idempotence absente ou mal formée")
        else:
            recomputed = compute_idempotency_key(intent)
            if recomputed.lower() != key.lower():
                fail("IDEMPOTENCY_KEY_MISMATCH", "idempotency_key",
                     "clé recalculée {} ≠ déclarée".format(recomputed))

    return (not errors), errors


def intent_calldata(intent: Dict[str, Any], *, decimals: int = 6) -> Dict[str, str]:
    """Calldata de l'intent **après** ALLOW (étape distincte, B5 §b.1 règle 7).

    Retourne ``{"to": <contrat jeton>, "data": 0xa9059cbb…}`` — non signé.
    """
    ok, errors = validate_intent(intent, ttl_minutes=10 ** 6, require_key=False)
    if not ok:
        codes = ", ".join(sorted({error["code"] for error in errors}))
        raise IntentError("intent invalide, calldata refusé: {}".format(codes))
    if intent.get("action") != "transfer":
        raise IntentError("calldata v1 construit uniquement pour transfer")
    units = int(intent["amount_base_units"])
    data = common.abi_encode_call(
        common.SELECTOR_TRANSFER,
        [common.enc_address(intent["recipient"]), common.enc_uint(units)],
    )
    return {"to": common.normalize_address(intent["asset"]), "data": data}


def intent_summary(intent: Dict[str, Any]) -> Dict[str, Any]:
    """Résumé imprimable (jamais de secret, jamais de clé)."""
    return {
        "intent_id": intent.get("intent_id"),
        "action": intent.get("action"),
        "amount": intent.get("amount"),
        "amount_base_units": intent.get("amount_base_units"),
        "asset": intent.get("asset"),
        "recipient": common.short_address(intent.get("recipient")),
        "expiry": intent.get("expiry"),
        "idempotency_key": intent.get("idempotency_key"),
        "policy_version": intent.get("policy_version"),
    }
