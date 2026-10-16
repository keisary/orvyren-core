# -*- coding: utf-8 -*-
"""Scripted HTTP transport — demo SEEDING only (W2, L2.6 support).

Not a runtime component. It replays canned OpenAI-compatible responses so a
demo run can be **recorded** into the response store
(``fixtures/agents/store_<case>/``) **without API keys**, walking the exact
same :class:`~orvyren.agents.llm.LiveBackend` recording path a live run would.
The store's ``SEED.json`` manifest declares the entries as scripted — they are
never presented as live recordings (honesty rule; a live recording simply
replaces them once the keys exist:

    python run_agents.py --case usdc-2023-03 --replay live   # records too
).

One worker process builds one transport for **its** role; responses are
consumed **in order** (the scripted run is deterministic by construction).
The HTTP contract is ``http_post(url, headers, body_bytes, timeout) ->
(status, text)`` — identical to the injected transport used in
``tests/test_agents_llm.py``.

Standard library only.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

__all__ = ["ScriptedHTTP", "load_script", "build_scripted_backend"]

#: Fake keys: they only satisfy the "key present" check — no network happens.
_FAKE_KEYS = {"ORVYREN_DEEPSEEK_API_KEY": "scripted-seed",
              "ORVYREN_MIMO_API_KEY": "scripted-seed"}


class ScriptedHTTP:
    """Callable transport serving canned chat-completion envelopes in order."""

    def __init__(self, role: str, responses: List[Dict[str, Any]]) -> None:
        self.role = role
        self._queue = list(responses)
        self.calls = 0

    def __call__(self, url: str, headers: Dict[str, str], body_bytes: bytes,
                 timeout: float) -> Tuple[int, str]:
        self.calls += 1
        if not self._queue:
            raise RuntimeError("E_SCRIPT_EXHAUSTED: no scripted response left for %r"
                               % self.role)
        item = self._queue.pop(0)
        content = item["content"]
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False, sort_keys=True)
        envelope = {
            "id": "scripted-%s-%03d" % (self.role, self.calls),
            "object": "chat.completion",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": int(item.get("prompt_tokens", 1200)),
                      "prompt_cache_hit_tokens": int(item.get("cached_tokens", 0)),
                      "completion_tokens": int(item.get("completion_tokens", 300))},
        }
        return (200, json.dumps(envelope, ensure_ascii=False))


def load_script(run_dir: str) -> Dict[str, Any]:
    """Load ``scripted_responses.json`` from the run directory."""
    path = os.path.join(run_dir, "scripted_responses.json")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def build_scripted_backend(spec: Dict[str, Any], run_dir: str, role: str):
    """Build a recording :class:`LiveBackend` fed by the run's scripted queue."""
    from orvyren.agents.llm import LiveBackend, load_models_config
    from orvyren.agents.store import ResponseStore

    script = load_script(run_dir)
    responses = script.get(role)
    if not responses:
        raise ValueError("E_SCRIPT_ROLE: no scripted responses for %r" % role)
    store_dir = spec.get("store_dir")
    if not store_dir:
        raise ValueError("E_SCRIPT_STORE: store_dir required for scripted seeding")
    store = ResponseStore(store_dir if os.path.isabs(store_dir)
                          else os.path.join(run_dir, store_dir))
    state = {"t": 0.0}

    def clock() -> float:
        state["t"] += 0.02  # deterministic latency (20 ms per read)
        return state["t"]

    return LiveBackend(load_models_config(), store=store, env=dict(_FAKE_KEYS),
                       http_post=ScriptedHTTP(role, responses), clock=clock,
                       sleeper=lambda seconds: None)
