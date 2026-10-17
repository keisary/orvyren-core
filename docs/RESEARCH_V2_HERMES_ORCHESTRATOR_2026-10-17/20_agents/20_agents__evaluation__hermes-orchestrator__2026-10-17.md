# 20_agents — Évaluation des agents

**Auteur / agent** : Hermes-orchestrateur (deepseek-flash, session recherche V2).
**Date** : 2026-10-17.
**Chantier** : `20_agents`.
**Statut** : INTERNE — recherche V2, ne pas soumettre.
**Périmètre** : métriques, baselines, protocole, traces, coûts, sécurité, plan 72 h. Les tests actuels sont des tests de contrats, pas une évaluation d'agent.
**Fichiers lus** : `src/orvyren/agents/`, `tests/test_agents_*`, `evidence/agents_live/`, `docs/RECHERCHE_AMELIORATION_ET_SCALING_2026-10-17.md`, `10_graph__contradiction-72h-scope__codex__2026-10-17.md`.

---

## 0. Verdict

Il n'y a **pas d'évaluation d'agent** : les tests vérifient des contrats, des budgets et du déterminisme, pas la qualité d'une enquête. Une session live existe (19 appels, 0,0192 $, `DONE/ARRET-2`, critique FRAGILE) mais elle n'est pas un benchmark : N=1, pas de baseline, pas de tâches répétées.

**Décision** : un petit benchmark de 20–50 tâches, 3 baselines (A0 sans agent, A1 agent sans graphe, A2 agent + graphe), des métriques de résultat **et** de processus, des traces, des coûts, et un verdict honnête. Pas de score unique, pas de N=1 présenté comme preuve.

---

## 1. Métriques

| Niveau | Métrique | Définition |
|---|---|---|
| Tâche | succès | la question reçoit une réponse correcte et sourcée |
| Tâche | abstention | `INCONCLUSIVE`/`NO_ACTION` correct si les preuves manquent |
| Outils | précision | appels utiles / appels totaux |
| Outils | couverture | faits nécessaires effectivement collectés |
| Preuve | provenance | % de claims avec source + timestamp + hash |
| Recherche | faits nouveaux | faits validés absents du snapshot initial |
| Recherche | discrimination | hypothèses départagées / hypothèses testées |
| Décision | qualité | action correcte vs baseline / règle |
| Sécurité | violations | actions hors policy, clés, calldata libre |
| Coût | USD/décision | tokens + outils |
| Latence | wall/décision | p50/p95 |
| Trace | complétude | étapes, outils, observations, arrêts |

**Règle** : un score global masque les échecs. Publier les métriques séparées et les cas.

---

## 2. Baselines

| Baseline | Description | Ce qu'elle teste |
|---|---|---|
| **A0** | règle fixe / humain / script | le minimum |
| **A1** | agent sans graphe, outils RPC/prix | la valeur des outils seuls |
| **A2** | agent + graphe (Q1/Q4/Q6/Q7/Q8) | la valeur du graphe |
| **A3** | agent + mémoire | la valeur de la mémoire |
| **A4** | multi-agent | seulement si A2 est stable |

**Pour le 72 h** : A0 vs A2 sur 20–30 tâches. A1/A3/A4 = roadmap. Ne pas revendiquer un gain multi-agent sans ablation.

---

## 3. Protocole

1. **Tâches** : 20–50 questions courtes, dérivées d'un portefeuille Aave et de 3 épisodes (USDC 2023, stETH 2022, rsETH 2026).
2. **Snapshot** : même bloc, même graphe, mêmes sources pour toutes les baselines.
3. **Exécution** : 2–3 répétitions par tâche (température 0, mais coût/latence varient).
4. **Trace** : chaque run enregistre messages, outils, observations, budgets, arrêts.
5. **Vérité** : réponse attendue + preuves minimales + cas d'abstention.
6. **Jugement** : correctness, provenance, abstention, sécurité ; pas de juge LLM seul pour les chiffres.
7. **Rapport** : N, coûts, p50/p95, échecs, limites ; si N<30 → « non conclusionnel ».

---

## 4. Ce qu'il faut mesurer sur le graphe

- Q1 : exposition correcte vs baseline ;
- Q4 : PIT correct (pas de fuite) ;
- Q6 : provenance complète ;
- Q7 : concentration/HHI ;
- Q8 : permissions as-of bloc ;
- Q10 : faits manquants détectés.

**Test clé** : mêmes questions, même snapshot, avec et sans graphe. Si le graphe n'améliore pas la provenance ou la détection d'inconnues, le dire.

---

## 5. Sécurité

- 0 action hors policy.
- 0 clé/calldata libre dans un outil de recherche.
- Refus correct sur source stale/contradiction.
- `REQUIRE_APPROVAL` pour action à risque.
- Un agent ne peut pas augmenter son budget.
- Toute action a un intent, une policy, un reçu.

---

## 6. Plan 72 h

- 20–30 tâches, A0 vs A2.
- 2 répétitions, température 0.
- 4 outils, 1 mémoire minimale.
- Rapport : N, succès, provenance, coût, latence, échecs.
- **Pas** de N=100, pas de score unique, pas de « EVAL » si les séries ne sont pas assemblées.
- **Pas** de juge LLM pour les chiffres ; les chiffres viennent des observations.

---

## 7. Risques

| Risque | Mitigation |
|---|---|
| N=1 présenté comme preuve | N, IC, « non conclusionnel » |
| Juge LLM biaisé | vérité humaine + preuves |
| Coût | budget, cache, tâches courtes |
| Fuite PIT | snapshot + Q4 |
| Métriques trop nombreuses | 6–8 métriques |
| Agent évalué sur son prompt | baselines identiques |
| Confusion tests/éval | section séparée |

---

## 8. Sources

- `src/orvyren/agents/` ; `tests/test_agents_*`.
- `evidence/agents_live/` (session N=1, 0,0192 $).
- `docs/RECHERCHE_AMELIORATION_ET_SCALING_2026-10-17.md`.
- `10_graph__contradiction-72h-scope__codex__2026-10-17.md`.
- Anthropic, *Building effective agents* — https://www.anthropic.com/engineering/building-effective-agents — consulté 2026-10-17.
- OpenAI, *A practical guide to building agents* — https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents — consulté 2026-10-17.
- 12-Factor Agents — https://github.com/humanlayer/12-factor-agents — consulté 2026-10-17.
