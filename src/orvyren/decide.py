#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — « une décision complète est une commande » (W3 [DONE]).

    # depuis la racine du dépôt :
    PYTHONPATH=src python -m orvyren.decide --case usdc-2023-03 --replay
    # ou, depuis src/ :
    cd src && python -m orvyren.decide --case usdc-2023-03 --replay

Compose la chaîne complète, hors-ligne et déterministe :
corpus gelé -> moteur v0 (``run_case``) -> dossier 3 axes (``build_dossier`` :
RDOF v1 + abstention A1-A5 + convention de prix + politique) ->
enregistrement des hypothèses falsifiables au registre de W2 (L3.1) ->
**DecisionRecord** JSON :

- 3 axes **séparés** : ``epistemic_verdict`` / ``economic_action`` /
  ``authorization_verdict`` (jamais fusionnés — « DENY de politique » !=
  « échec épistémique », DOC2 §5.4.4) ;
- ``intent`` borné (action, chaîne, actif, montant, destinataire) ou
  ``NO-ACTION`` / ``INCONCLUSIVE`` ;
- ``rationale``, ``evidence_refs[]``, coût réel de recherche.

Sortie : ``evidence/decision_record_<case>.json`` (ou ``--out``). Le dossier
machine ``evidence/decision_<case>.json`` reste produit par ``run_decision.py``.

Standard library only, aucun réseau.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":  # pragma: no cover — invocation directe du fichier
    sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))

from orvyren.branches.hypotheses import HypothesisRegistry  # noqa: E402
from orvyren.decision.axes import build_dossier  # noqa: E402
from orvyren.decision.engine import run_case  # noqa: E402
from orvyren.decision.predicates import BY_ID  # noqa: E402
from orvyren.decision.rdof import FROZEN_HYPOTHESIS_ORDER  # noqa: E402
from orvyren.decision.records import register_case_hypotheses  # noqa: E402
from orvyren.decision.scenarios import load_observations  # noqa: E402

SCHEMA = "orvyren-decision-record/v1"

DEFAULT_CASE = "usdc-2023-03"
DEFAULT_CORPUS = "corpus/usdc_observations.csv"
DEFAULT_OUT_DIR = "evidence"

#: Fenêtre principale gelée du cas (FREEZE_V1 D1), bornes incluses, UTC.
MAIN_WINDOW = ("2023-03-09T00:00:00+00:00", "2023-03-15T00:00:00+00:00")

#: L'action économique qui produit un Intent borné (axes.build_dossier).
ECONOMIC_TRANSFER = "CONVERTIR/TRANSFÉRER"


def _dedupe_refs(refs):
    """Stable de-duplication of provenance references (timestamp, venue, value)."""
    seen, unique = set(), []
    for ref in refs:
        key = (ref.get("timestamp_utc"), ref.get("venue"), ref.get("value"))
        if key not in seen:
            seen.add(key)
            unique.append(ref)
    return unique


