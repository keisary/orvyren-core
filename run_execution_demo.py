#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — execution-layer demo: policy verdict -> unsigned instruction -> receipt check.

Three demo intents go through the deterministic policy. Anything but ALLOW is
blocked by the guard. For the ALLOW case the demo emits a complete but
*unsigned* ERC-20 transfer instruction (token contract + calldata) that a human
executes in their own wallet — the agent never holds a key and never signs.
If ORVYREN_TX_HASH is set, the resulting receipt is fetched (read-only) and
verified against what the policy allowed.

Output: evidence/policy_execution_demo.json (plus a compact summary on stdout).
Usage:  python run_execution_demo.py
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from orvyren.policy import ALLOWED_CHAIN_ID, PolicyConfig, evaluate  # noqa: E402
from orvyren.execution import chain as chain_client  # noqa: E402
from orvyren.execution.guard import (  # noqa: E402
    ExecutionConfig,
    PolicyViolationError,
    assert_allowed,
    execution_allowed,
)
from orvyren.execution.intents import (  # noqa: E402
    EXPECTED_VERDICTS,
    build_demo_intents,
)
from orvyren.execution.verify import value_to_base_units, verify_receipt  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
EVIDENCE_PATH = os.path.join(ROOT, "evidence", "policy_execution_demo.json")
MODE = "unsigned instruction + human execution + on-chain receipt verification"
CHAIN_LABEL = "Base Sepolia (84532)"
INSTRUCTION_NOTE = "human executes this transfer; the agent never holds the key"
PENDING_VERIFICATION = "no transaction hash provided yet (pending human execution)"


def build_policy_config(config, now):
    """Policy limits taken from the (environment-overridable) execution config."""
    return PolicyConfig(
        allowed_recipients=frozenset({config.reserve_address.lower()}),
        max_per_tx=config.max_per_tx,
        max_cumulative=config.max_cumulative,
        permission_expires_at=now + timedelta(hours=config.permission_ttl_hours),
    )


def build_instruction(intent):
    """Complete unsigned ERC-20 transfer instruction (token contract + calldata)."""
    calldata = chain_client.erc20_transfer_calldata(
        intent.recipient, value_to_base_units(intent.amount))
    return {"to": intent.asset, "calldata": calldata, "note": INSTRUCTION_NOTE}


def verify_on_chain(config, intent, tx_hash):
    """Read-only receipt verification of a human-executed transfer."""
    try:
        receipt = chain_client.get_transaction_receipt(
            tx_hash, url=config.rpc_url, timeout=config.timeout_seconds)
        if receipt is None:
            return {"tx_hash": tx_hash,
                    "status": "receipt not found on chain yet (transaction may still be pending)"}
        receipt = dict(receipt)
        if "chainId" not in receipt:  # JSON-RPC receipts carry no chain id: attach the one we read
            receipt["chainId"] = hex(chain_client.chain_id(
                url=config.rpc_url, timeout=config.timeout_seconds))
        expected = {
            "token": intent.asset,
            "from": config.treasury_address,
            "to": intent.recipient,
            "amount_usdc": intent.amount,
            "chain_id": ALLOWED_CHAIN_ID,
        }
        return {"tx_hash": tx_hash, "result": verify_receipt(receipt, expected)}
    except chain_client.ChainError as exc:
        return {"tx_hash": tx_hash,
                "status": "read-only verification unavailable: {}".format(exc)}


def build_report(config, now, tx_hash=None):
    """Build the evidence report dict (also used directly by the test bench)."""
    policy = build_policy_config(config, now)
    cases = []
    guard_blocks = []
    allowed_intent = None

    for intent in build_demo_intents(now=now, reserve=config.reserve_address):
        decision = evaluate(intent, policy, now=now)
        instruction = None
        if execution_allowed(decision):
            instruction = build_instruction(intent)
            if allowed_intent is None:
                allowed_intent = intent
        else:
            try:
                assert_allowed(decision)
            except PolicyViolationError as exc:
                guard_blocks.append("{}: {}".format(intent.intent_id, exc))
        cases.append({
            "intent_id": intent.intent_id,
            "action_type": intent.action,
            "amount_usdc": intent.amount,
            "recipient": intent.recipient,
            "verdict": decision.verdict,
            "deny_codes": list(decision.reasons),
            "rules_evaluated": decision.rules_evaluated,
            "instruction": instruction,
        })

    if tx_hash and allowed_intent is not None:
        receipt_verification = verify_on_chain(config, allowed_intent, tx_hash)
    else:
        receipt_verification = {"status": PENDING_VERIFICATION}

    unexpected = [
        {"intent_id": case["intent_id"], "verdict": case["verdict"],
         "expected": EXPECTED_VERDICTS.get(case["intent_id"])}
        for case in cases if EXPECTED_VERDICTS.get(case["intent_id"]) != case["verdict"]
    ]

    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "chain": CHAIN_LABEL,
        "mode": MODE,
        "agent_holds_key": False,
        "execution_config": config.safe_dict(),
        "cases": cases,
        "guard_blocks": guard_blocks,
        "receipt_verification": receipt_verification,
        "verdict_check": {"expected": EXPECTED_VERDICTS, "unexpected": unexpected},
    }


def _short(address):
    return "{}…{}".format(address[:8], address[-6:]) if len(address) > 20 else address


def print_summary(report):
    config_view = report["execution_config"]
    print("ORVYREN-Core — execution-layer demo")
    print("mode: {}".format(report["mode"]))
    print("chain: {}".format(report["chain"]))
    print("policy: max_per_tx={} max_cumulative={} ttl={}h dry_run={} rpc={}".format(
        config_view["max_per_tx"], config_view["max_cumulative"],
        config_view["permission_ttl_hours"], config_view["dry_run"],
        config_view["rpc_url_masked"]))
    for case in report["cases"]:
        codes = ", ".join(case["deny_codes"]) if case["deny_codes"] else "-"
        print("{:>2}  {:<16} {:<13} {:>6} USDC -> {}  deny_codes: {}".format(
            case["intent_id"], case["verdict"], case["action_type"],
            case["amount_usdc"], _short(case["recipient"]), codes))
        if case["instruction"]:
            print("      instruction (unsigned): to {}".format(case["instruction"]["to"]))
            print("      calldata: {}".format(case["instruction"]["calldata"]))
    verification = report["receipt_verification"]
    if "result" in verification:
        print("receipt verification: tx={} ok={} mismatches={}".format(
            verification["tx_hash"], verification["result"]["ok"],
            verification["result"]["mismatches"]))
    else:
        print("receipt verification: {}".format(verification.get("status")))
    print("guard blocks: {} instruction(s) refused by assert_allowed".format(
        len(report["guard_blocks"])))
    blocked_ids = ", ".join(block.split(":")[0] for block in report["guard_blocks"]) or "none"
    print("guard blocked intents: {}".format(blocked_ids))
    print("secret env vars detected (names only, never read): {}".format(
        config_view["secret_env_vars_present"] or "none"))
    print("verdicts match expectation: {}".format(not report["verdict_check"]["unexpected"]))
    print("evidence written: {}".format(EVIDENCE_PATH))


def main():
    now = datetime.now(timezone.utc)
    config = ExecutionConfig.from_env()
    tx_hash = (os.environ.get("ORVYREN_TX_HASH") or "").strip() or None

    report = build_report(config, now, tx_hash=tx_hash)

    os.makedirs(os.path.dirname(EVIDENCE_PATH), exist_ok=True)
    with open(EVIDENCE_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    print_summary(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
