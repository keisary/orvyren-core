# -*- coding: utf-8 -*-
"""W8 (L8.5) — ADR registry index: contiguous numbering, README kept in sync."""

import importlib.util
import os
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_ROOT, "scripts", "adr_index.py")


def _load_adr_index():
    spec = importlib.util.spec_from_file_location("adr_index", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adr_index = _load_adr_index()
DECISIONS_DIR = os.path.join(_ROOT, "docs", "decisions")


def _write_adr(directory, number, title, status="ACCEPTÉE", date="2026-01-01", body=""):
    name = "ADR-%04d-test.md" % number
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# ADR-%04d — %s\n\n**Date :** %s · **Statut : %s** · **Portée :** test.\n%s"
                     % (number, title, date, status, body))
    return path


class AdrIndexTests(unittest.TestCase):
    def test_repository_registry_is_consistent(self):
        entries = adr_index.scan(DECISIONS_DIR)
        self.assertGreaterEqual(len(entries), 3)
        self.assertEqual([entry["number"] for entry in entries],
                         sorted(entry["number"] for entry in entries))
        self.assertEqual(adr_index.check(entries, DECISIONS_DIR), [])

    def test_readme_table_matches_rendered_registry(self):
        entries = adr_index.scan(DECISIONS_DIR)
        with open(os.path.join(DECISIONS_DIR, "README.md"), "r", encoding="utf-8") as handle:
            readme = handle.read()
        self.assertIn(adr_index.render_registry(entries), readme)

    def test_gap_in_numbering_is_detected(self):
        with tempfile.TemporaryDirectory(prefix="orvyren_adr_") as tmp:
            _write_adr(tmp, 1, "un")
            _write_adr(tmp, 3, "trois")
            entries = adr_index.scan(tmp)
            problems = adr_index.check(entries, tmp)
            self.assertTrue(any("ADR-0002" in problem for problem in problems), problems)

    def test_missing_status_and_date_are_flagged(self):
        with tempfile.TemporaryDirectory(prefix="orvyren_adr_") as tmp:
            path = os.path.join(tmp, "ADR-0001-partial.md")
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write("# ADR-0001 — partiel\n\nAucun entête structuré ici.\n")
            entries = adr_index.scan(tmp)
            problems = adr_index.check(entries, tmp)
            joined = " | ".join(problems)
            self.assertIn("statut manquant", joined)
            self.assertIn("date manquante", joined)

    def test_duplicated_number_is_detected(self):
        with tempfile.TemporaryDirectory(prefix="orvyren_adr_") as tmp:
            _write_adr(tmp, 1, "un")
            second = os.path.join(tmp, "ADR-0001-bis.md")
            with open(second, "w", encoding="utf-8", newline="\n") as handle:
                handle.write("# ADR-0001 — doublon\n\n**Date :** 2026-01-01 · **Statut : ACCEPTÉE** · x\n")
            entries = adr_index.scan(tmp)
            problems = adr_index.check(entries, tmp)
            self.assertTrue(any("dupliqué" in problem for problem in problems), problems)


if __name__ == "__main__":
    unittest.main()
