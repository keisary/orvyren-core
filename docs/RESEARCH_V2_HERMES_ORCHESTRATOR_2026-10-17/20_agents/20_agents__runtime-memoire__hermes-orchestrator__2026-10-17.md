# 20_agents — Runtime, outils, mémoire et orchestration

**Auteur / agent** : Hermes-orchestrateur (deepseek-flash, session recherche V2).
**Date** : 2026-10-17.
**Chantier** : `20_agents`.
**Statut** : INTERNE — recherche V2, ne pas soumettre.
**Périmètre** : définition d'agent, boucle, outils, mémoire, orchestration, checkpoints, évaluation, migration du code actuel.
**Fichiers lus** : `src/orvyren/agents/{loop,tools,journal,worker,contracts,llm}.py`, `config/models.json`, `run_agents.py`, Anthropic/OpenAI/ReAct/12-Factor/MemGPT/Zep/LangGraph.

---

## 0. Verdict

Le code actuel est un **orchestrateur de prompts** avec deux rôles et un outil fixture par tâche. Ce n'est pas un agent au sens **LLM + outils callables + mémoire + boucle**. Le journal est une trace d'audit, pas une mémoire retrieval.

**Décision** : pour le MVP, **un orchestrateur + un chercheur + un critique**, 4–6 outils live, une mémoire working + episodic minimale, des checkpoints, des budgets et une trace. Pas de swarm, pas de 5 agents, pas de framework lourd.

---

## 1. Définition opérationnelle

> Un agent = un LLM qui, dans une boucle, choisit des actions (outils), observe les résultats, met à jour son état/mémoire, et s'arrête sur un critère explicite.

Sans outils : chatbot. Sans mémoire : script. Sans boucle : pipeline. Sans budget/trace : risque.

---

## 2. Architecture MVP

```mermaid
flowchart LR
    Q[Question / alerte] --> O[Orchestrateur]
    O --> M[Memory retrieval]
    M --> P[Plan]
    P --> T[Tool call]
    T --> X[Observation]
    X --> H[Hypothesis update]
    H --> D{Décision?}
    D -- non --> P
    D -- oui --> C[Décision candidate]
    C --> POL[Policy hors LLM]
    POL --> ACT[Action / refus]
```

### Rôles

| Rôle | Fait | Ne fait pas |
|---|---|---|
| Orchestrateur | plan, budget, choix des outils | ne signe pas, n'invente pas de chiffre |
| Chercheur | `graph_query`, `chain_logs`, `price_history`, `fetch_document` | pas d'action |
| Critique | contre-preuves, unités, sources corrélées | pas de décision alone |
| Policy | ALLOW/DENY/REQUIRE_APPROVAL | hors LLM |
| Exécution | intent, signature, receipt | pas de choix |

**Ajouter un agent seulement si une ablation montre un gain.** Pas de vote comme vérité.

---

## 3. Boucle

Deux patterns acceptables :

- **Plan-execute** : plan initial, outils, observation, mise à jour, stop. Plus déterministe, plus facile à tester.
- **ReAct** : raisonner → agir → observer → répéter. Plus flexible, plus coûteux.

**Recommandation MVP** : plan-execute borné, avec une phase ReAct courte (2–3 itérations) pour les faits manquants. `max_iters=8`, `max_tool_calls=12`.

### État

```
run_id, question, holder, as_of, hypotheses[], evidence[], pending_tasks[],
budget{llm_calls, tool_calls, wall_s, cost_usd}, trace[], status
```

Checkpoint après chaque outil ; reprise possible ; pas de perte de trace.

---

## 4. Outils

| Outil | Entrée | Sortie | Lecture/Action |
|---|---|---|---|
| `graph_query` | kind, src/dst, as_of, block | relations + provenance | lecture |
| `graph_path` | src, dst, kinds, depth | chemins + signe | lecture |
| `graph_snapshot` | as_of/block | hash + counts | lecture |
| `chain_logs` | address, topic, range | events décodés | lecture |
| `chain_state` | address, block | état | lecture |
| `price_history` | asset, window | observations | lecture |
| `fetch_document` | url/doc | texte + hash | lecture |
| `web_search` | query | résultats + URLs | lecture |
| `hypothesis_update` | hyp, claim, support/refute | état | écriture mémoire |
| `evidence_attach` | claim/relation, source | provenance | écriture mémoire |
| `portfolio_exposure` | holder, as_of | exposition | lecture |
| `policy_propose` | action | policy candidate | proposition |
| `execute_intent` | intent autorisé | tx/reçu | action, séparé |

