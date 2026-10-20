# Paquet d'audit — runs A→E du 20/10/2026 (Base Sepolia, chainId 84532)

Exemplaire de référence, **versionné**, du paquet d'audit issu de la démonstration : les
**5 runs réels** — A (transfert autorisé) · B (refus hors chaîne) · C (refus par la chaîne) ·
D (kill switch) · E (audit) — exécutés le **2026-10-20** sur Base Sepolia, session
`evidence/demo_runs/rseth_20261020/` (`run_id` `01M5CCNNTXNSC3YEVEPAJFBWWH`).

- **référence (vérificateur gelé T10)** : `audit_packet_rseth_20261020-1012_01M5CCNN.zip`
  — 45 fichiers ; vérificateur auto-conteneur gelé (`verify/orvyren_verify.py`, stdlib-only) ;
  `VERDICT: OFFLINE_PASS` (**16 checks, 0 failed**) — re-mesuré le 2026-10-20 à 10:12Z sur
  le zip publié ici ; `--mutate-test` → **mutations 6/6** ; `sha256sum -c HASHES.txt` exit 0,
  zéro `__pycache__`. **Les deux vérificateurs concordent** : `python run_verify.py <zip>`
  depuis ce dépôt *et* le vérificateur embarqué (`unzip` puis
  `python verify/orvyren_verify.py .`) rendent le même `OFFLINE_PASS`.
- **v1 — historique** : `audit_packet_rseth_01M526YS.zip` — 28 fichiers : journal chaîné
  SHA-256 (`audit.jsonl`), **13 reçus réels**, politique effective + signatures, `report.md`,
  manifeste, `HASHES.txt`, `verify/verify_hashes.py`.
- **ancien paquet v2 du 16/10** — `audit_packet_rseth_20261016-2340_01M526YS.zip` :
  **déplacé hors dépôt** le 2026-10-20 vers
  `D:/orvyren_internal_2026-10-18/audit_packets_superseded/` avec `SUPERSEDED_NOTE.md`.
  Il n'était pas faux le 16/10 (son vérificateur embarqué rend toujours `OFFLINE_PASS`),
  mais `A4.dossier.rerender` re-rend le dossier avec le code courant et `audit/dossier.py`
  a changé après son scellement — d'où `FAIL — 16 checks, 2 failed` côté dépôt. Le paquet
  ci-dessus est reconstruit depuis une session fraîche, donc re-rendable par le code actuel.

## Contenu mesuré du paquet de référence

| mesure | valeur |
|---|---|
| lignes de journal (`audit.jsonl`) | **69** (dont 5 `RUN_START`, 3 `LINK`, 1 `SEAL` ; 64 entrées de run) |
| reçus | **10** — **1 succès** (`status 0x1`, transfert in-policy) + **9 reverts** (`0x0`, tentatives forcées refusées par la chaîne) |
| runs | A `VERIFIED_OK` 6/6 · B `DENIED` 4/4 · C `EXECUTED` 4/4 · D `EXECUTED` 5/5 · E `EXPORTED` 4/4 |
| rapport indépendant | « 1 exécution conforme, 6 refus hors chaîne, 9 tentatives forcées refusées par la chaîne » |

## Empreintes publiées (F3 — publiées dans ce dépôt public, 2026-10-20)

| paquet | sha256 du zip | `bundle_digest` interne |
|---|---|---|
| **référence 20261020-1012** | `63f4cefd905047eca2f71b4fa0c99fb05fb4cdb38bcc661919583f0c7592b83f` | `dd8511cdb521c77447427008a2c6449e5c62fd1f42e5c12d7208b327be942748` |
| v1 (historique) | `7ecea5ec6e77228c167321858fe67e02fe4bb7e7eaa8335bfa534070b2f32a36` | `f5409d23d7124652148c5620550c74de8b977746b1ecf003986b83737cde9229` |
| v2 du 16/10 (supersédé) | `a0c4562050a6c468ab8a2adea4a858acdd8e76154640b5f42b1be94ecc0a669e` | `658428691e4a68279dc1d57ee694fbd05258137a17c735028c7424d05269981f` |

