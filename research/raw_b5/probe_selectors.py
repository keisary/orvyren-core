#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B5 — vérification FONCTIONNELLE des sélecteurs candidats par eth_call (Base Sepolia, 2026-10-15).

Principe : un contrat sans fallback qui reçoit un sélecteur inconnu revert avec des données VIDES
(dispatch raté) ; un sélecteur CONNU exécute le corps de la fonction → revert NON vide (erreur du
domaine : 'STF' Uniswap, erreur custom du jeton, erreur Aave). On distingue donc existence vs absence.
"""
import json
import urllib.request

RPC = "https://sepolia.base.org"
UA = "ORVYREN-B5/0.1 (read-only probe)"


def call(to, data, frm=None):
    params = [{"to": to, "data": data}, "latest"]
    if frm:
        params[0]["from"] = frm
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                       "params": params}).encode()
    req = urllib.request.Request(RPC, data=body, method="POST",
                                 headers={"content-type": "application/json", "User-Agent": UA})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def pad(x):
    return format(x, "064x")


USDC = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
USDC_A = "0xba50Cd2A20f6DA35D788639E581bca8d0B5d4D5f".lower()
WETH = "0x4200000000000000000000000000000000000006"
ROUTER02 = "0x94cC0AaC535CCDB3C01d6787D6413C739ae12bc4"
AAVE_POOL = "0x8bAB6d1b75f19e9eD9fCe8b9BD338844fF79aE27"
FROM = "0x9999999999999999999999999999999999999999"

addr = lambda a: a.lower()[2:].rjust(64, "0")

print("== 1. SwapRouter02 — candidat 02 (7 champs, sans deadline) 0x04e45aaf ==")
data = ("0x04e45aaf" + addr(USDC) + addr(WETH) + pad(3000) + addr(FROM) + pad(50_000_000)
        + pad(0) + pad(0))
print(json.dumps(call(ROUTER02, data, FROM), indent=1)[:600])

print("== 2. SwapRouter02 — candidat v1 (8 champs, avec deadline) 0x414bf389 ==")
data = ("0x414bf389" + addr(USDC) + addr(WETH) + pad(3000) + addr(FROM) + pad(50_000_000)
        + pad(0) + pad(2 ** 32) + pad(0))
print(json.dumps(call(ROUTER02, data, FROM), indent=1)[:600])

print("== 3. Contrôle : sélecteur inconnu 0xdeadbeef sur SwapRouter02 ==")
print(json.dumps(call(ROUTER02, "0xdeadbeef" + pad(0)), indent=1)[:400])

print("== 4. Aave Pool — repay(address,uint256,address) : candidats 0x573ade81 / 0x3e62cd3f / 0x5ceae9c4 ==")
for sel in ("0x573ade81", "0x3e62cd3f", "0x5ceae9c4"):
    d = sel + addr(USDC_A) + pad(1) + addr(FROM)
    print(sel, "->", json.dumps(call(AAVE_POOL, d, FROM))[:400])

print("== 5. Contrôle : sélecteur inconnu sur Aave Pool ==")
print(json.dumps(call(AAVE_POOL, "0xdeadbeef" + pad(0)), indent=1)[:400])
