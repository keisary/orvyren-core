# ORVYREN — Direction et spécification UI

**Astra · 2026-10-18 · Analyse statique, dépôt en lecture seule**

Périmètre : copie `astra-run3/orvyren-core`. Aucun build, installation, test, serveur ou vérificateur exécuté ; aucune interface rendue ou chronométrée par Astra. Les constats visuels viennent du code. Les résultats d'exécution cités sont ceux des artefacts et rapports livrés, pas des résultats reproduits ici. Les chemins relatifs ci-dessous désignent ce dépôt. Les dimensions, notes et durées de travail proposées sont des choix ou estimations d'Astra, pas des mesures du projet. Échéance fournie dans le brief : **20 octobre 2026, 15:59 UTC** ; les « 45 h » sont l'enveloppe de planification fournie, pas un décompte recalculé.

## 1. Verdict direction

**Oui, le projet est intéressant. La démonstration actuelle ne rend pas encore justice à ce qui est intéressant.** Le moment fort est un agent qui s'arrête, un critique qui explique pourquoi, une politique qui refuse, puis un dossier que le jury peut emporter et vérifier. C'est un produit de contrôle du risque crédible dans son intention. Le nombre de nœuds, les acronymes et le prix d'un appel LLM ne constituent pas à eux seuls une proposition de valeur.

Le meilleur positionnement : **une console de contrôle et de preuve pour les décisions d'un agent wallet**. Utilisateur prioritaire proposé : la personne responsable d'une trésorerie on-chain qui doit comprendre pourquoi une action est proposée, bloquée ou renvoyée à un humain. Sa question est « que puis-je autoriser, sur quelles preuves ? ». Le parcours doit répondre en premier à cette question. Garder banques, rendement, prédiction et catalogues d'actions étendus dans la vision future.

**Le thème F est couvert par les mécanismes, partiellement démontré de bout en bout.** Agents, enveloppe d'autorisation, transfert borné, reçus testnet et vérificateur existent. Mais `--execute` n'a pas été exercé de bout en bout par le système ; les transactions T2 ont été signées par une clé humaine ; le segment d'exécution du scénario rsETH utilise la décision pilote USDC. Ce sont des limites centrales pour un concours « Autonomous On-chain Wallet », pas des notes de bas de page. Le testnet accepté, selon `FREEZE_V2.md` §0, ne transforme pas une exécution humaine en exécution autonome. Sources : `docs/SUBMISSION_SCOPE_AND_GAPS.md`, G-12/G-13 ; `evidence/policy_execution_demo.json`, `mode`.

**Ce qui accroche en dix minutes :** une contradiction concrète, une abstention compréhensible, les faits précis qui permettraient de changer d'avis, un refus hors LLM, puis la vérification hors ligne. **Ce qui décroche :** les trois couches d'acronymes, les cartes uniformes, un graphe sans question, des chiffres minuscules, et surtout le passage silencieux d'un cas à un autre. Le frontend présente aujourd'hui USDC dans Decision pendant que le script promet rsETH ; son « LIVE » décrit un transport qui rejoue des journaux. Ce décalage peut coûter plus cher que le manque d'une fonctionnalité.

La franchise du registre des gaps est une force. Elle ne suffit pas lorsque le scénario oral réintroduit des conclusions que le critique conteste lui-même : retraits supposés bloqués par `isFrozen`, divergence de prix mal datée, réfutation présentée comme une découverte des agents alors que le générateur de scénario fixe les verdicts. Il faut exploiter ces objections comme démonstration du contrôle, pas raconter qu'elles ont déjà été résolues.

**Verdict Astra : 6/10 pour la soumission dans son état lisible aujourd'hui.** Note éditoriale, sans prétention statistique : direction forte, preuves de composants substantielles, intégration et récit trop composites. Je ne donne aucun « top X % » sans connaître les concurrents. Je conserverais l'architecture et consacrerais le temps restant à la justesse des raccordements et à une interface lisible. Je ne tenterais pas de fabriquer à J-2 la preuve d'autonomie manquante.

## 2. Forces, faiblesses et risques

### 2.1 Ce que les preuves permettent de dire

Dans ce tableau, **prouvé dans le dossier** signifie « code et/ou artefact inspectable soutenant l'affirmation ». Cela ne signifie ni validation indépendante par Astra, ni aptitude à la production.

| Sujet | Niveau et constat | Conséquence produit / limite | Source |
|---|---|---|---|
| Séparation raisonnement / autorisation | Prouvé dans le dossier : politique fail-closed, modes explicites ; scénario avec `DENY`, `BALANCE_UNREADABLE`, `AGENT_NOT_MEMBER`, zéro signature | Bon garde-fou. Un refus pour état illisible ne démontre ni un contrôle de risque financier correct, ni un transfert autonome réussi | `docs/SUBMISSION_SCOPE_AND_GAPS.md` §Delivered 5, G-12 ; `evidence/scenario_rseth/scenario_report.md` §execution |
| Budget réel | Mesure publiée : **9 appels LLM, 7 outils, 59,781 s, 0,03968193 USD** pour le run rsETH archivé ; plafonds **30 / 12 / 600 s / 0,10 USD** | Un exemple de coût borné, pas un tarif universel ni une distribution de latence. Le badge constant « ≈ $0.04 per full run » doit disparaître | `evidence/scenario_rseth/outcome_orchestrator.json`, `budget_used` ; `evidence/scenario_rseth/run.json`, `budget` ; `LiveScreen.tsx` |
| Critique et abstention | Prouvé dans le dossier : arrêt `ARRET-3`, état orchestrateur `ABORTED`, critique `INCOHERENTE`, escalade `REQUIRE_APPROVAL`, liste de recherches manquantes | Le système sait exposer un échec d'instruction. Ne pas recolorer `ABORTED` en succès pour rendre la démo agréable | `evidence/scenario_rseth/{outcome_orchestrator,run_outcome}.json` ; `decision/abstention_rseth-2026-04.json` |
| Provenance | Portes d'admission de claims livrées ; côté critique, porte stricte différée et référence absente du paquet dans une graine scellée | Dire « claims gated by observed references ». Éviter « toutes les références sont validées » | Registre de périmètre §Delivered 1, G-6 ; `docs/ECARTS_REGISTRE.md`, AC-N1/N2 |
| Chaînage | `run_id`, parenté et manifestes existent ; API des journaux agents compare tête recalculée et tête enregistrée | Identité et intégrité ne prouvent pas que deux cas ont la même signification financière | `src/orvyren/api/artifacts.py::verify_journal_chain` ; G-13 |
| Paquet tiers | Rapport publié : v2, **47 fichiers**, `OFFLINE_PASS`, **16/16 contrôles**, **6/6 mutations** détectées | Excellente pièce de démonstration. Prouve les contrôles définis, pas la vérité des sources, le gain financier ni une relecture RPC faite aujourd'hui | `evidence/audit_packets/README.md` |
| Testnet | **13 reçus**, **1 exécution conforme**, **12 tentatives forcées refusées on-chain** ; rapport distingue aussi **6 refus hors chaîne** | Les reverts délibérés sont une preuve utile des verrous ; les reçus ne sont pas ceux de l'abstention rsETH du 18 octobre | `evidence/demo_chain/README.md` ; `evidence/demo_runs/rseth/report.md` ; G-12/G-13 |
| Graphe | Mesures archivées : **16 174 nœuds, 12 937 relations, 15 000 événements** ; Q1 **81,6 ms p50**, Q4 **25,3 ms**, Q7 **10,6 ms** | Dimension et latences d'une base locale déterminée, pas de n'importe quel clone ; pas une mesure de fluidité WebGL. Horodatages d'événements interpolés entre bornes de chunks, selon les notes du benchmark | `evidence/bench_graph_aave.json` ; `evidence/ui_snapshot.json` |
| Couverture du graphe | Déclarée et inspectable : Q2 `NO_PATH`, Q8 `NOT_INGESTED`, pas de `LIQUIDATED_IN` dans le slice ; base de repli **520 observations**, schéma v2 | L'absence de données n'est pas absence de risque. Le graphe Aave Base ne doit pas sembler être l'enquête rsETH Ethereum | G-4/G-14 ; `README.md`, limites ; `docs/RUNBOOK_DEMO.md` §4 |
| Évaluation | EVAL décision-gain **N=0**. Mini-benchmark courant : **12 runs scorés**, un épisode réel et un placebo synthétique, répétitions A2 en replay | Aucun gain financier ou avantage des agents mesuré. N≥100 est une porte du protocole, pas une garantie suffisante de puissance statistique | G-1/G-9 ; `evidence/benchmark_ab/report.md` |
| Tests | README : **1 418 tests, 3 sautés**, et pytest **1 415 passed + 289 subtests** ; périmètre et script : **1 411** au commit `b8f8bd3` | Résultats publiés à réconcilier avec leur version. Ne pas additionner tests et subtests. Un volume de tests n'atteste pas le parcours écran par écran | `README.md` ; `docs/SUBMISSION_SCOPE_AND_GAPS.md` §Delivered 13 ; `frontend/package.json` ; registre AF-10 |
| Valeur commerciale et opérations | Non mesurées dans les pièces prioritaires : adoption, temps gagné, pertes évitées, disponibilité, performance UI sur le poste jury | Ne pas inventer ROI, capacité de production ou supériorité. Ces questions restent après le concours | Absence de mesures correspondantes dans les sources ci-dessus |

### 2.2 Défauts précis qui peuvent casser la démonstration

**A. Le scénario promis n'est pas raccordé à l'écran Decision.** `DecisionScreen.tsx` interroge explicitement `api.decision("usdc-2023-03")`. `artifacts.decision_case` ne lit que `evidence/decision_<case>.json`, alors que l'abstention rsETH est dans `evidence/scenario_rseth/decision/`. La politique affichée vient de `evidence/policy_execution_demo.json`, pas du DENY du scénario. Modifier le seul titre ou ajouter un sélecteur ne résout pas cela. Le troisième axe peut en outre reprendre le verdict du premier cas de politique si le champ manque : cette substitution implicite est à supprimer.