**Règle** : le chercheur n'a jamais `execute_intent` ; l'agent d'action ne fait pas de recherche.

---

## 5. Mémoire

| Type | Contenu | Stockage | Retrieval |
|---|---|---|---|
| Working | question, hypothèses, plan, budget | état du run | direct |
| Episodic | runs, décisions, outcomes, erreurs | table `runs/decisions` | par entité/temps |
| Semantic | claims, relations, entités | graphe + FTS/pgvector | par entité/texte |
| Procedural | playbooks, requêtes, skills | fichiers/versionnés | par tâche |

**Règles** :

- Mémoire = **faits sourcés + résumés**, pas un chat log.
- Retrieval PIT-safe : ne jamais injecter un fait postérieur à `as_of`.
- Résumé avec liens vers les preuves, pas de chiffre inventé.
- Une mémoire peut être `UNKNOWN` ; ne pas compléter par le LLM.
- `source_family_id` pour l'indépendance.

**Patterns** : MemGPT (contexte virtuel), Zep/Graphiti (graphe temporel), LangGraph checkpoints/store. Pour le MVP : Postgres/SQLite + FTS, pas de base vectorielle obligatoire.

---

## 6. Orchestration

- **Manager pattern** : orchestrateur appelle chercheur/critique comme outils.
- **Handoffs** : seulement si un spécialiste a un contexte vraiment différent.
- **Swarm** : non pour le MVP ; difficile à évaluer et à auditer.
- **Parallélisme** : outils de lecture indépendants en parallèle ; écritures sérialisées.
- **Human-in-the-loop** : action au-dessus du seuil, contradiction non résolue, source stale.

---

## 7. Migration du code actuel

| Aujourd'hui | Cible |
|---|---|
| `loop.py` 1 tâche/1 outil | plan multi-étapes + observations |
| `tools.py` 7 fixtures | 4–6 outils live |
| `journal.py` trace | trace + mémoire |
| `worker.py` 2 rôles | orchestrateur + chercheur + critique |
| `contracts.LLMBackend` JSON | tool calling + fallback |
| `run_agents.py` replay/live | budget/trace/checkpoint |

**Ne pas casser** : policy, execution, replay, verify.

---

## 8. Plan 72 h

- Orchestrateur + chercheur + critique.
- 4 outils : `graph_query`, `chain_logs`, `price_history`, `fetch_document`.
- Mémoire working + episodic (SQLite) ; semantic via graphe.
- `max_iters=8`, `max_tool_calls=12`, budget $.
- Checkpoint après chaque outil ; trace.
- **Pas** de swarm, pas de 5 agents, pas de framework.

---

## 9. Risques

| Risque | Mitigation |
|---|---|
| Boucle infinie | max_iters, budget |
| Outil halluciné | schéma + registry |
| Mémoire inventée | faits sourcés + PIT |
| Agent qui agit | séparation lecture/action |
| Coût | budget + cache |
| Non-reproductibilité | trace + checkpoint |
| Complexité | 3 rôles max |

---

## 10. Sources

- `src/orvyren/agents/{loop,tools,journal,worker,contracts,llm}.py`.
- `config/models.json` ; `run_agents.py`.
- Anthropic, *Building effective agents* — https://www.anthropic.com/engineering/building-effective-agents — consulté 2026-10-17.
- OpenAI, *A practical guide to building agents* — https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents — consulté 2026-10-17.
- ReAct — https://arxiv.org/abs/2210.03629 — consulté 2026-10-17.
- 12-Factor Agents — https://github.com/humanlayer/12-factor-agents — consulté 2026-10-17.
- MemGPT — https://arxiv.org/abs/2310.08560 — consulté 2026-10-17.
- Zep/Graphiti — https://arxiv.org/abs/2501.13956 — consulté 2026-10-17.
- LangGraph persistence — https://docs.langchain.com/oss/python/langgraph/persistence — consulté 2026-10-17.
