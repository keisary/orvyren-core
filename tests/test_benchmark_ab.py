#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — tests for the honest mini-benchmark A0 vs A2 (P0-5).

Coverage:

* case fixture: shape, explicit ``synthetic`` flags, a labelled placebo case,
  and every ground-truth figure resolving to its declared source file/path
  (``fixtures/graphs/usdc_2023-03.json``, ``evidence/episode_usdc_2023-03.json``
  … — no figure is ever guessed);
* verdict normalisation for both modes (ALLOW/DENY/REQUIRE_APPROVAL/NO_ACTION/
  abstention) and quality scoring vs the declared expectation;
* aggregates (counts, rates, costs, abstentions, provenance rejections);
* the honesty gate: mandatory banner, superiority claims refused at N < 100,
  claim-shaped wording absent from the rendered markdown, and failures/no-legs
  rendered as visibly as successes;
* placebo handling: the fabricated calm corpus is materialised deterministically
  and the real deterministic engine (run_decision.py, no LLM) lands on
  NO_ACTION/abstention on it;
* one light integration test that plays ``bench.run_benchmark`` on doubles
  (no real LLM call anywhere).

Run: python -m unittest tests.test_benchmark_ab
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from orvyren.evaluation import bench  # noqa: E402

CASES_PATH = os.path.join(ROOT, "fixtures", "benchmark", "cases.json")


