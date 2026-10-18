"""Loaders for the real ORVYREN system artefacts — stdlib only.

Nothing here is invented: every loader reads the artefacts produced by the
pipeline (agent runs, hash-chained journals, evidence packets, policy demo,
decision records, execution receipts, audit chains, episodes, price series)
and returns them shaped for the frontend. Where a field is missing on disk,
the loader says so instead of fabricating a value.

Artefact map (repository layout):
- ``demo_runs/**/<run>/run.json``                      run spec (hypotheses, gaps)
- ``demo_runs/**/<run>/journal_orchestrator.jsonl``    hash-chained journal
- ``demo_runs/**/<run>/journal_critic.jsonl``          critic journal
- ``demo_runs/**/<run>/outcome_orchestrator.json``     budget + stop condition
- ``demo_runs/**/<run>/run_outcome.json``              chain heads + critique
- ``demo_runs/**/<run>/exchanges/*.json``              evidence / critique packets
- ``evidence/agents_live/<run>/``                      live run copies
- ``evidence/episode_*.json``                          3 stress episodes
- ``evidence/decision_*.json``                         decision + axes + RDOF
- ``evidence/policy_execution_demo.json``              ALLOW/DENY/REQUIRE_APPROVAL
- ``evidence/demo_chain/rseth/``                       audit chain + receipts
- ``evidence/graph_snapshots/*/``                      PIT snapshots + provenance
- ``evidence/audit_packets/*.zip``                     sealed audit packets
- ``corpus/series/*.json``                             price series

Standard library only.
"""

from __future__ import annotations

import json
import os
import re
import zipfile
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from orvyren.api.config import Settings, load_settings

# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

_JSON_CACHE: Dict[str, Tuple[float, Any]] = {}


def read_json(path: str) -> Any:
    """Read a JSON file with a tiny mtime cache (the graph payload is heavy)."""
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        raise FileNotFoundError(path)
    cached = _JSON_CACHE.get(path)
    if cached and cached[0] == mtime:
        return cached[1]
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    _JSON_CACHE[path] = (mtime, data)
    return data


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    """Read a JSONL file into a list of dicts (one artefact line = one event)."""
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _exists(*parts: str) -> bool:
    return os.path.exists(os.path.join(*parts))


def _listdir(path: str) -> List[str]:
    try:
        return sorted(os.listdir(path))
    except OSError:
        return []


# --------------------------------------------------------------------------
# agent runs
# --------------------------------------------------------------------------

def _run_roots(settings: Settings) -> List[str]:
    """Directories that contain run directories (real artefact locations)."""
    roots = []
    for base in (
        os.path.join(settings.demo_runs_dir, "agents"),
        os.path.join(settings.demo_runs_dir, "agents_live_replay"),
        os.path.join(settings.demo_runs_dir, "agents_smoke"),
        os.path.join(settings.demo_runs_dir, "agents_smoke2"),
        os.path.join(settings.evidence_dir, "agents_live"),
    ):
        if os.path.isdir(base):
            roots.append(base)
    return roots


def _find_run_dirs(settings: Settings) -> List[Tuple[str, str]]:
    """Return ``(run_id, abs_path)`` for every directory holding a run journal."""
    found: Dict[str, str] = {}
    for base in _run_roots(settings):
        stack = [base]
        while stack:
            current = stack.pop()
            for name in _listdir(current):
                full = os.path.join(current, name)
                if not os.path.isdir(full):
                    continue
                if os.path.exists(os.path.join(full, "journal_orchestrator.jsonl")):
                    if name not in found:
                        found[name] = full
                else:
                    stack.append(full)
    return sorted(found.items())


def _journal_summary(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"present": False, "lines": 0, "kinds": {}}
    rows = read_jsonl(path)
    kinds: Dict[str, int] = {}
    for row in rows:
        kinds[row.get("kind", "?")] = kinds.get(row.get("kind", "?"), 0) + 1
    return {"present": True, "lines": len(rows), "kinds": kinds,
            "agent_ids": sorted({r.get("agent_id", "") for r in rows})}


