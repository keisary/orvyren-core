# Campagne de recherche ORVYREN V2

**Statut** : interne — ne pas soumettre.
**Ouverture** : 2026-10-17.
**Clôture cible des premiers rapports** : 2026-10-18 (les synthèses peuvent suivre).
**Donneur d'ordre** : Jovanny (Team Leader).
**Dépôt** : `D:/orvyren_core` (privé).
**Brief complet** : `00_brief/RESEARCH_PROMPT_V2.md` (copie de `D:/orvyren_core/RESEARCH_PROMPT_V2.md`).

## But

Reconstruire ORVYREN comme un **vrai système** dont le **graphe** est le cœur de l'innovation, pas comme un prototype mono-cas. La campagne doit produire des rapports de recherche profonds, sourcés, qui tranchent : schéma de graphe, pipeline de données, runtime agent, produit, plan 72 h.

## Non-objectifs

- Ne pas modifier le code du dépôt.
- Ne pas exécuter de `git`, de transaction, ni manipuler des clés.
- Ne pas produire un document de soumission : les rapports sont internes.
- Ne pas copier le T0 de MIMIR : copier la **vision** du DFKG, adaptée au on-chain.

## Travail en parallèle

La tâche est donnée à **plusieurs IA**. Tu n'es pas seul. Tu verras des fichiers que tu n'as pas écrits : c'est normal. Lis `INDEX.md` avant d'écrire, ajoute ta ligne, ne modifie jamais le rapport d'une autre IA. En cas de désaccord, crée un fichier `...__contradiction.md` et cite les preuves.

## Structure

```
00_brief/          brief, réanalyse, conventions
10_graph/          ontologie, schéma, requêtes, raisonnement, benchmark
20_agents/         runtime, outils, mémoire, orchestration, évaluation
30_data/           sources, ingestion, résolution, stockage, qualité
40_product/        persona, JTBD, UI, parcours, métriques
50_competition/    barème, positionnement, démo, risques
60_synthesis/      synthèse, décisions, plan intégré
```

## Nommage

```
<chantier>__<sujet>__<auteur-ou-modele>__<YYYY-MM-DD>.md
```

Exemples :

- `10_graph__audit-34-relations__claude__2026-10-17.md`
- `10_graph__schema-cible-postgres__gpt__2026-10-17.md`
- `30_data__ingestion-aave-base__gemini__2026-10-17.md`
- `20_agents__tool-calling-provider-agnostic__deepseek__2026-10-17.md`
- `60_synthesis__architecture-v2__hermes__2026-10-18.md`

## Statuts

- `DRAFT` — première version, peut être incomplète.
- `REVIEW` — relu, prêt pour contradiction.
- `FINAL` — recommandation stabilisée.
- `CONTRADICTION` — désaccord documenté avec un autre rapport.
- `SYNTHESIS` — rapport de synthèse.

## Règles de qualité

- Chaque affirmation interne : `fichier:ligne`.
- Chaque affirmation externe : URL + date de consultation.
- Labels : `[FAIT]`, `[MESURÉ]`, `[HYPOTHÈSE]`, `[PROPOSITION]`, `[INCONNU]`.
- Pas de chiffres inventés, pas de benchmarks non exécutés.
- Une recommandation principale par rapport, avec coût et risque.
- Un tableau d'audit des 34 relations pour tout rapport graphe.
- Un plan 72 h et un plan 2–4 semaines.
- « Ce que je construirais d'abord » / « Ce que je ne construirais pas ».

## Lectures minimales

1. `00_brief/RESEARCH_PROMPT_V2.md`
2. `00_brief/REANALYSE_ORVYREN_2026-10-17.md`
3. `D:/orvyren_archive_2026-10-15/research/B2_GRAPHE_ETUDE.md`
4. `D:/midas_v2/MIMIR/docs/MIMIR_Technical_Design.md` §10–11
5. `C:/Users/User/Downloads/Project_2_DFKG_Research_State_0_a11y.docx` §3–18
6. `D:/orvyren_core/src/orvyren/graph/` (`catalog.py`, `record.py`, `queries.py`, `store.py`)
7. `D:/orvyren_core/docs/REANALYSE_ORVYREN_2026-10-17.md` (version repo)

## Chiffres de référence (à vérifier, pas à croire)

- Graphe live : **520 observations, 4 claims, 4 relations, toutes `SUPPORTS`**, 208 Ko, 0 table `entities`/`events`.
- Catalogue : **34 types** (8 / 15 / 3 / 8) ; record **17 champs** ; requêtes **Q1–Q8**.
- Fixtures : **20 records, 13 kinds** sur 3 épisodes.
- Agents : **7 outils fixtures**, 1 tâche / 1 outil, pas de tool calling natif, pas de mémoire retrieval.
- Tests : **844 pytest / 846 unittest**, 3 sautés.
- EVAL : **N = 0**, 2 fenêtres sautées.
- UI : **12 écrans statiques**.
- Deadline : **2026-10-20 15:59 UTC**.

## Contact

Team Leader : Jovanny. Les rapports sont déposés dans ce dossier ; l'index fait foi.
