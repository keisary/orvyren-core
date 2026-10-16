#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: ``agents.llm`` + ``agents.prompts`` smoke (L2.5/L2.6).

Covers the pinned/dated models config (DOC2 §5.2.2: smoke test fails when an
identifier is no longer conform), the $/Mtok cost model (frozen anchor:
0.0132 $ for the target profile), ``RecordedBackend`` fail-closed replay
(``E_LLM_NOT_RECORDED``, k=10 bit-identical results) and ``LiveBackend``:
no key → ``E_LLM_NO_KEY`` with zero network calls; HTTP 500 then success
(retry with backoff); 429 twice then provider fallback; empty content →
``E_LLM_EMPTY_RESPONSE``; invalid JSON → ``E_LLM_BAD_JSON``; success → the
store is written and ``RecordedBackend`` replays the same LLMResult
(``ts_utc`` included).

Execution: ``python -m pytest tests/test_agents_llm.py -q``
"""

import json
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.agents import contracts, prompts  # noqa: E402
from orvyren.agents.llm import (  # noqa: E402
    LiveBackend,
    RecordedBackend,
    compute_cost,
    load_models_config,
)
from orvyren.agents.store import ResponseStore, response_hash  # noqa: E402

DEEPSEEK_ENV = {"ORVYREN_DEEPSEEK_API_KEY": "sk-deepseek-test"}
MIMO_ENV = {"ORVYREN_MIMO_API_KEY": "sk-mimo-test"}

ORCH_RESPONSE = contracts.canonical_json(
    {"$schema": "orvyren/orch/v1", "lacune_id": "L1", "tache": None,
     "stop": True, "motif_stop": "aucune lacune à valeur positive",
     "non_recherche": ["prix SpotUSDC"]})


def orch_kwargs(**overrides):
    kwargs = dict(
        role="orchestrator",
        role_version=prompts.prompt_version("orchestrator"),
        schema_id="orvyren/orch/v1",
        system_prompt=prompts.system_prompt("orchestrator"),
        payload={"snapshot_at": "2023-03-12T00:00:00Z",
                 "lacunes": [{"id": "L1"}],
                 "budget": {"appels_llm_restants": 3}},
    )
    kwargs.update(overrides)
    return kwargs


def chat_response(content, tokens_in=260000, tokens_out=6000, cached_in=200000):
    """One OpenAI-compatible 200 body as (status, text)."""
    body = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": tokens_in,
                  "completion_tokens": tokens_out,
                  "prompt_cache_hit_tokens": cached_in},
    }
    return (200, json.dumps(body, ensure_ascii=False))


class FakeHTTP:
    """Scripted transport: (status, text) tuples or exceptions, in order."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def __call__(self, url, headers, body_bytes, timeout):
        self.calls.append({"url": url, "headers": dict(headers),
                           "body": body_bytes, "timeout": timeout})
        if not self.script:
            raise AssertionError("unexpected extra HTTP call to %s" % url)
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class FakeClock:
    def __init__(self, step_s=0.25):
        self.now = 0.0
        self.step_s = step_s

    def __call__(self):
        value = self.now
        self.now += self.step_s
        return value


class FakeSleeper:
    def __init__(self):
        self.slept = []

    def __call__(self, seconds):
        self.slept.append(seconds)


def live_backend(config, store=None, env=None, script=()):
    http = FakeHTTP(script)
    sleeper = FakeSleeper()
    backend = LiveBackend(config, store=store, env=env or {}, http_post=http,
                          clock=FakeClock(), sleeper=sleeper)
    return backend, http, sleeper


