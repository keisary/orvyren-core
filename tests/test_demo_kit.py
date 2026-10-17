#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — bench du kit de démo testnet (W3-D) : tests **hors chaîne**.

Aucun réseau, aucune clé, aucune transaction : tout tourne sur des fixtures
locales (répertoires temporaires). Couverture :

* hachages et sélecteurs vérifiés (Keccak-256 Python pur, vecteurs connus) ;
* encodage/décodage ABI des calldatas du kit (aller-retour) ;
* schéma d'intent v1 (montants décimaux, champs inconnus, échéances, clé d'idempotence) ;
* journal append-only chaîné SHA-256 (détection d'altération) ;
* préflight 12 contrôles + test de dérive 10 contrôles sur configuration factice ;
* dry-run des runs A, B, C, D, E (orchestrateur), y compris l'absence de secret ;
* vérification de reçu (règle d'unicité, enveloppe, échec de première classe) ;
* signataire en mode simulé ;
* paquet d'audit (HASHES.txt, bundle_digest, vérificateur embarqué).

Run: python -m pytest tests/test_demo_kit.py -q
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from demo import build_audit_packet, calls, common, demo, intents  # noqa: E402
from demo import preflight as preflight_mod  # noqa: E402
from demo import signer as signer_mod  # noqa: E402
from demo import verify_receipt  # noqa: E402

from orvyren.execution import verify as base_verify  # noqa: E402

try:  # dépendance optionnelle du signataire (isolée au module signer)
    import eth_account  # noqa: F401
    HAVE_ETH_ACCOUNT = True
except ImportError:  # pragma: no cover - environnement sans la dépendance optionnelle
    HAVE_ETH_ACCOUNT = False

DEMO_DIR = os.path.join(ROOT, "scripts", "demo")
ENVELOPE_EXAMPLE = os.path.join(DEMO_DIR, "envelope.example.json")

SAFE = "0x2222222222222222222222222222222222222222"
AGENT = "0x3333333333333333333333333333333333333333"
MODULE = "0x4444444444444444444444444444444444444444"
USDC = "0x036cbd53842c5426634e7929541ec2318f3dcf7e"
B = "0x1111111111111111111111111111111111111111"
C = "0x5555555555555555555555555555555555555555"
D_UNLISTED = "0x9999999999999999999999999999999999999999"

FAKE_ENV = {
    "ORVYREN_RPC_URL_BASE_SEPOLIA": "https://sepolia.base.org",
    "ORVYREN_CHAIN_ID": "84532",
    "ORVYREN_SAFE_ADDRESS": SAFE,
    "ORVYREN_AGENT_ADDRESS": AGENT,
    "ORVYREN_MODULE_ADDRESS": MODULE,
    "ORVYREN_USDC_ADDRESS": USDC,
    "ORVYREN_RECIPIENT_B": B,
    "ORVYREN_RECIPIENT_C": C,
    "ORVYREN_RECIPIENT_UNLISTED": D_UNLISTED,
}


def fake_envelope(**overrides):
    envelope = {
        "schema": "orvyren-envelope/v1",
        "chain_id": 84532,
        "role_key": common.ROLE_KEY_AGENT,
        "module": {"address": MODULE, "code_size_expected": 24409, "code_sha256_expected": None,
                   "version": "v1.4.1", "advisory_clear": True},
        "avatar": {"address": SAFE},
        "agent": {"address": AGENT},
        "role": {
            "targets": [{"address": USDC, "clearance": "Function"}],
            "functions": [{"target": USDC, "signature": common.TRANSFER_SIGNATURE,
                           "selector": common.SELECTOR_TRANSFER, "clearance": "Function",
                           "operation": "CALL"}],
            "conditions": {"param0": {"kind": "or_equal", "values": [B, C]},
                           "param1": {"kind": "within_allowance", "allowance_key": "usdc_daily"}},
            "allowances": {"usdc_daily": {"refill_base_units": 300000000,
                                          "max_refill_base_units": 300000000, "period_seconds": 86400}},
            "call_quota": {"key": "calls_daily", "max_per_period": 10, "period_seconds": 86400},
        },
        "probes": [],
    }
    envelope.update(overrides)
    return envelope


class TempSessionMixin(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_demo_test_")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def make_policy(self, **overrides):
        recipients = {"B": B, "C": C, "D_unlisted": D_UNLISTED}
        policy = common.load_policy_reference(os.path.join(DEMO_DIR, "policy.demo.json"), recipients)
        for key, value in overrides.items():
            setattr(policy, key, value)
        return policy

    def make_context(self, *, run_case="rseth", mode=demo.MODE_DRY, env=None, envelope=True):
        session_dir = os.path.join(self.tmp, "session_{}_{}".format(run_case, mode.replace("-", "_")))
        env_file = os.path.join(self.tmp, "session_{}_{}.env".format(run_case, mode.replace("-", "_")))
        with open(env_file, "w", encoding="utf-8") as handle:
            for key, value in (env or FAKE_ENV).items():
                handle.write("{}={}\n".format(key, value))
        ctx = demo.DemoContext(case=run_case, mode=mode, session_dir=session_dir,
                               env_file=env_file,
                               policy_path=os.path.join(DEMO_DIR, "policy.demo.json"),
                               envelope_path=ENVELOPE_EXAMPLE if envelope else None,
                               quiet=True)
        return ctx


# =============================================================================
# hachages, sélecteurs, ABI
# =============================================================================

class TestHashesAndSelectors(unittest.TestCase):
    def test_keccak_vectors(self):
        self.assertEqual(common.keccak256(b"").hex(), common.KECCAK_EMPTY)
        self.assertEqual(common.keccak256(b"abc").hex(), common.KECCAK_ABC)

    def test_verified_selectors(self):
        self.assertEqual(common.selector("transfer(address,uint256)"), "0xa9059cbb")
        self.assertEqual(common.selector("balanceOf(address)"), "0x70a08231")
        self.assertEqual(common.selector("assignRoles(address,bytes32[],bool[])"), "0x957ed2b3")
        self.assertEqual(
            common.selector("execTransactionWithRole(address,uint256,bytes,uint8,bytes32,bool)"),
            "0xc6fe8747")
        self.assertEqual(common.selector("allowTarget(bytes32,address,uint8)"), "0x7b0da5b2")
        self.assertEqual(calls.safe_enable_module_selector(), "0x610b5925")

    def test_transfer_topic_matches_repo_constant(self):
        self.assertEqual(common.TRANSFER_TOPIC, base_verify.TRANSFER_TOPIC)

    def test_role_key_agent_encoding(self):
        self.assertEqual(common.ROLE_KEY_AGENT,
                         "0x4147454e54" + "00" * 27)
        self.assertEqual(len(common.ROLE_KEY_AGENT), 66)

    def test_average_weights_helper(self):
        self.assertEqual(preflight_mod._weights([1, 2, 3]), 2.0)
        self.assertEqual(preflight_mod._weights([1, 2, 3, 4]), 2.5)
        self.assertEqual(preflight_mod._weights([]), 0.0)


class TestAbiRoundTrips(unittest.TestCase):
    def test_transfer_round_trip(self):
        data = calls.erc20_transfer_data(B, 50_000_000)
        self.assertEqual(data[:10], "0xa9059cbb")
        decoded = calls.decode_erc20_transfer(data)
        self.assertEqual(decoded["to"], B)
        self.assertEqual(decoded["value"], 50_000_000)

    def test_exec_with_role_round_trip(self):
        inner = calls.erc20_transfer_data(B, 500_000_000)
        data = calls.exec_with_role_data(target=USDC, value=0, inner_data=inner, operation=0,
                                         role_key=common.ROLE_KEY_AGENT)
        decoded = calls.decode_exec_with_role(data)
        self.assertEqual(decoded["target"], USDC)
        self.assertEqual(decoded["operation"], 0)
        self.assertEqual(decoded["role_key"], common.ROLE_KEY_AGENT)
        self.assertTrue(decoded["should_revert"])
        self.assertEqual(decoded["inner_data"], inner)
        # 6 mots d'en-tête + longueur + données (alignées sur 32 octets)
        inner_chars = len(inner) - 2
        padded = ((inner_chars + 63) // 64) * 64
        self.assertEqual(len(data), 10 + 6 * 64 + 64 + padded)

    def test_assign_roles_round_trip(self):
        data = calls.assign_roles_data(AGENT, [common.ROLE_KEY_AGENT], [False])
        decoded = calls.decode_assign_roles(data)
        self.assertEqual(decoded["member"], AGENT)
        self.assertEqual(decoded["role_keys"], [common.ROLE_KEY_AGENT])
        self.assertEqual(decoded["enabled"], [False])

    def test_assign_roles_two_roles(self):
        data = calls.assign_roles_data(AGENT, [common.ROLE_KEY_AGENT, "0x" + "11" * 32], [True, False])
        decoded = calls.decode_assign_roles(data)
        self.assertEqual(decoded["enabled"], [True, False])
        self.assertEqual(len(decoded["role_keys"]), 2)

    def test_balance_of_and_allowance_data(self):
        self.assertEqual(calls.balance_of_data(SAFE), "0x70a08231" + SAFE[2:].rjust(64, "0"))
        self.assertEqual(len(calls.allowance_data(SAFE, MODULE)), 10 + 128)

    def test_delegatecall_operation_accepted_but_recorded(self):
        data = calls.exec_with_role_data(target=USDC, value=0,
                                         inner_data=calls.erc20_transfer_data(B, 1),
                                         operation=calls.OPERATION_DELEGATECALL,
                                         role_key=common.ROLE_KEY_AGENT)
        self.assertEqual(calls.decode_exec_with_role(data)["operation"], 1)

    def test_invalid_operation_refused(self):
        with self.assertRaises(calls.CalldataError):
            calls.exec_with_role_data(target=USDC, value=0, inner_data="0x00", operation=7,
                                      role_key=common.ROLE_KEY_AGENT)


# =============================================================================
# intent v1
# =============================================================================

class TestIntents(unittest.TestCase):
    def build(self, **overrides):
        kwargs = dict(chain_id=84532, account=SAFE, asset=USDC, amount="50.0", recipient=B,
                      expiry_minutes=15, justification="test")
        kwargs.update(overrides)
        return intents.build_transfer_intent(**kwargs)

    def test_amount_base_units(self):
        self.assertEqual(intents.amount_to_base_units("50.0", 6), 50_000_000)
        self.assertEqual(intents.amount_to_base_units("0.000001", 6), 1)
        self.assertEqual(intents.base_units_to_amount(50_000_000, 6), "50.000000")

    def test_scientific_notation_refused(self):
        with self.assertRaises(intents.IntentError):
            intents.amount_to_base_units("5e1", 6)

    def test_negative_and_zero_refused(self):
        with self.assertRaises(intents.IntentError):
            intents.amount_to_base_units("-5.0", 6)
        with self.assertRaises(intents.IntentError):
            intents.amount_to_base_units("0", 6)

    def test_too_many_decimals_refused(self):
        with self.assertRaises(intents.IntentError):
            intents.amount_to_base_units("1.1234567", 6)

    def test_float_amount_refused(self):
        with self.assertRaises(intents.IntentError):
            intents.amount_to_base_units(50.0, 6)

    def test_built_intent_validates(self):
        intent = self.build()
        ok, errors = intents.validate_intent(intent, ttl_minutes=15)
        self.assertTrue(ok, errors)
        self.assertEqual(intent["schema_version"], "intent/v1")
        self.assertEqual(intent["function"], "transfer(address,uint256)")
        self.assertEqual(intent["params"]["value"], "50000000")

    def test_idempotency_key_deterministic(self):
        intent = self.build()
        self.assertEqual(intent["idempotency_key"], intents.compute_idempotency_key(intent))
        # elle ne dépend NI de intent_id NI de created_at
        other = dict(intent, intent_id="01ZZZZZZZZZZZZZZZZZZZZZZZZ", created_at="2026-10-15T00:00:00Z")
        self.assertEqual(intents.compute_idempotency_key(other), intent["idempotency_key"])

    def test_unknown_field_refused(self):
        intent = self.build()
        intent["extra"] = 1
        ok, errors = intents.validate_intent(intent)
        self.assertFalse(ok)
        self.assertIn("SCHEMA_UNKNOWN_FIELD", [error["code"] for error in errors])

    def test_unrepaired_address_refused(self):
        """Une adresse en casse mixte (checksum) n'est pas réparée : elle est refusée."""
        intent = self.build()
        intent["recipient"] = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
        ok, errors = intents.validate_intent(intent)
        self.assertFalse(ok)
        self.assertIn("SCHEMA_ADDRESS", [error["code"] for error in errors])

    def test_expired_intent_refused(self):
        intent = self.build()
        intent["expiry"] = "2020-01-01T00:00:00Z"
        ok, errors = intents.validate_intent(intent)
        self.assertFalse(ok)
        self.assertIn("INTENT_EXPIRED", [error["code"] for error in errors])

    def test_amount_base_units_recomputed(self):
        intent = self.build()
        intent["amount_base_units"] = "500000000000000000000"
        ok, errors = intents.validate_intent(intent)
        self.assertFalse(ok)
        self.assertIn("AMOUNT_BASE_UNITS_MISMATCH", [error["code"] for error in errors])

    def test_calldata_matches_expected(self):
        intent = self.build()
        built = intents.intent_calldata(intent)
        self.assertEqual(built["to"], USDC)
        self.assertEqual(built["data"], "0xa9059cbb" + B[2:].rjust(64, "0") + "{:064x}".format(50_000_000))

    def test_action_intent_has_no_function(self):
        intent = intents.build_action_intent(action="change_policy", chain_id=84532, account=SAFE,
                                             asset=USDC, amount="1.0", recipient=B)
        self.assertEqual(intent["function"], "")
        ok, errors = intents.validate_intent(intent)
        self.assertTrue(ok, errors)


# =============================================================================
# journal, registre, pause, signatures
# =============================================================================

class TestJournal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_journal_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.path = os.path.join(self.tmp, "audit.jsonl")

    def test_chain_and_verify(self):
        journal = common.Journal(self.path, run_id="01RUN", episode="rseth")
        journal.append("INTENT", payload={"intent_id": "I1"})
        journal.append("POLICY", payload={"verdict": "ALLOW"})
        report = journal.verify()
        self.assertTrue(report["ok"])
        self.assertEqual(report["records"], 2)
        self.assertEqual(report["heads"]["exec"], journal.head_hash("exec"))

    def test_tampering_detected(self):
        journal = common.Journal(self.path, run_id="01RUN", episode="rseth")
        journal.append("INTENT", payload={"amount": "50.0"})
        journal.append("POLICY", payload={"verdict": "ALLOW"})
        lines = open(self.path, "r", encoding="utf-8").read().splitlines()
        lines[0] = lines[0].replace('"50.0"', '"99.9"')
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        report = journal.verify()
        self.assertFalse(report["ok"])
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RECORD_HASH_MISMATCH", codes)

    def test_smart_tamper_breaks_the_chain(self):
        """Un faussaire qui recalcule le hash de la ligne modifiée casse la ligne suivante."""
        journal = common.Journal(self.path, run_id="01RUN", episode="rseth")
        journal.append("INTENT", payload={"amount": "50.0"})
        journal.append("POLICY", payload={"verdict": "ALLOW"})
        lines = open(self.path, "r", encoding="utf-8").read().splitlines()
        record = json.loads(lines[0].replace('"50.0"', '"99.9"'))
        record.pop("record_hash")
        record["record_hash"] = common.sha256_hex(common.canonical_json(record).encode("utf-8"))
        lines[0] = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        report = journal.verify()
        self.assertFalse(report["ok"])
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("PREV_HASH_MISMATCH", codes)

    def test_kinds_per_intent(self):
        journal = common.Journal(self.path, run_id="01RUN", episode="rseth")
        journal.append("INTENT", payload={}, refs={"intent_id": "I1"})
        journal.append("SUBMIT", payload={}, refs={"intent_id": "I1"})
        journal.append("INTENT", payload={}, refs={"intent_id": "I2"})
        self.assertEqual(journal.kinds("I1"), ["INTENT", "SUBMIT"])

    def test_canonical_json_is_stable(self):
        self.assertEqual(common.canonical_json({"b": 1, "a": [1, 2]}), '{"a":[1,2],"b":1}')


class TestRegistryPauseSignatures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_state_")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_registry_round_trip(self):
        registry = common.Registry(os.path.join(self.tmp, "registry.json"))
        self.assertFalse(registry.has_key("0xabc"))
        registry.record(intent_id="I1", idempotency_key="0xabc", status="RESERVED")
        self.assertTrue(registry.has_key("0xabc"))
        self.assertIn("I1", registry.seen_intent_ids())

    def test_pause_flag_env_and_file(self):
        flag = common.PauseFlag(os.path.join(self.tmp, "PAUSED"), env={})
        self.assertFalse(flag.is_paused())
        flag.set("test")
        self.assertTrue(flag.is_paused())
        flag.clear()
        self.assertFalse(flag.is_paused())
        self.assertTrue(common.PauseFlag(os.path.join(self.tmp, "NOPE"),
                                         env={"ORVYREN_K0_PAUSED": "1"}).is_paused())

    def test_signature_log_counts_without_key_material(self):
        log = common.SignatureLog(os.path.join(self.tmp, "signatures.jsonl"))
        self.assertEqual(log.count(), 0)
        log.append(intent_id="I1", mode="dry-run", tx_hash="0x00")
        self.assertEqual(log.count(), 1)
        entry = common.read_jsonl(os.path.join(self.tmp, "signatures.jsonl"))[0]
        self.assertEqual(entry["key_material"], "never recorded")
        self.assertNotIn("0x00" * 32, json.dumps(entry))


# =============================================================================
# préflight + test de dérive
# =============================================================================

class TestPreflight(TempSessionMixin, unittest.TestCase):
    def make_runner(self, *, intent=None, envelope=None, mode=preflight_mod.MODE_OFFLINE, registry=None,
                    pause=None, recorded=None):
        policy = self.make_policy()
        if intent is None:
            intent = intents.build_transfer_intent(
                chain_id=84532, account=SAFE, asset=USDC, amount="50.0", recipient=B,
                expiry_minutes=15, justification="préflight de test")
        return preflight_mod.PreflightRunner(
            policy=policy, intent=intent, envelope=envelope or fake_envelope(), mode=mode,
            registry=registry, pause=pause, recorded_decision=recorded,
            agent=AGENT, safe=SAFE, module=MODULE, asset=USDC)

    def test_offline_report_shape(self):
        report = self.make_runner().run()
        ids = [check["id"] for check in report["checks"]]
        self.assertEqual(sorted(ids), sorted(["P{}".format(n) for n in range(1, 13)]
                                             + ["D{}".format(n) for n in range(1, 11)]))
        self.assertEqual(report["verdict"], "OFFLINE_PASS")
        self.assertFalse(report["safe_mode"])
        self.assertTrue(report["safe_mode_required_when_live"])

    def test_offline_controls_pass_on_consistent_fixture(self):
        report = self.make_runner().run()
        statuses = {check["id"]: check["status"] for check in report["checks"]}
        for check_id in ("P1", "P2", "P3", "P5", "D1", "D4", "D5", "D6", "D7", "D8", "D9"):
            self.assertEqual(statuses[check_id], "PASS", "{} = {}".format(check_id, statuses[check_id]))
        for check_id in ("P7", "P8", "P9", "P10", "P11", "P12"):
            self.assertEqual(statuses[check_id], "SKIPPED")

    def test_p4_unknown_without_registry(self):
        report = self.make_runner().run()
        statuses = {check["id"]: check["status"] for check in report["checks"]}
        self.assertEqual(statuses["P4"], "UNKNOWN")

    def test_p4_fails_on_replay(self):
        intent = intents.build_transfer_intent(chain_id=84532, account=SAFE, asset=USDC, amount="50.0",
                                               recipient=B, expiry_minutes=15, justification="rejeu")
        registry = common.Registry(os.path.join(self.tmp, "registry.json"))
        registry.record(intent_id=intent["intent_id"], idempotency_key=intent["idempotency_key"],
                        status="RESERVED")
        report = self.make_runner(intent=intent, registry=registry).run()
        statuses = {check["id"]: check["status"] for check in report["checks"]}
        self.assertEqual(statuses["P4"], "FAIL")
        self.assertEqual(statuses["P1"], "FAIL")
        self.assertEqual(report["verdict"], "FAIL")
        self.assertTrue(report["blocking"])

    def test_pause_blocks(self):
        pause = common.PauseFlag(os.path.join(self.tmp, "PAUSED"), env={})
        pause.set("test")
        report = self.make_runner(pause=pause).run()
        statuses = {check["id"]: check["status"] for check in report["checks"]}
        self.assertEqual(statuses["P5"], "FAIL")
        self.assertEqual(report["verdict"], "FAIL")

    def test_recorded_decision_mismatch(self):
        report = self.make_runner(recorded={"verdict": "DENY"}).run()
        statuses = {check["id"]: check["status"] for check in report["checks"]}
        self.assertEqual(statuses["P1"], "FAIL")
        self.assertIn("policy_decision_mismatch", report["checks"][0]["detail"].get("code", ""))

    def test_drift_critical_target_clearance(self):
        envelope = fake_envelope()
        envelope["role"]["targets"] = [{"address": USDC, "clearance": "Target"}]
        report = self.make_runner(envelope=envelope).run()
        statuses = {check["id"]: check["status"] for check in report["checks"]}
        self.assertEqual(statuses["D4"], "FAIL")
        self.assertTrue(report["safe_mode"])
        self.assertTrue(any("ENVELOPE_DRIFT" in reason for reason in report["safe_mode_reasons"]))

    def test_drift_wrong_recipient_condition(self):
        envelope = fake_envelope()
        envelope["role"]["conditions"]["param0"]["values"] = [D_UNLISTED]
        report = self.make_runner(envelope=envelope).run()
        statuses = {check["id"]: check["status"] for check in report["checks"]}
        self.assertEqual(statuses["D6"], "FAIL")

    def test_drift_allowance_inconsistency(self):
        envelope = fake_envelope()
        envelope["role"]["allowances"]["usdc_daily"]["max_refill_base_units"] = 100000000
        report = self.make_runner(envelope=envelope).run()
        statuses = {check["id"]: check["status"] for check in report["checks"]}
        self.assertEqual(statuses["D7"], "FAIL")

    def test_drift_unverified_when_live(self):
        runner = self.make_runner(mode=preflight_mod.MODE_RPC)
        runner._live_mode = lambda: True        # pas de réseau : on simule le mode en ligne
        runner._live = {"gas_price": 6_000_000}
        report = runner.run()
        # D2/D3/D10 sans codehash épinglé ni probes ⇒ UNKNOWN ⇒ SAFE MODE en mode en ligne
        self.assertTrue(report["safe_mode"])
        self.assertTrue(any("ENVELOPE_UNVERIFIED" in reason for reason in report["safe_mode_reasons"]))

    def test_chain_id_mismatch(self):
        intent = intents.build_transfer_intent(chain_id=1, account=SAFE, asset=USDC, amount="50.0",
                                               recipient=B, expiry_minutes=15, justification="mauvaise chaîne")
        report = self.make_runner(intent=intent).run()
        statuses = {check["id"]: check["status"] for check in report["checks"]}
        self.assertEqual(statuses["P2"], "FAIL")


# =============================================================================
# runs A-E en dry-run (orchestrateur)
# =============================================================================

class TestRunsDryRun(TempSessionMixin, unittest.TestCase):
    def test_all_five_runs_dry(self):
        ctx = self.make_context()
        for run in ("A", "B", "C", "D", "E"):
            summary = demo.execute_run(run, ctx)
            statuses = [criterion["status"] for criterion in summary["criteria"]]
            self.assertNotIn("failed", statuses,
                             "run {} : {}".format(run, summary["criteria"]))
            if run == "B":  # les 4 critères B sont entièrement évaluables hors chaîne
                self.assertNotIn("pending", statuses, summary["criteria"])
                self.assertTrue(demo._criteria_ok(summary["criteria"]),
                                "run B : {}".format(summary["criteria"]))
            else:
                self.assertIn("pending", statuses,
                              "run {} : un dry-run doit déclarer ses critères non évalués".format(run))
                self.assertFalse(demo._criteria_ok(summary["criteria"]),
                                 "run {} : pending ne vaut pas « critères OK »".format(run))
            self.assertEqual(summary["status"], "DRY_RUN_OK")
        # journal : chaîne recalculée OK et aucune clé
        report = ctx.journal.verify()
        self.assertTrue(report["ok"], report["errors"])
        raw = open(os.path.join(ctx.session_dir, "audit.jsonl"), "r", encoding="utf-8").read()
        for forbidden in ("private_key", "PRIVATE_KEY=", "mnemonic", "0x" + "ab" * 32):
            self.assertNotIn(forbidden, raw)

    def test_run_a_dry_run_criteria(self):
        ctx = self.make_context()
        summary = demo.run_a(ctx)
        statuses = {criterion["id"]: criterion["status"] for criterion in summary["criteria"]}
        self.assertEqual(statuses["A.4"], "met")           # compteur de signatures +1
        self.assertEqual(statuses["A.1"], "pending")       # pas de reçu en dry-run
        self.assertEqual(statuses["A.5"], "pending")       # dry : RECEIPT/VERIFY impossibles sans chaîne → pending (l'ordre OUTCOME est testé par le run réel --execute)
        self.assertFalse(demo._criteria_ok(summary["criteria"]),
                         "5 critères pending ne valent pas « critères OK »")
        self.assertEqual(demo._criteria_label(summary["criteria"]), "DRY_RUN_PENDING")
        self.assertEqual(ctx.signatures.count(), 1)
        kinds = ctx.journal.kinds(summary["intent_id"])
        self.assertIn("INTENT", kinds)
        self.assertIn("POLICY", kinds)
        self.assertIn("SUBMIT", kinds)
        self.assertIn("OUTCOME", kinds)
        submit = [record for record in common.read_jsonl(os.path.join(ctx.session_dir, "audit.jsonl"))
                  if record["kind"] == "SUBMIT"][0]
        self.assertTrue(submit["payload"]["simulated"])
        self.assertEqual(submit["payload"]["signatures_count"], 1)

    def test_criteria_statuses_are_not_flattened(self):
        """E1 : pending n'est jamais un succès ; seuls les 'met' font OK."""
        self.assertFalse(demo._criteria_ok([]))
        self.assertFalse(demo._criteria_ok([{"status": "pending"}]))
        self.assertFalse(demo._criteria_ok([{"status": "met"}, {"status": "pending"}]))
        self.assertFalse(demo._criteria_ok([{"status": "failed"}]))
        self.assertTrue(demo._criteria_ok([{"status": "met"}, {"status": "met"}]))
        self.assertEqual(demo._criteria_label([{"status": "met"}, {"status": "pending"}]),
                         "DRY_RUN_PENDING")
        self.assertEqual(demo._criteria_label([{"status": "met"}]), "critères OK")
        self.assertEqual(demo._criteria_label([{"status": "failed"}]),
                         "CRITÈRES NON SATISFAITS")

    def test_run_b_zero_signatures(self):
        ctx = self.make_context()
        demo.run_a(ctx)
        before = ctx.signatures.count()
        summary = demo.run_b(ctx)
        self.assertEqual(ctx.signatures.count(), before)
        cases = {case["case"]: case for case in summary["cases"]}
        self.assertEqual(cases["B1"]["reasons"], ["AMOUNT_ABOVE_TX_CAP"])
        self.assertEqual(cases["B2"]["reasons"], ["RECIPIENT_NOT_ALLOWED"])
        self.assertEqual(cases["B3"]["reasons"], ["INTENT_ALREADY_PROCESSED"])
        self.assertEqual(cases["B4"]["verdict"], "REQUIRE_APPROVAL")
        self.assertEqual(cases["B4"]["reasons"], ["ACTION_NEEDS_HUMAN_APPROVAL"])

    def test_run_c_offline_checks(self):
        ctx = self.make_context()
        summary = demo.run_c(ctx)
        self.assertTrue(all(case["offline_checks"] for case in summary["cases"]))
        for case in summary["cases"]:
            self.assertTrue(all(check["ok"] for check in case["offline_checks"]), case["case"])
            if case["case"] in ("C1", "C2", "C4"):
                self.assertEqual(case["decoded"]["inner_to"],
                                 D_UNLISTED if case["case"] == "C2" else B)
        boundary = summary["boundary"]
        self.assertEqual(boundary["first"]["verdict"], "ALLOW")
        self.assertEqual(boundary["second"]["verdict"], "DENY")
        self.assertIn("AMOUNT_ABOVE_PERIOD_CAP", boundary["second"]["reasons"])

    def test_run_d_revocation_calldata(self):
        ctx = self.make_context()
        summary = demo.run_d(ctx)
        revocation = summary["revocation"]
        decoded = calls.decode_assign_roles(revocation["data"])
        self.assertEqual(decoded["member"], AGENT)
        self.assertEqual(decoded["enabled"], [False])
        self.assertEqual(revocation["expected_agent_revert"]["selector"], common.ERROR_NOT_AUTHORIZED)
        self.assertTrue(os.path.isfile(os.path.join(ctx.run_dir, "revocation_instruction.json")))

    def test_run_e_export(self):
        ctx = self.make_context()
        for run in ("A", "B"):
            demo.execute_run(run, ctx)
        summary = demo.run_e(ctx)
        self.assertTrue(summary["chain_report"]["ok"])
        self.assertTrue(os.path.isfile(os.path.join(ctx.session_dir, "export", "manifest.json")))
        self.assertTrue(os.path.isfile(os.path.join(ctx.session_dir, "report.md")))
        counters = summary["manifest"]["counters"]
        self.assertGreaterEqual(counters["deny_entries"], 4)
        self.assertEqual(counters["signatures"], 1)

    def test_execute_mode_refuses_placeholders(self):
        ctx = self.make_context(mode=demo.MODE_EXECUTE)
        with self.assertRaises(common.ConfigurationError):
            ctx.require_execute_prerequisites()

    def test_execute_mode_refuses_mainnet_flag(self):
        ctx = self.make_context()
        ctx.mode = demo.MODE_EXECUTE
        ctx.placeholders_used = []
        os.environ["ORVYREN_ALLOW_MAINNET"] = "1"
        try:
            with self.assertRaises(common.ConfigurationError):
                ctx.require_execute_prerequisites()
        finally:
            os.environ.pop("ORVYREN_ALLOW_MAINNET", None)


# =============================================================================
# vérification de reçu
# =============================================================================

def synthetic_receipt(*, logs, status="0x1", chain_id="0x14a34", to=MODULE, sender=AGENT):
    return {
        "transactionHash": "0x" + "aa" * 32,
        "status": status,
        "chainId": chain_id,
        "blockNumber": "0x2dff1e2",
        "blockHash": "0x" + "bb" * 32,
        "from": sender,
        "to": to,
        "gasUsed": "0x9f2c",
        "effectiveGasPrice": "0x5f5e100",
        "logs": logs,
    }


def transfer_log(*, token, sender, recipient, value, address=None):
    return {
        "address": address or token,
        "topics": [base_verify.TRANSFER_TOPIC,
                   "0x" + sender[2:].rjust(64, "0"),
                   "0x" + recipient[2:].rjust(64, "0")],
        "data": "0x" + "{:064x}".format(value),
    }


class TestReceiptVerification(TempSessionMixin, unittest.TestCase):
    def intent(self):
        return intents.build_transfer_intent(chain_id=84532, account=SAFE, asset=USDC, amount="50.0",
                                             recipient=B, expiry_minutes=15, justification="reçu")

    def verify(self, receipt):
        return verify_receipt.verify_full(receipt, intent=self.intent(), safe=SAFE, module=MODULE,
                                          agent=AGENT, chain_id=84532, decimals=6)

    def module_log(self):
        return {"address": MODULE, "topics": ["0x" + "cc" * 32], "data": "0x"}

    def test_conform_receipt(self):
        receipt = synthetic_receipt(logs=[transfer_log(token=USDC, sender=SAFE, recipient=B,
                                                       value=50_000_000),
                                          self.module_log()])
        result = self.verify(receipt)
        self.assertTrue(result["ok"], result["mismatches"])
        self.assertEqual(result["log_counts"]["exact_matches"], 1)
        self.assertEqual(result["warnings"], [])

    def test_wrong_amount_and_recipient(self):
        receipt = synthetic_receipt(logs=[transfer_log(token=USDC, sender=SAFE, recipient=C,
                                                       value=1)])
        result = self.verify(receipt)
        self.assertFalse(result["ok"])
        self.assertIn("RECIPIENT_MISMATCH", result["mismatches"])
        self.assertIn("AMOUNT_MISMATCH", result["mismatches"])

    def test_ambiguous_two_exact_logs(self):
        log = transfer_log(token=USDC, sender=SAFE, recipient=B, value=50_000_000)
        result = self.verify(synthetic_receipt(logs=[log, dict(log)]))
        self.assertFalse(result["ok"])
        self.assertIn(verify_receipt.LOG_COUNT_AMBIGUOUS, result["mismatches"])

    def test_single_non_matching_log_is_not_ambiguous(self):
        """Un seul log du jeton qui ne correspond pas = mismatch ordinaire (pas d'ambiguïté)."""
        receipt = synthetic_receipt(logs=[transfer_log(token=USDC, sender=SAFE, recipient=B, value=1),
                                          self.module_log()])
        result = self.verify(receipt)
        self.assertFalse(result["ok"])
        self.assertIn("AMOUNT_MISMATCH", result["mismatches"])
        self.assertNotIn(verify_receipt.LOG_COUNT_AMBIGUOUS, result["mismatches"])

    def test_two_token_logs_with_one_exact_match(self):
        """Deux logs du jeton dont un seul correspond exactement : conforme (règle d'unicité)."""
        other = transfer_log(token=USDC, sender=C, recipient=C, value=7)
        good = transfer_log(token=USDC, sender=SAFE, recipient=B, value=50_000_000)
        result = self.verify(synthetic_receipt(logs=[other, good, self.module_log()]))
        self.assertTrue(result["ok"], result["mismatches"])
        self.assertEqual(result["log_counts"]["exact_matches"], 1)

    def test_missing_transfer_log(self):
        result = self.verify(synthetic_receipt(logs=[self.module_log()]))
        self.assertIn("NO_TRANSFER_LOG", result["mismatches"])

    def test_wrong_envelope(self):
        receipt = synthetic_receipt(logs=[transfer_log(token=USDC, sender=SAFE, recipient=B,
                                                       value=50_000_000)],
                                    to=USDC, sender=SAFE)
        result = self.verify(receipt)
        self.assertIn(verify_receipt.WRONG_TARGET, result["mismatches"])
        self.assertIn(verify_receipt.WRONG_EXECUTOR, result["mismatches"])

    def test_failed_status_is_first_class(self):
        receipt = synthetic_receipt(logs=[], status="0x0")
        result = self.verify(receipt)
        self.assertFalse(result["ok"])
        self.assertIn("TRANSACTION_FAILED", result["mismatches"])

    def test_missing_chain_id(self):
        receipt = synthetic_receipt(logs=[transfer_log(token=USDC, sender=SAFE, recipient=B,
                                                       value=50_000_000)])
        receipt.pop("chainId")
        result = self.verify(receipt)
        self.assertIn("CHAIN_ID_MISSING", result["mismatches"])

    def test_module_event_absent_is_warning(self):
        receipt = synthetic_receipt(logs=[transfer_log(token=USDC, sender=SAFE, recipient=B,
                                                       value=50_000_000)])
        result = self.verify(receipt)
        self.assertTrue(result["ok"])
        self.assertIn(verify_receipt.MODULE_EVENT_ABSENT, result["warnings"])

    def test_foreign_token_transfer_log(self):
        other = "0x" + "77" * 20
        receipt = synthetic_receipt(logs=[transfer_log(token=other, sender=SAFE, recipient=B,
                                                       value=50_000_000)])
        result = self.verify(receipt)
        self.assertIn("TOKEN_CONTRACT_MISMATCH", result["mismatches"])


# =============================================================================
# signataire (mode simulé)
# =============================================================================

class TestSignerDryRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_signer_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.log = common.SignatureLog(os.path.join(self.tmp, "signatures.jsonl"))

    def test_dry_run_is_simulated_and_deterministic(self):
        signer = signer_mod.Signer(dry_run=True, signature_log=self.log, env={})
        tx = {"chainId": 84532, "nonce": 0, "to": MODULE, "value": 0, "data": "0xdeadbeef"}
        first = signer.sign_transaction(tx, intent_id="I1")
        second = signer.sign_transaction(tx, intent_id="I1")
        self.assertTrue(first["simulated"])
        self.assertEqual(first["tx_hash"], second["tx_hash"])
        self.assertIsNone(first["signed_transaction"])
        self.assertEqual(self.log.count(), 2)

    def test_dry_run_never_reads_key(self):
        signer = signer_mod.Signer(dry_run=True, env={"ORVYREN_PRIVATE_KEY": "0x" + "11" * 32})
        self.assertTrue(signer.key_present())
        self.assertIsNone(signer.address())     # dry-run : aucune dérivation
        result = signer.sign_transaction({"chainId": 84532, "nonce": 0, "to": MODULE, "value": 0,
                                          "data": "0x"})
        self.assertNotIn("11" * 32, json.dumps(result))

    def test_forbidden_field_refused(self):
        signer = signer_mod.Signer(dry_run=True, env={})
        with self.assertRaises(signer_mod.SignerError):
            signer.sign_transaction({"chainId": 84532, "privateKey": "nope"})

    def test_chain_mismatch_refused(self):
        signer = signer_mod.Signer(dry_run=True, env={})
        with self.assertRaises(signer_mod.SignerError):
            signer.sign_transaction({"chainId": 1, "nonce": 0, "to": MODULE, "value": 0, "data": "0x"})

    @unittest.skipIf(HAVE_ETH_ACCOUNT,
                     "eth-account présent : le chemin « bibliothèque absente » n'est pas testable")
    def test_real_mode_without_library_fails_cleanly(self):
        signer = signer_mod.Signer(dry_run=False, env={})
        with self.assertRaises(signer_mod.SignerDependencyError):
            signer.sign_transaction({"chainId": 84532, "nonce": 0, "to": MODULE, "value": 0, "data": "0x"})

    def test_send_raw_refused_in_dry_run(self):
        signer = signer_mod.Signer(dry_run=True, env={})
        with self.assertRaises(signer_mod.SignerError):
            signer.send_raw_transaction("0x00")

    def test_key_present_requires_32_bytes(self):
        self.assertFalse(signer_mod.Signer(dry_run=True, env={"ORVYREN_PRIVATE_KEY": "abc"}).key_present())
        self.assertTrue(signer_mod.Signer(dry_run=True,
                                          env={"ORVYREN_PRIVATE_KEY": "11" * 32}).key_present())

    # --- régression : casse EIP-55 du champ 'from' (rencontré le 2026-10-16 en exécution réelle) ---

    @unittest.skipUnless(HAVE_ETH_ACCOUNT, "eth-account requis pour signer réellement")
    def test_execute_normalizes_from_to_eip55(self):
        signer = signer_mod.Signer(dry_run=False, env={"ORVYREN_PRIVATE_KEY": "0x" + "22" * 32})
        address = signer.address()
        tx = {"chainId": 84532, "nonce": 0, "to": MODULE.lower(), "value": 0, "data": "0x",
              "gas": 21000, "maxFeePerGas": 10 ** 9, "maxPriorityFeePerGas": 10 ** 9,
              "type": 2, "from": address.lower()}
        result = signer.sign_transaction(tx, intent_id="I-FROM")
        self.assertFalse(result["simulated"])
        self.assertTrue(result["tx_hash"].startswith("0x"))
        self.assertEqual(tx["from"], address.lower())      # le dict appelant n'est pas muté
        self.assertNotIn("22" * 32, json.dumps(result))    # jamais de clé dans la sortie

    @unittest.skipUnless(HAVE_ETH_ACCOUNT, "eth-account requis pour signer réellement")
    def test_execute_refuses_from_mismatch(self):
        signer = signer_mod.Signer(dry_run=False, env={"ORVYREN_PRIVATE_KEY": "0x" + "22" * 32})
        tx = {"chainId": 84532, "nonce": 0, "to": MODULE, "value": 0, "data": "0x",
              "gas": 21000, "maxFeePerGas": 10 ** 9, "maxPriorityFeePerGas": 10 ** 9,
              "type": 2, "from": "0x" + "33" * 20}
        with self.assertRaises(signer_mod.SignerError):
            signer.sign_transaction(tx, intent_id="I-BAD")

    def test_signer_output_never_contains_key_material(self):
        """Propriété de sécurité testée MÊME sans eth-account (jamais sautée)."""
        key = "0x" + "22" * 32
        signer = signer_mod.Signer(dry_run=True, env={"ORVYREN_PRIVATE_KEY": key})
        result = signer.sign_transaction({"chainId": 84532, "nonce": 0, "to": MODULE,
                                          "value": 0, "data": "0x"})
        payload = json.dumps(result)
        self.assertNotIn("22" * 32, payload)
        self.assertNotIn(key, payload)
        self.assertNotIn("22" * 32, json.dumps(signer.safe_dict()))


# =============================================================================
# attente de confirmations (anti-reorg bornée)
# =============================================================================

class TestWaitConfirmations(unittest.TestCase):
    """Sémantique : CONFIRMED = profondeur ≥ k ET couple (bloc, hash) stable sur deux lectures."""

    def setUp(self):
        self.round = 0
        self.receipts = []
        self.heads = []

    def _fake_rpc(self, url, method, params, timeout=None):
        self.assertEqual(method, "eth_getTransactionReceipt")
        return self.receipts[min(self.round, len(self.receipts) - 1)]

    def _fake_head(self, url, timeout=None):
        head = self.heads[min(self.round, len(self.heads) - 1)]
        self.round += 1
        return head

    def _run(self, **kw):
        from unittest import mock
        with mock.patch.object(verify_receipt.common, "rpc", side_effect=self._fake_rpc), \
             mock.patch.object(verify_receipt.common, "eth_block_number", side_effect=self._fake_head):
            return verify_receipt.wait_for_confirmations(
                tx_hash="0x" + "11" * 32, receipt_block_number=kw.pop("bn", 100),
                receipt_block_hash=kw.pop("bh", "0x" + "aa" * 32), rpc_url="http://unused",
                confirmation_blocks=2, poll_seconds=0.01, **kw)

    def _receipt(self, bn, bh):
        return {"blockNumber": hex(bn), "blockHash": bh}

    def test_confirmed_after_stable_view(self):
        r = self._receipt(100, "0x" + "aa" * 32)
        self.receipts = [r, r]
        self.heads = [101, 102]
        result = self._run()
        self.assertEqual(result["status"], "CONFIRMED")
        self.assertNotIn("view_updated", result)

    def test_view_change_annotated_not_reorged(self):
        r = self._receipt(100, "0x" + "bb" * 32)  # hash différent du témoin consigné (aa)
        self.receipts = [r, r]
        self.heads = [101, 102]
        result = self._run()
        self.assertEqual(result["status"], "CONFIRMED")
        self.assertIn("view_updated", result)

    def test_receipt_disappears_is_reorged(self):
        self.receipts = [None]
        self.heads = [101]
        result = self._run()
        self.assertEqual(result["status"], "REORGED")

    def test_block_number_change_is_reorged(self):
        self.receipts = [self._receipt(101, "0x" + "aa" * 32)]
        self.heads = [102]
        result = self._run()
        self.assertEqual(result["status"], "REORGED")

    def test_timeout_returns_pending_never_hangs(self):
        r = self._receipt(100, "0x" + "aa" * 32)
        self.receipts = [r]
        self.heads = [100]  # profondeur 1 < 2 : jamais confirmable
        result = self._run(timeout_seconds=0)
        self.assertEqual(result["status"], "PENDING_CONFIRMATION")


class TestReplayRevertRetry(unittest.TestCase):
    """Régression : nœud en retard (« block not found ») → réessais bornés, jamais un faux revert."""

    def _rpc_error(self, message):
        return common.chain_client.RpcError("eth_call", -32000, message, None)

    def test_retries_then_succeeds(self):
        from unittest import mock
        tx = {"from": "0x" + "11" * 20, "to": "0x" + "22" * 20, "input": "0x", "value": "0x0"}
        with mock.patch.object(verify_receipt.common, "rpc",
                               side_effect=[tx, self._rpc_error("block not found: 0x2df556d"), "0x"]):
            result = verify_receipt.replay_revert(rpc_url="http://unused", tx_hash="0x" + "33" * 32,
                                                  block_number=100, attempts=3, retry_delay=0.01)
        self.assertEqual(result["status"], "NO_REVERT")

    def test_persistent_lag_is_not_a_revert_claim(self):
        from unittest import mock
        tx = {"from": "0x" + "11" * 20, "to": "0x" + "22" * 20, "input": "0x", "value": "0x0"}
        with mock.patch.object(verify_receipt.common, "rpc",
                               side_effect=[tx, self._rpc_error("block not found: 0x2df556d"),
                                            self._rpc_error("block not found: 0x2df556d")]):
            result = verify_receipt.replay_revert(rpc_url="http://unused", tx_hash="0x" + "33" * 32,
                                                  block_number=100, attempts=2, retry_delay=0.01)
        self.assertEqual(result["status"], "REPLAY_UNAVAILABLE")

    def test_real_revert_selector_extracted(self):
        from unittest import mock
        tx = {"from": "0x" + "11" * 20, "to": "0x" + "22" * 20, "input": "0x", "value": "0x0"}
        exc = self._rpc_error("execution reverted")
        exc.data = "0xfd8e9f28"
        with mock.patch.object(verify_receipt.common, "rpc", side_effect=[tx, exc]):
            result = verify_receipt.replay_revert(rpc_url="http://unused", tx_hash="0x" + "33" * 32,
                                                  block_number=100, attempts=2, retry_delay=0.01)
        self.assertEqual(result["status"], "REVERT")
        self.assertEqual(result["revert_selector"], "0xfd8e9f28")


# =============================================================================
# paquet d'audit
# =============================================================================

class TestAuditPacket(TempSessionMixin, unittest.TestCase):
    def test_packet_build_and_self_verification(self):
        ctx = self.make_context()
        for run in ("A", "B", "E"):
            demo.execute_run(run, ctx)
        result = build_audit_packet.build_packet(session_dir=ctx.session_dir, case="rseth",
                                                 evidence_dir=os.path.join(ROOT, "evidence"),
                                                 out_dir=os.path.join(self.tmp, "out"))
        self.assertTrue(os.path.isfile(result["zip_path"]))
        self.assertTrue(os.path.isfile("{}.sha256".format(result["zip_path"])))
        self.assertEqual(len(result["bundle_digest"]), 64)
        # le vérificateur embarqué doit valider le paquet extrait
        extract_dir = os.path.join(self.tmp, "extract")
        with zipfile.ZipFile(result["zip_path"]) as archive:
            archive.extractall(extract_dir)
        packet_root = os.path.join(extract_dir, os.path.basename(result["packet_dir"]))
        verifier = os.path.join(packet_root, "verify", "verify_hashes.py")
        run = subprocess.run([sys.executable, verifier, packet_root],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("OFFLINE_PASS", run.stdout)

    def test_packet_declares_missing_pieces(self):
        ctx = self.make_context()
        demo.run_a(ctx)
        result = build_audit_packet.build_packet(session_dir=ctx.session_dir, case="inexistant",
                                                 evidence_dir=os.path.join(ROOT, "evidence"),
                                                 out_dir=os.path.join(self.tmp, "out2"))
        pieces = {piece["piece"] for piece in result["missing_pieces"]}
        self.assertIn("dossier md (self-hash)", pieces)
        manifest = common.load_json(os.path.join(result["packet_dir"], "manifest.json"))
        self.assertFalse(manifest["streams"]["agent"]["present"])


# =============================================================================
# contraintes du kit : stdlib seule hors signataire
# =============================================================================

class TestKitConstraints(unittest.TestCase):
    NON_STDLIB = ("eth_account", "eth_keys", "web3", "requests", "yaml", "numpy",
                  "pandas", "httpx", "aiohttp", "coincurve")

    def test_only_signer_may_import_external_libraries(self):
        for name in sorted(os.listdir(DEMO_DIR)):
            if not name.endswith(".py") or name == "signer.py":
                continue
            source = open(os.path.join(DEMO_DIR, name), "r", encoding="utf-8").read()
            for module in self.NON_STDLIB:
                self.assertNotIn("import {}".format(module), source,
                                 "{} importe {}".format(name, module))

    def test_scripts_expose_help_and_exit_codes(self):
        for script in ("demo.py", "preflight.py", "signer.py", "verify_receipt.py",
                       "build_audit_packet.py"):
            run = subprocess.run([sys.executable, os.path.join(DEMO_DIR, script), "--help"],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, "{} --help".format(script))
            self.assertIn("usage", run.stdout.lower())

    def test_config_example_has_empty_private_key(self):
        text = open(os.path.join(DEMO_DIR, "config.example.env"), "r", encoding="utf-8").read()
        self.assertIn("ORVYREN_PRIVATE_KEY=\n", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
