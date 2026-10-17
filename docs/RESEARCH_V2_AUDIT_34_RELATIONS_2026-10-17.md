# Audit des 34 relations du graphe ORVYREN

**Statut** : INTERNE — recherche V2, ne pas soumettre.
**Auteur** : Hermes.
**Date** : 2026-10-17.
**Chantier** : `10_graph`.
**Fichiers lus** : `src/orvyren/graph/catalog.py`, `record.py`, `queries.py`, `store.py`, `models.py`, `fixtures/graphs/*.json`, `evidence/graph.sqlite`, `evidence/quality_report.json`, `B2_GRAPHE_ETUDE.md`, `MIMIR_Technical_Design.md` §10–11, `Project_2_DFKG_Research_State_0_a11y.docx` §3–18, `MIMIR_Project_Description_V3.docx` §5–6.
**Temps passé** : ~2 h de lecture/mesure.

---

## 0. Verdict

Le catalogue de 34 relations est **sérieux et réutilisable** : 8 relations de preuve/dérivation, 15 de structure/exposition, 3 de mécanisme économique, 8 de contrainte/permission ; 14 viennent de MIMIR/RC, 13 sont propres au DeFi/on-chain, 7 sont des ajouts explicites (B2 §3.3).

Mais le graphe **n'est pas construit** :

- `evidence/graph.sqlite` contient **520 observations, 4 claims, 4 relations**, et **ces 4 relations sont toutes `SUPPORTS`** (claim → hypothèse `H1-usdc-disclosure-disorder`). Il n'y a **aucune** arête structurelle (`HOLDS`, `DEPOSITED_IN`, `COLLATERALIZES`, `DEPLOYED_ON`, `PRICED_BY`, etc.).
- Il n'y a **aucune table `entities` ni `events`** ; les 520 observations sont des séries de prix/supply, pas un monde on-chain.
- Les 3 fixtures utilisent **20 records et 13 kinds** ; 21 kinds du catalogue ne sont jamais instanciés, même en fixture.
- Le record à 17 champs est **spécifié** (`record.py`) et, depuis le 17/10 (master `29db54b`), **persisté par le store** (schéma v3) ; mais `evidence/graph.sqlite` n'a pas encore été régénérée, donc le graphe live reste 520/4/4. Les Q1–Q8 restent des fonctions pures sur des `RelationRecord` de fixtures (`queries.py`), pas des requêtes SQL sur le graphe live.

**Conclusion** : le catalogue est un **plan**, pas un graphe. Le chantier prioritaire n'est pas d'ajouter 30 types de plus ; c'est de **peupler 8–10 relations avec des données on-chain réelles** (16 maximum conditionnel, cf. contradiction Codex), de **persister le record 17 champs**, et de faire tourner Q1–Q8 sur ce graphe.

---

## 1. Méthode

1. Extraction programmatique du catalogue : `RELATION_CATALOG`, `catalog_stats()`, origines M/D/N.
2. Comptage des relations dans `evidence/graph.sqlite` et dans les 3 fixtures.
3. Lecture de `B2_GRAPHE_ETUDE.md` §3.0–§3.4 (record, familles, catalogue, cas état-vs-relation), §4 (pipeline), §5 (ML), §6 (Q1–Q14), §7 (recommandations).
4. Lecture de MIMIR §10.1–10.6 (objet, event, temps, store), §11.2–11.4 (relation, causalité, propagation), §8.3 (révision).
5. Classification `P0/P1/P2` et `72 h Oui/Partiel/Non` selon la valeur pour la démo et le coût de peuplement.

**Limite** : je n'ai pas exécuté d'ingestion on-chain dans cette passe ; les colonnes « source » et « usage » sont des propositions de conception, pas des mesures. Les comptages sont mesurés.

---

## 2. Ce que le catalogue contient

