#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — execution-layer demo: REAL policy bundle -> verdict -> unsigned instruction.

The demo now evaluates the **real** policy: ``policy_v1.yaml`` is loaded with
``load_policy`` (recipient labels resolved from ``ORVYREN_RECIPIENT_B`` /
``ORVYREN_RECIPIENT_C``), and every verdict is computed with a full
``PolicyState`` (pause/kill switch P11, balance P7, envelope P12, decision
budget P14) plus a 24 h cumulative from a session ledger (P6). No state rule is
``SKIPPED`` any more — the only remaining skip is P4 for the approval-only
``change_policy`` action, with its motif written out.

Three demo intents go through the deterministic policy. Anything but ALLOW is
blocked by the guard. For the ALLOW case the demo emits a complete but
*unsigned* ERC-20 transfer instruction (token contract + calldata) that a human
executes in their own wallet — the agent never holds a key and never signs.
If ``ORVYREN_TX_HASH`` is set, the resulting receipt is fetched (read-only) and
verified against what the policy allowed.

A dedicated 4 x 100 USDC check then shows the period cap: the fourth transfer
is DENY ``AMOUNT_ABOVE_PERIOD_CAP`` — including after reloading the ledger from
disk (restart simulation).

Output: evidence/policy_execution_demo.json (override: ORVYREN_DEMO_OUT).
Usage:  python run_execution_demo.py
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from orvyren.policy import (  # noqa: E402
    ALLOWED_ASSET,
    ALLOWED_CHAIN_ID,
    Intent,
    evaluate,
    load_policy,
)
from orvyren.execution import chain as chain_client  # noqa: E402
from orvyren.execution.guard import (  # noqa: E402
    ExecutionConfig,
    PolicyViolationError,
    assert_allowed,
    execution_allowed,
)
from orvyren.execution.intents import (  # noqa: E402
    DEMO_CLOCK,
    EXPECTED_VERDICTS,
    build_demo_intents,
)
from orvyren.execution.loop import (  # noqa: E402
    DEFAULT_AVAILABLE_BALANCE,
    PeriodLedger,
    apply_permission_window,
    build_policy_state as make_policy_state,
    collect_recipients,
    decision_budget_cap,
    resolve_agent_member,
    resolve_available_balance,
    resolve_envelope,
    resolve_pause,
)
from orvyren.execution.verify import value_to_base_units, verify_receipt  # noqa: E402

POLICY_PATH = os.path.join(ROOT, "policy_v1.yaml")
EVIDENCE_PATH = os.path.join(ROOT, "evidence", "policy_execution_demo.json")
MODE = "unsigned instruction + human execution + on-chain receipt verification"
CHAIN_LABEL = "Base Sepolia (84532)"
INSTRUCTION_NOTE = "human executes this transfer; the agent never holds the key"
PENDING_VERIFICATION = "no transaction hash provided yet (pending human execution)"


def _display_path(path):
    """Repo-relative POSIX path when inside the repository, else absolute."""
    try:
        relative = os.path.relpath(path, ROOT).replace(os.sep, "/")
    except ValueError:
        return path.replace(os.sep, "/")
    return path.replace(os.sep, "/") if relative.startswith("..") else relative


def build_demo_policy(config, env=None):
    """Load policy_v1.yaml and resolve the session recipients.

    The file is the source of truth for the parameters; addresses stay out of
    the file (labels B/C resolved from the environment or the execution
    config). The mandate expiry (P8) is an execution fact: the bundle TTL is
    applied against the demo clock.
    """
    environment = os.environ if env is None else env
    recipient, recipients = collect_recipients(None, environment,
                                               fallback=config.reserve_address)
    if not os.path.exists(POLICY_PATH):
        raise FileNotFoundError("policy_v1.yaml not found: %s" % POLICY_PATH)
    bundle = load_policy(POLICY_PATH, recipients)
    return bundle, recipient, recipients


def build_state(bundle, clock, env=None):
    """Real PolicyState: pause, membership, envelope, balance, budget (P14).

    This is an **explicit offline demo**: when the membership/balance variables
    are unset it opts into the demo values (member=true, 1000 USDC) and records
    that fact in the report. Production callers (``run_executor.py``) have no
    such default: missing values fail closed.
    """
    environment = dict(os.environ if env is None else env)
    if not str(environment.get("ORVYREN_AGENT_MEMBER") or "").strip():
        environment["ORVYREN_AGENT_MEMBER"] = "true"
    if not str(environment.get("ORVYREN_AVAILABLE_BALANCE") or "").strip():
        environment["ORVYREN_AVAILABLE_BALANCE"] = str(DEFAULT_AVAILABLE_BALANCE)
    envelope = resolve_envelope(bundle, POLICY_PATH, None, environment)
    state = make_policy_state(
        paused=resolve_pause(environment),
        agent_member=resolve_agent_member(environment),
        envelope_status=envelope["status"],
        available_balance=resolve_available_balance(environment),
        budget_cap=decision_budget_cap(bundle),
    )
    return state, envelope


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