def discover_runs(settings: Optional[Settings] = None) -> List[Dict[str, Any]]:
    """Every recorded agent run, with real counts and real outcomes."""
    settings = settings or load_settings()
    runs: List[Dict[str, Any]] = []
    for run_id, path in _find_run_dirs(settings):
        spec = read_json(os.path.join(path, "run.json")) if _exists(path, "run.json") else {}
        outcome = (read_json(os.path.join(path, "outcome_orchestrator.json"))
                   if _exists(path, "outcome_orchestrator.json") else {})
        run_outcome = (read_json(os.path.join(path, "run_outcome.json"))
                       if _exists(path, "run_outcome.json") else {})
        exchanges = [n for n in _listdir(os.path.join(path, "exchanges"))
                     if n.endswith(".json")]
        journals = {
            "orchestrator": _journal_summary(os.path.join(path, "journal_orchestrator.jsonl")),
            "critic": _journal_summary(os.path.join(path, "journal_critic.jsonl")),
        }
        runs.append({
            "run_id": run_id,
            "path": settings.rel(path),
            "abs_path": path,
            "case_id": spec.get("case_id", ""),
            "mode": spec.get("mode", run_outcome.get("mode", "")),
            "created_at": spec.get("created_at", ""),
            "schema": spec.get("schema", ""),
            "state": outcome.get("state", run_outcome.get("outcome", {}).get("state", "")),
            "stop_condition": outcome.get("stop_condition", ""),
            "inconclusive": outcome.get("inconclusive", None),
            "motif": outcome.get("motif", ""),
            "budget": spec.get("budget", {}),
            "budget_used": outcome.get("budget_used", {}),
            "hypotheses": len(spec.get("hypotheses", []) or []),
            "lacunes": len(spec.get("lacunes", []) or []),
            "journals": journals,
            "exchanges": exchanges,
            "has_store": os.path.isdir(os.path.join(path, "store_live")),
            "chain_heads": {k: v.get("chain_head", "")
                            for k, v in (run_outcome.get("journals", {}) or {}).items()},
        })
    return runs


def _resolve_run_dir(settings: Settings, run_id: str) -> str:
    for rid, path in _find_run_dirs(settings):
        if rid == run_id:
            return path
    raise FileNotFoundError("run not found: %s" % run_id)


def load_run_bundle(run_id: str, settings: Optional[Settings] = None) -> Dict[str, Any]:
    """Full run dossier: spec + outcomes + exchanges + worker receipts."""
    settings = settings or load_settings()
    path = _resolve_run_dir(settings, run_id)
    bundle: Dict[str, Any] = {"run_id": run_id, "path": settings.rel(path)}
    for key, fname in (("spec", "run.json"),
                       ("outcome", "outcome_orchestrator.json"),
                       ("run_outcome", "run_outcome.json"),
                       ("worker_done_orchestrator", "worker_done_orchestrator.json"),
                       ("worker_done_critic", "worker_done_critic.json")):
        bundle[key] = read_json(os.path.join(path, fname)) if _exists(path, fname) else None
    exchanges_dir = os.path.join(path, "exchanges")
    bundle["exchanges"] = [
        {"name": name, "data": read_json(os.path.join(exchanges_dir, name))}
        for name in _listdir(exchanges_dir) if name.endswith(".json")
    ]
    store_calls = os.path.join(path, "store_live", "calls.jsonl")
    bundle["tool_calls"] = (read_jsonl(store_calls)
                            if os.path.exists(store_calls) else [])
    return bundle


