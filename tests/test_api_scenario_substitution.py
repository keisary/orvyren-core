#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Declared-substitution + run-budget API tests (real rsETH scenario artefacts).

Locks the pre-submission UI/product additions:

* ``artifacts.scenario_substitution()`` reads the rsETH scenario artefacts on
  disk (``evidence/scenario_rseth/``) and exposes the exact banner wording of
  the declared substitution — the execution leg replays the pilot USDC
  decision (mechanism demo) and the rsETH conclusion is the agents'
  abstention;
* ``audit_summary()`` carries the declaration (added field only) so the Audit
  screen can display the banner whenever it replays the rsETH artefacts;
* ``discover_runs()`` / ``load_run_bundle()`` carry an added ``substitution``
  field without removing or renaming anything;
* the run budget keys consumed by the Live KPI band (``budget_used`` from
  ``outcome_orchestrator.json`` + ``budget`` from ``run.json``) are the exact
  keys on disk: ``cost_usd``, ``llm_calls``, ``tool_calls``, ``wall_seconds``.

Run: python -m unittest tests.test_api_scenario_substitution
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.api import artifacts  # noqa: E402
from orvyren.api.config import load_settings  # noqa: E402

EXPECTED_BANNER = (
    "declared substitution: the execution leg replays the pilot USDC "
    "decision (mechanism demo) — the rsETH conclusion is the agents' "
    "abstention"
)

BUDGET_KEYS = {"cost_usd", "llm_calls", "tool_calls", "wall_seconds"}


class TestScenarioSubstitution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = load_settings()
        cls.sub = artifacts.scenario_substitution(cls.settings)

    def test_declared_banner_exact_wording(self):
        self.assertTrue(self.sub["declared"])
        self.assertEqual(self.sub["banner"], EXPECTED_BANNER)
        self.assertEqual(artifacts.SUBSTITUTION_BANNER, EXPECTED_BANNER)

    def test_facts_are_read_from_real_artefacts(self):
        self.assertEqual(self.sub["case_id"], "rseth-2026-04")
        self.assertTrue(self.sub["agents_run_id"].startswith("rseth-2026-04_live_"))
        self.assertTrue(self.sub["executor_run_id"].startswith("scenario-rseth-2026-04"))
        # Measured refusal of the executor case probe (kept under
        # execution/case_attempt/), never a fabricated code.
        self.assertEqual(self.sub["execution_probe_refusal"],
                         "E_WHAT_WOULD_CHANGE_REQUIRED")
        self.assertEqual(self.sub["agents_abstention"], "ESCALATE")
        self.assertEqual(self.sub["epistemic_verdict"], "INCONCLUSIVE")
        self.assertTrue(self.sub["sources"])
        self.assertTrue(any("scenario_report.md" in s for s in self.sub["sources"]))

    def test_budget_keys_match_the_live_kpi_band(self):
        budget = self.sub["budget"]
        used = self.sub["budget_used"]
        self.assertTrue(BUDGET_KEYS.issubset(set(budget)), budget)
        self.assertTrue(BUDGET_KEYS.issubset(set(used)), used)
        self.assertEqual(budget["cost_usd"], 0.1)
        self.assertEqual(budget["llm_calls"], 30)
        self.assertEqual(budget["tool_calls"], 12)
        self.assertEqual(budget["wall_seconds"], 600)
        # Real measured run of the scenario (≈ $0.04 per full run).
        self.assertAlmostEqual(used["cost_usd"], 0.0397, places=3)
        self.assertEqual(used["llm_calls"], 9)
        self.assertEqual(used["tool_calls"], 7)
        self.assertGreater(used["wall_seconds"], 0)

    def test_audit_summary_carries_the_declaration(self):
        summary = artifacts.audit_summary(self.settings)
        self.assertIn("scenario_substitution", summary)
        sub = summary["scenario_substitution"]
        self.assertTrue(sub["declared"])
        self.assertEqual(sub["banner"], EXPECTED_BANNER)

    def test_run_entries_carry_the_added_substitution_field(self):
        runs = artifacts.discover_runs(self.settings)
        self.assertTrue(runs)
        linked = artifacts.scenario_linked_run_ids(self.settings)
        self.assertTrue(linked)  # manifest ids really exist on disk
        for run in runs:
            self.assertIn("substitution", run)
            if run["run_id"] in linked:
                # Declared only for the identities linked by the manifest.
                self.assertTrue(run["substitution"]["declared"])
            else:
                # Same case is not same execution: no phantom disclosure.
                self.assertIsNone(run["substitution"])

    def test_run_detection_on_scenario_identifiers(self):
        self.assertTrue(artifacts.is_rseth_scenario_run("rseth-2026-04_live_20261018T110722Z"))
        self.assertTrue(artifacts.is_rseth_scenario_run("scenario-rseth-2026-04-20261018T110722Z"))
        self.assertTrue(artifacts.is_rseth_scenario_run("anything", "rseth-2026-04"))
        self.assertFalse(artifacts.is_rseth_scenario_run("usdc-2023-03_live_20261017T011315Z",
                                                        "usdc-2023-03"))

    def test_run_bundle_keeps_every_key_and_adds_substitution(self):
        runs = [r for r in artifacts.discover_runs(self.settings)
                if r["journals"]["orchestrator"].get("present")]
        self.assertTrue(runs)
        bundle = artifacts.load_run_bundle(runs[0]["run_id"], self.settings)
        for key in ("run_id", "path", "spec", "outcome", "run_outcome",
                    "worker_done_orchestrator", "worker_done_critic",
                    "exchanges", "tool_calls"):
            self.assertIn(key, bundle)
        self.assertIn("substitution", bundle)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
