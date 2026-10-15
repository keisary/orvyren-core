#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B5 — brute force : identifier le sélecteur 0x4a0bfec1 (module Roles) et retrouver `repay` du Pool."""
import json
import sys
import urllib.request

sys.path.insert(0, "D:/orvyren_core/research/raw_b5")
from keccak_selectors import selector  # noqa: E402

RPC = "https://sepolia.base.org"
UA = "ORVYREN-B5/0.1 (read-only probe)"


def code_of(addr):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_getCode",
                       "params": [addr, "latest"]}).encode()
    req = urllib.request.Request(RPC, data=body, method="POST",
                                 headers={"content-type": "application/json", "User-Agent": UA})
    return json.loads(urllib.request.urlopen(req, timeout=40).read())["result"]


POOL_IMPL = "0xE9fb54369E85b9714F9d86366D918c5C7C87783A"
ROLES = "0xF2964CE6161ce0e75964Fe7927cE114cb0B283D5"
pool_code = code_of(POOL_IMPL)[2:]
roles_code = code_of(ROLES)[2:]

print("== repay : variantes recherchées dans le bytecode du Pool impl ==")
for sig in ("repay(address,uint256,address)", "repay(address,uint256,uint256,address)",
            "repayWithATokens(address,uint256,address)",
            "repayWithATokens(address,uint256,uint256,address)",
            "getReserveData(address)"):
    sel = selector(sig)[2:]
    print(f"   {sel}  {sig} : {'PRÉSENT' if sel in pool_code else 'absent'}")

print("== module Roles : sélecteurs clés ==")
for sig in ("execTransactionWithRole(address,uint256,bytes,uint8,bytes32,bool)",
            "execTransactionWithRoleReturnData(address,uint256,bytes,uint8,bytes32,bool)",
            "assignRoles(address,bytes32[],bool[])",
            "allowTarget(bytes32,address,uint8)",
            "setAllowance(bytes32,address,address,uint128,uint128,uint64,uint128,uint64)"):
    sel = selector(sig)[2:]
    print(f"   {sel}  {sig} : {'PRÉSENT' if sel in roles_code else 'absent'}")

print("== recherche du nom de l'erreur 0x4a0bfec1 ==")
names = [
    "NoMembership(address)", "NoMembership()", "NotAMember(address)", "NotMember(address)",
    "AddressNotMember(address)", "CallerNotMember(address)", "SenderNotAMember(address)",
    "SenderNotMember(address)", "MemberNotFound(address)", "MembershipNotFound(address)",
    "AccountNotAMember(address)", "InvalidMember(address)", "UnauthorizedMember(address)",
    "NotAuthorized(address)", "Unauthorized(address)", "AccessDenied(address)",
    "RoleNotAssigned(address)", "UnknownRole(address)", "InvalidRole(address)",
    "RolesModifier__NoMembership(address)", "RoleMembershipCheck(address)",
    "NotAModule(address)", "CallerNotAVerifiedModule(address)", "NotAuthorizedModule(address)",
    "InvalidPermissions(address)", "PolicyViolation(address)", "NotAllowed(address)",
    "CallerNotAllowed(address)", "ActionNotAllowed(address)", "PermissionDenied(address)",
]
for n in names:
    if selector(n) == "0x4a0bfec1":
        print("   TROUVÉ :", n)
print("   (fin de la liste testée :", len(names), "candidats)")
