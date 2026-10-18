# ORVYREN — Montage on-chain Base Sepolia : résultats d'exécution (2026-10-16)

**Statut : EXÉCUTÉ** — Safe 2/3, module Zodiac Roles v2 (instance propre), rôle `AGENT` configuré et **vérifié on-chain**
(9 transactions, toutes `status = 0x1`). Les simulations de contrôle RUN A / RUN B concluent comme attendu.
`.env` mis à jour avec les adresses déployées.

Deux points restent ouverts et sont détaillés §6 : (a) **alimenter la Safe en USDC de test** (le transfert réel de
RUN A exige un solde), (b) **trancher D10** (version du module / avis) — tant qu'il reste `UNKNOWN`, le test de dérive
du kit conclut **SAFE MODE** et `demo.py` refuse les runs en mode `EXECUTE` (comportement voulu, B4 P12).

---

## 1. Adresses (vérifiées par relecture on-chain) et configuration

| Objet | Adresse | Preuve |
|---|---|---|
| **Safe 2/3** (owners O1/O2/O3, seuil 2, handler de compatibilité 1.4.1) | **`0x000e11a54daadf202542a0136f974f24d7c38be0`** | `ProxyCreation` (tx `0xcc291bb5…`) · `getOwners()` = 3 · `getThreshold()` = 2 · `VERSION()` = 1.4.1 |
| **Module Zodiac Roles v2** (clone EIP-1167 du mastercopy `0xF2964CE6…83D5`, `owner()=avatar()=target()` = Safe) | **`0x7e2b7798ab4b4db837b30107f0d2a3ffb24e95e8`** | `RolesModSetup` + `ModuleProxyCreation` (tx `0xc3329d29…`) · lectures `owner()/avatar()/target()` · code 45 o (sha256 `09bfac6b…`) |
| Agent (EOA jetable, gaz 0,0015 ETH) | `0xe1039e345Fa2AD9EcCeab7bb160FD5e53f58F01c` | transfert de gaz (tx `0xe711cba5…`) + solde relu |
| Rôle `AGENT` | `0x4147454e54000000000000000000000000000000000000000000000000000000` | `AssignRoles` (tx `0x994e762c…`) |
| Allowance `usdc_daily` | key `0x757364635f6461696c7900…` | `SetAllowance` (tx `0x5c13a9a8…`) : balance = refill = maxRefill = **300 000 000**, période **86 400 s** |
| Allowance `calls_daily` | key `0x63616c6c735f6461696c7900…` | `SetAllowance` (tx `0x0977f870…`) : balance = refill = maxRefill = **10**, période **86 400 s** |
| Fonction scopée | USDC Circle `0x036CbD53842c5426634e7929541eC2318f3dCF7e` · `transfer(address,uint256)` `0xa9059cbb` | `ScopeTarget` + `ScopeFunction` (tx `0x7f856bc2…`, `0xf623f087…`) |
| Destinataires allowlistés | B `0x37877F6f…53a3`, C `0x9f59ADcd…760E` | condition `Or(EqualTo(B), EqualTo(C))` — refus prouvé par RUN B |

Sel CREATE2 documenté et fixe : `84532` (Safe **et** module) → adresses reproductibles.
`unwrappers(USDC ‖ transfer) = 0x0` : aucun dépaquetage configuré pour la cible scopée (vecteur MultiSend hors du chemin).

## 2. Transactions (toutes `status = 0x1`)

