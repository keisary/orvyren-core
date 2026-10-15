# B6 — notes de contexte et mesures (matière brute)

**Date : 2026-10-15.** Chantier : `research/SYSTEME_ZONES_OMBRE.md` §6 (audit & vérifiabilité), 3ᵉ bloc traité après B1 (agents), B2 (graphe), B3 (décision).

## 1. Documents internes lus (chemins dans `D:\orvyren_core` sauf mention)

| Document | Ce qui en est tiré |
|---|---|
| `research/SYSTEME_ZONES_OMBRE.md` §6 | questions 6.1 (format journal), 6.2 (vérificateur T10), 6.3 (ancrage EAS) — les 3 questions du bloc |
| `research/W2C_enveloppe_execution.md` §(d).5 et §(g) | design `audit.jsonl` chaîné (INTENT/POLICY/SIMULATION/SUBMIT/RECEIPT/VERIFY), plan run E (journal), 5 runs ALLOW/DENY/DENY-chaîne/kill/audit |
| `src/orvyren/audit/dossier.py` + `tests/test_audit.py` | dossier v1 : entrées sha256, self-hash reproductible (champ remis à 64 `0`), HTML autonome, déterminisme (mêmes entrées + `generated_at` → fichier identique) |
| `src/orvyren/graph/provenance.py` + `store.py` | `verify_chain` (résolution des réfs de claim), `snapshot()`/`snapshot_hash` (sha256 stable), tables append-only (triggers UPDATE/DELETE interdits) |
| `src/orvyren/execution/verify.py` | `verify_receipt` pur (statut, chaîne, token, émetteur, destinataire, montant) — base du volet « revérifiable » |
| `src/orvyren/policy/__init__.py` | 8 règles R1–R8 déterministes, `ALLOWED_CHAIN_ID=84532`, plafonds 100/300 USDC, TTL 24 h, idempotence |
| `research/B1_AGENTS_ETUDE.md` §3 | `agent_journal` (25 champs, `prev_hash`, PROPOSED→ACCEPTED, magasin de payloads hashés, `prompt_hash`/`response_hash`) |
| `research/B2_GRAPHE_ETUDE.md` §7.4/§7.5, QO-1 | PIT admission, `snapshot()` par décision, delta de graphe par run, politique de reorg à figer |
| `research/W3_reconstruction_rseth_steth.md` | preuve reproductible : relance « identique au bit près » ; mode `--from-cache` hors-ligne ; provenance des lectures RPC |
| `research/REVUE_CROISEE_ET_CADRE_CONCRET.md` §2.4/§4 | 5 invariants (INV-PIT/AUTH/INTEGRITY/ACCOUNTING/DEPENDENCE) ; T10 = HYP-10R, P0, critères de succès gelés d'avance |
| `C:\Users\User\fintechathon_recherche\orvyren_v02\ORVYREN_Document_de_reference_V0_2.txt` §10.6 | « Une empreinte prouve l'intégrité du dossier ancré, pas sa véracité » — EAS option à étudier, reportée si elle menace le flux vertical |
| `ARCHITECTURE_V1.md` §2/§6 | carte des modules (audit, ui), EAS « reportée après le flux vertical », langues des artefacts (code/docs/vidéo EN pour l'UE, notes internes FR) |
| `dist/docs/ORVYREN_EXPLIQUE_SIMPLEMENT.md` (et `docs/partage/`) | T10 non négociable, ordre du lot T10 → T12 → T03 → T02 |

## 2. Mesures faites pour ce chantier (2026-10-15)

### 2.1 Contrôle hors-ligne du dossier d'audit v1 (`research/raw_b6/verif_dossier_v1*.py`)

- `evidence/dossier_usdc-2023-03.md` : self-hash embarqué
  `73399190489fac60b061a3441be1f62a5685f867788f4dfa3e92fd1f239e8ac7`,
  **reproduit à l'identique** par le recalcul (champ remis à 64 `0`) ; sha256 du fichier tel quel
  `f043bad856691130bea6f862eb0a37b46433d3a82946c2838b21a928936e8aad` ; 23 441 o (LF).
- `evidence/dossier_usdc-2023-03.html` : self-hash embarqué
  `7a609a14e1e6461472b262ae7f3692f93b5acd5458032062f86b455e7c4c3f89`,
  **reproduit** ; 1 seule occurrence ; 34 364 o ; sha256 tel quel
  `3787ab6f182436cf895b6994fd817f1f57d08f45cddd5418d6e1ff699b7035cf`.
- Entrées déclarées dans la table « Evidence & integrity » : les 3 SHA-256 se recalculent
  (decision `b65c0634…`, policy_execution_demo `3712a683…`, quality_report `5478728c…`).
  → la règle de vérification du dossier v1 fonctionne **hors-ligne, avec n'importe quel outil SHA-256**.
- Piège rencontré (documenté) : un contrôle naïf du HTML qui prend « le premier 64-hex du fichier »
  tombe sur un hash d'entrée (le corpus `c31088b3…` apparaît avant la ligne self dans la section
  Décision) → le contrôle doit cibler la cellule `dossier (self, html)`. À reprendre dans T10.

