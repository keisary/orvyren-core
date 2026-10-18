#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: end-to-end offline slice (M12 prep, B6).

One tooled turn over a **real** temporary graph database, through the whole
B1–B4 stack: ``ToolTurnRunner`` (native tool calling) → ``GraphQueryTool``
(real SQL through ``graph/api.py``) → ``AgentJournal`` (hash chain) →
``FTSMemory`` (entries with refs) → 3-panel payload. Then the turn is
**replayed** through ``RecordedBackend`` and must be identical byte for byte
(``ToolTurn.to_dict()`` equality) — the offline demo criterion.

Everything is offline: the graph is a temp SQLite, the LLM transport is a
scripted fake. No network, no key.

Execution: ``python -m pytest tests/test_agents_e2e.py -q``
"""

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from orvyren.agents import contracts  # noqa: E402
from orvyren.agents import llm as llm_mod  # noqa: E402
from orvyren.agents.graph_tools import build_graph_registry, graph_tool_specs  # noqa: E402
from orvyren.agents.journal import AgentJournal  # noqa: E402
from orvyren.agents.llm import (  # noqa: E402
    LiveBackend,
    RecordedBackend,
    ToolTurnRunner,
    load_models_config,
)
from orvyren.agents.memory import FTSMemory  # noqa: E402
from orvyren.ui import panels  # noqa: E402

ENV = {"ORVYREN_DEEPSEEK_API_KEY": "***"}

# Minimal graph schema + rows (the M7 fixture, abbreviated).
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

HOLDER = "addr:eip155:8453:0xaaa"
ASSET = "asset:eip155:8453:0xxx"


def build_db(path):
    con = sqlite3.connect(path)
    for statement in SCHEMA:
        con.execute(statement)
    con.execute(
        "INSERT INTO relations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("rel:e2e:1", 1, "HOLDS", HOLDER, ASSET,
         json.dumps({"amount": 10, "unit": "USDC"}), "ACTIVE", "VALIDATED",
         "2026-01-01T00:00:00+00:00", None, 100, None, "FACT", "SF-E2E"))
    con.execute("INSERT INTO relation_provenance VALUES (?,?,?,?,?,?,?)",
                ("rel:e2e:1", 1, "event:eip155:8453:0xeee:1", "EVENT",
                 "SF-E2E", "ONCHAIN_READ", "run-e2e"))
    con.execute("INSERT INTO nodes VALUES (?)", ("node:1",))
    con.execute("INSERT INTO events VALUES (?)", ("event:1",))
    con.commit()
    con.close()


def chat_tool_calls(calls, tokens_in=100, tokens_out=20, cached_in=10):
    body = {
        "id": "chatcmpl-e2e", "object": "chat.completion",
        "choices": [{"index": 0, "finish_reason": "tool_calls",
                     "message": {"role": "assistant", "content": None,
                                 "tool_calls": [
                                     {"id": call_id, "type": "function",
                                      "function": {"name": name,
                                                   "arguments": arguments}}
                                     for call_id, name, arguments in calls]}}],
        "usage": {"prompt_tokens": tokens_in, "completion_tokens": tokens_out,
                  "prompt_cache_hit_tokens": cached_in},
    }
    return (200, json.dumps(body, ensure_ascii=False))


def chat_content(content):
    body = {
        "id": "chatcmpl-e2e", "object": "chat.completion",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20,
                  "prompt_cache_hit_tokens": 10},
    }
    return (200, json.dumps(body, ensure_ascii=False))


class FakeHTTP:
    def __init__(self, script):
        self.script = list(script)

    def __call__(self, url, headers=None, body_bytes=None, timeout=None):
        # Defaults so the fake can also be wired over urllib.request.urlopen:
        # with an empty script ANY call (whatever its shape) raises.
        if not self.script:
            raise AssertionError("E_FAKE_HTTP: no scripted response left")
        return self.script.pop(0)


FINAL = json.dumps({"$schema": "orvyren/decision-draft/v1",
                    "verdict": "exposition USDC verifiee",
                    "refs": ["rel:e2e:1"]})


class TestEndToEndOffline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren-e2e-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.db = os.path.join(self.tmp, "graph_e2e.sqlite")
        build_db(self.db)
        self.config = load_models_config()
        self.store = None

    def test_full_slice_record_then_replay(self):
        from orvyren.agents.store import ResponseStore
        self.store = ResponseStore(os.path.join(self.tmp, "store"))

        http = FakeHTTP([
            chat_tool_calls([
                ("call-1", "graph_query",
                 json.dumps({"query": "Q1", "holder": HOLDER})),
                ("call-2", "graph_query",
                 json.dumps({"query": "Q6", "relation_id": "rel:e2e:1"})),
            ]),
            chat_content(FINAL),
        ])
        backend = LiveBackend(config=self.config, store=self.store,
                              env=ENV, http_post=http)
        registry = build_graph_registry(db=self.db)
        journal = AgentJournal()
        memory = FTSMemory()
        runner = ToolTurnRunner(backend, registry, journal,
                                agent_id="e2e", memory=memory,
                                max_tool_calls=3)
        turn = runner.run_turn(
            role="orchestrator", role_version="e2e/v1",
            schema_id="orvyren/decision-draft/v1",
            system_prompt="E2E.", payload={"question": "exposition"},
            tool_specs=graph_tool_specs())

        # 1 — native turn, real SQL executed, final draft produced.
        self.assertEqual(turn.mode, "native")
        self.assertEqual(turn.errors, ())
        self.assertEqual(turn.final["verdict"], "exposition USDC verifiee")
        observation = turn.results[0]["result"]["observations"][0]
        self.assertEqual(observation["rows"][0]["amount"], 10)

        # 2 — trace: journal chain intact with TOOL_CALL + TOOL_RESULT.
        self.assertTrue(journal.verify_chain()[0])
        kinds = [entry.kind for entry in journal.entries()]
        self.assertIn("TOOL_CALL", kinds)
        self.assertIn("TOOL_RESULT", kinds)

        # 3 — memory: Q1's rows carry no evidence ref → NOT remembered (rule);
        # Q6's rows do → remembered with both refs.
        self.assertEqual(memory.count(), 1)
        self.assertEqual(memory.refs_of("mem-e2e-call-2"),
                         ("rel:e2e:1", "event:eip155:8453:0xeee:1"))
        self.assertEqual(memory.refs_of("mem-e2e-call-1"), ())

        # 4 — replay: bit-identical turn through RecordedBackend. The fake
        # transport is now WIRED over the network doors (it used to be built
        # and never used): with an empty script any call raises E_FAKE_HTTP,
        # so a green replay proves the turn comes from the recorded store only.
        replay_http = FakeHTTP([])  # aucun réseau pendant le rejeu
        with mock.patch.object(llm_mod, "_urllib_post", replay_http), \
                mock.patch("urllib.request.urlopen", replay_http):
            replay_backend = RecordedBackend(self.store, config=self.config)
            replay_registry = build_graph_registry(db=self.db)
            replay_turn = ToolTurnRunner(replay_backend, replay_registry,
                                         agent_id="e2e").run_turn(
                role="orchestrator", role_version="e2e/v1",
                schema_id="orvyren/decision-draft/v1",
                system_prompt="E2E.", payload={"question": "exposition"},
                tool_specs=graph_tool_specs())
        self.assertEqual(replay_turn.to_dict(), turn.to_dict())
        self.assertEqual(replay_http.script, [])  # rien consommé, tout rejoué

        # 5 — UI: the same data renders in the 3 panels (LIVE path).
        saved = os.environ.get("ORVYREN_UI_HOLDER")
        os.environ["ORVYREN_UI_HOLDER"] = HOLDER
        try:
            payload = panels.panels_payload(
                FakeCtx(self.tmp), live=True, api=_ApiWrapper(self.db))
        finally:
            if saved is None:
                os.environ.pop("ORVYREN_UI_HOLDER", None)
            else:
                os.environ["ORVYREN_UI_HOLDER"] = saved
        self.assertEqual(payload["mode"], "LIVE")
        self.assertEqual(payload["panels"]["graphe"]["Q1"]["rows"][0]["amount"], 10)
        html_text = panels.build_html(payload)
        self.assertIn("Situation", html_text)
        self.assertIn("Q1", html_text)
        self.assertNotIn("RENDER ERROR", html_text)


class FakeCtx:
    def __init__(self, evidence_dir):
        self.evidence_dir = evidence_dir

    def evidence_path(self, *parts):
        return os.path.join(self.evidence_dir, *parts)


class _ApiWrapper:
    """Thin wrapper so panels can call the read-only API with our temp DB."""

    def __init__(self, db):
        self.db = db
        from orvyren.graph import api
        self.api = api

    def snapshot(self, db=None):
        return self.api.snapshot(self.db)

    def pit(self, db=None, **kwargs):
        return self.api.pit(self.db, **kwargs)

    def exposure(self, db, holder, **kwargs):
        return self.api.exposure(self.db, holder, **kwargs)

    def concentration(self, db, asset, **kwargs):
        return self.api.concentration(self.db, asset, **kwargs)

    def provenance(self, db, relation_id):
        return self.api.provenance(self.db, relation_id)


if __name__ == "__main__":
    unittest.main()
