# Paquet d'audit — runs A→E du 16/10/2026 (Base Sepolia, chainId 84532)

Exemplaire de référence, **versionné**, du paquet d'audit issu de la démonstration : les
**5 runs réels** — A (transfert autorisé) · B (refus hors chaîne) · C (refus par la chaîne) ·
D (kill switch) · E (audit) — exécutés le **2026-10-16** sur Base Sepolia.

- **v2 — autorité (vérificateur gelé T10)** : `audit_packet_rseth_20261016-2340_01M526YS.zip`
  — 47 fichiers ; vérificateur auto-conteneur gelé (`verify/orvyren_verify.py`, stdlib-only) ;
  `VERDICT: OFFLINE_PASS` (16/16 contrôles : A12 + B3 + C1), `--mutate-test` **6/6** mutations
  détectées, `sha256sum -c HASHES.txt` exit 0, zéro `__pycache__`.
- **v1 — historique** : `audit_packet_rseth_01M526YS.zip` — 28 fichiers : journal chaîné
  SHA-256 (`audit.jsonl`), **13 reçus réels**, politique effective + signatures, `report.md`,
  manifeste, `HASHES.txt`, `verify/verify_hashes.py`.

## Empreintes publiées (F3 — publiées dans ce dépôt public, 2026-10-17)

| paquet | sha256 du zip (recomputé) | `bundle_digest` interne |
|---|---|---|
| **v2** | `a0c4562050a6c468ab8a2adea4a858acdd8e76154640b5f42b1be94ecc0a669e` | `658428691e4a68279dc1d57ee694fbd05258137a17c735028c7424d05269981f` |
| v1 | `7ecea5ec6e77228c167321858fe67e02fe4bb7e7eaa8335bfa534070b2f32a36` | `f5409d23d7124652148c5620550c74de8b977746b1ecf003986b83737cde9229` |

- `bundle_digest` : scellé dans le zip (`BUNDLE_DIGEST.txt`), recalculé par le contrôle A3 du
  vérificateur ; chaque zip a son sidecar `.sha256` (match revérifié ici le 2026-10-17).
- **Ancrage EAS** (option conditionnelle du gel F3 : « si run E + T10 verts avant le
  18/10 23:59 ») : **non exécuté — déclaré tel quel**. La publication de l'empreinte au sens
  F3 est assurée par ce dépôt public (GitHub `keisary/orvyren-core`) et ce fichier daté.

## Vérifier (aucune confiance requise)

```bash
cd evidence/audit_packets
sha256sum -c audit_packet_rseth_20261016-2340_01M526YS.zip.sha256   # (v2) intégrité du zip
unzip -q audit_packet_rseth_20261016-2340_01M526YS.zip
cd audit_packet_rseth_20261016-2340_01M526YS
sha256sum -c HASHES.txt                     # fichier par fichier
python verify/orvyren_verify.py .           # attendu : VERDICT: OFFLINE_PASS
python verify/orvyren_verify.py . --mutate-test   # attendu : 6/6 mutations détectées
# optionnel, avec réseau : re-lecture de chaque transaction sur la chaîne
python verify/orvyren_verify.py . --rpc https://sepolia.base.org
```

Puis re-lire chaque transaction sur Base Sepolia : `https://sepolia.basescan.org/tx/0x…`
(hashes dans `audit.jsonl` et `receipts/`).

Tout est **public et vérifiable** : aucune clé, aucun secret (les clés de démo ne sont
jamais versionnées — cf. `.gitignore`). La démo est **reproductible par toute personne** :
`DEMO_KIT.md` §2 → §6. Critères des runs : §6 ; limites assumées : §10.
