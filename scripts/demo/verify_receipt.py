#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — testnet demo kit: **receipt verification** (B5 §d).

Exact checks (only exact fields of the JSON-RPC receipt; a check that cannot be
mapped to an exact field does not exist here):

======================  =====================================================  ==========================
Check                   Expected value                                         Mismatch code
======================  =====================================================  ==========================
Status                  ``status == 0x1`` (absent ≠ success)                   ``TRANSACTION_FAILED`` / ``RECEIPT_STATUS_MISSING``
Chain                   ``chainId == 84532`` (attached by the caller)          ``CHAIN_ID_*``
Token contract          ``logs[*].address == intent.asset``                    ``TOKEN_CONTRACT_MISMATCH``
Event                   ``topics[0]`` Transfer and **exactly 3 topics**        ``NO_TRANSFER_LOG``
Sender                  ``topics[1]`` == **Safe (avatar)**                     ``SENDER_MISMATCH``
Recipient               ``topics[2]`` == ``intent.recipient``                  ``RECIPIENT_MISMATCH``
Amount                  ``data`` == ``amount_base_units`` (integer)            ``AMOUNT_MISMATCH``
Envelope                ``receipt.to`` == module, ``receipt.from`` == agent    ``WRONG_TARGET`` / ``WRONG_EXECUTOR``
Uniqueness              +1 matching token Transfer log without exact match    ``LOG_COUNT_AMBIGUOUS``
Module                  at least one log emitted by the module (informative)   ``MODULE_EVENT_ABSENT`` (WARN)
======================  =====================================================  ==========================

v1 additions: the **uniqueness** rule (B5 §d.2 — never an optimistic "ok"),
the anti-reorg re-read (``blockNumber`` + ``blockHash`` + 2-block depth,
B5 §c.4) and, on ``status = 0x0``, the **``eth_call`` replay at the receipt block**
to extract the revert data (a failure is a first-class result).

CLI:

    python scripts/demo/verify_receipt.py --receipt receipt.json --intent intent.json \
        --safe 0x… --module 0x… --agent 0x… [--rpc] [--confirmation-blocks 2] [--out report.json]
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

try:
    from . import common
except ImportError:  # direct execution
    _sys_dir = os.path.dirname(os.path.abspath(__file__))
    if _sys_dir not in sys.path:
        sys.path.insert(0, _sys_dir)
    import common  # type: ignore  # noqa: E402

from orvyren.execution import verify as base_verify  # noqa: E402

# v1 additional codes (B5 §d.1) — the existing code's codes stay unchanged.
LOG_COUNT_AMBIGUOUS = "LOG_COUNT_AMBIGUOUS"
WRONG_TARGET = "WRONG_TARGET"
WRONG_EXECUTOR = "WRONG_EXECUTOR"
MODULE_EVENT_ABSENT = "MODULE_EVENT_ABSENT"       # informative (WARN), does not fail the check
REORGED = "REORGED"
RECEIPT_UNAVAILABLE = "RECEIPT_UNAVAILABLE"

EXIT_OK = 0
EXIT_MISMATCH = 1
EXIT_USAGE = 2


def _address(value: Any) -> Optional[str]:
    """Normalized address (lowercase), or None if the value is not an address."""
    if not common.is_address(value):
        return None
    return common.normalize_address(value)