| # | étape | tx hash | bloc | gaz | effet vérifié |
|---|---|---|---|---|---|
| 0 | `agent_fund` (0,0015 ETH vers l'agent) | `0xe711cba5059957f8d7e79919bf0e38596ebcd1683e8908a600e2b285c9842a34` | 48 189 412 | 21 000 | solde agent = 1 500 000 000 000 000 wei |
| 1 | `safe_deploy` | `0xcc291bb5ec9b86118ee1fe154ede944d17448af38986602e26c30ac7f40ec104` | 48 189 464 | 305 835 | `ProxyCreation` → Safe prédite ; owners/seuil relus |
| 2 | `module_deploy` | `0xc3329d29b9f5ae03e1eb3b3f70d049807aa5e3733d8b9dc2b2d523b89d721117` | 48 189 554 | 190 774 | `ModuleProxyCreation` + `RolesModSetup` ; owner/avatar/target relus |
| 3 | `safe_enable_module` | `0x05bca96760033e22acf7c0cf2ef6dbfcb16648d70f6a3c4228484a728dd927c5` | 48 189 624 | 112 723 | `EnabledModule(module)` ; `Safe.isModuleEnabled(module)` = true |
| 4 | `role_scope_target` | `0x7f856bc2f7e3648f6247fb837483ce921e24221317635784db823515b5197272` | 48 189 627 | 98 085 | `ScopeTarget(AGENT, USDC)` |
| 5 | `role_allowance_usdc` | `0x5c13a9a808d5042c48a0bdb0abb421b390e4c2bf278542b9a023e8fc121f7c4b` | 48 189 629 | 124 554 | `SetAllowance` + relecture `allowances()` = 300e6/300e6/300e6/86400 |
| 6 | `role_allowance_calls` | `0x0977f8702e0d3c323b51fcbdfd25e26a815dad2a76fa946f79180a1ec373c732` | 48 189 632 | 124 494 | `SetAllowance` + relecture = 10/10/10/86400 |
| 7 | `role_scope_function` | `0xf623f087949a9d5d42108825536ac520747237218dec2dc29cec958776a4980a` | 48 189 634 | 268 083 | `ScopeFunction` (arbre de conditions complet) |
| 8 | `role_assign_agent` | `0x994e762c17c87a4dede49b438b75edb1d27733bea2499b66e3102e8a10571ea9` | 48 189 636 | 131 931 | `AssignRoles(agent, [AGENT], [true])` + `EnabledModule(agent)` |

Coût total ≈ **1,38 M de gaz** (déploiements inclus), payé par O1.

**Signatures Safe 2/3** : chaque appel est signé par O1 + O2 (les deux premières clés), **signatures triées par adresse
croissante** (`v` ∈ {27,28} — chemin `ecrecover` par défaut de Safe 1.4.1), hash EIP-712 comparé à
`Safe.getTransactionHash` **avant chaque envoi**, et **contre-vérifié après coup** : les 6 hash Safe recalculés
localement sont **identiques aux `safeTxHash` émis par les événements `ExecutionSuccess`** (6/6, voir
`evidence/demo_runs/setup/tx_hashes.json` → `safe_tx_hash_checks`).

## 3. Simulées de contrôle (eth_call depuis l'adresse de l'agent) — verdicts

| Run | Appel | Résultat observé | Lecture |
|---|---|---|---|
| **A** | `execTransactionWithRole(USDC, 0, transfer(B, 100 USDC), CALL, AGENT, shouldRevert=true)` | revert **`ModuleTransactionFailed()`** (`0xd27b44a9`) | **l'autorisation a passé** (membre ✓, cible/fonction ✓, conditions ✓, allowances ✓) ; seul le transfert interne échoue → la Safe détient **0 USDC** (solde relu) |
| A′ | même appel, `shouldRevert=false` | **succès**, retour `false` | confirme que le refus vient de l'exécution interne, **pas** de l'autorisation |
| **B** | même appel vers le destinataire **non listé** | revert **`ConditionViolation(uint8 status=5, bytes32)`** (`0xd0a9bf58`…, status 5 = `OrViolation`) | la **portée du rôle refuse** le destinataire hors allowlist, y compris avec `shouldRevert=false` |
| — | allowances avant/après | inchangées | un échec d'exécution ne consomme pas d'allowance |

## 4. Capture d'enveloppe et préflight complet

```bash
python scripts/demo/preflight.py --rpc --env-file scripts/demo/.env --capture-envelope evidence/demo_runs/envelope_live.json
python scripts/demo/preflight.py --rpc --env-file scripts/demo/.env \
    --envelope evidence/demo_runs/envelope_reference.json --out evidence/demo_runs/preflight_live.json
```

- `evidence/demo_runs/envelope_live.json` : capture brute (bloc 48 189 829, 18 contrats, tailles + sha256).
- `evidence/demo_runs/envelope_reference.json` : **enveloppe complétée** avec les faits vérifiés (rôle déclaré + sondes des
  getters lisibles) — c'est celle à utiliser pour les runs.
- `evidence/demo_runs/preflight_live.json` : préflight en ligne → **verdict PASS**, dérive **D1–D9 PASS**,
  reste `D10 UNKNOWN` → `SAFE MODE : ENVELOPE_UNVERIFIED:D10`.
  Sondes exécutées : `isModuleEnabled(agent)` = true (D3) ; `allowances(usdc_daily).refill` = 300 000 000 (D7) ;
  `allowances(calls_daily).refill` = 10 (D8) ; module = code + codehash épinglés (D2) ; chaîne 84532 (D1).

## 5. Fichiers produits

| Fichier | Contenu |
|---|---|
| `scripts/demo/setup_chain.py` | outil de montage complet (préflight, validation d'arbre, simulations, exécution, preuves, `.env`) — `--self-test` : 24 contrôles hors ligne **verts** |
| `scripts/demo/setup_evidence.py` | consolidation des preuves depuis les reçus (index des tx, hash Safe recalculés, événements décodés) |
| `evidence/demo_runs/setup/setup_chain.json` | journal du run (infra, conditions, prédictions, calldata préparés, étapes) |
| `evidence/demo_runs/setup/addresses.json` | adresses Safe/module (+ owners, seuil) |
| `evidence/demo_runs/setup/tx_hashes.json` | index des 9 tx + événements décodés + `safe_tx_hash_checks` (6/6) |
| `evidence/demo_runs/setup/receipts/*.json` | 9 reçus bruts (un par étape) |
| `evidence/demo_runs/setup/simulations.json` | simulations de déploiement + validation de l'arbre + RUN A/B |
| `evidence/demo_runs/setup/integrity_enforce_simulations.json` | appel positif/négatifs sur la bibliothèque Integrity déployée |
| `evidence/demo_runs/setup/preflight_lecture_seule.json` | lecture seule : codes, tailles, sha256, sélecteurs, événements, soldes |
| `evidence/demo_runs/setup/abis/*.json` | ABI vérifiées (Blockscout) du mastercopy Roles et de la bibliothèque Integrity |
| `evidence/demo_runs/setup/execution_log.txt` · `SETUP_SUMMARY.md` | journaux d'exécution |
| `evidence/demo_runs/envelope_live.json` · `envelope_reference.json` · `preflight_live.json` | enveloppe capturée, enveloppe complétée, rapport de préflight |
| `docs/demo/SETUP_RESULTS.md` | ce document |

`scripts/demo/.env` : `ORVYREN_SAFE_ADDRESS` et `ORVYREN_MODULE_ADDRESS` remplacés par les adresses déployées ;
toutes les autres lignes intactes (clé privée inchangée — empreinte sha256 vérifiée avant/après).
Aucune clé privée n'apparaît dans un artefact ou une sortie (scan des fichiers `evidence/demo_runs/` : 0 occurrence).

## 6. Ce qui reste exactement à faire

1. **Alimenter la Safe en USDC de test** (robinet Circle, réseau Base Sepolia) — sans solde, RUN A autorise mais le
   transfert interne échoue (`ModuleTransactionFailed`). Une fois la Safe créditée, relancer
   `python scripts/demo/setup_chain.py --execute --skip-config` : RUN A passe alors en **succès complet** et la
   consommation d'allowance (balance 300 → 200) devient vérifiable.
2. **Trancher D10** (version du module + avis) : deux chemins — (a) comparer le codehash du mastercopy
   (`0xF2964CE6…83D5`, sha256 du code = `89c5dc3313b5669f669232de7033734b…`) à une release publiée ;
   (b) obtenir la confirmation des mainteneurs / de l'app Roles (bannière d'avis). Tant que D10 est `UNKNOWN`,
   le test de dérive conclut **SAFE MODE** et `demo.py` refuse les runs `EXECUTE` (B4 P12) — c'est le comportement
   voulu ; les runs ne sont pas bloqués en répétition.
3. **Rapprovisionner O1 en gaz** si nécessaire : O1 porte désormais ~0,0035 ETH ; le montage a coûté ≈ 1,38 M de gaz
   (~0,0000017 ETH au prix observé). L'agent a 0,0015 ETH (suffisant pour des dizaines d'exécutions).