def load_journal(run_id: str, agent: str = "orchestrator",
                 settings: Optional[Settings] = None) -> List[Dict[str, Any]]:
    """Journal lines of one agent, each carrying a monotonic ``seq``."""
    settings = settings or load_settings()
    path = _resolve_run_dir(settings, run_id)
    fname = "journal_critic.jsonl" if agent == "critic" else "journal_orchestrator.jsonl"
    rows = read_jsonl(os.path.join(path, fname))
    for index, row in enumerate(rows):
        row["seq"] = index
    return rows


# --------------------------------------------------------------------------
# journal hash-chain verification (the journal is chained by hash on disk)
# --------------------------------------------------------------------------

def verify_journal_chain(run_id: str, settings: Optional[Settings] = None) -> Dict[str, Any]:
    """Recompute both journal chains and compare to the recorded heads.

    Verification is real: the SHA-256 chain of every line is recomputed with
    the journal's own hashing rule and the final head is compared with the
    ``chain_head`` recorded in ``run_outcome.json`` at run time.
    """
    from orvyren.agents.journal import GENESIS_HASH, JournalEntry, entry_hash

    settings = settings or load_settings()
    path = _resolve_run_dir(settings, run_id)
    run_outcome = (read_json(os.path.join(path, "run_outcome.json"))
                   if _exists(path, "run_outcome.json") else {})
    expected = {k: v.get("chain_head", "")
                for k, v in (run_outcome.get("journals", {}) or {}).items()}
    result: Dict[str, Any] = {"run_id": run_id, "agents": {}}
    for agent, fname in (("orchestrator", "journal_orchestrator.jsonl"),
                         ("critic", "journal_critic.jsonl")):
        fpath = os.path.join(path, fname)
        if not os.path.exists(fpath):
            result["agents"][agent] = {"present": False}
            continue
        try:
            rows = read_jsonl(fpath)
        except ValueError as exc:
            # A broken line is a broken chain: report it, never crash the endpoint.
            result["agents"][agent] = {"present": True, "lines": 0, "links_ok": False,
                                       "verified": False, "error": str(exc)}
            continue
        known = {f for f in JournalEntry.__dataclass_fields__}  # type: ignore[attr-defined]
        previous = GENESIS_HASH
        links_ok = True
        head = GENESIS_HASH
        error = ""
        for index, row in enumerate(rows):
            payload = {k: v for k, v in row.items() if k in known and k != "prev_hash"}
            try:
                entry = JournalEntry(**payload)
            except (TypeError, ValueError) as exc:
                links_ok = False
                error = "unreadable journal line %d: %s" % (index, exc)
                break
            if row.get("prev_hash") != previous:
                links_ok = False
            previous = entry_hash(entry)
            head = previous
        recorded = expected.get(agent, "")
        report = {
            "present": True,
            "lines": len(rows),
            "links_ok": links_ok,
            "recomputed_head": head,
            "recorded_head": recorded,
            "verified": bool(recorded) and head == recorded and links_ok,
        }
        if error:
            report["error"] = error
        result["agents"][agent] = report
    return result


# --------------------------------------------------------------------------
# merged run timeline (what the Live screen replays over the WebSocket)
# --------------------------------------------------------------------------

_KIND_TO_EVENT = {
    "PLAN": "agent.thought",
    "REFLECTION": "agent.thought",
    "HYPOTHESIS_PROPOSED": "agent.thought",
    "BRANCH_UPDATE": "agent.thought",
    "TOOL_CALL": "agent.evidence",
    "TOOL_RESULT": "agent.evidence",
    "OBSERVATION_REF": "agent.evidence",
    "DECISION_DRAFT": "agent.decision",
    "STOP": "agent.decision",
    "CRITIQUE": "agent.critique",
    "ERROR": "agent.error",
}


