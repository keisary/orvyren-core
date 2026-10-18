#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regression tests — P0-6 (observed-reference provenance) and P1-1 (bounds).

One test per concrete question of the 2026-10-18 review:

P0-6 — a claim may only cite what the run really observed:
- is an invented reference rejected (claim REJECTED, refusal visible)?
- is a claim citing an observed reference accepted and promoted?
- does the evidence packet drop a claim whose refs were never observed?
- is the fixture-derived ledger strict (validation never silently off)?

P1-1 — execution bounds are imposed by the code, not by the model's good will:
- is a negative/zero ``limit`` refused instead of neutralising the restriction?
- is an unbounded ``max_depth`` refused?
- is ``deadline_s`` validated and ENFORCED (a slow result is dropped)?

Execution: ``python -m unittest tests.test_agents_provenance_bounds``
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.agents import contracts, graph_tools, tools  # noqa: E402
from orvyren.agents.journal import AgentJournal  # noqa: E402
from orvyren.agents.worker import build_evidence_packet  # noqa: E402

REF_OK = "observation:bitstamp/usdc-usd/2023-03-11T12:00Z"
REF_SUPPLY = "observation:circle/supply/2023-03-11T12:00Z"
REF_FAKE = "observation:invented/never-returned"
SNAPSHOT_REF = "graph_snapshot:usdc-2023-03@2023-03-11T12:00:00Z"


