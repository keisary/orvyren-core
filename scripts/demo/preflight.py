#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — testnet demo kit: **12-check preflight + 10-check drift test**.

Two families of checks, a single JSON report:

* **P1-P12** — the simulation/verification checklist **before any signature**
  (B5 §c.1): policy verdict, pinned chain, expiry, idempotency,
  K0 pause, on-chain policy version, presence of target contracts,
  nonce, balances, gas, **``eth_call`` simulation from the agent address**,
  gas estimate. A single failure ⇒ no signature.
* **D1-D10** — the off-chain ↔ Zodiac envelope **drift test** (B4 §d.3):
  chain, module (code), members, targets, functions, conditions, allowances,
  call quota, expiration/scheduled revocation, version/advisory. Divergence or
  inability to verify ⇒ **SAFE MODE** (B4 P12): every autonomous action refused,
  journal ``ENVELOPE_DRIFT`` / ``ENVELOPE_UNVERIFIED``.

Modes:

* ``--offline`` (default): **no network**; the live checks are
  ``SKIPPED``/``UNKNOWN`` and the report carries ``verdict = OFFLINE_PASS`` — it is
  the off-chain rehearsal, never a proof of execution;
* ``--rpc``: the live checks run (read-only, User-Agent
  included); on failure or an impossible check, the report refuses.

``--capture-envelope`` (live mode) writes a reference envelope
(addresses + sizes + code sha256 + block + gas price); the *probes*
(module getter calldata) remain to be confirmed on the deployed contract
(accepted limitation of B4 annex 4: the exact target/condition getter names
must be confirmed on demo day).

CLI:

    python scripts/demo/preflight.py --intent intent.json --policy policy.demo.json \
        --envelope envelope.example.json [--offline|--rpc] [--out report.json]
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from datetime import timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from . import calls, common, intents
except ImportError:  # direct execution: python scripts/demo/preflight.py
    _sys_dir = os.path.dirname(os.path.abspath(__file__))
    if _sys_dir not in sys.path:
        sys.path.insert(0, _sys_dir)
    import calls  # type: ignore  # noqa: E402
    import common  # type: ignore  # noqa: E402
    import intents  # type: ignore  # noqa: E402

MODE_OFFLINE = "offline"
MODE_RPC = "rpc"

#: Gas guard (B5 P10): refuse beyond 10× the reference value.
GAS_PRICE_BOUND_FACTOR = 10
#: Reference value measured on 2026-10-15 on Base Sepolia (B5 annex B): 0.006 gwei.
GAS_PRICE_BASELINE_WEI = 6_000_000
#: Estimation margin (B5 P12): gasLimit = 1.25 × estimate.
GAS_LIMIT_FACTOR = 1.25
#: Minimum ETH balance required: 2 × gas estimate (B5 P9).
GAS_BALANCE_FACTOR = 2

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2


