# -*- coding: utf-8 -*-
"""MA-B worker — one process, one role (W2 lot L2.4).

Two roles run in **separate processes** (FREEZE_V2 A1, DOC2 §5.2.1):

- ``orchestrator`` — runs the bounded loop (:class:`orvyren.agents.loop.BoundedLoop`),
  writes its own journal and emits an :class:`EvidencePacket` for the critic;
- ``critic`` — waits for the packet, attacks the reading on a **second model
  family** (mimo-v2.6-pro), writes **its own** journal and emits a
  :class:`CritiqueReport`.

Communication is file-based and strictly serializable (JSON in the run
directory) — never shared memory, per the frozen rule "communication between
roles travels as serializable objects". Each process stamps its own
``agent_id`` on every journal line; the journals are exported as append-only
JSONL files (``journal_<role>.jsonl``) verifiable by chain recomputation.

Usage (spawned by ``run_agents.py`` — rarely by hand)::

    python -m orvyren.agents.worker --role orchestrator --run-dir <dir>
    python -m orvyren.agents.worker --role critic --run-dir <dir>

The run directory contains ``run.json`` (spec) and receives
``outcome_orchestrator.json``, ``exchanges/*.json``, ``journal_*.jsonl`` and
``worker_done_<role>.json``. No agent process may import ``orvyren.policy``
or ``orvyren.execution`` (boundary rule, DOC4 W2).

Standard library only.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from orvyren.agents import contracts
from orvyren.agents.journal import AgentJournal, JournalEntry, entry_hash

__all__ = [
    "SystemClock",
    "VirtualClock",
    "load_run_spec",
    "export_journal",
    "load_journal",
    "verify_exported_chain",
    "build_backend",
    "run_orchestrator",
    "run_critic",
    "main",
]

#: Poll interval while waiting for the packet / reports (seconds).
POLL_SECONDS = 0.05


# ---------------------------------------------------------------------------
# Clocks — replay determinism lives here.
# ---------------------------------------------------------------------------
class SystemClock:
    """Real time (live mode). Wall-clock numbers are never claimed stable."""

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def monotonic(self) -> float:
        return time.monotonic()


class VirtualClock:
    """Deterministic clock for REPLAY: advances a fixed step on every read.

    The bounded loop only reads the clock through ``monotonic`` / ``now_iso``;
    a fixed step per read makes both the journal timestamps and the wall
    counter a pure function of the **call sequence**, so a journaled run
    rewrites byte-identical journals across replays (B1 §6.2).
    """

    def __init__(self, base_iso: str, step_seconds: float = 0.02) -> None:
        self._t = 0.0
        self._step = float(step_seconds)
        self._base = self._parse(base_iso)

    @staticmethod
    def _parse(value: str) -> datetime:
        text = str(value or "").replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            # Deterministic fallback: the wall clock must never leak into a
            # REPLAY clock (a missing/unparseable ``created_at`` would rewrite
            # different ``ts_utc`` — hence different chain heads — on every
            # replay, B1 §6.2).
            parsed = datetime.fromisoformat("1970-01-01T00:00:00+00:00")
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    def monotonic(self) -> float:
        self._t += self._step
        return self._t

    def now_iso(self) -> str:
        return (self._base + timedelta(seconds=self._t)).isoformat()


# ---------------------------------------------------------------------------
# Run directory plumbing.
# ---------------------------------------------------------------------------
def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: str, payload: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, path)


def load_run_spec(run_dir: str) -> Dict[str, Any]:
    """Load ``run.json`` and check the required keys (fail-closed)."""
    spec = _read_json(os.path.join(run_dir, "run.json"))
    required = ("schema", "run_id", "case_id", "mode", "budget", "snapshot",
                "lacunes", "hypotheses", "tool_fixtures")
    missing = [key for key in required if key not in spec]
    if missing:
        raise ValueError("E_RUN_SPEC_MISSING: %s" % ", ".join(missing))
    if spec["schema"] != "orvyren/agent-run/v1":
        raise ValueError("E_RUN_SPEC_SCHEMA: %r" % spec["schema"])
    if spec["mode"] not in ("journal", "live"):
        raise ValueError("E_RUN_SPEC_MODE: %r" % spec["mode"])
    return spec


def _entry_to_dict(entry: JournalEntry) -> Dict[str, Any]:
    return dataclasses.asdict(entry)


def export_journal(journal: AgentJournal, path: str) -> str:
    """Export a journal as append-only JSONL; returns the chain head hash."""
    head = "0" * 64
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for entry in journal.entries():
            handle.write(json.dumps(_entry_to_dict(entry), ensure_ascii=False,
                                    sort_keys=True) + "\n")
            head = entry_hash(entry)
    return head


def load_journal(path: str) -> List[JournalEntry]:
    """Load an exported journal (JSONL) back into entries."""
    entries: List[JournalEntry] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                payload = json.loads(line)
                payload["refs"] = tuple(payload.get("refs") or ())
                entries.append(JournalEntry(**{
                    key: value for key, value in payload.items()
                    if key in JournalEntry.__dataclass_fields__}))
    return entries


def verify_exported_chain(entries: List[JournalEntry]) -> Tuple[bool, str]:
    """Recompute the ``prev_hash`` chain of an exported journal."""
    previous = "0" * 64
    for index, entry in enumerate(entries):
        if entry.prev_hash != previous:
            return False, "chain broken at line %d (%s)" % (index, entry.journal_id)
        previous = entry_hash(entry)
    return True, ""


# ---------------------------------------------------------------------------
# Backends per mode (RECORDED for journal, LIVE for live) — no policy import.
# ---------------------------------------------------------------------------
def build_backend(spec: Dict[str, Any], run_dir: str, role: str = ""):
    """Build the LLM backend for the run mode.

    ``journal`` reads recorded calls from the store (fully offline,
    deterministic); ``live`` calls the pinned API (requires a key in the
    process environment — a missing key fails closed at call time).
    """
    from orvyren.agents.llm import LiveBackend, RecordedBackend, load_models_config
    from orvyren.agents.store import ResponseStore

    if spec.get("backend") == "scripted":
        from orvyren.agents.scripted import build_scripted_backend
        return build_scripted_backend(spec, run_dir, role)

    config = load_models_config()
    store_dir = spec.get("store_dir")
    if spec["mode"] == "journal":
        if not store_dir:
            raise ValueError("E_RUN_SPEC_STORE: journal mode needs store_dir")
        store = ResponseStore(os.path.join(os.path.dirname(run_dir), store_dir)
                              if not os.path.isabs(store_dir) else store_dir)
        return RecordedBackend(store, config)
    store = ResponseStore(os.path.join(run_dir, "store_live")) if spec.get("record_live") \
        else None
    return LiveBackend(config, store=store)


# ---------------------------------------------------------------------------
# The two roles.
# ---------------------------------------------------------------------------
def _build_tools(spec: Dict[str, Any], journal: AgentJournal,
                 observed: Any = None):
    from orvyren.agents.tools import ToolRegistry, build_v1_registry
    return build_v1_registry(fixtures=spec["tool_fixtures"], journal=journal,
                             observed=observed)


def build_evidence_packet(journal: AgentJournal, ledger: Any, *,
                          run_id: str, case_id: str, snapshot_ref: str
                          ) -> contracts.EvidencePacket:
    """Build the critic packet — refs and claims gathered from the journal.

    P0-6, second gate: the packet never carries a claim citing a reference the
    run did not observe (defence in depth — the loop already rejects at intake;
    this catches claims arriving from an exported journal). Excluded claims
    are counted in the summary: an exclusion is visible, never silent.
    """
    refs: List[str] = []
    claims: List[Dict[str, Any]] = []
    entries = journal.entries()
    for entry in entries:
        if entry.kind in ("TOOL_RESULT", "OBSERVATION_REF"):
            ledger.add_many(entry.refs)
    excluded = 0
    for entry in entries:
        for ref in entry.refs:
            if ref not in refs:
                refs.append(ref)
        if entry.kind == "REFLECTION" and entry.status in ("PROPOSED", "ACCEPTED"):
            if ledger.unknown(entry.refs):
                excluded += 1
                continue
            claims.append({"text": entry.content, "journal_id": entry.journal_id,
                           "refs": list(entry.refs)})
    summary = "evidence packet of the bounded run (%d reflections)" % len(claims)
    if excluded:
        summary += "; %d claim(s) excluded: ref not observed (P0-6)" % excluded
    return contracts.EvidencePacket(
        packet_id="%s-packet" % run_id,
        snapshot_ref=snapshot_ref,
        refs=tuple(refs), claims=tuple(claims),
        summary=summary)


def run_orchestrator(run_dir: str) -> int:
    """Orchestrator process: bounded loop -> outcome + evidence packet."""
    from orvyren.agents.loop import BoundedLoop
    from orvyren.agents.prompts import system_prompt, prompt_version

    spec = load_run_spec(run_dir)
    journal = AgentJournal()
    backend = build_backend(spec, run_dir, "orchestrator")
    # P0-6: one shared provenance ledger — the tools register what they really
    # observed, the loop refuses a claim citing anything else.
    ledger = contracts.ObservedRefs()
    if isinstance(spec.get("snapshot"), dict):
        ledger.add(spec["snapshot"].get("ref"))
    ledger.add_many(spec.get("authorized_refs") or ())
    tools = _build_tools(spec, journal, observed=ledger)
    clock = VirtualClock(spec.get("created_at", "")) if spec["mode"] == "journal" \
        else SystemClock()

    budget = contracts.Budget(**{k: float(v) for k, v in spec["budget"].items()
                                 if k in contracts.Budget.__dataclass_fields__})
    loop = BoundedLoop(
        case_id=spec["case_id"], run_id=spec["run_id"], agent_id="orchestrator",
        backend=backend, tools=tools, journal=journal, budget=budget, clock=clock,
        prompt_version=prompt_version("orchestrator"),
        system_prompt=system_prompt("orchestrator"),
        snapshot=spec["snapshot"], lacunes=spec["lacunes"],
        hypotheses=spec["hypotheses"], observed_refs=ledger)
    outcome = loop.run()

    _write_json(os.path.join(run_dir, "outcome_orchestrator.json"), outcome.to_dict())

    # Evidence packet for the critic: refs + claims gathered from the journal.
    packet = build_evidence_packet(
        journal, ledger, run_id=str(spec["run_id"]), case_id=str(spec["case_id"]),
        snapshot_ref=str(spec["snapshot"].get("ref", "")))
    exchanges = os.path.join(run_dir, "exchanges")
    os.makedirs(exchanges, exist_ok=True)
    _write_json(os.path.join(exchanges, "001_evidence_packet.json"), packet.to_dict())

    head = export_journal(journal, os.path.join(run_dir, "journal_orchestrator.jsonl"))
    _write_json(os.path.join(run_dir, "worker_done_orchestrator.json"),
                {"agent_id": "orchestrator", "pid": os.getpid(), "chain_head": head,
                 "lines": len(journal), "at": datetime.now(timezone.utc).isoformat()})
    print("[orchestrator] done — %d journal lines, state %s/%s"
          % (len(journal), outcome.state, outcome.stop_condition or "-"))
    return 0


def _critique_payload(packet: contracts.EvidencePacket, spec: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "snapshot_ref": packet.snapshot_ref,
        "claims": [dict(claim) for claim in packet.claims],
        "refs": list(packet.refs),
        "hypotheses": list(spec["hypotheses"]),
        "consigne": "attaque la lecture : cherche contradictions, unités, "
                    "obsolescence, PIT, dépendances, alternatives, preuves manquantes",
    }


def run_critic(run_dir: str, wait_s: float = 120.0) -> int:
    """Critic process: waits for the packet, attacks, writes its own journal."""
    from orvyren.agents.prompts import system_prompt, prompt_version

    spec = load_run_spec(run_dir)
    packet_path = os.path.join(run_dir, "exchanges", "001_evidence_packet.json")
    deadline = time.monotonic() + wait_s
    while not os.path.exists(packet_path):
        if time.monotonic() > deadline:
            print("[critic] E_CRITIC_NO_PACKET: no packet after %.0fs" % wait_s)
            return 3
        time.sleep(POLL_SECONDS)
    packet = contracts.EvidencePacket.from_dict(_read_json(packet_path))

    journal = AgentJournal()
    backend = build_backend(spec, run_dir, "critic")
    clock = VirtualClock(spec.get("created_at", "")) if spec["mode"] == "journal" \
        else SystemClock()
    payload = _critique_payload(packet, spec)
    role_version = prompt_version("critic")
    system = system_prompt("critic")

    result = backend.complete(role="critic", role_version=role_version,
                              schema_id="orvyren/crit/v1", system_prompt=system,
                              payload=payload)
    ok, errors = (False, ["E_LLM_CALL_FAILED: %s" % result.error])
    data = result.data if result.ok and isinstance(result.data, dict) else None
    if data is not None:
        ok, errors = contracts.validate_critique_output(data)
    if not ok:
        # 1 re-prompt with the error injected (B1 §5.5 rule 3), then quarantine.
        payload_retry = dict(payload, erreurs_precedentes=errors)
        result = backend.complete(role="critic", role_version=role_version,
                                  schema_id="orvyren/crit/v1", system_prompt=system,
                                  payload=payload_retry)
        data = result.data if result.ok and isinstance(result.data, dict) else None
        ok, errors = (contracts.validate_critique_output(data) if data is not None
                      else (False, ["E_LLM_CALL_FAILED: %s" % result.error]))

    llm_fields = {}
    if result.prompt_hash and result.response_hash:
        # Same rule as ``loop._llm_fields``: the ``llm`` provenance mapping is
        # stamped only when the call really carries BOTH pinned hashes —
        # otherwise the validator would reject the line for a "LLM line
        # without prompt/response hash" although a failed call simply has no
        # response blob to pin.
        llm_fields = {
            "provider": result.provider, "model": result.model,
            "model_version_pinned": result.model_version_pinned,
            "temperature": result.temperature,
        }
    if ok and data is not None:
        report = contracts.CritiqueReport.from_dict(data)
        critique_refs = [ref for finding in report.findings for ref in finding.refs]
        journal.append_dict({
            "journal_id": "%s-critique" % spec["run_id"], "run_id": spec["run_id"],
            "episode_id": spec["case_id"], "agent_id": "critic",
            "role_version": role_version, "step_index": 0, "ts_utc": clock.now_iso(),
            "kind": "CRITIQUE", "content": "verdict=%s, %d objections"
                       % (report.verdict_lecture, len(report.findings)),
            "refs": critique_refs or list(packet.refs[:1]),
            "llm": llm_fields, "prompt_hash": result.prompt_hash,
            "response_hash": result.response_hash, "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out, "cached_in": result.cached_in,
            "cost_usd": result.cost_usd, "latency_ms": result.latency_ms})
        _write_json(os.path.join(run_dir, "exchanges", "002_critique_report.json"),
                    report.to_dict())
        print("[critic] report written — verdict %s, %d objection(s)"
              % (report.verdict_lecture, len(report.findings)))
    else:
        journal.append_dict({
            "journal_id": "%s-critique-quarantaine" % spec["run_id"],
            "run_id": spec["run_id"], "episode_id": spec["case_id"],
            "agent_id": "critic", "role_version": role_version, "step_index": 0,
            "ts_utc": clock.now_iso(), "kind": "ERROR",
            "content": "non-conforming critique output — quarantined",
            "llm": llm_fields, "prompt_hash": result.prompt_hash,
            "response_hash": result.response_hash, "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out, "cached_in": result.cached_in,
            "cost_usd": result.cost_usd, "latency_ms": result.latency_ms})
        _write_json(os.path.join(run_dir, "exchanges", "002_critique_report.json"),
                    {"$status": "QUARANTINED", "errors": errors})
        print("[critic] non-conforming output — quarantined (%s)" % "; ".join(errors[:2]))

    head = export_journal(journal, os.path.join(run_dir, "journal_critic.jsonl"))
    _write_json(os.path.join(run_dir, "worker_done_critic.json"),
                {"agent_id": "critic", "pid": os.getpid(), "chain_head": head,
                 "lines": len(journal), "at": datetime.now(timezone.utc).isoformat()})
    return 0


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="worker.py",
                                     description="ORVYREN — MA-B worker (one process, one role)")
    parser.add_argument("--role", required=True, choices=("orchestrator", "critic"))
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--wait-s", type=float, default=120.0,
                        help="maximum wait for the packet (critic)")
    args = parser.parse_args(argv)
    run_dir = os.path.abspath(args.run_dir)
    try:
        if args.role == "orchestrator":
            return run_orchestrator(run_dir)
        return run_critic(run_dir, wait_s=args.wait_s)
    except Exception as exc:  # fail-closed: a worker crash is a KO, never a fake OK
        print("[%s] E_WORKER_FAILED: %s" % (args.role, exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
