#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — evaluation layer: the `orvyren.evaluation` package (Sprint 0).

Contents (standard library only, offline):

* :mod:`orvyren.evaluation.loss` — "wealth + feasible actions" loss function
  (G1), valuation conventions, DAO/desk persona variants;
* :mod:`orvyren.evaluation.comparators` — comparators A0, A1, AX0, B0, O (G2);
* :mod:`orvyren.evaluation.calibration` — C1–C7: Brier, Murphy, ECE, Wilson,
  block bootstrap (deterministic), skill, exact McNemar (G5);
* :mod:`orvyren.evaluation.windows` — DEV/EVAL window registry (G3),
  embargo checkers and freeze gate;
* :mod:`orvyren.evaluation.forecasts` — frozen, hashed and chained forecasts;
* :mod:`orvyren.evaluation.outcomes` — deterministic resolver and chained
  outcomes (rule ``sustained_depeg_v1``, ``resolve_not_before`` guard).

Every figure produced by this package is computed or refused — never invented:
missing data raises an explicit exception or produces ``None`` plus a reason.
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
