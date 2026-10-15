#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B6 — correction du contrôle HTML : extraire le hash de la ligne 'dossier (self, html)'.

La première passe ciblait le mauvais premier 64-hex du HTML (le repli regex tombait sur un
hash d'entrée). Ici on cible explicitement la cellule de la ligne self.
"""
import hashlib
import json
import os
import re

REPO = r"D:/orvyren_core"
OUT = os.path.join(REPO, "research", "raw_b6", "dossier_v1_verification.html_fix.json")
PATH = os.path.join(REPO, "evidence", "dossier_usdc-2023-03.html")

with open(PATH, "rb") as fh:
    raw = fh.read().replace(b"\r\n", b"\n")
text = raw.decode("utf-8")

m = re.search(
    r"<td>dossier \(self, html\)</td>\s*<td><code>([^<]+)</code></td>\s*<td><code>([0-9a-f]{64})</code></td>",
    text,
)
embedded = m.group(2) if m else None
n_occurrences = m is None and text.count("f" * 64)  # no-op
zeroed = raw.replace(embedded.encode(), b"0" * 64, 1) if embedded else None
recomputed = hashlib.sha256(zeroed).hexdigest() if zeroed else None
# vérifie aussi que le hash embarqué n'apparaît qu'une fois
count = text.count(embedded) if embedded else 0
report = {
    "file": "evidence/dossier_usdc-2023-03.html",
    "embedded_self_hash": embedded,
    "embedded_occurrences": count,
    "recomputed_with_field_zeroed": recomputed,
    "self_hash_ok": bool(embedded and recomputed and embedded == recomputed),
}
with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(report, fh, ensure_ascii=False, indent=2, sort_keys=True)
print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