### 2.2 Sondage RPC Base Sepolia — EAS (`research/raw_b6/eas_basesepolia_rpc.py`, `eas_impl_slots.json`)

- `https://sepolia.base.org` : `eth_chainId = 0x14a34` (84532) ; bloc `0x2deb693` = **47 988 371** ;
  `eth_gasPrice = 0x5b8d80` = **6 000 000 wei** (0,006 gwei).
- **EAS** `0x4200000000000000000000000000000000000021` : code présent (proxy ERC-1967, 2 059 o,
  sha256 `30ccc4ce49c00fae11d7118fc244f29a13788fb32cd4022ee69acc2f15c0e2f5`) ;
  implémentation lue au slot `0x360894a1…` = `0xc0d3c0d3c0d3c0d3c0d3c0d3c0d3c0d3c0d30021`
  (18 385 o, sha256 `9c576dec8bcebe50c5a85e4aba307540c9b28614374a485b75a805a6cbdcffd8`).
- **SchemaRegistry** `0x4200000000000000000000000000000000000020` : proxy identique ;
  implémentation `0xc0d3c0d3c0d3c0d3c0d3c0d3c0d3c0d3c0d30020` (2 865 o,
  sha256 `bda4f862814623d5f067378bc8c034dcf5786da243215d029fa48820a8eed4ff`).
- Coût d'une attestation : **ordre de grandeur** 0,0000007–0,0000015 ETH pour 120 k–250 k gaz au
  prix mesuré [HYPOTHÈSE sur les gaz ; gasPrice MESURÉ] → négligeable, le coût réel est la clé
  testnet financée + le script (prérequis déjà posé par W2-C pour la démo).
- Note : le premier appel sans en-tête `User-Agent` a reçu un **HTTP 403** du RPC public
  `sepolia.base.org` ; avec `User-Agent: orvyren-b6-research/1.0` la réponse est normale.
  À reprendre dans tout outil de vérification qui interroge ce RPC.

## 3. Fichiers produits par ce chantier

| Fichier | Nature |
|---|---|
| `research/B6_AUDIT_ETUDE.md` | **livrable** : étude du bloc audit & vérifiabilité |
| `research/raw_b6/verif_dossier_v1.py` | contrôle self-hash + entrées du dossier v1 (hors-ligne) |
| `research/raw_b6/verif_dossier_v1_html_fix.py` | re-contrôle HTML ciblé (correction du piège §2.1) |
| `research/raw_b6/dossier_v1_verification.json` | résultats du contrôle (JSON) |
| `research/raw_b6/eas_basesepolia_rpc.py` | sondage EAS Base Sepolia (lecture seule) |
| `research/raw_b6/eas_basesepolia_rpc.json`, `eas_impl_slots.json` | résultats du sondage |