**B. Le run rsETH n'est pas découvert à son emplacement livré.** `_run_roots` dans `src/orvyren/api/artifacts.py` énumère les dossiers `demo_runs/agents*` et `evidence/agents_live`, pas `evidence/scenario_rseth/agents_session`. `LiveScreen` prend le premier run disposant d'un journal, sans choix explicite du cas jury. Le hub charge une liste enregistrée et la reboucle ; il ne lance pas le pipeline et ne suit pas automatiquement un nouveau fichier de run. Conclusion statique : le run exécuté dans un terminal ne devient pas nécessairement le run montré à l'écran. Ne pas promettre le streaming des nouvelles réflexions sans raccordement supplémentaire.

**C. Un défaut de vérification dans l'API Audit mérite une correction ciblée.** Dans `artifacts.py::_verify_hashed_jsonl`, la boucle recalcule `head = digest(strip(row))`, puis vérifie ce résultat au tour suivant via `prev_hash`. À la dernière ligne, il n'y a plus de tour suivant, et la tête recalculée n'est pas comparée au `record_hash` stocké ; le retour `head` utilise `previous`, la tête stockée. Par lecture du code, une modification du seul payload final peut donc échapper à cette fonction. **Constat statique, non reproduit par un test ici.** Cela concerne le résumé de chaîne d'exécution de l'API ; ne pas l'étendre sans preuve à `verify_journal_chain`, qui compare les têtes, ni au vérificateur T10 du ZIP. Corriger la comparaison de chaque digest à son hash enregistré ; demander à l'implémenteur un test ciblant la dernière ligne. En attendant, retirer le `VERIFIED` global de cette carte, sans cacher le problème.