def build_period_cap_check(bundle, clock, recipient, env=None):
    """4 x 100 USDC on a persistent 24 h ledger: the 4th transfer is denied by P6.

    The ledger is written to disk then **reopened** with a fresh instance
    (simulated restart): the 300 USDC cumulative is really re-read, not
    forgotten.
    """
    state, _envelope = build_state(bundle, clock, env)
    amount = 100.0
    with tempfile.TemporaryDirectory(prefix="orvyren-period-cap-") as tmp:
        ledger_path = os.path.join(tmp, "ledger.json")
        ledger = PeriodLedger(ledger_path)
        verdicts = []
        for attempt in range(1, 5):
            intent = Intent(
                intent_id="period-cap-demo-{}".format(attempt),
                action="transfer",
                chain_id=ALLOWED_CHAIN_ID,
                asset=ALLOWED_ASSET,
                amount=amount,
                recipient=recipient,
                created_at=clock,
                justification="24 h rolling cap demonstration",
            )
            decision = evaluate(intent, bundle.config, now=clock,
                                seen_intent_ids=ledger.seen_intent_ids(),
                                cumulative_spent=ledger.spent(clock),
                                state=state)
            verdicts.append({
                "attempt": attempt,
                "intent_id": intent.intent_id,
                "verdict": decision.verdict,
                "deny_codes": list(decision.reasons),
            })
            if decision.verdict == "ALLOW":
                ledger.record(clock, intent.intent_id, amount)
        reopened = PeriodLedger(ledger_path)  # restart: re-read the file
        spent_after_restart = reopened.spent(clock)
        entries_after_restart = len(reopened.entries())
    return {
        "amount_usdc": amount,
        "max_cumulative_24h": bundle.config.max_cumulative,
        "verdicts": verdicts,
        "fourth_verdict": verdicts[-1]["verdict"],
        "fourth_deny_codes": verdicts[-1]["deny_codes"],
        "spent_24h_after_restart": spent_after_restart,
        "ledger_entries_after_restart": entries_after_restart,
        "restart_simulated": True,
    }


def build_report(config, now, tx_hash=None, clock=DEMO_CLOCK, env=None):
    """Build the evidence report dict (also used directly by the test bench).

    ``now`` is recorded as the run time (``generated_at``). Verdict content is
    computed at the fixed ``clock`` (see ``intents.py``) so the rule notes and
    permission window are reproducible across runs; pass ``clock=now`` to
    evaluate against the wall clock instead.
    """
    environment = os.environ if env is None else env
    demo_defaults = {
        "agent_member": not str(environment.get("ORVYREN_AGENT_MEMBER") or "").strip(),
        "available_balance": not str(environment.get("ORVYREN_AVAILABLE_BALANCE") or "").strip(),
    }
    bundle, recipient, recipients = build_demo_policy(config, environment)
    apply_permission_window(bundle, clock, default_hours=config.permission_ttl_hours)
    state, envelope = build_state(bundle, clock, environment)
    session = PeriodLedger()  # session ledger (in memory): replayable reports

    cases = []
    guard_blocks = []
    allowed_intent = None

    for intent in build_demo_intents(now=clock, reserve=recipient):
        decision = evaluate(intent, bundle.config, now=clock,
                            seen_intent_ids=session.seen_intent_ids(),
                            cumulative_spent=session.spent(clock),
                            state=state)
        instruction = None
        if execution_allowed(decision):
            instruction = build_instruction(intent)
            if allowed_intent is None:
                allowed_intent = intent
            session.record(clock, intent.intent_id, intent.amount)
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
            "skipped_rules": [rule.get("rule") for rule in decision.rules_evaluated
                              if rule.get("result") == "SKIPPED"],
            "policy_version": decision.policy_version,
            "policy_hash": decision.policy_hash,
            "instruction": instruction,
        })

    if tx_hash and allowed_intent is not None:
        receipt_verification = verify_on_chain(config, allowed_intent, tx_hash)
    elif tx_hash:
        # Truthful status: a hash WAS provided, but no intent was ALLOWed, so
        # there is nothing it could be verified against.
        receipt_verification = {
            "tx_hash": tx_hash,
            "status": "a transaction hash was provided but no intent was ALLOWed: "
                      "nothing to verify it against",
        }
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
        "policy": {
            "path": _display_path(POLICY_PATH),
            "version": bundle.version,
            "policy_hash": bundle.policy_hash,
            "yaml_sha256": bundle.yaml_sha256,
            "recipients_resolved": sorted(recipients),
            "unresolved_recipients": list(
                (bundle.data or {}).get("_unresolved_recipients") or []),
        },
        "policy_state": {
            "paused": state.paused,
            "agent_member": state.agent_member,
            "envelope_status": envelope["status"],
            "envelope_source": envelope.get("source"),
            "envelope_fixture": _display_path(envelope["fixture_path"])
            if envelope.get("fixture_path") else None,
            "envelope_checks": envelope.get("checks") or [],
            "available_balance": state.available_balance,
            "budget_cap_usd": state.budget_cap,
            "cumulative_spent_24h": session.spent(clock),
        },
        "demo_defaults": demo_defaults,
        "execution_config": config.safe_dict(),
        "cases": cases,
        "guard_blocks": guard_blocks,
        "period_cap_check": build_period_cap_check(bundle, clock, recipient, environment),
        "receipt_verification": receipt_verification,
        "verdict_check": {"expected": EXPECTED_VERDICTS, "unexpected": unexpected},
    }


