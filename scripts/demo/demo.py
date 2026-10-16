#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — kit de démo testnet : **orchestrateur des 5 runs** (W3-D, B5 §e).

    python scripts/demo/demo.py --run A --dry-run
    python scripts/demo/demo.py --run A --execute --case rseth

Runs (B5 §e, dérivés de W2C §g) :

* **A — ALLOW dans l'enveloppe** : intent v1 ``transfer 50 USDC`` → politique
  hors chaîne ``ALLOW`` → préflight (12 contrôles) → signature → reçu →
  vérification (B5 §d). Critères mesurables : ``status = 0x1``, **un seul** log
  Transfer exact, Δ soldes ±50 000 000, compteur de signatures = 1, les 7
  ``kind`` de journal, ``blockHash`` stable après 2 blocs.
* **B — DENY hors chaîne** : B1 150 USDC, B2 destinataire non listé, B3 rejeu ×3,
  B4 ``change_policy`` → **0 signature**, nonce inchangé, soldes inchangés.
* **C — DENY par la chaîne** : calldatas interdits fabriqués directement avec la
  clé de l'agent (C1 allowance, C2 destinataire, C3 admin, C4 cumul, C5 frontière
  de période) → revert attendu, sélecteur capturé, gaz perdu enregistré.
* **D — Kill switch chronométré** : révocation ``assignRoles(false)`` par la Safe
  (2/3), tentative de l'agent → revert ``NotAuthorized(address)`` ;
  ``Roles.roles(AGENT).members(agent) == false`` ; Reset.
* **E — Journal et audit** : export ``audit.jsonl`` chaîné + ``report.md`` +
  vérification indépendante (relecture des ``tx_hash``) + compteurs
  (« N exécutions conformes, M refus hors chaîne, K tentatives forcées refusées »).

Modes : ``--dry-run`` (défaut) est une **répétition hors chaîne** — aucune clé
lue, aucune transaction, hashes factices marqués ``simulated`` ; ``--execute``
envoie réellement (préflight obligatoire, un seul vol à la fois).

Sorties : ``<session>/audit.jsonl`` (append-only chaîné), ``runs/<RUN>_<ts>/``
(summary, criteria, intent, rapports), ``receipts/``, ``export/`` (run E).
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
except ImportError:  # exécution directe : python scripts/demo/demo.py
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

DEFAULT_RECIPIENT_AMOUNT = "100.0"     # RUN A : 100 USDC — décision GELÉE (FREEZE_V2 E2).
RUN_A_AMOUNT = DEFAULT_RECIPIENT_AMOUNT
RUN_D_AMOUNT = "100.0"                  # RUN D (B5 §e.4)
#: Note : l'étude B5 §e.1 écrit 50 USDC et laisse la question ouverte (Q2 §f de B5) ;
#: l'autorité est FREEZE_V2 (E2 = 100 USDC) — le kit applique le gel, et `--amount`
#: permet de rejouer la variante si l'équipe tranche autrement.

EXIT_OK = 0
EXIT_CRITERIA_FAILED = 1
EXIT_USAGE = 2
EXIT_PREREQUISITES = 3
EXIT_CONFIG = 4

#: Placeholders du fichier d'exemple (remplacés le jour J ; ``--execute`` les refuse).
PLACEHOLDER_ADDRESSES = {
    "0x2222222222222222222222222222222222222222",
    "0x3333333333333333333333333333333333333333",
    "0x4444444444444444444444444444444444444444",
    "0x5555555555555555555555555555555555555555",
    "0x9999999999999999999999999999999999999999",
    "0x1111111111111111111111111111111111111111",
}

GAS_LIMIT_DEFAULT = 120_000            # borne haute de la tx via le module (mesure le jour J)


def _short(address: Any) -> str:
    return common.short_address(address)


def _now_iso() -> str:
    return common.utc_now()


