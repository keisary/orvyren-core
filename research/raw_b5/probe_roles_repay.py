#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B5 — re-test module Roles + repay Aave + décodage de l'erreur custom 0x2c5211c6 (2026-10-15)."""
import json
import sys
import urllib.request

sys.path.insert(0, "D:/orvyren_core/research/raw_b5")
from keccak_selectors import selector  # noqa: E402

RPC = "https://sepolia.base.org"
UA = "ORVYREN-B5/0.1 (read-only probe)"


def call(to, data, frm=None):
    params = [{"to": to, "data": data}, "latest"]
    if frm:
        params[0]["from"] = frm
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": params}).encode()
    req = urllib.request.Request(RPC, data=body, method="POST",
                                 headers={"content-type": "application/json", "User-Agent": UA})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def pad(x):
    return format(x, "064x")


addr = lambda a: a.lower()[2:].rjust(64, "0")
FROM = "0x9999999999999999999999999999999999999999"
ROLES = "0xF2964CE6161ce0e75964Fe7927cE114cb0B283D5"
AAVE_POOL = "0x8bAB6d1b75f19e9eD9fCe8b9BD338844fF79aE27"
USDC_A = "0xba50Cd2A20f6DA35D788639E581bca8d0B5d4D5f"
USDC_C = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
AGENT_KEY = "4147454e" + "0" * 56  # bytes32 "AGENT" (64 hex, sans 0x)

# --- 1. Roles.execTransactionWithRole depuis une adresse non membre ---
inner = "a9059cbb" + addr("0x1111111111111111111111111111111111111111") + pad(1)
# calldata : to, value, data(offset), operation, roleKey, shouldRevert, [tail: len + inner]
tail_len = len(inner) // 2
data = ("0xc6fe8747" + addr(USDC_C) + pad(0) + pad(6 * 32) + pad(0) + AGENT_KEY + pad(1)
        + pad(tail_len) + inner)
print("1. execTransactionWithRole (0xc6fe8747) depuis adresse non membre :")
print(json.dumps(call(ROLES, data, FROM))[:600])

# --- 2. Roles : sélecteur inconnu (contrôle) ---
print("2. contrôle 0xdeadbeef sur le module Roles :")
print(json.dumps(call(ROLES, "0xdeadbeef" + pad(0), FROM))[:300])

# --- 3. Aave repay(address,uint256,address) = 0x5ceae9c4 (keccak) ---
d = "0x5ceae9c4" + addr(USDC_A) + pad(1) + addr(FROM)
print("3. repay(USDC_A,1,FROM) sur le Pool :")
print(json.dumps(call(AAVE_POOL, d, FROM))[:400])

# --- 4. Décodage de 0x2c5211c6 (erreur custom vue sur supply) ---
cands = [
    "SupplyCapExceeded()", "InvalidAmount()", "AmountNotZero()", "ZeroAmount()",
    "InsufficientBalance()", "ReserveInactive()", "ReserveFrozen()", "ReservePaused()",
    "BorrowingNotEnabled()", "NoDebtOfSelectedType()", "InvalidBurnAmount()",
    "MustBeVaultOrAToken()", "ERC20InsufficientBalance(address,uint256,uint256)",
    "ERC20InsufficientAllowance(address,uint256,uint256)", "CallerNotAToken()", "InvalidMintAmount()",
    "SupplyCapExceeded(address,uint256,uint256)", "AmountNotZero(address)", "ZeroAmount(address)",
]
print("4. recherche de l'erreur 0x2c5211c6 :")
for c in cands:
    s = selector(c)
    if s == "0x2c5211c6":
        print("   TROUVÉ :", c)
print("   (fin)")
