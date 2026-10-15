#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B5 — vérification fonctionnelle finale : topics, module Roles, vues Aave (Base Sepolia, 2026-10-15)."""
import json
import sys
import urllib.request

sys.path.insert(0, "D:/orvyren_core/research/raw_b5")
from keccak_selectors import keccak256, selector  # noqa: E402

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
USDC_A = "0xba50Cd2A20f6DA35D788639E581bca8d0B5d4D5f"
AAVE_POOL = "0x8bAB6d1b75f19e9eD9fCe8b9BD338844fF79aE27"
AGENT_KEY = "0x4147454e54000000000000000000000000000000000000000000000000000000"

# 1. topic0 Transfer complet
topic = "0x" + keccak256(b"Transfer(address,address,uint256)").hex()
print("topic0 Transfer calculé :", topic)
print("égal au topic attendu (W2C/verify.py) :",
      topic == "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef")

# 2. Roles.execTransactionWithRole depuis une adresse non membre (dispatch ?)
data = ("0xc6fe8747" + addr("0x036CbD53842c5426634e7929541eC2318f3dCF7e") + pad(0)
        + pad(4 + 32 + 32)  # offset des bytes data
        + pad(0)            # operation CALL
        + AGENT_KEY         # roleKey
        + pad(1)            # shouldRevert = true
        + pad(68)           # longueur des bytes
        + "a9059cbb" + addr("0x1111111111111111111111111111111111111111") + pad(1))
print("execTransactionWithRole (0xc6fe8747) depuis non-membre :")
print(json.dumps(call(ROLES, data, FROM))[:500])

# 3. assignRoles depuis une adresse quelconque (onlyOwner attendu)
data = "0x957ed2b3" + addr(FROM) + pad(0x60) + pad(0x20) + pad(1) + AGENT_KEY + pad(1)
print("assignRoles (0x957ed2b3) depuis une adresse quelconque :")
print(json.dumps(call(ROLES, data, FROM))[:500])

# 4. Aave — vue getUserAccountData (dispatch de vue)
print("Aave getUserAccountData(address) (0xbf92857c) :")
print(json.dumps(call(AAVE_POOL, "0xbf92857c" + addr(FROM), FROM))[:400])

# 5. Aave — supply depuis une adresse sans fonds (comportement)
data = "0x617ba037" + addr(USDC_A) + pad(1) + addr(FROM) + pad(0)
print("Aave supply(USDC_A,1,FROM,0) depuis FROM sans fonds :")
print(json.dumps(call(AAVE_POOL, data, FROM))[:400])
