# ORVYREN — PLAN D'IMPLÉMENTATION (document 4/4)

**Version 1 — 15 octobre 2026 · dépôt `D:\orvyren_core` · branche d'intégration `master`**
**Autorité : `FREEZE_V2.md`** — les valeurs sont gelées là-bas ; ce document ne gèle rien, il dit **qui fait quoi, dans quel ordre, avec quelles interfaces et quelle définition de « terminé »**.
**Public** : les collaborateurs qui codent, le responsable du planning, les relecteurs.
**Rôle dans la série des 4 documents** : doc 1 = la porte d'entrée (explicatif) · doc 2 = la référence technique · doc 3 = les propositions écartées et l'horizon · **doc 4 = l'action** (ce document).

**Règle de rédaction** (études UI/gouvernance §7.1) : aucun document final ne nomme un système amont ; les concepts sont repris sous nos propres noms (horloges temporelles, chaîne de provenance, record de relation, labels épistémiques, identifiants canoniques, pré-enregistrement haché). Une recherche automatique du terme interdit est passée avant livraison de ce document.

---

## 0. État de départ mesuré (et ce qui manque)

Vérifié sur le dépôt le 15/10/2026. Étiquettes : **[FAIT]** = exécuté et reproductible · **[PARTIEL]** = brique présente, périmètre v1 incomplet · **[ABSENT]** = à construire.

