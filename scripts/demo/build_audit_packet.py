#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — kit de démo testnet : **assemblage du paquet d'audit** (B6 §5).

Assemble le dossier livrable au jury/relecteur :

    1  README_AUDIT.md (EN — vérification en 3 commandes, « ce que ça prouve / pas »)
    2  dossier_<case>.md + .html          (self-hash, orvyren.audit.dossier)
    3  decision_<case>.json               (vérité machine du dossier)
    4  extras du dossier                  (baseline, quality, policy_execution_demo)
    5  audit.jsonl                        (flux exécution chaîné ; + manifest des flux)
    6  agent_journal.jsonl                (déclaré absent si le run sans LLM)
    7  graph/                             (déclaré absent si non exporté)
    8  manifest.json                      (têtes de flux, versions, inventaire)
    9  receipts/ + policy/                (reçus bruts + politique versionnée)
    10 verify/verify_hashes.py            (vérificateur hors-ligne minimal — squelette T10)
    11 HASHES.txt                         (sha256 de chaque fichier + bundle_digest)
    12 anchor/                            (vide/absent — ancrage EAS reporté, FREEZE_V2 F3)

``bundle_digest = sha256(canonical_json(sorted(files \\ {dossier_*.{md,html}, HASHES.txt})))``
(B6 annexe B). Le zip est nommé ``audit_packet_<case>_<run8>.zip`` et son sha256
est imprimé (ancrage « option ii » : empreinte publiée, coût nul).

Ce script fonctionne **hors ligne** (dry-run par défaut) : il n'invente aucune
pièce manquante, il les déclare absentes avec leur raison.