class ConfigSmokeTest(unittest.TestCase):
    """DOC2 §5.2.2: pinned + dated identifiers, two model families."""

    @classmethod
    def setUpClass(cls):
        cls.config = load_models_config()

    def test_config_loads_from_the_repo_root(self):
        self.assertEqual(self.config["schema"], "orvyren/models-config/v1")
        self.assertIn("deepseek-flash", self.config["models"])
        self.assertIn("mimo-v2.6-pro", self.config["models"])
        self.assertEqual(set(self.config["roles"]),
                         {"orchestrator", "explorer", "critic", "canonicalizer"})

    def test_every_model_is_pinned_and_dated(self):
        self.assertRegex(str(self.config.get("verified_at", "")),
                         r"\d{4}-\d{2}-\d{2}", "config must be dated")
        for key, model in self.config["models"].items():
            self.assertTrue(str(model.get("pinned_version", "")).strip(), key)
            self.assertTrue(str(model.get("api_key_env", "")).strip(), key)
            self.assertIsInstance(model.get("temperature"), (int, float), key)
            prices = model["prices_usd_per_mtok"]
            for price_key in ("cache_in", "in", "out"):
                self.assertIsInstance(prices[price_key], (int, float), (key, price_key))

    def test_critic_runs_on_a_second_family(self):
        orchestrator = self.config["models"][
            self.config["roles"]["orchestrator"]["model_key"]]
        critic = self.config["models"][self.config["roles"]["critic"]["model_key"]]
        self.assertNotEqual(orchestrator["provider"], critic["provider"])


