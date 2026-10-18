#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — fail-closed preflight, run before any transaction is signed.

The deterministic policy decides (ALLOW / DENY / REQUIRE_APPROVAL); this module
is the second gate: it re-checks the execution facts against the chain and
refuses to let a signature happen as soon as ONE control fails. A transport
error is never "unknown, carry on": it is a failure (fail-closed).

Design constraints
------------------
* **Standard library only** (``urllib``, ``json``, ``hashlib``-free here). No
  web3 / eth-account / requests: calldata is ABI-encoded by hand with integer
  arithmetic, token amounts are converted from ``str`` to base units without
  ever going through a rounded float.
* **Injectable transport**: every check talks to the node through the ``rpc``
  object (``JsonRpc`` by default). Tests inject a fake; no network is touched.
* **No secret leaves this module**: error details carry exception type names,
  never endpoints (an RPC URL may embed an API key).

Evaluation order (stop at the first FAIL)
-----------------------------------------
The declared order is::

    P1  POLICY_NOT_ALLOW
    P2  CHAIN_ID_MISMATCH
    P3  INTENT_EXPIRED
    P4  INTENT_ALREADY_PROCESSED
    P5  AGENT_PAUSED
    P7  TARGET_CODE_MISSING
    P12 GAS_ESTIMATE_FAILED
    P9a INSUFFICIENT_GAS_BALANCE
    P9b INSUFFICIENT_TOKEN_BALANCE
    P11 SIMULATION_REVERT

``P12`` runs BEFORE ``P9a`` on purpose: the gas balance control needs the gas
estimate (it requires ``balance >= 2 * estimate``), so the estimator must have
produced a number first. ``P12`` also builds the transfer calldata, which is
why an intent whose amount/recipient cannot be encoded fails there — always
fail-closed, never "could not check, so sign".

Names ``P6``, ``P8`` and ``P10`` are reserved by the wider design (approval,
nonce, fee checks) and are not implemented in this slice: no code exists for
them in ``CHECK_CODES`` and they are absent from ``CHECK_ORDER`` rather than
silently passing.

Skip semantics
--------------
Once a check fails, every later check stays in ``checks`` with status
``SKIP`` and detail ``"not evaluated: <blocking code>"``. A ``SKIP`` result
carries the code the check *would* have blocked with; only a ``PASS`` carries
an empty ``code``. This keeps a naive reader on the safe side: any non-empty
code means "this was not established", never "this passed".

