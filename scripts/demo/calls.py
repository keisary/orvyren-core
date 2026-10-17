#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — testnet demo kit: calldata building/decoding (stdlib).

All signatures are those **verified on 2026-10-15** on Base Sepolia
(``research/raw_b5/SELECTEURS_VERIFIES.md``); the others are computed with the
kit's local Keccak-256 and must be re-verified in the deployed bytecode
before the demo (protocol B5 §e.7).

Objects built here:

* token ``transfer(address,uint256)`` (ALLOW intent);
* Roles module ``execTransactionWithRole(address,uint256,bytes,uint8,bytes32,bool)``
  — the envelope through which the agent executes **and** makes its forced attempts
  (run C: the same builders, with forbidden parameters);
* ``assignRoles(address,bytes32[],bool[])`` (K1 kill switch — executed by the Safe);
* ``allowTarget(bytes32,address,uint8)`` (self-widening attempt, run C3);
* Safe ``enableModule(address)`` (admin attempt, run C3);
* ``balanceOf`` / ``allowance`` reads.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Sequence

try:  # package
    from . import common
except ImportError:  # direct execution
    _sys_dir = os.path.dirname(os.path.abspath(__file__))
    if _sys_dir not in sys.path:
        sys.path.insert(0, _sys_dir)
    import common  # type: ignore  # noqa: E402

OPERATION_CALL = 0
OPERATION_DELEGATECALL = 1

#: Zodiac ``Clearance`` enum (Roles v2): 0 = None, 1 = Target, 2 = Function.
CLEARANCE_NONE = 0
CLEARANCE_TARGET = 1
CLEARANCE_FUNCTION = 2

CLEARANCE_NAMES = {0: "None", 1: "Target", 2: "Function"}


class CalldataError(Exception):
    """Calldata refused (invalid address, amount or parameter)."""


# --- reads -------------------------------------------------------------------


def balance_of_data(holder: str) -> str:
    return common.SELECTOR_BALANCE_OF + common.enc_address(holder)


def allowance_data(owner: str, spender: str) -> str:
    return common.SELECTOR_ALLOWANCE + common.enc_address(owner) + common.enc_address(spender)


def decode_uint_result(payload: str) -> int:
    return common.decode_word_uint(payload, 0)


# --- ERC-20 transfer ---------------------------------------------------------


def erc20_transfer_data(recipient: str, amount_base_units: int) -> str:
    """``transfer(address,uint256)`` — verified selector ``0xa9059cbb``."""
    if isinstance(amount_base_units, bool) or not isinstance(amount_base_units, int):
        raise CalldataError("amount_base_units must be an integer")
    if amount_base_units < 0 or amount_base_units >= 2 ** 256:
        raise CalldataError("amount_base_units outside 256 bits")
    return common.SELECTOR_TRANSFER + common.enc_address(recipient) + common.enc_uint(amount_base_units)


def decode_erc20_transfer(data: str) -> Dict[str, Any]:
    """Decodes ``transfer`` (control round-trip, used by the tests)."""
    body = data[2:] if data.startswith("0x") else data
    if not body.startswith(common.SELECTOR_TRANSFER[2:]):
        raise CalldataError("selector ≠ transfer(address,uint256)")
    args = "0x" + body[8:]              # the ABI words start AFTER the selector
    return {
        "selector": common.SELECTOR_TRANSFER,
        "to": common.decode_word_address(args, 0),
        "value": common.decode_word_uint(args, 1),
    }


# --- Roles module: execTransactionWithRole ----------------------------------


def exec_with_role_data(*, target: str, value: int, inner_data: str, operation: int,
                        role_key: str, should_revert: bool = True) -> str:
    """``execTransactionWithRole(address,uint256,bytes,uint8,bytes32,bool)`` (``0xc6fe8747``).

    ``inner_data`` is the calldata executed by the Safe (e.g. ``transfer``).
    """
    if operation not in (OPERATION_CALL, OPERATION_DELEGATECALL):
        raise CalldataError("operation must be 0 (CALL) or 1 (DELEGATECALL)")
    if not isinstance(inner_data, str) or not inner_data.startswith("0x"):
        raise CalldataError("inner_data must be 0x… calldata")
    head = [
        common.enc_address(target),
        common.enc_uint(value),
        common.enc_uint(6 * 32),          # `bytes data` offset (6 header words)
        common.enc_uint(operation),
        common.enc_bytes32(role_key),
        common.enc_bool(should_revert),
    ]
    tail = common.enc_bytes_dynamic(inner_data)
    return common.abi_encode_call(common.SELECTOR_EXEC_TX_WITH_ROLE, head, tail)


