#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — kit de démo testnet : **préflight 12 contrôles + test de dérive 10 contrôles**.

Deux familles de contrôles, un seul rapport JSON :

* **P1-P12** — la checklist de simulation/vérifications **avant toute signature**
  (B5 §c.1) : verdict de politique, chaîne épinglée, échéance, idempotence,
  pause K0, version de la politique on-chain, présence des contrats cibles,
  nonce, soldes, gaz, **simulation ``eth_call`` depuis l'adresse de l'agent**,
  estimation de gaz. Un seul échec ⇒ aucune signature.
* **D1-D10** — le **test de dérive** hors chaîne ↔ enveloppe Zodiac (B4 §d.3) :
  chaîne, module (code), membres, cibles, fonctions, conditions, allowances,
  quota d'appels, expiration/révocation planifiée, version/avis. Divergence ou
  impossibilité de vérifier ⇒ **SAFE MODE** (B4 P12) : refus de tout autonome,
  journal ``ENVELOPE_DRIFT`` / ``ENVELOPE_UNVERIFIED``.

Modes :

* ``--offline`` (défaut) : **aucun réseau** ; les contrôles en ligne sont
  ``SKIPPED``/``UNKNOWN`` et le rapport porte ``verdict = OFFLINE_PASS`` — c'est
  la répétition hors chaîne, jamais une preuve d'exécution ;
* ``--rpc`` : les contrôles en ligne s'exécutent (lecture seule, User-Agent
  inclus) ; en cas d'échec ou de contrôle impossible, le rapport refuse.

``--capture-envelope`` (mode en ligne) écrit une enveloppe de référence
(adresses + tailles + sha256 du code + bloc + prix du gaz) ; les *probes*
(calldata des getters du module) restent à confirmer sur le contrat déployé
(limite assumée de B4 annexe 4 : les noms exacts des getters de cible/condition
doivent être confirmés le jour J).

CLI :

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
except ImportError:  # exécution directe : python scripts/demo/preflight.py
    _sys_dir = os.path.dirname(os.path.abspath(__file__))
    if _sys_dir not in sys.path:
        sys.path.insert(0, _sys_dir)
    import calls  # type: ignore  # noqa: E402
    import common  # type: ignore  # noqa: E402
    import intents  # type: ignore  # noqa: E402

MODE_OFFLINE = "offline"
MODE_RPC = "rpc"

