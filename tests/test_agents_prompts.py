#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: ``agents.prompts`` — the three versioned French skeletons (L2.5).

Covers B1_AGENTS_ETUDE.md §5.2/§5.3/§5.4: the three system-prompt skeletons
are present, non-empty, carry their closed JSON schema id and the key clauses
(external content is untrusted, JSON-only output, ``stop=true``), and their
versions are frozen and stable (``role_version`` of every journal line).

Execution: ``python -m pytest tests/test_agents_prompts.py -q``
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.agents import prompts  # noqa: E402

EXPECTED_VERSIONS = {
    "orchestrator": "orch-p1.0.0",
    "critic": "crit-p1.0.0",
    "canonicalizer": "canon-p1.0.0",
}


class SkeletonTest(unittest.TestCase):
    """The three skeletons exist, are substantial and carry the key clauses."""

    def test_three_skeletons_only(self):
        self.assertEqual(set(prompts.SYSTEM_PROMPTS), set(EXPECTED_VERSIONS))
        self.assertEqual(set(prompts.PROMPT_VERSIONS), set(EXPECTED_VERSIONS))

    def test_skeletons_are_non_empty_and_substantial(self):
        for role, text in prompts.SYSTEM_PROMPTS.items():
            self.assertIsInstance(text, str, role)
            self.assertGreater(len(text.strip()), 400, role)

    def test_every_skeleton_outputs_strict_json(self):
        for role, text in prompts.SYSTEM_PROMPTS.items():
            self.assertIn("JSON", text, role)
            self.assertIn('"$schema"', text, role)

    def test_every_skeleton_states_the_untrusted_clause(self):
        for role, text in prompts.SYSTEM_PROMPTS.items():
            self.assertIn("NON FIABLE", text, role)

    def test_orchestrator_carries_mission_context_rules_and_stop(self):
        text = prompts.system_prompt("orchestrator")
        self.assertIn("MISSION", text)
        self.assertIn("CONTEXTE FOURNI", text)
        self.assertIn("RÈGLES", text)
        self.assertIn('"orvyren/orch/v1"', text)
        self.assertIn("stop=true", text)
        self.assertIn("champ inconnu sera REJETÉ", text)
        for rule in ("1.", "2.", "3.", "4.", "5."):
            self.assertIn(rule, text)

    def test_critic_searches_for_the_error_and_bans_rewrites(self):
        text = prompts.system_prompt("critic")
        self.assertIn("chercher l'erreur", text)
        self.assertIn("INTERDITS", text)
        self.assertIn('Une objection sans ref est invalide', text)
        self.assertIn("REJETÉ", text)
        self.assertIn('"orvyren/crit/v1"', text)

    def test_canonicaliser_copies_never_computes(self):
        text = prompts.system_prompt("canonicalizer")
        self.assertIn("recopier, jamais calculer", text)
        self.assertIn("Ne convertit pas, ne calcule pas, n'arrondis pas", text)
        self.assertIn('"orvyren/canon/v1"', text)
        self.assertIn("OK | ABSENT | AMBIGU", text)
        self.assertIn("QUARANTAINE", text)


class VersionTest(unittest.TestCase):
    """Versions are frozen and stable — they key every replay."""

    def test_versions_are_the_frozen_ones(self):
        self.assertEqual(prompts.PROMPT_VERSIONS, EXPECTED_VERSIONS)

    def test_version_accessor(self):
        for role, version in EXPECTED_VERSIONS.items():
            self.assertEqual(prompts.prompt_version(role), version)

    def test_system_prompt_accessor(self):
        for role in EXPECTED_VERSIONS:
            self.assertIs(prompts.system_prompt(role), prompts.SYSTEM_PROMPTS[role])

    def test_unknown_role_raises_key_error(self):
        for accessor in (prompts.system_prompt, prompts.prompt_version):
            with self.assertRaises(KeyError):
                accessor("explorer")
            with self.assertRaises(KeyError):
                accessor("")


if __name__ == "__main__":
    unittest.main()
