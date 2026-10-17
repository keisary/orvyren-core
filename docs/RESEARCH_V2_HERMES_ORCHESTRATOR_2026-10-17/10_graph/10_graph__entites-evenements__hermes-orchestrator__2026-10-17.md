# 10_graph — Entités, événements et résolution

**Auteur / agent** : Hermes-orchestrateur (deepseek-flash, session recherche V2).
**Date** : 2026-10-17.
**Chantier** : `10_graph`.
**Statut** : INTERNE — recherche V2, ne pas soumettre.
**Périmètre** : modèle d'entités, modèle d'événements, résolution d'entités/événements, choix nœud/événement/relation/paramètre. Le schéma DDL détaillé est dans `10_graph__schema-cible__hermes__2026-10-17.md` ; ici, la sémantique et la résolution.
**Fichiers lus** : `src/orvyren/graph/{catalog,models,store,record,queries}.py`, `fixtures/graphs/*.json`, `evidence/graph.sqlite`, `B2_GRAPHE_ETUDE.md` §3.0–4, `MIMIR_Technical_Design.md` §10.1–10.5, `Project_2_DFKG_Research_State_0_a11y.docx` §5–12, `10_graph__audit-34-relations__mimo-v2.6-pro__2026-10-17.md`.

---

## 0. Verdict

Le dépôt a un **catalogue de nœuds** (58 `NodeKind`, 9 classes) et un **schéma v3** avec `nodes`, `events`, `node_aliases`, `event_observations`, mais **aucune résolution d'entités/événements n'est implémentée**, et le graphe live n'a ni entité ni événement.

Le vrai travail n'est pas d'ajouter des kinds : c'est de **décider ce qui est un nœud, un événement, une relation ou un paramètre**, puis d'écrire une résolution déterministe, sourcée et réversible.

**Décision recommandée** :

1. **Identité canonique = adresse on-chain namespacée** (`eip155:<chain>:<address>`), jamais un ticker.
2. **Événement = objet de première classe**, avec un ID `chain:tx:log`, des horloges, des acteurs/cibles, `actual/expected/surprise`, un statut et une provenance.
3. **Un événement n'est pas une relation** ; une relation n'est pas une observation ; un paramètre qui agit est `CONSTRAINS` + observation datée.
4. **Résolution déterministe d'abord**, LLM seulement pour les cas ambigus, avec provenance et réversibilité.
5. **72 h : on-chain seulement**, 10 000+ événements, 8–10 relations ; l'extraction documentaire reste à 2–3 documents.

---

## 1. Ce qui existe déjà

| Élément | État | Preuve |
|---|---|---|
| `NodeKind` | 58 kinds, 9 classes, `KIND_CLASS`, `ROLE_SETS` | `catalog.py:84–149,157–192,213–221` |
| Modèles | `Source`, `Observation`, `Claim`, `Relation`, `Hypothesis`, `DecisionNode` | `models.py:122–185` |
| Store v3 | `nodes`, `events`, `event_observations`, `node_aliases` | `store.py:58–258` |
| Record relation | 17 champs + `ChainRef` | `record.py:77–135` |
| Graphe live | 520 observations, 4 claims, 4 `SUPPORTS` ; aucune entité/événement | `evidence/graph.sqlite` |
| Fixtures | 20 records, 13 kinds | `fixtures/graphs/*.json` |

**Manque** : une table `entities` distincte n'est pas nécessaire si `nodes` porte les entités ; il manque surtout **la résolution** (alias, adresses, événements) et **le peuplement**.

---

## 2. Nœud, événement, relation ou paramètre ?

La règle B2 §3.4 est la bonne : **mesuré = Observation ; agit = Relation ; les deux quand les deux**, avec `DERIVED_FROM` du second vers le premier.

| Objet on-chain | Écriture correcte | Pourquoi |
|---|---|---|
| Prix, supply, TVL, taux, heartbeat | `Observation` | C'est une mesure horodatée, pas une arête |
| `isFrozen`, `supplyCap`, LTV, LT, pause | `Observation` du paramètre + `CONSTRAINS(paramètre → marché)` | La valeur est mesurée ; le paramètre agit |
| Détention | `HOLDS(adresse → actif)` + payload `{amount, unit, block}` | Exposition directe |
| Dette | `OWES(position/entité → dette)` | Exposition au passif |
| Dépôt | `DEPOSITED_IN(actif → marché)` | Chemin d'exposition |
| Collatéral | `COLLATERALIZES(actif → dette/marché)` | Risque de liquidation |
| Prix oracle | `PRICED_BY(actif/marché → oracle)` + observation du round | Valorisation et fraîcheur |
| Upgrade | `IMPLEMENTED_BY(proxy → implémentation)` + événement `Upgraded` | Le code peut changer |
| Rôle/permission | `MEMBER_OF`, `ALLOWS`, `REVOKES` | Qui peut quoi |
| Freeze, cap change, upgrade, liquidation | `Event` + relation/observation dérivée | C'est un changement d'état daté |
| Un document qui décrit un gel | `Event` + `EXTRACTED_FROM` (si le token est étendu) ou claim | La source documentaire reste une preuve |

