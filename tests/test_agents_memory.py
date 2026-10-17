#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: minimal FTS memory + bounded tool chain (M9, B3).

Memory rule of the journal applied verbatim: **an entry without refs cannot be
used** — ``remember`` refuses it and nothing else is ever stored. Search is
FTS5 with a re-quoted token expression (an FTS operator or a quote in the
query cannot change the syntax) and a deterministic order. The tool chain of
one turn is bounded (``max_tool_calls``, default 3): a call beyond the bound
is refused with ``E_TOOL_CHAIN_LIMIT`` and never executes.

Execution: ``python -m pytest tests/test_agents_memory.py -q``
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.agents import contracts  # noqa: E402
from orvyren.agents.llm import (  # noqa: E402
    LiveBackend,
    ToolTurnRunner,
    load_models_config,
)
from orvyren.agents.memory import (  # noqa: E402
    E_MEMORY_NO_REFS,
    FTSMemory,
    MemoryEntry,
    refs_from_observations,
)
from orvyren.agents.tools import ToolRegistry  # noqa: E402

ENV = {"ORVYREN_DEEPSEEK_API_KEY": "***"}


def envelope(*calls):
    return {"$schema": "orvyren/toolcall/v1",
            "calls": [{"name": name, "args": dict(args)} for name, args in calls]}


def chat_content(content):
    body = {
        "id": "chatcmpl-test", "object": "chat.completion",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5,
                  "prompt_cache_hit_tokens": 0},
    }
    return (200, json.dumps(body, ensure_ascii=False))


class FakeHTTP:
    def __init__(self, script):
        self.script = list(script)

    def __call__(self, url, headers, body_bytes, timeout):
        if not self.script:
            raise AssertionError("E_FAKE_HTTP: no scripted response left")
        return self.script.pop(0)


class RefTool:
    """Returns observations WITH refs (relation ids)."""

    name = "graph_query"

    def run(self, args, *, deadline_s=20.0):
        return contracts.ToolResult(
            ok=True, status="OK",
            observations=({"relation_id": "rel:%s" % args.get("query"),
                           "rows": 1},))


class ReflessTool:
    name = "read_prices"

    def run(self, args, *, deadline_s=20.0):
        return contracts.ToolResult(
            ok=True, status="OK", observations=({"value": 42},))


def registry_with(*tools):
    registry = ToolRegistry()
    for tool in tools:
        registry.register(tool.name, tool)
    return registry


class TestFTSMemory(unittest.TestCase):
    def setUp(self):
        self.memory = FTSMemory()

    def test_remember_requires_refs(self):
        with self.assertRaises(ValueError) as ctx:
            self.memory.remember("m1", "texte sans refs", [])
        self.assertIn(E_MEMORY_NO_REFS, str(ctx.exception))
        self.assertEqual(self.memory.count(), 0)

    def test_remember_and_recall(self):
        self.memory.remember("m1", "exposition WETH du holder", ["rel:1"])
        self.memory.remember("m2", "concentration cbBTC", ["rel:2", "rel:3"])
        hits = self.memory.recall("exposition")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].memory_id, "m1")
        self.assertEqual(hits[0].refs, ("rel:1",))
        self.assertIsInstance(hits[0], MemoryEntry)

    def test_refs_of_and_entries(self):
        self.memory.remember("m1", "texte", ["rel:1", "rel:2"])
        self.assertEqual(self.memory.refs_of("m1"), ("rel:1", "rel:2"))
        self.assertEqual(self.memory.refs_of("absent"), ())
        self.assertEqual(len(self.memory.entries()), 1)

    def test_fts_syntax_cannot_be_injected(self):
        self.memory.remember("m1", "exposition WETH", ["rel:1"])
        # Quotes/operators in the query are re-quoted, never interpreted.
        for hostile in ('" OR body:*', 'exposition OR 1', "'; DROP TABLE memory; --",
                        "NEAR(a b", "w*"):
            self.memory.recall(hostile)  # ne lève jamais, ne casse rien
        self.assertEqual(self.memory.recall('" OR body:*'), ())
        self.assertEqual(len(self.memory.recall("exposition")), 1)

    def test_deterministic_order_and_empty_query(self):
        self.memory.remember("m2", "graphe alpha", ["rel:2"])
        self.memory.remember("m1", "graphe alpha", ["rel:1"])
        ids = [entry.memory_id for entry in self.memory.recall("graphe")]
        self.assertEqual(ids, ["m1", "m2"])  # rank, memory_id
        self.assertEqual(self.memory.recall(""), ())
        self.assertEqual(self.memory.recall("   "), ())

    def test_refs_from_observations(self):
        refs = refs_from_observations((
            {"relation_id": "rel:1", "ref_id": "event:9"},
            {"relation_id": "rel:1"},
            {"value": 3},
            "pas un mapping",
        ))
        self.assertEqual(refs, ("rel:1", "event:9"))
        self.assertEqual(refs_from_observations(()), ())


