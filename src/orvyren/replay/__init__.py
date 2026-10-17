#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — moteur de rejeu : paquet `orvyren.replay` (W7, lot L7.7).

Deux modes officiels, jamais confondus (B7 §c.2, noms gelés) :

* **REPLAY-JOURNAL** — on relit le journal d'agents + le magasin de réponses
  (prompts/réponses bruts adressés par hash) : rien n'est recalculé, le
  chaînage ``prev_hash`` est vérifié à la lecture — **bit-à-bit garanti par
  construction** (:mod:`orvyren.replay.journal`) ;
* **REPLAY-ARCHIVE** — les appels LLM sont recalculés sur le corpus figé et
  des blocs épinglés : **non déterministe** (« même décision, texte
  différent » — c'est un résultat publié, pas un échec)
  (:mod:`orvyren.replay.archive`) ; exige un fournisseur LLM.

Règles transverses : horloge simulée à PIT strict (:mod:`orvyren.replay.clock`),
corpus figé vérifié par hash et aucun ``latest`` (:mod:`orvyren.replay.corpus`),
dossier de rejeu marqué ``REPLAY`` avec provenance
(:mod:`orvyren.replay.dossier`), et le journal des rejeux append-only
``replay/runs.jsonl``. **Un run de rejeu ne signe jamais et n'émet jamais de
transaction** (B7 §c.5-4).
"""

from __future__ import annotations

from orvyren.replay import archive, clock, corpus, dossier, journal  # noqa: F401

__all__ = ["archive", "clock", "corpus", "dossier", "journal"]
