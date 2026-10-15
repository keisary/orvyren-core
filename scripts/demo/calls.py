#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — kit de démo testnet : construction/décodage des calldatas (stdlib).

Toutes les signatures sont celles **vérifiées le 2026-10-15** sur Base Sepolia
(``research/raw_b5/SELECTEURS_VERIFIES.md``) ; les autres sont calculées par le
Keccak-256 local du kit et doivent être re-vérifiées dans le bytecode déployé
avant la démo (protocole B5 §e.7).

Objets construits ici :

* ``transfer(address,uint256)`` du jeton (intent ALLOW) ;
* ``execTransactionWithRole(address,uint256,bytes,uint8,bytes32,bool)`` du module
  Roles — l'enveloppe par laquelle l'agent exécute **et** ses tentatives forcées
  (run C : les mêmes builders, avec des paramètres interdits) ;
* ``assignRoles(address,bytes32[],bool[])`` (kill switch K1 — exécuté par la Safe) ;
* ``allowTarget(bytes32,address,uint8)`` (tentative d'auto-élargissement, run C3) ;
* ``enableModule(address)`` du Safe (tentative d'admin, run C3) ;
* lectures ``balanceOf`` / ``allowance``.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Sequence

try:  # paquet
    from . import common
except ImportError:  # exécution directe
    _sys_dir = os.path.dirname(os.path.abspath(__file__))
    if _sys_dir not in sys.path:
        sys.path.insert(0, _sys_dir)
    import common  # type: ignore  # noqa: E402

OPERATION_CALL = 0
OPERATION_DELEGATECALL = 1

#: Énumération Zodiac ``Clearance`` (Roles v2) : 0 = None, 1 = Target, 2 = Function.
CLEARANCE_NONE = 0
CLEARANCE_TARGET = 1
CLEARANCE_FUNCTION = 2

CLEARANCE_NAMES = {0: "None", 1: "Target", 2: "Function"}


class CalldataError(Exception):
    """Calldata refusé (adresse, montant ou paramètre invalide)."""


# --- lectures ----------------------------------------------------------------


def balance_of_data(holder: str) -> str:
    return common.SELECTOR_BALANCE_OF + common.enc_address(holder)


def allowance_data(owner: str, spender: str) -> str:
    return common.SELECTOR_ALLOWANCE + common.enc_address(owner) + common.enc_address(spender)


def decode_uint_result(payload: str) -> int:
    return common.decode_word_uint(payload, 0)


# --- transfert ERC-20 --------------------------------------------------------


def erc20_transfer_data(recipient: str, amount_base_units: int) -> str:
    """``transfer(address,uint256)`` — sélecteur vérifié ``0xa9059cbb``."""
    if isinstance(amount_base_units, bool) or not isinstance(amount_base_units, int):
        raise CalldataError("amount_base_units doit être un entier")
    if amount_base_units < 0 or amount_base_units >= 2 ** 256:
        raise CalldataError("amount_base_units hors 256 bits")
    return common.SELECTOR_TRANSFER + common.enc_address(recipient) + common.enc_uint(amount_base_units)


def decode_erc20_transfer(data: str) -> Dict[str, Any]:
    """Décode ``transfer`` (round-trip de contrôle, utilisé par les tests)."""
    body = data[2:] if data.startswith("0x") else data
    if not body.startswith(common.SELECTOR_TRANSFER[2:]):
        raise CalldataError("sélecteur ≠ transfer(address,uint256)")
    args = "0x" + body[8:]              # les mots ABI commencent APRÈS le sélecteur
    return {
        "selector": common.SELECTOR_TRANSFER,
        "to": common.decode_word_address(args, 0),
        "value": common.decode_word_uint(args, 1),
    }


# --- module Roles : execTransactionWithRole ---------------------------------


def exec_with_role_data(*, target: str, value: int, inner_data: str, operation: int,
                        role_key: str, should_revert: bool = True) -> str:
    """``execTransactionWithRole(address,uint256,bytes,uint8,bytes32,bool)`` (``0xc6fe8747``).

    ``inner_data`` est le calldata exécuté par la Safe (ex. ``transfer``).
    """
    if operation not in (OPERATION_CALL, OPERATION_DELEGATECALL):
        raise CalldataError("operation doit être 0 (CALL) ou 1 (DELEGATECALL)")
    if not isinstance(inner_data, str) or not inner_data.startswith("0x"):
        raise CalldataError("inner_data doit être un calldata 0x…")
    head = [
        common.enc_address(target),
        common.enc_uint(value),
        common.enc_uint(6 * 32),          # offset de `bytes data` (6 mots d'en-tête)
        common.enc_uint(operation),
        common.enc_bytes32(role_key),
        common.enc_bool(should_revert),
    ]
    tail = common.enc_bytes_dynamic(inner_data)
    return common.abi_encode_call(common.SELECTOR_EXEC_TX_WITH_ROLE, head, tail)


def decode_exec_with_role(data: str) -> Dict[str, Any]:
    """Décode un ``execTransactionWithRole`` (contrôle round-trip)."""
    body = data[2:] if data.startswith("0x") else data
    if not body.startswith(common.SELECTOR_EXEC_TX_WITH_ROLE[2:]):
        raise CalldataError("sélecteur ≠ execTransactionWithRole")
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


# --- module Roles : administration (jamais accordée à l'agent) ---------------


def assign_roles_data(member: str, role_keys: Sequence[str], enabled: Sequence[bool]) -> str:
    """``assignRoles(address,bytes32[],bool[])`` (``0x957ed2b3``) — exécuté par la Safe (K1)."""
    keys = [common.enc_bytes32(key) for key in role_keys]
    flags = [common.enc_bool(bool(flag)) for flag in enabled]
    if len(keys) != len(flags) or not keys:
        raise CalldataError("role_keys et enabled doivent être de même taille non nulle")
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
    """Décode un ``assignRoles`` (vérifie l'aller-retour du kill switch)."""
    body = data[2:] if data.startswith("0x") else data
    if not body.startswith(common.SELECTOR_ASSIGN_ROLES[2:]):
        raise CalldataError("sélecteur ≠ assignRoles")
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
    """``allowTarget(bytes32,address,uint8)`` (``0x7b0da5b2``) — tentative d'admin (run C3)."""
    if clearance not in (CLEARANCE_NONE, CLEARANCE_TARGET, CLEARANCE_FUNCTION):
        raise CalldataError("clearance hors énumération Zodiac")
    head = [common.enc_bytes32(role_key), common.enc_address(target), common.enc_uint(clearance)]
    return common.abi_encode_call(common.SELECTOR_ALLOW_TARGET, head)


# --- Safe : administre le module ---------------------------------------------


def safe_enable_module_selector() -> str:
    """Sélecteur ``enableModule(address)`` (calculé localement, re-vérifiable)."""
    return common.selector("enableModule(address)")


def safe_enable_module_data(module: str) -> str:
    return safe_enable_module_selector() + common.enc_address(module)


def safe_disable_module_data(previous_module: str, module: str) -> str:
    """``disableModule(address,address)`` — variante K2 (exécutée par la Safe)."""
    return common.selector("disableModule(address,address)") + common.enc_address(previous_module) + common.enc_address(module)


def safe_owner_selector() -> str:
    return common.selector("getOwners()")


# --- assemblage de la transaction d'exécution --------------------------------


def demo_exec_transaction(*, module: str, agent: str, chain_id: int, nonce: int, gas: int,
                          max_fee_per_gas: int, max_priority_fee_per_gas: int,
                          inner_data: str, asset: str,
                          operation: int = OPERATION_CALL,
                          role_key: str = common.ROLE_KEY_AGENT) -> Dict[str, Any]:
    """Transaction EIP-1559 **non signée** passant par le module Roles (l'agent paie le gaz)."""
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