4. Lancer ensuite les runs de démonstration (A/B/C/K) du kit avec `--env-file scripts/demo/.env` et l'enveloppe
   `evidence/demo_runs/envelope_reference.json`.

## 7. Garde-fous appliqués

- `eth_chainId` vérifié avant chaque signature (refus de toute chaîne ≠ 84532) ; `eth_getCode` avant chaque usage.
- Aucune transaction douteuse : l'appel `scopeFunction` n'a été envoyé qu'après **validation de l'arbre par la
  bibliothèque Integrity déployée** (contrôle positif + contrôles négatifs) et simulations de déploiement conformes
  aux prédictions CREATE2.
- Chaque reçu vérifié (`status = 0x1`) ; les relances après reçu attendent la propagation d'état (RPC public équilibré).
- En cas d'échec, aucune clé n'est journalisée et les preuves partielles sont écrites pour diagnostic.

## 8. Écarts et corrections documentés (utiles pour la soutenance)

1. L'adresse `0x4e1DCf7A71CCf7De11caCC46791B8d99d1BAbec0` (SafeProxyFactory de la consigne) **n'a aucun code** sur
   Base Sepolia : l'adresse vérifiée `0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67` a été utilisée (elle est déjà celle du
   kit). Le script journalise l'écart.
2. Le ModuleProxyFactory déployé exécute `proxy.call(initializer)` : l'`initializer` **est** le calldata complet
   `setUp(bytes)` (la forme historique « enveloppée » revertit — les deux variantes ont été testées par simulation).