def _check(cid: str, family: str, name: str, status: str, detail: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ok = {"PASS": True, "FAIL": False}.get(status)
    return {"id": cid, "family": family, "name": name, "status": status, "ok": ok, "detail": dict(detail or {})}


def _weights(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return float(ordered[middle - 1] + ordered[middle]) / 2.0


class PreflightRunner:
    """Runs the 12 + 10 checks and produces the JSON report."""

    def __init__(self, *, policy: common.PolicyReference,
                 intent: Optional[Dict[str, Any]] = None,
                 envelope: Optional[Dict[str, Any]] = None,
                 mode: str = MODE_OFFLINE,
                 registry: Optional[common.Registry] = None,
                 pause: Optional[common.PauseFlag] = None,
                 recorded_decision: Optional[Dict[str, Any]] = None,
                 agent: Optional[str] = None,
                 safe: Optional[str] = None,
                 module: Optional[str] = None,
                 asset: Optional[str] = None,
                 rpc_url: Optional[str] = None,
                 chain_id: Optional[int] = None,
                 timeout: int = common.RPC_TIMEOUT_SECONDS,
                 gas_baseline_wei: Optional[int] = None,
                 now: Optional[datetime] = None):
        self.policy = policy
        self.intent = intent
        self.envelope = envelope or {}
        self.mode = mode if mode in (MODE_OFFLINE, MODE_RPC) else MODE_OFFLINE
        self.registry = registry
        self.pause = pause
        self.recorded_decision = recorded_decision
        self.rpc_url = rpc_url or common.DEFAULT_RPC_URL
        self.chain_id = int(chain_id or policy.chain_id)
        self.timeout = int(timeout)
        self.now = now or common.utc_now_dt()
        self.agent = common.normalize_address(agent) if agent else None
        self.safe = common.normalize_address(safe) if safe else None
        self.module = common.normalize_address(module) if module else None
        self.asset = common.normalize_address(asset or policy.asset)
        self.gas_baseline_wei = int(gas_baseline_wei
                                    or (self.envelope.get("gas") or {}).get("gas_price_baseline_wei")
                                    or GAS_PRICE_BASELINE_WEI)
        # Values computed live, reused by several checks.
        self._live: Dict[str, Any] = {}

    # --- helpers --------------------------------------------------------------

    def _live_mode(self) -> bool:
        return self.mode == MODE_RPC

    def _exec_call(self) -> Optional[Dict[str, str]]:
        """Exact calldata executed by the agent (module ← transfer), built from the intent."""
        if not self.intent or not self.module:
            return None
        try:
            inner = calls.erc20_transfer_data(self.intent["recipient"], int(self.intent["amount_base_units"]))
            data = calls.exec_with_role_data(target=self.intent["asset"], value=0, inner_data=inner,
                                             operation=calls.OPERATION_CALL, role_key=self.policy.role_key)
        except (KeyError, ValueError) as exc:
            return None
        return {"to": self.module, "data": data, "from": self.agent or ""}

    def _read(self, method: str, params: Sequence[Any]) -> Any:
        return common.rpc(self.rpc_url, method, list(params), self.timeout)

    # --- P1-P12 ---------------------------------------------------------------

    def p1_policy_verdict(self) -> Dict[str, Any]:
        if not self.intent:
            return _check("P1", "preflight", "traced ALLOW policy verdict", "UNKNOWN",
                          {"reason": "no intent provided"})
        seen = self.registry.seen_intent_ids() if self.registry else ()
        decision = common.evaluate_policy(self.intent, self.policy, now=self.now, seen_intent_ids=seen)
        detail = {"recomputed": common.decision_as_dict(decision, intent=self.intent, policy=self.policy, now=self.now)}
        if decision.verdict != "ALLOW":
            detail["code"] = "policy_not_allow"
            return _check("P1", "preflight", "traced ALLOW policy verdict", "FAIL", detail)
        if self.recorded_decision is not None:
            recorded = str(self.recorded_decision.get("verdict"))
            detail["recorded"] = recorded
            if recorded != decision.verdict:
                detail["code"] = "policy_decision_mismatch"
                return _check("P1", "preflight", "traced ALLOW policy verdict", "FAIL", detail)
        return _check("P1", "preflight", "traced ALLOW policy verdict", "PASS", detail)

    def p2_chain_pinned(self) -> Dict[str, Any]:
        detail: Dict[str, Any] = {"expected": self.chain_id, "policy": self.policy.chain_id}
        if self.intent is not None:
            detail["intent"] = self.intent.get("chain_id")
            if int(self.intent.get("chain_id") or 0) != self.chain_id:
                detail["code"] = "chain_id_mismatch"
                return _check("P2", "preflight", "pinned chain (eth_chainId)", "FAIL", detail)
        if not self._live_mode():
            detail["note"] = "eth_chainId not read (offline mode) — the live check is required on demo day"
            return _check("P2", "preflight", "pinned chain (eth_chainId)", "PASS", detail)
        try:
            observed = common.eth_chain_id(self.rpc_url, self.timeout)
        except Exception as exc:  # ChainError
            detail.update({"code": "rpc_unreachable", "error": str(exc)})
            return _check("P2", "preflight", "pinned chain (eth_chainId)", "FAIL", detail)
        detail["observed"] = observed
        if observed != self.chain_id:
            detail["code"] = "chain_id_mismatch"
            return _check("P2", "preflight", "pinned chain (eth_chainId)", "FAIL", detail)
        return _check("P2", "preflight", "pinned chain (eth_chainId)", "PASS", detail)

    def p3_expiry(self) -> Dict[str, Any]:
        if not self.intent:
            return _check("P3", "preflight", "intent expiry not passed", "UNKNOWN",
                          {"reason": "no intent provided"})
        detail: Dict[str, Any] = {"expiry": self.intent.get("expiry"), "now": self.now.strftime("%Y-%m-%dT%H:%M:%SZ")}
        try:
            expiry = common.parse_rfc3339(self.intent.get("expiry"))
        except ValueError as exc:
            detail["code"] = "intent_expired"
            detail["error"] = str(exc)
            return _check("P3", "preflight", "intent expiry not passed", "FAIL", detail)
        if expiry <= self.now:
            detail["code"] = "intent_expired"
            return _check("P3", "preflight", "intent expiry not passed", "FAIL", detail)
        ttl = timedelta(minutes=self.policy.ttl_intent_minutes)
        if expiry > self.now + ttl:
            detail["code"] = "intent_ttl_too_long"
            return _check("P3", "preflight", "intent expiry not passed", "FAIL", detail)
        return _check("P3", "preflight", "intent expiry not passed", "PASS", detail)

    def p4_idempotency(self) -> Dict[str, Any]:
        if not self.intent:
            return _check("P4", "preflight", "idempotency (append-only registry)", "UNKNOWN",
                          {"reason": "no intent provided"})
        key = str(self.intent.get("idempotency_key") or "")
        if self.registry is None:
            return _check("P4", "preflight", "idempotency (append-only registry)", "UNKNOWN",
                          {"reason": "no registry provided", "code": "intent_registry_missing"})
        detail = {"idempotency_key": key, "registry": self.registry.as_dict()}
        if self.registry.has_key(key):
            detail["code"] = "intent_already_processed"
            return _check("P4", "preflight", "idempotency (append-only registry)", "FAIL", detail)
        if str(self.intent.get("intent_id")) in self.registry.seen_intent_ids():
            detail["code"] = "intent_already_processed"
            return _check("P4", "preflight", "idempotency (append-only registry)", "FAIL", detail)
        return _check("P4", "preflight", "idempotency (append-only registry)", "PASS", detail)

    def p5_pause(self) -> Dict[str, Any]:
        paused = bool(self.pause and self.pause.is_paused())
        detail = {"paused": paused, "flag_path": getattr(self.pause, "path", None)}
        if paused:
            detail["code"] = "agent_paused"
            return _check("P5", "preflight", "K0 pause (off-chain kill switch)", "FAIL", detail)
        return _check("P5", "preflight", "K0 pause (off-chain kill switch)", "PASS", detail)

    def p6_module_version(self) -> Dict[str, Any]:
        module_ref = (self.envelope.get("module") or {})
        address = self.module or module_ref.get("address")
        pinned = module_ref.get("code_sha256_expected")
        detail: Dict[str, Any] = {"module": address, "code_sha256_expected": pinned}
        if not address:
            return _check("P6", "preflight", "on-chain policy = expected (module)", "UNKNOWN",
                          {"reason": "module address missing (envelope and config)", "code": "module_version_unknown"})
        if not self._live_mode():
            if not pinned:
                detail["note"] = "codehash not pinned in the envelope: comparison impossible offline"
                return _check("P6", "preflight", "on-chain policy = expected (module)", "UNKNOWN", detail)
            return _check("P6", "preflight", "on-chain policy = expected (module)", "PASS", detail)
        try:
            code = common.eth_get_code(self.rpc_url, address, "latest", self.timeout)
        except Exception as exc:
            detail.update({"code": "module_version_unknown", "error": str(exc)})
            return _check("P6", "preflight", "on-chain policy = expected (module)", "FAIL", detail)
        if not code or code == "0x":
            detail["code"] = "target_code_missing"
            return _check("P6", "preflight", "on-chain policy = expected (module)", "FAIL", detail)
        body = code[2:]
        detail["code_size_bytes"] = len(body) // 2
        detail["code_sha256"] = common.sha256_hex(bytes.fromhex(body))
        if pinned and detail["code_sha256"] != str(pinned).lower():
            detail["code"] = "module_version_unknown"
            return _check("P6", "preflight", "on-chain policy = expected (module)", "FAIL", detail)
        expected_size = module_ref.get("code_size_expected")
        if expected_size and int(expected_size) != detail["code_size_bytes"]:
            detail["code"] = "module_version_unknown"
            return _check("P6", "preflight", "on-chain policy = expected (module)", "FAIL", detail)
        return _check("P6", "preflight", "on-chain policy = expected (module)", "PASS", detail)

    def p7_targets_code(self) -> Dict[str, Any]:
        addresses: Dict[str, str] = {}
        if self.intent:
            addresses["asset"] = str(self.intent.get("asset"))
            addresses["account"] = str(self.intent.get("account"))
        if self.module:
            addresses["module"] = self.module
        if self.asset:
            addresses.setdefault("asset", self.asset)
        detail: Dict[str, Any] = {"addresses": addresses}
        if not self._live_mode():
            detail["note"] = "eth_getCode not called (offline mode) — abort if code is empty on demo day"
            return _check("P7", "preflight", "target addresses re-verified (eth_getCode)", "SKIPPED", detail)
        results: Dict[str, Any] = {}
        missing = []
        for label, address in addresses.items():
            try:
                code = common.eth_get_code(self.rpc_url, address, "latest", self.timeout)
            except Exception as exc:
                results[label] = {"address": address, "error": str(exc)}
                missing.append(label)
                continue
            size = 0 if not code or code == "0x" else (len(code) - 2) // 2
            results[label] = {"address": address, "code_size_bytes": size}
            if size == 0:
                missing.append(label)
        detail["results"] = results
        if missing:
            detail["code"] = "target_code_missing"
            return _check("P7", "preflight", "target addresses re-verified (eth_getCode)", "FAIL", detail)
        return _check("P7", "preflight", "target addresses re-verified (eth_getCode)", "PASS", detail)

    def p8_nonce(self) -> Dict[str, Any]:
        detail: Dict[str, Any] = {"agent": self.agent}
        if not self.agent:
            return _check("P8", "preflight", "nonce (strict serialization)", "UNKNOWN",
                          {"reason": "agent address missing"})
        if not self._live_mode():
            detail["note"] = "eth_getTransactionCount not called (offline mode)"
            return _check("P8", "preflight", "nonce (strict serialization)", "SKIPPED", detail)
        try:
            nonce = common.eth_get_transaction_count(self.rpc_url, self.agent, "pending", self.timeout)
        except Exception as exc:
            detail.update({"code": "nonce_conflict", "error": str(exc)})
            return _check("P8", "preflight", "nonce (strict serialization)", "FAIL", detail)
        detail["pending_nonce"] = nonce
        self._live["nonce"] = nonce
        detail["note"] = "a single transaction in flight: the signer service serializes"
        return _check("P8", "preflight", "nonce (strict serialization)", "PASS", detail)

    def p9_balances(self) -> Dict[str, Any]:
        if not self.intent:
            return _check("P9", "preflight", "balances (gas + token)", "UNKNOWN", {"reason": "no intent provided"})
        detail: Dict[str, Any] = {"agent": self.agent, "safe": self.safe,
                                  "amount_base_units": self.intent.get("amount_base_units")}
        if not self._live_mode():
            detail["note"] = "balance reads not performed (offline mode)"
            return _check("P9", "preflight", "balances (gas + token)", "SKIPPED", detail)
        if not self.agent or not self.safe:
            detail["code"] = "insufficient_gas_balance"
            detail["reason"] = "agent/safe addresses missing"
            return _check("P9", "preflight", "balances (gas + token)", "FAIL", detail)
        gas_estimate = self._live.get("gas_estimate")
        try:
            eth_balance = common.eth_get_balance(self.rpc_url, self.agent, "latest", self.timeout)
            token_balance = calls.decode_uint_result(common.eth_call(
                self.rpc_url, self.asset, calls.balance_of_data(self.safe), "latest", self.timeout))
        except Exception as exc:
            detail.update({"code": "insufficient_token_balance", "error": str(exc)})
            return _check("P9", "preflight", "balances (gas + token)", "FAIL", detail)
        detail["agent_eth_wei"] = eth_balance
        detail["safe_token_base_units"] = token_balance
        if gas_estimate:
            need = int(math.ceil(gas_estimate * GAS_LIMIT_FACTOR)) * GAS_BALANCE_FACTOR * self.gas_price_wei()
            detail["required_gas_wei"] = need
            if eth_balance < need:
                detail["code"] = "insufficient_gas_balance"
                return _check("P9", "preflight", "balances (gas + token)", "FAIL", detail)
        else:
            if eth_balance == 0:
                detail["code"] = "insufficient_gas_balance"
                return _check("P9", "preflight", "balances (gas + token)", "FAIL", detail)
        if token_balance < int(self.intent.get("amount_base_units") or 0):
            detail["code"] = "insufficient_token_balance"
            return _check("P9", "preflight", "balances (gas + token)", "FAIL", detail)
        return _check("P9", "preflight", "balances (gas + token)", "PASS", detail)

    def gas_price_wei(self) -> int:
        if "gas_price" in self._live:
            return int(self._live["gas_price"])
        return int(self.gas_baseline_wei)

    def p10_gas_price(self) -> Dict[str, Any]:
        detail: Dict[str, Any] = {"baseline_wei": self.gas_baseline_wei,
                                  "bound_wei": self.gas_baseline_wei * GAS_PRICE_BOUND_FACTOR}
        if not self._live_mode():
            detail["note"] = "eth_gasPrice not read (offline mode)"
            return _check("P10", "preflight", "gas price within bounds", "SKIPPED", detail)
        try:
            price = common.eth_gas_price(self.rpc_url, self.timeout)
        except Exception as exc:
            detail.update({"code": "gas_price_out_of_bounds", "error": str(exc)})
            return _check("P10", "preflight", "gas price within bounds", "FAIL", detail)
        self._live["gas_price"] = price
        detail["gas_price_wei"] = price
        if price > self.gas_baseline_wei * GAS_PRICE_BOUND_FACTOR:
            detail["code"] = "gas_price_out_of_bounds"
            return _check("P10", "preflight", "gas price within bounds", "FAIL", detail)
        return _check("P10", "preflight", "gas price within bounds", "PASS", detail)

    def p11_simulation(self) -> Dict[str, Any]:
        call = self._exec_call()
        detail: Dict[str, Any] = {"exec_call_to": call["to"] if call else None}
        if not call or not self.agent:
            return _check("P11", "preflight", "eth_call simulation from the agent", "UNKNOWN",
                          {"reason": "calldata or agent address unavailable"})
        if not self._live_mode():
            detail["data_prefix"] = call["data"][:42] + "…"
            detail["note"] = ("simulation not executed (offline mode) — on demo day it starts from the agent's "
                              "key so the module policy evaluates it")
            return _check("P11", "preflight", "eth_call simulation from the agent", "SKIPPED", detail)
        try:
            result = self._read("eth_call", [{"from": self.agent, "to": call["to"], "data": call["data"]}, "latest"])
        except common.chain_client.RpcError as exc:
            detail.update({"code": "simulation_revert", "revert_selector": common.revert_selector(exc.data),
                           "error": exc.message})
            return _check("P11", "preflight", "eth_call simulation from the agent", "FAIL", detail)
        except Exception as exc:
            detail.update({"code": "simulation_revert", "error": str(exc)})
            return _check("P11", "preflight", "eth_call simulation from the agent", "FAIL", detail)
        detail["result"] = result
        return _check("P11", "preflight", "eth_call simulation from the agent", "PASS", detail)

    def p12_gas_estimate(self) -> Dict[str, Any]:
        call = self._exec_call()
        detail: Dict[str, Any] = {}
        if not call or not self.agent:
            return _check("P12", "preflight", "gas estimate (1.25×)", "UNKNOWN",
                          {"reason": "calldata or agent address unavailable"})
        if not self._live_mode():
            detail["note"] = "eth_estimateGas not called (offline mode)"
            detail["factor"] = GAS_LIMIT_FACTOR
            return _check("P12", "preflight", "gas estimate (1.25×)", "SKIPPED", detail)
        try:
            estimate = common.eth_estimate_gas(self.rpc_url, self.agent, call["to"], call["data"], self.timeout)
        except Exception as exc:
            detail.update({"code": "gas_estimate_failed", "error": str(exc)})
            return _check("P12", "preflight", "gas estimate (1.25×)", "FAIL", detail)
        limit = int(math.ceil(estimate * GAS_LIMIT_FACTOR))
        self._live["gas_estimate"] = estimate
        self._live["gas_limit"] = limit
        detail.update({"estimate": estimate, "gas_limit": limit, "factor": GAS_LIMIT_FACTOR})
        return _check("P12", "preflight", "gas estimate (1.25×)", "PASS", detail)

    # --- D1-D10 (drift test, B4 §d.3) ----------------------------------------

    def _envelope(self) -> Dict[str, Any]:
        return self.envelope or {}

    def _probes(self, check_id: str) -> List[Dict[str, Any]]:
        probes = self._envelope().get("probes") or []
        return [probe for probe in probes if isinstance(probe, dict) and probe.get("check") == check_id]

    def _run_probes(self, check_id: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Runs a check's ``eth_call`` probes (live mode). Failures are named."""
        executed: List[Dict[str, Any]] = []
        failures: List[str] = []
        for probe in self._probes(check_id):
            entry = {"id": probe.get("id"), "to": probe.get("to"), "note": probe.get("note", "")}
            if not self._live_mode():
                entry["status"] = "SKIPPED_OFFLINE"
                executed.append(entry)
                continue
            try:
                raw = common.eth_call(self.rpc_url, probe["to"], probe["data"], probe.get("block", "latest"),
                                      self.timeout)
                decode_type = (probe.get("decode") or {}).get("type", "uint256")
                if decode_type == "bool":
                    observed: Any = common.decode_word_bool(raw, 0)
                elif decode_type == "address":
                    observed = common.decode_word_address(raw, 0)
                elif decode_type == "bytes32":
                    observed = common.decode_word_bytes32(raw, 0)
                else:
                    observed = common.decode_word_uint(raw, 0)
                expected = probe.get("expect")
                if isinstance(expected, str) and expected.startswith("0x"):
                    match = str(observed).lower() == expected.lower()
                else:
                    match = observed == expected
                entry.update({"status": "PASS" if match else "FAIL", "observed": observed, "expect": expected})
                if not match:
                    failures.append("{}: observed {} ≠ expected {}".format(entry["id"], observed, expected))
            except Exception as exc:
                entry.update({"status": "ERROR", "error": str(exc)})
                failures.append("{}: {}".format(entry["id"], exc))
            executed.append(entry)
        return executed, failures

    def d1_chain(self) -> Dict[str, Any]:
        detail: Dict[str, Any] = {"policy_chain_id": self.policy.chain_id,
                                  "envelope_chain_id": self._envelope().get("chain_id")}
        probes, failures = self._run_probes("D1")
        detail["probes"] = probes
        if failures:
            detail["code"] = "ENVELOPE_DRIFT"
            detail["failures"] = failures
            return _check("D1", "drift", "chain (eth_chainId)", "FAIL", detail)
        if self._live_mode():
            try:
                detail["observed"] = common.eth_chain_id(self.rpc_url, self.timeout)
            except Exception as exc:
                detail.update({"code": "ENVELOPE_UNVERIFIED", "error": str(exc)})
                return _check("D1", "drift", "chain (eth_chainId)", "UNKNOWN", detail)
            if detail["observed"] != self.policy.chain_id:
                detail["code"] = "ENVELOPE_DRIFT"
                return _check("D1", "drift", "chain (eth_chainId)", "FAIL", detail)
            return _check("D1", "drift", "chain (eth_chainId)", "PASS", detail)
        envelope_chain = self._envelope().get("chain_id")
        if envelope_chain is None:
            detail["reason"] = "chain missing from the envelope"
            return _check("D1", "drift", "chain (eth_chainId)", "UNKNOWN", detail)
        if int(envelope_chain) != int(self.policy.chain_id):
            detail["code"] = "ENVELOPE_DRIFT"
            return _check("D1", "drift", "chain (eth_chainId)", "FAIL", detail)
        return _check("D1", "drift", "chain (eth_chainId)", "PASS", detail)

    def d2_module(self) -> Dict[str, Any]:
        module_ref = self._envelope().get("module") or {}
        address = self.module or module_ref.get("address")
        pinned = module_ref.get("code_sha256_expected")
        detail: Dict[str, Any] = {"module": address, "code_sha256_expected": pinned,
                                  "code_size_expected": module_ref.get("code_size_expected")}
        if not address:
            return _check("D2", "drift", "module (code + pinned codehash)", "UNKNOWN",
                          {"reason": "module address missing", "code": "ENVELOPE_UNVERIFIED"})
        if self._live_mode():
            try:
                code = common.eth_get_code(self.rpc_url, address, "latest", self.timeout)
            except Exception as exc:
                detail.update({"code": "ENVELOPE_UNVERIFIED", "error": str(exc)})
                return _check("D2", "drift", "module (code + pinned codehash)", "UNKNOWN", detail)
            body = code[2:] if code.startswith("0x") else code
            detail["code_size_bytes"] = len(body) // 2
            detail["code_sha256"] = common.sha256_hex(bytes.fromhex(body)) if body else ""
            if detail["code_size_bytes"] == 0:
                detail["code"] = "ENVELOPE_DRIFT"
                return _check("D2", "drift", "module (code + pinned codehash)", "FAIL", detail)
            if pinned and detail["code_sha256"] != str(pinned).lower():
                detail["code"] = "ENVELOPE_DRIFT"
                return _check("D2", "drift", "module (code + pinned codehash)", "FAIL", detail)
            expected_size = module_ref.get("code_size_expected")
            if expected_size and int(expected_size) != detail["code_size_bytes"]:
                detail["code"] = "ENVELOPE_DRIFT"
                return _check("D2", "drift", "module (code + pinned codehash)", "FAIL", detail)
            return _check("D2", "drift", "module (code + pinned codehash)", "PASS", detail)
        if not pinned:
            detail["reason"] = "codehash not pinned: offline comparison impossible (to be captured on demo day)"
            return _check("D2", "drift", "module (code + pinned codehash)", "UNKNOWN", detail)
        return _check("D2", "drift", "module (code + pinned codehash)", "PASS", detail)

    def d3_members(self) -> Dict[str, Any]:
        envelope_agent = ((self._envelope().get("agent") or {}).get("address"))
        detail: Dict[str, Any] = {"agent_config": self.agent, "agent_envelope": envelope_agent}
        probes, failures = self._run_probes("D3")
        detail["probes"] = probes
        if failures:
            detail["code"] = "ENVELOPE_DRIFT"
            detail["failures"] = failures
            return _check("D3", "drift", "AGENT role members", "FAIL", detail)
        if envelope_agent and self.agent and str(envelope_agent).lower() != self.agent.lower():
            detail["code"] = "ENVELOPE_DRIFT"
            detail["reason"] = "the config agent address ≠ the envelope's"
            return _check("D3", "drift", "AGENT role members", "FAIL", detail)
        if not probes:
            detail["reason"] = ("members not readable offline; eth_call probe to confirm on the deployed "
                                "contract (getter to freeze on demo day)")
            return _check("D3", "drift", "AGENT role members", "UNKNOWN", detail)
        return _check("D3", "drift", "AGENT role members", "PASS", detail)

    def d4_targets(self) -> Dict[str, Any]:
        role = self._envelope().get("role") or {}
        targets = role.get("targets")
        detail: Dict[str, Any] = {"declared": targets, "expected_asset": self.policy.asset}
        if not targets:
            return _check("D4", "drift", "role targets (clearance)", "UNKNOWN",
                          {"reason": "targets missing from the envelope", "code": "ENVELOPE_UNVERIFIED"})
        addresses = set()
        broad = []
        for target in targets:
            address = str(target.get("address") or "").lower()
            clearance = str(target.get("clearance") or "")
            addresses.add(address)
            if clearance.strip().lower() in ("target", "1"):
                broad.append(address)
        detail["addresses"] = sorted(addresses)
        if broad:
            detail["code"] = "ENVELOPE_DRIFT"
            detail["reason"] = "target in Clearance.Target (broad scope): {}".format(broad)
            return _check("D4", "drift", "role targets (clearance)", "FAIL", detail)
        if addresses != {self.policy.asset.lower()}:
            detail["code"] = "ENVELOPE_DRIFT"
            detail["reason"] = "the target set ≠ expected {{USDC}}"
            return _check("D4", "drift", "role targets (clearance)", "FAIL", detail)
        probes, failures = self._run_probes("D4")
        detail["probes"] = probes
        if failures:
            detail["code"] = "ENVELOPE_DRIFT"
            detail["failures"] = failures
            return _check("D4", "drift", "role targets (clearance)", "FAIL", detail)
        return _check("D4", "drift", "role targets (clearance)", "PASS", detail)

    def d5_functions(self) -> Dict[str, Any]:
        role = self._envelope().get("role") or {}
        functions = role.get("functions") or []
        detail: Dict[str, Any] = {"declared": functions, "expected": {
            "target": self.policy.asset, "signature": common.TRANSFER_SIGNATURE,
            "selector": common.SELECTOR_TRANSFER, "clearance": "Function", "operation": "CALL"}}
        if not functions:
            return _check("D5", "drift", "scoped functions", "UNKNOWN",
                          {"reason": "functions missing from the envelope", "code": "ENVELOPE_UNVERIFIED"})
        expected_pairs = set()
        problems: List[str] = []
        for function in functions:
            target = str(function.get("target") or "").lower()
            selector = str(function.get("selector") or "").lower()
            clearance = str(function.get("clearance") or "Function").lower()
            operation = str(function.get("operation") or "CALL").upper()
            expected_pairs.add((target, selector))
            if clearance == "target":
                problems.append("function in Target clearance (broad scope): {}".format(selector))
            if operation not in ("CALL",):
                problems.append("non-CALL operation on {}: {}".format(selector, operation))
        wanted = {(self.policy.asset.lower(), common.SELECTOR_TRANSFER)}
        if expected_pairs != wanted:
            problems.append("(target, selector) set = {} ≠ expected {}".format(sorted(expected_pairs), sorted(wanted)))
        detail["pairs"] = sorted("{}:{}".format(a, b) for a, b in expected_pairs)
        if problems:
            detail["code"] = "ENVELOPE_DRIFT"
            detail["failures"] = problems
            return _check("D5", "drift", "scoped functions", "FAIL", detail)
        probes, failures = self._run_probes("D5")
        detail["probes"] = probes
        if failures:
            detail["code"] = "ENVELOPE_DRIFT"
            detail["failures"] = failures
            return _check("D5", "drift", "scoped functions", "FAIL", detail)
        return _check("D5", "drift", "scoped functions", "PASS", detail)

    def d6_conditions(self) -> Dict[str, Any]:
        role = self._envelope().get("role") or {}
        conditions = role.get("conditions") or {}
        detail: Dict[str, Any] = {"declared": conditions,
                                  "expected_recipients": sorted(self.policy.allowed_recipients())}
        if not conditions:
            return _check("D6", "drift", "conditions (recipient, amount)", "UNKNOWN",
                          {"reason": "conditions missing from the envelope", "code": "ENVELOPE_UNVERIFIED"})
        problems: List[str] = []
        param0 = conditions.get("param0") or {}
        values = {str(value).lower() for value in (param0.get("values") or [])}
        if not values:
            return _check("D6", "drift", "conditions (recipient, amount)", "UNKNOWN",
                          {"reason": "recipient condition values not filled in the envelope "
                                     "(to paste from the Roles app on demo day)", "code": "ENVELOPE_UNVERIFIED"})
        if str(param0.get("kind")) != "or_equal":
            problems.append("recipient condition ≠ Or(EqualTo(B), EqualTo(C))")
        if values != set(self.policy.allowed_recipients()):
            problems.append("condition recipients {} ≠ policy allowlist {}".format(
                sorted(values), sorted(self.policy.allowed_recipients())))
        param1 = conditions.get("param1") or {}
        if str(param1.get("kind")) != "within_allowance":
            problems.append("amount condition missing (param1) — an unconditioned amount "
                            "can consume the allowance in one shot")
        elif str(param1.get("allowance_key")) not in (role.get("allowances") or {}):
            problems.append("allowance referenced by the condition not found: {}".format(param1.get("allowance_key")))
        if problems:
            detail["code"] = "ENVELOPE_DRIFT"
            detail["failures"] = problems
            return _check("D6", "drift", "conditions (recipient, amount)", "FAIL", detail)
        return _check("D6", "drift", "conditions (recipient, amount)", "PASS", detail)

    def d7_allowances(self) -> Dict[str, Any]:
        role = self._envelope().get("role") or {}
        allowances = role.get("allowances") or {}
        daily = allowances.get("usdc_daily") or {}
        detail: Dict[str, Any] = {"declared": daily, "policy": {
            "max_per_tx": self.policy.max_per_tx,
            "max_cumulative_24h": self.policy.max_cumulative_24h,
            "allowance_refill": self.policy.allowance_refill,
            "allowance_max_refill": self.policy.allowance_max_refill,
            "allowance_period_seconds": self.policy.allowance_period_seconds,
        }}
        if not daily:
            return _check("D7", "drift", "allowances (refill/maxRefill/period)", "UNKNOWN",
                          {"reason": "usdc_daily allowance missing from the envelope", "code": "ENVELOPE_UNVERIFIED"})
        refill = int(daily.get("refill_base_units") or 0)
        max_refill = int(daily.get("max_refill_base_units") or 0)
        period = int(daily.get("period_seconds") or 0)
        problems: List[str] = []
        if refill != max_refill:
            problems.append("refill ({}) ≠ maxRefill ({}): the boundary burst exceeds 2 periods".format(
                refill, max_refill))
        if (refill, max_refill, period) != (self.policy.allowance_refill, self.policy.allowance_max_refill,
                                            self.policy.allowance_period_seconds):
            problems.append("declared allowance {} ≠ policy {}".format(
                (refill, max_refill, period),
                (self.policy.allowance_refill, self.policy.allowance_max_refill,
                 self.policy.allowance_period_seconds)))
        max_per_tx_units = int(round(self.policy.max_per_tx * 10 ** self.policy.asset_decimals))
        if max_per_tx_units > min(refill, max_refill):
            problems.append("policy.max_per_tx ({}) > min(refill, maxRefill) ({})".format(
                max_per_tx_units, min(refill, max_refill)))
        max_cumul_units = int(round(self.policy.max_cumulative_24h * 10 ** self.policy.asset_decimals))
        if max_cumul_units > max_refill:
            problems.append("policy.max_cumulative_24h ({}) > maxRefill ({})".format(max_cumul_units, max_refill))
        if problems:
            detail["code"] = "ENVELOPE_DRIFT"
            detail["failures"] = problems
            return _check("D7", "drift", "allowances (refill/maxRefill/period)", "FAIL", detail)
        return _check("D7", "drift", "allowances (refill/maxRefill/period)", "PASS", detail)

    def d8_call_quota(self) -> Dict[str, Any]:
        role = self._envelope().get("role") or {}
        quota = role.get("call_quota") or {}
        detail: Dict[str, Any] = {"declared": quota, "policy_max_calls_24h": self.policy.max_calls_24h}
        if not quota:
            return _check("D8", "drift", "call quota (CallWithinAllowance)", "UNKNOWN",
                          {"reason": "call quota missing from the envelope", "code": "ENVELOPE_UNVERIFIED"})
        problems: List[str] = []
        if int(quota.get("max_per_period") or -1) != self.policy.max_calls_24h:
            problems.append("on-chain quota {} ≠ policy {}".format(
                quota.get("max_per_period"), self.policy.max_calls_24h))
        if int(quota.get("period_seconds") or 0) != self.policy.allowance_period_seconds:
            problems.append("quota period {} ≠ {}".format(
                quota.get("period_seconds"), self.policy.allowance_period_seconds))
        if problems:
            detail["code"] = "ENVELOPE_DRIFT"
            detail["failures"] = problems
            return _check("D8", "drift", "call quota (CallWithinAllowance)", "FAIL", detail)
        return _check("D8", "drift", "call quota (CallWithinAllowance)", "PASS", detail)

    def d9_expiration(self) -> Dict[str, Any]:
        scheduled = self.policy.revocation_scheduled_at or (self._envelope().get("revocation_scheduled_at"))
        detail: Dict[str, Any] = {"revocation_scheduled_at": scheduled,
                                  "note": "Zodiac Allowance has no expiration field (B4 P8): "
                                          "a scheduled revocation is required"}
        if not scheduled:
            detail["code"] = "ENVELOPE_DRIFT"
            return _check("D9", "drift", "expiration / scheduled revocation", "FAIL", detail)
        return _check("D9", "drift", "expiration / scheduled revocation", "PASS", detail)

    def d10_version(self) -> Dict[str, Any]:
        module_ref = self._envelope().get("module") or {}
        version = module_ref.get("version")
        advisory = module_ref.get("advisory_clear")
        detail: Dict[str, Any] = {"version": version, "advisory_clear": advisory,
                                  "codehash_pinned": bool(module_ref.get("code_sha256_expected"))}
        if not version or advisory is not True:
            detail["reason"] = ("module version not tracked or security advisory not declared clear "
                                "(2026 post-mortems: ERC-1271 v2.1.0→v2.1.1, MultiSend padding)")
            detail["code"] = "ENVELOPE_UNVERIFIED"
            return _check("D10", "drift", "module version / security advisory", "UNKNOWN", detail)
        return _check("D10", "drift", "module version / security advisory", "PASS", detail)

    # --- pilote ---------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        # Execution order: P9 (balances) consumes the gas estimate (P12) and the price (P10).
        checks = [
            self.p1_policy_verdict(), self.p2_chain_pinned(), self.p3_expiry(), self.p4_idempotency(),
            self.p5_pause(), self.p6_module_version(), self.p7_targets_code(), self.p8_nonce(),
            self.p10_gas_price(), self.p12_gas_estimate(), self.p9_balances(), self.p11_simulation(),
            self.d1_chain(), self.d2_module(), self.d3_members(), self.d4_targets(), self.d5_functions(),
            self.d6_conditions(), self.d7_allowances(), self.d8_call_quota(), self.d9_expiration(),
            self.d10_version(),
        ]
        checks.sort(key=lambda check: (check["family"] != "preflight", check["id"]))
        preflight = [check for check in checks if check["family"] == "preflight"]
        drift = [check for check in checks if check["family"] == "drift"]
        failed = [check["id"] for check in checks if check["ok"] is False]

        drift_fail = [check["id"] for check in drift if check["status"] == "FAIL"]
        drift_unknown = [check["id"] for check in drift if check["status"] == "UNKNOWN"]
        safe_mode_reasons: List[str] = []
        if drift_fail:
            safe_mode_reasons.append("ENVELOPE_DRIFT:" + ",".join(drift_fail))
        if self._live_mode() and drift_unknown:
            safe_mode_reasons.append("ENVELOPE_UNVERIFIED:" + ",".join(drift_unknown))
        safe_mode = bool(safe_mode_reasons)

        if failed:
            verdict = "FAIL"
        elif self._live_mode():
            verdict = "PASS"
        else:
            skipped = [check["id"] for check in checks if check["status"] in ("SKIPPED", "UNKNOWN")]
            verdict = "OFFLINE_PASS" if skipped else "PASS"

        report = {
            "v": 1,
            "schema": "orvyren-preflight/v1",
            "generated_at_utc": common.utc_now(),
            "mode": self.mode,
            "rpc_masked": common.mask_rpc_url(self.rpc_url),
            "chain_id": self.chain_id,
            "policy_version": self.policy.version,
            "role_key": self.policy.role_key,
            "verdict": verdict,
            "safe_mode": safe_mode,
            "safe_mode_reasons": safe_mode_reasons,
            "safe_mode_required_when_live": bool(drift_unknown),
            "blocking": bool(failed) or safe_mode,
            "checks": checks,
            "summary": {
                "preflight": {status: len([c for c in preflight if c["status"] == status])
                              for status in ("PASS", "FAIL", "SKIPPED", "UNKNOWN")},
                "drift": {status: len([c for c in drift if c["status"] == status])
                          for status in ("PASS", "FAIL", "SKIPPED", "UNKNOWN")},
                "failed": failed,
            },
        }
        return report


def capture_envelope(*, rpc_url: str, addresses: Dict[str, str], timeout: int = common.RPC_TIMEOUT_SECONDS,
                     chain_id_expected: int = common.CHAIN_ID_DEMO,
                     session: Optional[common.SessionConfig] = None) -> Dict[str, Any]:
    """Captures a reference envelope by read-only calls (chainId, block, gas, codes).

    The produced structure is directly consumable by the drift test
    (``module``, ``avatar``, ``agent``, ``assets``, ``contracts``); the
    ``role`` block (targets/conditions/allowances) and the ``probes`` remain to be confirmed
    on the deployed contract with the Roles app (B4 §d.3, annex 4).
    """
    chain_id = common.eth_chain_id(rpc_url, timeout)
    if chain_id != chain_id_expected:
        raise common.ConfigurationError(
            "observed chainId {} ≠ expected {} — capture refused".format(chain_id, chain_id_expected))
    block = common.eth_block_number(rpc_url, timeout)
    gas_price = common.eth_gas_price(rpc_url, timeout)
    contracts: Dict[str, Any] = {}
    for label, address in addresses.items():
        code = common.eth_get_code(rpc_url, address, "latest", timeout)
        body = code[2:] if code.startswith("0x") else code
        contracts[label] = {
            "address": common.normalize_address(address),
            "code_size_bytes": len(body) // 2,
            "code_sha256": common.sha256_hex(bytes.fromhex(body)) if body else "",
        }

    def pick(label: str) -> Optional[Dict[str, Any]]:
        entry = contracts.get(label)
        return {"address": entry["address"], "code_size_expected": entry["code_size_bytes"],
                "code_sha256_expected": entry["code_sha256"]} if entry else None

    envelope: Dict[str, Any] = {
        "schema": "orvyren-envelope/v1",
        "captured_at": common.utc_now(),
        "chain_id": chain_id,
        "block_number": block,
        "gas": {"gas_price_baseline_wei": gas_price, "captured_at_utc": common.utc_now()},
        "contracts": contracts,
        "probes": [],
        "note": ("envelope captured by read-only calls — `role` (targets/conditions/allowances) and `probes` "
                 "(getter calldata) remain to be confirmed on the deployed contract (B4 §d.3, annex 4)"),
    }
    module = pick("module") or pick("orvyren_module_address")
    if module:
        envelope["module"] = {**module, "version": None, "advisory_clear": None}
    avatar = pick("safe") or pick("orvyren_safe_address")
    if avatar:
        envelope["avatar"] = {"address": avatar["address"], "label": "demo Safe"}
    agent = pick("agent") or pick("orvyren_agent_address")
    if agent:
        envelope["agent"] = {"address": agent["address"], "label": "throwaway EOA member of the AGENT role"}
    assets = {}
    for label, key in (("usdc_circle", "usdc_circle_base_sepolia"), ("usdc_aave", "usdc_aave_base_sepolia"),
                       ("weth_predeploy", "weth_predeploy")):
        if key in contracts:
            assets[label] = contracts[key]["address"]
    if assets:
        envelope["assets"] = assets
    if session is not None:
        envelope["session_env_keys"] = sorted(session.env)
    return envelope


# --- CLI ---------------------------------------------------------------------


def _load_optional(path: Optional[str]) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    data = common.load_json(path)
    if not isinstance(data, dict):
        raise common.ConfigurationError("unreadable file: {}".format(path))
    return data


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="preflight.py",
        description="ORVYREN — 12-check preflight (B5 §c.1) + 10-check drift test (B4 §d.3). "
                    "No signature, no transaction; a single failure blocks.")
    parser.add_argument("--intent", help="JSON file of a v1 intent (validated by intents.validate_intent)")
    parser.add_argument("--policy", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                         "policy.demo.json"),
                        help="demo policy (default: policy.demo.json)")
    parser.add_argument("--env-file", help="session .env file (never versioned) for the addresses")
    parser.add_argument("--envelope", help="envelope reference (captured envelope.example.json)")
    parser.add_argument("--decision", help="recorded policy verdict (compared to P1)")
    parser.add_argument("--registry", help="idempotency registry (JSON) — P4")
    parser.add_argument("--out", help="write the JSON report to this path")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", default=None, help="no network (default)")
    mode.add_argument("--rpc", action="store_true", help="run the live checks (read-only)")
    parser.add_argument("--rpc-url", default=os.environ.get("ORVYREN_RPC_URL_BASE_SEPOLIA")
                        or common.DEFAULT_RPC_URL)
    parser.add_argument("--capture-envelope", metavar="OUT",
                        help="capture a reference envelope (live mode, read-only)")
    parser.add_argument("--quiet", action="store_true", help="print only the verdict")
    args = parser.parse_args(argv)

    mode_value = MODE_RPC if args.rpc else MODE_OFFLINE

    try:
        session = common.SessionConfig.from_env(args.env_file)
        recipients = {label: address for label, address in session.recipients.items() if address}
        policy = common.load_policy_reference(args.policy, recipients)

        if args.capture_envelope:
            if mode_value != MODE_RPC:
                print("ERROR: --capture-envelope requires --rpc (read-only)", file=sys.stderr)
                return EXIT_USAGE
            addresses = dict(common.KNOWN_ADDRESSES)
            for key in common.SessionConfig.REQUIRED_ADDRESS_KEYS:
                value = (session.env.get(key) or "").strip()
                if value:
                    addresses[key.lower()] = value
            envelope = capture_envelope(rpc_url=args.rpc_url, addresses=addresses, session=session)
            common.write_json(args.capture_envelope, envelope)
            print("envelope captured: {} (block {}, {} contracts)".format(
                args.capture_envelope, envelope["block_number"], len(envelope["contracts"])))
            return EXIT_OK

        intent = _load_optional(args.intent)
        envelope = _load_optional(args.envelope)
        recorded = _load_optional(args.decision)
        registry = common.Registry(args.registry) if args.registry else None

        if intent is not None:
            ok, errors = intents.validate_intent(intent, ttl_minutes=policy.ttl_intent_minutes,
                                                 decimals=policy.asset_decimals)
            if not ok:
                for error in errors:
                    print("invalid intent: [{}] {} — {}".format(error["code"], error["field"], error["detail"]),
                          file=sys.stderr)
                return EXIT_USAGE

        runner = PreflightRunner(
            policy=policy, intent=intent, envelope=envelope, mode=mode_value,
            registry=registry, recorded_decision=recorded,
            agent=session.env.get("ORVYREN_AGENT_ADDRESS"),
            safe=session.env.get("ORVYREN_SAFE_ADDRESS"),
            module=session.env.get("ORVYREN_MODULE_ADDRESS"),
            rpc_url=args.rpc_url,
        )
        report = runner.run()
    except common.ConfigurationError as exc:
        print("CONFIGURATION ERROR: {}".format(exc), file=sys.stderr)
        return EXIT_USAGE

    if args.out:
        common.write_json(args.out, report)

    if not args.quiet:
        print("ORVYREN — preflight ({}): verdict {} — safe_mode {}".format(
            report["mode"], report["verdict"], report["safe_mode"]))
        for check in report["checks"]:
            print("  [{}] {:<5} {:<4} {}".format(
                check["family"][:4], check["status"], check["id"], check["name"]))
        if report["safe_mode"]:
            print("  SAFE MODE: {}".format(", ".join(report["safe_mode_reasons"])))
    else:
        print(report["verdict"])

    return EXIT_FAIL if report["verdict"] == "FAIL" or report["safe_mode"] else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
