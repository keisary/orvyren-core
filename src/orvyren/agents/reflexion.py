# -*- coding: utf-8 -*-
"""``reflexion`` — ACH reflexive agents: the matrix is built in CODE, never by an LLM.

Analysis of Competing Hypotheses (Heuer; EMR-ACH 2026) for the research loop:

- at least two competing hypotheses (mutually exclusive when possible, the
  counter-intuitive ones flagged), one evidence matrix ``hypotheses x preuves``;
- each cell is scored ``COHERENT`` / ``INCOHERENT`` / ``NEUTRE`` (closed
  verdicts — anything else is refused);
- **refutation first** (Heuer): an hypothesis is ranked by the diagnosticity
  -weighted count of its ``INCOHERENT`` cells, never by its confirmations;
- **diagnosticity**: the variance of the verdicts of one evidence across the
  hypotheses. An evidence that says the same thing everywhere has a weight of
  ~0; an evidence that separates the hypotheses is strong;
- **next test**: :meth:`EvidenceMatrix.most_discriminating_gap` returns the
  most uncertain (hypothesis, evidence) cell — the discriminating test to buy
  next, with a deterministic textual justification;
- **reaction to change**: :meth:`EvidenceMatrix.reaction_to_change` turns a new
  verdict into a structured reaction (``retester`` / ``reviser`` / ``escalade``)
  when an evidence becomes ``INCOHERENT`` for the dominant hypothesis — a
  dominant flip is NEVER silent (it is always ``escalade``).

Invariants (pinned by ``tests/test_agents_reflexion.py``):

- deterministic: no randomness, no clock, no network, no LLM call anywhere;
- a hypothesis is never ``REFUTEE`` without at least one ``INCOHERENT`` cell;
- an empty matrix stays honest: ``to_dict`` carries the note ``"aucune preuve"``
  and :meth:`EvidenceMatrix.most_discriminating_gap` answers ``found=False``
  instead of inventing a test;
- :meth:`EvidenceMatrix.to_dict` / :meth:`EvidenceMatrix.from_dict` are
  canonical (``schema_version``, stable sorts) and round-trip exactly.

This module is derived-data-only: it never touches an LLM payload, a prompt or
a frozen output schema (the recorded responses stay replayable byte for byte).
Standard library only.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

__all__ = [
    "SCHEMA_VERSION",
    "VERDICTS",
    "COHERENT",
    "INCOHERENT",
    "NEUTRE",
    "HYPOTHESIS_STATES",
    "REACTIONS",
    "REFUTATION_BAR",
    "EvidenceMatrix",
    "sens_to_verdict",
    "matrix_from_claims",
]

#: Canonical schema of :meth:`EvidenceMatrix.to_dict`.
SCHEMA_VERSION = "orvyren/ach-matrix/v1"

#: Closed verdicts of one (hypothesis, evidence) cell.
COHERENT = "COHERENT"
INCOHERENT = "INCOHERENT"
NEUTRE = "NEUTRE"
VERDICTS: Tuple[str, ...] = (COHERENT, INCOHERENT, NEUTRE)

#: Numeric codes used by the diagnosticity variance (documented choice):
#: supporting = +1, silent = 0, refuting = -1.
_VERDICT_CODE: Mapping[str, float] = {COHERENT: 1.0, NEUTRE: 0.0, INCOHERENT: -1.0}

#: Closed hypothesis states of :meth:`EvidenceMatrix.rank_hypotheses`.
SOLIDE = "SOLIDE"
FRAGILE = "FRAGILE"
REFUTEE = "REFUTEE"
HYPOTHESIS_STATES: Tuple[str, ...] = (SOLIDE, FRAGILE, REFUTEE)

#: Closed reactions of :meth:`EvidenceMatrix.reaction_to_change`.
RETESTER = "retester"
REVISER = "reviser"
ESCALADE = "escalade"
AUCUNE = "aucune"
REACTIONS: Tuple[str, ...] = (AUCUNE, RETESTER, REVISER, ESCALADE)

#: Refutation bar: a weighted refutation score at or above this value refutes
#: the hypothesis (and a refutation ALWAYS needs at least one INCOHERENT cell).
REFUTATION_BAR = 1.0

#: Direction of one claim relative to its ``branches_concernees`` -> verdict.
#: An unknown (or missing) direction is honestly silent: NEUTRE, never a guess.
_SENS_TO_VERDICT: Mapping[str, str] = {
    "POUR": COHERENT,
    "CONTRE": INCOHERENT,
    "NEUTRE": NEUTRE,
}


def sens_to_verdict(sens: Any) -> str:
    """Map a claim ``sens`` to a matrix verdict (unknown direction -> NEUTRE)."""
    return _SENS_TO_VERDICT.get(str(sens or "").strip().upper(), NEUTRE)


class EvidenceMatrix:
    """Hypotheses x evidence ACH matrix: scoring, refutation, next test.

    All state is plain data (insertion-ordered dicts + one cell dict); every
    derived value is a pure function of it, so two matrices built from the same
    calls rank, gap and react identically forever.
    """

    def __init__(self) -> None:
        self._hypotheses: Dict[str, Dict[str, Any]] = {}
        self._evidence: Dict[str, Dict[str, Any]] = {}
        self._cells: Dict[Tuple[str, str], str] = {}

    # -- construction ------------------------------------------------------
    def add_hypothesis(self, hyp_id: str, label: str, *,
                       counter_intuitive: bool = False) -> None:
        """Register one competing hypothesis (``counter_intuitive`` is kept).

        A duplicated identifier is refused — the matrix never silently merges
        two hypotheses.
        """
        key = str(hyp_id or "").strip()
        if not key:
            raise ValueError("E_ACH_HYPOTHESIS_ID: empty id")
        if key in self._hypotheses:
            raise ValueError("E_ACH_DUPLICATE_HYPOTHESIS: %s" % key)
        self._hypotheses[key] = {"hyp_id": key, "label": str(label or ""),
                                 "counter_intuitive": bool(counter_intuitive)}

    def add_evidence(self, evidence_id: str, refs: Sequence[Any] = (),
                     weight: float = 1.0) -> None:
        """Register one evidence (a claim) with its observed references.

        ``weight`` is the prior weight of the evidence (finite, >= 0); the
        diagnostic weight is computed from the verdicts (see
        :meth:`diagnosticity`), never chosen by hand.
        """
        key = str(evidence_id or "").strip()
        if not key:
            raise ValueError("E_ACH_EVIDENCE_ID: empty id")
        if key in self._evidence:
            raise ValueError("E_ACH_DUPLICATE_EVIDENCE: %s" % key)
        try:
            value = float(weight)
        except (TypeError, ValueError):
            raise ValueError("E_ACH_WEIGHT: %r is not a number" % (weight,))
        if not math.isfinite(value) or value < 0.0:
            raise ValueError("E_ACH_WEIGHT: %r outside [0, +inf[" % (weight,))
        if isinstance(refs, (str, bytes)):
            # A bare string would be iterated character by character and
            # corrupt the provenance refs into one-character "references".
            raise ValueError("E_ACH_REFS_TYPE: %r is not a list of refs" % (refs,))
        clean_refs = tuple(str(ref).strip() for ref in (refs or ())
                           if str(ref).strip())
        self._evidence[key] = {"evidence_id": key, "refs": clean_refs,
                               "weight": value}

    def score(self, hyp_id: str, evidence_id: str, verdict: str) -> None:
        """Score one cell — closed verdicts, everything else is refused."""
        hyp = self._require_hypothesis(hyp_id)
        evidence = self._require_evidence(evidence_id)
        value = verdict if isinstance(verdict, str) else ""
        if value not in VERDICTS:
            raise ValueError("E_ACH_VERDICT: %r not in %s" % (verdict, VERDICTS))
        self._cells[(hyp, evidence)] = value

    def add_claim(self, claim: Mapping[str, Any], evidence_id: str
                  ) -> List[Dict[str, Any]]:
        """Score one accepted claim: ``branches_concernees`` x ``sens``.

        The claim becomes one evidence; every hypothesis named in
        ``branches_concernees`` receives the claim's verdict for its cell.
        Unknown branch ids are ignored (only the run's hypotheses compete — a
        claim never invents a branch). Returns the structured reactions, one
        per scored branch (see :meth:`reaction_to_change`).
        """
        # ``refs`` travels verbatim to :meth:`add_evidence`, which refuses a
        # mistyped container (a bare string must never become char refs).
        self.add_evidence(evidence_id, claim.get("refs") or ())
        verdict = sens_to_verdict(claim.get("sens"))
        branches = claim.get("branches_concernees")
        if not isinstance(branches, (list, tuple)):
            branches = ()
        reactions: List[Dict[str, Any]] = []
        seen: List[str] = []
        for branch in branches:
            hyp_id = str(branch or "").strip()
            if not hyp_id or hyp_id in seen or not self.has_hypothesis(hyp_id):
                continue
            seen.append(hyp_id)
            reactions.append(self.reaction_to_change(hyp_id, evidence_id, verdict))
        return reactions

    # -- reads -------------------------------------------------------------
    def has_hypothesis(self, hyp_id: str) -> bool:
        """True when this hypothesis competes in the matrix."""
        return str(hyp_id or "").strip() in self._hypotheses

    def hypothesis_ids(self) -> Tuple[str, ...]:
        """Every hypothesis id (registration order, immutable view)."""
        return tuple(self._hypotheses)

    def evidence_ids(self) -> Tuple[str, ...]:
        """Every evidence id (registration order, immutable view)."""
        return tuple(self._evidence)

    def scored_cells(self) -> Tuple[Tuple[str, str, str], ...]:
        """Every scored cell ``(hyp_id, evidence_id, verdict)``, stable order."""
        return tuple((hyp, evidence, self._cells[(hyp, evidence)])
                     for hyp, evidence in sorted(self._cells))

    def diagnosticity(self, evidence_id: str) -> float:
        """Diagnostic weight of one evidence: variance of its verdicts.

        Each hypothesis contributes the code of its verdict for this evidence
        (``COHERENT`` +1, ``NEUTRE`` 0, ``INCOHERENT`` -1); an unscored cell is
        honestly silent (code 0). An evidence that says the same thing to every
        hypothesis has a variance of ~0 (no discriminating power); an evidence
        that separates the hypotheses is strong. With fewer than two hypotheses
        nothing can be discriminated: 0.0.
        """
        evidence = self._require_evidence(evidence_id)
        hypotheses = list(self._hypotheses)
        if len(hypotheses) < 2:
            return 0.0
        codes = [_VERDICT_CODE[self._cells.get((hyp, evidence), NEUTRE)]
                 for hyp in hypotheses]
        mean = sum(codes) / float(len(codes))
        return sum((code - mean) ** 2 for code in codes) / float(len(codes))

    def rank_hypotheses(self) -> List[Dict[str, Any]]:
        """Refutation ranking: the least refuted hypothesis first.

        Each row carries ``score_refutation`` (the count of ``INCOHERENT``
        cells weighted by diagnosticity and evidence weight),
        ``etat`` ∈ {SOLIDE, FRAGILE, REFUTEE} and ``meilleur_rival`` (the most
        competitive alternative). Order: ``(score_refutation, hyp_id)`` — fully
        deterministic, ties broken by identifier. A hypothesis is never
        ``REFUTEE`` without at least one ``INCOHERENT`` cell.
        """
        rows: List[Dict[str, Any]] = []
        for hyp_id, hypothesis in self._hypotheses.items():
            coherent = neutre = incoherent = 0
            score = 0.0
            for evidence_id, evidence in self._evidence.items():
                verdict = self._cells.get((hyp_id, evidence_id))
                if verdict is None:
                    continue
                if verdict == COHERENT:
                    coherent += 1
                elif verdict == INCOHERENT:
                    incoherent += 1
                    score += evidence["weight"] * self.diagnosticity(evidence_id)
                else:
                    neutre += 1
            if incoherent == 0:
                etat = SOLIDE
            elif score >= REFUTATION_BAR:
                etat = REFUTEE
            else:
                etat = FRAGILE
            rows.append({"hyp_id": hyp_id, "label": hypothesis["label"],
                         "counter_intuitive": hypothesis["counter_intuitive"],
                         "nb_coherent": coherent, "nb_incoherent": incoherent,
                         "nb_neutre": neutre, "nb_preuves": coherent + incoherent + neutre,
                         "score_refutation": score, "etat": etat,
                         "meilleur_rival": ""})
        for row in rows:
            rivals = [other for other in rows if other["hyp_id"] != row["hyp_id"]]
            if rivals:
                best = min(rivals, key=lambda other: (other["score_refutation"],
                                                      other["hyp_id"]))
                row["meilleur_rival"] = best["hyp_id"]
        rows.sort(key=lambda row: (row["score_refutation"], row["hyp_id"]))
        return rows

    def most_discriminating_evidence(self) -> Dict[str, Any]:
        """The most discriminating scored claim (ties: smallest evidence id)."""
        best_id = ""
        best_key: Optional[Tuple[float, str]] = None
        for evidence_id in sorted(self._evidence):
            if not any((hyp, evidence_id) in self._cells for hyp in self._hypotheses):
                continue
            key = (-self.diagnosticity(evidence_id), evidence_id)
            if best_key is None or key < best_key:
                best_key, best_id = key, evidence_id
        if not best_id:
            return {"found": False, "evidence_id": "", "refs": [],
                    "diagnosticity": 0.0}
        return {"found": True, "evidence_id": best_id,
                "refs": list(self._evidence[best_id]["refs"]),
                "diagnosticity": self.diagnosticity(best_id)}

    def most_discriminating_gap(self) -> Dict[str, Any]:
        """The most uncertain cell = the discriminating test to buy next.

        Candidates: the unscored cells first (the verdict is unknown — the real
        gap), then the ``NEUTRE`` cells (known but uninformative). Among them,
        the cells of the dominant hypothesis or of its best rival come first,
        then the highest potential diagnosticity, then the identifiers — always
        deterministic. The justification text is deterministic too. An empty
        matrix answers honestly (``found=False`` and the note "aucune preuve").
        """
        empty = {"found": False, "hyp_id": "", "evidence_id": "", "refs": [],
                 "diagnosticity": 0.0, "kind": "", "justification": ""}
        if not self._evidence:
            empty["justification"] = ("aucune preuve — aucun test discriminant "
                                     "a acquerir")
            return empty
        if not self._hypotheses:
            empty["justification"] = ("aucune hypothese concurrente — la matrice "
                                     "n'a rien a departager")
            return empty
        unscored = [(hyp, evidence) for hyp in self._hypotheses
                    for evidence in self._evidence
                    if (hyp, evidence) not in self._cells]
        if unscored:
            candidates, kind = unscored, "sans_verdict"
        else:
            candidates = [(hyp, evidence) for hyp in self._hypotheses
                          for evidence in self._evidence
                          if self._cells[(hyp, evidence)] == NEUTRE]
            kind = "neutre"
        if not candidates:
            empty["justification"] = ("aucune cellule incertaine — la matrice "
                                     "est entierement renseignee")
            return empty
        ranking = self.rank_hypotheses()
        dominant = ranking[0]["hyp_id"]
        rival = ranking[0]["meilleur_rival"]

        def order(pair: Tuple[str, str]) -> Tuple[int, float, str, str]:
            hyp_id, evidence_id = pair
            focus = 0 if hyp_id in (dominant, rival) else 1
            return (focus, -self.diagnosticity(evidence_id), hyp_id, evidence_id)

        hyp_id, evidence_id = sorted(candidates, key=order)[0]
        refs = list(self._evidence[evidence_id]["refs"])
        word = "sans verdict" if kind == "sans_verdict" else "verdict neutre"
        justification = ("cellule %s x %s %s — prochain test discriminant a "
                         "acquerir (diagnosticite %.2f, refs: %s)"
                         % (hyp_id, evidence_id, word,
                            self.diagnosticity(evidence_id),
                            ", ".join(refs) or "-"))
        return {"found": True, "hyp_id": hyp_id, "evidence_id": evidence_id,
                "refs": refs, "diagnosticity": self.diagnosticity(evidence_id),
                "kind": kind, "justification": justification}

    def reaction_to_change(self, hyp_id: str, evidence_id: str, new_verdict: str
                           ) -> Dict[str, Any]:
        """Record one verdict change and return its structured reaction.

        The change is applied to the matrix (the function IS the change), then
        the reaction is computed — never a silent state change:

        - a flip of the dominant hypothesis is always ``escalade``;
        - ``INCOHERENT`` on the dominant hypothesis: ``escalade`` when it falls
          ``REFUTEE``, ``reviser`` when the incoherence is diagnostic and it
          falls ``FRAGILE``, ``retester`` when the incoherence discriminates
          nothing (zero diagnosticity — the evidence itself is suspect);
        - anything else is honestly ``aucune``.
        """
        hyp = self._require_hypothesis(hyp_id)
        evidence = self._require_evidence(evidence_id)
        before = self.rank_hypotheses()
        dominant_before = before[0]["hyp_id"] if before else ""
        etat_before = next((row["etat"] for row in before if row["hyp_id"] == hyp),
                           SOLIDE)
        self.score(hyp, evidence, new_verdict)
        value = self._cells[(hyp, evidence)]
        after = self.rank_hypotheses()
        dominant_after = after[0]["hyp_id"] if after else ""
        etat_after = next((row["etat"] for row in after if row["hyp_id"] == hyp),
                          SOLIDE)
        flipped = dominant_before != dominant_after
        trigger = (value == INCOHERENT and dominant_before
                   and hyp == dominant_before)
        if flipped:
            action = ESCALADE
            motif = ("bascule de l'hypothese dominante — escalade, jamais de "
                     "bascule silencieuse")
        elif trigger and etat_after == REFUTEE:
            action = ESCALADE
            motif = ("une preuve devient incoherente pour l'hypothese dominante "
                     "— elle est réfutée par la preuve, escalade")
        elif trigger and etat_after == FRAGILE and self.diagnosticity(evidence) > 0.0:
            action = REVISER
            motif = ("une preuve devient incoherente pour l'hypothese dominante "
                     "— reviser la lecture")
        elif trigger:
            action = RETESTER
            motif = ("incoherence non discriminante (diagnosticite nulle) sur "
                     "l'hypothese dominante — retester la preuve avant toute revision")
        else:
            action = AUCUNE
            motif = ("aucune reaction: la lecture dominante n'est pas menacee "
                     "par ce changement")
        return {"action": action, "hyp_id": hyp, "evidence_id": evidence,
                "new_verdict": value, "refs": list(self._evidence[evidence]["refs"]),
                "dominant_before": dominant_before,
                "dominant_after": dominant_after,
                "etat_before": etat_before, "etat_after": etat_after,
                "revision": action in (REVISER, ESCALADE), "motif": motif}

    # -- canonical serialisation ------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Canonical dict (``schema_version``, stable sorts, recomputed views)."""
        return {
            "schema_version": SCHEMA_VERSION,
            "note": "" if self._evidence else "aucune preuve",
            "hypotheses": [dict(self._hypotheses[hyp])
                           for hyp in sorted(self._hypotheses)],
            "evidence": [{"evidence_id": self._evidence[evidence]["evidence_id"],
                          "refs": list(self._evidence[evidence]["refs"]),
                          "weight": self._evidence[evidence]["weight"]}
                         for evidence in sorted(self._evidence)],
            "cells": [list(cell) for cell in self.scored_cells()],
            "diagnosticity": {evidence: self.diagnosticity(evidence)
                              for evidence in sorted(self._evidence)},
            "ranking": self.rank_hypotheses(),
            "gap": self.most_discriminating_gap(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvidenceMatrix":
        """Rebuild a matrix from its canonical dict (exact round-trip).

        The derived views (``diagnosticity``, ``ranking``, ``gap``) are
        recomputed from the cells — a tampered view can never survive a
        round-trip.
        """
        if not isinstance(data, Mapping):
            raise ValueError("E_ACH_SCHEMA: not an object")
        if str(data.get("schema_version", "")) != SCHEMA_VERSION:
            raise ValueError("E_ACH_SCHEMA: %r" % (data.get("schema_version"),))
        allowed = {"schema_version", "note", "hypotheses", "evidence", "cells",
                   "diagnosticity", "ranking", "gap"}
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise ValueError("E_ACH_SCHEMA_FIELDS: %s" % ", ".join(unknown))
        matrix = cls()
        for hypothesis in data.get("hypotheses") or ():
            if not isinstance(hypothesis, Mapping):
                raise ValueError("E_ACH_SCHEMA: hypothesis is not an object")
            matrix.add_hypothesis(str(hypothesis.get("hyp_id", "")),
                                  str(hypothesis.get("label", "")),
                                  counter_intuitive=bool(
                                      hypothesis.get("counter_intuitive", False)))
        for evidence in data.get("evidence") or ():
            if not isinstance(evidence, Mapping):
                raise ValueError("E_ACH_SCHEMA: evidence is not an object")
            matrix.add_evidence(str(evidence.get("evidence_id", "")),
                                evidence.get("refs") or (),
                                evidence.get("weight", 1.0))
        for cell in data.get("cells") or ():
            if not isinstance(cell, (list, tuple)) or len(cell) != 3:
                raise ValueError("E_ACH_SCHEMA: cell is not a (hyp, ev, verdict)")
            matrix.score(str(cell[0]), str(cell[1]), str(cell[2]))
        return matrix

    # -- internals ---------------------------------------------------------
    def _require_hypothesis(self, hyp_id: str) -> str:
        key = str(hyp_id or "").strip()
        if key not in self._hypotheses:
            raise ValueError("E_ACH_UNKNOWN_HYPOTHESIS: %r" % (hyp_id,))
        return key

    def _require_evidence(self, evidence_id: str) -> str:
        key = str(evidence_id or "").strip()
        if key not in self._evidence:
            raise ValueError("E_ACH_UNKNOWN_EVIDENCE: %r" % (evidence_id,))
        return key


def matrix_from_claims(hypotheses: Sequence[Any], claims: Sequence[Any]
                       ) -> Tuple[EvidenceMatrix, List[Dict[str, Any]]]:
    """Build + score one matrix from run hypotheses and accepted claims.

    ``hypotheses`` are the run spec objects (``id`` / ``enonce``); ``claims``
    are the accepted evaluation claims (``refs`` / ``sens`` /
    ``branches_concernees``). Evidence ids are deterministic (``EV-001`` in
    claim order). Returns the matrix and every structured reaction returned by
    :meth:`EvidenceMatrix.reaction_to_change` (claim order, branch order).
    """
    matrix = EvidenceMatrix()
    for spec in hypotheses or ():
        if not isinstance(spec, Mapping):
            continue
        hyp_id = str(spec.get("id", "") or "").strip()
        if not hyp_id:
            continue
        try:
            matrix.add_hypothesis(hyp_id, str(spec.get("enonce", "") or hyp_id),
                                  counter_intuitive=bool(
                                      spec.get("counter_intuitive", False)))
        except ValueError:
            continue  # duplicate id in the run spec — never crash the run
    reactions: List[Dict[str, Any]] = []
    for position, claim in enumerate(claims or (), start=1):
        if not isinstance(claim, Mapping):
            continue
        reactions.extend(matrix.add_claim(claim, "EV-%03d" % position))
    return matrix, reactions
