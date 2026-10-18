# Revue de code et chasse aux bugs — ORVYREN-Core (17/10/2026)

**Statut** : revue interne, post-fusion de la branche Mimo.
**Périmètre** : 185 fichiers Python (~57 000 lignes avec les tests), plus YAML/TOML/HTML/CI.

## 1. Fusion Mimo

La branche `feat/10h-agents-ui` contenait **15 commits de corrections** absents de `master`
(85 fichiers, 3 329 insertions, 379 suppressions). Fusion `--no-ff` : `d92b943`.
Après fusion : **1 061 passed, 3 skipped**.

## 2. Méthode

- `ruff check .` avec le gate du dépôt (`E9,F63,F7,F82`) : **pass**.
- `python -m compileall` : **pass**.
- `pytest` : **1 069 passed, 3 skipped, 274 subtests**.
- `mypy src/orvyren` : 69 signalements, principalement des annotations `Optional`/types ; les cas à impact runtime ont été corrigés.
- `bandit -r src scripts` : 49 signalements low/medium, 0 high ; les traversées de chemins et les schémas d’URL ont été corrigés, le reste est trié (SQL construit sur des constantes, faux positifs de mots de passe, bind d’affichage).
- `yamllint` : YAML syntaxiquement valide ; warnings de longueur/document-start uniquement.
- `tomllib` : `pyproject.toml` valide.
- `sha256sum -c` sur `evidence/demo_chain/rseth/MANIFEST.sha256` : aucun échec.
- `verify_frozen.py` : **COMPLIANT**.
- Revue indépendante des tests : 50 fichiers A–G et 17 fichiers H–Z lus individuellement ; les défauts de tests tautologiques trouvés ont été corrigés.

## 3. Bugs corrigés

