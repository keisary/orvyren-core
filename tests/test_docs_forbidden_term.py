# -*- coding: utf-8 -*-
"""W8 (L8.7) — rule 0 over the public documentation surface.

The public repository must never name the upstream system. The scope is the
documentation a third party actually reads: ``README.md`` and every Markdown
file under ``docs/`` (including sub-directories). Internal research and review
material lives outside the repository and is therefore out of scope by
construction, not by exception.

Guarded against a silently empty scope: the test fails if fewer than three
public documents are found.
"""

import os
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORBIDDEN_TERM = "mimir"  # rule 0 of the freeze: no upstream system name
MINIMUM_DOCUMENTS = 3


def public_documents():
    """README + every Markdown file under ``docs/`` (recursive, sorted)."""
    paths = [os.path.join(_ROOT, "README.md")]
    docs_dir = os.path.join(_ROOT, "docs")
    for dirpath, dirnames, filenames in os.walk(docs_dir):
        dirnames.sort()
        for name in sorted(filenames):
            if name.lower().endswith(".md"):
                paths.append(os.path.join(dirpath, name))
    return paths


class ForbiddenTermTests(unittest.TestCase):
    def test_the_public_documents_are_clean(self):
        documents = public_documents()
        self.assertGreaterEqual(len(documents), MINIMUM_DOCUMENTS,
                                "the public documentation surface is empty")
        for path in documents:
            self.assertTrue(os.path.isfile(path), "document manquant : %s" % path)
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read().lower()
            self.assertNotIn(
                FORBIDDEN_TERM, text,
                "%s contains a proper name forbidden by rule 0 (freeze v2)"
                % os.path.relpath(path, _ROOT))

    def test_the_scope_is_the_documentation_surface_not_a_fixed_list(self):
        names = {os.path.relpath(path, _ROOT).replace(os.sep, "/")
                 for path in public_documents()}
        self.assertIn("README.md", names)
        self.assertTrue(any(name.startswith("docs/") for name in names),
                        "docs/ contributes no Markdown file to the scope")


if __name__ == "__main__":
    unittest.main()
