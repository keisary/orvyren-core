#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: native tool calling + strict-JSON fallback (M8, B1).

Covers the strict tool spec (``additionalProperties=false``, ``execute_intent``
refused), the ``orvyren/toolcall/v1`` envelope validator, native ``tool_calls``
parsing (wire shape and replayed shape), and :class:`ToolTurnRunner`:

- one tooled turn in **native** mode: the request carries ``tools`` (and no
  ``response_format``), the proposed args are validated against the spec,
  the tool executes through the allow-list registry, the final strict JSON
  is returned — and the whole turn is **recorded then replayed bit-identical**
  through :class:`RecordedBackend`;
- the **strict-JSON fallback** (provider answers with the envelope, or with
  garbage then the envelope on a tools-less retry): the turn is marked
  ``json_strict`` with a ``fallback_motif`` and the fallback is **journaled**
  (``TOOL_CALL`` line, hash chain intact) — never a silent downgrade;
- args are closed objects: unknown/missing keys refuse the call and the tool
  never executes; unknown names and ``execute_intent`` are refused.

Execution: ``python -m pytest tests/test_agents_toolcall.py -q``
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.agents import contracts  # noqa: E402
from orvyren.agents.journal import AgentJournal  # noqa: E402
from orvyren.agents.llm import (  # noqa: E402
    LiveBackend,
    RecordedBackend,
    ToolTurnRunner,
    load_models_config,
    parse_tool_calls,
    tool_spec,
)
from orvyren.agents.store import ResponseStore  # noqa: E402
from orvyren.agents.tools import ToolRegistry  # noqa: E402

ENV = {"ORVYREN_DEEPSEEK_API_KEY": "***"}
ROLE = "orchestrator"
ROLE_VERSION = "toolturn-test/v1"
SCHEMA_ID = "orvyren/test/v1"
SYSTEM = "SYSTEME DE TEST."
PAYLOAD = {"question": "etat du graphe"}


def envelope(*calls):
    """One strict ``orvyren/toolcall/v1`` fallback envelope."""
    return {"$schema": "orvyren/toolcall/v1",
            "calls": [{"name": name, "args": dict(args)} for name, args in calls]}


def chat_content(content, tokens_in=100, tokens_out=20, cached_in=10):
    """One OpenAI-compatible 200 body whose message carries ``content``."""
    body = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": tokens_in, "completion_tokens": tokens_out,
                  "prompt_cache_hit_tokens": cached_in},
    }
    return (200, json.dumps(body, ensure_ascii=False))


def chat_tool_calls(calls, tokens_in=100, tokens_out=20, cached_in=10):
    """One 200 body whose message carries native ``tool_calls``."""
    body = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
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


class FakeHTTP:
    """Scripted transport: (status, text) tuples in order; bodies captured."""

    def __init__(self, script):
        self.script = list(script)
        self.requests = []

    def __call__(self, url, headers, body_bytes, timeout):
        self.requests.append(json.loads(body_bytes.decode("utf-8")))
        if not self.script:
            raise AssertionError("E_FAKE_HTTP: no scripted response left")
        return self.script.pop(0)


class SpyTool:
    """A deterministic tool that records every executed call."""

    name = "graph_query"

    def __init__(self):
        self.executed = []

    def run(self, args, *, deadline_s=20.0):
        self.executed.append(dict(args))
        return contracts.ToolResult(
            ok=True, status="OK",
            observations=({"query": args.get("query"), "rows": 2},))


SPEC = tool_spec("graph_query", "interroger le graphe",
                 {"query": {"type": "string"}, "as_of": {"type": "string"}},
                 ["query"])


def build_registry(spy=None):
    registry = ToolRegistry()
    registry.register("graph_query", spy if spy is not None else SpyTool())
    return registry


def run_turn(backend, registry, journal=None, specs=(SPEC,)):
    runner = ToolTurnRunner(backend, registry, journal, agent_id="t1")
    return runner.run_turn(role=ROLE, role_version=ROLE_VERSION,
                           schema_id=SCHEMA_ID, system_prompt=SYSTEM,
                           payload=PAYLOAD, tool_specs=specs)


FINAL = json.dumps({"verdict": "graphe interroge"})


class TestToolSpec(unittest.TestCase):
    def test_strict_closed_parameters(self):
        spec = tool_spec("graph_query", "d", {"query": {"type": "string"}}, ["query"])
        self.assertEqual(spec["type"], "function")
        parameters = spec["function"]["parameters"]
        self.assertEqual(parameters["type"], "object")
        self.assertFalse(parameters["additionalProperties"])
        self.assertEqual(parameters["required"], ["query"])
        self.assertIn("query", parameters["properties"])

    def test_execute_intent_refused(self):
        with self.assertRaises(ValueError):
            tool_spec("execute_intent", "jamais")
        with self.assertRaises(ValueError):
            tool_spec("", "sans nom")


