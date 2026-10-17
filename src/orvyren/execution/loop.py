#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — bounded autonomous executor: TICK -> decision -> policy -> journal.

One single loop, off-LLM, that finally connects the three stages of the repository:

1. **decision** — ``orvyren.decide.build_decision_record`` (replay of the frozen
   corpus, ``reserve_recipient`` supplied) produces a ``DecisionRecord`` whose
   ``intent`` is the only structure that crosses the boundary;
2. **policy** — ``orvyren.policy.evaluate`` with a real ``PolicyState``:
   pause/kill switch (P11), balance (P7), envelope (P12), budget (P14) are
   never ``SKIPPED`` again on this path; the 24 h cumulative (P6) comes from a
   **persistent ledger** and idempotency (P10) from already-seen identifiers;
3. **execution** — dry-run by default (no signature, no key read);
   ``--execute`` **lazily** imports the isolated signer
   (``scripts/demo/signer.py``), signs, broadcasts, then verifies the receipt with
   the existing verifier (``orvyren.execution.verify.verify_receipt``).
   Any missing key/dependency is a refusal *before* the first tick.

Invariants:

* **fail-closed**: an unreadable state (pause, balance, envelope) is a refusal,
  never a "we assume"; an unreadable ledger stops the run;
* **kill switch re-checked on every tick**: ``ORVYREN_K0_PAUSED`` (or the
  ``ORVYREN_K0_PAUSE_FLAG`` file) is re-read before every evaluation; a
  pause produces a journaled refusal, never a crash;
* **chained journal** JSONL (``prev_hash`` / ``record_hash``) append-only;
* **24 h ledger** JSON written atomically (temporary file +
  ``os.replace``, ``newline="\\n"``): every ALLOW adds
  ``(ts, intent_id, amount)``, a DENY consumes nothing;
* no secret is read or journaled (the signer only outputs the address and
  the hash; the key never leaves its environment).

Standard library only. The ``scripts/`` modules are imported only when
``--execute`` requires them (never for the dry-run, never at top-level).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from orvyren.execution import chain as chain_client
from orvyren.execution.guard import DEFAULT_RESERVE_ADDRESS
from orvyren.execution.verify import value_to_base_units, verify_receipt
from orvyren.policy import (
    ALLOWED_CHAIN_ID,
    Intent,
    PolicyBundle,
    PolicyState,
    evaluate,
    load_policy,
)
from orvyren.policy.miniyaml import MiniYamlError

# --- constants ---------------------------------------------------------------

SCHEMA_LEDGER = "orvyren-executor-ledger/v1"
SCHEMA_JOURNAL = "orvyren-executor-journal/v1"
SCHEMA_RUN = "orvyren-executor-run/v1"

GENESIS_HASH = "0" * 64
LEDGER_WINDOW = timedelta(hours=24)
DEFAULT_AVAILABLE_BALANCE = 1000.0          # test USDC — DEMONSTRATION balance
DEFAULT_TICKS = 1
DEFAULT_INTERVAL_S = 0.0
DEFAULT_RECEIPT_TIMEOUT = 180

#: Envelope statuses (P12) — taken from ``orvyren.policy``.
ENVELOPE_PASS = "PASS"
ENVELOPE_DRIFT = "DRIFT"
ENVELOPE_UNVERIFIED = "UNVERIFIED"

FIXTURE_SCHEMA = "orvyren-roles-agent-config/v1"

#: Real-execution failure (missing key or dependency) — never a bare crash.
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PAUSED = 3
EXIT_EXECUTE = 4
EXIT_RUNTIME = 5

#: Denial code added by the executor (outside the policy registry) when
#: ``--max-usd`` is exceeded: fail-closed denial, no ledger consumption.
TICK_BUDGET_CODE = "TICK_BUDGET_EXCEEDED"
NO_INTENT_CODE = "NO_ACTIONABLE_INTENT"


class LedgerError(Exception):
    """Unreadable or inconsistent ledger — the run stops (fail-closed)."""


class JournalError(Exception):
    """Unreadable journal or broken chain — the run stops (fail-closed)."""


class PolicyLoadError(Exception):
    """``policy_v1.yaml`` missing or invalid."""


class RecipientError(Exception):
    """Recipient missing, malformed or outside the allowlist."""


class ExecuteUnavailable(Exception):
    """``--execute`` requested without a key or without the signing library."""


# --- utilities ---------------------------------------------------------------

def utcnow() -> datetime:
    """Default clock: UTC, aware."""
    return datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    """ISO-8601 UTC timestamp at microsecond precision (stable lexicographic sort)."""
    if moment.tzinfo is None:
        # Same documented choice as parse_iso(): naive means UTC, never the
        # local timezone (astimezone on a naive datetime would localise it).
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat(timespec="microseconds")


def parse_iso(text: Any) -> datetime:
    """Parse an ISO-8601 timestamp; naive = UTC (documented choice)."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("missing timestamp")
    moment = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def canonical_json(payload: Any) -> str:
    """Canonical serialization (sorted keys, fixed separators, UTF-8)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def parse_bool(value: Any) -> Optional[bool]:
    """True/False for a readable value, ``None`` otherwise (P11 fail-closed)."""
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "paused"}:
        return True
    if text in {"0", "false", "no", "off", "active"}:
        return False
    return None


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _env(env: Optional[Mapping[str, str]]) -> Mapping[str, str]:
    return os.environ if env is None else env


def _normalize_address(value: str, context: str = "recipient") -> str:
    """0x + 40 hex address, lower-cased; never repaired (denial if invalid)."""
    try:
        return chain_client.normalize_address(value, context)
    except chain_client.ChainError as exc:
        raise RecipientError(str(exc)) from exc


def safe_case(case: str) -> str:
    """Safe path fragment for a case identifier."""
    cleaned = "".join(ch if (ch.isalnum() or ch in "._-") else "_" for ch in str(case or ""))
    return cleaned or "case"


# --- persistent 24 h ledger --------------------------------------------------

