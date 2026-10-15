# W3-D — matière brute du kit de démo testnet (2026-10-15)

Ce répertoire contient la **matière reproductible** du chantier W3-D (kit de
démo testnet). Aucun commit n'a été fait (règle projet : l'orchestrateur
committe). Aucune transaction n'a été envoyée et aucune clé n'existe : tout ce
qui suit est **lecture seule** ou **hors chaîne**.

## Fichiers

| Fichier | Contenu |
|---|---|
| `dryrun_output.txt` | Sortie complète des **5 runs en dry-run** (A→E) sur une session neuve — 5/5 sortie 0, 5/5 critères OK |
| `full_suite_output.txt` | `python -m pytest tests/ -q` — **296 passed, 2 skipped** (221 verts d'origine + 75 du kit) |
| `demo_kit_tests_output.txt` | `python -m pytest tests/test_demo_kit.py -q` — **75 passed** |
| `rehearsal_live.env` | Configuration de la **répétition en ligne** (lecture seule) : USDC Circle réel + module Roles officiel, agent/Safe simulés |
| `rehearsal_intent.json` | Intent v1 de la répétition (transfer 50 USDC, compte = Safe simulée) |
| `rehearsal_preflight_cli.json` | Préflight `--rpc` lancé par la **CLI** (22 contrôles) |
| `rehearsal_preflight_live.json` | Même préflight lancé par l'API Python (avec registre d'idempotence) |
| `envelope_capture_live.json` | **Enveloppe capturée en ligne** par `--capture-envelope` (18 contrats, tailles + sha256 + bloc + gaz) |
| `session_dry/` | Session de démonstration complète en dry-run (journal chaîné, registre, reçus, export, rapport) |
| `packets/` | Paquet d'audit assemblé + zip + `.sha256` (vérifié par son propre vérificateur) |

## Mesures en ligne du 2026-10-15 (lecture seule, `https://sepolia.base.org`)

Répétition du préflight en mode `--rpc` (bloc **48 151 294 → 48 151 322**) :

* `eth_chainId` = **84532** → P2 PASS ;
* **module Roles officiel** `0xF2964CE6161ce0e75964Fe7927cE114cb0B283D5` :
  code **24 409 octets**, sha256 `89c5dc3313b5669f669232de7033734b4ee10339297cdf523bee5eb1b093cd05`
  → P6 PASS et, avec le codehash épinglé dans l'enveloppe, **D2 PASS en ligne** ;
* USDC Circle `0x036CbD…CF7e` : **1 798 octets** ; USDC Aave `0xba50Cd2A…4d5f` :
  **3 981 octets** ; WETH pré-déploiement : **2 041 octets** — identiques aux
  mesures de B5 §b.2 (le déploiement n'a pas bougé) ;
* `eth_gasPrice` = **6 000 000 wei** (0,006 gwei) → P10 PASS (borne = 10× la référence) ;
* `eth_getTransactionCount(agent, "pending")` = 0 → P8 PASS ;
* soldes lus par `eth_call` (P9 PASS) ;
* **P11 (simulation)** : `eth_call` de
  `execTransactionWithRole(USDC, 0, transfer(B, 50e6), 0, AGENT, true)` depuis
  l'adresse agent simulée → **revert `0x4a0bfec1`** — soit `NotAuthorized(address)`,
  exactement le sélecteur mesuré par B5 §b.2.d (le non-membre est refusé par le
  module officiel, dont la Safe n'est pas la nôtre). **P12** échoue ensuite
  (`gas_estimate_failed`) : pas d'estimation possible sur un appel qui revert —
  comportement attendu et voulu (aucune signature si la simulation revert) ;
* **P7** échoue (`target_code_missing`) parce que l'adresse « Safe » de la
  répétition n'a pas de code : c'est la preuve que le contrôle détecte une
  adresse non déployée ;
* dérive : D1/D2/D4/D5/D6/D7/D8/D9 PASS quand l'enveloppe est renseignée ;
  D3/D6/D10 `UNKNOWN` tant que les *probes* (getters du module) et la version du
  module ne sont pas confirmées → **SAFE MODE** en mode en ligne (fail-closed,
  B4 P12) — attendu, pas un défaut.

## Résultats hors chaîne

* **5 runs dry-run** : A/B/C/D/E sortie `0`, critères OK ; le journal de session
  se recalcule (chaîne SHA-256 OK) ; compteur de signatures = 1 après le run A,
  inchangé par le run B ; run C : aller-retours de calldata OK et frontière de
  période démontrée (ALLOW puis DENY `AMOUNT_ABOVE_PERIOD_CAP`) ; run E : export
  `manifest.json` + `report.md` + compteurs (refus, soumissions, signatures) ;
* **paquet d'audit** : 18 fichiers, `HASHES.txt` + `bundle_digest`, zip + `.sha256` ;
  le vérificateur hors-ligne embarqué rend **`OFFLINE_PASS`** sur le paquet intact
  et **`FAIL`** (avec `sha256 mismatch: audit.jsonl` + `line 2: record_hash mismatch`)
  après altération d'un octet d'une ligne du journal — test de mutation exécuté ;
* **suite complète** : 294 passed / 2 skipped (aucune régression).

## Limites assumées (à ne pas masquer)

1. Les *probes* du test de dérive sont **déclaratifs** : les noms exacts des
   getters de cible/condition/allowance doivent être confirmés sur le contrat
   déployé le jour J (B4 §d.3 annexe 4) — tant qu'ils manquent, le mode en ligne
   reste en SAFE MODE (voulu).
2. Le run A utilise **100 USDC** (FREEZE_V2 E2, gelé) ; B5 §e.1 écrivait 50 USDC
   (question ouverte Q2 de B5) — `--amount` permet la variante.
3. Le paquet d'audit embarque un **vérificateur hors-ligne minimal** : le
   vérificateur T10 complet (`python -m orvyren.verify`) n'existe pas encore
   (constat B6 §2) et le paquet le dit explicitement
   (`verify/VERIFY_NOT_BUILT.txt`).
4. L'ancrage EAS reste **conditionnel** (FREEZE_V2 F3) ; seule l'empreinte
   publiée (option ii) est produite par le kit.
5. Rien n'a été envoyé sur une chaîne : les seules preuves on-chain viendront de
   l'exécution réelle des 5 runs, qui exige un wallet financé.