class TestEnvelopeValidator(unittest.TestCase):
    def test_valid_envelope(self):
        ok, errors = contracts.validate_toolcall_output(
            envelope(("graph_query", {"query": "Q1"})))
        self.assertTrue(ok, errors)

    def test_closed_fields(self):
        ok, errors = contracts.validate_toolcall_output(
            {"$schema": "orvyren/toolcall/v1", "calls": [],
             "inconnu": 1})
        self.assertFalse(ok)
        self.assertTrue(any("unknown fields" in e for e in errors))
        ok, errors = contracts.validate_toolcall_output(
            {"$schema": "orvyren/toolcall/v1",
             "calls": [{"name": "graph_query", "args": {}, "extra": 1}]})
        self.assertFalse(ok)

    def test_call_requires_name_and_mapping_args(self):
        ok, errors = contracts.validate_toolcall_output(
            {"$schema": "orvyren/toolcall/v1",
             "calls": [{"name": "", "args": {}}, {"name": "t", "args": 3}]})
        self.assertFalse(ok)
        self.assertEqual(len(errors), 2)

    def test_bad_schema_id(self):
        ok, _ = contracts.validate_toolcall_output(
            {"$schema": "orvyren/autre/v1", "calls": []})
        self.assertFalse(ok)


class TestParseToolCalls(unittest.TestCase):
    def test_wire_shape(self):
        calls = parse_tool_calls([
            {"id": "call_1", "type": "function",
             "function": {"name": "graph_query",
                          "arguments": "{\"query\": \"Q1\"}"}}])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].call_id, "call_1")
        self.assertEqual(calls[0].name, "graph_query")
        self.assertEqual(calls[0].args, {"query": "Q1"})
        self.assertEqual(calls[0].source, "native")

    def test_replayed_shape(self):
        calls = parse_tool_calls([
            {"call_id": "call_9", "name": "graph_query",
             "args": {"query": "Q1"}, "source": "json_strict"}])
        self.assertEqual(calls[0].call_id, "call_9")
        self.assertEqual(calls[0].source, "json_strict")

    def test_bad_arguments_become_empty(self):
        calls = parse_tool_calls([
            {"id": "call_1",
             "function": {"name": "graph_query", "arguments": "pas du json"}}])
        self.assertEqual(calls[0].args, {})

    def test_non_list_is_none(self):
        self.assertIsNone(parse_tool_calls(None))
        self.assertIsNone(parse_tool_calls([]))
        self.assertIsNone(parse_tool_calls("x"))


class TestNativeTurn(unittest.TestCase):
    def setUp(self):
        self.store_dir = tempfile.mkdtemp(prefix="orvyren-toolcall-")
        self.config = load_models_config()
        self.store = ResponseStore(self.store_dir)

    def test_native_turn_recorded_then_replayed(self):
        http = FakeHTTP([
            chat_tool_calls([("call_1", "graph_query",
                              json.dumps({"query": "Q1"}))]),
            chat_content(FINAL),
        ])
        live = LiveBackend(config=self.config, store=self.store,
                           env=ENV, http_post=http)
        spy = SpyTool()
        journal = AgentJournal()
        turn = run_turn(live, build_registry(spy), journal)

        # Native mode, no fallback, tool executed, final strict JSON.
        self.assertEqual(turn.mode, "native")
        self.assertEqual(turn.fallback_motif, "")
        self.assertEqual(turn.errors, ())
        self.assertEqual([c.name for c in turn.calls], ["graph_query"])
        self.assertEqual(turn.calls[0].source, "native")
        self.assertEqual(spy.executed, [{"query": "Q1"}])
        self.assertEqual(turn.final, {"verdict": "graphe interroge"})
        self.assertEqual(turn.results[0]["result"]["status"], "OK")

        # The native request carries the specs and no response_format.
        first_body = http.requests[0]
        self.assertIn("tools", first_body)
        self.assertNotIn("response_format", first_body)
        self.assertEqual(first_body["tool_choice"], "auto")
        self.assertEqual(first_body["tools"][0]["function"]["name"], "graph_query")
        # The finalize call is strict JSON (no tools offered).
        self.assertIn("response_format", http.requests[1])
        self.assertNotIn("tools", http.requests[1])

        # Journal: TOOL_CALL + TOOL_RESULT lines, chain intact.
        kinds = [entry.kind for entry in journal.entries()]
        self.assertIn("TOOL_CALL", kinds)
        self.assertIn("TOOL_RESULT", kinds)
        self.assertTrue(journal.verify_chain()[0])

        # Replay: the whole turn is rebuilt bit-identically.
        replay = RecordedBackend(self.store, config=self.config)
        turn2 = run_turn(replay, build_registry(SpyTool()))
        self.assertEqual(turn2.to_dict(), turn.to_dict())

    def test_replayed_native_calls_keep_their_ids(self):
        http = FakeHTTP([
            chat_tool_calls([("call_7", "graph_query",
                              json.dumps({"query": "Q1"}))]),
            chat_content(FINAL),
        ])
        live = LiveBackend(config=self.config, store=self.store,
                           env=ENV, http_post=http)
        turn = run_turn(live, build_registry())
        self.assertEqual(turn.calls[0].call_id, "call_7")
        turn2 = run_turn(RecordedBackend(self.store, config=self.config),
                         build_registry())
        self.assertEqual(turn2.calls[0].call_id, "call_7")