@dataclass(frozen=True)
class LedgerEntry:
    """One authorized consumption: (timestamp, intent identifier, amount)."""

    ts_utc: str
    intent_id: str
    amount: float

    def when(self) -> datetime:
        return parse_iso(self.ts_utc)

    def as_dict(self) -> Dict[str, Any]:
        return {"ts_utc": self.ts_utc, "intent_id": self.intent_id, "amount": self.amount}


def _atomic_write_json(path: str, payload: Any) -> None:
    """Atomic write: temporary file in the same directory then ``os.replace``."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    handle_fd, tmp_path = tempfile.mkstemp(prefix=".orvyren-ledger-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(handle_fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


class PeriodLedger:
    """Persistent JSON ledger of consumptions over a rolling 24 h window.

    ``path=None``: in-memory ledger (demo/tests). An existing ledger is
    re-read **at construction**: two successive processes therefore share the
    same cumulative (P6) and the same seen identifiers (P10).
    """

    def __init__(self, path: Optional[str] = None, window: timedelta = LEDGER_WINDOW):
        self.path = path
        self.window = window
        self._entries: List[LedgerEntry] = []
        if path and os.path.exists(path):
            self._load()

    # -- read -----------------------------------------------------------
    def entries(self) -> Tuple[LedgerEntry, ...]:
        return tuple(self._entries)

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                raw = handle.read()
        except OSError as exc:
            raise LedgerError("ledger unreadable: {} ({})".format(self.path, exc)) from exc
        if not raw.strip():
            return
        try:
            payload = json.loads(raw)
        except ValueError as exc:
            raise LedgerError("ledger: invalid JSON: {} ({})".format(self.path, exc)) from exc
        if not isinstance(payload, dict):
            raise LedgerError("ledger: JSON object expected ({})".format(self.path))
        entries = payload.get("entries")
        if entries is None:
            entries = []
        if not isinstance(entries, list):
            raise LedgerError("ledger: 'entries' must be a list ({})".format(self.path))
        loaded: List[LedgerEntry] = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise LedgerError("ledger: entry #{} is not an object".format(index))
            intent_id = entry.get("intent_id")
            amount = entry.get("amount")
            ts_utc = entry.get("ts_utc")
            if not isinstance(intent_id, str) or not intent_id.strip():
                raise LedgerError("ledger: entry #{} without intent_id".format(index))
            if not _finite_number(amount) or amount < 0:
                raise LedgerError("ledger: entry #{} amount unreadable".format(index))
            try:
                parse_iso(ts_utc)
            except (TypeError, ValueError) as exc:
                raise LedgerError("ledger: entry #{} timestamp unreadable".format(index)) from exc
            loaded.append(LedgerEntry(str(ts_utc), intent_id, float(amount)))
        self._entries = loaded

    def spent(self, now: datetime) -> float:
        """Sum of the amounts in the rolling window (future entries included)."""
        threshold = now - self.window
        total = 0.0
        for entry in self._entries:
            if entry.when() >= threshold:
                total += entry.amount
        return total

    def calls(self, now: datetime) -> int:
        """Number of consumptions in the window (call quota, informational)."""
        threshold = now - self.window
        return sum(1 for entry in self._entries if entry.when() >= threshold)

    def seen_intent_ids(self) -> frozenset:
        """Every identifier already consumed — including outside the window (P10)."""
        return frozenset(entry.intent_id for entry in self._entries)

    # -- write ----------------------------------------------------------
    def record(self, now: datetime, intent_id: str, amount: float) -> LedgerEntry:
        """Add an authorized consumption then persist it (atomic)."""
        if not isinstance(intent_id, str) or not intent_id.strip():
            raise LedgerError("consumption refused: empty intent_id")
        if not _finite_number(amount) or amount < 0:
            raise LedgerError("consumption refused: unreadable amount")
        entry = LedgerEntry(_iso(now), intent_id, float(amount))
        self._entries.append(entry)
        try:
            self.save()
        except BaseException:
            self._entries.pop()
            raise
        return entry

    def save(self) -> None:
        if not self.path:
            return
        payload = {"schema": SCHEMA_LEDGER, "window_hours": self.window.total_seconds() / 3600.0,
                   "entries": [entry.as_dict() for entry in self._entries]}
        try:
            _atomic_write_json(self.path, payload)
        except OSError as exc:
            raise LedgerError("cannot write the ledger: {} ({})".format(self.path, exc)) from exc

    def as_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "entries": len(self._entries),
                "seen_intent_ids": len(self.seen_intent_ids())}


# --- chained journal ----------------------------------------------------------

def record_hash(record: Mapping[str, Any]) -> str:
    """SHA-256 canonique du contenu, ``record_hash`` exclu."""
    payload = {key: value for key, value in record.items() if key != "record_hash"}
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


class ChainedJournal:
    """Append-only JSONL journal chained by ``prev_hash`` (one line = one tick)."""

    def __init__(self, path: str):
        self.path = path
        self._prev = GENESIS_HASH
        self._seq = 0
        self._count = 0
        if os.path.exists(path):
            integrity = verify_journal(path)
            if not integrity["ok"]:
                raise JournalError("invalid existing journal ({}): {}".format(path, integrity["error"]))
            self._resume()

    def _resume(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                lines = [line for line in handle if line.strip()]
        except OSError as exc:
            raise JournalError("journal unreadable: {} ({})".format(self.path, exc)) from exc
        self._count = len(lines)
        if not lines:
            return
        try:
            last = json.loads(lines[-1])
        except ValueError as exc:
            raise JournalError("journal: invalid last line ({})".format(self.path)) from exc
        previous = last.get("record_hash") if isinstance(last, dict) else None
        if not isinstance(previous, str) or len(previous) != 64:
            raise JournalError("journal: missing or invalid last record_hash ({})".format(self.path))
        seq = last.get("seq")
        self._seq = int(seq) if isinstance(seq, int) and not isinstance(seq, bool) else self._count
        self._prev = previous

    @property
    def count(self) -> int:
        return self._count

    @property
    def last_hash(self) -> str:
        return self._prev

    def append(self, record: Mapping[str, Any]) -> Dict[str, Any]:
        """Append a record, compute its hash and persist it."""
        payload = dict(record)
        payload["schema"] = SCHEMA_JOURNAL
        payload["seq"] = self._seq + 1
        payload["prev_hash"] = self._prev
        payload["record_hash"] = record_hash(payload)
        directory = os.path.dirname(os.path.abspath(self.path)) or "."
        os.makedirs(directory, exist_ok=True)
        line = canonical_json(payload)
        try:
            with open(self.path, "a", encoding="utf-8", newline="\n") as handle:
                handle.write(line + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise JournalError("cannot write the journal: {} ({})".format(self.path, exc)) from exc
        self._seq += 1
        self._prev = payload["record_hash"]
        self._count += 1
        return payload


def verify_journal(path: str) -> Dict[str, Any]:
    """Recompute the journal chain; any rewritten line breaks it."""
    if not os.path.exists(path):
        return {"ok": True, "records": 0, "error": "", "path": path}
    previous = GENESIS_HASH
    count = 0
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for index, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    return {"ok": False, "records": count, "path": path,
                            "error": "line {}: invalid JSON".format(index)}
                if not isinstance(record, dict):
                    return {"ok": False, "records": count, "path": path,
                            "error": "line {}: object expected".format(index)}
                if record.get("seq") != count + 1:
                    return {"ok": False, "records": count, "path": path,
                            "error": "line {}: unexpected seq {}".format(index, record.get("seq"))}
                if record.get("prev_hash") != previous:
                    return {"ok": False, "records": count, "path": path,
                            "error": "line {}: broken prev_hash".format(index)}
                if record.get("record_hash") != record_hash(record):
                    return {"ok": False, "records": count, "path": path,
                            "error": "line {}: non-conforming record_hash".format(index)}
                previous = record["record_hash"]
                count += 1
    except OSError as exc:
        return {"ok": False, "records": count, "path": path,
                "error": "journal unreadable: {}".format(exc)}
    return {"ok": True, "records": count, "error": "", "path": path}


# --- external state (P7/P11/P12/P14) ------------------------------------------

def resolve_pause(env: Optional[Mapping[str, str]] = None,
                  flag_path: Optional[str] = None) -> Optional[bool]:
    """Pause/kill switch, re-read on every tick.

    explicit ``ORVYREN_K0_PAUSED`` (1/true/… or 0/false/…); otherwise the presence of the
    ``ORVYREN_K0_PAUSE_FLAG`` file (or ``flag_path``). Unreadable value ->
    ``None`` (P11 denies: fail-closed). Never a crash.
    """
    environment = _env(env)
    raw = environment.get("ORVYREN_K0_PAUSED")
    if raw is not None and str(raw).strip() != "":
        return parse_bool(raw)
    path = flag_path or environment.get("ORVYREN_K0_PAUSE_FLAG")
    if path:
        try:
            return bool(os.path.exists(str(path)))
        except OSError:
            return None
    return False


def resolve_agent_member(env: Optional[Mapping[str, str]] = None) -> Optional[bool]:
    """AGENT role membership (P11). No implicit default: missing -> ``None``.

    P11 treats ``None`` as unreadable and **denies** (AGENT_NOT_MEMBER). A demo
    that wants ``member=true`` must opt in explicitly (``--demo-defaults``);
    a permissive default here would turn the kill switch into decoration.
    """
    environment = _env(env)
    raw = environment.get("ORVYREN_AGENT_MEMBER")
    if raw is None or str(raw).strip() == "":
        return None
    return parse_bool(raw)


def resolve_available_balance(env: Optional[Mapping[str, str]] = None) -> Optional[float]:
    """Available balance (P7): ``ORVYREN_AVAILABLE_BALANCE``. Missing -> ``None``.

    P7 treats ``None`` as unreadable and **denies** (BALANCE_UNREADABLE). No
    implicit 1000 USDC default: a demo must opt in explicitly.
    """
    environment = _env(env)
    raw = environment.get("ORVYREN_AVAILABLE_BALANCE")
    if raw is None or str(raw).strip() == "":
        return None
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) and value >= 0 else None


def decision_budget_cap(bundle: PolicyBundle) -> Optional[float]:
    """Decision-budget cap (P14) read from ``policy_v1.yaml``."""
    raw = (bundle.data or {}).get("decision_budget_usd")
    if raw is None:
        return None
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) and value > 0 else None


def build_policy_state(*, paused: Optional[bool], agent_member: Optional[bool],
                       envelope_status: Optional[str], available_balance: Optional[float],
                       budget_cap: Optional[float]) -> PolicyState:
    """Real-state snapshot passed to ``evaluate`` (no state rule SKIPPED any more)."""
    return PolicyState(
        paused=paused,
        agent_member=agent_member,
        envelope_status=envelope_status,
        available_balance=available_balance,
        # Deterministic path (no LLM): zero decision cost, cap from the bundle.
        budget_spent=(0.0 if budget_cap is not None else None),
        budget_cap=budget_cap,
    )


# --- envelope (P12): off-chain policy <-> fixture conformance ----------------

def _check(check_id: str, name: str, status: str, detail: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"id": check_id, "name": name, "status": status, "detail": detail or {}}


def offline_envelope_checks(bundle: PolicyBundle, fixture: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Static v1 policy <-> envelope fixture checks (D3-D10 subset).

    No network: the versioned fixture is the reference capture. A field
    missing from the fixture is ``UNVERIFIED``; an observed mismatch is ``DRIFT``.
    """
    data, config = bundle.data or {}, bundle.config
    role = fixture.get("role") if isinstance(fixture, Mapping) else None
    checks: List[Dict[str, Any]] = []

    if not isinstance(fixture, Mapping) or fixture.get("schema") != FIXTURE_SCHEMA:
        return [_check("ENV-schema", "fixture schema", ENVELOPE_UNVERIFIED,
                       {"observed": (fixture or {}).get("schema") if isinstance(fixture, Mapping) else None,
                        "expected": FIXTURE_SCHEMA})]

    # D1 — chain
    fixture_chain = fixture.get("chain_id")
    if fixture_chain is None:
        checks.append(_check("D1", "chain", ENVELOPE_UNVERIFIED, {"note": "chain_id missing from the fixture"}))
    elif fixture_chain in config.allowed_chain_ids:
        checks.append(_check("D1", "chain", ENVELOPE_PASS, {"chain_id": fixture_chain}))
    else:
        checks.append(_check("D1", "chain", ENVELOPE_DRIFT,
                             {"fixture": fixture_chain, "policy": sorted(config.allowed_chain_ids)}))

    # D3 — role identity
    policy_key = str(data.get("role_key") or "").strip().lower()
    fixture_key = str(fixture.get("role_key") or "").strip().lower()
    if not policy_key or not fixture_key:
        checks.append(_check("D3", "role key", ENVELOPE_UNVERIFIED,
                             {"policy": policy_key or None, "fixture": fixture_key or None}))
    elif policy_key == fixture_key:
        checks.append(_check("D3", "role key", ENVELOPE_PASS))
    else:
        checks.append(_check("D3", "role key", ENVELOPE_DRIFT,
                             {"policy": policy_key, "fixture": fixture_key}))

    if not isinstance(role, Mapping):
        checks.append(_check("D4", "role targets", ENVELOPE_UNVERIFIED, {"note": "role absent"}))
        checks.append(_check("D5", "role functions", ENVELOPE_UNVERIFIED, {"note": "role absent"}))
        checks.append(_check("D7", "allowance", ENVELOPE_UNVERIFIED, {"note": "role absent"}))
        checks.append(_check("D8", "call quota", ENVELOPE_UNVERIFIED, {"note": "role absent"}))
    else:
        # D4 — targets (broad scope forbidden)
        targets = role.get("targets")
        if not isinstance(targets, list) or not targets:
            checks.append(_check("D4", "role targets", ENVELOPE_UNVERIFIED, {"note": "targets absent"}))
        else:
            addresses, broad = set(), []
            for entry in targets:
                if not isinstance(entry, Mapping):
                    continue
                address = str(entry.get("address") or "").strip().lower()
                clearance = str(entry.get("clearance") or "").strip().lower()
                if address:
                    addresses.add(address)
                if clearance != "function":
                    broad.append(address or clearance or "?")
            if broad:
                checks.append(_check("D4", "role targets", ENVELOPE_DRIFT,
                                     {"portee_large": sorted(broad),
                                      "note": "Clearance.Target = any calldata"}))
            elif addresses != set(config.allowed_targets):
                checks.append(_check("D4", "role targets", ENVELOPE_DRIFT,
                                     {"fixture": sorted(addresses), "policy": sorted(config.allowed_targets)}))
            else:
                checks.append(_check("D4", "role targets", ENVELOPE_PASS,
                                     {"targets": sorted(addresses)}))

        # D5 — functions (target/selector pairs)
        functions = role.get("functions")
        if not isinstance(functions, list) or not functions:
            checks.append(_check("D5", "role functions", ENVELOPE_UNVERIFIED, {"note": "functions absent"}))
        else:
            pairs, broad = set(), []
            for entry in functions:
                if not isinstance(entry, Mapping):
                    continue
                target = str(entry.get("target") or "").strip().lower()
                selector = str(entry.get("selector") or "").strip().lower()
                clearance = str(entry.get("clearance") or "").strip().lower()
                if target and selector:
                    pairs.add((target, selector))
                if clearance != "function":
                    broad.append((target, selector))
            if broad:
                checks.append(_check("D5", "role functions", ENVELOPE_DRIFT,
                                     {"portee_large": broad}))
            elif pairs != set(config.allowed_functions):
                checks.append(_check("D5", "role functions", ENVELOPE_DRIFT,
                                     {"fixture": sorted(pairs), "policy": sorted(config.allowed_functions)}))
            else:
                checks.append(_check("D5", "role functions", ENVELOPE_PASS,
                                     {"functions": sorted(pairs)}))

        # D7 — allowance (on-chain cap = the policy bound)
        allowances = role.get("allowances")
        allowance = None
        if isinstance(allowances, Mapping) and allowances:
            allowance = allowances.get("usdc_daily") or next(iter(allowances.values()))
        if not isinstance(allowance, Mapping):
            checks.append(_check("D7", "allowance", ENVELOPE_UNVERIFIED, {"note": "allowances absent"}))
        else:
            try:
                fixture_refill = int(allowance.get("refill_base_units"))
                fixture_max = int(allowance.get("max_refill_base_units"))
                fixture_period = int(allowance.get("period_seconds"))
                policy_refill = int(data.get("allowance_refill_base_units"))
                policy_max = int(data.get("allowance_max_refill_base_units"))
                policy_period = int(data.get("allowance_period_seconds"))
            except (TypeError, ValueError):
                checks.append(_check("D7", "allowance", ENVELOPE_UNVERIFIED,
                                     {"note": "allowance field unreadable"}))
            else:
                mismatches = []
                if fixture_refill != policy_refill:
                    mismatches.append("refill_base_units")
                if fixture_max != policy_max:
                    mismatches.append("max_refill_base_units")
                if fixture_period != policy_period:
                    mismatches.append("period_seconds")
                checks.append(_check(
                    "D7", "allowance", ENVELOPE_DRIFT if mismatches else ENVELOPE_PASS,
                    {"mismatches": mismatches, "fixture": fixture_refill,
                     "policy": policy_refill}))

        # D8 — call quota
        quota = role.get("call_quota")
        if not isinstance(quota, Mapping):
            checks.append(_check("D8", "call quota", ENVELOPE_UNVERIFIED, {"note": "call_quota absent"}))
        else:
            try:
                quota_max = int(quota.get("max_per_period"))
                policy_max_calls = int(data.get("max_calls_24h"))
            except (TypeError, ValueError):
                checks.append(_check("D8", "call quota", ENVELOPE_UNVERIFIED,
                                     {"note": "max_per_period/max_calls_24h unreadable"}))
            else:
                checks.append(_check(
                    "D8", "call quota",
                    ENVELOPE_PASS if quota_max == policy_max_calls else ENVELOPE_DRIFT,
                    {"fixture": quota_max, "policy": policy_max_calls}))

    # D9 — scheduled revocation
    policy_revocation = str(data.get("revocation_scheduled_at") or "").strip()
    fixture_revocation = str(fixture.get("revocation_scheduled_at") or "").strip()
    if not policy_revocation or not fixture_revocation:
        checks.append(_check("D9", "scheduled revocation", ENVELOPE_UNVERIFIED,
                             {"policy": policy_revocation or None,
                              "fixture": fixture_revocation or None}))
    elif policy_revocation != fixture_revocation:
        checks.append(_check("D9", "scheduled revocation", ENVELOPE_DRIFT,
                             {"policy": policy_revocation, "fixture": fixture_revocation}))
    else:
        checks.append(_check("D9", "scheduled revocation", ENVELOPE_PASS))

    # D10 — asset
    assets = fixture.get("assets")
    fixture_asset = str((assets or {}).get("usdc_circle") or "").strip().lower() \
        if isinstance(assets, Mapping) else ""
    if not fixture_asset:
        checks.append(_check("D10", "asset", ENVELOPE_UNVERIFIED, {"note": "assets.usdc_circle absent"}))
    elif fixture_asset in {str(asset).lower() for asset in config.allowed_assets}:
        checks.append(_check("D10", "asset", ENVELOPE_PASS))
    else:
        checks.append(_check("D10", "asset", ENVELOPE_DRIFT,
                             {"fixture": fixture_asset, "policy": sorted(config.allowed_assets)}))

    return checks