def build_run_events(run_id: str, settings: Optional[Settings] = None) -> List[Dict[str, Any]]:
    """Chronological live events of a run — journal lines + exchanges + status.

    Each event is the WS envelope payload: ``type`` from the documented event
    vocabulary, ``run_id``, ``ts``, plus the untouched artefact fields.
    """
    settings = settings or load_settings()
    path = _resolve_run_dir(settings, run_id)
    entries: List[Tuple[str, int, Dict[str, Any]]] = []
    for agent, fname in (("orchestrator", "journal_orchestrator.jsonl"),
                         ("critic", "journal_critic.jsonl")):
        fpath = os.path.join(path, fname)
        if not os.path.exists(fpath):
            continue
        for order, row in enumerate(read_jsonl(fpath)):
            entries.append((row.get("ts_utc", ""), order * 2 + (1 if agent == "critic" else 0),
                            {"agent": agent, "entry": row}))
    entries.sort(key=lambda item: (item[0], item[1]))
    events: List[Dict[str, Any]] = []
    for ts, _, item in entries:
        entry = item["entry"]
        events.append({
            "type": _KIND_TO_EVENT.get(entry.get("kind", ""), "agent.thought"),
            "run_id": run_id,
            "ts": ts,
            "payload": {
                "agent": item["agent"],
                "kind": entry.get("kind", ""),
                "status": entry.get("status", ""),
                "journal_id": entry.get("journal_id", ""),
                "step_index": entry.get("step_index", 0),
                "content": entry.get("content", ""),
                "refs": entry.get("refs", []),
                "validation": entry.get("validation", {}),
                "llm": entry.get("llm", {}),
                "tokens_in": entry.get("tokens_in", 0),
                "tokens_out": entry.get("tokens_out", 0),
                "cached_in": entry.get("cached_in", 0),
                "cost_usd": entry.get("cost_usd", 0.0),
                "latency_ms": entry.get("latency_ms", 0),
                "prev_hash": entry.get("prev_hash", ""),
            },
        })
    exchanges_dir = os.path.join(path, "exchanges")
    for name in _listdir(exchanges_dir):
        if not name.endswith(".json"):
            continue
        data = read_json(os.path.join(exchanges_dir, name))
        is_critique = "critique" in name
        events.append({
            "type": "agent.critique" if is_critique else "agent.evidence",
            "run_id": run_id,
            "ts": "",
            "payload": {"exchange": name, "data": data},
        })
    outcome = (read_json(os.path.join(path, "outcome_orchestrator.json"))
               if _exists(path, "outcome_orchestrator.json") else {})
    events.append({
        "type": "run.status",
        "run_id": run_id,
        "ts": "",
        "payload": {"phase": "outcome", **outcome},
    })
    for index, event in enumerate(events):
        event["seq"] = index
    return events


# --------------------------------------------------------------------------
# episodes (the three reference stress episodes)
# --------------------------------------------------------------------------

def _episode_files(settings: Settings) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for name in _listdir(settings.evidence_dir):
        if name.startswith("episode") and name.endswith(".json"):
            full = os.path.join(settings.evidence_dir, name)
            data = read_json(full)
            episode_id = (data.get("case") or
                          re.sub(r"^episode_|\.json$", "", name).replace("_", "-"))
            out[str(episode_id)] = full
    return out


def episodes_index(settings: Optional[Settings] = None) -> List[Dict[str, Any]]:
    settings = settings or load_settings()
    index: List[Dict[str, Any]] = []
    for episode_id, path in _episode_files(settings).items():
        data = read_json(path)
        series = data.get("series") or {}
        hourly = data.get("hourly") or []
        points = len(series) if series else len(hourly)
        index.append({
            "id": episode_id,
            "file": settings.rel(path),
            "title": (data.get("meta", {}).get("episode") or
                      data.get("episode") or episode_id),
            "window": data.get("window") or {
                "start": data.get("meta", {}).get("grid_key", ""),
                "end": ""},
            "points": points,
            "headline": data.get("headline", {}),
            "events": data.get("events", []),
            "limitations": data.get("limitations", []),
        })
    return index