def _short(address):
    return "{}…{}".format(address[:8], address[-6:]) if len(address) > 20 else address


def print_summary(report, out_path=None):
    config_view = report["execution_config"]
    policy = report["policy"]
    state = report["policy_state"]
    print("ORVYREN-Core — execution-layer demo")
    print("mode: {}".format(report["mode"]))
    print("chain: {}".format(report["chain"]))
    print("policy: policy_v1.yaml {} (hash {}) — parameters loaded from {}".format(
        policy["version"], str(policy["policy_hash"])[:16], policy["path"]))
    print("state : paused={} agent_member={} envelope={} balance={} budget_cap={}".format(
        state["paused"], state["agent_member"], state["envelope_status"],
        state["available_balance"], state["budget_cap_usd"]))
    defaults = report.get("demo_defaults") or {}
    if any(defaults.values()):
        print("demo defaults: ENABLED (member=true, balance=1000 USDC when env unset) "
              "— explicit offline demo, never implicit in production")
    print("limits: max_per_tx={} max_cumulative_24h={} ttl={}h dry_run={} rpc={}".format(
        config_view["max_per_tx"], config_view["max_cumulative"],
        config_view["permission_ttl_hours"], config_view["dry_run"],
        config_view["rpc_url_masked"]))
    skipped_all = set()
    for case in report["cases"]:
        codes = ", ".join(case["deny_codes"]) if case["deny_codes"] else "-"
        print("{:>2}  {:<16} {:<13} {:>6} USDC -> {}  deny_codes: {}".format(
            case["intent_id"], case["verdict"], case["action_type"],
            case["amount_usdc"], _short(case["recipient"]), codes))
        if case["skipped_rules"]:
            skipped_all.update(case["skipped_rules"])
            motifs = [str(rule.get("note") or "not applicable")
                      for rule in case["rules_evaluated"]
                      if rule.get("result") == "SKIPPED"]
            print("      SKIPPED rules: {} — {}".format(
                ", ".join(case["skipped_rules"]), "; ".join(motifs)))
        if case["instruction"]:
            print("      instruction (unsigned): to {}".format(case["instruction"]["to"]))
            print("      calldata: {}".format(case["instruction"]["calldata"]))

    cap = report["period_cap_check"]
    chain_verdicts = " · ".join(
        "{} {}".format(item["attempt"], item["verdict"]) for item in cap["verdicts"])
    print("24 h period (4 x {} USDC, cap {} USDC, JSON ledger re-read after restart):".format(
        cap["amount_usdc"], cap["max_cumulative_24h"]))
    print("      {}".format(chain_verdicts))
    print("      4th transfer: {} {}".format(
        cap["fourth_verdict"], ", ".join(cap["fourth_deny_codes"]) or "-"))
    print("      cumulative re-read after restart: {} USDC ({} entry(ies))".format(
        cap["spent_24h_after_restart"], cap["ledger_entries_after_restart"]))

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
    print("state rules evaluated (state supplied): P7/P11/P12/P14 — none SKIPPED")
    print("SKIPPED rules on the path: {}".format(
        ", ".join(sorted(skipped_all)) or "none"))
    print("evidence written: {}".format(out_path or EVIDENCE_PATH))


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="run_execution_demo.py",
        description="ORVYREN — execution demo: real policy (policy_v1.yaml), "
                    "full state, 24 h cap; no signature.")
    parser.add_argument("--out", default=os.environ.get("ORVYREN_DEMO_OUT") or EVIDENCE_PATH,
                        help="path of the JSON report (default: %(default)s)")
    args = parser.parse_args(argv)

    now = datetime.now(timezone.utc)
    config = ExecutionConfig.from_env()
    tx_hash = (os.environ.get("ORVYREN_TX_HASH") or "").strip() or None

    try:
        report = build_report(config, now, tx_hash=tx_hash)
    except Exception as exc:  # noqa: BLE001 — policy or fixture unavailable: clean refusal
        # Keep the refusal clean but name the failure class: an unexplained
        # "ERROR: ..." must not hide which kind of problem occurred.
        print("ERROR: {}: {}".format(type(exc).__name__, exc), file=sys.stderr)
        return 2

    out_path = args.out
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    print_summary(report, out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
