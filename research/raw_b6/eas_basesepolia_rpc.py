#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B6 — sondage RPC (lecture seule) : EAS et registre de schémas sur Base Sepolia (84532).

Mesure (2026-10-15) :
  - eth_chainId sur https://sepolia.base.org ;
  - eth_getCode pour EAS 0x4200000000000000000000000000000000000021 et
    SchemaRegistry 0x4200000000000000000000000000000000000020 (predeploys OP-Stack) ;
  - eth_gasPrice (pour borner le coût réel d'une attestation en ETH de test) ;
  - taille des codes si présents.

Écrit raw_b6/eas_basesepolia_rpc.json. Aucun envoi de transaction.
"""
import hashlib
import json
import os
import time
import urllib.request

REPO = r"D:/orvyren_core"
OUT = os.path.join(REPO, "research", "raw_b6", "eas_basesepolia_rpc.json")
RPC = "https://sepolia.base.org"
EAS = "0x4200000000000000000000000000000000000021"
SCHEMA_REGISTRY = "0x4200000000000000000000000000000000000020"


def rpc_call(method, params, endpoints=None):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    last = None
    for ep in (endpoints or [RPC, "https://base-sepolia-rpc.publicnode.com",
                             "https://base-sepolia.gateway.tenderly.co"]):
        try:
            req = urllib.request.Request(ep, data=body, headers={
                "Content-Type": "application/json",
                "User-Agent": "orvyren-b6-research/1.0",
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode())
            if "error" in payload:
                last = {"endpoint": ep, "error": payload["error"]}
                continue
            return {"endpoint": ep, "result": payload.get("result")}
        except Exception as exc:  # noqa: BLE001 — repli d'endpoint volontaire
            last = {"endpoint": ep, "exception": "%s: %s" % (type(exc).__name__, exc)}
    return last


def main():
    report = {"rpc": RPC, "measured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    report["chainId"] = rpc_call("eth_chainId", [])
    report["blockNumber"] = rpc_call("eth_blockNumber", [])
    report["gasPrice"] = rpc_call("eth_gasPrice", [])
    for name, addr in (("EAS", EAS), ("SchemaRegistry", SCHEMA_REGISTRY)):
        code = rpc_call("eth_getCode", [addr, "latest"])
        entry = {"address": addr, "getCode": code}
        if isinstance(code.get("result"), str) and code["result"] not in ("0x", "0x0", None):
            raw = bytes.fromhex(code["result"][2:])
            entry["code_size_bytes"] = len(raw)
            entry["code_sha256"] = hashlib.sha256(raw).hexdigest()
        report[name] = entry
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, sort_keys=True)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
