#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — testnet demo kit: shared helpers (**stdlib only**).

This module never reads or writes a private key: the key lives only in the
signing process environment and is read only by
:mod:`scripts.demo.signer`. Sensitive variable names are reported by
``orvyren.execution.guard.present_secret_env_names`` (by NAME only).

Contents:

* repository paths + import of the existing ``src/orvyren`` code (house style,
  like ``scripts/recon_common.py``);
* hashes: SHA-256 (stdlib, the journal standard B6 R-2) and **pure-Python
  Keccak-256** (validated on the vectors ``keccak256("")`` / ``keccak256("abc")``,
  taken from ``research/raw_b5/keccak_selectors.py``) — required to compute
  ``idempotency_key`` (B5 §b.1) and the selectors;
* minimal ABI encoding (32-byte words, dynamic ``bytes``);
* **read-only** JSON-RPC client (reuses ``orvyren.execution.chain.rpc``,
  User-Agent included: the public Base Sepolia RPC rejects requests without a UA);
* SHA-256 chained append-only journal (format B6 §1.3), idempotency registry,
  signature log, K0 pause flag;
* loading of the session configuration (demo ``.env``, never
  versioned) and of the demo policy (``policy.demo.json``).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(HERE)
ROOT = os.path.dirname(SCRIPTS_DIR)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:  # pragma: no cover - depends on the execution mode
    sys.path.insert(0, SRC)

from orvyren.execution import chain as chain_client  # noqa: E402
from orvyren.execution.guard import mask_rpc_url, present_secret_env_names  # noqa: E402
from orvyren.policy import (  # noqa: E402
    ALLOWED_ASSET,
    Intent,
    PolicyConfig,
    evaluate,
)

# --- demo plan constants (W2C §g, B5 §b, verified 2026-10-15) --------------

CHAIN_ID_DEMO = 84532                     # Base Sepolia (FREEZE_V2: testnet accepted)
DEFAULT_RPC_URL = "https://sepolia.base.org"
RPC_TIMEOUT_SECONDS = 30

#: Zodiac role "AGENT": ASCII label (<= 32 bytes, a-z 0-9 _), right-padded with zeros (W2C §g.0).
ROLE_KEY_AGENT = "0x" + b"AGENT".hex() + "00" * 27

#: Selectors **verified** on Base Sepolia on 2026-10-15 (research/raw_b5/SELECTEURS_VERIFIES.md).
SELECTOR_TRANSFER = "0xa9059cbb"           # transfer(address,uint256)
SELECTOR_BALANCE_OF = "0x70a08231"         # balanceOf(address)
SELECTOR_ALLOWANCE = "0xdd62ed3e"          # allowance(address,address)
SELECTOR_EXEC_TX_WITH_ROLE = "0xc6fe8747"  # execTransactionWithRole(address,uint256,bytes,uint8,bytes32,bool)
SELECTOR_EXEC_TX_WITH_ROLE_RET = "0x2b99e506"  # execTransactionWithRoleReturnData(...)
SELECTOR_ASSIGN_ROLES = "0x957ed2b3"       # assignRoles(address,bytes32[],bool[])
SELECTOR_ALLOW_TARGET = "0x7b0da5b2"       # allowTarget(bytes32,address,uint8)
ERROR_NOT_AUTHORIZED = "0xfd8e9f28"        # NoMembership() — revert of a non-member; MEASURED on-chain on 2026-10-16 (the 0x4a0bfec1 "NotAuthorized" hypothesis came from a doc note — measurement wins)

#: Topic0 of the ERC-20 Transfer event (recomputed, equal to the orvyren.execution.verify constant).
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

#: Plan addresses (to be re-verified on demo day with eth_getCode — protocol B5 §e.7).
KNOWN_ADDRESSES = {
    "module_roles_officiel": "0xF2964CE6161ce0e75964Fe7927cE114cb0B283D5",  # clean instance required for the demo Safe
    "usdc_circle_base_sepolia": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
    "usdc_aave_base_sepolia": "0xba50Cd2A20f6DA35D788639E581bca8d0B5d4D5f",
    "weth_predeploy": "0x4200000000000000000000000000000000000006",
    "safe_l2_singleton_1_4_1": "0x29fcB43b46531BcA003ddC8FCB67FFE91900C762",
    "safe_proxy_factory_1_4_1": "0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67",
    "multisend_call_only_1_4_1": "0x40A2aCCbd92BCA938b02010E17A5b8929b49130D",
    "swap_router02": "0x94cC0AaC535CCDB3C01d6787D6413C739ae12bc4",
    "uniswap_v3_factory": "0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24",
    "quoter_v2": "0xC5290058841028F1614F3A6F0F5816cAd0df5E27",
    "aave_v3_pool": "0x8bAB6d1b75f19e9eD9fCe8b9BD338844fF79aE27",
    "eas": "0x4200000000000000000000000000000000000021",
}

