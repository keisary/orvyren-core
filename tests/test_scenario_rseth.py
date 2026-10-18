#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — integration tests for the rsETH 2026-04 E2E scenario script.

``scripts/run_scenario_rseth.py`` chains the existing CLIs (agents LIVE ->
decision -> policy -> dry-run execution under one run_id) and collects the
scenario artifacts under ``evidence/scenario_rseth/``. These tests run the
script **offline on doubles** (the CLI subprocesses are mocked at the single
`_run_command` seam — no LLM call, no network anywhere) and check:

* the fixture loads and keeps the frozen agent-case schema;
* the chained commands are the existing CLIs (agents `--replay live
  --record-live`, decision `--no-rdof` declared substitution, executor
  `--dry-run` with an explicit `--run-id` chained to the agents run id) and
  **never** `--execute`;
* the full pipeline runs on doubles and collects run.json, outcome, packet,
  critique, decision, policy verdicts, tick journal, scenario_run.json and
  scenario_report.md;
* the report contains the required sections (risk -> hypotheses -> evidence ->
  decision -> policy verdict -> execution + explicit gaps);
* a missing live key stops the run honestly (no LLM step, no fabricated run);
* a failing step never fabricates artifacts.

Run: python -m unittest tests.test_scenario_rseth
"""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if os.path.join(ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "src"))

FIXTURE_PATH = os.path.join(ROOT, "fixtures", "agents", "rseth-2026-04",
                            "run_inputs.json")
SCRIPT_PATH = os.path.join(ROOT, "scripts", "run_scenario_rseth.py")

CASE_ID = "rseth-2026-04"
FAKE_RUN_STAMP = "20260101T000000Z"
FAKE_AGENT_RUN_ID = "%s_live_%s" % (CASE_ID, FAKE_RUN_STAMP)


def load_module():
    spec = importlib.util.spec_from_file_location("run_scenario_rseth",
                                                  SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scenario = load_module()


def flag_value(argv, name):
    argv = list(argv)
    if name not in argv:
        return None
    return argv[argv.index(name) + 1]


class FakeRunner(object):
    """Offline double of the four CLIs (writes the artifacts they would)."""

    def __init__(self, keys_rc=0, agents_rc=0, refuse_case_probe=False):
        self.keys_rc = keys_rc
        self.agents_rc = agents_rc
        self.refuse_case_probe = refuse_case_probe
        self.calls = []

    def __call__(self, argv, env, cwd, timeout_s):
        argv = list(argv)
        self.calls.append(argv)
        name = os.path.basename(str(argv[1]))
        if name == "inspect_env_masked.py":
            return {"rc": self.keys_rc, "stdout": "live-mode keys: OK\n",
                    "stderr": ""}
        if name == "run_agents.py":
            if self.agents_rc != 0:
                return {"rc": self.agents_rc, "stdout": "",
                        "stderr": "E_WORKER_ORCHESTRATOR: code 1"}
            session = flag_value(argv, "--session")
            run_dir = os.path.join(session, "%s_live_%s" % (CASE_ID,
                                                            FAKE_RUN_STAMP))
            os.makedirs(os.path.join(run_dir, "exchanges"), exist_ok=True)
            self._write_json(os.path.join(run_dir, "run.json"), {
                "schema": "orvyren/agent-run/v1",
                "run_id": FAKE_AGENT_RUN_ID, "case_id": CASE_ID,
                "mode": "live", "tool_mode": "live",
                "budget": {"llm_calls": 30, "tool_calls": 12,
                           "wall_seconds": 600, "cost_usd": 0.10}})
            self._write_json(os.path.join(run_dir, "outcome_orchestrator.json"),
                             {"stop_condition": "ARRET-2", "inconclusive": True,
                              "budget_used": {"llm_calls": 6, "cost_usd": 0.02},
                              "non_recherche": ["on-chain exit venue"]})
            self._write_json(os.path.join(run_dir, "run_outcome.json"), {
                "schema": "orvyren/agent-run-outcome/v1", "case_id": CASE_ID,
                "mode": "live", "run_dir": run_dir,
                "outcome": {"stop_condition": "ARRET-2", "inconclusive": True},
                "critique": {"verdict_lecture": "FRAGILE", "findings": []},
                "escalation": "REQUIRE_APPROVAL",
                "journals": {"orchestrator": {"lines": 4},
                             "critic": {"lines": 2}}})
            self._write_json(
                os.path.join(run_dir, "exchanges", "001_evidence_packet.json"),
                {"packet_id": "packet-test", "snapshot_ref":
                 "graph_snapshot:rseth-2026-04@2026-04-18T19:03:59Z",
                 "claims": [], "refs": []})
            self._write_json(
                os.path.join(run_dir, "exchanges", "002_critique_report.json"),
                {"verdict_lecture": "FRAGILE", "findings": [], "$status": ""})
            for role in ("orchestrator", "critic"):
                self._write_text(
                    os.path.join(run_dir, "journal_%s.jsonl" % role),
                    json.dumps({"journal_id": "j-%s-1" % role}) + "\n")
            return {"rc": 0, "stdout": "run summary\n", "stderr": ""}
        if name == "run_decision.py":
            out_dir = flag_value(argv, "--out-dir")
            os.makedirs(out_dir, exist_ok=True)
            case = flag_value(argv, "--case")
            self._write_json(os.path.join(out_dir, "decision_%s.json" % case), {
                "case": case,
                "hypothesis_verdicts": {
                    "H1": {"label": "local liquidity perturbation",
                           "verdict": "INCONCLUSIVE"},
                    "H2": {"label": "broad stress on asset or issuer",
                           "verdict": "INCONCLUSIVE"},
                    "H3": {"label": "data or market artifact",
                           "verdict": "INCONCLUSIVE"}},
                "decision": {"verdict": "INCONCLUSIVE", "action": None,
                             "missing_inputs": ["no observation in window"]},
                "inputs_summary": {"corpus": {"path": "fixtures/agents/"
                                                     "rseth-2026-04/"
                                                     "corpus_rseth.csv",
                                              "observations_in_window": 0}}})
            self._write_json(os.path.join(out_dir, "baseline_report.json"),
                             {"signals_main": [], "signals_control": [],
                              "false_signals_control": 0})
            return {"rc": 0, "stdout": "decision run\n", "stderr": ""}
        if name == "run_executor.py":
            run_id = flag_value(argv, "--run-id")
            parent = flag_value(argv, "--parent-run-id")
            journal = flag_value(argv, "--journal")
            ledger = flag_value(argv, "--ledger")
            case = flag_value(argv, "--case")
            if self.refuse_case_probe and case == CASE_ID:
                return {"rc": 5, "stdout": "decision unavailable: "
                        "E_WHAT_WOULD_CHANGE_REQUIRED: INCONCLUSIVE must "
                        "enumerate what would change the verdict (B3 §c.3)",
                        "stderr": ""}
            os.makedirs(os.path.dirname(journal), exist_ok=True)
            chain_dir = os.path.join(os.path.dirname(journal), "chain", run_id)
            os.makedirs(chain_dir, exist_ok=True)
            self._write_text(os.path.join(chain_dir, "events.jsonl"),
                             json.dumps({"run_id": run_id,
                                         "parent_run_id": parent,
                                         "stage": "decision"}) + "\n")
            self._write_json(os.path.join(chain_dir, "manifest.json"),
                             {"run_id": run_id, "events_head": "0" * 64})
            self._write_text(journal, json.dumps({
                "case": CASE_ID, "run_id": run_id, "tick": 1,
                "ts_utc": "2026-01-01T00:00:00Z", "mode": "dry-run",
                "dry_run": True, "verdict": "DENY",
                "policy_verdict": "DENY", "outcome": "DRY-RUN",
                "executed": False, "reasons": ["AGENT_NOT_MEMBER"],
                "rules_evaluated": ["P1", "P7", "P11"],
                "skipped_rules": [], "policy_version": "v1",
                "policy_hash": "0" * 16,
                "chain": {"run_id": run_id, "parent_run_id": parent,
                          "root_dir": chain_dir, "verify_ok": True,
                          "verify_error": "", "events_head": "0" * 64}})
                             + "\n")
            self._write_json(ledger, {"schema": "orvyren/period-ledger/v1",
                                      "entries": []})
            return {"rc": 0,
                    "stdout": json.dumps({"mode": "dry-run", "case": CASE_ID,
                                          "ticks_run": 1}),
                    "stderr": ""}
        return {"rc": 99, "stdout": "", "stderr": "unknown CLI %s" % name}

    @staticmethod
    def _write_json(path, payload):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=1)
            handle.write("\n")

    @staticmethod
    def _write_text(path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)


class FixtureLoadingTest(unittest.TestCase):
    def test_fixture_loads_and_follows_the_case_schema(self):
        with open(FIXTURE_PATH, "r", encoding="utf-8") as handle:
            fixture = json.load(handle)
        self.assertEqual(fixture["schema"], "orvyren/agent-case/v1")
        self.assertEqual(fixture["case_id"], CASE_ID)
        self.assertEqual(sorted(fixture["tool_fixtures"]),
                         ["chain", "documents", "prices", "signals",
                          "snapshot", "supply"])


class PipelineShapeTest(unittest.TestCase):
    def test_commands_chain_the_existing_clis(self):
        steps = scenario.build_steps(case_id=CASE_ID, out_dir="out",
                                    run_id="run-1", ticks=2,
                                    parent_run_id="parent-1")
        by_name = {step["name"]: step["argv"] for step in steps}
        self.assertEqual(sorted(by_name),
                         ["agents", "decision", "execution",
                          "execution_case_probe", "keys"])
        agents = by_name["agents"]
        self.assertEqual(os.path.basename(agents[1]), "run_agents.py")
        self.assertIn("--replay", agents)
        self.assertEqual(flag_value(agents, "--replay"), "live")
        self.assertIn("--record-live", agents)
        decision = by_name["decision"]
        self.assertEqual(os.path.basename(decision[1]), "run_decision.py")
        self.assertIn("--no-rdof", decision)
        probe = by_name["execution_case_probe"]
        self.assertEqual(os.path.basename(probe[1]), "run_executor.py")
        self.assertEqual(flag_value(probe, "--case"), CASE_ID)
        self.assertEqual(flag_value(probe, "--run-id"), "run-1-case-probe")
        execution = by_name["execution"]
        self.assertEqual(os.path.basename(execution[1]), "run_executor.py")
        self.assertIn("--dry-run", execution)
        self.assertNotIn("--execute", execution)
        self.assertEqual(flag_value(execution, "--case"),
                         scenario.EXECUTION_CASE_ID)
        self.assertEqual(flag_value(execution, "--run-id"), "run-1")
        self.assertEqual(flag_value(execution, "--parent-run-id"), "parent-1")
        self.assertEqual(flag_value(execution, "--ticks"), "2")

    def test_executor_leg_is_never_an_execute_leg(self):
        steps = scenario.build_steps(case_id=CASE_ID, out_dir="out",
                                    run_id="run-1", ticks=1,
                                    parent_run_id="parent-1")
        for step in steps:
            self.assertNotIn("--execute", step["argv"],
                             "the scenario is dry-run only")

    def test_corpus_materialization_derives_rows_from_the_episode(self):
        tmp = tempfile.mkdtemp(prefix="orvyren-scenario-")
        try:
            out_path = os.path.join(tmp, "corpus_rseth.csv")
            count = scenario.materialize_corpus(out_path=out_path)
            self.assertGreater(count, 50)
            with open(out_path, "r", encoding="utf-8", newline="") as handle:
                header = handle.readline().strip()
            self.assertEqual(header,
                             "timestamp_utc,venue,metric,value,extra,retrieved_at")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class OfflineDryRunTest(unittest.TestCase):
    """The script is executable offline on doubles (mocked CLIs)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren-scenario-")
        self.runner = FakeRunner()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_pipeline(self, runner=None, extra=()):
        original = scenario._run_command
        scenario._run_command = runner or self.runner
        try:
            return scenario.run_pipeline(
                ["--out-dir", self.tmp, "--run-id", "scenario-test-rseth-1",
                 "--ticks", "1"] + list(extra))
        finally:
            scenario._run_command = original

    def test_dry_run_on_doubles_collects_every_artifact(self):
        rc = self.run_pipeline()
        self.assertEqual(rc, scenario.EXIT_OK)
        for name in ("run.json", "run_outcome.json", "outcome_orchestrator.json",
                     "evidence_packet.json", "critique_report.json",
                     "journal_orchestrator.jsonl", "journal_critic.jsonl",
                     "policy_verdicts.json", "scenario_run.json",
                     "scenario_report.md"):
            self.assertTrue(os.path.isfile(os.path.join(self.tmp, name)), name)
        self.assertTrue(os.path.isfile(
            os.path.join(self.tmp, "decision", "decision_%s.json" % CASE_ID)))
        self.assertTrue(os.path.isfile(
            os.path.join(self.tmp, "decision", "abstention_%s.json" % CASE_ID)))
        self.assertTrue(os.path.isfile(
            os.path.join(self.tmp, "execution", "journal.jsonl")))
        self.assertTrue(os.path.isfile(
            os.path.join(self.tmp, "execution", "case_attempt", "journal.jsonl")))
        self.assertTrue(os.path.isfile(
            os.path.join(self.tmp, "execution", "chain",
                         "scenario-test-rseth-1", "events.jsonl")))
        self.assertTrue(os.path.isfile(
            os.path.join(self.tmp, "execution", "case_attempt", "chain",
                         "scenario-test-rseth-1-case-probe", "events.jsonl")))

    def test_run_ids_are_chained(self):
        self.assertEqual(self.run_pipeline(), scenario.EXIT_OK)
        with open(os.path.join(self.tmp, "scenario_run.json"),
                  encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["status"], "OK")
        self.assertEqual(manifest["run_id"], "scenario-test-rseth-1")
        self.assertEqual(manifest["agents_run_id"], FAKE_AGENT_RUN_ID)
        self.assertEqual(manifest["executor_run_id"], "scenario-test-rseth-1")
        self.assertEqual(manifest["executor_parent_run_id"], FAKE_AGENT_RUN_ID)
        execution = [step for step in manifest["steps"]
                     if step["name"] == "execution"][0]
        self.assertEqual(flag_value(execution["argv"], "--parent-run-id"),
                         FAKE_AGENT_RUN_ID)
        self.assertEqual(flag_value(execution["argv"], "--run-id"),
                         "scenario-test-rseth-1")

    def test_policy_verdicts_and_tick_journal_are_collected(self):
        self.assertEqual(self.run_pipeline(), scenario.EXIT_OK)
        with open(os.path.join(self.tmp, "policy_verdicts.json"),
                  encoding="utf-8") as handle:
            verdicts = json.load(handle)
        self.assertEqual(len(verdicts["ticks"]), 1)
        tick = verdicts["ticks"][0]
        self.assertEqual(tick["verdict"], "DENY")
        self.assertEqual(tick["policy_verdict"], "DENY")
        self.assertTrue(tick["chain"]["verify_ok"])
        self.assertEqual(tick["chain"]["run_id"], "scenario-test-rseth-1")
        with open(os.path.join(self.tmp, "execution", "journal.jsonl"),
                  encoding="utf-8") as handle:
            lines = [json.loads(line) for line in handle if line.strip()]
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0]["dry_run"])

    def test_report_contains_the_required_sections(self):
        self.assertEqual(self.run_pipeline(), scenario.EXIT_OK)
        with open(os.path.join(self.tmp, "scenario_report.md"),
                  encoding="utf-8") as handle:
            report = handle.read()
        for section in scenario.REPORT_SECTIONS:
            self.assertIn(section, report)
        self.assertIn("Observed risk", report)
        self.assertIn("HYP-004", report)
        self.assertIn("counter-intuitive", report)
        self.assertIn("Declared substitutions", report)
        self.assertIn("L-1", report)
        self.assertIn("what_would_change", report)
        self.assertIn("never a forced decision", report)
        # raw step outputs are part of the report (stdout AND stderr)
        self.assertIn("### step `agents` (rc 0)", report)
        self.assertIn("run summary", report)

    def test_decision_is_an_abstention_with_mandatory_what_would_change(self):
        self.assertEqual(self.run_pipeline(), scenario.EXIT_OK)
        with open(os.path.join(self.tmp, "decision",
                               "abstention_%s.json" % CASE_ID),
                  encoding="utf-8") as handle:
            record = json.load(handle)
        self.assertEqual(record["schema"], "orvyren/scenario-decision/v1")
        self.assertEqual(record["epistemic_verdict"], "INCONCLUSIVE")
        self.assertIsNone(record["action"])
        payload = record["abstention"]
        self.assertEqual(payload["epistemic_verdict"], "INCONCLUSIVE")
        self.assertTrue(payload["what_would_change_the_verdict"],
                        "B3 §c.3: an INCONCLUSIVE outcome must enumerate "
                        "what_would_change")
        self.assertIn("A1", payload["conditions_declenchees"])
        self.assertEqual(payload["action"], None)
        self.assertEqual(record["escalade"]["sortie"], "ESCALATE")
        # the counter-intuitive competitor is refuted by the sourced figure
        self.assertEqual(record["verdicts"]["HYP-004"]["verdict"], "REFUTED")
        self.assertIn("episode_rseth_2026-04.json",
                      record["verdicts"]["HYP-004"]["basis"])
        for entry in payload["what_would_change_the_verdict"]:
            self.assertTrue(entry["fait"])
            self.assertTrue(entry["predicat"])
            self.assertTrue(entry["cible"])
            self.assertTrue(entry["cout_estime"])
        manifest_steps = scenario._read_json(
            os.path.join(self.tmp, "scenario_run.json"))["steps"]
        self.assertIn("decision_abstention",
                      [step["name"] for step in manifest_steps])

    def test_documented_guard_refuses_an_abstention_without_what_would_change(self):
        from orvyren.decision import abstention as abstention_mod
        conditions = {"conditions": ["A1"], "labels": ["A1"], "evidence": {}}
        with self.assertRaises(ValueError) as caught:
            abstention_mod.build_inconclusive(
                {"HYP-001": {"verdict": "INCONCLUSIVE"}}, conditions, [],
                decision_delta={}, budget={})
        self.assertIn("E_WHAT_WOULD_CHANGE_REQUIRED", str(caught.exception))

    def test_measured_case_refusal_is_kept_and_the_pipeline_continues(self):
        runner = FakeRunner(refuse_case_probe=True)
        rc = self.run_pipeline(runner=runner)
        self.assertEqual(rc, scenario.EXIT_OK)
        with open(os.path.join(self.tmp, "scenario_run.json"),
                  encoding="utf-8") as handle:
            manifest = json.load(handle)
        probe = [step for step in manifest["steps"]
                 if step["name"] == "execution_case_probe"][0]
        self.assertEqual(probe["verdict"],
                         "REFUSED_E_WHAT_WOULD_CHANGE_REQUIRED")
        self.assertIn("E_WHAT_WOULD_CHANGE_REQUIRED", probe["stdout_tail"])
        with open(os.path.join(self.tmp, "scenario_report.md"),
                  encoding="utf-8") as handle:
            report = handle.read()
        self.assertIn("E_WHAT_WOULD_CHANGE_REQUIRED", report)
        self.assertIn(scenario.EXECUTION_CASE_ID, report)

    def test_probe_without_the_measured_refusal_signature_stops(self):
        base = FakeRunner()

        def runner(argv, env, cwd, timeout_s):
            if (os.path.basename(str(argv[1])) == "run_executor.py"
                    and flag_value(argv, "--case") == CASE_ID):
                return {"rc": 5, "stdout": "some other failure", "stderr": ""}
            return base(argv, env, cwd, timeout_s)

        rc = self.run_pipeline(runner=runner)
        self.assertEqual(rc, scenario.EXIT_STEP_FAILED)
        with open(os.path.join(self.tmp, "scenario_run.json"),
                  encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["status"], "FAILED")
        self.assertEqual(manifest["failed_step"], "execution_case_probe")

    def test_collect_only_rerenders_and_filters_stale_journal_ticks(self):
        self.assertEqual(self.run_pipeline(), scenario.EXIT_OK)
        journal = os.path.join(self.tmp, "execution", "journal.jsonl")
        with open(journal, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"run_id": "scenario-stale-run", "tick": 1,
                                     "verdict": "DENY"}) + "\n")
        original = scenario._run_command

        def forbidden(argv, env, cwd, timeout_s):
            raise AssertionError("collect-only must not execute a CLI")

        scenario._run_command = forbidden
        try:
            rc = scenario.run_pipeline(["--out-dir", self.tmp, "--collect-only"])
        finally:
            scenario._run_command = original
        self.assertEqual(rc, scenario.EXIT_OK)
        with open(os.path.join(self.tmp, "scenario_run.json"),
                  encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertTrue(manifest.get("recollected_only"))
        self.assertEqual(manifest["run_id"], "scenario-test-rseth-1")
        self.assertEqual(len(manifest["steps"]), 6)
        with open(os.path.join(self.tmp, "policy_verdicts.json"),
                  encoding="utf-8") as handle:
            verdicts = json.load(handle)
        self.assertEqual(verdicts["journal_records_total"], 2)
        self.assertEqual(len(verdicts["ticks"]), 1,
                         "ticks of other runs never enter this run's verdicts")
        self.assertEqual(verdicts["ticks"][0]["run_id"], "scenario-test-rseth-1")

    def test_missing_live_keys_stop_honestly(self):
        runner = FakeRunner(keys_rc=1)
        rc = self.run_pipeline(runner=runner)
        self.assertEqual(rc, scenario.EXIT_KEYS_MISSING)
        names = [os.path.basename(argv[1]) for argv in runner.calls]
        self.assertEqual(names, ["inspect_env_masked.py"],
                         "no LLM step may run without a live key")
        with open(os.path.join(self.tmp, "scenario_run.json"),
                  encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["status"], "ABORTED_KEYS_MISSING")
        self.assertFalse(os.path.isfile(
            os.path.join(self.tmp, "scenario_report.md")))

    def test_failed_step_never_fabricates_artifacts(self):
        runner = FakeRunner(agents_rc=3)
        rc = self.run_pipeline(runner=runner)
        self.assertEqual(rc, scenario.EXIT_STEP_FAILED)
        with open(os.path.join(self.tmp, "scenario_run.json"),
                  encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["status"], "FAILED")
        self.assertEqual(manifest["failed_step"], "agents")
        self.assertFalse(os.path.isfile(
            os.path.join(self.tmp, "scenario_report.md")))
        self.assertFalse(os.path.isfile(
            os.path.join(self.tmp, "policy_verdicts.json")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
