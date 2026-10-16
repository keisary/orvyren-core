#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench — « une décision complète est une commande » (W3 [DONE]).

Couvre : la commande ``python -m orvyren.decide --case usdc-2023-03 --replay`` ;
les **3 axes présents et distincts** dans le JSON ; un cas où une entrée manque
reste ``INCONCLUSIVE`` (jamais « supposé satisfait ») ; le coût réel de recherche
et l'intent borné sont reportés ; deux exécutions sont identiques à l'octet près.

Execution: ``python -m pytest tests/test_decide_cli.py -q``.
"""

import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO_ROOT, "src")
CORPUS_ABS = os.path.join(REPO_ROOT, "corpus", "usdc_observations.csv")

SUPPLY_VENUES = {"defillama_supply_aggregate", "defillama_supply_ethereum"}


def run_decide(args, timeout=240):
    """Run ``python -m orvyren.decide`` with the repository src on PYTHONPATH."""
    return subprocess.run(
        [sys.executable, "-m", "orvyren.decide"] + args,
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout,
        env=dict(os.environ, PYTHONPATH=SRC))


def write_corpus_without_supply(target_path):
    """Copy the frozen corpus minus every supply row (INCONCLUSIVE case)."""
    with open(CORPUS_ABS, newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames
        rows = [row for row in reader if row["venue"] not in SUPPLY_VENUES]
    with open(target_path, "w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class TestDecideCommand(unittest.TestCase):
    """The one command of W3 [DONE] — full decision, offline, deterministic."""

    def test_command_writes_a_record_with_three_separate_axes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "decision_record.json")
            run = run_decide(["--case", "usdc-2023-03", "--replay", "--out", out])
            self.assertEqual(0, run.returncode, run.stderr)
            with open(out, encoding="utf-8") as handle:
                payload = json.load(handle)

            self.assertEqual("orvyren-decision-record/v1", payload["schema"])
            # The three axes are present, separate and never fused (DOC2 §5.4.4).
            for axis in ("epistemic_verdict", "economic_action",
                         "authorization_verdict"):
                self.assertIn(axis, payload, axis)
            self.assertEqual("CONCLUANT", payload["epistemic_verdict"])
            self.assertEqual("CONVERTIR/TRANSFÉRER", payload["economic_action"])
            # The bounded Intent accompanies the action ([I]).
            self.assertIsNotNone(payload["intent"])
            self.assertEqual("transfer", payload["intent"]["action"])
            self.assertGreater(payload["intent"]["amount"], 0)
            # Real research cost, straight from the RDOF trace.
            self.assertEqual(1, len(payload["rdof"]["trace"]))
            self.assertEqual("P-6.3", payload["rdof"]["trace"][0]["chosen"])
            self.assertGreater(
                payload["research_cost"]["budget"]["consomme"]["secondes"], 0.0)
            # Falsifiable hypotheses registered in the W2 registry (L3.1).
            self.assertEqual(3, payload["hypotheses_registry"]["count"])
            self.assertEqual(["CREATED"], payload["hypotheses_registry"]["etats"])

    def test_missing_input_stays_inconclusive_and_enriched(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = os.path.join(tmp, "corpus_without_supply.csv")
            write_corpus_without_supply(corpus)
            out = os.path.join(tmp, "record.json")
            run = run_decide(["--case", "usdc-2023-03", "--replay",
                              "--corpus", corpus, "--out", out])
            self.assertEqual(0, run.returncode, run.stderr)
            with open(out, encoding="utf-8") as handle:
                payload = json.load(handle)
            self.assertEqual("INCONCLUSIVE", payload["epistemic_verdict"])
            self.assertIsNone(payload["intent"])
            # Enriched INCONCLUSIVE: an actionable research plan, never a mute refusal.
            self.assertIsNotNone(payload["abstention"])
            self.assertTrue(payload["abstention"]["what_would_change_the_verdict"])

    def test_two_runs_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            outs = [os.path.join(tmp, "a.json"), os.path.join(tmp, "b.json")]
            for out in outs:
                run = run_decide(["--case", "usdc-2023-03", "--replay", "--out", out])
                self.assertEqual(0, run.returncode, run.stderr)
            with open(outs[0], "rb") as handle:
                first = handle.read()
            with open(outs[1], "rb") as handle:
                second = handle.read()
            self.assertEqual(first, second, "the decision record is not deterministic")

    def test_unknown_case_is_rejected(self):
        run = run_decide(["--case", "inconnu", "--replay"])
        self.assertEqual(4, run.returncode)
        self.assertIn("usdc-2023-03", run.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
