#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — pure receipt verification for ERC-20 transfers.

Everything here is pure and offline: decode an ERC-20 Transfer log, convert
amounts to base units, and compare a transaction receipt against what the
policy actually allowed. No key is needed — the human executes the transfer,
this module only reads what the chain says afterwards.

verify_receipt() expects the receipt to carry a "chainId" field (JSON-RPC
receipts do not include one): the caller enriches the receipt with the chain id
it read from the node before calling. Expected shape:

    expected = {"token": "0x…", "from": "0x…", "to": "0x…", "amount_usdc": 100.0,
                "chain_id": 84532, "decimals": 6}   # chain_id / decimals optional
"""

from decimal import Decimal

from orvyren.policy import ALLOWED_CHAIN_ID

# keccak256("Transfer(address,address,uint256)")
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
DEFAULT_DECIMALS = 6  # USDC

# Stable, machine-readable mismatch codes.
NO_TRANSFER_LOG = "NO_TRANSFER_LOG"
TOKEN_CONTRACT_MISMATCH = "TOKEN_CONTRACT_MISMATCH"
SENDER_MISMATCH = "SENDER_MISMATCH"
RECIPIENT_MISMATCH = "RECIPIENT_MISMATCH"
AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
TRANSACTION_FAILED = "TRANSACTION_FAILED"
RECEIPT_STATUS_MISSING = "RECEIPT_STATUS_MISSING"
CHAIN_ID_MISSING = "CHAIN_ID_MISSING"
CHAIN_ID_MISMATCH = "CHAIN_ID_MISMATCH"
CHAIN_ID_INVALID = "CHAIN_ID_INVALID"


def value_to_base_units(amount, decimals=DEFAULT_DECIMALS):
    """Convert a human token amount to integer base units (USDC: 6 decimals).

    value_to_base_units(100, 6) == 100000000
    """
    try:
        scaled = Decimal(str(amount)).scaleb(int(decimals))
    except (ArithmeticError, ValueError, TypeError) as exc:
        raise ValueError("invalid amount: {!r}".format(amount)) from exc
    if not scaled.is_finite():
        # Decimal('Infinity') is "integral", so the check below would let it
        # through and int() would raise OverflowError instead of ValueError.
        raise ValueError("invalid amount: {!r}".format(amount))
    if scaled != scaled.to_integral_value():
        raise ValueError("amount {!r} has more than {} decimals".format(amount, decimals))
    return int(scaled)


def _address(value):
    """Normalised (lower-case) address, or None when the value is not an address."""
    if not isinstance(value, str):
        return None
    body = value[2:] if value.startswith(("0x", "0X")) else ""
    if len(body) != 40 or not all(c in "0123456789abcdefABCDEF" for c in body):
        return None
    return "0x" + body.lower()


def _topic_address(topic):
    """Extract the 20-byte address from a 32-byte indexed-argument topic."""
    if not isinstance(topic, str):
        raise ValueError("invalid address topic: {!r}".format(topic))
    body = topic[2:] if topic.startswith(("0x", "0X")) else topic
    if len(body) < 40 or not all(c in "0123456789abcdefABCDEF" for c in body):
        raise ValueError("invalid address topic: {!r}".format(topic))
    return "0x" + body[-40:].lower()


def is_transfer_log(log, token_address=None):
    """True for an ERC-20 Transfer log (exactly 3 topics), optionally from a given token."""
    if not isinstance(log, dict):
        return False
    topics = log.get("topics") or []
    if len(topics) != 3 or str(topics[0]).lower() != TRANSFER_TOPIC:
        return False
    if token_address is None:
        return True
    expected = _address(token_address)
    return expected is not None and _address(log.get("address")) == expected


def decode_transfer(log, decimals=DEFAULT_DECIMALS):
    """Decode an ERC-20 Transfer log into {token, from, to, value_base_units, value}."""
    if not isinstance(log, dict):
        raise ValueError("not a log object: {!r}".format(log))
    topics = log.get("topics") or []
    if len(topics) != 3:
        raise ValueError("not an ERC-20 Transfer log: expected 3 topics, got {}".format(len(topics)))
    if str(topics[0]).lower() != TRANSFER_TOPIC:
        raise ValueError("unexpected topic0: {!r}".format(topics[0]))
    data = log.get("data")
    if data is None:
        data = "0x"
    if not isinstance(data, str):
        raise ValueError("invalid log data: {!r}".format(data))
    body = data[2:] if data.startswith(("0x", "0X")) else data
    try:
        value_base_units = int(body, 16) if body else 0
    except ValueError as exc:
        raise ValueError("invalid transfer value: {!r}".format(data)) from exc
    return {
        "token": _address(log.get("address")),
        "from": _topic_address(topics[1]),
        "to": _topic_address(topics[2]),
        "value_base_units": value_base_units,
        "value": value_base_units / 10 ** int(decimals),
    }


def _status_mismatch(receipt):
    """None when the receipt status is a success, otherwise the mismatch code."""
    status = receipt.get("status")
    if status is None:
        return RECEIPT_STATUS_MISSING
    if isinstance(status, bool):
        return None if status else TRANSACTION_FAILED
    if isinstance(status, int):
        return None if status == 1 else TRANSACTION_FAILED
    if isinstance(status, str):
        text = status.strip()
        try:
            numeric = int(text, 16) if text.startswith(("0x", "0X")) else int(text, 10)
        except ValueError:
            return TRANSACTION_FAILED
        return None if numeric == 1 else TRANSACTION_FAILED
    return TRANSACTION_FAILED


def _parse_chain_id(value):
    if value is None or isinstance(value, bool):
        raise ValueError("invalid chain id: {!r}".format(value))
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        return int(text, 16) if text.startswith(("0x", "0X")) else int(text, 10)
    raise ValueError("invalid chain id: {!r}".format(value))


def verify_receipt(receipt, expected):
    """Compare a receipt with the transfer the policy allowed.

    expected = {"token", "from", "to", "amount_usdc"} (plus optional "chain_id",
    "decimals"). Checks: status == success, chain id, token contract, sender,
    recipient and amount. Returns {"ok": bool, "mismatches": [codes],
    "transfer": decoded best-match log or None, "expected": normalised request}.
    Pure function: no network, no key, deterministic.
    """
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be a dict")
    if not isinstance(expected, dict):
        raise ValueError("expected must be a dict")
    missing = [key for key in ("token", "from", "to", "amount_usdc")
               if expected.get(key) in (None, "")]
    if missing:
        raise ValueError("expected is missing: {}".format(", ".join(missing)))

    decimals = int(expected.get("decimals", DEFAULT_DECIMALS))
    # Same hex-tolerant parsing as the receipt side: an expected chain id given
    # as "0x14a34" must not fail on int(, 10).
    chain_id = _parse_chain_id(expected.get("chain_id", ALLOWED_CHAIN_ID))
    token = _address(expected["token"]) or str(expected["token"])
    sender = _address(expected["from"]) or str(expected["from"])
    recipient = _address(expected["to"]) or str(expected["to"])
    amount_base_units = value_to_base_units(expected["amount_usdc"], decimals)

    mismatches = []

    status_code = _status_mismatch(receipt)
    if status_code:
        mismatches.append(status_code)

    seen_chain = receipt.get("chainId", receipt.get("chain_id"))
    if seen_chain is None:
        mismatches.append(CHAIN_ID_MISSING)
    else:
        try:
            if _parse_chain_id(seen_chain) != chain_id:
                mismatches.append(CHAIN_ID_MISMATCH)
        except (TypeError, ValueError):
            mismatches.append(CHAIN_ID_INVALID)

    logs = receipt.get("logs") or []
    transfer_logs = [log for log in logs if isinstance(log, dict) and is_transfer_log(log)]
    token_logs = [log for log in transfer_logs if is_transfer_log(log, token)]

    best = None
    if not token_logs:
        mismatches.append(TOKEN_CONTRACT_MISMATCH if transfer_logs else NO_TRANSFER_LOG)
    else:
        decoded = []
        for log in token_logs:
            try:
                decoded.append(decode_transfer(log, decimals))
            except ValueError:
                continue
        if not decoded:
            mismatches.append(NO_TRANSFER_LOG)
        else:
            best = max(decoded, key=lambda transfer: (
                transfer["from"] == sender,
                transfer["to"] == recipient,
                transfer["value_base_units"] == amount_base_units,
            ))
            if best["from"] != sender:
                mismatches.append(SENDER_MISMATCH)
            if best["to"] != recipient:
                mismatches.append(RECIPIENT_MISMATCH)
            if best["value_base_units"] != amount_base_units:
                mismatches.append(AMOUNT_MISMATCH)

    return {
        "ok": not mismatches,
        "mismatches": mismatches,
        "transfer": best,
        "expected": {
            "token": token,
            "from": sender,
            "to": recipient,
            "amount_usdc": expected["amount_usdc"],
            "amount_base_units": amount_base_units,
            "chain_id": chain_id,
            "decimals": decimals,
        },
    }