| Famille | Nombre | Rôle | Exemples |
|---|---:|---|---|
| Preuve et dérivation | **8** | Relier une observation, un claim, une relation à sa source, à son document, à sa recette, à une hypothèse | `OBSERVED_FROM`, `EXTRACTED_FROM`, `DERIVED_FROM`, `SUPPORTS`, `REFUTES`, `CONTRADICTS`, `SUPERSEDES`, `SAME_AS` |
| Structure et exposition | **15** | Décrire le monde : actifs, contrats, marchés, positions, ponts, oracles, custody | `DEPLOYED_ON`, `ISSUED_BY`, `TARGETS_PEG`, `HOLDS`, `OWES`, `DEPOSITED_IN`, `COLLATERALIZES`, `PRICED_BY` |
| Mécanisme économique | **3** | Décrire une transmission économique, avec statut épistémique | `AFFECTS`, `DEPENDS_ON`, `CORRELATES_WITH` |
| Contrainte et permission | **8** | Décrire qui peut quoi, ce qui limite quoi, qui gouverne quoi | `CONSTRAINS`, `AUTHORIZES`, `REVOKES`, `MEMBER_OF`, `ALLOWS`, `ADMINISTERED_BY`, `GOVERNED_BY`, `REGULATED_BY` |
| **Total** | **34** | | |

Origine : **14 M** (MIMIR/RC), **13 D** (DeFi/on-chain définis par B2), **7 N** (nouveaux explicites). Le catalogue est donc déjà un travail d'adaptation, pas une copie.

---

## 3. Ce qui est réellement instancié

### 3.1 Graphe live

```text
evidence/graph.sqlite
├── sources              : table présente
├── observations         : 520
├── claims               : 4
├── relations            : 4  (toutes SUPPORTS)
├── hypotheses           : 1  (H1-usdc-disclosure-disorder)
├── decision_nodes       : présent
├── entities             : ABSENT
└── events               : ABSENT
```

Les 4 relations :

| relation | src | dst | kind |
|---|---|---|---|
| `rel-b484dd909f3b72c6` | `claim-defillama-low-main` | `H1-usdc-disclosure-disorder` | `SUPPORTS` |
| `rel-8efa956ea16ad535` | `claim-bitstamp-low-main` | `H1-usdc-disclosure-disorder` | `SUPPORTS` |
| `rel-c5ac6abdaf64c728` | `claim-binance-low-main` | `H1-usdc-disclosure-disorder` | `SUPPORTS` |
| `rel-365a6bd413aa8b9b` | `claim-supply-contraction` | `H1-usdc-disclosure-disorder` | `SUPPORTS` |

**Interprétation** : le graphe live est un **graphe de preuve d'un cas**, pas un graphe du monde. Il ne peut pas répondre à « quelles sont mes expositions ? », « quel marché dépend de quel oracle ? », « qui peut déplacer mes fonds ? ».

### 3.2 Fixtures

| Fichier | Records | Kinds distincts |
|---|---:|---:|
| `fixtures/graphs/usdc_2023-03.json` | 9 | 6 |
| `fixtures/graphs/steth_2022-06.json` | 4 | 2 |
| `fixtures/graphs/rseth_2026-04.json` | 7 | 6 |
| **Total** | **20** | **13** |

Kinds utilisés dans les fixtures : `AFFECTS`, `COLLATERALIZES`, `CONSTRAINS`, `CONTRADICTS`, `DEPENDS_ON`, `DEPOSITED_IN`, `DERIVED_FROM`, `EXTRACTED_FROM`, `HOLDS`, `OBSERVED_FROM`, `OWES`, `PRICED_BY`, `SUPPORTS`.

**21 kinds du catalogue ne sont jamais instanciés, même en fixture** : `REFUTES`, `SUPERSEDES`, `SAME_AS`, `IS_A`, `PART_OF`, `DEPLOYED_ON`, `ISSUED_BY`, `TARGETS_PEG`, `REDEEMABLE_VIA`, `CUSTODIED_AT`, `REHYPOTHECATED_TO`, `BRIDGED_VIA`, `VERIFIED_BY`, `CORRELATES_WITH`, `AUTHORIZES`, `REVOKES`, `MEMBER_OF`, `ALLOWS`, `ADMINISTERED_BY`, `GOVERNED_BY`, `REGULATED_BY`.

### 3.3 Le record 17 champs : de la spécification au store (corrigé le 17/10)

`record.py:86–135` définit 17 groupes de champs (identité, famille, kind, src/dst typés, mécanisme, signe, conditions/régime/horizon, statut épistémique, lifecycle, validation, validité, révision, provenance, extraction, chain_ref, confiance, payload). `record.py:138–156` les liste.

**Avant le 17/10**, `store.py` ne stockait que 7 champs métier + `inserted_at` ; la base live n'utilisait pas le record. **Depuis master `29db54b`**, la table `relations` du schéma v3 stocke les 17 champs + les champs on-chain (`chain_id`, bloc, tx, log, finalité, confiance, payload), et `insert_relation_record` écrit la provenance. La base `evidence/graph.sqlite` n'a pas encore été régénérée : le graphe live reste donc 520/4/4. Le prochain test de vérité est l'ingestion Aave, pas le schéma.

