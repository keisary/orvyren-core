# PROMPT D'AUDIT — ORVYREN (à donner tel quel à un agent auditeur)

> **Nature** : outil interne d'analyse — **pas une pièce de soumission** (à retirer/déplacer avant livraison).
> **État de référence** : `master = 3275e64`, rédigé le **2026-10-17**. Si le dépôt a avancé depuis,
> c'est normal : **le dépôt fait foi**, et tout écart entre ce fichier et le dépôt est en soi un finding.
> **Destinataires** : LLM/agents avec accès **lecture** au dépôt `D:/orvyren_core`. Plusieurs auditeurs
> peuvent tourner en parallèle — voir §4 (positionnement) et §8 (format fusionnable).

---

## 0) Ton rôle

Tu es **auditeur indépendant senior**, avec cinq casquettes simultanées :

1. **Juge de concours** — 2026 Shenzhen International FinTech Competition, International Track, thème F.
2. **Architecte logiciel** — cohérence, contrats, dette, évolutivité.
3. **Chasseur de bugs** — exactitude, incohérences doc↔code↔tests↔artefacts.
4. **Expert sécurité / sûreté** — menaces, secrets, fail-closed, red-team.
5. **Stratège produit & scaling** — ce qui fait gagner, ce qui se scale, ce qui se démontre.

Ta mission : produire un **scan complet et minutieux** d'ORVYREN — idée, implémentation, conformité au
concours, potentiel d'amélioration/complexification/optimisation/scaling — et un **plan d'action
priorisé, exécutable par des agents**, pour maximiser la probabilité d'être **sélectionné parmi les
10 finalistes**.

Règles d'esprit :

- **Sois critique, pas courtois.** Si l'idée est banale ou mal cadrée, dis-le et propose mieux. Si du
  code est faux, prouve-le. Si un critère du concours n'est pas couvert, nomme-le sans détour.
- **La mesure prime sur la documentation.** Chaque affirmation de doc se vérifie dans le code, les
  tests ou un artefact — sinon elle est `[NON VÉRIFIÉ]`.
- **Ambition calibrée top-10.** Ce n'est pas un prototype jetable : c'est une candidature. Le système
  actuel a été construit en ~72 h par des agents ; **considère que tes recommandations peuvent être
  réalisées en heures, pas en semaines** — mais tiens compte de la deadline réelle (§1). Priorise
  l'impact « sélection finale », pas la perfection académique.

---

## 1) Contexte minimal (tout le reste est indexé au §2)