def load_episode(episode_id: str, settings: Optional[Settings] = None) -> Dict[str, Any]:
    settings = settings or load_settings()
    files = _episode_files(settings)
    if episode_id not in files:
        raise FileNotFoundError("episode not found: %s" % episode_id)
    return read_json(files[episode_id])


def _iso(ts: Any) -> int:
    """Epoch seconds for Lightweight Charts (UTC).

    A timestamp that carries an offset keeps it (``2023-03-11T00:00:00+02:00``
    is 2023-03-10 22:00 UTC); only naive timestamps are read as UTC. An
    unparseable value degrades to 0 (the chart shows a gap) instead of
    failing the whole series.
    """
    if isinstance(ts, (int, float)):
        return int(ts)
    from datetime import datetime, timezone

    text = str(ts).replace("Z", "+00:00")
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return 0
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return int(moment.timestamp())


def episode_series(episode_id: str, settings: Optional[Settings] = None) -> Dict[str, Any]:
    """Normalised chart series for one episode (prices + exposures + signals)."""
    settings = settings or load_settings()
    data = load_episode(episode_id, settings)
    lines: List[Dict[str, Any]] = []
    bars: List[Dict[str, Any]] = []
    events = data.get("events", [])

    if "hourly" in data:  # usdc-2023-03: per-venue hourly quotes
        venues: Dict[str, List[List[float]]] = {}
        medians: List[List[float]] = []
        lows: List[List[float]] = []
        decotes: List[List[float]] = []
        for point in data["hourly"]:
            ts = _iso(point.get("ts") or point.get("utc"))
            for venue, quote in (point.get("venues") or {}).items():
                venues.setdefault(venue, []).append([ts, float(quote.get("last", 0.0))])
            market = point.get("market") or {}
            if market.get("median") is not None:
                medians.append([ts, float(market["median"])])
            if market.get("min") is not None:
                lows.append([ts, float(market["min"])])
            signals = point.get("signals") or {}
            if signals.get("decote_min_bps") is not None:
                decotes.append([ts, float(signals["decote_min_bps"])])
        for venue, points in sorted(venues.items()):
            lines.append({"id": "price:" + venue, "label": "USDC/USD — " + venue,
                          "unit": "USD", "kind": "price", "points": points})
        lines.append({"id": "price:median", "label": "médiane multi-venues",
                      "unit": "USD", "kind": "price", "points": medians})
        lines.append({"id": "price:min", "label": "plus bas venue",
                      "unit": "USD", "kind": "price", "points": lows})
        bars.append({"id": "signal:decote_min_bps", "label": "décote minimale",
                     "unit": "bps", "kind": "signal", "points": decotes})
    elif "series" in data:  # steth / rseth: per-block snapshots
        keys = sorted(data["series"].keys())
        first = data["series"][keys[0]] if keys else {}
        if "discount" in first:  # stETH: curve discount by trade size
            sizes = sorted(first.get("discount", {}).keys(), key=lambda s: float(s))
            for size in sizes:
                points = []
                for key in keys:
                    entry = data["series"][key].get("discount", {}).get(size)
                    if entry:
                        points.append([_iso(data["series"][key].get("ts") or key),
                                       float(entry.get("discount_bps", 0.0))])
                lines.append({"id": "discount:" + size,
                              "label": "décote %s stETH" % size,
                              "unit": "bps", "kind": "discount", "points": points})
            chainlink = []
            ratios = []
            for key in keys:
                entry = data["series"][key]
                ts = _iso(entry.get("ts") or key)
                cl = entry.get("chainlink_steth_eth") or {}
                if cl.get("price") is not None:
                    chainlink.append([ts, float(cl["price"])])
                pool = entry.get("pool_balances") or {}
                if pool.get("ratio_steth_per_eth") is not None:
                    ratios.append([ts, float(pool["ratio_steth_per_eth"])])
            lines.append({"id": "chainlink:steth_eth", "label": "Chainlink stETH/ETH",
                          "unit": "ETH", "kind": "price", "points": chainlink})
            lines.append({"id": "pool:ratio_steth_per_eth",
                          "label": "ratio pool stETH/ETH", "unit": "ratio",
                          "kind": "exposure", "points": ratios})
        else:  # rsETH: Aave V3 reserve metrics per asset
            assets = [k for k in first.keys() if isinstance(first[k], dict)]
            metrics = (("cash", "liquidité (cash)", "exposure"),
                       ("variable_debt_supply", "dette variable", "exposure"),
                       ("a_token_supply", "supply aToken", "exposure"),
                       ("utilisation", "utilisation", "signal"),
                       ("cap_ratio", "remplissage du cap", "signal"),
                       ("oracle_price", "prix oracle", "price"))
            for asset in assets:
                for metric, label, kind in metrics:
                    points = []
                    for key in keys:
                        entry = data["series"][key].get(asset) or {}
                        if entry.get(metric) is not None:
                            points.append([_iso(data["series"][key].get("ts") or key),
                                           float(entry[metric])])
                    if points:
                        lines.append({"id": "%s:%s" % (asset, metric),
                                      "label": "%s — %s" % (asset, label),
                                      "unit": metric, "kind": kind, "points": points})
    return {
        "id": episode_id,
        "title": (data.get("meta", {}).get("episode") or
                  data.get("episode") or episode_id),
        "window": data.get("window") or {},
        "lines": lines,
        "bars": bars,
        "events": events,
        "headline": data.get("headline", {}),
        "notes": data.get("notes", []),
        "limitations": data.get("limitations", []),
        "rpc_provenance": data.get("rpc_provenance", {}),
    }


