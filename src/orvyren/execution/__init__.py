"""ORVYREN-Core — execution layer (guard, JSON-RPC client, receipt verification, demo intents).

The execution layer never holds a key: it enforces an ALLOW verdict, emits an
*unsigned* instruction for a human to execute in their own wallet, and verifies
the resulting on-chain receipt in read-only mode.
"""

from orvyren.execution import chain, intents, verify  # noqa: F401
from orvyren.execution.guard import (  # noqa: F401
    DEFAULT_RESERVE_ADDRESS,
    DEFAULT_RPC_URL,
    DEFAULT_TREASURY_ADDRESS,
    ConfigurationError,
    ExecutionConfig,
    PolicyViolationError,
    assert_allowed,
    execution_allowed,
)

__all__ = [
    "chain",
    "intents",
    "verify",
    "ConfigurationError",
    "ExecutionConfig",
    "PolicyViolationError",
    "assert_allowed",
    "execution_allowed",
    "DEFAULT_RESERVE_ADDRESS",
    "DEFAULT_RPC_URL",
    "DEFAULT_TREASURY_ADDRESS",
]