def decode_exec_with_role(data: str) -> Dict[str, Any]:
    """Decodes an ``execTransactionWithRole`` (round-trip check)."""
    body = data[2:] if data.startswith("0x") else data
    if not body.startswith(common.SELECTOR_EXEC_TX_WITH_ROLE[2:]):
        raise CalldataError("selector ≠ execTransactionWithRole")
    args_hex = body[8:]
    payload = "0x" + args_hex
    offset_words = common.decode_word_uint(payload, 2) // 32
    length = common.decode_word_uint(payload, offset_words)
    start = (offset_words + 1) * 64
    inner = "0x" + args_hex[start:start + length * 2]
    return {
        "selector": common.SELECTOR_EXEC_TX_WITH_ROLE,
        "target": common.decode_word_address(payload, 0),
        "value": common.decode_word_uint(payload, 1),
        "operation": common.decode_word_uint(payload, 3),
        "role_key": common.decode_word_bytes32(payload, 4),
        "should_revert": common.decode_word_bool(payload, 5),
        "inner_data": inner,
    }


# --- Roles module: administration (never granted to the agent) ---------------


def assign_roles_data(member: str, role_keys: Sequence[str], enabled: Sequence[bool]) -> str:
    """``assignRoles(address,bytes32[],bool[])`` (``0x957ed2b3``) — executed by the Safe (K1)."""
    keys = [common.enc_bytes32(key) for key in role_keys]
    flags = [common.enc_bool(bool(flag)) for flag in enabled]
    if len(keys) != len(flags) or not keys:
        raise CalldataError("role_keys and enabled must have the same non-zero length")
    head_words = 3
    keys_offset = head_words * 32
    flags_offset = keys_offset + (1 + len(keys)) * 32
    head = [
        common.enc_address(member),
        common.enc_uint(keys_offset),
        common.enc_uint(flags_offset),
    ]
    keys_tail = common.enc_uint(len(keys)) + "".join(keys)
    flags_tail = common.enc_uint(len(flags)) + "".join(flags)
    return common.abi_encode_call(common.SELECTOR_ASSIGN_ROLES, head, keys_tail + flags_tail)


def decode_assign_roles(data: str) -> Dict[str, Any]:
    """Decodes an ``assignRoles`` (checks the kill-switch round-trip)."""
    body = data[2:] if data.startswith("0x") else data
    if not body.startswith(common.SELECTOR_ASSIGN_ROLES[2:]):
        raise CalldataError("selector ≠ assignRoles")
    payload = "0x" + body[8:]
    member = common.decode_word_address(payload, 0)
    keys_offset = common.decode_word_uint(payload, 1) // 32
    flags_offset = common.decode_word_uint(payload, 2) // 32
    keys_len = common.decode_word_uint(payload, keys_offset)
    keys = [common.decode_word_bytes32(payload, keys_offset + 1 + index) for index in range(keys_len)]
    flags_len = common.decode_word_uint(payload, flags_offset)
    flags = [common.decode_word_bool(payload, flags_offset + 1 + index) for index in range(flags_len)]
    return {"member": member, "role_keys": keys, "enabled": flags}


def allow_target_data(role_key: str, target: str, clearance: int) -> str:
    """``allowTarget(bytes32,address,uint8)`` (``0x7b0da5b2``) — admin attempt (run C3)."""
    if clearance not in (CLEARANCE_NONE, CLEARANCE_TARGET, CLEARANCE_FUNCTION):
        raise CalldataError("clearance outside the Zodiac enum")
    head = [common.enc_bytes32(role_key), common.enc_address(target), common.enc_uint(clearance)]
    return common.abi_encode_call(common.SELECTOR_ALLOW_TARGET, head)


# --- Safe: administers the module --------------------------------------------


def safe_enable_module_selector() -> str:
    """``enableModule(address)`` selector (computed locally, re-verifiable)."""
    return common.selector("enableModule(address)")


def safe_enable_module_data(module: str) -> str:
    return safe_enable_module_selector() + common.enc_address(module)


def safe_disable_module_data(previous_module: str, module: str) -> str:
    """``disableModule(address,address)`` — K2 variant (executed by the Safe)."""
    return common.selector("disableModule(address,address)") + common.enc_address(previous_module) + common.enc_address(module)


def safe_owner_selector() -> str:
    return common.selector("getOwners()")


# --- execution transaction assembly ------------------------------------------


def demo_exec_transaction(*, module: str, agent: str, chain_id: int, nonce: int, gas: int,
                          max_fee_per_gas: int, max_priority_fee_per_gas: int,
                          inner_data: str, asset: str,
                          operation: int = OPERATION_CALL,
                          role_key: str = common.ROLE_KEY_AGENT) -> Dict[str, Any]:
    """**Unsigned** EIP-1559 transaction going through the Roles module (the agent pays the gas)."""
    return {
        "chainId": int(chain_id),
        "nonce": int(nonce),
        "to": common.normalize_address(module, "module"),
        "value": 0,
        "data": exec_with_role_data(target=asset, value=0, inner_data=inner_data,
                                    operation=operation, role_key=role_key, should_revert=True),
        "gas": int(gas),
        "maxFeePerGas": int(max_fee_per_gas),
        "maxPriorityFeePerGas": int(max_priority_fee_per_gas),
        "type": 2,
        "from": common.normalize_address(agent, "agent"),
    }