CLI :

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
except ImportError:  # exécution directe
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
                # format sha256sum : <digest>  <chemin>
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
        raise common.ConfigurationError("session inexistante: {}".format(session_dir))
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

    # 2/3/4 — le dossier de décision et ses extras (produits par orvyren.audit.dossier)
    place(os.path.join(evidence_dir, "dossier_{}.md".format(case)), "dossier_{}.md".format(case),
          "dossier md (self-hash)")
    place(os.path.join(evidence_dir, "dossier_{}.html".format(case)), "dossier_{}.html".format(case),
          "dossier html (self-hash)")
    place(os.path.join(evidence_dir, "decision_{}.json".format(case)), "decision_{}.json".format(case),
          "vérité machine du dossier")
    for extra in ("baseline_report.json", "quality_report.json", "policy_execution_demo.json"):
        place(os.path.join(evidence_dir, extra), extra, "extra: {}".format(extra), required=False)

    # 5 — le journal d'exécution chaîné
    journal_source = os.path.join(session_dir, "audit.jsonl")
    place(journal_source, "audit.jsonl", "journal d'exécution chaîné")

    # 6/7 — flux non produits par ce run (déclarés absents, jamais inventés)
    streams = {
        "exec": {"path": "audit.jsonl", "records": len(common.read_jsonl(journal_source)),
                 "head_hash": None, "present": os.path.isfile(journal_source)},
        "agent": {"present": False, "reason": "run de démonstration sans LLM (démo d'exécution)"},
        "graph": {"present": False, "reason": "aucun export de graphe attaché à ce run"},
    }

    # 9 — reçus bruts + politique versionnée
    receipts_src = os.path.join(session_dir, "receipts")
    if os.path.isdir(receipts_src):
        for name_file in sorted(os.listdir(receipts_src)):
            place(os.path.join(receipts_src, name_file), "receipts/{}".format(name_file), "reçu brut", required=False)
    place(os.path.join(session_dir, "policy.effective.json"), "policy/policy.effective.json",
          "politique versionnée", required=False)
    place(os.path.join(common.HERE, "policy.demo.json"), "policy/policy.demo.json", "politique de démo", required=False)
    place(os.path.join(session_dir, "intent_registry.json"), "policy/intent_registry.json",
          "registre d'idempotence", required=False)
    place(os.path.join(session_dir, "signatures.jsonl"), "policy/signatures.jsonl",
          "journal des signatures (compteur)", required=False)

    # 5bis — le manifeste de session (écrit par le run E) et le rapport lisible
    place(os.path.join(session_dir, "export", "manifest.json"), "manifest.json",
          "manifeste de session", required=False)
    place(os.path.join(session_dir, "report.md"), "report.md", "rapport lisible", required=False)

    # 10 — vérificateur hors-ligne minimal (le vérificateur T10 complet n'existe pas encore)
    os.makedirs(os.path.join(staging, "verify"), exist_ok=True)
    with open(os.path.join(staging, "verify", "verify_hashes.py"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(VERIFY_SCRIPT)
    note = ("The full third-party verifier (`python -m orvyren.verify`, test T10) is NOT built yet "
            "(research/B6_AUDIT_ETUDE.md §2 constat). This packet ships the minimal offline verifier only, "
            "which checks file digests, the journal hash chain and (with --rpc) the tx hashes. "
            "It must not be presented as T10.\n")
    with open(os.path.join(staging, "verify", "VERIFY_NOT_BUILT.txt"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(note)

    # 12 — ancrage (reporté) : dossier vide avec la raison, jamais un faux artefact
    os.makedirs(os.path.join(staging, "anchor"), exist_ok=True)
    with open(os.path.join(staging, "anchor", "README_ANCHOR.txt"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("EAS anchoring is conditional (FREEZE_V2 F3) and was not executed for this session. "
                     "The published digest required by option (ii) is the `bundle_digest` of HASHES.txt.\n")

    # 1 — README (l'inventaire est complet à ce stade : pièces + vérificateur)
    inventory.append(("README_AUDIT.md", "mode d'emploi de vérification (EN)"))
    inventory.append(("verify/verify_hashes.py", "vérificateur hors-ligne minimal"))
    inventory.append(("verify/VERIFY_NOT_BUILT.txt", "note sur l'absence du vérificateur T10 complet"))
    inventory.append(("manifest.json", "manifeste du paquet"))
    inventory.append(("anchor/README_ANCHOR.txt", "note d'ancrage (reporté)"))
    inventory.append(("HASHES.txt", "sha256 de chaque fichier + bundle_digest"))
    with open(os.path.join(staging, "README_AUDIT.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(README_TEMPLATE.format(
            case=case, run8=run8, run_id=run_id, txt_ok=TXT_PROVES, txt_no=TXT_NOT_PROVES,
            inventory="\n".join("- `{}` — {}".format(path, label) for path, label in inventory)
                      or "- (aucune pièce)"))

    # 8 — manifeste du paquet (têtes de flux, versions, inventaire — sans digests : stabilité du hash)
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
        "note": "Le sha256 du zip est publié à côté du zip (<nom>.zip.sha256) : il ne peut pas être "
                "inscrit dans le paquet sans créer une récursion.",
    }
    common.write_json(os.path.join(staging, "manifest.json"), manifest)

    # 11 — HASHES.txt + bundle_digest (calculés APRÈS la dernière écriture dans le paquet)
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

    # zip nommé + hashé (le sha256 du zip est publié à côté — ancrage option ii)
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
        description="ORVYREN — assemblage du paquet d'audit (B6 §5) : pièces, HASHES.txt, bundle_digest, zip. "
                    "Hors ligne ; ne fabrique aucune pièce manquante (elle est déclarée absente).")
    parser.add_argument("--session", default=None,
                        help="répertoire de session de démo (défaut : evidence/demo_runs/<case>)")
    parser.add_argument("--case", default="rseth", help="étiquette de cas (défaut : rseth)")
    parser.add_argument("--evidence", default=os.path.join(common.ROOT, "evidence"),
                        help="répertoire des dossiers de décision (défaut : evidence/)")
    parser.add_argument("--out", default=None, help="répertoire de sortie du zip (défaut : <session>/packet)")
    parser.add_argument("--dry-run", action="store_true",
                        help="assemblage hors ligne (défaut de fait : aucun réseau n'est utilisé)")
    parser.add_argument("--strict", action="store_true",
                        help="échec si une pièce requise est absente (dossier de décision, journal)")
    args = parser.parse_args(argv)

    session_dir = args.session or os.path.join(common.ROOT, "evidence", "demo_runs", args.case)
    try:
        result = build_packet(session_dir=session_dir, case=args.case, evidence_dir=args.evidence,
                              out_dir=args.out, strict=args.strict)
    except common.ConfigurationError as exc:
        print("ERREUR: {}".format(exc), file=sys.stderr)
        return EXIT_USAGE

    print("ORVYREN — paquet d'audit assemblé")
    print("  répertoire : {}".format(common.display_path(result["packet_dir"])))
    print("  zip        : {}".format(common.display_path(result["zip_path"])))
    print("  sha256(zip): {}".format(result["zip_sha256"]))
    print("  bundle_digest (à publier — option ii, FREEZE_V2 F3) : {}".format(result["bundle_digest"]))
    print("  fichiers   : {}".format(result["files"]))
    if result["missing_pieces"]:
        print("  pièces absentes (déclarées, jamais inventées) :")
        for piece in result["missing_pieces"]:
            print("    - {} ({})".format(piece["piece"], piece["reason"]))
    if args.strict and result["missing_pieces"]:
        return EXIT_MISSING
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
