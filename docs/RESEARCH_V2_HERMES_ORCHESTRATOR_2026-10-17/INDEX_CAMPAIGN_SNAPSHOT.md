# INDEX — Campagne de recherche ORVYREN V2

**Dernière mise à jour** : 2026-10-17 (ouverture).
**Règle** : chaque IA ajoute une ligne après avoir écrit son rapport. Ne pas modifier les lignes des autres ; en cas de correction, ajouter une ligne `v2` et expliquer le delta.

| # | Fichier | Auteur / modèle | Chantier | Date | Statut | Conclusion en une phrase |
|---|---|---|---|---|---|---|
| 0 | `00_brief/RESEARCH_PROMPT_V2.md` | Jovanny / Hermes | Brief | 2026-10-17 | READY | Brief de campagne : reconstruire le système autour du graphe, pas améliorer le prototype. |
| 1 | `00_brief/REANALYSE_ORVYREN_2026-10-17.md` | Hermes | Diagnostic | 2026-10-17 | FINAL | Le noyau de confiance est réel ; le système (données, graphe, agents, produit) manque. |
| 2 | `10_graph/10_graph__audit-34-relations__hermes__2026-10-17.md` | Hermes | 10_graph | 2026-10-17 | CONTESTED | 34 types définis, 4 relations live toutes SUPPORTS ; scope 72 h ramené à 8–10 relations core après Codex. |
| 3 | `10_graph/10_graph__schema-cible__hermes__2026-10-17.md` | Hermes | 10_graph | 2026-10-17 | REVISED | Schéma nodes/events/relations 17 champs, PIT ; SQL/PGQ retiré, index (src,kind) retiré, seuils v4 MiniMax. |
| 4 | `60_synthesis/60_synthesis__graph-first-architecture__hermes__2026-10-17.md` | Hermes | 60_synthesis | 2026-10-17 | DRAFT | Architecture graph-first v2 : 8–10 relations core, Aave v3 Base, PIT, plan 72 h et critères d'acceptation. |
| 5 | 10_graph/10_graph__contradiction-72h-scope__codex__2026-10-17.md | Codex / GPT-6 | 10_graph | 2026-10-17 | CONTRADICTION | Le test SQLite synthetique ne valide pas 16 types et 10^5 evenements on-chain en 72 h; viser une slice bornee. |
| 6 | 10_graph/10_graph__schema-cible__minimax-code__2026-10-17.md | minimax-code / MiniMax-M3.1 | 10_graph | 2026-10-17 | FINAL | Le goulet n'est pas le moteur mais **deux représentations de relation sans pont** (`models.Relation` 6 champs minuscules ≠ `record.RelationRecord` 17 champs majuscules) ; SQLite réglé tient 10⁵ à **220 ms / 31,7 Mo** (×342 vs Python), aucune base graphe justifiée, et l'index `(src, kind)` de B2 §6.2 coûte **×139**. |
| 7 | 10_graph/10_graph__contradiction-sqlpgq-et-index__minimax-code__2026-10-17.md | minimax-code / MiniMax-M3.1 | 10_graph | 2026-10-17 | CONTRADICTION | SQL/PGQ n'est livrable dans aucune PostgreSQL (patch reverté, URL citée par Hermes en 404) ; l'index `(src,kind)` mesuré ×117 à ×139 ; benchmark §10 de Hermes bâti sur un générateur dégénéré (`q2_paths: 1`), écart réel ~16× supérieur. |
| 8 |  |  |  |  |  |  |
| 8 |  |  |  |  |  |  |
| 9 |  |  |  |  |  |  |
| 10 |  |  |  |  |  |  |
| 11 | `60_synthesis/60_synthesis__reconciliation-status__hermes__2026-10-17.md` | Hermes | 60_synthesis | 2026-10-17 | STATUS | Non, la recherche n'est pas finie ; contradictions Codex/MiniMax intégrées, reste C1/C2, ingestion, SQL, agents, produit. |
| 12 | `10_graph/10_graph__entites-evenements__hermes-orchestrator__2026-10-17.md` | Hermes-orchestrateur | 10_graph | 2026-10-17 | FINAL | Identités `chain:address`, événements `(chain,tx,log)`, résolution déterministe ; pas de ticker comme clé. |
| 13 | `10_graph/10_graph__temporalite-pit__hermes-orchestrator__2026-10-17.md` | Hermes-orchestrateur | 10_graph | 2026-10-17 | FINAL | Bitemporel applicatif, bloc finalisé, reorg `REORGED`, pas de SQL/PGQ ; snapshot 72 h. |
| 14 | `10_graph/10_graph__requetes-propagation__hermes-orchestrator__2026-10-17.md` | Hermes-orchestrateur | 10_graph | 2026-10-17 | FINAL | Q1/Q4/Q6/Q7/Q8 SQL, profondeur bornée, pas d'index (src,kind) ; Q2/Q3/Q10 ensuite. |
| 15 | `10_graph/10_graph__benchmark__hermes-orchestrator__2026-10-17.md` | Hermes-orchestrateur | 10_graph | 2026-10-17 | FINAL | Benchmark synthétique v2/v4 ; Aave réel à faire ; seuils 0,25 s/50k et 0,5 s/100k. |
| 16 | `30_data/30_data__sources-ingestion__hermes-orchestrator__2026-10-17.md` | Hermes-orchestrateur | 30_data | 2026-10-17 | FINAL | Aave v3 Base, 30 jours, 10k+ events, manifest, watermark, reorg ; pas de multi-chaîne. |
| 17 | `30_data/30_data__resolution-extraction__hermes-orchestrator__2026-10-17.md` | Hermes-orchestrateur | 30_data | 2026-10-17 | FINAL | Résolution déterministe, alias = preuve, extraction LLM hors décision ; 2–3 docs max. |
| 18 | `20_agents/20_agents__tool-calling__hermes-orchestrator__2026-10-17.md` | Hermes-orchestrateur | 20_agents | 2026-10-17 | FINAL | Tool calling natif si disponible, fallback JSON strict, schémas, budgets, trace. |
| 19 | `20_agents/20_agents__runtime-memoire__hermes-orchestrator__2026-10-17.md` | Hermes-orchestrateur | 20_agents | 2026-10-17 | FINAL | Orchestrateur+chercheur+critique, 4 outils, mémoire working/episodic/semantic, pas de swarm. |
| 20 | `20_agents/20_agents__evaluation__hermes-orchestrator__2026-10-17.md` | Hermes-orchestrateur | 20_agents | 2026-10-17 | FINAL | 20–30 tâches, A0 vs A2, provenance/coût/latence ; N=1 n'est pas une preuve. |
| 21 | `40_product/40_product__persona-ui__hermes-orchestrator__2026-10-17.md` | Hermes-orchestrateur | 40_product | 2026-10-17 | FINAL | Opérateur de trésorerie, un espace d'enquête, démo 5 min ; pas 12 écrans. |
| 22 | `50_competition/50_competition__positionnement__hermes-orchestrator__2026-10-17.md` | Hermes-orchestrateur | 50_competition | 2026-10-17 | FINAL | Graph-first, sécurité=trust layer, claims honnêtes 8–10 relations/10k events. |
| 23 | `60_synthesis/60_synthesis__architecture-v2__hermes-orchestrator__2026-10-17.md` | Hermes-orchestrateur | 60_synthesis | 2026-10-17 | FINAL | Slice Aave v3 Base, C1/C2 puis ingestion, Q1/Q4/Q6/Q7/Q8, plan 72 h et claims. |

