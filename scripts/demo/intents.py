#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — testnet demo kit: intent v1 (schema B5 §b.1).

An *intent* is a **structured request**, never a payment, never
calldata. Schema v1 (B5 §b.1) is a superset of the existing code
(``orvyren.policy.Intent``):

``schema_version, intent_id, idempotency_key, chain_id, account, action,
asset, amount (decimal STRING), amount_base_units, recipient, function,
params, expiry, created_at, justification, policy_version, source``

Deterministic validation rules (no repair, no unknown field):

1. unknown fields rejected, strict types, ``amount`` in point-decimal
   notation (never scientific);
2. ``amount_base_units`` recomputed from ``amount`` + token decimals
   (USDC = 6, contract value read over RPC when available);
3. addresses normalized to lowercase — **no repair**;
4. ``action`` ∈ catalog; (action, function, params) triple constrained:
   ``transfer`` requires ``transfer(address,uint256)`` and ``params.to == recipient``;
5. ``expiry > now`` and ``expiry ≤ now + TTL`` (demo TTL: 15 min by default);
6. ``idempotency_key`` absent from the registry (checked by preflight P4);
7. the intent **is not** calldata: calldata is built after ALLOW.

``idempotency_key = keccak256(canonical JSON WITHOUT intent_id or created_at)``.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

try:  # package (``demo.intents``)
    from . import common
except ImportError:  # direct execution: python scripts/demo/intents.py
    import os as _os
    import sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    import common  # type: ignore  # noqa: E402

SCHEMA_VERSION = "intent/v1"

ACTIONS_AUTONOMES = ("transfer",)
ACTIONS_SOUS_APPROBATION = ("swap", "approve", "change_policy", "revoke")
ACTIONS_CONNUES = ACTIONS_AUTONOMES + ACTIONS_SOUS_APPROBATION

#: v1 registry action -> (target, signature, operation) — B4 P4.
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
    """Invalid intent (schema, type, decimal, address, expiry)."""


def amount_to_base_units(amount: str, decimals: int) -> int:
    """Converts an ASCII decimal string into base units (integer, never a float).

    ``"50.0"`` + 6 decimals → ``50000000``. Refuses scientific notation,
    negative/zero values and more decimals than the token has.
    """
    if not isinstance(amount, str):
        raise IntentError("amount must be an ASCII decimal string, got {!r}".format(type(amount).__name__))
    text = amount.strip()
    if not text or "e" in text.lower() or text.startswith(("+", "-")):
        raise IntentError("non-decimal notation refused: {!r}".format(amount))
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise IntentError("unreadable amount: {!r}".format(amount)) from exc
    if value != value.to_integral_value() and -value.as_tuple().exponent > int(decimals):
        raise IntentError("amount {!r} has more than {} decimals".format(amount, decimals))
    scaled = value.scaleb(int(decimals))
    if scaled != scaled.to_integral_value():
        raise IntentError("amount {!r} is not representable in {} decimals".format(amount, decimals))
    units = int(scaled)
    if units <= 0:
        raise IntentError("amount must be > 0, got {!r}".format(amount))
    return units


def base_units_to_amount(units: int, decimals: int) -> str:
    """Inverse of :func:`amount_to_base_units` (stable decimal representation)."""
    scaled = Decimal(int(units)).scaleb(-int(decimals))
    text = format(scaled, "f")
    return text


def compute_idempotency_key(intent: Dict[str, Any]) -> str:
    """``keccak256(canonical JSON without intent_id or created_at)`` (B5 §b.1)."""
    payload = {key: value for key, value in intent.items()
               if key not in ("intent_id", "created_at", "idempotency_key")}
    return "0x" + common.keccak256_hex(common.canonical_json(payload).encode("utf-8"))