---

## 4. Audit complet des 34 relations

Légende :
- **Fam.** : P = preuve/dérivation, S = structure/exposition, M = mécanisme, C = contrainte/permission.
- **Live** : nombre de lignes dans `evidence/graph.sqlite`.
- **Fix.** : nombre de records dans les 3 fixtures.
- **Source** : source de données réaliste pour peupler la relation.
- **Usage** : requête(s) ou décision(s) qui justifient la relation (Q1–Q14 de B2 ; Q1–Q8 existent dans `queries.py`).
- **Prio** : P0 = indispensable à la démo ; P1 = utile si cheap ; P2 = report.
- **72 h** : Oui = peupler ; Partiel = schéma + quelques instances ; Non = schéma seulement.

| # | Type (origine) | Fam. | Sujet → Objet | Sémantique | Live | Fix. | Source | Usage | Prio | 72 h |
|---|---|---|---:|---|---:|---:|---|---|---|---|
| 1 | `OBSERVED_FROM` (M) | P | Observation → Source | La mesure vient de cette source (endpoint, retrieved_at, limites) | 0 | 6 | Toutes les observations | Q6 provenance ; audit | P0 | Oui |
| 2 | `EXTRACTED_FROM` (M) | P | Claim/Relation → Document/Observation | L'élément est extrait d'un document/passage (offsets + run versionné) | 0 | 4 | Docs, communiqués, extraction | Q6 ; preuve documentaire | P0 | Oui (2–3 docs) |
| 3 | `DERIVED_FROM` (M) | P | Claim/Relation → Claim/Observation | Fait calculé à partir de parents via une recette versionnée | 0 | 2 | Calculs (prix, supply, ratios) | Q6 ; reproductibilité | P0 | Oui |
| 4 | `SUPPORTS` (M) | P | Claim → Hypothèse | Ce fait soutient cette hypothèse, sans transmission économique | **4** | 1 | Claims validés | Q3/Q10 ; décision | P0 | Oui |
| 5 | `REFUTES` (N) | P | Claim → Hypothèse | Ce fait réfute cette hypothèse selon un critère pré-déclaré | 0 | 0 | Claims validés | Q10 ; abstention | P0 | Oui |
| 6 | `CONTRADICTS` (N) | P | Claim → Claim | Deux faits incompatibles coexistent, jamais fusionnés | 0 | 1 | Claims de sources différentes | Q3 ; recherche | P0 | Oui |
| 7 | `SUPERSEDES` (M) | P | Tout → Tout | La révision remplace l'ancienne sans l'effacer | 0 | 0 | Révisions, corrections | Q13 ; PIT | P1 | Partiel |
| 8 | `SAME_AS` (N) | P | Tout → Tout | Alias résolu : deux références = une identité canonique | 0 | 0 | Résolution d'entités | Q4/Q6 ; dédoublonnage | P1 | Partiel |
| 9 | `IS_A` (N) | S | Entité/Actif → Classe | Taxonomie (USDC IS_A stablecoin ; rsETH IS_A LST) | 0 | 0 | Registre d'actifs | Q1/Q7 ; classes | P1 | Partiel |
| 10 | `PART_OF` (N) | S | Entité/Contrat → Entité | Appartenance structurelle (réserve PART_OF pool ; aToken PART_OF Aave) | 0 | 0 | Address book, docs | Q1/Q12 | P1 | Partiel |
| 11 | `DEPLOYED_ON` (D) | S | Actif/Contrat → Chaîne | Présence d'un contrat/asset sur cette chaîne | 0 | 0 | RPC, address book | Q11 ; multi-chaîne | P0 | Oui |
| 12 | `ISSUED_BY` (M) | S | Actif → Organisation | L'actif est émis par cette entité | 0 | 0 | Docs, registre | Q1/Q7 ; risque émetteur | P0 | Oui |
| 13 | `TARGETS_PEG` (D) | S | Actif → Actif/Unité | Parité cible (1 USD, 1 ETH), pas une garantie | 0 | 0 | Docs, oracle | Q9 ; depeg | P0 | Oui |
| 14 | `REDEEMABLE_VIA` (M) | S | Actif → Contrat/Facilité | Redemption/time-lock via cette facilité | 0 | 0 | Docs, contrat | Q1/Q9 ; liquidité | P1 | Partiel |
| 15 | `CUSTODIED_AT` (M) | S | Actif → Contrat/Dépositaire | L'actif repose chez ce dépositaire (wrapping, PSM, escrow) | 0 | 0 | Docs, on-chain | Q1/Q9 ; custody | P1 | Partiel |
| 16 | `HOLDS` (M) | S | Adresse/Entité → Actif | Détient N unités à (chaîne, bloc) | 0 | 1 | RPC, treasury | Q1 ; exposition | P0 | Oui |
| 17 | `OWES` (M) | S | Entité/Position → Dette | Doit N unités sur ce marché (taux, échéance) | 0 | 1 | Aave/Compound | Q1/Q7 ; levier | P0 | Oui |
| 18 | `DEPOSITED_IN` (D) | S | Actif → Marché/Pool | Dépôt dans un marché/pool (Aave reserve, Curve pool) | 0 | 1 | RPC | Q1 ; exposition | P0 | Oui |
| 19 | `COLLATERALIZES` (D) | S | Actif → Dette/Marché | Sert de collatéral pour cette dette (LTV/LT dans payload) | 0 | 1 | RPC, Aave config | Q1/Q7 ; liquidation | P0 | Oui |
| 20 | `REHYPOTHECATED_TO` (D) | S | Actif → Protocole | L'actif reçu est re-plédgé/re-hypothéqué à ce protocole | 0 | 0 | Docs, on-chain | Q1/Q2 ; contagion | P1 | Non |
| 21 | `BRIDGED_VIA` (D) | S | Actif → Pont/OApp | L'émission sur cette chaîne dépend de ce pont | 0 | 0 | Docs, on-chain | Q11 ; risque pont | P1 | Non |
| 22 | `VERIFIED_BY` (D) | S | Pont/OApp → Config vérif. | La sécurité du pont repose sur ces vérifieurs (count, DVN) | 0 | 0 | Docs, on-chain | Q11/Q12 ; pont | P1 | Non |
| 23 | `PRICED_BY` (D) | S | Actif/Marché → Oracle | Valorisation adossée à ce feed (type, heartbeat, cap) | 0 | 1 | RPC, oracle | Q9 ; oracle stale | P0 | Oui |
| 24 | `AFFECTS` (M) | M | Entité/Instrument/Variable → idem | Mécanisme M transmet un changement (signe, horizon, conditions, statut) | 0 | 1 | Docs, curé | Q2/Q10 ; propagation | P1 | Partiel (3–5) |
| 25 | `DEPENDS_ON` (N) | M | Entité → Entité | X dépend économiquement de Y (canal, sensibilité) | 0 | 1 | Docs, curé | Q2/Q10 ; contagion | P1 | Partiel (3–5) |
| 26 | `CORRELATES_WITH` (N) | M | Entité → Entité | Lien statistique, statut STATISTICAL obligatoire, jamais causal | 0 | 0 | Calcul | Q2 (interdit propagation) | P2 | Non |
| 27 | `CONSTRAINS` (M) | C | Paramètre/Règle/Institution → Actif/Marché/Action | Limite le comportement (supplyCap, LTV, freeze, timelock) | 0 | 2 | RPC, config | Q1/Q8/Q9 ; risque | P0 | Oui (freeze/cap/LTV) |
| 28 | `AUTHORIZES` (M) | C | Autorité → Sujet | Accorde un droit (scope, instruments, dates, preuve) | 0 | 0 | Safe/Zodiac | Q8 ; permissions | P1 | Partiel |
| 29 | `REVOKES` (M) | C | Autorité → Droit/Sujet | Révoque un droit (événement daté) | 0 | 0 | Logs | Q8/Q13 | P1 | Partiel |
| 30 | `MEMBER_OF` (D) | C | Adresse → Rôle | Membre de ce rôle à (chaîne, bloc) — `AssignRoles` | 0 | 0 | Zodiac logs | Q8 ; agent wallet | P0 | Oui |
| 31 | `ALLOWS` (D) | C | Rôle → Cible/Fonction | Le rôle autorise cette cible/fonction (allowlist, allowance) | 0 | 0 | Zodiac config | Q8 ; policy | P0 | Oui |
| 32 | `ADMINISTERED_BY` (D) | C | Contrat/Module → Safe/Multisig | Admin/owner du contrat (`owner()`, module) | 0 | 0 | RPC, Safe | Q12/Q8 ; contrôle | P0 | Oui |
| 33 | `GOVERNED_BY` (D) | C | Contrat/Protocole → DAO/Timelock | Paramètres gouvernés par cette instance | 0 | 0 | Docs, on-chain | Q12 ; gouvernance | P1 | Partiel |
| 34 | `REGULATED_BY` (D) | C | Actif/Entité → Régime/Licence | Encadrement réglementaire (hors démo) | 0 | 0 | Docs | Vision | P2 | Non |

