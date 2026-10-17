#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — minimal read-only JSON-RPC client (Python stdlib only).

Only read-only capabilities are exposed: chain id, block number, transaction
receipt and ERC-20 balanceOf. There is deliberately no signing or broadcast
method in this module — the agent never holds a key.

Error handling is explicit: every failure raises ChainError (or RpcError for a
JSON-RPC level error) with a readable message. RPC URLs may embed an API key,
so messages only ever show the masked form of the URL.
"""

import json
import os
import urllib.error
import urllib.request

from orvyren.execution.guard import DEFAULT_RPC_URL, DEFAULT_TIMEOUT_SECONDS, mask_rpc_url

USER_AGENT = "ORVYREN-Core/0.1 (read-only JSON-RPC client; Python stdlib)"
ERC20_TRANSFER_SELECTOR = "0xa9059cbb"
ERC20_BALANCE_OF_SELECTOR = "0x70a08231"
_HEX_CHARS = set("0123456789abcdefABCDEF")


class ChainError(Exception):
    """Any failure while talking to the JSON-RPC endpoint (network, HTTP, shape)."""


class RpcError(ChainError):
    """The node answered with a JSON-RPC error object."""

    def __init__(self, method, code, message, data=None):
        self.method = method
        self.code = code
        self.message = message
        self.data = data
        super().__init__("{} failed: code={} message={}".format(method, code, message))


def default_rpc_url():
    """Base Sepolia endpoint from the environment, or the public default."""
    return str(os.environ.get("ORVYREN_RPC_URL_BASE_SEPOLIA") or DEFAULT_RPC_URL).strip()


def rpc(url, method, params=None, timeout=DEFAULT_TIMEOUT_SECONDS):
    """Single JSON-RPC 2.0 call. Returns the `result` field, or raises ChainError."""
    if not url:
        raise ChainError("no RPC URL configured")
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": list(params or []),
    }).encode("utf-8")
    request = urllib.request.Request(
        url, data=payload, method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    safe_url = mask_rpc_url(url)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise ChainError("HTTP {} from {} while calling {}".format(exc.code, safe_url, method)) from exc
    except TimeoutError as exc:
        raise ChainError("timeout after {}s calling {} at {}".format(timeout, method, safe_url)) from exc
    except urllib.error.URLError as exc:
        raise ChainError("cannot reach {} while calling {}: {}".format(safe_url, method, exc.reason)) from exc
    except OSError as exc:
        raise ChainError("network error calling {} at {}: {}".format(method, safe_url, exc)) from exc

    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ChainError("invalid JSON-RPC response from {} for {}".format(safe_url, method)) from exc
    if not isinstance(body, dict):
        raise ChainError("malformed JSON-RPC response from {} for {}".format(safe_url, method))
    if body.get("error") is not None:
        raw_error = body["error"]
        # A conforming node sends an error OBJECT; proxies and gateways have
        # been seen sending strings. Never AttributeError out of this function:
        # normalise whatever arrived and raise the typed RpcError.
        error = raw_error if isinstance(raw_error, dict) else {"message": str(raw_error)}
        raise RpcError(method, error.get("code"), error.get("message"), error.get("data"))
    if "result" not in body:
        raise ChainError("JSON-RPC response from {} has no result for {}".format(safe_url, method))
    return body["result"]


def _hex_to_int(value, context):
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if not isinstance(value, str) or not value.startswith("0x"):
        raise ChainError("unexpected {} value: {!r}".format(context, value))
    try:
        return int(value, 16)
    except ValueError as exc:
        raise ChainError("invalid hex {} value: {!r}".format(context, value)) from exc


def chain_id(url=None, timeout=DEFAULT_TIMEOUT_SECONDS):
    """EIP-155 chain id (Base Sepolia = 84532)."""
    return _hex_to_int(rpc(url or default_rpc_url(), "eth_chainId", [], timeout), "eth_chainId")


def block_number(url=None, timeout=DEFAULT_TIMEOUT_SECONDS):
    """Latest block number."""
    return _hex_to_int(rpc(url or default_rpc_url(), "eth_blockNumber", [], timeout), "eth_blockNumber")


def normalize_address(address, context="address"):
    """Validate a 0x-prefixed 20-byte address and return it lower-cased (no repair)."""
    if not isinstance(address, str):
        raise ChainError("invalid {}: {!r}".format(context, address))
    text = address.strip()
    body = text[2:] if text.startswith(("0x", "0X")) else ""
    if len(body) != 40 or not all(c in _HEX_CHARS for c in body):
        raise ChainError("invalid {}: {!r} (expected 0x + 40 hex digits)".format(context, address))
    return "0x" + body.lower()


def normalize_tx_hash(tx_hash):
    """Validate a 0x-prefixed 32-byte transaction hash; casing is preserved, nothing is repaired."""
    if not isinstance(tx_hash, str):
        raise ChainError("invalid transaction hash: {!r}".format(tx_hash))
    text = tx_hash.strip()
    body = text[2:] if text.startswith(("0x", "0X")) else ""
    if len(body) != 64 or not all(c in _HEX_CHARS for c in body):
        raise ChainError("invalid transaction hash: {!r} (expected 0x + 64 hex digits)".format(tx_hash))
    return "0x" + body


def _pad32(hex_body):
    if len(hex_body) > 64:
        raise ChainError("cannot pad {} hex digits into 32 bytes".format(len(hex_body)))
    return hex_body.rjust(64, "0")


def erc20_transfer_calldata(recipient, amount_base_units):
    """ERC-20 transfer(address,uint256): selector + 32-byte recipient + 32-byte amount."""
    if isinstance(amount_base_units, bool) or not isinstance(amount_base_units, int):
        raise ChainError("amount_base_units must be an integer, got {!r}".format(amount_base_units))
    if amount_base_units < 0:
        raise ChainError("amount_base_units must be >= 0, got {}".format(amount_base_units))
    if amount_base_units >= 2 ** 256:
        raise ChainError("amount_base_units does not fit in 32 bytes")
    target = normalize_address(recipient, "recipient")
    return ERC20_TRANSFER_SELECTOR + _pad32(target[2:]) + _pad32(format(amount_base_units, "x"))


def erc20_balance_of_data(holder):
    """ERC-20 balanceOf(address) eth_call data: selector 0x70a08231 + 32-byte padded holder."""
    target = normalize_address(holder, "holder")
    return ERC20_BALANCE_OF_SELECTOR + _pad32(target[2:])


def get_transaction_receipt(tx_hash, url=None, timeout=DEFAULT_TIMEOUT_SECONDS):
    """Read-only receipt fetch; returns the receipt dict, or None if the node does not know it."""
    value = normalize_tx_hash(tx_hash)
    return rpc(url or default_rpc_url(), "eth_getTransactionReceipt", [value], timeout)


def erc20_balance_of(token, holder, url=None, timeout=DEFAULT_TIMEOUT_SECONDS):
    """Read-only ERC-20 balanceOf through eth_call; returns the balance in base units."""
    contract = normalize_address(token, "token")
    data = erc20_balance_of_data(holder)
    result = rpc(url or default_rpc_url(), "eth_call",
                 [{"to": contract, "data": data}, "latest"], timeout)
    return _hex_to_int(result, "eth_call balanceOf")
