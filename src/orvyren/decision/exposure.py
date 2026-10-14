#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core - demonstration exposure parameters (decision/exposure.py).

Scope: the decision engine needs a bounded notion of "how much exposure could
still be moved while keeping a reserve floor". This module holds the three
demonstration parameters fixed with the team (FREEZE_V1.md D8) and one pure
function that answers the only question the engine asks.

These are DOCUMENTATION-LEVEL DEMONSTRATION PARAMETERS, not a real portfolio:
no wallet, no bank balance, no market impact and no counterparty are modelled.
The 100 USDC action size comes from the frozen decision D8 of FREEZE_V1.md
("Transfert de 100 USDC de test ... du wallet « tresorerie » vers le wallet
« reserve »").
"""

from dataclasses import dataclass

# --- demonstration parameters (not a real portfolio) ------------------------
EXPOSURE_USDC = 500.0   # total USDC exposure of the demonstration treasury
FLOOR_USDC = 350.0      # reserve floor that must never be crossed
ACTION_USDC = 100.0     # bounded demonstration action size (FREEZE_V1.md D8)

# Default note shipped in every serialised exposure envelope, so that no
# consumer can mistake these numbers for a real position.
DEMO_NOTE = (
    "demonstration parameters only: no real wallet, no real balance, "
    "no market impact modelled"
)


def available_to_move(exposure, floor, desired):
    """Pure function: how much can be moved without crossing the floor.

    Returns ``max(0.0, min(desired, exposure - floor))`` -- the amount is
    capped both by what remains above the floor and by the desired action
    size. Never returns a negative number: an exposure already below the
    floor yields 0.0, never a forced move.
    """
    return max(0.0, min(desired, exposure - floor))


@dataclass(frozen=True)
class Exposure:
    """Demonstration exposure envelope used by the decision engine.

    Holds the three frozen demonstration parameters and exposes the same
    availability rule as :func:`available_to_move`. This is a documentation
    object: it represents a fictitious treasury of 500 USDC with a 350 USDC
    floor, where the registered bounded action is 100 USDC. It is NOT a real
    portfolio and carries no wallet, key or balance.
    """

    exposure_usdc: float = EXPOSURE_USDC
    floor_usdc: float = FLOOR_USDC
    action_usdc: float = ACTION_USDC
    note: str = DEMO_NOTE

    def available_to_move(self, desired=None):
        """Amount movable right now (defaults to the registered action size)."""
        target = self.action_usdc if desired is None else desired
        return available_to_move(self.exposure_usdc, self.floor_usdc, target)

    def as_dict(self):
        """JSON-serialisable view, including the computed availability."""
        return {
            "exposure_usdc": self.exposure_usdc,
            "floor_usdc": self.floor_usdc,
            "action_usdc": self.action_usdc,
            "available_to_move_usdc": self.available_to_move(),
            "note": self.note,
        }
