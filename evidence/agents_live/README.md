# Session agents LIVE — usdc-2023-03 (17/10/2026)

Première **exécution réelle** de la boucle MA-B (orchestrateur + critique en
processus séparés) avec les modèles épinglés du gel A2 — ferme la partie
« live » de W2, restée [NON EXÉCUTÉE] jusqu'ici.

- **Modèles réels** : `deepseek-flash` (V4.1-Flash ; orchestrateur, 18 appels) +
  `mimo-v2.6-pro` (V2.6 ; critique adversarial, 1 appel) — endpoints épinglés
  dans `config/models.json` (MiMo = Token Plan régional `token-plan-sgp`).
- **Résultat** : `DONE / ARRET-2` (arrêt **ordonné** : plafond d'outils 12/12
  atteint) ; critique **FRAGILE** (8 objections) → escalade **REQUIRE_APPROVAL** —
  même chemin que la démo scriptée, mais 100 % réel.
- **Budget** : 18/30 appels LLM · 12/12 outils · 137 s/600 · **0,0192 $** / 0,10 $
  (compteurs gelés A5, fail-closed).
- **Chaînes vérifiées** : orchestrateur 62 lignes, tête
  `87bd314d78a68c11398b223bb0c4bcd427879fc5fd6f3bd47d92e3b858f36cec` ;
  critique 1 ligne, tête
  `df7b175a0a542a2355a950fef380cfd1eb3d2656346e4a1de144fd43a71a680f`.

## Contenu du run (`usdc-2023-03_live_20261017T013034Z/`)

- `journal_orchestrator.jsonl` / `journal_critic.jsonl` — journaux append-only chaînés SHA-256.
- `run.json` / `run_outcome.json` / `outcome_orchestrator.json` — spécification, bilan, sortie.
- `exchanges/` — paquet de preuves envoyé au critique (`001_evidence_packet.json`) + son
  rapport (`002_critique_report.json`, 8 objections).
- `store_live/` — **enregistrement scellé** : `calls.jsonl` (rôle, version de prompt,
  modèle épinglé, hashes prompt/réponse, tokens, latence, coût) + `blobs/`
  (enveloppes prompt/réponse adressées par hash SHA-256).

## Rejouabilité (honnête)

Le rejeu **bit-à-bit** (`REPLAY-JOURNAL`, k=10 identique) s'applique à la session
**scriptée** (`fixtures/agents/store_usdc-2023-03`) : ses payloads sont déterministes.
Une session **live** embarque dans ses prompts les compteurs dépensés (temps réel,
coût) — variables par construction ; son rejeu se fait en mode **REPLAY-ARCHIVE**
(`python run_replay.py archive --case usdc-2023-03 --k 3`), c'est-à-dire un
**recalcul** sur les mêmes entrées. `store_live/` est la **preuve** de ce qui a été
demandé et répondu, re-vérifiable par hash hors-ligne.

## Contexte d'itération (visible dans git)

Les deux premières passes live ont été **aborties fail-closed** (`ARRET-3`) :
l'orchestrateur live confondait le schéma du plan et celui de l'évaluation
(le prompt système disait « toujours le schéma ci-dessous »). Correctif :
prompt `orch-p1.0.0` → **`orch-p1.1.0`** (« deux étapes, deux sorties ») +
consigne d'évaluation explicite (forme JSON exacte) + re-prompt transmettant la
sortie précédente ; magasin scripté **re-seedé** et dossier de rejeu **régénéré**
(re-scellement visible — jamais un patch silencieux).
