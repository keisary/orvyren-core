# RAW B2 — notes de contexte (15/10/2026)

## 0. Sources internes lues (pour ce chantier)

### MIMIR — `D:\midas_v2\MIMIR\docs\MIMIR_Technical_Design.md` (v0.1, 16/09/2026)
Éléments à réutiliser pour le bloc GRAPHE ORVYREN :

- **Chaîne de provenance** (§10.5) : `Source → Observation → Extraction → Claim → Relation → Hypothesis → Prediction → Outcome` — chaque flèche = une ligne de lien explicite dans le store (pas de texte libre).
- **Six horloges** (§10.5, REQ-KNOW-008) : event, publication, observation, effective, validity, revision — portées par les objets qui les définissent. T0 = event/publication/observation (dans le record Event §10.3) ; effective/validity/revision = FULL.
- **Record Relation (§11.2, REQ-CAUS-001)** — 10 champs : `relation_id` · `cause`/`effect` (références d'objets, ex. `EVT:FOMC_DECISION.surprise → VAR:DGS2`) · `mechanism` (label court) · `conditions` (prédicats d'état/régime) · `regime_scope` + `horizon_scope` · `epistemic_status` (CAUSAL-DOCUMENTED / CAUSAL-HYPOTHESIS / MODELLED) · `sign_prior` (+/−/ambigu) · `provenance` (littérature/mécanisme documenté) · `lifecycle` (DISCOVERED → EVALUATING → ACTIVE → WEAKENING → SUSPENDED → REJECTED + REACTIVATION CANDIDATE).
- **Labels épistémiques** (§0.3, §Annexe A) : FACT · REPORTED · STATISTICAL · CAUSAL-DOCUMENTED · CAUSAL-HYPOTHESIS · MODEL-INFERRED · REJECTED. Une hypothèse ne devient jamais base de design en silence.
- **Modèle temporel & PIT** (§7.1, §7.4, §7.5) : 3 modes d'admission (PIT-native / Reconstructible / Non-PIT) ; règle PIT normative (« admissible si et seulement si l'accessibilité publique à t est reconstructible ») ; audit PIT par run ; une violation = porte G1 (résultats invalides).
- **Stockage T0 (§10.6 + ADR-002)** : Parquet + catalogue DuckDB ; **pas de base graphe au T0** ; as-of reconstruction FULL tier via tables d'update event-sourcées ; à T0 = filtre sur timestamps (79 événements). OPEN-14 : « Graph storage paradigm (RDF/property/hybrid) — workload benchmark after T0 shape known ».
- **Résolution** (§10.4) : `resolve-entity`/`resolve-event` = FULL ; ordre déterministe avant toute désambiguïsation sémantique/modèle (REQ-KNOW-004) ; une seule identité canonique immuable par entité, identifiants externes = preuves (REQ-KNOW-005).
- **Contradictions** (REQ-KNOW-003) : préserver les claims contradictoires sans les fusionner.
- **Révision** (§13.4) : niveaux L1 confiance/paramètre → L2 état de relation → L3 création/suppression de relation → L4 architecture → L5 ontologie ; pas de réécriture d'histoire ; candidats évalués en shadow mode sur données futures. T0 : seuls L1–L2 automatiques.
- **Audit natif** (§13.5) : la promenade decision → target/thesis → scenario set → propagation paths (relation ids) → claims → observations → sources ; pas d'explainer post-hoc comme mécanisme primaire.
- **LLM hors du chemin confirmatoire** (D26, ADR-014) ; contrat d'extraction versionné ailleurs (FULL).
- **Coût du graphe** : rien de payant (C2/C5), sources gratuites, un nœud, Python, pas de service.

### ORVYREN — état interne
- `SYSTEME_ZONES_OMBRE.md` §2 : 6 questions ouvertes (2.1 schéma, 2.2 relations exactes, 2.3 DL/ML, 2.4 construction, 2.5 stockage, 2.6 requêtes). Invariant : `SUPPORTS` n'autorise **aucune** propagation causale.
- `REVUE_CROISEE_ET_CADRE_CONCRET.md` §2.3 : **4 familles de relations** :
  1. Preuve et dérivation — DERIVED_FROM, EXTRACTED_FROM, SUPPORTS, CONTRADICTS, SUPERSEDES (interdit : SUPPORTS ≠ propagation causale) ;
  2. Structure et exposition — ISSUED_BY, CUSTODIED_AT, HOLDS, OWES, REDEEMABLE_VIA ;
  3. Mécanisme économique — AFFECTS (mécanisme : LIQUIDITY, REDEMPTION, FUNDING…) ;
  4. Contrainte / permission — CONSTRAINS, AUTHORIZES, REVOKES.
  Attributs séparés : `epistemic_status`, `lifecycle`, `validation_status`. Appui : W3C PROV-O (2013) sans obligation RDF.
- `ARCHITECTURE_V1.md` §4 : 16 tables v1 (source, observation, claim, relation, graph_version, hypothesis, branch_delta, research_task, job, portfolio_snapshot, intent, policy_decision, execution, outcome, decision_dossier, calibration) ; ULID ; append-only ; Postgres cible / SQLite tests.
- Code `src/orvyren/graph/` : SQLite append-only v0 — tables sources/observations/claims/relations/hypotheses/decision_nodes ; triggers SQLite qui refusent UPDATE/DELETE ; observation_id = empreinte SHA-256 du contenu ; claim sans référence d'observation refusé ; `snapshot()` = hash SHA-256 stable des lignes courantes ; `verify_chain` = chaque ref d'un claim doit résoudre (observation + source).
- `W2B_signaux_detection.md` : 6 familles de signaux ; mesures vérifiées (rsETH isFrozen bloc 24 908 723, saturation supplyCap 99,999 %, stETH décote 6,185 % le 15/06/2022, USDC dispersion 870 bps le 11/03/2023) ; invariants I1–I12 ; 5 signaux prioritaires.
- `W2C_enveloppe_execution.md` : événements on-chain de l'enveloppe — `AssignRoles`, `SetDefaultRole`, `RolesModSetup`, `ConsumeAllowance` (Zodiac Roles v2, 0xF296…83D5, identique ETH/Base/Base Sepolia) ; kill switch assignRoles(...,false) 1 tx ; politiques lisibles on-chain + subgraph.
- Invariants cadrés (REVUE §2.4) : INV-PIT, INV-AUTH, INV-INTEGRITY, INV-ACCOUNTING, INV-DEPENDENCE (source_family_id — reformater ≠ nouvelle observation indépendante).
- HYP-07R (reportée) : extension ML du graphe — masquage par périodes/familles sans fuite, précision@k ET fraction d'inférences avec provenance complète ; budget égal à une règle simple.
- Contrainte concours : deadline 20/10 15:59 UTC ; recherche d'abord ; free sources only ; démo testnet Base Sepolia ; pas de git commit par les sous-agents.

## 1. Rappels techniques de départ (à vérifier en ligne — voir search_*.json)
- Modèle bitemporel canonique (Snodgrass) : event time / valid time (application) + transaction time (système) ; SQL:2011 : `SYSTEM_TIME` (system-versioned), `APPLICATION_TIME` (application-versioned), `BITEMPORAL`.
- Feature stores : « point-in-time correct join » (Feast/Tecton) — as-of join sans fuite du futur.
- Requêtes « état à l'instant T » : as-of join / temporal join ; snapshots ; SCD2.
- Bases : PostgreSQL (+ AGEl, ltree, recursive CTE, pgvector), Kuzu (embarquée, colonnes, Cypher), Neo4j (AuraDB Free), RDF (Oxigraph/Jena/Blazegraph), DuckDB.
