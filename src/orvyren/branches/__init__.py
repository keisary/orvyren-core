"""Living hypothesis registry: falsifiable records with append-only history.

Contracts of B3_DECISION_ETUDE.md §a.3–§a.5 (archive 2026-10-15) and DOC4 L2.1:
a 12-field record, a 7-state lifecycle with 5 transition rules, and an
append-only history — a hypothesis is **never deleted** (ARCHIVED is a state,
not a deletion) and an LLM never removes one.

Standard library only.
"""
