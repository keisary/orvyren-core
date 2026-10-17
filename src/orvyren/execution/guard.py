#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — execution guard: environment configuration and verdict enforcement.

This layer never holds a signing key. It reads public configuration from the
environment, refuses to proceed unless the policy verdict is ALLOW, and masks
every sensitive value (RPC endpoints that may embed an API key, signer
variables) so that no secret can ever be printed or logged.

Design (FREEZE_V1.md D9/D10):
  * the deterministic policy engine (orvyren.policy) decides; this module only
    carries the decision and blocks anything that is not ALLOW;
  * on an ALLOW verdict the agent produces an *unsigned* instruction that a
    human executes in their own wallet — no key ever reaches this process;
  * sensitive environment variable names are reported by NAME only, their
    values are never read into memory nor emitted anywhere.
"""

import math
import os
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from orvyren.policy import MAX_CUMULATIVE, MAX_PER_TX, PERMISSION_TTL

# Demo wallets (same values as tests/test_policy.py): the treasury pays, the reserve receives.
DEFAULT_TREASURY_ADDRESS = "0x2222222222222222222222222222222222222222"
DEFAULT_RESERVE_ADDRESS = "0x1111111111111111111111111111111111111111"
DEFAULT_RPC_URL = "https://sepolia.base.org"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_TTL_HOURS = int(PERMISSION_TTL.total_seconds() // 3600)  # 24

MASK = "***"

# Variable names that may carry key material: detected by NAME only, never read
# into memory and never emitted anywhere.
SENSITIVE_ENV_NAMES = (
    "ORVYREN_PRIVATE_KEY",
    "ORVYREN_SIGNER_KEY",
    "ORVYREN_SIGNER_KEYFILE",
    "ORVYREN_MNEMONIC",
    "ORVYREN_SEED",
    "PRIVATE_KEY",
    "MNEMONIC",
)

_TRUTHY = {"1", "true", "yes", "on"}


class ConfigurationError(Exception):
    """Raised when an environment value cannot be parsed into a usable configuration."""


class PolicyViolationError(Exception):
    """Raised when execution is attempted on a policy verdict other than ALLOW."""

    def __init__(self, verdict, reasons=()):
        self.verdict = verdict
        self.reasons = list(reasons or [])
        if self.verdict == "REQUIRE_APPROVAL":
            detail = "a human approval is required before this instruction may be prepared"
        else:
            detail = "the instruction is refused"
        message = "execution blocked: policy verdict {!r} — {}".format(self.verdict, detail)
        if self.reasons:
            message += " (reason codes: {})".format(", ".join(str(r) for r in self.reasons))
        super().__init__(message)


# --- masking helpers: no secret value ever leaves this module -----------------

def mask_secret(value):
    """Return a fixed mask for any non-empty secret; nothing of the value leaks."""
    return MASK if value else ""


def mask_rpc_url(url):
    """Mask credential-bearing parts of an RPC URL while keeping the host readable.

    https://sepolia.base.org                      -> unchanged (public endpoint)
    https://base-sepolia.g.alchemy.com/v2/<KEY>   -> https://base-sepolia.g.alchemy.com/v2/***
    https://rpc.example.com/<KEY>                 -> https://rpc.example.com/***
    """
    if not url:
        return ""
    try:
        parsed = urlsplit(url)
        if not parsed.scheme or not parsed.hostname:
            return MASK  # unparseable: mask everything
        netloc = parsed.hostname
        if parsed.port:
            netloc += ":{}".format(parsed.port)
        if parsed.username or parsed.password:
            netloc = "{}@{}".format(MASK, netloc)  # user:password@host
        segments = [segment for segment in (parsed.path or "").split("/") if segment]
    except ValueError:
        # Malformed URL (bad port, broken IPv6 bracket, ...): this helper runs
        # inside error paths and must never raise nor leak — mask everything.
        return MASK
    if not segments:
        return "{}://{}".format(parsed.scheme, netloc)
    # Deny-by-default on path segments: only version-like tokens (v2, v3, ...)
    # are kept visible, every other segment is masked. The previous behaviour
    # ("keep the first segment") leaked credentials placed at the front of the
    # path: https://rpc.example/CANARY_SECRET/v1 printed CANARY_SECRET (F08).
    shown = [segment if re.fullmatch(r"v\d+", segment) else MASK
             for segment in segments]
    return "{}://{}/{}".format(parsed.scheme, netloc, "/".join(shown))


def present_secret_env_names(env=None):
    """Names (never values) of sensitive variables present in the environment."""
    env = os.environ if env is None else env
    return tuple(sorted(name for name in SENSITIVE_ENV_NAMES if str(env.get(name) or "").strip()))


# --- configuration -----------------------------------------------------------

def _is_address(value):
    if not isinstance(value, str):
        return False
    text = value.strip()
    if len(text) != 42 or not text.startswith("0x"):
        return False
    return all(c in "0123456789abcdefABCDEF" for c in text[2:])


def _number(env, name, default, cast):
    raw = env.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        if cast is int:
            return int(str(raw).strip(), 10)
        value = cast(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise ConfigurationError("invalid {} {!r}: expected a number".format(name, raw)) from exc
    if not math.isfinite(value):
        raise ConfigurationError("invalid {} {!r}: expected a finite number".format(name, raw))
    return value


@dataclass(frozen=True, repr=False)
class ExecutionConfig:
    """Execution-layer configuration, read from the environment with safe defaults.

    dry_run defaults to True and is informational: this layer contains no code
    path that signs or broadcasts anything, with or without a key.
    """

    rpc_url: str = DEFAULT_RPC_URL
    treasury_address: str = DEFAULT_TREASURY_ADDRESS
    reserve_address: str = DEFAULT_RESERVE_ADDRESS
    max_per_tx: float = float(MAX_PER_TX)
    max_cumulative: float = float(MAX_CUMULATIVE)
    permission_ttl_hours: int = DEFAULT_TTL_HOURS
    dry_run: bool = True
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    secret_env_names_present: tuple = ()

    @classmethod
    def from_env(cls, env=None):
        """Build the configuration from environment variables, with defaults."""
        env = os.environ if env is None else env

        rpc_url = str(env.get("ORVYREN_RPC_URL_BASE_SEPOLIA") or DEFAULT_RPC_URL).strip()
        treasury = str(env.get("ORVYREN_TREASURY_ADDRESS") or DEFAULT_TREASURY_ADDRESS).strip()
        reserve = str(env.get("ORVYREN_RESERVE_ADDRESS") or DEFAULT_RESERVE_ADDRESS).strip()
        if not _is_address(treasury):
            raise ConfigurationError(
                "invalid ORVYREN_TREASURY_ADDRESS {!r}: expected a 0x-prefixed 20-byte address".format(treasury))
        if not _is_address(reserve):
            raise ConfigurationError(
                "invalid ORVYREN_RESERVE_ADDRESS {!r}: expected a 0x-prefixed 20-byte address".format(reserve))

        max_per_tx = _number(env, "ORVYREN_MAX_PER_TX", float(MAX_PER_TX), float)
        max_cumulative = _number(env, "ORVYREN_MAX_CUMULATIVE", float(MAX_CUMULATIVE), float)
        ttl_hours = _number(env, "ORVYREN_PERMISSION_TTL_HOURS", DEFAULT_TTL_HOURS, int)
        timeout_seconds = _number(env, "ORVYREN_RPC_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS, int)

        if max_per_tx <= 0:
            raise ConfigurationError("ORVYREN_MAX_PER_TX must be > 0, got {}".format(max_per_tx))
        if max_cumulative <= 0:
            raise ConfigurationError("ORVYREN_MAX_CUMULATIVE must be > 0, got {}".format(max_cumulative))
        if ttl_hours <= 0:
            raise ConfigurationError("ORVYREN_PERMISSION_TTL_HOURS must be > 0, got {}".format(ttl_hours))
        if timeout_seconds <= 0:
            raise ConfigurationError("ORVYREN_RPC_TIMEOUT_SECONDS must be > 0, got {}".format(timeout_seconds))

        dry_raw = str(env.get("ORVYREN_DRY_RUN", "")).strip().lower()
        dry_run = True if dry_raw == "" else dry_raw in _TRUTHY

        return cls(
            rpc_url=rpc_url,
            treasury_address=treasury,
            reserve_address=reserve,
            max_per_tx=max_per_tx,
            max_cumulative=max_cumulative,
            permission_ttl_hours=ttl_hours,
            dry_run=dry_run,
            timeout_seconds=timeout_seconds,
            secret_env_names_present=present_secret_env_names(env),
        )

    def safe_dict(self):
        """JSON/log-safe view: the RPC URL is masked and no secret is ever included."""
        return {
            "rpc_url_masked": mask_rpc_url(self.rpc_url),
            "treasury_address": self.treasury_address,
            "reserve_address": self.reserve_address,
            "max_per_tx": self.max_per_tx,
            "max_cumulative": self.max_cumulative,
            "permission_ttl_hours": self.permission_ttl_hours,
            "dry_run": self.dry_run,
            "timeout_seconds": self.timeout_seconds,
            "secret_env_vars_present": list(self.secret_env_names_present),
            "agent_holds_key": False,
        }

    def __repr__(self):
        return "ExecutionConfig({})".format(self.safe_dict())


# --- verdict enforcement ------------------------------------------------------

def execution_allowed(decision):
    """True only for an explicit ALLOW verdict."""
    return getattr(decision, "verdict", None) == "ALLOW"


def assert_allowed(decision):
    """Return the decision if its verdict is ALLOW; raise PolicyViolationError otherwise."""
    if not execution_allowed(decision):
        verdict = getattr(decision, "verdict", "UNKNOWN")
        reasons = list(getattr(decision, "reasons", []) or [])
        raise PolicyViolationError(verdict, reasons)
    return decision
