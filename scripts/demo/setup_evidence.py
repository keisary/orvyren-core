#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — consolidation of the on-chain setup evidence (from the receipts).

Reads ``demo_runs/setup/receipts/*.json`` (one receipt per step), fetches each
transaction's input via ``eth_getTransactionByHash``, **recomputes the Safe (EIP-712) hashes** of the
2/3 calls and **decodes the expected events** (ProxyCreation, ModuleProxyCreation, RolesModSetup,
ScopeTarget, ScopeFunction, SetAllowance, AssignRoles, EnabledModule, ExecutionSuccess).

Output: ``demo_runs/setup/tx_hashes.json`` (full index + decoded events).

Usage:
    python scripts/demo/setup_evidence.py [--receipts DIR] [--out DIR] [--rpc-url URL]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

try:  # package
    from . import common, setup_chain
except ImportError:  # direct execution
    _sys_dir = os.path.dirname(os.path.abspath(__file__))
    if _sys_dir not in sys.path:
        sys.path.insert(0, _sys_dir)
    import common  # type: ignore  # noqa: E402
    import setup_chain  # type: ignore  # noqa: E402

TOPICS = {
    "ProxyCreation(address,address)": None,
    "ModuleProxyCreation(address,address)": None,
    "RolesModSetup(address,address,address,address)": None,
    "SetAllowance(bytes32,uint128,uint128,uint128,uint64,uint64)": None,
    "ScopeTarget(bytes32,address)": None,
    "ScopeFunction(bytes32,address,bytes4,(uint8,uint8,uint8,bytes)[],uint8)": None,
    "AllowTarget(bytes32,address,uint8)": None,
    "AssignRoles(address,bytes32[],bool[])": None,
    "EnabledModule(address)": None,
    "ExecutionSuccess(bytes32,uint256)": None,
    "ExecutionFailure(bytes32,uint256)": None,
}


def _topic_map() -> Dict[str, str]:
    return {common.keccak256_hex(sig.encode("ascii")): sig.split("(")[0] for sig in TOPICS}


SAFE_STEPS = ["safe_enable_module", "role_scope_target", "role_allowance_usdc",
              "role_allowance_calls", "role_scope_function", "role_assign_agent"]


def decode_event(log_entry: Dict[str, Any], topics_map: Dict[str, str]) -> Dict[str, Any]:
    """Decodes the event name and its main arguments (best effort, never an exception)."""
    raw_topics = log_entry.get("topics") or []
    topic0 = raw_topics[0][2:].lower() if raw_topics else ""
    name = topics_map.get(topic0, "?")
    data = (log_entry.get("data") or "0x")[2:]
    out: Dict[str, Any] = {"address": log_entry.get("address"), "topic0": "0x" + topic0, "event": name}
    args: Dict[str, Any] = {}
    try:
        if name == "SetAllowance" and len(data) >= 64 * 6:
            args = {"allowanceKey": "0x" + data[0:64], "balance": int(data[64:128], 16),
                    "maxRefill": int(data[128:192], 16), "refill": int(data[192:256], 16),
                    "period": int(data[256:320], 16), "timestamp": int(data[320:384], 16)}
        elif name == "ScopeTarget" and len(data) >= 128:
            args = {"roleKey": "0x" + data[0:64], "targetAddress": "0x" + data[24:64]}
        elif name == "ScopeFunction" and len(data) >= 64 * 4:
            args = {"roleKey": "0x" + data[0:64], "targetAddress": "0x" + data[24:64],
                    "selector": "0x" + data[64:72], "options": int(data[192:256], 16),
                    "conditions_sha256": common.sha256_hex(bytes.fromhex(data))}
        elif name == "AssignRoles" and len(data) >= 64:
            args = {"module_declared": "0x" + data[24:64]}
        elif name in ("ProxyCreation", "ModuleProxyCreation"):
            args = {"proxy": ("0x" + raw_topics[1][26:]) if len(raw_topics) > 1 else None,
                    "second": ("0x" + data[24:64]) if len(data) >= 64 else None}
        elif name in ("ExecutionSuccess", "ExecutionFailure"):
            args = {"safeTxHash": ("0x" + raw_topics[1][2:]) if len(raw_topics) > 1 else ("0x" + data[0:64])}
            if len(data) >= 128:
                args["payment"] = int(data[64:128], 16)
        elif name == "EnabledModule" and len(raw_topics) > 1:
            args = {"module": "0x" + raw_topics[1][26:]}
        elif name == "RolesModSetup" and len(raw_topics) >= 4:
            args = {"initiator": "0x" + raw_topics[1][26:], "owner": "0x" + raw_topics[2][26:],
                    "avatar": "0x" + raw_topics[3][26:]}
    except Exception:  # noqa: BLE001 - best-effort proof
        args = {"note": "arguments not decoded"}
    if args:
        out["args"] = args
    return out


def build_index(receipts_dir: str, rpc_url: str, safe_hint: Optional[str] = None) -> Dict[str, Any]:
    topics_map = _topic_map()
    receipts: Dict[str, Dict[str, Any]] = {}
    for name in sorted(os.listdir(receipts_dir)):
        if name.endswith(".json"):
            receipts[name[:-5]] = json.load(open(os.path.join(receipts_dir, name), encoding="utf-8"))
    order = ["agent_fund", "safe_deploy", "module_deploy"] + SAFE_STEPS
    index: Dict[str, Any] = {"schema": "orvyren-setup-evidence/v1", "chain_id": setup_chain.CHAIN_ID_DEMO,
                             "rebuilt_at": common.utc_now(), "tx": [], "events": {}}
    safe_address = safe_hint
    safe_nonce: Optional[int] = None
    for step in order:
        receipt = receipts.get(step)
        if not receipt:
            continue
        tx_hash = receipt["transactionHash"]
        transaction = common.rpc(rpc_url, "eth_getTransactionByHash", [tx_hash]) or {}
        entry: Dict[str, Any] = {
            "step": step, "tx_hash": tx_hash,
            "status": "0x1" if int(receipt.get("status") or "0x0", 16) == 1 else receipt.get("status"),
            "block": int(receipt.get("blockNumber") or "0x0", 16),
            "gas_used": int(receipt.get("gasUsed") or "0x0", 16),
            "from": transaction.get("from"), "to": transaction.get("to"),
            "value_wei": int(transaction.get("value") or "0x0", 16),
            "input_selector": (transaction.get("input") or "0x")[:10],
            "input_sha256": common.sha256_hex(bytes.fromhex((transaction.get("input") or "0x")[2:])),
        }
        if step == "safe_deploy" and not safe_address:
            events = [decode_event(log, topics_map) for log in (receipt.get("logs") or [])]
            proxy = next((e.get("args", {}).get("proxy") for e in events if e["event"] == "ProxyCreation"), None)
            safe_address = proxy or safe_address
        if step in SAFE_STEPS and safe_address and safe_nonce is not None:
            outer = transaction.get("input") or "0x"
            body = outer[10:]
            inner_to = "0x" + body[24:64]
            data_offset = int(body[128:192], 16) * 2      # mot 0 = to, mot 1 = value, mot 2 = offset(data)
            inner_len = int(body[data_offset:data_offset + 64], 16)
            inner_data = "0x" + body[data_offset + 64: data_offset + 64 + inner_len * 2]
            entry.update({
                "safe_nonce": safe_nonce,
                "safe_tx_hash": setup_chain.safe_tx_hash(safe_address, inner_to, 0, inner_data, 0, 0, 0, 0,
                                                         setup_chain.ZERO_ADDRESS, setup_chain.ZERO_ADDRESS,
                                                         safe_nonce, setup_chain.CHAIN_ID_DEMO),
                "inner_to": inner_to,
                "inner_calldata_sha256": common.sha256_hex(bytes.fromhex(inner_data[2:])),
            })
            safe_nonce += 1
        if step == "safe_deploy" and safe_nonce is None:
            safe_nonce = 0
        index["tx"].append(entry)
        index["events"][step] = [decode_event(log, topics_map) for log in (receipt.get("logs") or [])]
    # cross-check: local hash == safeTxHash emitted by ExecutionSuccess
    checks = []
    for entry in index["tx"]:
        if "safe_tx_hash" not in entry:
            continue
        onchain = next((e.get("args", {}).get("safeTxHash") for e in index["events"].get(entry["step"], [])
                        if e["event"] == "ExecutionSuccess"), None)
        checks.append({"step": entry["step"], "local": entry["safe_tx_hash"], "on_chain": onchain,
                       "match": bool(onchain and onchain.lower() == entry["safe_tx_hash"].lower())})
    index["safe_tx_hash_checks"] = checks
    index["all_safe_tx_hashes_verified"] = bool(checks) and all(c["match"] for c in checks)
    return index


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="ORVYREN — consolidation of the setup evidence")
    parser.add_argument("--receipts", default=os.path.join(common.ROOT, "demo_runs", "setup", "receipts"))
    parser.add_argument("--out", default=os.path.join(common.ROOT, "demo_runs", "setup"))
    parser.add_argument("--rpc-url", default=os.environ.get("ORVYREN_RPC_URL_BASE_SEPOLIA") or common.DEFAULT_RPC_URL)
    args = parser.parse_args(argv)
    if common.eth_chain_id(args.rpc_url) != setup_chain.CHAIN_ID_DEMO:
        print("REFUSED: chain ≠ {}".format(setup_chain.CHAIN_ID_DEMO), file=sys.stderr)
        return 2
    index = build_index(args.receipts, args.rpc_url)
    common.write_json(os.path.join(args.out, "tx_hashes.json"), index)
    print("{} transaction(s) indexed; Safe hashes verified: {}".format(
        len(index["tx"]), index["all_safe_tx_hashes_verified"]))
    for entry in index["tx"]:
        print("  {:<22} {} status={} block={}".format(entry["step"], entry["tx_hash"], entry["status"], entry["block"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
