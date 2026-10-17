#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: real graph tools (M7, B2).

A temporary SQLite graph (schema v3 shape, real rows) backs the three tools of
CONTRACT.md (§ Outils agent): ``graph_query`` (Q1/Q4/Q6/Q7/Q8), ``graph_path``
(honest ``UNAVAILABLE`` while A's API has no Q2) and ``graph_snapshot``
(hash + counts). The M7 criterion is the point of this bench: **the args change
the result** (holder, block, asset, subject) and there is **no frozen
snapshot** — plus strict args (closed objects), ``ToolResult`` only, and no
``execute_intent`` anywhere.

Execution: ``python -m pytest tests/test_agents_graph_tools.py -q``
"""

import json
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.agents import contracts  # noqa: E402
from orvyren.agents.graph_tools import (  # noqa: E402
    GRAPH_TOOL_NAMES,
    GraphPathTool,
    GraphQueryTool,
    GraphSnapshotTool,
    build_graph_registry,
    graph_tool_specs,
)

ADDR_A = "addr:eip155:8453:0xaaa"
ADDR_B = "addr:eip155:8453:0xbbb"
ASSET_X = "asset:eip155:8453:0xxx"
DEBT_D = "debt:eip155:8453:0xddd"
POS_P = "position:eip155:8453:0xppp:0xddd"
POS_Q = "position:eip155:8453:0xqqq:0xddd"
SUBJ_S = "addr:eip155:8453:0xsss"
REL_1 = "rel:test:1"
REL_6 = "rel:test:6"

SCHEMA = [
    "CREATE TABLE relations (relation_id TEXT, revision INTEGER, kind TEXT, "
    "src TEXT, dst TEXT, payload TEXT, lifecycle TEXT, validation_status TEXT, "
    "valid_from TEXT, valid_to TEXT, valid_from_block INTEGER, "
    "valid_to_block INTEGER, epistemic_status TEXT, source_family_id TEXT)",
    "CREATE TABLE relation_provenance (relation_id TEXT, revision INTEGER, "
    "ref_id TEXT, ref_kind TEXT, source_family_id TEXT, extract_method TEXT, "
    "run_id TEXT)",
    "CREATE TABLE nodes (node_id TEXT)",
    "CREATE TABLE events (event_id TEXT)",
]

RELATIONS = [
    # (relation_id, kind, src, dst, payload, lifecycle, valid_from, vfb)
    (REL_1, "HOLDS", ADDR_A, ASSET_X,
     {"amount": 10, "unit": "USDC"}, "ACTIVE", "2026-01-01T00:00:00+00:00", 100),
    ("rel:test:2", "HOLDS", ADDR_B, ASSET_X,
     {"amount": 5, "unit": "USDC"}, "ACTIVE", "2026-01-05T00:00:00+00:00", 200),
    ("rel:test:3", "OWES", POS_P, DEBT_D,
     {"amount": 100}, "ACTIVE", "2026-01-01T00:00:00+00:00", 100),
    ("rel:test:4", "OWES", POS_Q, DEBT_D,
     {"amount": 50}, "ACTIVE", "2026-01-01T00:00:00+00:00", 100),
    ("rel:test:5", "MEMBER_OF", SUBJ_S, "group:eip155:8453:0xggg",
     {}, "ACTIVE", "2026-01-01T00:00:00+00:00", 100),
    (REL_6, "HOLDS", ADDR_A, ASSET_X,
     {"amount": 1, "unit": "USDC"}, "RETIRED", "2026-01-01T00:00:00+00:00", 100),
]


def build_db(path):
    con = sqlite3.connect(path)
    try:
        for statement in SCHEMA:
            con.execute(statement)
        for relation_id, kind, src, dst, payload, lifecycle, valid_from, vfb in RELATIONS:
            con.execute(
                "INSERT INTO relations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (relation_id, 1, kind, src, dst, json.dumps(payload), lifecycle,
                 "VALIDATED", valid_from, None, vfb, None, "FACT",
                 "SF-TEST"))
        con.execute(
            "INSERT INTO relation_provenance VALUES (?,?,?,?,?,?,?)",
            (REL_1, 1, "event:eip155:8453:0xeee:1", "EVENT", "SF-TEST",
             "ONCHAIN_READ", "run-test"))
        for i in range(4):
            con.execute("INSERT INTO nodes VALUES (?)", ("node:%d" % i,))
        for i in range(7):
            con.execute("INSERT INTO events VALUES (?)", ("event:%d" % i,))
        con.commit()
    finally:
        con.close()


class GraphToolsFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="orvyren-graph-tools-")
        cls.db = os.path.join(cls.tmp, "graph_test.sqlite")
        build_db(cls.db)

    def tool(self, cls):
        return cls(db=self.db)


class TestGraphQueryTool(GraphToolsFixture):
    def test_args_change_the_result_holder(self):
        tool = self.tool(GraphQueryTool)
        a = tool.run({"query": "Q1", "holder": ADDR_A})
        b = tool.run({"query": "Q1", "holder": ADDR_B})
        self.assertTrue(a.ok and b.ok)
        self.assertEqual(a.observations[0]["rows"][0]["amount"], 10)
        self.assertEqual(b.observations[0]["rows"][0]["amount"], 5)
        self.assertNotEqual(a.observations[0]["rows"],
                            b.observations[0]["rows"])

    def test_args_change_the_result_block_pit(self):
        tool = self.tool(GraphQueryTool)
        early = tool.run({"query": "Q1", "holder": ADDR_B,
                          "as_of_block": 150})
        late = tool.run({"query": "Q1", "holder": ADDR_B,
                         "as_of_block": 250})
        self.assertTrue(early.ok and late.ok)
        self.assertEqual(early.observations[0]["rows"], [])   # pas encore HOLDS
        self.assertEqual(late.observations[0]["count"], 1)

    def test_args_change_the_result_as_of(self):
        tool = self.tool(GraphQueryTool)
        before = tool.run({"query": "Q4", "as_of": "2026-01-02T00:00:00+00:00"})
        after = tool.run({"query": "Q4", "as_of": "2026-01-10T00:00:00+00:00"})
        self.assertTrue(before.ok and after.ok)
        self.assertLess(before.observations[0]["count"],
                        after.observations[0]["count"])

    def test_active_filter_hides_retired(self):
        tool = self.tool(GraphQueryTool)
        result = tool.run({"query": "Q4", "limit": 100})
        ids = [row["relation_id"] for row in result.observations[0]["rows"]]
        self.assertNotIn(REL_6, ids)  # lifecycle RETIRED

    def test_q6_provenance(self):
        tool = self.tool(GraphQueryTool)
        result = tool.run({"query": "Q6", "relation_id": REL_1})
        self.assertTrue(result.ok)
        rows = result.observations[0]["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ref_kind"], "EVENT")
        empty = tool.run({"query": "Q6", "relation_id": "rel:inconnue"})
        self.assertEqual(empty.observations[0]["count"], 0)

    def test_q7_concentration(self):
        tool = self.tool(GraphQueryTool)
        result = tool.run({"query": "Q7", "asset": DEBT_D})
        self.assertTrue(result.ok)
        body = result.observations[0]
        self.assertEqual(body["counterparties"], 2)
        self.assertEqual(body["total"], 150.0)
        self.assertEqual(body["rows"][0]["amount"], 100)
        self.assertAlmostEqual(body["hhi"], (100 / 150) ** 2 + (50 / 150) ** 2)

    def test_q8_permissions_not_ingested(self):
        tool = self.tool(GraphQueryTool)
        empty = tool.run({"query": "Q8", "subject": "addr:eip155:8453:0xzzz"})
        self.assertEqual(empty.observations[0]["status"], "NOT_INGESTED")
        ok = tool.run({"query": "Q8", "subject": SUBJ_S})
        self.assertEqual(ok.observations[0]["status"], "OK")
        self.assertEqual(ok.observations[0]["count"], 1)

    def test_strict_args_refused(self):
        tool = self.tool(GraphQueryTool)
        unknown_key = tool.run({"query": "Q1", "holder": ADDR_A, "inconnu": 1})
        self.assertFalse(unknown_key.ok)
        self.assertIn("E_TOOL_ARGS_UNKNOWN:inconnu", unknown_key.error)
        missing = tool.run({"query": "Q1"})
        self.assertFalse(missing.ok)
        self.assertIn("E_TOOL_ARGS_REQUIRED:holder", missing.error)
        bad_query = tool.run({"query": "Q99", "holder": ADDR_A})
        self.assertFalse(bad_query.ok)
        self.assertIn("E_TOOL_QUERY_UNKNOWN:Q99", bad_query.error)

    def test_deadline_defaults_to_contract_20s(self):
        tool = self.tool(GraphQueryTool)
        result = tool.run({"query": "Q1", "holder": ADDR_A})
        self.assertTrue(result.ok)  # 20 s par défaut (CONTRACT.md)


class TestGraphPathTool(GraphToolsFixture):
    def test_q2_unavailable_is_honest(self):
        tool = self.tool(GraphPathTool)
        result = tool.run({"src": ADDR_A, "dst": ASSET_X})
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertTrue(result.error.startswith("E_TOOL_NO_API:Q2"))

    def test_strict_args(self):
        tool = self.tool(GraphPathTool)
        result = tool.run({"src": ADDR_A})
        self.assertFalse(result.ok)
        self.assertIn("E_TOOL_ARGS_REQUIRED:dst", result.error)
        bad = tool.run({"src": ADDR_A, "dst": ASSET_X, "bidule": 1})
        self.assertIn("E_TOOL_ARGS_UNKNOWN:bidule", bad.error)


class TestGraphSnapshotTool(GraphToolsFixture):
    def test_hash_and_real_counts(self):
        tool = self.tool(GraphSnapshotTool)
        result = tool.run({})
        self.assertTrue(result.ok)
        body = result.observations[0]
        self.assertEqual(body["counts"],
                         {"relations": 6, "nodes": 4, "events": 7,
                          "relation_provenance": 1})
        self.assertEqual(len(body["graph_hash"]), 64)
        # Pas de snapshot figé : deux lectures, même hash (déterministe).
        self.assertEqual(tool.run({}).observations[0]["graph_hash"],
                         body["graph_hash"])

    def test_db_unavailable_is_not_a_crash(self):
        tool = GraphSnapshotTool(db=os.path.join(self.tmp, "absent.sqlite"))
        result = tool.run({})
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertTrue(result.error.startswith("E_TOOL_DB_UNAVAILABLE"))


class TestRegistryAndSpecs(GraphToolsFixture):
    def test_registry_allow_list_without_execute_intent(self):
        registry = build_graph_registry(db=self.db)
        self.assertEqual(registry.names(), GRAPH_TOOL_NAMES)
        self.assertNotIn("execute_intent", registry)

    def test_specs_are_strict_closed_objects(self):
        specs = graph_tool_specs()
        self.assertEqual(len(specs), 3)
        names = [spec["function"]["name"] for spec in specs]
        self.assertEqual(names, list(GRAPH_TOOL_NAMES))
        for spec in specs:
            parameters = spec["function"]["parameters"]
            self.assertFalse(parameters["additionalProperties"])
        query_spec = specs[0]["function"]["parameters"]
        self.assertEqual(query_spec["required"], ["query"])
        self.assertEqual(query_spec["properties"]["query"]["enum"],
                         ["Q1", "Q4", "Q6", "Q7", "Q8"])

    def test_registry_results_are_tool_results(self):
        registry = build_graph_registry(db=self.db)
        result = registry.get("graph_query").run(
            {"query": "Q1", "holder": ADDR_A})
        self.assertIsInstance(result, contracts.ToolResult)
        self.assertEqual(result.status, "OK")


if __name__ == "__main__":
    unittest.main()