def load_fixture():
    with open(CASES_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def case_by_id(payload, case_id):
    for case in payload["cases"]:
        if case["case_id"] == case_id:
            return case
    raise AssertionError("case %r missing from fixture" % case_id)


# ---------------------------------------------------------------------------
# Fixture + ground truth
# ---------------------------------------------------------------------------

class CasesFixtureTest(unittest.TestCase):
    def setUp(self):
        self.payload = load_fixture()

    def test_fixture_shape_and_placebo_labelled(self):
        bench.validate_cases(self.payload)
        self.assertEqual(self.payload["schema_version"], bench.CASES_SCHEMA_VERSION)
        synthetic = [case for case in self.payload["cases"] if case.get("synthetic")]
        self.assertGreaterEqual(len(synthetic), 1, "at least one explicitly synthetic placebo case")
        for case in synthetic:
            self.assertTrue(case["case_id"].startswith("placebo") or "placebo" in case["title"].lower(),
                            "placebo must be identifiable by id/title")
            for row in case["ground_truth"]:
                self.assertTrue(row.get("synthetic"),
                                "fabricated figures must never be presented as real")
        real = [case for case in self.payload["cases"] if not case.get("synthetic")]
        self.assertGreaterEqual(len(real), 1, "at least one real episode case")

    def test_expectations_are_one_sided_never_both(self):
        for case in self.payload["cases"]:
            acceptable = set(case["expectation"]["acceptable_verdicts"])
            wrong = set(case["expectation"]["miss_verdicts"])
            self.assertFalse(acceptable & wrong)

    def test_ground_truth_resolves_to_declared_sources(self):
        mismatches = bench.verify_ground_truth(self.payload, ROOT)
        self.assertEqual(mismatches, [], "every ground-truth figure must resolve exactly")

    def test_ground_truth_covers_the_episode_minima(self):
        usdc = case_by_id(self.payload, "usdc-2023-03")
        claims = " ".join(row["claim"] for row in usdc["ground_truth"])
        self.assertIn("market minimum, Bitstamp", claims)
        self.assertIn("dispersion", claims)
        values = {(row["source_file"], row["source_json_path"]): row["value"]
                  for row in usdc["ground_truth"]}
        self.assertEqual(values[("evidence/episode_usdc_2023-03.json",
                                "facts.minima.bitstamp.low")], 0.80526)
        self.assertEqual(values[("evidence/episode_usdc_2023-03.json",
                                "facts.signals.dispersion_window_bps.value_bps")], 870.07)

    def test_verify_ground_truth_detects_a_forged_figure(self):
        payload = load_fixture()
        usdc = case_by_id(payload, "usdc-2023-03")
        usdc["ground_truth"][0]["value"] = "not-the-recorded-value"
        mismatches = bench.verify_ground_truth(payload, ROOT)
        self.assertEqual(len(mismatches), 1)
        self.assertIn("mismatch", mismatches[0]["error"])

    def test_resolve_json_path_variants(self):
        data = {"a": {"b": [{"k": "x", "v": 1}, {"k": "y", "v": 2}]},
                "weird.key": 3, "list": [10, 20]}
        self.assertEqual(bench.resolve_json_path(data, "a.b[k=y].v"), 2)
        self.assertEqual(bench.resolve_json_path(data, "a.b[0].v"), 1)
        self.assertEqual(bench.resolve_json_path(data, '["weird.key"]'), 3)
        self.assertEqual(bench.resolve_json_path(data, "list[1]"), 20)
        with self.assertRaises(bench.CasesError):
            bench.resolve_json_path(data, "a.missing")
        with self.assertRaises(bench.CasesError):
            bench.resolve_json_path(data, "a.b[k=zzz].v")


# ---------------------------------------------------------------------------
# Verdict normalisation + scoring
# ---------------------------------------------------------------------------

class NormalisationTest(unittest.TestCase):
    def test_a0_action_recommended_maps_to_allow(self):
        record = {"decision": {"verdict": "ACTION_RECOMMENDED"},
                  "axes": {"authorization_verdict": None}}
        norm = bench.normalize_a0(record)
        self.assertEqual(norm["verdict"], bench.ALLOW)
        self.assertFalse(norm["abstained"])

    def test_a0_authorization_axis_wins_when_evaluated(self):
        base = {"decision": {"verdict": "ACTION_RECOMMENDED"}}
        self.assertEqual(bench.normalize_a0(dict(base, axes={"authorization_verdict": "DENY"}))["verdict"],
                         bench.DENY)
        self.assertEqual(bench.normalize_a0(dict(base, axes={"authorization_verdict": "REQUIRE_APPROVAL"}))["verdict"],
                         bench.REQUIRE_APPROVAL)

    def test_a0_no_action_and_inconclusive(self):
        self.assertEqual(bench.normalize_a0({"decision": {"verdict": "NO_ACTION"}})["verdict"],
                         bench.NO_ACTION)
        norm = bench.normalize_a0({"decision": {"verdict": "INCONCLUSIVE"}})
        self.assertEqual(norm["verdict"], bench.ABSTENTION)
        self.assertTrue(norm["abstained"])

    def test_a0_unknown_never_guessed(self):
        self.assertEqual(bench.normalize_a0({})["verdict"], bench.UNKNOWN)
        self.assertEqual(bench.normalize_a0({"decision": {"verdict": "SOMETHING_NEW"}})["verdict"],
                         bench.UNKNOWN)

    def test_a2_fragility_gate_mapping(self):
        base = {"outcome": {"inconclusive": False, "state": "DONE"},
                "critique": {"verdict_lecture": "FRAGILE"}}
        self.assertEqual(bench.normalize_a2(dict(base, escalation="REQUIRE_APPROVAL"))["verdict"],
                         bench.REQUIRE_APPROVAL)
        self.assertEqual(bench.normalize_a2(dict(base, escalation=None))["verdict"], bench.ALLOW)
        abstained = bench.normalize_a2({"outcome": {"inconclusive": True},
                                        "escalation": "REQUIRE_APPROVAL"})
        self.assertEqual(abstained["verdict"], bench.ABSTENTION)
        self.assertTrue(abstained["abstained"])

    def test_a2_abstention_outranks_the_brake(self):
        norm = bench.normalize_a2({"outcome": {"inconclusive": True}, "escalation": "REQUIRE_APPROVAL"})
        self.assertEqual(norm["verdict"], bench.ABSTENTION)
        self.assertTrue(norm["braked"], "the brake stays visible even when the verdict is the abstention")

    def test_a2_empty_outcome_is_unknown(self):
        self.assertEqual(bench.normalize_a2({})["verdict"], bench.UNKNOWN)

    def test_score_verdict_against_declared_expectation(self):
        expectation = {"acceptable_verdicts": [bench.NO_ACTION, bench.ABSTENTION],
                       "miss_verdicts": [bench.ALLOW, bench.DENY, bench.REQUIRE_APPROVAL]}
        self.assertEqual(bench.score_verdict(bench.NO_ACTION, expectation), bench.QUALITY_MATCH)
        self.assertEqual(bench.score_verdict(bench.ABSTENTION, expectation), bench.QUALITY_MATCH)
        self.assertEqual(bench.score_verdict(bench.ALLOW, expectation), bench.QUALITY_MISS)
        self.assertEqual(bench.score_verdict(bench.REQUIRE_APPROVAL, expectation), bench.QUALITY_MISS)
        self.assertEqual(bench.score_verdict("unranked-value", expectation), bench.QUALITY_OTHER)
        self.assertEqual(bench.score_verdict(None, expectation), bench.QUALITY_NOT_SCORED)


# ---------------------------------------------------------------------------
# Measurements + aggregates
# ---------------------------------------------------------------------------

def a0_payload(verdict="ACTION_RECOMMENDED", wall=0.5, auth=None):
    return {"status": "ok", "wall_seconds": wall, "exit_code": 0,
            "decision_record": {
                "decision": {"verdict": verdict,
                             "action": {"type": "transfer", "amount_usdc": 100.0},
                             "missing_inputs": []},
                "hypothesis_verdicts": {"H1": {"verdict": "REFUTED"}, "H2": {"verdict": "SUPPORTED"}},
                "axes": {"epistemic_verdict": "CONCLUANT", "authorization_verdict": auth},
                "rdof": {"stop": "c1", "budget": {"consomme": {"recherches": 1, "appels": 1, "secondes": 0.65}}},
                "inputs_summary": {"corpus": {"sha256": "ab", "observations_in_window": 444}},
            }}


def a2_payload(inconclusive=False, escalation="REQUIRE_APPROVAL", critique="FRAGILE", cost=0.001827,
               llm=5.0, tools=2.0, wall=1.2):
    return {"status": "ok", "wall_seconds": wall, "exit_code": 0,
            "run_outcome": {
                "schema": "orvyren/agent-run-outcome/v1",
                "outcome": {"inconclusive": inconclusive, "state": "DONE",
                            "stop_condition": "ARRET-1", "motif": "test",
                            "non_recherche": ["executability depth not measured"],
                            "budget_used": {"cost_usd": cost, "llm_calls": llm,
                                            "tool_calls": tools, "wall_seconds": 0.14}},
                "critique": {"verdict_lecture": critique},
                "escalation": escalation,
                "journals": {"orchestrator": {"lines": 11}, "critic": {"lines": 1}},
            },
            "journal_entries": [
                {"validation": {"provenance_ok": True, "schema_ok": True}},
                {"validation": {"provenance_ok": False, "motif": "provenance: incomplete"}},
                {"validation": {"provenance_ok": False, "motif": "provenance: unknown ref"}},
            ]}


class MeasurementTest(unittest.TestCase):
    def setUp(self):
        self.expectation = {"acceptable_verdicts": [bench.ALLOW, bench.REQUIRE_APPROVAL, bench.ABSTENTION],
                            "miss_verdicts": [bench.NO_ACTION]}

    def test_measure_a0_is_zero_cost_by_construction(self):
        row = bench.measure_a0("usdc-2023-03", 1, a0_payload(), self.expectation)
        self.assertEqual(row["verdict"], bench.ALLOW)
        self.assertEqual(row["quality"], bench.QUALITY_MATCH)
        self.assertEqual(row["cost_usd"], 0.0)
        self.assertEqual(row["llm_calls"], 0.0)
        self.assertEqual(row["tool_calls"], 0.0)
        self.assertEqual(row["claims_rejected_provenance"], 0)
        self.assertTrue(row["detail"]["deterministic"])
        self.assertEqual(row["detail"]["rdof_searches"], 1)

    def test_measure_a2_records_budget_and_provenance_rejections(self):
        row = bench.measure_a2("usdc-2023-03", 1, a2_payload(), self.expectation)
        self.assertEqual(row["verdict"], bench.REQUIRE_APPROVAL)
        self.assertEqual(row["quality"], bench.QUALITY_MATCH)
        self.assertAlmostEqual(row["cost_usd"], 0.001827)
        self.assertEqual(row["llm_calls"], 5.0)
        self.assertEqual(row["tool_calls"], 2.0)
        self.assertEqual(row["claims_rejected_provenance"], 2)
        self.assertTrue(row["detail"]["braked"])
        self.assertIn("recorded offline replay", row["detail"]["cost_note"])

    def test_measure_failure_is_recorded_not_inferred(self):
        row = bench.measure_a2("placebo-calm-2023-03", 1,
                               {"status": "not_executed", "wall_seconds": 0.1,
                                "exit_code": 1, "error": "E_CASE_UNKNOWN: run_inputs.json missing"})
        self.assertEqual(row["status"], "not_executed")
        self.assertIsNone(row["verdict"])
        self.assertEqual(row["quality"], bench.QUALITY_NOT_SCORED)
        self.assertIn("E_CASE_UNKNOWN", row["notes"][0])

    def test_count_provenance_rejections_counts_only_explicit_failures(self):
        entries = [{"validation": {"provenance_ok": True}},
                   {"validation": {"provenance_ok": False}},
                   {"validation": {}},
                   {"no_validation": 1},
                   {}]
        self.assertEqual(bench.count_provenance_rejections(entries), 1)

    def test_aggregate_computes_counts_rates_and_totals(self):
        rows = [
            bench.measure_a0("usdc-2023-03", 1, a0_payload(), self.expectation),
            bench.measure_a0("usdc-2023-03", 2, a0_payload(), self.expectation),
            bench.measure_a2("usdc-2023-03", 1, a2_payload(), self.expectation),
            bench.measure_a2("usdc-2023-03", 2, a2_payload(inconclusive=True), self.expectation),
            bench.measure_a2("usdc-2023-03", 3, {"status": "not_executed", "error": "E_CASE_UNKNOWN"}),
        ]
        agg = bench.aggregate(rows)
        self.assertEqual(agg["n_runs"], 5)
        self.assertEqual(agg["n_ok"], 4)
        self.assertEqual(agg["n_not_executed"], 1)
        self.assertEqual(agg["n_scored"], 4)
        self.assertEqual(agg["quality_counts"][bench.QUALITY_MATCH], 4)
        self.assertEqual(agg["quality_counts"][bench.QUALITY_MISS], 0)
        self.assertAlmostEqual(agg["match_rate"], 1.0)
        self.assertEqual(agg["abstentions"], 1)
        self.assertAlmostEqual(agg["cost_usd_total"], 2 * 0.001827)
        self.assertEqual(agg["llm_calls_total"], 10.0)
        self.assertEqual(agg["claims_rejected_provenance_total"], 4)
        self.assertEqual(agg["verdict_counts"],
                         {bench.ALLOW: 2, bench.REQUIRE_APPROVAL: 1, bench.ABSTENTION: 1})

    def test_delta_tags_are_symmetric_and_visible(self):
        a0 = [bench.measure_a0("c", 1, a0_payload(), self.expectation)]
        a2 = [bench.measure_a2("c", 1, a2_payload(), self.expectation)]
        self.assertEqual(bench.delta_tag(a0, a2)["tag"], "agents_abstain_where_engine_acts")
        same_a2 = [bench.measure_a2("c", 1, a2_payload(escalation=None, critique="TENABLE"),
                                    self.expectation)]
        self.assertEqual(bench.delta_tag(a0, same_a2)["tag"], "same_call")
        # A0 misses (NO_ACTION is a declared miss on the real episode) while A2
        # matches: the divergence is tagged and stays visible.
        a0_miss = [bench.measure_a0("c", 1, a0_payload(verdict="NO_ACTION"), self.expectation)]
        self.assertEqual(bench.delta_tag(a0_miss, a2)["tag"], "agents_match_a0_miss")
        self.assertEqual(bench.delta_tag(a0, [])["tag"], "a2_not_executed")
        degrade_a2 = [bench.measure_a2("c", 1, a2_payload(escalation=None, critique="TENABLE"),
                                       {"acceptable_verdicts": [bench.REQUIRE_APPROVAL],
                                        "miss_verdicts": [bench.ALLOW]})]
        self.assertEqual(bench.delta_tag(a0, degrade_a2)["tag"], "agents_miss_a0_match")


# ---------------------------------------------------------------------------
# Honesty gate: banner + refusal of superiority at small N
# ---------------------------------------------------------------------------

class HonestyGateTest(unittest.TestCase):
    def _report(self, n=3):
        measurements = [bench.measure_a0("usdc-2023-03", 1, a0_payload())]
        measurements[0]["quality"] = bench.QUALITY_MATCH
        report = bench.build_report(load_fixture(), measurements, budget={"llm_calls": 30})
        report["n_scored_runs"] = n
        report["superiority"] = bench.superiority_block(n)
        return report

    def test_banner_is_exact_and_mandatory(self):
        self.assertEqual(bench.BANNER,
                         "small-N diagnostic run — no superiority claim (G1 threshold N>=100 not reached)")
        text = bench.render_report_md(self._report())
        self.assertIn(bench.BANNER, text)
        broken = self._report()
        broken["banner"] = "something else"
        with self.assertRaises(bench.ReportError):
            bench.render_report_md(broken)
        del broken["banner"]
        with self.assertRaises(bench.ReportError):
            bench.render_report_md(broken)

    def test_superiority_refused_below_100(self):
        for n in (0, 1, 3, 99):
            with self.assertRaises(bench.SuperiorityClaimRefused):
                bench.require_superiority_threshold(n)
        self.assertEqual(bench.require_superiority_threshold(100), 100)
        block = bench.superiority_block(3)
        self.assertFalse(block["claimable"])
        self.assertIn("refused", block["statement"])
        self.assertIn("N=3", block["statement"])
        self.assertTrue(bench.superiority_block(100)["claimable"])

    def test_report_never_contains_superiority_claims(self):
        text = bench.render_report_md(self._report())
        self.assertEqual(bench.contains_superiority_claim(text), [])
        self.assertIn("no superiority claim", text)
        self.assertTrue(any("refused" in line.lower() or "no superiority" in line.lower()
                            for line in text.splitlines()))

    def test_claim_wording_detector_catches_real_claims(self):
        self.assertTrue(bench.contains_superiority_claim("A2 outperforms A0 on this episode"))
        self.assertTrue(bench.contains_superiority_claim("les agents sont meilleurs que le moteur"))
        self.assertEqual(bench.contains_superiority_claim(bench.BANNER), [])

    def test_report_shows_failures_as_visibly_as_successes(self):
        measurements = [
            bench.measure_a0("placebo-calm-2023-03", 1,
                             a0_payload(verdict="NO_ACTION")),
            bench.measure_a2("placebo-calm-2023-03", 1,
                             {"status": "not_executed", "error": "E_CASE_UNKNOWN: no recorded inputs"}),
        ]
        measurements[0]["quality"] = bench.QUALITY_MATCH
        report = bench.build_report(load_fixture(), measurements)
        text = bench.render_report_md(report)
        self.assertIn("placebo-calm-2023-03", text)
        self.assertIn("not_executed", text)
        self.assertIn("E_CASE_UNKNOWN", text)
        self.assertIn("never inferred", text)

    def test_honesty_sections_are_always_rendered(self):
        text = bench.render_report_md(self._report())
        for heading in ("## When the agents help / add nothing / must abstain",
                        "### When the agents help",
                        "### When the agents add nothing — or degrade",
                        "### When the agents must abstain",
                        "## Superiority", "## Limitations", "## Raw runs"):
            self.assertIn(heading, text)
        self.assertIn("measured: **none** in this sample", text)

    def test_run_ids_come_from_the_run_chain_shape(self):
        first = bench.new_run_id("bench")
        second = bench.new_run_id("bench")
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("bench"))