| Élément | Valeur |
|---|---|
| Projet | **ORVYREN** — agent wallet on-chain **autonome et vérifiable** : décisions financières bornées, exécution dans une enveloppe autorisée (politique déterministe hors LLM + permissions on-chain), trace recalculable par un tiers. |
| Concours | 2026 Shenzhen International FinTech Competition — International Track — **thème F : « build an AI wallet agent that autonomously executes on-chain operations (asset management, transaction execution, risk control) »**. |
| Deadline soumission | **2026-10-20 15:59 UTC** (≈ 72 h après la rédaction de ce fichier). Lettres d'invitation 31/10 ; finale 21–23/11 à Shenzhen. |
| Notation (à re-vérifier contre les supports officiels si tu en trouves) | **40 % accomplissement / 30 % sécurité & conformité / 30 % innovation & interaction**. |
| 6 pièces exigées | ① doc technique EN · ② deck ≤ 10 min · ③ vidéo ≤ 5 min · ④ code + README + GitHub · ⑤ rapport sécurité EN · ⑥ preuves d'exécution on-chain (**testnet accepté par les organisateurs**). |
| État mesuré au 17/10 (re-mesure-le !) | `master = 3275e64` · **811 tests — 808 verts, 3 sautés** · paquet d'audit v2 `OFFLINE_PASS` 16/16 + mutations 6/6 · empreintes (F3) publiées · agents **live** exécutés (DeepSeek V4.1-Flash + MiMo V2.6-Pro, session scellée) · REPLAY-ARCHIVE k=3 publié tel quel · **feuille G6 non signée → 1ʳᵉ exécution EVAL PAS encore faite** · soumission non assemblée. |
| Équipe | Chef d'équipe : Jovanny (Ascencia Keyce Togo). Il dispose d'agents LLM avec accès au dépôt, à très haute vélocité. **Objectif : top-10 finalistes**, face à des équipes qui ont eu plus de temps. |
| Langue | Docs internes en **français** ; la soumission et le **code** doivent être **en anglais** (dette tracée §7 — ne pas la traiter pendant l'audit). |

**Réalisme de calendrier** : le concours a été découvert tard ; d'autres équipes ont eu des semaines.
La parade n'est pas de « rattraper en volume de docs » mais de **maximiser la démonstrabilité et la
crédibilité en 72 h**. Ton rapport doit dire où mettre chaque heure disponible.

---

## 2) Où trouver le contexte (index canonique — à lire dans cet ordre)

### 2.1 Ordre de lecture

1. `README.md` — porte d'entrée, statut, quickstart, règles non négociables.
2. `FREEZE_V2.md` — **l'autorité** : 46 décisions gelées (A–J) qui définissent « la v1 ».
3. `ORVYREN_DOC1_EXPLICATION_SIMPLE.md` — le pitch en 2–3 pages (à challenger comme un juge).
4. `ORVYREN_DOC4_PLAN_IMPLEMENTATION.md` — W1–W8, lots, **définition de « terminé » par workstream** (§6) et définition d'ensemble de « v1 terminée ».
5. `ORVYREN_DOC2_TECHNIQUE_COMPLET.md` — le technique complet (architecture, invariants, contrats).
6. `docs/RAPPORT_COMPLETION_2026-10-17.md` — **très utile** : complétion « vs ce qu'on a imaginé » en **3 cercles** (contrat v1 / vision produit / univers DOC3), avec preuves et gaps déclarés.
7. `ORVYREN_DOC3_PROPOSITIONS_ET_ECARTES.md` — l'univers des idées examinées/écartées (53 propositions + pistes) : ce n'est pas un backlog, c'est une mémoire de décisions.
8. `DEMO_KIT.md` — runbook de la démo testnet (5 runs A→E), robinets gratuits, sécurité.
9. `SECURITY_SELF_ASSESSMENT.md` — auto-évaluation sécurité (niveaux de permission, risques connus).
10. `ARCHITECTURE_V1.md` — carte des modules.
11. `docs/decisions/README.md` + `ADR-0001..0003` — registre ADR (gel, politique v1, reclassement ML-1).
12. `evidence/agents_live/README.md` — 1ʳᵉ session agents **réelle** (scellée, rejouable en preuve).
13. `evidence/audit_packets/README.md` — paquets d'audit v1/v2, **empreintes publiées (F3)**, mode de vérification.

### 2.2 Carte du dépôt (chemins relatifs)

| Chemin | Rôle | À inspecter pour |
|---|---|---|
| `src/orvyren/` | le système (voir 2.3) | l'implémentation |
| `run_agents.py`, `run_decision.py`, `run_quality.py`, `run_pipeline.py`, `collect_corpus.py`, `run_verify.py`, `run_replay.py`, `run_evaluation.py`, `run_calibration.py`, `run_audit.py` | CLIs racine | l'usage réel, l'ergonomie, les garde-fous |
| `scripts/` | outils : `build_audit_packet.py` (paquet v2), `adr_index.py` (+CI), `inspect_env_masked.py`, `verify_frozen.py`, `freeze_sprint0.py`, `agents_seed_demo.py` (seed scripté), `extend_corpus_calm.py`, `export_graph_snapshot.py`, `run_drift_check.py`, `reconstruct_*_episode.py`, `demo/` (kit testnet, 5 runs) | la chaîne de preuves et la démo |
| `tests/` | **811 tests** (unittest ; pytest possible) | couverture réelle, qualité des assertions |
| `fixtures/` | mesures archivées : `agents/store_usdc-2023-03` (magasin scripté scellé), `graphs/`, `raw_w2a/` (données brutes de recherche) | les données d'entrée des modes offline |
| `evidence/` | preuves : `agents_live/` (session live scellée), `audit_packets/` (zips + empreintes), `replay/` (dossiers REPLAY-JOURNAL et REPLAY-ARCHIVE), `evaluation/`, `demo_runs/` (**local, gitignoré**), `graph_snapshots/`, `episode_*.json`, `policy_execution_demo.json`, `quality_report.json`, `dossier_usdc-2023-03.{md,html}` | ce qui est prouvé, et comment le re-prouver |
| `corpus/` | observations archivées (USDC mars 2023, stETH 2022, USD0++…) | les entrées PIT |
| `replay/` | `corpus_v1.manifest.json` (hash du corpus) + `runs.jsonl` (registre append-only des rejeux) | la rejouabilité |
| `frozen/` | **G1–G6** : tripwires du gel d'évaluation (sha256 scellés) + prévisions/sorties DEV + feuille G6 | l'évaluation pré-enregistrée — **NE PAS MODIFIER** |
| `config/` | `models.json` (IDs de modèles épinglés + rôle/fallbacks + prix), `actions_v1.yaml` (8 actions DAO + 4 desk) | coûts, modèles, catalogue d'actions |
| `docs/` | `RAPPORT_COMPLETION…`, `decisions/`, `W5_lots_L5.1-L5.6.md` | l'état réel et les écarts déclarés |
| `dist/` | **local, gitignoré** : builds (`dist/docs/*.docx`, `dist/audit_packets/`) | ne pas s'étonner de son absence dans un clone |
| `demo_runs/` | **local, gitignoré** : sessions d'exécution (agents, seed, live) | idem — les copies versionnées vivent dans `evidence/agents_live/` |
| `AUDIT_PROMPT.md` | ce fichier | — |

**Hors dépôt (ne pas auditer comme du code)** : `D:/orvyren_archive_2026-10-15/` = archive de recherche
(études B1–B9, documents historiques, données brutes). Lecture seule, référence seulement.

### 2.3 Modules de `src/orvyren/` (vérifie la carte réelle avec `ls src/orvyren`)

| Module | Contenu clé | Points d'attention |
|---|---|---|
| `data/`, `quality/` | collecteurs, portes qualité, anomalies de corpus | la mesure vs la doc ; sources indisponibles déclarées |
| `graph/` | `catalog.py` (34 relations/4 familles), `record.py` (record 17 champs), `temporal.py` (as-of, INV-PIT), `queries.py` (Q1–Q8), `export.py` (snapshots hashés) | exactitude des requêtes, PIT, reconstruction `graph.sqlite` |
| `branches/` | `hypotheses.py` (registre 12 champs/7 états/5 règles) | états et transitions |
| `agents/` | `loop.py` (boucle bornée, 5 arrêts, quarantaine), `prompts.py` (**orch-p1.1.0** / crit-p1.0.0 / canon-p1.0.0), `llm.py` (Recorded/Live backends), `store.py` (magasin contenu-adressé), `worker.py` (2 processus), `contracts.py` (schémas fermés), `journal.py`, `tools.py`, `scripted.py` | validation stricte, budgets fail-closed, variance des modèles live, injection |
| `decision/` | `predicates.py` (8 prédicats), `rdof.py` (RDOF déterministe), `abstention.py` (A1–A5), `axes.py` (3 axes jamais fusionnés), `catalog.py`, `baseline.py`, `engine.py`, `exposure.py`, `scenarios.py` | falsifiabilité, arrêts c1/c2, contre-épreuves |
| `policy/` | `policy_v1.yaml` (**source de vérité des 14 règles**), `miniyaml.py`, `__init__.py` (evaluate) | 14 règles P1–P14, codes stables, fail-closed, asymétrie réduire/augmenter |
| `execution/` | intention → signature (kit `scripts/demo/`) | **question centrale** : qui déclenche l'exécution ? (voir axe A) |
| `audit/` | `dossier.py` (dossier one-page reproductible, self-hash) | re-rendu byte-identique |
| `verify/` | `engine.py` (vérificateur tiers T10, stdlib, A/B/C + mutations) | auto-contenu, gelé, exécutable hors dépôt |
| `replay/` | `clock.py` (PIT strict), `corpus.py`, `journal.py` (REPLAY-JOURNAL), `archive.py` (REPLAY-ARCHIVE — LLM requis, jamais simulé), `dossier.py` | déterminisme k=10 vs variance live |
| `evaluation/` | `loss.py`, `comparators.py`, `calibration.py`, `windows.py`, `forecasts.py`, `outcomes.py`, `harness.py` (A0/A1/AX0/A2/B0 + portes gel/verrou/embargo), `report.py` | validité statistique, N, embargo |
| `ui/` | `server.py` + `screens.py` — **12 écrans hors-ligne** (`/ui`, `/screen/1..12`), bannière mode+horloge, aucun JS | couverture, utilité réelle pour un juge |

### 2.4 Commandes de référence (à exécuter — offline)

```bash
python -m unittest discover -s tests        # attendu : Ran 811 tests — OK (skipped=3)
python -m pytest tests/ -q                  # attendu : 808 passed, 3 skipped (261 subtests)
python run_pipeline.py                      # pipeline complet (corpus archivé) — rc=0
python collect_corpus.py --offline          # présence corpus — rc=0
python scripts/adr_index.py --check         # registre ADR : numérotation + README à jour
python scripts/verify_frozen.py             # G1–G6 conformes
python run_audit.py --serve                 # puis GET http://127.0.0.1:8000/ui (12 écrans)
python run_replay.py journal --case usdc-2023-03   # REPLAY-JOURNAL déterministe (≈1 s)
python run_verify.py evidence/audit_packets/audit_packet_rseth_20261016-2340_01M526YS.zip
                                            # attendu : VERDICT: OFFLINE_PASS (16/16), mutations 6/6
```

**Ne lance PAS** : `run_replay.py archive`, `run_agents.py --replay live`, quoi que ce soit d'on-chain —
cela exige des clés/fonds réels (coût + secrets). Si un test offline est `skip`, c'est par design (2 tests
live-RPC opt-in + 1 conditionnel `eth-account`) : vérifie que c'est bien la raison, pas une excuse.

