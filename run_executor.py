#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — autonomous executor CLI (dry-run by default).

One command, one bounded loop:

    python run_executor.py --case usdc-2023-03 --ticks 5 --dry-run

Each tick: replay decision (``build_decision_record``) -> bounded intent ->
``policy.evaluate`` with a real ``PolicyState`` (pause, balance, envelope,
budget) and the 24 h cumulative of a persistent ledger -> journaled verdict. An
ALLOW verdict in dry-run produces a DRY-RUN report without signature; with
``--execute`` the isolated signer is imported lazily, signs, broadcasts and the
receipt is verified — without a key or without ``eth-account``, the run is
refused before the first tick (code 4).

Exit codes: 0 run finished · 2 configuration/recipient · 3 pause
(kill switch) · 4 real execution unavailable · 5 execution error
(ledger/journal/network/receipt).

No key is read in dry-run. No secret is printed in any mode whatsoever.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime
from typing import Any, Callable, Mapping, Optional

ROOT = os.path.dirname(os.path.abspath(__file__))
if os.path.join(ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "src"))

from orvyren.execution import loop as executor  # noqa: E402
from orvyren.execution.chain import ChainError  # noqa: E402

DEFAULT_CASE = "usdc-2023-03"
DEFAULT_POLICY = os.path.join(ROOT, "policy_v1.yaml")
DEFAULT_RUN_DIR = os.path.join(ROOT, "demo_runs", "executor")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_executor.py",
        description="ORVYREN — bounded autonomous executor: decision -> policy "
                    "(real state) -> chained journal. Dry-run by default, no key read.")
    parser.add_argument("--case", default=DEFAULT_CASE,
                        help="replayed case identifier (default: %(default)s)")
    parser.add_argument("--ticks", type=int, default=1,
                        help="number of ticks (default: %(default)s)")
    parser.add_argument("--interval-s", type=float, default=0.0,
                        help="wait between ticks, in seconds (default: %(default)s)")
    parser.add_argument("--max-usd", type=float, default=None,
                        help="per-tick cap in USDC (optional) — above it, fail-closed refusal")
    parser.add_argument("--recipient", default=None,
                        help="requested reserve recipient — must appear in the resolved "
                             "allowlist (ORVYREN_RECIPIENT_B/C)")
    parser.add_argument("--policy", default=DEFAULT_POLICY,
                        help="path of policy_v1.yaml (default: repository root)")
    parser.add_argument("--fixture", default=None,
                        help="envelope fixture (default: the one declared by policy_v1.yaml)")
    parser.add_argument("--ledger", default=None,
                        help="24 h JSON ledger (default: demo_runs/executor/<case>/ledger.json)")
    parser.add_argument("--journal", default=None,
                        help="chained JSONL journal (default: demo_runs/executor/<case>/journal.jsonl)")
    parser.add_argument("--json", action="store_true",
                        help="machine output (one JSON object on stdout)")
    parser.add_argument("--demo-defaults", action="store_true",
                        help="explicit offline-demo defaults: AGENT member=true and "
                             "available balance=1000 USDC when the variables are unset "
                             "(never enabled implicitly)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=None,
                      help="no signature, no key read (default)")
    mode.add_argument("--execute", action="store_true",
                      help="real signing and broadcast (requires ORVYREN_PRIVATE_KEY + eth-account)")
    return parser


def _human(summary: Mapping[str, Any]) -> None:
    counts = summary["counts"]
    policy = summary["policy"]
    envelope = summary["envelope"]
    print("ORVYREN — autonomous executor ({})".format(summary["mode"]))
    print("  case       : {}  ({} tick(s) executed)".format(summary["case"], summary["ticks_run"]))
    print("  policy     : {}  hash {}  ({})".format(
        policy.get("version"), str(policy.get("policy_hash") or "")[:16],
        policy.get("path") or "policy_v1.yaml"))
    print("  envelope   : {} (source: {})".format(envelope.get("status"), envelope.get("source")))
    print("  recipient  : {}".format(summary["recipient"]))
    print("  ledger     : {}  ({:.2f} USDC spent / 24 h before the run)".format(
        summary["ledger"]["path"] or "(memory)", summary["ledger"]["spent_24h_before"]))
    print("  journal    : {}".format(summary["journal"]["path"]))
    print("  tick  intent                                        amount   verdict   outcome")
    for record in summary["records"]:
        intent = record.get("intent") or {}
        codes = ", ".join(record.get("reasons") or []) or "-"
        print("  {:>4}  {:<46} {:>7.2f}  {:<8}  {}".format(
            record.get("tick", 0), str(intent.get("intent_id") or "-")[:46],
            float(intent.get("amount") or 0.0), str(record.get("verdict") or "-"),
            str(record.get("outcome") or "-")))
        if codes != "-" or record.get("error"):
            print("        denied: {} {}".format(codes, record.get("error") or "").rstrip())
    chain_state = summary["journal"]
    print("  journal chain    : {}".format(
        "VALID ({} record(s))".format(chain_state["records"])
        if chain_state["ok"] else "BROKEN — {}".format(chain_state["error"])))
    print("  summary    : {} ALLOW · {} DENY · {} DRY-RUN · {} signed · {} error(s)".format(
        counts["allow"], counts["deny"], counts["dry_run"], counts["signed"], counts["errors"]))
    print("  spent 24 h after the run : {:.2f} USDC".format(summary["ledger"]["spent_24h_after"]))
    if summary["paused"]:
        print("  PAUSE / kill switch ENGAGED — no autonomous transfer was authorised.")
    if summary.get("demo_defaults"):
        print("  demo defaults : ENABLED (member=true, balance=1000 USDC) — explicit, never implicit")