**Lecture** : **18 relations sont `P0`** : 1, 2, 3, 4, 5, 6 (preuve), 11, 12, 13, 16, 17, 18, 19, 23 (structure), 27, 30, 31, 32 (contrainte). Le sous-ensemble réaliste pour 72 h est **16–18** : 18 si on branche l'extraction documentaire (`EXTRACTED_FROM`) et `REFUTES` ; 16 si on coupe ces deux et qu'on garde les 16 autres. Le reste est `P1/P2` et doit rester schema-only.

---

## 5. Types manquants ou extensions nécessaires

Le catalogue est bon, mais il a trois angles morts pour le on-chain :

### 5.1 `IMPLEMENTED_BY` (proxy → implémentation) — **candidat 35**

**Pourquoi** : les contrats Aave, Safe, Zodiac, bridges et tokens sont souvent derrière un proxy. `ADMINISTERED_BY` dit qui peut upgrade, pas **quelle implémentation** est active. Sans cette relation, on ne peut pas répondre à « le code a-t-il changé entre le bloc B1 et B2 ? », ni distinguer un upgrade légitime d'une compromission.

**Forme proposée** :

```
IMPLEMENTED_BY : CONTRAT (proxy) → CONTRAT (implementation)
  chain_ref : (chain_id, block, tx_hash)
  valid_from / valid_to : block range
  payload : {proxy_type: EIP1967|transparent|beacon, implementation_slot, admin}
```