**Règle** : ne jamais créer une arête par transfert ERC-20. Un transfert est un événement ; il ne devient une relation que s'il change une position, une permission ou une garantie.

---

## 3. Identités canoniques

### 3.1 Formats

| Objet | `node_id` | Exemple |
|---|---|---|
| Contrat / token / EOA | `addr:eip155:<chain>:<address_lower>` | `addr:eip155:8453:0x...` |
| Actif | `asset:eip155:<chain>:<address_lower>` | `asset:eip155:8453:0x...` |
| Marché / pool | `market:eip155:<chain>:<address_lower>` | `market:eip155:8453:0x...` |
| Organisation | `org:<slug>` | `org:circle` |
| Rôle | `role:eip155:<chain>:<modifier>:<role_key>` | `role:eip155:8453:0x...:AGENT` |
| Événement | `event:eip155:<chain>:<tx>:<log_index>` | `event:eip155:8453:0x...:12` |
| Observation | `obs:<fingerprint>` | `obs:547c6426c72953ad` |
| Claim | `claim:<fingerprint>` | `claim:d6cb095fc695a249` |
| Document | `doc:sha256:<hash>` | `doc:sha256:...` |
| Paramètre | `param:eip155:<chain>:<contract>:<name>` | `param:eip155:8453:0x...:supply_cap` |

**Adresses** : lowercase pour la clé, checksum EIP-55 pour l'affichage. Ne jamais utiliser un ticker comme clé.

### 3.2 Alias, pas identité

Un alias (`USDC`, `USD Coin`, `USDC.e`, `wstETH`) est une **preuve rattachée** à un nœud, avec source, date, confiance. `SAME_AS` est explicite et révisable ; jamais une fusion automatique.

Cas à ne pas confondre :

- `USDC` et `USDC.e` sont deux contrats ; `SAME_AS` seulement si la preuve de pont/wrapper le justifie.
- `wstETH` n'est pas `stETH` : c'est un wrapper (`WRAPS`, à ajouter), pas un alias.
- Un proxy et son implémentation ne sont pas le même contrat : `IMPLEMENTED_BY`, pas `SAME_AS`.

### 3.3 Pipeline de résolution

```
mention
  -> identifiant exact (adresse, LEI, ISIN, hash)
  -> normalisation déterministe (checksum, lowercase, decimals)
  -> génération de candidats (registre, alias, chaîne)
  -> score contextuel (source, chaîne, type, voisins)
  -> RESOLVED / PROBABLE / AMBIGUOUS / UNRESOLVED
  -> décision datée + provenance
```

- **Déterministe d'abord** : une adresse `chain:address` est canonique ; un nom ne l'est pas.
- **LLM uniquement pour `AMBIGUOUS`**, avec liste de candidats et justification ; jamais pour créer une adresse.
- **Réversible** : `SAME_AS` peut être superseded ; l'historique reste.
- **Provenance** : chaque résolution porte `source_id`, `method`, `confidence`, `run_id`.

### 3.4 Tests de résolution

1. Deux écritures de la même adresse (checksum/lowercase) → un seul nœud.
2. `USDC` vs `USDC.e` → deux nœuds, `SAME_AS` absent sans preuve.
3. `wstETH` vs `stETH` → `WRAPS`, pas `SAME_AS`.
4. Proxy → implémentation : `IMPLEMENTED_BY`, pas `SAME_AS`.
5. Alias sans source → refusé.
6. Résolution ambiguë → `AMBIGUOUS`, pas de fusion silencieuse.

---

## 4. Modèle d'événements

### 4.1 Objet

Un événement est un **changement d'état du monde** : gel, cap, upgrade, liquidation, rôle, pont, gouvernance, ou un communiqué qui annonce un tel changement.

Champs minimaux (schéma v3) :

```
event_id, event_type, chain_id, block_number, block_hash, tx_hash, log_index,
event_time, publication_time, observation_time, effective_time,
valid_from, valid_to, actors, targets, magnitude, actual, expected, surprise,
status, payload
```

### 4.2 Cycle de vie

`RUMOR → ANNOUNCED → CONFIRMED → IMPLEMENTED → CONSEQUENCE`

- Un événement on-chain confirmé peut être `CONFIRMED` puis `IMPLEMENTED`.
- Un communiqué est `ANNOUNCED` jusqu'à preuve on-chain.
- Une conséquence observée (liquidation en cascade) est un événement `CONSEQUENCE` ou une observation dérivée.
- **Ne jamais transformer un `MODEL-INFERRED` en `CONFIRMED`** sans preuve.

### 4.3 Résolution d'événements

