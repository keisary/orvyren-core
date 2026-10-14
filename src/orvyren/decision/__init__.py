#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core - decision engine package (see ARCHITECTURE_V1.md section 2).

Modules:
  exposure.py   demonstration exposure envelope and the pure availability function
  scenarios.py  pre-registered H1/H2/H3 classification over the frozen corpus
  engine.py     decision engine: candidate action, NO-ACTION or INCONCLUSIVE
  baseline.py   baseline A0: fixed aggregator-threshold rule (the adversary)

All reasoning is stdlib-only, deterministic and replayable offline:
  python run_decision.py
"""

from orvyren.decision.exposure import (
    ACTION_USDC,
    EXPOSURE_USDC,
    FLOOR_USDC,
    Exposure,
    available_to_move,
)
from orvyren.decision.scenarios import (
    Observation,
    classify_hypotheses,
    load_observations,
)
from orvyren.decision.engine import run_case
from orvyren.decision.baseline import run_baseline

__all__ = [
    "ACTION_USDC",
    "EXPOSURE_USDC",
    "FLOOR_USDC",
    "Exposure",
    "available_to_move",
    "Observation",
    "classify_hypotheses",
    "load_observations",
    "run_case",
    "run_baseline",
]