**Source** : event `Upgraded(address indexed implementation)` (EIP-1967), `BeaconUpgraded`, `AdminChanged` ; ou lecture du slot EIP-1967 au bloc.
**Usage** : Q12 (chaîne de contrôle), Q13 (révision), risque d'upgrade.
**Priorité** : P1 ; **72 h : Partiel** (Aave Pool proxy + implémentation actuelle).

### 5.2 `EVENT` comme sujet de `AFFECTS` / `EXTRACTED_FROM` / `DERIVED_FROM`

Aujourd'hui, `AFFECTS` n'accepte que `ENTITE`, `INSTRUMENT`, `VARIABLE` ; `EXTRACTED_FROM` et `DERIVED_FROM` n'acceptent que `CLAIM`, `RELATION`. Or un événement (gel, upgrade, liquidation, depeg) est un objet de première classe ; il doit pouvoir **affecter** un marché et être **extrait** d'un document.

**Proposition** : étendre les tokens sujet de `AFFECTS` à `EVENT`, et ceux de `EXTRACTED_FROM`/`DERIVED_FROM` à `EVENT` (ou créer `EVENT_AFFECTS`/`EVENT_EXTRACTED_FROM` si on veut garder les kinds séparés). C'est un changement de schéma, pas un nouveau type métier.

**Usage** : Q5 (chronologie), Q6 (provenance), Q10 (fait manquant).
**Priorité** : P0 pour le modèle d'événements ; **72 h : Oui** (au moins le token `EVENT` dans le validateur).

### 5.3 `ROLE_OF` (rôle → contrat/protocole) — **candidat 36**

`MEMBER_OF` relie une adresse à un rôle ; `ALLOWS` relie un rôle à une cible/fonction. Mais rien ne relie explicitement un rôle à **son contrat de permissions** (le Roles Modifier). Pour Q8, on peut inférer via `ALLOWS`, mais c'est fragile.

**Proposition** :

```
ROLE_OF : ROLE → CONTRAT (Roles Modifier / Safe)
  payload : {role_key, admin, default_role, guard}
```

**Source** : `RolesModSetup`, `SetDefaultRole`, config Zodiac.
**Usage** : Q8, policy, audit.
**Priorité** : P1 ; **72 h : Partiel**.

### 5.4 Ce qu'il ne faut pas ajouter

