# ORVYREN — Registre détaillé des écarts (rapports de revue du 2026-10-18)

**Périmètre de ce fichier.** Consolidation **fidèle** de chaque entrée « non
corrigé » des quatre rapports de revue du 2026-10-18 — aucune synthèse
approximative : chaque ligne du tableau ci-dessous est une entrée du rapport
cité (fichier:ligne repris tels quels quand le rapport les donne), avec sa
raison de report et son renvoi précis dans le rapport d'origine.

| Rapport source | Section reprise |
|---|---|
| `D:/orvyren_work_2026-10-18/review/agents_chain.md` | §2 « Non corrigé (raisons) » — N1…N11 |
| `D:/orvyren_work_2026-10-18/review/api_frontend.md` | « Non corrigé (décisions assumées / hors périmètre) » — 1…11 |
| `D:/orvyren_work_2026-10-18/review/graph_eval_bench.md` | « Non corrigé (avec raisons) » — 1…9 |
| `D:/orvyren_work_2026-10-18/review/test_harness.md` | §5 « Non corrigé » — 5.1, 5.2 (+ note « Non corrigé ici » du §2) |

Les numéros **G-x** renvoient au registre de périmètre
`docs/SUBMISSION_SCOPE_AND_GAPS.md` (croisements indicatifs). Les deux
tautologies de tests gelés (TH-1/TH-2) ont leurs correctifs **prêts** dans
`review/test_harness.md` §5.1 ; la procédure de re-scellement visible est
indexée dans `frozen/INDEX.md` §3.

## Tableau unique des écarts

