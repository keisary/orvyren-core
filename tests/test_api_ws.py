#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WebSocket /ws/live tests — envelope contract + subscribe + resume.

Skips cleanly and visibly when FastAPI (or httpx) is not installed.

Run: python -m unittest tests.test_api_ws
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None
HAS_HTTPX = importlib.util.find_spec("httpx") is not None
SKIP_REASON = ("fastapi/httpx absent — tests API skippés "
               "(import paresseux respecté)")


@unittest.skipUnless(HAS_FASTAPI and HAS_HTTPX, SKIP_REASON)
class TestApiWebSocket(unittest.TestCase):
    def _open(self):
        from fastapi.testclient import TestClient

        from orvyren.api.main import create_app

        client = TestClient(create_app())
        return client, client.websocket_connect("/ws/live")

    def test_hello_and_monotonic_seq(self):
        client, connection = self._open()
        with connection as websocket:
            hello = json.loads(websocket.receive_text())
            self.assertEqual(hello["type"], "run.status")
            self.assertEqual(hello["payload"]["phase"], "hello")
            self.assertIn("seq", hello)
            first = json.loads(websocket.receive_text())
            second = json.loads(websocket.receive_text())
            self.assertGreater(first["seq"], hello["seq"])
            self.assertGreater(second["seq"], first["seq"])
            self.assertIn(first["type"], (
                "agent.thought", "agent.evidence", "agent.decision",
                "agent.critique", "agent.error", "run.status", "ping"))

    def test_subscribe_run_and_pong(self):
        client, connection = self._open()
        with connection as websocket:
            json.loads(websocket.receive_text())  # hello
            runs = client.get("/api/runs").json()["runs"]
            run_id = next(r["run_id"] for r in runs
                          if r["journals"]["orchestrator"].get("present"))
            websocket.send_text(json.dumps(
                {"type": "subscribe", "channels": ["run:%s" % run_id]}))
            got_subscribed = False
            for _ in range(20):
                message = json.loads(websocket.receive_text())
                if (message["type"] == "run.status"
                        and message["payload"].get("phase") == "subscribed"):
                    got_subscribed = True
                    self.assertEqual(message["payload"]["run_id"], run_id)
                    break
            self.assertTrue(got_subscribed)
            websocket.send_text(json.dumps({"type": "ping"}))
            got_pong = False
            for _ in range(20):
                message = json.loads(websocket.receive_text())
                if message["type"] == "pong":
                    got_pong = True
                    break
            self.assertTrue(got_pong)


@unittest.skipUnless(HAS_FASTAPI, SKIP_REASON)
class TestWebSocketCompressionContract(unittest.TestCase):
    """permessage-deflate (RFC 7692) is pinned in the uvicorn server options.

    The handshake/extension itself belongs to uvicorn's WS implementation
    (the TestClient transport does not negotiate extensions); what the app
    owns — and what can silently regress — is the server option, so that is
    the contract here.
    """

    def test_per_message_deflate_is_pinned_on(self):
        from orvyren.api.main import _uvicorn_kwargs
        options = _uvicorn_kwargs()
        self.assertIs(options["ws_per_message_deflate"], True)

    def test_explicit_override_still_wins(self):
        from orvyren.api.main import _uvicorn_kwargs
        self.assertIs(
            _uvicorn_kwargs(ws_per_message_deflate=False)["ws_per_message_deflate"],
            False)


if __name__ == "__main__":
    unittest.main()