- Pas de `HAS_PRICE`, `HAS_SUPPLY`, `HAS_TVL` : ce sont des **observations**, pas des relations. La règle B2 §3.4 s'applique : **mesuré = Observation ; agit = relation ; les deux quand les deux**, avec `DERIVED_FROM`.
- Pas de `HAS_PARAMETER` : `CONSTRAINS(paramètre → marché)` suffit ; le paramètre est un nœud.
- Pas de `HAS_ROLE` : `MEMBER_OF` + `ALLOWS` + `ROLE_OF` couvrent le besoin.
- Pas de `HAS_AUDIT` : un audit est un document, relié par `EXTRACTED_FROM`.
- Pas de relation causale générique : `AFFECTS` doit porter mécanisme, signe, conditions, horizon, statut épistémique.

---

## 6. Ne pas confondre état, observation et relation

C'est le piège qui a déjà produit un graphe de 4 relations.

| Objet | Écriture correcte | Exemple |
|---|---|---|
| Prix, supply, TVL, taux, heartbeat | `Observation` | USDC price 0,87667 à 2023-03-11T08:00Z |
| Paramètre qui **agit** (freeze, cap, LTV, LT) | `CONSTRAINS(paramètre → marché)` + `Observation` du paramètre | `isFrozen=true` au bloc 24 908 723 ; `supplyCap` 99,999 % |
| Détention | `HOLDS(adresse → actif)` avec payload `{amount, block, role}` | Trésorerie détient 100 USDC |
| Dette | `OWES(position/entité → dette)` | Position doit 50 USDC sur Aave |
| Dépôt | `DEPOSITED_IN(actif → marché)` | 100 USDC déposés dans Aave v3 Base |
| Collatéral | `COLLATERALIZES(actif → dette/marché)` | 100 USDC collatéralisent 50 USDC de dette |
| Prix oracle | `PRICED_BY(actif/marché → oracle)` + `Observation` du round | USDC prix par feed Chainlink |
| Upgrade | `IMPLEMENTED_BY(proxy → implémentation)` + `Observation` du slot | Aave Pool proxy → implémentation X |
| Permission | `MEMBER_OF` + `ALLOWS` + `REVOKES` | Agent est membre du rôle AGENT ; rôle autorise `transfer` |
| Contradiction | `CONTRADICTS(claim → claim)` | DeFiLlama dit 0,876 ; Binance dit 0,912 |

**Règle** : une relation doit changer une réponse de décision. Si elle ne sert à aucune requête, elle ne mérite pas d'être peuplée.

---

## 7. Priorisation 72 h

### 7.1 Les 8–10 relations à peupler d'abord

| Rang | Relation | Pourquoi |
|---:|---|---|
| 1 | `DEPLOYED_ON` | Ancre chaque contrat/asset dans une chaîne ; prérequis de tout le reste |
| 2 | `ISSUED_BY` | Identité de l'émetteur (USDC, rsETH, LST) |
| 3 | `TARGETS_PEG` | Détecter un depeg par rapport à la cible |
| 4 | `HOLDS` | Exposition directe de la trésorerie |
| 5 | `OWES` | Dette/levier |
| 6 | `DEPOSITED_IN` | Exposition aux marchés |
| 7 | `COLLATERALIZES` | Risque de liquidation |
| 8 | `PRICED_BY` | Oracle, heartbeat, stale price |
| 9 | `CONSTRAINS` | Freeze, cap, LTV, LT, pause |
| 10 | `MEMBER_OF` | Rôle de l'agent dans le wallet |
| 11 | `ALLOWS` | Fonctions autorisées par le rôle |
| 12 | `ADMINISTERED_BY` | Admin/owner, module, Safe |
| 13 | `OBSERVED_FROM` | Provenance de chaque observation |
| 14 | `DERIVED_FROM` | Prix/supply/ratios calculés |
| 15 | `SUPPORTS` | Claims → hypothèses |
| 16 | `CONTRADICTS` | Contradictions de sources |

Le **slice 72 h** retenu après contradiction Codex = **10 relations** : rangs 1, 4, 6, 7, 8, 9, 13, 14, 15, 16 (`DEPLOYED_ON`, `HOLDS`, `DEPOSITED_IN`, `COLLATERALIZES`, `PRICED_BY`, `CONSTRAINS`, `OBSERVED_FROM`, `DERIVED_FROM`, `SUPPORTS`, `CONTRADICTS`). Les rangs 2, 3, 5 et 10–12 (`ISSUED_BY`, `TARGETS_PEG`, `OWES`, permissions Safe) sont **conditionnels** : à n'ajouter que si le parcours ou le wallet les utilise réellement. Les 16 ne sont pas un quota.