def resolve_envelope(bundle: PolicyBundle, policy_path: Optional[str] = None,
                     fixture_path: Optional[str] = None,
                     env: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    """P12 status: PASS / DRIFT / UNVERIFIED, with the list of checks.

    ``ORVYREN_ENVELOPE_STATUS`` allows an explicit operator attestation
    (unknown value -> UNVERIFIED, never PASS by default).
    """
    environment = _env(env)
    override = str(environment.get("ORVYREN_ENVELOPE_STATUS") or "").strip().upper()
    if override:
        status = override if override in {ENVELOPE_PASS, ENVELOPE_DRIFT, ENVELOPE_UNVERIFIED} \
            else ENVELOPE_UNVERIFIED
        return {"status": status, "source": "env", "checks": [],
                "note": "status forced by ORVYREN_ENVELOPE_STATUS",
                "fixture_path": None}

    relative = str((bundle.data or {}).get("envelope_fixture")
                   or os.path.join("fixtures", "roles_agent_config.json"))
    if fixture_path:
        path = fixture_path
    elif os.path.isabs(relative):
        path = relative
    else:
        base = os.path.dirname(os.path.abspath(policy_path)) if policy_path else os.getcwd()
        path = os.path.normpath(os.path.join(base, relative))
    if not os.path.exists(path):
        return {"status": ENVELOPE_UNVERIFIED, "source": "fixture", "checks": [],
                "note": "envelope fixture not found: {}".format(path),
                "fixture_path": path}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            fixture = json.load(handle)
    except (OSError, ValueError) as exc:
        return {"status": ENVELOPE_UNVERIFIED, "source": "fixture", "checks": [],
                "note": "unreadable fixture: {} ({})".format(path, exc), "fixture_path": path}

    checks = offline_envelope_checks(bundle, fixture)
    if any(check["status"] == ENVELOPE_DRIFT for check in checks):
        status = ENVELOPE_DRIFT
    elif any(check["status"] == ENVELOPE_UNVERIFIED for check in checks):
        status = ENVELOPE_UNVERIFIED
    else:
        status = ENVELOPE_PASS
    return {"status": status, "source": "fixture", "checks": checks,
            "note": "", "fixture_path": path}


# --- policy: loading, recipients, mandate window -----------------------------

def collect_recipients(recipient: Optional[str] = None,
                       env: Optional[Mapping[str, str]] = None,
                       fallback: Optional[str] = None) -> Tuple[str, Dict[str, str]]:
    """Resolve the effective recipient and the label -> session address table.

    The **effective** recipient is ``recipient`` when supplied, otherwise
    ``ORVYREN_RECIPIENT_B``, sinon ``ORVYREN_RESERVE_ADDRESS``, sinon
    ``fallback``, otherwise the demo address. The label -> address table
    resolves B from the environment first: a ``--recipient`` can therefore
    never widen the allowlist, it must be listed there (B or C).
    An explicitly empty variable is a refusal (never a silent fallback).
    """
    environment = _env(env)

    def configured(name: str) -> Optional[str]:
        if name not in environment:
            return None
        value = str(environment.get(name) or "").strip()
        if not value:
            raise RecipientError("{} is set but empty — recipient refused".format(name))
        return value

    primary = recipient
    if primary is not None:
        primary = str(primary).strip()
        if not primary:
            raise RecipientError("empty recipient — fail-closed denial")

    table: Dict[str, str] = {}
    label_b = configured("ORVYREN_RECIPIENT_B")
    if label_b:
        table["B"] = _normalize_address(label_b, "ORVYREN_RECIPIENT_B")
    elif primary:
        table["B"] = _normalize_address(primary, "--recipient")

    label_c = configured("ORVYREN_RECIPIENT_C")
    if label_c:
        table["C"] = _normalize_address(label_c, "ORVYREN_RECIPIENT_C")

    reserve = str(environment.get("ORVYREN_RESERVE_ADDRESS") or "").strip()
    default_address = reserve or str(fallback or "").strip() or DEFAULT_RESERVE_ADDRESS
    effective = _normalize_address(primary or label_b or default_address, "recipient")
    if "B" not in table:
        table["B"] = effective
    return effective, table


def load_bundle(policy_path: str, recipients: Optional[Mapping[str, str]] = None) -> PolicyBundle:
    """Load ``policy_v1.yaml``; any error becomes ``PolicyLoadError``."""
    if not policy_path or not os.path.exists(policy_path):
        raise PolicyLoadError("policy_v1.yaml not found: {}".format(policy_path))
    try:
        return load_policy(policy_path, dict(recipients or {}))
    except (OSError, MiniYamlError, ValueError, TypeError) as exc:
        raise PolicyLoadError("invalid policy_v1.yaml: {} ({})".format(policy_path, exc)) from exc


def apply_permission_window(bundle: PolicyBundle, now: datetime,
                            default_hours: Optional[float] = None) -> float:
    """Set the mandate expiry (P8): now + TTL from the bundle.

    ``policy_v1.yaml`` carries ``permission_ttl_hours``; the expiry itself
    is an execution fact (grant date), not a file parameter.
    """
    raw = (bundle.data or {}).get("permission_ttl_hours", default_hours)
    try:
        hours = float(str(raw))
    except (TypeError, ValueError):
        hours = 0.0
    if not math.isfinite(hours) or hours <= 0:
        raise PolicyLoadError("permission_ttl_hours missing or invalid in policy_v1.yaml")
    bundle.config.permission_expires_at = now + timedelta(hours=hours)
    return hours


# --- signer (lazy import, only for --execute) --------------------------------

def _scripts_demo_dir() -> str:
    here = os.path.dirname(os.path.abspath(__file__))          # .../src/orvyren/execution
    root = os.path.dirname(os.path.dirname(os.path.dirname(here)))  # repository root
    return os.path.join(root, "scripts", "demo")


def preflight_signer(scripts_dir: Optional[str] = None,
                     env: Optional[Mapping[str, str]] = None) -> Any:
    """Load the isolated signer and check key + dependency BEFORE any tick.

    Raise ``ExecuteUnavailable`` with a clear message (never any key
    material). No ``scripts/`` import at the module top-level.
    """
    environment = _env(env)
    directory = scripts_dir or _scripts_demo_dir()
    if not os.path.isdir(directory):
        raise ExecuteUnavailable("signer service not found: {}".format(directory))
    if directory not in sys.path:
        sys.path.insert(0, directory)
    try:
        import signer as signer_module  # noqa: PLC0415 — lazy import on purpose
    except Exception as exc:  # noqa: BLE001 — depends on the installation
        raise ExecuteUnavailable("signer service unavailable: {}".format(exc)) from exc

    rpc_url = str(environment.get("ORVYREN_RPC_URL_BASE_SEPOLIA")
                  or getattr(signer_module.common, "DEFAULT_RPC_URL", "")).strip()
    instance = signer_module.Signer(rpc_url=rpc_url, chain_id=ALLOWED_CHAIN_ID,
                                    dry_run=False, env=dict(environment))
    if not instance.library_available():
        raise ExecuteUnavailable(
            "real signing requires eth-account — python -m pip install eth-account "
            "(the --dry-run mode works without it)")
    if not instance.key_present():
        raise ExecuteUnavailable(
            "ORVYREN_PRIVATE_KEY missing or malformed — --execute refused (fail-closed)")
    return instance


def _rpc_int(url: Optional[str], method: str, params: List[Any], timeout: int) -> int:
    result = chain_client.rpc(url or chain_client.default_rpc_url(), method, params, timeout)
    if isinstance(result, int) and not isinstance(result, bool):
        return result
    if isinstance(result, str) and result.startswith("0x"):
        try:
            return int(result, 16)
        except ValueError:
            pass  # "0x" or non-hex digits: fall through to the typed error below
    raise chain_client.ChainError("non-integer response to {}: {!r}".format(method, result))


def _execute_intent(intent: Intent, *, signer: Any, rpc_url: Optional[str],
                    timeout: int = 30, receipt_timeout: int = DEFAULT_RECEIPT_TIMEOUT) -> Dict[str, Any]:
    """Sign, broadcast and verify the receipt of an already-ALLOW intent (real mode)."""
    calldata = chain_client.erc20_transfer_calldata(
        intent.recipient, value_to_base_units(intent.amount))
    sender = signer.address()
    nonce = _rpc_int(rpc_url, "eth_getTransactionCount", [sender, "pending"], timeout)
    try:
        gas_price = _rpc_int(rpc_url, "eth_gasPrice", [], timeout)
    except chain_client.ChainError:
        gas_price = 0
    if gas_price <= 0:
        gas_price = 1_000_000_000  # fallback bound: 1 gwei (testnet)
    gas = 120_000
    try:
        estimate = _rpc_int(rpc_url, "eth_estimateGas",
                            [{"from": sender, "to": intent.asset, "data": calldata}], timeout)
        gas = max(60_000, int(estimate * 1.25))
    except chain_client.ChainError:
        pass
    tx = {
        "type": 2,
        "chainId": ALLOWED_CHAIN_ID,
        "nonce": nonce,
        "to": intent.asset,
        "value": 0,
        "data": calldata,
        "gas": gas,
        "maxFeePerGas": gas_price * 2,
        "maxPriorityFeePerGas": gas_price,
    }
    signed = signer.sign_transaction(tx, intent_id=intent.intent_id)
    tx_hash = signer.send_raw_transaction(signed["signed_transaction"], timeout=timeout)

    receipt = None
    deadline = time.monotonic() + max(0, int(receipt_timeout))
    while receipt is None and time.monotonic() <= deadline:
        receipt = chain_client.get_transaction_receipt(tx_hash, url=rpc_url, timeout=timeout)
        if receipt is None:
            time.sleep(2)
    if receipt is None:
        return {"tx_hash": tx_hash, "sent": True, "receipt_verification": None,
                "error": "receipt not found after {}s (transaction broadcast, not verified)".format(receipt_timeout)}
    receipt = dict(receipt)
    if "chainId" not in receipt:
        try:
            receipt["chainId"] = hex(chain_client.chain_id(url=rpc_url, timeout=timeout))
        except chain_client.ChainError:
            pass
    verification = verify_receipt(receipt, {
        "token": intent.asset,
        "from": sender,
        "to": intent.recipient,
        "amount_usdc": intent.amount,
        "chain_id": ALLOWED_CHAIN_ID,
        "decimals": 6,
    })
    error = None
    if not verification.get("ok"):
        error = "non-conforming receipt: {}".format(", ".join(verification.get("mismatches") or ["?"]))
    return {"tx_hash": tx_hash, "sent": True, "receipt_verification": verification,
            "error": error}


# --- loop --------------------------------------------------------------------

def _default_decision_provider(case: str, corpus_path: Optional[str], recipient: str
                               ) -> Callable[[int, datetime], Dict[str, Any]]:
    def provider(tick: int, now: datetime) -> Dict[str, Any]:
        from orvyren.decide import build_decision_record  # lazy import (heavy engine)
        return build_decision_record(case, corpus_path, recipient)
    return provider


def _build_intent(decision_record: Optional[Mapping[str, Any]], *, case: str, tick: int,
                  now: datetime, run_id: str) -> Tuple[Optional[Intent], str, Dict[str, Any]]:
    """Turn the DecisionRecord ``intent`` into a bounded executable intent.

    No repair: a missing field stays missing and the policy will deny it
    (P1/P3/P5). The recipient is never silently replaced.
    """
    record = decision_record if isinstance(decision_record, Mapping) else {}
    raw = record.get("intent")
    summary = {
        "epistemic_verdict": record.get("epistemic_verdict"),
        "economic_action": record.get("economic_action"),
        "authorization_verdict": record.get("authorization_verdict"),
    }
    if not isinstance(raw, Mapping):
        return None, "the DecisionRecord carries no executable intent", summary
    action = str(raw.get("action") or "").strip()
    if action != "transfer":
        return None, "action not autonomous in v1: {!r}".format(action or None), summary
    amount = raw.get("amount")
    if not _finite_number(amount):
        return None, "unreadable intent amount: {!r}".format(amount), summary
    chain_id = raw.get("chain_id")
    if isinstance(chain_id, bool) or not isinstance(chain_id, int):
        chain_id = 0  # P1 will deny with CHAIN_NOT_ALLOWED
    base_id = str(raw.get("intent_id") or "").strip() or "intent-{}".format(safe_case(case))
    intent = Intent(
        intent_id="{}-t{:03d}-{}".format(base_id, tick, run_id),
        action=action,
        chain_id=chain_id,
        asset=str(raw.get("asset") or "").strip(),
        amount=float(amount),
        recipient=str(raw.get("recipient") or "").strip(),
        created_at=now,
        justification="autonomous executor — decision {} / tick {}".format(case, tick),
    )
    return intent, "", summary


def _intent_view(intent: Intent) -> Dict[str, Any]:
    return {
        "intent_id": intent.intent_id,
        "action": intent.action,
        "chain_id": intent.chain_id,
        "asset": intent.asset,
        "amount": intent.amount,
        "recipient": intent.recipient,
        "created_at": _iso(intent.created_at),
    }


def run_loop(bundle: PolicyBundle, *, case: str, recipient: str,
             journal_path: str, ledger_path: Optional[str],
             ticks: int = DEFAULT_TICKS, interval_s: float = DEFAULT_INTERVAL_S,
             dry_run: bool = True, max_usd: Optional[float] = None,
             decision_provider: Optional[Callable[[int, datetime], Dict[str, Any]]] = None,
             policy_path: Optional[str] = None, fixture_path: Optional[str] = None,
             corpus_path: Optional[str] = None,
             env: Optional[Mapping[str, str]] = None,
             clock: Optional[Callable[[], datetime]] = None,
             sleep: Optional[Callable[[float], None]] = None,
             signer: Any = None,
             execute: Optional[Callable[[Intent, Dict[str, Any]], Dict[str, Any]]] = None,
             rpc_url: Optional[str] = None,
             receipt_timeout: int = DEFAULT_RECEIPT_TIMEOUT) -> Dict[str, Any]:
    """Run ``ticks`` ticks and return the summary (JSON-serializable dict).

    Each tick journals exactly one record, whatever the
    verdict. A denial (policy, pause, budget) does not stop the loop;
    an execution error stops it (fail-closed).
    """
    if not isinstance(ticks, int) or isinstance(ticks, bool) or ticks < 0:
        raise ValueError("ticks must be an integer >= 0")
    if max_usd is not None and (not _finite_number(max_usd) or max_usd < 0):
        raise ValueError("max_usd must be a finite number >= 0")
    if interval_s is None:
        interval_s = 0.0
    if interval_s < 0:
        raise ValueError("interval_s must be >= 0")

    environment = _env(env)
    now_fn = clock or utcnow
    sleeper = sleep or time.sleep
    provider = decision_provider or _default_decision_provider(case, corpus_path, recipient)

    journal = ChainedJournal(journal_path)
    ledger = PeriodLedger(ledger_path)
    budget_cap = decision_budget_cap(bundle)
    run_id = uuid.uuid4().hex[:8]
    mode = "dry-run" if dry_run else "execute"
    spent_before = ledger.spent(now_fn())
    records: List[Dict[str, Any]] = []
    stopped = ""
    last_envelope: Dict[str, Any] = {"status": None, "source": None, "checks": []}
    paused_engaged = False

    for tick in range(1, ticks + 1):
        if tick > 1 and interval_s > 0:
            sleeper(interval_s)
        now = now_fn()
        # Kill switch re-read on EVERY tick (env or flag file).
        paused = resolve_pause(environment)
        agent_member = resolve_agent_member(environment)
        available_balance = resolve_available_balance(environment)
        last_envelope = resolve_envelope(bundle, policy_path, fixture_path, environment)
        if paused is not False:
            paused_engaged = True
        state = build_policy_state(paused=paused, agent_member=agent_member,
                                   envelope_status=last_envelope["status"],
                                   available_balance=available_balance,
                                   budget_cap=budget_cap)

        record: Dict[str, Any] = {
            "case": case,
            "run_id": run_id,
            "tick": tick,
            "ts_utc": _iso(now),
            "mode": mode,
            "dry_run": bool(dry_run),
            "verdict": "DENY",
            "policy_verdict": None,
            "outcome": None,
            "executed": False,
            "intent": None,
            "decision_summary": {},
            "reasons": [],
            "rules_evaluated": [],
            "skipped_rules": [],
            "policy_version": bundle.version,
            "policy_hash": bundle.policy_hash,
            "safe_mode": False,
            "state": {
                "paused": paused,
                "agent_member": agent_member,
                "envelope_status": last_envelope["status"],
                "available_balance": available_balance,
                "cumulative_spent": ledger.spent(now),
                "budget_spent": 0.0 if budget_cap is not None else None,
                "budget_cap": budget_cap,
            },
            "tx_hash": None,
            "receipt_verification": None,
            "error": None,
            "ledger_spent_after": None,
        }

        try:
            decision_record = provider(tick, now)
        except Exception as exc:  # noqa: BLE001 — an unreadable decision stops the run
            record.update(outcome="ERROR", verdict="ERROR",
                          error="decision unavailable: {}".format(exc))
            journal.append(record)
            records.append(record)
            stopped = "decision"
            break

        intent, problem, decision_summary = _build_intent(
            decision_record, case=case, tick=tick, now=now, run_id=run_id)
        record["decision_summary"] = decision_summary
        if intent is None:
            record.update(outcome="NO_ACTION", reasons=[NO_INTENT_CODE], error=problem)
            journal.append(record)
            records.append(record)
            continue

        record["intent"] = _intent_view(intent)
        try:
            decision = evaluate(intent, bundle.config, now=now,
                                seen_intent_ids=ledger.seen_intent_ids(),
                                cumulative_spent=ledger.spent(now),
                                state=state)
        except Exception as exc:  # noqa: BLE001
            record.update(outcome="ERROR", verdict="ERROR",
                          error="policy unavailable: {}".format(exc))
            journal.append(record)
            records.append(record)
            stopped = "policy"
            break

        record["policy_verdict"] = decision.verdict
        record["verdict"] = decision.verdict
        record["reasons"] = list(decision.reasons)
        record["rules_evaluated"] = list(decision.rules_evaluated)
        record["skipped_rules"] = [rule.get("rule") for rule in decision.rules_evaluated
                                   if rule.get("result") == "SKIPPED"]
        record["policy_version"] = decision.policy_version
        record["policy_hash"] = decision.policy_hash
        record["safe_mode"] = bool(decision.safe_mode)

        if decision.verdict != "ALLOW":
            record["outcome"] = "DENIED_POLICY"
            journal.append(record)
            records.append(record)
            continue

        # Per-tick budget guard (outside the policy): denial without consumption.
        if max_usd is not None and intent.amount > max_usd:
            record["verdict"] = "DENY"
            record["outcome"] = "DENIED_TICK_BUDGET"
            record["reasons"] = list(decision.reasons) + [TICK_BUDGET_CODE]
            journal.append(record)
            records.append(record)
            continue

        if dry_run:
            # DRY-RUN report: no signature, no key read, no network.
            record["outcome"] = "DRY_RUN"
            record["executed"] = False
            ledger.record(now, intent.intent_id, intent.amount)
            record["ledger_spent_after"] = ledger.spent(now)
            journal.append(record)
            records.append(record)
            continue

        # Real mode: signer imported lazily, then receipt verification.
        try:
            if execute is not None:  # injected path (tests/bench): no signer required
                result = execute(intent, record)
            else:
                active_signer = signer or preflight_signer(env=environment)
                result = _execute_intent(intent, signer=active_signer, rpc_url=rpc_url,
                                         timeout=30, receipt_timeout=receipt_timeout)
        except Exception as exc:  # noqa: BLE001 — key/dependency/network: fail-closed stop
            record.update(outcome="ERROR", verdict="ERROR", executed=False,
                          error="execution refused: {}".format(exc))
            journal.append(record)
            records.append(record)
            stopped = "execute"
            break

        record["tx_hash"] = result.get("tx_hash")
        record["receipt_verification"] = result.get("receipt_verification")
        record["error"] = result.get("error")
        if result.get("tx_hash"):
            ledger.record(now, intent.intent_id, intent.amount)
            record["ledger_spent_after"] = ledger.spent(now)
        if result.get("error"):
            record["outcome"] = "RECEIPT_UNVERIFIED" if result.get("tx_hash") else "ERROR"
            record["executed"] = bool(result.get("sent"))
            journal.append(record)
            records.append(record)
            stopped = "receipt"
            break
        record["outcome"] = "SIGNED"
        record["executed"] = True
        journal.append(record)
        records.append(record)

    chain_state = verify_journal(journal_path)
    counts = {
        "allow": sum(1 for record in records if record.get("verdict") == "ALLOW"),
        "deny": sum(1 for record in records if record.get("verdict") == "DENY"),
        "require_approval": sum(1 for record in records
                                if record.get("verdict") == "REQUIRE_APPROVAL"),
        "dry_run": sum(1 for record in records if record.get("outcome") == "DRY_RUN"),
        "signed": sum(1 for record in records if record.get("outcome") == "SIGNED"),
        "no_action": sum(1 for record in records if record.get("outcome") == "NO_ACTION"),
        "errors": sum(1 for record in records if record.get("outcome") in
                      {"ERROR", "RECEIPT_UNVERIFIED"}),
    }
    return {
        "schema": SCHEMA_RUN,
        "case": case,
        "mode": mode,
        "ticks": ticks,
        "ticks_run": len(records),
        "recipient": recipient,
        "policy": {"path": policy_path, "version": bundle.version,
                   "policy_hash": bundle.policy_hash, "yaml_sha256": bundle.yaml_sha256},
        "envelope": {"status": last_envelope.get("status"),
                     "source": last_envelope.get("source"),
                     "fixture_path": last_envelope.get("fixture_path"),
                     "note": last_envelope.get("note"),
                     "checks": last_envelope.get("checks")},
        "paused": paused_engaged,
        "stopped": stopped,
        "journal": {"path": journal_path, "records": chain_state["records"],
                    "ok": chain_state["ok"], "error": chain_state["error"]},
        "ledger": {"path": ledger_path,
                   "entries": len(ledger.entries()),
                   "spent_24h_before": spent_before,
                   "spent_24h_after": ledger.spent(now_fn())},
        "counts": counts,
        "records": records,
    }