- **1 document → N événements** : un communiqué peut annoncer plusieurs marchés/paramètres.
- **N documents → 1 événement** : plusieurs sources décrivent le même gel/upgrade.
- **Identité on-chain** : `(chain_id, tx_hash, log_index)` est canonique.
- **Identité documentaire** : `doc:sha256` + offsets + `EXTRACTED_FROM` ; pas de fusion sans preuve.
- **Dédoublonnage** : même `(chain, tx, log)` = un événement ; même événement décrit par deux docs = un événement + deux `event_observations`.

### 4.4 Types Aave/Safe/Zodiac

**Aave Pool** : `Supply`, `Withdraw`, `Borrow`, `Repay`, `LiquidationCall`, `FlashLoan`, `ReserveDataUpdated`, `ReserveUsedAsCollateralEnabled/Disabled`, `MintedToTreasury`.
**Oracle** : `AnswerUpdated`, `NewRound`.
**Tokens** : `Transfer`, `Approval`, `Mint`, `Burn`.
**Proxy** : `Upgraded`, `AdminChanged`, `BeaconUpgraded`.
**Safe** : `ExecutionSuccess`, `ExecutionFailure`, `EnabledModule`, `DisabledModule`, `ChangedThreshold`, `AddedOwner`, `RemovedOwner`, `ChangedGuard`.
**Zodiac Roles** : `AssignRoles`, `SetDefaultRole`, `RolesModSetup`, `ConsumeAllowance`.

### 4.5 Événement vs observation vs relation

| Question | Réponse |
|---|---|
| Un prix a changé | Observation (pas un événement) |
| Un marché a été gelé | Événement + `CONSTRAINS` daté |
| Un utilisateur a déposé | Événement `Supply` ; `DEPOSITED_IN` si la position change |
| Un rôle a été révoqué | Événement `Revoke` + `REVOKES` |
| Un oracle a un nouveau round | Événement `AnswerUpdated` + observation du prix |
| Un document annonce un gel | Événement `ANNOUNCED` + claim/preuve ; pas `CONSTRAINS` avant confirmation |

---

## 5. Plan 72 h

- **On-chain seulement** : Aave v3 Base, un marché, 30 jours, bloc finalisé.
- **10 000+ événements décodés** ; IDs `chain:tx:log`.
- **Résolution** : adresses/contrats via address book ; événements par ID on-chain ; alias seulement pour 5–10 entités.
- **8–10 relations** : `HOLDS`, `DEPOSITED_IN`, `COLLATERALIZES`, `PRICED_BY`, `CONSTRAINS`, `DEPLOYED_ON`, `OBSERVED_FROM`, `DERIVED_FROM`, `SUPPORTS`, `CONTRADICTS`.
- **2–3 documents** max : communiqué Aave/Chainlink, avec offsets et `EXTRACTED_FROM`.
- **Pas** de résolution universelle, pas de GraphRAG, pas d'extraction large.
- **Tests** : IDs, alias, doublons, proxy, event lifecycle, PIT.

---

## 6. Risques

| Risque | Mitigation |
|---|---|
| Ticker utilisé comme clé | Refus à l'écriture ; `node_id` namespacé |
| `USDC.e` fusionné avec `USDC` | `SAME_AS` seulement avec preuve ; test |
| Proxy pris pour l'implémentation | `IMPLEMENTED_BY` + `Upgraded` |
| Un document crée un fait | `ANNOUNCED`/claim, pas `CONFIRMED` |
| Doublons d'événements | clé `(chain, tx, log)` |
| Résolution LLM inventée | candidats + provenance + révision |
| Trop d'événements | 30 jours, 3–5 marchés, agrégation transfers |

---

## 7. Sources

- `src/orvyren/graph/catalog.py:84–149,157–192,213–221,272–408`.
- `src/orvyren/graph/models.py:122–185`.
- `src/orvyren/graph/store.py:58–258` (tables v3), `:590–639` (`insert_relation_record`).
- `src/orvyren/graph/record.py:77–135`.
- `fixtures/graphs/*.json` ; `evidence/graph.sqlite`.
- `B2_GRAPHE_ETUDE.md` §3.0–3.4, §4.2.
- `MIMIR_Technical_Design.md` §10.1–10.5 ; `Project_2_DFKG_Research_State_0_a11y.docx` §5–12.
- Aave `IPool.sol` — https://github.com/aave/aave-v3-core/blob/master/contracts/interfaces/IPool.sol — consulté 2026-10-17.
- Aave address book — https://github.com/aave/aave-address-book — consulté 2026-10-17.
- EIP-1967 — https://eips.ethereum.org/EIPS/eip-1967 — consulté 2026-10-17.
- Zodiac Roles — https://docs.roles.gnosisguild.org/ — consulté 2026-10-17.
- Safe docs — https://docs.safe.global/ — consulté 2026-10-17.
- Mimo audit : `10_graph/10_graph__audit-34-relations__mimo-v2.6-pro__2026-10-17.md` (58 kinds, 3 défauts validateur).