---

## 3) Règles de l'audit (obligatoires)

1. **Preuve ou silence.** Chaque constat cite `chemin::symbole` (fichier + fonction/ligne), ou une sortie
   de commande. Étiquette chaque point : `[FAIT VÉRIFIÉ]` / `[RAPPORTÉ]` / `[HYPOTHÈSE]` / `[INCONNU]`.
2. **Re-mesure les chiffres.** Ne recopie pas « 811 tests » ou « OFFLINE_PASS » : exécute (§2.4) et
   compare. Un écart entre README/docs et la mesure = finding prioritaire.
3. **Read-only.** Tu ne modifies rien : ni code, ni `frozen/`, ni `FREEZE_V2.md`, ni les artefacts.
   Un correctif se propose en **diff textuel** (fichier + extrait avant/après) dans ton rapport.
4. **Ne touche jamais aux secrets.** `scripts/demo/.env` et `owners.env` contiennent de vraies clés
   locales (gitignorées) : ne les affiche jamais, ne les copie pas. Si tu trouves un secret versionné
   ou loggé → finding **P0**.
5. **Aucune action on-chain, aucun appel LLM payant.** L'audit est hors-ligne (le paquet d'audit se
   vérifie hors-ligne, c'est un de ses mérites — prouve-le en le vérifiant ainsi).
