#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — testnet demo kit: **audit packet assembly** (B6 §5).

NOTE (W6): **historical v1 builder of the kit** (simple layout). The full
T10 packet — multiple streams + LINK/SEAL, embedded frozen verifier, HASHES +
BUNDLE_DIGEST, mutation-test — is built by ``scripts/build_audit_packet.py``
(v2, repository root). The T10 verifier reads both layouts.

Assembles the deliverable dossier for the jury/reviewer:

    1  README_AUDIT.md (EN — verification in 3 commands, "what it proves / does not")
    2  dossier_<case>.md + .html          (self-hash, orvyren.audit.dossier)
    3  decision_<case>.json               (machine truth of the dossier)
    4  dossier extras                     (baseline, quality, policy_execution_demo)
    5  audit.jsonl                        (chained execution stream; + stream manifest)
    6  agent_journal.jsonl                (declared absent if the run had no LLM)
    7  graph/                             (declared absent if not exported)
    8  manifest.json                      (stream heads, versions, inventory)
    9  receipts/ + policy/                (raw receipts + versioned policy)
    10 verify/verify_hashes.py            (minimal offline verifier — T10 skeleton)
    11 HASHES.txt                         (sha256 of each file + bundle_digest)
    12 anchor/                            (empty/absent — EAS anchoring deferred, FREEZE_V2 F3)

``bundle_digest = sha256(canonical_json(sorted(files \\ {dossier_*.{md,html}, HASHES.txt})))``
(B6 annex B). The zip is named ``audit_packet_<case>_<run8>.zip`` and its sha256
is printed (anchoring "option ii": published digest, zero cost).

This script works **offline** (dry-run by default): it invents no
missing piece, it declares them absent with their reason.

CLI:

    python scripts/demo/build_audit_packet.py --session evidence/demo_runs/rseth \
        [--case rseth] [--evidence evidence] [--out dist/audit_packets] [--strict]
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import zipfile
from typing import Any, Dict, List, Optional, Tuple

try:
    from . import common
except ImportError:  # direct execution
    _sys_dir = os.path.dirname(os.path.abspath(__file__))
    if _sys_dir not in sys.path:
        sys.path.insert(0, _sys_dir)
    import common  # type: ignore  # noqa: E402

EXIT_OK = 0
EXIT_MISSING = 1
EXIT_USAGE = 2

README_TEMPLATE = """# ORVYREN — audit packet ({case}, run {run8})

Testnet only (Base Sepolia, chainId 84532). No real funds were involved.
This packet is the execution-side record of the ORVYREN demo session
(`run_id = {run_id}`), assembled offline by `scripts/demo/build_audit_packet.py`.

## How to verify (offline, no network, no repository needed)

```bash
unzip audit_packet_{case}_{run8}.zip && cd audit_packet_{case}_{run8}
# 1) file integrity: every file against HASHES.txt (and the bundle digest)
python verify/verify_hashes.py .
# 2) execution journal: recompute the SHA-256 chain of audit.jsonl line by line
python verify/verify_hashes.py . --journal audit.jsonl
# 3) (optional, with network) re-read every tx hash and re-match it to its intent
python verify/verify_hashes.py . --rpc https://sepolia.base.org
```

`HASHES.txt` lists the sha256 of every file except itself, followed by
`bundle_digest = sha256(canonical_json(sorted(files \\ {{dossier_*.md, dossier_*.html, HASHES.txt}})))`.

## What this audit packet proves

{txt_ok}

## What this audit packet does not prove

{txt_no}

## Packet inventory

{inventory}
"""

VERIFY_SCRIPT = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Offline packer verifier shipped inside the audit packet (stdlib only).

Controls:
  * every file's sha256 matches HASHES.txt (and the recomputed bundle_digest);
  * the SHA-256 chain of audit.jsonl recomputes line by line;
  * with --rpc, every SUBMIT tx hash of the journal is re-read from the chain.

