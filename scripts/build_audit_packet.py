#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — audit packet builder v2 (W6 lots L6.1-L6.2).

Assembles the full auditor bundle (B6_AUDIT_ETUDE.md §1.5) from a demo
session + the frozen evidence artefacts:

  * audit.jsonl        — execution stream (+ 3 LINK + 1 SEAL junction, §1.4)
  * graph/             — knowledge stream: graph_delta.jsonl (chained) +
                         graph_snapshot.json + provenance.json
  * dossier_*.md/html  — re-rendered here (packet-relative paths) with a fixed
                         generated_at, so A4 re-rendering is byte-identical
  * decision_*.json + extras + receipts/ + policy/ + fixtures/
  * manifest.json      — streams/heads/versions (never its own digest, §1.4)
  * verify/            — FROZEN third-party verifier (double distribution,
                         §2.8) + VERIFY_EXPECTED.txt + MUTATE_TEST_RESULTS.json
  * README_AUDIT.md (EN), HASHES.txt + bundle_digest, zip + .sha256

Offline, stdlib only, and honest: a piece that is absent is declared in
``manifest.missing_pieces`` — never fabricated.

Usage:
    python scripts/build_audit_packet.py --session evidence/demo_runs/rseth \
        --case rseth --evidence evidence --corpus corpus/usdc_observations.csv \
        --out-dir dist/audit_packets
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
import zipfile
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

GENESIS = "0" * 64
SELF_HASH_ZERO = "0" * 64


# --------------------------------------------------------------------------- #
# Small helpers (the journal rule lives here AND in the verifier; the
# mutation self-test keeps both sides honest — B6 §2.7 M2)
# --------------------------------------------------------------------------- #

def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as handle:
            return sha256_hex(handle.read())
    except OSError:
        return None


def read_jsonl(path: str) -> List[Any]:
    out: List[Any] = []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    except OSError:
        pass
    return out


def load_json(path: str, default: Any = None) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: str, payload: Any, indent: int = 1) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=indent, sort_keys=True)
        handle.write("\n")


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def copy_if_exists(source: str, destination: str) -> bool:
    if not os.path.isfile(source):
        return False
    os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
    shutil.copyfile(source, destination)
    return True


def chain_head(records: Sequence[Dict[str, Any]]) -> str:
    head = GENESIS
    for record in records:
        body = {key: value for key, value in record.items() if key != "record_hash"}
        head = sha256_hex(canonical_json(body).encode("utf-8"))
        if record.get("record_hash") != head or record.get("prev_hash") != (
                GENESIS if head == record.get("record_hash") and False else record.get("prev_hash")):
            pass  # verification is the verifier's job; head extraction stays simple
    return head


def append_chained(path: str, base_head: str, records: List[Dict[str, Any]]) -> str:
    """Append ``records`` to a JSONL chain; returns the new head."""
    head = base_head
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        for record in records:
            body = dict(record)
            body.pop("record_hash", None)
            body["prev_hash"] = head
            record_hash = sha256_hex(canonical_json(body).encode("utf-8"))
            body["record_hash"] = record_hash
            handle.write(canonical_json(body) + "\n")
            head = record_hash
    return head


def verify_chain(records: Sequence[Dict[str, Any]]) -> Tuple[bool, str]:
    head = GENESIS
    for index, record in enumerate(records, 1):
        if not isinstance(record, dict):
            return False, "unparsable record at position %d" % index
        body = {key: value for key, value in record.items() if key != "record_hash"}
        recomputed = sha256_hex(canonical_json(body).encode("utf-8"))
        if recomputed != record.get("record_hash"):
            return False, "record_hash mismatch at position %d" % index
        if record.get("prev_hash") != head:
            return False, "prev_hash break at position %d" % index
        head = recomputed
    return True, head


# --------------------------------------------------------------------------- #
# Upstream artifacts the packet must never fabricate
# --------------------------------------------------------------------------- #

