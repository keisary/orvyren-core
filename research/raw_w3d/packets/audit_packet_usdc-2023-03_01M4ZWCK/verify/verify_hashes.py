#!/usr/bin/env python
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