class ConfigValidationTest(unittest.TestCase):
    """Strict loading: E_CONFIG_* on every non-conforming file."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def write(self, config):
        path = os.path.join(self._tmp.name, "models.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(config, handle)
        return path

    @staticmethod
    def base_config():
        return {
            "schema": "orvyren/models-config/v1",
            "roles": {"orchestrator": {"model_key": "m1", "fallbacks": []}},
            "models": {"m1": {
                "provider": "p", "api_model": "m1", "pinned_version": "1.0",
                "base_url": "https://api.example.invalid/v1",
                "api_key_env": "K1", "temperature": 0.0,
                "prices_usd_per_mtok": {"cache_in": 0.001, "in": 0.1, "out": 0.2},
            }},
        }

    def assert_code(self, code, config):
        with self.assertRaises(ValueError) as caught:
            load_models_config(self.write(config))
        self.assertIn(code, str(caught.exception))

    def test_missing_models_key_is_E_CONFIG_INVALID(self):
        config = self.base_config()
        del config["models"]
        self.assert_code("E_CONFIG_INVALID", config)

    def test_unknown_model_reference_is_E_CONFIG_MODEL_UNKNOWN(self):
        config = self.base_config()
        config["roles"]["orchestrator"]["fallbacks"] = ["ghost"]
        self.assert_code("E_CONFIG_MODEL_UNKNOWN", config)

    def test_model_without_pinned_version_is_E_CONFIG_MODEL_INCOMPLETE(self):
        config = self.base_config()
        del config["models"]["m1"]["pinned_version"]
        self.assert_code("E_CONFIG_MODEL_INCOMPLETE", config)

    def test_empty_base_url_requires_a_note(self):
        config = self.base_config()
        config["models"]["m1"]["base_url"] = ""
        self.assert_code("E_CONFIG_BASE_URL", config)
        config["models"]["m1"]["base_url_note"] = "renseigner le jour J"
        self.assertIn("m1", load_models_config(self.write(config))["models"])

    def test_missing_file_is_E_CONFIG_NOT_FOUND(self):
        with self.assertRaises(FileNotFoundError) as caught:
            load_models_config(os.path.join(self._tmp.name, "absent.json"))
        self.assertIn("E_CONFIG_NOT_FOUND", str(caught.exception))


class ComputeCostTest(unittest.TestCase):
    """$/Mtok, cache discount, frozen DOC2 anchor."""

    @classmethod
    def setUpClass(cls):
        cls.flash = load_models_config()["models"]["deepseek-flash"]
        cls.mimo_pro = load_models_config()["models"]["mimo-v2.6-pro"]

    def test_no_cache_plain_rates(self):
        self.assertAlmostEqual(
            compute_cost(self.flash, 1_000_000, 0, 1_000_000),
            0.15 + 0.60, places=9)

    def test_cached_input_is_billed_at_the_cache_rate(self):
        self.assertAlmostEqual(
            compute_cost(self.flash, 1_000_000, 1_000_000, 0), 0.003, places=9)
        self.assertAlmostEqual(
            compute_cost(self.flash, 1_000_000, 200_000, 0), 0.1206, places=9)

    def test_frozen_target_profile_costs_0_0132(self):
        # DOC2 §5.2.2: 60k missed + 200k cached in, 6k out -> 0,0132 $.
        self.assertAlmostEqual(
            compute_cost(self.flash, 60_000 + 200_000, 200_000, 6_000),
            0.0132, places=9)

    def test_second_family_rates(self):
        self.assertAlmostEqual(
            compute_cost(self.mimo_pro, 1_000_000, 0, 1_000_000),
            0.435 + 0.87, places=9)


class RecordedBackendTest(unittest.TestCase):
    """REPLAY-JOURNAL: fail-closed on absence, bit-identical on presence."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = ResponseStore(self._tmp.name)
        self.config = load_models_config()
        self.backend = RecordedBackend(self.store, self.config)

    def test_absent_recording_returns_E_LLM_NOT_RECORDED(self):
        result = self.backend.complete(**orch_kwargs())
        expected_hash = self.store.hash_prompt(
            "orchestrator", prompts.prompt_version("orchestrator"),
            "orvyren/orch/v1", prompts.system_prompt("orchestrator"),
            orch_kwargs()["payload"])
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "E_LLM_NOT_RECORDED:%s" % expected_hash)
        self.assertEqual(result.provider, "deepseek")
        self.assertEqual(result.model, "deepseek-flash")
        self.assertEqual(result.model_version_pinned, "V4.1-Flash")
        self.assertEqual(result.temperature, 0.0)

    def test_recorded_answer_is_identical_over_k10_replays(self):
        kwargs = orch_kwargs()
        p_hash = self.store.hash_prompt(
            kwargs["role"], kwargs["role_version"], kwargs["schema_id"],
            kwargs["system_prompt"], kwargs["payload"])
        r_hash = response_hash(ORCH_RESPONSE)
        self.store.save_prompt(p_hash, kwargs["system_prompt"], kwargs["payload"])
        self.store.save_response(r_hash, ORCH_RESPONSE)
        self.store.record_call({
            "record_id": "rec-fixed", "prompt_hash": p_hash,
            "response_hash": r_hash, "role": kwargs["role"],
            "role_version": kwargs["role_version"], "schema_id": kwargs["schema_id"],
            "ts_utc": "2026-10-16T01:02:03Z", "provider": "deepseek",
            "model": "deepseek-flash", "model_version_pinned": "V4.1-Flash",
            "temperature": 0.0, "tokens_in": 260000, "cached_in": 200000,
            "tokens_out": 6000, "cost_usd": 0.0132, "latency_ms": 1234,
        })
        results = [self.backend.complete(**kwargs) for _ in range(10)]
        fingerprints = {json.dumps(r.to_dict(), sort_keys=True) for r in results}
        self.assertEqual(len(fingerprints), 1, "k=10 replays must be identical")
        sample = results[0]
        self.assertTrue(sample.ok)
        self.assertEqual(sample.data, json.loads(ORCH_RESPONSE))
        self.assertEqual(sample.ts_utc, "2026-10-16T01:02:03Z")
        self.assertEqual(sample.latency_ms, 1234)
        self.assertEqual(sample.tokens_in, 260000)
        self.assertEqual(sample.cached_in, 200000)
        self.assertEqual(sample.tokens_out, 6000)
        self.assertEqual(sample.cost_usd, 0.0132)
        self.assertEqual(sample.prompt_hash, p_hash)
        self.assertEqual(sample.response_hash, r_hash)

    def test_recorded_non_json_answer_is_E_LLM_BAD_JSON_with_raw(self):
        kwargs = orch_kwargs()
        p_hash = self.store.hash_prompt(
            kwargs["role"], kwargs["role_version"], kwargs["schema_id"],
            kwargs["system_prompt"], kwargs["payload"])
        raw = "pas du JSON"
        r_hash = response_hash(raw)
        self.store.save_prompt(p_hash, kwargs["system_prompt"], kwargs["payload"])
        self.store.save_response(r_hash, raw)
        self.store.record_call({
            "record_id": "rec-bad", "prompt_hash": p_hash, "response_hash": r_hash,
            "role": kwargs["role"], "role_version": kwargs["role_version"],
            "schema_id": kwargs["schema_id"], "ts_utc": "2026-10-16T01:02:03Z"})
        result = self.backend.complete(**kwargs)
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "E_LLM_BAD_JSON")
        self.assertEqual(result.raw, raw)

    def test_find_call_is_exposed(self):
        self.assertIsNone(self.backend.find_call("0" * 64))


