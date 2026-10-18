#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regression tests — 2026-10-18 graph/evaluation/benchmark review fixes.

One class per fix of this review pass:

* **R1** — ``graph/api.py`` Q2 (``dependency_paths``): every result row shares
  one schema (``node, depth, path, sign``). A path whose edge carries a legacy
  or direct-writer ``sign_prior = 'ambigu'`` (the storage triggers only guard
  INSERTs, migrated/direct rows can still carry it) is mapped to
  ``sign = "ambigu"`` without leaking the raw SQL flag columns into the row;
* **R2** — ``evaluation/harness.py`` (``run_set`` aggregates): ``R⁺``/``R⁻``
  are the G1 quantities measured **against A0** (``loss.py``:
  ``R⁺ = max(0, L(A0) − L(a))``, ``R⁻ = max(0, L(a) − L(A0))``), never
  ``max/min`` of the oracle regret ``R`` (which is ≥ 0 by construction and
  pinned ``R⁻`` to a structural zero in every published report);
* **R3** — ``evaluation/bench.py`` + ``run_benchmark_ab.py``: the declared
  A0-engine substitution (``a0_rdof: false`` → ``--no-rdof``, the RDOF/axes
  enrichment is scoped to case ``usdc-2023-03``) is **recorded per run**, as
  the benchmark's limitations section claims.