| Brique | Preuve | État |
|---|---|---|
| Couche données d'archive (`src/orvyren/data/` : `rpc`, `aave`, `curve`, `chainlink`) | `scripts/reconstruct_rseth_episode.py` · `reconstruct_steth_episode.py` · `reconstruct_usdc2023_episode.py` → `evidence/episode_*.json` | [FAIT] |
| Collecteur de corpus hors-ligne (520 observations, manifeste, contrats de fenêtre) | `collect_corpus.py` → `corpus/` ; CI : `collect_corpus.py --offline` | [FAIT] |
| Qualité + graphe SQLite append-only (12 déclencheurs refusant UPDATE/DELETE) | `run_quality.py` → `evidence/quality_report.json`, `evidence/graph.sqlite` | [FAIT] |
| Moteur de décision déterministe (hypothèses pré-enregistrées, NO-ACTION/INCONCLUSIVE) | `python -m orvyren.decide` → `evidence/decision_record_usdc-2023-03.json` (+ `run_decision.py` → `evidence/decision_usdc-2023-03.json`) | [FAIT] (v0 + **RDOF v1/3 axes/abstention/catalogues** livrés 16/10 ; **fusion des deux W3 le 17/10** : commande `orvyren.decide`, `config/actions_v1.yaml`, L3.1 registre W2) |
| Baseline A0 (l'adversaire) | `evidence/baseline_report.json` | [FAIT] |
| Service de politique (`ALLOW`/`DENY`/`REQUIRE_APPROVAL`) | `src/orvyren/policy/` + `policy_v1.yaml` + `scripts/run_drift_check.py` → `evidence/envelope_drift_report.json` | [FAIT] (16/10 — 14 règles P1–P14, dérive offline+live PASS ; **ADR-0002 à acter par l'équipe**) |
| Exécution bornée + vérification de receipt | `run_execution_demo.py`, `src/orvyren/execution/` | [FAIT] (16/10 — exécution bornée **on-chain** : 5 runs A→E via le kit démo ; vérification de reçu + contrôle A8 du vérificateur T10) |
| Dossier 1 page + visionneuse locale | `run_audit.py` → `evidence/dossier_usdc-2023-03.{md,html}` | [FAIT] |
| Orchestrateur de pipeline | `run_pipeline.py` → `evidence/pipeline_summary.json` | [FAIT] |
| Suite de tests | `python -m unittest discover -s tests` → **811 tests — OK (808 verts, 3 sautés)** | VERTE |
| `src/orvyren/branches/`, `src/orvyren/research/`, `src/orvyren/agents/` | — | [PARTIEL] (`branches/` + `agents/` MA-B livrés et **fusionnés** 16/10 — boucle, 2 processus, magasin haché ; partie live sous clé API ; `research/` absent) |
| `src/orvyren/evaluation/`, `src/orvyren/replay/` | `run_evaluation.py` · `run_calibration.py` · `run_replay.py` → `evidence/evaluation/`, `evidence/calibration_report.{json,md}`, `evidence/replay/` | [FAIT] (Sprint 0 pour `loss`/`comparators`/`calibration`/`windows`/`forecasts`/`outcomes` + gel G1–G6 ; **17/10 — W7 complet** : `harness.py`/`report.py`, paquet `replay/` (clock PIT, corpus figé, journal k=10, archive, dossier), CLIs ; portes de gel/verrou/embargo ; correctif identité de Murphy intra-bin + **re-gel G5** documenté) |
| `python -m orvyren.verify` (vérificateur tiers T10) | `src/orvyren/verify/` (moteur A1–A8 + B/C) ; `scripts/build_audit_packet.py` (paquet v2) | [FAIT] (16/10 — `--mutate-test` **6/6** ; vérificateur **gelé** livré dans chaque paquet ; `README_AUDIT.md` + `VERIFY_EXPECTED.txt`) |
| `policy_v1.yaml` + fixtures d'enveloppe + test de conformité/dérive | — | [ABSENT] |
| Kit de démo testnet (montage Safe 2/3 + module Roles + scripts) | `scripts/demo/` (19 fichiers) + `DEMO_KIT.md` | **[FAIT]** (16/10 — 5 runs on-chain A→E exécutés ; scripts montage + hygiène L5.2 complétés ; bilan `docs/W5_lots_L5.1-L5.6.md`) |
| Wallet testnet financé | — | **chemin critique, côté équipe** |
| `agent_journal` (journal privé append-only par agent) | spécifié (DOC2 §5.2) | [ABSENT] |

**Convention de lecture de ce document** : **[LOT]** = lot de travail démontrable par une commande ou un artefact · **[DONE]** = critère de fin testable · **[I]** = interface contractuelle entre workstreams. Les renvois courts du type « Bx §y » désignent les études de recherche d'origine (archivées hors dépôt — `README.md` §Archives), dont les conclusions sont reprises dans les DOC 1–3 et `FREEZE_V2.md`.

---

## 1. Principes de collaboration

### 1.1 Branches, commits, revue
- **Une branche par sujet** : `feat/<sujet>` (ex. `feat/branches-registry`, `feat/policy-14-rules`, `feat/verify-t10`, `feat/replay-journal`). Jamais de développement direct sur `master`.
- **Toute PR est relue** par au moins un autre collaborateur — et par le propriétaire du module **aval** quand la PR touche une interface (voir §1.3, §2).
- CI verte obligatoire avant merge (`tests.yml` : tests + `run_pipeline.py` + `collect_corpus.py --offline`).
- Commits impératifs en anglais (`add policy deny codes`) ; une PR > 400 lignes utiles est scindée.
- **Un seul écrivain git** : le coordinateur (P5, §4). Les autres poussent leurs branches, pas de merge local sur `master`, pas de rebase réécrivant l'historique partagé.
- Une PR qui casse la CI n'est pas mergée ; une PR mergée qui fait rougir la CI est **revertée le jour même**.

### 1.2 Tests obligatoires par module
- **Barre non négociable** : la suite reste verte (aujourd'hui **811 tests — 808 verts, 3 sautés** : deux tests live-RPC opt-in + un conditionnel selon la présence d'`eth-account`). **Le total monte, il ne descend jamais** ; aucun test supprimé, aucun test désactivé pour faire passer une PR.
- Chaque lot apporte **ses tests dans la même PR** que le code. Les seuils par module sont en §6.
- **Hors-ligne par défaut** : les tests lisent les fixtures archivées (`corpus/`, `evidence/`, `fixtures/`) ; un test qui exige le réseau est `skip` par défaut et exécutable explicitement (convention des 2 sautés existants).
- **Test de contrat** : toute interface [I] a un test qui la consomme côté aval. Une PR qui change un contrat change **les deux côtés** et le test, sinon refus.

### 1.3 Pas d'écriture croisée entre workstreams
Chaque fichier a **un propriétaire unique**. Un workstream n'édite pas les fichiers d'un autre : il ouvre une issue/PR de contrat, ou le propriétaire fait le changement.

| Chemins | Propriétaire |
|---|---|
| `src/orvyren/data/`, `quality/`, `graph/`, `corpus/`, `scripts/reconstruct_*`, `reconstruct_common.py`, `collect_corpus.py`, `run_quality.py` | **W1** |
| `src/orvyren/branches/`, `src/orvyren/research/`, `src/orvyren/agents/`, `run_agents.py`, `config/models.json` | **W2** |
| `src/orvyren/decision/`, `run_decision.py`, `config/decision_*.yaml`, catalogues d'actions | **W3** |
| `src/orvyren/policy/`, `policy_v1.yaml`, `fixtures/roles_agent_config.json`, `scripts/run_drift_check.py`, `docs/decisions/` (politique) | **W4** |
| `src/orvyren/execution/`, `scripts/b5/`, `run_execution_demo.py`, `docs/demo/` | **W5** |
| `src/orvyren/audit/`, `src/orvyren/verify.py`, `README_AUDIT.md`, `scripts/audit_*` | **W6** |
| `src/orvyren/evaluation/`, `src/orvyren/replay/`, `run_evaluation.py`, `run_calibration.py`, `run_replay.py`, `frozen/` | **W7** |
| `src/orvyren/ui/`, `run_audit.py`, `docs/`, `dist/docs/`, `README.md`, `ORVYREN_DOC*.md` | **W8** |

**Exception : `tests/` est partagé en ajout seul** — chacun crée ses fichiers `tests/test_<module>.py` ; personne ne réécrit le test d'un autre (un test faux se corrige par PR chez son propriétaire).

### 1.4 stdlib-only pour le cœur ; exceptions isolées documentées
- Le **cœur** (`data`, `quality`, `graph`, `branches`, `research`, `decision`, `policy`, `audit`, `evaluation`, `replay`) est **Python 3.11 standard, sans dépendance** : `urllib`, `sqlite3`, `json`, `hashlib`, `dataclasses`, `unittest`. Motif : la démo et le vérificateur tiers (T10) doivent tourner **hors-ligne, sans installation**.
- **Exceptions isolées admises** (déclarées dans `README.md` et `LICENSES.md`, jamais importées par le cœur) :
  1. le **service de signature** (`scripts/b5/signer_service.py`) peut utiliser une bibliothèque de signature hors stdlib (`eth-account`, choix par défaut gelé) — il est le **seul** lecteur de la clé, tourne dans un **processus séparé** et n'est jamais importé par `decision` ni `policy` ;
  2. l'éventuel serveur d'UI (aucune dépendance nouvelle aujourd'hui) et, si un besoin mesuré l'exige, `fastapi` **hors du cœur** ;
  3. la **recherche sémantique** d'appoint (embeddings) reste **hors du chemin de décision** et **hors CI** par défaut.
- Règle : une exception ne s'ajoute que par PR qui met à jour `LICENSES.md` **et** ajoute un test prouvant que le cœur s'importe sans elle.

### 1.5 Secrets hors dépôt
- `.env.example` ne liste que les **noms** de variables ; aucune valeur. `.gitignore` couvre `.env*`.
- **Scan secrets en CI** (bloquant) : motif `0x[0-9a-f]{64}`, `PRIVATE`, `MNEMONIC`, `API_KEY` — hors noms de champs déclarés.
- La clé de démo est **jetable** : générée localement par script (jamais imprimée), **détruite après la démonstration**. Elle n'est jamais lue par le raisonnement, jamais écrite dans un journal, un prompt ou un log.
- Les clés API des modèles vivent en variables d'environnement côté poste ; le journal des réponses ne contient **jamais** de clé.

### 1.6 CI existante + ajouts acceptés
- **Existant à ne pas casser** : `tests.yml` (unit tests, pipeline bout-en-bout, contrôle hors-ligne).
- **Ajouts acceptés** (chacun ≤ 0,5 j, propriétaire indiqué) : ① scan secrets (W4) · ② test de conformité politique ↔ enveloppe on-chain, hors-ligne (W4) · ③ vérification du journal d'audit sur fixtures (W6) · ④ vérificateur T10 lancé sur un paquet de fixtures (W6) · ⑤ contrôle d'index des ADR (W8) · ⑥ build documentaire (`md2docx.py` → `dist/docs/`) (W8).
- Aucun ajout CI n'est mergé sans son **test local qui passe** et sans sa ligne dans `README.md` (« comment lancer »).

### 1.7 Règles transverses
- **Replay hors-ligne obligatoire** : toute commande livrée tourne **sans réseau** (`--replay` / `--offline`) sur le corpus et les sorties archivées. Le réseau n'est admis que pour la collecte et les runs chaîne — chacun étiqueté.
- **Zéro placeholder** : pas de `TODO` déguisé en résultat, pas de chiffre inventé, pas de champ « à remplir » livré. Ce qui n'est pas fait est **écrit comme non fait** (`NOT DONE` + raison + date).
- **Étiquetage honnête partout** : `LIVE`, `REPLAY (journal, <cas>)`, `REPLAY (live, données archivées)`, `SIMULÉ` — jamais un replay présenté comme du direct.
- **Versionnage** : voir §5.4.

---

## 2. Carte des 8 workstreams

Gabarit identique pour chacun : **objectif · périmètre · livrables [DONE] · interfaces [I] · dépendances · estimation**. Les estimations sont en **jours-homme (j-h)** d'un développeur familier du dépôt ; elles reprennent celles des études B1–B7/B89 et des recommandations du gel.

### W1 — Données & Graphe
- **Objectif** : un graphe de collatéral typé, complet et requêtable *as-of*, qui **sert la décision** (les 8 requêtes noyau s'exécutent sur les épisodes déjà mesurés).
- **Périmètre** : `src/orvyren/data/` [FAIT], `src/orvyren/quality/` [FAIT], `src/orvyren/graph/` (`models.py`, `store.py`, `provenance.py`), `corpus/`, `scripts/reconstruct_*`, `run_quality.py`.
- **Lots** :
  - **L1.1** record de relation à **17 champs** + catalogue **34 relations / 4 familles** en **enum machine-vérifiable** + tests de conformité (types sujet/objet) — 1,5 j.
  - **L1.2** **horloges** minimales : `valid_from`/`valid_to` (familles 2 et 4), `ts_published` (documents) ; requêtes *as-of* à deux filtres ; test INV-PIT — 1,5 j.
  - **L1.3** deux colonnes à fort effet rétroactif : `source_family_id`, `extract_method` — 0,5 j.
  - **L1.4** les **8 requêtes noyau Q1–Q8** écrites comme **contrat de test** du store (jeux d'essai : USDC 2023, stETH 2022, rsETH 2026) — 2,5 j.
  - **L1.5** fenêtres DEV/EVAL en données : extension corpus (fenêtres CALME 2022-23 et 2025-26, USD0++ EVAL secondaire), archivage et manifeste — 1,5 j.
  - **L1.6** export `graph_snapshot.json` + `provenance.json` point-in-time pour le paquet d'audit (contrat avec W6) — 1 j.
- **[DONE]** : `tests/test_graph_relations.py`, `test_graph_pit.py`, `test_graph_queries.py` verts ; une relation malformée (mauvais type sujet/objet, champ manquant) est **refusée** (test de rejet) ; les 8 requêtes reproduisent les valeurs publiées de W2-B/W3 sur le corpus figé ; `graph.sqlite` se reconstruit hors-ligne en < 60 s ; `graph_snapshot.json` hashé.
- **[I]** : entrée `(entité|adresse, grandeur, as_of, sources)` → sortie **`Observation` / `Relation` / `SnapshotFigé` / `graph_version`** ; point d'accès unique `orvyren.graph.store` (aucun autre module n'ouvre la base) ; export dans le paquet d'audit.
- **Dépendances** : *amont* rien (archive et couche données déjà là) ; *aval* **W2** (le planificateur lit le snapshot), **W6** (export), **W7** (replay lit corpus + snapshots).
- **Estimation : 8,5 j-h.**

### W2 — Agents & Orchestration
- **Objectif** : multi-agent **réel** (MA-B gelé) — orchestrateur et critique adversarial en **processus distincts**, journaux propres, outils bornés, budgets stricts, et un mode **REPLAY-JOURNAL** bit-à-bit.
- **Périmètre** : `src/orvyren/branches/` [à créer], `src/orvyren/research/` [à créer], `src/orvyren/agents/` [à créer], `run_agents.py` [à créer], `config/models.json` (IDs épinglés + date de vérification).
- **Lots** :
  - **L2.1** registre d'hypothèses : record **12 champs**, cycle **7 états** + 5 règles de transition (une hypothèse ne se supprime jamais), historique append-only — 1,5 j.
  - **L2.2** boucle agent : états cibles, **4 compteurs** (appels LLM, outils, temps, coût) et **5 conditions d'arrêt** ; plafonds gelés A5 : ≤ 30 appels · ≤ 12 outils · ≤ 10 min · ≤ 0,10 $ — 2 j.
  - **L2.3** **`agent_journal`** append-only **séparé du graphe** ; promotion journal → graphe uniquement par **validateurs déterministes** ; branches LLM à poids **nul** — 1,5 j.
  - **L2.4** **MA-B** : orchestrateur + critique en processus séparés (même dépôt), échange par **objets sérialisables** (table de jobs / fichiers JSON), `agent_id` et journal par instance ; critique sur **second modèle** dès v1 — 3 j.
  - **L2.5** prompts système (3 squelettes + schémas JSON) et **6 tests anti-injection** intégrés au banc — 1,5 j.
  - **L2.6** magasin de **réponses LLM enregistrées + hashées** (base du REPLAY-JOURNAL), versionnage du prompt, température 0 documentée — 1 j.
  - **L2.7** CLI `run_agents.py` (`--case`, `--replay journal|live`, `--budget`) + compteur de coût affiché — 0,5 j.
- **[DONE]** : deux processus démarrent séparément et leurs journaux montrent **deux `agent_id` distincts** sur le même cas ; les 4 plafonds coupent la boucle (test par plafond) ; un cas rejoué en mode journal produit un hash **identique** (k=10) ; 6/6 tests anti-injection verts ; l'import de `policy`/`execution` par un module agent est refusé (test de frontière).
- **[I]** : entrée **`SnapshotFigé` + catalogue de prédicats + budget** → sortie **`ResearchTask`, `Claim[]`, mises à jour d'hypothèses (proposées), entrées `agent_journal`** ; contrats B1 §3.4/§4.6 ; la promotion vers le graphe passe par un validateur de W1 (jamais d'écriture directe).
- **Dépendances** : *après* **W1** (snapshot) ; *avant* **W3** (RDOF consomme tâches et prédicats), **W6** (flux journal), **W7** (mode replay), **W8** (écrans 3-5).
- **Estimation : 11 j-h.**

### W3 — Décision & Recherche RDOF
- **Objectif** : la décision **généralisée** : hypothèses falsifiables, RDOF déterministe, abstention propre, catalogues d'actions bornées — 3 axes matérialisés dans le dossier.
- **Périmètre** : `src/orvyren/decision/` (`engine.py`, `exposure.py`, `scenarios.py`, `baseline.py` [FAIT v0]), `run_decision.py`, `config/decision_*.yaml`, `config/actions_v1.yaml`.
- **Lots** :
  - **L3.1** enregistrement d'hypothèses falsifiables (critères S/R obligatoires, pas de p∅ silencieux) + branchement sur le registre de W2 — 1,5 j.
  - **L3.2** **RDOF v1** déterministe : « quel prédicat réfute le leader au moindre coût » — évaluabilité, effet des prédicats (classes de seuils, jamais de probabilité), ordonnancement lexicographique gelé, arrêt (invariance / budget) avec **liste de ce qui n'a pas été recherché** — 3 j.
  - **L3.3** test **RDOF vs ordre fixe** (essai T02/HYP-02R) ; VoI derrière interface, `VOI_NOT_ESTIMABLE` autorisé (jamais un point de défaillance) — 1 j.
  - **L3.4** abstention **A1–A5** + format `INCONCLUSIVE` enrichi (`what_would_change_the_verdict` obligatoire) + table **ESCALATE vs NO-ACTION** — 1,5 j.
  - **L3.5** catalogues **8 actions DAO + 4 desk** (gabarit : déclencheur épistémique, seuil économique, bornes, coût, effet, applicabilité) — 2 j.
  - **L3.6** double convention de prix (alerte sur le low, décision sur close + low) exposée comme paramètre unique et testée — 0,5 j.
- **[DONE]** : une décision complète est **une commande** (`python -m orvyren.decide --case usdc-2023-03 --replay`) ; les 3 axes (`epistemic_verdict`/`economic_action`/`authorization_verdict`) sont présents et distincts dans le JSON ; un cas où une entrée manque reste `INCONCLUSIVE` (jamais « supposé satisfait ») ; aucun nombre produit par un agent ne déclenche un critère (test) ; `actions_v1.yaml` couvre 12 actions, chacune avec son test d'applicabilité.
- **[I]** : entrée **`SnapshotFigé` + hypothèses + `Claim[]`** → sortie **`DecisionRecord`** : verdicts 3 axes, **`Intent{action, chaîne, actif, montant, destinataire, intent_id}`** ou `NO-ACTION`/`INCONCLUSIVE`, rationale, `evidence_refs[]`, coût réel de recherche. Rien de financier ne sort de `decision` vers `policy` sans passer par `Intent`.
- **Dépendances** : *après* **W1** (requêtes/observations) et **W2** (tâches) ; *avant* **W4** (`Intent` → politique), **W6** (dossier), **W7** (harnais A1/AX0).
- **Estimation : 10 j-h.**

### W4 — Politique & Sécurité
- **Objectif** : le **premier verrou** — autorisation déterministe, 14 règles, codes de refus stables, fail-closed, aligné sur l'enveloppe on-chain et prouvé par tests.
- **Périmètre** : `src/orvyren/policy/` [PARTIEL], `policy_v1.yaml`, `fixtures/roles_agent_config.json`, `scripts/run_drift_check.py`, `docs/decisions/` (partie politique), flux d'approbation.
- **Lots** :
  - **L4.1** compléter le set v1 à **14 règles** : P4 (fonction scopée), P7 (exposition/solde), P9 (fraîcheur), P11 (pause / agent non membre), P12 (alignement d'enveloppe), P14 (budget de décision) — 3 j.
  - **L4.2** les **8 tests prioritaires** ajoutés au banc (frontière de période, fonction scopée, décimales, dédup par hash, fraîcheur, solde/exposition, pause, dérive) — 1,5 j.
  - **L4.3** `policy_v1.yaml` + **version et hash dans chaque verdict** ; procédure de changement à 6 étapes écrite — 0,5 j.
  - **L4.4** **test de conformité offline** politique ↔ fixture d'enveloppe (`roles_agent_config.json`, capturée une fois, versionnée) + **`run_drift_check.py`** live (eth_call, écrit `evidence/envelope_drift_report.json`) — 1,5 j.
  - **L4.5** flux **REQUIRE_APPROVAL** v1 : file + signature **EIP-712** (TTL 2 h, canal local), journalisation des données d'approbation — 1,5 j.
  - **L4.6** **kill switch** K0 ≤ 5 min / K1 ≤ 60 min : leviers, runbook détection → clôture, procédure de mesure — 0,5 j.
- **[DONE]** : les 14 règles ont chacune ≥ 1 test (refus *et* frontière) ; un **style de refus** est stable (mêmes codes) ; le test de conformité détecte une dérive simulée (fixture modifiée → SAFE MODE) ; la politique **n'importe pas** `research`/`agents`/LLM (test de frontière) ; le verdict porte `policy_version` + hash ; le flux d'approbation signe puis refuse un intent modifié après signature.
- **[I]** : entrée **`Intent`** (+ état : pause, soldes, compteur glissant, config d'enveloppe) → sortie **`PolicyDecision{ALLOW|DENY|REQUIRE_APPROVAL, règles violées, motifs, policy_version}`** ; sortie secondaire `envelope_drift_report.json`. La politique ne signe pas, ne détient aucune clé, ne juge pas les prix.
- **Dépendances** : *après* **W3** (l'intent vient de la décision) ; *avant* **W5** (seul un `ALLOW` s'exécute), **W6** (journal des verdicts), **W8** (écran 7).
- **Estimation : 8,5 j-h.**

### W5 — Exécution & Démo testnet
- **Objectif** : le **second verrou** — un signer isolé qui n'exécute qu'un intent déjà autorisé, une vérification de receipt, et **les 5 runs de démo** (ALLOW / DENY hors-chaîne / DENY par la chaîne / kill switch / audit) produisant des **hashes réels**.
- **Périmètre** : `src/orvyren/execution/` (`chain.py`, `guard.py`, `intents.py`, `verify.py` [FAIT]), `scripts/b5/` (13 scripts listés en B5 §e.6), `run_execution_demo.py`, `docs/demo/` (kit de démo).
- **Lots** :
  - **L5.1** **kit de démo** (W3-D) : procédure de montage Safe 2/3 + module Roles + rôle `AGENT` + allowance `usdc_daily`, deux USDC distincts nommés (Circle pour les transferts, Aave pour les lectures), robinets gratuits — 2 j (dont 0,5 j côté équipe : wallet + faucet).
  - **L5.2** scripts de montage et d'hygiène : `generate_signer_key.py`, `check_env_hygiene.py`, `verify_addresses.py` (eth_getCode + chainId + blockNumber, **arrêt si écart**), `faucet_check.py` — 1,5 j.
  - **L5.3** **service signataire isolé** (`signer_service.py`, seul lecteur de la clé, processus séparé, nonce/retries bornés) — 1,5 j.
  - **L5.4** préflight (12 contrôles dont simulation `eth_call`) + politique de confirmations + **anti-reorg 2 blocs** (démo) — 1,5 j.
  - **L5.5** vérification de receipt (champs exacts, correspondance intent ↔ logs, cas revert/partiel) + liaison vers l'audit — 1 j.
  - **L5.6** exécution des **5 runs** + capture des preuves (reçus, blocs, émetteur, destinataire, statuts `0x0` des rejets chaîne, chronométrage kill switch) — 2 j.
- **[DONE]** : run A (ALLOW, 100 USDC) produit une tx dont le **receipt est vérifié** (status `0x1`, log `Transfer`, soldes avant/après) ; run B refuse hors-chaîne (compteur de signatures = 0) ; run C encaisse des **statuts `0x0`** avec sélecteurs de revert affichés ; run D chronomètre le kill switch (`assignRoles(false)`, latence réelle = coordination humaine) ; run E exporte `audit.jsonl` chaîné et le fait vérifier par un **script indépendant** ; `verify_addresses.py` passe **avant chaque run** ; aucun secret dans le dépôt (scan CI vert).
- **[I]** : entrée **`Intent autorisé (PolicyDecision.verdict == ALLOW)`** → sortie **`TxHash + Receipt vérifié`** (ou échec **enregistré comme échec**) + lignes `audit.jsonl`. `execution` refuse tout intent non `ALLOW` (test), n'importe ni `decision` ni `policy`, et n'expose la clé à aucun autre processus.
- **Dépendances** : *après* **W4** ; *avant* **W6** (reçus et journal dans le paquet) ; dépendance **externe** : wallet testnet financé (chemin critique) et RPC public disponible.
- **Estimation : 9,5 j-h** (dont 2 j dépendant de l'extérieur).

### W6 — Audit & Vérificateur
- **Objectif** : rendre la décision **reconstructible par un tiers** — journal à 3 flux chaînés, dossier 1 page, paquet livrable, **vérificateur T10** auto-testé.
- **Périmètre** : `src/orvyren/audit/` (`dossier.py` [FAIT]), `src/orvyren/verify.py` [à créer], `README_AUDIT.md`, `scripts/audit_*`, `evidence/dossier_*`.
- **Lots** :
  - **L6.1** **3 flux chaînés SHA-256** (exécution · raisonnement · connaissance) + enveloppe commune + DAG de commit inter-flux — 1,5 j.
  - **L6.2** dossier 1 page version démo + **export du paquet 12 pièces** (`manifest.json`, `HASHES.txt`, `bundle_digest`) — 1,5 j.
  - **L6.3** **vérificateur T10** `python -m orvyren.verify` : 8 calculs déterminants (classe A), contrôles B (récupération en ligne), contrôles C (couverture du non rejouable), rapport JSON + MD, codes de sortie 0/1/2/3 — 3 j.
  - **L6.4** `--mutate-test` : **6 mutations** doivent être détectées (auto-test de l'outil) — 1 j.
  - **L6.5** `README_AUDIT.md` (EN) : vérification en 3 commandes, textes « prouve / ne prouve pas » verbatim, checklist interne 11 points — 1 j.
  - **L6.6** ancrage externe (**conditionnel** : seulement si le run E et T10 sont verts avant la date limite interne) — 0,5 j.
- **[DONE]** : `python -m orvyren.verify .` renvoie `VERDICT: OFFLINE_PASS` sur le paquet **tel que zippé** ; `--mutate-test` détecte 6/6 ; `HASHES.txt` couvre tous les fichiers (aucun absent, aucun non listé) ; le dossier re-rendu depuis le JSON est **identique octet à octet** ; zéro `dangling_refs` ; le vérificateur tourne **sans le dépôt producteur** (copie gelée du paquet) ; aucun secret dans le paquet (test).
- **[I]** : entrée **artefacts produits** (`decision_*.json`, `agent_journal.jsonl`, `audit.jsonl`, `graph_snapshot.json`, `receipts/`, `policy/`, `baseline_report.json`, `quality_report.json`) → sortie **`verify_report.json` + `verify_report.md` + `HASHES.txt` + `bundle_digest`**. Le vérificateur ne relit **jamais** la base du producteur : il relit `graph_snapshot.json`.
- **Dépendances** : *après* **W1** (export), **W2** (journal), **W5** (reçus) ; *avant* **W8** (page d'audit) et la pièce ⑥ de soumission.
- **Estimation : 9 j-h.**

### W7 — Évaluation & Replay
- **Objectif** : mesurer sans se mentir — perte, comparateurs, calibration, harnais DEV/EVAL sous embargo, et **replay à deux modes** explicitement étiquetés.
- **Périmètre** : `src/orvyren/evaluation/` [à créer], `src/orvyren/replay/` [à créer], `run_evaluation.py`, `run_calibration.py`, `run_replay.py`, `frozen/` (hashs G1–G6).
- **Lots** :
  - **L7.1** `evaluation/loss.py`: fonction de perte + conventions de valorisation (`terminale`, `liquidation`) — 0,5 j.
  - **L7.2** `evaluation/comparators.py` : A0, A1, B0 (graine, M), AX0, oracle faisable — 0,5 j.
  - **L7.3** `evaluation/windows.py` : registre DEV/EVAL, vérificateur d'embargo (24 h ; chevauchement de calibration croisée) — 0,25 j.
  - **L7.4** `evaluation/forecasts.py` + `outcomes.py` : formats hashés, chaînage, règle `sustained_depeg_v1`, garde `resolve_not_before`, `supersedes` — 0,5 j.
  - **L7.5** `evaluation/calibration.py` : C1–C7 en stdlib (BS, REL, RES, UNC, ECE, Wilson, bootstrap déterministe) — 0,5 j.
  - **L7.6** `evaluation/harness.py` + `report.py` : boucle, agrégats, tests de supériorité, bannières obligatoires, refus si le gel est absent — 1,25 j.
  - **L7.7** `replay/` : `clock.py` (horloge simulée, garde-fous PIT), `corpus.py` (manifeste, ancres de blocs), `journal.py` (mode 1), `archive.py` (mode 2), `dossier.py` + `run_replay.py` — 3 j.
  - **L7.8** `frozen/` : gel **G1–G6** hashé et daté (perte, comparateurs, fenêtres, seuils, plan d'analyse, hypothèses économiques) — 0,5 j.
  - **L7.9** **5–10 prévisions gelées DEV** (pré-enregistrées, hashées, avec `ȳ` et Wilson) — 1 j (Sprint 0).
- **[DONE]** : les six tests de la fonction de perte (neutralité, translation, monotonie, signe, additivité, référence dégénérée) verts ; A0 = 0 action, B0 reproductible à graine fixe, AX0 reproduit `baseline_report.json` ; KAT de calibration exacts et bornes de Wilson à ±0,001 ; `run_evaluation.py --set eval` **refuse d'écrire** si les hashs de gel manquent, si `eval_run.lock` existe ou si une fenêtre EVAL chevauche la période de calibration ; rejeu journal k=10 → hash identique ; le rejeu porte le marquage `REPLAY` obligatoire ; toute sortie sans bannière est un bug.
- **[I]** : entrée **prévisions gelées + outcomes + corpus + sorties de décision** → sortie **`evaluation_report.{json,md}`** (métriques, N affiché, bannières) et **rapports de replay** ; `run_replay.py inspect|journal|archive|verify` est l'outil d'appui de W6 (mode journal) et de la démo (écrans 1-5).
- **Dépendances** : *après* **W1** (corpus, snapshots) et **W2** (journal, pour le mode 1 complet ; en attendant, le mode 1 se démontre sur le dossier déterministe USDC existant) ; *avant* la revendication d'évaluation (S4) et le doc 2 (§10).
- **Estimation : 8 j-h** (dont ≈ 1,5 j de chemin critique avant la soumission).

### W8 — UI locale & Coordination docs
- **Objectif** : la vitrine **locale** (lecture seule) et la cohérence documentaire : 12 écrans démontrables, docs finaux, registre d'ADR, livraison.
- **Périmètre** : `src/orvyren/ui/` (`server.py` [FAIT]), `run_audit.py`, `docs/`, `dist/docs/`, `README.md`, `ORVYREN_DOC*.md`, `docs/decisions/`.
- **Lots** :
  - **L8.1** enrichissement de la visionneuse locale : écrans 1-9 (fenêtre & PIT, graphe, branches, timeline des réflexions, recherche & coût, dossier, refus politique, quarantaine, coût par décision) — 2 j.
  - **L8.2** bandeau + étiquette de mode obligatoires (REPLAY journal / REPLAY live / LIVE) sur chaque vue, horloge simulée affichée — 0,5 j.
  - **L8.3** intégration des artefacts chaîne (écrans 10-12 : runs A/C/E, journal, kill switch) à partir des preuves capturées — 1 j.
  - **L8.4** consolidation du **doc 2** (technique complet) et du **doc 3** (propositions/écartés) à partir des études — 2 j (rédaction) + contributions des propriétaires (hors charge).
  - **L8.5** registre **ADR** (`docs/decisions/`), script d'index, contrôle CI — 1 j.
  - **L8.6** livraison : `README.md` à jour (commandes, tests, replay), build `dist/docs/`, checklist de soumission — 0,5 j.
  - **L8.7** coordination : planning, suivi des PR, gel des documents, recherche du terme interdit avant livraison — continu (0,5 j/semaine, compté dans la charge de P5).
- **[DONE]** : `python run_audit.py --serve` sert `/`, `/api/dossier`, `/api/health` **hors-ligne** ; chaque écran affiche son mode et son horloge ; aucun asset externe, aucun JavaScript requis ; doc 2 et doc 3 livrés et référencent les ADR ; le registre d'ADR est numéroté sans trou et son contrôle CI passe ; les 4 documents passent la recherche du terme interdit (0 occurrence).
- **[I]** : entrée **tous les artefacts** (dossiers, JSON de décision, journaux, `verify_report`) → sortie **pages HTML autonomes + documentations** ; contrat de routes inchangé (`/`, `/api/dossier`, `/api/health`).
- **Dépendances** : *après* tout (agrège) ; *avant* la soumission (docs/vidéo/deck) mais **les écrans 1-9 se développent en parallèle** sur les artefacts déjà existants.
- **Estimation : 7 j-h** (+ coordination continue).

**Total des 8 workstreams : ≈ 71,5 j-h**, soit ≈ 3 semaines à 5 personnes (voir §4).

---

## 3. Chemin critique & sprints

### 3.1 Vue d'ensemble des dépendances

```
        W1 Données & Graphe ──────────────┐
                                          ▼
   W2 Agents & Orchestration ───────► W3 Décision & RDOF ──► W4 Politique ──► W5 Exécution & Démo
            │                              │                     │                 │
            │                              ▼                     ▼                 ▼
            └───────────────► W6 Audit & Vérificateur ◄──────────┴─────────────────┘
                                          │
                                          ▼
                    W7 Évaluation & Replay ──► W8 UI locale & Coordination docs
```

**Chemin critique (la chaîne qui décide de la date)** :
`G4 (Sprint 0)` → **runs chaîne du kit de démo** (dépend du wallet) → `agent_journal` (W2) → `RDOF` (W3, consomme les prédicats de W1) → `14 règles` (W4) → `runs 5/5 + reçus` (W5) → `vérificateur T10` (W6) → `replay mode 1` (W7) → `démo complète + EVAL` (S4).
Second chemin, parallèle : `journal 3 flux` (W6) → `paquet 12 pièces` → `clôture de l'évaluation` (W7).

### 3.2 Sprint 0 — immédiat, 15 → 20 octobre (avant la soumission)

**Priorité absolue** : la soumission (deadline **20/10 15 h 59 UTC**, tampon interne le **19/10**). La construction qui n'alimente pas une pièce de soumission **attend** S1.

| # | Lot | Propriétaire | Durée | Sortie |
|---|---|---|---|---|
| 0.1 | **G4** — `evaluation/loss.py` (6 tests), `comparators.py` (A0/A1/AX0/B0), `calibration.py` (C1–C7, KAT) | P3 | 1,5 j | modules + tests verts (L7.1/L7.2/L7.5) |
| 0.2 | **Prévisions gelées DEV** (5–10, hashées, avec `ȳ` et Wilson) — pré-enregistrement | P3 + coordinateur | 1 j | `frozen/forecasts_dev.jsonl` + hash |
| 0.3 | **Gel G1–G6** hashé et daté (avec le squelette de rapport `N=0`) | coordinateur | 0,5 j | `frozen/G1..G6.sha256` |
| 0.4 | **Kit de démo** : montage documenté + scripts d'hygiène/préflight | P4 (+ équipe pour wallet) | 2 j | `docs/demo/` + `scripts/b5/*` |
| 0.5 | **Runs testnet** (A/B/C/D/E) — **si le wallet est prêt** | P4 | 2 j | reçus + hashes + `audit.jsonl` (pièce ⑥) |
| 0.6 | Assemblage des pièces EN (docs ①, ⑤), README, deck, vidéo | W8 + tous | continu | paquets ①–⑥ prêts |
| 0.7 | **Interdit avant la 1ʳᵉ exécution EVAL** : publier le moindre résultat EVAL, ajuster un seuil après coup d'œil, modifier une liste de fenêtres EVAL | — | — | embargo tenu |

**Doit être prêt avant le 20/10 — liste opposable** : (1) `loss.py` + `comparators.py` + `calibration.py` avec leurs tests ; (2) 5–10 prévisions gelées DEV hashées ; (3) gel G1–G6 + sha256 ; (4) kit de démo + **runs chaîne si wallet** (sinon : plan explicitement daté « non exécuté à la soumission ») ; (5) rapport de calibration squelette (`N=0` assumé) ; (6) docs/vidéo/deck.
**Ce qui peut glisser sans casser la soumission** : EVAL complet, T10 par un tiers, mode 2 du replay, ancrage externe, UI enrichie.

### 3.3 Sprint 1 — 21 → 27/10 : Agents MA-B + graphe v1

- **W2** L2.1 → L2.4 (registre d'hypothèses, boucle bornée, `agent_journal`, processus séparés) — P1.
- **W1** L1.1 + L1.2 (record 17 champs, 34 relations, horloges, INV-PIT) — P2.
- **W7** L7.4 + L7.7 amorce (`clock.py`, `corpus.py`) — P1/P3.
- **Démarrage anticipé (2026-10-16)** : lots **hors-ligne d'abord** — W1 L1.1 (enum 34 relations + record 17 champs + tests de rejet) → L1.2 (horloges, INV-PIT) ; W2 L2.1 (registre d'hypothèses) + L2.3 (`agent_journal`) ; la **partie live** des agents (L2.2/L2.4 sur modèles réels) attend la clé API (§3.7, ligne « Clés API agents »). **[FAIT 16/10]** : L1.1 (`graph/catalog.py`, `graph/record.py`), L1.2 (`graph/temporal.py` + INV-PIT), L2.1 (`branches/hypotheses.py`), L2.3 (`agents/journal.py`) — 528 tests verts (après fusion `feat/policy-14-rules`) ; reste L2.2/L2.4–L2.7 (boucle/MA-B : partie live sous clé API) → **livrés + FUSIONNÉS le 16/10 (`bfcfa6d`, merge --no-ff)**. **[FAIT 16/10 — W1 clos]** : L1.4 (requêtes noyau Q1–Q8 + `test_graph_queries.py`, figure publiée 870,07 bps pinnée), L1.5 (fenêtres CALME calm_a 2023-01 + calm_b 2025-09 — proposition B7 à figer en G1 — série USD0++ 635 h, `replay/corpus_v1.manifest.json` vérifiable), L1.6 (`graph_snapshot.json`/`provenance.json` hashés sous `evidence/graph_snapshots/`) ; `graph.sqlite` reconstruit hors-ligne en **0,5 s** (mesuré, critère < 60 s) ; **706 verts, 3 sautés** (242 subtests) sur master après les fusions W1+W2.
- **Jalon S1** : `run_agents.py --case usdc-2023-03 --replay journal` écrit un journal à deux `agent_id`, et le graphe accepte/refuse les relations selon l'enum (tests de rejet visibles).

### 3.4 Sprint 2 — 28/10 → 03/11 : RDOF + 14 règles + exécution

- **W3** L3.2 → L3.5 (RDOF, test contre l'ordre fixe, abstention, catalogues) — P3. **[FAIT 16/10 — avec L3.6]** : RDOF v1 déterministe (`decision/rdof.py` : 5 règles, effets calculés par contre-épreuve, arrêts invariance/budget + liste de non-recherché), essai T02/HYP-02R vs ordre fixe (`compare_rdof_vs_fixed_order` : RDOF 1 achat/0 inutile vs fixe 2/1, verdicts identiques), abstention A1–A5 + format enrichi (`abstention.py`), catalogues 8+4 (`catalog.py`), 3 axes séparés (`axes.py`), double convention C5 exposée et testée ; trace USDC reproduite : **P-6.3 choisi, −7,172196 %, H2 INCONCLUSIVE→SUPPORTED, arrêt c1 à 0,65 s**. **[COMPLÉTÉ 17/10 — fusion des deux W3]** : lot L3.1 (`decision/records.py` — hypothèses falsifiables → registre de W2), commande `python -m orvyren.decide` → `evidence/decision_record_usdc-2023-03.json`, catalogue paramétré `config/actions_v1.yaml` (test d'applicabilité par action) ; détail : `docs/handoff-w3-fusion.md`.
- **W4** L4.1 → L4.4 (14 règles, tests, `policy_v1.yaml`, conformité + dérive) — P4. **[Livré 16/10 par UnoriginalDude14 — fusionné `a35c22b`]**
- **W1** L1.4 + L1.6 (8 requêtes noyau, export snapshot) — P2. **[FAIT 16/10 — avec L1.5]**
- **W5** L5.4 + L5.5 (préflight, confirmations, anti-reorg, vérification de receipt) — P4.
- **Jalon S2** : une décision complète traverse `graphe → RDOF → décision → 14 règles → intent` en une commande, hors-ligne ; le test de conformité politique ↔ enveloppe attrape une dérive simulée.

### 3.5 Sprint 3 — 04 → 10/11 : audit/vérificateur T10 + replay 2 modes

- **W6** L6.1 → L6.5 (3 flux, paquet, vérificateur, `--mutate-test`, README_AUDIT) — P5.
- **W7** L7.7 complet + L7.6 (replay 2 modes, harnais, rapport) — P1/P3.
- **W2** L2.5 + L2.6 (anti-injection, magasin de réponses) — P1. **[FAIT 16/10 — livré avec L2.2–L2.7, fusionné `bfcfa6d`]**
- **Jalon S3** : `python -m orvyren.verify .` → `OFFLINE_PASS` et `--mutate-test` 6/6 ; `run_replay.py journal` rejoue k=10 à hash identique.

### 3.6 Sprint 4 — 11 → 17/11 : démo complète + évaluation EVAL

- **W5** L5.6 (les 5 runs, captures finales) — P4.
- **W7** L7.9 complété → **première exécution EVAL** (une passe, résultat publié tel quel, même décevant) — P3.
- **W8** L8.1 → L8.3 (écrans, bandeaux), L8.4 (docs finaux) — P5.
- **Jalon S4** : démonstration de bout en bout **hors-ligne** (écrans 1-9 + reçus capturés des écrans 10-12), rapport d'évaluation publié avec ses limites et son N.

### 3.7 Chemin critique serré (ce qui bloque, et quoi)

| Blocage | Débloque | Décision de repli si glissement |
|---|---|---|
| **Wallet + faucet** (côté équipe) | runs chaîne (pièce ⑥) | vidéo en REPLAY-JOURNAL seul + reçus ajoutés dès exécution ; écrire « non exécuté » plutôt que simuler |
| **Clés API agents** budgétées | mode 2 du replay, harnais A2 | mode 1 sur le dossier déterministe USDC ; coût mesuré 0,013–0,036 $/décision, replay ≈ 0,03–0,04 $/3 épisodes |
| **Budget de décision** (≤ 30 appels/≤ 0,10 $) | boucle agent utilisable | ordre fixe borné comme repli documenté (RDOF non livré = repli assumé) |
| **Suite de tests** qui rougit | tout merge | revert le jour même ; jamais de test désactivé |
| **Gel G1–G6 signé** | toute revendication d'évaluation | sans gel : publier « évaluation gelée, non exécutée » (plus fort qu'un chiffre contaminé) |

### 3.8 Après le 20/10 (horizon, non bloquant)

Migration Postgres (cible ; SQLite reste la base du concours), rétention intégrale du journal, ancrage conditionnel, VoI (derrière interface), ML d'appoint borné, deuxième persona desk, 2ᵉ/3ᵉ épisodes (stETH backtest, UST), banques/institutions en phase 2. Tout cela vit dans le **doc 3** et ne contredit aucun ADR.

---

## 4. Répartition type par personne

Cinq rôles, une propriété claire, un **backup déclaré** par workstream (personne ne doit être un point de défaillance unique).

| Personne | Rôle | Workstreams (primaire) | Charge estimée | Backup / secondaire |
|---|---|---|---|---|
| **P1** | Dev Agents / Orchestration | **W2** (11 j) + replay L7.7 (4 j) | ≈ 15 j | backup W3 |
| **P2** | Dev Graphe / Données | **W1** (8,5 j) + kit de montage et scripts de données W5 (3 j) | ≈ 11,5 j | backup W6 (export) |
| **P3** | Dev Décision / Évaluation | **W3** (10 j) + éval/calibration W7 (4 j) | ≈ 14 j | backup W1 (requêtes noyau) |
| **P4** | Dev Politique / Exécution | **W4** (8,5 j) + **W5** (6,5 j) | ≈ 15 j | backup W2 (budgets) |
| **P5** | Dev UI / Audit **+ Coordinateur** | **W6** (9 j) + **W8** (5,5 j) + coordination continue | ≈ 14,5 j | backup W4 (docs décisions) |

**Dépendances entre personnes** (qui attend qui) :
- P2 → P1 : snapshot et requêtes noyau avant la boucle agent (S1). **Contrat gelé dès S0** (formes des objets) pour que P1 code contre le contrat, pas contre le code.
- P1 → P3 : journal et tâches avant le RDOF complet (S2). En attendant, P3 travaille sur le dossier déterministe existant.
- P3 → P4 : `Intent` et catalogues avant les règles et l'exécution (S2).
- P4 → P5 : reçus et journal avant le paquet et le vérificateur (S3).
- P5 → tous : planning, revues, gel documentaire, **tenue des interfaces** (toute dérive de contrat est arbitrée par P5 le jour même).
- **Réunion d'interface** : 30 min en fin de sprint, obligatoire, avec la liste des contrats modifiés (aucun changement de contrat hors de cette réunion).
- **Charge non comptée** : rédaction du doc 2/doc 3 par les propriétaires (contributions), revues de PR (~10 % de la charge de chacun, incluse dans les estimations).
**Total affecté ≈ 70 j-h** (sur 71,5 j-h estimés) : le solde (≈ 1,5 j) correspond à la rédaction des documents finaux, portée par le coordinateur au-delà de sa charge de code.

**Règle d'équilibrage** : toute personne qui dépasse **3 jours de retard déclaré** rend une partie de son périmètre au coordinateur qui la redistribue (le planning est révisé en fin de sprint, jamais en silence).

---

## 5. Conventions techniques rappelées

### 5.1 Tests
- `python -m unittest discover -s tests` — état actuel **811 tests — OK (808 verts, 3 sautés)**. Aucune baisse autorisée.
- Chaque module nouveau apporte ses fichiers `tests/test_<module>.py` ; chaque règle de politique, chaque relation du graphe, chaque état d'hypothèse a son test de rejet ou de frontière.
- Les tests qui exigent le réseau sont `skip` par défaut, avec un drapeau explicite pour les lancer.
- Un bug corrigé **gagne son test de non-régression** dans la même PR.

### 5.2 Replay hors-ligne
- `--replay` / `--offline` **obligatoire** pour toute commande livrée : corpus archivé, SQLite, aucune dépendance réseau.
- Deux modes, étiquetés : **REPLAY-JOURNAL** (réponses enregistrées, bit-à-bit, celui de la démo) et **REPLAY-LIVE** (recalcul à température 0, versions épinglées — « même décision, texte différent » est un résultat honnête, pas un échec).
- Marquage `REPLAY` obligatoire dans toute sortie rejouée, horloge simulée affichée.

### 5.3 Zéro placeholder
- Aucun `TODO` livré, aucun champ vide non expliqué, aucun chiffre non tracé.
- Un `Claim` sans observation parente est **refusé** par le store (invariant, test) ; aucun nombre du LLM n'entre dans un calcul (invariant, test).
- Ce qui n'est pas fait est écrit `NOT DONE` avec la raison et la date envisagée.

### 5.4 Versionnage
- **Documents** : version + date en tête ; toute mise à jour ultérieure passe par la procédure de révision (ADR + registre) et le paquet hashé.
- **Politique** : `policy_v1.yaml` versionné, **hash dans chaque verdict** ; changement de règle = 6 étapes documentées.
- **Modèles API** : IDs **épinglés** dans `config/models.json` (avec date de vérification) ; les fournisseurs redirigent ou déprécient les identifiants — la reproductibilité repose sur le **journal des réponses**, pas sur « même modèle, même prompt ».
- **Artefacts** : tout JSON livré porte sa version, son horodatage et ses `provenance_refs` ; les hashs (SHA-256) sont recalculables par un tiers.
- **Langue** : notes internes et études en français ; code, README, docs et vidéo du concours **en anglais** (exigence organisateur) ; les documents finaux de l'équipe, celui-ci inclus, sont en français.

---

## 6. Définition de « terminé » (par workstream)

| W | « Terminé » veut dire (testable) | Artefact de preuve | Tests associés |
|---|---|---|---|
| **W1** | 34 relations et 17 champs en enum machine-vérifiable ; requêtes *as-of* correctes ; 8 requêtes noyau rejouent les valeurs mesurées ; export snapshot hashé | `evidence/graph.sqlite`, `graph_snapshot.json`, `provenance.json` | `test_graph_relations.py`, `test_graph_pit.py`, `test_graph_queries.py` |
| **W2** | 2 processus d'agents, 2 journaux ; plafonds coupent ; rejeu journal k=10 identique ; 6/6 anti-injection ; frontière `policy`/`execution` respectée | `agent_journal.jsonl` + `payloads/` hashés | `test_agents_budget.py`, `test_agent_journal.py`, `test_injection.py` |
| **W3** | décision en une commande ; 3 axes distincts ; `INCONCLUSIVE` sur entrée manquante ; RDOF bat/matche l'ordre fixe sur l'essai ; 12 actions cataloguées | `decision_<cas>.json` | `test_decision_rdof.py`, `test_decision_axes.py`, `test_actions_catalog.py` |
| **W4** | 14 règles testées (refus + frontière) ; codes stables ; conformité ↔ enveloppe détecte une dérive ; approbation EIP-712 refuse un intent modifié ; politique sans accès LLM | `policy_v1.yaml`, `envelope_drift_report.json`, verdicts | `test_policy.py` (+8), `test_policy_zodiac_conformance.py` |
| **W5** | receipt vérifié bout en bout ; 5 runs tracés ; rejets chaîne en `0x0` documentés ; `verify_addresses.py` vert avant chaque run ; aucun secret | reçus + `audit.jsonl` + `evidence/demo_runs/*` | `test_execution.py` (+), `test_env_hygiene.py` |
| **W6** | `OFFLINE_PASS` sur paquet zippé ; `--mutate-test` 6/6 ; dossier re-rendu identique ; `HASHES.txt` complet ; zéro `dangling_refs` | `verify_report.json/.md`, `HASHES.txt`, `bundle_digest` | `test_verify_t10.py`, `test_audit_flux.py` |
| **W7** | 6 tests de perte ; comparateurs reproductibles ; KAT calibration exacts ; gate de gel bloque `--set eval` ; rejeu 2 modes étiquetés | `evaluation_report.{json,md}`, `frozen/*.sha256` | `test_evaluation_*.py`, `test_replay_*.py` |
| **W8** | UI locale servie hors-ligne, 12 écrans avec mode + horloge ; docs finaux livrés ; registre ADR sans trou ; 4 documents sans terme interdit | pages HTML autonomes, `dist/docs/`, `docs/decisions/` | `test_ui_routes.py`, `test_adr_index.py` |

**« v1 terminée » (définition d'ensemble)** : les 8 lignes ci-dessus vertes **en même temps**, la démo complète rejouable hors-ligne, le paquet d'audit vérifié par une personne qui n'a pas écrit le code (test T10 par un tiers), et les documents finaux cohérents avec les ADR.

---

## 7. Risques & mitigations

| # | Risque | Impact | Signal précoce | Mitigation | Propriétaire |
|---|---|---|---|---|---|
| R1 | **Panne d'un fournisseur LLM** (503, quota, indisponibilité) | boucle agent bloquée | erreurs d'appel répétées, latence | second modèle dès v1 (critique cross-modèle) ; **journal de réponses** → rejeu sans appel ; arrêt fail-closed borné ; sauvegarde incrémentale des artefacts | P1 |
| R2 | **Versionnage des modèles API** (IDs redirigés ou invalides) | reproductibilité détruite | ID inconnu au smoke test | IDs épinglés + date de vérification dans `config/models.json` ; test de fumée d'ID ; reproductibilité portée par le journal, pas par l'ID | P1 |
| R3 | **Chemin critique wallet / faucet testnet** | pièce ⑥ manquante (preuves d'exécution) | wallet non financé à J-2 | kit de démo prêt à l'avance ; robinets gratuits ; montage la veille ; **repli** : vidéo en REPLAY-JOURNAL + reçus ajoutés dès exécution | P4 + équipe |
| R4 | **Deadline 20/10 15 h 59 UTC** (+ clôture anticipée des inscriptions) | soumission incomplète | retard > 0,5 j sur Sprint 0 | priorité soumission > construction ; tampon interne 19/10 ; liste opposable §3.2 ; inscription gérée en parallèle | P5 |
| R5 | **Budget API** dépassé (plafond 20 $/mois) | agents à l'arrêt | compteur de coût | 4 compteurs par décision (0,10 $ max) ; cache de réponses ; coût mesuré 0,013–0,036 $/décision ; replay gratuit | P1 |
| R6 | **RPC public instable** ou limite de débit | collecte/lectures bloquées | timeouts, 403 sans User-Agent | deux endpoints avec bascule, retries bornés, cache local ; re-vérification des adresses avant chaque run ; arrêt si écart | P2 |
| R7 | **Suite de tests qui rougit** (régression) | tout merge bloqué | CI rouge | CI obligatoire, revue de PR, revert le jour même, aucun test désactivé | tous |
| R8 | **Fuite de secret** | disqualifiant (et dangereux) | scan CI | clé jetable hors dépôt, jamais loggée, `.gitignore`, scan bloquant, destruction après démo | P4 |
| R9 | **Point de défaillance mono-personne** | glissement non absorbable | une PR attend > 2 j | backup déclaré par workstream (§4), contrats écrits, docs d'exécution à jour | P5 |
| R10 | **Contamination DEV/EVAL** (seuils réglés en regardant EVAL) | évaluation sans valeur | un seuil modifié après inspection | embargo paramètres/données/inspection + **calibration croisée** ; gate mécanique `--set eval` (hashs + lock + chevauchement) | P3 |
| R11 | **Reorg / réinitialisation du testnet** | preuves invalidées | receipt orphelin | anti-reorg 2 blocs en démo (safe+finalized en prod) ; escalade humaine après reorg ; capture des preuves tôt | P4 |
| R12 | **Dérive politique ↔ enveloppe on-chain** (règle d'un côté seulement) | exécution hors enveloppe ou refus silencieux | test de conformité rouge | test offline à chaque PR + `run_drift_check.py` avant chaque fenêtre d'exécution ; SAFE MODE si non vérifiable | P4 |
| R13 | **Écart entre le plan et le réel** (un lot « fini » non démontrable) | dépendances cassées | jalon de sprint non atteint | définition de « terminé » par workstream (§6) ; un lot sans commande ni artefact n'est pas fini ; révision de planning en fin de sprint | P5 |

**Règle de remontée** : un risque qui se matérialise se **journalise** (date, signal, décision prise, effet) — pas de résolution silencieuse. Un repli utilisé est écrit dans le dossier de décision et dans le rapport d'évaluation.

---

## 8. Annexe A — Inventaire « intégrer vs construire » (posture actée)

Principe acté par l'équipe : **intégrer ce qui existe et est éprouvé** ; ne pas réinventer ; ne refuser une brique que si elle est fermée, incompatible ou morte.

| Brique | Intégrer / Construire | Usage dans ORVYREN | État |
|---|---|---|---|
| Safe{Wallet} + Zodiac Roles v2 (module, bytecode identique Ethereum/Base/Base Sepolia) | **Intégrer** | enveloppe on-chain, second verrou, kill switch `assignRoles(false)` | adresses mesurées ; montage à faire (W5) |
| Chainlink (feeds rsETH capped, USDC/USD) | **Intégrer (lecture)** | source unique par quantité, divergence oracle/marché | couche données [FAIT] |
| DeFiLlama, Binance, Bitstamp, Kraken, OKX | **Intégrer (lecture)** | séries de prix et d'offre du corpus | [FAIT] |
| Blockscout | **Intégrer (lecture)** | concentration, recoupements on-chain | utilisé en W3-C |
| Curve `get_dy` (ladder) , Aave Pool (lectures, `isFrozen`, `supplyCap`) | **Intégrer (lecture)** | décote **réalisable**, saturation, gel | [FAIT] (W3-A) |
| RPC d'archive publics (drpc, blastapi) | **Intégrer** | lecture point-in-time 2021→2026 | [FAIT] (W3-A) |
| Graphe de collatéral typé (record de relation, horloges, provenance, labels épistémiques) | **Construire** | notre nouveauté : la substance du projet | base SQLite [FAIT], v1 à compléter (W1) |
| Registre d'hypothèses + RDOF (« réfutation d'abord, coût mesuré ») | **Construire** | notre nouveauté : la décision vérifiable | v0 [FAIT], RDOF à livrer (W3) |
| Double verrou (politique + mandat on-chain) | **Construire** | différentiateur de sécurité | politique [PARTIEL] (W4) |
| Audit 3 flux + vérificateur tiers T10 | **Construire** | ce qui rend la promesse vérifiable | à livrer (W6) |
| Replay 2 modes + harnais DEV/EVAL | **Construire** | honnêteté de mesure | à livrer (W7) |
| `eth-account` (signature) | **Intégrer (exception isolée)** | service signataire, seul lecteur de la clé | à isoler (W5, §1.4) |
| Postgres/Neon + `pgvector`, SQL/PGQ | **Option ultérieure** (post-concours) ; SQLite pour le concours | migration contenue dans `store.py` | décidé, exécution après |
| EAS (attestation) | **Conditionnel / reporté** | ancrage externe si run E + T10 verts avant la date interne | conditionnel (W6/L6.6) |
| Recherche sémantique (embeddings) | **Hors chemin de décision** | appoint documentaire, sorties étiquetées | optionnel, jamais un fait |
| Base graphe externe (Kuzu archivé, Neo4j) | **Écarter** | aucune plus-value à notre échelle + 2ᵉ base à synchroniser | écarté, raison au doc 3 |

**Livrable de planification** : cet inventaire est mis à jour à chaque sprint par le coordinateur ; une brique qui change de colonne passe par un ADR.

## 9. Annexe B — Récapitulatif des estimations et jalons

| Workstream | Estimation | Propriétaire | Jalon de fin |
|---|---|---|---|
| W1 Données & Graphe | 8,5 j-h | P2 | requêtes noyau + INV-PIT verts (S1→S2) |
| W2 Agents & Orchestration | 11 j-h | P1 | 2 journaux, budgets, journal hashé (S1) |
| W3 Décision & RDOF | 10 j-h | P3 | décision en une commande + essai RDOF (S2) |
| W4 Politique & Sécurité | 8,5 j-h | P4 | 14 règles + conformité/dérive (S2) |
| W5 Exécution & Démo testnet | 9,5 j-h | P4 (+P2) | 5 runs + reçus (S0 partiel, S4 complet) |
| W6 Audit & Vérificateur | 9 j-h | P5 | `OFFLINE_PASS` + 6/6 mutations (S3) |
| W7 Évaluation & Replay | 8 j-h | P3 (+P1) | rapport + replay 2 modes (S3→S4) |
| W8 UI locale & Coordination | 7 j-h + continu | P5 | 12 écrans + docs finaux (S4) |
| **Total** | **≈ 71,5 j-h** | 5 personnes | 4 sprints après le Sprint 0 |

| Jalon | Date | Critère |
|---|---|---|
| J0 — soumission | 19/10 (tampon) · **20/10 15 h 59 UTC** (limite) | pièces ①–⑥ prêtes ; §3.2 satisfait |
| J1 — agents + graphe v1 | 27/10 | `run_agents.py --replay journal` + enum du graphe |
| J2 — décision & règles | 03/11 | décision → 14 règles en une commande |
| J3 — audit & replay | 10/11 | T10 vert + rejeu k=10 identique |
| J4 — démo complète & EVAL | 17/11 | démo hors-ligne + rapport EVAL publié avec limites |

## 10. Annexe C — La première semaine, jour par jour (Sprint 0)

| Jour | P1 | P2 | P3 | P4 | P5 |
|---|---|---|---|---|---|
| J0 (15/10) | lecture des contrats B1 §3.4 (journal), maquette `agent_journal` | revue record 17 champs (B2 §3.0) | **loss.py + 6 tests** | préparation kit de démo (adresses, checklist) | gel : rassemble G1–G6, prépare `frozen/` |
| J1 (16/10) | squelette registre d'hypothèses | `test_graph_relations.py` (enum) | **comparators.py + tests** | scripts d'hygiène + `verify_addresses.py` | doc : squelette de rapport `N=0` |
| J2 (17/10) | `.gitignore`/scan CI secrets (avec P5) | horloges + INV-PIT | **calibration.py + KAT** | montage Safe/Roles (ou attente wallet) | 5 prévisions gelées DEV + hash |
| J3 (18/10) | boucle bornée (4 compteurs, 5 arrêts) | requêtes Q1–Q3 | prévisions DEV (suite) | préflight + répétition à blanc des runs | assemblage pièces EN ①/⑤ |
| J4 (19/10) | tests de budget | requêtes Q4–Q8 | gate de gel (`--set eval` refuse) | **runs chaîne si wallet**, sinon plan daté | revue finale, tampon de soumission |
| J5 (20/10) | — | — | — | — | **soumission avant 15 h 59 UTC** ; figer l'état |

**Définition de fin du Sprint 0** : §3.2 satisfait, et rien de l'embargo EVAL n'a été franchi (`grep` sur `frozen/` + journal de exécutions).

---

*Références internes : `FREEZE_V2.md` (autorité) · `ARCHITECTURE_V1.md` §2-3 (modules et interfaces) · `ORVYREN_DOC2_TECHNIQUE_COMPLET.md` · `ORVYREN_DOC3_PROPOSITIONS_ET_ECARTES.md`. Les études et plans de recherche d'origine (B1→B9, W2/W3, questionnaire de gel) sont archivés hors dépôt — voir `README.md` §Archives.*