class DemoContext:
    """État partagé d'une session de démonstration (journal, registre, adresses)."""

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

    # --- adresses -------------------------------------------------------------

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
                        "{} absente — --execute exige une configuration complète (.env)".format(key))
                addresses[label] = common.normalize_address(fallbacks[label], key)
                self.placeholders_used.append(label)
        self.policy.recipients.setdefault("B", addresses["B"])
        self.policy.recipients.setdefault("C", addresses["C"])
        return addresses

    def require_execute_prerequisites(self) -> None:
        """--execute : adresses réelles, bibliothèque de signature, clé présente."""
        if self.mode != MODE_EXECUTE:
            return
        # Garde-fou chaîne d'abord : la démo est testnet uniquement (Base Sepolia, 84532).
        if os.environ.get("ORVYREN_ALLOW_MAINNET") == "1":
            raise common.ConfigurationError(
                "garde-fou : ORVYREN_ALLOW_MAINNET=1 est posé — la démo est testnet uniquement "
                "(Base Sepolia, 84532). Retirer la variable.")
        if self.placeholders_used:
            raise common.ConfigurationError(
                "--execute refuse les adresses factices ({}): renseigner le .env avec les adresses "
                "réelles de la session (FREEZE_V2 J2)".format(", ".join(sorted(set(self.placeholders_used)))))
        if not self.signer.library_available():
            raise signer_mod.SignerDependencyError(
                "la signature réelle exige eth-account — python -m pip install eth-account")
        if not self.signer.key_present():
            raise signer_mod.SignerError(
                "{} absente : le mode --execute refuse de démarrer sans clé (elle ne vit que dans "
                "l'environnement du signataire)".format(signer_mod.KEY_ENV_NAME))

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
        """Intent d'une action sous approbation : le destinataire reste un ADRESSE AUTORISÉE
        afin que la demande atteigne la règle de périmètre d'action (R8) — comme I3 du dépôt
        (``change_policy`` ne déplace aucun fonds ; le destinataire ne sert qu'à satisfaire R3)."""
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
        """Signe (mode réel) et diffuse la transaction passant par le module, attend le reçu.

        En dry-run : signature simulée, hash factice, **aucun envoi**.
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
        """Émission **brute** (sans l'enveloppe ``exec_with_role``) — cas C3 : l'agent tente une
        action d'administration directe ; le contrat doit la refuser (``onlyOwner`` / ``GS*``)."""
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
        """Persiste le reçu brut + l'entrée RECEIPT (receipt_sha256, règle B6 M4)."""
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
        """Nombre d'entrées SUBMIT du journal de session (critère B.3)."""
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
    print("  critères ({}):".format(run))
    for criterion in criteria:
        print("    [{:>12}] {} — {}".format(criterion["status"], criterion["id"], criterion["description"]))


def _criteria_ok(criteria: List[Dict[str, Any]]) -> bool:
    return all(criterion["status"] not in ("failed",) for criterion in criteria)


# =============================================================================
# RUN A
# =============================================================================

def run_a(ctx: DemoContext, amount: str = RUN_A_AMOUNT) -> Dict[str, Any]:
    """RUN A — ALLOW dans l'enveloppe (les deux verrous disent oui)."""
    ctx.journal_run_start("A")
    signatures_before = ctx.signatures.count()
    intent = ctx.build_transfer(amount=amount, recipient_label="B",
                                justification="RUN A — transfert {} USDC dans l'enveloppe (ALLOW)".format(amount),
                                source={"decision_id": common.ulid(), "case": ctx.case})
    common.write_json(os.path.join(ctx.run_dir, "intent.json"), intent)
    ctx.journal_intent(intent, "A")

    decision = common.evaluate_policy(intent, ctx.policy, seen_intent_ids=ctx.registry.seen_intent_ids())
    payload = common.decision_as_dict(decision, intent=intent, policy=ctx.policy,
                                      context={"placeholders": sorted(set(ctx.placeholders_used))})
    ctx.journal_policy(payload, intent, "A")
    ctx.log("verdict de politique : {} {}".format(decision.verdict, decision.reasons or ""))

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

    # Le préflight précède la réservation : le registre d'idempotence ne doit pas
    # voir l'intent de ce run avant que P1/P4 ne l'aient évalué (B5 §c.1).
    report = ctx.run_preflight(intent, name="preflight")
    if ctx.mode == MODE_EXECUTE and (report["verdict"] == "FAIL" or report["safe_mode"]):
        ctx.journal_outcome(run="A", intent=intent, outcome="REFUSED_BY_PREFLIGHT",
                            detail={"verdict": report["verdict"], "safe_mode_reasons": report["safe_mode_reasons"]})
        summary["status"] = "REFUSED_BY_PREFLIGHT"
        summary["preflight_verdict"] = report["verdict"]
        criteria.append(_criterion("A.1", "receipt.status == 0x1", "failed", "préflight refusé"))
        _write_run_artifacts(ctx, "A", summary, criteria)
        return summary

    ctx.registry.record(intent_id=intent["intent_id"], idempotency_key=intent["idempotency_key"],
                        status="RESERVED", note="run A — préflight passé, signature imminente")

    balances_before = {"safe": ctx.balance_of(ctx.addresses["safe"]),
                       "B": ctx.balance_of(ctx.addresses["B"])} if ctx.mode == MODE_EXECUTE else None

    sent = ctx.execute_tx(intent)
    summary["tx"] = {key: value for key, value in sent.items() if key != "receipt"}
    ctx.log("transaction : {} (simulée={}, envoyée={})".format(sent["tx_hash"][:18] + "…",
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

    # L'OUTCOME est journalisé AVANT l'évaluation des critères : A.5 compte les 7 kind,
    # OUTCOME compris — l'ancien ordre (OUTCOME après l'évaluation) le manquait
    # systématiquement en --execute (mesuré le 2026-10-16).
    if ctx.mode == MODE_DRY:
        ctx.journal_outcome(run="A", intent=intent, outcome="DRY_RUN_SIMULATED",
                            detail={"note": "aucune transaction envoyée — hash factice ; "
                                            "les critères 1/2/3/6 seront mesurés en --execute"})
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
        _criterion("A.2", "exactement un log Transfer correspondant exactement",
                   "met" if (verification and verification["log_counts"]["exact_matches"] == 1) else "pending",
                   verification and verification["log_counts"]),
        _criterion("A.3", "Δ solde Safe = −{} et Δ solde B = +{}".format(units, units),
                   "met" if delta_ok else "pending",
                   {"before": balances_before, "after": balances_after}),
        _criterion("A.4", "compteur de signatures = +1 (simulées incluses en dry-run)",
                   "met" if signatures_after - signatures_before == 1 else "failed",
                   {"before": signatures_before, "after": signatures_after}),
        _criterion("A.5", "les 7 kind de journal présents pour l'intent_id",
                   "met" if all(kind in kinds for kind in required_kinds) else
                   ("pending" if ctx.mode == MODE_DRY else "failed"), sorted(set(kinds))),
        _criterion("A.6", "blockHash stable après 2 blocs",
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
    """Intent déjà enregistré dans la session (pour le rejeu B3), sinon None."""
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
    """RUN B — DENY par la politique hors chaîne (le LLM propose, le système refuse)."""
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
                                        justification="RUN B3 — intent de référence enregistré (rejeu)")
        ctx.registry.record(intent_id=registered["intent_id"],
                            idempotency_key=registered["idempotency_key"],
                            status="REJECTED_DRY_RUN", note="référence B3")
    else:
        ctx.registry.record(intent_id=registered["intent_id"],
                            idempotency_key=registered["idempotency_key"],
                            status="REGISTERED", note="rejeu B3 (déjà enregistré)")

    definitions = [
        ("B1", "transfer 150 USDC (plafond par transaction)",
         ctx.build_transfer(amount="150.0", recipient_label="B",
                            justification="RUN B1 — 150 USDC : au-delà du plafond par transaction"),
         ["AMOUNT_ABOVE_TX_CAP"], "DENY"),
        ("B2", "destinataire non listé (20 USDC)",
         ctx.build_transfer(amount="20.0", recipient_label="D_unlisted",
                            justification="RUN B2 — destinataire hors allowlist (attaque #12)"),
         ["RECIPIENT_NOT_ALLOWED"], "DENY"),
        ("B3", "rejeu du même intent (×3, idempotence)",
         registered, ["INTENT_ALREADY_PROCESSED"], "DENY"),
        ("B4", "change_policy (jamais autonome)",
         ctx.build_action(action="change_policy",
                          justification="RUN B4 — l'agent tente de modifier sa propre enveloppe", amount="100.0"),
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
            ctx.log("{} (essai {}) : {} {}".format(case_id, attempt, decision.verdict, decision.reasons))
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
        _criterion("B.1", "compteur de signatures inchangé sur tout le run",
                   "met" if signatures_after == signatures_before else "failed",
                   {"before": signatures_before, "after": signatures_after}),
        _criterion("B.2", "nonce de l'agent inchangé",
                   "met" if (nonce_before == nonce_after) else ("pending" if nonce_before is None else "failed"),
                   {"before": nonce_before, "after": nonce_after}),
        _criterion("B.3", "aucun tx_hash émis pendant le run (aucun SUBMIT)",
                   "met" if not any_tx_hash else "failed",
                   {"submits_before": submits_before, "submits_after": submits_after,
                    "intents_du_run": b_intent_ids}),
        _criterion("B.4", "4 cas B1-B4 avec verdicts et codes exacts",
                   "met" if all(case["ok"] for case in cases) else "failed", cases),
    ]
    if ctx.mode == MODE_DRY:
        ctx.journal_outcome(run="B", intent=None, outcome="DRY_RUN_OK",
                            detail={"note": "refus hors chaîne exécutés hors ligne (déterministes)"})
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
    """Fabrique les calldatas interdits (C1-C5) — mêmes builders que le chemin nominal."""
    asset = ctx.addresses["asset"]
    agent = ctx.addresses["agent"]
    role = ctx.policy.role_key
    allow_refill = ctx.policy.allowance_max_refill
    return {
        "C1": {
            "label": "transfer 500 USDC via le module (au-delà de l'allowance maxRefill)",
            "call": {"to": ctx.addresses["module"],
                     "data": calls.exec_with_role_data(
                         target=asset, value=0,
                         inner_data=calls.erc20_transfer_data(ctx.addresses["B"], 500_000_000),
                         operation=calls.OPERATION_CALL, role_key=role)},
            "expect": "revert (dépassement d'allowance) ; tx incluse status 0x0, gaz perdu",
            "offline_checks": [
                ("montant 500 000 000 > maxRefill {}".format(allow_refill), 500_000_000 > allow_refill),
            ],
            "revert_expect": ["AllowanceExceeded", "0x"],
        },
        "C2": {
            "label": "transfer 1 USDC vers un destinataire non listé via le module",
            "call": {"to": ctx.addresses["module"],
                     "data": calls.exec_with_role_data(
                         target=asset, value=0,
                         inner_data=calls.erc20_transfer_data(ctx.addresses["D_unlisted"], 1_000_000),
                         operation=calls.OPERATION_CALL, role_key=role)},
            "expect": "revert (condition de destinataire) ; aucun log Transfer",
            "offline_checks": [
                ("destinataire hors allowlist",
                 ctx.addresses["D_unlisted"] not in ctx.policy.allowed_recipients()),
            ],
            "revert_expect": ["ConditionViolation", "0x"],
        },
        "C3a": {
            "label": "l'agent tente allowTarget (auto-élargissement de sa propre cible)",
            "call": {"to": ctx.addresses["module"],
                     "data": calls.allow_target_data(role, asset, calls.CLEARANCE_TARGET)},
            "expect": "revert onlyOwner (aucun droit d'administration — attaque #7)",
            "offline_checks": [
                ("sélecteur allowTarget vérifié 0x7b0da5b2", common.SELECTOR_ALLOW_TARGET == "0x7b0da5b2"),
            ],
            "revert_expect": ["OwnableUnauthorizedAccount", "Unauthorized", "0x"],
        },
        "C3b": {
            "label": "l'agent tente Safe.enableModule (le module a les pleins pouvoirs de la Safe)",
            "call": {"to": ctx.addresses["safe"],
                     "data": calls.safe_enable_module_data(agent)},
            "expect": "revert GS* (seul owner = la Safe elle-même)",
            "offline_checks": [
                ("sélecteur enableModule(address) calculé localement",
                 calls.safe_enable_module_selector().startswith("0x")),
            ],
            "revert_expect": ["GS", "0x"],
        },
        "C4": {
            "label": "boucle 100 + 100 + 100 + 100 (cumul on-chain)",
            "calls": [
                {"to": ctx.addresses["module"],
                 "data": calls.exec_with_role_data(
                     target=asset, value=0,
                     inner_data=calls.erc20_transfer_data(ctx.addresses["B"], 100_000_000),
                     operation=calls.OPERATION_CALL, role_key=role)}
                for _ in range(4)
            ],
            "expect": "les 3 premières passent ; la 4ᵉ revert (dépassement cumulé, attaque #8)",
            "offline_checks": [
                ("100+100+100 = 300 000 000 ≤ maxRefill", 300_000_000 <= allow_refill),
                ("100+100+100+100 = 400 000 000 > maxRefill", 400_000_000 > allow_refill),
            ],
            "revert_expect": ["AllowanceExceeded", "0x"],
        },
    }


def run_c(ctx: DemoContext) -> Dict[str, Any]:
    """RUN C — DENY par la chaîne (on contourne volontairement le verrou hors chaîne)."""
    ctx.journal_run_start("C")
    cases = _c_for(ctx)
    results: List[Dict[str, Any]] = []
    criteria: List[Dict[str, Any]] = []

    for case_id, spec in cases.items():
        entry: Dict[str, Any] = {"case": case_id, "label": spec["label"], "expect": spec["expect"],
                                 "sent": False}
        entry["offline_checks"] = [{"description": description, "ok": bool(ok)}
                                   for description, ok in spec.get("offline_checks", [])]

        # Contrôle de construction : le calldata doit décoder vers ce qu'on croit avoir fabriqué.
        primary = spec.get("call") or (spec.get("calls") or [{}])[0]
        decoded = None
        if case_id in ("C1", "C2", "C4"):
            decoded = calls.decode_exec_with_role(primary["data"])
            inner = calls.decode_erc20_transfer(decoded["inner_data"])
            entry["decoded"] = {"target": decoded["target"], "role_key": decoded["role_key"],
                                "inner_to": inner["to"], "inner_value": inner["value"],
                                "operation": decoded["operation"]}
            entry["offline_checks"].append({
                "description": "aller-retour calldata (exec → transfer) cohérent",
                "ok": decoded["target"].lower() == ctx.addresses["asset"].lower()
                      and decoded["operation"] == 0})
        elif case_id == "C3a":
            decoded = calls.allow_target_data(ctx.policy.role_key, ctx.addresses["asset"],
                                              calls.CLEARANCE_TARGET)
            entry["offline_checks"].append({
                "description": "calldata allowTarget complet (sélecteur + 3 mots)",
                "ok": decoded.startswith(common.SELECTOR_ALLOW_TARGET) and len(decoded) == 10 + 3 * 64})
        elif case_id == "C3b":
            entry["offline_checks"].append({
                "description": "calldata enableModule complet",
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
                    # C3 : émission brute (sans enveloppe exec_with_role) — l'agent tente une
                    # action d'administration directe ; le contrat doit la refuser.
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

    # C5 — frontière de période : la chaîne laisse passer, le compteur glissant refuse.
    boundary_first = ctx.build_transfer(amount="100.0", recipient_label="B",
                                        justification="RUN C5a — dépense à T−1 s de la frontière")
    boundary_second = ctx.build_transfer(amount="100.0", recipient_label="B",
                                         justification="RUN C5b — dépense à T+1 s (compteur glissant)")
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
        "label": "frontière de période : 2 dépenses de 100 USDC encadrant la frontière",
        "first": {"verdict": decision_first.verdict, "reasons": decision_first.reasons,
                  "cumulative_before": 150.0},
        "second": {"verdict": decision_second.verdict, "reasons": decision_second.reasons,
                   "cumulative_before": 250.0},
        "expect": ("les deux passent on-chain (limite assumée, rafale maxRefill+refill) mais le compteur "
                   "glissant hors chaîne refuse la seconde"),
        "ok": decision_first.verdict == "ALLOW" and decision_second.verdict == "DENY"
              and "AMOUNT_ABOVE_PERIOD_CAP" in decision_second.reasons,
    }
    ctx.log("C5 : hors chaîne {} puis {} {}".format(boundary["first"]["verdict"],
                                                    boundary["second"]["verdict"], boundary["second"]["reasons"]))

    offline_ok = all(all(check["ok"] for check in entry["offline_checks"]) for entry in results)
    criteria = [
        _criterion("C.1", "calldatas forcés construits et décodés (C1-C4)", "met" if offline_ok else "failed",
                   [entry["case"] for entry in results]),
        _criterion("C.2", "C1/C2/C4 : revert attendu, sélecteur capturé, gaz enregistré",
                   "pending" if ctx.mode == MODE_DRY else
                   ("met" if all(entry.get("sends") and all(str(s.get("status")) in ("0x0", "0") for s in entry["sends"])
                                 for entry in results if entry["case"] in ("C1", "C2")) else "failed")),
        _criterion("C.3", "C3 : l'agent n'a aucun droit d'administration (revert des deux appels)",
                   "pending" if ctx.mode == MODE_DRY else
                   ("met" if all(entry.get("sends") and all(str(s.get("status")) in ("0x0", "0") for s in entry["sends"])
                                 for entry in results if entry["case"] in ("C3a", "C3b")) else "failed")),
        _criterion("C.4", "C5 : 2 exécutions chaîne + 1 refus hors chaîne démontrés",
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
    """RUN D — kill switch chronométré (K1 : assignRoles(false) par la Safe)."""
    ctx.journal_run_start("D")
    criteria: List[Dict[str, Any]] = []
    timings: Dict[str, Any] = {"signature_collection": None, "inclusion": None, "effect": None}
    started = common.utc_now()

    intent = ctx.build_transfer(amount=RUN_D_AMOUNT, recipient_label="B",
                                justification="RUN D — intent ALLOW préparé, non envoyé (kill switch)")
    common.write_json(os.path.join(ctx.run_dir, "intent.json"), intent)
    ctx.journal_intent(intent, "D")
    decision = common.evaluate_policy(intent, ctx.policy, seen_intent_ids=ctx.registry.seen_intent_ids())
    ctx.journal_policy(common.decision_as_dict(decision, intent=intent, policy=ctx.policy), intent, "D")
    ctx.registry.record(intent_id=intent["intent_id"], idempotency_key=intent["idempotency_key"],
                        status="PREPARED", note="RUN D — intent non envoyé (kill switch)")

    revocation = calls.assign_roles_data(ctx.addresses["agent"], [ctx.policy.role_key], [False])
    reset = calls.assign_roles_data(ctx.addresses["agent"], [ctx.policy.role_key], [True])
    instruction = {
        "schema": "orvyren-safe-instruction/v1",
        "executed_by": "la Safe 2/3 (2 signatures) — JAMAIS par l'agent",
        "to": ctx.addresses["module"],
        "data": revocation,
        "description": "assignRoles(agent, [AGENT], [false]) — retire le rôle AGENT (K1)",
        "verify_after": "Roles.roles(AGENT).members(agent) == false (eth_call)",
        "reset": {"to": ctx.addresses["module"], "data": reset,
                  "description": "assignRoles(agent, [AGENT], [true]) — reset après la démo"},
        "expected_agent_revert": {"selector": common.ERROR_NOT_AUTHORIZED,
                                  "name": "NotAuthorized(address) — mesuré sur Base Sepolia le 2026-10-15",},
    }
    common.write_json(os.path.join(ctx.run_dir, "revocation_instruction.json"), instruction)
    ctx.log("instruction de révocation écrite (à exécuter depuis la Safe) : "
            "assignRoles(agent, [AGENT], [false]) — sélecteur {}".format(common.SELECTOR_ASSIGN_ROLES))
    decoded = calls.decode_assign_roles(revocation)
    criteria.append(_criterion("D.1", "calldata K1 construit et vérifié (aller-retour)",
                               "met" if (decoded["member"] == ctx.addresses["agent"]
                                         and decoded["role_keys"] == [ctx.policy.role_key]
                                         and decoded["enabled"] == [False]) else "failed", decoded))

    attempt: Dict[str, Any] = {"sent": False}
    if ctx.mode == MODE_EXECUTE:
        if decision.verdict != "ALLOW":
            attempt = {"sent": False, "reason": "intent D refusé par la politique: {}".format(decision.reasons)}
        else:
            if revocation_tx:
                timings["revocation_tx"] = revocation_tx
                try:
                    receipt_rev = common.rpc(ctx.rpc_url, "eth_getTransactionReceipt", [revocation_tx])
                    timings["inclusion"] = {
                        "tx_hash": revocation_tx,
                        "block_number": common.hex_to_int(receipt_rev.get("blockNumber")) if receipt_rev else None,
                        "status": receipt_rev.get("status") if receipt_rev else "non inclus",
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
                attempt["status"] = "non incluse (issue valide si suffisamment retardée — B5 §e.4)"
    else:
        attempt = {"sent": False, "reason": "dry-run : répétition, aucune révocation réelle"}

    criteria.extend([
        _criterion("D.2", "tentative de l'agent : status 0x0 (ou non incluse) après révocation",
                   "pending" if ctx.mode == MODE_DRY else
                   ("met" if attempt.get("status") in ("0x0", "0", None) else "failed"), attempt),
        _criterion("D.3", "sélecteur de revert constaté = {}".format(common.ERROR_NOT_AUTHORIZED),
                   "pending" if ctx.mode == MODE_DRY else
                   ("met" if (attempt.get("revert") or {}).get("revert_selector") == common.ERROR_NOT_AUTHORIZED
                    else "failed"), attempt.get("revert")),
        _criterion("D.4", "latences (a) collecte, (b) inclusion, (c) effet affichées",
                   "pending" if ctx.mode == MODE_DRY else "met", timings),
        _criterion("D.5", "révocation vérifiée indépendamment (members == false) puis reset préparé",
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
    """RUN E — journal et audit : export, vérification indépendante, compteurs."""
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
        "# ORVYREN — rapport de session de démonstration",
        "",
        "- session : `{}`".format(common.display_path(ctx.session_dir)),
        "- run_id : `{}` · cas : `{}` · mode : **{}**".format(ctx.run_id, ctx.case, ctx.mode),
        "- chaîne : Base Sepolia (84532) — testnet uniquement, aucun argent réel",
        "",
        "## Journal (append-only chaîné SHA-256)",
        "",
        "- enregistrements : **{}**".format(chain_report["records"]),
        "- chaîne recalculée : **{}**".format("OK (aucune écriture détectée)" if chain_report["ok"] else "RUPTURE"),
        "- têtes de flux : `{}`".format(json.dumps(chain_report["heads"], ensure_ascii=False)),
        "",
        "## Compteurs",
        "",
        "- exécutions autorisées (entrées POLICY ALLOW) : {}".format(len(allow_policies)),
        "- refus hors chaîne (POLICY DENY) : {}".format(len(denials)),
        "- demandes d'approbation (REQUIRE_APPROVAL) : {}".format(len(approvals)),
        "- transactions soumises : {} · reçus enregistrés : {}".format(len(submits), len(receipts)),
        "- signatures émises par le service : {}".format(ctx.signatures.count()),
        "",
        "## Vérification indépendante (relecture des tx_hash)",
        "",
    ]
    if ctx.mode == MODE_EXECUTE:
        conforms = len([check for check in chain_checks if check.get("verification_ok")])
        forced_failed = len([check for check in chain_checks if str(check.get("status")) in ("0x0", "0")])
        report_lines.append("- {} exécutions conformes, {} refus hors chaîne, {} tentatives forcées "
                            "refusées par la chaîne".format(conforms, len(denials), forced_failed))
    else:
        report_lines.append("- confrontation à la chaîne non exécutée (dry-run) — relancer le run E "
                            "en `--execute --rpc` après le run A réel")
    report_lines.extend([
        "",
        "## Ce que ce rapport ne prouve pas",
        "",
        "- les prix du testnet ne sont pas des données de marché (aucune performance n'est revendiquée) ;",
        "- en dry-run, **aucune transaction n'a été envoyée** : les hashes sont factices et marqués `simulated` ;",
        "- la couverture n'est pas l'exhaustivité : ce qui n'est pas journalisé n'existe pas pour le relecteur.",
        "",
    ])
    report_path = os.path.join(ctx.session_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(report_lines))
    ctx.journal.append("OUTCOME", payload={"run": "E", "export": "export/manifest.json",
                                           "report": "report.md", "chain_ok": chain_report["ok"],
                                           "chain_checks": chain_checks})

    criteria = [
        _criterion("E.1", "chaîne de hash recalculée OK (aucune écriture détectée)",
                   "met" if chain_report["ok"] else "failed", chain_report["errors"][:5]),
        _criterion("E.2", "écart journal ↔ chaîne = 0",
                   "pending" if ctx.mode == MODE_DRY else
                   ("met" if all(check.get("verification_ok", check.get("status") in ("0x0", "0"))
                                 for check in chain_checks) else "failed"), chain_checks),
        _criterion("E.3", "le rapport liste refus et échecs (première classe)",
                   "met" if (denials or approvals) else "pending",
                   {"deny": len(denials), "require_approval": len(approvals)}),
        _criterion("E.4", "compteurs exportés (manifest.json)",
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
    raise ValueError("run inconnu: {}".format(run))


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="demo.py",
        description="ORVYREN — orchestrateur des 5 runs de démonstration testnet (A ALLOW · B DENY hors chaîne · "
                    "C DENY par la chaîne · D kill switch · E journal/audit). "
                    "Dry-run par défaut : aucune clé, aucune transaction.")
    parser.add_argument("--run", required=True, choices=list(RUNS) + [run.lower() for run in RUNS],
                        help="run à exécuter : A, B, C, D ou E")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=None,
                      help="répétition hors chaîne : signatures simulées, hashes factices (défaut)")
    mode.add_argument("--execute", action="store_true",
                      help="exécution réelle (exige .env complet, eth-account et ORVYREN_PRIVATE_KEY)")
    parser.add_argument("--case", default="rseth",
                        help="étiquette de cas/épisode journalisée (défaut : rseth ; ex. usdc-2023-03)")
    parser.add_argument("--session", default=None,
                        help="répertoire de session (défaut : evidence/demo_runs/<case>)")
    parser.add_argument("--env-file", default=None, help="fichier .env de session (jamais versionné)")
    parser.add_argument("--policy", default=None, help="politique (défaut : policy.demo.json)")
    parser.add_argument("--envelope", default=None,
                        help="enveloppe de référence capturée (envelope.example.json complété)")
    parser.add_argument("--rpc-url", default=None, help="RPC Base Sepolia (défaut : variable d'env ou endpoint public)")
    parser.add_argument("--revocation-tx", default=None,
                        help="run D : hash de la transaction de révocation exécutée par la Safe (chronométrage)")
    parser.add_argument("--amount", default=None,
                        help="run A : montant en USDC (défaut 100.0 — décision gelée FREEZE_V2 E2 ; "
                             "B5 §e.1 écrivait 50, écart ouvert Q2 de B5)")
    parser.add_argument("--quiet", action="store_true", help="sortie minimale")
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
        print("ERREUR de configuration: {}".format(exc), file=sys.stderr)
        return EXIT_CONFIG
    except signer_mod.SignerError as exc:
        print("ERREUR du signataire: {}".format(exc), file=sys.stderr)
        return EXIT_PREREQUISITES

    print("ORVYREN — run {} ({}) · session {}".format(
        run, ctx.mode, common.display_path(ctx.session_dir)))
    if ctx.placeholders_used:
        print("  (adresses factices de répétition : {})".format(", ".join(sorted(set(ctx.placeholders_used)))))

    try:
        summary = execute_run(run, ctx, revocation_tx=args.revocation_tx, amount=args.amount)
    except signer_mod.SignerDependencyError as exc:
        print("ERREUR du signataire: {}".format(exc), file=sys.stderr)
        return EXIT_PREREQUISITES
    except signer_mod.SignerError as exc:
        print("ERREUR du signataire: {}".format(exc), file=sys.stderr)
        return EXIT_PREREQUISITES
    except common.chain_client.ChainError as exc:
        print("ERREUR réseau/RPC: {}".format(exc), file=sys.stderr)
        return EXIT_PREREQUISITES

    criteria = summary.get("criteria") or []
    ok = _criteria_ok(criteria)
    print("")
    print("  run {} : {} — {}".format(run, summary.get("status"), "critères OK" if ok else "CRITÈRES NON SATISFAITS"))
    print("  artefacts : {}".format(common.display_path(ctx.run_dir)))
    print("  journal   : {}".format(common.display_path(os.path.join(ctx.session_dir, "audit.jsonl"))))
    return EXIT_OK if ok else EXIT_CRITERIA_FAILED


if __name__ == "__main__":
    sys.exit(main())
