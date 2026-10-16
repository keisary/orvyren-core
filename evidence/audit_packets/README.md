# Paquet d'audit — runs A→E du 16/10/2026 (Base Sepolia, chainId 84532)

Exemplaire de référence, **versionné**, du paquet d'audit produit par la démonstration :
les **5 runs réels** — A (transfert autorisé) · B (refus hors chaîne) · C (refus par la
chaîne) · D (kill switch) · E (audit) — exécutés le **2026-10-16** sur Base Sepolia.

- `audit_packet_rseth_01M526YS.zip` — 28 fichiers : journal chaîné SHA-256 (`audit.jsonl`),
  **13 reçus de transaction réels**, politique effective + signatures, rapport (`report.md`),
  manifeste (têtes de flux, compteurs), `HASHES.txt`, vérificateur `verify/verify_hashes.py`.
- `audit_packet_rseth_01M526YS.zip.sha256` — hash du zip.
  **`bundle_digest` à publier** (option ii, FREEZE_V2 F3) :
  `f5409d23d7124652148c5620550c74de8b977746b1ecf003986b83737cde9229`.

## Vérifier (aucune confiance requise)

```bash
sha256sum -c audit_packet_rseth_01M526YS.zip.sha256   # intégrité du zip (ou comparer à la main)
unzip audit_packet_rseth_01M526YS.zip && cd audit_packet_rseth_01M526YS
python verify/verify_hashes.py                        # recalcule HASHES.txt fichier par fichier
# puis re-lire chaque transaction sur Base Sepolia :
# https://sepolia.basescan.org/tx/0x…  (hashes dans audit.jsonl et receipts/)
```

Tout est **public et vérifiable** : aucune clé, aucun secret (les clés de démo ne sont
jamais versionnées — cf. `.gitignore`). La démo est **reproductible par toute personne** :
`DEMO_KIT.md` §2 → §6. Critères des runs : §6 ; limites assumées : §10.