TRANSFER_SIGNATURE = "transfer(address,uint256)"

# --- time --------------------------------------------------------------------


def utc_now() -> str:
    """RFC 3339 UTC timestamp to the second (``2026-10-15T12:00:00Z``)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_now_dt() -> datetime:
    return datetime.now(timezone.utc)


def parse_rfc3339(text: str) -> datetime:
    """Parses an RFC 3339 timestamp (tolerates the ``Z`` suffix) into a UTC datetime."""
    if not isinstance(text, str):
        raise ValueError("not an RFC 3339 timestamp: {!r}".format(text))
    value = text.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# --- canonical serialization ------------------------------------------------


def canonical_json(obj: Any) -> str:
    """Project canonical JSON: sorted keys, tight separators, UTF-8 (B6 §1.2)."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: str, default: Any = None) -> Any:
    """Reads a JSON file; returns ``default`` if absent, raises if invalid."""
    if not os.path.isfile(path):
        return default
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def display_path(path: Any, root: Optional[str] = None) -> str:
    """Readable path: repo-relative when possible, absolute otherwise.

    Never raises (unlike ``os.path.relpath``, which fails across two
    Windows drives): a hashed artifact must not depend on the machine.
    """
    text = str(path)
    try:
        relative = os.path.relpath(text, root or ROOT)
    except ValueError:
        return text.replace(os.sep, "/")
    if relative == ".." or relative.startswith(".." + os.sep) or relative.startswith("../"):
        return text.replace(os.sep, "/")
    return relative.replace(os.sep, "/")


def write_json(path: str, payload: Any) -> None:
    """Writes indented JSON, atomic replacement (never a truncated file)."""
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    temporary = "{}.tmp".format(path)
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def append_jsonl(path: str, payload: Any) -> None:
    """Appends one JSON line (the journal's only write mode: append-only)."""
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")


def read_jsonl(path: str) -> List[Any]:
    """Reads a JSONL file; an unreadable line is reported (never silently)."""
    records: List[Any] = []
    if not os.path.isfile(path):
        return records
    with open(path, "r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                records.append(json.loads(text))
            except ValueError as exc:
                raise ValueError("{}: unreadable line {}: {}".format(path, number, exc))
    return records


# --- Keccak-256 (Python pur, stdlib) -----------------------------------------
# Implementation taken from research/raw_b5/keccak_selectors.py (validated on the
# known vectors): required because hashlib does not provide Keccak-256.

_RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]
_ROT = [
    [0, 36, 3, 41, 18],
    [1, 44, 10, 45, 2],
    [62, 6, 43, 15, 61],
    [28, 55, 25, 21, 56],
    [27, 20, 39, 8, 14],
]
_MASK64 = (1 << 64) - 1

KECCAK_EMPTY = "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
KECCAK_ABC = "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45"


def _rol64(x: int, n: int) -> int:
    n %= 64
    return ((x << n) | (x >> (64 - n))) & _MASK64 if n else x


