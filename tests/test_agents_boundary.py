#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Boundary test (W2 criterion): no agent module may import ``orvyren.policy``
or ``orvyren.execution``.

The rule (DOC4 W2 / FREEZE_V2): agent code proposes, it never touches the
policy authority nor the signer/executor. Two checks:

1. **Static**: scan every ``src/orvyren/agents/*.py`` import line;
2. **Runtime**: in a fresh interpreter, import every agent module and assert
   neither ``orvyren.policy`` nor ``orvyren.execution`` ever lands in
   ``sys.modules`` (lazy worker imports included).

Execution: ``python -m pytest tests/test_agents_boundary.py -q``.
"""

import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
AGENTS_DIR = os.path.join(SRC, "orvyren", "agents")


class TestAgentBoundary(unittest.TestCase):

    def test_static_no_forbidden_imports(self):
        offenders = []
        for name in sorted(os.listdir(AGENTS_DIR)):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(AGENTS_DIR, name), encoding="utf-8") as handle:
                for line in handle:
                    stripped = line.strip()
                    if not stripped.startswith(("import ", "from ")):
                        continue
                    if ("orvyren.policy" in stripped or "orvyren.execution" in stripped
                            or "orvyren import policy" in stripped
                            or "orvyren import execution" in stripped):
                        offenders.append("%s: %s" % (name, stripped))
        self.assertEqual(offenders, [], "agent modules importing policy/execution: %r"
                         % offenders)

    def test_runtime_import_does_not_load_policy_or_execution(self):
        code = (
            "import sys\n"
            "sys.path.insert(0, r'%s')\n"
            "import importlib\n"
            "loaded = []\n"
            "failed = []\n"
            "for name in ('contracts', 'journal', 'prompts', 'store', 'llm',\n"
            "             'tools', 'loop', 'worker'):\n"
            "    try:\n"
            "        importlib.import_module('orvyren.agents.' + name)\n"
            "        loaded.append(name)\n"
            "    except ImportError as exc:\n"
            "        failed.append('%%s: %%s' %% (name, exc))\n"
            "assert not failed, 'agent modules failed to import: %%r' %% failed\n"
            "assert 'orvyren.policy' not in sys.modules, 'policy loaded by agents'\n"
            "assert 'orvyren.execution' not in sys.modules, 'execution loaded by agents'\n"
            "print('BOUNDARY_OK', ','.join(loaded))\n" % SRC
        )
        done = subprocess.run([sys.executable, "-c", code], capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
        self.assertIn("BOUNDARY_OK", done.stdout, done.stdout + done.stderr)
        # every module of the loop must really have been imported — otherwise the
        # boundary check above would silently skip its lazy imports
        for name in ("contracts", "journal", "prompts", "store", "llm",
                     "tools", "loop", "worker"):
            self.assertIn(name, done.stdout, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
