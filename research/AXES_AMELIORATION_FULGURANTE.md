# AXES D'AMÉLIORATION FULGURANTE — ORVYREN

**Version 1 — 14 octobre 2026.** Constat honnête, état de l'art sourcé, fonctionnement optimal visé, et ce qui se construit avant la soumission.
*Trois rapports de recherche approfondie (R1 orchestration/VOI, R2 permissions on-chain, R3 évaluation) viennent renforcer les axes A, C et E — cette version sera consolidée à leur arrivée.*

---

## 0. Le constat, sans détour

Ce qui existe aujourd'hui est un **pipeline déterministe sur un seul cas**, pas le système décrit dans la conception. Écart exact, station par station (voir `figures/orvyren_cycle_complet.png`) :

| # | Station du cycle | État réel |
|---|---|---|
| 1 | Surveiller l'exposition | **Partiel** — une baseline A0 sur une fenêtre figée ; pas de surveillance continue, pas de multi-actifs |
| 2 | Détecter un épisode | **Fait et testé** — H1/H2/H3 pré-enregistrées, critères gelés, INCONCLUSIVE prouvé par test |
| 3 | Ouvrir des branches concurrentes | **Manquant** — promis par la conception §7, aucune implémentation |
| 4 | Calculer la valeur de l'information | **Manquant** — le système cherche un fait discriminant *sans calculer s'il vaut son coût* |
| 5 | Exécuter les recherches (outils) | **Manquant** — pas d'agent : pas de boucle planifier → appeler un outil → évaluer, pas de budget |
| 6 | Verdict par branche | **Partiel** — trois verdicts statiques ; pas de mise à jour dynamique, pas de fusion |
| 7 | Décider (exposition, scénarios) | **Partiel** — le moteur est réel mais l'exposition (500/350 USDC) est une **valeur de démonstration** ; aucun portefeuille modélisé |
| 8 | Passer les verrous | **Partiel** — politique déterministe + vérification de reçu : solides et testés ; manque la **permission on-chain réelle** |
| 9 | Archiver et calibrer | **Partiel** — dossier d'audit réel (hashes) ; **aucune calibration** (prévisions gelées vs résultats) |

**En une phrase** : les briques « verrous » et « preuve » sont vraies ; le **cœur intellectuel** — branches, valeur de l'information, agent de recherche, calibration — n'existe pas encore. C'est exactement là que se joue la différenciation.

---

## 1. Méthode

Recherche en ligne (français/anglais), sources primaires privilégiées (specs, papiers, régulateurs, dépôts officiels), publications 2025-2026. Chaque axe est jugé sur : ce que ça change réellement, le coût, le risque, et **ce qu'on pourra affirmer sans mentir devant un jury**. Les sources sont citées avec leur date.

---

## 2. Les axes, classés par levier

### AXE A — Transformer « chercher une preuve » en décision optimale (valeur de l'information)

**Ce que c'est** : le système ne se contente pas de chercher un fait qui départage les hypothèses — il **calcule** la valeur espérée de chaque recherche (EVPI/EVSI : *expected value of perfect / sample information*), la compare à son coût (requêtes, latence, argent), et **ne lance une recherche que si elle peut changer la décision**. Il en déduit mécaniquement quand s'arrêter, quand s'abstenir, et quand escalader à l'humain.

**Pourquoi c'est fulgurant** : c'est le passage d'une heuristique (« va chercher des données ») à une **règle de décision démontrable** — et c'est exactement ce que la littérature 2026 dit que les agents doivent faire. Le papier *« Position: agentic AI orchestration should be Bayes-consistent »* (arXiv 2605.00742) énonce la règle : *un appel d'agent supplémentaire n'est justifié que si sa valeur d'information espérée dépasse son coût*. La version longue (HAL, hal-05480691) demande d'exprimer « routage, arrêt, abstention, escalade et allocation de budget » comme des décisions d'utilité postérieure ou de valeur de l'information. D'autres travaux 2026 vont dans le même sens : *Value of Information: A Framework for Human–Agent Communication* (ACL 2026) et *Expected Value of Information Meets Bandit Learning* (ACM, DOI 10.1145/3696410.3714773).