`REFUTES` et `SAME_AS` sont les suivants ; `AFFECTS`/`DEPENDS_ON` peuvent être ajoutés si le temps le permet (3–5 mécanismes curés, pas plus).

### 7.2 Ce qu'on ne fait pas en 72 h

- Pas de `REHYPOTHECATED_TO`, `BRIDGED_VIA`, `VERIFIED_BY` si le périmètre est Aave v3 Base sans bridge.
- Pas de `GOVERNED_BY`/`REGULATED_BY` au-delà d'un exemple.
- Pas de `CORRELATES_WITH` : c'est statistique, non causal, et il ne doit jamais être chaîné.
- Pas de `AFFECTS` générique : seulement des mécanismes nommés, avec source et conditions.
- Pas de 34 types peuplés : 8–10 relations bien faites valent mieux que 34 coquilles.

---

## 8. Mapping relations → requêtes

| Requête | Relations nécessaires | État actuel |
|---|---|---|
| Q1 exposition consolidée | `HOLDS`, `DEPOSITED_IN`, `COLLATERALIZES`, `OWES` | fixtures seulement ; live 0 |
| Q2 chemins de dépendance | `DEPENDS_ON`, `AFFECTS` | fixtures 2 ; live 0 |
| Q3 contradictions | `CONTRADICTS`, `SUPPORTS` | live 4 supports ; 0 contradiction |
| Q4 PIT | toutes + `valid_from/to`, `revision` | record non persisté |
| Q5 chronologie | `OBSERVED_FROM`, `EXTRACTED_FROM`, `AFFECTS` (event) | pas d'events |
| Q6 provenance | `OBSERVED_FROM`, `EXTRACTED_FROM`, `DERIVED_FROM` | 0 live |
| Q7 concentration | `OWES`, `COLLATERALIZES`, `HOLDS` | fixtures 3 ; live 0 |
| Q8 permissions | `MEMBER_OF`, `ALLOWS`, `REVOKES`, `ADMINISTERED_BY` | live 0 |
| Q9 fraîcheur | `PRICED_BY`, observations | live 0 |
| Q10 faits manquants | toutes + hypothèses | impossible sans kinds |
| Q11 invariants inter-chaînes | `DEPLOYED_ON`, `BRIDGED_VIA` | live 0 |
| Q12 chaîne de contrôle | `ADMINISTERED_BY`, `GOVERNED_BY`, `IMPLEMENTED_BY` | live 0 |
| Q13 révision | `SUPERSEDES`, `valid_to` | live 0 |
| Q14 recherche sémantique | documents/claims + pgvector | non câblé |

**Conclusion** : **aucune des 14 requêtes ne peut être exécutée sur le graphe live dans son état actuel**. Q1–Q8 ne tournent que sur des fixtures. C'est le vrai indicateur de maturité du graphe.

---

## 9. Décisions recommandées

1. **Garder les 34 types** comme catalogue normatif, mais **ne pas les peupler tous**. Le catalogue est une vision ; le graphe est un produit.
2. **Adopter le record 17 champs comme schéma de stockage**, pas seulement comme dataclass de fixture. Ajouter les champs DeFi : `chain_id`, `block_number`, `tx_hash`, `log_index`, `finality`, `payload`.
3. **Ajouter `IMPLEMENTED_BY`** (35e candidat) et étendre `AFFECTS`/`EXTRACTED_FROM`/`DERIVED_FROM` à `EVENT`. Ajouter `ROLE_OF` seulement si Q8 l'exige.
4. **Peupler 8–10 relations** sur Aave v3 Base + trésorerie de démonstration, avec **10 000+ événements** (50 000 seulement si le débit RPC est mesuré) et **8 000+ relations** ; 16 types = maximum conditionnel, pas un quota.
5. **Faire tourner Q1–Q8 sur SQL**, avec un test de parité fixture ↔ SQL : les mêmes records doivent produire les mêmes résultats.
6. **Ne pas ajouter de base graphe** : SQLite pour la démo, PostgreSQL + `WITHOUT OVERLAPS` (PG 19) pour la cible ; **pas de SQL/PGQ** (patch reverté) ; DuckDB pour l'analytique. Le graphe est petit ; le problème est le schéma et les données, pas le moteur.
7. **Ne pas utiliser de GNN/GraphRAG** dans le chemin de décision v1. B2 §5.3 le dit déjà : aucun modèle appris dans le confirmatoire.

---

## 10. Questions ouvertes