class LiveBackendTest(unittest.TestCase):
    """Recovery by class, key hygiene, store recording and replay equality."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = ResponseStore(self._tmp.name)
        self.config = load_models_config()

    def test_no_key_returns_E_LLM_NO_KEY_without_any_network_call(self):
        backend, http, sleeper = live_backend(self.config, env={})
        result = backend.complete(**orch_kwargs())
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "E_LLM_NO_KEY")
        self.assertEqual(http.calls, [])
        self.assertEqual(sleeper.slept, [])
        self.assertEqual(result.model, "deepseek-flash")
        self.assertEqual(result.model_version_pinned, "V4.1-Flash")
        self.assertEqual(result.temperature, 0.0)

    def test_http_500_then_success_is_retried(self):
        backend, http, sleeper = live_backend(
            self.config, env=DEEPSEEK_ENV,
            script=[(500, "boom"), chat_response(ORCH_RESPONSE)])
        result = backend.complete(**orch_kwargs())
        self.assertTrue(result.ok, result.error)
        self.assertEqual(len(http.calls), 2)
        self.assertEqual(sleeper.slept, [0.5])
        self.assertEqual(result.model, "deepseek-flash")
        self.assertEqual(result.tokens_in, 260000)
        self.assertEqual(result.cached_in, 200000)
        self.assertEqual(result.tokens_out, 6000)
        self.assertAlmostEqual(result.cost_usd, 0.0132, places=9)
        self.assertEqual(result.latency_ms, 250)

    def test_transport_exception_is_retried(self):
        backend, http, sleeper = live_backend(
            self.config, env=DEEPSEEK_ENV,
            script=[OSError("réseau coupé"), chat_response(ORCH_RESPONSE)])
        result = backend.complete(**orch_kwargs())
        self.assertTrue(result.ok, result.error)
        self.assertEqual(len(http.calls), 2)
        self.assertEqual(sleeper.slept, [0.5])

    def test_429_twice_then_fallback_model(self):
        env = dict(DEEPSEEK_ENV)
        env.update(MIMO_ENV)
        backend, http, sleeper = live_backend(
            self.config, env=env,
            script=[(429, "quota"), (429, "quota"), chat_response(ORCH_RESPONSE)])
        result = backend.complete(**orch_kwargs())
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.provider, "mimo")
        self.assertEqual(result.model, "mimo-v2.6-flash")
        self.assertEqual(len(http.calls), 3)
        self.assertIn("api.deepseek.com", http.calls[0]["url"])
        self.assertIn("api.deepseek.com", http.calls[1]["url"])
        self.assertIn("xiaomimimo", http.calls[2]["url"])
        self.assertEqual(sleeper.slept, [0.5])
        self.assertAlmostEqual(result.cost_usd, 0.01064, places=9)
        self.assertEqual(result.temperature, 0.0)

    def test_fallback_skipped_when_its_key_is_absent(self):
        backend, http, sleeper = live_backend(
            self.config, env=MIMO_ENV,
            script=[chat_response(ORCH_RESPONSE)])
        result = backend.complete(**orch_kwargs())
        self.assertTrue(result.ok, result.error)
        self.assertEqual(len(http.calls), 1)
        self.assertIn("xiaomimimo", http.calls[0]["url"])
        self.assertEqual(result.model, "mimo-v2.6-flash")

    def test_all_providers_exhausted_is_E_LLM_ALL_PROVIDERS_FAILED(self):
        backend, http, sleeper = live_backend(
            self.config, env=DEEPSEEK_ENV,
            script=[(500, "a"), (500, "b"), (503, "c")])
        result = backend.complete(**orch_kwargs())
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "E_LLM_ALL_PROVIDERS_FAILED")
        self.assertEqual(len(http.calls), 3)
        self.assertEqual(sleeper.slept, [0.5, 1.0])

    def test_empty_content_is_E_LLM_EMPTY_RESPONSE(self):
        backend, http, sleeper = live_backend(
            self.config, env=DEEPSEEK_ENV, script=[chat_response("")])
        result = backend.complete(**orch_kwargs())
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "E_LLM_EMPTY_RESPONSE")
        self.assertEqual(result.raw, "")
        self.assertEqual(len(http.calls), 1, "content failures are terminal")
        self.assertEqual(result.model, "deepseek-flash")

    def test_invalid_json_content_is_E_LLM_BAD_JSON_keeping_raw(self):
        content = "{\"$schema\": \"orvyren/orch/v1\", oops"
        backend, http, sleeper = live_backend(
            self.config, env=DEEPSEEK_ENV, script=[chat_response(content)])
        result = backend.complete(**orch_kwargs())
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "E_LLM_BAD_JSON")
        self.assertEqual(result.raw, content)

    def test_request_is_openai_compatible_json_mode(self):
        backend, http, sleeper = live_backend(
            self.config, env=DEEPSEEK_ENV, script=[chat_response(ORCH_RESPONSE)])
        kwargs = orch_kwargs()
        backend.complete(**kwargs)
        call = http.calls[0]
        self.assertEqual(call["url"], "https://api.deepseek.com/chat/completions")
        self.assertEqual(call["headers"]["Authorization"], "Bearer sk-deepseek-test")
        self.assertEqual(call["headers"]["Content-Type"], "application/json")
        body = json.loads(call["body"].decode("utf-8"))
        self.assertEqual(body["model"], "deepseek-flash")
        self.assertEqual(body["temperature"], 0.0)
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(body["messages"][0],
                         {"role": "system", "content": kwargs["system_prompt"]})
        self.assertEqual(body["messages"][1],
                         {"role": "user", "content": contracts.canonical_json(kwargs["payload"])})

    def test_success_records_the_store_and_replay_matches_ts_included(self):
        backend, http, sleeper = live_backend(
            self.config, store=self.store, env=DEEPSEEK_ENV,
            script=[chat_response(ORCH_RESPONSE)])
        kwargs = orch_kwargs()
        live = backend.complete(**kwargs)
        self.assertTrue(live.ok, live.error)
        ok, problems = self.store.verify()
        self.assertTrue(ok, msg=f"store after a live call: {problems}")
        calls = self.store.calls()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["prompt_hash"], live.prompt_hash)
        self.assertEqual(calls[0]["response_hash"], live.response_hash)
        self.assertEqual(self.store.get_response(live.response_hash), ORCH_RESPONSE)
        replay = RecordedBackend(self.store, self.config).complete(**kwargs)
        self.assertEqual(replay.to_dict(), live.to_dict(),
                         "replay must be bit-identical (ts_utc included)")
        self.assertEqual(replay.ts_utc, live.ts_utc)

    def test_payload_is_passed_as_canonical_json_user_message(self):
        backend, http, sleeper = live_backend(
            self.config, env=DEEPSEEK_ENV, script=[chat_response(ORCH_RESPONSE)])
        kwargs = orch_kwargs(payload={"b": 1, "a": 2})
        backend.complete(**kwargs)
        body = json.loads(http.calls[0]["body"].decode("utf-8"))
        self.assertEqual(body["messages"][1]["content"], '{"a":2,"b":1}')


if __name__ == "__main__":
    unittest.main()