3. `setAllowance` a **6 arguments** dans le contrat déployé (`bytes32 key, uint128 balance, uint128 maxRefill,
   uint128 refill, uint64 period, uint64 timestamp`) — une forme à 5 arguments revertirait.
4. `execTransactionWithRole` est **`moduleOnly`** dans la version déployée : le membre doit aussi être un **module
   activé du contrat Roles** (c'est ce que fait `assignRoles`, vérifié : `getModulesPaginated` → l'agent ;
   `isModuleEnabled(agent)` = true).
5. La bibliothèque Integrity déployée expose `enforce` sous le sélecteur **`0x783a9047`** (établi par désassemblage
   du bytecode et confirmé par appels réussis) — pas `0x33a2616f` (forme « source »).

## 9. Sources

- Sources contrats : `safe-global/safe-smart-account@v1.4.1` ; `zodiaceco/zodiac-core` (`Module.sol`, `Modifier.sol`,
  `ModuleProxyFactory.sol`) ; `zodiaceco/zodiac-modifier-roles@3a429ab902` (`Roles.sol`, `Types.sol`,
  `PermissionBuilder.sol`, `Integrity.sol`, `Topology.sol`, `AbiDecoder.sol`, `PermissionChecker.sol`, tests officiels).
- ABI vérifiées on-chain (Blockscout Base Sepolia), archivées dans `evidence/demo_runs/setup/abis/`.
- Lectures/écritures : `https://sepolia.base.org` (`eth_chainId`, `eth_getCode`, `eth_call`, `eth_sendRawTransaction`,
  `eth_getTransactionByHash`, `eth_getTransactionReceipt`), 2026-10-16.


## Addendum D10 — résolu le 2026-10-16

Version du mastercopy identifiée : **Zodiac Roles Modifier v2.1.1** (version corrigée post-incident 06/2026).

- Source vérifiée Blockscout du mastercopy `0xF2964CE6…83D5` : **26/26 fichiers identiques à l'artefact publié v2.1.1** (vs 24/26 pour v2.1.0) — les deux fichiers qui distinguent nos sources sont précisément les deux fichiers corrigés (`SignatureChecker.sol` : contrôle `success` du staticcall ERC-1271 ajouté ; `PermissionChecker.sol` : `payload.children`).
- `code_sha256` du mastercopy : `89c5dc3313b5669f669232de7033734b4ee10339297cdf523bee5eb1b093cd05` (identique Ethereum / Base / Base Sepolia, 24 409 octets).
- Enveloppe de référence mise à jour (`module.version=v2.1.1`, `advisory_clear=true`), preuve complète : `evidence/demo_runs/setup/d10_resolution.json`.
