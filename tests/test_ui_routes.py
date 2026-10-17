# -*- coding: utf-8 -*-
"""W8 (L8.1-L8.3) — local UI routes: twelve screens, mode + clock on every page,
no JavaScript, no external asset, offline robustness.

Kept deliberately functional: we boot the real stdlib server on an ephemeral
port and hit it over HTTP, exactly like a browser would.
"""

import os
import sys
import threading
import unittest
import urllib.error
import urllib.request

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from orvyren.ui import screens  # noqa: E402
from orvyren.ui import server as ui_server  # noqa: E402


class UiRoutesTests(unittest.TestCase):
    """Boot once, hit every route, assert the W8 contract."""

    @classmethod
    def setUpClass(cls):
        cls.httpd = ui_server.make_server(
            "127.0.0.1", 0, evidence_dir=os.path.join(_ROOT, "evidence"), quiet=True)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.httpd.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=10)

    def _get(self, path):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=15) as response:
            return response.status, response.read().decode("utf-8")

    # -- the twelve screens -------------------------------------------------

    def test_index_lists_all_twelve_screens(self):
        status, body = self._get("/ui")
        self.assertEqual(status, 200)
        self.assertIn("Index des écrans", body)
        self.assertNotIn("ERREUR DE RENDU", body)
        for screen_id in screens.screen_ids():
            self.assertIn(f"/screen/{screen_id}", body)

    def test_every_screen_renders_with_mode_and_clock(self):
        self.assertEqual(screens.screen_ids(), list(range(1, 13)))
        for screen_id in screens.screen_ids():
            status, body = self._get(f"/screen/{screen_id}")
            self.assertEqual(status, 200, f"screen {screen_id}")
            self.assertIn("MODE :", body, f"screen {screen_id} must declare its mode")
            self.assertIn("Horloge (UTC)", body, f"screen {screen_id} must display a clock")
            self.assertIn("Horloge simulée", body, f"screen {screen_id}")
            self.assertIn("Sources rendues", body, f"screen {screen_id}")
            self.assertNotIn("ERREUR DE RENDU", body, f"screen {screen_id} crashed")

    def test_pages_are_static_no_javascript_no_external_asset(self):
        pages = [self._get("/ui")[1]]
        for screen_id in screens.screen_ids():
            pages.append(self._get(f"/screen/{screen_id}")[1])
        for page in pages:
            lowered = page.lower()
            self.assertNotIn("<script", lowered)
            self.assertNotIn("src=\"http", lowered)
            self.assertNotIn("href=\"http", lowered)
            self.assertNotIn("@import", lowered)
            self.assertNotIn("url(http", lowered)

    def test_known_modes_are_declared_honestly(self):
        _, body1 = self._get("/screen/1")
        self.assertIn("DONNÉES FIGÉES", body1)
        _, body4 = self._get("/screen/4")
        self.assertIn("REPLAY", body4)
        _, body10 = self._get("/screen/10")
        self.assertIn("LIVE", body10)
        # Sources render with a short sha when they exist in the checkout.
        self.assertIn("sha256:", body10)

    # -- robustness ---------------------------------------------------------

    def test_unknown_screen_is_404_with_the_list_of_screens(self):
        for path in ("/screen/99", "/screen/abc", "/screen/"):
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=10)
            self.assertEqual(raised.exception.code, 404, path)

    def test_previous_routes_still_answer(self):
        status, body = self._get("/api/health")
        self.assertEqual(status, 200)
        self.assertIn('"ok": true', body)
        status, body = self._get("/api/dossier")
        self.assertEqual(status, 200)

    def test_screens_never_invent_missing_sources(self):
        built = screens.build_screen(10, screens.Ctx(_ROOT, os.path.join(_ROOT, "evidence")))
        self.assertIn(b"MODE :", built)


if __name__ == "__main__":
    unittest.main()
