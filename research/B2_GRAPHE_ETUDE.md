# B2 — ÉTUDE DU BLOC GRAPHE (DFKG)

**Version 1 — 15 octobre 2026.** Auteur : sous-agent B2 (chantier « graphe » de la carte des zones d'ombre, questions 2.1–2.6 de `SYSTEME_ZONES_OMBRE.md` §2).
**Périmètre** : document de RECHERCHE et de PROPOSITION — il prépare la décision d'équipe, il ne la remplace pas. À valider en revue, puis à intégrer au futur gel v2 et au document technique.
**Matière brute et recherches** : `research/raw_b2/` (82 fichiers : 2 notes internes, 52 recherches JSON sauvegardées, 28 extraits de pages).
**Statuts utilisés dans tout le document** :
- **[FAIT SOURCÉ]** — vérifié dans une source citée (interne au dépôt ou en ligne), URL + date d'accès ;
- **[MESURÉ]** — mesuré par le projet lui-même (rapports W2-x, W3-x, code) ;
- **[PROPOSITION]** — proposition de ce document, à trancher ;
- **[NON TROUVÉ]** — recherché, introuvable, dit tel quel.

**Sources internes principales** : `D:\midas_v2\MIMIR\docs\MIMIR_Technical_Design.md` (v0.1, 16/09/2026, lu en entier — LA source d'inspiration) · `research/SYSTEME_ZONES_OMBRE.md` §2 · `ARCHITECTURE_V1.md` §2–4 · `research/REVUE_CROISEE_ET_CADRE_CONCRET.md` §2.3 (4 familles) · `research/W2B_signaux_detection.md` · `research/W2C_enveloppe_execution.md` · code `src/orvyren/graph/` + `src/orvyren/data/`.

---

## 0. RÉSUMÉ EXÉCUTIF (les 6 réponses)

1. **Temporel/PIT** — le modèle à retenir est le **bitemporel classique** (Snodgrass / SQL:2011) croisé avec les **six horloges** de MIMIR : chaque fait porte un temps du monde (`ts_event`, `valid_from/valid_to`) **et** un temps de connaissance (`retrieved_at`/`inserted_at` + `revision`). Toutes les requêtes « état à l'instant T » filtrent **les deux**. Deux modes distincts : « le monde à T » et « ce qu'on savait à T » — la décision utilise l'intersection. Implémentable dès aujourd'hui sur SQLite append-only (revues + filtre) ; PostgreSQL 19 (beta) apporte l'*application time* natif (`WITH OVERLAPS`) mais **pas** le *system time*. Voir §1.
2. **Stockage** — **PostgreSQL reste la cible** (extension `pgvector` pour les embeddings, **SQL/PGQ** natif depuis PG 18 pour les requêtes de graphe, hébergement gratuit durable chez **Neon** ; Render free expire à 30 jours). **SQLite reste la base du concours** (démo hors-ligne, zéro ops ; le `store.py` unique point d'accès garde la migration contenue). **Kuzu est à écarter** (projet archivé le 10/10/2025, équipe acquise par Apple ; forks communautaires non matures). Neo4j AuraDB Free = 200 k nœuds / 400 k relations, inutile à notre échelle + 2ᵉ base à synchroniser. DuckDB reste le compagnon analytique ; RDF/PROV-O = alignement d'export, pas stockage. Voir §2.
3. **Catalogue de relations** — proposé en §3 : **34 types répartis en 4 familles actées** (preuve & dérivation ×8 · structure & exposition ×15 · mécanisme économique ×3 · contrainte & permission ×8), chacun avec sujet→objet autorisés, sens, transitivité et une sémantique d'une ligne. Décompte d'origine : **14 repris de MIMIR/RC, 13 du domaine DeFi/on-chain (définis par ce document), 7 rendus explicites par nécessité** (§3.3). Record de relation ORVYREN à 17 champs (§3.0) enrichi du record MIMIR à 10 champs. **Aucun catalogue public réutilisable de relations DeFi n'a été trouvé** — c'est notre pièce à produire.
4. **Pipeline de construction** — trois voies : **règles** (marché structuré), **lecture on-chain = PIT par bloc** (état + événements `AssignRoles`, gel, caps), **extraction documentaire LLM avec portes de validation** (GLiNER/REBEL/LangExtract existent et sont matures 2024-2026). Résolution d'entités : **déterministe d'abord** (adresses `chaîne:adresse` = identifiants canoniques), sémantique ensuite, jamais l'inverse. Un extrait ne devient un fait « porteur » que via la porte de validation (§4.5) ; snapshots hashés par décision (déjà dans le code). Voir §4.
5. **DL/ML** — état des lieux réel : GraphRAG (Microsoft) est **en maintenance depuis 2025** ; l'écosystème continue (LightRAG, HippoRAG 2, LazyGraphRAG) ; GNN/link-prediction = recherche (précédent DeFi : DeFiGuard 2024) ; KGC classique (RotatE…). **Pour v1 : rien d'appris dans le chemin de décision** ; au plus une recherche sémantique `pgvector` en outil de documentation. Expérimental post-concours sous protocole (HYP-07R) : GNN/embeddings de liens manquants, anomalies — toujours étiquetés `MODEL-INFERRED` et **jamais** des faits. Écartés : tout modèle qui casse la reconstruibilité. Voir §5.
6. **Requêtes** — 14 requêtes nécessaires identifiées (expositions, chemins de dépendance, contradictions, PIT, provenance, permissions, fraîcheur, invariants inter-chaînes…) avec les index et structures associés (§6). Règles d'inférence : clôtures autorisées (PART_OF, IS_A), `DEPENDS_ON` borné à décroissance ; **SUPPORTS n'autorise aucune propagation** (invariant) ; corrélation ≠ chaînable.

---

## 1. (a) MODÉLISATION TEMPORELLE & PIT

### 1.1 Ce que dit MIMIR (la source directe)

**[FAIT SOURCÉ — MIMIR §10.5, §10.3, §7.4–7.5, REQ-KNOW-008]**

- **Six horloges** : `event_time` (quand le fait s'est produit), `publication_time` (quand il a été publié), `observation_time` (quand le système l'a vu), `effective_time`, `validity_time`, `revision_time` — portées par les objets qui les définissent. T0 n'en active que trois (event/publication/observation) ; les trois autres sont pour le tier FULL.
- **Chaîne de provenance** explicite : `Source → Observation → Extraction → Claim → Relation → Hypothesis → Prediction → Outcome`, chaque flèche = une ligne, jamais du texte libre.
- **Trois modes d'admission d'une donnée** : *PIT-native* (vintages reconstructibles), *reconstructible* (métadonnées de publication/version horodatées assez précises), *non-PIT* (usage descriptif seulement). Une donnée PIT-sensible sans horodatage d'accessibilité admissible est **inutilisable**.
- **Audit PIT** par run ; une violation = porte G1 : résultats invalides, y compris rétroactivement.

### 1.2 Les patterns existants (état de l'art réel)

**[FAIT SOURCÉ]** Le modèle canonique est **bitemporel** : *valid time* (le fait est vrai dans le monde) + *transaction time* (le système l'a enregistré). Origine Snodgrass ; codifié en SQL:2011 (« Temporal features in SQL:2011 », SIGMOD Record, déc. 2012 — https://sigmod.org/publications/sigmodRecord/1209/pdfs/07.industry.kulkarni.pdf). Martin Fowler donne l'intuition opérationnelle (07/04/2021, https://martinfowler.com/articles/bitemporal-history.html, consulté 15/10/2026) : deux dimensions — *actual history* (« ce que l'histoire serait avec une transmission parfaite de l'information ») vs *record history* (« comment notre connaissance de l'histoire change »). Son exemple (augmentation rétroactive d'un salaire) est exactement notre cas : le 18/04/2026, un exploit KelpDAO survenu à 17:35 UTC n'a été **connu** du système qu'à la lecture suivante ; une correction publiée plus tard ne doit **pas** modifier une décision passée.

Implémentations réelles examinées le 15/10/2026 :

| Pattern | Mécanisme | Forces | Limites | Référence (accès 15/10/2026) |
|---|---|---|---|---|
| **System-versioned (SQL Server)** | table courante + table d'historique gérée par le moteur ; requêtes `AS OF` / `BETWEEN` | zéro effort applicatif ; « point-in-time analysis » directe | lié au moteur ; le *valid time* du monde reste à porter à la main | learn.microsoft.com/…/tables/temporal-tables |
| **Temporal tables PostgreSQL 19 (beta4)** | *application time* natif : colonnes `daterange`, `PRIMARY KEY (…, WITHOUT OVERLAPS)`, FK temporelles `PERIOD` | intégrité temporelle **contrainte par le moteur** (pas de chevauchement) | **system time non supporté** (« could be emulated using triggers ») ; version en **beta** au 15/10/2026 (docs 19 beta3/beta4, publiées ~13/08/2026) | postgresql.org/docs/19/ddl-temporal-tables.html |
| **AS OF « maison » PostgreSQL** | tables + trigger `version_trigger` + `tstzrange` (bornes `[)`), filtre `current_timestamp <@ valid` | fonctionne sur PG stables (13+) ; contrôle total | à écrire soi-même ; discipline de requête requise | cybertec-postgresql.com/en/implementing-as-of-queries-in-postgresql/ |
| **Feature store (PIT join)** | jointure « as-of » à l'instant T : ne joindre que les valeurs horodatées ≤ T, par entité | le standard ML pour éviter la fuite du futur | orienté features, pas provenance ; à reproduire | Azure ML « point-in-time join » ; Databricks « Point-in-time feature joins » (docs, consultées 15/10/2026) |
| **Append-only + révisions** (notre code v0) | chaque révision = nouvelle ligne ; lecture = dernière révision ; `sqflite` triggers interdisent UPDATE/DELETE | reconstruibilité totale ; réutilise le v0 ; pas de migration | requêtes « as-of » à écrire (filtre `inserted_at ≤ T`) ; pas de contrainte de non-chevauchement | `src/orvyren/graph/store.py` [MESURÉ, code] |
| **XTDB** | base SQL **immuable, bitemporelle native** (docs.xtdb.com) | bitemporel sans effort, time-travel | écosystème jeune, service à opérer ; hors trajectoire pour un concours | xtdb.com / docs.xtdb.com |
| **Graphiti (Zep)** | graphe temporel par épisodes : les faits sont **invalidés, jamais supprimés** ; « temporal knowledge graph for agents » | exactement notre philosophie (mémoire = graphe) | orienté mémoire d'agents/conversations, pas données financières | github.com/getzep/graphiti ; papier Zep arXiv:2501.13956 (2025) |

**[FAIT SOURCÉ]** La littérature confirme ce besoin au-delà de nous : les articles 2025-2026 sur les « bitemporal knowledge graphs » et les surveys de graphes de connaissances temporels (ex. MDPI *Mathematics* 11(23):4852, 2023, https://www.mdpi.com/2227-7390/11/23/4852) traitent la même question (invalidité ≠ suppression, provenance first-class).

### 1.3 Recommandation ORVYREN : trois horloges minimales + validité + révision

**[PROPOSITION]** Adopter le mapping suivant (compatible avec le code actuel, extensible) :

| Horloge MIMIR | Champ ORVYREN proposé | Portée | Statut |
|---|---|---|---|
| event_time | `ts_event` | Observations (existant [MESURÉ]) | **en v1** |
| publication_time | `ts_published` | Documents, communiqués, événements publics (FOMC-like) | **en v1** |
| observation_time | `retrieved_at` | Toutes les observations (existant [MESURÉ]) | **en v1** |
| valid_time (monde) | `valid_from` / `valid_to` | Relations du monde (familles 2 et 4) : « détenu du … au … », « gelé à partir du bloc … » | **en v1** (nullable = ouvert/inconnu) |
| effective_time | (fusionné avec `valid_from` tant que non nécessaire) | différé | FULL |
| revision_time | `inserted_at` + `revision` + `superseded_by` | Le store append-only l'a déjà [MESURÉ] | **en v1** |

**Deux modes de requête à distinguer formellement** (documenté, testé) :

1. **« Le monde à T »** — faits dont l'intervalle de validité contient T (`valid_from ≤ T < valid_to`). Sert à reconstituer l'état réel (exposition au 18/04/2026 17:35).
2. **« Ce qui était connu à T »** — faits dont la révision a été insérée à `inserted_at ≤ T`. Sert à la décision rejouée (PIT).
3. **La décision PIT** utilise l'**intersection** (état du monde tel que connaissable) — invariant INV-PIT de la REVUE CROISÉE [FAIT SOURCÉ interne, §2.4] : « modifier le futur, ou une révision publiée après `as_of`, ne change pas une décision passée ».

**Requête as-of type** (schéma, transposable SQLite/Postgres) :

```sql
-- « état connu à T » sur les relations : validité monde ∩ connaissance
SELECT r.* FROM relations r
JOIN (SELECT relation_id, MAX(revision) AS rev
      FROM relations WHERE inserted_at <= :T GROUP BY relation_id) c
  ON r.relation_id = c.relation_id AND r.revision = c.rev
WHERE r.valid_from <= :T AND (r.valid_to IS NULL OR r.valid_to > :T);
```

**Pour l'on-chain, l'horloge PIT est le bloc** : un `eth_call` sur bloc d'archive rejoue l'état exact ; tout fait on-chain stocke `chain_id`, `block`, `tx_hash` [MESURÉ — W2B : lecture archive `eth.drpc.org` jusqu'au bloc 14 720 000 ≈ mai 2022]. Le bloc est monotone dans le temps → PIT parfait par construction ; noter le **temps de bloc propre à chaque chaîne** (W2B chantier n°2) et prévoir une **politique de reorg** [PROPOSITION, question ouverte QO-1].

**Limites assumées** (à écrire noir sur blanc) :
- **Correction rétroactive** : gérée par SUPERSEDES + révision (la décision passée ne se recalcule pas — on la rejoue avec les données d'époque) ; c'est la logique Fowler.
- **Chevauchement d'intervalles** : non contraint par SQLite ; en PG 19+ `WITHOUT OVERLAPS` le fait nativement ; en attendant, contrainte applicative + test unitaire [PROPOSITION].
- **Performance** : les sous-requêtes de révision coûtent cher si mal indexées → index sur `(relation_id, inserted_at)` et vue matérialisée « état courant » (SQLite : vue simple ; PG : vue matérialisée rafraîchie par lot) [PROPOSITION].
- **Doubles horloges des documents** : `ts_published` est souvent estimée (heure d'un post, d'un communiqué) — marquée `ESTIMATED` quand elle n'est pas exacte, jamais silencieusement ronde [PROPOSITION, cohérent avec MIMIR §7.4].
- **[NON TROUVÉ]** : aucun pattern publié spécifique « bitemporel pour graphe de collatéral on-chain » n'a été trouvé — la combinaison six-horloges × PIT-par-bloc × append-only semble native de notre projet (et de MIMIR pour la partie générale).

---

## 2. (b) STOCKAGE — MATRICE ET RECOMMANDATION

### 2.1 Le besoin exact (gelé pour l'évaluation)

**[FAIT SOURCÉ — interne]** Append-only + provenance recalculable (promesse produit) · PIT/bitemporel (§1) · requêtes de chemins (expositions, dépendances) · embeddings/recherche sémantique (optionnels v1) · 16 tables v1 prévues (`ARCHITECTURE_V1.md` §4) · **coût zéro** (sources et hébergement gratuits — contrainte concours) · fonctionne en démo hors-ligne (`--replay` obligatoire) · un seul développeur, « boring technology » (MIMIR C4) · sauvegarde/export simple (dossier de preuve) · Python.

### 2.2 Matrice comparative (accès 15/10/2026)

| Critère | **SQLite** (actuel) | **PostgreSQL 18/19 + extensions** | **Kuzu** (embarquée) | **LadybugDB** (fork Kuzu) | **Neo4j AuraDB Free** | **RDF (Oxigraph/Jena)** | **DuckDB + Parquet** | **XTDB** |
|---|---|---|---|---|---|---|---|---|
| Append-only / provenance | ✅ (code v0 [MESURÉ]) | ✅ (mêmes patterns + triggers) | ⚠️ (pas de discipline append-only native) | idem | ⚠️ (transactions, pas d'historique de fait) | ✅ (quads immuables) | ✅ (fichiers immuables) | ✅ (immuable par conception) |
| PIT / bitemporel | ⚠️ à la main (revues) mais complet | ⚠️ à la main ; **app-time natif en PG19 beta** (`WITH OVERLAPS`) ; system-time via triggers/extensions | ⚠️ à la main | ⚠️ | ⚠️ (pas natif) | ⚠️ à la main (reification) | ⚠️ (ASOF JOIN pour les jointures PIT) | ✅ **natif** |
| Requêtes de graphe | ✅ recursive CTE (natif SQLite) | ✅ recursive CTE + **SQL/PGQ natif (PG 18+, standard SQL:2023)** | ✅ Cypher, moteurs colonnes, très rapide | ✅ (même moteur) | ✅✅ Cypher + GDS (algos) | ⚠️ SPARQL (clôtures OK, moins direct) | ✅ **DuckPGQ** (extension SQL/PGQ, VLDB 2023) | ⚠️ SQL (pas de langage graphe) |
| Embeddings | ❌ (extension non standard) | ✅ **pgvector v0.8.6** (HNSW/IVFFlat, fourni par de nombreux hébergeurs) | ✅ vector index intégré | ✅ | ⚠️ vecteur en feature tier payant | ⚠️ | ⚠️ (VSS expérimental) | ⚠️ |
| Hébergement gratuit | = fichier (zéro) | **Neon free : permanent, 1 Go/projet + 20 Go/compte, 100 CU-h** ; ⚠️ Render free PG **expire à 30 j** | = fichier | = fichier | AuraDB Free : 1 base, **200 k nœuds / 400 k relations**, 1 export ponctuel | = fichier (Oxigraph embarqué) | = fichier | à héberger (service) |
| Ops / simplicité | ✅✅ zéro | 🟡 serveur géré (Neon : zéro ops) | ✅ zéro | ✅ zéro | 🟡 SaaS + 2ᵉ base à synchroniser | 🟡 | ✅ zéro | 🔴 service jeune |
| Sauvegarde / export | ✅ fichier + hash snapshot [MESURÉ] | ✅ dump standard | ✅ fichier | ✅ | ⚠️ 1 snapshot ponctuel | ✅ | ✅ fichiers | 🟡 |
| Maturité 2026 | ✅✅ | ✅✅ | 🔴 **archivé 10/10/2025** (Apple) — installations existantes fonctionnent, plus de support amont | 🟡 fork communautaire actif (arun Sharma ; « DuckDB for Graphs ») | ✅ (éditeur commercial) | ✅ (W3C) | ✅ | 🟡 |
| Alignement projet | ✅ tests + démo | ✅ cible déjà actée (AV1 §5) | ❌ | 🟡 trop jeune | 🟡 | ✅ (PROV-O, RC §2.3) | ✅ (choix MIMIR ADR-002) | ❌ |

Sources de la matrice : [FAIT SOURCÉ] Kuzu archivé (README github.com/kuzudb/kuzu + The Register 14/10/2025 https://theregister.com/software/2025/10/14/kuzudb-graph-database-abandoned-community-mulls-options/1142229 + BetaKit acquisition Apple https://betakit.com/apple-strikes-deal-to-acquire-canadian-database-software-startup-kuzu/ ; forks : gdotv.com « Kuzu's Legacy… » mai 2026, Vela-Engineering/kuzu, ladybugdb.com) ; Neo4j AuraDB Free (neo4j.com/cloud/aura/faq) ; Neon (neon.com/pricing) ; Render (changelog 20/05/2024 https://render.com/changelog/free-postgresql-instances-now-expire-after-30-days-previously-90) ; pgvector (github.com/pgvector/pgvector, v0.8.6) ; SQL/PGQ (EDB 18/02/2025 ; docs PG19 §5.15/§7.9) ; DuckPGQ (vldb.org/pvldb/vol16/p4034-wolde.pdf) ; XTDB (xtdb.com). Tous consultés le 15/10/2026.

### 2.3 Recommandation argumentée [PROPOSITION]

1. **Cible = PostgreSQL** (déjà acté AV1 §5) : SQL/PGQ natif depuis PG 18 (les requêtes de chemins du §6 deviennent du SQL standard, sans 2ᵉ base), `pgvector` pour la recherche sémantique (§5), temporalité *application time* natif dès PG 19 GA, écosystème maximal, **Neon free permanent** (= l'hébergement du plan AV1, sans la limite des 30 jours de Render).
2. **Concours = SQLite** : le code v0 marche, la démo est hors-ligne obligatoire, SQLite a `WITH RECURSIVE` (les requêtes de chemins passent dès aujourd'hui) et les triggers append-only [MESURÉ]. **Pas de migration avant le 20/10** (avis A2 déjà consigné). Le `store.py` « seul point d'accès base » rend la bascule mécanique ; prévoir un test d'équivalence de schéma [PROPOSITION].
3. **Neo4j : non** — 200 k/400 k suffirait, mais ajoute une 2ᵉ base à synchroniser, un PIT à la main, et zéro bénéfice à notre échelle (< quelques milliers de nœuds en v1) ; les algos GDS sont du confort post-concours.
4. **Kuzu : écarté** (projet archivé, site mort, support nul). Si l'embarqué graphe redevient un besoin, évaluer **LadybugDB** (fork actif, « DuckDB for Graphs ») — mais hors trajectoire concours.
5. **DuckDB + Parquet : compagnon analytique** (suggestions MIMIR ADR-002) — rejouer des mesures lourdes offline (séries, walk-forward), pas le store de faits.
6. **RDF/PROV-O : export, pas stockage** — la RC §2.3 cite PROV-O comme « appui sémantique sans obligation d'importer RDF » : on garde les **noms** de PROV (W3C Rec. 30/04/2013, https://www.w3.org/TR/prov-o/) dans la famille « preuve et dérivation », et un export JSON-LD est un nice-to-have post-concours.
7. **XTDB : écarté** (jeune, service à opérer) mais **cité** comme existence de référence : bitemporel natif, c'est la preuve que notre besoin est standard.

**Coût de changement** : migration SQLite→Postgres ≈ 1 table `store.py` + DDL (le schéma v1 est le même) ; le vrai coût est le temps de test. À planifier post-concours, avec Neon free comme cible de démo publique [PROPOSITION].

---

## 3. (c) CATALOGUE DE RELATIONS PROPOSÉ — LA PIÈCE DEMANDÉE

### 3.0 Cadre : trois couches, quatre familles, un record

**[FAIT SOURCÉ — MIMIR §10.1/§11.2 + RC §2.3 + code]**
- **Couche monde** (faits sur le monde) : `Entité`, `Événement`, `Relation structurelle/économique`.
- **Couche connaissance** (faits sur nos connaissances) : `Source`, `Observation`, `Extraction`, `Claim`, `Hypothèse`, `Prédiction`, `Issue`. C'est la chaîne MIMIR §10.5.
- **Couche décision** : `Décision`, `Intent`, `Exécution`, `Dossier` (AV1 §4).

**Types de nœuds** (nécessaires pour définir sujet/objet) [PROPOSITION, en cohérence avec V0.2 §6.4 et WC] :

| Classe | Types | Identifiant canonique |
|---|---|---|
| Organisation | émetteur, DAO, société, dépositaire, régulateur | registre interne + entité canonique immuable (REQ-KNOW-005) |
| Actif | stablecoin, LST, token de prêt, LP, part | `chaîne:adresse` (+ symbole alias) |
| Contrat | marché (réserve Aave), pool, pont/OApp, oracle, module, Safe | `chaîne:adresse` |
| Adresse | trésorerie, EOA, multisig | `chaîne:adresse` |
| Chaîne | Ethereum, L2s | `chain_id` (CAIP-2) |
| Unité/référence | USD, ETH, indice | enum |
| Preuve | Source, Observation, Claim, Document, ExtractionRun | empreinte de contenu (code v0 [MESURÉ]) |
| Décision | Hypothèse, Branche, Décision, Intent, Exécution, Outcome | ULID |
| Gouvernance | Rôle, Permission, Timelock | `contrat:role_key` |

**Record de relation ORVYREN (17 champs)** — adapté du record à 10 champs de MIMIR §11.2, enrichi des contraintes internes [PROPOSITION] :

| # | Champ | Rôle | Origine |
|---|---|---|---|
| 1 | `relation_id` | ULID stable | AV1 §4 |
| 2 | `family` | enum 4 familles | RC §2.3 |
| 3 | `kind` | type du catalogue (§3.2) | ce document |
| 4 | `src`, `dst` (+ `src_kind`, `dst_kind`) | références typées | MIMIR (`cause`/`effect` généralisés) |
| 5 | `mechanism` | label court (LIQUIDITY, REDEMPTION, FUNDING, PEG, ORACLE, CUSTODY, GOVERNANCE…) | MIMIR §11.2 |
| 6 | `sign_prior` | + / − / ambigu | MIMIR §11.2 |
| 7 | `conditions`, `regime_scope`, `horizon_scope` | prédicats d'activation, portée | MIMIR §11.2 |
| 8 | `epistemic_status` | FACT / REPORTED / STATISTICAL / CAUSAL-DOCUMENTED / CAUSAL-HYPOTHESIS / MODEL-INFERRED / REJECTED | MIMIR §0.3 |
| 9 | `lifecycle` | DISCOVERED → EVALUATING → ACTIVE → WEAKENING → SUSPENDED → REJECTED | MIMIR §11.2 |
| 10 | `validation_status` | PENDING / VALIDATED / QUARANTINED / REJECTED | RC (attribut séparé) |
| 11 | `valid_from`, `valid_to` | temps de validité monde (nullable) | §1 (bitemporel) |
| 12 | `revision`, `inserted_at`, `superseded_by` | temps système | code v0 [MESURÉ] |
| 13 | `provenance_refs[]` + `source_family_id` | claims/observations parents + famille de source (INV-DEPENDENCE) | MIMIR §10.5 + RC §2.4 |
| 14 | `extract_method` + `model_version` + `run_id` | RULE / ONCHAIN_READ / LLM_EXTRACT / HUMAN, avec version | RC §2.3 + ce doc |
| 15 | `chain_ref` | (chain_id, block, tx_hash) pour les faits on-chain | W2C/W2B [MESURÉ] |
| 16 | `confidence` | 0–1, méthode documentée (fiabilité source × fraîcheur × indépendance) | W2B §7.7 (MIMIR) + code `quality/` |
| 17 | `payload` | champs propres à la famille (montant, rôle, périmètre, passage source…) | RC §2.3 « champs propres » |

**Trois attributs à ne jamais confondre** (RC §2.3, repris tel quel) : `epistemic_status` (ce qu'on croit savoir), `lifecycle` (où en est la relation dans son cycle), `validation_status` (a-t-elle passé la porte de validation). Une relation ACTIVE peut rester hypothétique.

### 3.1 Les 4 familles — règles d'or

| Famille | Rôle | Interdits structurants |
|---|---|---|
| **1. Preuve et dérivation** | Relier sources, observations, claims, hypothèses — la couche « comment on sait » | **`SUPPORTS` n'autorise AUCUNE propagation causale** (invariant acté) ; une corrélation n'est jamais un mécanisme |
| **2. Structure et exposition** | Qui détient/émet/doit quoi, où, sur quelle chaîne | « absence de publication » ≠ « exposition nulle » ; une quantité sans unité/date est invalide |
| **3. Mécanisme économique** | Comment une variation se transmet (avec statut épistémique) | une relation statistique ne porte que le statut STATISTICAL ; conditions et horizon obligatoires |
| **4. Contrainte et permission** | Qui peut quoi, qui garde quoi (on-chain inclus) | texte informatif ≠ règle exécutable validée ; toujours porter la preuve d'octroi (event/ref) |

### 3.2 Catalogue complet [PROPOSITION — à valider en revue]

Légende origine : **M**=MIMIR/RC (repris) · **D**=DeFi/on-chain (ce document) · **N**=nouveau (nécessaire, exposé ici) · Transitivité : N=non, T=transitive, Q=quasi-transitive bornée.

#### Famille 1 — Preuve et dérivation (8)

| # | Kind | Sujet → Objet autorisés | Sens | Trans. | Sémantique | Origine |
|---|---|---|---|---|---|---|
| 1.1 | `OBSERVED_FROM` | Observation → Source | dirigé | N | La mesure provient de cette source (endpoint, horodatage de récupération, limites). | M (chaîne MIMIR §10.5) |
| 1.2 | `EXTRACTED_FROM` | Claim/Relation → Document/Observation | dirigé | N | L'élément a été extrait de ce document/passage (offsets + run d'extraction versionné). | M (§10.5, Extraction) |
| 1.3 | `DERIVED_FROM` | Claim/Relation → Observation/Claim | dirigé | N (DAG) | Fait calculé à partir de parents, via une recette versionnée. | M (RC DERIVED_FROM) |
| 1.4 | `SUPPORTS` | Claim → Hypothesis | dirigé | N | Ce constat soutient cette hypothèse — sans aucune transmission économique. | M (RC ; code `supports`) |
| 1.5 | `REFUTES` | Claim → Hypothesis | dirigé | N | Ce constat réfute cette hypothèse selon un critère pré-déclaré. | M (falsification) / N (kind explicite) |
| 1.6 | `CONTRADICTS` | Claim ↔ Claim | symétrique | N | Deux constats incompatibles coexistent (jamais fusionnés) — signal de recherche. | M (§REQ-KNOW-003) / N (kind explicite) |
| 1.7 | `SUPERSEDES` | toute entité → même type (révision précédente) | dirigé | T (chaîne) | La révision remplace l'ancienne sans l'effacer (reconstruibilité). | M (§13.4) / code (révisions) |
| 1.8 | `SAME_AS` | Entité → Entité | symétrique | N | Alias résolu : deux références = une identité canonique (décision datée, révisable). | M (§10.4) / N (kind explicite) |

#### Famille 2 — Structure et exposition (15)

| # | Kind | Sujet → Objet autorisés | Sens | Trans. | Sémantique | Origine |
|---|---|---|---|---|---|---|
| 2.1 | `IS_A` | Entité/Actif → Classe | dirigé | T | Taxonomie (USDC IS_A stablecoin ; rsETH IS_A LST) — sert les requêtes par classe. | N |
| 2.2 | `PART_OF` | Entité/Contrat → Entité | dirigé | T | Appartenance structurelle (aEthUSDC PART_OF Aave V3 ; réserve PART_OF pool). | N |
| 2.3 | `DEPLOYED_ON` | Contrat/Token → Chaîne | dirigé | N | Présence d'un contrat/émission sur cette chaîne (multi-chaînes explicite). | D |
| 2.4 | `ISSUED_BY` | Token → Organisation | dirigé | N | L'actif est émis par cette entité. | M (RC) |
| 2.5 | `TARGETS_PEG` | Token → Unité/Actif de référence | dirigé | N | Parité visée (1 USD, 1 ETH) — une cible, pas une garantie. | D |
| 2.6 | `REDEEMABLE_VIA` | Token → Facilité/Contrat | dirigé | N | Redemption/time-lock auprès de cette facilité (délais, conditions en payload). | M (RC) |
| 2.7 | `CUSTODIED_AT` | Actif → Dépositaire/Contrat | dirigé | N | L'actif repose chez ce dépositaire (wrapping, PSM, escrow). | M (RC) |
| 2.8 | `HOLDS` | Adresse/Entité → Actif | dirigé | N | Détient N unités à (chaîne, bloc) ; rôle : trésorerie / liquidité / collatéral / custody. | M (RC) |
| 2.9 | `OWES` | Position/Entité → Dette | dirigé | N | Doit N unités sur ce marché (exposition au passif, taux, échéance). | M (RC) |
| 2.10 | `DEPOSITED_IN` | Actif (quantité) → Marché/Pool | dirigé | N | Dépôt dans un marché/protocole (réserve Aave, pool Curve) — chemin d'exposition. | D |
| 2.11 | `COLLATERALIZES` | Actif (quantité) → Dette/Marché | dirigé | N | Sert de collatéral à cette dette sur ce marché (paramètres LTV/LT en payload). | D |
| 2.12 | `REHYPOTHECATED_TO` | Actif → Protocole | dirigé | N | L'actif reçu est réengagé/ré-hypothéqué vers ce protocole (chaîne des droits). | D |
| 2.13 | `BRIDGED_VIA` | Token (supply d'une chaîne) → Pont/OApp | dirigé | N | L'émission sur cette chaîne dépend de ce pont (mint/burn, invariant inter-chaînes). | D |
| 2.14 | `VERIFIED_BY` | Pont/OApp → Configuration vérificateurs | dirigé | N | La sécurité du pont repose sur ces vérificateurs (nombre, type de DVN). | D (cas KelpDAO) |
| 2.15 | `PRICED_BY` | Marché/Actif → Feed oracle | dirigé | N | Valorisation adossée à ce feed (type, `description()`, heartbeat, plafond). | D (W2B 1.3/4.1) |

#### Famille 3 — Mécanisme économique (3)

| # | Kind | Sujet → Objet autorisés | Sens | Trans. | Sémantique | Origine |
|---|---|---|---|---|---|---|
| 3.1 | `AFFECTS` | Cause → Effet (variables, acteurs, instruments) | dirigé | Q (via moteur de propagation borné, jamais clôture nue) | Le mécanisme M transmet une variation de Cause vers Effet (signe, horizon, conditions, statut épistémique). | M (§11.2 ; RC) |
| 3.2 | `DEPENDS_ON` | X → Y | dirigé | Q (décroissance par saut, profondeur bornée) | X dépend économiquement de Y (canal + sensibilité en payload). | M (§6.3 conditionnel) / N (kind explicite) |
| 3.3 | `CORRELATES_WITH` | X ↔ Y | symétrique | N | Lien statistique constaté — statut STATISTICAL obligatoire, jamais causal, jamais chaîné. | M (§0.3 labels) / N (kind explicite) |

#### Famille 4 — Contrainte et permission (8)

| # | Kind | Sujet → Objet autorisés | Sens | Trans. | Sémantique | Origine |
|---|---|---|---|---|---|---|
| 4.1 | `CONSTRAINS` | Paramètre/Règle/Institution → Marché/Actif/Action | dirigé | N | Limite le comportement (supplyCap, LTV=0, gel, timelock) — état ou paramètre daté. | M (RC) |
| 4.2 | `AUTHORIZES` | Autorité → Sujet | dirigé | N | Accorde un droit à ce sujet (périmètre, instruments, dates, preuve d'octroi). | M (RC) |
| 4.3 | `REVOKES` | Autorité → Droit/Sujet | dirigé | N | Révoque un droit (événement daté : tx on-chain ou décision). | M (RC) |
| 4.4 | `MEMBER_OF` | Adresse/EOA → Rôle | dirigé | N | Est membre de ce rôle à (chaîne, bloc) — fait on-chain `AssignRoles`. | D (Zodiac ; W2C) |
| 4.5 | `ALLOWS` | Rôle → Cible/Fonction | dirigé | N | Le rôle autorise cette cible/fonction (allowlist, allowances période). | D (Zodiac) |
| 4.6 | `ADMINISTERED_BY` | Contrat/Module → Safe/Multisig | dirigé | N (requête « chemin de contrôle » en clôture dédiée) | L'admin/propriétaire du contrat est cette adresse (`owner()`, module enabled). | D |
| 4.7 | `GOVERNED_BY` | Protocole/Contrat → DAO/Timelock | dirigé | N | Les paramètres sont gouvernés par cette instance (seuils, délais). | D |
| 4.8 | `REGULATED_BY` | Entité/Actif → Régime/Licence | dirigé | N | Encadrement réglementaire (phase banques, hors démo — table conservée pour la vision). | D (optionnel) |

**Total : 34 types.**

### 3.3 Origine et nouveauté — décompte honnête

- **Repris de MIMIR/RC tels quels ou généralisés (14)** : OBSERVED_FROM, EXTRACTED_FROM, DERIVED_FROM, SUPPORTS, SUPERSEDES, ISSUED_BY, REDEEMABLE_VIA, CUSTODIED_AT, HOLDS, OWES, AFFECTS, CONSTRAINS, AUTHORIZES, REVOKES.
- **Du domaine DeFi/on-chain, définis par ce document (13)** : DEPLOYED_ON, TARGETS_PEG, DEPOSITED_IN, COLLATERALIZES, REHYPOTHECATED_TO, BRIDGED_VIA, VERIFIED_BY, PRICED_BY, MEMBER_OF, ALLOWS, ADMINISTERED_BY, GOVERNED_BY, REGULATED_BY.
- **Rendus explicites par nécessité (7)** — pour que les invariants soient vérifiables par une machine (types sujet/objet + règles de chaînage) et non par la mémoire des auteurs : `SAME_AS`, `CONTRADICTS`, `REFUTES` (garde-fous d'invariants : jamais fusionner, jamais propager) · `DEPENDS_ON`, `CORRELATES_WITH` (séparer dépendance économique et constat statistique) · `IS_A`, `PART_OF` (taxonomie et composition, nécessaires aux requêtes par classe).
- **[NON TROUVÉ]** : aucun catalogue public complet de types de relation pour un graphe de collatéral DeFi n'a été trouvé (la littérature fournit des notations et schémas partiels — Nebula/Dialectic 2024 « graph-based representation of DeFi », DeFiGuard arXiv:2406.11157, compositions DeFi arXiv:2111.11933). Notre catalogue est donc **à produire et à assumer comme nôtre**.

### 3.4 Cas particuliers — état on-chain vs relation

**[PROPOSITION]** Certains « faits » du domaine sont des **états/paramètres** plus que des relations : `isFrozen` [MESURÉ W2B : bascule datée au bloc 24 908 723], `supplyCap` (99,999 % atteint), LTV, heartbeat oracle. Deux écritures possibles : (i) `Observation` (chaîne, bloc, valeur) — recommandé pour tout ce qui est **mesuré** ; (ii) `CONSTRAINS` paramètre→marché — pour ce qui **agit** (le gel contraint la réserve rsETH). Règle : *mesuré = Observation ; agit = relation ; les deux quand les deux* — avec un lien `DERIVED_FROM` du second vers le premier. Ça évite le double comptage et garde la valeur PIT (bloc).

---

## 4. (d) PIPELINE DE CONSTRUCTION DU GRAPHE

### 4.1 Par type de source — trois voies, une discipline

**Voie 1 — Données marché structurées → RÈGLES** [FAIT SOURCÉ interne — code `connectors/` + `quality/` + W2B]
Déjà en place : `(url, params) → PayloadBrut{source, url, retrieved_at, body}` → normalisation → `Observation{venue, metric, ts_event, value, unité, qualité, empreinte}`. Les claims dérivés (seuils, signaux) référencent des observations (un claim sans observation est refusé par le store [MESURÉ]). À ajouter [PROPOSITION] : recettes versionnées pour tout dérivé (`DERIVED_FROM` + `run_id`), unités explicites (mapping versionné — MIMIR REQ-DATA-005), et `source_family_id` (INV-DEPENDENCE).

**Voie 2 — Lecture on-chain → RÈGLES** [FAIT SOURCÉ — W2B/W2C]
- `eth_call` sur **bloc d'archive** (état PIT natif) : réserves Aave (`getReserveData`), oracles (`latestRoundData`, `description()`), supply multi-chaînes, `get_dy` Curve…
- `eth_getLogs` pour les **événements** : `AssignRoles`, `SetDefaultRole`, `RolesModSetup`, `ConsumeAllowance` (Zodiac — W2C §a.2), gels, mints/burns de ponts.
- Chaque fait on-chain = Observation ou relation avec `chain_ref` (bloc, tx) ; l'ordre est **total** (le bloc), le PIT est **exact**. Politique de reorg à figer (QO-1) [PROPOSITION].
- Les relations produites (MEMBER_OF, ALLOWS, VERIFIED_BY, CONSTRAINS…) sont mises à jour par **diff de blocs** : décoder, comparer à l'état stocké, écrire la transition (revocation = `REVOKES`/fin de validité `valid_to` = bloc de la révocation).

**Voie 3 — Documents/communiqués → EXTRACTION LLM + VALIDATION** [FAIT SOURCÉ outils 2024-2026]
Outils réels (état des lieux au 15/10/2026) :
- **GLiNER** (urchade/GLiNER, Apache-2.0, créé 11/2023, doc 0.2.24) : NER zero-shot + extraction conjointe entité-relation, léger, tourne sur CPU.
- **REBEL** (Babelscape, EMNLP 2021 Findings) : extraction de relations end-to-end (seq2seq), sortie triplets Wikidata-like — bonne **génération de candidats**, faible précision de domaine.
- **LangExtract** (google, v1.6.0 sur PyPI, 2025) : extraction structurée par LLM **avec ancrage aux passages source** (l'ancrage = la provenance).
- **LLM + JSON schema strict** (voie V0.2 §5.3) : schéma imposé, champs inconnus → **quarantaine**.
Pipeline proposé [PROPOSITION] : `document → sha256 → mentions (GLiNER) → résolution d'entités (§4.3) → triplets candidats + offsets → moteur de validation (§4.5) → relation (VALIDATED) ou quarantaine`. Chaque relation extraite porte `extract_method=LLM_EXTRACT`, `model_version`, `run_id`, passage exact.

### 4.2 Résolution d'entités & dédoublonnage [PROPOSITION, aligné MIMIR REQ-KNOW-004/005]

1. **Déterministe d'abord** : `chaîne:adresse` (checksum) = identifiant canonique des contrats/tokens/EOAs ; registre d'entités (émetteurs, DAO) avec identité canonique **immuable** ; alias (symboles, noms marketing, variantes) = **preuves** rattachées, jamais des clés (REQ-KNOW-005).
2. **Ensuite seulement** la désambiguïsation par règles floues/sémantique (ex. « USDC » vs « USD Coin » vs « USDC.e » — attention aux tokens *wrapped* : SAME_AS explicite, jamais implicite).
3. **Dédoublonnage des observations** : empreinte de contenu (déjà en place [MESURÉ]) ; les re-réceptions créent des révisions, pas des doublons.
4. **Dédoublonnage des relations** : clé `(src, kind, dst, valid_from, source_family_id)` — reformater la même source ne crée pas une preuve indépendante (INV-DEPENDENCE).
5. **Outils de marché** si besoin un jour : Splink (Fellegi-Sunter, open source, « deduplicating 7M records in two minutes », moj-analytical-services) et Zingg (ML dedup) — **post-concours**, en générateurs de candidats seulement [FAIT SOURCÉ + PROPOSITION].

### 4.3 Qualité, confiance, indépendance

[PROPOSITION, fondé MIMIR §7.7 + code `quality/`]
- Signaux : fraîcheur, complétude, cohérence, duplication, intégrité temporelle, fiabilité de source, validité de schéma — calculés par série et par run (le code a déjà `quality_report.json` [MESURÉ]).
- `confidence` d'une relation = f(fiabilité de la source, fraîcheur, indépendance) — règle fixe, documentée, versionnée ; la confiance **module** mais ne remplace jamais le statut épistémique.
- **INV-DEPENDENCE** : deux canaux issus de la même archive partagent `source_family_id` ; la fusion ne double-compte pas (préfigure la règle de fusion MIMIR §OPEN-09).

### 4.4 Quand un extrait devient un fait — la porte de validation [PROPOSITION]

Ordre d'évaluation (une porte qui échoue = quarantaine, jamais réparation silencieuse) :

| Porte | Contrôle | Rejet typique |
|---|---|---|
| G1 — Schéma | kind ∈ catalogue §3.2 ; types sujet/objet autorisés ; champs requis présents | triplets « à la REBEL » hors catalogue |
| G2 — Provenance | passage source + offsets ; observation/document parent résolu (échec = orphelin bloquant, INV-INTEGRITY) | citation non localisable |
| G3 — Autorité | hiérarchie : fait on-chain vérifié > document officiel (émetteur, régulateur, gouvernance) > presse de référence > communautaire | rumeur présentée comme fait structurel |
| G4 — Indépendance | une **seconde** source de famille DIFFÉRENTE pour tout fait porteur qui n'est pas on-chain (deux familles identiques ne comptent pas) | reprise d'AFP par 10 médias |
| G5 — Cohérence | contradiction avec un fait VALIDATED existant → écriture quand même mais avec `CONTRADICTS` + revue ; jamais d'écrasement | valeur divergente cachée |

**Règle de charge** : un fait « porteur » (qui peut déclencher une décision) exige : on-chain vérifié, **ou** G3=document officiel, **ou** deux familles indépendantes. Sinon il reste `PENDING/QUARANTINED` et ne peut servir que de contexte narratif. Le LLM ne produit jamais un chiffre décisionnel (règle actée) — les extractions LLM sont `MODEL-INFERRED` jusqu'à validation, et **exclues du chemin confirmatoire** (MIMIR D26/ADR-014).

### 4.5 Snapshots, révision, versionnage

Déjà en place [MESURÉ, code] : `snapshot()` = hash SHA-256 stable des lignes courantes + compteurs ; `GRAPH_VERSION` ; révisions append-only ; triggers qui refusent UPDATE/DELETE. À compléter [PROPOSITION] : (i) un snapshot figé **par décision** référencé dans le dossier d'audit (l'interface AV1 §3 le prévoit déjà : « une branche référence un snapshot, ne le copie pas ») ; (ii) un journal de mises à jour du graphe entre deux snapshots (delta par run) ; (iii) la politique de révision MIMIR §13.4 (L1–L2 automatiques, L3+ en decision record) transposée : nouvelles relations = L3 → proposition soumise à validation, pas auto-écriture.

---

## 5. (e) DL/ML SUR LE GRAPHE — ÉTAT DE L'ART ET DÉCISIONS

### 5.1 État des lieux réel (vérifié 15/10/2026)

| Famille | État | Faits datés |
|---|---|---|
| GraphRAG (Microsoft) | **Maintenance** | repo MIT 36 324 ★ ; README : « largely in maintenance mode, won't be accepting new PRs or implementing new features » (github.com/microsoft/graphrag). Papier fondateur « From Local to Global » arXiv:2404.16130 (avr. 2024). |
| GraphRAG variantes | Actives | LightRAG arXiv:2410.05779 (10/2024, v3 04/2025) ; HippoRAG 2 arXiv:2502.14802 (02/2025) ; LazyGraphRAG (Microsoft Research blog, 11/2024 — qualité/coût) ; surveys arXiv:2501.13958 / arXiv:2501.00309 (2025) ; variantes « extraction-free » émergentes (arXiv:2605.19735, 2026). |
| Embeddings de graphe | Classiques établis | node2vec arXiv:1607.00653 (2016) ; GraphSAGE arXiv:1706.02216 (NeurIPS 2017) — inductif, utilisable sur nœuds nouveaux. |
| GNN temporels | Recherche active | TGN arXiv:2006.10637 (2020) ; survey GNN finance arXiv:2111.15367. |
| GNN appliqués DeFi/blockchain | Précédents réels | DeFiGuard arXiv:2406.11157 (2024) : détection de manipulation de prix DeFi par GNN ; arXiv:2602.23599 (2026) : normalisation des GNN pour l'anomalie blockchain. |
| Complétion de KG (KGC) | Classiques établis | TransE/RotatE (arXiv:1902.10197, 2019) et suivants — évaluation standardisée. |
| Mémoire temporelle d'agents | Bitemporal appliqué | Graphiti (github.com/getzep/graphiti) + papier Zep arXiv:2501.13956 (2025) : faits invalidés, jamais supprimés. |
| Extraction (rappel §4) | Matures | GLiNER (zero-shot NER+RE, CPU) ; REBEL (EMNLP 2021) ; LangExtract (google, v1.6.0, 2025). |

### 5.2 Chaque option face à ORVYREN — tâche, maturité, coût, traçabilité

| Option | Tâche dans ORVYREN | Maturité | Coût | Traçabilité | Verdict proposé |
|---|---|---|---|---|---|
| **GraphRAG (MS/LightRAG/HippoRAG)** | Répondre sur le corpus documentaire (dossiers d'incidents, communiqués) pour l'agent de recherche | 🟡 moyenne (l'indexation coûte cher, la qualité dépend du corpus) | LLM par document indexé ; ré-indexation à chaque ajout | entités/communautés générées par LLM — provenance à reconstruire ; risque de fuite confirmatoire | **Écarté du produit v1** ; exploration post-concours pour la couche documents |
| **Embeddings sémantiques + pgvector** | Retrouver documents/claims/prototypes similaires ; aide à la résolution d'entités (candidats) | ✅ élevée (pgvector v0.8.6 ; sentence-transformers courants) | quasi nul en local/Neon free | retrieval = **liste de candidats**, la décision ne cite que des claims validés | **Optionnel v1** (si l'agent de recherche manipule des textes) ; sinon post |
| **Node embeddings (node2vec, GraphSAGE)** | Représenter entités pour similarité/regroupement ; candidats de liens | 🟡 recherche→ingénierie | CPU OK (graphe petit) | embeddings **non interprétables** ; utilisables seulement comme générateurs d'hypothèses | Post-concours (expérimental) |
| **GNN prédiction de liens (dont temporels/TGN)** | « Détecter une relation manquante avant qu'elle ne casse » : prédire COLLATERALIZES/PRICED_BY/BRIDGED_VIA non encore enregistrés ou rompus | 🔴 recherche appliquée (précédent DeFiGuard) | entraînement + étiquetage = jours ; risque de fuite temporelle élevé | sorties `MODEL-INFERRED` uniquement ; jamais un fait ; alimentent des **hypothèses** avec critères de réfutation | **Post-concours uniquement**, sous protocole §5.3 |
| **KGC (TransE/RotatE…)** | même tâche que GNN, autre famille de modèles | 🟡 | faible (petit graphe, CPU) | idem GNN | Post-concours (comparatif) |
| **Anomalies statistiques sur métriques de graphe** (sans DL) | Changement de degré/concentration, nouveau type d'arête, rupture de chemin — détecter une évolution anormale **du graphe lui-même** | ✅ simple, déterministe | nul | entièrement traçable (règle + seuil versionnés) | **En v1** si utile : c'est une règle, pas un modèle |
| **LLM extraction (GLiNER/REBEL/LangExtract)** | Peupler la couche documents (voie 3 §4.1) | ✅ outillage mature | faible volume en v1 | ancrage passages + run versionné + portes §4.4 | **v1 minimal** (quelques documents d'épisode), expansible ensuite |

### 5.3 Proposition de décision (à trancher en revue)

1. **v1 (concours) : rien d'appris dans le chemin de décision.** La valeur du projet ne vient pas du ML mais de la vérifiabilité ; introduire un modèle non validé affaiblit l'argument. Au plus : recherche sémantique d'appoint + extraction documentaire bornée (§5.2).
2. **Expérimental post-concours** (si et seulement si le graphe v1 tourne) : programme **HYP-07R** déjà pré-enregistré dans la REVUE (extension ML du graphe ; masquage par périodes/familles sans fuite ; métriques : précision@k **et** fraction d'inférences avec provenance complète ; budget égal à une règle simple). Candidats : GNN de prédiction de liens temporels, détection d'anomalies, KGC — comparés à des baselines triviales (voisins communs, règles).
3. **Écarté** : tout modèle dont la sortie ne peut pas être étiquetée `MODEL-INFERRED` avec provenance (fin de la reconstruibilité), et tout usage de ML pour produire un chiffre dans le dossier de décision. GraphRAG-comme-produit : écarté tant que la maintenance amont est en cause.

**Comment la traçabilité se préserve (règle transverse)** : un score de modèle n'entre dans le graphe que comme (i) observation dérivée avec `DERIVED_FROM` + `model_version` + recette, ou (ii) hypothèse `MODEL-INFERRED` avec critères de réfutation. Jamais comme relation `FACT`. C'est exactement le sens de la contrainte « aucune perte de reconstruibilité » du brief.

---

## 6. (f) REQUÊTES NÉCESSAIRES ET STRUCTURES

### 6.1 Les requêtes que la décision devra faire [PROPOSITION — dérivées de W2B/W2C + scénarios d'usage]

| # | Requête | Forme | Source du besoin |
|---|---|---|---|
| Q1 | **Exposition consolidée de la trésorerie** : tous les actifs détenus (as-of), directs + indirects, par protocole | clôture bornée HOLDS/DEPOSITED_IN/COLLATERALIZES | persona DAO ; 3.7 zone d'ombre |
| Q2 | **Chemins de dépendance** d'un actif A : qui en dépend, par quel canal, avec quel signe (profondeur ≤ k) | clôture bornée DEPENDS_ON/AFFECTS avec décroissance | rsETH/xUSD ; 2.6 |
| Q3 | **Contradictions ouvertes** : paires de claims incompatibles, non résolues | jointure CONTRADICTS + statut | REQ-KNOW-003 ; abstention |
| Q4 | **État PIT** : graphe tel que connu à T (monde ∩ connaissance) | as-of (§1.3) | INV-PIT ; replay |
| Q5 | **Chronologie d'un épisode** : événements/claims/relations entre T1 et T2, ordonnés (event_time et tx_time séparés) | range scan + tri | dossier de décision |
| Q6 | **Promenade de provenance** : décision → claims → observations → sources, avec hashes | jointure en chaîne (exists déjà `verify_chain` [MESURÉ]) | audit v1 ; promesse produit |
| Q7 | **Agrégats de concentration** : dette adossée à A, poids w_A, supply/cap, HHI | agrégation + arêtes OWES/COLLATERALIZES | signaux 3.1/4.2 W2B |
| Q8 | **État de permission** : qui est membre de quel rôle, quelles fonctions autorisées, as-of bloc B ; révocations | MEMBER_OF/ALLOWS/REVOKES + validité | W2C (Zodiac) |
| Q9 | **Fraîcheur** : observations ou oracles plus vieux que le heartbeat ; divergences inter-sources | scan temporel + seuils | I4/I9 W2B |
| Q10 | **Faits manquants discriminants** : quels types de relations/observations, absents, départageraient les hypothèses | « négation » par type + VoI | R1 ; 3.3 |
| Q11 | **Invariants inter-chaînes** : Σ supplies par chaîne ; mint/burn de pont appariés | agrégation multi-chaînes via BRIDGED_VIA/DEPLOYED_ON | I1/I2 W2B |
| Q12 | **Chaîne de contrôle** : contrat → admin → safe → DAO (ADMINISTERED_BY/GOVERNED_BY) | clôture bornée | attaques W2C ; timelock Drift |
| Q13 | **Révision/invalidation** : quels faits ont été superseded ou invalidés depuis T | SUPERSEDES + valid_to | cohérence PIT |
| Q14 | **Recherche sémantique** (option) : documents/claims proches d'une requête | pgvector ANN | agent de recherche |

### 6.2 Index et structures nécessaires [PROPOSITION]

**SQLite/PG (noyau, dès v1) :**
- `relations(src)`, `relations(dst)`, `relations(kind)`, `relations(src, kind)`, `relations(dst, kind)` — traversées ;
- `relations(relation_id, inserted_at)` — as-of ; `relations(valid_from, valid_to)` — monde à T ;
- `observations(ts_event)`, `observations(venue, metric, ts_event)`, `observations(retrieved_at)`, `observations(chain_id, block)` ;
- `claims(refs)` — index GIN (PG) / table d'association (SQLite) ;
- unicité partielle `(src, kind, dst, valid_from, source_family_id)` sur la révision courante — dédoublonnage ;
- **index partiels** sur `lifecycle='ACTIVE' AND validation_status='VALIDATED'` — la vue opérationnelle (petite) se parcourt vite.
- **Vue « état courant »** (`MAX(revision) GROUP BY relation_id`) matérialisée par lot ; **clôtures matérialisées** pour `PART_OF`/`IS_A`/chaîne de contrôle si elles chauffent.

**Postgres cible :** `GRAPH_TABLE`/SQL/PGQ (PG 18+) pour exprimer Q1/Q2/Q12 en motifs de chemin natifs ; `pgvector` (HNSW) pour Q14 ; éventuellement `ltree` pour les hiérarchies pures (pas nécessaire au vu du catalogue). **SQLite démo :** `WITH RECURSIVE` + garde-fous (profondeur ≤ 5, détection de cycle) — testé comme tel [PROPOSITION, à valider par un test].

### 6.3 Règles d'inférence autorisées / interdites [PROPOSITION, aligné MIMIR §11.4 et RC]

**Autorisé** : clôture de `PART_OF`, `IS_A` ; lecture inverse implicite (HOLDS réciproque « held_by » en requête) ; `DEPENDS_ON` **borné avec décroissance** (jamais une clôture nue) ; composition `AFFECTS` **uniquement** via le moteur de propagation déclaré (mécanismes nommés, horizons, pas de parcours libre — MIMIR REQ-CAUS-003) ; cycles traités par progression temporelle + décroissance.
**Interdit** : propager le long de `SUPPORTS`/`CONTRADICTS` (invariant) ; chaîner `CORRELATES_WITH` ; orienter une `AFFECTS` en sens inverse sans déclaration ; fermer transitivement `HOLDS` (détenir ≠ contrôler — le contrôle passe par `ADMINISTERED_BY`/`GOVERNED_BY`).

---

## 7. (g) RECOMMANDATIONS & QUESTIONS OUVERTES

### 7.1 Recommandations (ordre de mise en œuvre si validées)

| # | Recommandation | Coût | Quand |
|---|---|---|---|
| R1 | **Adopter le record de relation à 17 champs** (§3.0) et le **catalogue à 34 types** (§3.2) comme v1 — avec enum machine-vérifiable et tests de conformité (types sujet/objet). | 1–2 j | avant gel v2 |
| R2 | **Implémenter les horloges minimales** (§1.3) : `valid_from/valid_to` sur les familles 2/4, `ts_published` sur documents ; requêtes as-of à deux filtres + test INV-PIT. | 1–2 j | v1/démo |
| R3 | **Garder SQLite pour le concours ; Postgres (Neon free) comme cible**, DDL identique, migration contenue dans `store.py` ; **pas Kuzu, pas Neo4j** (§2.3). | migration ≈ 1–2 j post-concours | décision maintenant, exécution après |
| R4 | **Voie 3 minimale seulement** : extraction documentaire activée uniquement pour les documents d'épisode, avec les portes §4.4 ; tout le reste par règles. | 1–2 j | v1 si budget, sinon post |
| R5 | **Aucun modèle appris dans le chemin de décision v1** ; un seul slot expérimental (recherche sémantique, optionnel) ; HYP-07R pour le reste (§5.3). | 0 | gel v2 |
| R6 | **Écrire les 8 requêtes noyau (Q1–Q8)** comme contrat de test du store (jeux d'essai sur les épisodes mesurés W2B/W3) — c'est ce qui prouve que le graphe « sert » la décision. | 2–3 j | avant démo |
| R7 | **Ajouter `source_family_id` et `extract_method` dès maintenant** (INV-DEPENDENCE + audit d'extraction) — deux colonnes, effet rétroactif fort. | 0,5 j | v1 |
| R8 | **Exporter l'ontologie en JSON-LD/PROV-O-like** en annexe du document technique (posture de standard, pas d'import RDF) — différenciateur de crédibilité. | 0,5 j | post-concours |

### 7.2 Questions ouvertes

| # | Question | Pourquoi elle compte | Qui/quand |
|---|---|---|---|
| QO-1 | **Politique de reorg** : profondeur de confirmation avant qu'un fait on-chain devienne VALIDATED ; que fait-on d'un fait orphelin ? | PIT par bloc vs réalité ; la démo Base Sepolia (1,64 s/bloc [MESURÉ]) | à figer au gel v2 |
| QO-2 | **Identité des contrats upgradeables** (implémentation derrière proxy) : l'adresse stable du proxy suffit-elle, ou suit-on les upgrades ? | l'identité canonique immuable peut masquer un changement de code | revue |
| QO-3 | **Où vivent les quantités** : HOLDS/OWES portent un montant — quelle normalisation (décimaux, unités, pas de double source) pour éviter le double comptage ? | signaux Q1/Q7 en dépendent | revue |
| QO-4 | **Langage des `conditions`** de la famille 3 : enum figée (régime, seuil) vs mini-DSL ? | simplicité vs expressivité ; MIMIR garde des prédicats simples | revue |
| QO-5 | **PROV-O en vocabulaire** : garder nos noms + mapping d'export, ou adopter les termes PROV ? | interop vs lisibilité (reco : mapping) | revue |
| QO-6 | **Gel du LLM d'extraction** (quand on l'active) : version épinglée + hash de prompt + sorties rejouables hors-ligne ? | sans ça, la reconstructibilité meurt à la première extraction | post-concours |
| QO-7 | **Multi-chaînes : un graphe ou des vues par chaîne ?** | Q11 ; les adresses ne collisionnent pas (incluses dans l'id) mais les agrégats si | revue |
| QO-8 | **Neon free en démo vidéo** : les 100 CU-h/projet et le scale-to-zero (5 min) suffisent-ils pour le live ? Sinon, démo SQLite locale et Postgres en miroir. | plan démo | avant démo |
| QO-9 | **PG 19 GA** : adopter les ranges natifs à la GA (attendu fin 2026) ou rester en PG 18 + contraintes applicatives ? | dépend de la date de migration (post-concours : non bloquant) | post-concours |
| QO-10 | **Faut-il un statut `DEPRECATED` de hiérarchie de sources** (source disparue — précédent FRED gold, MIMIR ADR-005) ? | fraîcheur/confiance des familles de sources | revue |

---

## ANNEXE A — Sources

**Interne (dépôt `D:\orvyren_core`)** [lus le 15/10/2026] : `research/SYSTEME_ZONES_OMBRE.md` · `ARCHITECTURE_V1.md` · `research/REVUE_CROISEE_ET_CADRE_CONCRET.md` · `research/W2B_signaux_detection.md` · `research/W2C_enveloppe_execution.md` · `research/VAGUE2_SYNTHESE.md` · `src/orvyren/graph/{models,store,provenance}.py` · `src/orvyren/data/` · `evidence/graph.sqlite`. MIMIR : `D:\midas_v2\MIMIR\docs\MIMIR_Technical_Design.md` (v0.1, 16/09/2026).

**Externe (URLs consultées le 15/10/2026, sauf mention)** :
- Temporalité : sigmod.org/publications/sigmodRecord/1209/pdfs/07.industry.kulkarni.pdf (SQL:2011, 2012) · martinfowler.com/articles/bitemporal-history.html (07/04/2021) · learn.microsoft.com/en-us/sql/relational-databases/tables/temporal-tables (MAJ 2025-05-19) · postgresql.org/docs/19/ddl-temporal-tables.html (PG 19 beta4) · cybertec-postgresql.com/en/implementing-as-of-queries-in-postgresql/ · docs.xtdb.com · arxiv.org/abs/2501.13956 (Zep, 2025) · github.com/getzep/graphiti · mdpi.com/2227-7390/11/23/4852 (2023).
- Stockage/graphe SQL : postgresql.org/docs/19/ddl-property-graphs.html + queries-graph.html (SQL/PGQ) · enterprisedb.com/blog/representing-graphs-postgresql-sqlpgq (18/02/2025) · gavinray97.github.io/blog/postgres-sql-property-graphs · cybertec-postgresql.com/en/handling-graphs-with-sql-pgq-in-postgresql · vldb.org/pvldb/vol16/p4034-wolde.pdf (DuckPGQ) · github.com/pgvector/pgvector (v0.8.6).
- Kuzu : github.com/kuzudb/kuzu (README archivage) · theregister.com/software/2025/10/14/kuzudb-graph-database-abandoned-community-mulls-options · betakit.com/apple-strikes-deal-to-acquire-canadian-database-software-startup-kuzu/ · gdotv.com/blog/kuzu-legacy-embedded-graph-database-landscape/ (mai 2026) · ladybugdb.com · vela.partners/blog/kuzudb-ai-agent-memory-graph-database · pypi.org/project/kuzu (0.11.1).
- Hébergement : render.com/changelog/free-postgresql-instances-now-expire-after-30-days-previously-90 (20/05/2024) · neon.com/pricing · neo4j.com/cloud/aura/faq.
- Extraction : github.com/urchade/GLiNER · aclanthology.org/2021.findings-emnlp.204.pdf (REBEL) · github.com/google/langextract + pypi.org/project/langextract (v1.6.0) · github.com/moj-analytical-services/splink · github.com/zinggai/zingg.
- DL/ML : github.com/microsoft/graphrag (README maintenance) · arxiv.org/abs/2404.16130 · arxiv.org/abs/2410.05779 (LightRAG) · arxiv.org/abs/2502.14802 (HippoRAG 2) · arxiv.org/abs/2501.13958 + 2501.00309 (surveys) · microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/ · arxiv.org/abs/1607.00653 (node2vec) · arxiv.org/abs/1706.02216 (GraphSAGE) · arxiv.org/abs/2006.10637 (TGN) · arxiv.org/abs/2111.15367 (GNN finance) · arxiv.org/abs/2406.11157 (DeFiGuard) · arxiv.org/abs/2602.23599 · arxiv.org/abs/1902.10197 (RotatE).
- Ontologies/DeFi : w3.org/TR/prov-o/ (Rec. 30/04/2013) · spec.edmcouncil.org/fibo/ · dialecticgroup.substack.com/p/introducing-nebula-a-graph-based (26/03/2024) · arxiv.org/abs/2111.11933 (DeFi compositions) · arxiv.org/abs/2506.15295 (lending protocols).

**Fichiers bruts** : `research/raw_b2/` — `notes_00_contexte.md`, `notes_02_recherche_web.md`, `search_*.json` (30 requêtes sauvegardées), `extract_*.md` (10 pages intégrales/extraits).

---

## ANNEXE B — Correspondance MIMIR → ORVYREN (pour le futur document technique)

| Élément MIMIR | Reprise ORVYREN | Écart assumé |
|---|---|---|
| Six horloges (§10.5) | 6 champs (§1.3), toutes portées dès qu'un objet les définit | effective time fusionné avec valid_from en v1 |
| Record Relation 10 champs (§11.2) | Record 17 champs (§3.0) | + validation_status, chain_ref, extract_method, source_family_id, payload |
| Chaîne provenance (§10.5) | Famille 1 complète (8 kinds) | + SAME_AS, CONTRADICTS, REFUTES explicites |
| Labels épistémiques (§0.3) | Conservés tels quels (7 labels) | — |
| Lifecycle relation (§11.2) | Conservé | — |
| Révision L1–L5 (§13.4) | Transposée (L1–L2 auto, L3+ validation) | — |
| Stockage Parquet+DuckDB, pas de base graphe (ADR-002) | SQLite v1 → Postgres cible (§2.3) | MIMIR est mono-nœud recherche ; ORVYREN a une démo web |
| PIT admission (§7.4) + audit (§7.5) | INV-PIT + test de reproduction par décision | — |
| Pas de ML dans le confirmatoire (D26/ADR-014) | §5.3 : idem + étiquetage MODEL-INFERRED | — |
