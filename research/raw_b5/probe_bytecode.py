#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B5 — vérification par BYTECODE : les sélecteurs apparaissent-ils dans le dispatcher ?
Base Sepolia, 2026-10-15. Pool impl Aave = 0xE9fb54369E85b9714F9d86366D918c5C7C87783A (address-book)."""
import json
import sys
import urllib.request

sys.path.insert(0, "D:/orvyren_core/research/raw_b5")
from keccak_selectors import selector  # noqa: E402

RPC = "https://sepolia.base.org"
UA = "ORVYREN-B5/0.1 (read-only probe)"


def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(RPC, data=body, method="POST",
                                 headers={"content-type": "application/json", "User-Agent": UA})
    return json.loads(urllib.request.urlopen(req, timeout=40).read())


POOL_IMPL = "0xE9fb54369E85b9714F9d86366D918c5C7C87783A"
code = rpc("eth_getCode", [POOL_IMPL, "latest"]).get("result") or "0x"
print("code Pool impl :", len(code[2:]) // 2, "octets")

tests = {
    "supply(address,uint256,address,uint16)": selector("supply(address,uint256,address,uint16)"),
    "withdraw(address,uint256,address)": selector("withdraw(address,uint256,address)"),
    "repay(address,uint256,address)": selector("repay(address,uint256,address)"),
    "borrow(address,uint256,uint256,uint16,address)": selector("borrow(address,uint256,uint256,uint16,address)"),
    "getReservesList()": selector("getReservesList()"),
    "controle:0xdeadbeef": "0xdeadbeef",
    "controle:fourbite": "0x0d1e2f3a",
}
for label, sel in tests.items():
    present = sel[2:] in code[2:]
    print(f"  {sel}  présent dans le bytecode : {present}   ({label})")

# Identification du revert du module Roles (0x4a0bfec1)
print()
for name in ("NoMembership(address)", "NoMembership()", "ModuleTransactionFailed()",
             "InvalidRoleKey(bytes32)", "NotAuthorized()", "Unauthorized()",
             "OwnableUnauthorizedAccount(address)", "NoPermissions()"):
    print("  ", selector(name), name)
