#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B6 — verification hors-ligne du dossier d'audit v1 (evidence/dossier_usdc-2023-03.{md,html}).

Mesure :
  1. règle de self-hash : SHA-256 du fichier avec le champ self-hash (64 hex) remis à 64 '0'
     -> doit reproduire la valeur embarquée (règle documentée dans dossier.py) ;
  2. table 'Evidence & integrity' : les SHA-256 déclarés pour les fichiers d'entrée
     (normalisation CRLF->LF, comme dossier.sha256_file) se recalculent-ils ?

Écrit raw_b6/dossier_v1_verification.json. Aucun réseau, aucun fichier du dépôt modifié.
"""
import hashlib
import json
import os
import re

REPO = r"D:/orvyren_core"
OUT = os.path.join(REPO, "research", "raw_b6", "dossier_v1_verification.json")
CANDIDATES = [
    os.path.join(REPO, "evidence", "dossier_usdc-2023-03.md"),
    os.path.join(REPO, "evidence", "dossier_usdc-2023-03.html"),
]


def norm_bytes(path):
    with open(path, "rb") as fh:
        return fh.read().replace(b"\r\n", b"\n")


def verify_self_hash(path):
    raw = norm_bytes(path)
    text = raw.decode("utf-8")
    embedded = None
    if path.endswith(".html"):
        # Le premier 64-hex du HTML n'est pas forcément le self-hash : cibler la cellule
        # de la ligne "dossier (self, html)" (cellule <code> du 3e <td>).
        m = re.search(
            r"<td>dossier \(self, html\)</td>\s*<td><code>[^<]+</code></td>\s*<td><code>([0-9a-f]{64})</code></td>",
            text,
        )
        embedded = m.group(1) if m else None
    else:
        m = re.search(r"dossier \(self[^|]*\|[^|]*\|\s*`?([0-9a-f]{64})`?", text)
        embedded = m.group(1) if m else None
    zeroed = raw.replace(embedded.encode(), b"0" * 64, 1) if embedded else None
    recomputed = hashlib.sha256(zeroed).hexdigest() if zeroed else None
    return {
        "file": os.path.relpath(path, REPO).replace(os.sep, "/"),
        "size_bytes_lf": len(raw),
        "embedded_self_hash": embedded,
        "recomputed_with_field_zeroed": recomputed,
        "self_hash_ok": bool(embedded and recomputed and embedded == recomputed),
        "raw_file_sha256_as_written": hashlib.sha256(norm_bytes(path)).hexdigest(),
    }


def verify_inputs(path):
    """Recalcule les SHA-256 de la table Evidence & integrity (chemins repo-relatifs)."""
    text = norm_bytes(path).decode("utf-8")
    rows = []
    for m in re.finditer(r"\|\s*(decision|baseline|policy[^|]*|quality[^|]*)\s*\|\s*`?([^|`]+?)`?\s*\|\s*`?([0-9a-f]{64})`?\s*\|", text):
        label, rel, declared = m.group(1).strip(), m.group(2).strip(), m.group(3)
        abs_path = os.path.join(REPO, rel.replace("/", os.sep))
        actual = None
        if os.path.exists(abs_path):
            actual = hashlib.sha256(norm_bytes(abs_path)).hexdigest()
        rows.append({
            "label": label,
            "path": rel,
            "declared_sha256": declared,
            "actual_sha256": actual,
            "match": (actual == declared) if actual else None,
        })
    return rows


def main():
    report = {"generated_at_utc": None, "checks": []}
    from datetime import datetime, timezone
    report["generated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for path in CANDIDATES:
        if not os.path.exists(path):
            report["checks"].append({"file": path, "error": "absent"})
            continue
        entry = verify_self_hash(path)
        entry["inputs"] = verify_inputs(path) if path.endswith(".md") else []
        report["checks"].append(entry)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, sort_keys=True)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
