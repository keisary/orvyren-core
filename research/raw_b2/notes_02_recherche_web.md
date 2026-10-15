# RAW B2 — Recherche web (accès 2026-10-15, sauf mention)

## A. Temporel / PIT

- **Snodgrass / SQL:2011** : modèle bitemporel valid time (monde) + transaction time (système). « Temporal features in SQL:2011 » — Kulkarni & Michels, SIGMOD Record, sept. 2012 — https://sigmod.org/publications/sigmodRecord/1209/pdfs/07.industry.kulkarni.pdf
- **Fowler, « Bitemporal History »** (07/04/2021, extrait) : deux dimensions — *actual history* (« what history should be given perfect transmission of information ») vs *record history* (« how our knowledge of history changes »). Exemple salaire rétroactif. https://martinfowler.com/articles/bitemporal-history.html
- **SQL Server system-versioned temporal tables** (doc MAJ 2025-05-19) : period columns, history table, point-in-time analysis. https://learn.microsoft.com/en-us/sql/relational-databases/tables/temporal-tables
- **PostgreSQL 19 (beta4 au 15/10/2026)** — §5.7 Temporal Tables : **application time natif** (`daterange`, `PRIMARY KEY (…, WITH OVERLAPS)`, `PERIOD`, FKs temporelles) ; **system time NON supporté** (« could be emulated using triggers », extensions externes). Doc publiée ~13/08/2026 (19 beta3 annoncée le 13/08/2026). https://www.postgresql.org/docs/19/ddl-temporal-tables.html
- **SQL/PGQ (property graph queries)** : standard ISO **SQL:2023** ; implémenté dans PostgreSQL (docs PG19 §5.15 + 7.9 ; billets EDB 18/02/2025 https://www.enterprisedb.com/blog/representing-graphs-postgresql-sqlpgq ; blog « Experimenting with SQL:2023 Property-Graph Queries in Postgres 18 » gavinray97.github.io ; Cybertec « Handling graphs with SQL/PGQ in PostgreSQL »). Permet CREATE PROPERTY GRAPH + GRAPH_TABLE sur tables relationnelles, sans SGBD graphe séparé.
- **Cybertec as-of** : pattern maison « AS OF »-queries with triggers + tstzrange — https://www.cybertec-postgresql.com/en/implementing-as-of-queries-in-postgresql/
- **Feature stores / PIT joins** : Azure ML « Offline feature retrieval using a point-in-time join » ; Databricks « Point-in-time feature joins ». Principe : au moment T, ne joindre que les valeurs dont l'horodatage est ≤ T (par entité).
- **XTDB** : base SQL immuable, bitemporelle native (« immutable SQL database », docs.xtdb.com) — https://www.xtdb.com/ ; https://docs.xtdb.com/intro/what-is-xtdb.html
- **Graphiti (Zep)** : « A Framework for Building Temporal Knowledge Graphs » (github.com/getzep/graphiti) ; papier Zep arXiv:2501.13956 (2025) « A Temporal Knowledge Graph Architecture for Agent Memory » ; graphe temporel par épisodes (validité + invalidation, pas de suppression). https://arxiv.org/abs/2501.13956
- **Bitemporal KG (article marketing Sentra, 2025-2026)** : « What Is a Bi-Temporal Knowledge Graph? » — valid time vs transaction time ; invalidation au lieu de suppression ; provenance first-class. https://www.sentra.app/articles/what-is-a-bitemporal-knowledge-graph
- **Event-centric Temporal KG survey** (MDPI Mathematics 11(23):4852, 2023) — https://www.mdpi.com/2227-7390/11/23/4852

## B. Stockage

- **Kuzu / KuzuDB : ABANDONNÉ**. Repo archivé le 10/10/2025 ; accord d'acquisition Apple signé le 09/10/2025 (confirmé par dépôt UE ; BetaKit 2026-02) ; site kuzudb.com hors service ; README : « prior Kuzu releases will continue to be usable ». The Register 14/10/2025 « KuzuDB graph database abandoned, community mulls options ». Forks : Vela-Engineering/kuzu (blog vela.partners), LadybugDB (« DuckDB for Graphs — The KuzuDB Successor », ladybugdb.com ; gdotv blog « Kuzu's Legacy… » statut mai 2026 : LadybugDB actif, Lance Graph, Raphtory, TuringDB, FalkorDBLite), SiafuDB. PyPI kuzu 0.11.1 toujours installable.
- **Neo4j AuraDB Free** (FAQ, accès 15/10/2026) : 1 base, **200 000 nœuds / 400 000 relations**, pas de CB, upgrades auto, **un export de backup ponctuel** (pas de backups glissants). https://neo4j.com/cloud/aura/faq
- **Render free PostgreSQL** : changelog — depuis le 20/05/2024 **expire après 30 jours** (avant 90) ; +14 jours pour upgrader avant suppression ; 1 base gratuite par compte. https://render.com/changelog/free-postgresql-instances-now-expire-after-30-days-previously-90
- **Neon (Databricks) free plan** : permanent (pas un essai), 100 projets, **1 Go/projet + 20 Go/compte**, 100 CU-heures/projet, scale-to-zero après 5 min, historique 6 h, egress 5 Go/projet, snapshot manuel 1. https://neon.com/pricing
- **pgvector** (README, v0.8.6, accès 15/10/2026) : recherche exacte/approximative (HNSW, IVFFlat), quantisation, distances L2/IP/cosinus ; « comes preinstalled with … many hosted providers ». https://github.com/pgvector/pgvector
- **Apache AGE** : extension Cypher pour PostgreSQL (apache/age). https://age.apache.org/
- **DuckPGQ** (DuckDB) : SQL/PGQ dans DuckDB, papier VLDB vol.16 (2023) p.4034 — https://vldb.org/pvldb/vol16/p4034-wolde.pdf ; extension communautaire duckpgq. DuckDB = colonne, embarqué, ASOF JOIN (doc duckdb).
- **Microsoft GraphRAG** : repo MIT, 36 324 stars, ~3 847 forks (15/10/2026) ; README : « largely in maintenance mode, won't be accepting new PRs or implementing new features ». https://github.com/microsoft/graphrag
- **RDF/SPARQL** : Oxigraph (embarqué), Apache Jena ; PROV-O = W3C Recommendation 30/04/2013 (page vérifiée) — https://www.w3.org/TR/prov-o/