TXT_PROVES = (
    "**What this audit packet proves.** (1) **Integrity** — no byte of the dossier or its "
    "journals has changed since sealing: any alteration breaks a hash chain or the dossier "
    "self-hash (INV-INTEGRITY). (2) **Recomputability** — every determinant computation "
    "(policy verdicts, dossier re-rendering, graph snapshot, intent↔receipt matching) is "
    "recomputed **offline** by a third party from the supplied pieces alone: same inputs, "
    "same versions, same outputs. (3) **Intent↔execution correspondence** — each recorded "
    "transaction is tied to an intent and a policy verdict and cross-checked against the "
    "public receipt (status, block, logs). (4) **Bounded mandate** — what the agent *could* "
    "do is a public, dated on-chain fact; the worst case is a finite, readable number. "
    "(5) **Point-in-time admissibility (INV-PIT)** — every fact carries event and retrieval "
    "timestamps; data inadmissible at decision time is excluded from the decision path. "
    "(6) **Refusals preserved** — policy denials, rejections, quarantines and abstentions "
    "are journaled and counted. (7) **Channel independence (INV-DEPENDENCE)** — two channels "
    "from the same archive never count as two confirmations. (8) **Accountability** — every "
    "step is attributed to a versioned component with its inputs and outputs."
)

TXT_NOT_PROVES = (
    "**What this audit packet does not prove.** (1) The **truthfulness** of external "
    "sources — an oracle can be wrong while every hash is valid. (2) The **soundness** of "
    "hypotheses or the quality of decisions. (3) Any **financial performance** (returns, "
    "avoided loss, superiority over a baseline) — none is claimed. (4) **Completeness** — "
    "the packet covers signer actions and journaled steps; anything not journaled is not "
    "in it. (5) **LLM call text is not replayed** (inference nondeterminism); it is "
    "**covered by the journal** (prompts and responses archived and hashed, validators "
    "replayed). (6) Absence of **bugs** in upstream components. (7) **Legal or regulatory "
    "compliance** in any jurisdiction. (8) A **sealed digest** (if anchored) proves the "
    "integrity and dating of the anchored dossier, **not its truthfulness**."
)

README_TEMPLATE = """# ORVYREN — audit packet ({case}, run {run8})

Testnet only (Base Sepolia, chainId {chain_id}). No real funds were involved.
This packet is the auditable record of the ORVYREN demonstration run
(`run_id = {run_id}`), assembled offline by `scripts/build_audit_packet.py`.
It carries **three journals** (execution / reasoning / knowledge), sealed by a
manifest and a LINK/SEAL junction (B6 §1.4), and a **frozen copy of the
third-party verifier** (T10).

## How to verify (offline, no network, no repository needed)

```bash
unzip {name}.zip && cd {name}
# 1) file integrity: every file against HASHES.txt (and the bundle digest)
sha256sum -c HASHES.txt        # the verifier redoes this check (A3) if coreutils is absent
# 2) full offline verification — expected: VERDICT: OFFLINE_PASS
python verify/orvyren_verify.py .
# 3) mutation self-test — expected: 6/6 mutations detected
python verify/orvyren_verify.py . --mutate-test
```

With network (optional, separate verdict): `python verify/orvyren_verify.py . --rpc https://sepolia.base.org`
re-reads every recorded transaction from the chain and re-matches it to its intent.

## What this audit packet proves

{txt_proves}

## What this audit packet does not prove

{txt_not_proves}

## Inventory

{inventory}

## Notes

- **Three streams, one manifest**: `audit.jsonl` (execution), the reasoning
  stream (declared absent with a reason when the run had no LLM — never a
  simulated stream), `graph/graph_delta.jsonl` (knowledge; `graph_snapshot.json`
  and `provenance.json` carry the frozen state). The manifest fixes each
  stream's head; `audit.jsonl` then carries 3 `LINK` + 1 `SEAL` records that
  bind the chains together (B6 §1.4 — acyclic by construction).
- **Hash rules**: all digests are SHA-256; `record_hash = sha256(canonical_json(
  record minus record_hash))`, `prev_hash` = previous record of the same
  stream, genesis `0`×64. The dossier self-hash: zero the 64-hex self field,
  hash the file — reproducible with any SHA-256 tool.
- **Frozen verifier**: `verify/orvyren_verify.py` + `verify/_orvyren/` are a
  frozen copy of the repository module (`python -m orvyren.verify`); its file
  digests are listed in `HASHES.txt` (mutation M6 checks this).
- **Anchoring**: the published digest (option ii) is `BUNDLE_DIGEST.txt`
  (recomputed by verifier check A3). EAS anchoring on Base Sepolia is
  conditional (FREEZE_V2 F3) and was not executed for this packet.
- **Published zip digest**: recorded next to the zip (`<name>.zip.sha256`) —
  it cannot be inside the packet without a recursion.
"""