**Ce que ça change concrètement** : chaque branche porte une probabilité ; chaque recherche a un coût et une valeur espérée ; le budget est alloué par priorité décroissante ; le système s'arrête quand aucune recherche restante ne peut changer la décision. Les chiffres restent produits par le moteur déterministe — le LLM propose, le solveur dispose.

**Coût / risque** : moyen (algorithmes simples à implémenter : EVSI par échantillonnage sur un petit espace d'hypothèses) ; risque = probabilités subjectives non calibrées → à encadrer (voir axe G).

**Verdict : à construire — c'est LE saut conceptuel du projet.**

### AXE B — Le registre de branches (l'arbre épistémique)

**Ce que c'est** : les hypothèses deviennent des objets vivants — « chaque branche contient une hypothèse, les observations qui la soutiennent, les observations défavorables, les inconnues, les critères de réfutation, un état, une probabilité et une histoire de recherche » (conception V0.2 §7.1), avec un cycle de vie (`CREATED → UNDER_TEST → SUPPORTED/REFUTED → ARCHIVED`, `§7.2`) et un **planificateur qui construit des tâches à partir d'une lacune explicitement identifiée** (§7.3).

**Pourquoi c'est fulgurant** : c'est ce qui empêche les conclusions prématurées — et la conception prévoit déjà l'ablation qui le prouve (A1 sans branches vs **A2 avec branches, budget égal**). Un jury peut juger une démonstration où l'on **voit** une branche mourir faute de preuve et une autre survivre.

**Ce que ça change** : nouvelle table `branch` (état, probabilité, historique), liens claim↔branche, et le signal d'entrée du calculateur VOI (axe A). Les branches réfutées ne sont jamais supprimées — elles sont l'historique.

**Coût / risque** : faible-moyen (le graphe de preuve existe déjà) ; risque = complexité si on dépasse 3-5 branches — la conception fixe la limite volontairement (§16.2).

**Verdict : à construire — c'est la promesse non tenue la plus visible.**

### AXE C — La permission on-chain réelle (le thème même du concours)

**Ce que c'est** : aujourd'hui l'agent produit une instruction non signée qu'un humain exécute. Demain : le propriétaire du wallet **accorde une permission bornée** (montant, période, actif, destinataire) que la chaîne **applique elle-même**. Le standard existe et est vivant : **ERC-7715** (*Request Permissions from Wallets*, EIP-7715) introduit `wallet_grantPermissions` — « délégations délimitées et bornées dans le temps pour les session keys, les agent wallets et les abonnements on-chain » ; il est déployé via le **Delegation Toolkit de MetaMask** (annoncé par MetaMask comme « Advanced Permissions ») et actif **sur Polygon depuis avril 2026** (Relay, 17/04/2026). Les implémentations doivent réutiliser des modules audités (allowance modules de **Safe**, validateurs de **Kernel**, Coinbase smart wallet) plutôt que réinventer la permission (Eco, 2026).

**Pourquoi c'est fulgurant** : le projet devient littéralement un **Agent Wallet** — la contrainte n'est plus seulement dans notre code (contournable en théorie), elle est **appliquée par la chaîne** (impossible à contourner par l'agent). C'est la réponse la plus forte à la question « pourquoi on-chain, et pas une base SQL ? » — et ça transforme la station 8 (verrous) de « partiel » à « complet ».

**Ce que ça change** : ajouter une couche de délégation (grant, révocation, limites par période) et une démonstration où **la chaîne elle-même refuse** un dépassement, distincte du refus par notre politique (deux verrous indépendants = argument de sécurité imbattable).

**Coût / risque** : moyen (intégration d'un module audité sur testnet) ; risques = disponibilité réellement chaîne par chaîne (à vérifier), complexité de démo à 6 jours → **à câbler après la soumission si besoin**, avec la démonstration testnet minimale maintenant.

**Verdict : intégrer la version minimale démontrable ; la version complète dès que la deadline le permet.**

### AXE D — L'audit qui se **reconstruit** (et non qui se raconte)

**Ce que c'est** : passer du dossier d'une page à un **journal reconstructible** : chaque étape de l'agent (modèle appelé, outil invoqué, argument, résultat, coût) est un span horodaté, chaîné par hash, exportable dans un format standard.

**Pourquoi c'est fulgurant** : le standard d'observabilité des agents est **en train de se stabiliser et ce n'est pas encore stable** — OpenTelemetry a **déprécié tous les attributs `gen_ai.*` le 12 juin 2026** (release v1.42.0) et les a déplacés vers un dépôt dédié qui, au 12 octobre 2026, **n'a toujours aucune version taguée** ; la conséquence pratique documentée : *« aucun standard achetable n'existe encore ; le journal d'audit durable est celui que l'on héberge soi-même »*, d'autant que la règle américaine **17a-4** exige déjà de pouvoir **reconstruire l'enregistrement avec attribution** (ibl.ai, 12/10/2026). Autre confirmation : les conventions OTel considèrent un run d'agent comme un **arbre de spans** (`invoke_agent`, `execute_tool`, `gen_ai.agent.name`, `gen_ai.tool.name`) et les métriques `gen_ai.invoke_agent.tool_calls` / `inference_calls` détectent les boucles d'agent (Dash0, 2026).

**Ce que ça change** : un format maison stable aujourd'hui, aligné sur `gen_ai.*` **quand** le standard se stabilise ; un export `traces.jsonl` + un vérificateur indépendant (`verify_chain` existe déjà pour les claims — on l'étend aux étapes d'agent).

**Coût / risque** : faible-moyen (structure à définir, vérificateur à écrire) ; risque = suivre un standard mouvant → décision : format interne stable + adaptateur.

**Verdict : à construire — c'est le meilleur argument « conformité/sécurité » (30 % de la note).**

### AXE E — L'évaluation qui rend les affirmations crédibles

**Ce que c'est** : un protocole qui mesure la **qualité des décisions**, pas la qualité rédactionnelle : regret face à une référence, calibration (Brier, courbes de fiabilité, ECE), ablations à budget égal, et un **benchmark multi-cas** construit sur des épisodes historiques publics (USDC mars 2023 — déjà fait, UST mai 2022, FTX nov. 2022, stETH juin 2022, pannes d'oracles…).

**Pourquoi c'est fulgurant** : l'évaluation des agents financiers est en train de devenir un champ régulé. Le **UK Treasury Committee (rapport du 20 janvier 2026)** a demandé aux régulateurs des **stress tests spécifiques aux IA** — et la **Bank of England et la FCA ont confirmé en avril 2026** travailler sur les comportements corrélés (« herding ») d'agents. Côté benchmarks, *Finance Agent v1.1* (Vals AI) mesure des tâches d'analyste junior, et *FinanceComplexQA* (arXiv 2607.19238) évalue du raisonnement documentaire — **aucun ne mesure une décision bornée avec exécution vérifiable**, notre créneau.

**Ce que ça change** : un harnais `run_benchmark.py` (cas pré-enregistrés, résultats comparés à la baseline A0), un rapport d'ablation A1/A2, et une **taxonomie de défaillance** écrite (les 4 catégories de test que les régulateurs attendent).

**Coût / risque** : moyen ; risque = petit échantillon (ne pas prétendre à une performance générale — la conception V0.2 l'exige déjà : « si l'échantillon est insuffisant, le verdict doit rester non établi »).

**Verdict : à construire — c'est ce qui rend les 40 % « accomplissement de la tâche » vérifiables.**

### AXE F — Le moteur de risque réel (fin des valeurs de démonstration)

**Ce que c'est** : remplacer l'exposition 500/350 par un **portefeuille modélisé** : positions, décotes (haircuts), horizons de liquidité, corrélations, et une **fonction d'utilité explicite** (que cherche-t-on à protéger : un plancher de trésorerie, une limite CVaR, une maturité de passif ?). Les scénarios deviennent des chocs paramétrés, pas des illustrations.

**Pourquoi c'est fulgurant** : c'est le pont entre « agent IA » et « finance » : un jury de fintech jugera la **solidité financière** du raisonnement, pas seulement la plomberie. Et c'est ce qui rend la décision *discutable* au sens noble : on peut contester une hypothèse de modèle.

**Coût / risque** : moyen (modèle d'exposition + scénarios) ; risque = sur-promettre une précision de risque qu'un prototype ne peut pas garantir → assumer des hypothèses simples mais explicites.

**Verdict : à construire — remplace des placeholders par un modèle auditable.**

### AXE G — Calibration et apprentissage gouverné

**Ce que c'est** : chaque décision archive une **prévision gelée** (probabilité, horizon) ; quand le résultat est observable, le système calcule son score (Brier, décomposition fiabilité / résolution), tient un registre, et **n'ajuste ses seuils que par une procédure gouvernée** — jamais en pleine décision.

**Pourquoi c'est fulgurant** : c'est la réponse à la question la plus dure d'un jury (« comment savez-vous que vous avez raison ? ») — et la conception le dit déjà : « un score de Brier peut être utilisé […] mais un petit nombre de cas ne permet pas de conclure » (§12.3). La littérature 2026 sur la calibration des LLM et les garanties sans distribution (conformal prediction) donne des outils pour borner honnêtement.

**Coût / risque** : faible-moyen ; risque = confusion entre « calibration des probabilités » et « performance des décisions » → à écrire noir sur blanc.

**Verdict : à construire — c'est la différence entre un prototype et un système qui apprend.**

### AXE H — Les acteurs : séparation des devoirs

**Ce que c'est** : plus d'un acteur dans la boucle — un **analyste** (propose), un **critique adversarial** (cherche à réfuter, y compris erreurs d'unité, obsolescence, explications alternatives — conception §8), un **responsable risque** (limites), un **conformité** (politique), un **signataire** (exécution). Chacun avec des permissions distinctes et des traces distinctes.

**Pourquoi c'est fulgurant** : c'est le langage des institutions financières (segregation of duties) — et ça donne au thème F sa profondeur « agentique » : plusieurs agents qui **se contrôlent mutuellement**, dont aucun ne cumule proposition, validation et exécution.

**Coût / risque** : faible (ce sont des rôles dans la boucle, pas des microservices) ; risque = théâtre multi-agents sans valeur → chaque rôle doit avoir un **test qui prouve qu'il est nécessaire** (ablation).

**Verdict : à construire, avec preuve d'utilité par ablation.**

### AXE I — De « un cas » à « un système qui tourne »

**Ce que c'est** : surveillance continue (boucle temporelle), plusieurs actifs et plusieurs sources, reprise après arrêt, journal d'épisodes. Le mode actuel est « une commande, un cas ».

**Pourquoi c'est fulgurant** : c'est ce qui transforme une démonstration en **produit**.

**Coût / risque** : moyen ; risque = fuite de périmètre avant la deadline → version minimale maintenant (un second cas), système complet après.

**Verdict : après la soumission (conception prête).**

### AXE J — Élargir la preuve : on-chain profond, réserves, attestations

**Ce que c'est** : au-delà des prix, ingérer la **liquidité réelle** (profondeur des pools, flux de redemption), les **preuves de réserves** (oracles type Chainlink PoR), et des documents datés (communiqués) avec extraction tracée.

**Pourquoi c'est fulgurant** : la différence entre « le prix a bougé » et « la capacité de sortie a changé » — c'est-à-dire entre un signal et un diagnostic.

**Coût / risque** : moyen (chaque source = un connecteur + un test de qualité) ; risque = sources indisponibles → la porte de données les déclare manquantes (elle existe déjà).

**Verdict : une source de plus avant la soumission (on-chain), le reste ensuite.**

---

## 3. Le fonctionnement optimal et complet (cible)

Le système complet, en régime : **surveillance** (boucle temporelle sur un portefeuille modélisé) → **épisode** → **branches concurrentes** porteuses de probabilités → **calculateur VOI** qui dit quoi chercher et à quel coût → **agent de recherche** à outils bornés (lecture seule), budget encadré, critiques adversariaux → **verdicts** mis à jour, fusion ou abandon de branches → **décision** sous contrainte d'exposition (utilité explicite, scénarios) → **double verrou** (politique déterministe, puis permission on-chain bornée) → **exécution** (humain/signataire) → **vérification du reçu** → **journal reconstructible** + **dossier** → **calibration** périodique qui ajuste les seuils par procédure gouvernée. À tout moment, l'absence de preuve suffisante produit **INCONCLUSIVE** avec la liste chiffrée de ce qui manquait et de son coût.

**Invariants non négociables** (ce qui distingue ORVYREN d'un chatbot) : 1) aucun chiffre déterminant ne vient d'un LLM ; 2) aucune action sans passage par les verrous ; 3) aucune conclusion sans provenance ; 4) aucune suppression — les branches mortes et les refus restent ; 5) l'arrêt est une décision, pas un échec.

---

## 4. Priorisation — ce qu'on construit avant le 20 octobre

| Priorité | Axe | Pourquoi maintenant |
|---|---|---|
| **P0** | B (branches) + A (VOI minimal) | Le cœur manquant, réalisable en bibliothèque standard ; c'est l'innovation (30 %) |
| **P0** | F (moteur de risque réel, version simple mais explicite) | Fin des placeholders — argument financier devant le jury |
| **P0** | D (journal reconstructible) | 30 % de la note ; peu coûteux, très visible |
| **P1** | G (calibration, registre de prévisions gelées) | Réponse à « comment savez-vous ? » |
| **P1** | E (protection : benchmark 2e cas + rapport d'ablation A1/A2) | Rend les 40 % vérifiables |
| **P1** | C (permission on-chain réelle sur testnet) | Thème du concours ; la chaîne comme second verrou |
| **P2** | H (rôles séparés, avec ablation), I (surveillance continue), J (sources élargies) | Après la soumission — conception déjà écrite |

---

## 5. Ce qu'on pourra affirmer au jury (sans mentir)

1. « Notre agent ne cherche une information que si sa valeur espérée dépasse son coût — c'est une règle bayésienne publiée, pas une intuition » (arXiv 2605.00742 ; HAL hal-05480691).
2. « La contrainte n'est pas seulement dans notre code : elle est appliquée par la chaîne via des permissions bornées standard » (EIP-7715 ; Relay 04/2026).
3. « Notre agent ne détient aucune clé et aucune action n'est possible hors de l'enveloppe autorisée » (politique déterministe + 116 tests, dont les 7 attaques pré-déclarées).
4. « Nous pouvons reconstruire chaque décision : sources horodatées, hypothèses, verdicts, refus, hashes » (dossier d'audit reproductible).
5. « Nous ne revendiquons aucune performance tant qu'un échantillon suffisant ne l'établit pas » — position alignée sur les attentes réglementaires de stress tests IA (UK Treasury Committee, 20/01/2026).

---

## Annexe — Sources citées

| Sujet | Source | Date |
|---|---|---|
| Orchestration bayésienne des agents | arXiv 2605.00742 (position paper) ; HAL hal-05480691 | 2026 |
| Valeur de l'information humain–agent | ACL 2026, aclanthology 2026.acl-long.1987 | 2026 |
| EVOI et apprentissage par bandit | ACM 10.1145/3696410.3714773 | 2026 |
| Permissions de wallet | EIP-7715 (ERC-7715) ; MetaMask « Advanced Permissions » ; Relay (Polygon, avril 2026) | 2024-2026 |
| Observabilité des agents | OpenTelemetry blog genai-observability ; dépréciation `gen_ai.*` (v1.42.0, 12/06/2026) ; Dash0 (2026) ; ibl.ai (12/10/2026) | 2025-2026 |
| Stress tests IA financiers | UK Treasury Committee (20/01/2026) ; BoE/FCA (avril 2026) ; Aveni (10/06/2026) | 2026 |
| Benchmarks agents financiers | Vals AI Finance Agent v1.1 ; FinanceComplexQA (arXiv 2607.19238) | 2026 |