class TestStrictJsonFallback(unittest.TestCase):
    def setUp(self):
        self.store_dir = tempfile.mkdtemp(prefix="orvyren-toolcall-")
        self.config = load_models_config()
        self.store = ResponseStore(self.store_dir)

    def test_envelope_answer_is_a_journaled_fallback(self):
        http = FakeHTTP([
            chat_content(json.dumps(
                envelope(("graph_query", {"query": "Q1"})))),
            chat_content(FINAL),
        ])
        live = LiveBackend(config=self.config, store=self.store,
                           env=ENV, http_post=http)
        spy = SpyTool()
        journal = AgentJournal()
        turn = run_turn(live, build_registry(spy), journal)

        self.assertEqual(turn.mode, "json_strict")
        self.assertEqual(turn.fallback_motif, "no_native_tool_calls")
        self.assertEqual(turn.calls[0].source, "json_strict")
        self.assertEqual(spy.executed, [{"query": "Q1"}])
        self.assertEqual(turn.final, {"verdict": "graphe interroge"})
        # The fallback is JOURNALED, never silent.
        fallbacks = [entry.content for entry in journal.entries()
                     if entry.content.startswith("fallback json_strict")]
        self.assertEqual(fallbacks, ["fallback json_strict: no_native_tool_calls"])
        self.assertTrue(journal.verify_chain()[0])

    def test_bad_json_retries_without_tools_and_journals(self):
        http = FakeHTTP([
            chat_content("ceci n'est pas du json"),
            chat_content(json.dumps(
                envelope(("graph_query", {"query": "Q1"})))),
            chat_content(FINAL),
        ])
        live = LiveBackend(config=self.config, store=self.store,
                           env=ENV, http_post=http)
        journal = AgentJournal()
        turn = run_turn(live, build_registry(), journal)

        self.assertEqual(turn.mode, "json_strict")
        self.assertEqual(turn.fallback_motif, "E_LLM_BAD_JSON")
        self.assertIn("E_LLM_BAD_JSON", turn.errors)
        # Three LLM calls: failed propose, tools-less retry, finalize.
        self.assertEqual(len(turn.llm), 3)
        # The retry is a strict-JSON request (no tools offered).
        self.assertNotIn("tools", http.requests[1])
        self.assertIn("response_format", http.requests[1])
        fallbacks = [entry.content for entry in journal.entries()
                     if entry.content.startswith("fallback json_strict")]
        self.assertEqual(fallbacks, ["fallback json_strict: E_LLM_BAD_JSON"])
        self.assertTrue(journal.verify_chain()[0])

    def test_fallback_turn_also_replays(self):
        http = FakeHTTP([
            chat_content(json.dumps(
                envelope(("graph_query", {"query": "Q1"})))),
            chat_content(FINAL),
        ])
        live = LiveBackend(config=self.config, store=self.store,
                           env=ENV, http_post=http)
        turn = run_turn(live, build_registry())
        turn2 = run_turn(RecordedBackend(self.store, config=self.config),
                         build_registry())
        self.assertEqual(turn2.to_dict(), turn.to_dict())
        self.assertEqual(turn2.fallback_motif, "no_native_tool_calls")


class TestArgValidation(unittest.TestCase):
    """Closed objects: the tool NEVER runs on a non-conforming call."""

    def setUp(self):
        self.config = load_models_config()

    def _turn_with(self, calls):
        http = FakeHTTP([
            chat_content(json.dumps({"$schema": "orvyren/toolcall/v1",
                                     "calls": calls})),
            chat_content(FINAL),
        ])
        live = LiveBackend(config=self.config, env=ENV, http_post=http)
        spy = SpyTool()
        turn = run_turn(live, build_registry(spy))
        return turn, spy

    def test_unknown_arg_refused(self):
        turn, spy = self._turn_with(
            [{"name": "graph_query", "args": {"query": "Q1", "inconnu": 2}}])
        self.assertEqual(spy.executed, [])
        self.assertEqual(turn.results[0]["result"]["status"], "FAILED")
        self.assertIn("E_TOOL_ARGS_UNKNOWN:inconnu",
                      turn.results[0]["result"]["error"])

    def test_missing_required_refused(self):
        turn, spy = self._turn_with([{"name": "graph_query", "args": {}}])
        self.assertEqual(spy.executed, [])
        self.assertIn("E_TOOL_ARGS_REQUIRED:query",
                      turn.results[0]["result"]["error"])

    def test_unknown_tool_refused(self):
        turn, spy = self._turn_with([{"name": "ghost", "args": {"query": "Q1"}}])
        self.assertEqual(spy.executed, [])
        self.assertEqual(turn.results[0]["result"]["error"], "E_TOOL_UNKNOWN:ghost")

    def test_execute_intent_refused_even_if_proposed(self):
        turn, spy = self._turn_with(
            [{"name": "execute_intent", "args": {}}])
        self.assertEqual(spy.executed, [])
        self.assertEqual(turn.results[0]["result"]["error"], "E_TOOL_FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
