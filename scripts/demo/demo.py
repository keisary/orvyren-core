#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — testnet demo kit: **orchestrator for the 5 runs** (W3-D, B5 §e).

    python scripts/demo/demo.py --run A --dry-run
    python scripts/demo/demo.py --run A --execute --case rseth

Runs (B5 §e, derived from W2C §g):

* **A — ALLOW inside the envelope**: v1 intent ``transfer 50 USDC`` → off-chain
  policy ``ALLOW`` → preflight (12 checks) → signature → receipt →
  verification (B5 §d). Measurable criteria: ``status = 0x1``, **exactly one**
  matching Transfer log, balance deltas ±50 000 000, signature counter = 1, the 7
  journal ``kind`` values, ``blockHash`` stable after 2 blocks.
* **B — off-chain DENY**: B1 150 USDC, B2 unlisted recipient, B3 replay ×3,
  B4 ``change_policy`` → **0 signatures**, nonce unchanged, balances unchanged.
* **C — chain-level DENY**: forbidden calldatas built directly with the agent
  key (C1 allowance, C2 recipient, C3 admin, C4 cumulative, C5 period
  boundary) → expected revert, selector captured, wasted gas recorded.
* **D — timed kill switch**: ``assignRoles(false)`` revocation by the Safe
  (2/3), agent attempt → ``NotAuthorized(address)`` revert;
  ``Roles.roles(AGENT).members(agent) == false``; Reset.
* **E — journal and audit**: chained ``audit.jsonl`` export + ``report.md`` +
  independent verification (re-reading the ``tx_hash`` values) + counters
  ("N compliant executions, M off-chain refusals, K forced attempts refused").

Modes: ``--dry-run`` (default) is an **off-chain rehearsal** — no key is read,
no transaction is sent, placeholder hashes tagged ``simulated``; ``--execute``
really sends (preflight mandatory, one flight at a time).

Outputs: ``<session>/audit.jsonl`` (chained append-only), ``runs/<RUN>_<ts>/``
(summary, criteria, intent, reports), ``receipts/``, ``export/`` (run E).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    from . import calls, common, intents, preflight as preflight_mod, signer as signer_mod, verify_receipt
except ImportError:  # direct execution: python scripts/demo/demo.py
    _sys_dir = os.path.dirname(os.path.abspath(__file__))
    if _sys_dir not in sys.path:
        sys.path.insert(0, _sys_dir)
    import calls  # type: ignore  # noqa: E402
    import common  # type: ignore  # noqa: E402
    import intents  # type: ignore  # noqa: E402
    import preflight as preflight_mod  # type: ignore  # noqa: E402
    import signer as signer_mod  # type: ignore  # noqa: E402
    import verify_receipt  # type: ignore  # noqa: E402

MODE_DRY = "dry-run"
MODE_EXECUTE = "execute"

RUNS = ("A", "B", "C", "D", "E")

DEFAULT_RECIPIENT_AMOUNT = "100.0"     # RUN A: 100 USDC — FROZEN decision (FREEZE_V2 E2).
RUN_A_AMOUNT = DEFAULT_RECIPIENT_AMOUNT
RUN_D_AMOUNT = "100.0"                  # RUN D (B5 §e.4)
#: Note: study B5 §e.1 says 50 USDC and leaves the question open (B5 Q2 §f);
#: the authority is FREEZE_V2 (E2 = 100 USDC) — the kit applies the freeze, and `--amount`
#: lets the variant be replayed if the team decides otherwise.

EXIT_OK = 0
EXIT_CRITERIA_FAILED = 1
EXIT_USAGE = 2
EXIT_PREREQUISITES = 3
EXIT_CONFIG = 4

#: Placeholders from the example file (replaced on demo day; ``--execute`` refuses them).
PLACEHOLDER_ADDRESSES = {
    "0x2222222222222222222222222222222222222222",
    "0x3333333333333333333333333333333333333333",
    "0x4444444444444444444444444444444444444444",
    "0x5555555555555555555555555555555555555555",
    "0x9999999999999999999999999999999999999999",
    "0x1111111111111111111111111111111111111111",
}

GAS_LIMIT_DEFAULT = 120_000            # upper bound for the tx through the module (measured on demo day)


def _short(address: Any) -> str:
    return common.short_address(address)


def _now_iso() -> str:
    return common.utc_now()