VERIFY_EXPECTED = """Expected result on this packet (offline, no network, no repository needed):

  python verify/orvyren_verify.py .
      -> VERDICT: OFFLINE_PASS  (all class-A checks RECOMPUTED and ok;
         class-B checks SKIPPED (offline); class-C elements COVERED)

  python verify/orvyren_verify.py . --mutate-test
      -> all 6 registered mutations detected (details:
         verify/MUTATE_TEST_RESULTS.json)

  sha256sum -c HASHES.txt
      -> every file OK (exit 0); the sealed bundle digest is the
         BUNDLE_DIGEST.txt file, recomputed by check A3

Expected class-A checks: A1.exec.chain, A1.agent.absent, A1.graph.chain,
A2.dossier.md, A2.dossier.html, A3.packet.sha256, A3.dossier.inputs,
A4.dossier.rerender.md, A4.dossier.rerender.html, A5.policy.verdicts,
A6.graph.snapshot, A7.fixtures.signals, A8.receipts.cross.
Offline, a class-B row (B1.chain.rpc) is also reported with status SKIPPED.
"""


# --------------------------------------------------------------------------- #
# Builder
# --------------------------------------------------------------------------- #

def build_packet(*, session_dir: str, case: str, evidence_dir: str,
                 corpus: str, out_dir: str,
                 graph_snapshot_dir: Optional[str] = None) -> Dict[str, Any]:
    session_dir = os.path.abspath(session_dir)
    evidence_dir = os.path.abspath(evidence_dir)
    corpus = os.path.abspath(corpus)
    if not os.path.isdir(session_dir):
        raise SystemExit("E_SESSION: %s missing" % session_dir)

    session = load_json(os.path.join(session_dir, "session.json"), default={}) or {}
    journal_source = os.path.join(session_dir, "audit.jsonl")
    session_records = read_jsonl(journal_source)
    if not session_records:
        raise SystemExit("E_JOURNAL: %s missing or empty" % journal_source)
    chain_ok, session_head = verify_chain(session_records)
    if not chain_ok:
        raise SystemExit("E_JOURNAL_CHAIN: %s (%s)" % (journal_source, session_head))
    run_id = str(session.get("run_id")
                 or session_records[0].get("run_id") or "unknown-run")
    run8 = run_id[:8]
    mode = str(session.get("mode") or session_records[0].get("mode") or "LIVE")
    chain_id = int(session.get("chain_id") or 84532)

    now = dt.datetime.now(dt.timezone.utc)
    assembled_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    name = "audit_packet_%s_%s_%s" % (case, now.strftime("%Y%m%d-%H%M"), run8)
    staging = os.path.join(os.path.abspath(out_dir), name)
    if os.path.isdir(staging):
        shutil.rmtree(staging)
    os.makedirs(staging)

    missing: List[Dict[str, str]] = []

    def place(source: str, relative: str, label: str, required: bool = True) -> Optional[str]:
        destination = os.path.join(staging, relative)
        if not copy_if_exists(source, destination):
            if required:
                missing.append({"piece": label, "path": source, "reason": "absent"})
            return None
        return destination

    # --- decision + extras ---------------------------------------------------
    decision_src = os.path.join(evidence_dir, "decision_usdc-2023-03.json")
    decision_rel = "decision_usdc-2023-03.json"
    place(decision_src, decision_rel, "vérité machine du dossier")
    extras_placed: Dict[str, str] = {}
    for extra in ("baseline_report.json", "quality_report.json", "policy_execution_demo.json"):
        if place(os.path.join(evidence_dir, extra), extra, "extra: %s" % extra,
                 required=False):
            extras_placed[extra.split(".")[0]] = extra

    # --- dossier re-rendered for the packet (fixed generated_at) -------------
    from orvyren.audit import dossier as dossier_mod
    dossier_mod._REPO_ROOT = staging  # packet-relative display paths (portable)
    built = dossier_mod.build(
        os.path.join(staging, decision_rel), staging,
        extra_paths={label: os.path.join(staging, rel)
                     for label, rel in extras_placed.items()},
        generated_at=assembled_at)
    dossier_case = built["case"]

    # --- execution stream (+ receipts, policy, session pieces) ---------------
    cli_journal_rel = "audit.jsonl"
    place(journal_source, cli_journal_rel, "journal d'exécution chaîné")
    receipts_src = os.path.join(session_dir, "receipts")
    n_receipts = 0
    if os.path.isdir(receipts_src):
        for entry in sorted(os.listdir(receipts_src)):
            if place(os.path.join(receipts_src, entry), "receipts/%s" % entry,
                     "reçu brut", required=False):
                n_receipts += 1
    place(os.path.join(session_dir, "policy.effective.json"), "policy/policy.effective.json",
          "politique versionnée", required=False)
    place(os.path.join(REPO_ROOT, "scripts", "demo", "policy.demo.json"),
          "policy/policy.demo.json", "politique de démo", required=False)
    place(os.path.join(session_dir, "intent_registry.json"), "policy/intent_registry.json",
          "registre d'idempotence", required=False)
    place(os.path.join(session_dir, "signatures.jsonl"), "policy/signatures.jsonl",
          "journal des signatures", required=False)
    place(os.path.join(session_dir, "report.md"), "report.md", "rapport de session", required=False)

    # --- knowledge stream ----------------------------------------------------
    snap_dir = graph_snapshot_dir or os.path.join(evidence_dir, "graph_snapshots")
    graph_copied = False
    graph_records = 0
    graph_head = GENESIS
    snapshot_hash_value = None
    snapshot_path_src = None
    if os.path.isdir(snap_dir):
        candidates = sorted(os.listdir(snap_dir))
        for entry in candidates:
            candidate = os.path.join(snap_dir, entry, "graph_snapshot.json")
            if os.path.isfile(candidate):
                snapshot_path_src = candidate
        if snapshot_path_src:
            snapshot = load_json(snapshot_path_src, default={}) or {}
            snapshot_hash_value = snapshot.get("snapshot_hash")
            records = snapshot.get("records") or []
            delta_lines = []
            for index, record in enumerate(records, 1):
                delta_lines.append({
                    "v": 1, "stream": "graph", "seq": index, "run_id": run_id,
                    "episode": snapshot.get("case_id", case), "mode": "FIXTURES",
                    "ts_utc": snapshot.get("as_of"),
                    "kind": "INSERT",
                    "payload": {"obj": record.get("relation_id"),
                                "kind": record.get("kind"),
                                "family": record.get("family")},
                    "refs": {}})
            graph_records = len(delta_lines)
            delta_path = os.path.join(staging, "graph", "graph_delta.jsonl")
            os.makedirs(os.path.dirname(delta_path), exist_ok=True)
            open(delta_path, "w", encoding="utf-8", newline="\n").close()
            graph_head = append_chained(delta_path, GENESIS, delta_lines)
            shutil.copyfile(snapshot_path_src, os.path.join(staging, "graph", "graph_snapshot.json"))
            provenance_src = os.path.join(os.path.dirname(snapshot_path_src), "provenance.json")
            copy_if_exists(provenance_src, os.path.join(staging, "graph", "provenance.json"))
            graph_copied = True
    if not graph_copied:
        missing.append({"piece": "graph snapshot", "path": snap_dir,
                        "reason": "aucun export de graphe trouvé"})

    # --- fixtures (recomputation inputs for A7) ------------------------------
    fixtures: Dict[str, Any] = {}
    if copy_if_exists(corpus, os.path.join(staging, "fixtures",
                                           "corpus_usdc_observations.csv")):
        fixtures["corpus"] = "fixtures/corpus_usdc_observations.csv"
    else:
        missing.append({"piece": "corpus fixture", "path": corpus, "reason": "absent"})
    episodes = []
    for episode in ("episode_usdc_2023-03.json", "episode_rseth_2026-04.json",
                    "episode_steth_2022-06.json"):
        if copy_if_exists(os.path.join(evidence_dir, episode),
                          os.path.join(staging, "fixtures", episode)):
            episodes.append("fixtures/%s" % episode)
    fixtures["episodes"] = episodes
    graphs = []
    graphs_dir = os.path.join(REPO_ROOT, "fixtures", "graphs")
    if os.path.isdir(graphs_dir):
        for entry in sorted(os.listdir(graphs_dir)):
            if copy_if_exists(os.path.join(graphs_dir, entry),
                              os.path.join(staging, "fixtures", "graphs", entry)):
                graphs.append("fixtures/graphs/%s" % entry)
    fixtures["graphs"] = graphs

    # --- frozen verifier (double distribution, B6 §2.8) ----------------------
    frozen_root = os.path.join(staging, "verify")
    frozen_pkg = os.path.join(frozen_root, "_orvyren")
    os.makedirs(os.path.join(frozen_pkg, "policy"), exist_ok=True)
    write_text(os.path.join(frozen_pkg, "__init__.py"),
               '"""Frozen ORVYREN modules shipped with the audit packet."""\n')
    shutil.copyfile(os.path.join(REPO_ROOT, "src", "orvyren", "verify", "engine.py"),
                    os.path.join(frozen_pkg, "verify_engine.py"))
    shutil.copyfile(os.path.join(REPO_ROOT, "src", "orvyren", "audit", "dossier.py"),
                    os.path.join(frozen_pkg, "audit_dossier.py"))
    shutil.copyfile(os.path.join(REPO_ROOT, "src", "orvyren", "policy", "__init__.py"),
                    os.path.join(frozen_pkg, "policy", "__init__.py"))
    shutil.copyfile(os.path.join(REPO_ROOT, "src", "orvyren", "policy", "miniyaml.py"),
                    os.path.join(frozen_pkg, "policy", "miniyaml.py"))
    write_text(os.path.join(frozen_root, "orvyren_verify.py"),
               '#!/usr/bin/env python\n'
               '# -*- coding: utf-8 -*-\n'
               '"""Frozen ORVYREN third-party verifier (T10) — launcher.\n\n'
               'Usage: python verify/orvyren_verify.py <packet_dir> [--mutate-test] [--rpc URL]\n'
               '"""\n'
               'import os\n'
               'import sys\n\n'
               'sys.dont_write_bytecode = True  # keep the packet byte-identical\n'
               'HERE = os.path.dirname(os.path.abspath(__file__))\n'
               'sys.path.insert(0, HERE)\n\n'
               'from _orvyren.verify_engine import main  # noqa: E402\n\n'
               'if __name__ == "__main__":\n'
               '    sys.exit(main())\n')
    write_text(os.path.join(frozen_root, "VERIFY_EXPECTED.txt"), VERIFY_EXPECTED)

    # --- manifest (never its own digest nor the dossier's, B6 §1.4) ----------
    policy_effective = load_json(os.path.join(staging, "policy", "policy.effective.json"),
                                 default={}) or {}
    manifest = {
        "schema": "orvyren-audit-packet/v2",
        "case": case,
        "run_id": run_id,
        "assembled_at": assembled_at,
        "mode": mode,
        "chain_id": chain_id,
        "streams": {
            "exec": {"path": cli_journal_rel, "records": len(session_records),
                     "head_hash": session_head, "present": True},
            "agent": {"present": False,
                      "reason": "run de démonstration sans LLM (démo d'exécution) — "
                                "aucun flux simulé"},
            "graph": ({"path": "graph/graph_delta.jsonl", "records": graph_records,
                       "head_hash": graph_head, "present": True,
                       "snapshot": {"path": "graph/graph_snapshot.json",
                                    "snapshot_hash": snapshot_hash_value},
                       "delta_note": "delta dérivé du premier snapshot — chaque relation "
                                     "en INSERT, chaîné par flux"}
                      if graph_copied else
                      {"present": False, "reason": "aucun export de graphe"}), },
        "decision": {"path": decision_rel, "case": dossier_case,
                     "sha256": sha256_file(os.path.join(staging, decision_rel))},
        "dossier": {"md": "dossier_%s.md" % dossier_case,
                    "html": "dossier_%s.html" % dossier_case,
                    "case": dossier_case, "generated_at": assembled_at,
                    "inputs": {"decision": decision_rel,
                               "extras": {label: rel for label, rel in extras_placed.items()}}},
        "policy": {"version": policy_effective.get("policy_version"),
                   "file": "policy/policy.effective.json"},
        "fixtures": fixtures,
        "engine_version": "orvyren W5/W6 (packet v2)",
        "verifier": {"entry": "verify/orvyren_verify.py", "frozen": True,
                     "version": "T10/v1"},
        "missing_pieces": missing,
    }
    manifest_path = os.path.join(staging, "manifest.json")
    write_json(manifest_path, manifest)
    manifest_sha = sha256_file(manifest_path)

    # --- LINK x3 + SEAL junction (B6 §1.4, appended after the manifest) ------
    intents = [record.get("payload", {}).get("intent_id") for record in session_records
               if record.get("kind") == "INTENT"]
    base_seq = max((record.get("seq") or 0) for record in session_records) + 1
    junction = [
        {"v": 1, "stream": "exec", "seq": base_seq, "run_id": run_id, "episode": case,
         "mode": mode, "ts_utc": assembled_at, "kind": "LINK",
         "payload": {"stream": "graph", "records": graph_records, "head_hash": graph_head},
         "refs": {}},
        {"v": 1, "stream": "exec", "seq": base_seq + 1, "run_id": run_id, "episode": case,
         "mode": mode, "ts_utc": assembled_at, "kind": "LINK",
         "payload": {"stream": "decision",
                     "sha256": manifest["decision"]["sha256"], "case": dossier_case},
         "refs": {}},
        {"v": 1, "stream": "exec", "seq": base_seq + 2, "run_id": run_id, "episode": case,
         "mode": mode, "ts_utc": assembled_at, "kind": "LINK",
         "payload": {"stream": "agent", "absent": True,
                     "reason": manifest["streams"]["agent"]["reason"]},
         "refs": {}},
        {"v": 1, "stream": "exec", "seq": base_seq + 3, "run_id": run_id, "episode": case,
         "mode": mode, "ts_utc": assembled_at, "kind": "SEAL",
         "payload": {"manifest_sha256": manifest_sha,
                     "decision_sha256": manifest["decision"]["sha256"]},
         "refs": {}},
    ]
    packet_journal = os.path.join(staging, cli_journal_rel)
    append_chained(packet_journal, session_head, junction)

    # --- README (inventory is complete at this point) ------------------------
    inventory = []
    for dirpath, _dirnames, filenames in os.walk(staging):
        for entry in sorted(filenames):
            rel = os.path.relpath(os.path.join(dirpath, entry), staging).replace(os.sep, "/")
            if rel in ("README_AUDIT.md", "HASHES.txt"):
                continue
            inventory.append(rel)
    inventory = sorted(inventory)
    write_text(os.path.join(staging, "README_AUDIT.md"), README_TEMPLATE.format(
        case=case, run8=run8, run_id=run_id, chain_id=chain_id, name=name,
        txt_proves=TXT_PROVES, txt_not_proves=TXT_NOT_PROVES,
        inventory="\n".join("- `%s`" % rel for rel in inventory) or "- (none)"))

    # --- HASHES (two-file layout: HASHES.txt pure + BUNDLE_DIGEST.txt) -------
    def walk_packet_files() -> List[List[str]]:
        files: List[List[str]] = []
        for dirpath, dirnames, filenames in os.walk(staging):
            dirnames[:] = [name for name in dirnames if name != "__pycache__"]
            for entry in sorted(filenames):
                if entry.endswith(".pyc"):
                    continue
                full = os.path.join(dirpath, entry)
                rel = os.path.relpath(full, staging).replace(os.sep, "/")
                if rel == "HASHES.txt":
                    continue
                files.append([rel, sha256_file(full)])
        files.sort()
        return files

    def bundle_of(files: List[List[str]]) -> str:
        digest_input = sorted([rel, digest] for rel, digest in files
                              if rel != "BUNDLE_DIGEST.txt"
                              and not (rel.startswith("dossier_")
                                       and (rel.endswith(".md") or rel.endswith(".html"))))
        return sha256_hex(canonical_json(digest_input).encode("utf-8"))

    def finalize_hashes() -> Tuple[List[List[str]], str]:
        """Write BUNDLE_DIGEST.txt first, then HASHES.txt listing every file
        (BUNDLE_DIGEST.txt included) — deterministic, no self-reference."""
        bundle = bundle_of(walk_packet_files())
        write_text(os.path.join(staging, "BUNDLE_DIGEST.txt"),
                   "bundle_digest  %s\n" % bundle)
        files = walk_packet_files()
        with open(os.path.join(staging, "HASHES.txt"), "w",
                  encoding="utf-8", newline="\n") as handle:
            for rel, digest in files:
                handle.write("%s  %s\n" % (digest, rel))
        return files, bundle

    files, bundle_digest = finalize_hashes()

    from orvyren.verify.engine import verify_packet
    mutation_report = verify_packet(staging, with_mutations=True)
    mutations = mutation_report.get("mutations", [])
    detected = sum(1 for entry in mutations if entry.get("detected"))
    write_json(os.path.join(frozen_root, "MUTATE_TEST_RESULTS.json"),
               {"detected": detected, "total": len(mutations), "results": mutations})

    files, bundle_digest = finalize_hashes()

    final_report = verify_packet(staging)
    if final_report.get("verdict") not in ("PASS", "OFFLINE_PASS") or detected != len(mutations):
        write_json(os.path.join(os.path.abspath(out_dir), "BUILD_FAILED_REPORT.json"),
                   final_report)
        raise SystemExit("E_BUILD: expected OFFLINE_PASS, got %s (mutations %d/%d) — "
                         "full report in BUILD_FAILED_REPORT.json"
                         % (final_report.get("verdict"), detected, len(mutations)))

    # --- zip + published digest ---------------------------------------------
    for dirpath, dirnames, _filenames in os.walk(staging):
        for directory in list(dirnames):
            if directory == "__pycache__":
                shutil.rmtree(os.path.join(dirpath, directory), ignore_errors=True)
    zip_path = os.path.join(os.path.abspath(out_dir), "%s.zip" % name)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for dirpath, _dirnames, filenames in os.walk(staging):
            for entry in sorted(filenames):
                full = os.path.join(dirpath, entry)
                archive.write(full, os.path.join(name, os.path.relpath(full, staging)))
    zip_digest = sha256_file(zip_path)
    write_text("%s.sha256" % zip_path, "%s  %s.zip\n" % (zip_digest, name))

    return {
        "packet_dir": staging,
        "zip_path": zip_path,
        "zip_sha256": zip_digest,
        "bundle_digest": bundle_digest,
        "verdict": final_report.get("verdict"),
        "checks": len(final_report.get("checks", [])),
        "mutations": "%d/%d" % (detected, len(mutations)),
        "files": len(files) + 1,
        "missing_pieces": missing,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="build_audit_packet.py",
        description="ORVYREN — assemble the full audit packet v2 (W6), freeze the "
                    "verifier, self-test the mutations, zip. Offline; never fabricates "
                    "a missing piece (declared in manifest.missing_pieces).")
    parser.add_argument("--session", required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--evidence", default=os.path.join(REPO_ROOT, "evidence"))
    parser.add_argument("--corpus", default=os.path.join(REPO_ROOT, "corpus",
                                                         "usdc_observations.csv"))
    parser.add_argument("--graph-snapshot-dir", default=None)
    parser.add_argument("--out-dir", default=os.path.join(REPO_ROOT, "dist", "audit_packets"))
    args = parser.parse_args(argv)

    summary = build_packet(session_dir=args.session, case=args.case,
                           evidence_dir=args.evidence, corpus=args.corpus,
                           out_dir=args.out_dir,
                           graph_snapshot_dir=args.graph_snapshot_dir)
    print("ORVYREN — audit packet v2 assembled")
    print("  packet        : %s (%d files)" % (summary["packet_dir"], summary["files"]))
    print("  zip           : %s" % summary["zip_path"])
    print("  zip sha256    : %s" % summary["zip_sha256"])
    print("  bundle_digest : %s" % summary["bundle_digest"])
    print("  verification  : %s (%d checks), mutations %s"
          % (summary["verdict"], summary["checks"], summary["mutations"]))
    if summary["missing_pieces"]:
        print("  declared missing pieces: %d" % len(summary["missing_pieces"]))
        for item in summary["missing_pieces"]:
            print("    - %s (%s)" % (item["piece"], item["reason"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
