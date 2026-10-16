#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — couche d'évaluation : paquet `orvyren.evaluation` (Sprint 0).

Contenu (bibliothèque standard uniquement, hors-ligne) :

* :mod:`orvyren.evaluation.loss` — fonction de perte « richesse + actions
  faisables » (G1), conventions de valorisation, variantes persona DAO/desk ;
* :mod:`orvyren.evaluation.comparators` — comparateurs A0, A1, AX0, B0, O (G2) ;
* :mod:`orvyren.evaluation.calibration` — C1–C7 : Brier, Murphy, ECE, Wilson,
  bootstrap par blocs (déterministe), compétence, McNemar exact (G5) ;
* :mod:`orvyren.evaluation.windows` — registre des fenêtres DEV/EVAL (G3),
  vérificateurs d'embargo et porte de gel ;
* :mod:`orvyren.evaluation.forecasts` — prévisions gelées hachées et chaînées ;
* :mod:`orvyren.evaluation.outcomes` — résolveur déterministe et outcomes
  chaînés (règle ``sustained_depeg_v1``, garde ``resolve_not_before``).

Tout chiffre produit par ce paquet est calculé ou refusé — jamais inventé :
une donnée absente lève une exception explicite ou produit ``None`` + un motif.
"""

from __future__ import annotations

from orvyren.evaluation import calibration, comparators, forecasts  # noqa: F401
from orvyren.evaluation import loss, outcomes, windows  # noqa: F401

__all__ = [
    "calibration",
    "comparators",
    "forecasts",
    "loss",
    "outcomes",
    "windows",
]