## Rapports attendus (priorité)

| Chantier | Sujet | Priorité | Fichier attendu |
|---|---|---|---|
| 10_graph | Audit complet des 34 relations + types manquants | P0 | `10_graph__audit-34-relations__*.md` |
| 10_graph | Schéma cible (Postgres/SQLite/graph DB) + migration | P0 | `10_graph__schema-cible__*.md` |
| 10_graph | Modèle entités/événements + résolution | P0 | `10_graph__entites-evenements__*.md` |
| 10_graph | Temporalité/PIT + provenance + contradictions | P0 | `10_graph__temporalite-pit__*.md` |
| 10_graph | Requêtes de décision Q1–Q14 + propagation | P0 | `10_graph__requetes-propagation__*.md` |
| 10_graph | Benchmark et évaluation du graphe | P0 | `10_graph__benchmark__*.md` |
| 30_data | Sources on-chain + ingestion 72 h | P0 | `30_data__sources-ingestion__*.md` |
| 30_data | Résolution entités/événements + extraction documentaire | P1 | `30_data__resolution-extraction__*.md` |
| 20_agents | Tool calling provider-agnostique | P1 | `20_agents__tool-calling__*.md` |
| 20_agents | Outils, boucle, mémoire, orchestration | P1 | `20_agents__runtime-memoire__*.md` |
| 20_agents | Évaluation agent | P1 | `20_agents__evaluation__*.md` |
| 40_product | Persona, JTBD, UI, parcours | P1 | `40_product__persona-ui__*.md` |
| 50_competition | Positionnement, barème, démo, risques | P1 | `50_competition__positionnement__*.md` |
| 60_synthesis | Architecture v2 + plan 72 h | P0 | `60_synthesis__architecture-v2__*.md` |

## Contradictions

| Fichier | Conteste | Date | Statut |
|---|---|---|---|
| 10_graph/10_graph__contradiction-72h-scope__codex__2026-10-17.md | Hermes audit/schema reports, sections 0/3/7/9 | 2026-10-17 | CONTRADICTION |
| 10_graph/10_graph__contradiction-sqlpgq-et-index__minimax-code__2026-10-17.md | Hermes `10_graph__schema-cible__hermes__2026-10-17.md`, lignes 18, 54, 304, 637-648, 765 — SQL/PGQ en cible, index `(src,kind)`, chiffres du benchmark §10 | 2026-10-17 | CONTRADICTION |
| 10_graph/10_graph__schema-cible__minimax-code__2026-10-17.md | B2_GRAPHE_ETUDE.md §2.2, §2.3 (« SQL/PGQ natif PG 18 ») et §6.2 (index `(src,kind)`) — prémisses infirmées | 2026-10-17 | CONTRADICTION |