Run: python -m unittest tests.test_graph_eval_review_fixes
"""

import os
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from orvyren.evaluation import bench  # noqa: E402
from orvyren.evaluation import harness  # noqa: E402
from orvyren.evaluation import report as report_mod  # noqa: E402
from orvyren.graph import api  # noqa: E402

DEV_PERIODS = ["2023-02", "2023-03"]

# ---------------------------------------------------------------------------
# R1 — Q2 row schema uniformity
# ---------------------------------------------------------------------------

#: Columns the Q2 SQL touches. Written directly (no GraphStore triggers) to
#: reproduce the rows a legacy v2 migration or a direct sqlite3 writer can
#: produce: a DEPENDS_ON/AFFECTS edge whose ``sign_prior`` is 'ambigu'.
_Q2_COLUMNS = """
CREATE TABLE relations (
    row_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    relation_id      TEXT NOT NULL,
    revision         INTEGER NOT NULL,
    kind             TEXT NOT NULL,
    src              TEXT NOT NULL,
    dst              TEXT NOT NULL,
    sign_prior       TEXT NOT NULL DEFAULT 'ambigu',
    lifecycle        TEXT NOT NULL DEFAULT 'DISCOVERED',
    validation_status TEXT NOT NULL DEFAULT 'PENDING',
    valid_from       TEXT,
    valid_to         TEXT,
    valid_from_block INTEGER,
    valid_to_block   INTEGER,
    inserted_at      TEXT NOT NULL DEFAULT ''
)
"""


class GraphApiQ2RowContractTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "legacy.sqlite")
        con = sqlite3.connect(self.db)
        try:
            con.executescript(_Q2_COLUMNS)
            rows = [
                # legacy/direct-writer edge: propagatable kind with the
                # migration default sign 'ambigu'
                ("rel-ambigu", 1, "DEPENDS_ON", "node:x", "node:y", "ambigu"),
                # negative edge: the '-' must survive, the flags must not
                ("rel-neg", 1, "AFFECTS", "node:x", "node:z", "-"),
            ]
            for relation_id, revision, kind, src, dst, sign in rows:
                con.execute(
                    "INSERT INTO relations (relation_id, revision, kind, src, dst, "
                    "sign_prior, lifecycle, validation_status, inserted_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', 'VALIDATED', '2026-01-01T00:00:00Z')",
                    (relation_id, revision, kind, src, dst, sign))
            con.commit()
        finally:
            con.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_rows_share_one_schema_even_for_legacy_ambiguous_signs(self):
        result = api.dependency_paths(self.db, "node:x", "node:y", max_depth=2)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["count"], 1)
        row = result["rows"][0]
        self.assertEqual(set(row), {"node", "depth", "path", "sign"},
                         "no raw SQL flag column may leak into a Q2 row: %r" % row)
        self.assertEqual(row["sign"], "ambigu")

    def test_negative_sign_is_preserved_without_leaking_flags(self):
        result = api.dependency_paths(self.db, "node:x", "node:z", max_depth=2)
        self.assertEqual(result["count"], 1)
        row = result["rows"][0]
        self.assertEqual(set(row), {"node", "depth", "path", "sign"})
        self.assertEqual(row["sign"], "-")


# ---------------------------------------------------------------------------
# R2 — aggregates: R⁻/R⁺ measured against A0
# ---------------------------------------------------------------------------

def _detail(window_id, losses, regrets):
    """One OK window detail; ``regrets`` maps label -> oracle regret R."""
    configs = {}
    for label in harness.CONFIG_LABELS:
        if label in losses:
            configs[label] = {"loss": losses[label],
                              "regret": {"R": regrets.get(label, 0.0)}}
        else:
            configs[label] = {"actions": None, "status": "DECLARED"}
    return {"window_id": window_id, "status": "OK", "notes": [], "configs": configs}


class HarnessAggregateRegretTest(unittest.TestCase):
    def _run(self):
        # Window A: A1 beats no-action (R⁺ 4, R⁻ 0), A2 is worse (R⁺ 0, R⁻ 2).
        detail_a = _detail("w-a",
                           {"A0": 10.0, "A1": 6.0, "A2": 12.0},
                           {"A0": 0.3, "A1": 0.9, "A2": 0.1})
        # Window B: A1 is worse (R⁺ 0, R⁻ 3), A2 ties no-action (0, 0).
        detail_b = _detail("w-b",
                           {"A0": 5.0, "A1": 8.0, "A2": 5.0},
                           {"A0": 0.2, "A1": 0.7, "A2": 0.4})
        with mock.patch.object(harness, "runs_for_set",
                               return_value=[object(), object()]), \
                mock.patch.object(harness, "run_window",
                                  side_effect=[detail_a, detail_b]):
            return harness.run_set("dev", b0_draws=1, calibration_periods=DEV_PERIODS)

    def test_mean_r_plus_r_minus_follow_the_g1_definition_against_a0(self):
        content = self._run()["content"]
        aggregates = content["aggregates"]
        self.assertAlmostEqual(aggregates["A1"]["mean_R_plus"], 2.0)    # (4 + 0) / 2
        self.assertAlmostEqual(aggregates["A1"]["mean_R_minus"], 1.5)   # (0 + 3) / 2
        self.assertAlmostEqual(aggregates["A2"]["mean_R_plus"], 0.0)    # (0 + 0) / 2
        self.assertAlmostEqual(aggregates["A2"]["mean_R_minus"], 1.0)   # (2 + 0) / 2
        self.assertAlmostEqual(aggregates["A0"]["mean_R_plus"], 0.0)
        self.assertAlmostEqual(aggregates["A0"]["mean_R_minus"], 0.0)
        self.assertAlmostEqual(aggregates["A1"]["mean_loss"], 7.0)

    def test_r_minus_is_measured_not_structurally_zero(self):
        # The pre-fix formula (min(R, 0) of the oracle regret) pinned R⁻ to a
        # constant 0.0000 in every published report.
        content = self._run()["content"]
        self.assertGreater(content["aggregates"]["A1"]["mean_R_minus"], 0.0)
        self.assertGreater(content["aggregates"]["A2"]["mean_R_minus"], 0.0)

    def test_oracle_regret_r_stays_published_separately(self):
        content = self._run()["content"]
        self.assertEqual(content["aggregates"]["A1"]["regrets"], [0.9, 0.7])

    def test_report_renders_the_measured_r_minus(self):
        result = self._run()
        out_dir = tempfile.mkdtemp(prefix="orvyren_rminus_")
        self.addCleanup(__import__("shutil").rmtree, out_dir, True)
        paths = report_mod.render_evaluation_report(content=result["content"],
                                                    out_dir=out_dir)
        with open(paths["md_path"], "r", encoding="utf-8") as handle:
            text = handle.read()
        # A1 row: N=2, mean L 7.0000, R⁺ 2.0000, R⁻ 1.5000
        self.assertIn("| A1 | 2 | 7.0000 | 2.0000 | 1.5000 |", text)


# ---------------------------------------------------------------------------
# R3 — the A0 engine variant is recorded per run
# ---------------------------------------------------------------------------

class BenchEngineVariantRecordingTest(unittest.TestCase):
    def test_measure_a0_records_the_engine_variant(self):
        payload = {"status": "ok", "wall_seconds": 0.1, "exit_code": 0,
                   "a0_rdof": False,
                   "decision_record": {"decision": {"verdict": "NO_ACTION"}}}
        row = bench.measure_a0("case-x", 1, payload)
        self.assertIs(row["detail"]["a0_rdof"], False)
        payload_rdof = dict(payload, a0_rdof=True)
        row = bench.measure_a0("case-x", 1, payload_rdof)
        self.assertIs(row["detail"]["a0_rdof"], True)
        # a payload that does not declare the variant reports it as unknown,
        # never as a guess
        row = bench.measure_a0("case-x", 1, {key: value for key, value in payload.items()
                                            if key != "a0_rdof"})
        self.assertIsNone(row["detail"]["a0_rdof"])

    def test_runner_a0_declares_the_variant_from_the_case_fixture(self):
        import run_benchmark_ab as runner_mod
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        case = {"case_id": "case-x", "corpus": "corpus/usdc_observations.csv",
                "a0_rdof": False}
        with mock.patch.object(
                runner_mod, "_run_subprocess",
                return_value={"exit_code": 1, "wall_seconds": 0.1,
                              "stdout_tail": "", "stderr_tail": "boom"}):
            payload = runner_mod.runner_a0(case, os.path.join(tmp.name, "run"), 1)
        self.assertIs(payload["a0_rdof"], False)
        case_default = {"case_id": "case-x", "corpus": "corpus/usdc_observations.csv"}
        with mock.patch.object(
                runner_mod, "_run_subprocess",
                return_value={"exit_code": 1, "wall_seconds": 0.1,
                              "stdout_tail": "", "stderr_tail": "boom"}):
            payload = runner_mod.runner_a0(case_default, os.path.join(tmp.name, "run2"), 1)
        self.assertIs(payload["a0_rdof"], True)


if __name__ == "__main__":
    unittest.main()
