#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: ``agent_journal`` — append-only, hash chain, promotion gate.

Covers B1_AGENTS_ETUDE.md §3.4 (schema, immutable content store keys,
``prev_hash`` chaining) and DOC4 L2.3: the journal is separate from the graph,
promotes only through deterministic validators, and LLM-proposed branches
carry zero weight (B3 rule R1: no decision figure comes from an LLM).

Execution: ``python -m unittest discover -s tests -v``
"""

import os
import sys
import unittest
from dataclasses import replace as dc_replace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.agents.journal import (  # noqa: E402
    GENESIS_HASH,
    JOURNAL_KINDS,
    JOURNAL_STATUSES,
    PROPOSAL_KINDS,
    AgentJournal,
    JournalEntry,
    branch_weight,
    deterministic_validator,
    entry_hash,
)


def line(**overrides):
    """A valid non-LLM journal line as an append_dict mapping."""
    data = dict(
        journal_id="01JAV7Q2M4E1",
        run_id="01JAV7Q0AA",
        episode_id="usdc-2023-03",
        agent_id="explorer",
        role_version="expl-v1",
        step_index=3,
        ts_utc="2023-03-12T00:05:00Z",
        kind="REFLECTION",
        content="L'offre en circulation baisse de 7,17 % en 24 h ; "
                "cela affaiblit « trou de liquidité local ».",
        refs=("observation:binance-2023-03-11T15", "hypothesis:H2"),
    )
    data.update(overrides)
    return data


def llm_fields():
    return dict(
        llm={"provider": "deepseek", "model": "deepseek-v3",
             "model_version_pinned": "deepseek-v3-2026-01", "temperature": 0},
        prompt_hash="a" * 64,
        response_hash="b" * 64,
    )


class SchemaTest(unittest.TestCase):
    """B1 §3.4 columns and closed enums."""

    def test_kinds_and_statuses_are_closed(self):
        self.assertEqual(len(JOURNAL_KINDS), 11, msg=f"measured {JOURNAL_KINDS}")
        self.assertEqual(set(JOURNAL_STATUSES),
                         {"PROPOSED", "ACCEPTED", "REJECTED", "QUARANTINED"})

    def test_proposal_kinds_are_the_usable_ones(self):
        self.assertEqual(PROPOSAL_KINDS,
                         frozenset({"HYPOTHESIS_PROPOSED", "BRANCH_UPDATE",
                                    "DECISION_DRAFT"}))

    def test_entry_carries_the_b1_columns(self):
        entry = JournalEntry(**line())
        self.assertEqual(entry.prev_hash, GENESIS_HASH)
        self.assertEqual(entry.tokens_in, 0)
        self.assertIsInstance(entry.cost_usd, float)


class ValidatorTest(unittest.TestCase):
    """The deterministic gate: schema / no_number / provenance."""

    def test_valid_line_passes(self):
        self.assertTrue(deterministic_validator(JournalEntry(**line())).ok)

    def test_llm_line_needs_pinned_hashes(self):
        data = line(kind="HYPOTHESIS_PROPOSED",
                    content="Le stress vient de l'émetteur.")
        data.pop("refs", None)
        data["llm"] = {"provider": "deepseek", "model": "deepseek-v3",
                       "model_version_pinned": "deepseek-v3-2026-01",
                       "temperature": 0}
        verdict = deterministic_validator(JournalEntry(**data))
        self.assertFalse(verdict.schema_ok)
        self.assertIn("prompt/response hash", verdict.motif)

    def test_proposal_never_carries_a_figure(self):
        data = line(kind="HYPOTHESIS_PROPOSED",
                    content="L'écart passe à 31 %, hypothèse : stress émetteur.")
        verdict = deterministic_validator(JournalEntry(**data))
        self.assertFalse(verdict.no_number_ok)
        self.assertFalse(verdict.ok)
        # A reflection may quote figures (B1 example line does).
        self.assertTrue(deterministic_validator(JournalEntry(**line())).no_number_ok)

    def test_llm_provenance_must_be_complete(self):
        data = line(**llm_fields())
        data["llm"] = {"provider": "deepseek"}  # no pinned version / temperature
        verdict = deterministic_validator(JournalEntry(**data))
        self.assertFalse(verdict.provenance_ok)

    def test_llm_proposal_without_figure_passes(self):
        data = line(kind="HYPOTHESIS_PROPOSED",
                    content="Le stress vient de l'émetteur, pas de la venue.",
                    **llm_fields())
        self.assertTrue(deterministic_validator(JournalEntry(**data)).ok)


class JournalTest(unittest.TestCase):
    """Append-only store, hash chain, quarantine policy."""

    def setUp(self):
        self.journal = AgentJournal()
        self.journal.append_dict(line())
        self.journal.append_dict(line(
            journal_id="01JAV7Q2M4E2", step_index=4, kind="OBSERVATION_REF",
            refs=("observation:supply-2023-03-12T00",)))

    def test_lines_are_hash_chained(self):
        entries = self.journal.entries()
        self.assertEqual(entries[0].prev_hash, GENESIS_HASH)
        self.assertEqual(entries[1].prev_hash, entry_hash(entries[0]))
        ok, motif = self.journal.verify_chain()
        self.assertTrue(ok, motif)

    def test_a_modified_line_breaks_the_chain(self):
        entries = list(self.journal._entries)
        entries[0] = dc_replace(entries[0], content="réécrit en secret")
        self.journal._entries = entries
        ok, motif = self.journal.verify_chain()
        self.assertFalse(ok)
        self.assertIn("chain broken", motif)

    def test_no_update_and_no_delete_api(self):
        for forbidden in ("update", "delete", "remove", "pop", "clear"):
            self.assertFalse(hasattr(self.journal, forbidden), forbidden)

    def test_entries_view_is_immutable(self):
        view = self.journal.entries()
        self.assertIsInstance(view, tuple)
        with self.assertRaises(AttributeError):
            view[0].content = "muté"

    def test_unknown_fields_quarantine_the_line(self):
        entry = self.journal.append_dict(line(
            journal_id="01JAV7Q2M4E3", step_index=5, secret_field="oops"))
        self.assertEqual(entry.status, "QUARANTINED")
        self.assertIn("secret_field", entry.validation["motif"])
        ok, _ = self.journal.verify_chain()
        self.assertTrue(ok)

    def test_invalid_line_is_rejected_but_stays_visible(self):
        entry = self.journal.append_dict(line(
            journal_id="01JAV7Q2M4E4", step_index=6, kind="VIBES"))
        self.assertEqual(entry.status, "REJECTED")
        self.assertEqual(len(self.journal), 3)  # the line is kept, not dropped
        ok, _ = self.journal.verify_chain()
        self.assertTrue(ok)

    def test_llm_branches_carry_zero_weight(self):
        entry = self.journal.append_dict(line(
            journal_id="01JAV7Q2M4E5", step_index=7,
            kind="BRANCH_UPDATE", content="Nouvelle branche : stress émetteur.",
            refs=("hypothesis:H3",), **llm_fields()))
        self.assertEqual(branch_weight(entry), 0.0)
        self.assertEqual(branch_weight(self.journal.entries()[0]), 1.0)
        promotions = self.journal.promote(entry)
        self.assertTrue(promotions)
        self.assertEqual({p.weight for p in promotions}, {0.0})


class PromotionTest(unittest.TestCase):
    """journal -> graph only through deterministic validators (L2.3)."""

    def setUp(self):
        self.journal = AgentJournal()
        self.entry = self.journal.append_dict(line())

    def test_promotion_emits_candidates_and_never_writes(self):
        promotions = self.journal.promote(self.entry)
        self.assertEqual([p.ref for p in promotions], list(self.entry.refs))
        self.assertEqual({p.journal_id for p in promotions}, {self.entry.journal_id})

    def test_a_line_without_refs_cannot_be_used(self):
        entry = self.journal.append_dict(line(
            journal_id="01JAV7Q2M4E6", step_index=9, refs=()))
        with self.assertRaises(ValueError) as caught:
            self.journal.promote(entry)
        self.assertIn("E_JOURNAL_PROMOTION_NO_REFS", str(caught.exception))

    def test_rejected_and_quarantined_lines_never_promote(self):
        rejected = self.journal.append_dict(line(
            journal_id="01JAV7Q2M4E7", step_index=10, kind="VIBES", refs=("x",)))
        with self.assertRaises(ValueError) as caught:
            self.journal.promote(rejected)
        self.assertIn("E_JOURNAL_PROMOTION_STATUS", str(caught.exception))

    def test_a_refused_validator_blocks_promotion(self):
        def refusing(entry):
            return type(deterministic_validator(entry))(
                True, True, False, "provenance: external refusal")

        with self.assertRaises(ValueError) as caught:
            self.journal.promote(self.entry, validator=refusing)
        self.assertIn("E_JOURNAL_PROMOTION_REFUSED", str(caught.exception))

    def test_only_lines_of_this_store_promote(self):
        stranger = JournalEntry(**line(journal_id="01JEXTERNAL", step_index=99))
        with self.assertRaises(ValueError) as caught:
            self.journal.promote(stranger)
        self.assertIn("E_JOURNAL_NOT_IN_STORE", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