| Bug | Correction | Commit |
|---|---|---|
| Zip-slip et liens symboliques dans les paquets d’audit | extraction avec `safe_join`, refus des membres hors racine, limite 512 MiB | `e4b13d9` |
| Chemins `../`/absolus lus depuis le manifeste du vérificateur | `safe_join` sur A1–A8 et C2 | `e4b13d9`, `e58655d` |
| Timestamp d’ingestion fabriqué avec l’horloge murale | échec explicite si le timestamp de bloc manque ou est nul | `23cc106` |
| Métadonnées de réserve inconnues inventées (`UNKNOWN`, 18 décimales) | échec explicite si `symbol()`/`decimals()` ne répondent pas | `c4dcd84` |
| Outcome écrit avant `resolve_not_before` | garde dans `append_outcome` + test de refus | `babf907` |
| G5 devenu incohérent après modification de `outcomes.py` | re-scellement explicite de G5/outcomes ; rebuild identique | `babf907` |
| Backfill structurel sans événement timestampé | refus explicite au lieu d’un ancrage à 1970 | `b47249a` |
| Endpoint LLM non HTTP(S) | refus avant `urlopen` | `bd11822` |
| RPC d’exécution/vérification non HTTP(S) | refus dans `execution.chain`, `data.rpc` et `verify.engine` | `faa9d16`, `98f8af8`, `6e58b76` |
| `series_from_episode` sur un JSON non-objet | `CorpusError` explicite | `faa9d16` |
| Tests tautologiques (empreinte, fuseau, outcome) | assertions indépendantes | `b994970` |
| Test de pureté de la politique limité à deux fichiers | scan AST de tous les modules `policy/` avec allow-list stdlib | `673c84c` |
| Provenance des claims `run_quality` non déterministe si le manifeste corpus manque | refus explicite, plus de fallback sur l’horloge murale | `d80911c` |
| Encodage des sous-processus du pipeline dépendant de la console Windows | capture UTF-8 avec `errors="replace"` | `d80911c` |
| `--case` pouvait sortir du répertoire de preuve/fixtures | token de cas fichiers-safe dans `run_decision` et `run_agents` | `d80911c`, `3128f9c` |
| Cas `null`/non-liste dans `run_pipeline` | normalisation `cases or []` | `d80911c` |
| Évidence partielle non-objet dans `load_partial` | rejet explicite, pas de `.get` sur une liste | `c2d1f83` |
| `run_drift_check` D8 plantait si `max_calls_24h` manquait | garde de type → `DRIFT`, plus de crash | `c2d1f83` |
| `run_drift_check` D2 plantait sur un fixture incomplet | `KeyError`/`TypeError` → `UNVERIFIED` | `c2d1f83` |
| Clé répétée vide dans `inspect_env_masked` masquait une clé présente | conserve la longueur maximale | `c2d1f83` |
| BlockIndex `usdc` supposait `timestamp` toujours présent | timestamp invalide → `None` explicite | `c2d1f83` |
| Cache rsETH avec entrée non-dict | entrée ignorée, pas de crash | `c2d1f83` |
| `urlopen` sur URL non HTTP(S) dans les reconstructeurs | schéma validé avant appel | `c2d1f83` |
| `adr_index --write` tronquait les sections README après `## Registre` | remplacement limité à la section, tail préservé + test | `f50dc8b` |
| Signer : `chainId` non entier ou clé rejetée par `eth-account` provoquait un crash | erreurs converties en `SignerError`, aucun matériau de clé affiché | `f50dc8b` |
| `verify_receipt` : `amount_base_units` absent → `TypeError` non géré | refus `ValueError` explicite | `f50dc8b` |
| `generate_signer_key` : ligne de clé manquante écrite sans `=` | clé explicite passée à `_assign` + test | `f50dc8b` |
| `common.write_json` et rapport demo écrivaient du JSON en CRLF sous Windows | `newline="\n"` explicite | `f50dc8b` |
| `export_graph_snapshot` / seed agents : `--case` pouvait sortir du dossier | token fichiers-safe | `f50dc8b` |
| API graphe : chemin SQLite avec `?`/`#`/espaces mal encodé dans l’URI read-only | URI construite avec `os.path.abspath` + `urllib.parse.quote` | `dea7f44` |
| Q7 graphe : un `supply_cap` négatif produisait un ratio négatif | cap non positif → ratio `None` | `dea7f44` |
| Axe épistémique : toutes hypothèses `REFUTED` donnait `INCONCLUSIVE` | décidable si chaque hypothèse est `SUPPORTED` ou `REFUTED` | `d761f4c` |
| `load_policy` : champs numériques/listes mal typés provoquaient un traceback | validation explicite → `MiniYamlError` | `d761f4c` |

## 4. Limites de la revue

- Les passes indépendantes sur `agents`, `graph`, `decision/policy`, `execution` et la première moitié de `scripts` ont échoué côté fournisseur LLM ; `execution/verify/audit/replay`, `runners/UI` et la seconde moitié de `scripts` ont été relus et corrigés manuellement, les autres restent couverts par les contrôles statiques et les tests, pas par une lecture ligne-à-ligne revendiquée.
- Les 69 erreurs mypy restantes sont majoritairement des annotations, pas des crashes observés ; elles sont listées comme dette de typage.
- `ruff format --check` signale 171 fichiers : le `pyproject.toml` interdit le reformatage massif de la baseline gelée ; aucun reformatage global n’a été appliqué.
- Les findings Bandit restants sont des faux positifs à faible risque ou des SQL construits uniquement à partir de constantes et de placeholders.
- Les limites produit restent celles du rapport 10 h : **EVAL N=0**, **Q8 NOT_INGESTED**, `LIQUIDATED_IN` sans occurrence, Q2 sans arête dans le slice Aave, pas de 10⁵ événements.

## 5. État git

- `master` local : voir `git log -1` ; `origin/master` est mis à jour après chaque lot.
- `verify_frozen.py` : **COMPLIANT**.
- Dernière suite complète : **1 069 passed, 3 skipped**.