What this module does NOT prove: recipient allow-listing and caps (that is the
policy's job, and P1 only trusts its verdict), ERC-20 allowance of the Safe,
nonce/fee sanity, finality, or that the Safe transaction was actually
approved by its owners. Those are out of scope here.
"""

import json
import math
import os
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

__all__ = [
    "CHECK_CODES",
    "CHECK_ORDER",
    "CheckResult",
    "GAS_BALANCE_MULTIPLIER",
    "INTENT_TTL_SECONDS",
    "JsonRpc",
    "MAX_GAS_LIMIT",
    "PreflightResult",
    "PreflightRpcError",
    "abi_encode_balance_of",
    "abi_encode_transfer",
    "amount_to_base_units",
    "decode_uint256",
    "hex_data",
    "run_preflight",
]

#: Stable failure codes, in catalogue order. Every failure reported by this
#: module is exactly one of these strings.
CHECK_CODES = (
    "POLICY_NOT_ALLOW",
    "CHAIN_ID_MISMATCH",
    "INTENT_EXPIRED",
    "INTENT_ALREADY_PROCESSED",
    "AGENT_PAUSED",
    "TARGET_CODE_MISSING",
    "INSUFFICIENT_GAS_BALANCE",
    "INSUFFICIENT_TOKEN_BALANCE",
    "SIMULATION_REVERT",
    "GAS_ESTIMATE_FAILED",
)

#: An intent is signable for 24 h after it was created.
INTENT_TTL_SECONDS = 24 * 3600

#: Hard ceiling on the gas limit sent with the transaction.
MAX_GAS_LIMIT = 500_000

#: gas_limit = ceil(5/4 * estimate), i.e. 25 % headroom, integer arithmetic.
GAS_LIMIT_NUMERATOR = 5
GAS_LIMIT_DENOMINATOR = 4

#: The agent EOA must hold at least this many times the estimated gas.
GAS_BALANCE_MULTIPLIER = 2

#: ERC-20 function selectors (hard-coded, no ABI file needed).
TRANSFER_SELECTOR = "a9059cbb"    # transfer(address,uint256)
BALANCE_OF_SELECTOR = "70a08231"  # balanceOf(address)

#: Kill switch read on every run.
PAUSE_ENV_NAME = "ORVYREN_K0_PAUSED"
_TRUTHY = frozenset({"1", "true", "yes", "on"})

#: Base Sepolia, the only chain this slice targets (callers still pass it in).
BASE_SEPOLIA_CHAIN_ID = 84532

_STATUSES = frozenset({"PASS", "FAIL", "SKIP"})


class PreflightRpcError(Exception):
    """Raised when a JSON-RPC call cannot be completed or returns an error.

    The message never contains the endpoint URL (it may embed an API key).
    """

    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


class JsonRpc:
    """Minimal JSON-RPC 2.0 client over ``urllib`` (POST, one attempt).

    ``call`` returns the ``result`` member verbatim and raises
    :class:`PreflightRpcError` for a transport error, an invalid JSON body, an
    ``error`` member, or a response without a ``result``. There is no retry
    loop: a retried call would hide the failure the preflight is meant to see.
    """

    def __init__(self, url, timeout=10.0):
        self.url = str(url)
        self.timeout = float(timeout)
        self._request_id = 0

    def call(self, method, params):
        """POST one JSON-RPC request and return its ``result``.

        Args:
            method: JSON-RPC method name, e.g. ``"eth_chainId"``.
            params: positional parameters list.

        Raises:
            PreflightRpcError: on any transport, decoding or JSON-RPC error.
        """
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": list(params),
        }
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except Exception as exc:  # fail-closed: no retry, no fallback
            raise PreflightRpcError(
                "rpc transport error calling {}: {}".format(method, type(exc).__name__)
            ) from exc
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise PreflightRpcError(
                "rpc returned invalid JSON for {}".format(method)
            ) from exc
        if not isinstance(decoded, dict):
            raise PreflightRpcError("rpc returned a non-object body for {}".format(method))
        error = decoded.get("error")
        if error:
            if isinstance(error, dict):
                code = error.get("code")
                message = str(error.get("message") or "error")
            else:
                code = None
                message = str(error)
            raise PreflightRpcError(
                "rpc error for {}: {} (code {})".format(method, message, code), code=code
            )
        if "result" not in decoded:
            raise PreflightRpcError("rpc response for {} has no result".format(method))
        return decoded["result"]


@dataclass(frozen=True)
class CheckResult:
    """Outcome of one preflight control."""

    code: str    # one of CHECK_CODES, or "" when the check passed
    name: str    # stable short id: P1, P2, P3, P4, P5, P7, P12, P9a, P9b, P11
    status: str  # "PASS" | "FAIL" | "SKIP"
    detail: str  # one line, English, no secrets

    def __post_init__(self):
        if self.status not in _STATUSES:
            raise ValueError("invalid check status {!r}".format(self.status))
        if self.code and self.code not in CHECK_CODES:
            raise ValueError("invalid check code {!r}".format(self.code))
        if self.status == "PASS" and self.code:
            raise ValueError("a PASS check must not carry a failure code")

    def to_dict(self):
        return {
            "name": self.name,
            "status": self.status,
            "code": self.code,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class PreflightResult:
    """Aggregate preflight outcome. ``ok`` is True only if every check passed."""

    ok: bool
    checks: tuple
    failed_code: str
    gas_limit: int
    gas_estimate: int

    def to_dict(self):
        """JSON-serialisable view with a deterministic key order."""
        return {
            "ok": bool(self.ok),
            "failed_code": self.failed_code,
            "gas_estimate": int(self.gas_estimate),
            "gas_limit": int(self.gas_limit),
            "checks": [check.to_dict() for check in self.checks],
        }


# --- ABI helpers (hand-rolled, integer arithmetic only) -----------------------

def _address_bytes(address, field_name="address"):
    """Decode a 0x-prefixed 20-byte hex address into raw bytes."""
    if not isinstance(address, str):
        raise ValueError("{} must be a 0x-prefixed 20-byte hex string".format(field_name))
    text = address.strip()
    if not text.lower().startswith("0x") or len(text) != 42:
        raise ValueError("{} must be a 0x-prefixed 20-byte hex string".format(field_name))
    try:
        raw = bytes.fromhex(text[2:])
    except ValueError as exc:
        raise ValueError("{} is not hexadecimal".format(field_name)) from exc
    if len(raw) != 20:
        raise ValueError("{} must decode to exactly 20 bytes".format(field_name))
    return raw


def _uint256_bytes(value, field_name="amount"):
    """Encode a non-negative integer as a 32-byte big-endian word."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("{} must be an integer".format(field_name))
    if value < 0:
        raise ValueError("{} must not be negative".format(field_name))
    if value >= 1 << 256:
        raise ValueError("{} does not fit in uint256".format(field_name))
    return value.to_bytes(32, "big")


def abi_encode_transfer(recipient, amount_base_units):
    """Encode ``transfer(address,uint256)`` calldata (4-byte selector + 2 words)."""
    return (
        bytes.fromhex(TRANSFER_SELECTOR)
        + b"\x00" * 12
        + _address_bytes(recipient, "recipient")
        + _uint256_bytes(amount_base_units, "amount_base_units")
    )


def abi_encode_balance_of(address):
    """Encode ``balanceOf(address)`` calldata (4-byte selector + 1 word)."""
    return bytes.fromhex(BALANCE_OF_SELECTOR) + b"\x00" * 12 + _address_bytes(address)


def hex_data(data):
    """Return ``data`` as a lowercase ``0x``-prefixed hex string.

    Accepts bytes-like objects and already-hex strings ("0x..." or bare hex);
    everything else is a TypeError so a wrong argument cannot silently become
    ``"0x"`` (which some nodes read as empty calldata).
    """
    if isinstance(data, str):
        text = data.strip()
        if not text:
            raise ValueError("hex string is empty")
        if text.lower().startswith("0x"):
            text = text[2:]
        try:
            bytes.fromhex(text)
        except ValueError as exc:
            raise ValueError("argument is not a hexadecimal string") from exc
        return "0x" + text.lower()
    if isinstance(data, (bytes, bytearray, memoryview)):
        return "0x" + bytes(data).hex()
    raise TypeError("hex_data expects bytes or a hex string, got {}".format(type(data).__name__))


def decode_uint256(hexstr):
    """Decode a JSON-RPC quantity/data word into a non-negative int.

    Accepts an int (some providers normalize) or a hex string; ``"0x"`` and
    ``""`` decode to 0. Anything else raises ValueError.
    """
    if isinstance(hexstr, bool):
        raise ValueError("expected a hex string, got a boolean")
    if isinstance(hexstr, int):
        if hexstr < 0:
            raise ValueError("expected a non-negative integer")
        return hexstr
    if not isinstance(hexstr, str):
        raise ValueError("expected a hex string, got {}".format(type(hexstr).__name__))
    text = hexstr.strip()
    if text == "" or text.lower() == "0x":
        return 0
    if text.lower().startswith("0x"):
        text = text[2:]
    try:
        return int(text, 16)
    except ValueError as exc:
        raise ValueError("value is not a hexadecimal quantity") from exc


def amount_to_base_units(value, decimals):
    """Convert a token amount to integer base units, without float rounding.

    ``decimals`` decimal places are accepted, never more. Inputs may be ``str``,
    ``int``, ``Decimal`` or ``float`` (a float is read through its shortest
    repr; a float whose repr is exponential, e.g. ``1e-06``, is still exact
    here because the conversion is integer arithmetic on the decimal digits).

    Rejected with ValueError: scientific notation in a *string* ("1e-6"),
    a leading sign ("-1", "+1"), a non-finite value, a negative amount, and any
    amount carrying more than ``decimals`` decimal places ("1.0000001" with
    ``decimals=6``).

    Examples:
        >>> amount_to_base_units("1.0", 6)
        1000000
        >>> amount_to_base_units("0.000001", 6)
        1
    """
    if isinstance(value, bool):
        raise ValueError("amount must be a decimal number, not a boolean")
    if isinstance(decimals, bool) or not isinstance(decimals, int):
        raise ValueError("decimals must be an integer")
    if decimals < 0 or decimals > 36:
        raise ValueError("decimals must be between 0 and 36")

    if isinstance(value, int):
        decimal_value = Decimal(value)
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("amount must be finite")
        decimal_value = Decimal(repr(value))
    elif isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("amount is empty")
        if "e" in text.lower():
            raise ValueError("amount must not use scientific notation: {!r}".format(value))
        if text[0] in "+-":
            raise ValueError("amount must not carry a sign: {!r}".format(value))
        try:
            decimal_value = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError("amount is not a decimal number: {!r}".format(value)) from exc
    else:
        raise TypeError("amount must be str, int, Decimal or float, got {}".format(
            type(value).__name__))

    if not decimal_value.is_finite():
        raise ValueError("amount must be finite")
    if decimal_value < 0:
        raise ValueError("amount must not be negative")

    sign, digits, exponent = decimal_value.as_tuple()
    if exponent < -decimals:
        raise ValueError(
            "amount {!r} has more than {} decimal places".format(value, decimals))
    digits_value = int("".join(str(digit) for digit in digits)) if digits else 0
    return (1 if sign == 0 else -1) * digits_value * 10 ** (exponent + decimals)


def _gas_limit(gas_estimate):
    """ceil(5/4 * estimate), capped at MAX_GAS_LIMIT (integer arithmetic)."""
    scaled = (
        gas_estimate * GAS_LIMIT_NUMERATOR + GAS_LIMIT_DENOMINATOR - 1
    ) // GAS_LIMIT_DENOMINATOR
    return min(MAX_GAS_LIMIT, scaled)


# --- times -------------------------------------------------------------------

def _one_line(text):
    """Collapse a detail message to a single line."""
    return " ".join(str(text).split())


def _as_utc(value, field_name):
    """Return an aware UTC datetime, or raise ValueError (naive is refused)."""
    if isinstance(value, str):
        text = value.strip()
        if text[-1:] in ("Z", "z"):
            text = text[:-1] + "+00:00"
        try:
            value = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError("{} is not an ISO-8601 datetime".format(field_name)) from exc
    if not isinstance(value, datetime):
        raise ValueError("{} must be a datetime, got {}".format(
            field_name, type(value).__name__))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            "{} is timezone-naive; a timezone-aware datetime is required".format(field_name))
    return value.astimezone(timezone.utc)