| # | Question | Impact |
|---|---|---|
| QO-1 | Quelle profondeur de confirmation pour un fait on-chain (reorg) ? | PIT et validation |
| QO-2 | Identité des proxies upgradeables : adresse du proxy ou suivi des implémentations ? | `IMPLEMENTED_BY` |
| QO-3 | Où vivent les quantités (`HOLDS`/`OWES`) : payload ou table `positions` ? | Q1/Q7, double comptage |
| QO-4 | Les `conditions` de `AFFECTS` : enum ou mini-DSL ? | propagation |
| QO-5 | Les événements sont-ils des nœuds `EVENT` ou des observations enrichies ? | modèle, Q5 |
| QO-6 | Faut-il un `ROLE_OF` ou inférer le contrat de rôle via `ALLOWS` ? | Q8 |
| QO-7 | Quel périmètre exact pour la démo : Aave v3 Base seul, ou Aave + un pont + un stablecoin ? | 72 h |
| QO-8 | Combien de relations peuvent être peuplées automatiquement sans curation ? | effort |

---

## 11. Sources

### 11.1 Internes

- `D:/orvyren_core/src/orvyren/graph/catalog.py:272–408` — 34 specs ; `:414–419` — stats.
- `D:/orvyren_core/src/orvyren/graph/record.py:86–135` — record 17 champs ; `:138–156` — groupes ; `:226+` — validation.
- `D:/orvyren_core/src/orvyren/graph/queries.py:10–27` — Q1–Q8 ; `:89+` — Q1 ; `:134+` — Q2 ; `:198+` — Q3 ; `:215+` — Q4 ; `:224+` — Q5 ; `:251+` — Q6 ; `:288+` — Q7 ; `:336+` — Q8.
- `D:/orvyren_core/src/orvyren/graph/store.py:52–134` — schéma SQLite ; `:94–104` — table `relations` à 7 colonnes.
- `D:/orvyren_core/src/orvyren/graph/models.py:122–165` — `Source`, `Claim`, `Relation`.
- `D:/orvyren_core/fixtures/graphs/*.json` — 20 records, 13 kinds.
- `D:/orvyren_core/evidence/graph.sqlite` — 520 observations, 4 claims, 4 supports.
- `D:/orvyren_archive_2026-10-15/research/B2_GRAPHE_ETUDE.md` — §3.0–3.4, §4, §5, §6, §7.
- `D:/midas_v2/MIMIR/docs/MIMIR_Technical_Design.md` — §10.1–10.6, §11.2–11.4, §8.3.
- `C:/Users/User/Downloads/Project_2_DFKG_Research_State_0_a11y.docx` — §7–18.
- `D:/midas_v2/MIMIR/docs/MIMIR_Project_Description_V3.docx` — §5–6.

### 11.2 Externes

- Aave, `IPool.sol` — https://github.com/aave/aave-v3-core/blob/master/contracts/interfaces/IPool.sol (events `Supply`, `Withdraw`, `Borrow`, `Repay`, `LiquidationCall`, `ReserveDataUpdated`) — consulté 2026-10-17.
- Aave, adresses des marchés — https://github.com/aave/aave-address-book — consulté 2026-10-17.
- Aave, docs Pool — https://aave.com/docs/aave-v3/smart-contracts/pool — consulté 2026-10-17.
- EIP-1967, storage slots des proxies — https://eips.ethereum.org/EIPS/eip-1967 — consulté 2026-10-17.
- Zodiac Roles — https://docs.roles.gnosisguild.org/ — consulté 2026-10-17.
- Safe docs — https://docs.safe.global/ — consulté 2026-10-17.
- Base docs — https://docs.base.org/ — consulté 2026-10-17.
- PostgreSQL, documentation courante — https://www.postgresql.org/docs/current/index.html — consulté 2026-10-17.
- PostgreSQL 19, tables temporelles (`WITHOUT OVERLAPS`) — https://www.postgresql.org/docs/19/ddl-temporal-tables.html — consulté 2026-10-17.
- PostgreSQL, commit SQL/PGQ puis rollback — https://git.postgresql.org/gitweb/?p=postgresql.git;a=commit;h=2f094e7ac69 et https://git.postgresql.org/pg/commitdiff/2b9e1aff4d3d933ae8ee377fef22c2af9c7797e8 — consulté 2026-10-17.
- SQLite recursive CTE — https://sqlite.org/lang_with.html — consulté 2026-10-17.
- MIMIR/DFKG, voir §3 du brief et les documents internes ci-dessus.