# --------------------------------------------------------------------------
# decision + policy + execution
# --------------------------------------------------------------------------

def decision_case(case_id: str, settings: Optional[Settings] = None) -> Dict[str, Any]:
    """Decision artefact of a case: axes, RDOF trace, verdicts, provenance."""
    settings = settings or load_settings()
    path = os.path.join(settings.evidence_dir, "decision_%s.json" % case_id)
    if not os.path.exists(path):
        raise FileNotFoundError("decision not found: %s" % case_id)
    return read_json(path)


def decision_record(case_id: str, settings: Optional[Settings] = None) -> Dict[str, Any]:
    settings = settings or load_settings()
    path = os.path.join(settings.evidence_dir, "decision_record_%s.json" % case_id)
    if not os.path.exists(path):
        raise FileNotFoundError("decision record not found: %s" % case_id)
    return read_json(path)


def decision_cases(settings: Optional[Settings] = None) -> List[str]:
    settings = settings or load_settings()
    out = []
    for name in _listdir(settings.evidence_dir):
        match = re.match(r"^decision_(?!record_)(.+)\.json$", name)
        if match:
            out.append(match.group(1))
    return sorted(out)


def policy_verdicts(settings: Optional[Settings] = None) -> Dict[str, Any]:
    """The recorded policy evaluation: 3 intents x 14 rules, real verdicts."""
    settings = settings or load_settings()
    return read_json(os.path.join(settings.evidence_dir, "policy_execution_demo.json"))


def policy_effective(settings: Optional[Settings] = None) -> Dict[str, Any]:
    settings = settings or load_settings()
    root = settings.root
    out: Dict[str, Any] = {}
    eff = os.path.join(settings.evidence_dir, "demo_chain", "rseth", "policy.effective.json")
    if os.path.exists(eff):
        out["effective"] = read_json(eff)
    yaml_path = os.path.join(root, "policy_v1.yaml")
    if os.path.exists(yaml_path):
        out["policy_v1_yaml"] = read_text(yaml_path)
        out["policy_v1_path"] = settings.rel(yaml_path)
    return out