def _keccak_f(state: List[List[int]]) -> List[List[int]]:
    for rnd in range(24):
        c = [state[x][0] ^ state[x][1] ^ state[x][2] ^ state[x][3] ^ state[x][4] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rol64(c[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                state[x][y] ^= d[x]
        b = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                b[y][(2 * x + 3 * y) % 5] = _rol64(state[x][y], _ROT[x][y])
        for x in range(5):
            for y in range(5):
                state[x][y] = b[x][y] ^ ((~b[(x + 1) % 5][y]) & b[(x + 2) % 5][y])
        state[0][0] ^= _RC[rnd]
    return state


_keccak_cache: Dict[bytes, str] = {}
_keccak_lock = threading.Lock()


def keccak256(data: bytes) -> bytes:
    """Keccak-256 (Ethereum variant, 0x01 padding) in pure Python."""
    rate = 136
    padlen = rate - (len(data) % rate)
    if padlen == 1:
        padded = data + b"\x81"
    else:
        padded = data + b"\x01" + b"\x00" * (padlen - 2) + b"\x80"
    state = [[0] * 5 for _ in range(5)]
    for offset in range(0, len(padded), rate):
        block = padded[offset:offset + rate]
        for index in range(rate // 8):
            lane = int.from_bytes(block[index * 8:(index + 1) * 8], "little")
            state[index % 5][index // 5] ^= lane
        _keccak_f(state)
    out = b""
    for index in range(4):
        out += state[index % 5][index // 5].to_bytes(8, "little")
    return out


def keccak256_hex(data: bytes) -> str:
    with _keccak_lock:
        cached = _keccak_cache.get(data)
    if cached is None:
        cached = keccak256(data).hex()
        with _keccak_lock:
            _keccak_cache[data] = cached
    return cached


def selector(signature: str) -> str:
    """4-byte selector of a canonical ASCII signature (``0xa9059cbb``)."""
    return "0x" + keccak256(signature.encode("ascii"))[:4].hex()


# --- ABI minimal -------------------------------------------------------------


def enc_uint(value: int) -> str:
    number = int(value)
    if number < 0 or number >= 1 << 256:
        raise ValueError("enc_uint: value outside 256 bits: {!r}".format(value))
    return "{:064x}".format(number)


def enc_address(address: str) -> str:
    return normalize_address(address)[2:].rjust(64, "0")


def enc_bytes32(value: str) -> str:
    body = value[2:] if value.startswith("0x") else value
    if len(body) != 64 or not all(c in "0123456789abcdefABCDEF" for c in body):
        raise ValueError("enc_bytes32: expected 32 hex bytes: {!r}".format(value))
    return body.lower()


def enc_bytes_dynamic(data_hex: str) -> str:
    """Encoding of a dynamic ``bytes`` (length + data padded to 32 bytes)."""
    body = data_hex[2:] if data_hex.startswith("0x") else data_hex
    if len(body) % 2:
        raise ValueError("enc_bytes_dynamic: odd hex length: {!r}".format(data_hex[:20]))
    padded = body + "0" * ((64 - len(body) % 64) % 64)
    return enc_uint(len(body) // 2) + padded


def enc_bool(value: bool) -> str:
    return enc_uint(1 if value else 0)


def decode_word_uint(payload: str, index: int = 0) -> int:
    body = payload[2:] if payload.startswith("0x") else payload
    if len(body) < (index + 1) * 64:
        raise ValueError("decode_word_uint: payload too short")
    return int(body[index * 64:(index + 1) * 64], 16)


def decode_word_address(payload: str, index: int = 0) -> str:
    return "0x" + "{:040x}".format(decode_word_uint(payload, index) % (1 << 160))


def decode_word_bool(payload: str, index: int = 0) -> bool:
    return decode_word_uint(payload, index) != 0


def decode_word_bytes32(payload: str, index: int = 0) -> str:
    body = payload[2:] if payload.startswith("0x") else payload
    return "0x" + body[index * 64:(index + 1) * 64].lower()


def hex_to_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    text = str(value).strip()
    return int(text, 16)


# --- addresses ---------------------------------------------------------------


def is_address(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if len(text) != 42 or not text.startswith("0x"):
        return False
    return all(c in "0123456789abcdefABCDEF" for c in text[2:])


def normalize_address(address: Any, context: str = "address") -> str:
    """Address normalized to lowercase — **no repair** (refused if malformed)."""
    if not is_address(address):
        raise ValueError("invalid {}: {!r} (expected 0x + 40 hex)".format(context, address))
    return "0x" + str(address).strip()[2:].lower()


def short_address(address: Any) -> str:
    if isinstance(address, str) and len(address) > 20:
        return "{}…{}".format(address[:8], address[-6:])
    return str(address)


# --- ULID --------------------------------------------------------------------


_ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ulid_lock = threading.Lock()
_ulid_last_ms = 0
_ulid_last_random = 0


def ulid() -> str:
    """ULID (26 Crockford base32 characters, time-sorted) — pure stdlib."""
    global _ulid_last_ms, _ulid_last_random
    with _ulid_lock:
        now_ms = int(time.time() * 1000)
        if now_ms == _ulid_last_ms:
            _ulid_last_random += 1
        else:
            _ulid_last_ms = now_ms
            _ulid_last_random = int.from_bytes(os.urandom(10), "big")
        timestamp, randomness = _ulid_last_ms, _ulid_last_random
    value = ((timestamp & ((1 << 48) - 1)) << 80) | (randomness & ((1 << 80) - 1))
    chars = []
    for shift in range(125, -1, -5):
        chars.append(_ULID_ALPHABET[(value >> shift) & 0x1F])
    return "".join(chars)


# --- JSON-RPC client (read-only) --------------------------------------------


def rpc(url: str, method: str, params: Optional[Sequence[Any]] = None,
        timeout: int = RPC_TIMEOUT_SECONDS) -> Any:
    """Single JSON-RPC call — delegates to ``orvyren.execution.chain.rpc`` (UA included, URL masked)."""
    return chain_client.rpc(url or DEFAULT_RPC_URL, method, list(params or []), timeout)


def eth_chain_id(url: str, timeout: int = RPC_TIMEOUT_SECONDS) -> int:
    return hex_to_int(rpc(url, "eth_chainId", [], timeout))


def eth_block_number(url: str, timeout: int = RPC_TIMEOUT_SECONDS) -> int:
    return hex_to_int(rpc(url, "eth_blockNumber", [], timeout))


def eth_get_code(url: str, address: str, block: str = "latest",
                 timeout: int = RPC_TIMEOUT_SECONDS) -> str:
    return rpc(url, "eth_getCode", [normalize_address(address), block], timeout)


def eth_get_transaction_count(url: str, address: str, block: str = "pending",
                              timeout: int = RPC_TIMEOUT_SECONDS) -> int:
    return hex_to_int(rpc(url, "eth_getTransactionCount", [normalize_address(address), block], timeout))


def eth_gas_price(url: str, timeout: int = RPC_TIMEOUT_SECONDS) -> int:
    return hex_to_int(rpc(url, "eth_gasPrice", [], timeout))


def eth_get_balance(url: str, address: str, block: str = "latest",
                    timeout: int = RPC_TIMEOUT_SECONDS) -> int:
    return hex_to_int(rpc(url, "eth_getBalance", [normalize_address(address), block], timeout))


def eth_get_block(url: str, tag: str = "latest", timeout: int = RPC_TIMEOUT_SECONDS) -> Dict[str, Any]:
    block = rpc(url, "eth_getBlockByNumber", [tag, False], timeout)
    if not isinstance(block, dict):
        raise chain_client.ChainError("eth_getBlockByNumber({}) returned {}".format(tag, type(block).__name__))
    return block


def eth_call(url: str, to: str, data: str, block: str = "latest",
             timeout: int = RPC_TIMEOUT_SECONDS) -> str:
    return rpc(url, "eth_call", [{"to": normalize_address(to), "data": data}, block], timeout)


def eth_estimate_gas(url: str, from_address: str, to: str, data: str,
                     timeout: int = RPC_TIMEOUT_SECONDS) -> int:
    return hex_to_int(rpc(url, "eth_estimateGas",
                          [{"from": normalize_address(from_address),
                            "to": normalize_address(to), "data": data}], timeout))


def rpc_call_raw(url: str, method: str, params: Optional[Sequence[Any]] = None,
                 timeout: int = RPC_TIMEOUT_SECONDS) -> Any:
    """Public alias (tests inject a fake transport through ``rpc``)."""
    return rpc(url, method, params, timeout)


def revert_selector(data: Any) -> str:
    """Selector of a revert (first 4 bytes of the raw return), or '0x' if empty."""
    if not isinstance(data, str):
        return "0x"
    body = data[2:] if data.startswith("0x") else data
    return "0x" + body[:8].lower()


# --- session configuration (.env) -------------------------------------------


class ConfigurationError(Exception):
    """Incomplete or invalid demo configuration."""


def read_env_file(path: str) -> Dict[str, str]:
    """Reads a ``.env`` file (KEY=VALUE); **values are never printed**."""
    values: Dict[str, str] = {}
    if not os.path.isfile(path):
        return values
    with open(path, "r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            values[key] = value
    return values


def load_session_env(env_file: Optional[str] = None, environ: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Demo session: ``.env`` file then environment variables (which take precedence).

    The ``.env`` file is never versioned (``.gitignore``) and never
    written by the kit. Sensitive values do not leave this function.
    """
    environ = os.environ if environ is None else environ
    merged: Dict[str, str] = {}
    if env_file:
        merged.update(read_env_file(env_file))
    for key, value in environ.items():
        if key.startswith("ORVYREN_") and str(value).strip() != "":
            merged[key] = str(value)
    return merged


def safe_env_view(env: Dict[str, str]) -> Dict[str, Any]:
    """Printable view of a configuration: names + presence, never a sensitive value."""
    view: Dict[str, Any] = {"secret_env_names_present": list(present_secret_env_names(env))}
    for key in sorted(env):
        if key in ("ORVYREN_PRIVATE_KEY", "ORVYREN_SIGNER_KEY", "ORVYREN_SIGNER_KEYFILE",
                   "ORVYREN_MNEMONIC", "ORVYREN_SEED"):
            view[key] = "<present — never read or displayed>" if env[key] else ""
        elif "RPC" in key.upper():
            view[key] = mask_rpc_url(env[key])
        else:
            view[key] = env[key]
    return view


class SessionConfig:
    """Configuration of a demo session (addresses, RPC, paths)."""

    REQUIRED_ADDRESS_KEYS = (
        "ORVYREN_SAFE_ADDRESS",         # the Safe (avatar) — holder of the funds
        "ORVYREN_AGENT_ADDRESS",        # the throwaway EOA member of the AGENT role
        "ORVYREN_MODULE_ADDRESS",       # Roles module deployed FOR this Safe
        "ORVYREN_USDC_ADDRESS",         # Circle test USDC (transfers)
        "ORVYREN_RECIPIENT_B",          # allowlisted recipient B
        "ORVYREN_RECIPIENT_C",          # allowlisted recipient C
    )

    def __init__(self, env: Dict[str, str]):
        self.env = env
        self.rpc_url = env.get("ORVYREN_RPC_URL_BASE_SEPOLIA") or DEFAULT_RPC_URL
        self.chain_id = int(env.get("ORVYREN_CHAIN_ID") or CHAIN_ID_DEMO)
        self.timeout = int(env.get("ORVYREN_RPC_TIMEOUT_SECONDS") or RPC_TIMEOUT_SECONDS)
        self.recipients: Dict[str, str] = {}
        for label, key in (("B", "ORVYREN_RECIPIENT_B"), ("C", "ORVYREN_RECIPIENT_C"),
                           ("D_unlisted", "ORVYREN_RECIPIENT_UNLISTED")):
            value = env.get(key)
            self.recipients[label] = normalize_address(value, key) if value else ""

    @classmethod
    def from_env(cls, env_file: Optional[str] = None,
                 environ: Optional[Dict[str, str]] = None) -> "SessionConfig":
        return cls(load_session_env(env_file, environ))

    def require_addresses(self, keys: Optional[Iterable[str]] = None) -> Dict[str, str]:
        """Returns the required addresses or raises a readable error (list of the missing ones)."""
        keys = tuple(keys or self.REQUIRED_ADDRESS_KEYS)
        addresses: Dict[str, str] = {}
        missing: List[str] = []
        for key in keys:
            value = (self.env.get(key) or "").strip()
            if not value:
                missing.append(key)
                continue
            addresses[key] = normalize_address(value, key)
        if missing:
            raise ConfigurationError(
                "incomplete configuration — fill in .env: {}".format(", ".join(missing)))
        return addresses

    def safe_view(self) -> Dict[str, Any]:
        return safe_env_view(self.env)


# --- demo policy -------------------------------------------------------------


class PolicyReference:
    """Demo off-chain policy, loaded from ``policy.demo.json``."""

    def __init__(self, data: Dict[str, Any], recipients: Dict[str, str]):
        self.data = dict(data or {})
        self.recipients = {k: normalize_address(v) for k, v in (recipients or {}).items() if v}
        self.version = str(self.data.get("policy_version") or "v1.0")
        self.chain_id = int(self.data.get("chain_id") or CHAIN_ID_DEMO)
        self.asset = normalize_address(self.data.get("asset") or ALLOWED_ASSET, "policy.asset")
        self.asset_symbol = str(self.data.get("asset_symbol") or "USDC (test)")
        self.asset_decimals = int(self.data.get("asset_decimals") or 6)
        self.max_per_tx = float(self.data.get("max_per_tx", 100.0))
        self.max_cumulative_24h = float(self.data.get("max_cumulative_24h", 300.0))
        self.max_calls_24h = int(self.data.get("max_calls_24h", 10))
        self.ttl_intent_minutes = int(self.data.get("ttl_intent_minutes", 15))
        self.ttl_approval_hours = int(self.data.get("ttl_approval_hours", 2))
        self.permission_ttl_hours = int(self.data.get("permission_ttl_hours", 24))
        self.allowance_refill = int(self.data.get("allowance_refill_base_units", 300000000))
        self.allowance_max_refill = int(self.data.get("allowance_max_refill_base_units", 300000000))
        self.allowance_period_seconds = int(self.data.get("allowance_period_seconds", 86400))
        self.role_key = str(self.data.get("role_key") or ROLE_KEY_AGENT)
        self.revocation_scheduled_at = self.data.get("revocation_scheduled_at")
        self.recipient_labels = list(self.data.get("recipients") or ["B", "C"])

    def recipient(self, label: str) -> str:
        address = self.recipients.get(label) or ""
        if not address:
            raise ConfigurationError("recipient {} missing from the configuration (.env)".format(label))
        return address

    def allowed_recipients(self) -> frozenset:
        return frozenset(self.recipient(label) for label in self.recipient_labels if self.recipients.get(label))

    def as_policy_config(self, now: datetime, cumulative_spent: float = 0.0) -> PolicyConfig:
        """Configuration accepted by ``orvyren.policy.evaluate`` (rules R1-R8)."""
        return PolicyConfig(
            allowed_chain_ids=frozenset({self.chain_id}),
            allowed_assets=frozenset({self.asset}),
            allowed_recipients=self.allowed_recipients(),
            max_per_tx=self.max_per_tx,
            max_cumulative=self.max_cumulative_24h,
            permission_expires_at=now + timedelta_hours(self.permission_ttl_hours),
        )

    def to_policy_intent(self, intent: Dict[str, Any]) -> Intent:
        """Converts a v1 intent (amount as a string) into ``orvyren.policy.Intent``."""
        return Intent(
            intent_id=str(intent.get("intent_id")),
            action=str(intent.get("action")),
            chain_id=int(intent.get("chain_id")),
            asset=str(intent.get("asset")),
            amount=float(intent.get("amount")),
            recipient=str(intent.get("recipient")),
            created_at=parse_rfc3339(intent.get("created_at")),
            justification=str(intent.get("justification") or ""),
        )


def timedelta_hours(hours: int):
    from datetime import timedelta
    return timedelta(hours=int(hours))


def evaluate_policy(intent: Dict[str, Any], policy: PolicyReference, *,
                    now: Optional[datetime] = None, seen_intent_ids: Iterable[str] = (),
                    cumulative_spent: float = 0.0):
    """Deterministic verdict from the existing code (``orvyren.policy.evaluate``) on a v1 intent."""
    moment = now or utc_now_dt()
    decision = evaluate(
        policy.to_policy_intent(intent),
        policy.as_policy_config(moment, cumulative_spent),
        now=moment,
        seen_intent_ids=seen_intent_ids,
        cumulative_spent=cumulative_spent,
    )
    return decision


def decision_as_dict(decision, *, intent: Optional[Dict[str, Any]] = None,
                     policy: Optional[PolicyReference] = None,
                     now: Optional[datetime] = None,
                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Enriched verdict (additive fields B4 §f.2) — never a secret."""
    payload: Dict[str, Any] = {
        "decision_id": ulid(),
        "verdict": decision.verdict,
        "reasons": list(decision.reasons),
        "rules_evaluated": decision.rules_evaluated,
        "evaluator": "orvyren-policy v0.1 (deterministic, off-LLM)",
        "decided_at": (now or utc_now_dt()).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if intent is not None:
        payload["intent_id"] = intent.get("intent_id")
        payload["intent_hash"] = intent.get("idempotency_key")
    if policy is not None:
        payload["policy_version"] = policy.version
        payload["policy_chain_id"] = policy.chain_id
    if context is not None:
        payload["context_used"] = context
    return payload


# --- SHA-256 chained append-only journal (B6 §1.3) ---------------------------

GENESIS_HASH = "0" * 64
JOURNAL_MODE_LIVE = "LIVE"
JOURNAL_MODE_DRY_RUN = "DRY_RUN"


class Journal:
    """Append-only JSONL journal, chained per stream.

    ``record_hash = sha256(canonical_json(record without record_hash))`` and
    ``prev_hash = record_hash`` of the preceding record **of the same stream**
    (genesis ``0``×64). The format follows B6 §1.3; the ``DRY_RUN`` mode is a kit
    addition (a rehearsal must never pass for ``LIVE``).
    """

    def __init__(self, path: str, *, run_id: str, episode: str = "rseth",
                 mode: str = JOURNAL_MODE_DRY_RUN):
        self.path = path
        self.run_id = run_id
        self.episode = episode
        self.mode = mode

    def _records(self) -> List[Dict[str, Any]]:
        return [record for record in read_jsonl(self.path) if isinstance(record, dict)]

    def head_hash(self, stream: str = "exec") -> str:
        head = GENESIS_HASH
        for record in self._records():
            if record.get("stream") == stream:
                head = record.get("record_hash") or head
        return head

    def head(self) -> str:
        return self.head_hash("exec")

    def count(self, stream: Optional[str] = None) -> int:
        records = self._records()
        if stream is None:
            return len(records)
        return sum(1 for record in records if record.get("stream") == stream)

    def kinds(self, intent_id: Optional[str] = None) -> List[str]:
        found = []
        for record in self._records():
            if intent_id is not None:
                refs = record.get("refs") or {}
                payload = record.get("payload") or {}
                if refs.get("intent_id") != intent_id and payload.get("intent_id") != intent_id:
                    continue
            found.append(record.get("kind"))
        return found

    def append(self, kind: str, payload: Optional[Dict[str, Any]] = None,
               refs: Optional[Dict[str, Any]] = None, stream: str = "exec",
               mode: Optional[str] = None) -> Dict[str, Any]:
        payload = dict(payload or {})
        refs = dict(refs or {})
        seq = self.count() + 1
        record: Dict[str, Any] = {
            "v": 1,
            "stream": stream,
            "seq": seq,
            "run_id": self.run_id,
            "episode": self.episode,
            "mode": mode or self.mode,
            "ts_utc": utc_now(),
            "kind": kind,
            "payload": payload,
            "refs": refs,
            "prev_hash": self.head_hash(stream),
        }
        record["record_hash"] = sha256_hex(canonical_json(record).encode("utf-8"))
        append_jsonl(self.path, record)
        return record

    def append_run_marker(self, run: str, note: str = "", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {"run": run, "note": note}
        if extra:
            payload.update(extra)
        return self.append("RUN_START", payload=payload, refs={"run": run})

    def verify(self) -> Dict[str, Any]:
        """Recomputes the whole chain: ``{ok, records, errors, heads, counts}``."""
        records = self._records()
        errors: List[Dict[str, Any]] = []
        heads: Dict[str, str] = {}
        counts: Dict[str, int] = {}
        for index, record in enumerate(records, start=1):
            copy = dict(record)
            stored = copy.pop("record_hash", None)
            computed = sha256_hex(canonical_json(copy).encode("utf-8"))
            stream = record.get("stream")
            if stored != computed:
                errors.append({"index": index, "seq": record.get("seq"), "code": "RECORD_HASH_MISMATCH",
                               "stored": stored, "computed": computed})
            expected_prev = heads.get(stream, GENESIS_HASH)
            if record.get("prev_hash") != expected_prev:
                errors.append({"index": index, "seq": record.get("seq"), "code": "PREV_HASH_MISMATCH",
                               "stored_prev": record.get("prev_hash"), "expected_prev": expected_prev})
            heads[stream] = stored if stored is not None else computed
            counts[stream] = counts.get(stream, 0) + 1
        return {
            "ok": not errors,
            "records": len(records),
            "errors": errors,
            "heads": heads,
            "counts": counts,
        }


# --- idempotency registry ----------------------------------------------------


class Registry:
    """Persistent append-only registry of intents (idempotency_key + intent_id)."""

    def __init__(self, path: str):
        self.path = path

    def _data(self) -> Dict[str, Any]:
        data = load_json(self.path, default=None)
        if not isinstance(data, dict):
            return {"keys": {}, "intent_ids": [], "entries": []}
        data.setdefault("keys", {})
        data.setdefault("intent_ids", [])
        data.setdefault("entries", [])
        return data

    def has_key(self, key: str) -> bool:
        return str(key) in self._data()["keys"]

    def seen_intent_ids(self) -> Tuple[str, ...]:
        return tuple(self._data()["intent_ids"])

    def record(self, *, intent_id: str, idempotency_key: str, status: str, note: str = "") -> None:
        data = self._data()
        entry = {"intent_id": intent_id, "idempotency_key": idempotency_key,
                 "status": status, "note": note, "ts_utc": utc_now()}
        data["entries"].append(entry)
        data["keys"][idempotency_key] = entry
        if intent_id not in data["intent_ids"]:
            data["intent_ids"].append(intent_id)
        write_json(self.path, data)

    def as_dict(self) -> Dict[str, Any]:
        data = self._data()
        return {"keys": sorted(data["keys"]), "intent_ids": list(data["intent_ids"]),
                "entries": len(data["entries"])}


# --- signature log (counter, never a key) ------------------------------------


class SignatureLog:
    """Signature counter of the signing service (never a key, never a nonce)."""

    def __init__(self, path: str):
        self.path = path

    def count(self) -> int:
        return len(read_jsonl(self.path))

    def append(self, *, intent_id: str, mode: str, tx_hash: str, note: str = "") -> Dict[str, Any]:
        entry = {"ts_utc": utc_now(), "intent_id": intent_id, "mode": mode,
                 "tx_hash": tx_hash, "note": note, "key_material": "never recorded"}
        append_jsonl(self.path, entry)
        return entry


class PauseFlag:
    """K0 pause (off-chain kill switch): a file flag, never cleared by the agent."""

    def __init__(self, path: str, env: Optional[Dict[str, str]] = None):
        self.path = path
        self.env = env or {}

    def is_paused(self) -> bool:
        if str(self.env.get("ORVYREN_K0_PAUSED", "")).strip().lower() in ("1", "true", "yes", "on"):
            return True
        return os.path.isfile(self.path)

    def set(self, reason: str) -> None:
        write_json(self.path, {"paused": True, "reason": reason, "ts_utc": utc_now(),
                               "note": "cleared by a human only (B4 P11)"})

    def clear(self, reason: str = "") -> None:
        if os.path.isfile(self.path):
            os.remove(self.path)
        _ = reason


# --- output packets ----------------------------------------------------------


def ensure_session_dir(path: str, *, episode: str = "rseth", mode: str = JOURNAL_MODE_DRY_RUN,
                       policy: Optional[PolicyReference] = None) -> Dict[str, Any]:
    """Creates/retrieves the session directory and its ``session.json``."""
    os.makedirs(path, exist_ok=True)
    session_path = os.path.join(path, "session.json")
    session = load_json(session_path, default=None)
    if not isinstance(session, dict):
        session = {
            "schema": "orvyren-demo-session/v1",
            "run_id": ulid(),
            "episode": episode,
            "mode": mode,
            "created_at": utc_now(),
            "chain_id": CHAIN_ID_DEMO,
            "danger": "throwaway key only — no real money (FREEZE_V2 J2)",
        }
        write_json(session_path, session)
    if policy is not None:
        write_json(os.path.join(path, "policy.effective.json"), policy.data)
    return session


def load_policy_reference(policy_path: Optional[str], recipients: Dict[str, str]) -> PolicyReference:
    """Loads ``policy.demo.json`` (or the supplied file); refuses an unreadable file."""
    path = policy_path or os.path.join(HERE, "policy.demo.json")
    data = load_json(path)
    if not isinstance(data, dict):
        raise ConfigurationError("policy unreadable or missing: {}".format(path))
    return PolicyReference(data, recipients)


def abi_encode_call(selector_hex: str, head_words: Sequence[str], tail: str = "") -> str:
    """Concatenates a selector and already-encoded ABI words (builder utility)."""
    body = "".join(head_words)
    return selector_hex + body + tail
