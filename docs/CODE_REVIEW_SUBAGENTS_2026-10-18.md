# Revue indépendante par dossier — 2026-10-18

Six relectures indépendantes ont couvert les paquets restants, en lecture seule,
fichier par fichier. Ce document consigne ce qui a été **corrigé et vérifié**
dans cette passe, puis les findings **laissés ouverts** pour ne pas les
présenter comme traités.

## Périmètre lu

| Paquet | Fichiers | Lignes | Tests ciblés |
|---|---:|---:|---:|
| `agents` | 12 | 4 614 | 199 |
| `graph` | 10 | 3 159 | 117 |
| `decision` | 11 | 3 025 | 60 |
| `policy` | 2 | 816 | 67 |
| `data` + `quality` | 8 | 1 900 | 70 |
| `evaluation` | 9 | 2 710 | 82 |
| **Total** | **52** | **16 224** | **595** |

Les rapports de tests A–G et H–Z ont également été relus ; leurs findings de
harnais (tautologies, fuites de répertoires, fichiers non fermés) ne sont pas
des bugs de production et restent listés en §3.

## Corrections intégrées

### Agents

- `_llm_fields` conserve la provenance `llm` sur **toutes** les lignes LLM :
  les claims 2..n ne pèsent plus 1,0 (B3 R1).
- `journal_write` : les champs réservés (`run_id`, `episode_id`, `agent_id`,
  `role_version`, `step_index`, `ts_utc`, `journal_id`) sont liés par la boucle,
  jamais par le modèle ; seuls `REFLECTION` / `OBSERVATION_REF` sont acceptés.
- Budget : `NaN`, `inf`, négatif ou au-dessus du plafond gelé refusés.
- `wrap_untrusted` neutralise les délimiteurs présents dans le contenu et la
  regex anglaise exige `previous|prior` + espace + `instructions`.
- Usage fournisseur mal formé → `E_LLM_BAD_USAGE` (plus de crash).
- `ResponseStore` : hash validé à la lecture, hash de blob validé dans le
  chemin, écriture tmp + `os.replace`, `verify()` vérifie que chaque appel a
  bien ses blobs.
- Mémoire : identifiant suffixé par le digest en cas de collision de `call_id`.
- `compute_signal` refuse `None`, `""` et les booléens, mais accepte `0`.
- Critique `QUARANTINED` → `REQUIRE_APPROVAL` et outcome `inconclusive`.

### Graphe

- PIT : la révision courante est calculée parmi les révisions publiées
  (`inserted_at`) avant `as_of`, sur Q1/Q2/Q4/Q5/Q7/Q8/snapshot.
- Q7 : `COLLATERALIZES` est filtré sur `src` (l'actif), `OWES` sur `dst` (la
  dette) ; le regroupement renvoie la contrepartie correcte.
- Snapshot : le hash couvre désormais le payload et les autres colonnes
  métier, pas seulement `(relation_id, revision, kind, src, dst)`.
- `SUPPORTS`/`REFUTES` : constante en majuscules, lecture insensible à la casse
  pour compatibilité avec l'ancien writer.
- Refs d'arête vides refusées ; `inserted_at` futur ne fausse plus le PIT.
- `insert_decision_node` sérialise le payload avec `sort_keys`; un schéma futur
  (`schema_version > 3`) est refusé au lieu d'être ouvert silencieusement.

### Décision / policy

- Déduplication des refs non hashables (listes) : plus de `TypeError` sur le
  flag `duplicate_conflicting_observation`.
- Le dossier reprend les `final_verdicts` du RDOF ; A1/A2/A3/A5 forcent
  `INCONCLUSIVE` et suppriment l'action économique sur preuve incomplète.
- H1 : exactement une venue en alerte, même venue pour la recovery, tolérance
  agrégateur bilatérale et évaluée au voisinage de l'alerte.
- H2 : la baisse de supply doit être temporellement liée aux heures d'alerte.
- RDOF : une classe d'effet n'est `available` que si l'injection produit
  réellement cette classe ; l'invariant c1 exige toutes les classes.
- Horodatage policy : `window_end` (chaîne ISO) est converti en `datetime`
  avant `evaluate`, ce qui restaure `run_executor`.
- Policy : P11 exige de vrais booléens ; entiers/chaines/adresses validés ;
  `transfer` doit cibler `intent.asset`.

### Data / quality

- Freeze Aave : la recherche doit converger (`high - low == 1`) avant de
  déclarer la transition ; une sonde transitoire ne fabrique plus une date.