def build_decision_record(case_id: str = DEFAULT_CASE, corpus_path: str = None,
                          reserve_recipient: str = None) -> dict:
    """Run the full decision chain and return the DecisionRecord payload.

    Deterministic: identical corpus + identical window -> byte-identical
    serialisation (no wall-clock, no random — the registry registration date
    is the case's freeze date).
    """
    corpus_abs = corpus_path or DEFAULT_CORPUS
    if not os.path.isabs(corpus_abs):
        corpus_abs = os.path.normpath(os.path.join(_REPO_ROOT, corpus_abs))
    if not os.path.exists(corpus_abs):
        raise FileNotFoundError("corpus introuvable : %s" % corpus_abs)

    case = run_case(corpus_abs, MAIN_WINDOW[0], MAIN_WINDOW[1],
                    case_id=case_id, window_label="main")
    observations = load_observations(corpus_abs)
    dossier = build_dossier(case_id, observations, MAIN_WINDOW[0], MAIN_WINDOW[1],
                            reserve_recipient=reserve_recipient)

    # L3.1 — enregistrement des hypothèses falsifiables au registre de W2
    # (critères S/R obligatoires ; prédicats instrumentés uniquement).
    registry = HypothesisRegistry()
    registered = register_case_hypotheses(registry, case_id,
                                          case["hypothesis_verdicts"],
                                          tuple(BY_ID))

    verdicts = case["hypothesis_verdicts"]
    axes = dossier["axes"]
    rdof = dossier["rdof"]

    # L'intent borné — la seule structure qui franchit decision -> policy ([I]).
    intent = None
    if axes["economic_action"] == ECONOMIC_TRANSFER:
        from orvyren.policy import ALLOWED_ASSET, ALLOWED_CHAIN_ID
        intent = {
            "intent_id": "intent-%s-a-d1" % case_id,
            "action": "transfer",
            "chain_id": ALLOWED_CHAIN_ID,
            "asset": ALLOWED_ASSET,
            "amount": axes["x_star_usdc"],
            "recipient": reserve_recipient or "",
        }

    rationale_parts = [
        "verdicts : " + ", ".join("%s %s" % (hid, verdicts[hid]["verdict"])
                                  for hid in FROZEN_HYPOTHESIS_ORDER),
        "RDOF : arrêt « %s » après %d recherche(s), coût %s s / %s appel(s)" % (
            rdof["stop"], len(rdof["trace"]),
            rdof["budget"]["consomme"]["secondes"],
            rdof["budget"]["consomme"]["appels"]),
    ]
    if axes["economic_action"]:
        rationale_parts.append("action : %s (catalogue %s)"
                               % (axes["economic_action"],
                                  dossier["action_catalog_version"]))
    if dossier["abstention"]:
        rationale_parts.append("abstention : conditions %s"
                               % ",".join(dossier["abstention"]["conditions_declenchees"]))

    evidence_refs = _dedupe_refs(
        [ref for hid in FROZEN_HYPOTHESIS_ORDER
         for ref in verdicts[hid].get("evidence_refs", ())])

    return {
        "schema": SCHEMA,
        "case": case_id,
        "mode": "replay",
        "epistemic_verdict": axes["epistemic_verdict"],
        "economic_action": axes["economic_action"],
        "authorization_verdict": axes["authorization_verdict"],
        "intent": intent,
        "rationale": " ; ".join(rationale_parts),
        "evidence_refs": evidence_refs,
        "research_cost": {
            "budget": rdof["budget"],
            "arret": rdof["stop"],
            "arret_regle": rdof["stop_rule"],
        },
        "axes": axes,
        "rdof": rdof,
        "abstention": dossier["abstention"],
        "catalog_version": dossier["action_catalog_version"],
        "price_convention": dossier["price_convention"],
        "hypotheses_registry": {
            "count": len(registered),
            "ids": [record.id for record in registered],
            "etats": sorted({record.etat for record in registered}),
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m orvyren.decide",
        description="ORVYREN-Core — décision complète en une commande "
                    "(3 axes séparés, RDOF v1, abstention A1-A5) — offline, "
                    "stdlib, rejouable.")
    parser.add_argument("--case", default=DEFAULT_CASE,
                        help="identifiant de cas (défaut : %(default)s)")
    parser.add_argument("--replay", action="store_true",
                        help="rejoue le cas gelé depuis le corpus figé "
                             "(offline, déterministe — le seul mode v1)")
    parser.add_argument("--corpus", default=DEFAULT_CORPUS,
                        help="corpus CSV, relatif à la racine du dépôt "
                             "(défaut : %(default)s)")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR,
                        help="répertoire de sortie (défaut : %(default)s)")
    parser.add_argument("--out", default=None,
                        help="chemin de sortie explicite (sinon "
                             "decision_record_<case>.json)")
    parser.add_argument("--reserve-recipient", default=None,
                        help="adresse du destinataire de réserve pour évaluer "
                             "l'axe 3 via le service de politique ; omis, l'axe "
                             "reste explicitement « non évalué »")
    args = parser.parse_args(argv)

    if args.case != DEFAULT_CASE:
        print("ERREUR : cas non câblé en v1 : %s (seul %s est rejouable)"
              % (args.case, DEFAULT_CASE), file=sys.stderr)
        return 4

    corpus_abs = args.corpus
    if not os.path.isabs(corpus_abs):
        corpus_abs = os.path.normpath(os.path.join(_REPO_ROOT, corpus_abs))
    if not os.path.exists(corpus_abs):
        print("ERREUR : corpus introuvable : %s" % corpus_abs, file=sys.stderr)
        return 2

    record = build_decision_record(args.case, corpus_abs, args.reserve_recipient)

    out_dir = args.out_dir
    if not os.path.isabs(out_dir):
        out_dir = os.path.normpath(os.path.join(_REPO_ROOT, out_dir))
    os.makedirs(out_dir, exist_ok=True)
    out_path = args.out or os.path.join(out_dir, "decision_record_%s.json" % args.case)
    with open(out_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print("ORVYREN — décision (replay) : %s" % args.case)
    print("  epistemic_verdict    : %s" % record["epistemic_verdict"])
    print("  economic_action      : %s" % record["economic_action"])
    print("  authorization_verdict: %s" % record["authorization_verdict"])
    print("  intent               : %s" % (json.dumps(record["intent"], ensure_ascii=False)
                                           if record["intent"] else "aucun"))
    print("  rationale            : %s" % record["rationale"])
    print("  écrit                : %s" % out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