def exact_transfer_matches(receipt: Dict[str, Any], *, token: str, sender: str, recipient: str,
                           amount_base_units: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Token Transfer logs: ``(all, exact matches)``."""
    logs = receipt.get("logs") or []
    token_logs = [log for log in logs if isinstance(log, dict)
                  and base_verify.is_transfer_log(log, token)]
    exact: List[Dict[str, Any]] = []
    for log in token_logs:
        try:
            decoded = base_verify.decode_transfer(log)
        except ValueError:
            continue
        if (decoded["from"] == sender and decoded["to"] == recipient
                and decoded["value_base_units"] == amount_base_units):
            exact.append(decoded)
    return token_logs, exact


def verify_full(receipt: Dict[str, Any], *, intent: Dict[str, Any], safe: str, module: str,
                agent: str, chain_id: int = common.CHAIN_ID_DEMO,
                decimals: int = 6) -> Dict[str, Any]:
    """Full verification of a receipt against the authorized intent (pure function)."""
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be an object")
    safe_n = common.normalize_address(safe, "safe")
    module_n = common.normalize_address(module, "module")
    agent_n = common.normalize_address(agent, "agent")
    token = common.normalize_address(intent.get("asset"), "intent.asset")
    recipient = common.normalize_address(intent.get("recipient"), "intent.recipient")
    amount_base_units = int(intent.get("amount_base_units"))

    expected = {
        "token": token,
        "from": safe_n,
        "to": recipient,
        "amount_usdc": intent.get("amount"),
        "chain_id": chain_id,
        "decimals": decimals,
    }
    base = base_verify.verify_receipt(receipt, expected)
    mismatches: List[str] = list(base["mismatches"])
    warnings: List[str] = []

    token_logs, exact = exact_transfer_matches(receipt, token=token, sender=safe_n,
                                               recipient=recipient, amount_base_units=amount_base_units)
    # Uniqueness rule (B5 §d.2): as soon as there are SEVERAL token Transfer logs and the
    # number of exact matches is not exactly 1, the verification is ambiguous
    # (never an optimistic "ok"). A single token log that does not match = ordinary
    # mismatch (AMOUNT_MISMATCH / RECIPIENT_MISMATCH…), not an ambiguity.
    if len(token_logs) > 1 and len(exact) != 1:
        mismatches.append(LOG_COUNT_AMBIGUOUS)

    receipt_to = _address(receipt.get("to"))
    receipt_from = _address(receipt.get("from"))
    envelope: Dict[str, Any] = {"receipt.to": receipt_to, "receipt.from": receipt_from,
                                "expected_module": module_n, "expected_agent": agent_n}
    if receipt_to is not None and receipt_to != module_n:
        mismatches.append(WRONG_TARGET)
    if receipt_from is not None and receipt_from != agent_n:
        mismatches.append(WRONG_EXECUTOR)

    module_logs = [log for log in (receipt.get("logs") or []) if isinstance(log, dict)
                   and _address(log.get("address")) == module_n]
    if not module_logs:
        warnings.append(MODULE_EVENT_ABSENT)

    return {
        "ok": not mismatches,
        "mismatches": mismatches,
        "warnings": warnings,
        "log_counts": {"token_transfer_logs": len(token_logs), "exact_matches": len(exact)},
        "transfer": base.get("transfer"),
        "expected": base.get("expected"),
        "envelope": envelope,
        "status": receipt.get("status"),
        "block_number": common.hex_to_int(receipt.get("blockNumber")) if receipt.get("blockNumber") else None,
        "block_hash": receipt.get("blockHash"),
        "tx_hash": receipt.get("transactionHash"),
    }


def reorg_check(*, tx_hash: str, receipt_block_number: Optional[int], receipt_block_hash: Optional[str],
                rpc_url: str, confirmation_blocks: int = 2, timeout: int = common.RPC_TIMEOUT_SECONDS) -> Dict[str, Any]:
    """Anti-reorg re-read (B5 §c.4): unchanged block hash + confirmation depth."""
    result: Dict[str, Any] = {"tx_hash": tx_hash, "confirmation_blocks": confirmation_blocks}
    try:
        fresh = common.rpc(rpc_url, "eth_getTransactionReceipt", [tx_hash], timeout)
        head = common.eth_block_number(rpc_url, timeout)
    except Exception as exc:
        result.update({"status": "UNRESOLVED", "code": RECEIPT_UNAVAILABLE, "error": str(exc)})
        return result
    if fresh is None:
        result.update({"status": "REORGED", "code": REORGED,
                       "note": "the receipt has disappeared: probable reorg — re-check P4/P5 before any re-send"})
        return result
    result["block_number"] = common.hex_to_int(fresh.get("blockNumber"))
    result["block_hash"] = fresh.get("blockHash")
    result["confirmations"] = (head - result["block_number"] + 1) if result["block_number"] is not None else None
    if receipt_block_hash and str(fresh.get("blockHash")).lower() != str(receipt_block_hash).lower():
        result.update({"status": "REORGED", "code": REORGED,
                       "note": "blockHash differs from the one recorded"})
        return result
    if receipt_block_number is not None and result["block_number"] != receipt_block_number:
        result.update({"status": "REORGED", "code": REORGED,
                       "note": "block number differs from the one recorded"})
        return result
    if (result["confirmations"] or 0) < int(confirmation_blocks):
        result["status"] = "PENDING_CONFIRMATION"
        return result
    result["status"] = "CONFIRMED"
    return result


def wait_for_confirmations(*, tx_hash: str, receipt_block_number: Optional[int], receipt_block_hash: Optional[str],
                           rpc_url: str, confirmation_blocks: int = 2, timeout_seconds: int = 45,
                           poll_seconds: float = 3.0) -> Dict[str, Any]:
    """Bounded wait: **stable inclusion** = depth ≥ ``confirmation_blocks`` **and**
    ``(block, hash)`` pair unchanged over two consecutive reads.

    The recorded ``receipt_block_hash`` witness may come from a view preceding consensus
    (testnet micro-fork, load-balanced RPC): if it differs but the re-read is stable and
    deep, the state is ``CONFIRMED`` with ``view_updated`` annotated (never a false "reorg").
    ``REORGED`` is reserved for real anomalies: receipt gone, or a different block number.
    Never blocks beyond ``timeout_seconds`` (Base blocks ≈ 2 s); past that, the state
    ``PENDING_CONFIRMATION`` is returned as is.
    """
    import time as _time
    started = _time.monotonic()
    deadline = started + max(0, int(timeout_seconds))
    previous = None
    result: Dict[str, Any] = {}
    while True:
        try:
            fresh = common.rpc(rpc_url, "eth_getTransactionReceipt", [tx_hash])
            head = common.eth_block_number(rpc_url)
        except Exception as exc:
            result = {"status": "UNRESOLVED", "code": RECEIPT_UNAVAILABLE, "error": str(exc)}
        else:
            if fresh is None:
                result = {"status": "REORGED", "code": REORGED,
                          "note": "the receipt has disappeared: probable reorg — re-check P4/P5 before any re-send"}
            else:
                number = common.hex_to_int(fresh.get("blockNumber"))
                block_hash = fresh.get("blockHash")
                confirmations = (head - number + 1) if number is not None else None
                result = {"tx_hash": tx_hash, "confirmation_blocks": confirmation_blocks,
                          "block_number": number, "block_hash": block_hash,
                          "confirmations": confirmations}
                if receipt_block_number is not None and number != receipt_block_number:
                    result.update({"status": "REORGED", "code": REORGED,
                                   "note": "block number differs from the one recorded"})
                elif (confirmations or 0) >= int(confirmation_blocks) and previous == (number, str(block_hash).lower()):
                    result["status"] = "CONFIRMED"
                    if receipt_block_hash and str(block_hash).lower() != str(receipt_block_hash).lower():
                        result["view_updated"] = {
                            "consigned_block_hash": receipt_block_hash, "final_block_hash": block_hash,
                            "note": "initial receipt view differed (testnet micro-fork) — re-read stabilized"}
                else:
                    result["status"] = "PENDING_CONFIRMATION"
                previous = (number, str(block_hash).lower())
        if result.get("status") in ("CONFIRMED", "REORGED"):
            break
        if _time.monotonic() >= deadline:
            break
        _time.sleep(min(poll_seconds, max(0.1, deadline - _time.monotonic())))
    result["waited_seconds"] = round(_time.monotonic() - started, 2)
    return result


def replay_revert(*, rpc_url: str, tx_hash: str, block_number: Optional[int],
                  timeout: int = common.RPC_TIMEOUT_SECONDS, attempts: int = 5,
                  retry_delay: float = 2.0) -> Dict[str, Any]:
    """``eth_call`` replay at the receipt block to extract the revert data (first-class failure).

    **Robust to node lag** (load-balanced RPC): a "block not found" on a just-mined block
    is retried ``attempts`` times; if the node stays behind, the returned state is
    ``REPLAY_UNAVAILABLE`` — never a false "revert" (measured 2026-10-16).
    """
    import time as _time
    try:
        tx = common.rpc(rpc_url, "eth_getTransactionByHash", [tx_hash], timeout)
        if not isinstance(tx, dict):
            return {"status": "TX_UNAVAILABLE"}
        call = {"from": tx.get("from"), "to": tx.get("to"),
                "data": tx.get("input"), "value": tx.get("value")}
        tag = hex(int(block_number)) if block_number is not None else "latest"
        for attempt in range(max(1, int(attempts))):
            try:
                output = common.rpc(rpc_url, "eth_call", [call, tag], timeout)
                return {"status": "NO_REVERT", "output": output}
            except common.chain_client.RpcError as exc:
                message = getattr(exc, "message", "") or ""
                lag = "not found" in message.lower() or "unknown block" in message.lower()
                if lag and attempt < max(1, int(attempts)) - 1:
                    _time.sleep(retry_delay)
                    continue
                if lag:
                    return {"status": "REPLAY_UNAVAILABLE", "error": message,
                            "note": "node behind (block not served) — retry later, not a revert"}
                return {"status": "REVERT", "revert_selector": common.revert_selector(exc.data),
                        "error_message": exc.message, "data": exc.data}
    except Exception as exc:
        return {"status": "REPLAY_FAILED", "error": str(exc)}
    return {"status": "REPLAY_FAILED", "error": "retries exhausted"}


# --- CLI ---------------------------------------------------------------------


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verify_receipt.py",
        description="ORVYREN — verification of an execution receipt against the authorized intent (B5 §d). "
                    "Read-only; no signature.")
    parser.add_argument("--receipt", required=True, help="JSON receipt (eth_getTransactionReceipt)")
    parser.add_argument("--intent", required=True, help="authorized v1 intent (JSON)")
    parser.add_argument("--safe", required=True, help="Safe address (avatar) — expected sender")
    parser.add_argument("--module", required=True, help="Roles module address — expected target (receipt.to)")
    parser.add_argument("--agent", required=True, help="agent address — expected receipt.from")
    parser.add_argument("--chain-id", type=int, default=common.CHAIN_ID_DEMO,
                        help="expected chain (default 84532); the receipt must carry chainId")
    parser.add_argument("--decimals", type=int, default=6, help="token decimals (USDC = 6)")
    parser.add_argument("--confirmation-blocks", type=int, default=2, help="anti-reorg depth (default 2)")
    parser.add_argument("--rpc", action="store_true", help="anti-reorg re-read + revert replay (read-only)")
    parser.add_argument("--rpc-url", default=os.environ.get("ORVYREN_RPC_URL_BASE_SEPOLIA")
                        or common.DEFAULT_RPC_URL)
    parser.add_argument("--out", help="write the JSON report to this path")
    args = parser.parse_args(argv)

    try:
        receipt = common.load_json(args.receipt)
        intent = common.load_json(args.intent)
    except (OSError, ValueError) as exc:
        print("ERROR: unreadable file: {}".format(exc), file=sys.stderr)
        return EXIT_USAGE
    if not isinstance(receipt, dict) or not isinstance(intent, dict):
        print("ERROR: --receipt and --intent must be JSON objects", file=sys.stderr)
        return EXIT_USAGE

    try:
        report = verify_full(receipt, intent=intent, safe=args.safe, module=args.module,
                             agent=args.agent, chain_id=args.chain_id, decimals=args.decimals)
    except ValueError as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return EXIT_USAGE

    if args.rpc:
        tx_hash = report.get("tx_hash")
        if tx_hash:
            report["reorg"] = reorg_check(tx_hash=tx_hash, receipt_block_number=report.get("block_number"),
                                          receipt_block_hash=report.get("block_hash"),
                                          rpc_url=args.rpc_url,
                                          confirmation_blocks=args.confirmation_blocks)
        if str(report.get("status")).lower() in ("0x0", "0"):
            if tx_hash:
                report["revert_replay"] = replay_revert(rpc_url=args.rpc_url, tx_hash=tx_hash,
                                                        block_number=report.get("block_number"))

    if args.out:
        common.write_json(args.out, report)

    status = str(report.get("status"))
    print("ORVYREN — receipt verification {}…: {}".format(
        str(report.get("tx_hash") or "?")[:18], "COMPLIANT" if report["ok"] else "NON-COMPLIANT"))
    print("  on-chain status: {}".format(status))
    print("  token Transfer logs: {} (exact matches: {})".format(
        report["log_counts"]["token_transfer_logs"], report["log_counts"]["exact_matches"]))
    if report.get("transfer"):
        transfer = report["transfer"]
        print("  decoded transfer: {} → {}: {} base units".format(
            common.short_address(transfer["from"]), common.short_address(transfer["to"]),
            transfer["value_base_units"]))
    if report["mismatches"]:
        print("  mismatches: {}".format(", ".join(report["mismatches"])))
    if report["warnings"]:
        print("  warnings: {}".format(", ".join(report["warnings"])))
    if "reorg" in report:
        print("  anti-reorg: {} (depth {})".format(report["reorg"].get("status"),
                                                         report["reorg"].get("confirmations")))
    if "revert_replay" in report:
        print("  revert replay: {}".format(report["revert_replay"]))

    if not report["ok"]:
        return EXIT_MISMATCH
    if report.get("reorg", {}).get("status") == "REORGED":
        return EXIT_MISMATCH
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
