#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — the three demo intents of the execution layer (FREEZE_V1.md D10).

Three structurally identical requests, three different verdicts:

  I1  transfer 100 USDC test -> reserve    ALLOW             (nominal case)
  I2  transfer 500 USDC test -> reserve    DENY              (above the per-transaction cap)
  I3  change_policy                        REQUIRE_APPROVAL  (never autonomous)

Nothing here is signed and nothing moves: an Intent is a *request*, not a payment.
"""

from datetime import datetime, timezone

from orvyren.policy import ALLOWED_ASSET, ALLOWED_CHAIN_ID, Intent

from orvyren.execution.guard import DEFAULT_RESERVE_ADDRESS, DEFAULT_TREASURY_ADDRESS

# Demo wallets (same values as tests/test_policy.py).
TREASURY_ADDRESS = DEFAULT_TREASURY_ADDRESS  # pays (the human executes from here)
RESERVE_ADDRESS = DEFAULT_RESERVE_ADDRESS    # receives (allowlisted recipient)

# Fixed clock so a run without an explicit clock stays reproducible.
DEMO_CLOCK = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)

# Expected verdicts, pinned here as the single source of truth for demo and tests.
EXPECTED_VERDICTS = {"I1": "ALLOW", "I2": "DENY", "I3": "REQUIRE_APPROVAL"}


def build_demo_intents(now=None, reserve=RESERVE_ADDRESS):
    """Return the three demo intents [I1, I2, I3] as orvyren.policy.Intent objects."""
    created_at = now or DEMO_CLOCK
    return [
        Intent(
            intent_id="I1",
            action="transfer",
            chain_id=ALLOWED_CHAIN_ID,
            asset=ALLOWED_ASSET,
            amount=100.0,
            recipient=reserve,
            created_at=created_at,
            justification="transfer 100 USDC test to reserve",
        ),
        Intent(
            intent_id="I2",
            action="transfer",
            chain_id=ALLOWED_CHAIN_ID,
            asset=ALLOWED_ASSET,
            amount=500.0,
            recipient=reserve,
            created_at=created_at,
            justification="transfer 500 USDC test to reserve",
        ),
        Intent(
            intent_id="I3",
            action="change_policy",
            chain_id=ALLOWED_CHAIN_ID,
            asset=ALLOWED_ASSET,
            # A policy change moves no funds: the amount field only satisfies the
            # policy's structural rule R4 (amount > 0) so that the request reaches
            # the R8 action check instead of failing on shape.
            amount=100.0,
            recipient=reserve,
            created_at=created_at,
            justification="change the policy: raise the per-transaction cap; requires human approval",
        ),
    ]