def build_transfer_intent(*, chain_id: int, account: str, asset: str, amount: str,
                          recipient: str, expiry_minutes: int, decimals: int = 6,
                          justification: str = "", policy_version: str = "v1.0",
                          source: Optional[Dict[str, Any]] = None,
                          created_at: Optional[str] = None) -> Dict[str, Any]:
    """Builds a v1 ``transfer`` intent (schema B5 §b.1) — unsigned, unauthorized."""
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
    """v1 intent for a non-``transfer`` action (swap/approve/change_policy/revoke).

    Actions under approval have no scoped function in v1: the ``function`` field
    stays empty and the schema explicitly requires it.
    """
    if action not in ACTIONS_CONNUES:
        raise IntentError("unknown action: {!r}".format(action))
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
    """Deterministic validation of schema v1. Returns ``(ok, errors)``.

    Each error: ``{"code", "field", "detail"}`` — stable codes.
    """
    errors: List[Dict[str, str]] = []

    def fail(code: str, field: str, detail: str) -> None:
        errors.append({"code": code, "field": field, "detail": detail})

    if not isinstance(intent, dict):
        return False, [{"code": "SCHEMA_TYPE", "field": "<root>", "detail": "intent must be an object"}]

    for key in intent:
        if key not in ALLOWED_FIELDS:
            fail("SCHEMA_UNKNOWN_FIELD", key, "unknown field refused")

    for field in ("schema_version", "intent_id", "chain_id", "account", "action", "asset",
                  "amount", "amount_base_units", "recipient", "function", "params",
                  "expiry", "created_at"):
        if field not in intent:
            fail("SCHEMA_MISSING", field, "required field missing")

    if intent.get("schema_version") != SCHEMA_VERSION:
        fail("SCHEMA_VERSION", "schema_version", "expected {}".format(SCHEMA_VERSION))

    action = intent.get("action")
    if action not in ACTIONS_CONNUES:
        fail("ACTION_UNKNOWN", "action", "action outside the v1 catalog: {!r}".format(action))

    for field in ("account", "asset", "recipient"):
        value = intent.get(field)
        if not common.is_address(value):
            fail("SCHEMA_ADDRESS", field, "malformed address: {!r}".format(value))
        elif value != common.normalize_address(value):
            fail("SCHEMA_ADDRESS", field, "non-normalized address (lowercase expected)")

    chain_id = intent.get("chain_id")
    if not isinstance(chain_id, int) or isinstance(chain_id, bool) or chain_id <= 0:
        fail("SCHEMA_TYPE", "chain_id", "positive integer expected")

    amount = intent.get("amount")
    if not isinstance(amount, str):
        fail("SCHEMA_TYPE", "amount", "decimal string expected (never a float)")
    else:
        try:
            units = amount_to_base_units(amount, decimals)
        except IntentError as exc:
            fail("SCHEMA_AMOUNT", "amount", str(exc))
            units = None
        if units is not None:
            declared = intent.get("amount_base_units")
            if not isinstance(declared, str) or not declared.isdigit():
                fail("SCHEMA_TYPE", "amount_base_units", "integer string expected")
            elif int(declared) != units:
                fail("AMOUNT_BASE_UNITS_MISMATCH", "amount_base_units",
                     "declared {} ≠ recomputed {}".format(declared, units))

    params = intent.get("params")
    if not isinstance(params, dict):
        fail("SCHEMA_TYPE", "params", "object expected")
    function = intent.get("function")
    if action == "transfer":
        if function != common.TRANSFER_SIGNATURE:
            fail("FUNCTION_NOT_ALLOWED", "function",
                 "transfer requires {}".format(common.TRANSFER_SIGNATURE))
        if isinstance(params, dict):
            if params.get("to") != intent.get("recipient"):
                fail("PARAMS_RECIPIENT_MISMATCH", "params.to",
                     "params.to must equal recipient")
            if str(params.get("value")) != str(intent.get("amount_base_units")):
                fail("PARAMS_VALUE_MISMATCH", "params.value",
                     "params.value must equal amount_base_units")
    else:
        if function not in ("", None):
            fail("FUNCTION_NOT_ALLOWED", "function",
                 "no scoped function for action {!r} in v1".format(action))

    try:
        expiry = common.parse_rfc3339(intent.get("expiry"))
        created = common.parse_rfc3339(intent.get("created_at"))
        moment = common.parse_rfc3339(now) if now else common.utc_now_dt()
        if expiry <= moment:
            fail("INTENT_EXPIRED", "expiry", "expiry passed ({})".format(intent.get("expiry")))
        if expiry > moment + timedelta(minutes=int(ttl_minutes)):
            fail("INTENT_TTL_TOO_LONG", "expiry",
                 "expiry beyond now + {} min".format(ttl_minutes))
        if created > moment + timedelta(seconds=60):
            fail("INTENT_NOT_YET_VALID", "created_at", "created_at in the future")
    except ValueError as exc:
        fail("SCHEMA_TIME", "expiry", "unreadable timestamp: {}".format(exc))

    if require_key:
        key = intent.get("idempotency_key")
        if not isinstance(key, str) or len(key) != 66 or not key.startswith("0x"):
            fail("SCHEMA_MISSING", "idempotency_key", "idempotency key missing or malformed")
        else:
            recomputed = compute_idempotency_key(intent)
            if recomputed.lower() != key.lower():
                fail("IDEMPOTENCY_KEY_MISMATCH", "idempotency_key",
                     "recomputed key {} ≠ declared".format(recomputed))

    return (not errors), errors


def intent_calldata(intent: Dict[str, Any], *, decimals: int = 6) -> Dict[str, str]:
    """Intent calldata **after** ALLOW (separate step, B5 §b.1 rule 7).

    Returns ``{"to": <token contract>, "data": 0xa9059cbb…}`` — unsigned.
    """
    ok, errors = validate_intent(intent, ttl_minutes=10 ** 6, require_key=False)
    if not ok:
        codes = ", ".join(sorted({error["code"] for error in errors}))
        raise IntentError("invalid intent, calldata refused: {}".format(codes))
    if intent.get("action") != "transfer":
        raise IntentError("v1 calldata built only for transfer")
    units = int(intent["amount_base_units"])
    data = common.abi_encode_call(
        common.SELECTOR_TRANSFER,
        [common.enc_address(intent["recipient"]), common.enc_uint(units)],
    )
    return {"to": common.normalize_address(intent["asset"]), "data": data}


def intent_summary(intent: Dict[str, Any]) -> Dict[str, Any]:
    """Printable summary (never a secret, never a key)."""
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
