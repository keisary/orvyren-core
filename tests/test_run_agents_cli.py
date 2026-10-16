#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CLI guard tests for ``run_agents.py`` (W2 lot L2.7).

Offline: the happy path uses the scripted store; the refusal paths never
spawn a worker. Covers: frozen budget ceilings (A5), live mode without keys
(fail-closed, no network), unknown case, and the cost counter line.
"""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

import run_agents  # noqa: E402

CASE = "usdc-2023-03"
STORE = os.path.join(ROOT, "fixtures", "agents", "store_%s" % CASE)


class TestRunAgentsCli(unittest.TestCase):

    def setUp(self):
        self.session = tempfile.mkdtemp(prefix="orvyren_cli_")
        self.addCleanup(shutil.rmtree, self.session, ignore_errors=True)

    def test_budget_above_frozen_ceiling_refused(self):
        with self.assertRaises(SystemExit) as caught:
            run_agents.main(["--case", CASE, "--budget-llm", "40"])
        self.assertIn("E_BUDGET", str(caught.exception))

    def test_live_without_keys_fails_closed_without_network(self):
        env = {k: v for k, v in os.environ.items()
               if k not in ("ORVYREN_DEEPSEEK_API_KEY", "ORVYREN_MIMO_API_KEY")}
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit) as caught:
                run_agents.main(["--case", CASE, "--replay", "live"])
        self.assertIn("E_LLM_NO_KEY", str(caught.exception))

    def test_unknown_case_refused(self):
        with self.assertRaises(SystemExit) as caught:
            run_agents.main(["--case", "cas-inexistant-xyz", "--replay", "journal"])
        self.assertIn("E_CASE_UNKNOWN", str(caught.exception))

    def test_journal_run_prints_cost_and_escalation(self):
        if not os.path.exists(os.path.join(STORE, "calls.jsonl")):
            self.skipTest("store scripté absent")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = run_agents.main(["--case", CASE, "--replay", "journal",
                                    "--session", self.session])
        self.assertEqual(code, 0)
        text = buffer.getvalue()
        self.assertIn("coût LLM cumulé", text)
        self.assertIn("REQUIRE_APPROVAL", text)
        self.assertIn("chaîne OK", text)

    def test_replay_with_changed_budget_fails_closed(self):
        """Le budget fait partie du prompt enregistré : un budget différent ne
        doit PAS improviser — abstention fail-closed (E_LLM_NOT_RECORDED)."""
        if not os.path.exists(os.path.join(STORE, "calls.jsonl")):
            self.skipTest("store scripté absent")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = run_agents.main(["--case", CASE, "--replay", "journal",
                                    "--session", self.session, "--budget-llm", "10"])
        self.assertEqual(code, 0)
        run_dirs = sorted(entry for entry in os.listdir(self.session)
                          if os.path.isdir(os.path.join(self.session, entry)))
        with open(os.path.join(self.session, run_dirs[-1], "run_outcome.json"),
                  encoding="utf-8") as handle:
            final = json.load(handle)
        self.assertEqual(final["outcome"]["state"], "ABORTED")
        self.assertEqual(final["outcome"]["stop_condition"], "ARRET-3")


if __name__ == "__main__":
    unittest.main()
