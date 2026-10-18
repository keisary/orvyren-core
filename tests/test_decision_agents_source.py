#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench — the agents -> decision bridge (stdlib, offline).

Covers the two things that make the bridge trustworthy:

* **shape** — the payload carries the DecisionRecord keys
  (``build_decision_record``'s contract) plus a ``source`` block that names the
  run it came from;
* **honesty** — a live sealed run that ended inconclusive produces an
  abstention (no action, no intent, ``REQUIRE_APPROVAL``) whose
  ``what_would_change`` is ``outcome.non_recherche`` *verbatim*, and every
  ``evidence_refs`` entry is a chain head recomputed from a journal that really
  sits in the run directory.

The bench reads the REAL sealed artefacts found on disk (``evidence/agents_live``
first, then ``evidence/demo_runs/agents``) and skips explicitly when none exists —
no fabricated run is ever substituted for a missing measurement.

Execution: ``python -m unittest tests.test_decision_agents_source -v``.
"""

import glob
import json
import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO_ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from orvyren.decision import agents_source  # noqa: E402
from orvyren.decision.agents_source import (  # noqa: E402
    SCHEMA,
    UNAVAILABLE,
    AgentsSourceError,
    build_decision_from_agents,
)

#: Keys the decision engine's record always carries (``orvyren.decide``).
REQUIRED_KEYS = ("schema", "case", "mode", "epistemic_verdict", "economic_action",
                 "authorization_verdict", "intent", "rationale", "evidence_refs")

#: Directories scanned for sealed runs, in priority order.
RUN_PATTERNS = ("evidence/agents_live/*/run_outcome.json",
                "evidence/demo_runs/agents/*/*/run_outcome.json")


def discover_run_dirs():
    """Sealed run directories on disk, priority order then lexical order."""
    for pattern in RUN_PATTERNS:
        found = sorted(glob.glob(os.path.join(REPO_ROOT, pattern)))
        if found:
            return [os.path.dirname(path) for path in found]
    return []


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def serialise(payload):
    """Stable serialisation used as the determinism witness."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


class AgentsSourceTest(unittest.TestCase):
    """Contract of ``build_decision_from_agents`` on a real sealed run."""

    @classmethod
    def setUpClass(cls):
        cls.run_dirs = discover_run_dirs()
        if not cls.run_dirs:
            raise unittest.SkipTest(
                "no sealed agents run found (looked for %s) — refusing to "
                "invent a fixture" % ", ".join(RUN_PATTERNS))
        cls.run_dir = cls.run_dirs[0]
        cls.outcome = read_json(os.path.join(cls.run_dir, "run_outcome.json"))
        cls.record = build_decision_from_agents(cls.run_dir)

    # -- shape -------------------------------------------------------------
    def test_declared_schema_is_the_decision_engine_schema(self):
        from orvyren import decide
        self.assertEqual(decide.SCHEMA, SCHEMA)
        self.assertEqual(SCHEMA, self.record["schema"])

    def test_record_carries_the_decision_record_shape(self):
        for key in REQUIRED_KEYS:
            self.assertIn(key, self.record, "missing decision-record key: %s" % key)
        self.assertIsInstance(self.record["case"], str)
        self.assertTrue(self.record["case"])
        self.assertIn(self.record["mode"], ("live", "journal"))
        self.assertEqual(self.outcome.get("case_id"), self.record["case"])
        self.assertIsInstance(self.record["evidence_refs"], list)
        self.assertTrue(self.record["evidence_refs"])
        self.assertIsInstance(self.record["rationale"], str)
        self.assertTrue(self.record["rationale"])

    def test_source_block_names_the_run_it_came_from(self):
        source = self.record["source"]
        self.assertEqual("agents", source["kind"])
        self.assertEqual(os.path.relpath(self.run_dir, REPO_ROOT).replace("\\", "/"),
                         source["run_dir"])
        run_json = read_json(os.path.join(self.run_dir, "run.json"))
        self.assertEqual(run_json["run_id"], source["run_id"])
        self.assertEqual(run_json["schema"], source["run_schema"])
        self.assertEqual(self.outcome["schema"], source["outcome_schema"])

    def test_case_id_argument_overrides_the_declared_case(self):
        record = build_decision_from_agents(self.run_dir, case_id="override-case")
        self.assertEqual("override-case", record["case"])
        self.assertEqual("argument", record["source"]["case_id_source"])

    # -- abstention (the normal v1 path) -----------------------------------
    def test_abstention_is_motivated_and_quotes_non_recherche_verbatim(self):
        outcome = self.outcome.get("outcome") or {}
        if not outcome.get("inconclusive") and \
                self.outcome.get("escalation") != "REQUIRE_APPROVAL":
            self.skipTest("the sealed run on disk is conclusive — nothing to abstain on")
        self.assertIsNone(self.record["intent"])
        self.assertIsNone(self.record["economic_action"])
        self.assertEqual("REQUIRE_APPROVAL", self.record["authorization_verdict"])
        self.assertIsNotNone(self.record["abstention"])
        declared = list(outcome.get("non_recherche") or [])
        self.assertEqual(declared, self.record["what_would_change"])
        # verbatim, not merely equal after a round-trip through another shape
        self.assertEqual(json.dumps(declared, ensure_ascii=False),
                         json.dumps(self.record["what_would_change"], ensure_ascii=False))
        self.assertEqual(declared,
                         self.record["abstention"]["what_would_change_the_verdict"])

    # -- determinism -------------------------------------------------------
    def test_two_calls_are_byte_identical(self):
        first = build_decision_from_agents(self.run_dir)
        second = build_decision_from_agents(self.run_dir)
        self.assertEqual(serialise(first), serialise(second))

    # -- provenance --------------------------------------------------------
    def test_evidence_refs_are_real_chain_heads(self):
        journals = self.outcome.get("journals") or {}
        expected = [{"source": "agents_journal:%s" % role,
                     "value": journals[role]["chain_head"]}
                    for role in sorted(journals)]
        self.assertEqual(expected, self.record["evidence_refs"])
        for ref in self.record["evidence_refs"]:
            self.assertEqual({"source", "value"}, set(ref))
            self.assertTrue(ref["source"].startswith("agents_journal:"))
            self.assertEqual(64, len(ref["value"]))
            self.assertIn(ref["value"].strip(), [entry["chain_head"]
                                                for entry in journals.values()])
        self.assertEqual({role: journals[role]["chain_head"] for role in journals},
                         self.record["source"]["chain_heads"])
        self.assertEqual({role: journals[role]["lines"] for role in journals},
                         self.record["source"]["journal_lines"])

    # -- declared replayability (rule 6) -----------------------------------
    def test_replayability_is_declared_not_raised(self):
        source = self.record["source"]
        self.assertEqual(source["mode"] == "journal", source["replayable"])
        self.assertIsInstance(source["replayable_reason"], str)
        self.assertTrue(source["replayable_reason"])

    def test_journal_mode_run_is_declared_replayable(self):
        journal_runs = [path for pattern in RUN_PATTERNS
                        for path in sorted(glob.glob(os.path.join(REPO_ROOT, pattern)))
                        if read_json(path).get("mode") == "journal"]
        if not journal_runs:
            self.skipTest("no journal-mode sealed run on disk")
        record = build_decision_from_agents(os.path.dirname(journal_runs[0]))
        self.assertEqual("journal", record["mode"])
        self.assertTrue(record["source"]["replayable"])

    # -- no invented figure ------------------------------------------------
    def test_no_figure_is_invented(self):
        outcome = self.outcome.get("outcome") or {}
        if self.record["intent"] is not None:
            # an intent may only copy a declared amount, never compute one
            self.assertIn("amount", self.record["intent"])
            self.assertIsNotNone(self.record["intent"]["amount"])
        for hypothesis in self.record["hypotheses"]:
            # a missing probability is declared, never turned into 0.0
            if hypothesis["probability_declared"] != UNAVAILABLE:
                self.assertNotIn(hypothesis["probability_declared"], ("0", "0.0"))
            self.assertEqual(UNAVAILABLE, self.record["verdicts"][hypothesis["id"]]["verdict"])
        if outcome.get("budget_used"):
            self.assertEqual(outcome["budget_used"],
                             self.record["research_cost"]["budget"])
        else:
            self.assertEqual(UNAVAILABLE, self.record["research_cost"]["budget"])

    # -- a bounded intent needs a complete declared action (rule 4) --------
    def test_bounded_intent_requires_a_complete_declared_action(self):
        complete = {"action": "transfer", "chain_id": 8453, "asset": "USDC",
                    "amount": 100, "recipient": ""}
        intent, reason = agents_source._build_intent(complete, "case-x", "0xabc")
        self.assertEqual("intent-case-x-agents", intent["intent_id"])
        self.assertEqual({"action": "transfer", "chain_id": 8453, "asset": "USDC",
                          "amount": 100, "recipient": "0xabc"},
                         {key: intent[key] for key in
                          ("action", "chain_id", "asset", "amount", "recipient")})
        self.assertIn("declared", reason)

        for missing_key in ("action", "chain_id", "asset", "amount"):
            incomplete = dict(complete)
            incomplete.pop(missing_key)
            intent, reason = agents_source._build_intent(incomplete, "case-x", "0xabc")
            self.assertIsNone(intent, "a missing %s must not produce an intent"
                              % missing_key)
            self.assertIn(missing_key, reason)

        # a declared amount is copied, never recomputed or rounded
        intent, _ = agents_source._build_intent(complete, "case-x", "")
        self.assertEqual(100, intent["amount"])
        self.assertEqual("", intent["recipient"])

    # -- failures are explicit, never silent -------------------------------
    def test_missing_directory_raises(self):
        with self.assertRaises(AgentsSourceError):
            build_decision_from_agents(os.path.join(REPO_ROOT, "no-such-run-dir-xyz"))

    def test_directory_without_run_outcome_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "run.json"), "w", encoding="utf-8",
                      newline="\n") as handle:
                json.dump({"schema": "orvyren/agent-run/v1"}, handle)
            with self.assertRaises(AgentsSourceError):
                build_decision_from_agents(tmp)


if __name__ == "__main__":
    unittest.main()
