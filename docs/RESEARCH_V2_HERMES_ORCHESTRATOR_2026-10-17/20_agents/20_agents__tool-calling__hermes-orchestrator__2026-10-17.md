# 20_agents — Tool calling provider-agnostique

**Auteur / agent** : Hermes-orchestrateur (deepseek-flash, session recherche V2).
**Date** : 2026-10-17.
**Chantier** : `20_agents`.
**Statut** : INTERNE — recherche V2, ne pas soumettre.
**Périmètre** : mécanisme natif de tool calling, support providers, schémas, boucle, erreurs, budgets, fallback, migration du code actuel.
**Fichiers lus** : `src/orvyren/agents/{contracts,llm,loop,tools,journal,worker}.py`, `config/models.json`, `DeepSeek tool calls` docs, Anthropic/OpenAI/12-Factor/ReAct.

---

## 0. Verdict

Le code actuel est en **JSON mode**, pas en tool calling natif : `LLMBackend.complete()` ne prend que `system_prompt` + `payload` (`contracts.py:202–212`), et `loop.py` exécute un outil fixture après un plan. DeepSeek documente le tool calling ; MiMo/GLM/Kimi doivent être vérifiés endpoint par endpoint.

**Décision** : un **adaptateur provider-agnostique** avec tool calling natif quand disponible et fallback JSON strict ; schémas JSON, `tool_choice`, messages `tool`, validation, budgets, trace. Ne jamais donner au LLM un shell, une clé ou une calldata libre.

---

## 1. Ce que « tool calling » veut dire

1. Le runtime envoie une liste d'outils (`tools`) avec `name`, `description`, `parameters` JSON Schema.
2. Le modèle répond soit du texte, soit `tool_calls` : `{id, name, arguments}`.
3. Le runtime **valide** les arguments, **exécute** l'outil, **trace** l'appel.
4. Le résultat est renvoyé comme message `role: "tool"`, `tool_call_id`.
5. La boucle recommence ; l'API est **stateless**, donc tout l'historique est renvoyé à chaque tour.
6. On plafonne (5–10 itérations) et on budgete (tokens, coût, temps, outils).

**Le modèle n'exécute rien.** Il propose ; le runtime dispose.

---

## 2. Support providers (à vérifier, pas à supposer)

| Provider | Modèle | Tool calling | Remarque |
|---|---|---|---|
| DeepSeek | `deepseek-flash` | **oui**, documenté | `tools`, `tool_calls`, `strict` en beta ; base `https://api.deepseek.com` |
| MiMo | `mimo-v2.6-pro` | **à vérifier** | endpoint OpenAI-compatible, mais « compatible » ≠ tool calling natif |
| GLM | `glm-5.3-flash` | **à vérifier** | base URL à renseigner |
| Moonshot | `kimi-k2.6` | **à vérifier** | base URL à renseigner |

**Règle** : un test de fumée par provider (`tools` + `tool_choice=auto`, un outil `ping`) avant de l'utiliser en live. Si le provider ne renvoie pas `tool_calls`, fallback JSON strict.

---

## 3. Contrat d'outil ORVYREN

```json
{
  "type": "function",
  "function": {
    "name": "graph_query",
    "description": "Query the on-chain evidence graph at a PIT snapshot.",
    "parameters": {
      "type": "object",
      "properties": {
        "kind": {"type": "string", "enum": ["HOLDS", "DEPOSITED_IN", "COLLATERALIZES"]},
        "src": {"type": "string"},
        "as_of": {"type": "string", "format": "date-time"},
        "as_of_block": {"type": "integer"}
      },
      "required": ["kind"],
      "additionalProperties": false
    }
  }
}
```

**Règles** :

- Schéma strict, `additionalProperties: false`.
- Un outil = une action, pas un DSL géant.
- Lecture vs action séparées : `graph_query` ne signe pas ; `execute_intent` est réservé.
- Idempotence, timeout, budget, erreurs typées.
- Toute sortie porte `source`, `ts`, `hash`, `status`.
- Un outil peut retourner `UNAVAILABLE`/`UNKNOWN`, jamais une valeur inventée.

---

## 4. Boucle runtime

```
messages = [system, user]
for i in range(max_iters):
    response = provider.chat(messages, tools=schemas, tool_choice="auto")
    if response.tool_calls:
        for call in response.tool_calls:
            args = validate(call.arguments)
            result = registry.execute(call.name, args)
            messages.append(tool_message(call.id, result))
        continue
    return response.content
raise BudgetExceeded
```

**Garde-fous** :

- `max_iters` 5–10.
- budget tokens/coût/temps/outils par run.
- retry transport/429/5xx, pas de retry sur validation.
- trace de chaque appel (nom, args hashés, durée, statut, source).
- stop si outil indisponible répété.
- human-in-the-loop pour action à risque.

---

## 5. Fallback JSON strict

Si le provider ne supporte pas `tools` :

1. demander un JSON `{ "tool": "...", "arguments": {...} }` avec schéma ;
2. valider le JSON et les arguments ;
3. exécuter ;
4. renvoyer l'observation dans le prompt ;
5. refuser si JSON invalide (pas de réparation silencieuse).

Le fallback est **moins bon** (le modèle ne voit pas les outils comme des fonctions), mais il est déterministe et testable.

---

## 6. Migration du code actuel

| Aujourd'hui | Cible |
|---|---|
| `LLMBackend.complete(role, schema, payload)` | `complete_with_tools(messages, tools, tool_choice)` |
| `ResearchPlan` JSON + un outil | boucle multi-étapes avec observations |
| `ToolRegistry` fixtures | outils live (`graph_query`, `chain_logs`, `price_history`, etc.) |
| `loop.py` 1 tâche/1 outil | plan → tool → observation → hypothèse → décision |
| `journal.py` trace | trace + mémoire retrieval |
| `config/models.json` `json_mode` | `tool_mode` + fallback |

**Migration minimale** : ajouter `tools` au backend, un adaptateur par provider, un test de fumée, puis brancher `graph_query`. Ne pas réécrire la policy.

---

## 7. Tests

1. Provider renvoie `tool_calls` → outil exécuté.
2. Arguments invalides → refus, pas d'exécution.
3. Outil inconnu → refus.
4. Timeout → `UNAVAILABLE`, pas de valeur inventée.
5. Budget dépassé → arrêt.
6. Fallback JSON → même résultat.
7. Trace : chaque appel a un hash et un statut.
8. Aucun outil d'action accessible au chercheur.

---

## 8. Plan 72 h

- Adaptateur DeepSeek natif + fallback JSON.
- 4 outils : `graph_query`, `chain_logs`, `price_history`, `fetch_document`.
- 1 test de fumée par provider.
- Budget 8 itérations, 12 appels d'outils.
- **Pas** de swarm, pas de 20 outils, pas d'action libre.

---

## 9. Sources

- `src/orvyren/agents/contracts.py:202–212` ; `llm.py` ; `loop.py:8` ; `tools.py:10–17,75–84`.
- `config/models.json`.
- DeepSeek tool calls — https://api-docs.deepseek.com/guides/tool_calls — consulté 2026-10-17.
- OpenAI function calling — https://platform.openai.com/docs/guides/function-calling — consulté 2026-10-17.
- Anthropic tool use — https://docs.anthropic.com/en/docs/build-with-claude/tool-use — consulté 2026-10-17.
- 12-Factor Agents — https://github.com/humanlayer/12-factor-agents — consulté 2026-10-17.
- ReAct — https://arxiv.org/abs/2210.03629 — consulté 2026-10-17.