def _entry_data(**overrides):
    """One schema-valid journal line (proposal kind, no figure)."""
    data = {
        "journal_id": "jw-test-1", "run_id": "run-test", "episode_id": "usdc-2023-03",
        "agent_id": "orchestrator", "role_version": "tool-jw/v1", "step_index": 0,
        "ts_utc": "2023-03-11T12:00:00+00:00", "kind": "REFLECTION",
        "content": "la lecture est confirmee par la source archivee",
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# P0-6 — the ledger itself.
# ---------------------------------------------------------------------------
class ObservedRefsTest(unittest.TestCase):
    def test_unknown_reports_only_the_unobserved_refs(self):
        ledger = contracts.ObservedRefs([REF_OK, SNAPSHOT_REF])
        self.assertEqual(
            ledger.unknown([REF_OK, REF_FAKE, REF_FAKE, ""]), (REF_FAKE,))

    def test_blank_strings_are_never_observations(self):
        ledger = contracts.ObservedRefs(["", "   ", None])
        self.assertEqual(len(ledger), 0)

    def test_membership_strips_whitespace(self):
        ledger = contracts.ObservedRefs(["  %s  " % REF_OK])
        self.assertIn(REF_OK, ledger)

    def test_add_many_registers_tool_results(self):
        ledger = contracts.ObservedRefs()
        ledger.add_many([REF_OK, REF_SUPPLY])
        self.assertEqual(ledger.all(), tuple(sorted((REF_OK, REF_SUPPLY))))


# ---------------------------------------------------------------------------
# P0-6 — the journal refuses visibly.
# ---------------------------------------------------------------------------
class JournalRejectReasonTest(unittest.TestCase):
    def test_reject_reason_marks_the_line_rejected_and_keeps_it_visible(self):
        journal = AgentJournal()
        entry = journal.append_dict(_entry_data(refs=(REF_OK,)),
                                    reject_reason="E_REF_NOT_OBSERVED: %s" % REF_FAKE)
        self.assertEqual(entry.status, "REJECTED")
        self.assertIn("E_REF_NOT_OBSERVED", entry.validation["motif"])
        self.assertEqual(len(journal), 1)  # the refusal is appended, never dropped
        ok, message = journal.verify_chain()
        self.assertTrue(ok, message)

    def test_quarantine_still_wins_over_reject_reason(self):
        journal = AgentJournal()
        entry = journal.append_dict(_entry_data(refs=(REF_OK,), bogus_field=1),
                                    reject_reason="E_REF_NOT_OBSERVED: %s" % REF_FAKE)
        self.assertEqual(entry.status, "QUARANTINED")

    def test_a_rejected_line_can_never_be_promoted(self):
        journal = AgentJournal()
        entry = journal.append_dict(_entry_data(refs=(REF_OK,)),
                                    reject_reason="E_REF_NOT_OBSERVED: %s" % REF_FAKE)
        with self.assertRaises(ValueError) as caught:
            journal.promote(entry)
        self.assertIn("E_JOURNAL_PROMOTION_STATUS", str(caught.exception))


# ---------------------------------------------------------------------------
# P0-6 — journal_write refuses an invented reference.
# ---------------------------------------------------------------------------
class JournalWriteRefValidationTest(unittest.TestCase):
    def setUp(self):
        self.journal = AgentJournal()
        self.observed = contracts.ObservedRefs([REF_OK])
        self.tool = tools.JournalWriteTool(self.journal, observed=self.observed)

    def test_a_claim_citing_an_invented_ref_is_rejected_but_visible(self):
        result = self.tool.run(
            {"content": "claim douteux", "refs": [REF_OK, REF_FAKE]})
        self.assertTrue(result.ok)  # the write succeeded; the LINE is refused
        self.assertEqual(result.observations[0]["status"], "REJECTED")
        entry = self.journal.entries()[0]
        self.assertIn("E_REF_NOT_OBSERVED", entry.validation["motif"])
        self.assertIn(REF_FAKE, entry.validation["motif"])

    def test_a_claim_citing_only_observed_refs_is_accepted(self):
        result = self.tool.run({"content": "claim sourcé", "refs": [REF_OK]})
        self.assertEqual(result.observations[0]["status"], "PROPOSED")

    def test_registry_derives_the_ledger_from_the_archived_fixtures(self):
        fixtures = {
            "prices": {"bitstamp|USDC-USD": [
                {"venue": "bitstamp", "value": 0.8053, "source_ref": REF_OK}]},
            "supply": {}, "chain": {}, "documents": {}, "signals": {},
            "snapshot": {"ref": SNAPSHOT_REF},
        }
        registry = tools.build_v1_registry(fixtures=fixtures,
                                           journal=AgentJournal())
        journal_write = registry.get("journal_write")
        good = journal_write.run({"content": "sourcé", "refs": [REF_OK]})
        self.assertEqual(good.observations[0]["status"], "PROPOSED")
        bad = journal_write.run({"content": "inventé", "refs": [REF_FAKE]})
        self.assertEqual(bad.observations[0]["status"], "REJECTED")

    def test_no_ledger_is_never_a_silent_bypass_in_the_registry(self):
        fixtures = {"prices": {}, "supply": {}, "chain": {}, "documents": {},
                    "signals": {}, "snapshot": {}}
        registry = tools.build_v1_registry(fixtures=fixtures,
                                           journal=AgentJournal())
        journal_write = registry.get("journal_write")
        result = journal_write.run({"content": "claim", "refs": [REF_FAKE]})
        self.assertEqual(result.observations[0]["status"], "REJECTED")


# ---------------------------------------------------------------------------
# P0-6 — the evidence packet drops unobserved citations (defence in depth).
# ---------------------------------------------------------------------------
class EvidencePacketTest(unittest.TestCase):
    def test_packet_excludes_a_claim_citing_an_unobserved_ref(self):
        journal = AgentJournal()
        journal.append_dict(_entry_data(
            journal_id="jw-tr", kind="TOOL_RESULT", refs=(REF_OK,),
            content="read_prices status=OK error=-"))
        journal.append_dict(_entry_data(
            journal_id="jw-good", refs=(REF_OK,), content="claim sourcé"))
        journal.append_dict(_entry_data(
            journal_id="jw-bad", refs=(REF_FAKE,), content="claim inventé"))
        ledger = contracts.ObservedRefs([SNAPSHOT_REF])
        packet = build_evidence_packet(journal, ledger, run_id="run-test",
                                       case_id="usdc-2023-03",
                                       snapshot_ref=SNAPSHOT_REF)
        self.assertEqual([claim["journal_id"] for claim in packet.claims],
                         ["jw-good"])
        self.assertIn("1 claim(s) excluded: ref not observed (P0-6)",
                      packet.summary)

    def test_packet_keeps_every_claim_when_all_refs_were_observed(self):
        journal = AgentJournal()
        journal.append_dict(_entry_data(
            journal_id="jw-tr", kind="TOOL_RESULT", refs=(REF_OK, REF_SUPPLY),
            content="read_supply status=OK error=-"))
        journal.append_dict(_entry_data(
            journal_id="jw-good", refs=(REF_SUPPLY,), content="claim sourcé"))
        ledger = contracts.ObservedRefs([SNAPSHOT_REF])
        packet = build_evidence_packet(journal, ledger, run_id="run-test",
                                       case_id="usdc-2023-03",
                                       snapshot_ref=SNAPSHOT_REF)
        self.assertEqual(len(packet.claims), 1)
        self.assertNotIn("excluded", packet.summary)


# ---------------------------------------------------------------------------
# P1-1 — bounds and deadline are imposed by the code.
# ---------------------------------------------------------------------------
class _FakeApi:
    """Answers every graph query with one constant row (latency included)."""

    def exposure(self, db, holder, **kwargs):
        return {"query": "Q1", "rows": [], "latency_ms": 12.5}

    def pit(self, db, **kwargs):
        return {"query": "Q4", "rows": [], "latency_ms": 3.0}

    def provenance(self, db, relation_id):
        return {"query": "Q6", "rows": []}

    def concentration(self, db, asset, **kwargs):
        return {"query": "Q7", "rows": []}

    def permissions(self, db, subject, **kwargs):
        return {"query": "Q8", "rows": []}

    def snapshot(self, db, **kwargs):
        return {"counts": {"relations": 0}}

    def dependency_paths(self, db, src, dst, **kwargs):
        return {"paths": []}


class GraphToolBoundsTest(unittest.TestCase):
    def setUp(self):
        self.api = _FakeApi()
        self.tool = graph_tools.GraphQueryTool(api=self.api, clock=lambda: 0.0)

    def test_negative_limit_is_refused(self):
        result = self.tool.run({"query": "Q4", "limit": -1})
        self.assertFalse(result.ok)
        self.assertIn("E_TOOL_ARGS_RANGE:limit", result.error)

    def test_explicit_zero_is_a_bounded_value_not_an_unlimited_one(self):
        # ``limit=0`` is ``LIMIT 0`` (empty, bounded) — a legal explicit value;
        # ``limit=-1`` would be ``LIMIT -1`` (UNLIMITED) and is refused above.
        result = self.tool.run({"query": "Q4", "limit": 0}, deadline_s=20.0)
        self.assertTrue(result.ok, result.error)

    def test_limit_above_the_ceiling_is_refused(self):
        result = self.tool.run({"query": "Q4", "limit": graph_tools.MAX_LIMIT + 1})
        self.assertIn("E_TOOL_ARGS_RANGE:limit", result.error)

    def test_negative_max_depth_is_refused(self):
        result = self.tool.run({"query": "Q1", "holder": "0xholder",
                                "max_depth": -3})
        self.assertIn("E_TOOL_ARGS_RANGE:max_depth", result.error)

    def test_unbounded_max_depth_is_refused(self):
        result = self.tool.run({"query": "Q1", "holder": "0xholder",
                                "max_depth": 999})
        self.assertIn("E_TOOL_ARGS_RANGE:max_depth", result.error)

    def test_negative_as_of_block_is_refused(self):
        result = self.tool.run({"query": "Q4", "as_of_block": -5})
        self.assertIn("E_TOOL_ARGS_RANGE:as_of_block", result.error)

    def test_deadline_must_be_finite_positive_and_capped(self):
        for bad in (0, -1.0, float("nan"), float("inf"), 10 ** 9, True, "20"):
            result = self.tool.run({"query": "Q4"}, deadline_s=bad)
            self.assertFalse(result.ok, "deadline accepted: %r" % (bad,))
            self.assertTrue(result.error.startswith("E_TOOL_ARGS_"), result.error)

    def test_the_deadline_is_enforced_not_decorative(self):
        ticks = iter((0.0, 99.0))  # started, then far beyond the budget
        slow = graph_tools.GraphQueryTool(api=self.api, clock=lambda: next(ticks))
        result = slow.run({"query": "Q4"}, deadline_s=20.0)
        self.assertFalse(result.ok)
        self.assertIn("E_TOOL_DEADLINE", result.error)

    def test_latency_is_neutralised_but_the_result_stays_usable(self):
        result = self.tool.run({"query": "Q4"}, deadline_s=20.0)
        self.assertTrue(result.ok, result.error)
        self.assertIsNone(result.observations[0]["latency_ms"])

    def test_graph_path_bounds_max_depth(self):
        tool = graph_tools.GraphPathTool(api=self.api, clock=lambda: 0.0)
        result = tool.run({"src": "a", "dst": "b", "max_depth": -1})
        self.assertIn("E_TOOL_ARGS_RANGE:max_depth", result.error)
        too_deep = tool.run({"src": "a", "dst": "b",
                             "max_depth": graph_tools.MAX_DEPTH + 1})
        self.assertIn("E_TOOL_ARGS_RANGE:max_depth", too_deep.error)
        ok = tool.run({"src": "a", "dst": "b", "max_depth": 4}, deadline_s=20.0)
        self.assertTrue(ok.ok, ok.error)

    def test_graph_snapshot_bounds_as_of_block(self):
        tool = graph_tools.GraphSnapshotTool(api=self.api, clock=lambda: 0.0)
        result = tool.run({"as_of_block": -1})
        self.assertIn("E_TOOL_ARGS_RANGE:as_of_block", result.error)


if __name__ == "__main__":
    unittest.main()