# --- checks ------------------------------------------------------------------

@dataclass
class _Context:
    """State shared by the checks (gas figures are produced by P12)."""

    intent: object
    policy_verdict: str
    processed: frozenset
    now: object
    rpc: object
    expected_chain_id: int
    agent_address: str
    treasury_address: str
    token_address: str
    token_decimals: int
    env: object
    gas_estimate: int = 0
    gas_limit: int = 0
    amount_base_units: int = 0
    calldata: bytes = field(default=b"")


def _check_policy(ctx):
    if ctx.policy_verdict == "ALLOW":
        return True, "policy verdict is ALLOW"
    return False, "policy verdict {!r} is not ALLOW".format(ctx.policy_verdict)


def _check_chain_id(ctx):
    try:
        chain_id = decode_uint256(ctx.rpc.call("eth_chainId", []))
    except Exception as exc:  # transport, JSON-RPC error or bad payload
        return False, "cannot read the chain id from rpc (fail-closed): {}".format(
            type(exc).__name__)
    if chain_id != ctx.expected_chain_id:
        return False, "chain id {} does not match expected {}".format(
            chain_id, ctx.expected_chain_id)
    return True, "chain id {}".format(chain_id)


def _check_expiry(ctx):
    try:
        created_at = _as_utc(ctx.intent.created_at, "intent.created_at")
        now = _as_utc(ctx.now, "now")
    except ValueError as exc:
        return False, str(exc)
    expires_at = created_at + timedelta(seconds=INTENT_TTL_SECONDS)
    if expires_at > now:
        return True, "intent valid until {}".format(expires_at.isoformat())
    return False, "intent expired at {} (ttl {} s)".format(
        expires_at.isoformat(), INTENT_TTL_SECONDS)


