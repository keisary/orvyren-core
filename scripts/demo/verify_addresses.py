#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — testnet demo kit (W5, L5.2): **address verification before a run**.

Before every run, check that the session points to the right Base Sepolia
addresses: EIP-55 format, **code presence** (``eth_getCode``) for the expected
contracts, **code absence** for the expected EOAs, pinned ``chainId``, captured
reference block. Kit rule: **stop on any mismatch** — every mismatch exits with
``exit 1`` and the setup stops.

Modes:

* ``--offline`` (default): format only — no network; the chain checks
  are ``SKIPPED`` and the report carries ``verdict = OFFLINE_PASS``;
* ``--rpc``: live checks (read-only, User-Agent included).

CLI:

    python scripts/demo/verify_addresses.py [--env-file scripts/demo/.env] [--rpc] [--out report.json]
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional

try:  # package (``demo.verify_addresses``)
    from . import common
except ImportError:  # direct execution: python scripts/demo/verify_addresses.py
    _sys_dir = os.path.dirname(os.path.abspath(__file__))
    if _sys_dir not in sys.path:
        sys.path.insert(0, _sys_dir)
    import common  # type: ignore  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ENV = os.path.join(HERE, ".env")
DEFAULT_OWNERS = os.path.join(HERE, "owners.env")

#: Addresses that MUST carry code (deployed contracts).
EXPECT_CONTRACT = ("ORVYREN_SAFE_ADDRESS", "ORVYREN_MODULE_ADDRESS", "ORVYREN_USDC_ADDRESS")
#: Addresses that MUST NOT carry code (throwaway EOA).
EXPECT_EOA = ("ORVYREN_AGENT_ADDRESS",)
#: Addresses reported without contract/EOA requirement (recipients, owners).
INFO_ONLY = ("ORVYREN_RECIPIENT_B", "ORVYREN_RECIPIENT_C", "ORVYREN_RECIPIENT_UNLISTED",
             "ORVYREN_OWNER1_ADDRESS", "ORVYREN_OWNER2_ADDRESS", "ORVYREN_OWNER3_ADDRESS")
ADDRESS_KEYS = EXPECT_CONTRACT + EXPECT_EOA + INFO_ONLY

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2


def collect_addresses(env_files: List[str]) -> Dict[str, str]:
    """Merges the env files; known ``*_ADDRESS`` keys only."""
    merged: Dict[str, str] = {}
    for path in env_files:
        for key, value in common.read_env_file(path).items():
            if key in ADDRESS_KEYS and value.strip():
                merged.setdefault(key, value.strip())
    return merged


def check_one(key: str, value: str, *, rpc_url: Optional[str]) -> Dict[str, Any]:
    entry: Dict[str, Any] = {"key": key, "address": value, "status": "PASS"}
    try:
        normalized = common.normalize_address(value)
    except Exception as exc:  # invalid EIP-55 format → immediate mismatch
        entry["status"] = "FAIL"
        entry["reason"] = "invalid address (EIP-55): %s" % exc
        return entry
    entry["normalized"] = normalized
    if key in EXPECT_CONTRACT:
        entry["expected"] = "contract"
    elif key in EXPECT_EOA:
        entry["expected"] = "eoa"
    else:
        entry["expected"] = "info"
    if rpc_url is None:
        entry["code"] = "SKIPPED (offline)"
        return entry
    try:
        code = common.eth_get_code(rpc_url, normalized) or "0x"
    except Exception as exc:
        entry["status"] = "FAIL"
        entry["reason"] = "rpc getCode: %s" % exc
        return entry
    kind = "contract" if code not in ("0x", "") else "eoa"
    entry["code_kind"] = kind
    entry["code_size_bytes"] = (len(code) - 2) // 2
    if entry["expected"] == "contract" and kind != "contract":
        entry["status"] = "FAIL"
        entry["reason"] = "code expected (contract) — absent on chain"
    if entry["expected"] == "eoa" and kind != "eoa":
        entry["status"] = "FAIL"
        entry["reason"] = "unexpected code on an EOA"
    return entry