class TestRunnerMemoryWiring(unittest.TestCase):
    def setUp(self):
        self.config = load_models_config()
        self.memory = FTSMemory()

    def _runner(self, registry, tool_name="graph_query",
                call_args=None, **kwargs):
        http = FakeHTTP([
            chat_content(json.dumps(
                envelope((tool_name, call_args or {"query": "Q1"})))),
            chat_content(json.dumps({"reponse": "ok"})),
        ])
        backend = LiveBackend(config=self.config, env=ENV, http_post=http)
        runner = ToolTurnRunner(backend, registry, memory=self.memory,
                                agent_id="t-mem", **kwargs)
        return runner.run_turn(
            role="orchestrator", role_version="v-test",
            schema_id="orvyren/test/v1", system_prompt="SYS",
            payload={"q": 1},
            tool_specs=({"type": "function",
                         "function": {"name": tool_name,
                                      "parameters": {"type": "object",
                                                     "properties": {"query": {"type": "string"}},
                                                     "additionalProperties": False}}},))

    def test_result_with_refs_is_remembered(self):
        turn = self._runner(registry_with(RefTool()))
        self.assertEqual(self.memory.count(), 1)
        hits = self.memory.recall("relation")
        self.assertEqual(hits[0].refs, ("rel:Q1",))
        self.assertTrue(turn.final)

    def test_result_without_refs_is_not_remembered(self):
        self._runner(registry_with(ReflessTool()), tool_name="read_prices",
                     call_args={"query": "x"})
        self.assertEqual(self.memory.count(), 0)


class TestBoundedChain(unittest.TestCase):
    def setUp(self):
        self.config = load_models_config()

    def test_chain_is_capped_at_max_tool_calls(self):
        calls = [("graph_query", {"query": "Q%d" % i}) for i in range(4)]
        http = FakeHTTP([
            chat_content(json.dumps({"$schema": "orvyren/toolcall/v1",
                                     "calls": [{"name": n, "args": a}
                                               for n, a in calls]})),
            chat_content(json.dumps({"reponse": "ok"})),
        ])
        backend = LiveBackend(config=self.config, env=ENV, http_post=http)
        runner = ToolTurnRunner(backend, registry_with(RefTool()),
                                max_tool_calls=2, agent_id="t-chain")
        turn = runner.run_turn(
            role="orchestrator", role_version="v-test",
            schema_id="orvyren/test/v1", system_prompt="SYS", payload={},
            tool_specs=({"type": "function",
                         "function": {"name": "graph_query",
                                      "parameters": {"type": "object",
                                                     "properties": {"query": {"type": "string"}},
                                                     "additionalProperties": False}}},))
        self.assertEqual(len(turn.results), 4)
        executed = [r for r in turn.results if r["result"]["status"] == "OK"]
        refused = [r for r in turn.results if r["result"]["status"] == "FAILED"]
        self.assertEqual(len(executed), 2)   # chaîne bornée
        self.assertEqual(len(refused), 2)
        for result in refused:
            self.assertEqual(result["result"]["error"], "E_TOOL_CHAIN_LIMIT:2")


if __name__ == "__main__":
    unittest.main()