- `encode_int` refuse `2**255` (borne int256 positive).
- `HttpTransport` conserve la query string et refuse les credentials dans
  l'URL ; `get_code(null) == "0x"`, `eth_call(null)` échoue explicitement.
- `RpcRangeError` n'est levé que pour une vraie erreur de plage.
- `ArchiveRpc(urls="...")` ne découpe plus la chaîne caractère par caractère ;
  une liste vide est une erreur ; `repr` masque les endpoints.
- `time_grid` refuse un pas non entier (plus de boucle infinie).
- Corpus : venue inconnue, BOM UTF-8, colonnes manquantes et unités inconnues
  sont refusés ; `steth_discount_ladder` matérialise `sizes` une seule fois.

### Évaluation

- `R⁻`/`R⁺` sont calculés contre A0 comme le demande G1, pas comme
  `max/min` du regret oracle.
- EVAL exige un `lock_path`; un run à `N=0` ne brûle plus le jeu.
- Les outcomes portent une `signature` auto-portée ; la chaîne et la
  modification du dernier enregistrement sont détectées.
- `forecast_hash` 64-hex et `t_resolution_window_utc` obligatoires.
- La mention de réexécution forcée est rendue dans le Markdown.
- G5 a été re-scellé après modification de `outcomes.py` ; le paquet gelé est
  **COMPLIANT** et se reconstruit à l'identique.

## Findings ouverts (non revendiqués comme corrigés)

### P1 — à traiter avant la soumission si le temps le permet

- **Agents** : les refs d'un claim ne sont toujours pas comparées à l'ensemble
  des refs réellement observées ; un claim peut citer une ref inventée.
- **Agents** : `deadline_s` des tools graphe est accepté mais non appliqué ;
  `limit=-1` / `max_depth` ne sont pas bornés côté outil.
- **Agents** : le prompt système annonce une forme de budget (`appels_llm_restants`)
  différente du payload (`llm_calls`) ; à aligner avant de changer le hash.
- **Graphe** : Q8 ne résout pas encore les allowances des rôles du sujet ;
  les comparaisons de timestamps restent lexicographiques sur des offsets
  non-UTC.
- **Graphe** : Q5 `as_of` filtre `event_time`, pas `observation_time`.
- **Policy** : `state=None` laisse P7/P11/P12/P14 en `SKIPPED` (legacy) ;
  le chemin exécuteur fournit l'état, mais l'API publique reste permissive.
- **Évaluation** : la cascade G5 (bootstrap/ECE/BSS selon N) est appliquée au
  libellé, pas au contenu ; le gate de gel ne vérifie pas les hashes de code
  inscrits dans les documents Gx.
- **Évaluation** : l'embargo de calibration reste opt-in si
  `--calibration-periods` est omis.

### P2 — qualité de harnais de tests

- Tautologies : `test_evaluation_calibration.py:97` (`+1.0`), `test_evaluation_loss.py:106`
  (constante), `test_evaluation_review.py:73` (offset identité),
  `test_agents_e2e.py:175` (objet jamais branché), `test_quality_graph.py:452`
  (empreinte comparée à elle-même).
- Fuites de répertoires temporaires : `test_agents_toolcall`, `test_agents_graph_tools`,
  `test_agents_e2e`, `test_evaluation_harness`, `test_ui_review`,
  `test_ui_panels`, `test_replay_determinism`.
- Fichiers non fermés : `test_evaluation_report`, `test_graph_export`,
  `test_agents_mab`, `test_demo_kit`, `test_policy*`.
- Skips silencieux : `test_agents_mab` (store scripté), `test_data_layer`
  (`load_fixture`), `test_agents_tools` (`run_inputs.json`).

### P3 — limites assumées

- Pas de reformatage `ruff format` massif (171 fichiers) : baseline gelée.
- `mypy` n'est pas propre (annotations `Optional` héritées) ; les cas à impact
  runtime connus ont été corrigés.
- Q8 reste `NOT_INGESTED` sur le slice Aave ; Q2 reste `OK / 0 chemin`.
- EVAL N=0 : aucun gain de décision mesuré ; les séries EVAL manquent.

## Vérifications de cette passe

```text
pytest -q                         1073 passed, 3 skipped, 274 subtests
ruff check .                      All checks passed
compileall src scripts tests      rc 0
verify_frozen.py                  COMPLIANT (recalc byte-identical)
```

Commits de la passe : `36ebeeb` (agents), `6d18f65` (graphe),
`c50e270` (décision/policy), `9236ef7` (data/quality),
`a8c1064` (évaluation + G5).