**D. Le récit rsETH contient précisément les erreurs que son critique signale.** HYP-001 affirme que `isFrozen` bloque les retraits ; `build_case_abstention` en déduit même qu'aucun transfert autonome n'est possible. Le bit observé ne prouve pas cette conséquence. La documentation Aave distingue freeze, qui bloque de nouveaux supply/borrow, et les opérations de sortie encore possibles sous leurs autres conditions ; le code V3 `validateWithdraw` ne teste pas `isFrozen`. Cela ne démontre pas qu'un retrait rsETH particulier aurait réussi à la date historique : il faut encore établir l'état exact, la liquidité et les contraintes du compte. Sources internes : `evidence/scenario_rseth/run_outcome.json`, premier finding ; `scripts/run_scenario_rseth.py::build_case_abstention`. Sources primaires : [Aave — Governance](https://aave.com/docs/ecosystem/governance), [Aave V3 — ValidationLogic](https://raw.githubusercontent.com/aave/aave-v3-core/master/contracts/protocol/libraries/logic/ValidationLogic.sol). Copie autorisée : **“Reserve freeze observed. Withdrawal availability was not established.”**

**E. La réfutation HYP-004 n'est pas entièrement une découverte du run live.** `build_case_abstention` assigne `REFUTED` si la fixture porte `counter_intuitive`, et `INCONCLUSIVE` sinon ; il rattache la référence `REFUTING_REF`. Les pistes de recherche viennent de `CASE_PREDICATES`. C'est un dossier de scénario construit de manière déterministe à partir de faits et d'issues enregistrées ; ce n'est pas la preuve que l'agent a trouvé seul ces verdicts et ces pistes. La critique dit même que la mesure d'utilisation est absente des références observées par le run. Conserver la démonstration réflexive générale, mais présenter cette carte comme **“Scenario assessment”**, distincte de **“Agent outcome”**. Sources : script précité ; `evidence/scenario_rseth/run_outcome.json`, finding HYP-004.

**F. Markets rend des unités incomparables sur les mêmes axes.** `MarketsScreen.tsx` regroupe `price` et `discount`, puis `exposure` et `signal`. Pour stETH, cela mélange ETH et bps ; pour rsETH, quantités de plusieurs actifs et ratios. `PriceChart.tsx` n'assigne pas d'axe par unité. La palette est réindexée après filtrage : décocher une série peut changer les couleurs restantes sans changer sa légende. Ce sont des erreurs de lecture, pas seulement de style.

**G. Le chiffre de marché et la courbe oracle ne forment pas une série synchronisée.** Le script rapproche 2 526,76 USD et 1 686 USD avec « −31 % ». Le critique enregistré conteste le calcul et la datation ; le prix marché est documentaire, non archivé en série. Afficher les valeurs avec leurs sources et dates distinctes ; supprimer le pourcentage comparatif du premier écran tant que convention et instant commun ne sont pas établis. Ne jamais dessiner une ligne marché inventée à partir de ce chiffre. Sources : `docs/DEMO_SCRIPT_10MIN.md` ; `evidence/scenario_rseth/run_outcome.json`, finding `UNITE` ; `evidence/episode_rseth_2026-04.json`.

**H. Plusieurs éléments sont aujourd'hui marqués plus fortement que leur preuve.** `AuditScreen` colore en vert la simple présence de `snapshot_hash` ; `hashes_complete` ne signifie pas vérification indépendante (GE-4). `verdictVariant` colore `DONE` comme une autorisation favorable, `REFUTED` comme une panne. Une hypothèse réfutée peut être un résultat utile ; un run terminé n'est pas une action autorisée. La sémantique doit dépendre du domaine.

### 2.3 Incohérences documentaires à fermer sans réécrire l'histoire

| Divergence | Correction avant soumission |
|---|---|
| Script : benchmark N=9, placebo `not_executed`. Rapport actuel : N=12 et placebo A2 exécuté en graine scriptée, avec abstention | Faire parler le rapport courant, rappeler que les répétitions ne sont pas des observations indépendantes et que le placebo est synthétique. Le registre F-1/F-2 conserve aussi des remarques devenues historiques : les dater |
| 1 411 / 1 418 tests | Référencer un résultat, une date et un commit cohérents ; retirer le compteur du hook oral si l'équipe ne peut pas le réconcilier |
| README : UI 12 écrans puis trois panneaux ; SPA réellement examinée : cinq routes | Nommer clairement l'ancienne UI et la SPA utilisée pour la soumission |
| G-5 fermé et re-scellé ; runbook FAQ 8 encore formulée comme un travail restant | Mettre à jour le texte opérationnel, conserver les anciens rapports datés |
| Rapport d'évaluation historique antérieur à la correction R−/R+ | Garder `evidence/evaluation/SUPERSEDED_NOTE.md` adjacent à toute présentation ; pas de modification des artefacts scellés |
| Fichiers `.docx` datés, certaines sources narratives très antérieures | Vérifier le paquet réellement déposé, pas seulement les Markdown. Le DOC1 affiche encore 221 tests et parle de ce que v1 « va construire » |
| Bannière rsETH de scénario dans Audit, flux réellement lu dans `demo_chain/rseth/audit.jsonl` du 16 octobre | Distinguer le dossier testnet historique du scénario agents du 18 octobre. Un nom de dossier `rseth` ne suffit pas à établir l'identité du run |

Sources : `docs/DEMO_SCRIPT_10MIN.md`, `docs/RUNBOOK_DEMO.md`, `docs/ECARTS_REGISTRE.md`, `README.md`, `ORVYREN_DOC1_EXPLICATION_SIMPLE.md`, G-5/G-16/G-17 et `src/orvyren/api/artifacts.py::{audit_summary,audit_stream}`.

## 3. Priorités des 45 h

Estimations en heures de travail d'une personne connaissant le dépôt. Ordre par impact attendu rapporté à l'effort, avec priorité absolue aux affirmations fausses. Ne pas additionner la migration UI détaillée une seconde fois : elle est incluse dans les lignes 3 et 4.

| Rang | Travail | Effort estimé | Impact et critère de sortie |
|---|---|---|---|
| 0 | Corriger le contrôle du dernier hash dans l'API, ou suspendre son badge de vérification ; retirer les inférences freeze → retrait bloqué et « découverte autonome » HYP-004 | 1–2 h | Très fort : aucune preuve affichée plus forte que le contrôle réellement effectué ; correction et validation ciblées par l'équipe |
| 1 | Unifier le récit et les chiffres sur les artefacts courants ; rendre explicites les quatre contextes : agents rsETH, mécanisme USDC, graphe Base, testnet historique | 1–2 h | Très fort / faible effort : chaque phrase jury correspond à ce qui est affiché |
| 2 | Rendre disponibles les artefacts rsETH via l'API de lecture et sélectionner le run jury ; vérifier la présence réelle du graphe sur le poste | 1,5–3 h | Bloquant : Live et Decision affichent la bonne identité ; sinon plan B explicite décrit en §4.3 |
| 3 | Migrer tokens, composants, shell, puis Live → Markets → Decision → Graph → Audit | 6–8 h | Fort : la conclusion et ses limites sont lisibles dès l'arrivée sur chaque route ; aucun ajout de moteur ni de bibliothèque |
| 4 | Recette visuelle et fonctionnelle sur le poste de projection ; états erreur/vide ; contrôle des unités ; alignement EN ; ajustements | 1,5–2 h | Fort : pas d'écran « loading… » éternel, de données zéro par défaut ni de changement de cas caché |
| 5 | Répéter le script avec le vrai paquet et le plan B ; vérifier la procédure tiers hors dépôt ; figer le montage | 2–3 h | Très fort : le parcours tient dans le créneau existant, la machine hors ligne dispose des artefacts nécessaires |
| 6 | Contrôle de soumission par le responsable : pièces, fichiers finaux, limites, identité du paquet ; dépôt avec marge | 2–3 h | Critique : respect de la deadline fournie. Aucun écran parfait ne compense une soumission manquée |

Les raccordements techniques et la migration ne doivent pas consommer toute l'enveloppe : conserver le reste pour incidents, disponibilité des personnes, repos et dépôt. **La direction UI seule tient dans une journée de travail estimée ; la fermeture de tous les gaps du produit n'y tient pas.** Si le raccordement rsETH dépasse son budget, utiliser le plan B honnête, pas un faux affichage de résultat.

**À couper maintenant :** promesse de supériorité financière ; grand récit prédictif ; chiffres de test et graphe en rafale dans les quarante premières secondes ; métriques de tokens en vedette ; comparaison −31 % non synchronisée ; excursion Q2/Q8 longue ; exposition de tous les reçus et de tous les JSON ; narration de l'optimisation SQL sauf question du jury. Garder l'ordre Live, Markets, Live, Decision, Graph, Decision, Audit du script. Si le timing déborde, appliquer sa coupe prévue du bloc d'exécution.

**À ne pas toucher pour cette passe :** prompts, magasins de replay scellés, formules et jeux confirmatoires gelés, clés/signature, règles de politique, modèle graphe, architecture SQLite, mécanisme FA2, versions de dépendances. Ne pas lancer un re-seeding général pour rendre la critique plus flatteuse. Ne pas contourner `STATE_REQUIRED` ou injecter des valeurs par défaut pour faire apparaître `ALLOW`. Ne pas ouvrir un chantier mainnet, auth, cloud, wallet-connect ou approbation : l'UI v1 est en lecture seule (`FREEZE_V2.md`, H2/H3).

**Hook proposé :** “Before an agent wallet moves funds, it needs evidence and permission. Here is a run that could not establish enough evidence, stopped, and left a record you can inspect.”

**Clôture proposée :** “The current submission demonstrates bounded reasoning, independent policy checks and offline-verifiable records. Autonomous end-to-end execution and financial added value remain unproven.” Le montant du run peut être montré dans son contexte ; il n'a plus besoin de porter toute la promesse.

## 4. Spécification UI complète

### 4.1 Direction retenue : document de contrôle sur fond ivoire

**Fond ivoire neutre, texte anthracite, un seul accent vert profond.** La console doit ressembler à un instrument de décision utilisé quotidiennement : titres simples, chiffres alignés, listes de preuves, séparateurs nets. Le fond clair rend les sources et les tableaux plus faciles à lire en projection ; ce bénéfice reste à vérifier sur le matériel réel. Le vert indique sélection, action de consultation et contrôle effectivement passé. Il ne colore pas toute la page et ne signifie jamais « rentable ».

Pas de second thème à livrer. Pas de grain pour cette version : il ne porte aucune information. Aucun dégradé, transparence de surface, blur, halo, néon, emoji, orange, terracotta, ombre, illustration ou animation d'entrée. Les seuls arrondis sont des angles de contrôle de 2 px. Garder React, Tailwind 4, les composants locaux, Sigma et Lightweight Charts.

Références choisies, comme principes de conception et non comme copies pixel à pixel :

| Référence réelle | Ce qu'on prend | Ce qu'on ne prend pas |
|---|---|---|
| [GitHub Primer — DataTable](https://primer.style/product/components/data-table/) | Une ligne = un objet ; colonnes comparables ; titres et interactions explicites. C'est le modèle principal pour règles, preuves et journaux | Habillage GitHub, menus multiples, accumulation de badges |
| [Grafana — Table](https://grafana.com/docs/grafana/latest/visualizations/panels-visualizations/visualizations/table/) | Contrôle de la largeur des colonnes, unités, consultation du détail et traitement explicite des cellules | Mosaïque de panneaux équivalents, couleurs partout, jauges décoratives |
| [Linear — Conceptual model](https://linear.app/docs/conceptual-model) | Identité claire de l'objet consulté et navigation stable entre des vues ; appliquer cette discipline au run et au dossier | Codes visuels de marque, mise en scène marketing, fonctionnalités de gestion de projet |

Ces emprunts sont les choix d'Astra. On n'importe aucun design system tiers. Une imitation de Bloomberg ajouterait une densité et des codes couleur que le public n'a pas le temps d'apprendre ; une imitation de landing page SaaS affaiblirait le caractère documentaire du produit.

### 4.2 Tokens exacts et primitives

#### Couleurs

Déclarer les noms `--color-*` dans le `@theme` existant de `frontend/src/styles/index.css`. Les valeurs sont opaques. Un seul accent chromatique ; refus et avertissements utilisent le contraste, le contour et leur libellé plutôt qu'une deuxième couleur.

| Token | Hex | Usage |
|---|---|---|
| `background` | `#F4F4EF` | Fond global ivoire neutre |
| `surface` | `#FCFCF9` | Surface des sections, header et canvas |
| `surface2` | `#EAEDE7` | En-têtes de table, hover, zones de détail |
| `ink` | `#202823` | Texte principal, refus inversé |
| `muted` | `#59635C` | Texte secondaire, jamais utilisé avec une opacité réduite |
| `line` | `#CDD3CB` | Séparateurs non interactifs |
| `line-strong` | `#788379` | Contours d'inputs, contrôles et états qui doivent se distinguer |
| `accent` | `#24543D` | Sélection et action primaire |
| `accent-hover` | `#193E2D` | Hover de l'action primaire |
| `accent-soft` | `#E2EBE3` | Ligne sélectionnée, contrôle vérifié |
| `on-accent` | `#FCFCF9` | Texte sur vert et anthracite |
| `graph-node` | `#7B867E` | Nœuds ordinaires |
| `graph-dim` | `#CDD3CB` | Nœuds hors voisinage sélectionné |
| `graph-edge` | `#D8DDD6` | Relations de fond |
| `plot-secondary` | `#667269` | Série secondaire neutre |

Migration courte : `accent2` devient temporairement un alias d'`ink`, `up` d'`accent`, `down` et `warn` d'`ink`. Ensuite supprimer leurs usages sémantiques génériques dans les écrans au profit des variantes décrites ci-dessous. Les variantes `violet`/`info` restantes deviennent neutres pendant la migration. Ne pas garder `bg-warn/10`, `text-muted/80` ou d'autres opacités comme substituts aux surfaces définies.

#### Typographie

**Décision J-2 : Arial**, choisie explicitement pour sa disponibilité locale et sa sobriété ; pas de dépendance réseau de police. Stack : `Arial, "Helvetica Neue", Helvetica, sans-serif`. Mono : `"Cascadia Mono", Consolas, "Liberation Mono", monospace`. DM Sans serait pertinente avec un WOFF2 local et sa licence déjà prêts ; elle n'est pas un prérequis de cette passe. La personnalité vient de la composition, pas d'un téléchargement de font.

| Rôle / token de taille | Taille / interligne | Poids / approche |
|---|---|---|
| `page-title` | 22 / 28 px | 600 ; tracking −0,02 em |
| `section-title` | 15 / 22 px | 600 ; tracking 0 |
| `body` | 14 / 20 px | 400 ; tracking 0 |
| `table` | 13 / 18 px | 400 ; entêtes 600 |
| `meta` | 12 / 16 px | 400 ; labels 500 |
| `kpi` | 26 / 30 px | 600 ; tracking −0,02 em |
| `verdict` | 24 / 30 px | 600 |
| `code` | 12 / 18 px | Mono 400 |

Créer les tokens Tailwind `--text-page-title`, `--text-page-title--line-height`, etc., puis utiliser `text-page-title`, `text-body`, `text-meta`. Réserver la mono aux codes, adresses, hashes et données brutes. Tous les nombres en `tabular-nums` et `lining-nums` ; conserver `.tnum` comme alias. **Aucun texte du parcours principal sous 12 px.** Pas de titres systématiquement en capitales ni de tracking de 0,14–0,20 em ; capitales réservées aux enums machine.

#### Espacement, géométrie et interaction

| Paramètre | Valeur proposée |
|---|---|
| Base | 4 px ; échelle 4, 8, 12, 16, 24, 32 px |
| Marge du contenu | 24 px à partir de 1280 px ; 16 px en dessous |
| Espacement entre sections | 16 px ; entre label et valeur 4 px |
| Padding de section | 16 px ; lignes de table 8 px vertical / 12 px horizontal |
| Bordure | 1 px `line` ; contrôles 1 px `line-strong` |
| Rayon | Sections, tables, bande KPI : 0 ; boutons, inputs, badges : 2 px |
| Ombres | `none`, y compris ombre interne de `card.tsx` |
| Contrôles | Bouton/input/select 36 px de haut ; bouton compact 32 px ; icône 16 px, trait 1,5 px |
| Focus clavier | Outline 2 px `accent`, offset 2 px ; ne pas le remplacer par un glow |
| Désactivé | Fond `surface2`, texte `muted`, bord `line`, sans opacité globale ; raison adjacente si utile |
| Hover | Changement immédiat vers `surface2` ; aucune translation ni changement de taille |
| Animations ordinaires | 0 ms, aucun easing ; seul mouvement autorisé en §4.10 |

Actions de consultation permises : choisir un cas/run, lancer une requête de lecture, ouvrir un détail, rafraîchir, copier. Aucun bouton `Approve`, `Execute` ou `Connect wallet` : ils contrediraient le périmètre gelé. `Copy` ne montre `Copied` qu'après succès du presse-papiers ; en échec, afficher `Select and copy the text` et conserver le texte sélectionnable.

### 4.3 Contrat de données minimal : préalable aux maquettes

Il faut distinguer **cas étudié**, **identité du run**, **origine de l'artefact**, **mode de présentation** et **état du transport**. Ne jamais déduire l'un de l'autre. Un run produit en mode live hier reste un enregistrement lorsque le hub le rejoue aujourd'hui.

| Vue | Sources actuelles utilisables | Adaptation minimale proposée |
|---|---|---|
| Live | `api.runs`, `api.run`, `api.runEvents`, `api.runVerify` ; WS ; budgets dans spec/outcome | Ajouter le dossier `scenario_rseth/agents_session` à la découverte de runs, avec déduplication par run_id. Sélectionner explicitement le run lié par `scenario_run.json`, puis garder le choix humain. Ajouter `Refresh runs` via refetch. Pas de prétention de suivi de fichiers en continu |
| Markets | `api.episodes`, `api.episodeSeries`, `api.episode` déjà présents | Choix initial rsETH s'il existe ; regroupement frontend par actif/unité. `api.episode` donne les données brutes et les timestamps absents du résumé. Le chiffre marché documentaire vient de la fixture citée, pas de l'invention d'une nouvelle série |
| Decision rsETH | Les artefacts existent mais leur lecture n'est pas exposée au bon endroit | Ajouter **un endpoint de lecture explicitement nouveau**, `/api/scenarios/rseth-2026-04`, qui retourne les objets existants listés ci-dessous, sans recalcul de verdict |
| Decision USDC | `api.decision("usdc-2023-03")`, `api.policyVerdicts`, `api.executionReceipts` | Garder le mécanisme actuel dans une section ou un onglet nommé `USDC pilot`. Ne pas lui donner le run_id rsETH par défaut |
| Graph | `api.graphFull`, `api.graphInfo`, `api.graphQuery`, `api.graphNode` | Montrer la base et les comptes de la réponse courante ; le benchmark enregistré est une autre source. Réutiliser les reducers Sigma |
| Audit | `api.auditSummary`, `api.auditStream`, vérification agents ; ZIP énumérés | Distinguer résultats de checks et présence d'empreintes. L'API actuelle n'exécute pas le vérificateur tiers du ZIP et ne fournit pas de téléchargement : ne pas dessiner ces boutons comme fonctionnels |

**Réponse du nouvel endpoint scénario, proposition de contrat :** `case_id`, `scenario` ← `scenario_run.json`, `run` ← `run.json`, `outcome` ← `outcome_orchestrator.json`, `agent_outcome` ← `run_outcome.json`, `assessment` ← `decision/abstention_rseth-2026-04.json`, `execution` ← `policy_verdicts.json`, `execution_journal` ← `execution/journal.jsonl`, `substitution` ← fonction existante, `inputs` ← `fixtures/agents/rseth-2026-04/run_inputs.json`, `sources` ← chemins relatifs des objets effectivement chargés. Vérifier le schéma du fichier d'exécution avant de mapper ses champs ; conserver les objets bruts. Fichier absent : champ `null` et entrée explicite dans `missing_sources`, jamais un exemple substitué. Le retour ne doit pas être présenté comme un nouvel artefact scellé. Cible de modification : `api/artifacts.py`, `api/routes.py`, `frontend/src/lib/{api,types}.ts`.

Cette adaptation est une lecture de fichiers autorisés dans un périmètre fixe, pas une API permettant au navigateur de choisir un chemin arbitraire. Elle ne touche ni modèle, ni prompt, ni décision. Pour relier les écrans, utiliser un contexte UI partagé distinct du store de transport, avec cas et run sélectionnés ; ne pas reprendre `store.runId`, que chaque enveloppe WS peut modifier. Réutiliser Zustand ou les paramètres d'URL, sans nouvelle dépendance.

Les journaux peuvent conserver plusieurs tentatives : filtrer la vue du scénario par `scenario.executor_run_id`, sans effacer les autres lignes ni renuméroter les événements. `policy_verdicts.json` contient un tableau `ticks`, pas `records` ni un compteur de signatures. Le mode et `executed` sont présents dans le journal ; le compteur `signed: 0` est publié dans la sortie d'exécution du rapport. Sans compteur accessible pour l'objet choisi, afficher `No transaction submitted` lorsque les enregistrements le démontrent, plutôt que fabriquer un champ `signed`.

**Plan B si ces lectures ne sont pas prêtes :** Decision reste `USDC pilot — mechanism demonstration`. Le résultat rsETH est montré dans le terminal à partir du rapport et de l'abstention livrés, puis le présentateur annonce le changement de cas. Live affiche seulement un run effectivement découvert. Aucun collage d'un verdict rsETH sur les cartes USDC ; aucun faux `what_would_change` codé dans le JSX. Le thème, les mises en page et les états honnêtes restent livrables dans la journée.

**Champs manquants et provenance :** `null`/absent → `Not available`, jamais `0`, `ALLOW`, `concordant` ou `no`. Le coût zéro n'est affiché que si la source contient effectivement zéro. Le booléen absent `agent_holds_key` ne devient pas « no ». Les compteurs se rapportent toujours au run/cas de la carte. Les chaînes `mode`, `case_id`, `agent_run_id`, `parent_run_id`, `policy_hash` restent disponibles en entier dans `Source details`. Un bouton de copie est plus utile qu'un hash tronqué sans accès au contenu.

### 4.4 Shell, navigation et éléments communs

**Gabarit cible :** desktop 1440 × 900 CSS px, recette indispensable également à 1366 × 768. Ces dimensions sont des cibles de conception. Sidebar 192 px ; header 64 px ; bande de contexte 48 px minimum, extensible sans masquer de texte ; contenu sans max-width artificielle. Grille principale en `minmax(0,1fr)` pour éviter le débordement des hashes.

**Sidebar :** fond `background`, bord droit `line`, mot `ORVYREN` à 16/22 px, 600 ; sous-titre `Risk & verification` à 12/16. Supprimer le carré Ω. Navigation dans l'ordre de la première apparition au jury : `Live`, `Markets`, `Decision & Policy`, `Graph`, `Audit` ; garder les URLs existantes. Ligne de 40 px, icône Lucide de 16 px, espace de 8 px. Actif : fond `accent-soft`, texte `accent`, filet gauche 2 px ; pas de contour arrondi complet. Inactif : texte `muted`, hover `surface2`. Footer : `Local workspace`, puis `Read-only`. Retirer `FastAPI + local WebSocket` du chrome produit.

**Header :** titre à gauche, action pertinente à droite. Un seul bouton primaire maximum ; la plupart des pages n'en ont pas besoin. Le select de cas/run fait 280–360 px selon l'espace, avec label visible `Run` ou `Episode`. L'identifiant complet reste lisible dans la bande de contexte ou le détail. Supprimer les suffixes `— agents running`, les versions de bibliothèques et les slogans techniques. Titres exacts : `Agent activity`, `Market evidence`, `Decision & Policy`, `Risk graph`, `Audit dossier`.

**Bande de contexte, sous le header :** `Case`, `Run`, `Evidence`, et à droite `Connection`. Valeurs d'exemple de structure : `Case rsETH / April 2026` ; `Evidence RECORDED RUN` ; `Connection LIVE`. Afficher les dates en UTC. En Graph : remplacer cas/run par `Dataset Aave v3 / Base` et base réellement chargée. En Audit : nom/date du paquet ou du flux sélectionné. Pas de prétention à un dossier global unique lorsque les sources diffèrent.

**Responsive borné :** à moins de 1280 px, sidebar 176 px et marge 16 px ; à moins de 1100 px, les colonnes secondaires passent sous la principale ; à moins de 900 px, nav horizontale texte au-dessus du header, sans nouveau menu hamburger. Les tables peuvent défiler horizontalement dans leur propre conteneur ; jamais la page entière. Aucun redesign mobile avancé pour le concours. Le header peut grandir si les contrôles doivent passer à la ligne.

**Bande KPI :** une seule surface horizontale de 72 px, sans cartes individuelles ; quatre cellules égales séparées par un trait vertical. Label 12 px, valeur 26 px, unité/plafond 12 px. Live : `LLM calls`, `Tool calls`, `Elapsed time`, `Recorded cost`. Forme `9 / 30`, `7 / 12`, `59.8 / 600 s`, `$0.0397 / $0.10` seulement pour le run dont les valeurs proviennent des fichiers cités en §2.1. Texte adjacent `Recorded run totals` si le résultat est achevé ; ne pas laisser croire que ces totaux croissent avec le replay. Moins de 1100 px : grille 2 × 2. Pas de barres de progression suggérant qu'un budget consommé est un travail accompli.

**Tables :** en-tête opaque `surface2`, 32 px minimum ; lignes 36 px minimum, agrandies si le contenu utile se replie. Aucun zébrage ; filet horizontal `line`. Texte à gauche, nombres à droite, valeurs décimales à précision constante, unité dans l'en-tête. Identifiants à gauche en mono, chiffres tabulaires. La dernière colonne de commentaire prend le reste. Tri affiché uniquement s'il est implémenté ; pas de chevrons décoratifs. Une ligne interactive comporte un vrai bouton `Details`. En-tête sticky uniquement à l'intérieur d'un tableau qui défile. Le résumé reste hors de ce scroll.

**Sections :** une bordure autour d'un groupe logique, jamais une carte par champ. Section title 15 px ; éventuel compteur neutre à droite. Les JSON et métadonnées techniques passent dans des `<details>` natifs nommés `Raw record`, `Source details` ou `Verification details`. Ne pas masquer les limites qui changent le verdict.

#### États : forme et libellés exacts

Badge : hauteur minimum 24 px, padding horizontal 8 px, rayon 2 px, police 12/16 px, 600, approche 0. Aucun pulse. État toujours écrit ; pas de dépendance à la couleur seule.

| Domaine / valeur | Apparence | Texte explicatif associé |
|---|---|---|
| Connexion `LIVE` | Texte/bord vert, fond `accent-soft` | `Connected to the local event stream.` La mention `Connection` reste visible |
| Connexion `DEGRADED` | Texte anthracite, contour tireté `line-strong`, fond `surface2` | `Stream interrupted. Showing recorded events via polling.` Seulement si le polling fonctionne |
| Connexion `OFFLINE` | Anthracite sur `surface2`, contour plein | `Stream unavailable.` Ajouter `Showing cached data from {time} UTC.` uniquement si ce cache existe |
| Connexion `CONNECTING` | Contour neutre | `Connecting to the local event stream…` |
| Présentation `RECORDED RUN` | Neutre | `Recorded events replayed for this view. Original run mode: LIVE.` Le mode original vient de la source |
| `REPLAY` / `FIXTURE` | Neutre ; FIXTURE contour tireté | `Deterministic replay.` / `Labelled simulation data.` Ne pas requalifier toute archive live en fixture |
| Politique `ALLOW` | Vert sur `accent-soft` | `Policy checks passed. This is not a transaction receipt.` |
| Politique `DENY` | Texte `on-accent`, fond/bord `ink` | `Action blocked by policy.` Afficher les codes de refus immédiatement dessous |
| Politique `REQUIRE_APPROVAL` | Texte `ink`, fond `surface`, bord `line-strong` | `Human review required.` Aucune action d'approbation dans v1 |
| Hypothèse `REFUTED` | Neutre, mot exact et trait de statut court | `Refuted by the cited evidence.` Seulement lorsque le niveau de preuve le permet ; indiquer ici `Scenario assessment` pour HYP-004 |
| Hypothèse `INCONCLUSIVE` | Neutre, contour tireté | `Evidence is insufficient to conclude.` |
| Exécution de programme `ABORTED` | Anthracite inversé | `Run stopped — ARRET-3`. Ne pas renommer `ABORTED` en `DONE` |
| Vérification `VERIFIED` | Vert sur `accent-soft` | Nommer le contrôle et sa source ; pas de validation globale par transitivité |
| `NOT CHECKED` / `NOT AVAILABLE` | Neutre | Distinguer un contrôle non fait et une preuve absente |
| `MISMATCH` / `FAILED` | Anthracite inversé | Montrer quel contrôle échoue et garder les éléments inspectables |

`NO_ACTION` signifie une décision de ne rien faire ; `INCONCLUSIVE` une insuffisance de preuve ; `REQUIRE_APPROVAL` une exigence d'autorisation. Ne jamais les fusionner en un simple état « blocked ».

#### Bannière de substitution

Réutiliser `SubstitutionBanner.tsx`. Rectangle opaque `surface2`, filet gauche 3 px `ink`, autres bords 1 px `line`, padding 12 × 16 px. Titre 13 px/600 **`Declared substitution`** ; corps 13/18 px ; aucun bouton fermer. Elle précède immédiatement tout panneau du mécanisme substitué ; si son journal a un scroll interne, elle reste hors du scroll et visible. Ne pas la poser au sommet d'une page très longue puis la perdre avant le journal.

Copie exacte : **“This execution leg uses the USDC pilot decision. The rsETH agent run ended in abstention. No rsETH transaction was executed by this scenario.”** Ligne suivante : **“The rsETH execution probe was refused: E_WHAT_WOULD_CHANGE_REQUIRED.”** Afficher aussi `Agent run`, `Execution run`, `Execution case`, alimentés par les sources. Garder accessible le texte de disclosure d'origine via `Source details` ; ne pas réécrire un artefact.

Pour le dossier historique du 16 octobre, utiliser une déclaration différente : **`Separate testnet demonstration`** puis **“These Base Sepolia receipts belong to the earlier testnet demonstration. They do not prove autonomous execution of the rsETH agent decision.”** Ne pas lui appliquer mécaniquement la bannière du tick USDC du 18 octobre.

### 4.5 Live — faire lire une activité et son résultat

**Priorité visuelle n°1 : c'est le premier écran et le retour pendant l'exécution terminal.** En arrivant : titre, identité du run, `RECORDED RUN`, puis budget. La conclusion doit être visible sans descendre jusqu'à la dernière carte.

Après la bande KPI, grille `minmax(0,1fr) 360px`, gap 16 px. À 1440 px, la colonne journal prend le reste de la largeur disponible ; à 1366 px, ramener l'inspecteur à 320 px. Le contenu principal utilise la hauteur restante ; journal scrollable avec minimum 320 px. La page peut défiler à faible hauteur, mais résultat et budget restent en haut.

- **Colonne gauche — `Agent journal`** : remplacer `execution timeline`, qui confond raisonnement et transaction. Barre de 40 px : titre, compteur `Showing {n} of {total} events`, bouton de consultation `Latest event`. Chaque entrée : ligne compacte `Time UTC` (92 px), `Agent` (96 px), `Event` (140 px), statut éventuel ; puis résumé du contenu à 14/20 px, deux lignes maximum, bouton `Expand` / `Collapse`. Détails techniques et hashes seulement à l'ouverture. N'afficher les références qu'une fois, sous la ligne, sous forme de liens textuels sobres. Un lien sans cible réelle devient du texte sélectionnable, pas un faux lien.
- **Colonne droite — résultat d'abord** : `Agent outcome`, état programme exact, arrêt, `Critic assessment`, escalade. Pour rsETH, lire le verdict critique dans `run_outcome.critique.verdict_lecture` ou le rapport d'échange, pas dans `outcome.critique_verdict` qui est vide dans l'artefact lu. Les findings sont dans `findings`, pas seulement dans un hypothétique tableau `errors`. Donner en premier l'objection sur l'identité de l'actif et celle sur le freeze ; afficher la gravité d'origine en détail.
- Sous le résultat : `Hypotheses`, liste plate ID + énoncé court + état. Si l'état vient de `spec.hypotheses`, titre `Initial hypotheses` : le code actuel lit les hypothèses d'entrée et non les verdicts finaux. Les verdicts du dossier assemblé appartiennent à Decision. Ensuite `Missing evidence`, liste textuelle ; l'evidence packet et les outils sont repliés sous `Evidence packet` et `Tool records`.
- Supprimer la seconde bande de quatre cartes tokens/hypothèses/events/state ; tokens et informations modèle vont dans `Run details`. Supprimer le slogan tarifaire constant et le tableau de badges de tous les kinds.

Copie de résultat, issue de champs réels : **`Run stopped — ARRET-3`**, **`Agent assessment: INCONCLUSIVE`** si l'abstention est établie, **`Critic assessment: INCOHERENTE`**, **`Escalation: REQUIRE_APPROVAL`**. Traduire pour l'utilisateur par `Inconsistent evidence` à côté du code critique, pas à sa place dans les données brutes.

Le journal ne se met pas à défiler automatiquement pendant que quelqu'un lit. Quand une nouvelle entrée arrive hors du bas de page : bouton **`New events available`**. Les totaux enregistrés restent stables lors des boucles du hub ; ne pas additionner REST, WS et outcome. Au chargement d'un nouveau run, garder toutes les requêtes et l'inspecteur liés à cet ID ; un ancien résultat affiché provisoirement porte **`Previous run data`**, ou est remplacé par un placeholder neutre.

### 4.6 Markets — une preuve de marché, des unités intelligibles

**Priorité visuelle n°2 : rendre le problème compréhensible avant de parler d'agents.** Sélecteur `Episode`, choix rsETH explicite si présent ; titre secondaire `rsETH / April 2026`. Texte permanent **`Historical evidence · Ethereum`**, car le graphe montré ensuite porte sur Base.

Première ligne : bande de trois faits, hauteur minimale 88 px : **`Oracle price at freeze`**, **`Peak supply-cap usage`**, **`First frozen block`**. Mapping explicite aux clés de `evidence/episode_rseth_2026-04.json`, pas `Object.entries(headline).slice(0,12)`. Affichages pour cet artefact : `$2,513.66`, `99.999%`, `24,908,723`, avec instant source sous chaque valeur. La valeur arrondie du cap n'est pas « cap atteint exactement » ; la valeur complète reste dans le détail.

Puis grille `minmax(0,1fr) 320px`, gap 16 px :

1. **À gauche, graphique principal de 280 px : `rsETH oracle price · USD`.** Seule la série `rsETH:oracle_price` par défaut. Une ligne de 2 px vert profond, pas de remplissage. La série WETH n'apparaît que sur sélection explicite, avec unité USD compatible et libellé visible. Le prix marché documentaire **`Documented market quote: $1,686`** est à droite, accompagné de **`Not an archived market series. Not time-aligned with the oracle reading.`** et de la référence de la fixture ; il n'est ni point inventé, ni ligne horizontale donnant l'illusion d'une série.
2. **À droite, `Evidence limits`**, texte toujours visible : **`Oracle freshness is unavailable for this feed.`**, **`The retained oracle price is not a measured exit price.`**, **`Reserve freeze observed. Withdrawal availability was not established.`** Ensuite `Episode events`, trois premiers événements documentés avec date UTC et source ; le reste est consultable via `Show all events`. Aucun placeholder de date à 1970.
3. **Sous le graphique, deux petits panneaux de 160 px chacun : `Supply-cap usage · %` et `Utilisation · %`**, rsETH par défaut. Convertir les ratios source en pourcentages uniquement à l'affichage. Utilisation avec précision suffisante pour ne pas réduire la mesure citée d'environ 0,008 % à `0.0%` ; pas de comparaison directe à des quantités USDC. Une ligne de cap à 100 % est admissible comme seuil explicitement nommé, pas comme mesure.
4. Les quantités `cash`, `variable_debt_supply`, `a_token_supply` vont dans une table `Reserve balances`, colonnes par actif avec unité explicite, ou un graphique sélectionnant un seul actif et des métriques de même unité. Pas de volume USDC et rsETH sur le même axe.

Pour USDC : `Price · USD` avec deux séries par défaut, médiane et minimum ; venues en sélection secondaire. Pour stETH : `Discount · bps` distinct de `Oracle ratio · ETH per stETH`. Aucune échelle secondaire cachée ; préférer des petits graphiques séparés à un double axe ambigu.

**Réglages communs Lightweight Charts :** fond `surface`, texte `muted`, Arial 12 px ; horizontales `line` de 1 px, verticales masquées ; axe temps UTC et unité écrite au-dessus de chaque plot. Crosshair anthracite fin pointillé, label anthracite sur fond `surface2`. Pas d'aire remplie, pas de courbe lissée inventant des observations, pas d'animation. Les trous connus restent des trous ; pas d'extrapolation ni de valeur zéro ajoutée. Entre points échantillonnés, expliciter `Sampled observations; lines connect available points.`

Associer le style **par `line.id` avant filtrage**, commun à `SeriesToggles` et `PriceChart` : série principale `accent`, trait plein 2 px ; comparateur `ink`, trait tireté 2 px ; troisième `plot-secondary`, pointillé 1 px. Au-delà, sélection de séries, pas palette multicolore. Maximum trois séries simultanées dans un plot de démo, et uniquement d'unité compatible. Les legendes utilisent un segment de trait de 20 px, une checkbox native avec `accent-color: var(--color-accent)`, puis un label à 12 px. Un toggle ne change ni les styles des autres séries ni le zoom par défaut si cela peut être évité sans refonte.

Masquer les détails d'implémentation `TradingView Lightweight Charts v5` dans le sous-titre produit ; préserver toute attribution exigée par la licence, après contrôle par l'implémenteur. Regrouper `RPC provenance`, notes et clés brutes dans `Source details`, sous les limites utiles.

### 4.7 Decision & Policy — séparer conclusion, autorisation et transaction

**Priorité visuelle n°3, mais raccordement fonctionnel bloquant.** L'écran doit répondre immédiatement à trois questions : que sait-on, quelle action est proposée, qu'est-il permis de faire ? L'autorisation d'agents et le verdict final de politique ne sont pas interchangeables.

Après le header et le contexte : trois cellules horizontales, sans trois cartes flottantes, minimum 112 px. Libellés **`Evidence assessment`**, **`Proposed action`**, **`Agent escalation`**. Pour l'abstention rsETH livrée : `INCONCLUSIVE`, `No action proposed`, `REQUIRE_APPROVAL`. Sous la première : `Scenario assessment linked to the recorded agent run`. Sous la troisième : `Human review required. No approval can be granted in this console.` Ne pas afficher un zéro USDC comme si une taille de position avait été décidée.

Ensuite grille `minmax(0,1fr) 360px` :

- Gauche, **`What would change the assessment`** : liste numérotée des entrées de `assessment.what_would_change`. Énoncé en langage humain, puis cible/source en 12 px, prédicat machine repliable. Ordre livré : série marché rsETH archivée ; fraîcheur oracle ; fenêtre dense du cap ; dette par compte ; observation rsETH pertinente dans les références du run. Ces pistes sont celles du dossier assemblé, pas des tâches déjà exécutées. Les coûts estimés contenus dans les prédicats restent dans le détail et portent `Estimated`, jamais « measured ».
- Droite, **`Scenario hypotheses`** : table `Hypothesis / Assessment / Evidence`. Les verdicts finaux du dossier sont affichés distinctement des hypothèses initiales ; HYP-004 montre sa source mesurée et **`Assessment assembled by the scenario script`**. Ne pas raconter sa réfutation comme une nouvelle découverte de ce run. Sous la table : `Agent critique`, objection et code d'origine ; traductions EN relues, originaux FR disponibles dans `Raw record`.

Puis une navigation interne simple : **`Scenario execution`**, **`USDC pilot`**, **`Testnet receipts`**. Ce sont des boutons de vue, style trait inférieur 2 px vert pour l'actif, sans pilules. Leur intitulé suffit à montrer le changement de contexte. Si la gestion accessible des tabs n'est pas implémentée, utiliser des boutons normaux avec état `aria-pressed`, plutôt que des rôles ARIA incomplets.

**Scenario execution :** bannière de substitution immédiatement avant le contenu. Ligne de verdict **`Policy result: DENY`**, codes **`BALANCE_UNREADABLE`**, **`AGENT_NOT_MEMBER`**, puis **`Execution mode: DRY RUN`**, **`Transactions signed: 0`** si ces champs sont présents dans le scénario. Ces valeurs sont celles du tick USDC lié au run rsETH ; la bannière ne doit jamais disparaître. Table `Rule / Result / Reason` : toutes les règles effectivement évaluées, dans l'ordre fourni ; ne pas imprimer « 14 passed » parce que le catalogue contient P1–P14. Les règles sautées, si présentes, ont leur propre état et motif. Les instructions non émises portent **`No transaction was submitted.`**

**Journal d'exécution :** tableau `Seq` (56 px), `Time UTC` (160 px), `Event` (120 px), `Outcome` (140 px), `Details` (reste). Légende des kinds : `INTENT`, `POLICY`, `SIMULATION`, `SUBMIT`, `RECEIPT`, `VERIFY`, `OUTCOME`. Afficher uniquement les événements présents, dans leur ordre source ; ne pas remplir sept étapes pour une exécution arrêtée avant simulation. Les payloads ont un bouton `Details`, les hashes peuvent être copiés ; aucune animation de pipeline qui ferait croire à une progression transactionnelle. Si l'artefact court du scénario n'a pas ce vocabulaire, garder ses champs réels et nommer la table `Executor records` ; le flux historique à sept kinds reste dans Testnet/Audit.

**USDC pilot :** conserver les trois axes du dossier USDC, RDOF et les cas de politique actuels, en lecture détaillée. En haut : **`USDC pilot — mechanism demonstration`**, source précise et mode de `policy_execution_demo.json`. RDOF devient le titre humain **`Discriminating checks`**, acronyme dans l'aide. La convention low/close et les garde-fous restent consultables ; pas de grand panneau pour du JSON. Ne pas recopier ici le DENY du scénario si l'artefact de démonstration porte un autre résultat.

**Testnet receipts :** déclaration `Separate testnet demonstration`. Colonnes `Transaction`, `Receipt status`, `Block`, `From / To`, `Source`. Pour status `0x1` : `SUCCESS`, pour `0x0` : `REVERTED`, pour absent/inconnu : `NOT AVAILABLE`. Ne qualifier un revert de `Expected refusal` que si le journal ou le rapport le rattache à un test de verrou ; pas à partir du seul statut hexadécimal. Blocks en entier, jamais `24.9 M`. Gas et logs dans le détail.

L'ancienne carte `final decision` en bas remonte dans le résumé. Supprimer les grappes de cartes d'intent : les intentions deviennent des lignes sélectionnables avec code, montant/unité et verdict. Le détail change sans déplacer la table. Le `policy_hash` est visible sous le verdict de politique en mono, avec `Copy policy hash` ; chaîne et mode l'accompagnent.

### 4.8 Graph — rendre une relation inspectable

**Priorité visuelle n°4.** Le graphe sert à poser une question et suivre ses preuves. Il ne doit pas être un fond animé ou un concours de nœuds.

Sous le header : barre dataset avec **`Aave v3 / Base`** uniquement si confirmé par les données, comptes exacts de la réponse courante, `Database`, `Schema`, `Graph version`. Une base legacy donne **`Repository snapshot · legacy schema`**. Le chemin Windows par défaut ne devient pas une donnée opérationnelle si cette base n'est pas chargée. Ne pas utiliser `ui_snapshot.json.counts` pour habiller le graphe effectivement servi par une autre base.

Layout desktop : canvas `minmax(0,1fr)`, inspecteur 360 px à droite, gap 16 px, hauteur du contenu restante avec minimum 440 px. Réduire le panneau actuel de 460 px ; supprimer le minimum arbitraire de 600 px qui force le scroll sur petit écran. L'inspecteur contient deux vues : `Query` et `Selected node`. La sélection d'un nœud ouvre son détail ; revenir à Query conserve les paramètres. Sur une largeur inférieure à 1100 px, inspecteur sous le canvas.

**Canvas Sigma :** fond `surface`, nœuds ordinaires `graph-node`, relations `graph-edge`, sélection `accent`, voisins `ink`, reste `graph-dim`. Garder la taille relative déjà calculée par le payload et borner les excès visuels si nécessaire ; ne pas l'appeler « risque » ou « exposition » sans métrique correspondante. Types affichés dans l'inspecteur et la légende textuelle, pas douze couleurs ni douze formes à implémenter. Relations 0,6 px au repos et 1,4 px pour celles du voisinage sélectionné, comme dans les reducers existants ; aucune flèche ou edge label globale. Le détail textuel rétablit le sens `Source → Target` et le type de relation.

Conserver worker, cache de positions par `graph_version`, densité de labels et culling existants ; labels sélectionnés 12 px, `ink`, sans boîte flottante ombrée. Supprimer le déplacement automatique de caméra de 350 ms à chaque sélection : la caméra reste où l'utilisateur l'a placée. Les commandes de zoom/pan restent celles de Sigma ; pas de nouveau layout pour la démo, pas de recalcul forcé au changement de couleur.

**Query :** select `Query`, puis formulaires actuels relabellés : `Holder`, `Source`, `Target`, `Asset`, `As of (UTC)`, `As of block`, `Maximum depth`, `Limit`. Addresses et dates pleine largeur ; `Maximum depth` et `Limit` peuvent partager une ligne. Boutons **`Run query`** primaire et **`Load example parameters`** secondaire. Le deuxième remplace l'ambigu `snapshot values` ; préciser **`Example parameters from the archived Aave Base snapshot.`** S'ils ne correspondent pas à la base courante, ne pas promettre un résultat ; afficher cette limite ou proposer des paramètres issus d'un nœud sélectionné.

Résultat sous formulaire : `Result`, statut brut, nombre de lignes, latence de **cette réponse** si fournie. Ne pas afficher les p50 archivés dans ce composant comme s'ils étaient chronométrés maintenant. Table compacte limitée comme aujourd'hui, avec **`Showing {shown} of {total} rows`** si le total est connu, sinon **`Showing the first {shown} rows`**. Lorsqu'on modifie les paramètres, le résultat précédent porte **`Previous query result`** jusqu'à la nouvelle réponse ; son en-tête conserve le nom et les paramètres qui l'ont produit.

Copie de limites : **`NO_PATH — No dependency path was found in this dataset.`**, puis **`Dependency edges are not populated in the demonstrated slice.`** si c'est bien le slice déclaré. **`NOT_INGESTED — Permission data is not available in this dataset.`** Une table vide avec statut OK porte **`No rows match these parameters.`** Ces cas ne deviennent ni `PASS` ni « no exposure ».

**Selected node :** identité lisible, ID copiable, type, nombre total de relations, table des relations disponibles. Afficher le plafonnement API et le plafonnement UI si applicables (`relations_truncated`, total vs lignes montrées), pas un total intégral au-dessus d'une liste qui paraît exhaustive. La requête Q6 permet d'inspecter la provenance d'une relation. Ne pas implémenter une nouvelle recherche globale ou du pathfinding visuel à J-2.

Mention permanente sous le canvas : **`Dataset overview. Point-in-time filters apply to query results.`** `graph_service.full` expose des révisions brutes (AF-3) : le canvas n'est pas une vue PIT synchronisée. Après une requête PIT, ne pas prétendre que tout le graphe s'est filtré. Q7 de l'API SPA passe par `graph/api.concentration` ; la limite `queries.q7 debt_backed` du registre concerne une autre voie. Ne pas masquer Q7 SPA par confusion, ni convertir `debt_backed` en exposition dans un autre panneau.

### 4.9 Audit — un dossier emportable, des contrôles nommés

**Priorité visuelle n°5 ; moment de crédibilité final.** La vue ne commence plus par trois cartes de métadonnées équivalentes. Elle commence par l'objet que le jury peut vérifier.

Première section en deux colonnes `minmax(0,3fr) minmax(320px,2fr)`, gap 24 px :

- Gauche : **`Offline audit packet`**, nom complet du ZIP v2, date/source, taille réellement retournée, empreinte publiée complète sur deux lignes mono, **`Copy verification command`**. Commande copiée pour le paquet de référence : `python run_verify.py evidence/audit_packets/audit_packet_rseth_20261016-2340_01M526YS.zip`. Libellé adjacent **`Repository command`**. Détail **`Verify without the repository`** : après extraction du ZIP, se placer dans son dossier et lancer `python verify/orvyren_verify.py .`. Cette seconde commande correspond au vérificateur embarqué décrit dans `evidence/audit_packets/README.md`.
- Droite : **`Verification scope`**. Trois lignes distinctes : `Agent journal hashes`, `Execution journal hashes`, `Offline packet verification`. Pour les deux premières, résultat réel des endpoints et scope de l'objet. Pour le ZIP : **`Not run in this view`** tant qu'aucun résultat T10 de cette invocation n'est connecté. Un manifeste présent ou une liste de fichiers ne déclenche pas `OFFLINE_PASS`. Le résultat publié peut être cité comme **`Recorded verifier result`**, avec la date/source, clairement séparé du contrôle actuel.

En dessous, table **`Verification records`** : `Object` (28 %), `Check` (22 %), `Result` (16 %), `Source / Time` (34 %). La présence d'un `snapshot_hash` affiche **`Hash present`**, pas une pastille de vérification. `hashes_complete` affiche **`Provenance hashes present`**. Comparaison recalculée uniquement quand elle existe ; cellule vide → `NOT CHECKED`. Le défaut de §2.2 C doit être corrigé ou son résultat suspendu avant tout badge positif sur l'execution chain.

Puis **`Execution journal — separate testnet demonstration`**, disclosure historique immédiatement avant le tableau. Montrer le `run_id` de chaque ligne ; le flux peut contenir plusieurs runs et le `run_id` de sa première ligne n'est pas celui de tout le dossier. `Source details` montre `demo_chain/rseth/audit.jsonl`, sa date et le manifeste. Pagination `First page` / `Next page`, compteur des lignes montrées ; pas de scroll infini. Conserver les séquences et leurs gaps éventuels, ne pas renuméroter des preuves.

Les autres ZIP vont dans **`Other packets`**, replié ; le v1 historique n'est pas traité comme équivalent au v2 d'autorité. Les snapshots et la politique effective vont en dessous, dans des sections compactes. Les sources et hashes restent intégralement accessibles. Le constat `83` dans le manifeste d'export contre `84` lignes de journal a une explication documentée : export avant le dernier OUTCOME ; afficher **`Manifest reflects the export point; the journal contains a later final event.`** si ces objets sont comparés, au lieu d'un faux `DRIFT`. Source : `evidence/demo_chain/README.md`.

**Limite produit assumée pour cette passe :** pas de faux bouton `Download packet` sans route fichier ; le paquet est remis par le canal de soumission et son chemin est copiable. Pas de bouton `Verify now` qui ne ferait que refetch un manifeste. Le présentateur lance T10 dans le terminal comme prévu dans le script. Afficher à côté de la procédure : **`Offline verification checks recorded integrity. It does not establish financial performance or a fresh RPC confirmation.`**

### 4.10 Une seule idée forte : la ligne de preuve sélectionnée

**Une ligne sélectionnée conserve sa place, et son détail s'ouvre à côté ou juste dessous.** Filet gauche 2 px `accent`, fond `accent-soft`, libellé de source visible. Ce traitement s'applique au journal, à une règle de politique, à une preuve et à une ligne d'audit. C'est le geste commun du produit : on part d'une conclusion et on inspecte ce qui la soutient. Il ne suppose pas de construire un nouveau moteur de liens entre écrans ; on réutilise les détails locaux.

Seule motion autorisée : transition du fond de cette ligne vers `accent-soft` en **160 ms**, easing **`cubic-bezier(0.2, 0.8, 0.2, 1)`**, une fois par sélection explicite. Aucun clignotement, animation de largeur/hauteur, déplacement de caméra, changement de compteur animé, défilement automatique, skeleton shimmer ou pulse LIVE. Le filet et le texte changent immédiatement. Avec `prefers-reduced-motion: reduce`, durée **0 ms**. Le panneau de détail apparaît sans animation ; le focus clavier reste sur le bouton qui l'a ouvert.

### 4.11 Copies EN et états dégradés

Implémenter les états dans l'ordre **erreur sans données → chargement initial → succès vide → succès renseigné**. Une erreur de rafraîchissement avec anciennes données conserve les données, leur date et un bandeau `Refresh failed`. Ne pas remplacer une erreur par une liste vide. Le `Suspense` de `App.tsx` ne doit plus être un grand rectangle vide.

| Situation | Titre / copie exacte | Action et comportement |
|---|---|---|
| Route chargée paresseusement | `Loading view…` | Squelette statique du header et d'une section, pas de valeurs factices |
| API inaccessible | `Local service unavailable` — `The console could not load this view.` | `Retry`, refetch uniquement ; détails techniques repliés |
| Rafraîchissement échoué | `Refresh failed. Showing data loaded at {time} UTC.` | `Retry` ; date issue du chargement réel, pas horloge courante inventée |
| Aucun run | `No recorded runs found` — `No agent journal is available in this workspace.` | `Refresh runs` ; pas de budget affiché à zéro |
| Chargement journal | `Loading recorded events…` | État temporaire, pas une phrase réutilisée pour liste vide |
| Journal vide | `No events recorded for this run.` | Conserver l'identité et les sources du run |
| Packet absent | `No evidence packet recorded for this run.` | Ne pas afficher `0 claims verified` |
| Critique absente | `No critic report recorded.` | Aucun badge favorable par défaut |
| Série absente | `No archived series for this selection.` | Garder l'unité et les sélecteurs ; ne pas tracer une ligne plate |
| Série partiellement disponible | `Some observations are unavailable. Gaps are preserved.` | Montrer la couverture connue et la source |
| Décision absente | `No decision record available for this case.` | `View agent outcome` seulement si une cible chargée existe |
| Dossier scénario absent | `Scenario evidence unavailable` — `The USDC pilot is a separate demonstration.` | Choix explicite `Open USDC pilot`, sans bascule automatique |
| Base graphe absente | `Graph database unavailable` — `The selected database could not be opened.` | `Retry` ; afficher source configurée dans le détail |
| Schéma incompatible | `SCHEMA_UNSUPPORTED` — `This query is not available for the loaded database schema.` | Paramètres conservés ; aucun résultat fictif |
| WebGL indisponible | `Graph rendering unavailable` — `Use the query panel to inspect the dataset.` | Laisser les requêtes REST utilisables ; limite/erreur canvas locale |
| Aucun nœud sélectionné | `Select a node to inspect its identity and relations.` | Texte à gauche dans l'inspecteur, aucune illustration |
| Aucun journal exécution | `No execution records available for this source.` | Conserver la distinction avec un run qui a explicitement signé zéro transaction |
| Aucun reçu | `No transaction receipt recorded.` | Ne pas qualifier l'action de failed si elle n'a jamais été soumise |
| Aucun ZIP | `No audit packet available in this workspace.` | Pas de contrôle `Copy verification command` actif pour un fichier absent |
| Vérification non faite | `Verification has not been run for this object.` | Statut `NOT CHECKED` |
| Hash divergent | `Hash mismatch` — `The recomputed hash does not match the recorded hash.` | Montrer les deux valeurs et l'objet concerné ; inspection toujours possible |
| Succès de copie | `Copied` | Remplace `Copy` pendant 2 s, puis revient sans animation ; durée de feedback proposée |

Pour les textes FR fournis par les artefacts, ne pas traduire silencieusement une preuve scellée. La chrome, les labels de séries et les résumés du parcours sont EN ; un glossaire de présentation explicite peut traduire `médiane multi-venues` → `Multi-venue median`, `plus bas venue` → `Lowest venue quote`, `décote` → `Discount`, `remplissage du cap` → `Supply-cap usage`, `dette variable` → `Variable debt`. Les findings utilisés au jury ont un résumé EN relu par l'équipe, indiqué comme résumé ; `Original record (FR)` reste disponible. Pas d'appel LLM de traduction pendant la démo.

Accessibilité pratique : labels de champs reliés aux contrôles ; états et erreurs en texte ; `aria-current="page"` sur la nav ; boutons de détails avec `aria-expanded` ; outline visible ; message de copie en `aria-live="polite"`. Ne pas mettre tout le journal dans une région live qui récite chaque événement. Si une info essentielle est tronquée, prévoir une ouverture clavier, pas seulement un `title` au survol. Prévoir un ordre de tabulation naturel sidebar → contexte → contenu.

### 4.12 Checklist de migration dans l'ordre

Les durées ci-dessous détaillent **la journée UI** : elles sont des estimations, et incluent une passe de recette. Le raccordement serveur de §4.3 et le correctif de vérification sont des préalables distincts, déjà budgétés en §3. Une personne peut réaliser les étapes UI séquentiellement sans nouvelle dépendance.

| Ordre | Fichiers concernés | Intervention exécutable | Estimation |
|---|---|---|---|
| 0 | `src/orvyren/api/artifacts.py`, `routes.py` ; `frontend/src/lib/api.ts`, `types.ts` | Exposer les lectures scénario, découvrir ses sessions, borner les identités, corriger le contrôle de hash. Mapper `policy_verdicts.ticks[]` à la politique du scénario ; le mode et `executed` viennent des lignes d'`execution/journal.jsonl`, pas d'une propriété fictive du résumé | Préalable §3 |
| 1 | `frontend/src/styles/index.css` | Remplacer les couleurs, introduire les tokens typographiques, `line-strong`, `accent-soft`, normaliser corps à 14/20, scrollbar pouce `line-strong` sans arrondi décoratif. Définir `.tnum`, focus et reduced-motion. Aucune font réseau | 30 min |
| 2 | `components/ui/{card,badge,button,input,tabs,table}.tsx` ; `lib/format.ts` | Aplatir les sections, supprimer l'inset shadow et `animate-pulse`, mettre les tailles et variantes d'état, remplacer le mapping unique de verdicts par des mappings de domaine. Formateurs : absence ≠ zéro, UTC explicite, blocs entiers, pourcentages contrôlés | 45 min |
| 3 | `App.tsx`, `components/ScreenShell.tsx`, `components/SubstitutionBanner.tsx` ; contexte UI dans `lib/store.ts` ou module dédié | Sidebar, ordre de nav, titre, bande contexte, sélection persistante indépendante du WS, fallback Suspense utile, bannières ancrées au bon objet. Garder lazy routes, URLs et client WS | 45 min |
| 4 | `features/live/LiveScreen.tsx` | Une bande budget, résultat remonté, journal agent, critique lue dans les bons champs, limites et mode de présentation, détails repliés | 60 min |
| 5 | `features/markets/{MarketsScreen,PriceChart}.tsx` | Headline explicite, trois vues rsETH par unité, citation marché hors courbe, mapping stable `line.id` → style, palette et axes canvas ; remplacer les légendes FR du parcours par le glossaire | 60 min |
| 6 | `features/decision/DecisionScreen.tsx` | Choix rsETH/pilote explicite, résumé du dossier et `what_would_change`, contextes d'exécution et bannières, règles et journal réels, table des reçus | 60 min |
| 7 | `features/graph/{GraphScreen,SigmaGraph}.tsx` | Canvas neutre, inspecteur 360 px, états source/schéma/PIT, styles de sélection ; supprimer `camera.animate` automatique. **Ne pas modifier `fa2.worker.ts`** | 45 min |
| 8 | `features/audit/AuditScreen.tsx` | Paquet en premier, portée des vérifications, identités historiques, états non vérifiés honnêtes, commandes copiables | 45 min |
| 9 | Tous les écrans touchés | Recette sur poste jury, erreurs, réductions de largeur/hauteur, clavier, lecture des textes EN ; derniers ajustements | 75 min |

Total nominal de la passe UI : **7 h 45 estimées**, dont **6 h 30 d'implémentation** et **1 h 15 de recette initiale**. Les priorités 3 et 4 du planning prévoient une marge supplémentaire. Cette estimation suppose les lectures de §4.3 disponibles et une personne familière des composants ; ce n'est pas un engagement mesuré. Si l'équipe n'a pas une journée disponible : conserver étapes 1–6 et la correction de portée Audit ; réduire Graph à palette, libellés et largeur d'inspecteur. Ne jamais sacrifier les bannières ou unités pour terminer une motion.

#### Classes et règles Tailwind 4 attendues

Ce sont des conventions de mise en œuvre, pas un patch :

| Élément | Classes attendues / contraintes |
|---|---|
| Surface de section | `rounded-none border border-line bg-surface shadow-none` |
| Corps / secondaire | `text-body text-ink` / `text-meta text-muted` ; pas `text-[9.5px]`, `text-muted/80` |
| Header | `min-h-16 border-b border-line bg-surface px-6` ; titre `text-page-title font-semibold` |
| Grille avec inspecteur | `grid grid-cols-1 gap-4 min-[1100px]:grid-cols-[minmax(0,1fr)_360px]` ; enfants `min-w-0` |
| Bande KPI | `grid grid-cols-2 min-[1100px]:grid-cols-4 border border-line bg-surface` ; séparateurs selon le breakpoint, pas cartes imbriquées |
| Valeur KPI | `text-kpi font-semibold tabular-nums` ; chiffres sans `font-mono` imposée |
| Bouton primaire | `h-9 rounded-[2px] border border-accent bg-accent px-3 text-on-accent hover:bg-accent-hover` |
| Input / select | `h-9 rounded-[2px] border border-line-strong bg-surface px-3 text-table text-ink` |
| Focus | `focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent` ; aucune suppression sans remplacement |
| Refus de politique | `border-ink bg-ink text-on-accent` |
| Attente / preuve manquante | `border-line-strong bg-surface text-ink` ; contour tireté seulement pour états explicitement indéterminés |
| Sélection de preuve | `border-l-2 border-accent bg-accent-soft` ; prévoir un bord transparent au repos pour éviter un décalage de largeur |
| Texte brut | `font-mono text-code break-words` ; `break-all` réservé à hashes/adresses, pas aux phrases |
| Scroll borné | `min-h-0 overflow-auto` dans le journal ; un seul conteneur de scroll table, éviter `Table` + `ScrollArea` imbriqués inutilement |

Définir les tokens de taille dans `@theme`, sans ancien `tailwind.config.js` ajouté. Pour la motion unique, propriété CSS `background-color` seulement, durée/easing de §4.10 ; retirer les `transition-colors` génériques ailleurs. Ne pas appliquer un remplacement global aveugle de `rounded-*` si un contrôle natif exige un cas particulier. `tailwind-merge` et les dépendances restent à leur version actuelle : retirer les anciennes classes conflictuelles à la source au lieu de compter sur la priorité d'une classe ajoutée.

**Canvas : point de contrôle indispensable.** Modifier `index.css` ne recolore ni Sigma ni Lightweight Charts. Remplacer les hex hardcodés dans `SigmaGraph.tsx`, `PriceChart.tsx` **et** `SeriesToggles`. Lire les variables calculées avec `getComputedStyle` au montage, ou centraliser un mapping de thème partagé ; conserver une seule source de vérité. Pas de variable CSS non résolue passée à un moteur canvas attendant une couleur. La palette actuelle de Sigma contient notamment `#fb923c` : son orange doit disparaître avec cyan, indigo, rose et lime.

### 4.13 Critères de réception de la migration

Cette checklist est à exécuter **par l'équipe d'implémentation après ses modifications**, pas par Astra pendant la présente mission en lecture seule. Ne pas confondre prescriptions de recette et tests déjà passés.

- [ ] À 1366 × 768, l'entrée sur Live montre le run choisi, `RECORDED RUN`, son résultat et ses budgets sans chercher dans une pile de cartes. Le journal reste lisible et aucun texte utile ne descend sous 12 px.
- [ ] Navigation Live → Markets → Decision : l'identité rsETH reste explicite ; les données affichées proviennent du bon run ou portent leur contexte distinct. Graph annonce Base, reçus annoncent la démonstration testnet séparée.
- [ ] La déconnexion du WS ne transforme pas l'archive en panne métier ni le cache en donnée fraîche. Une erreur HTTP est différente d'un résultat vide. Les données manquantes n'affichent pas zéro ou une autorisation favorable.
- [ ] Markets ne superpose jamais bps, USD, ratios et quantités d'actifs différents sur le même axe. Masquer une série ne change pas le style des autres. Le prix documentaire rsETH n'est pas tracé comme une série archivée.
- [ ] `isFrozen` est décrit comme une observation de configuration ; aucun texte de présentation n'en déduit à lui seul un retrait ou transfert impossible. Les sources brutes historiques sont conservées avec leur objection.
- [ ] Les hypothèses initiales, le résultat agent et l'évaluation assemblée par le scénario sont identifiés séparément ; HYP-004 n'est pas vendue comme une découverte autonome du run live.
- [ ] À côté de chaque journal d'exécution, le visiteur voit le cas, le mode, le run et la bonne déclaration de substitution ou de démonstration séparée.
- [ ] `ALLOW`, `REQUIRE_APPROVAL`, `DENY`, `INCONCLUSIVE` et `ABORTED` restent distincts ; aucune commande d'approbation/signature n'a été ajoutée.
- [ ] `VERIFIED` est réservé à un contrôle effectivement effectué et complet pour l'objet concerné. Le contrôle du dernier payload de la chaîne API est corrigé et couvert par une vérification ciblée de l'implémenteur, ou le badge est retiré. Le résultat T10 du terminal n'est pas confondu avec celui de l'API.
- [ ] Graph garde positions, worker et performances existantes ; sélection lisible, détail textuel disponible, source et limitation PIT toujours visibles. Pas de nouveau chargement réseau externe.
- [ ] Toutes les chaînes du parcours sont EN ; texte de preuve FR explicitement présenté comme original ou résumé traduit. Aucun slogan, tarif générique, version de librairie, emoji, orange, dégradé, halo, ombre ou pulse ne subsiste.
- [ ] Le build frontend existant et les vérifications ciblées sur les lectures/contrôles changés sont exécutés par l'équipe ; aucune nouvelle infrastructure de test n'est nécessaire pour les seuls styles. La recette visuelle sur machine jury complète ces contrôles.
- [ ] Après validation, préchauffer le montage suivant `docs/DEMO_SCRIPT_10MIN.md` et ne plus reconstruire après ce préchauffage. Le fallback USDC est annoncé comme un changement de cas, le paquet tiers correct est disponible, et les chiffres oraux correspondent aux artefacts remis.

**Décision de livraison :** garder le cœur ; corriger les assertions et les raccordements ; faire du dossier de preuve l'objet central de l'interface. Une journée suffit pour changer radicalement sa lisibilité. Elle ne suffit pas pour transformer des démonstrations de composants en autonomie financière prouvée.