# ---------------------------------------------------------------------------
# Placebo corpus materialisation + real deterministic engine on it
# ---------------------------------------------------------------------------

class PlaceboTest(unittest.TestCase):
    def setUp(self):
        self.payload = load_fixture()
        self.placebo = case_by_id(self.payload, "placebo-calm-2023-03")
        self.tmp = tempfile.mkdtemp(prefix="bench_placebo_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_materialisation_is_deterministic_and_calm(self):
        out_a = os.path.join(self.tmp, "a.csv")
        out_b = os.path.join(self.tmp, "b.csv")
        info_a = bench.materialize_synthetic_corpus(self.placebo, out_a)
        info_b = bench.materialize_synthetic_corpus(self.placebo, out_b)
        self.assertEqual(info_a["sha256"], info_b["sha256"], "fabrication must be deterministic")
        self.assertTrue(info_a["synthetic"])
        with open(out_a, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        self.assertEqual(lines[0], "timestamp_utc,venue,metric,value,extra,retrieved_at")
        self.assertEqual(len(lines) - 1, info_a["rows"])
        prices = []
        venues = set()
        for line in lines[1:]:
            parts = line.split(",")
            venues.add(parts[1])
            self.assertIn("synthetic=true", parts[4], "every fabricated row is stamped synthetic")
            if parts[2] == "price_usd":
                prices.append(float(parts[3]))
        self.assertGreaterEqual(len(prices), 100)
        self.assertTrue(all(0.99 <= price <= 1.01 for price in prices),
                        "placebo prices must stay inside the calm band")
        for venue in ("bitstamp", "binance", "defillama"):
            self.assertIn(venue, venues)

    def test_real_engine_on_placebo_never_finds_a_signal(self):
        run_decision = os.path.join(ROOT, "run_decision.py")
        if not os.path.exists(run_decision):
            self.skipTest("run_decision.py absent from the repository")
        sys.path.insert(0, ROOT)
        import run_benchmark_ab as harness
        run_dir = os.path.join(self.tmp, "a0_run")
        payload = harness.runner_a0(self.placebo, run_dir, 1)
        self.assertEqual(payload["status"], "ok", payload.get("error"))
        row = bench.measure_a0(self.placebo["case_id"], 1, payload,
                               self.placebo["expectation"])
        self.assertIn(row["verdict"], (bench.NO_ACTION, bench.ABSTENTION),
                      "a placebo must not produce a decisive call: %r" % (row,))
        self.assertEqual(row["quality"], bench.QUALITY_MATCH)
        self.assertEqual(row["cost_usd"], 0.0)


# ---------------------------------------------------------------------------
# Light integration: bench.run_benchmark on doubles (no LLM anywhere)
# ---------------------------------------------------------------------------

class DoublesIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.payload = load_fixture()
        self.tmp = tempfile.mkdtemp(prefix="bench_doubles_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_run_benchmark_on_doubles_end_to_end(self):
        def runner_a0(case, run_dir, run_index):
            if case["case_id"] == "placebo-calm-2023-03":
                return a0_payload(verdict="NO_ACTION")
            return a0_payload(verdict="ACTION_RECOMMENDED")

        def runner_a2(case, run_dir, run_index):
            if case["case_id"] == "placebo-calm-2023-03":
                return {"status": "not_executed", "wall_seconds": 0.1, "exit_code": 1,
                        "error": "E_CASE_UNKNOWN: fixtures/agents/placebo-calm-2023-03/run_inputs.json missing"}
            return a2_payload(inconclusive=False, escalation="REQUIRE_APPROVAL")

        report = bench.run_benchmark(self.payload, [], 2, self.tmp,
                                     runner_a0, runner_a2,
                                     budget=self.payload["budget"])
        self.assertEqual(report["schema_version"], bench.SCHEMA_VERSION)
        self.assertEqual(report["n_runs"], 8, "2 cases x 2 modes x 2 runs")
        self.assertEqual(report["n_scored_runs"], 6, "the placebo A2 leg is missing, not inferred")
        self.assertFalse(report["superiority"]["claimable"])
        self.assertEqual(report["banner"], bench.BANNER)

        json_path = os.path.join(self.tmp, "report.json")
        md_path = os.path.join(self.tmp, "report.md")
        self.assertTrue(os.path.exists(json_path))
        self.assertTrue(os.path.exists(md_path))
        with open(json_path, "r", encoding="utf-8") as handle:
            stored = json.load(handle)
        self.assertEqual(len(stored["runs"]), 8)
        self.assertTrue(all(row.get("run_id") for row in stored["runs"]),
                        "every raw run carries its own run_id")
        with open(md_path, "r", encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn(bench.BANNER, text)
        self.assertIn("usdc-2023-03", text)
        self.assertIn("placebo-calm-2023-03 — SYNTHETIC PLACEBO", text)
        self.assertIn("not_executed", text)
        self.assertIn("brakes/abstains where the engine", text)
        self.assertEqual(bench.contains_superiority_claim(text), [])

        usdc = [case for case in report["cases"] if case["case_id"] == "usdc-2023-03"][0]
        self.assertEqual(usdc["delta"]["tag"], "agents_abstain_where_engine_acts")
        placebo = [case for case in report["cases"] if case["case_id"] == "placebo-calm-2023-03"][0]
        self.assertEqual(placebo["delta"]["tag"], "a2_not_executed")
        self.assertEqual(placebo["aggregates"]["A0"]["verdict_counts"], {bench.NO_ACTION: 2})
        self.assertEqual(placebo["aggregates"]["A2"]["n_not_executed"], 2)

    def test_unknown_case_is_refused(self):
        with self.assertRaises(bench.CasesError):
            bench.run_benchmark(self.payload, ["no-such-case"], 1, self.tmp,
                                lambda c, d, i: a0_payload(), lambda c, d, i: a2_payload())

    def test_bad_runs_count_is_refused(self):
        with self.assertRaises(bench.BenchError):
            bench.run_benchmark(self.payload, [], 0, self.tmp,
                                lambda c, d, i: a0_payload(), lambda c, d, i: a2_payload())


if __name__ == "__main__":
    unittest.main()
