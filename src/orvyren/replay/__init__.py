#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — replay engine: the `orvyren.replay` package (W7, lot L7.7).

Two official modes, never confused (B7 §c.2, frozen names):

* **REPLAY-JOURNAL** — the agent journals and the response store are re-read
  (raw prompts/responses addressed by hash): nothing is recomputed, the
  ``prev_hash`` chaining is verified at read time — **bit-for-bit guaranteed
  by construction** (:mod:`orvyren.replay.journal`);
* **REPLAY-ARCHIVE** — LLM calls are recomputed on the frozen corpus and
  pinned blocks: **non-deterministic** ("same decision, different text" —
  this is a published result, not a failure)
  (:mod:`orvyren.replay.archive`); requires an LLM provider.

Cross-cutting rules: simulated clock with strict PIT (:mod:`orvyren.replay.clock`),
frozen corpus verified by hash and no ``latest`` (:mod:`orvyren.replay.corpus`),
replay dossier tagged ``REPLAY`` with provenance
(:mod:`orvyren.replay.dossier`), and the append-only replay log
``replay/runs.jsonl``. **A replay run never signs and never emits a
transaction** (B7 §c.5-4).
"""

from __future__ import annotations

from orvyren.replay import archive, clock, corpus, dossier, journal  # noqa: F401

__all__ = ["archive", "clock", "corpus", "dossier", "journal"]
