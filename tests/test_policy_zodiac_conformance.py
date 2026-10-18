#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Policy ↔ envelope conformance (L4.4): the off-chain policy is the
LOWER bound of the on-chain envelope (DOC2 §5.5.3/§5.5.4).

Part 1 — the **offline** conformance test (CI): `policy_v1.yaml` ↔ versioned
fixture `fixtures/roles_agent_config.json`; any drift introduced on one
side or the other is detected, including a simulated drift (modified
fixture => SAFE MODE).
Part 2 — the `scripts/run_drift_check.py` script: functions, report and exit
codes in `--offline` mode.

Run: python -m unittest discover -s tests -v
"""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _path in (os.path.join(ROOT, "src"), os.path.join(ROOT, "scripts"), ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from orvyren.policy import load_policy  # noqa: E402

import run_drift_check as drift  # noqa: E402

POLICY = os.path.join(ROOT, "policy_v1.yaml")
FIXTURE = os.path.join(ROOT, "fixtures", "roles_agent_config.json")
# Only B is resolved here (address measured on-chain); C stays an unversioned
# session label — listed as "pending" by the D6 check.
RECIPIENTS = {"B": "0x37877f6ffb6656e752bf4807b9c3c7b761a953a3"}


def load_fixture():
    with open(FIXTURE, encoding="utf-8") as handle:
        return json.load(handle)


def build_offline_report(fixture):
    bundle = load_policy(POLICY, RECIPIENTS)
    return drift.build_report(bundle=bundle, fixture=fixture, fixture_path=FIXTURE,
                              policy_path=POLICY, mode="offline", rpc_url=None, timeout=10)


class TestOfflineConformance(unittest.TestCase):
    def test_fixture_et_politique_conformes(self):
        report = build_offline_report(load_fixture())
        self.assertEqual(report["verdict"], "PASS", [c for c in report["checks"]
                                                     if c["status"] != "PASS"])
        self.assertFalse(report["safe_mode"])
        self.assertEqual(len(report["checks"]), 10)
        statuses = {check["id"]: check["status"] for check in report["checks"]}
        for check_id in ("D3", "D4", "D5", "D6", "D7", "D8", "D9"):
            self.assertEqual(statuses[check_id], "PASS", check_id)

    def test_derive_simulee_est_detectee(self):
        def drop_allowance(fixture):
            fixture["role"]["allowances"]["usdc_daily"].update(
                {"refill_base_units": 50000000, "max_refill_base_units": 50000000})

        def widen_target(fixture):
            fixture["role"]["targets"][0]["clearance"] = "Target"

        def change_quota(fixture):
            fixture["role"]["call_quota"]["max_per_period"] = 5

        def empty_recipients(fixture):
            fixture["role"]["conditions"]["param0"]["values"] = []

        def drop_revocation(fixture):
            fixture["revocation_scheduled_at"] = None

        def swap_role_key(fixture):
            fixture["role_key"] = "0xdeadbeef" + "0" * 56

        for name, mutate in (("reduced allowance", drop_allowance),
                             ("broad-scope target", widen_target),
                             ("modified quota", change_quota),
                             ("empty recipients", empty_recipients),
                             ("revocation removed", drop_revocation),
                             ("role key changed", swap_role_key)):
            with self.subTest(name=name):
                fixture = copy.deepcopy(load_fixture())
                mutate(fixture)
                report = build_offline_report(fixture)
                self.assertEqual(report["verdict"], "DRIFT", name)
                self.assertTrue(report["safe_mode"], name)
                self.assertTrue(report["safe_mode_reasons"], name)

    def test_fonction_a_la_place_de_la_condition(self):
        fixture = copy.deepcopy(load_fixture())
        fixture["role"]["functions"][0]["selector"] = "0xdeadbeef"
        report = build_offline_report(fixture)
        self.assertEqual(report["verdict"], "DRIFT")
        self.assertIn("D5", report["safe_mode_reasons"])


class TestDriftCli(unittest.TestCase):
    def test_cli_offline_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "report.json")
            run = subprocess.run(
                [sys.executable, "scripts/run_drift_check.py", "--offline", "--quiet", "--out", out],
                cwd=ROOT, capture_output=True, text=True, timeout=120)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stdout.strip(), "PASS")
            with open(out, encoding="utf-8") as handle:
                report = json.load(handle)
            self.assertEqual(report["schema"], "orvyren-envelope-drift-report/v1")
            self.assertEqual(report["mode"], "offline")
            self.assertFalse(report["safe_mode"])

    def test_cli_offline_derive_simulee_safe_mode(self):
        fixture = copy.deepcopy(load_fixture())
        fixture["role"]["allowances"]["usdc_daily"]["refill_base_units"] = 10000000
        fixture["role"]["allowances"]["usdc_daily"]["max_refill_base_units"] = 10000000
        with tempfile.TemporaryDirectory() as tmp:
            tampered = os.path.join(tmp, "fixture_drift.json")
            with open(tampered, "w", encoding="utf-8") as handle:
                json.dump(fixture, handle)
            out = os.path.join(tmp, "report.json")
            run = subprocess.run(
                [sys.executable, "scripts/run_drift_check.py", "--offline", "--quiet",
                 "--fixture", tampered, "--out", out],
                cwd=ROOT, capture_output=True, text=True, timeout=120)
            self.assertEqual(run.returncode, 2, run.stderr)
            self.assertEqual(run.stdout.strip(), "DRIFT")
            with open(out, encoding="utf-8") as handle:
                report = json.load(handle)
            self.assertTrue(report["safe_mode"])
            self.assertIn("D7", report["safe_mode_reasons"])

    def test_cli_fixture_schema_invalide(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "bad.json")
            with open(bad, "w", encoding="utf-8") as handle:
                json.dump({"schema": "autre"}, handle)
            run = subprocess.run(
                [sys.executable, "scripts/run_drift_check.py", "--offline", "--fixture", bad],
                cwd=ROOT, capture_output=True, text=True, timeout=120)
            self.assertEqual(run.returncode, 4)


class TestFixtureContent(unittest.TestCase):
    def test_sondes_et_empreintes_presentes(self):
        fixture = load_fixture()
        self.assertEqual(fixture["schema"], "orvyren-roles-agent-config/v1")
        module = fixture["module"]
        self.assertEqual(module["code_size_expected"], 45)          # proxy d'instance
        self.assertEqual(module["singleton"]["code_size_expected"], 24409)  # singleton officiel
        self.assertEqual(len(module["singleton"]["code_sha256_expected"]), 64)
        probes = fixture["probes"]
        self.assertGreaterEqual(len(probes), 2)
        for probe in probes:
            self.assertTrue(probe["proves"], probe["id"])
            self.assertTrue(probe["data"].startswith("0x") and len(probe["data"]) > 500, probe["id"])
            self.assertRegex(probe["expect"]["revert_selector"], r"^0x[0-9a-f]{8}$")
        self.assertIn("D3", probes[0]["proves"])
        numbers = {probe["id"]: probe["expect"]["revert_selector"] for probe in probes}
        self.assertNotIn("0xfd8e9f28", numbers["members.agent.behavioural"],
                         "not NoMembership: the agent must be a member at capture time")

    def test_la_fixture_nomme_ses_zones_incertaines(self):
        fixture = load_fixture()
        self.assertTrue(fixture["pending"])
        self.assertIsNone(fixture["module"]["version"])
        self.assertIn("non versionnée", fixture["role"]["conditions"]["param0"]["note"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
