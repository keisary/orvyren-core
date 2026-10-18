#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — DAO side of the kill switch (run D): ``assignRoles(agent, [AGENT], [flag])`` by the 2/3 Safe.

The AGENT role is removed (or restored) by the **DAO** — 2 signatures out of 3, never by the agent:

    python scripts/demo/dao_assign_roles.py --enable false    # revocation (K1 kill switch)
    python scripts/demo/dao_assign_roles.py --enable true     # reset after the demonstration

Printed evidence: Safe transaction signed/submitted from a funded owner, verified receipt,
and **independent simulation** of the effect (eth_call from the agent: the module must revert
``NoMembership`` = ``0xfd8e9f28`` after revocation, and no longer do so after reset).
No key is ever displayed; ``evidence/demo_runs/setup/dao_assign_roles_last.json`` receives the hash.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import calls  # noqa: E402
import common  # noqa: E402
import setup_chain as sc  # noqa: E402

NOT_AUTHORIZED = "0xfd8e9f28"  # NoMembership() — measured on-chain on 2026-10-16 (measurement beats the doc)


def simulate_agent_call(setup: "sc.ChainSetup", recipient: str, amount: int = 1_000_000) -> Dict[str, Any]:
    """Simulation (eth_call) of a transfer through the module from the agent — revert selector included."""
    data = calls.exec_with_role_data(target=setup.usdc, value=0,
                                     inner_data=calls.erc20_transfer_data(recipient, amount),
                                     operation=calls.OPERATION_CALL, role_key=common.ROLE_KEY_AGENT)
    return setup.call_with_revert_data(setup.module_address, data, frm=setup.agent)


def main() -> int:
    parser = argparse.ArgumentParser(description="assignRoles(agent, [AGENT], [flag]) by the 2/3 Safe")
    parser.add_argument("--enable", required=True, choices=("true", "false"),
                        help="true = (re)grants the AGENT role; false = revocation (kill switch)")
    parser.add_argument("--env-file", default=os.path.join(_HERE, ".env"))
    parser.add_argument("--owners-file", default=os.path.join(_HERE, "owners.env"))
    parser.add_argument("--rpc-url", default=os.environ.get("ORVYREN_RPC_URL_BASE_SEPOLIA") or common.DEFAULT_RPC_URL)
    parser.add_argument("--out-dir", default=os.path.join(common.ROOT, "evidence", "demo_runs", "setup"))
    args = parser.parse_args()

    setup = sc.ChainSetup(env_file=args.env_file, owners_file=args.owners_file, rpc_url=args.rpc_url,
                          out_dir=args.out_dir, execute=True)
    setup.load_config()
    setup.check_chain()
    setup.safe_address = common.normalize_address(setup.env["ORVYREN_SAFE_ADDRESS"], "safe")
    setup.module_address = common.normalize_address(setup.env["ORVYREN_MODULE_ADDRESS"], "module")
    for address, label in ((setup.safe_address, "Safe"), (setup.module_address, "module")):
        code = common.eth_get_code(setup.rpc_url, address)
        if not code or code == "0x":
            raise sc.SetupError("{} without code on chain — stopping".format(label))
    setup.submitter = setup.owner_addresses[0]
    setup._safe_nonce_expected = None

    flag = args.enable == "true"
    label = "dao_assign_roles_enable" if flag else "dao_assign_roles_revoke"
    data = calls.assign_roles_data(setup.agent, [common.ROLE_KEY_AGENT], [flag])
    decoded = calls.decode_assign_roles(data)
    print("[info] assignRoles member={} role_keys={} enabled={}".format(
        decoded["member"], decoded["role_keys"], decoded["enabled"]))

    def verify() -> None:
        sim = simulate_agent_call(setup, setup.recipient_b)
        selector = common.revert_selector(sim.get("revert_data")) if sim.get("revert_data") else None
        if not flag:
            if selector != NOT_AUTHORIZED:
                raise sc.SetupError(
                    "agent simulation: expected NotAuthorized({}) after revocation, observed {!r}".format(
                        NOT_AUTHORIZED, selector))
        elif selector == NOT_AUTHORIZED:
            raise sc.SetupError("agent simulation: the role still seems removed (NotAuthorized) after reset")
        print("[ok] independent agent simulation — revert_selector={!r} (expected: {} )".format(
            selector, "absent/other" if flag else NOT_AUTHORIZED))

    setup.execute_safe_call(label, setup.module_address, data, verify=verify)
    entry = setup.artifacts["safe_calls"][-1]
    print("TX_HASH={}".format(entry["tx_hash"]))
    common.write_json(os.path.join(setup.out_dir, "dao_assign_roles_last.json"),
                      {"label": label, "enable": flag, "safe": setup.safe_address,
                       "module": setup.module_address, "agent": setup.agent,
                       "tx_hash": entry["tx_hash"], "safe_tx_hash": entry["safe_tx_hash"],
                       "signers": entry["signers"], "calldata": data,
                       "calldata_sha256": common.sha256_hex(bytes.fromhex(data[2:])),
                       "submitted_at": common.utc_now()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