- `bundle_digest` : scellé dans le zip (`BUNDLE_DIGEST.txt`), recalculé par le contrôle A3 du
  vérificateur ; chaque zip a son sidecar `.sha256`. Les fichiers
  `…20261020-1012_01M5CCNN.HASHES.txt` et `….BUNDLE_DIGEST.txt` de ce répertoire sont les
  **copies** des fichiers scellés dans le zip (commodité de lecture — la vérification fait foi
  sur le zip).
- **Ancrage EAS** (option conditionnelle du gel F3) : **non exécuté — déclaré tel quel**.
  La publication de l'empreinte au sens F3 est assurée par ce dépôt public
  (GitHub `keisary/orvyren-core`) et ce fichier daté.

## Vérifier (aucune confiance requise)

```bash
cd evidence/audit_packets
sha256sum -c audit_packet_rseth_20261020-1012_01M5CCNN.zip.sha256   # intégrité du zip
unzip -q audit_packet_rseth_20261020-1012_01M5CCNN.zip
cd audit_packet_rseth_20261020-1012_01M5CCNN
sha256sum -c HASHES.txt                     # fichier par fichier
python verify/orvyren_verify.py .           # attendu : VERDICT: OFFLINE_PASS — 16 checks, 0 failed
python verify/orvyren_verify.py . --mutate-test   # attendu : mutations 6/6
# optionnel, avec réseau : re-lecture de chaque transaction sur la chaîne
python verify/orvyren_verify.py . --rpc https://sepolia.base.org
```

Le vérificateur embarqué ne demande **ni ce dépôt, ni notre API, ni `pip install`** : stdlib
seule. Depuis la racine du dépôt, la même vérification passe par
`python run_verify.py evidence/audit_packets/audit_packet_rseth_20261020-1012_01M5CCNN.zip`.

Puis re-lire chaque transaction sur Base Sepolia : `https://sepolia.basescan.org/tx/0x…`
(hashes dans `audit.jsonl` et `receipts/`).

## Écarts mesurés du run (déclarés, pas corrigés)

- **Run A dépense les 100 USDC du coffre** (décision gelée FREEZE_V2 E2) : après A, la Safe
  est à **0 USDC**. Les tentatives forcées de C qui auraient dû être arrêtées par une
  *condition de rôle* le sont bien : `C1` (500 USDC) et `C2` (destinataire non listé)
  rendent `ConditionViolation` **`0xd0a9bf58`** — pour C1 le payload nomme l'allowance
  `usdc_daily`, pour C2 le status vaut 5 (`OrViolation`, le destinataire sort de
  `Or(EqualTo(B), EqualTo(C))`). En revanche `C4` (4×100 USDC) rend
  `ModuleTransactionFailed()` **`0xd27b44a9`** : l'**autorisation du rôle passe**, c'est le
  transfert interne qui échoue faute de solde. Autrement dit, **l'épuisement d'allowance que
  C4 voulait montrer n'est pas démontré sur ce run** — il ne l'était pas davantage le 16/10
  (même sélecteur, même cause). Le critère C.4 du kit reste « met » parce qu'il porte sur C5
  (frontière de période, évaluation hors chaîne), pas sur C4.
- `C3a` (agent → `allowTarget`) rend `OwnableUnauthorizedAccount` `0x118cdaa7` ; `C3b`
  (agent → `Safe.enableModule`) rend `Error(string)` `0x08c379a0` (`GS*`).
- `D` (kill switch) rend `NoMembership()` **`0xfd8e9f28`** à la tentative de l'agent après
  `assignRoles(agent, [AGENT], [false])`, puis le rôle est **rétabli**
  (`dao_assign_roles.py --enable true`, tx `0x6fa209f2…`).

Tout est **public et vérifiable** : aucune clé, aucun secret (les clés de démo ne sont
jamais versionnées — cf. `.gitignore`). La démo est **reproductible par toute personne** :
`DEMO_KIT.md` §2 → §6. Critères des runs : §6 ; limites assumées : §10.