def main(argv: Optional[list] = None, env: Optional[Mapping[str, str]] = None,
         clock: Optional[Callable[[], datetime]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    environment = dict(os.environ if env is None else env)
    effective_env = dict(environment)
    if args.demo_defaults:
        if not str(effective_env.get("ORVYREN_AGENT_MEMBER") or "").strip():
            effective_env["ORVYREN_AGENT_MEMBER"] = "true"
        if not str(effective_env.get("ORVYREN_AVAILABLE_BALANCE") or "").strip():
            effective_env["ORVYREN_AVAILABLE_BALANCE"] = str(executor.DEFAULT_AVAILABLE_BALANCE)
    else:
        missing = [name for name in ("ORVYREN_AGENT_MEMBER", "ORVYREN_AVAILABLE_BALANCE")
                   if not str(environment.get(name) or "").strip()]
        if missing:
            print("NOTE: {} unset — P11/P7 fail closed (DENY). "
                  "Pass --demo-defaults for the offline demo.".format(", ".join(missing)),
                  file=sys.stderr)
    now_fn = clock or executor.utcnow

    if args.ticks < 0:
        print("ERROR: --ticks must be >= 0", file=sys.stderr)
        return executor.EXIT_USAGE
    if args.interval_s is not None and (not math.isfinite(args.interval_s) or args.interval_s < 0):
        print("ERROR: --interval-s must be a finite number >= 0", file=sys.stderr)
        return executor.EXIT_USAGE
    if args.max_usd is not None and (not math.isfinite(args.max_usd) or args.max_usd < 0):
        print("ERROR: --max-usd must be a finite number >= 0", file=sys.stderr)
        return executor.EXIT_USAGE

    policy_path = args.policy if os.path.isabs(args.policy) else os.path.join(ROOT, args.policy)
    if not os.path.exists(policy_path):
        print("ERROR: policy_v1.yaml not found: {}".format(policy_path), file=sys.stderr)
        return executor.EXIT_USAGE
    # Same resolution rule as --policy: relative CLI paths resolve against the
    # repository root, never against the caller's working directory.
    fixture_path = args.fixture if (args.fixture is None or os.path.isabs(args.fixture)) \
        else os.path.join(ROOT, args.fixture)
    if fixture_path and not os.path.exists(fixture_path):
        print("ERROR: envelope fixture not found: {}".format(fixture_path), file=sys.stderr)
        return executor.EXIT_USAGE

    try:
        recipient, recipients = executor.collect_recipients(args.recipient, effective_env)
    except executor.RecipientError as exc:
        print("ERROR recipient: {}".format(exc), file=sys.stderr)
        return executor.EXIT_USAGE

    try:
        bundle = executor.load_bundle(policy_path, recipients)
    except executor.PolicyLoadError as exc:
        print("ERROR policy: {}".format(exc), file=sys.stderr)
        return executor.EXIT_USAGE
    allowed = {str(address).lower() for address in bundle.config.allowed_recipients}
    if recipient not in allowed:
        print("ERROR recipient: {} outside the policy_v1.yaml allowlist "
              "({} recipient(s) resolved: {}). Set ORVYREN_RECIPIENT_B/C "
              "or --recipient.".format(recipient, len(allowed), ", ".join(sorted(allowed)) or "none"),
              file=sys.stderr)
        return executor.EXIT_USAGE

    try:
        executor.apply_permission_window(bundle, now_fn())
    except executor.PolicyLoadError as exc:
        print("ERROR policy: {}".format(exc), file=sys.stderr)
        return executor.EXIT_USAGE

    signer = None
    if args.execute:
        try:
            signer = executor.preflight_signer(env=effective_env)
        except executor.ExecuteUnavailable as exc:
            print("ERROR --execute: {}".format(exc), file=sys.stderr)
            return executor.EXIT_EXECUTE

    run_dir = os.path.join(DEFAULT_RUN_DIR, executor.safe_case(args.case))
    journal_path = args.journal or os.path.join(run_dir, "journal.jsonl")
    ledger_path = args.ledger or os.path.join(run_dir, "ledger.json")

    try:
        summary = executor.run_loop(
            bundle,
            case=args.case,
            recipient=recipient,
            journal_path=journal_path,
            ledger_path=ledger_path,
            ticks=args.ticks,
            interval_s=args.interval_s,
            dry_run=not args.execute,
            max_usd=args.max_usd,
            policy_path=policy_path,
            fixture_path=fixture_path,
            env=effective_env,
            clock=now_fn,
            signer=signer,
            rpc_url=str(effective_env.get("ORVYREN_RPC_URL_BASE_SEPOLIA") or "") or None,
        )
    except (executor.LedgerError, executor.JournalError, executor.PolicyLoadError) as exc:
        print("ERROR execution: {}".format(exc), file=sys.stderr)
        return executor.EXIT_RUNTIME
    except ChainError as exc:
        print("ERROR network: {}".format(exc), file=sys.stderr)
        return executor.EXIT_RUNTIME

    summary["demo_defaults"] = bool(args.demo_defaults)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        _human(summary)

    if summary["stopped"] or summary["counts"]["errors"]:
        return executor.EXIT_RUNTIME
    if summary["paused"]:
        return executor.EXIT_PAUSED
    if not summary["journal"]["ok"]:
        print("ERROR: invalid journal chain — {}".format(summary["journal"]["error"]),
              file=sys.stderr)
        return executor.EXIT_RUNTIME
    return executor.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
