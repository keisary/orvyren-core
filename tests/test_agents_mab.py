#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""MA-B integration testbench (W2 [DONE] criteria, lots L2.4/L2.7).

Proves, end to end and offline (scripted store committed under
``fixtures/agents/store_usdc-2023-03/``):

1. **two real processes**: the orchestrator and the critic run as separate OS
   processes (distinct PIDs in ``worker_done_*.json``) and write two journals
   with two distinct ``agent_id`` values;
2. **journal replay determinism**: the same case replayed k=10 times produces
   byte-identical journal chain heads (B1 §6.2 — the only determinism claim we
   can defend);
3. the fragility rule surfaces (FRAGILE -> REQUIRE_APPROVAL) and the forced
   abstention list travels in the outcome.

Execution: ``python -m pytest tests/test_agents_mab.py -q`` (offline, ~15 s).
"""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)
sys.path.insert(0, ROOT)

import run_agents  # noqa: E402
from orvyren.agents import worker as worker_mod  # noqa: E402

CASE = "usdc-2023-03"
STORE = os.path.join(ROOT, "fixtures", "agents", "store_%s" % CASE)
K_REPLAYS = 10


def _run_once(session_dir):
    """One full MA-B run (two worker processes); returns the outcome dict."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = run_agents.main(["--case", CASE, "--replay", "journal",
                                "--session", session_dir])
    if code != 0:
        raise AssertionError("run_agents rc=%d\n%s" % (code, buffer.getvalue()[-2000:]))
    run_dirs = sorted(entry for entry in os.listdir(session_dir)
                      if os.path.isdir(os.path.join(session_dir, entry)))
    latest = os.path.join(session_dir, run_dirs[-1])
    with open(os.path.join(latest, "run_outcome.json"), encoding="utf-8") as handle:
        return json.load(handle), latest, buffer.getvalue()


class TestMaBProcesses(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Committed fixture (P2 harness review): its absence is a broken
        # checkout, never a silent skip — the store ships in the repo, so this
        # class always runs and fails loudly if the data is missing.
        if not os.path.exists(os.path.join(STORE, "calls.jsonl")):
            raise AssertionError(
                "scripted store missing: %s — checkout broken, regenerate with "
                "scripts/agents_seed_demo.py --case %s" % (STORE, CASE))

    def setUp(self):
        self.session = tempfile.mkdtemp(prefix="orvyren_mab_")
        self.addCleanup(shutil.rmtree, self.session, ignore_errors=True)

    def test_two_processes_two_agent_ids(self):
        final, run_dir, _ = _run_once(self.session)
        with open(os.path.join(run_dir, "worker_done_orchestrator.json"),
                  encoding="utf-8") as handle:
            done_orch = json.load(handle)
        with open(os.path.join(run_dir, "worker_done_critic.json"),
                  encoding="utf-8") as handle:
            done_crit = json.load(handle)
        self.assertNotEqual(done_orch["pid"], done_crit["pid"],
                            "the two roles must run in SEPARATE PROCESSES")
        orch_entries = worker_mod.load_journal(os.path.join(run_dir, "journal_orchestrator.jsonl"))
        crit_entries = worker_mod.load_journal(os.path.join(run_dir, "journal_critic.jsonl"))
        self.assertEqual({e.agent_id for e in orch_entries}, {"orchestrator"})
        self.assertEqual({e.agent_id for e in crit_entries}, {"critic"})
        for entries in (orch_entries, crit_entries):
            ok, message = worker_mod.verify_exported_chain(entries)
            self.assertTrue(ok, message)
        self.assertGreaterEqual(len(orch_entries), 5)
        self.assertGreaterEqual(len(crit_entries), 1)

    def test_fragility_rule_and_abstention_list(self):
        final, run_dir, _ = _run_once(self.session)
        self.assertEqual(final["critique"].get("verdict_lecture"), "FRAGILE")
        self.assertEqual(final["escalation"], "REQUIRE_APPROVAL",
                         "FRAGILE must push towards human approval (B1 §5.3)")
        outcome = final["outcome"]
        self.assertEqual(outcome["stop_condition"], "ARRET-1")
        self.assertTrue(outcome["non_recherche"], "non_recherche list required (DOC2 §5.2.4)")
        self.assertLessEqual(outcome["budget_used"]["llm_calls"], 30)
        self.assertLessEqual(outcome["budget_used"]["cost_usd"], 0.10)

    def test_replay_k10_identical_chain_heads(self):
        heads = set()
        for _ in range(K_REPLAYS):
            final, _run_dir, _ = _run_once(self.session)
            heads.add((final["journals"]["orchestrator"]["chain_head"],
                       final["journals"]["critic"]["chain_head"]))
        self.assertEqual(len(heads), 1,
                         "k=%d replays must produce identical chain heads "
                         "(got %d variants)" % (K_REPLAYS, len(heads)))


if __name__ == "__main__":
    unittest.main()