def run(*, env_files: List[str], rpc_url: Optional[str],
        expected_chain_id: int) -> Dict[str, Any]:
    addresses = collect_addresses(env_files)
    report: Dict[str, Any] = {
        "mode": "rpc" if rpc_url else "offline",
        "env_files": [common.display_path(p) if os.path.isfile(p) else p for p in env_files],
        "expected_chain_id": expected_chain_id,
        "addresses": [], "chain": {}, "checks": [],
    }
    if not addresses:
        report["checks"].append({"id": "V0", "status": "FAIL",
                                 "detail": "no address (*_ADDRESS) found in %s"
                                           % ", ".join(env_files)})
        report["verdict"] = "FAIL"
        return report

    chain_id = None
    block_number = None
    if rpc_url:
        try:
            chain_id = common.eth_chain_id(rpc_url)
            block_number = common.eth_block_number(rpc_url)
        except Exception as exc:
            report["checks"].append({"id": "V1", "status": "FAIL",
                                     "detail": "rpc unavailable: %s" % exc})
            report["verdict"] = "FAIL"
            return report
        report["chain"] = {"chain_id": chain_id, "block_number": block_number,
                           "chain_id_ok": chain_id == expected_chain_id}
        if chain_id != expected_chain_id:
            report["checks"].append({
                "id": "V1.chain_id", "status": "FAIL",
                "detail": "failure: chainId %s expected %s — stopping (everything would sign on the "
                          "wrong chain)" % (chain_id, expected_chain_id)})
            report["verdict"] = "FAIL"
            return report
    else:
        report["chain"] = {"chain_id": "SKIPPED (offline)", "block_number": "SKIPPED (offline)"}

    failures = 0
    for key in ADDRESS_KEYS:
        if key not in addresses:
            continue
        entry = check_one(key, addresses[key], rpc_url=rpc_url)
        report["addresses"].append(entry)
        if entry["status"] == "FAIL":
            failures += 1

    missing = [key for key in (EXPECT_CONTRACT + EXPECT_EOA) if key not in addresses]
    if missing:
        report["checks"].append({"id": "V2.complete", "status": "FAIL",
                                 "detail": "missing keys: %s" % ", ".join(missing)})
        failures += 1
    else:
        report["checks"].append({"id": "V2.complete", "status": "PASS",
                                 "detail": "all required addresses are present"})

    if failures:
        report["verdict"] = "FAIL"
    elif rpc_url:
        report["verdict"] = "PASS"
    else:
        report["verdict"] = "OFFLINE_PASS"
    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verify_addresses.py",
        description="ORVYREN (W5/L5.2) — session addresses: EIP-55 format, contract "
                    "code, code absence on EOAs, pinned chainId. "
                    "Stop on mismatch.")
    parser.add_argument("--env-file", action="append", default=None,
                        help="KEY=VALUE file (repeatable; default: .env then owners.env)")
    parser.add_argument("--rpc", action="store_true", help="live checks (read-only)")
    parser.add_argument("--rpc-url", default=None)
    parser.add_argument("--chain-id", type=int, default=None)
    parser.add_argument("--out", default=None, help="JSON report")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    env_files = args.env_file or [DEFAULT_ENV, DEFAULT_OWNERS]
    env = common.load_session_env(env_files[0] if env_files else None)
    rpc_url = args.rpc_url or (env.get("ORVYREN_RPC_URL_BASE_SEPOLIA") if args.rpc else None)
    if args.rpc and not rpc_url:
        print("verify_addresses: --rpc requires --rpc-url or ORVYREN_RPC_URL_BASE_SEPOLIA", file=sys.stderr)
        return EXIT_USAGE
    expected_chain_id = args.chain_id or int(env.get("ORVYREN_CHAIN_ID") or 84532)

    report = run(env_files=env_files, rpc_url=rpc_url, expected_chain_id=expected_chain_id)
    if args.out:
        common.write_json(args.out, report)
    if not args.quiet:
        for entry in report["addresses"]:
            line = "  %-32s %-44s %s" % (entry["key"], entry.get("normalized", entry["address"]),
                                         entry.get("code_kind", entry.get("code", "")))
            if entry["status"] == "FAIL":
                line += "  → %s" % entry.get("reason", "mismatch")
            print(line)
        for check in report["checks"]:
            print("  [%s] %s — %s" % (check["status"], check["id"], str(check["detail"])[:160]))
        print("VERDICT: %s" % report["verdict"])
    return EXIT_OK if report["verdict"] in ("PASS", "OFFLINE_PASS") else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