## C. Extraction / construction

- **GLiNER** (urchade/GLiNER, créé 2023-11) : NER zero-shot généraliste, léger ; supporte joint entity+relation extraction, streaming ; Apache-2.0. https://github.com/urchade/GLiNER
- **REBEL** (Babelscape/rebel, EMNLP 2021 Findings) : relation extraction seq2seq end-to-end — https://aclanthology.org/2021.findings-emnlp.204.pdf ; modèle rebel-large sur HF.
- **LangExtract** (google/langextract, PyPI v1.6.0, 2025) : extraction d'information structurée par LLM avec ancrage aux passages source. https://github.com/google/langextract
- **Entity resolution** : Splink (moj-analytical-services, algorithme Fellegi-Sunter, « deduplicating 7M records in two minutes ») https://github.com/moj-analytical-services/splink ; Zingg AI (ML dedup) https://github.com/zinggai/zingg
- **GraphRAG variantes** : LightRAG arXiv:2410.05779 (08/10/2024, v3 04/2025) ; HippoRAG 2 arXiv:2502.14802 (fév. 2025) ; LazyGraphRAG (Microsoft Research blog, nov. 2024 — indexation à coût réduit) ; surveys arXiv:2501.13958 et arXiv:2501.00309 (2025). MSE GraphRAG papier « From Local to Global » arXiv:2404.16130 (avr. 2024).

## D. DL/ML graphe — références

- **node2vec** arXiv:1607.00653 (2016) ; **GraphSAGE** arXiv:1706.02216 (NeurIPS 2017) ; **TGN** arXiv:2006.10637 (Temporal Graph Networks, 2020) ; **RotatE** arXiv:1902.10197 (ICLR 2019).
- **GNN & finance** : « A Review on Graph Neural Network Methods in Financial Applications » arXiv:2111.15367.
- **DeFiGuard** arXiv:2406.11157 (2024) : détection de manipulation de prix DeFi par GNN (précédent direct de tâche « anomalies »).
- **GNN blockchain anomalies** arXiv:2602.23599 (2026) : normalisation/initialisation des GNN pour l'anomalie blockchain.
- **Nebula (Dialectic, 26/03/2024)** : « DeFi should be represented as a knowledge graph to properly assess the risk » — https://dialecticgroup.substack.com/p/introducing-nebula-a-graph-based
- **DeFi compositions** arXiv:2111.11933 (2021) ; **Théorie des lending protocols** arXiv:2506.15295 (2025).
- **FIBO** (EDMC Financial Industry Business Ontology) — https://spec.edmcouncil.org/fibo/ ; OMG spec FND 1.2.

## E. Divers
- **Microsoft temporal tables** (doc MAJ 2025-05-19) ; **SQL:2011** : PG n'implémentait pas SQL:2011 avant PG19 (wiki PostgreSQL SQL2011Temporal).
- Kuzu PyPI dernière version vue : 0.11.1. https://pypi.org/project/kuzu