def execution_receipts(settings: Optional[Settings] = None) -> Dict[str, Any]:
    """On-chain receipts (Base Sepolia) + unsigned instructions."""
    settings = settings or load_settings()

    def collect(dirpath: str) -> List[Dict[str, Any]]:
        out = []
        for name in _listdir(dirpath):
            if not name.endswith(".json"):
                continue
            data = read_json(os.path.join(dirpath, name))
            out.append({
                "name": name,
                "tx_hash": data.get("transactionHash", ""),
                "status": data.get("status", ""),
                "block_number": data.get("blockNumber", ""),
                "from": data.get("from", ""),
                "to": data.get("to", ""),
                "contract_address": data.get("contractAddress", ""),
                "gas_used": data.get("gasUsed", ""),
                "effective_gas_price": data.get("effectiveGasPrice", ""),
                "logs": len(data.get("logs", []) or []),
                "source": settings.rel(dirpath),
                "raw": data,
            })
        return out

    setup = os.path.join(settings.demo_runs_dir, "setup")
    chain = os.path.join(settings.evidence_dir, "demo_chain", "rseth", "receipts")
    out: Dict[str, Any] = {
        "setup_receipts": collect(os.path.join(setup, "receipts")),
        "chain_receipts": collect(chain),
    }
    for key, fname in (("tx_hashes", "tx_hashes.json"), ("setup_chain", "setup_chain.json"),
                       ("simulations", "simulations.json"),
                       ("encodages", "encodages_simulations.json")):
        path = os.path.join(setup, fname)
        if os.path.exists(path):
            out[key] = read_json(path)
    return out


# --------------------------------------------------------------------------
# audit
# --------------------------------------------------------------------------

def _verify_hashed_jsonl(rows: Sequence[Mapping[str, Any]],
                         hash_field: str, prev_field: str,
                         genesis: str) -> Dict[str, Any]:
    """Verify a hash-chained JSONL stream; try the canonical hash forms.

    Returns link status + which serialisation (if any) reproduces the stored
    hashes. Honest output: if no form matches, the algorithm is reported as
    not reproduced rather than claimed verified.
    """
    import hashlib

    def digest(payload: Mapping[str, Any]) -> str:
        text = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, default=str)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    variants = {
        "all_minus_hash": lambda r: {k: v for k, v in r.items() if k != hash_field},
        "all_minus_hash_prev": lambda r: {k: v for k, v in r.items()
                                          if k not in (hash_field, prev_field)},
    }
    links_ok = True
    previous = genesis
    match_form = ""
    for row in rows:
        if row.get(prev_field) != previous:
            links_ok = False
        previous = row.get(hash_field, "")
    if rows:
        for name, strip in variants.items():
            head = genesis
            ok = True
            for row in rows:
                if row.get(prev_field) != head:
                    ok = False
                    break
                head = digest(strip(row))
            if ok:
                match_form = name
                break
    return {
        "records": len(rows),
        "links_ok": links_ok,
        "head": previous,
        "genesis_ok": bool(rows) and rows[0].get(prev_field) == genesis,
        "hash_form": match_form or "not_reproduced",
        "verified": links_ok and bool(match_form),
    }