| id | fichier:ligne | écart | raison du report | artefact (rapport de revue §) | croisement G-x |
|---|---|---|---|---|---|
| AC-N1 | `src/orvyren/agents/worker.py` (`run_critic`) | Provenance P0-6 des findings du critique **non couverte** : les `refs` du rapport `orvyren/crit/v1` ne sont pas comparées aux refs observées | BLOQUANT : (a) le prompt système gelé (`prompts.py`, hash de rejeu) invite à citer `observation:… \| claim:… \| hypothesis:…` — une porte stricte sur les refs du paquet donnerait des faux refus sur `claim:`/`hypothesis:` ; (b) le magasin enregistré `store_usdc-2023-03` cite `observation:defillama/usdc-usd/2023-03-11T12:00Z`, absente de son paquet — toute porte stricte rejetterait la critique ENREGISTRÉE et casserait le rejeu (`test_agents_mab` exige `verdict_lecture == "FRAGILE"` + têtes de chaîne stables k=10) ; magasins enregistrés = report-only. À traiter en re-scelant une nouvelle graine avec critique conforme | agents_chain.md §2 N1 | G-6 |
| AC-N2 | `src/orvyren/agents/worker.py` (`run_critic`) | Namespaces `claim:` / `hypothesis:` du critique non résolus | Contrat de refs du critique à définir (avec N1) avant toute validation — contrat posé par `docs/decisions/ADR-0004-references-critique-namespaces.md`, porte critique REPORTÉE | agents_chain.md §2 N2 | G-6 |
| AC-N3 | `src/orvyren/agents/prompts.py` (gelé) | Écart de forme de budget : `appels_llm_restants` côté prompt vs `budget_restant` / `llm_calls` côté payload | Report-only (« à aligner avant de changer le hash ») — prompt gelé = hash de rejeu | agents_chain.md §2 N3 | — |
| AC-N4 | `src/orvyren/agents/graph_tools.py` (`GraphQueryTool`) | `limit`/`max_depth` acceptés pour toutes les requêtes mais ne transmis qu'à Q4/Q1 : argument sans effet accepté sans refus visible | Contrat actuel (« cadrage optionnel ») ; non modifié pour ne pas toucher les specs d'outils enregistrés ; à trancher dans le spec | agents_chain.md §2 N4 | — |
| AC-N5 | `src/orvyren/agents/journal.py` (`AgentJournal.append_dict`) | Un mapping amputé d'un champ requis lève `TypeError` (construction `JournalEntry(**payload)`) au lieu d'une ligne REJECTED visible | Les seuls appelants (loop, `journal_write`, worker) fournissent tous les champs ; la sémantique du journal figé n'a pas été modifiée | agents_chain.md §2 N5 | — |
| AC-N6 | `src/orvyren/agents/loop.py` (`deterministic_validator`) | Ne type pas `refs` (dict/liste acceptés muettement) | Comportement inchangé : le typage est désormais refusé en amont dans l'ACH (fixes R1–R3) | agents_chain.md §2 N6 | — |
| AC-N7 | `run_agents.py` (spawn worker, `_spawn`) | Timeout worker = kill du processus (`subprocess.run(timeout=…)`, rc 124) | Sémantique voulue (« un worker bloqué est un worker échoué »), déjà fail-closed ; seul le plafond incohérent était un bug (corrigé A4) ; un tueur plus doux (terminaison gracieuse) = ajout de conception, hors périmètre « corrections minimales » | agents_chain.md §2 N7 | — |
| AC-N8 | `scripts/run_scenario_rseth.py` (`collect_artifacts`, `agents_run_dir=""`) | Joindrait `run.json` relatif au cwd (cas limite si l'étape agents n'a rien produit mais que la collecte tourne) | Chemin mort dans le pipeline nominal (l'étape agents précède toujours la collecte) — noté | agents_chain.md §2 N8 | — |
| AC-N9 | `scripts/run_scenario_rseth.py` | Flux stdout/stderr intégrés **sans borne** à `scenario_run.json` | Choix assumé (« a swallowed stderr is a blind spot ») ; taille non bornée sur très grosses sorties, noté | agents_chain.md §2 N9 | — |
| AC-N10 | `tests/*.py` (fichiers de tests de harnais existants) | Non touchés (interdits, autres agents) ; les findings P2 de la revue précédente (tautologies, fuites de répertoires temporaires, fichiers non fermés, skips silencieux) restent ouverts de leur côté | Responsabilité de leurs relecteurs ; aucun faux test supplémentaire constaté dans le périmètre de cette revue — état croisé : TH-1…TH-5 | agents_chain.md §2 N10 | G-5 |
| AC-N11 | `src/orvyren/agents/tools.py` (`JournalWriteTool` hors boucle) | Un appel `journal_write` standalone peut toujours épingler les colonnes LLM | La réservation (fix L1) est portée par la boucle, seul chemin d'exécution de production ; le seeding scripté passe par la même boucle, donc le contrat de rejeu est préservé | agents_chain.md §2 N11 | — |
| AF-1 | `src/orvyren/api/artifacts.py:419` (`_iso`) | Un horodatage présent mais illisible dégrade toujours en `0` (point à l'epoch) au lieu de lever | Lever une exception ferait échouer toute la série pour un seul point exotique ; comportement documenté dans la docstring ; modifier ce compromis = décision produit | api_frontend.md « Non corrigé » 1 | — |
| AF-2 | `src/orvyren/api/artifacts.py` (`build_run_events`) | Trie les lignes de journal par la chaîne `ts_utc` (tri lexicographique) | Les artefacts produits sont en UTC homogène (`…Z`) où ce tri est correct ; convertir chaque ligne en datetime changerait l'ordre à ts égal (clé secondaire déjà présente) sans bénéfice mesuré | api_frontend.md « Non corrigé » 2 | — |
| AF-3 | `src/orvyren/api/graph_service.py` (`full`) | Ne filtre pas la « révision courante » des relations (PIT) : vue brute de la table, contrairement à q1–q8 qui passent par `graph/api` (contrat de lecture gelé) | Dédupliquer changerait `counts["edges"]`, contrat de test (`test_api_artifacts` compare aux compteurs de la table) ; décision laissée au propriétaire du schéma ; le frontend ne plante plus sur les doublons (fix 18) | api_frontend.md « Non corrigé » 3 | — |
| AF-4 | `src/orvyren/api/artifacts.py:42` (`_JSON_CACHE`) | Cache mtime **non borné**, effet de bord global | Assumé (« the graph payload is heavy ») ; aucune mutation des objets cachés observée sur les chemins de lecture ; invalidation = changement de mtime ; laissé en l'état | api_frontend.md « Non corrigé » 4 | — |
| AF-5 | `src/orvyren/api/graph_service.py:285-291` (`node_detail`) | Au plus 200 relations transportées, **pas de pagination REST** des relations (le compte est désormais honnête : `relation_count` + `relations_truncated`) | Évolution d'API, pas un bug | api_frontend.md « Non corrigé » 5 | — |
| AF-6 | `src/orvyren/api/routes.py` (`after_seq`) | Sémantique hétérogène : inclusive (`>=`) côté journal/événements de run, exclusive (`>`) côté flux d'audit | Épinglé par les tests existants et la pagination de l'UI ; harmoniser casserait les deux | api_frontend.md « Non corrigé » 6 | — |
| AF-7 | `src/orvyren/graph/api.py` (`dependency_paths` ; hors périmètre de la revue) | Réécrit `max_depth=0` en 1 silencieusement (clamp `max(1, …)`) — contraire à la convention P1-1 « 0 reste légal » ; Q8 ne résolve pas encore les allowances | Module de contrat hors périmètre ; trou à remonter au propriétaire `src/orvyren/graph/**` | api_frontend.md « Non corrigé » 7 | G-4 (Q8) |
| AF-8 | `frontend/src/lib/format.ts` (`fr-FR`) + labels du SPA | SPA React **en français** alors que l'UI stdlib 12 écrans est en anglais | Cohérent en interne, mais l'écart est un choix produit (concours en anglais) ; non traduit ici pour ne pas mélanger i18n et chasse aux bugs | api_frontend.md « Non corrigé » 8 | — |
| AF-9 | périmètres `src/orvyren/agents/`, `src/orvyren/evaluation/` | Findings P1 ouverts de `docs/CODE_REVIEW_SUBAGENTS_2026-10-18.md` non traités par cette revue (refs des claims vs ledger P0-6, `deadline_s` des outils agents, prompt budget, embargo calibration…) | Hors périmètre : ce sont les paquets `agents/` et `evaluation/` — voir AC-N1/AC-N3, GE-8 | api_frontend.md « Non corrigé » 9 | G-6 |
| AF-10 | `frontend/` (pas de testeur JS) | Aucun test JS : build = `tsc` + `vite build` ; les correctifs 17–20 ne sont couverts que par le build vert + l'analyse (seul le 21 a un test serveur dédié) | Ajouter Vitest = nouvelle dépendance (interdite par la consigne de revue) | api_frontend.md « Non corrigé » 10 | — |
| AF-11 | `src/orvyren/api/live.py` (`producer_loop`) | Le hub reboucle le run enregistré (position remise à 0) | Comportement démo assumé par le docstring ; l'UI déduplique désormais côté client (fix 19) au lieu d'afficher des doublons | api_frontend.md « Non corrigé » 11 | — |
| GE-1 | `src/orvyren/graph/queries.py:326-329` (Q7, `debt_backed`) | `debt_backed` somme **TOUS** les `OWES` visibles, sans filtre par actif (alors que `api.concentration` borne `OWES` sur `dst = asset`) ; sur la fixture rsETH le seul `OWES` (`rseth-owes-weth-borrowed`) donne 190 000 000 | Valeur **épinglée** par le contrat fixture `tests/test_graph_queries.py:324` (test interdit de modification) : corriger le filtre casserait le contrat gelé de la figure publiée ; l'arbitrage sémantique (quelle dette « backed by asset » ?) appartient aux propriétaires du contrat Q7 ; écart documenté entre les deux implémentations de Q7 | graph_eval_bench.md « Non corrigé » 1 | G-8, G-15 |
| GE-2 | `src/orvyren/evaluation/comparators.py:120` (`a1_signal_times`) | Ne se déclenche qu'à `len(run) == 2` : sur une grille plus fine que 15 min, une séquence ≥ 2 observations qui atteint `span ≥ 15 min` au bout de la 3e lecture **ne déclenche jamais** | Règle documentée comme dégénérescence « grille horaire » ; module gelé par hash G2 ⇒ report-only | graph_eval_bench.md « Non corrigé » 2 | G-8 |
| GE-3 | `src/orvyren/evaluation/comparators.py`, `src/orvyren/evaluation/windows.py`, `tests/test_evaluation_{loss,comparators,calibration}.py` | Gel G2/G3 : tout correctif de ces fichiers rend `verify_frozen.py` NON COMPLIANT (recalc byte-identical) et bloque les runs d'évaluation (porte de gel) | `frozen/` (re-scellement) hors fichiers autorisés pour la mission de revue ; report-only — procédure de re-scellement visible : `frozen/INDEX.md` §3 | graph_eval_bench.md « Non corrigé » 3 | G-5 |
| GE-4 | `src/orvyren/graph/queries.py:303` (`hashes_complete`) | Drapeau **structurellement `True`** : `fingerprint()` est recalculé à la volée et toujours non vide, le drapeau ne peut pas être faux | Pour être vérifiable il faudrait une empreinte stockée à comparer ; changement de contrat d'export hors « fix minimal » ; affirmation faible, pas fausse (« chaque hop porte une empreinte ») | graph_eval_bench.md « Non corrigé » 4 | — |
| GE-5 | `src/orvyren/graph/api.py` (`_current` appelée entre `_connect` et le `try/finally` de `exposure`/`dependency_paths`/`pit`/`concentration`/`permissions`/`snapshot`) ; `src/orvyren/graph/store.py:359-364` (`GraphStore.__init__`) | Fuites théoriques de connexion sqlite sur chemins d'erreur rares (connexion ouverte jusqu'au GC ; `__init__` laisse la connexion ouverte si `_init_schema` lève `E_SCHEMA_TOO_NEW`) | Impact négligeable (GC CPython referme) ; correctif = churn sur 7 fonctions sans effet fonctionnel — non fait par discipline de changement minimal | graph_eval_bench.md « Non corrigé » 5 | — |
| GE-6 | `run_calibration.py:54-56` vs `src/orvyren/evaluation/windows.py` (`sha256_file`) vs `src/orvyren/replay/corpus.py:43` | Convention de hash **hétérogène mais déclarée** : octets bruts (`forecasts_file`, `outcomes_file`, `scoring_code`) vs normalisation CRLF→LF (convention des manifestes Gx) vs « raw bytes » explicites | Avec `.gitattributes eol=lf` les deux coïncident en pratique ; harmoniser changerait les valeurs publiées du rapport sans bénéfice mesuré — noté | graph_eval_bench.md « Non corrigé » 6 | — |
| GE-7 | `src/orvyren/graph/api.py` (`pit`, `timeline` — `limit`) | `limit` non borné côté API (`LIMIT -1` = illimité) | La règle P1-1 (bornage `limit`/`max_depth`/`deadline_s`) vit dans la couche outils agents (`src/orvyren/agents/`), hors périmètre de cette revue ; les outils bornent avant d'appeler l'API (revue agents du 18/10) | graph_eval_bench.md « Non corrigé » 7 | — |
| GE-8 | `evidence/evaluation/` (état EVAL) | 1re passe EVAL gate **N=0**, `eval_run.lock` brûlé ; aucune supériorité mesurable ; séries EVAL non assemblées | État connu, inchangé : choix de collecte, pas un bug de code | graph_eval_bench.md « Non corrigé » 8 | G-1 |
| GE-9 | `tests/test_evaluation_harness.py` (fuites de répertoires temporaires) ; `tests/test_evaluation_report.py`, `tests/test_graph_export.py` (fichiers non fermés) ; `tests/test_evaluation_calibration.py:97`, `tests/test_evaluation_loss.py:106` (tautologies) | Findings de harnais de tests (P2 du compte rendu du 18/10) non corrigés dans cette passe : tests existants hors fichiers autorisés ; les deux tautologies sont en plus gelées côté code | Aucun n'est un bug de production ; listés pour ne pas les présenter comme traités. État croisé : la passe harnais du 18/10 (test_harness.md §2–§3) a corrigé les fuites de `mkdtemp` et les fichiers non fermés ; **restent** les deux tautologies (TH-1/TH-2) | graph_eval_bench.md « Non corrigé » 9 | G-5 |
| TH-1 | `tests/test_evaluation_loss.py:106` | Tautologie : `assertAlmostEqual(20.0 - 10.0, 100.0 * (1.0 - 0.90))` compare deux constantes (toujours vrai) | **CORRIGÉ + RE-SCÉLÉ le 2026-10-18** (re-scellement visible G1 : écart mesuré depuis les deux pertes du test, `keep_loss - sell_loss == q · (1 - p_terminal)` dérivé des paramètres ; empreintes recalculées via `freeze_sprint0.py`, `verify_frozen.py` COMPLIANT, suite verte — commit dédié de l'orchestrateur) | test_harness.md §5.1 | G-5 (clos) |
| TH-2 | `tests/test_evaluation_calibration.py:97` | Tautologie : `assertLess(mcnemar_exact(5, 1), mcnemar_exact(4, 2) + 1.0)` — le `+ 1.0` rend l'inégalité toujours vraie | **CORRIGÉ + RE-SCÉLÉ le 2026-10-18** (re-scellement visible G5 : monotonie stricte `(6,0) < (5,1) < (4,2)`, mesurée 0,03125 < 0,21875 < 0,6875 ; empreintes recalculées, `verify_frozen.py` COMPLIANT, suite verte — commit dédié) | test_harness.md §5.1 | G-5 (clos) |
| TH-3 | `tests/test_integrity_reproducibility.py:86, 126, 179, 227` | Ouvertures non fermées (`json.load(open(…))`, `open(…).read()`) | Fichier non nommé dans les findings P2, donc laissé intact ; à signaler au propriétaire | test_harness.md §5.2 | — |
| TH-4 | `tests/test_api_review_fixes.py` (non suivi, agent parallèle api/frontend) | WIP en évolution (24 `def test_` ; run isolé bloqué > 120 s pendant la passe) | Appartient à l'agent api/frontend ; non touché | test_harness.md §5.2 | — |
| TH-5 | `tests/test_evaluation_protocol.py`, `tests/test_agents_tool_modes.py`, `tests/test_audit.py`, `tests/test_benchmark_ab.py`, `tests/test_chain_run_id.py`, `tests/test_demo_kit.py`, `tests/test_scenario_rseth.py`, `tests/test_run_agents_cli.py`, `tests/test_agents_review.py` (`mkdtemp`) | Fuites de répertoires temporaires éventuelles — **non traitées** dans la passe harnais | Hors périmètre nommé par les findings P2 ; déjà pourvus de nettoyage (`addCleanup`/`tearDown`) ou hors liste — vérifiés, non touchés | test_harness.md §2 (note « Non corrigé ici ») | — |

## Annexes — écarts constatés hors revues (passe gouvernance du 2026-10-18)

Ces trois points ne viennent pas des quatre rapports ; ils sont listés ici pour
ne pas être perdus (détail et arbitrage dans le compte rendu de la passe) :

* **F-1 — `fixtures/benchmark/cases.json` (case `placebo-calm-2023-03`) :
  notes périmées.** `a2_availability_note` (« the A2 leg is EXPECTED to fail
  with E_CASE_UNKNOWN »), `expect_agents_note` (« the A2 leg is not
  executable ») et `a2_store: null` ne sont plus vrais depuis la graine
  scriptée du case (`fixtures/agents/store_placebo-calm-2023-03`, `SEED.json`
  = `scripted-demo`). `evidence/benchmark_ab/report.md` rend ces notes telles
  quelles : la ligne « declared agent expectation » du cas placebo contredit la
  ligne mesurée du même rapport. Fichier hors contrat de fichiers de la passe →
  rafraîchissement à la charge du propriétaire (avec l'étiquette d'origine
  scriptée).
* **F-2 — colonne « claims rejected (provenance) » du rapport de benchmark.**
  Elle compte les entrées `validation.provenance_ok == False`
  (`evaluation/bench.count_provenance_rejections`) ; or les refus
  `E_REF_NOT_OBSERVED` portent `status: REJECTED` avec `provenance_ok: true`
  (le motif nomme la porte) : la colonne affiche 0 alors que les journaux du
  placebo montrent **2 claims rejetés par jambe A2**. Arbitrage propriétaire :
  compter aussi `status == "REJECTED"` ou renommer la colonne
  (`bench.py` hors contrat de la passe).
* **F-3 — `frozen/` est un inventaire recalculé intégralement.** Tout fichier
  étranger ajouté à `frozen/` est signalé par `scripts/verify_frozen.py`
  (`recalc: mismatches […]`) et par
  `tests/test_evaluation_forecasts.py::test_recalcul_hors_ligne_identique`
  (`not rebuilt`) — mesuré avant que `frozen/INDEX.md` ne soit produit par le
  générateur lui-même (`scripts/freeze_sprint0.build_all`, ajout additif) ;
  voir `frozen/INDEX.md` §4. Conséquence : un index du gel ne peut pas vivre
  dans `frozen/` comme fichier à part.

---

Le registre de périmètre `docs/SUBMISSION_SCOPE_AND_GAPS.md` est l'autorité ;
ce fichier est la liste détaillée des écarts techniques.