This is the minimal offline verifier; the full third-party verifier
(`python -m orvyren.verify`, test T10 of research/B6_AUDIT_ETUDE.md) is not built
yet — this script does not pretend to be it.
"""
import argparse, hashlib, json, os, sys
import urllib.request


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_hashes(root):
    entries, digest = {}, None
    with open(os.path.join(root, "HASHES.txt"), "r", encoding="utf-8") as fh:
        for line in fh:
            parts = line.strip().split()
            if len(parts) == 2 and parts[0] == "bundle_digest":
                digest = parts[1]
            elif len(parts) == 2:
                # sha256sum format: <digest>  <path>
                entries[parts[1]] = parts[0]
    return entries, digest


def verify_files(root):
    entries, declared = read_hashes(root)
    problems = []
    for path, expected in sorted(entries.items()):
        full = os.path.join(root, path)
        if not os.path.isfile(full):
            problems.append("missing file: %s" % path)
            continue
        actual = sha256_file(full)
        if actual != expected:
            problems.append("sha256 mismatch: %s" % path)
    listed = set(entries)
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel in ("HASHES.txt",) or rel.startswith("audit_packet_"):
                continue
            if rel not in listed:
                problems.append("file not listed in HASHES.txt: %s" % rel)
    computed = hashlib.sha256(canonical(sorted(
        [path, digest] for path, digest in entries.items()
        if not (path.startswith("dossier_") and (path.endswith(".md") or path.endswith(".html")))
        and path != "HASHES.txt")).encode("utf-8")).hexdigest()
    if declared and declared != computed:
        problems.append("bundle_digest mismatch: declared %s computed %s" % (declared, computed))
    return problems


def verify_journal(path):
    problems, previous, count = [], {}, 0
    if not os.path.isfile(path):
        return ["journal not found: %s" % path]
    with open(path, "r", encoding="utf-8") as fh:
        for number, line in enumerate(fh, 1):
            text = line.strip()
            if not text:
                continue
            count += 1
            try:
                record = json.loads(text)
            except ValueError:
                problems.append("line %d: invalid JSON" % number)
                continue
            stored = record.pop("record_hash", None)
            computed = hashlib.sha256(canonical(record).encode("utf-8")).hexdigest()
            if stored != computed:
                problems.append("line %d: record_hash mismatch" % number)
            stream = record.get("stream")
            expected = previous.get(stream, "0" * 64)
            if record.get("prev_hash") != expected:
                problems.append("line %d: prev_hash mismatch" % number)
            previous[stream] = stored
    print("journal: %d records, heads=%s" % (count, json.dumps(previous, sort_keys=True)))
    return problems


def rpc(url, method, params):
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    request = urllib.request.Request(url, data=payload, method="POST", headers={
        "Content-Type": "application/json",
        "User-Agent": "ORVYREN-audit-verify/0.1 (offline packet verifier)"})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
    if body.get("error"):
        raise RuntimeError(body["error"])
    return body["result"]


def verify_chain(root, journal, rpc_url):
    problems = []
    with open(os.path.join(root, journal), "r", encoding="utf-8") as fh:
        for line in fh:
            record = json.loads(line)
            if record.get("kind") == "SUBMIT":
                tx_hash = (record.get("payload") or {}).get("tx_hash")
                if not tx_hash or (record.get("payload") or {}).get("simulated"):
                    print("submit (simulated): %s" % tx_hash)
                    continue
                receipt = rpc(rpc_url, "eth_getTransactionReceipt", [tx_hash])
                status = receipt.get("status") if receipt else "absent"
                print("submit %s -> status %s" % (tx_hash, status))
                if receipt is None:
                    problems.append("receipt unavailable: %s" % tx_hash)
    return problems


def main():
    parser = argparse.ArgumentParser(description="ORVYREN audit packet verifier (offline).")
    parser.add_argument("target", help="packet directory")
    parser.add_argument("--journal", default="audit.jsonl", help="journal file (default audit.jsonl)")
    parser.add_argument("--rpc", help="optional RPC URL to re-read tx hashes")
    args = parser.parse_args()
    problems = verify_files(args.target)
    problems += verify_journal(os.path.join(args.target, args.journal))
    if args.rpc:
        problems += verify_chain(args.target, args.journal, args.rpc)
    print("MODE: %s" % ("OFFLINE+RPC" if args.rpc else "OFFLINE"))
    if problems:
        print("VERDICT: FAIL")
        for problem in problems:
            print("  - %s" % problem)
        return 1
    print("VERDICT: %s" % ("OFFLINE_PASS" if not args.rpc else "PASS"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

TXT_PROVES = """(1) **Integrity** — no byte of the dossier or its journals has changed since sealing: any alteration breaks a hash chain or the dossier self-hash (INV-INTEGRITY).
(2) **Recomputability** — every determinant computation (policy verdicts, dossier re-rendering, graph snapshot, intent↔receipt matching) is recomputed **offline** by a third party from the supplied pieces alone: same inputs, same versions, same outputs.
(3) **Intent↔execution correspondence** — each recorded transaction is tied to an intent and a policy verdict and cross-checked against the public receipt (status, block, logs).
(4) **Bounded mandate** — what the agent *could* do is a public, dated on-chain fact; the worst case is a finite, readable number.
(5) **Point-in-time admissibility (INV-PIT)** — every fact carries event and retrieval timestamps; data inadmissible at decision time is excluded from the decision path.
(6) **Refusals preserved** — policy denials, rejections, quarantines and abstentions are journaled and counted.
(7) **Channel independence (INV-DEPENDENCE)** — two channels from the same archive never count as two confirmations.
(8) **Accountability** — every step is attributed to a versioned component with its inputs and outputs."""

TXT_NOT_PROVES = """(1) The **truthfulness** of external sources — an oracle can be wrong while every hash is valid.
(2) The **soundness** of hypotheses or the quality of decisions.
(3) Any **financial performance** (returns, avoided loss, superiority over a baseline) — none is claimed.
(4) **Completeness** — the packet covers signer actions and journaled steps; anything not journaled is not in it.
(5) **LLM call text is not replayed** (inference nondeterminism); it is **covered by the journal**.
(6) Absence of **bugs** in upstream components.
(7) **Legal or regulatory compliance** in any jurisdiction.
(8) A **sealed digest** (if anchored) proves the integrity and dating of the anchored dossier, **not its truthfulness**."""


def _copy_if_exists(source: str, destination_dir: str, name: Optional[str] = None) -> Optional[str]:
    if not os.path.isfile(source):
        return None
    os.makedirs(destination_dir, exist_ok=True)
    target = os.path.join(destination_dir, name or os.path.basename(source))
    shutil.copyfile(source, target)
    return target


def build_packet(*, session_dir: str, case: str, evidence_dir: str, out_dir: Optional[str] = None,
                 strict: bool = False) -> Dict[str, Any]:
    session_dir = os.path.abspath(session_dir)
    if not os.path.isdir(session_dir):
        raise common.ConfigurationError("nonexistent session: {}".format(session_dir))
    session = common.load_json(os.path.join(session_dir, "session.json"), default={}) or {}
    run_id = str(session.get("run_id") or common.ulid())
    run8 = run_id[:8]
    name = "audit_packet_{}_{}".format(case, run8)
    staging = os.path.join(session_dir, "packet", name)
    if os.path.isdir(staging):
        shutil.rmtree(staging)
    os.makedirs(staging)

    missing: List[Dict[str, str]] = []
    inventory: List[Tuple[str, str]] = []

    def place(source: str, relative: str, label: str, required: bool = True) -> Optional[str]:
        destination = os.path.join(staging, relative)
        copied = _copy_if_exists(source, os.path.dirname(destination), os.path.basename(destination))
        if copied is None:
            if required:
                missing.append({"piece": label, "path": source, "reason": "absent"})
            return None
        inventory.append((relative, label))
        return destination

    # 2/3/4 — the decision dossier and its extras (produced by orvyren.audit.dossier)
    place(os.path.join(evidence_dir, "dossier_{}.md".format(case)), "dossier_{}.md".format(case),
          "dossier md (self-hash)")
    place(os.path.join(evidence_dir, "dossier_{}.html".format(case)), "dossier_{}.html".format(case),
          "dossier html (self-hash)")
    place(os.path.join(evidence_dir, "decision_{}.json".format(case)), "decision_{}.json".format(case),
          "machine truth of the dossier")
    for extra in ("baseline_report.json", "quality_report.json", "policy_execution_demo.json"):
        place(os.path.join(evidence_dir, extra), extra, "extra: {}".format(extra), required=False)

    # 5 — the chained execution journal
    journal_source = os.path.join(session_dir, "audit.jsonl")
    place(journal_source, "audit.jsonl", "chained execution journal")

    # 6/7 — streams not produced by this run (declared absent, never invented)
    streams = {
        "exec": {"path": "audit.jsonl", "records": len(common.read_jsonl(journal_source)),
                 "head_hash": None, "present": os.path.isfile(journal_source)},
        "agent": {"present": False, "reason": "demo run without LLM (execution demo)"},
        "graph": {"present": False, "reason": "no graph export attached to this run"},
    }

    # 9 — raw receipts + versioned policy
    receipts_src = os.path.join(session_dir, "receipts")
    if os.path.isdir(receipts_src):
        for name_file in sorted(os.listdir(receipts_src)):
            place(os.path.join(receipts_src, name_file), "receipts/{}".format(name_file), "raw receipt", required=False)
    place(os.path.join(session_dir, "policy.effective.json"), "policy/policy.effective.json",
          "versioned policy", required=False)
    place(os.path.join(common.HERE, "policy.demo.json"), "policy/policy.demo.json", "demo policy", required=False)
    place(os.path.join(session_dir, "intent_registry.json"), "policy/intent_registry.json",
          "idempotency registry", required=False)
    place(os.path.join(session_dir, "signatures.jsonl"), "policy/signatures.jsonl",
          "signature log (counter)", required=False)

    # 5bis — the session manifest (written by run E) and the human-readable report
    place(os.path.join(session_dir, "export", "manifest.json"), "manifest.json",
          "session manifest", required=False)
    place(os.path.join(session_dir, "report.md"), "report.md", "human-readable report", required=False)

    # 10 — minimal offline verifier (the full T10 verifier does not exist yet)
    os.makedirs(os.path.join(staging, "verify"), exist_ok=True)
    with open(os.path.join(staging, "verify", "verify_hashes.py"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(VERIFY_SCRIPT)
    note = ("The full third-party verifier (`python -m orvyren.verify`, test T10) is NOT built yet "
            "(research/B6_AUDIT_ETUDE.md §2 constat). This packet ships the minimal offline verifier only, "
            "which checks file digests, the journal hash chain and (with --rpc) the tx hashes. "
            "It must not be presented as T10.\n")
    with open(os.path.join(staging, "verify", "VERIFY_NOT_BUILT.txt"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(note)

    # 12 — anchoring (deferred): empty folder with the reason, never a fake artifact
    os.makedirs(os.path.join(staging, "anchor"), exist_ok=True)
    with open(os.path.join(staging, "anchor", "README_ANCHOR.txt"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("EAS anchoring is conditional (FREEZE_V2 F3) and was not executed for this session. "
                     "The published digest required by option (ii) is the `bundle_digest` of HASHES.txt.\n")

    # 1 — README (the inventory is complete at this point: pieces + verifier)
    inventory.append(("README_AUDIT.md", "verification instructions (EN)"))
    inventory.append(("verify/verify_hashes.py", "minimal offline verifier"))
    inventory.append(("verify/VERIFY_NOT_BUILT.txt", "note on the missing full T10 verifier"))
    inventory.append(("manifest.json", "packet manifest"))
    inventory.append(("anchor/README_ANCHOR.txt", "anchoring note (deferred)"))
    inventory.append(("HASHES.txt", "sha256 of each file + bundle_digest"))
    with open(os.path.join(staging, "README_AUDIT.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(README_TEMPLATE.format(
            case=case, run8=run8, run_id=run_id, txt_ok=TXT_PROVES, txt_no=TXT_NOT_PROVES,
            inventory="\n".join("- `{}` — {}".format(path, label) for path, label in inventory)
                      or "- (no piece)"))

    # 8 — packet manifest (stream heads, versions, inventory — no digests: hash stability)
    journal = common.read_jsonl(journal_source) if os.path.isfile(journal_source) else []
    journal_records = [record for record in journal if isinstance(record, dict)]
    if journal_records:
        chain = common.Journal(journal_source, run_id=run_id, episode=case)
        verification = chain.verify()
        streams["exec"]["head_hash"] = verification["heads"].get("exec")
        streams["exec"]["chain_ok"] = verification["ok"]
    manifest = {
        "schema": "orvyren-audit-packet/v1",
        "case": case,
        "run_id": run_id,
        "assembled_at": common.utc_now(),
        "mode": session.get("mode"),
        "chain_id": session.get("chain_id", common.CHAIN_ID_DEMO),
        "streams": streams,
        "policy": {"version": (common.load_json(os.path.join(session_dir, "policy.effective.json"),
                                                default={}) or {}).get("policy_version")},
        "engine_version": "orvyren-demo-kit W3-D",
        "verifier": {"full_t10": "not built", "shipped": "verify/verify_hashes.py"},
        "missing_pieces": missing,
        "files": [path for path, _label in inventory],
        "note": "The zip sha256 is published next to the zip (<name>.zip.sha256): it cannot be "
                "written inside the packet without creating a recursion.",
    }
    common.write_json(os.path.join(staging, "manifest.json"), manifest)

    # 11 — HASHES.txt + bundle_digest (computed AFTER the last write into the packet)
    files: List[List[str]] = []
    for dirpath, _dirnames, filenames in os.walk(staging):
        for entry in sorted(filenames):
            full = os.path.join(dirpath, entry)
            relative = os.path.relpath(full, staging).replace(os.sep, "/")
            if relative == "HASHES.txt":
                continue
            files.append([relative, common.sha256_hex(open(full, "rb").read())])
    files.sort()
    digest_input = sorted([path, digest] for path, digest in files
                          if path != "HASHES.txt"
                          and not (path.startswith("dossier_") and (path.endswith(".md") or path.endswith(".html"))))
    bundle_digest = common.sha256_hex(common.canonical_json(digest_input).encode("utf-8"))
    with open(os.path.join(staging, "HASHES.txt"), "w", encoding="utf-8", newline="\n") as handle:
        for path, digest in files:
            handle.write("{}  {}\n".format(digest, path))
        handle.write("bundle_digest  {}\n".format(bundle_digest))

    # named + hashed zip (the zip sha256 is published next to it — anchoring option ii)
    destination_dir = out_dir or os.path.join(session_dir, "packet")
    os.makedirs(destination_dir, exist_ok=True)
    zip_path = os.path.join(destination_dir, "{}.zip".format(name))
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for dirpath, _dirnames, filenames in os.walk(staging):
            for entry in sorted(filenames):
                full = os.path.join(dirpath, entry)
                archive.write(full, os.path.join(name, os.path.relpath(full, staging)))
    zip_digest = common.sha256_hex(open(zip_path, "rb").read())
    with open("{}.sha256".format(zip_path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("{}  {}.zip\n".format(zip_digest, name))

    return {
        "packet_dir": staging,
        "zip_path": zip_path,
        "zip_sha256": zip_digest,
        "bundle_digest": bundle_digest,
        "missing_pieces": missing,
        "files": len(files) + 1,
    }


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="build_audit_packet.py",
        description="ORVYREN — audit packet assembly (B6 §5): pieces, HASHES.txt, bundle_digest, zip. "
                    "Offline; fabricates no missing piece (it is declared absent).")
    parser.add_argument("--session", default=None,
                        help="demo session directory (default: evidence/demo_runs/<case>)")
    parser.add_argument("--case", default="rseth", help="case label (default: rseth)")
    parser.add_argument("--evidence", default=os.path.join(common.ROOT, "evidence"),
                        help="decision dossier directory (default: evidence/)")
    parser.add_argument("--out", default=None, help="zip output directory (default: <session>/packet)")
    parser.add_argument("--dry-run", action="store_true",
                        help="offline assembly (de facto default: no network is used)")
    parser.add_argument("--strict", action="store_true",
                        help="fail if a required piece is absent (decision dossier, journal)")
    args = parser.parse_args(argv)

    session_dir = args.session or os.path.join(common.ROOT, "evidence", "demo_runs", args.case)
    try:
        result = build_packet(session_dir=session_dir, case=args.case, evidence_dir=args.evidence,
                              out_dir=args.out, strict=args.strict)
    except common.ConfigurationError as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return EXIT_USAGE

    print("ORVYREN — audit packet assembled")
    print("  directory  : {}".format(common.display_path(result["packet_dir"])))
    print("  zip        : {}".format(common.display_path(result["zip_path"])))
    print("  sha256(zip): {}".format(result["zip_sha256"]))
    print("  bundle_digest (to publish — option ii, FREEZE_V2 F3): {}".format(result["bundle_digest"]))
    print("  files      : {}".format(result["files"]))
    if result["missing_pieces"]:
        print("  missing pieces (declared, never invented):")
        for piece in result["missing_pieces"]:
            print("    - {} ({})".format(piece["piece"], piece["reason"]))
    if args.strict and result["missing_pieces"]:
        return EXIT_MISSING
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