def audit_summary(settings: Optional[Settings] = None) -> Dict[str, Any]:
    """Audit dossier: PIT snapshots, provenance, sealed packets, chain status."""
    settings = settings or load_settings()
    out: Dict[str, Any] = {"snapshots": [], "packets": [], "chains": []}

    snaps_dir = os.path.join(settings.evidence_dir, "graph_snapshots")
    for name in _listdir(snaps_dir):
        dirpath = os.path.join(snaps_dir, name)
        if not os.path.isdir(dirpath):
            continue
        item: Dict[str, Any] = {"id": name, "path": settings.rel(dirpath)}
        for key, fname in (("snapshot", "graph_snapshot.json"),
                           ("provenance", "provenance.json")):
            path = os.path.join(dirpath, fname)
            if os.path.exists(path):
                item[key] = read_json(path)
        manifest = os.path.join(dirpath, "MANIFEST.sha256")
        if os.path.exists(manifest):
            item["manifest"] = read_text(manifest)
        out["snapshots"].append(item)

    packets_dir = os.path.join(settings.evidence_dir, "audit_packets")
    for name in _listdir(packets_dir):
        if not name.endswith(".zip"):
            continue
        path = os.path.join(packets_dir, name)
        packet: Dict[str, Any] = {"name": name, "path": settings.rel(path),
                                  "size": os.path.getsize(path)}
        sha_side = path + ".sha256"
        if os.path.exists(sha_side):
            packet["sha256_file"] = read_text(sha_side).strip()
        try:
            with zipfile.ZipFile(path) as zf:
                packet["files"] = [{"name": info.filename, "size": info.file_size}
                                   for info in zf.infolist()]
        except zipfile.BadZipFile:
            packet["files"] = []
        out["packets"].append(packet)

    chain_dir = os.path.join(settings.evidence_dir, "demo_chain", "rseth")
    audit_path = os.path.join(chain_dir, "audit.jsonl")
    if os.path.exists(audit_path):
        rows = read_jsonl(audit_path)
        check = _verify_hashed_jsonl(rows, "record_hash", "prev_hash", "0" * 64)
        out["chains"].append({
            "name": "demo_chain/rseth/audit.jsonl",
            "path": settings.rel(audit_path),
            "run_id": rows[0].get("run_id", "") if rows else "",
            "first_kind": rows[0].get("kind", "") if rows else "",
            "last_kind": rows[-1].get("kind", "") if rows else "",
            **check,
        })
    manifest = os.path.join(chain_dir, "MANIFEST.sha256")
    if os.path.exists(manifest):
        out["manifest"] = read_text(manifest)
    return out


def audit_stream(name: str = "exec", after_seq: int = 0, limit: int = 200,
                 settings: Optional[Settings] = None) -> Dict[str, Any]:
    """Paginated read of the on-chain execution audit stream."""
    settings = settings or load_settings()
    allowed = {"exec": os.path.join(settings.evidence_dir, "demo_chain", "rseth",
                                    "audit.jsonl")}
    path = allowed.get(name)
    if not path or not os.path.exists(path):
        raise FileNotFoundError("audit stream not found: %s" % name)
    rows = read_jsonl(path)
    window = [row for row in rows if row.get("seq", 0) > after_seq][:limit]
    return {"stream": name, "total": len(rows), "returned": len(window),
            "after_seq": after_seq, "records": window,
            "has_more": bool(rows) and rows[-1].get("seq", 0) >
            (window[-1].get("seq", 0) if window else after_seq)}


# --------------------------------------------------------------------------
# market corpus
# --------------------------------------------------------------------------

def corpus_index(settings: Optional[Settings] = None) -> Dict[str, Any]:
    settings = settings or load_settings()
    out: Dict[str, Any] = {"series": [], "observations_csv": None}
    series_dir = os.path.join(settings.corpus_dir, "series")
    for name in _listdir(series_dir):
        if not name.endswith(".json"):
            continue
        path = os.path.join(series_dir, name)
        data = read_json(path)
        observations = data.get("observations") or {}
        points = (len(observations) if isinstance(observations, (list, dict))
                  else len(data.get("windows", {})))
        out["series"].append({
            "name": name,
            "path": settings.rel(path),
            "asset": data.get("asset", ""),
            "contract": data.get("contract", ""),
            "schema": data.get("schema", ""),
            "points": points,
            "size": os.path.getsize(path),
        })
    csv_path = os.path.join(settings.corpus_dir, "usdc_observations.csv")
    if os.path.exists(csv_path):
        out["observations_csv"] = {"path": settings.rel(csv_path),
                                   "size": os.path.getsize(csv_path)}
    return out