class DemoContext:
    """Shared state of a demo session (journal, registry, addresses)."""

    def __init__(self, *, case: str, mode: str, session_dir: str,
                 env_file: Optional[str] = None, policy_path: Optional[str] = None,
                 envelope_path: Optional[str] = None, rpc_url: Optional[str] = None,
                 quiet: bool = False):
        self.case = case
        self.mode = mode
        self.session_dir = os.path.abspath(session_dir)
        self.env_file = env_file
        self.envelope_path = envelope_path
        self.quiet = quiet

        self.session_config = common.SessionConfig.from_env(env_file)
        self.rpc_url = rpc_url or self.session_config.rpc_url
        recipients = {label: address for label, address in self.session_config.recipients.items() if address}
        self.policy = common.load_policy_reference(policy_path, recipients)
        self.envelope = common.load_json(envelope_path) if envelope_path else None

        os.makedirs(self.session_dir, exist_ok=True)
        self.session = common.ensure_session_dir(
            self.session_dir, episode=case,
            mode=common.JOURNAL_MODE_DRY_RUN if mode == MODE_DRY else common.JOURNAL_MODE_LIVE,
            policy=self.policy)
        self.run_id = self.session["run_id"]
        self.journal = common.Journal(
            os.path.join(self.session_dir, "audit.jsonl"), run_id=self.run_id, episode=case,
            mode=common.JOURNAL_MODE_DRY_RUN if mode == MODE_DRY else common.JOURNAL_MODE_LIVE)
        self.registry = common.Registry(os.path.join(self.session_dir, "intent_registry.json"))
        self.signatures = common.SignatureLog(os.path.join(self.session_dir, "signatures.jsonl"))
        self.pause = common.PauseFlag(os.path.join(self.session_dir, "PAUSED"), env=self.session_config.env)
        self.run_dir = os.path.join(
            self.session_dir, "runs",
            "{}_{}Z_{}".format(case, time.strftime("%Y%m%dT%H%M%S", time.gmtime()), common.ulid()[-6:]))
        os.makedirs(self.run_dir, exist_ok=True)
        self.receipts_dir = os.path.join(self.session_dir, "receipts")
        os.makedirs(self.receipts_dir, exist_ok=True)
        self.placeholders_used: List[str] = []
        self.addresses = self._addresses()
        self.signer = signer_mod.Signer(rpc_url=self.rpc_url, chain_id=self.policy.chain_id,
                                        dry_run=(mode == MODE_DRY), signature_log=self.signatures,
                                        env=self.session_config.env)

    # --- addresses ------------------------------------------------------------

    def _addresses(self) -> Dict[str, str]:
        env = self.session_config.env
        keys = {
            "safe": "ORVYREN_SAFE_ADDRESS",
            "agent": "ORVYREN_AGENT_ADDRESS",
            "module": "ORVYREN_MODULE_ADDRESS",
            "asset": "ORVYREN_USDC_ADDRESS",
            "B": "ORVYREN_RECIPIENT_B",
            "C": "ORVYREN_RECIPIENT_C",
            "D_unlisted": "ORVYREN_RECIPIENT_UNLISTED",
        }
        addresses: Dict[str, str] = {}
        fallbacks = {
            "safe": "0x2222222222222222222222222222222222222222",
            "agent": "0x3333333333333333333333333333333333333333",
            "module": "0x4444444444444444444444444444444444444444",
            "asset": common.ALLOWED_ASSET,
            "B": "0x1111111111111111111111111111111111111111",
            "C": "0x5555555555555555555555555555555555555555",
            "D_unlisted": "0x9999999999999999999999999999999999999999",
        }
        for label, key in keys.items():
            value = (env.get(key) or "").strip()
            if value:
                addresses[label] = common.normalize_address(value, key)
                if addresses[label] in PLACEHOLDER_ADDRESSES:
                    self.placeholders_used.append(label)
            else:
                if self.mode == MODE_EXECUTE:
                    raise common.ConfigurationError(
                        "{} is missing — --execute requires a complete configuration (.env)".format(key))
                addresses[label] = common.normalize_address(fallbacks[label], key)
                self.placeholders_used.append(label)
        self.policy.recipients.setdefault("B", addresses["B"])
        self.policy.recipients.setdefault("C", addresses["C"])
        return addresses

    def require_execute_prerequisites(self) -> None:
        """--execute: real addresses, signing library, key present."""
        if self.mode != MODE_EXECUTE:
            return
        # Chain guard first: the demo is testnet only (Base Sepolia, 84532).
        if os.environ.get("ORVYREN_ALLOW_MAINNET") == "1":
            raise common.ConfigurationError(
                "safety guard: ORVYREN_ALLOW_MAINNET=1 is set — the demo is testnet only "
                "(Base Sepolia, 84532). Remove the variable.")
        if self.placeholders_used:
            raise common.ConfigurationError(
                "--execute refuses placeholder addresses ({}): fill the .env with the session's "
                "real addresses (FREEZE_V2 J2)".format(", ".join(sorted(set(self.placeholders_used)))))
        if not self.signer.library_available():
            raise signer_mod.SignerDependencyError(
                "real signing requires eth-account — python -m pip install eth-account")
        if not self.signer.key_present():
            raise signer_mod.SignerError(
                "{} is missing: --execute mode refuses to start without a key (it only lives in "
                "the signer's environment)".format(signer_mod.KEY_ENV_NAME))

    # --- journal ---------------------------------------------------------------

    def log(self, message: str) -> None:
        if not self.quiet:
            print("  {}".format(message))

    def journal_run_start(self, run: str, extra: Optional[Dict[str, Any]] = None) -> None:
        payload = {
            "run": run,
            "case": self.case,
            "session_dir": common.display_path(self.session_dir),
            "placeholders": sorted(set(self.placeholders_used)),
            "signatures_at_start": self.signatures.count(),
            "journal_records_at_start": self.journal.count(),
        }
        if extra:
            payload.update(extra)
        self.journal.append("RUN_START", payload=payload, refs={"run": run})

    def journal_intent(self, intent: Dict[str, Any], run: str) -> None:
        self.journal.append("INTENT", payload=intents.intent_summary(intent),
                            refs={"intent_id": intent["intent_id"], "run": run})

    def journal_policy(self, decision: Dict[str, Any], intent: Optional[Dict[str, Any]], run: str) -> None:
        self.journal.append(
            "POLICY",
            payload={key: value for key, value in decision.items() if key != "rules_evaluated"}
                    | {"rules_evaluated": decision.get("rules_evaluated")},
            refs={"intent_id": (intent or {}).get("intent_id"), "run": run})

    def journal_outcome(self, *, run: str, intent: Optional[Dict[str, Any]], outcome: str,
                        detail: Optional[Dict[str, Any]] = None) -> None:
        self.journal.append("OUTCOME", payload={"outcome": outcome, **(detail or {})},
                            refs={"intent_id": (intent or {}).get("intent_id"), "run": run})

    # --- steps ----------------------------------------------------------------

    def build_transfer(self, *, amount: str, recipient_label: str, justification: str,
                       source: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return intents.build_transfer_intent(
            chain_id=self.policy.chain_id,
            account=self.addresses["safe"],
            asset=self.addresses["asset"],
            amount=amount,
            recipient=self.addresses[recipient_label],
            expiry_minutes=self.policy.ttl_intent_minutes,
            decimals=self.policy.asset_decimals,
            justification=justification,
            policy_version=self.policy.version,
            source=source)

    def build_action(self, *, action: str, justification: str, amount: str = "1.0",
                     recipient_label: Optional[str] = None) -> Dict[str, Any]:
        """Intent for an action under approval: the recipient stays an AUTHORIZED ADDRESS
        so the request reaches the action-scope rule (R8) — same as the repository's I3
        (``change_policy`` moves no funds; the recipient only serves to satisfy R3)."""
        return intents.build_action_intent(
            action=action,
            chain_id=self.policy.chain_id,
            account=self.addresses["safe"],
            asset=self.addresses["asset"],
            amount=amount,
            recipient=self.addresses[recipient_label or "B"],
            expiry_minutes=self.policy.ttl_intent_minutes,
            decimals=self.policy.asset_decimals,
            justification=justification,
            policy_version=self.policy.version,
            source={"decision_id": common.ulid()})

    def run_preflight(self, intent: Optional[Dict[str, Any]] = None, name: str = "preflight",
                      extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        runner = preflight_mod.PreflightRunner(
            policy=self.policy, intent=intent, envelope=self.envelope,
            mode=preflight_mod.MODE_RPC if self.mode == MODE_EXECUTE else preflight_mod.MODE_OFFLINE,
            registry=self.registry, pause=self.pause,
            agent=self.addresses["agent"], safe=self.addresses["safe"],
            module=self.addresses["module"], asset=self.addresses["asset"],
            rpc_url=self.rpc_url, chain_id=self.policy.chain_id)
        report = runner.run()
        common.write_json(os.path.join(self.run_dir, "{}.json".format(name)), report)
        self.journal.append("SIMULATION",
                            payload={"preflight_verdict": report["verdict"],
                                     "safe_mode": report["safe_mode"],
                                     "checks": {check["id"]: check["status"] for check in report["checks"]},
                                     **(extra or {})},
                            refs={"intent_id": (intent or {}).get("intent_id")})
        return report

    def execute_tx(self, intent: Dict[str, Any], *, inner_data: Optional[str] = None,
                   target_label: str = "asset", value: int = 0, wait_receipt: bool = True,
                   timeout: int = 180) -> Dict[str, Any]:
        """Signs (real mode) and broadcasts the transaction going through the module, waits for the receipt.

        In dry-run: simulated signature, placeholder hash, **nothing sent**.
        """
        inner = inner_data if inner_data is not None else calls.erc20_transfer_data(
            intent["recipient"], int(intent["amount_base_units"]))
        call = calls.exec_with_role_data(target=self.addresses[target_label], value=value,
                                         inner_data=inner, operation=calls.OPERATION_CALL,
                                         role_key=self.policy.role_key)
        nonce = 0
        gas = GAS_LIMIT_DEFAULT
        fees = int(preflight_mod.GAS_PRICE_BASELINE_WEI)
        if self.mode == MODE_EXECUTE:
            nonce = common.eth_get_transaction_count(self.rpc_url, self.addresses["agent"], "pending")
            try:
                gas = int(preflight_mod.GAS_LIMIT_FACTOR * common.eth_estimate_gas(
                    self.rpc_url, self.addresses["agent"], self.addresses["module"], call))
            except Exception:
                gas = GAS_LIMIT_DEFAULT
            try:
                fees = common.eth_gas_price(self.rpc_url)
            except Exception:
                fees = preflight_mod.GAS_PRICE_BASELINE_WEI
        tx = calls.demo_exec_transaction(module=self.addresses["module"], agent=self.addresses["agent"],
                                         chain_id=self.policy.chain_id, nonce=nonce, gas=gas,
                                         max_fee_per_gas=fees * 2, max_priority_fee_per_gas=fees,
                                         inner_data=inner, asset=self.addresses["asset"],
                                         role_key=self.policy.role_key)
        signed = self.signer.sign_transaction(tx, intent_id=intent["intent_id"])
        self.journal.append("SUBMIT",
                            payload={"tx_hash": signed["tx_hash"], "simulated": signed["simulated"],
                                     "nonce": nonce, "gas": gas, "max_fee_per_gas": fees * 2,
                                     "max_priority_fee_per_gas": fees, "to": self.addresses["module"],
                                     "signatures_count": self.signatures.count(),
                                     "key_material": "never recorded"},
                            refs={"intent_id": intent["intent_id"]})
        if self.mode == MODE_DRY or not signed.get("signed_transaction"):
            return {"mode": signed["mode"], "tx_hash": signed["tx_hash"], "simulated": True,
                    "sent": False, "nonce": nonce, "gas": gas}
        tx_hash = self.signer.send_raw_transaction(signed["signed_transaction"])
        receipt = None
        if wait_receipt:
            deadline = time.time() + timeout
            while time.time() < deadline:
                receipt = common.rpc(self.rpc_url, "eth_getTransactionReceipt", [tx_hash])
                if receipt is not None:
                    break
                time.sleep(2)
        return {"mode": "execute", "tx_hash": tx_hash, "simulated": False, "sent": True,
                "nonce": nonce, "gas": gas, "receipt": receipt, "raw_signed": signed["signed_transaction"]}

    def execute_raw_tx(self, intent: Dict[str, Any], *, to: str, data: str,
                       wait_receipt: bool = True, timeout: int = 90) -> Dict[str, Any]:
        """**Raw** submission (without the ``exec_with_role`` envelope) — case C3: the agent attempts
        a direct administrative action; the contract must reject it (``onlyOwner`` / ``GS*``)."""
        nonce = 0
        gas = GAS_LIMIT_DEFAULT
        fees = int(preflight_mod.GAS_PRICE_BASELINE_WEI)
        if self.mode == MODE_EXECUTE:
            nonce = common.eth_get_transaction_count(self.rpc_url, self.addresses["agent"], "pending")
            try:
                gas = int(preflight_mod.GAS_LIMIT_FACTOR * common.eth_estimate_gas(
                    self.rpc_url, self.addresses["agent"], to, data))
            except Exception:
                gas = GAS_LIMIT_DEFAULT
            try:
                fees = common.eth_gas_price(self.rpc_url)
            except Exception:
                fees = preflight_mod.GAS_PRICE_BASELINE_WEI
        tx = {"chainId": self.policy.chain_id, "nonce": nonce, "to": common.normalize_address(to, "to"),
              "value": 0, "data": data, "gas": gas, "maxFeePerGas": fees * 2,
              "maxPriorityFeePerGas": fees, "type": 2,
              "from": common.normalize_address(self.addresses["agent"], "agent")}
        signed = self.signer.sign_transaction(tx, intent_id=intent["intent_id"])
        self.journal.append("SUBMIT",
                            payload={"tx_hash": signed["tx_hash"], "simulated": signed["simulated"],
                                     "nonce": nonce, "gas": gas, "raw": True, "to": to,
                                     "signatures_count": self.signatures.count(),
                                     "key_material": "never recorded"},
                            refs={"intent_id": intent["intent_id"]})
        if self.mode == MODE_DRY or not signed.get("signed_transaction"):
            return {"mode": signed["mode"], "tx_hash": signed["tx_hash"], "simulated": True,
                    "sent": False, "nonce": nonce, "gas": gas}
        tx_hash = self.signer.send_raw_transaction(signed["signed_transaction"])
        receipt = None
        if wait_receipt:
            deadline = time.time() + timeout
            while time.time() < deadline:
                receipt = common.rpc(self.rpc_url, "eth_getTransactionReceipt", [tx_hash])
                if receipt is not None:
                    break
                time.sleep(2)
        return {"mode": "execute", "tx_hash": tx_hash, "simulated": False, "sent": True,
                "nonce": nonce, "gas": gas, "receipt": receipt, "raw_signed": signed["signed_transaction"]}

    def journal_receipt(self, intent: Dict[str, Any], receipt: Dict[str, Any], run: str) -> Dict[str, Any]:
        """Persists the raw receipt + the RECEIPT entry (receipt_sha256, rule B6 M4)."""
        enriched = dict(receipt)
        if "chainId" not in enriched:
            enriched["chainId"] = hex(self.policy.chain_id)
        path = os.path.join(self.receipts_dir, "{}.json".format(str(receipt.get("transactionHash")).lower()))
        common.write_json(path, enriched)
        digest = common.sha256_hex(json.dumps(enriched, sort_keys=True).encode("utf-8"))
        self.journal.append("RECEIPT",
                            payload={"tx_hash": enriched.get("transactionHash"),
                                     "status": enriched.get("status"),
                                     "block_number": common.hex_to_int(enriched.get("blockNumber")) if enriched.get("blockNumber") else None,
                                     "block_hash": enriched.get("blockHash"),
                                     "gas_used": common.hex_to_int(enriched.get("gasUsed")) if enriched.get("gasUsed") else None,
                                     "effective_gas_price": common.hex_to_int(enriched.get("effectiveGasPrice")) if enriched.get("effectiveGasPrice") else None,
                                     "receipt_sha256": digest, "raw_ref": common.display_path(path, self.session_dir)},
                            refs={"intent_id": intent["intent_id"], "run": run})
        return {"receipt_sha256": digest, "raw_ref": path}

    def _submit_count(self) -> int:
        """Number of SUBMIT entries in the session journal (criterion B.3)."""
        try:
            return len([record for record in common.read_jsonl(os.path.join(self.session_dir, "audit.jsonl"))
                        if record.get("kind") == "SUBMIT"])
        except ValueError:
            return 0

    def balances(self) -> Optional[Dict[str, Any]]:
        if self.mode != MODE_EXECUTE:
            return None
        safe = self.balance_of(self.addresses["safe"])
        recipient = self.balance_of(self.addresses["B"])
        if safe is None or recipient is None:
            return None
        return {"safe_usdc": safe, "recipient_usdc": recipient}

    def balance_of(self, holder: str) -> Optional[int]:
        if self.mode != MODE_EXECUTE:
            return None
        try:
            return calls.decode_uint_result(common.eth_call(
                self.rpc_url, self.addresses["asset"], calls.balance_of_data(holder)))
        except Exception:
            return None


def _criterion(cid: str, description: str, status: str, detail: Any = None) -> Dict[str, Any]:
    return {"id": cid, "description": description, "status": status, "detail": detail}


def _write_run_artifacts(ctx: DemoContext, run: str, summary: Dict[str, Any],
                         criteria: List[Dict[str, Any]]) -> None:
    common.write_json(os.path.join(ctx.run_dir, "summary.json"), summary)
    common.write_json(os.path.join(ctx.run_dir, "criteria.json"), {"run": run, "criteria": criteria})
    print("")
    print("  criteria ({}):".format(run))
    for criterion in criteria:
        print("    [{:>12}] {} — {}".format(criterion["status"], criterion["id"], criterion["description"]))


def _criteria_counts(criteria: List[Dict[str, Any]]) -> Dict[str, int]:
    """Counts the ``met`` / ``pending`` / ``failed`` statuses (and unknown ones)."""
    statuses = [str(criterion.get("status") or "") for criterion in criteria]
    met = statuses.count("met")
    pending = statuses.count("pending")
    failed = statuses.count("failed")
    return {"met": met, "pending": pending, "failed": failed,
            "other": len(statuses) - met - pending - failed}


def _criteria_ok(criteria: List[Dict[str, Any]]) -> bool:
    """True **only** if every criterion is ``met``.

    ``pending`` is not a success: an unevaluated criterion (dry-run) leaves
    a missing proof. The kit declares it (``DRY_RUN_PENDING``) instead of
    claiming "criteria OK" — finding E1 of the external audit of 17/10.
    """
    return bool(criteria) and all(str(criterion.get("status")) == "met"
                                  for criterion in criteria)


def _criteria_label(criteria: List[Dict[str, Any]]) -> str:
    """Honest label: OK only if everything is ``met``; otherwise PENDING/FAILED."""
    counts = _criteria_counts(criteria)
    if not criteria or counts["failed"] or counts["other"]:
        return "CRITERIA NOT MET"
    if counts["pending"]:
        return "DRY_RUN_PENDING"
    return "criteria OK"


# =============================================================================
# RUN A
# =============================================================================

def run_a(ctx: DemoContext, amount: str = RUN_A_AMOUNT) -> Dict[str, Any]:
    """RUN A — ALLOW inside the envelope (both locks say yes)."""
    ctx.journal_run_start("A")
    signatures_before = ctx.signatures.count()
    intent = ctx.build_transfer(amount=amount, recipient_label="B",
                                justification="RUN A — {} USDC transfer inside the envelope (ALLOW)".format(amount),
                                source={"decision_id": common.ulid(), "case": ctx.case})
    common.write_json(os.path.join(ctx.run_dir, "intent.json"), intent)
    ctx.journal_intent(intent, "A")

    decision = common.evaluate_policy(intent, ctx.policy, seen_intent_ids=ctx.registry.seen_intent_ids())
    payload = common.decision_as_dict(decision, intent=intent, policy=ctx.policy,
                                      context={"placeholders": sorted(set(ctx.placeholders_used))})
    ctx.journal_policy(payload, intent, "A")
    ctx.log("policy verdict: {} {}".format(decision.verdict, decision.reasons or ""))

    criteria: List[Dict[str, Any]] = []
    summary: Dict[str, Any] = {"run": "A", "mode": ctx.mode, "intent_id": intent["intent_id"],
                               "verdict": decision.verdict, "policy": payload,
                               "expected": {"receipt_status": "0x1", "transfer_base_units": int(intent["amount_base_units"])}}

    if decision.verdict != "ALLOW":
        ctx.journal_outcome(run="A", intent=intent, outcome="REFUSED_BY_POLICY",
                            detail={"reasons": decision.reasons})
        summary["status"] = "REFUSED_BY_POLICY"
        _write_run_artifacts(ctx, "A", summary, [_criterion("A.policy", "verdict ALLOW", "failed", decision.reasons)])
        return summary

    # Preflight precedes reservation: the idempotency registry must not
    # see this run's intent before P1/P4 have evaluated it (B5 §c.1).
    report = ctx.run_preflight(intent, name="preflight")
    if ctx.mode == MODE_EXECUTE and (report["verdict"] == "FAIL" or report["safe_mode"]):
        ctx.journal_outcome(run="A", intent=intent, outcome="REFUSED_BY_PREFLIGHT",
                            detail={"verdict": report["verdict"], "safe_mode_reasons": report["safe_mode_reasons"]})
        summary["status"] = "REFUSED_BY_PREFLIGHT"
        summary["preflight_verdict"] = report["verdict"]
        criteria.append(_criterion("A.1", "receipt.status == 0x1", "failed", "preflight refused"))
        _write_run_artifacts(ctx, "A", summary, criteria)
        return summary

    ctx.registry.record(intent_id=intent["intent_id"], idempotency_key=intent["idempotency_key"],
                        status="RESERVED", note="run A — preflight passed, signature imminent")

    balances_before = {"safe": ctx.balance_of(ctx.addresses["safe"]),
                       "B": ctx.balance_of(ctx.addresses["B"])} if ctx.mode == MODE_EXECUTE else None

    sent = ctx.execute_tx(intent)
    summary["tx"] = {key: value for key, value in sent.items() if key != "receipt"}
    ctx.log("transaction: {} (simulated={}, sent={})".format(sent["tx_hash"][:18] + "…",
                                                               sent["simulated"], sent["sent"]))

    receipt = sent.get("receipt")
    verification = None
    reorg = None
    if receipt is not None:
        ctx.journal_receipt(intent, receipt, "A")
        enriched = dict(receipt)
        enriched.setdefault("chainId", hex(ctx.policy.chain_id))
        verification = verify_receipt.verify_full(enriched, intent=intent, safe=ctx.addresses["safe"],
                                                  module=ctx.addresses["module"], agent=ctx.addresses["agent"],
                                                  chain_id=ctx.policy.chain_id,
                                                  decimals=ctx.policy.asset_decimals)
        reorg = verify_receipt.wait_for_confirmations(
            tx_hash=str(enriched.get("transactionHash")), receipt_block_number=verification["block_number"],
            receipt_block_hash=verification["block_hash"], rpc_url=ctx.rpc_url,
            confirmation_blocks=2)
        ctx.journal.append("VERIFY", payload={"ok": verification["ok"],
                                              "mismatches": verification["mismatches"],
                                              "warnings": verification["warnings"],
                                              "log_counts": verification["log_counts"],
                                              "reorg_status": reorg.get("status")},
                           refs={"intent_id": intent["intent_id"], "run": "A"})

    balances_after = {"safe": ctx.balance_of(ctx.addresses["safe"]),
                      "B": ctx.balance_of(ctx.addresses["B"])} if ctx.mode == MODE_EXECUTE else None
    delta_ok = None
    if balances_before and balances_after and None not in list(balances_before.values()) + list(balances_after.values()):
        amount = int(intent["amount_base_units"])
        delta_ok = (balances_before["safe"] - balances_after["safe"] == amount
                    and balances_after["B"] - balances_before["B"] == amount)
    signatures_after = ctx.signatures.count()

    # OUTCOME is journaled BEFORE the criteria are evaluated: A.5 counts the 7 kind
    # values, OUTCOME included — the old order (OUTCOME after evaluation) missed it
    # systematically under --execute (measured 2026-10-16).
    if ctx.mode == MODE_DRY:
        ctx.journal_outcome(run="A", intent=intent, outcome="DRY_RUN_SIMULATED",
                            detail={"note": "no transaction sent — placeholder hash; "
                                            "criteria 1/2/3/6 will be measured under --execute"})
        summary["status"] = "DRY_RUN_OK"
    else:
        outcome = "VERIFIED_OK" if (verification and verification["ok"]) else "EXECUTION_FAILED"
        ctx.journal_outcome(run="A", intent=intent, outcome=outcome,
                            detail={"ok": bool(verification and verification["ok"])})
        summary["status"] = outcome

    kinds = ctx.journal.kinds(intent["intent_id"])
    required_kinds = ["INTENT", "POLICY", "SIMULATION", "SUBMIT", "RECEIPT", "VERIFY", "OUTCOME"]

    units = int(intent["amount_base_units"])
    criteria = [
        _criterion("A.1", "receipt.status == 0x1", "met" if (verification and verification["ok"]) else "pending",
                   verification and verification["mismatches"]),
        _criterion("A.2", "exactly one exactly matching Transfer log",
                   "met" if (verification and verification["log_counts"]["exact_matches"] == 1) else "pending",
                   verification and verification["log_counts"]),
        _criterion("A.3", "Δ Safe balance = −{} and Δ B balance = +{}".format(units, units),
                   "met" if delta_ok else "pending",
                   {"before": balances_before, "after": balances_after}),
        _criterion("A.4", "signature counter = +1 (simulated ones included in dry-run)",
                   "met" if signatures_after - signatures_before == 1 else "failed",
                   {"before": signatures_before, "after": signatures_after}),
        _criterion("A.5", "the 7 journal kind values present for intent_id",
                   "met" if all(kind in kinds for kind in required_kinds) else
                   ("pending" if ctx.mode == MODE_DRY else "failed"), sorted(set(kinds))),
        _criterion("A.6", "blockHash stable after 2 blocks",
                   "met" if (reorg and reorg.get("status") == "CONFIRMED") else "pending",
                   reorg),
    ]
    _write_run_artifacts(ctx, "A", summary, criteria)
    summary["criteria"] = criteria
    return summary


# =============================================================================
# RUN B
# =============================================================================

def _find_registered_intent(ctx: DemoContext) -> Optional[Dict[str, Any]]:
    """Intent already recorded in the session (for the B3 replay), else None."""
    runs_dir = os.path.join(ctx.session_dir, "runs")
    if not os.path.isdir(runs_dir):
        return None
    candidates = []
    for name in sorted(os.listdir(runs_dir)):
        path = os.path.join(runs_dir, name, "intent.json")
        if os.path.isfile(path):
            candidates.append(path)
    for path in reversed(candidates):
        data = common.load_json(path)
        if isinstance(data, dict) and data.get("idempotency_key") in (ctx.registry.as_dict()["keys"] or []):
            return data
    for path in reversed(candidates):
        data = common.load_json(path)
        if isinstance(data, dict):
            return data
    return None


def run_b(ctx: DemoContext) -> Dict[str, Any]:
    """RUN B — DENY by the off-chain policy (the LLM proposes, the system refuses)."""
    ctx.journal_run_start("B")
    signatures_before = ctx.signatures.count()
    submits_before = ctx._submit_count()
    nonce_before = None
    if ctx.mode == MODE_EXECUTE:
        try:
            nonce_before = common.eth_get_transaction_count(ctx.rpc_url, ctx.addresses["agent"], "pending")
        except Exception:
            nonce_before = None

    cases: List[Dict[str, Any]] = []
    registered = _find_registered_intent(ctx)
    if registered is None:
        registered = ctx.build_transfer(amount="20.0", recipient_label="B",
                                        justification="RUN B3 — reference intent recorded (replay)")
        ctx.registry.record(intent_id=registered["intent_id"],
                            idempotency_key=registered["idempotency_key"],
                            status="REJECTED_DRY_RUN", note="B3 reference")
    else:
        ctx.registry.record(intent_id=registered["intent_id"],
                            idempotency_key=registered["idempotency_key"],
                            status="REGISTERED", note="B3 replay (already recorded)")

    definitions = [
        ("B1", "transfer 150 USDC (per-transaction cap)",
         ctx.build_transfer(amount="150.0", recipient_label="B",
                            justification="RUN B1 — 150 USDC: above the per-transaction cap"),
         ["AMOUNT_ABOVE_TX_CAP"], "DENY"),
        ("B2", "unlisted recipient (20 USDC)",
         ctx.build_transfer(amount="20.0", recipient_label="D_unlisted",
                            justification="RUN B2 — recipient outside the allowlist (attack #12)"),
         ["RECIPIENT_NOT_ALLOWED"], "DENY"),
        ("B3", "replay of the same intent (×3, idempotency)",
         registered, ["INTENT_ALREADY_PROCESSED"], "DENY"),
        ("B4", "change_policy (never autonomous)",
         ctx.build_action(action="change_policy",
                          justification="RUN B4 — the agent attempts to modify its own envelope", amount="100.0"),
         ["ACTION_NEEDS_HUMAN_APPROVAL"], "REQUIRE_APPROVAL"),
    ]

    criteria: List[Dict[str, Any]] = []
    for case_id, label, intent, expected_codes, expected_verdict in definitions:
        repeats = 3 if case_id == "B3" else 1
        for attempt in range(1, repeats + 1):
            decision = common.evaluate_policy(intent, ctx.policy, seen_intent_ids=ctx.registry.seen_intent_ids())
            payload = common.decision_as_dict(decision, intent=intent, policy=ctx.policy)
            ctx.journal.append("POLICY", payload=payload,
                               refs={"intent_id": intent["intent_id"], "run": "B", "case": case_id,
                                     "attempt": attempt})
            ok_verdict = decision.verdict == expected_verdict
            ok_codes = all(code in decision.reasons for code in expected_codes)
            cases.append({"case": case_id, "attempt": attempt, "label": label,
                          "verdict": decision.verdict, "reasons": decision.reasons,
                          "expected_verdict": expected_verdict, "expected_codes": expected_codes,
                          "ok": ok_verdict and ok_codes})
            ctx.log("{} (attempt {}): {} {}".format(case_id, attempt, decision.verdict, decision.reasons))
        ctx.journal_outcome(run="B", intent=intent, outcome="DENIED_OFFCHAIN",
                            detail={"case": case_id, "expected": expected_codes})
        if case_id == "B4":
            ctx.registry.record(intent_id=intent["intent_id"], idempotency_key=intent["idempotency_key"],
                                status="REQUIRE_APPROVAL", note="change_policy")

    signatures_after = ctx.signatures.count()
    nonce_after = None
    if ctx.mode == MODE_EXECUTE:
        try:
            nonce_after = common.eth_get_transaction_count(ctx.rpc_url, ctx.addresses["agent"], "pending")
        except Exception:
            nonce_after = None

    submits_after = ctx._submit_count()
    any_tx_hash = submits_after != submits_before
    b_intent_ids = sorted({definition[2]["intent_id"] for definition in definitions})

    criteria = [
        _criterion("B.1", "signature counter unchanged across the whole run",
                   "met" if signatures_after == signatures_before else "failed",
                   {"before": signatures_before, "after": signatures_after}),
        _criterion("B.2", "agent nonce unchanged",
                   "met" if (nonce_before == nonce_after) else ("pending" if nonce_before is None else "failed"),
                   {"before": nonce_before, "after": nonce_after}),
        _criterion("B.3", "no tx_hash emitted during the run (no SUBMIT)",
                   "met" if not any_tx_hash else "failed",
                   {"submits_before": submits_before, "submits_after": submits_after,
                    "intents_du_run": b_intent_ids}),
        _criterion("B.4", "4 cases B1-B4 with exact verdicts and codes",
                   "met" if all(case["ok"] for case in cases) else "failed", cases),
    ]
    if ctx.mode == MODE_DRY:
        ctx.journal_outcome(run="B", intent=None, outcome="DRY_RUN_OK",
                            detail={"note": "off-chain refusals executed offline (deterministic)"})
    summary = {"run": "B", "mode": ctx.mode, "cases": cases, "status": "DRY_RUN_OK" if ctx.mode == MODE_DRY else "DENIED",
               "signatures_before": signatures_before, "signatures_after": signatures_after,
               "nonce_before": nonce_before, "nonce_after": nonce_after}
    _write_run_artifacts(ctx, "B", summary, criteria)
    summary["criteria"] = criteria
    return summary


# =============================================================================
# RUN C
# =============================================================================

def _c_for(ctx: DemoContext) -> Dict[str, Any]:
    """Builds the forbidden calldatas (C1-C5) — same builders as the nominal path."""
    asset = ctx.addresses["asset"]
    agent = ctx.addresses["agent"]
    role = ctx.policy.role_key
    allow_refill = ctx.policy.allowance_max_refill
    return {
        "C1": {
            "label": "transfer 500 USDC through the module (above the maxRefill allowance)",
            "call": {"to": ctx.addresses["module"],
                     "data": calls.exec_with_role_data(
                         target=asset, value=0,
                         inner_data=calls.erc20_transfer_data(ctx.addresses["B"], 500_000_000),
                         operation=calls.OPERATION_CALL, role_key=role)},
            "expect": "revert (allowance exceeded); tx included with status 0x0, gas wasted",
            "offline_checks": [
                ("amount 500 000 000 > maxRefill {}".format(allow_refill), 500_000_000 > allow_refill),
            ],
            "revert_expect": ["AllowanceExceeded", "0x"],
        },
        "C2": {
            "label": "transfer 1 USDC to an unlisted recipient through the module",
            "call": {"to": ctx.addresses["module"],
                     "data": calls.exec_with_role_data(
                         target=asset, value=0,
                         inner_data=calls.erc20_transfer_data(ctx.addresses["D_unlisted"], 1_000_000),
                         operation=calls.OPERATION_CALL, role_key=role)},
            "expect": "revert (recipient condition); no Transfer log",
            "offline_checks": [
                ("recipient outside the allowlist",
                 ctx.addresses["D_unlisted"] not in ctx.policy.allowed_recipients()),
            ],
            "revert_expect": ["ConditionViolation", "0x"],
        },
        "C3a": {
            "label": "the agent attempts allowTarget (self-widening of its own target)",
            "call": {"to": ctx.addresses["module"],
                     "data": calls.allow_target_data(role, asset, calls.CLEARANCE_TARGET)},
            "expect": "revert onlyOwner (no administrative rights — attack #7)",
            "offline_checks": [
                ("allowTarget selector verified 0x7b0da5b2", common.SELECTOR_ALLOW_TARGET == "0x7b0da5b2"),
            ],
            "revert_expect": ["OwnableUnauthorizedAccount", "Unauthorized", "0x"],
        },
        "C3b": {
            "label": "the agent attempts Safe.enableModule (the module has full powers over the Safe)",
            "call": {"to": ctx.addresses["safe"],
                     "data": calls.safe_enable_module_data(agent)},
            "expect": "revert GS* (the only owner is the Safe itself)",
            "offline_checks": [
                ("enableModule(address) selector computed locally",
                 calls.safe_enable_module_selector().startswith("0x")),
            ],
            "revert_expect": ["GS", "0x"],
        },
        "C4": {
            "label": "loop 100 + 100 + 100 + 100 (on-chain accumulation)",
            "calls": [
                {"to": ctx.addresses["module"],
                 "data": calls.exec_with_role_data(
                     target=asset, value=0,
                     inner_data=calls.erc20_transfer_data(ctx.addresses["B"], 100_000_000),
                     operation=calls.OPERATION_CALL, role_key=role)}
                for _ in range(4)
            ],
            "expect": "the first 3 pass; the 4th reverts (cumulative overrun, attack #8)",
            "offline_checks": [
                ("100+100+100 = 300 000 000 ≤ maxRefill", 300_000_000 <= allow_refill),
                ("100+100+100+100 = 400 000 000 > maxRefill", 400_000_000 > allow_refill),
            ],
            "revert_expect": ["AllowanceExceeded", "0x"],
        },
    }


def run_c(ctx: DemoContext) -> Dict[str, Any]:
    """RUN C — DENY by the chain (the off-chain lock is deliberately bypassed)."""
    ctx.journal_run_start("C")
    cases = _c_for(ctx)
    results: List[Dict[str, Any]] = []
    criteria: List[Dict[str, Any]] = []

    for case_id, spec in cases.items():
        entry: Dict[str, Any] = {"case": case_id, "label": spec["label"], "expect": spec["expect"],
                                 "sent": False}
        entry["offline_checks"] = [{"description": description, "ok": bool(ok)}
                                   for description, ok in spec.get("offline_checks", [])]

        # Construction check: the calldata must decode to what we believe we built.
        primary = spec.get("call") or (spec.get("calls") or [{}])[0]
        decoded = None
        if case_id in ("C1", "C2", "C4"):
            decoded = calls.decode_exec_with_role(primary["data"])
            inner = calls.decode_erc20_transfer(decoded["inner_data"])
            entry["decoded"] = {"target": decoded["target"], "role_key": decoded["role_key"],
                                "inner_to": inner["to"], "inner_value": inner["value"],
                                "operation": decoded["operation"]}
            entry["offline_checks"].append({
                "description": "calldata round-trip (exec → transfer) consistent",
                "ok": decoded["target"].lower() == ctx.addresses["asset"].lower()
                      and decoded["operation"] == 0})
        elif case_id == "C3a":
            decoded = calls.allow_target_data(ctx.policy.role_key, ctx.addresses["asset"],
                                              calls.CLEARANCE_TARGET)
            entry["offline_checks"].append({
                "description": "complete allowTarget calldata (selector + 3 words)",
                "ok": decoded.startswith(common.SELECTOR_ALLOW_TARGET) and len(decoded) == 10 + 3 * 64})
        elif case_id == "C3b":
            entry["offline_checks"].append({
                "description": "complete enableModule calldata",
                "ok": len(spec["call"]["data"]) == 10 + 64})

        ctx.journal.append("INTENT", payload={"case": case_id, "label": spec["label"],
                                              "forced_calldata": True, "to": primary.get("to"),
                                              "data_prefix": (primary.get("data") or "")[:42] + "…"},
                           refs={"run": "C", "case": case_id})

        if ctx.mode == MODE_EXECUTE:
            fake_intent = {"intent_id": "forced-{}".format(case_id), "recipient": ctx.addresses["B"],
                           "amount_base_units": "1", "action": "forced"}
            sends = []
            for call in (spec.get("calls") or [spec["call"]]):
                if case_id in ("C3a", "C3b"):
                    # C3: raw submission (without the exec_with_role envelope) — the agent attempts
                    # a direct administrative action; the contract must reject it.
                    sent = ctx.execute_raw_tx(fake_intent, to=call["to"], data=call["data"])
                else:
                    inner = calls.decode_exec_with_role(call["data"])["inner_data"]
                    sent = ctx.execute_tx(fake_intent, inner_data=inner)
                outcome = {"tx_hash": sent["tx_hash"], "sent": sent["sent"],
                           "nonce": sent["nonce"]}
                receipt = sent.get("receipt")
                if receipt is not None:
                    outcome["status"] = receipt.get("status")
                    outcome["gas_used"] = common.hex_to_int(receipt.get("gasUsed")) if receipt.get("gasUsed") else None
                    if receipt.get("effectiveGasPrice"):
                        outcome["gas_cost_wei"] = (outcome["gas_used"] or 0) * common.hex_to_int(receipt["effectiveGasPrice"])
                    ctx.journal_receipt(fake_intent, receipt, "C")
                    replay = verify_receipt.replay_revert(
                        rpc_url=ctx.rpc_url, tx_hash=str(receipt.get("transactionHash")),
                        block_number=common.hex_to_int(receipt.get("blockNumber")) if receipt.get("blockNumber") else None)
                    outcome["revert"] = replay
                    ctx.journal.append("VERIFY", payload={"case": case_id, "status": receipt.get("status"),
                                                          "revert": replay},
                                       refs={"intent_id": fake_intent["intent_id"], "run": "C"})
                sends.append(outcome)
            entry["sent"] = True
            entry["sends"] = sends
        results.append(entry)
        ctx.journal_outcome(run="C", intent=None, outcome="DRY_RUN_SIMULATED" if ctx.mode == MODE_DRY else "FORCED_ATTEMPT",
                            detail={"case": case_id})

    # C5 — period boundary: the chain lets it through, the rolling counter refuses.
    boundary_first = ctx.build_transfer(amount="100.0", recipient_label="B",
                                        justification="RUN C5a — spend at T−1 s from the boundary")
    boundary_second = ctx.build_transfer(amount="100.0", recipient_label="B",
                                         justification="RUN C5b — spend at T+1 s (rolling counter)")
    decision_first = common.evaluate_policy(boundary_first, ctx.policy, cumulative_spent=150.0)
    decision_second = common.evaluate_policy(boundary_second, ctx.policy, cumulative_spent=250.0)
    ctx.journal.append("POLICY", payload=common.decision_as_dict(decision_first, intent=boundary_first,
                                                                 policy=ctx.policy,
                                                                 context={"cumulative_spent": 150.0}),
                       refs={"intent_id": boundary_first["intent_id"], "run": "C", "case": "C5a"})
    ctx.journal.append("POLICY", payload=common.decision_as_dict(decision_second, intent=boundary_second,
                                                                 policy=ctx.policy,
                                                                 context={"cumulative_spent": 250.0}),
                       refs={"intent_id": boundary_second["intent_id"], "run": "C", "case": "C5b"})
    boundary = {
        "case": "C5",
        "label": "period boundary: 2 spends of 100 USDC straddling the boundary",
        "first": {"verdict": decision_first.verdict, "reasons": decision_first.reasons,
                  "cumulative_before": 150.0},
        "second": {"verdict": decision_second.verdict, "reasons": decision_second.reasons,
                   "cumulative_before": 250.0},
        "expect": ("both pass on-chain (accepted limit, burst of maxRefill+refill) but the off-chain "
                   "rolling counter refuses the second one"),
        "ok": decision_first.verdict == "ALLOW" and decision_second.verdict == "DENY"
              and "AMOUNT_ABOVE_PERIOD_CAP" in decision_second.reasons,
    }
    ctx.log("C5: off-chain {} then {} {}".format(boundary["first"]["verdict"],
                                                    boundary["second"]["verdict"], boundary["second"]["reasons"]))

    offline_ok = all(all(check["ok"] for check in entry["offline_checks"]) for entry in results)
    criteria = [
        _criterion("C.1", "forced calldatas built and decoded (C1-C4)", "met" if offline_ok else "failed",
                   [entry["case"] for entry in results]),
        _criterion("C.2", "C1/C2/C4: expected revert, selector captured, gas recorded",
                   "pending" if ctx.mode == MODE_DRY else
                   ("met" if all(entry.get("sends") and all(str(s.get("status")) in ("0x0", "0") for s in entry["sends"])
                                 for entry in results if entry["case"] in ("C1", "C2")) else "failed")),
        _criterion("C.3", "C3: the agent has no administrative rights (both calls revert)",
                   "pending" if ctx.mode == MODE_DRY else
                   ("met" if all(entry.get("sends") and all(str(s.get("status")) in ("0x0", "0") for s in entry["sends"])
                                 for entry in results if entry["case"] in ("C3a", "C3b")) else "failed")),
        _criterion("C.4", "C5: 2 chain executions + 1 off-chain refusal demonstrated",
                   "met" if boundary["ok"] else "failed", boundary),
    ]
    summary = {"run": "C", "mode": ctx.mode, "cases": results, "boundary": boundary,
               "status": "DRY_RUN_OK" if ctx.mode == MODE_DRY else "EXECUTED"}
    _write_run_artifacts(ctx, "C", summary, criteria)
    summary["criteria"] = criteria
    return summary


# =============================================================================
# RUN D
# =============================================================================

def run_d(ctx: DemoContext, revocation_tx: Optional[str] = None) -> Dict[str, Any]:
    """RUN D — timed kill switch (K1: assignRoles(false) by the Safe)."""
    ctx.journal_run_start("D")
    criteria: List[Dict[str, Any]] = []
    timings: Dict[str, Any] = {"signature_collection": None, "inclusion": None, "effect": None}
    started = common.utc_now()

    intent = ctx.build_transfer(amount=RUN_D_AMOUNT, recipient_label="B",
                                justification="RUN D — ALLOW intent prepared, not sent (kill switch)")
    common.write_json(os.path.join(ctx.run_dir, "intent.json"), intent)
    ctx.journal_intent(intent, "D")
    decision = common.evaluate_policy(intent, ctx.policy, seen_intent_ids=ctx.registry.seen_intent_ids())
    ctx.journal_policy(common.decision_as_dict(decision, intent=intent, policy=ctx.policy), intent, "D")
    ctx.registry.record(intent_id=intent["intent_id"], idempotency_key=intent["idempotency_key"],
                        status="PREPARED", note="RUN D — intent not sent (kill switch)")

    revocation = calls.assign_roles_data(ctx.addresses["agent"], [ctx.policy.role_key], [False])
    reset = calls.assign_roles_data(ctx.addresses["agent"], [ctx.policy.role_key], [True])
    instruction = {
        "schema": "orvyren-safe-instruction/v1",
        "executed_by": "the 2/3 Safe (2 signatures) — NEVER by the agent",
        "to": ctx.addresses["module"],
        "data": revocation,
        "description": "assignRoles(agent, [AGENT], [false]) — removes the AGENT role (K1)",
        "verify_after": "Roles.roles(AGENT).members(agent) == false (eth_call)",
        "reset": {"to": ctx.addresses["module"], "data": reset,
                  "description": "assignRoles(agent, [AGENT], [true]) — reset after the demo"},
        "expected_agent_revert": {"selector": common.ERROR_NOT_AUTHORIZED,
                                  "name": "NotAuthorized(address) — measured on Base Sepolia on 2026-10-15",},
    }
    common.write_json(os.path.join(ctx.run_dir, "revocation_instruction.json"), instruction)
    ctx.log("revocation instruction written (to be executed from the Safe): "
            "assignRoles(agent, [AGENT], [false]) — selector {}".format(common.SELECTOR_ASSIGN_ROLES))
    decoded = calls.decode_assign_roles(revocation)
    criteria.append(_criterion("D.1", "K1 calldata built and verified (round-trip)",
                               "met" if (decoded["member"] == ctx.addresses["agent"]
                                         and decoded["role_keys"] == [ctx.policy.role_key]
                                         and decoded["enabled"] == [False]) else "failed", decoded))

    attempt: Dict[str, Any] = {"sent": False}
    if ctx.mode == MODE_EXECUTE:
        if decision.verdict != "ALLOW":
            attempt = {"sent": False, "reason": "D intent refused by the policy: {}".format(decision.reasons)}
        else:
            if revocation_tx:
                timings["revocation_tx"] = revocation_tx
                try:
                    receipt_rev = common.rpc(ctx.rpc_url, "eth_getTransactionReceipt", [revocation_tx])
                    timings["inclusion"] = {
                        "tx_hash": revocation_tx,
                        "block_number": common.hex_to_int(receipt_rev.get("blockNumber")) if receipt_rev else None,
                        "status": receipt_rev.get("status") if receipt_rev else "not included",
                    }
                except Exception as exc:
                    timings["inclusion"] = {"tx_hash": revocation_tx, "error": str(exc)}
            sent = ctx.execute_tx(intent)
            attempt = {"sent": sent["sent"], "tx_hash": sent["tx_hash"], "nonce": sent["nonce"]}
            receipt = sent.get("receipt")
            if receipt is not None:
                attempt["status"] = receipt.get("status")
                ctx.journal_receipt(intent, receipt, "D")
                replay = verify_receipt.replay_revert(
                    rpc_url=ctx.rpc_url, tx_hash=str(receipt.get("transactionHash")),
                    block_number=common.hex_to_int(receipt.get("blockNumber")) if receipt.get("blockNumber") else None)
                attempt["revert"] = replay
                ctx.journal.append("VERIFY", payload={"run": "D", "attempt_status": receipt.get("status"),
                                                      "revert": replay},
                                   refs={"intent_id": intent["intent_id"], "run": "D"})
                timings["effect"] = {"attempt_status": receipt.get("status"),
                                     "revert_selector": replay.get("revert_selector"),
                                     "expected_selector": common.ERROR_NOT_AUTHORIZED}
            else:
                attempt["status"] = "not included (valid outcome if delayed long enough — B5 §e.4)"
    else:
        attempt = {"sent": False, "reason": "dry-run: rehearsal, no real revocation"}

    criteria.extend([
        _criterion("D.2", "agent attempt: status 0x0 (or not included) after revocation",
                   "pending" if ctx.mode == MODE_DRY else
                   ("met" if attempt.get("status") in ("0x0", "0", None) else "failed"), attempt),
        _criterion("D.3", "observed revert selector = {}".format(common.ERROR_NOT_AUTHORIZED),
                   "pending" if ctx.mode == MODE_DRY else
                   ("met" if (attempt.get("revert") or {}).get("revert_selector") == common.ERROR_NOT_AUTHORIZED
                    else "failed"), attempt.get("revert")),
        _criterion("D.4", "latencies (a) collection, (b) inclusion, (c) effect displayed",
                   "pending" if ctx.mode == MODE_DRY else "met", timings),
        _criterion("D.5", "revocation independently verified (members == false) then reset prepared",
                   "pending" if ctx.mode == MODE_DRY else "met",
                   {"reset_calldata": reset, "reset_selector": common.SELECTOR_ASSIGN_ROLES}),
    ])

    ctx.journal_outcome(run="D", intent=intent, outcome="KILL_SWITCH_REHEARSED" if ctx.mode == MODE_DRY else "KILL_SWITCH_EXECUTED",
                        detail={"started_at": started, "timings": timings, "attempt": attempt})
    summary = {"run": "D", "mode": ctx.mode, "intent_id": intent["intent_id"], "verdict": decision.verdict,
               "revocation": instruction, "attempt": attempt, "timings": timings,
               "status": "DRY_RUN_OK" if ctx.mode == MODE_DRY else "EXECUTED"}
    _write_run_artifacts(ctx, "D", summary, criteria)
    summary["criteria"] = criteria
    return summary


# =============================================================================
# RUN E
# =============================================================================

def run_e(ctx: DemoContext) -> Dict[str, Any]:
    """RUN E — journal and audit: export, independent verification, counters."""
    ctx.journal_run_start("E")
    export_dir = os.path.join(ctx.session_dir, "export")
    os.makedirs(export_dir, exist_ok=True)

    chain_report = ctx.journal.verify()
    records = common.read_jsonl(os.path.join(ctx.session_dir, "audit.jsonl"))
    records = [record for record in records if isinstance(record, dict)]

    submits = [record for record in records if record.get("kind") == "SUBMIT"]
    receipts = [record for record in records if record.get("kind") == "RECEIPT"]
    policies = [record for record in records if record.get("kind") == "POLICY"]
    denials = [record for record in policies
               if (record.get("payload") or {}).get("verdict") == "DENY"]
    approvals = [record for record in policies
                 if (record.get("payload") or {}).get("verdict") == "REQUIRE_APPROVAL"]
    allow_policies = [record for record in policies
                      if (record.get("payload") or {}).get("verdict") == "ALLOW"]

    chain_checks: List[Dict[str, Any]] = []
    if ctx.mode == MODE_EXECUTE:
        for submit in submits:
            payload = submit.get("payload") or {}
            if payload.get("simulated"):
                continue
            tx_hash = payload.get("tx_hash")
            intent_paths = [os.path.join(ctx.session_dir, "runs", name, "intent.json")
                            for name in sorted(os.listdir(os.path.join(ctx.session_dir, "runs")))] \
                if os.path.isdir(os.path.join(ctx.session_dir, "runs")) else []
            intent = None
            target_intent_id = ((submit.get("refs") or {}).get("intent_id"))
            for path in intent_paths:
                candidate = common.load_json(path)
                if isinstance(candidate, dict) and candidate.get("intent_id") == target_intent_id:
                    intent = candidate
                    break
            entry: Dict[str, Any] = {"tx_hash": tx_hash, "intent_id": target_intent_id}
            try:
                receipt = common.rpc(ctx.rpc_url, "eth_getTransactionReceipt", [tx_hash])
                if receipt is None:
                    entry["status"] = "RECEIPT_UNAVAILABLE"
                    chain_checks.append(entry)
                    continue
                entry["status"] = receipt.get("status")
                if intent and str(receipt.get("status")) in ("0x1", "1"):
                    enriched = dict(receipt)
                    enriched.setdefault("chainId", hex(ctx.policy.chain_id))
                    verification = verify_receipt.verify_full(
                        enriched, intent=intent, safe=ctx.addresses["safe"], module=ctx.addresses["module"],
                        agent=ctx.addresses["agent"], chain_id=ctx.policy.chain_id,
                        decimals=ctx.policy.asset_decimals)
                    entry["verification_ok"] = verification["ok"]
                    entry["mismatches"] = verification["mismatches"]
                chain_checks.append(entry)
            except Exception as exc:
                entry["status"] = "UNRESOLVED"
                entry["error"] = str(exc)
                chain_checks.append(entry)

    manifest = {
        "schema": "orvyren-session-manifest/v1",
        "run_id": ctx.run_id,
        "case": ctx.case,
        "exported_at": _now_iso(),
        "journal": {"records": chain_report["records"], "heads": chain_report["heads"],
                    "counts": chain_report["counts"], "chain_ok": chain_report["ok"]},
        "counters": {
            "allow_policy_entries": len(allow_policies),
            "deny_entries": len(denials),
            "require_approval_entries": len(approvals),
            "submits": len(submits),
            "receipts": len(receipts),
            "signatures": ctx.signatures.count(),
            "chain_confronted": len(chain_checks),
        },
        "addresses": {label: address for label, address in ctx.addresses.items()},
        "contracts_expected_present": {label: address for label, address in common.KNOWN_ADDRESSES.items()},
    }
    common.write_json(os.path.join(export_dir, "manifest.json"), manifest)

    report_lines = [
        "# ORVYREN — demo session report",
        "",
        "- session: `{}`".format(common.display_path(ctx.session_dir)),
        "- run_id: `{}` · case: `{}` · mode: **{}**".format(ctx.run_id, ctx.case, ctx.mode),
        "- chain: Base Sepolia (84532) — testnet only, no real money",
        "",
        "## Journal (SHA-256 chained append-only)",
        "",
        "- records: **{}**".format(chain_report["records"]),
        "- recomputed chain: **{}**".format("OK (no write detected)" if chain_report["ok"] else "BREAK"),
        "- stream heads: `{}`".format(json.dumps(chain_report["heads"], ensure_ascii=False)),
        "",
        "## Counters",
        "",
        "- authorized executions (POLICY ALLOW entries): {}".format(len(allow_policies)),
        "- off-chain refusals (POLICY DENY): {}".format(len(denials)),
        "- approval requests (REQUIRE_APPROVAL): {}".format(len(approvals)),
        "- submitted transactions: {} · receipts recorded: {}".format(len(submits), len(receipts)),
        "- signatures issued by the service: {}".format(ctx.signatures.count()),
        "",
        "## Independent verification (re-reading the tx_hash values)",
        "",
    ]
    if ctx.mode == MODE_EXECUTE:
        conforms = len([check for check in chain_checks if check.get("verification_ok")])
        forced_failed = len([check for check in chain_checks if str(check.get("status")) in ("0x0", "0")])
        report_lines.append("- {} compliant executions, {} off-chain refusals, {} forced attempts "
                            "refused by the chain".format(conforms, len(denials), forced_failed))
    else:
        report_lines.append("- chain confrontation not executed (dry-run) — rerun run E "
                            "with `--execute --rpc` after the real run A")
    report_lines.extend([
        "",
        "## What this report does not prove",
        "",
        "- testnet prices are not market data (no performance is claimed);",
        "- in dry-run, **no transaction was sent**: the hashes are placeholders tagged `simulated`;",
        "- coverage is not exhaustiveness: what is not journaled does not exist for the reviewer.",
        "",
    ])
    report_path = os.path.join(ctx.session_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(report_lines))
    ctx.journal.append("OUTCOME", payload={"run": "E", "export": "export/manifest.json",
                                           "report": "report.md", "chain_ok": chain_report["ok"],
                                           "chain_checks": chain_checks})

    criteria = [
        _criterion("E.1", "hash chain recomputed OK (no write detected)",
                   "met" if chain_report["ok"] else "failed", chain_report["errors"][:5]),
        _criterion("E.2", "journal ↔ chain divergence = 0",
                   "pending" if ctx.mode == MODE_DRY else
                   ("met" if all(check.get("verification_ok", check.get("status") in ("0x0", "0"))
                                 for check in chain_checks) else "failed"), chain_checks),
        _criterion("E.3", "the report lists refusals and failures (first-class)",
                   "met" if (denials or approvals) else "pending",
                   {"deny": len(denials), "require_approval": len(approvals)}),
        _criterion("E.4", "counters exported (manifest.json)",
                   "met", manifest["counters"]),
    ]
    summary = {"run": "E", "mode": ctx.mode, "chain_report": chain_report, "manifest": manifest,
               "chain_checks": chain_checks,
               "status": "DRY_RUN_OK" if ctx.mode == MODE_DRY else "EXPORTED"}
    _write_run_artifacts(ctx, "E", summary, criteria)
    summary["criteria"] = criteria
    return summary


# =============================================================================
# CLI
# =============================================================================

def execute_run(run: str, ctx: DemoContext, *, revocation_tx: Optional[str] = None,
                amount: Optional[str] = None) -> Dict[str, Any]:
    run = run.upper()
    if run == "A":
        return run_a(ctx, amount=amount or RUN_A_AMOUNT)
    if run == "B":
        return run_b(ctx)
    if run == "C":
        return run_c(ctx)
    if run == "D":
        return run_d(ctx, revocation_tx=revocation_tx)
    if run == "E":
        return run_e(ctx)
    raise ValueError("unknown run: {}".format(run))


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="demo.py",
        description="ORVYREN — orchestrator for the 5 testnet demo runs (A ALLOW · B off-chain DENY · "
                    "C chain-level DENY · D kill switch · E journal/audit). "
                    "Dry-run by default: no key, no transaction.")
    parser.add_argument("--run", required=True, choices=list(RUNS) + [run.lower() for run in RUNS],
                        help="run to execute: A, B, C, D or E")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=None,
                      help="off-chain rehearsal: simulated signatures, placeholder hashes (default)")
    mode.add_argument("--execute", action="store_true",
                      help="real execution (requires a complete .env, eth-account and ORVYREN_PRIVATE_KEY)")
    parser.add_argument("--case", default="rseth",
                        help="journaled case/episode label (default: rseth; e.g. usdc-2023-03)")
    parser.add_argument("--session", default=None,
                        help="session directory (default: evidence/demo_runs/<case>)")
    parser.add_argument("--env-file", default=None, help="session .env file (never versioned)")
    parser.add_argument("--policy", default=None, help="policy (default: policy.demo.json)")
    parser.add_argument("--envelope", default=None,
                        help="captured reference envelope (completed envelope.example.json)")
    parser.add_argument("--rpc-url", default=None, help="Base Sepolia RPC (default: environment variable or public endpoint)")
    parser.add_argument("--revocation-tx", default=None,
                        help="run D: hash of the revocation transaction executed by the Safe (timing)")
    parser.add_argument("--amount", default=None,
                        help="run A: amount in USDC (default 100.0 — frozen decision FREEZE_V2 E2; "
                             "B5 §e.1 wrote 50, open gap B5 Q2)")
    parser.add_argument("--quiet", action="store_true", help="minimal output")
    args = parser.parse_args(argv)

    run = args.run.upper()
    mode_value = MODE_EXECUTE if args.execute else MODE_DRY
    session_dir = args.session or os.path.join(common.ROOT, "evidence", "demo_runs", args.case)
    env_file = args.env_file or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

    try:
        ctx = DemoContext(case=args.case, mode=mode_value, session_dir=session_dir,
                          env_file=env_file if os.path.isfile(env_file) else None,
                          policy_path=args.policy, envelope_path=args.envelope,
                          rpc_url=args.rpc_url, quiet=args.quiet)
        ctx.require_execute_prerequisites()
    except common.ConfigurationError as exc:
        print("CONFIGURATION ERROR: {}".format(exc), file=sys.stderr)
        return EXIT_CONFIG
    except signer_mod.SignerError as exc:
        print("SIGNER ERROR: {}".format(exc), file=sys.stderr)
        return EXIT_PREREQUISITES

    print("ORVYREN — run {} ({}) · session {}".format(
        run, ctx.mode, common.display_path(ctx.session_dir)))
    if ctx.placeholders_used:
        print("  (placeholder rehearsal addresses: {})".format(", ".join(sorted(set(ctx.placeholders_used)))))

    try:
        summary = execute_run(run, ctx, revocation_tx=args.revocation_tx, amount=args.amount)
    except signer_mod.SignerDependencyError as exc:
        print("SIGNER ERROR: {}".format(exc), file=sys.stderr)
        return EXIT_PREREQUISITES
    except signer_mod.SignerError as exc:
        print("SIGNER ERROR: {}".format(exc), file=sys.stderr)
        return EXIT_PREREQUISITES
    except common.chain_client.ChainError as exc:
        print("NETWORK/RPC ERROR: {}".format(exc), file=sys.stderr)
        return EXIT_PREREQUISITES

    criteria = summary.get("criteria") or []
    counts = _criteria_counts(criteria)
    ok = _criteria_ok(criteria)
    print("")
    print("  run {} : {} — {} ({}/{} met, {} pending{})".format(
        run, summary.get("status"), _criteria_label(criteria),
        counts["met"], len(criteria), counts["pending"],
        ", {} failed".format(counts["failed"]) if counts["failed"] else ""))
    if not ok and counts["pending"] and not counts["failed"]:
        print("  ! criteria not evaluated in dry-run: no \"OK\" proof is claimed.")
    print("  artifacts : {}".format(common.display_path(ctx.run_dir)))
    print("  journal   : {}".format(common.display_path(os.path.join(ctx.session_dir, "audit.jsonl"))))
    return EXIT_OK if ok else EXIT_CRITERIA_FAILED


if __name__ == "__main__":
    sys.exit(main())