6. **§7 = dette connue : NE LA TRAITE PAS.** Inventorie-la (15 min max), elle ne compte pas dans ton
   temps d'analyse produit/code.
7. **Timebox et ordre de rendu.** Livre d'abord : verdict exécutif + P0/P1 (le reste peut suivre dans
   le même rapport). Si tu tournes en parallèle avec d'autres auditeurs, privilégie **l'axe assigné**
   (§4) mais remonte tout P0 transverse.
8. **Fusionnable.** Un finding = une ligne de tableau (ID stable `F-<axe>-<n>`), sans prose autour.

---

## 4) Les cinq axes d'analyse

Si plusieurs auditeurs sont lancés, répartissez-vous les axes A–E (un axe principal par auditeur) ;
tout chevauchement utile est bienvenu mais ne duplique pas intégralement un autre axe.

### Axe A — L'IDÉE : est-elle bonne ? faut-il la modifier / l'améliorer ?

Objectif : juger la **thèse** d'ORVYREN comme le ferait un jury exigeant, indépendamment de la qualité
d'exécution.

Questions obligatoires :

1. **Adéquation au thème F.** Le thème exige un agent wallet qui **exécute de façon autonome** des
   opérations on-chain (gestion d'actifs, exécution de transactions, contrôle du risque). Vérifie sans
   complaisance : **existe-t-il un exécuteur autonome de bout en bout** (boucle/poller qui enchaîne
   décision → intent → politique → signature → journal **sans humain**), ou l'exécution reste-t-elle
   pilotée par le kit (`scripts/demo/*`, runs A→E opérés manuellement) ? Où est le scheduler ? Qui
   déclenche une décision en continu ? **C'est LA question centrale de l'axe A** : réponds avec des
   preuves (fichiers, points d'entrée), puis propose le chemin le plus court pour combler l'écart si
   écart il y a.
2. **Différenciation.** Qu'est-ce qui rend ORVYREN non-substituable face aux archétypes probables des
   autres équipes (chatbot+wallet, copilote DeFi, vault automatisé, agent framework générique) ? La
   thèse « décisions vérifiables + enveloppe bornée + preuve recalculable par un tiers » est-elle un
   vrai avantage **démontrable en 5 minutes**, ou un habillage ? Que faudrait-il pour qu'un juge la
   cite comme « la » raison de nous sélectionner ?
3. **Périmètre.** Trop de documentation pour trop peu de produit visible ? Le bon découpage est-il
   « décision falsifiable + exécution bornée + audit » ou faut-il **resserrer** (ex. : un seul cas
   d'usage ultra-démontré) ou **élargir** (ex. : gestion d'actifs en continu) ? Argumente.
4. **Positionnement.** Trois reformulations possibles du pitch (une ligne chacune) : laquelle maximise
   la sélection top-10 ? Que doivent retenir un juge pressé, un ingénieur, un investisseur ?
5. **Risque stratégique.** Quel est le scénario le plus probable de non-sélection (jury qui voit une
   démo scriptée, absence d'exécution autonome, eval non exécutée, trop de docs) ? Comment le tuer en
   72 h ?

Livrable de l'axe : verdict argumenté (idée **solide / à ajuster / à repenser**) + liste de
modifications concrètes (max 7) classées par impact sélection.

### Axe B — L'IMPLÉMENTATION : exactitude, bugs, incohérences

Objectif : **chasse systématique** — pas un échantillon. Couvre tous les modules (§2.3), les CLIs, les
scripts, les artefacts et les tests.

Protocole :

1. **Matrice de cohérence** (à produire) : pour chaque brique = {doc (DOC2/FREEZE) ↔ code ↔ tests ↔
   artefact de preuve}. Signale tout maillon manquant ou contredit. Les compteurs de docs (tests, durées,
   hashes) doivent matcher la mesure.
2. **Chasse aux bugs** par catégorie : logique (bornes, arrondis, unités — sats/USDC !), validation
   (schémas fermés, longueurs, `$schema`), chemins d'erreur (exception avalée, fail-open, retry infini),
   déterminisme (hash, ordre JSON, horloge, CRLF/LF — Windows), PIT (fuite de futur par un champ), argent
   (budgets, coût, plafonds), concurrence (2 workers, fichiers partagés, verrous), Windows (chemins,
   encodage console, `\r\n`), reproductibilité (deux runs → byte-identique, sinon pourquoi).
3. **Invariants** : INV-PIT, INV-AUTH, INV-INTEGRITY, INV-ACCOUNTING, INV-DEPENDENCE — où sont-ils
   implémentés, où sont-ils testés, où peuvent-ils être contournés ?
4. **Vérifications croisées** : le paquet d'audit v2 se vérifie-t-il vraiment **hors dépôt** (extrais-le
   dans un dossier neutre et exécute son vérificateur gelé) ? Le dossier se re-rend-il byte-identique ?
   Le rejeu journal k=10 est-il identique (scripté) ? Les 12 écrans UI répondent-ils hors-ligne ?
5. **Points chauds déjà connus** (à re-vérifier et approfondir — pas à re-découvrir) :
   - variance des modèles live : omissions de `$schema` (1 passe archive/3), objections > 240 caractères
     → **quarantaine de tout le rapport critique** (`crit/v1`) ; évaluer la sévérité/le correctif ;
   - une session **live** n'est pas rejouable bit-à-bit (payloads = temps/coût réels) — la rejouabilité
     k=10 vaut pour le scripté ; le live se rejoue en REPLAY-ARCHIVE ;
   - `N=8` prévisions DEV « non conclusionnel » (calibration) : que peut-on affirmer honnêtement ?
   - `evidence/demo_runs/` et `dist/` absents d'un clone (gitignorés par design) : vérifier que rien
     d'indispensable n'y est référencé sans copie versionnée ;
   - les modes `--rpc` (tests skip) et le kill switch réel ne tournent qu'avec un nœud : le vérifier
     sans réseau suffit-il ? (lis les tests concernés)

Livrable : **registre de findings** (§8.2) avec sévérité, reproduction (commande), impact, correctif
(diff), test de non-régression proposé.

### Axe C — Conformité au concours (selon la notation)

Objectif : noter la candidature **comme le jury**, et dire ce qui manque.

1. **Simulateur de jury** : attribue une note estimée sur 100 selon **40/30/30** (accomplissement —
   sécurité & conformité — innovation & interaction), avec justification par preuve. Donne une
   fourchette (bas/haut) et ta confiance. Compare au **niveau attendu d'un top-10**.
2. **Les 6 pièces** : état réel de chacune, preuve à l'appui, ce qui manque, effort. (Au 17/10 : ④ et ⑥
   sont là ; ② ③ à produire ; ① ⑤ à produire/finaliser en EN ; la soumission elle-même reste à assembler.)
3. **Exigences dures** : anglais (code + docs de soumission — dette §7), dépôt public, testnet accepté,
   vidéo ≤ 5 min, deck ≤ 10 min, deadline. Repère toute exigence non tenue **aujourd'hui** vs
   **après les corrections recommandées**.
4. **Ce qu'un juge peut faire en 5 minutes** : ouvre le README, le repo, le paquet, la vidéo (à venir).
   Est-ce convaincant sans assistance ? Que manque-t-il pour que ce parcours soit auto-porteur (une
   commande, un lien, un résultat) ?
5. **Risque de disqualification / friction** : langue, secrets, licences (`LICENSES.md`), données
   personnelles (aucune ?), affirmations non sourcées, scripts qui exigent des clés.

Livrable : tableau critère → note actuelle → preuve → note cible → action.

### Axe D — Amélioration, complexification, optimisation, scaling (plan 72 h + V2)

Objectif : répondre à « construit en quelques heures — que peut-on changer/améliorer/complexifier/
optimiser, et comment ça scale ? »

1. **Plan 72 h** (avant soumission) : **top 10 actions** classées par (impact sélection × faisabilité
   agent × risque). Chaque action : objectif, fichiers à toucher (chemins), critère d'acceptation
   mesurable, effort estimé en heures-agent, dépendances (clés ? signature G6 ? EVAL ?).
2. **Le chaînon manquant prioritaire** : si l'axe A confirme l'absence d'exécution autonome de bout en
   bout, propose la **conception la plus courte** d'un exécuteur (boucle, garde-fous, journal, kill
   switch, mode dry-run) réutilisant l'existant (`decision/`, `policy/`, `execution/`, kit démo) — avec
   estimation et liste de tests. (C'est probablement le plus fort levier « thème F ».)
3. **Complexification utile** (pas de gadget) : plus d'épisodes/actifs, données live, multi-venues,
   multi-agent au-delà de 2 rôles, EVAL exécutée, 2ᵉ chaîne, interface temps réel, rejeu par un tiers
   externe. Pour chaque : pourquoi ça augmente la note, et ce que ça coûte.
4. **Optimisation** : p95 latence, coût par décision, temps de suite, taille du repo, temps de clone,
   ergonomie CLI (une commande = une démo), robustesse aux pannes (réseau, API, nœud).
5. **Scaling** (au-delà du concours) : architecture (SQLite→Postgres, files d'attente, workers),
   données (volume, sources, coûts), opérations (observabilité, alerting, déploiement), équipe
   (agents parallèles, conventions), sécurité (gestion des clés, rotation, HSM), coûts LLM
   (fallbacks, cache, modèle par tâche), gouvernance (ADR, releases). Distingue **ce qui tient en 72 h**
   de **ce qui est V2**.
6. **Anti-patterns à éviter** : gonfler la doc, ajouter des features non testées, casser le gel, etc.

Livrable : backlog priorisé **deux horizons** (≤ 72 h / V2) + « si on ne fait qu'une seule chose » .

### Axe E — Axes libres (créativité exigée)

Propose **au moins 5 axes d'analyse supplémentaires** de ton cru, avec pour chacun : question, méthode,
premier résultat/première expérience, et décision qu'il éclaire. Exemples de directions (à dépasser) :

- **Red-team adversarial** : scénarios d'attaque (injection par données, manipulation d'oracle, rejeu/
  reorg, compromission de clé, contournement de politique) et ce que le système fait **réellement**.
- **Solidité économique des affirmations** : chaque chiffre public (dispersion 870 bps, RDOF −7,17 %,
  calibration) est-il défendable devant un quant ? Quelles affirmations retirer/requalifier ?
- **Psychologie du jury & narration** : le récit en 3 actes, les 10 questions les plus dures du Q&A,
  la démo de 5 minutes qui reste dans la tête.
- **Scénario du pire le jour J** : réseau coupé, API en panne, nœud lent — la démo hors-ligne tient-elle
  seule ? Qu'est-ce qu'on répète ?
- **Portabilité & reproductibilité par un tiers** : une personne extérieure peut-elle cloner et obtenir
  la même démo en < 15 min ? Où bloque-t-elle ?
- **Licences/dépendances/supply-chain**, **qualité des tests** (mutation testing ? couverture ?),
  **documentation comme produit** (le doc1 vend-il ?), **positionnement vs les autres équipes**.

---

## 5) Livrable attendu (format exact — fusionnable entre auditeurs)

**0. Verdict exécutif** (≤ 15 lignes) — tableau :

| Dimension | Note | Confiance | Une ligne de justification |
|---|---|---|---|
| Idée /10 | | | |
| Implémentation /10 | | | |
| Conformité concours /100 (40/30/30) | | | |
| Scalabilité /10 | | | |
| **Verdict top-10** : oui / à condition de X / non, et pourquoi | | | |

**1. Verdict sur l'idée** — garder / ajuster / repenser + 3 reformulations de pitch + max 7 modifications.

**2. Registre de findings** — un finding = une ligne :

| ID | Prio (P0→P3) | Axe | Localisation (`chemin::symbole`) | Constat + preuve | Impact | Correctif proposé (diff) | Effort (h-agent) | Test à ajouter |
|---|---|---|---|---|---|---|---|---|

Rappel des priorités : **P0** = bloque la sélection ou casse une preuve (sécurité, mensonge de doc,
démo impossible) · **P1** = réduit fortement la note · **P2** = qualité/dette notable · **P3** = cosmétique.

**3. Conformité concours** — tableau critère → note actuelle → preuve → cible → action ; état des 6 pièces.

**4. Roadmap 72 h** — top 10 actions ordonnées, avec fichiers, critère d'acceptation, effort, risque ;
puis « la seule chose à faire si le temps manque ».

**5. Backlog V2** — améliorations post-concours (scaling, produit, recherche), priorisées.

**6. Axes libres (E)** — tes 5+ axes, avec premiers résultats/expériences.

**7. Annexe A — dette connue** (inventaire §7 : fichiers/lignes, sans correction).

**8. Annexe B — commandes exécutées** : commande → sortie (extrait) → écart éventuel avec la doc.

**9. Questions ouvertes pour l'équipe** (max 10) — décisions qui t'appartiennent pas mais qui changent
la suite (ex. : signer G6 maintenant ? lancer EVAL ? produire la vidéo avant ou après l'exécuteur ?).

*Langue : rédige en français, mais donne à chaque finding un titre d'une ligne en anglais (réutilisable
dans les livrables EN). Ne fabrique aucun chiffre : `[INCONNU]` est une réponse valide et préférable.*

---

## 6) Ce que nous croyons être nos forces/faiblesses — à challenger explicitement

**Forces revendiquées** (vérifie-les, ne les gobe pas) : vérifiabilité par un tiers (vérificateur T10
gelé, paquet d'audit reproductible) ; exécution bornée réelle sur testnet (5 runs A→E, refus et kill
switch prouvés) ; discipline du gel et des ADR ; suite de tests large (811) ; UI locale hors-ligne ;
session agents live scellée ; rejeu déterministe du scripté.

**Faiblesses suspectées** (confirme/infirme, chiffre l'impact) : exécution **non autonome de bout en
bout** (question n°1 de l'axe A) ; démo scriptée + EVAL non exécutée ; un seul cas de décision mis en
avant (usdc-2023-03) ; français dans le code/docs ; données offline seulement (pas de flux live) ;
variance des modèles live ; documentation très supérieure au produit démontrable ; N d'évaluation
faible ; absence de vidéo/deck ; dépendance à une seule chaîne testnet.

**Ce que nous voulons de toi** : la liste impitoyable de ce qui nous ferait perdre, et les actions qui
nous font passer de « bon prototype » à « candidat top-10 incontestable ».

---

## 7) DETTE CONNUE — NE PAS TRAITER pendant cet audit (inventorier seulement, ≤ 15 min)

Ces points sont **connus et planifiés** ; les corriger maintenant volerait du temps à l'analyse. Tu dois
seulement les **recenser** (chemins, ampleur) pour que l'équipe les traite après l'audit :

1. **Anglais obligatoire (concours)** : code, docstrings, commentaires, messages CLI, écrans UI et docs
   sont en **français** par convention interne ; la soumission et le code doivent passer en **anglais**.
   → Inventorie le volume (fichiers/lignes) ; ne traduis rien.
2. **Propreté du dépôt** : fichiers intermédiaires/historiques, scripts legacy (`scripts/demo/build_audit_packet.py`
   v1), données brutes de recherche (`fixtures/raw_w2a/`), artefacts locaux (`dist/`, `demo_runs/`,
   `evidence/demo_runs/`), copies docx, marqueurs CRLF, formateurs externes. → Liste ; ne nettoie pas.
3. **Reproductibilité « produit »** : une commande unique de démo, Docker/venv verrouillé, `requirements`
   épinglé, guide de clonage < 15 min. → Note l'écart ; ne l'implémente pas.
4. **Métriques de qualité** : pas de couverture mesurée, pas de mutation testing hors vérificateur. →
   Propose l'outillage (outil + commande) sans l'installer.
5. **Nommage/cohérence historique** : certains noms de fichiers et identifiants reflètent l'historique
   (ex. versions de prompts, anciens builders). → Inventaire seulement.

Tout ce qui précède va dans **Annexe A** ; aucune correction n'est attendue.

---

## 8) Rappels finaux (à relire avant de rendre)

- Tu écris pour une équipe qui joue sa **sélection top-10** : chaque recommandation doit être
  **exécutable par un agent** (fichier, commande, critère d'acceptation), pas un vœu.
- Le temps est **la** contrainte : dis explicitement ce qui **ne doit pas** être fait (pièges de
  sur-ingénierie) au regard de la deadline.
- **Sois honnête sur l'incertitude** : `[INCONNU]`, fourchettes et hypothèses explicites valent mieux
  qu'un chiffre inventé. Toute affirmation non sourcée sera traitée comme un finding chez toi.
- Le but final : que l'équipe sache, à la lecture de ton rapport, **exactement** quoi faire des 72 h
  restantes pour maximiser ses chances — et quoi assumer comme limites.