#: Garde-fou gaz (B5 P10) : refus au-delà de 10× la valeur de référence.
GAS_PRICE_BOUND_FACTOR = 10
#: Valeur de référence mesurée le 2026-10-15 sur Base Sepolia (B5 annexe B) : 0,006 gwei.
GAS_PRICE_BASELINE_WEI = 6_000_000
#: Marge d'estimation (B5 P12) : gasLimit = 1,25 × estimation.
GAS_LIMIT_FACTOR = 1.25
#: Solde ETH minimal exigé : 2 × estimation de gaz (B5 P9).
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
    """Exécute les 12 + 10 contrôles et produit le rapport JSON."""

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
        # Valeurs calculées en ligne, réutilisées par plusieurs contrôles.
        self._live: Dict[str, Any] = {}

    # --- helpers --------------------------------------------------------------

    def _live_mode(self) -> bool:
        return self.mode == MODE_RPC

    def _exec_call(self) -> Optional[Dict[str, str]]:
        """Calldata exact exécuté par l'agent (module ← transfer), construit depuis l'intent."""
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
            return _check("P1", "preflight", "verdict de politique ALLOW tracé", "UNKNOWN",
                          {"reason": "aucun intent fourni"})
        seen = self.registry.seen_intent_ids() if self.registry else ()
        decision = common.evaluate_policy(self.intent, self.policy, now=self.now, seen_intent_ids=seen)
        detail = {"recomputed": common.decision_as_dict(decision, intent=self.intent, policy=self.policy, now=self.now)}
        if decision.verdict != "ALLOW":
            detail["code"] = "policy_not_allow"
            return _check("P1", "preflight", "verdict de politique ALLOW tracé", "FAIL", detail)
        if self.recorded_decision is not None:
            recorded = str(self.recorded_decision.get("verdict"))
            detail["recorded"] = recorded
            if recorded != decision.verdict:
                detail["code"] = "policy_decision_mismatch"
                return _check("P1", "preflight", "verdict de politique ALLOW tracé", "FAIL", detail)
        return _check("P1", "preflight", "verdict de politique ALLOW tracé", "PASS", detail)

    def p2_chain_pinned(self) -> Dict[str, Any]:
        detail: Dict[str, Any] = {"expected": self.chain_id, "policy": self.policy.chain_id}
        if self.intent is not None:
            detail["intent"] = self.intent.get("chain_id")
            if int(self.intent.get("chain_id") or 0) != self.chain_id:
                detail["code"] = "chain_id_mismatch"
                return _check("P2", "preflight", "chaîne épinglée (eth_chainId)", "FAIL", detail)
        if not self._live_mode():
            detail["note"] = "eth_chainId non lu (mode hors-ligne) — le contrôle en ligne est requis le jour J"
            return _check("P2", "preflight", "chaîne épinglée (eth_chainId)", "PASS", detail)
        try:
            observed = common.eth_chain_id(self.rpc_url, self.timeout)
        except Exception as exc:  # ChainError
            detail.update({"code": "rpc_unreachable", "error": str(exc)})
            return _check("P2", "preflight", "chaîne épinglée (eth_chainId)", "FAIL", detail)
        detail["observed"] = observed
        if observed != self.chain_id:
            detail["code"] = "chain_id_mismatch"
            return _check("P2", "preflight", "chaîne épinglée (eth_chainId)", "FAIL", detail)
        return _check("P2", "preflight", "chaîne épinglée (eth_chainId)", "PASS", detail)

    def p3_expiry(self) -> Dict[str, Any]:
        if not self.intent:
            return _check("P3", "preflight", "expiry de l'intent non dépassée", "UNKNOWN",
                          {"reason": "aucun intent fourni"})
        detail: Dict[str, Any] = {"expiry": self.intent.get("expiry"), "now": self.now.strftime("%Y-%m-%dT%H:%M:%SZ")}
        try:
            expiry = common.parse_rfc3339(self.intent.get("expiry"))
        except ValueError as exc:
            detail["code"] = "intent_expired"
            detail["error"] = str(exc)
            return _check("P3", "preflight", "expiry de l'intent non dépassée", "FAIL", detail)
        if expiry <= self.now:
            detail["code"] = "intent_expired"
            return _check("P3", "preflight", "expiry de l'intent non dépassée", "FAIL", detail)
        ttl = timedelta(minutes=self.policy.ttl_intent_minutes)
        if expiry > self.now + ttl:
            detail["code"] = "intent_ttl_too_long"
            return _check("P3", "preflight", "expiry de l'intent non dépassée", "FAIL", detail)
        return _check("P3", "preflight", "expiry de l'intent non dépassée", "PASS", detail)

    def p4_idempotency(self) -> Dict[str, Any]:
        if not self.intent:
            return _check("P4", "preflight", "idempotence (registre append-only)", "UNKNOWN",
                          {"reason": "aucun intent fourni"})
        key = str(self.intent.get("idempotency_key") or "")
        if self.registry is None:
            return _check("P4", "preflight", "idempotence (registre append-only)", "UNKNOWN",
                          {"reason": "aucun registre fourni", "code": "intent_registry_missing"})
        detail = {"idempotency_key": key, "registry": self.registry.as_dict()}
        if self.registry.has_key(key):
            detail["code"] = "intent_already_processed"
            return _check("P4", "preflight", "idempotence (registre append-only)", "FAIL", detail)
        if str(self.intent.get("intent_id")) in self.registry.seen_intent_ids():
            detail["code"] = "intent_already_processed"
            return _check("P4", "preflight", "idempotence (registre append-only)", "FAIL", detail)
        return _check("P4", "preflight", "idempotence (registre append-only)", "PASS", detail)

    def p5_pause(self) -> Dict[str, Any]:
        paused = bool(self.pause and self.pause.is_paused())
        detail = {"paused": paused, "flag_path": getattr(self.pause, "path", None)}
        if paused:
            detail["code"] = "agent_paused"
            return _check("P5", "preflight", "pause K0 (kill switch hors chaîne)", "FAIL", detail)
        return _check("P5", "preflight", "pause K0 (kill switch hors chaîne)", "PASS", detail)

    def p6_module_version(self) -> Dict[str, Any]:
        module_ref = (self.envelope.get("module") or {})
        address = self.module or module_ref.get("address")
        pinned = module_ref.get("code_sha256_expected")
        detail: Dict[str, Any] = {"module": address, "code_sha256_expected": pinned}
        if not address:
            return _check("P6", "preflight", "politique on-chain = attendue (module)", "UNKNOWN",
                          {"reason": "adresse du module absente (enveloppe et config)", "code": "module_version_unknown"})
        if not self._live_mode():
            if not pinned:
                detail["note"] = "codehash non épinglé dans l'enveloppe : la comparaison est impossible hors ligne"
                return _check("P6", "preflight", "politique on-chain = attendue (module)", "UNKNOWN", detail)
            return _check("P6", "preflight", "politique on-chain = attendue (module)", "PASS", detail)
        try:
            code = common.eth_get_code(self.rpc_url, address, "latest", self.timeout)
        except Exception as exc:
            detail.update({"code": "module_version_unknown", "error": str(exc)})
            return _check("P6", "preflight", "politique on-chain = attendue (module)", "FAIL", detail)
        if not code or code == "0x":
            detail["code"] = "target_code_missing"
            return _check("P6", "preflight", "politique on-chain = attendue (module)", "FAIL", detail)
        body = code[2:]
        detail["code_size_bytes"] = len(body) // 2
        detail["code_sha256"] = common.sha256_hex(bytes.fromhex(body))
        if pinned and detail["code_sha256"] != str(pinned).lower():
            detail["code"] = "module_version_unknown"
            return _check("P6", "preflight", "politique on-chain = attendue (module)", "FAIL", detail)
        expected_size = module_ref.get("code_size_expected")
        if expected_size and int(expected_size) != detail["code_size_bytes"]:
            detail["code"] = "module_version_unknown"
            return _check("P6", "preflight", "politique on-chain = attendue (module)", "FAIL", detail)
        return _check("P6", "preflight", "politique on-chain = attendue (module)", "PASS", detail)

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
            detail["note"] = "eth_getCode non appelé (mode hors-ligne) — arrêt si code vide le jour J"
            return _check("P7", "preflight", "adresses cibles re-vérifiées (eth_getCode)", "SKIPPED", detail)
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
            return _check("P7", "preflight", "adresses cibles re-vérifiées (eth_getCode)", "FAIL", detail)
        return _check("P7", "preflight", "adresses cibles re-vérifiées (eth_getCode)", "PASS", detail)

    def p8_nonce(self) -> Dict[str, Any]:
        detail: Dict[str, Any] = {"agent": self.agent}
        if not self.agent:
            return _check("P8", "preflight", "nonce (sérialisation stricte)", "UNKNOWN",
                          {"reason": "adresse de l'agent absente"})
        if not self._live_mode():
            detail["note"] = "eth_getTransactionCount non appelé (mode hors-ligne)"
            return _check("P8", "preflight", "nonce (sérialisation stricte)", "SKIPPED", detail)
        try:
            nonce = common.eth_get_transaction_count(self.rpc_url, self.agent, "pending", self.timeout)
        except Exception as exc:
            detail.update({"code": "nonce_conflict", "error": str(exc)})
            return _check("P8", "preflight", "nonce (sérialisation stricte)", "FAIL", detail)
        detail["pending_nonce"] = nonce
        self._live["nonce"] = nonce
        detail["note"] = "une seule transaction en vol : le service signataire sérialise"
        return _check("P8", "preflight", "nonce (sérialisation stricte)", "PASS", detail)

    def p9_balances(self) -> Dict[str, Any]:
        if not self.intent:
            return _check("P9", "preflight", "soldes (gaz + jeton)", "UNKNOWN", {"reason": "aucun intent fourni"})
        detail: Dict[str, Any] = {"agent": self.agent, "safe": self.safe,
                                  "amount_base_units": self.intent.get("amount_base_units")}
        if not self._live_mode():
            detail["note"] = "lectures de soldes non effectuées (mode hors-ligne)"
            return _check("P9", "preflight", "soldes (gaz + jeton)", "SKIPPED", detail)
        if not self.agent or not self.safe:
            detail["code"] = "insufficient_gas_balance"
            detail["reason"] = "adresses agent/safe absentes"
            return _check("P9", "preflight", "soldes (gaz + jeton)", "FAIL", detail)
        gas_estimate = self._live.get("gas_estimate")
        try:
            eth_balance = common.eth_get_balance(self.rpc_url, self.agent, "latest", self.timeout)
            token_balance = calls.decode_uint_result(common.eth_call(
                self.rpc_url, self.asset, calls.balance_of_data(self.safe), "latest", self.timeout))
        except Exception as exc:
            detail.update({"code": "insufficient_token_balance", "error": str(exc)})
            return _check("P9", "preflight", "soldes (gaz + jeton)", "FAIL", detail)
        detail["agent_eth_wei"] = eth_balance
        detail["safe_token_base_units"] = token_balance
        if gas_estimate:
            need = int(math.ceil(gas_estimate * GAS_LIMIT_FACTOR)) * GAS_BALANCE_FACTOR * self.gas_price_wei()
            detail["required_gas_wei"] = need
            if eth_balance < need:
                detail["code"] = "insufficient_gas_balance"
                return _check("P9", "preflight", "soldes (gaz + jeton)", "FAIL", detail)
        else:
            if eth_balance == 0:
                detail["code"] = "insufficient_gas_balance"
                return _check("P9", "preflight", "soldes (gaz + jeton)", "FAIL", detail)
        if token_balance < int(self.intent.get("amount_base_units") or 0):
            detail["code"] = "insufficient_token_balance"
            return _check("P9", "preflight", "soldes (gaz + jeton)", "FAIL", detail)
        return _check("P9", "preflight", "soldes (gaz + jeton)", "PASS", detail)

    def gas_price_wei(self) -> int:
        if "gas_price" in self._live:
            return int(self._live["gas_price"])
        return int(self.gas_baseline_wei)

    def p10_gas_price(self) -> Dict[str, Any]:
        detail: Dict[str, Any] = {"baseline_wei": self.gas_baseline_wei,
                                  "bound_wei": self.gas_baseline_wei * GAS_PRICE_BOUND_FACTOR}
        if not self._live_mode():
            detail["note"] = "eth_gasPrice non lu (mode hors-ligne)"
            return _check("P10", "preflight", "prix du gaz dans les bornes", "SKIPPED", detail)
        try:
            price = common.eth_gas_price(self.rpc_url, self.timeout)
        except Exception as exc:
            detail.update({"code": "gas_price_out_of_bounds", "error": str(exc)})
            return _check("P10", "preflight", "prix du gaz dans les bornes", "FAIL", detail)
        self._live["gas_price"] = price
        detail["gas_price_wei"] = price
        if price > self.gas_baseline_wei * GAS_PRICE_BOUND_FACTOR:
            detail["code"] = "gas_price_out_of_bounds"
            return _check("P10", "preflight", "prix du gaz dans les bornes", "FAIL", detail)
        return _check("P10", "preflight", "prix du gaz dans les bornes", "PASS", detail)

    def p11_simulation(self) -> Dict[str, Any]:
        call = self._exec_call()
        detail: Dict[str, Any] = {"exec_call_to": call["to"] if call else None}
        if not call or not self.agent:
            return _check("P11", "preflight", "simulation eth_call depuis l'agent", "UNKNOWN",
                          {"reason": "calldata ou adresse d'agent indisponible"})
        if not self._live_mode():
            detail["data_prefix"] = call["data"][:42] + "…"
            detail["note"] = ("simulation non exécutée (mode hors-ligne) — le jour J elle part de la clé de "
                              "l'agent pour faire évaluer la politique du module")
            return _check("P11", "preflight", "simulation eth_call depuis l'agent", "SKIPPED", detail)
        try:
            result = self._read("eth_call", [{"from": self.agent, "to": call["to"], "data": call["data"]}, "latest"])
        except common.chain_client.RpcError as exc:
            detail.update({"code": "simulation_revert", "revert_selector": common.revert_selector(exc.data),
                           "error": exc.message})
            return _check("P11", "preflight", "simulation eth_call depuis l'agent", "FAIL", detail)
        except Exception as exc:
            detail.update({"code": "simulation_revert", "error": str(exc)})
            return _check("P11", "preflight", "simulation eth_call depuis l'agent", "FAIL", detail)
        detail["result"] = result
        return _check("P11", "preflight", "simulation eth_call depuis l'agent", "PASS", detail)

    def p12_gas_estimate(self) -> Dict[str, Any]:
        call = self._exec_call()
        detail: Dict[str, Any] = {}
        if not call or not self.agent:
            return _check("P12", "preflight", "estimation de gaz (1,25×)", "UNKNOWN",
                          {"reason": "calldata ou adresse d'agent indisponible"})
        if not self._live_mode():
            detail["note"] = "eth_estimateGas non appelé (mode hors-ligne)"
            detail["factor"] = GAS_LIMIT_FACTOR
            return _check("P12", "preflight", "estimation de gaz (1,25×)", "SKIPPED", detail)
        try:
            estimate = common.eth_estimate_gas(self.rpc_url, self.agent, call["to"], call["data"], self.timeout)
        except Exception as exc:
            detail.update({"code": "gas_estimate_failed", "error": str(exc)})
            return _check("P12", "preflight", "estimation de gaz (1,25×)", "FAIL", detail)
        limit = int(math.ceil(estimate * GAS_LIMIT_FACTOR))
        self._live["gas_estimate"] = estimate
        self._live["gas_limit"] = limit
        detail.update({"estimate": estimate, "gas_limit": limit, "factor": GAS_LIMIT_FACTOR})
        return _check("P12", "preflight", "estimation de gaz (1,25×)", "PASS", detail)

    # --- D1-D10 (test de dérive, B4 §d.3) ------------------------------------

    def _envelope(self) -> Dict[str, Any]:
        return self.envelope or {}

    def _probes(self, check_id: str) -> List[Dict[str, Any]]:
        probes = self._envelope().get("probes") or []
        return [probe for probe in probes if isinstance(probe, dict) and probe.get("check") == check_id]

    def _run_probes(self, check_id: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Exécute les probes ``eth_call`` d'un contrôle (mode en ligne). Échecs nommés."""
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
                    failures.append("{}: observé {} ≠ attendu {}".format(entry["id"], observed, expected))
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
            return _check("D1", "drift", "chaîne (eth_chainId)", "FAIL", detail)
        if self._live_mode():
            try:
                detail["observed"] = common.eth_chain_id(self.rpc_url, self.timeout)
            except Exception as exc:
                detail.update({"code": "ENVELOPE_UNVERIFIED", "error": str(exc)})
                return _check("D1", "drift", "chaîne (eth_chainId)", "UNKNOWN", detail)
            if detail["observed"] != self.policy.chain_id:
                detail["code"] = "ENVELOPE_DRIFT"
                return _check("D1", "drift", "chaîne (eth_chainId)", "FAIL", detail)
            return _check("D1", "drift", "chaîne (eth_chainId)", "PASS", detail)
        envelope_chain = self._envelope().get("chain_id")
        if envelope_chain is None:
            detail["reason"] = "chaîne absente de l'enveloppe"
            return _check("D1", "drift", "chaîne (eth_chainId)", "UNKNOWN", detail)
        if int(envelope_chain) != int(self.policy.chain_id):
            detail["code"] = "ENVELOPE_DRIFT"
            return _check("D1", "drift", "chaîne (eth_chainId)", "FAIL", detail)
        return _check("D1", "drift", "chaîne (eth_chainId)", "PASS", detail)

    def d2_module(self) -> Dict[str, Any]:
        module_ref = self._envelope().get("module") or {}
        address = self.module or module_ref.get("address")
        pinned = module_ref.get("code_sha256_expected")
        detail: Dict[str, Any] = {"module": address, "code_sha256_expected": pinned,
                                  "code_size_expected": module_ref.get("code_size_expected")}
        if not address:
            return _check("D2", "drift", "module (code + codehash épinglé)", "UNKNOWN",
                          {"reason": "adresse du module absente", "code": "ENVELOPE_UNVERIFIED"})
        if self._live_mode():
            try:
                code = common.eth_get_code(self.rpc_url, address, "latest", self.timeout)
            except Exception as exc:
                detail.update({"code": "ENVELOPE_UNVERIFIED", "error": str(exc)})
                return _check("D2", "drift", "module (code + codehash épinglé)", "UNKNOWN", detail)
            body = code[2:] if code.startswith("0x") else code
            detail["code_size_bytes"] = len(body) // 2
            detail["code_sha256"] = common.sha256_hex(bytes.fromhex(body)) if body else ""
            if detail["code_size_bytes"] == 0:
                detail["code"] = "ENVELOPE_DRIFT"
                return _check("D2", "drift", "module (code + codehash épinglé)", "FAIL", detail)
            if pinned and detail["code_sha256"] != str(pinned).lower():
                detail["code"] = "ENVELOPE_DRIFT"
                return _check("D2", "drift", "module (code + codehash épinglé)", "FAIL", detail)
            expected_size = module_ref.get("code_size_expected")
            if expected_size and int(expected_size) != detail["code_size_bytes"]:
                detail["code"] = "ENVELOPE_DRIFT"
                return _check("D2", "drift", "module (code + codehash épinglé)", "FAIL", detail)
            return _check("D2", "drift", "module (code + codehash épinglé)", "PASS", detail)
        if not pinned:
            detail["reason"] = "codehash non épinglé : comparaison impossible hors ligne (à capturer le jour J)"
            return _check("D2", "drift", "module (code + codehash épinglé)", "UNKNOWN", detail)
        return _check("D2", "drift", "module (code + codehash épinglé)", "PASS", detail)

    def d3_members(self) -> Dict[str, Any]:
        envelope_agent = ((self._envelope().get("agent") or {}).get("address"))
        detail: Dict[str, Any] = {"agent_config": self.agent, "agent_envelope": envelope_agent}
        probes, failures = self._run_probes("D3")
        detail["probes"] = probes
        if failures:
            detail["code"] = "ENVELOPE_DRIFT"
            detail["failures"] = failures
            return _check("D3", "drift", "membres du rôle AGENT", "FAIL", detail)
        if envelope_agent and self.agent and str(envelope_agent).lower() != self.agent.lower():
            detail["code"] = "ENVELOPE_DRIFT"
            detail["reason"] = "l'adresse de l'agent de la config ≠ celle de l'enveloppe"
            return _check("D3", "drift", "membres du rôle AGENT", "FAIL", detail)
        if not probes:
            detail["reason"] = ("membres non lisibles hors ligne ; probe eth_call à confirmer sur le contrat "
                                "déployé (getter à figer le jour J)")
            return _check("D3", "drift", "membres du rôle AGENT", "UNKNOWN", detail)
        return _check("D3", "drift", "membres du rôle AGENT", "PASS", detail)

    def d4_targets(self) -> Dict[str, Any]:
        role = self._envelope().get("role") or {}
        targets = role.get("targets")
        detail: Dict[str, Any] = {"declared": targets, "expected_asset": self.policy.asset}
        if not targets:
            return _check("D4", "drift", "cibles du rôle (clearance)", "UNKNOWN",
                          {"reason": "cibles absentes de l'enveloppe", "code": "ENVELOPE_UNVERIFIED"})
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
            detail["reason"] = "cible en Clearance.Target (portée large) : {}".format(broad)
            return _check("D4", "drift", "cibles du rôle (clearance)", "FAIL", detail)
        if addresses != {self.policy.asset.lower()}:
            detail["code"] = "ENVELOPE_DRIFT"
            detail["reason"] = "l'ensemble des cibles ≠ {{USDC}} attendu"
            return _check("D4", "drift", "cibles du rôle (clearance)", "FAIL", detail)
        probes, failures = self._run_probes("D4")
        detail["probes"] = probes
        if failures:
            detail["code"] = "ENVELOPE_DRIFT"
            detail["failures"] = failures
            return _check("D4", "drift", "cibles du rôle (clearance)", "FAIL", detail)
        return _check("D4", "drift", "cibles du rôle (clearance)", "PASS", detail)

    def d5_functions(self) -> Dict[str, Any]:
        role = self._envelope().get("role") or {}
        functions = role.get("functions") or []
        detail: Dict[str, Any] = {"declared": functions, "expected": {
            "target": self.policy.asset, "signature": common.TRANSFER_SIGNATURE,
            "selector": common.SELECTOR_TRANSFER, "clearance": "Function", "operation": "CALL"}}
        if not functions:
            return _check("D5", "drift", "fonctions scopées", "UNKNOWN",
                          {"reason": "fonctions absentes de l'enveloppe", "code": "ENVELOPE_UNVERIFIED"})
        expected_pairs = set()
        problems: List[str] = []
        for function in functions:
            target = str(function.get("target") or "").lower()
            selector = str(function.get("selector") or "").lower()
            clearance = str(function.get("clearance") or "Function").lower()
            operation = str(function.get("operation") or "CALL").upper()
            expected_pairs.add((target, selector))
            if clearance == "target":
                problems.append("fonction en clearance Target (portée large) : {}".format(selector))
            if operation not in ("CALL",):
                problems.append("opération non-CALL sur {} : {}".format(selector, operation))
        wanted = {(self.policy.asset.lower(), common.SELECTOR_TRANSFER)}
        if expected_pairs != wanted:
            problems.append("ensemble (cible, sélecteur) = {} ≠ {} attendu".format(sorted(expected_pairs), sorted(wanted)))
        detail["pairs"] = sorted("{}:{}".format(a, b) for a, b in expected_pairs)
        if problems:
            detail["code"] = "ENVELOPE_DRIFT"
            detail["failures"] = problems
            return _check("D5", "drift", "fonctions scopées", "FAIL", detail)
        probes, failures = self._run_probes("D5")
        detail["probes"] = probes
        if failures:
            detail["code"] = "ENVELOPE_DRIFT"
            detail["failures"] = failures
            return _check("D5", "drift", "fonctions scopées", "FAIL", detail)
        return _check("D5", "drift", "fonctions scopées", "PASS", detail)

    def d6_conditions(self) -> Dict[str, Any]:
        role = self._envelope().get("role") or {}
        conditions = role.get("conditions") or {}
        detail: Dict[str, Any] = {"declared": conditions,
                                  "expected_recipients": sorted(self.policy.allowed_recipients())}
        if not conditions:
            return _check("D6", "drift", "conditions (destinataire, montant)", "UNKNOWN",
                          {"reason": "conditions absentes de l'enveloppe", "code": "ENVELOPE_UNVERIFIED"})
        problems: List[str] = []
        param0 = conditions.get("param0") or {}
        values = {str(value).lower() for value in (param0.get("values") or [])}
        if not values:
            return _check("D6", "drift", "conditions (destinataire, montant)", "UNKNOWN",
                          {"reason": "valeurs de la condition destinataire non renseignées dans l'enveloppe "
                                     "(à coller depuis l'app Roles le jour J)", "code": "ENVELOPE_UNVERIFIED"})
        if str(param0.get("kind")) != "or_equal":
            problems.append("condition destinataire ≠ Or(EqualTo(B), EqualTo(C))")
        if values != set(self.policy.allowed_recipients()):
            problems.append("destinataires de la condition {} ≠ allowlist de la politique {}".format(
                sorted(values), sorted(self.policy.allowed_recipients())))
        param1 = conditions.get("param1") or {}
        if str(param1.get("kind")) != "within_allowance":
            problems.append("condition de montant absente (param1) — un montant non conditionné "
                            "peut consommer l'allowance en un coup")
        elif str(param1.get("allowance_key")) not in (role.get("allowances") or {}):
            problems.append("allowance référencée par la condition introuvable : {}".format(param1.get("allowance_key")))
        if problems:
            detail["code"] = "ENVELOPE_DRIFT"
            detail["failures"] = problems
            return _check("D6", "drift", "conditions (destinataire, montant)", "FAIL", detail)
        return _check("D6", "drift", "conditions (destinataire, montant)", "PASS", detail)

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
                          {"reason": "allowance usdc_daily absente de l'enveloppe", "code": "ENVELOPE_UNVERIFIED"})
        refill = int(daily.get("refill_base_units") or 0)
        max_refill = int(daily.get("max_refill_base_units") or 0)
        period = int(daily.get("period_seconds") or 0)
        problems: List[str] = []
        if refill != max_refill:
            problems.append("refill ({}) ≠ maxRefill ({}) : la rafale de frontière dépasse 2 périodes".format(
                refill, max_refill))
        if (refill, max_refill, period) != (self.policy.allowance_refill, self.policy.allowance_max_refill,
                                            self.policy.allowance_period_seconds):
            problems.append("allowance déclarée {} ≠ politique {}".format(
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
            return _check("D8", "drift", "quota d'appels (CallWithinAllowance)", "UNKNOWN",
                          {"reason": "quota d'appels absent de l'enveloppe", "code": "ENVELOPE_UNVERIFIED"})
        problems: List[str] = []
        if int(quota.get("max_per_period") or -1) != self.policy.max_calls_24h:
            problems.append("quota on-chain {} ≠ politique {}".format(
                quota.get("max_per_period"), self.policy.max_calls_24h))
        if int(quota.get("period_seconds") or 0) != self.policy.allowance_period_seconds:
            problems.append("période du quota {} ≠ {}".format(
                quota.get("period_seconds"), self.policy.allowance_period_seconds))
        if problems:
            detail["code"] = "ENVELOPE_DRIFT"
            detail["failures"] = problems
            return _check("D8", "drift", "quota d'appels (CallWithinAllowance)", "FAIL", detail)
        return _check("D8", "drift", "quota d'appels (CallWithinAllowance)", "PASS", detail)

    def d9_expiration(self) -> Dict[str, Any]:
        scheduled = self.policy.revocation_scheduled_at or (self._envelope().get("revocation_scheduled_at"))
        detail: Dict[str, Any] = {"revocation_scheduled_at": scheduled,
                                  "note": "Allowance Zodiac n'a aucun champ d'expiration (B4 P8) : "
                                          "une révocation planifiée est exigée"}
        if not scheduled:
            detail["code"] = "ENVELOPE_DRIFT"
            return _check("D9", "drift", "expiration / révocation planifiée", "FAIL", detail)
        return _check("D9", "drift", "expiration / révocation planifiée", "PASS", detail)

    def d10_version(self) -> Dict[str, Any]:
        module_ref = self._envelope().get("module") or {}
        version = module_ref.get("version")
        advisory = module_ref.get("advisory_clear")
        detail: Dict[str, Any] = {"version": version, "advisory_clear": advisory,
                                  "codehash_pinned": bool(module_ref.get("code_sha256_expected"))}
        if not version or advisory is not True:
            detail["reason"] = ("version du module non suivie ou avis de sécurité non déclaré clair "
                                "(post-mortems 2026 : ERC-1271 v2.1.0→v2.1.1, padding MultiSend)")
            detail["code"] = "ENVELOPE_UNVERIFIED"
            return _check("D10", "drift", "version du module / avis de sécurité", "UNKNOWN", detail)
        return _check("D10", "drift", "version du module / avis de sécurité", "PASS", detail)

    # --- pilote ---------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        # Ordre d'exécution : P9 (soldes) consomme l'estimation de gaz (P12) et le prix (P10).
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
    """Capture une enveloppe de référence par lecture seule (chainId, bloc, gaz, codes).

    La structure produite est directement consommable par le test de dérive
    (``module``, ``avatar``, ``agent``, ``assets``, ``contracts``) ; le bloc
    ``role`` (cibles/conditions/allowances) et les ``probes`` restent à confirmer
    sur le contrat déployé avec l'app Roles (B4 §d.3, annexe 4).
    """
    chain_id = common.eth_chain_id(rpc_url, timeout)
    if chain_id != chain_id_expected:
        raise common.ConfigurationError(
            "chainId observé {} ≠ {} attendu — capture refusée".format(chain_id, chain_id_expected))
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
        "note": ("enveloppe capturée par lecture seule — `role` (cibles/conditions/allowances) et `probes` "
                 "(calldata des getters) restent à confirmer sur le contrat déployé (B4 §d.3, annexe 4)"),
    }
    module = pick("module") or pick("orvyren_module_address")
    if module:
        envelope["module"] = {**module, "version": None, "advisory_clear": None}
    avatar = pick("safe") or pick("orvyren_safe_address")
    if avatar:
        envelope["avatar"] = {"address": avatar["address"], "label": "Safe de démonstration"}
    agent = pick("agent") or pick("orvyren_agent_address")
    if agent:
        envelope["agent"] = {"address": agent["address"], "label": "EOA jetable membre du rôle AGENT"}
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
        raise common.ConfigurationError("fichier illisible: {}".format(path))
    return data


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="preflight.py",
        description="ORVYREN — préflight 12 contrôles (B5 §c.1) + test de dérive 10 contrôles (B4 §d.3). "
                    "Aucune signature, aucune transaction ; un seul échec bloque.")
    parser.add_argument("--intent", help="fichier JSON d'un intent v1 (validé par intents.validate_intent)")
    parser.add_argument("--policy", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                         "policy.demo.json"),
                        help="politique de démonstration (défaut : policy.demo.json)")
    parser.add_argument("--env-file", help="fichier .env de session (jamais versionné) pour les adresses")
    parser.add_argument("--envelope", help="référence d'enveloppe (envelope.example.json capturé)")
    parser.add_argument("--decision", help="verdict de politique enregistré (comparé à P1)")
    parser.add_argument("--registry", help="registre d'idempotence (JSON) — P4")
    parser.add_argument("--out", help="écrire le rapport JSON à ce chemin")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", default=None, help="aucun réseau (défaut)")
    mode.add_argument("--rpc", action="store_true", help="exécuter les contrôles en ligne (lecture seule)")
    parser.add_argument("--rpc-url", default=os.environ.get("ORVYREN_RPC_URL_BASE_SEPOLIA")
                        or common.DEFAULT_RPC_URL)
    parser.add_argument("--capture-envelope", metavar="OUT",
                        help="capture une enveloppe de référence (mode en ligne, lecture seule)")
    parser.add_argument("--quiet", action="store_true", help="n'imprimer que le verdict")
    args = parser.parse_args(argv)

    mode_value = MODE_RPC if args.rpc else MODE_OFFLINE

    try:
        session = common.SessionConfig.from_env(args.env_file)
        recipients = {label: address for label, address in session.recipients.items() if address}
        policy = common.load_policy_reference(args.policy, recipients)

        if args.capture_envelope:
            if mode_value != MODE_RPC:
                print("ERREUR: --capture-envelope exige --rpc (lecture seule)", file=sys.stderr)
                return EXIT_USAGE
            addresses = dict(common.KNOWN_ADDRESSES)
            for key in common.SessionConfig.REQUIRED_ADDRESS_KEYS:
                value = (session.env.get(key) or "").strip()
                if value:
                    addresses[key.lower()] = value
            envelope = capture_envelope(rpc_url=args.rpc_url, addresses=addresses, session=session)
            common.write_json(args.capture_envelope, envelope)
            print("enveloppe capturée: {} (bloc {}, {} contrats)".format(
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
                    print("intent invalide: [{}] {} — {}".format(error["code"], error["field"], error["detail"]),
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
        print("ERREUR de configuration: {}".format(exc), file=sys.stderr)
        return EXIT_USAGE

    if args.out:
        common.write_json(args.out, report)

    if not args.quiet:
        print("ORVYREN — préflight ({}) : verdict {} — safe_mode {}".format(
            report["mode"], report["verdict"], report["safe_mode"]))
        for check in report["checks"]:
            print("  [{}] {:<5} {:<4} {}".format(
                check["family"][:4], check["status"], check["id"], check["name"]))
        if report["safe_mode"]:
            print("  SAFE MODE : {}".format(", ".join(report["safe_mode_reasons"])))
    else:
        print(report["verdict"])

    return EXIT_FAIL if report["verdict"] == "FAIL" or report["safe_mode"] else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