def _check_processed(ctx):
    intent_id = str(getattr(ctx.intent, "intent_id", ""))
    if intent_id in ctx.processed:
        return False, "intent {} was already processed".format(intent_id)
    return True, "intent {} was not processed before".format(intent_id)


def _check_pause(ctx):
    raw = ctx.env.get(PAUSE_ENV_NAME)
    if raw is not None and str(raw).strip().lower() in _TRUTHY:
        return False, "execution is paused by {}".format(PAUSE_ENV_NAME)
    return True, "kill switch is not set ({})".format(PAUSE_ENV_NAME)


def _check_target_code(ctx):
    try:
        code = ctx.rpc.call("eth_getCode", [ctx.token_address, "latest"])
    except Exception as exc:
        return False, "cannot read the token contract code (fail-closed): {}".format(
            type(exc).__name__)
    if not isinstance(code, str) or code.strip().lower() in ("", "0x", "0x0"):
        return False, "no contract code at the token address on the latest block"
    return True, "token contract code present ({} bytes)".format(
        max(0, (len(code.strip()) - 2) // 2))


def _check_gas_estimate(ctx):
    # P12 also builds the transfer calldata, so an intent that cannot be encoded
    # is refused here rather than allowed to reach the signer unchecked.
    try:
        ctx.amount_base_units = amount_to_base_units(ctx.intent.amount, ctx.token_decimals)
        ctx.calldata = abi_encode_transfer(ctx.intent.recipient, ctx.amount_base_units)
    except (TypeError, ValueError) as exc:
        return False, "intent amount or recipient cannot be encoded (fail-closed): {}".format(
            _one_line(exc))
    call = {
        "from": ctx.treasury_address,
        "to": ctx.token_address,
        "data": hex_data(ctx.calldata),
    }
    try:
        ctx.gas_estimate = decode_uint256(ctx.rpc.call("eth_estimateGas", [call]))
    except Exception as exc:
        return False, "gas estimate failed: {}".format(type(exc).__name__)
    if ctx.gas_estimate <= 0:
        return False, "gas estimate is zero"
    ctx.gas_limit = _gas_limit(ctx.gas_estimate)
    return True, "gas estimate {}, gas limit {}".format(ctx.gas_estimate, ctx.gas_limit)


def _check_gas_balance(ctx):
    required = GAS_BALANCE_MULTIPLIER * ctx.gas_estimate
    try:
        balance = decode_uint256(ctx.rpc.call("eth_getBalance", [ctx.agent_address, "latest"]))
    except Exception as exc:
        return False, "cannot read the agent gas balance (fail-closed): {}".format(
            type(exc).__name__)
    if balance < required:
        return False, "agent balance {} wei is below the required {} wei ({}x gas estimate {})".format(
            balance, required, GAS_BALANCE_MULTIPLIER, ctx.gas_estimate)
    return True, "agent balance {} wei covers the required {} wei".format(balance, required)


def _check_token_balance(ctx):
    try:
        required = amount_to_base_units(ctx.intent.amount, ctx.token_decimals)
        call = {
            "to": ctx.token_address,
            "data": hex_data(abi_encode_balance_of(ctx.treasury_address)),
        }
        balance = decode_uint256(ctx.rpc.call("eth_call", [call, "latest"]))
    except Exception as exc:
        return False, "cannot read the treasury token balance (fail-closed): {}".format(
            type(exc).__name__)
    if balance < required:
        return False, "treasury token balance {} is below the required {} base units".format(
            balance, required)
    return True, "treasury token balance {} covers the required {} base units".format(
        balance, required)


def _check_simulation(ctx):
    try:
        call = {
            "from": ctx.treasury_address,
            "to": ctx.token_address,
            "data": hex_data(abi_encode_transfer(
                ctx.intent.recipient,
                amount_to_base_units(ctx.intent.amount, ctx.token_decimals))),
        }
        returned = ctx.rpc.call("eth_call", [call, "latest"])
    except Exception as exc:
        return False, "transfer simulation reverted: {}".format(type(exc).__name__)
    if isinstance(returned, str) and returned.strip().lower() not in ("", "0x"):
        try:
            decoded = decode_uint256(returned)
        except ValueError:
            return False, "transfer simulation returned unreadable data"
        if decoded == 0:
            return False, "transfer simulation returned false"
    return True, "transfer simulation succeeded"


#: Declared evaluation order; P12 precedes P9a because the gas balance needs the
#: estimate. See the module docstring.
CHECK_ORDER = (
    ("P1", "POLICY_NOT_ALLOW", _check_policy),
    ("P2", "CHAIN_ID_MISMATCH", _check_chain_id),
    ("P3", "INTENT_EXPIRED", _check_expiry),
    ("P4", "INTENT_ALREADY_PROCESSED", _check_processed),
    ("P5", "AGENT_PAUSED", _check_pause),
    ("P7", "TARGET_CODE_MISSING", _check_target_code),
    ("P12", "GAS_ESTIMATE_FAILED", _check_gas_estimate),
    ("P9a", "INSUFFICIENT_GAS_BALANCE", _check_gas_balance),
    ("P9b", "INSUFFICIENT_TOKEN_BALANCE", _check_token_balance),
    ("P11", "SIMULATION_REVERT", _check_simulation),
)


def _processed_ids(processed_intent_ids):
    """Normalise the replay ledger into a frozenset of strings."""
    if processed_intent_ids is None:
        return frozenset()
    if isinstance(processed_intent_ids, str):
        return frozenset({processed_intent_ids})
    try:
        return frozenset(str(item) for item in processed_intent_ids)
    except TypeError:
        return frozenset()


def run_preflight(intent, *, policy_verdict, processed_intent_ids, now, rpc,
                  expected_chain_id, agent_address, treasury_address, token_address,
                  token_decimals=6, env=None):
    """Run every control in ``CHECK_ORDER`` and stop at the first failure.

    Args:
        intent: an ``orvyren.execution.intents.Intent`` (or any object exposing
            ``intent_id``, ``amount``, ``recipient``, ``created_at``).
        policy_verdict: the deterministic policy verdict; only ``"ALLOW"`` passes.
        processed_intent_ids: ids already executed (replay protection).
        now: timezone-aware datetime (or ISO-8601 string) used for expiry.
        rpc: transport exposing ``call(method, params)`` (``JsonRpc`` by default).
        expected_chain_id: chain the transaction must target.
        agent_address: EOA paying the gas.
        treasury_address: the Safe acting as the transaction ``sender``.
        token_address: ERC-20 contract (USDC on Base Sepolia).
        token_decimals: token decimals, 6 for USDC.
        env: mapping used for the kill switch; ``os.environ`` when None.

    Returns:
        PreflightResult: ``ok`` is True only when all checks passed. On failure
        ``failed_code`` names the blocking control and the remaining checks are
        reported as ``SKIP`` / ``"not evaluated: <code>"``.

    Raises:
        TypeError: if ``rpc`` has no ``call`` method (programming error, not a
            chain condition).
    """
    if rpc is None or not callable(getattr(rpc, "call", None)):
        raise TypeError("rpc must expose a call(method, params) method")
    if isinstance(token_decimals, bool) or not isinstance(token_decimals, int):
        raise TypeError("token_decimals must be an integer")

    ctx = _Context(
        intent=intent,
        policy_verdict=policy_verdict,
        processed=_processed_ids(processed_intent_ids),
        now=now,
        rpc=rpc,
        expected_chain_id=int(expected_chain_id),
        agent_address=agent_address,
        treasury_address=treasury_address,
        token_address=token_address,
        token_decimals=token_decimals,
        env=os.environ if env is None else env,
    )

    checks = []
    failed_code = ""
    for name, code, evaluator in CHECK_ORDER:
        if failed_code:
            checks.append(CheckResult(
                code=code, name=name, status="SKIP",
                detail=_one_line("not evaluated: {}".format(failed_code))))
            continue
        try:
            passed, detail = evaluator(ctx)
        except Exception as exc:  # fail-closed: an unexpected error blocks signing
            passed, detail = False, "check raised {} (fail-closed)".format(type(exc).__name__)
        if passed:
            checks.append(CheckResult(code="", name=name, status="PASS",
                                      detail=_one_line(detail)))
        else:
            failed_code = code
            checks.append(CheckResult(code=code, name=name, status="FAIL",
                                      detail=_one_line(detail)))

    return PreflightResult(
        ok=(failed_code == ""),
        checks=tuple(checks),
        failed_code=failed_code,
        gas_limit=ctx.gas_limit,
        gas_estimate=ctx.gas_estimate,
    )
