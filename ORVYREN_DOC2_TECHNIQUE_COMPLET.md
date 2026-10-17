# ORVYREN — DOCUMENT TECHNIQUE COMPLET (v1)

### Document 2/4 — de la philosophie à la technique : architecture, mécanismes et décisions gelées

**Statut : spécification v1 GELÉE le 15 octobre 2026.** Ce document décrit ORVYREN v1 tel qu'il est décidé — pas tel qu'il pourrait être. Il est autonome : un lecteur externe compétent (collaborateur qui arrive, jury technique, auditeur) doit pouvoir le lire seul, sans aucun autre document, et comprendre le système « dans les moindres détails, de la philosophie à la technique ». Tous les chiffres cités sont **mesurés** (reproductibles depuis le dépôt ou adossés à une source publique datée) ; les sources publiques sont en §10.

**Ce document fait partie d'un ensemble de quatre** : (1) l'explication simple (accessible, avec schémas) ; (2) le présent document technique complet ; (3) les propositions écartées et l'horizon V2 ; (4) le plan d'implémentation. Le présent document est la référence de vérité technique ; en cas de contradiction avec tout autre écrit sur ORVYREN, c'est lui qui fait foi.

---

## Conventions de lecture

| Étiquette | Signification |
|---|---|
| **[GELÉ]** | Décision d'équipe arrêtée le 15/10/2026 — ne se rediscute pas sans procédure de révision (§5.5.6). |
| **[MESURÉ]** | Valeur produite par une mesure du projet (script exécuté, artefact reproductible), avec date. |
| **[FAIT SOURCÉ]** | Affirmation adossée à une source publique citée (URL + date, §10). |
| **[CONCEPTION]** | Choix d'ingénierie décrit ici et couvert par le gel, sans mesure propre associée. |
| **[NON TROUVÉ]** | Cherché, pas trouvé — écrit tel quel, jamais comblé par une invention. |

Deux règles de fond s'appliquent à tout ce document :

1. **Aucun chiffre sans provenance.** Chaque valeur numérique est mesurée (date + méthode) ou sourcée (URL + date) ; « on estime que » n'existe pas ici.
2. **« Spécifié » ≠ « réalisé aujourd'hui ».** Le document décrit la **v1 cible du gel** ; là où une brique n'est pas encore construite, c'est écrit noir sur blanc (§7 pour ce qui commence immédiatement, §8 pour les limites).

---

## Sommaire

1. Introduction — objet, statut, comment lire
2. ORVYREN en bref — définition, philosophie, cinq principes non négociables
3. Contexte — le problème chiffré, les utilisateurs, les épisodes, la différenciation
4. Données et faisabilité prouvée — sources gratuites testées, reconstructions, signaux, testnet
5. Architecture v1 — agents, graphe, décision, politique, exécution, audit, évaluation, UI/ops
6. Décisions gelées — le registre complet
7. Périmètre v1 — ce qui commence juste après ce document
8. Limites assumées et hors-v1
9. Glossaire complet
10. Sources publiques

---

# 1. Introduction

## 1.1 Objet

ORVYREN est un **système d'agents qui transforme des signaux financiers publics en décisions bornées et vérifiables**. Concrètement : il surveille un graphe de collatéral on-chain (stablecoins, jetons de staking liquide, positions de prêt, ponts), détecte les ruptures de risque (décote de peg, divergence entre valorisation retenue et prix réalisable, gel de marché, saturation de plafond), formule des hypothèses concurrentes, cherche le fait qui les départage, décide — ou déclare honnêtement « je ne sais pas » — puis exécute, **dans une enveloppe strictement bornée**, en laissant une trace qu'un tiers peut recalculer.

Ce document couvre **les quatre blocs qui font le système** :

- **ce qui décide** : les agents (multi-agent borné), le graphe de connaissance, la logique de décision ;
- **ce qui autorise** : la politique déterministe hors du modèle de langage et l'enveloppe de permissions on-chain (« double verrou ») ;
- **ce qui exécute** : le service de signature isolé, le préflight, la vérification de reçu ;
- **ce qui prouve** : le journal à trois flux chaînés, le vérificateur tiers, l'évaluation et la calibration.

## 1.2 Statut de ce document

- **Version** : v1, **gelée le 15 octobre 2026**. Le gel portait sur l'ensemble des recommandations issues des études de conception ; toutes ont été acceptées, avec deux ajustements (interface : exécution **100 % locale** pour la v1 ; préparation de la vidéo de démonstration **reportée**) et l'intégration des confirmations des organisateurs du concours du 14 octobre 2026 (§4.4).
- **Financement / dépendances** : aucune dépendance payante. Données : sources publiques gratuites (§4.1). Modèles de langage : API à la carte, budget plafonné (§5.2). Hébergement v1 : local (§5.9).
- **Ce que ce document remplace** : les notes de conception antérieures. Tout ce qui n'est pas dans ce document n'est **pas** dans la v1.
- **Procédure de révision** : toute modification passe par le protocole de gel (§5.5.6) — une modification de fait d'un des éléments gelés crée une nouvelle version datée et hachée ; l'ancienne reste lisible. En v1, **aucun composant ne modifie automatiquement** un seuil, une politique ou une probabilité (§5.8).

## 1.3 Comment lire ce document

- Le lecteur pressé peut lire §2 (l'essentiel en deux pages) puis §5.1 (l'architecture) et §6 (le registre des décisions gelées).
- Le lecteur technique trouvera l'ossature en §5 : chaque sous-section décrit **le contrat** (entrées/sorties), **les invariants** (ce qui ne peut pas arriver) et **les preuves** (tests, mesures) de chaque bloc.
- Le lecteur qui cherche les limites trouvera §8 : ce qu'ORVYREN ne prétend **pas** faire — écrit explicitement, sans détour.
- Les termes en gras à leur première apparition sont définis au glossaire (§9).

---

# 2. ORVYREN en bref

## 2.1 Définition

**ORVYREN est un agent d'exécution on-chain autonome et borné pour trésoreries : il détecte des ruptures de risque dans un graphe de collatéral, raisonne par hypothèses falsifiables, et n'agit que dans une enveloppe autorisée — en laissant une preuve recalculable de chaque étape.**

Trois propriétés font la définition, et chacune est vérifiable :

1. **Autonome** — l'agent exécute seul, dans l'enveloppe, sans validation humaine à chaque transaction ; c'est précisément ce qu'exige un scénario où la fenêtre d'action se compte en minutes.
2. **Borné** — la limite ne dépend ni de la bonne volonté du modèle, ni de la qualité de son prompt : elle est appliquée par une politique déterministe (hors LLM) **et** par des permissions on-chain votées, révocables par les propriétaires en une transaction.
3. **Vérifiable** — chaque étape (raisonnement, connaissance, exécution) laisse une trace horodatée, chaînée par empreintes cryptographiques, qu'un tiers peut recalculer hors-ligne sans nous.

## 2.2 Philosophie

ORVYREN part d'un constat simple et d'une conséquence sévère.

**Le constat** : les marchés on-chain sont transparents — tous les prix et tous les mouvements sont publics — mais **leurs risques ne sont pas lisibles**. La solvabilité d'une trésorerie dépend d'une chaîne de collatéraux (stablecoins, jetons de staking, actifs re-déposés partout) dont la valeur retenue par les protocoles s'écarte silencieusement du prix auquel on peut réellement vendre, et dont la dégradation est annoncée par des signaux publics dispersés (décote, dispersion entre places, divergence oracle/marché, saturation de plafond, gel administratif).

**La conséquence** : dans un incident, le facteur limitant n'est ni l'information (elle est publique) ni la capacité de calcul (elle est banale) — c'est le **temps de décision et d'exécution humain**, plus la **méfiance légitime** envers tout ce qui « agit tout seul ». ORVYREN répond aux deux : il décide et exécute en minutes, mais il agit à l'intérieur d'une enveloppe dont les pires cas sont finis, lisibles et prouvables — et il refuse de conclure quand les preuves ne le permettent pas.

La philosophie se résume en une phrase : **l'autonomie de l'agent est réelle, c'est l'enveloppe qui est la garantie ; et la garantie n'est utilisable que si elle est vérifiable par ceux qui la subissent.**

## 2.3 Les cinq principes non négociables

Ces principes sont **structurels** : ils sont implémentés par l'architecture (§5), pas par la discipline des opérateurs. Chacun a été choisi parce qu'il ferme un mode de défaillance précis.

| # | Principe | Ce qu'il ferme | Où il vit dans l'architecture |
|---|---|---|---|
| 1 | **Aucun calcul financier ne vient d'un modèle de langage.** Les modèles structurent, expliquent, proposent ; des fonctions déterministes calculent, vérifient, refusent. Un chiffre produit par un LLM est rejeté par un validateur. | L'hallucination de chiffres, la confiance verbale mal calibrée, l'injection de prompt qui fait « changer un montant » | §5.2 (validateurs), §5.4 (moteur déterministe), §5.5 (politique hors LLM) |
| 2 | **Les contradictions sont conservées, jamais effacées en silence.** Deux constats incompatibles coexistent dans le graphe comme une relation explicite, et une contradiction non résolue bloque la conclusion. | Le « lissage » qui fait disparaître un signal gênant ; la fausse confiance d'une source unique | §5.3 (relation de contradiction), §5.4 (règle « pas de verdict concluant sur contradiction ouverte ») |
| 3 | **Une hypothèse n'est jamais promue en fait** parce qu'elle est répétée ou « approuvée » par un modèle. La promotion d'une proposition (journal d'agent → graphe) exige des validateurs déterministes (schéma, provenance, absence de chiffre LLM) ; toute branche nouvelle démarre à poids nul. | L'auto-renforcement, la contamination de la mémoire partagée par du raisonnement non validé | §5.2 (journal privé séparé + protocole de promotion) |
| 4 | **L'agent ne peut pas élargir ses droits.** La limite est appliquée **hors de lui** — politique déterministe (premier verrou) + permissions on-chain (second verrou) — et révocable par ses propriétaires sans sa coopération. | La compromission de l'agent, l'erreur du modèle, la dérive de configuration | §5.5 (politique + test de dérive), §5.6 (enveloppe on-chain, kill switch) |
| 5 | **« Je ne sais pas » est une réponse de première classe.** L'abstention est produite avec la liste de ce qui manque et de ce qui changerait le verdict ; elle est journalisée et comptée comme un résultat, pas comme un échec. | La fausse décision sous incertitude, l'omission silencieuse, la pression à conclure | §5.4 (conditions d'abstention A1–A5, format enrichi) |

## 2.4 Ce que ce n'est pas

- **Ce n'est pas un bot de trading directionnel.** ORVYREN ne prend pas position sur la direction des marchés ; il protège une exposition existante (persona trésorerie) ou réduit un inventaire exposé (persona desk). Son profil est celui d'un **put** : un coût certain en échange d'une protection conditionnelle — et il le dit (§5.8).
- **Ce n'est pas un orage d'agents.** Le multi-agent est **borné et minimal** : un orchestrateur et un critique adversarial, sur deux familles de modèles, avec des budgets durs (≤ 30 appels, ≤ 12 outils, ≤ 10 minutes, ≤ 0,10 $ par décision). Pas de boucle « ReAct » libre ; un graphe fixe borné (§5.2).
- **Ce n'est pas un oracle, ni un fournisseur de signal.** Il lit des sources publiques ; il ne prétend ni les rendre infaillibles, ni certifier leur véracité (§5.7, « ce que l'audit ne prouve pas »).
- **Ce n'est pas un système de rendement.** Aucune promesse de gain, aucun token, aucune performance revendiquée. Le concours et le produit partagent cette ligne (§8).
- **Ce n'est pas juridiquement un délégataire de responsabilité.** La chaîne prouve des faits ; elle ne répartit pas la responsabilité (§5.7).
- **Ce n'est pas (encore) un produit multi-chaînes, ni bancaire.** La v1 est mono-chaîne d'exécution, testnet, une action bornée ; les banques sont une vision phase 2 (§3.2), et le document dit pourquoi.

---

# 3. Contexte

## 3.1 Le problème, chiffré : la valorisation retenue n'est pas le prix réalisable

Le cœur du problème ORVYREN tient en une phrase : **ce que les protocoles retiennent comme valeur d'un collatéral (la « valorisation retenue », lue par les oracles) peut s'écarter durablement de ce qu'une trésorerie obtiendrait réellement en le vendant (le « prix réalisable »), et c'est cet écart qui transforme une trésorerie solvable en trésorerie en difficulté.**

Trois mesures, faites sur données publiques réelles (méthode : reconstruction par appels d'archive et API publiques, sessions du 15/10/2026, reproductibles depuis le dépôt) :

**Mesure 1 — USDC / Silicon Valley Bank, 11 mars 2023.** L'oracle on-chain affichait encore **0,99065 $** à 03:00 UTC quand la médiane des places de marché était à ~**0,935 $** (divergence mesurée : **−558,9 bps**). À 07:00 UTC, une place cotait l'USDC à **0,80526 $** (plus bas horaire ; décote **1 947 bps**) tandis que l'agrégat multi-places était à **0,876675 $** (07:57 UTC) et que la dispersion inter-places atteignait **1 047,7 bps en horaire, 870 bps sur la fenêtre**. Même actif, même instant : **deux prix qui diffèrent de ~10 %**, et une valorisation retenue qui sous-estime la décote réelle de la trésorerie qui doit vendre.

**Mesure 2 — rsETH / KelpDAO, 18–20 avril 2026.** L'oracle retenait **2 526,76 $** par rsETH à l'instant de l'exploit (17:35 UTC), encore **2 513,66 $** au gel (19:03:59 UTC) et **2 419,21 $** le 20 avril — pendant que le prix de marché décrochait à **1 686 $** : divergence **≈ −31 %**, et pour la poche de collatéral concernée, une valeur réellement réalisable **nulle** (marché gelé). Pendant ce temps, 89 567 rsETH (53 400 sur Ethereum + 36 167 sur Arbitrum) avaient été déposés en collatéral contre ~190 M$ de WETH empruntés, et le taux d'utilisation du WETH est passé de **88,6 % à 99,9 % en 46 minutes** (17:21 → 18:57 UTC) : la sortie se fermait avant que quiconque ait pu décider deux fois. Le bad debt résultant est chiffré officiellement : **123,7 M$** (socialisation uniforme) à **230,1 M$** (isolement par chaîne), et la TVL DeFi a perdu **13 Md$ en 48 h**.

**Mesure 3 — stETH / Celsius, mai–juin 2022.** La décote de vente **réalisable** (mesurée par le prix de sortie effectif d'un pool, pas par l'affichage) est passée au-dessus de **2 % dès le 13–21 mai 2022** (213,7 bps le 13/05, contre 66,9 bps la veille), a culminé à **6,93 % le 14 juin 2022 à 10:00 UTC** (755,4 bps pour une sortie de 10 000 stETH) et valait encore **3,84 % fin juin** ; **227 des 253 points** de la série mai–juillet 2022 restent au-dessus de 2 %. La fenêtre d'antériorité — le temps où l'information était publique **avant** la matérialisation de la crise (gel des retraits Celsius les 12–13 juin) — est d'environ **4 semaines**.

À ces trois mesures s'ajoutent deux constats d'échelle qui situent l'enjeu :

- Sur une trésorerie de référence (ENS, 16,4 M$/an de dépenses → **44 932 $/jour** de coût opérationnel), une perte de 100 k$ vaut **≈ 2,2 jours de roulage** (« runway »). La « perte évitée » se mesure donc en jours de vie du protocole, pas en points de performance abstraits. [MESURÉ — conversion à partir du document d'investissement public de la DAO, 2026]
- Un exemple complet chiffré sur l'épisode USDC (20 M$ exposés, obligation de payer 1,37 M$ pendant la crise) : pré-positionner une part bornée à 0,95 et convertir évitait **≈ 110 912 $ (≈ 2,5 jours de roulage)** face à une conversion au plus mal (0,8820) — et **≈ 258 578 $ (≈ 5,8 jours)** si l'exécution tombait sur la place la plus décotée du panier (0,80526). **Mais sans obligation de vendre, le même aller-retour coûtait 4,0 %** (−800 000 $ sur 20 M$) : la « protection » n'a de valeur que conditionnée à l'obligation. Ce double résultat est la boussole de la v1 : l'agent est un **put payé**, pas une alpha directionnelle.

## 3.2 Pourquoi maintenant, et pour qui

### 3.2.1 Persona 1 — trésoreries de DAO, protocoles et fonds on-chain (cible prioritaire)

Objectif **mesuré dans leurs propres documents publics** : « préserver le capital et honorer les obligations de liquidité », pas « maximiser le rendement ». Le document d'investissement public de l'ENS (adopté en 2026) définit le risque de trésorerie comme *la probabilité de ne pas honorer une obligation* et *la probabilité de perdre le principal* — et impose par exemple un rapport de trésorerie disponible sous 7 jours. Un incident ouvert : le 18/04/2026, une équipe de gestion d'actifs a dû sortir manuellement ses positions de prêt adossées à rsETH **avant** le gel, puis reconstruire en mai **sans perte** : la fenêtre existait, un humain entraîné l'a attrapée — la plupart des trésoreries dorment à 3 h du matin. [FAIT SOURCÉ — documents publics de gouvernance, 2026]

Ce que cette cible achète : **anticipation** (voir venir 6 h, 6 jours ou 4 semaines), **réaction bornée** (sortir/réduire dans une enveloppe pré-votée, sans réveiller le vote de gouvernance), et **preuve** (un dossier opposable que le comité de risque — et la communauté — peut relire).

### 3.2.2 Persona 2 — équipes de trading crypto / desks (cible secondaire)

Objectif : **P&L net** après frais, gas, slippage et financement, avec des contraintes de capacité et de marge. Même machine, critères différents : le catalogue d'actions est un sous-ensemble orienté réduction/défense, les métriques sont le bp de P&L et le ratio ajusté du risque (§5.8). Aucun acteur du panel consulté ne publie ses cibles chiffrées (Sharpe cible, budget de drawdown) : nous n'en inventons aucune. [NON TROUVÉ — recherche du 15/10/2026]

### 3.2.3 Persona 3 — banques et institutions (phase 2, vision)

Même architecture, exigences supplémentaires : multi-chaînes, custodian, conformité, audit externe. **Hors périmètre v1** — la table de relations du graphe contient déjà la place nécessaire (régulation, licences) pour que la phase 2 ne soit pas une refonte (§5.3).

## 3.3 Les épisodes de référence (le terrain de jeu)

Six épisodes réels, tous reconstruits sur données publiques, jouent le rôle de sol de vérité pour la conception, la démonstration et l'évaluation :

| Épisode | Fenêtre | Ce qui a été mesuré (résumé) | Rôle dans la v1 |
|---|---|---|---|
| **USDC / SVB** | 10–14 mars 2023 | Oracle 0,99065 vs médiane ~0,935 (03:00) ; plus bas 0,80526 (Bitstamp) ; dispersion 870–1 047,7 bps ; offre en circulation **−7,17 %/24 h** ; taux d'utilisation Aave USDC 64,4 % → pic 87,3 % → 27,5 % | **Jeu DÉVELOPPEMENT** (réglages, démonstration du cycle complet) |
| **stETH / Celsius** | mai–juin 2022 | Décote réalisable > 2 % dès mi-mai, pic 6,93 % le 14/06, 227/253 points > 2 % | **DÉVELOPPEMENT — « backtest long »** (contrôle de longue série, antériorité ~4 semaines) |
| **rsETH / KelpDAO** | 17–21 avril 2026 | Saturation du plafond d'émission **99,9989 %** (529 993,98/530 000) à 18:00 ; gel daté à la seconde (**bloc 24 908 723 = 19:03:59 UTC**) ; divergence oracle/marché −31 % ; fenêtre humaine d'action **46–77 minutes** | **Jeu ÉVALUATION #1** — exécuté **une fois** après gel, le plus tardif donc le moins contaminé |
| **USD0++ / Usual** | 8–31 janvier 2025 | Changement du plancher de rachat (0,995 → 0,87) ; série horaire de 635 points, reconstruction on-chain de 610 swaps (écart moyen 0,31 %) | **ÉVALUATION #2** (mécanisme différent : débasement contractuel ; contamination probable assumée) |
| **xUSD / Stream** | 2–12 novembre 2025 | Série horaire de 457 points et 411 swaps retrouvés, mais mécanique non comparable (wrapper staké, sorties suspendues, pas d'oracle ni de profondeur) | **Qualitatif seulement** (annexe ; aucune perte évitée quantifiable honnêtement) |
| **Fenêtres CALME** | ≥ 6 fenêtres 2022–23 (DEV) + ≥ 6 fenêtres 2025–26 (EVAL) | Critère mécanique : `max|prix − 1| < 0,5 %` sur toute la fenêtre | Faux signaux, friction, placebo (l'agent doit **ne rien faire** en calme) |

La règle de séparation DEV/EVAL, les embargos et le protocole d'évaluation sont spécifiés en §5.8.

## 3.4 La différenciation : ce que le marché fait déjà, ce qu'ORVYREN ajoute

L'étude concurrentielle (recherche du 15/10/2026, sources publiques en §10) établit trois faits désagréables — donc utiles :

1. **L'enveloppe bornée est une commodité 2026.** Au moins **neuf plateformes** fournissent des « portefeuilles d'agents » avec plafonds, listes d'autorisation et clés de session (analyse de marché publique, 13/09/2026 ; synthèse des risques d'agents, 29/08/2026). **ORVYREN ne peut pas vendre l'enveloppe comme innovation** — elle est nécessaire, pas différenciante.
2. **La boucle « risque → action on-chain bornée » existe déjà, mais sous gouvernance et mono-protocole.** Des oracles de risque écrivent des paramètres de protocole dans une enveloppe pré-approuvée avec fenêtre de contestation (« limites pré-approuvées par la gouvernance », ~10 Md$ de valeur sécurisée annoncés) ; le plus avancé tourne sur infrastructure publique avec méthodologie publiée et rôle borné détenu par la DAO. C'est le concurrent le plus sérieux **et** la meilleure preuve que le concept fonctionne — mais il règle des paramètres **d'un** protocole, pas la trésorerie **multi-protocole** d'une organisation.
3. **Le créneau « prévision + décision tracée » est ouvert.** La littérature de janvier 2026 identifie le « journal de décision de politique » auditable comme chantier à construire ; le système de recherche le plus proche (prévision de réseaux d'exposition + tickets de supervision, juin 2026) se déclare lui-même « **aide à la décision pour un superviseur humain, pas un agent de risque autonome** » (résolution hebdomadaire, mono-surface). La chasse au concurrent qui ferait déjà tout : [NON TROUVÉ].

**Conséquence pour ORVYREN — la différenciation est ce qui décide *à l'intérieur* de l'enveloppe** :

- **Une décision vérifiable** : pas seulement « des garde-fous » — une chaîne complète **hypothèses → fait discriminant → décision → exécution**, dont chaque maillon est horodaté, référé et recalculable par un tiers. Les concurrents bornent des stratégies pré-écrites ou alertent des humains ; ORVYREN documente une **décision** sous incertitude, avec ses contradictions et ses refus.
- **L'abstention de première classe** : « je m'abstiens, voici ce qui manque, voici ce qui changerait le verdict ». Aucun acteur du panel ne publie ce comportement ; c'est pourtant la réponse correcte dans la moitié des situations réelles (après un gel, la bonne décision est souvent « la sortie est fermée, j'escalade »).
- **Le double verrou** : politique déterministe hors LLM **et** permissions on-chain votées, avec un test de dérive automatique entre les deux — la borne ne dépend ni du modèle, ni d'une UI, ni de la bonne santé d'un service : elle survit à la compromission de l'agent.

Corollaire assumé : **ne pas vendre** ce qui est commoditisé (caps, allowlists, exécution conditionnelle, « non-custodial », « 24/7 ») et **vendre** ce qui est rare : le signal, la preuve, le refus, le coût marginal par décision (≤ 0,10 $).

---

# 4. Données et faisabilité prouvée

Tout ce que décrit ce document tourne sur des **sources gratuites, sans clé API**, testées le 15 octobre 2026. Cette section est la preuve de faisabilité : sources testées (§4.1), trois reconstructions d'épisodes de bout en bout (§4.2), signaux mesurés et seuils candidats (§4.3), et le socle testnet validé par les organisateurs (§4.4).

## 4.1 Sources de données — testées, gratuites, sans clé

### 4.1.1 États on-chain historiques (la brique critique)

| Source | Ce qu'elle donne | Mesure du 15/10/2026 |
|---|---|---|
| `eth.drpc.org` (RPC public) | **Archive complète Ethereum** : `eth_call` sur n'importe quel bloc passé | Testé avec succès sur des blocs 2021 → 2026 (Aave V2/V3, Lido, Curve, Chainlink) ; ~0,65 s par appel séquentiel |
| `eth-mainnet.public.blastapi.io` (repli) | Idem | Repli automatique testé ; ~0,36 s par appel ; **12,4 appels/s sur 8 fils** en charge |
| Limite mesurée | `eth_getLogs` ≤ **10 000 blocs par requête** sur les paliers gratuits | Pagination automatique implémentée (gratuite, sans perte) |
| Refusés (testés) | `ethereum.publicnode.com` (« archive requests require a token »), `cloudflare-eth.com`, `1rpc.io/eth` (pas d'état historique), `rpc.flashbots.net` | Motivés et écartés — aucun n'est requis |

**Pourquoi c'est décisif** : l'état on-chain historique à un bloc donné est un **point-in-time parfait par construction** (le bloc est monotone dans le temps, l'état d'un bloc est immuable). C'est la colonne vertébrale temporelle du graphe (§5.3.4) : chaque fait on-chain porte `(chaîne, bloc, transaction)`, et un rejeu d'`eth_call` au même bloc reproduit le même résultat — vérifié par relance complète d'une reconstruction de 1 538 appels : **identique au bit près**.

### 4.1.2 Prix multi-places et masse monétaire

| Source | Granularité | Profondeur | Coût |
|---|---|---|---|
| Binance `api.binance.com/api/v3/klines` + dumps mensuels `data.binance.vision` (y compris `aggTrades` pour la microstructure) | 1 minute (tick pour les dumps) | complet depuis cotation ; testé sur mars 2023 | Gratuit, sans clé |
| OKX `/api/v5/market/history-candles` | 1 minute | paginé ; testé mars 2023 | Gratuit, sans clé |
| Kraken `/0/public/Trades` | tick (agrégeable 1 min) | complet | Gratuit, sans clé |
| Bitstamp `/api/v2/ohlc` | 1 minute | complet | Gratuit, sans clé |
| DeFiLlama `coins.llama.fi` (`prices/historical`, `chart`) + `stablecoins.llama.fi` + `yields.llama.fi` | 1 min / 1 h, multi-chaînes, scores de confiance | testé sur USDC 2023, stETH 2022, rsETH 2026 | Gratuit, sans clé |
| Refusés / écartés (testés) | CoinGecko sans clé (**401**), CryptoCompare (**401**), Dune en lecture seule (inutilisable en pipeline), Kaiko (~1 000–2 500 $/mois) | — | Aucun n'est nécessaire |

### 4.1.3 Contrats et feeds — adresses vérifiées on-chain (2026)

Feeds d'oracle Ethereum : `USDC / USD` (`0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6`), `STETH / ETH` (`0x86392dC19c0b719886221c78AB11eb8Cf5c52812`), `Capped rsETH / ETH / USD` (`0x7292C95A5f6A501a9c4B34f6393e221F2A0139c3` — lu via `description()` ; le feed **réverte sur `latestRoundData()`**, seuls `description()`, `decimals()` et `latestAnswer()` répondent : la couche données le gère et le documente). Pool Curve stETH/ETH (`0xDC24…7022`), Curve 3pool (`0xbEbc…1C7`), Uniswap QuoterV2, Aave V3 Pool Ethereum (`0x8787…A4E2`) et Arbitrum, tokens rsETH/aEthUSDC/aEthrsETH. Toutes ces adresses ont été **lues et vérifiées** (`eth_getCode`, `symbol()`, `decimals()`, comparaison oracle Aave ↔ feed Chainlink sur 5 blocs clés : identiques). Leçon de méthode actée : **les adresses et sélecteurs se re-vérifient à l'exécution, jamais de mémoire** (§5.6).

### 4.1.4 Performance mesurée (budgets de la v1)

- Reconstruction complète de l'épisode USDC (97 points horaires × oracle + Aave + 4 sources de prix) : **~2 minutes** de bout en bout.
- Lecture horaire oracle + état Aave : **~15 secondes** pour une journée.
- Résolution bloc ↔ horodatage par dichotomie : 97 heures en **6 requêtes groupées** (463 sondes JSON-RPC) ; en série parallèle, 9,9 s/point → **2,07 s/point** avec 5 tranches.
- Ces coûts réels fondent le budget par décision (§5.2) : le budget est exprimé en **requêtes + secondes mesurés**, pas en tokens.

## 4.2 Trois reconstructions d'épisodes, de bout en bout

Chaque épisode a été **reconstruit exécutable**, pas résumé : scripts relançables, sorties JSON de preuve, tests hors-ligne. Les valeurs ci-dessous sont mesurées ; elles constituent la matière première de la démonstration (§5.6) et de l'évaluation (§5.8).

### 4.2.1 rsETH / KelpDAO — 17 → 21 avril 2026 (100 points horaires + blocs clés)

| Instant (UTC) | Fait mesuré | Valeur |
|---|---|---|
| 18/04 17:35 | Exploit : paquet de pont forgé, 116 500 rsETH libérés (~292 M$) | [FAIT SOURCÉ + reconstruit] |
| 18/04 18:00 | **Plafond d'émission saturé : 99,9989 %** (529 993,98 / 530 000), après +48 725 rsETH déposés en ~6 h | [MESURÉ — on-chain, bloc 24 908 406] |
| 18/04 18:52 | Gel des marchés annoncé (77 min après le drain) | [FAIT SOURCÉ] |
| 18/04 19:03:59 | **Gel de la réserve : `isFrozen` 0→1, bloc 24 908 723** (dernier bloc non gelé 24 908 722 à 19:03:47) — trouvé par **recherche dichotomique en 14 itérations** | [MESURÉ] |
| 19/04 08:00 | WETH gelé, LTV → 0 ; utilisation WETH **100,0079 %** ; cash USDC d'Aave : **6 403 $** pour 2,47 Md$ de supply | [MESURÉ] |
| 18–20/04 | Oracle rsETH : 2 526,76 $ (exploit) → 2 513,66 $ (gel) → 2 419,21 $ (20/04) vs marché 1 686 $ — **−31 %** | [MESURÉ] |
| 20/04 | Bad debt chiffré **123,7 M$ / 230,1 M$** ; TVL DeFi −13 Md$ en 48 h | [FAIT SOURCÉ] |

**Reconstruction : 100 points horaires, blocs clés datés à la seconde, rejouée identique au bit près.** Correction documentée : l'hypothèse initiale « marché bloqué par une utilisation à 100 % » est **fausse** — l'utilisation de la réserve rsETH était ≈ 0,008 % (aucun emprunt) ; le mécanisme réel est le **gel administratif** d'une réserve dont l'LTV était déjà 0, précédé par la **saturation du plafond**. C'est exactement le type d'erreur qu'un système « qui mesure » doit détecter et consigner.

### 4.2.2 stETH / Celsius — mai → juillet 2022 (253 points, décote réalisable)

- Décote **réalisable** (prix de sortie effectif du pool Curve pour la taille de la trésorerie, pas l'affichage) : 0,082 % au calme (5 mai) ; **> 2 % dès le 13–21 mai** (213,7 bps le 13/05) ; **pic 6,93 % le 14/06 à 10:00 UTC** (755,4 bps pour 10 000 stETH) ; **6,42 % le 15/06 à 22:00** ; 3,84 % le 30/06.
- **227 des 253 points restent > 2 %** jusqu'au 31 juillet.
- Point de référence reproduit à l'identique depuis l'archive : bloc 14 970 000, 15/06 22:43:58, **6,185 %**.
- Étalonnage de profondeur (calme) : 1 000 stETH → 0,56 bp ; 10 000 stETH → 7,13 bp ; Uniswap 0,01 % : 100 000 USDC → ~1,7 bp d'impact marginal.
- Antériorité mesurée ≈ **4 semaines** avant le gel des retraits (12–13 juin) : c'est le seul signal à préavis long du dossier.

### 4.2.3 USDC / SVB — 10 → 14 mars 2023 (97 points horaires, 6 sources)

- Oracle Chainlink : minimum **0,8833** (11/03 07:53 UTC) ; plus bas agrégé **0,876675** (07:57) ; Bitstamp plus bas **0,80526** (07:00) ; OKX 0,8698 ; Binance plus bas 0,8820 ; clôture Bitstamp 0,86267.
- **Dispersion** : maximale horaire 1 047,7 bps ; 870,07 bps sur la fenêtre ; au repos < 5 bps.
- **Divergence oracle/marché** : −558,9 bps (11/03 03:00) ; l'oracle ne descendra que jusqu'à 0,9069–0,8833 pendant que le marché voyait 0,805–0,877.
- **Offre en circulation : −7,17 % sur 24 h** ; taux d'utilisation Aave V3 USDC : 0,6443 → pic 0,8727 (11/03 03:00) → 0,2754 (12/03 23:00) ; guérison (oracle 0,9910) le 13/03 à 08:51.
- Hypothèses sur données réelles : « perturbation locale » **réfutée** (décote > 1 % persistante 42 h sur une place, 45 h sur une autre), « stress large » **soutenue** (34 heures simultanées > 1 % sur deux places indépendantes + baisse d'offre −7,17 %/24 h), « artefact » **réfutée** (sources concordantes). **C'est la démonstration que la chaîne « signal → hypothèses → fait discriminant → décision » fonctionne sur des données réelles.**
- Convention de prix à retenir (tranchée au gel) : la **même heure** vaut 0,86267 en clôture et 0,80526 en plus bas chez Bitstamp — l'écart de convention (740 bps) dépasse beaucoup de seuils. Décision gelée : **double convention assumée** — alerte de stress sur le **plus bas**, décision sur **clôture + plus bas**, et les deux lectures sont publiées partout où un seuil décide (§5.4).

## 4.3 Signaux mesurés et seuils candidats

Les signaux ci-dessous ont tous été **calculés sur données réelles** le 15/10/2026. Les seuils sont « candidats » au sens du gel : ils sont justifiés par les mesures ci-dessus, et leur calibration statistique par quantiles (sur 12 mois d'historique) est un chantier identifié (§7) — jamais un prétexte pour attendre.

| # | Signal | Formule (résumée) | Seuil candidat | Justification mesurée | Antériorité observée |
|---|---|---|---|---|---|
| 1 | **Décote de peg** | écart du prix (médiane pondérée multi-places) au peg de référence | **≥ 50 bps / 15 min** = alerte ; **≥ 200 bps** = rupture ; **≥ 500 bps** = sortie obligatoire | au repos < 5 bps de dispersion ; 870 bps le 11/03/2023 ; 6,93 % stETH | heures à semaines |
| 2 | **Dispersion inter-places** | max − min entre places à volume significatif | **> 100 bps** = référence unique non fiable ; **> 300 bps** = exclure la place extrême | 870–1 047,7 bps mesurés (USDC) ; < 5 bps au repos | quelques heures |
| 3 | **Divergence oracle / marché** | prix de marché − valeur retenue par l'oracle | **\|Δ\| > 100 bps pendant > 1 h** = ne plus valoriser sur l'oracle | 296–559 bps (USDC) ; **31 %** (rsETH) ; jusqu'à ~1 000 bps vs la place la plus décotée | ~6 h (rsETH) |
| 4 | **Décote réalisable d'un LST (ladder de tailles)** | prix de sortie effectif pour la taille exacte de la trésorerie | **≥ 100 / 300 / 600 bps** (alerte / exploitable / juin 2022) | 2,57 % le 21/05/2022 ; 6,19 % le 15/06 ; 0,07–0,56 bp au calme | **~4 semaines** |
| 5 | **Utilisation d'un marché de prêt** | 1 − liquidité disponible / offerte | **> 90 %** = profondeur < 10 % ; **> 99 %** = file d'attente de fait | montée 88,6 % → 99,9 % **en 46 min** (WETH, 18/04/2026) | minutes (confirmation) |
| 6 | **Gel administratif d'une réserve** | bit « gelé » de la configuration | **0 → 1** = sortie fermée | daté à la seconde : bloc 24 908 723, 19:03:59 UTC | **aucun préavis** (confirmation) |
| 7 | **Saturation de plafond d'émission** | émission / plafond | **≥ 95 %** = plus d'entrée possible | **99,9989 %** le 18/04 18:00, +48 725 rsETH en 6 h | −25 min après l'exploit (confirmation) |
| 8 | **Baisse d'offre en circulation 24 h** | variation du stock émis | **> 1 %** | **−7,17 %** sur USDC (11/03/2023) ; discriminant H1→H2 | heures |
| 9 | **Impact / profondeur d'exécution** | perte au change pour la taille X | profondeur < taille de sortie ⇒ actif traité comme non liquide | 7,13 bp pour 10 000 stETH au calme ; 755 bp en crise | (dimensionne l'action) |
| 10 | **Valorisation « fixe / plafonnée »** | libellé du feed (« Capped… ») + variance nulle du prix retenu | détection de label / variance ≈ 0 | cas xUSD et USD0++ (prix oracle figé pendant que la sortie se fermait) | (détection structurelle) |
| 11 | **Invariant d'émission inter-chaînes** | émis sur chaîne distante ≤ verrouillé sur la chaîne source | violation = incident | nommé comme la **seule détection possible** du cas KelpDAO par l'analyse forensique publique | rapide (le bloc de la frappe) |

**Bilan d'antériorité, écrit honnêtement** : un seul signal a une antériorité longue mesurée (la décote persistante d'un LST, ~4 semaines) ; deux ont une antériorité courte mais réelle (divergence oracle/marché ~6 h ; dispersion quelques heures) ; les autres (gel, saturation, décote brusque) sont des **signaux de confirmation** — utiles pour réagir vite et bien, pas pour anticiper des jours à l'avance. La v1 est conçue pour les deux régimes : **anticiper quand c'est possible, réagir proprement quand ça ne l'est pas**.

## 4.4 Le testnet : confirmations et socle vérifié

**Confirmations des organisateurs du concours (14 octobre 2026)** : (1) la preuve d'exécution sur **testnet est pleinement acceptée** — agent sur **Base Sepolia** avec hashes réellement vérifiables (reçus, blocs, émetteur, destinataire) ; le mainnet n'est pas requis ; (2) les pièces d'identité nationales sont acceptées pour l'inscription ; (3) **aucune restriction sur les modèles d'IA** utilisés ; (4) inscription traitée par l'équipe. La v1 intègre ces faits : toute la démonstration d'exécution vit sur Base Sepolia.

**Socle testnet vérifié par mesure (15/10/2026, RPC `https://sepolia.base.org`, blocs 48 150 148 → 48 150 201)** :

- `chainId = 0x14a34` (84532) ; gaz : `gasPrice` 0,006 gwei, `baseFee` 0,005 gwei — un transfert ≈ 50 000 gaz ≈ **3 × 10⁻⁷ ETH** (0,01 ETH couvre des milliers de transactions de démonstration) ; les tags `safe` et `finalized` sont servis par le RPC (politique de confirmations §5.6).
- **Deux USDC distincts coexistent sur Base Sepolia** — découverte opérationnelle : l'USDC « de test » (Circle, `0x036CbD53…CF7e`, utilisé par les pools d'échange) et l'USDC d'Aave (`0xba50Cd2A…4d5f`, réserve de prêt). **Ils ne sont pas interchangeables** ; chaque usage a son robinet. [MESURÉ]
- Uniswap v3 (routeur, fabrique, Quoter, positions) **déployé et liquide** : quotes en direct mesurées (50 USDC → 0,0106 WETH via frais 3000). **Attention documentée** : deux étages de frais du même couple cotaient 4 674 et 2 479 USDC/WETH au même instant — **les prix de testnet ne sont pas des données de marché** ; la démo prouve le **chemin d'exécution**, jamais l'économie.
- Aave v3 (Pool, oracle, 6 réserves dont USDC/WETH) déployé ; réserve USDC active, non gelée (LTV 82,5 %, plafond 0).
- Module de permissions (rôles Zodiac v2) : code déployé, bytecode identique Ethereum/Base/Base Sepolia (`0xF296…83D5`) ; événement `AssignRoles`, consommateurs d'allowance et kill switch vérifiés (détails §5.6).
- **Sélecteurs vérifiés fonctionnellement** (calcul keccak local + bytecode + appels réels) : `transfer(address,uint256)` = `0xa9059cbb` ; `exactInputSingle` du routeur = `0x04e45aaf` (la variante avec `deadline`, `0x414bf389`, est **absente** du routeur déployé — l'annuaire public de sélecteurs s'est révélé bruité) ; `repay` d'Aave porte la signature **réellement déployée** `repay(address,uint256,uint256,address)` (`0x573ade81`), pas la forme de la documentation. **Leçon actée : la signature d'appel se prend du contrat déployé, jamais de la doc ni de la mémoire.**

**État du code et des tests au gel** : la couche données (lecture d'archive, Curve, Aave, Chainlink), les reconstructions d'épisodes, la politique (12 tests dédiés, « 0 action hors politique »), le moteur de décision (épisode USDC rejoué), le graphe v0 (append-only, snapshots hachés) et l'audit du dossier v1 existent et tournent : **221 tests verts, 2 sautés** (les sautés sont les tests réseau, désactivés par conception). Le total ne fait que croître : jamais un test cassé, jamais un saut ajouté sans raison. [MESURÉ — 15/10/2026]

---

# 5. ARCHITECTURE v1

## 5.1 Vue d'ensemble

### 5.1.1 Le cycle complet (schéma de référence)

```
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │                          LA BOUCLE ORVYREN (v1)                              │
 └──────────────────────────────────────────────────────────────────────────────┘

 ① OBSERVER           sources multiples, horodatées, avec provenance
     │                (prix multi-places, chaîne par blocs d'archive, documents)
     ▼
 ② VÉRIFIER           qualité, unités, trous DÉCLARÉS (jamais inventés)
     │                → GRAINE DU GRAPHE : observations, claims, relations
     ▼
 ③ DÉTECTER           signaux : décote, dispersion, divergence oracle/marché,
     │                saturation, gel, invariants inter-chaînes
     ▼
 ④ HYPOTHÈSES         plusieurs explications concurrentes (agent LLM),
     │                critères de réfutation écrits D'AVANCE (obligatoires)
     ▼
 ⑤ RECHERCHER         le fait qui départage — recherche discriminante
     │                ordonnée par falsification (déterministe, bornée)
     ▼
 ⑥ DÉCIDER            3 axes séparés : épistémique / économique / autorisation
     │                action bornée, abstention (« il manque ceci »), ou escalade
     ▼
 ⑦ AUTORISER          VERROU 1 : politique déterministe hors LLM
     │                VERROU 2 : enveloppe on-chain (permissions votées)
     ▼
 ⑧ EXÉCUTER           service de signature ISOLÉ (clé hors LLM/graphe/politique)
     │                préflight 12 contrôles → tx → reçu → vérification
     ▼
 ⑨ PROUVER            journal 3 flux chaînés SHA-256 + dossier 1 page
     │                + paquet 12 pièces + vérificateur tiers (T10)
     ▼
 ⑩ ÉVALUER            prévisions gelées → outcomes → calibration (Brier/ECE)
                      rejeu 2 modes (journal bit-à-bit / archive) — sans redescente
                      dans la décision : rien ne s'auto-révise en v1
```

Deux lectures utiles du schéma :

- **Les verrous (⑦) sont hors de la boucle de raisonnement** : l'agent peut aller jusqu'à « je propose cette action bornée » ; il ne peut ni autoriser, ni signer, ni modifier sa politique.
- **La preuve (⑨) et l'évaluation (⑩) ne réinjectent rien** : en v1, aucun seuil, aucune probabilité, aucune politique ne se modifie automatiquement à partir des scores (§5.8).

### 5.1.2 Forme d'architecture : monolithe modulaire

**Choix gelé** : un **seul service** (monolithe modulaire), conforme au contexte de l'équipe (un développeur, Python, dépendances minimales), avec des **modules aux frontières d'import strictes**. Ce n'est pas un renoncement : les « coutures » nécessaires au multi-agent réel (§5.2) et à la séparation des privilèges (§5.5, §5.6) sont posées dès la v1.

| Module | Rôle | Peut importer | Ne peut PAS importer |
|---|---|---|---|
| `data` | Connecteurs : archive on-chain, Curve/Aave/Chainlink, prix multi-places | stdlib | le reste du système |
| `quality` | Normalisation, unités, contrôles de qualité, rapports | `data` | LLM, décision |
| `graph` | **Le graphe** : modèles, store append-only (seul point d'accès base), provenance, snapshots | `quality` | LLM, décision, exécution |
| `agents` (nouveau) | Orchestrateur, explorateur, critique ; journaux privés ; budgets | `graph` (lecture), outils | `policy`, `execution` (écriture), clés |
| `decision` | Moteur déterministe : hypothèses, recherche discriminante, catalogues, calculs | `graph` (lecture), `quality` | LLM (aucun appel), `execution` |
| `policy` | **Verrou 1** : évaluation pure des 14 règles (entrée : intention + config + état ; sortie : verdict) | rien d'autre (pur) | LLM, LLM-only, réseau |
| `execution` | Construction de calldata, préflight, client signataire (processus séparé), vérification de reçu | `policy` (types) | LLM, graphe (écriture), agents |
| `audit` | Dossier, journaux, paquet, manifeste | lecture de tous les artefacts | aucun écrivain métier |
| `verify` (nouveau) | **Vérificateur tiers T10** : recalcule hors-ligne | lecture seule de `audit`, fonctions pures | réseau (mode offline), état caché |
| `evaluation` (nouveau) | Pertes, comparateurs, calibration, harnais | `graph`, artefacts | écriture dans la décision |
| `ui` | Interface **lecture seule** (HTML statique, sans JavaScript) | lecture des artefacts | écriture, clés |

**Règle d'or des dépendances** : `policy` est un service **pur** (aucune entrée/sortie réseau, aucune lecture LLM) et `execution` n'accepte que le verdict `ALLOW` — un refus lève une exception et est journalisé. Ces deux faits sont testés et le resteront : c'est ce qui rend « le LLM ne détient rien » structurel et non déclaratif.

### 5.1.3 Les trois mémoires, strictement séparées

| Mémoire | Quoi | Qui écrit | Qui lit |
|---|---|---|---|
| **Le graphe** (mémoire partagée des faits) | Faits, observations, relations typées, horloges, provenance — append-only, snapshots hachés | Le pipeline (règles, lectures on-chain, extraction validée) — **jamais un LLM directement** | Agents (lecture), décision, audit |
| **Le journal d'agents** (`agent_journal`, mémoire interne) | Réflexions, plans, appels d'outils, propositions, quarantaines, coûts — un flux par agent, append-only, chaîné | Chaque agent (son propre flux) | L'UI, l'audit, le rejeu — **jamais le moteur de décision** |
| **Le journal d'exécution** (`audit.jsonl`) | Intention → politique → simulation → envoi → reçu → vérification, chaîné par hash | Le pipeline d'exécution (un seul écrivain) | L'audit, le vérificateur, le jury |

**Règle non négociable** : le moteur de décision ne lit **jamais** les journaux d'agents. Si une information n'existe que dans un journal, elle n'existe pas pour la décision. C'est ce qui garantit qu'aucun raisonnement non validé ne peut influencer un chiffre.

### 5.1.4 Stores et hébergement (v1 → cible)

| Élément | v1 (concours) | Cible post-concours | Pourquoi |
|---|---|---|---|
| Base du graphe et des journaux | **SQLite** (append-only, triggers qui interdisent UPDATE/DELETE, snapshots SHA-256) | **PostgreSQL** (Neon gratuit permanent : 1 Go/projet) | Zéro ops en démo, hors-ligne par conception ; migration contenue dans **un seul module** (le store), DDL identique |
| Recherche sémantique | optionnelle (aucune dépendance) | `pgvector` (recherche de documents proches) | ML-1 ci-dessous — hors chemin décisionnel |
| Exécution | Base Sepolia (testnet), clé jetable | Backend de clés remplaçable (HSM/KMS) | E1 §5.6 |
| Interface | **100 % locale** (§5.9) | Service web lecture seule + Postgres en miroir | Décision gelée H3 |

**Écartés et pourquoi (assumé)** : base graphe embarquée archivée par son éditeur en octobre 2025 (support amont nul) ; base graphe SaaS inutile à l'échelle (quelques milliers de nœuds) et ajoutant une seconde base à synchroniser ; RDF/PROV-O conservé comme **vocabulaire d'export** (les noms de la famille « preuve et dérivation » suivent la recommandation W3C PROV-O), pas comme stockage.

## 5.2 Bloc A — Agents (MA-B : multi-agent borné)

### 5.2.1 Topologie gelée

**MA-B** : **orchestrateur + critique adversarial en instances séparées**, chacun avec son journal propre et ses outils bornés ; le critique tourne sur un **second modèle** (famille différente) — « second avis » cross-modèle démontrable dès la v1. Extension multi-agents complète possible plus tard **sans refonte**, à condition que deux règles soient tenues dès maintenant : (1) chaque rôle écrit dans **son** journal avec le même schéma d'entrée ; (2) la communication entre rôles passe par des **objets sérialisables** (tâche de recherche, paquet de preuves, rapport de critique), jamais par un état mémoire partagé.

| Rôle | Modèle (gelé) | Mission | Sorties |
|---|---|---|---|
| Orchestrateur / planificateur | `deepseek-flash` (température 0) | Lire le snapshot du graphe, détecter les lacunes, produire le plan de recherche | Plan (JSON strict), tâches ordonnées |
| Explorateur / canonicaliseur | `deepseek-flash` | Formuler les hypothèses, structurer des documents en objets, expliquer | Propositions (poids 0 jusqu'à validation) |
| **Critique adversarial** | `mimo-v2.6-pro` (2ᵉ famille) | Attaquer : chercher l'hypothèse manquante, l'incohérence, le biais de confirmation, l'item de preuve non recherché | Rapport d'objections → déclenche la recherche suivante |
| Rédacteur de dossier | **aucun LLM** | Rendu du dossier 1 page par gabarit déterministe | Dossier md/html |

**Pourquoi deux modèles** : un second avis d'une **autre famille** est exactement ce qu'un critique adversarial doit apporter (l'essai comparatif « second modèle vs seconde passe du même modèle à budget égal » reste au registre des expérimentations, mais la v1 l'implémente par défaut — décision gelée A3).

### 5.2.2 Modèles, prix et épinglage

**Choix gelés** : `deepseek-flash` (principal) et `mimo-v2.6-pro`/`mimo-v2.6-flash` (secondaire/critique). Prix officiels vérifiés le 15/10/2026 : DeepSeek flash **$0,003 / $0,15 / $0,60** par million de tokens (entrée cache atteint / entrée / sortie, tarif hors pointe — le cache d'entrée répété est décoté ×50) ; MiMo flash **$0,0028 / $0,14 / $0,28** ; MiMo pro **$0,0036 / $0,435 / $0,87** ; contexte 1M tokens, sorties structurées JSON et appels d'outils disponibles chez les deux.

**Coût réel d'une décision, mesuré sur le profil d'appels cible** : 12 appels (60k tokens d'entrée manqués, 200k en cache, 6k de sortie) → **0,0132 $** (DeepSeek flash hors pointe) ; profil plafond 30 appels → **0,0363 $**. **Le coût n'est pas un critère de choix entre les deux familles** — les critères réels sont la stabilité des identifiants, la conformité JSON, la latence, les quotas. Un rejeu complet de trois épisodes coûte **0,03–0,04 $**.

**Épinglage obligatoire** : les fournisseurs **déprécient et redirigent les identifiants de modèle** (observé : redirection d'anciens noms DeepSeek vers la version courante ; dépréciation d'identifiants MiMo annoncée **pendant la fenêtre de concours**, 21/10/2026). Conséquence : un fichier de configuration versionné fige les identifiants exacts + la date de vérification, avec un **test de fumée** qui échoue si l'identifiant n'existe plus. La reproductibilité ne repose **pas** sur « même modèle, même prompt » (faux : les piles d'inférence hébergées ne sont pas déterministes à température 0 — non-associativité des flottants + batching) mais sur le **journal des réponses** (prompt et réponse archivés, hachés).

### 5.2.3 `agent_journal` — la mémoire interne, séparée du graphe

Table **append-only**, chaînée par hash (`prev_hash`), table **séparée du graphe**, jamais lue par le moteur de décision. Une ligne = un événement de raisonnement. Champs principaux :

`journal_id` (ULID) · `run_id` / `episode_id` · `agent_id` (`orchestrator` | `explorer` | `critic` | spécialiste) · `role_version` (version du prompt) · `step_index` · `ts_utc` · `kind` (`PLAN`, `TOOL_CALL`, `TOOL_RESULT`, `OBSERVATION_REF`, `REFLECTION`, `HYPOTHESIS_PROPOSED`, `BRANCH_UPDATE`, `CRITIQUE`, `DECISION_DRAFT`, `STOP`, `ERROR`) · `content` (texte de la réflexion) · `refs[]` (renvois vers le graphe : observations, claims, hypothèses) · `status` (`PROPOSED` | `ACCEPTED` | `REJECTED` | `QUARANTINED`) · `validation` (résultat des validateurs : schéma, « pas de chiffre LLM », provenance, motif) · `llm` (fournisseur, modèle, version épinglée, température, raisonnement) · `prompt_hash` / `response_hash` (les payloads bruts vivent dans un magasin immuable, indexés par hash) · `tokens_in` / `tokens_out` / `cached_in` · `cost_usd` · `latency_ms` · `prev_hash`.

**Protocole de promotion (journal → graphe)** — 5 étapes, toutes déterministes sauf la dernière :

1. L'agent écrit une réflexion/proposition → ligne `PROPOSED`.
2. **Validation de forme** (déterministe) : schéma strict ; champ inconnu → `QUARANTINED` ; **chiffre produit par le LLM → `REJECTED`**.
3. **Validation de provenance** : chaque référence doit exister et être admissible à l'instant simulé (invariant PIT).
4. **Promotion** (déterministe pour les observations/claims ; relecture humaine pour les nouvelles branches) : l'objet entre dans le graphe avec le lien vers la ligne de journal d'origine ; une branche nouvelle démarre **à poids nul**.
5. Le refus est conservé (`REJECTED`) : c'est un résultat, et il est **démontrable** (« la mémoire interne n'a pas contaminé le graphe »).

**Ce qui n'entre jamais dans le graphe** : hypothèses non validées, raisonnements libres, valeurs numériques calculées par le modèle, sorties en quarantaine, historique conversationnel. **Rétention du journal : intégrale** (décision gelée A6) — les volumes sont négligeables et la valeur de preuve est maximale.

### 5.2.4 La boucle bornée et ses cinq conditions d'arrêt

La boucle n'est **pas** une boucle « ReAct » libre — c'est un **graphe fixe borné** : planifier → appeler **un** outil → évaluer → continuer ou s'arrêter. États : `IDLE → PLANNING → EXECUTING → (RECOVERING) → DONE / ABORTED`, avec une seule tâche en vol.

| Condition d'arrêt | Déclencheur |
|---|---|
| ARRÊT-1 | Plus aucune tâche à valeur positive dans le plan |
| ARRÊT-2 | Budget épuisé (un des quatre compteurs ci-dessous) |
| ARRÊT-3 | Validation impossible (schéma en quarantaine, provenance cassée) → **arrêt fail-closed** |
| ARRÊT-4 | Preuve jugée suffisante (garde-fou, jamais critère principal) |
| ARRÊT-5 | Aucune recherche ne vaut plus son coût (recherche discriminante : invariance de décision) |

**Budgets par décision (gelés, vérifiés avant chaque appel/outil)** :

| Compteur | Plafond |
|---|---|
| Appels LLM | **≤ 30** |
| Appels d'outils / recherches | **≤ 12** |
| Temps mural | **≤ 10 min** (démo ; 2 min si live) |
| Coût API | **≤ 0,10 USD** |

Aucun agent **ne peut augmenter son budget ni élargir sa liste de sources** : les plafonds sont des paramètres de configuration versionnés, pas des constantes cachées ni des choix du modèle. **Sortie forcée d'abstention** : si l'arrêt intervient sans hypothèse suffisamment soutenue, la sortie est `INCONCLUSIVE` avec la liste de ce qui **n'a pas été recherché** faute de budget — obligation de dossier (§5.4).

**Reprise après erreur, par classe** : erreur réseau → retry ≤ 2 avec repli de fournisseur, sinon arrêt fail-closed ; sortie non conforme → 1 re-prompt puis quarantaine ; sortie vide (documentée chez un des fournisseurs) → traitée comme non conforme ; outil en panne → source marquée indisponible, on continue, et si une preuve déterminante manque → `INCONCLUSIVE` ; reprise après plantage → reprise au dernier `step_index` du journal (les appels déjà payés ne sont pas refaits).

### 5.2.5 Registre d'outils (contrats v1)

| Outil | Entrée | Sortie | Contrainte |
|---|---|---|---|
| `read_prices` | venue, symbole, fenêtre | Observations (source, horodatage, valeur) | lecture seule, timeout 20 s |
| `read_supply` | actif, fenêtre | Observations | idem |
| `read_chain` | chaîne, adresse, plage de blocs | Observations (bloc, tx) | timeout 30 s |
| `fetch_document` | URL, attente | Document brut → canonicalisation | **contenu non fiable** (injection) |
| `compute_signal` | identifiant de signal, paramètres | Valeur + méthode + unité | **déterministe, hors LLM** |
| `graph_query` | question, instant simulé | Snapshot figé | lecture seule |
| `journal_write` | type, contenu, refs | identifiant de ligne | écrit dans **son** journal |
| `execute_intent` | — | — | **jamais exposé aux agents de recherche** |

**Hygiène des prompts** : instructions système stables et versionnées (rôle, interdits — « aucun chiffre », « aucune réécriture de politique »), sorties toujours validées par schéma côté serveur (les fournisseurs ne garantissent que la **syntaxe** JSON, pas le schéma — vérifié dans leur documentation), et un banc de tests **anti-injection** (contenu externe piégé, faux ordres, faux chiffres) intégré au banc de sûreté.

## 5.3 Bloc B — Le graphe de connaissance

### 5.3.1 Ce qu'est le graphe

**Un dépôt typé, en ajout seul, de faits, entités et relations horodatés et sourcés**, orienté vers la documentation d'un risque de collatéral et des décisions qui en découlent. Trois couches :

- **Couche monde** (faits sur le monde) : entités, événements, relations structurelles et économiques ;
- **Couche connaissance** (faits sur nos connaissances) : la **chaîne de provenance** — Source → Observation → Extraction → Affirmation → Relation → Hypothèse → Prévision → Résultat — chaque flèche étant une ligne de lien stockée ;
- **Couche décision** : Décisions, Intentions, Exécutions, Dossiers.

La règle de fond : **aucun chiffre n'existe dans un dossier de décision s'il ne peut pas être remonté jusqu'à une source horodatée**. Un claim sans observation parente est refusé par le magasin.

### 5.3.2 Le catalogue de relations : 34 types en 4 familles (liste complète)

C'est la pièce centrale du graphe — **le vocabulaire du risque de collatéral**, rendu machine-vérifiable : chaque type déclare les types de sujets et d'objets autorisés, son sens (dirigé/symétrique), sa transitivité et une sémantique d'une ligne. Aucun catalogue public complet de relations pour un graphe de collatéral DeFi n'existe (recherche du 15/10/2026) : c'est **notre pièce**, assumée comme telle.

**Famille 1 — Preuve et dérivation (8).** Règle d'or : la relation de soutien **n'autorise aucune propagation causale** ; une corrélation n'est jamais un mécanisme.

| # | Type | Sémantique |
|---|---|---|
| 1.1 | `OBSERVED_FROM` | L'observation provient de cette source (endpoint, horodatage, limites). |
| 1.2 | `EXTRACTED_FROM` | L'élément a été extrait de ce document/passage (ancrage + run d'extraction versionné). |
| 1.3 | `DERIVED_FROM` | Fait calculé à partir de parents, via une recette versionnée. |
| 1.4 | `SUPPORTS` | Ce constat soutient cette hypothèse — sans aucune transmission économique. |
| 1.5 | `REFUTES` | Ce constat réfute cette hypothèse selon un critère pré-déclaré. |
| 1.6 | `CONTRADICTS` | Deux constats incompatibles coexistent (jamais fusionnés) — signal de recherche. |
| 1.7 | `SUPERSEDES` | La révision remplace l'ancienne sans l'effacer (reconstruibilité). |
| 1.8 | `SAME_AS` | Alias résolu : deux références = une identité canonique (décision datée, révisable). |

**Famille 2 — Structure et exposition (15).** Règle d'or : « absence de publication » ≠ « exposition nulle » ; une quantité sans unité ni date est invalide.

| # | Type | Sémantique |
|---|---|---|
| 2.1 | `IS_A` | Taxonomie (USDC est-un stablecoin ; rsETH est-un jeton de staking liquide). |
| 2.2 | `PART_OF` | Appartenance structurelle (aUSDC partie du pool de prêt ; réserve partie du marché). |
| 2.3 | `DEPLOYED_ON` | Présence d'un contrat/émission sur cette chaîne (multi-chaînes explicite). |
| 2.4 | `ISSUED_BY` | L'actif est émis par cette entité. |
| 2.5 | `TARGETS_PEG` | Parité visée (1 $, 1 ETH) — une cible, pas une garantie. |
| 2.6 | `REDEEMABLE_VIA` | Rachat/retrait auprès de cette facilité (délais et conditions en charge utile). |
| 2.7 | `CUSTODIED_AT` | L'actif repose chez ce dépositaire/contrat (wrapping, escrow). |
| 2.8 | `HOLDS` | Détient N unités à (chaîne, bloc) ; rôle précisé (trésorerie, liquidité, collatéral). |
| 2.9 | `OWES` | Doit N unités sur ce marché (taux, échéance). |
| 2.10 | `DEPOSITED_IN` | Dépôt dans un marché/pool — chemin d'exposition. |
| 2.11 | `COLLATERALIZES` | Sert de collatéral à cette dette sur ce marché (paramètres LTV en charge utile). |
| 2.12 | `REHYPOTHECATED_TO` | L'actif reçu est réengagé vers ce protocole (chaîne des droits). |
| 2.13 | `BRIDGED_VIA` | L'émission dépend de ce pont (invariant inter-chaînes). |
| 2.14 | `VERIFIED_BY` | La sécurité du pont repose sur ces vérificateurs (nombre, type). |
| 2.15 | `PRICED_BY` | Valorisation adossée à ce feed oracle (type, heartbeat, plafond). |

**Famille 3 — Mécanisme économique (3).** Règle d'or : une relation statistique ne porte que le statut statistique ; conditions et horizon obligatoires.

| # | Type | Sémantique |
|---|---|---|
| 3.1 | `AFFECTS` | Le mécanisme transmet une variation de la cause vers l'effet (signe, horizon, conditions). |
| 3.2 | `DEPENDS_ON` | Dépendance économique (canal + sensibilité), propagation bornée et décroissante. |
| 3.3 | `CORRELATES_WITH` | Lien statistique constaté — jamais causal, jamais chaîné. |

**Famille 4 — Contrainte et permission (8).** Règle d'or : un texte informatif n'est pas une règle exécutable validée ; toujours porter la preuve d'octroi.

| # | Type | Sémantique |
|---|---|---|
| 4.1 | `CONSTRAINS` | Limite le comportement (plafond, LTV, gel, délai) — état ou paramètre daté. |
| 4.2 | `AUTHORIZES` | Accorde un droit à ce sujet (périmètre, dates, preuve d'octroi). |
| 4.3 | `REVOKES` | Révoque un droit (événement daté : transaction ou décision). |
| 4.4 | `MEMBER_OF` | Est membre de ce rôle à (chaîne, bloc) — fait on-chain. |
| 4.5 | `ALLOWS` | Le rôle autorise cette cible/fonction (liste d'autorisation, allowances). |
| 4.6 | `ADMINISTERED_BY` | L'administrateur du contrat est cette adresse (module activé). |
| 4.7 | `GOVERNED_BY` | Les paramètres sont gouvernés par cette instance (seuils, délais). |
| 4.8 | `REGULATED_BY` | Encadrement réglementaire (phase banques — table conservée pour la vision). |

**Total : 34 types** (8+15+3+8). **Décompte d'origine — honnêteté** : 14 types repris du vocabulaire général (bitemporel, provenance, causalité), 13 définis par le domaine DeFi/on-chain (présents dans la liste ci-dessus), 7 rendus explicites par nécessité de machine (alias, contradiction, réfutation, dépendance, corrélation, taxonomie, composition) pour que les invariants soient **vérifiables par un programme** et non par la mémoire des auteurs.

### 5.3.3 Le record de relation : 17 champs

Chaque relation est un enregistrement typé — pas un triplet nu :

| # | Champ | Rôle |
|---|---|---|
| 1 | `relation_id` | Identifiant stable (ULID). |
| 2 | `family` | Famille (1-4). |
| 3 | `kind` | Type du catalogue (§5.3.2). |
| 4 | `src`, `dst` (+ types) | Références typées sujet → objet. |
| 5 | `mechanism` | Étiquette de mécanisme (liquidité, rachat, financement, peg, oracle, garde, gouvernance…). |
| 6 | `sign_prior` | Signe attendu (+ / − / ambigu). |
| 7 | `conditions`, `regime_scope`, `horizon_scope` | Prédicats d'activation en **énumération** (pas de texte libre), portée, horizon. |
| 8 | `epistemic_status` | **7 labels** : `FACT`, `REPORTED`, `STATISTICAL`, `CAUSAL-DOCUMENTED`, `CAUSAL-HYPOTHESIS`, `MODEL-INFERRED`, `REJECTED`. |
| 9 | `lifecycle` | `DISCOVERED → EVALUATING → ACTIVE → WEAKENING → SUSPENDED → REJECTED`. |
| 10 | `validation_status` | `PENDING / VALIDATED / QUARANTINED / REJECTED`. |
| 11 | `valid_from`, `valid_to` | Temps de validité monde (nullable = ouvert/inconnu). |
| 12 | `revision`, `inserted_at`, `superseded_by` | Temps système (append-only). |
| 13 | `provenance_refs[]` + `source_family_id` | Parents (claims/observations) + famille de source (indépendance). |
| 14 | `extract_method` + `model_version` + `run_id` | Règle / lecture on-chain / extraction LLM / humaine, avec version. |
| 15 | `chain_ref` | (chaîne, bloc, transaction) pour les faits on-chain. |
| 16 | `confidence` | 0–1, méthode documentée (fiabilité de source × fraîcheur × indépendance) — module, ne remplace jamais le statut épistémique. |
| 17 | `payload` | Champs propres à la famille (montant, rôle, périmètre, passage source…). |

**Trois attributs à ne jamais confondre** : le statut épistémique (ce qu'on croit savoir), le cycle de vie (où en est la relation), le statut de validation (a-t-elle passé la porte). Une relation active peut parfaitement rester hypothétique.

### 5.3.4 Les horloges temporelles et le point-in-time

Chaque fait du graphe porte **plusieurs horodatages distincts** — et la décision n'utilise que ce qui était connaissable :

| Horloge | Champ | Statut v1 |
|---|---|---|
| Temps de l'événement (quand le fait s'est produit) | `ts_event` | **en v1** |
| Temps de publication (quand l'information est devenue publique) | `ts_published` (marquée « estimée » si approximative) | **en v1** |
| Temps d'observation (quand le système l'a lue) | `retrieved_at` | **en v1** |
| Fenêtre de validité (jusqu'à quand le fait est vrai) | `valid_from` / `valid_to` (nullable) | **en v1** |
| Temps d'effet (quand la règle prend effet) | fusionné avec la validité | v1 (simplifié) |
| Temps de révision (quand une correction est apportée) | `inserted_at` + `revision` + `superseded_by`, append-only | **en v1** |

**Deux modes de requête, formellement distingués** : (1) « **le monde à T** » — faits dont l'intervalle de validité contient T ; (2) « **ce qui était connu à T** » — faits dont la révision a été insérée avant T. **La décision rejouée utilise l'intersection** : c'est l'invariant PIT — *modifier le futur, ou publier une correction après coup, ne change pas une décision passée*.

**Le point-in-time on-chain est le bloc** : un appel d'archive sur le bloc X rejoue l'état exact ; tout fait on-chain stocke (chaîne, bloc, transaction). Le bloc est monotone dans le temps — le PIT y est parfait par construction. Politique de reorg gelée : **anti-reorg à 2 blocs en démo** (blocs Base ≈ 1,64 s), tags `safe`/`finalized` en production ; les faits on-chain ne deviennent `VALIDATED` qu'après la fenêtre de confirmation, et un fait orphelin par reorg déclenche la procédure documentée (§5.6.4).

**Limites assumées des horloges** : un `ts_published` estimé n'est jamais maquillé en exact ; les chevauchements d'intervalles ne sont pas contraints par SQLite (contrainte applicative + test unitaire en v1 ; contrainte native de la cible Postgres) ; la performance des requêtes « as-of » repose sur des index dédiés (§5.3.7).

### 5.3.5 Construction du graphe — trois voies, une discipline

1. **Données marché structurées → règles.** Déjà en place : `(url, paramètres) → charge utile brute (source, horodatage, corps) → normalisation → observation typée` avec empreinte de contenu. Les claims dérivés (seuils, signaux) référencent des observations ; un claim sans observation est refusé.
2. **Lectures on-chain → règles.** État par appel d'archive (réserves, oracles, supply, prix de sortie des pools) et événements par logs paginés (rôles attribués/révoqués, gels, frappes/brûlages de ponts). Chaque fait porte son bloc ; les mises à jour se font par **diff de blocs** (décoder, comparer à l'état stocké, écrire la transition).
3. **Documents → extraction LLM avec portes de validation.** Outillage mature (extraction d'entités zero-shot, extraction de relations, extraction structurée avec ancrage aux passages). Pipeline : `document → empreinte → mentions → résolution d'entités → triplets candidats + ancrage → porte de validation → relation validée ou quarantaine`. Chaque relation extraite porte méthode, version de modèle et passage exact.

**Résolution d'entités** : déterministe d'abord — `chaîne:adresse` (avec somme de contrôle) = identifiant canonique des contrats et tokens ; registre d'entités à identité immuable pour les organisations ; les alias (symboles, noms marketing) sont des **preuves rattachées**, jamais des clés. Ensuite seulement, désambiguïsation sémantique — jamais l'inverse. Dédoublonnage : empreinte de contenu pour les observations ; clé `(sujet, type, objet, validité, famille de source)` pour les relations — reformater la même source ne crée **pas** une preuve indépendante.

**La porte de validation** — cinq contrôles, toute porte qui échoue → quarantaine (jamais de réparation silencieuse) :

| Porte | Contrôle | Rejet typique |
|---|---|---|
| G1 — Schéma | Type connu, sujet/objet autorisés, champs requis | triplet hors catalogue |
| G2 — Provenance | Passage source localisable + parent résolu | citation non localisable |
| G3 — Autorité | Hiérarchie : on-chain vérifié > document officiel > presse de référence > communautaire | rumeur présentée comme fait structurel |
| G4 — Indépendance | Pour tout fait « porteur », une **seconde** source de famille différente (sauf on-chain vérifié) | dix reprises d'une même dépêche ≠ dix preuves |
| G5 — Cohérence | Contradiction avec un fait validé → écriture **quand même** avec relation de contradiction + revue ; jamais d'écrasement | valeur divergente cachée |

**Règle de charge** : un fait « porteur » (qui peut déclencher une décision) exige : vérifié on-chain, **ou** document officiel, **ou** deux familles indépendantes. Sinon il reste `PENDING/QUARANTINED` et ne sert que de contexte narratif.

### 5.3.6 Requêtes de service (contrat du store)

Le graphe doit servir 14 requêtes types, dont les 8 noyaux testés en priorité : (Q1) exposition consolidée d'une trésorerie, directe et indirecte, par protocole ; (Q2) chemins de dépendance d'un actif (profondeur bornée, avec signe) ; (Q3) contradictions ouvertes ; (Q4) état PIT (monde ∩ connaissance) ; (Q5) chronologie d'un épisode ; (Q6) promenade de provenance (décision → claims → observations → sources, avec empreintes) ; (Q7) agrégats de concentration (dette adossée à un actif, part de supply) ; (Q8) état de permission (qui est membre de quoi, as-of bloc, révocations). Puis : fraîcheur vs heartbeat ; faits manquants discriminants ; invariants inter-chaînes (sommes de supply par chaîne) ; chaîne de contrôle (contrat → admin → coffre → DAO) ; révisions/invalidations ; recherche sémantique optionnelle (ML-1). Structures : index par (sujet), (objet), (type), (sujet,type), (objet,type) ; index as-of sur (identifiant, insertion) ; index temporels sur les observations (événement, source, récupération, chaîne+bloc) ; vue « état courant » matérialisée ; unicité partielle pour le dédoublonnage.

**Règles d'inférence autorisées / interdites** (machine-vérifiables) : autorisé — clôture de `PART_OF` et `IS_A` (profondeur bornée, détection de cycle), lecture inverse implicite, `DEPENDS_ON` avec décroissance, propagation `AFFECTS` **uniquement** via le moteur de propagation déclaré. Interdit — propager le long de `SUPPORTS`/`CONTRADICTS`, chaîner `CORRELATES_WITH`, fermer transitivement `HOLDS` (détenir ≠ contrôler : le contrôle passe par les relations d'administration et de gouvernance).

### 5.3.7 Stockage, snapshots, et la part de machine learning

- **v1 : SQLite append-only** (triggers qui interdisent UPDATE/DELETE ; révisions par nouvelles lignes ; snapshot = empreinte SHA-256 stable des lignes courantes + compteurs ; un snapshot figé **par décision**, référencé dans le dossier). **Cible : PostgreSQL** + extension vectorielle (recherche sémantique) + requêtes de graphe natives du standard SQL récent — migration contenue dans le module store, schéma identique.
- **ML-1 (implémenté en v1, hors chemin décisionnel)** : embeddings de documents/claims pour la **recherche sémantique** d'appoint (retrouver des cas similaires) — le résultat est une **liste de candidats**, jamais une preuve.
- **ML-2 (implémenté, hors confirmatoire)** : **détection d'anomalies sur les métriques du graphe** — c'est une **règle statistique déterministe** (changement de degré, concentration, rupture de chemin), entièrement traçable, qui produit des **hypothèses étiquetées `MODEL-INFERRED`**, jamais des faits.
- **Le reste du ML (prédiction de liens par réseaux de neurones de graphe, plongements de nœuds, complétion de graphe) : post-concours**, sous protocole pré-enregistré (masquage par périodes sans fuite, comparaison à des baselines triviales, budget de calcul égal à une règle simple). **Rien d'appris n'entre dans le chemin de décision de la v1** — la valeur du projet vient de la vérifiabilité, pas d'un modèle non validé.

**Règle transverse de traçabilité** : un score de modèle n'entre dans le graphe que comme (i) observation dérivée avec recette et version de modèle, ou (ii) hypothèse étiquetée `MODEL-INFERRED` avec critères de réfutation. **Jamais** comme fait.

---

## 5.4 Bloc C — Décision : hypothèses, recherche, abstention, catalogues

### 5.4.1 La discipline : analyse d'hypothèses concurrentes (ACH)

La décision ORVYREN part d'une **discipline** — analyser des hypothèses concurrentes en cherchant à les **réfuter**, pas à les confirmer — pas d'un algorithme copié. Cette distinction est fondée : la littérature en sciences de la décision ne soutient pas l'efficacité du format « matrice » en lui-même (une étude contrôlée de 2018 montre que le groupe formé à la méthode n'a pas été *plus exact* qu'un groupe contrôle — la recalibration et l'agrégation, elles, réduisent l'erreur ; une étude de 2024 à N=161 montre que le format matriciel n'a pas réduit le biais de confirmation). **Ce qu'on garde** : l'ensemble d'hypothèses explicite (y compris minoritaires), les preuves **pour ET contre** chaque hypothèse, la progression par réfutation, la sensibilité aux items critiques, les jalons d'observation future. **Ce qu'on ne revendique pas** : le format matriciel comme garantie.

Et une conséquence de méthode, issue de la littérature 2025-2026 : la réfutation peut être **opérationnalisée par un agent** (des frameworks font concevoir et exécuter par des agents des expériences de réfutation avec contrôle de l'erreur statistique) — mais « plus de précision » ne signifie pas « plus d'humilité » : des agents détectent les conflits sans communiquer l'incertitude résiduelle. D'où nos exigences : l'escalade (`ESCALATE`) est une **dimension mesurable de la sortie**, et l'abstention est enrichie (§5.4.5).

### 5.4.2 Format du record d'hypothèse — 12 champs, cycle de vie 7 états

| # | Champ | Règle |
|---|---|---|
| 1 | `id` | Identifiant stable, jamais réutilisé. |
| 2 | `case_id` | Épisode/fenêtre (`usdc-2023-03`, `rseth-2026-04`…). |
| 3 | `enonce` | Une phrase, falsifiable, avec mécanisme et portée (actif, lieu, horizon). |
| 4 | `criteres` | ≥ 1 critère de **soutien** et **≥ 1 critère de réfutation obligatoire** ; chaque critère = prédicat sur observations + seuil + sources admissibles + fenêtre. |
| 5 | `preuves_pour` | Références d'observations (horodatage, valeur, source). |
| 6 | `preuves_contre` | Idem — les deux listes existent toujours (pas de champ « vide par omission »). |
| 7 | `inconnues` | Séries/faits requis absents → alimente la liste « ce qui manque ». |
| 8 | `etat` | Un des 7 états (ci-dessous). |
| 9 | `p` | **Jamais un nombre libre** : vide tant que non gelé, puis étiquette ordinale gelée (improbable / possible / probable) + référence du gel ; le nombre n'apparaît qu'en annexe de calibration. |
| 10 | `histoire` | Journal append-only : (horodatage, transition, raison, références, empreinte du dossier). |
| 11 | `provenance` | Auteur logique (rôle, pas personne), version du logiciel/modèle, date, sources du texte. |
| 12 | `relations` | Liens typés : dérivation, soutien, contradiction, remplacement, fusion/scission. |

**Les 7 états et les règles de transition** :

```
CREATED ── première évaluation par un critère ──▶ UNDER_TEST
   │                                                  ├─ critère de soutien satisfait ──▶ SUPPORTED
   │ fusion validée                                   ├─ critère de réfutation satisfait ─▶ REFUTED
   ▼                                                  ├─ critères non évaluables ───────▶ INCONCLUSIVE
MERGED_INTO (pointeur ; trace conservée)              │
   tout état ── inutile / morte (masse, doublon, épisode clos) ──▶ ARCHIVED (jamais supprimé)
                                                      nouvelle preuve / nouveau cas ──▶ retour UNDER_TEST
```

1. `SUPPORTED` exige un critère de soutien **explicitement satisfait** ; `REFUTED` exige un critère de réfutation **explicitement satisfait** ; sinon `INCONCLUSIVE` — jamais d'état « par défaut ».
2. Une seule transition par observation, journalisée avec ses références ; pas de mise à jour silencieuse.
3. `ARCHIVED` n'est pas une suppression : un réveil réutilise le même identifiant et le même historique. **Un enregistrement archivé ne peut jamais satisfaire une preuve obligatoire** : c'est l'état courant qui compte.
4. Fusion permise seulement si les énoncés sont équivalents après déduplication validée ; **les contradictions restent visibles** (jamais de fusion pour lisser un désaccord).
5. **Un LLM ne retire jamais une hypothèse** : la liste des hypothèses d'un cas est gelée à l'ouverture et versionnée ; seul l'état change.

**Checklist de falsifiabilité (opposable, vérifiée par le banc de tests)** : critère de réfutation exécutable par nos instruments (sinon refus à la création) ; sources admissibles nommées avec pas temporel et convention de prix ; aucun chiffre de décision issu du LLM ; sensibilité calculée (montrer que le verdict ne tient pas à un seul item sans le dire) ; chaque inconnue a au moins un prédicat candidat qui pourrait la lever.

### 5.4.3 La recherche du fait discriminant — RDOF v1

**Mécanisme v1 : « recherche discriminante ordonnée par falsification » (RDOF)** — 5 règles, zéro probabilité. « Quel fait départage H1/H2 ? » devient : *quel prédicat observable, déjà instrumenté, peut changer le verdict d'au moins une hypothèse — en privilégiant ce qui peut **réfuter l'hypothèse dominante** au coût le plus faible ?*

**Entrées** : `H` (hypothèses + critères), `P` (catalogue de prédicats : source, grandeur, seuils enregistrés, pas temporel, **coût mesuré en requêtes et secondes**, périmètre), `É` (état de preuve admissible, PIT), `B_max` (budget gelé).

**Procédure (une itération)** :
1. **Évaluabilité** : pour chaque hypothèse, marquer chaque critère évaluable / non évaluable sous l'état de preuve ; collecter les inconnues.
2. **Effet des prédicats** (déterministe, sans probabilité) : pour chaque prédicat non collecté et chacune de ses issues possibles (classes définies par ses seuils enregistrés), calculer *« si l'issue était celle-là, que devient le verdict de chaque hypothèse ? »* → {peut soutenir, peut réfuter, rend évaluable, inchangé}.
3. **Ordonnancement — comparaison lexicographique, ordre gelé** : (i) peut **réfuter** l'hypothèse dominante ← réfutation d'abord ; (ii) rend évaluable un critère portant une **décision opposée** ← l'inconnue la plus décisive ; (iii) résout une **contradiction** enregistrée non résolue ; (iv) coût le plus faible (secondes + appels mesurés). Égalités tranchées par identifiant (déterminisme total).
4. **Exécution** : collecter le prédicat choisi, l'ajouter à l'état de preuve, recommencer.
5. **Arrêt** (première condition vraie) : **invariance** — pour tous les prédicats restants, toutes les issues mènent à la même action candidate → arrêt « décision stable », y compris quand il reste du budget ; **budget** épuisé → arrêt, avec la liste de ce qui n'a pas été recherché et l'effet possible ; garde-fou de confiance optionnel, désactivé par défaut.

**Prédicats instrumentés v1** (tous exécutés le 15/10/2026) : gel d'une réserve (1 appel/bloc ≈ 0,4–0,7 s) ; ratio de saturation du plafond (classes {<95 %, ≥95 %, ≥99 %}) ; divergence oracle/marché (classes {<100 bps, ≥100 bps}) ; dispersion inter-places (classes {<100, ≥100, ≥300 bps}) ; baisse d'offre 24 h (classes {<1 %, ≥1 %}) ; décote réalisable par paliers de taille (le prix de sortie **dimensionne l'action**, il ne fait pas que détecter) ; invariant inter-chaînes.

**Micro-exemple mesuré (USDC, 11/03/2023, après les signaux de 07:00–08:00)** : preuves déjà en main — décote > 1 % sur deux places, dispersion 870 bps (coût nul) ; candidats restants — (i) persistance > 12 h (lisible mais récompensée seulement en fin de fenêtre) et (ii) baisse d'offre 24 h (une requête, verdict immédiat). La règle (i) place la **réfutation du leader** en tête : Or, (ii) **peut réfuter** H1 (« perturbation locale ») — une baisse d'offre est incompatible avec un incident de place — et coûte moins cher qu'attendre. Résultat mesuré : **−7,1722 % d'offre sur 24 h → H1 réfutée, H2 soutenue**. La trace exacte de ce raisonnement (question → prédicat → coût réel → effet sur les verdicts) est ce que le dossier v1 doit porter.

**La VoI reste derrière une interface** (post-v1, non livrée) : quand des probabilités **gelées et calibrées** existeront, l'ordonnancement pourra être fait par « valeur d'information attendue − coût » ; sinon le service renvoie explicitement `VOI_NOT_ESTIMABLE` et le mécanisme v1 prend la main **sans changer le résultat de la décision**. La VoI n'est jamais un point de défaillance : c'est un raffinement derrière une porte, testé contre l'ordre fixe avant activation. [NON TROUVÉ à ce jour : aucune évaluation publiée de cette approche intégrée à un agent financier.]

### 5.4.4 L'abstention : 5 conditions (A1–A5) et l'escalade

L'abstention est **coût-optimale** (règle classique du rejet : refuser coûte moins cher que se tromper quand l'utilité espérée de décider est inférieure au coût de rejet) et la littérature sur les événements rares avertit : sur notre classe d'intérêt (rupture de peg — un événement **minoritaire**), toute « couverture globale » est trompeuse. D'où **5 conditions**, toutes vérifiables sans probabilités :

| # | Condition | Test opérationnel | Exemple réel |
|---|---|---|---|
| **A1** | Entrée requise absente | une série/un fait nécessaire à un critère manque | série d'une place absente d'une fenêtre |
| **A2** | Contradiction non résolue | ≥ 2 sources de nature distincte se contredisent au-delà des tolérances, sans résolution | divergence oracle/marché non expliquée ; prix « fabriqué » (cas Drift) |
| **A3** | Décision non identifiable sous budget | après budget épuisé, deux hypothèses survivantes prescrivent des actions **opposées** et le fait discriminant est hors budget ou inexistant | rsETH après fermeture de la sortie |
| **A4** | Hors enveloppe / politique | l'action préférée viole les bornes, la place exclue, l'expiration passée | tout refus de politique |
| **A5** | Convention de mesure ambiguë | deux lectures admissibles du même fait donnent deux verdicts (clôture vs plus bas) sans convention gelée | Bitstamp 0,86267 vs 0,80526 |

**Note structurante** : A4 est une abstention **d'autorisation** (axe 3), jamais confondue avec A1–A3, **épistémiques** (axe 1). « DENY de politique » ≠ « échec épistémique » ; « INCONCLUSIVE » ≠ « NO-ACTION ».

**Format de sortie enrichi** — l'abstention n'est jamais un refus muet :

```json
{
  "epistemic_verdict": "INCONCLUSIVE",
  "conditions_declenchees": ["A1"],
  "missing_inputs": ["offre en circulation 24 h (source : agrégat public, 1 requête)"],
  "what_would_change_the_verdict": [
    {"fait": "baisse d'offre >= 1 % sur 24 h", "hypotheses_affectees": ["H2"],
     "predicat": "P-6.3", "cout_estime": "1 requete, < 5 s"}
  ],
  "decision_delta": {"si_H2_soutenue": "candidat A-D1 (convertir borne x*)",
                      "si_H2_refutee": "NO_ACTION documente"},
  "budget": {"consomme": {"recherches": 2, "appels": 14, "s": 9.6}, "raison_arret": "budget epuise"},
  "escalade": null, "action": null
}
```

Règle : `missing_inputs` **énumère** chaque fait manquant avec sa source possible et son coût estimé (jamais « données insuffisantes » en prose) ; `what_would_change_the_verdict` est **obligatoire** ; `decision_delta` montre les deux décisions selon l'issue — c'est ce qui rend l'abstention **utile** (un plan de recherche) et non un silence.

**Table de décision ESCALATE vs NO-ACTION** (déterministe) :

| Situation | Sortie | Motif |
|---|---|---|
| Verdict conclusif ; aucune action faisable ne passe le seuil économique ; l'attente ne crée pas d'obligation nouvelle | **NO-ACTION** (chiffré) | ne rien faire est optimal sous les hypothèses gelées |
| Verdict conclusif ; l'action décidée sort de l'enveloppe, ou la politique répond « approbation requise » | **ESCALATE** (dossier prêt à signer) | flux d'approbation (§5.5.5) |
| Verdict conclusif ; le fait décisif n'est obtainable que par un canal non outillé (contact humain, document payant) | **ESCALATE** | l'agent ne peut pas acheter l'information |
| `INCONCLUSIVE` (A1/A2), **perte potentielle bornée**, budget épuisé | **NO-ACTION** + journal d'abstention | asymétrie des coûts favorable |
| `INCONCLUSIVE` (A1/A2/A3), hypothèses survivantes prescrivant des actions opposées dont la mauvaise est coûteuse | **ESCALATE** | postérieure fragile → abstention ou escalade |
| Intégrité en échec (preuve déterminante invalide, provenance orpheline) | **ESCALATE** et blocage | une preuve déterminante invalide ne produit jamais d'action |

**Rappel de cadre** : « attendre » n'est pas « ne pas agir » — le NO-ACTION doit être justifié comme la meilleure action faisable, jamais comme l'absence de décision.

### 5.4.5 Les catalogues d'actions bornées — 8 (DAO) + 4 (desk)

Principes communs : une action n'est **jamais un ordre libre** — c'est une **intention bornée** (actif, montant, destinataire, fonction, expiration) que la politique peut refuser ; les bornes sont `x* = min(x_max_rôle, profondeur d'exécution mesurée, taille qui passe le seuil économique)` ; **le coût est dans la décision** (frais + gaz + slippage mesuré + financement) ; aucune action n'ouvre une exposition nouvelle en épisode de stress (uniquement réduire / convertir / rembourser / retirer) ; chaque action est étiquetée « exécutable on-chain » ou « simulée » (honnêteté de démonstration).

**Catalogue trésorerie / protocole (DAO) — 8 actions** :

| # | Action | Déclencheur (résumé) | Bornes / coût | Applicabilité v1 |
|---|---|---|---|---|
| A-D1 | **Pré-positionner / convertir** une part du stablecoin exposé vers un support non exposé | stress large soutenu, levée des conditions d'abstention | x ≤ x_max, place autorisée, ≤ profondeur ; frais + slippage mesurés | oui (v1 démo : transfert borné) |
| A-D2 | **Sortir d'un LST** (retrait/échange) | décote **réalisable** > seuil et non transitoire | ≤ profondeur ; avant files de retrait | oui (conçu) |
| A-D3 | **Rembourser une dette / dé-leverer** | probabilité de gel/liquidation de la place de dette en hausse | x ≤ disponible + dette | v2 (Aave) |
| A-D4 | **Retirer la liquidité / ne pas en ajouter** | gel, saturation, files | ≤ liquidité disponible ; priorité aux paniers les plus fermés | v2 |
| A-D5 | **Rapatrier vers le module de roulage** (réapprovisionner le plancher) | buffer sous cible / roulage projeté proche du plancher | ≤ cible du module ; tranches standardisées | oui (conçu) |
| A-D6 | **Geler / réduire des dépenses** | stress prolongé | **pas une action de l'agent** → proposition de gouvernance | non (ESCALATE) |
| A-D7 | **Ne rien faire** (documenté) | verdict conclusif sans action au-dessus du seuil | x = 0 ; coût d'opportunité si alertes répétées | oui (défaut) |
| A-D8 | **Escalader** (comité, trésorier, gouvernance) | A3/A4/A5 ou intégrité en échec | latence humaine ; décision tracée | via file d'approbation |

**Catalogue desk (rentabilité) — 4 actions** : **K-D1** réduire/sortir une position d'inventaire (déclencheur : rupture + `x·(P_T − P_exec) > coût aller-retour + financement` ; coûte si le peg se rétablit — « le put payé ») ; **K-D2** hedger (couverture par produit dérivé ; **simulation** en v1, hors enveloppe) ; **K-D3** dimensionner (toujours, avant toute action : `x = min(x_max, profondeur, x*)` et publication du slippage réalisé vs budget ≤ 30 bp) ; **K-D4** ne rien faire/attendre (éviter le « churn » — le coût décide du signe).

**Règles transverses** : `x_max` par action et par persona avec compteur glissant 24 h ; toute action porte son effet attendu (perte évitée conditionnelle pour la DAO, ΔP&L net pour le desk) recalculé à la taille réelle ; le catalogue est **versionné** et l'exécution cite sa version.

### 5.4.6 La règle de décision généralisée : 3 axes de sortie, jamais fusionnés

```
ENTRÉES
  É     état de preuve admissible (observations PIT référencées)          ← bloc B
  H     hypothèses + critères (format §5.4.2), version gelée
  pers  persona ∈ {DAO, desk} ; mandat (contraintes, plancher, plafonds)
  F     exposition consolidée (positions, unités, places,
        valorisation retenue ET valorisation réalisable)
  E     enveloppe : x_max par type d'action, places/actifs autorisés, expiration, plafonds 24 h
  k     coûts mesurés (frais, gaz, slippage, financement)
  P     catalogue de prédicats (coût, seuils)                             ← bloc B
  B_max budget de recherche gelé

SORTIES — trois axes SÉPARÉS (jamais fusionnés)
  epistemic_verdict     ∈ {CONCLUANT, INCONCLUSIVE}  + ce qui manque + ce qui changerait
  economic_action       ∈ {CONSERVER, CONVERTIR/TRANSFÉRER, CÉDER(x*), RÉDUIRE(x*),
                            HEDGER(x*), RAPATRIER, ESCALADER}            (vide si INCONCLUSIVE)
  authorization_verdict ∈ {ALLOW, DENY, REQUIRE_APPROVAL}                (indépendant des deux autres)
  dossier               verdicts des hypothèses, faits discriminants, calculs,
                        prévision gelée, budget, empreinte
```

**Ce qui reste déterministe** : le classement des hypothèses, l'évaluation des critères, les seuils, la taille `x*`, les pertes/regrets, la politique, le choix du prédicat (RDOF), les arrêts, l'empreinte du dossier. **Ce que fait le LLM** (jamais un chiffre) : rédiger les énoncés d'hypothèses, structurer des documents, expliquer le motif et les contradictions, proposer des jalons — tout étant validé par schéma et mis en quarantaine si un champ est inconnu.

**Seuils clés et leur statut** : décote alerte/rupture/sortie ≥ 50/200/500 bps (candidats justifiés par les mesures, calibration par quantiles identifiée) ; dispersion > 100/300 bps ; divergence oracle > 100 bps pendant > 1 h ; saturation ≥ 95 %, gel 0→1, baisse d'offre > 1 % ; seuil desk `x·(P_T − P_exec) > coût aller-retour + financement` ; seuil DAO perte évitée ≥ 5 % de l'exposition conditionnelle, friction ≤ 10 % de la perte évitée ; budget en requêtes + secondes. **Aucune cible chiffrée publiée n'existe pour `P(obligation)`** — c'est une hypothèse explicite gelée à défaut de source (aucune distribution publique de scénarios de dépeg pour une trésorerie de DAO n'a été trouvée) : signée par responsable d'équipe par défaut, **avec sensibilité publiée** (les deux facteurs — probabilité et perte conditionnelle — restent visibles, interdiction de publier une espérance sans eux).

**Double convention de prix (gelée)** : **alerte sur le plus bas ; décision sur clôture + plus bas** ; les deux lectures sont reportées partout où un seuil décide — l'écart mesuré entre conventions (740 bps sur Bitstamp, 11/03/2023) dépasse la plupart des seuils, donc la convention est un objet de décision, pas un détail.

### 5.4.7 Scénarios, prévisions et gel

- **Qualitatif d'abord** : les hypothèses ne forment pas une partition (stress réel et artefact peuvent coexister) — aucune normalisation à somme 1. Le champ `p` reste vide jusqu'au gel ; gelé, c'est une étiquette ordinale avec une **définition calibrée écrite au moment du gel**.
- **Qui produit quoi** : l'agent propose les énoncés et l'élicitation (cadrage « recherche de bugs », mesuré comme le mieux calibré) ; le composant déterministe **écrit** la prévision gelée et son empreinte ; un humain **signe** le gel.
- **Une prévision non gelée n'entre dans aucun calcul** : prévision = {énoncé, critère de résolution, horizon, date de gel, empreinte SHA-256, état d'observation au gel}. La confiance verbale d'un modèle est interdite comme probabilité.
- **v1 : aucune probabilité dans la décision** ; les seules valeurs probabilistes sont des hypothèses explicites gelées avec sensibilité publiée. Scoring futur : score de Brier, décomposition, couverture — avec effectifs publiés et « non établi » sous effectif insuffisant (§5.8).

## 5.5 Bloc D — Politique & autorisation (le premier verrou)

### 5.5.1 Principes de conception

- **Déterministe et hors LLM** : service pur — (intention, configuration, état local) → verdict. Le module politique n'importe ni modèle ni réseau.
- **Fail-closed** : tout état inaccessible, illisible ou invalide (compteur, solde, drapeau de pause, alignement d'enveloppe) vaut **refus** — jamais « on suppose que tout va bien ».
- **Deny-by-default** : tout ce qui n'est pas explicitement autorisé est refusé.
- **Codes de refus stables** : SCREAMING_SNAKE_CASE, jamais renommés ni réutilisés ; un code déprécié reste au registre. C'est ce registre qui rend le journal opposable et le refus rejouable.
- **Évaluation complète** : toutes les règles applicables sont évaluées et **tous** les codes en échec sont renvoyés — le dossier de refus montre tout ce qui ne va pas, pas seulement la première barrière.
- **Précédence du verdict** : `DENY` > `REQUIRE_APPROVAL` > `ALLOW`.
- **Trois classes d'action** : autonomes = {transfert borné} ; sous approbation = {échange, approbation de jeton, changement de politique, révocation} ; tout le reste = refus.
- **Garde structurelle (pré-politique)** : le schéma de l'intention rejette champs inconnus, types incorrects, quantités négatives, adresses mal formées — la politique ne reçoit qu'un objet déjà validé.

### 5.5.2 Le set v1 : 14 règles (liste complète)

| # | Règle | Déclencheur | Verdict / codes de refus |
|---|---|---|---|
| **P1** | Chaîne épinglée | chaîne de l'intention ∉ {chaînes autorisées} (démo : Base Sepolia ; prod : Base) | DENY · `CHAIN_NOT_ALLOWED` |
| **P2** | Actif/contrat autorisé | adresse d'actif ∉ liste d'autorisation | DENY · `ASSET_NOT_ALLOWED` |
| **P3** | Destinataire autorisé | adresse destinataire ∉ liste (comparaison insensible à la casse) | DENY · `RECIPIENT_NOT_ALLOWED` |
| **P4** | Fonction scopée | paire (cible, sélecteur) ou type d'opération ∉ registre v1 | DENY · `TARGET_NOT_ALLOWED` / `FUNCTION_NOT_ALLOWED` / `OPERATION_NOT_ALLOWED` |
| **P5** | Plafond par transaction | montant non fini / ≤ 0 / > plafond | DENY · `AMOUNT_NOT_FINITE` / `AMOUNT_INVALID` / `AMOUNT_ABOVE_TX_CAP` |
| **P6** | Cumul glissant 24 h | somme glissante + montant > plafond ; compteur invalide | DENY · `AMOUNT_ABOVE_PERIOD_CAP` / `CUMULATIVE_INVALID` |
| **P7** | Exposition / solde | solde illisible ; montant > solde ; plancher franchi ; plafond d'exposition franchi | DENY · `BALANCE_UNREADABLE` / `BALANCE_INSUFFICIENT` / `FLOOR_BREACH` / `EXPOSURE_ABOVE_CAP` |
| **P8** | Permission (mandat) active | expiration absente ; échéance dépassée | DENY · `PERMISSION_MISSING` / `PERMISSION_EXPIRED` |
| **P9** | Fraîcheur de l'intention | âge > TTL (15 min en démo) ; horodatage futur au-delà de la tolérance d'horloge (60 s) | DENY · `INTENT_STALE` / `INTENT_NOT_YET_VALID` |
| **P10** | Idempotence (rejeu) | identifiant déjà vu **ou** empreinte du contenu canonique déjà vue | DENY · `INTENT_ALREADY_PROCESSED` |
| **P11** | Pause / kill switch | drapeau de pause actif ; pré-vol : l'agent n'est plus membre du rôle | DENY · `PAUSED` / `AGENT_NOT_MEMBER` |
| **P12** | Alignement d'enveloppe | configuration on-chain ≠ politique attendue, ou vérification impossible | DENY (SAFE MODE) · `ENVELOPE_DRIFT` / `ENVELOPE_UNVERIFIED` |
| **P13** | Périmètre d'action | action inconnue → refus ; action connue hors périmètre autonome → approbation | DENY · `ACTION_UNKNOWN` ; REQUIRE_APPROVAL · `ACTION_NEEDS_HUMAN_APPROVAL` |
| **P14** | Budget de décision | budget de recherche/raisonnement épuisé ou incohérent | DENY · `BUDGET_EXCEEDED` / `BUDGET_UNREADABLE` |

**Cas limites documentés (exemples)** : montant non fini refusé **avant** toute comparaison (piège classique : une comparaison avec NaN est toujours fausse) ; montant en **unités décimales canoniques** du jeton avec test anti-erreur de décimale (un débit 1 000 000× doit être refusé par le plafond, pas découvert on-chain) ; le cumul glissant hors chaîne est **le verrou strict** de la frontière de période (le plafond on-chain est un plafond *d'accumulation* — une rafale à cheval sur la frontière peut engager jusqu'à 2 périodes : limite mesurée, documentée, testée, et bornée par un dimensionnement explicite `refill = maxRefill`) ; la permission n'a **aucune** expiration native on-chain — la révocation planifiée est obligatoire, sinon l'échéance hors chaîne seule laisse la clé capable d'exécuter (limite connue, écrite).

**Ce que la politique ne fait pas** (frontières) : elle ne juge pas les prix (c'est la décision), ne signe pas, ne détient aucune clé, ne remplace pas l'enveloppe on-chain (elle est le premier verrou, l'enveloppe le second) et ne détecte pas les anomalies de marché (elle applique l'état qu'on lui donne).

### 5.5.3 Formalisation, versionnage et changement de règle

**Le bundle à quatre pièces — et l'autorité de chacune** :

| Pièce | Contenu | Autorité |
|---|---|---|
| `policy_v1.yaml` | **paramètres** : chaînes, actifs, destinataires, plafonds (transaction, 24 h), TTL d'intention, plancher/plafond d'exposition, TTL d'approbation, liste d'approbateurs, version | Source de vérité des **paramètres** |
| Code du module politique | **sémantique** des règles (ordre, codes, vérifications) | Source de vérité de la **sémantique** |
| Banc de tests (nominal + attaques + cas limites) | Preuves exécutables | La **preuve** — aucun changement sans test |
| Spécification (ce document) | Description, justifications | La **description** — jamais l'autorité |

La phrase exacte du contrat : « *la politique appliquée est identifiée par une version et une empreinte ; le texte ne peut pas diverger silencieusement du code parce que c'est le code qui émet le verdict et l'empreinte qui identifie le bundle* ». L'enveloppe on-chain votée est la **borne supérieure** : la politique hors chaîne doit lui être **inférieure ou égale** (règle P12).

**Version et empreinte dans chaque verdict** : `policy_version` = vMAJOR.MINOR (MAJOR = changement de sémantique ou du set de règles ; MINOR = changement de paramètre) ; `policy_hash` = empreinte du YAML canonique combinée à l'empreinte du code du module. Chaque verdict et chaque entrée de journal de politique portent les deux.

**Procédure de changement (6 étapes)** : (1) proposition type « dossier de décision » (changement, règle touchée, impact, tests modifiés) — rédigeable par un humain ou assisté, **jamais appliqué par un LLM** (le processus agent n'a **aucun** accès en écriture à la politique) ; (2) PR + tests, banc complet vert ; (3) **si le changement touche une borne couplée on-chain : d'abord on-chain, ensuite hors chaîne — on réduit d'abord (sens sûr), on augmente d'abord côté politique après vote on-chain** ; rapport de dérive joint ; (4) revue et signature par deux personnes (auteur ≠ approbateur) ; (5) incrément de version + empreinte + ligne au registre de versions append-only ; (6) déploiement + entrée de journal + test de dérive au démarrage (SAFE MODE si échec).

**Asymétrie d'urgence (gelée)** : **réduire** un plafond, retirer un destinataire ou activer la pause sont des changements « sens sûr » applicables **immédiatement** (journalisés, régularisés sous 24 h) ; **toute augmentation** suit la procédure complète. C'est le pendant hors chaîne des règles de propriété côté chaîne.

### 5.5.4 Le test de dérive (`envelope_drift_check`) et le SAFE MODE

Le risque structurel du double verrou est la **divergence silencieuse** entre les deux couches — surtout le cas dangereux : une enveloppe on-chain élargie (nouvelle cible, allowance augmentée) que la politique hors chaîne ne « voit » pas. Le test de dérive transforme la promesse en **vérification exécutable**, en deux étages : **offline en intégration continue** (comparaison `policy_v1.yaml` ↔ fixture versionnée de la configuration on-chain — détecte toute dérive introduite d'un côté ou de l'autre, sans réseau) et **live à l'exécution** (lecture de la configuration réelle au démarrage, avant chaque fenêtre d'exécution, périodiquement).

**Les 10 contrôles v1** :

1. **Chaîne** : identifiant de chaîne du RPC épinglé == chaîne attendue.
2. **Module** : code présent et empreinte du bytecode == empreinte épinglée (détecte un module réétiqueté ou une version non suivie).
3. **Membres** : l'agent est membre du rôle ; **aucun autre membre** ; aucun droit d'administration.
4. **Cibles** : l'ensemble des cibles du rôle == l'ensemble attendu ; toute cible en portée large = **dérive critique** (mode d'erreur n° 1 : autoriser une cible entière laisse passer n'importe quel calldata).
5. **Fonctions** : pour chaque paire (cible, sélecteur) attendue, portée exacte `Function` et options d'exécution compatibles ; toute fonction non attendue = dérive.
6. **Conditions** : condition de destinataire lue == condition attendue ; condition de montant présente (une absence = un montant non conditionné qui peut consommer l'allowance en un coup).
7. **Allowances** : paramètres lus == attendus, avec cohérence `plafond par transaction ≤ min(refill, maxRefill)` et `plafond 24 h ≤ maxRefill` et `refill = maxRefill` (borne la rafale de frontière à ≈ 2 périodes).
8. **Quota d'appels** : quota d'appels par jour == paramètre politique.
9. **Expiration/processus** : l'échéance hors chaîne ≤ la révocation planifiée enregistrée ; absence des deux = dérive.
10. **Version/avis** : version du module suivie vs avis de sécurité connus (l'empreinte épinglée sert de garde).

**Trois états** : `PASS` (exécution autonome permise) ; `DRIFT` → **SAFE MODE** : refus de toute action autonome (`ENVELOPE_DRIFT`), alerte, journal ; `UNVERIFIED` (RPC injoignable ou incohérent) → SAFE MODE (`ENVELOPE_UNVERIFIED`). Le mode sûr est un **état de la politique**, pas une exception du logiciel : il se prouve dans le journal et n'empêche ni les lectures ni les dossiers — il bloque l'exécution.

### 5.5.5 Le flux d'approbation (`REQUIRE_APPROVAL`)

**Principe : « un canal notifie, une signature autorise. »** Le canal de notification n'est **jamais** l'autorité (les canaux de messagerie sont un vecteur d'hameçonnage connu).

1. **Création** : un verdict « approbation requise » crée un enregistrement d'approbation : identifiant, identifiant et empreinte de l'intention, décision liée, version+empreinte de politique, date de demande, **expiration (défaut 2 h, configurable 5 min – 24 h)** — changements de politique : **7 jours** (référence : pratique publique d'un fournisseur de garde institutionnel) — dossier joint (empreinte), résumé lisible.
2. **Notification** : entrée de journal + affichage dans la page d'audit ; optionnellement webhook/canal d'équipe. La notification contient **l'empreinte et le lien vers le dossier**, jamais des instructions d'exécution.
3. **Décision humaine** : l'approbateur signe, **avec son propre portefeuille**, un message **EIP-712** liant {identifiant d'approbation, empreinte de l'intention, version de politique, expiration} ; un refus est une action journalisée.
4. **Vérification** : le service de politique (jamais le LLM) vérifie la signature, l'identité de l'approbateur (liste), la non-expiration et le non-rejeu ; le verdict humain est attaché au dossier.
5. **Suite** : si l'action reste dans l'enveloppe, l'instruction **non signée** est remise à l'humain qui exécute dans son portefeuille ; si elle en sort, une transaction est **proposée** à la file du coffre multi-signatures (v1.5/V2 : module de délai on-chain pour porter la classe « hors enveloppe » avec fenêtre de réaction de 1–7 jours).
6. **Clôture** : entrées `APPROVAL_REQUESTED / APPROVED / REJECTED / EXPIRED` + la signature ; le dossier gagne la ligne « approbation ».

**Données journalisées (gelées)** : identifiant d'approbation (ULID), intention + empreinte, décision, version+empreinte de politique, verdict d'origine + motifs, empreinte du dossier, date de demande, expiration, canal(aux), approbateur (adresse + rôle), signature EIP-712 (ou référence), décision humaine + horodatage, conséquence (transaction ou « aucune exécution », motif), chaînage. **Une approbation est un enregistrement immuable** : une correction crée une nouvelle entrée.

### 5.5.6 Kill switch, incident, et procédure de révision du gel

**Les leviers d'arrêt (du plus rapide au plus fort)** :

| Niveau | Action | Qui | Latence | Effet |
|---|---|---|---|---|
| **K0** | Pause hors chaîne (drapeau du service de signature) | l'équipe (astreinte) | **immédiat** | plus aucune signature émise |
| **K1** | Retrait du rôle de l'agent (1 transaction du coffre DAO) | coffre DAO (seuil de signatures) | **≤ 60 min** (cible ; blocs Base ≈ 1,64 s — le seul délai non compressible est la coordination humaine) | toute exécution ultérieure est refusée par la chaîne |
| **K2** | Désactivation du module entier | coffre DAO | idem K1 | tous les rôles du module |
| **K3** | Retrait du gaz de l'agent | coffre DAO | idem K1 | arrêt par asphyxie |

**Cibles de temps (gelées)** : K0 **≤ 5 min** après détection ; K1 **≤ 60 min**. **L'agent ne peut jamais lever une pause** (règle : la levée exige un humain + une entrée de journal) ; il peut seulement la **poser** (sens sûr, y compris par auto-surveillance sur anomalie). **Ce que le kill switch ne peut pas faire** (écrit, pas caché) : annuler une transaction déjà incluse ; dépasser une transaction déjà séquencée avant la révocation. La protection pratique est : plafonds faibles (le dommage par bloc est borné par l'allowance), délais courts décision→envoi, surveillance des intentions.

**Runbook d'incident (résumé, avec cibles)** : détection ≤ 15 min (surveillance des événements du rôle, des consommations d'allowance, des transferts + anomalies) → qualification sévérité S1–S4 ≤ 15 min → confinement (S1/S2 : K0 immédiat, K1 demandé en parallèle) → vérification (membre = faux, aucun transfert non conforme, soldes, allowance restante) ≤ 15 min après K1 → communication interne ≤ 30 min, externe ≤ 4 h (« dire d'abord le pire cas **chiffré** ; ne jamais promettre l'annulation d'une transaction incluse ») → journal continu (append-only) → post-mortem ≤ 72 h → redémarrage conditionné (cause comprise, correctifs fusionnés, **test de dérive PASS**, rôle ré-assigné par la DAO, plafonds réduits pour la première période). Note d'honnêteté : aucun SLA contractuel public de kill switch n'existe — ces délais sont des cibles internes.

**Procédure de révision du gel (protocole ADR)** : toute décision gelée vit dans un registre unique ; une révision suit un dossier de type « ADR » (contexte, options avec arguments pour/contre et coût de changement, décision et justification, conséquences, **conditions de réouverture**, références) et la procédure : (1) une proposition écrite (qui gèle quoi, pourquoi) ; (2) impact identifié (tests, documents, enveloppe) ; (3) revue d'équipe et acceptation explicite ; (4) nouvelle version datée + hachée du paquet de gel ; (5) mise à jour du registre et des documents. **Toute modification silencieuse est interdite par construction** : le journal des versions est append-only, et le paquet de gel est haché. **Registre en vigueur** : `docs/decisions/` (index `docs/decisions/README.md`, contrôle d'index en CI) — actes à ce jour : **ADR-0001** (gel G1–G6), **ADR-0002** (politique v1, 14 règles), **ADR-0003** (recherche sémantique/ML-1 → V2).

### 5.5.7 Le schéma du verdict de politique (`PolicyDecision`)

Chaque évaluation produit un enregistrement complet : `decision_id` (ULID) ; `intent_id` + `intent_hash` ; `verdict ∈ {ALLOW, DENY, REQUIRE_APPROVAL}` ; `reasons[]` (codes en échec, ordre canonique) ; `rules_evaluated[]` (une ligne par règle : résultat OK/FAIL/SKIPPED + code + note — y compris les règles sautées) ; `policy_version` + `policy_hash` ; `envelope_ref` (chaîne, module, rôle, empreinte du code, date de vérification, état du test de dérive) ; `approval` (présent si approbation requise : identifiant, canal, expiration, état) ; `context_used` (valeurs réellement lues : horloge, cumul 24 h, solde, exposition, pause, **sources** de chaque lecture) ; `evaluator` (« politique déterministe vX — jamais un LLM ») ; horodatages. Sérialisation **canonique** (clés triées, nombres en unités décimales avec l'actif) ; l'empreinte du verdict est calculée sur la forme canonique et chaînée dans le journal.

**Interfaces** : la décision (bloc C) produit l'intention bornée ; la politique rend le verdict ; l'exécution (bloc E) **n'accepte que `ALLOW`** (toute autre valeur lève une exception, journalisée) ; `REQUIRE_APPROVAL` déclenche exactement le flux §5.5.5 ; un `DENY` conserve intégralement le dossier — refuser est un résultat.

---

## 5.6 Bloc E — Exécution : le service signataire et le second verrou

### 5.6.1 Le signer de démonstration (spec v1-démo)

L'objet : une **EOA dédiée, membre du rôle permissions d'un coffre de démonstration**, qui paie son propre gaz et n'a **aucun** droit d'administration.

| # | Exigence | Règle |
|---|---|---|
| S1 | Génération | clé générée localement, jamais dérivée d'une phrase mnémonique réutilisée, jamais copiée dans un chat |
| S2 | Stockage | uniquement en variable d'environnement du processus de signature ; fichier local non versionné, permissions restreintes |
| S3 | Interdits absolus | jamais dans le dépôt, un prompt, un log, un message d'erreur, une capture d'écran, un ticket, un rapport — le code de sécurité ne lit que les **noms** des variables sensibles et masque les URL porteuses de clé |
| S4 | Portée | membre du rôle ; zéro droit d'admin (les appels d'administration sont conçus pour **reverter** depuis cette clé — test on-chain prévu) |
| S5 | Financement gaz | robinets publics gratuits ; les frais mesurés (0,006 gwei) rendent 0,01 ETH largement suffisants ; le gaz est une ligne budgétaire **distincte** du plafond métier |
| S6 | Financement actif | les jetons de test arrivent au **coffre**, pas à l'agent — l'agent ne détient jamais les fonds |
| S7 | Isolation | le service signataire est un **processus séparé** ; il n'expose qu'une interface : « intention autorisée → transaction signée + hash ». Il ne connaît ni le LLM, ni le graphe, ni la politique (il la reçoit déjà tranchée). **Le LLM ne voit jamais de clé.** |
| S8 | Rotation | changer d'agent = une transaction : attribuer le rôle au nouveau, le retirer à l'ancien |
| S9 | Cycle de vie démo | après les runs : retirer le rôle, vérifier membre == faux, archiver sans la clé, supprimer le fichier d'environnement — une clé de démo révoquée est sans portée |
| S10 | Traçabilité | le journal enregistre l'**adresse** et le rôle du signer, jamais la clé ; chaque exécution référence l'intention et la version de politique |

**Bibliothèque de signature** : la règle projet est « code neuf en bibliothèque standard » ; or la standard n'a ni Keccak-256 ni courbe secp256k1. Décision gelée : **une dépendance isolée** (bibliothèque de signature légère, licence permissive) **réservée au seul processus signataire**, déclarée dans les licences du dépôt ; le reste du code reste pur. **Produit (hors v1)** : backend de clé remplaçable (module de sécurité matériel / service de signature à seuil) ; le différenciant d'ORVYREN n'est pas le backend de clés, c'est le premier verrou + le journal.

**Ce que la clé ne peut PAS faire, écrit noir sur blanc** : dépasser le plafond on-chain par période, envoyer vers un destinataire hors liste, appeler une cible non autorisée, modifier la politique ou le module, vider le coffre. Si la clé fuit, **le pire cas est un nombre connu** : « au plus `maxRefill` par période, uniquement vers les destinataires autorisés » — et les deux runs de refus de la démonstration (par la politique **et** par la chaîne) montrent ce nombre en action (§5.6.6).

**Évolution assumée par rapport à l'existant** : le mode historique « l'agent produit le calldata, un humain exécute » est solide pour la preuve documentaire mais **n'est pas** l'exécution autonome qu'exige le thème du concours. La v1 ajoute le service signataire isolé qui exécute **dans l'enveloppe** ; le mode « instruction + exécution humaine » reste le **repli manuel** documenté, jamais le mode principal de la démonstration.

### 5.6.2 Le schéma d'intention (intent v1)

```jsonc
{
  "schema_version": "intent/v1",
  "intent_id": "01J…",                     // ULID unique, trié par temps
  "idempotency_key": "0x…64 hex…",         // empreinte du contenu canonique (sans id ni date de création)
  "chain_id": 84532,                       // Base Sepolia (8453 en prod) — épinglée
  "account": "0x…",                        // le COFFRE qui exécute — pas l'agent
  "action": "transfer",                    // transfer | swap | supply | withdraw | repay | approve | change_policy
  "asset": "0x036CbD…CF7e",                // contrat du jeton (USDC de test)
  "amount": "50.0",                        // CHAÎNE décimale ASCII — jamais un flottant
  "amount_base_units": "50000000",         // entier dérivé, revérifié (décimales lues du contrat)
  "recipient": "0x…",                      // destinataire (transfert) ou contrat cible (échange…)
  "function": "transfer(address,uint256)", // signature exacte, obligatoire
  "params": {"to": "0x…", "value": "50000000"},
  "expiry": "2026-10-16T12:00:00Z",        // RFC 3339 UTC — au-delà : refus, sans exception
  "created_at": "2026-10-15T12:00:00Z",
  "justification": "réduction d'exposition — 50 USDC vers réserve",  // ≤ 200 caractères, tracé
  "policy_version": "v1.0",
  "source": {"decision_id": "…", "case": "usdc-2023-03", "signal": "…"}
}
```

**Règles de validation (déterministes)** : champs inconnus rejetés (pas de quarantaine en exécution : un champ non prévu = refus) ; types stricts ; notation décimale à point, notations scientifiques refusées ; `amount_base_units` **recalculé** depuis les décimales du contrat lues par RPC (protection contre l'erreur de décimale) ; adresses normalisées minuscules, **aucune réparation** ; couple (action, fonction, paramètres) contraint ; expiration > maintenant et ≤ TTL (24 h en démo) ; empreinte d'idempotence absente du registre persistant. **L'intention n'est pas du calldata** : la construction du calldata est une étape distincte, **après** le verdict `ALLOW` (la sécurité ne repose pas sur « le bon objet a été fabriqué par la bonne partie »).

### 5.6.3 Le préflight — 12 contrôles avant toute signature

Aucune signature si un seul contrôle échoue ; chaque échec a un code stable journalisé.

| # | Contrôle | Échec → code |
|---|---|---|
| P1 | Verdict de politique `ALLOW` tracé | `policy_not_allow` |
| P2 | Chaîne épinglée : identifiant de chaîne du RPC == attendu | `chain_id_mismatch` |
| P3 | Expiration de l'intention non dépassée (horloge UTC du service) | `intent_expired` |
| P4 | Idempotence : clé absente du registre persistant | `intent_already_processed` |
| P5 | Pause (K0) inactive | `agent_paused` |
| P6 | Version du module on-chain == version attendue (avant chaque période d'exécution) | `module_version_unknown` |
| P7 | Adresses cibles re-vérifiées (`eth_getCode` non vide pour chaque contrat) | `target_code_missing` |
| P8 | Nonce : lecture `pending` ; **un seul vol en cours** (sérialisation stricte) | `nonce_conflict` |
| P9 | Soldes : gaz de l'agent ≥ 2 × estimation ; solde du coffre ≥ montant | `insufficient_gas_balance` / `insufficient_token_balance` |
| P10 | Gaz : prix lu ; refus si prix > 10 × la médiane observée (protection contre un RPC menteur ou un pic) | `gas_price_out_of_bounds` |
| P11 | **Simulation** du calldata exact, **depuis l'adresse de l'agent**, au dernier bloc — refus si revert | `simulation_revert` |
| P12 | Estimation du gaz ; `gasLimit = 1,25 × estimation`, plafonné | `gas_estimate_failed` |

**Note de méthode** : la simulation est faite **depuis la clé de l'agent** (et non depuis une adresse neutre) : c'est le seul moyen de faire évaluer par le module les conditions réelles (rôle, allowance, plafonds, destinataire) dans les mêmes conditions que l'exécution.

### 5.6.4 Envoi, confirmations, reorgs, machine d'états

- **Transactions** de type « frais de base + priorité » (EIP-1559), dérivées des lectures du préflight avec plafond.
- **Sérialisation stricte** : une seule transaction en vol par signer ; la suivante attend le reçu ou l'expiration du délai. Le parallélisme est interdit au niveau du service.
- **Retries bornés** : erreurs de transport (timeouts, 5xx, « already known ») → 3 tentatives, backoff exponentiel (1 s, 4 s, 16 s), **sur la même transaction signée** (re-diffusion idempotente). **Jamais de retry** sur : revert de simulation, refus de politique, statut d'échec on-chain. On ne « retente » pas une attaque interdite.
- **Après N blocs sans inclusion** : transaction marquée « en attente périmée » ; deux options documentées et journalisées : re-diffusion à l'identique, ou **remplacement** (même nonce, frais relevés d'au moins +10 %) — **jamais** une nouvelle transaction avec un nonce plus haut pour « contourner » un blocage (cela réordonnerait un vol entier). Toute reprise exige la re-vérification idempotence + pause.
- **Confirmations (gelé)** : démo = statut succès + **attendre 2 blocs** avant de déclarer confirmé (blocs Base ≈ 1,64 s → ≈ 3,3 s), puis vérification ; production = tag `safe` pour l'action courante, tag `finalized` pour clore l'entrée d'audit (les deux tags sont **servis et testés** sur le RPC de démonstration).
- **Reorgs (politique minimale)** : enregistrer nœud **et empreinte de bloc** du reçu dès la lecture ; relire après la fenêtre de confirmation ; détection par disparition du reçu ou changement d'empreinte de bloc ; réaction : repasser par idempotence + pause + simulation ; si l'intention est toujours autorisée et non exécutée, ré-émettre ; sinon marquer « non résolu » et **escalade humaine** (décision gelée E4). **Jamais de double exécution.** Formulation honnête : un L2 à séquenceur centralisé a des reorgs courts mais pas impossibles ; la protection pratique est la fenêtre courte décision→envoi + les plafonds faibles.
- **Machine d'états d'exécution** : `PREPARED → SIMULATED → SUBMITTED → INCLUDED → CONFIRMED → VERIFIED` ; branches : `ABORTED` (préflight), `FAILED` (revert on-chain), `PENDING_STALE`, `REORGED`, `UNRESOLVED`.

### 5.6.5 Vérification du reçu — champs exacts, et l'échec est un résultat

Contrôles (chacun a un code de non-conformité) :

| Contrôle | Valeur attendue | Code |
|---|---|---|
| Statut | succès (`0x1`) ; **absent ≠ succès** | `TRANSACTION_FAILED` / `RECEIPT_STATUS_MISSING` |
| Chaîne | identifiant lu séparément par le client, attaché au reçu | `CHAIN_ID_MISSING` / `CHAIN_ID_MISMATCH` / `CHAIN_ID_INVALID` |
| Contrat du jeton | l'un des journaux d'événements émis par l'adresse du jeton | `TOKEN_CONTRACT_MISMATCH` |
| Événement | sujet de l'événement `Transfer` (empreinte recalculée localement — vérifiée égale à la constante) et **exactement 3 sujets** | `NO_TRANSFER_LOG` |
| Émetteur | thème 1 == **le coffre** (pas l'agent) | `SENDER_MISMATCH` |
| Destinataire | thème 2 == destinataire de l'intention | `RECIPIENT_MISMATCH` |
| Montant | donnée == `amount_base_units` — **comparaison entière**, jamais flottante | `AMOUNT_MISMATCH` |
| Enveloppe | la transaction va au module (l'appel passe par lui) et vient de l'agent | `WRONG_EXECUTOR` / `WRONG_TARGET` |
| Module | au moins un journal émis par le module (consommation d'allowance attendue) | `MODULE_EVENT_ABSENT` (avertissement) |

**Règle d'unicité** : s'il y a plus d'un journal `Transfer` du jeton dans le reçu et qu'**aucun** ou **plus d'un** ne correspond exactement au triplet (coffre, destinataire, montant), le résultat est marqué ambigu → vérification **non concluante**, revue humaine (jamais un « ok » optimiste). Comparaisons d'adresses insensibles à la casse ; montants en unités de base entières ; une adresse malformée est refusée, jamais réparée.

**Un échec est un résultat de première classe** : un statut d'échec est journalisé, son revert est capturé par rejeu de l'appel au bloc du reçu (sélecteur + message si décodable), son coût en gaz est enregistré — jamais masqué. Les runs de refus de la démonstration **sont** des échecs on-chain affichés : c'est le prix de l'attaque, et il est montré.

### 5.6.6 La démonstration : cinq runs, critères mesurables

Montage la veille (non chronométré) : coffre de démonstration 2/3 sur Base Sepolia ; module de permissions déployé **pour ce coffre** (instance propre) ; politique du rôle `AGENT` : cible = USDC de test, fonction `transfer` scopée, condition de destinataire (deux adresses autorisées), plafond d'allowance **300 USDC / 24 h** (`refill = maxRefill = 300e6`, période 86 400 s), quota **10 appels/jour** ; signer EOA financé par robinet ; politique hors chaîne versionnée (exécutée par le module déterministe). Contrôles de montage journalisés (propriétaire du module = coffre ; agent membre ; soldes ; script de re-vérification des adresses OK).

| Run | Scénario | Ce qui est démontré | Critères de succès mesurables |
|---|---|---|---|
| **A — ALLOW** | Intention `transfer` 100 USDC → préflight 12 contrôles → signature → reçu | Les **deux verrous** disent oui ; l'agent exécute seul dans l'enveloppe | reçu succès ; **exactement un** journal de transfert concordant ; variation des soldes exacte ; compteur de signatures = 1 ; les 7 types d'entrées de journal présents ; empreinte de bloc stable après 2 blocs |
| **B — DENY (politique)** | Montant > plafond ; destinataire hors liste ; rejeu d'une intention ×3 ; `change_policy` | **Le LLM propose, le système refuse** | compteur de signatures = **0** ; nonce de l'agent inchangé ; soldes inchangés ; 4 entrées de refus avec codes exacts ; aucun hash de transaction |
| **C — DENY (chaîne)** | Calldata interdits fabriqués **directement avec la clé de l'agent** : 500 USDC ; destinataire non listé ; tentative d'administration ; 4×100 USDC (dépassement cumulé) ; frontière de période | **La sécurité ne repose pas sur le logiciel ORVYREN** : même en contournant le premier verrou, la chaîne refuse | chaque cas : statut d'échec **et** sélecteur de revert capturé **et** aucun transfert correspondant **et** soldes inchangés ; frontière : 2 transactions chaîne acceptées + 1 refus hors chaîne — **la limite est montrée à côté de la preuve** ; le coût de gaz de chaque échec est enregistré |
| **D — Kill switch** | Le coffre retire le rôle (2 signatures sur 3) pendant que l'agent prépare une intention autorisée ; K2 en variante | **L'arrêt est réel, mesuré et révocable** | latences affichées (collecte des signatures, inclusion ≈ 1,64 s/bloc, effet) ; tentative de l'agent : refus (sélecteur de revert constaté on-chain — mesuré : `NotAuthorized(address)` = `0x4a0bfec1`, **pas** le nom supposé par la documentation) ; membre == faux après révocation |
| **E — Journal & audit** | Export du journal chaîné + rapport lisible + **vérification indépendante en direct** : un script relit chaque transaction, recalcule les transferts depuis les journaux on-chain, compare aux intentions | **La partie qui vend ORVYREN** : tout est recalculable | chaîne de hachage recalculée OK ; écart journal ↔ chaîne = **0** ; le rapport liste explicitement les refus et les échecs ; réconciliation des compteurs (événements de transfert du jeton == exécutions autorisées, hors financement de montage) |

**Deux USDC, deux robinets — à écrire dans le runbook** : le transfert de démonstration utilise l'**USDC de test** (`0x036CbD53…CF7e`, robinet Circle) ; toute action de prêt utiliserait l'**USDC d'Aave** (`0xba50Cd2A…4d5f`, robinet Aave). Ils ne sont **pas** interchangeables. C'est exactement le genre de détail qui fait échouer une démonstration en direct — il est donc contractualisé.

**Protocole de re-vérification des adresses (avant chaque exécution)** : pour chaque adresse du plan (module, coffre, jetons, routeur, pools, oracle, attestation), appeler `eth_getCode` et comparer la taille à la table de référence, vérifier l'identifiant de chaîne, enregistrer bloc + horodatage. **Tout écart = arrêt de la démonstration.** Un testnet peut être réinitialisé sans préavis : la mesure prime sur la mémoire.

## 5.7 Bloc F — Audit et vérifiabilité (la promesse produit)

### 5.7.1 Le journal unifié : trois flux, un manifeste

| Flux | Ce qu'il porte | Écrit par |
|---|---|---|
| **Raisonnement** (`agent_journal`) | plans, appels d'outils, réflexions, propositions, quarantaines ; modèle épinglé, empreintes de prompt/réponse, tokens, coût, latence, statut | chaque agent (1 écrivain par agent) |
| **Connaissance** (delta + snapshot du graphe) | objets créés/révisés par le run ; état figé + empreinte du snapshot ; chaînes de provenance résolues (zéro référence pendante) | le pipeline du graphe (seul écrivain) |
| **Exécution** (`audit.jsonl`) | intention → verdict de politique → simulation → envoi → reçu → vérification | le pipeline d'exécution (seul écrivain) |

**Pourquoi trois flux séparés, décision et non accident** : un lecteur externe doit pouvoir lire l'exécution seule (la plus vérifiable) ; le raisonnement n'alimente **jamais** la décision — le mélanger aux faits détruirait l'invariant « aucun chiffre ne vient du LLM » ; et la littérature identifie la cohérence multi-journaux comme problème **ouvert**, auquel nous répondons par un manifeste unique + un chaînage inter-flux explicite plutôt que par une mémoire partagée.

**Règles de forme (gelées)** : append-only strict (une correction est une nouvelle ligne avec référence de remplacement) ; JSONL UTF-8, une ligne = un enregistrement, clés triées, sérialisation canonique ; **SHA-256 partout** (bibliothèque standard, vérifiable par n'importe quel outil — l'ancrage on-chain ne stocke qu'une empreinte 32 octets, la fonction de hachage y est indifférente) ; horodatage ISO-8601 UTC ; **étiquette de mode obligatoire sur chaque enregistrement** (données courantes / rejeu journal / rejeu archive) ; versionnement de tout (format, run, épisode, politique, moteur, rôles, schémas) ; **un seul écrivain par flux** ; **aucun secret** (le journal est destiné à être publié intégralement) ; **le refus est un résultat** (refus, rejets, quarantaines, erreurs conservés et comptés).

**Chaînage — intra-flux et inter-flux** : chaque enregistrement porte `record_hash = SHA256(sérialisation canonique du record sans ce champ)` et `prev_hash` = empreinte du précédent **du même flux** (genèse = 64 zéros). À la clôture du run, un **manifeste** fige les têtes et compteurs des trois flux, les versions, les RPC et blocs utilisés, et l'inventaire des fichiers ; le flux d'exécution reçoit alors trois enregistrements de **liaison** (un par autre flux) + un **sceau** (empreinte du manifeste). Propriétés testées : **acyclique** (aucun objet ne référence un objet construit après lui), **anti-altération transitive** (modifier une ligne casse sa chaîne, donc la tête, donc le manifeste, donc la table d'intégrité du dossier et son empreinte self), **vérifiable par morceaux** (chaque flux indépendamment, puis la jonction). En l'absence d'un flux (run sans LLM), il est **déclaré absent au manifeste avec motif** — jamais de flux vide simulé.

### 5.7.2 Le dossier de décision — une page, auto-hachée

Le dossier de décision (une page md + html autonome, produits par gabarit déterministe — **aucun LLM**) est l'objet central : verdicts des trois axes, action, explications chiffrées, limites, provenance. Sa règle d'intégrité : le champ d'empreinte est mis à zéro puis la page entière est hachée (SHA-256) — la vérification est **reproductible avec n'importe quel outil**, y compris sur une machine sans le projet. Une table « intégrité » liste les empreintes des pièces d'entrée ; le dossier devient ainsi le point de jonction des trois flux sans créer de cycle (§5.7.1). Le dossier est **re-rendu à l'identique** depuis ses entrées machine (exigence testée, §5.7.4).

### 5.7.3 Le paquet auditable — le livrable est un ensemble, pas un fichier

`audit_packet_<cas>_<horodatage>_<run>/` (zippé, empreinte publiée), avec **12 pièces** :

| # | Pièce | Rôle |
|---|---|---|
| 1 | `README_AUDIT.md` (anglais) | Comment vérifier en 3 commandes ; « ce que ça prouve / ne prouve pas » (texte §5.7.6) ; inventaire |
| 2 | Dossier de décision md + html | La page auto-hachée (§5.7.2) — version anglaise pour la soumission |
| 3 | `decision_*.json` | La vérité machine du dossier (verdicts, action, explications, limites, provenance) |
| 4 | Extras du dossier : rapport de comparateur, rapport de qualité, verdicts de politique sur cas figés | Entrées du dossier, recalculables |
| 5 | `audit.jsonl` | Flux d'exécution chaîné + liaisons + sceau |
| 6 | `agent_journal.jsonl` (+ magasin de charges utiles hachées) | Flux de raisonnement — ou déclaré absent au manifeste |
| 7 | `graph/` : delta, snapshot, provenance | Flux de connaissance + provenance résolue |
| 8 | `manifest.json` | Têtes des flux, versions, RPC et blocs, inventaire |
| 9 | `receipts/` + `policy/` | Reçus bruts + politique versionnée + instantané de l'enveloppe on-chain (rôles, allowances) et lien vers le diff public |
| 10 | `verify/` : le vérificateur **gelé** + la sortie attendue | Le tiers peut vérifier sans nous, et sait à quoi ressemble un succès |
| 11 | `HASHES.txt` | Empreinte de chaque fichier + **empreinte du paquet** (le « digest » machine qui sert d'ancre) |
| 12 | `anchor/` (optionnel) | Preuve d'ancrage public si la condition de §5.7.5 est verte |

**Règles d'export** : le nom porte l'épisode, l'horodatage et le run ; l'empreinte du zip est publiée ; le paquet s'ouvre et se vérifie **sans nous** (aucun outil maison au-delà de Python standard) ; le dossier de décision n'entre pas dans l'empreinte du paquet (sinon cycle) mais est couvert par la liste. **Critère de maturité** : un reviewer externe qui n'a jamais parlé à l'équipe doit pouvoir répondre **seul** à 10 questions — qui a décidé ? sur quelles preuves ? qu'est-ce qui a été exclu et pourquoi ? pourquoi l'action passe la politique ? que s'est-il réellement passé on-chain ? quel était le mandat exact ? que proposait le raisonnement et qu'est-ce qui a été retenu/jeté ? quelles versions ont produit cela ? qu'est-ce qui est recalculable / revérifiable / non rejouable ? comment je vérifie moi-même ? — **chaque réponse pointant une pièce précise du paquet**. Si une question n'a pas de réponse « pièce, pas prose », le paquet n'est pas prêt. **Exclus explicitement** : clés, fichiers d'environnement, chemins personnels, données personnelles, journaux d'un autre run, résultats du jeu d'évaluation sous embargo, et **toute affirmation de performance**.

### 5.7.4 Le vérificateur tiers (essai T10) — spécification

**Exigence gelée** : « un tiers recalcule **sans réseau** chaque calcul déterminant (recette, entrées, version, sortie) ; toute **mutation d'entrée** est détectée ; **zéro référence pendante** ».

**Trois classes de vérifiabilité, écrites noir sur blanc** (le rapport n'emploie jamais un mot au-delà de la classe atteinte) :

| Classe | Définition | Éléments | Preuve exigée |
|---|---|---|---|
| **A — recalculable hors-ligne** | mêmes entrées + même code ⇒ même sortie au bit | chaînes des 3 flux ; self-hash du dossier ; empreintes des entrées ; **re-rendu du dossier** depuis la machine ; **verdicts de politique recalculés** ; empreinte du snapshot ; signaux reconstruits des fixtures ; croisement intention ↔ reçu | recalcul local, comparaison d'octets/hex |
| **B — revérifiable** | le fait on-chain est relu à la source (RPC), au bloc enregistré (immutable) | reçus (statut, bloc, journaux `Transfer`) ; soldes avant/après ; allowance après ; contrats présents (empreintes de code) | relecture `--rpc`, verdict séparé ; refus de conclure « PASS » global sans réseau |
| **C — non rejouable, couvert par le journal** | le texte d'un LLM n'est pas re-dérivable (non-déterminisme d'inférence documenté) | chaque appel enregistré (prompt/réponse hachés, modèle épinglé) ; validateurs déterministes **rejoués** sur les réponses enregistrées | rapport : chaque élément nommé et vérifié en **couverture**, jamais présenté comme « recalculé » |

**Outil** : `python -m orvyren.verify <cible> [--offline|--rpc] [--mutate-test] [--strict]` — cible = le paquet zippé ou le dossier ; `--offline` par défaut (aucun réseau ; les contrôles B sont marqués « sautés ») ; `--rpc` active les contrôles B (avec repli d'endpoint contrôlé) ; `--mutate-test` rejoue l'outil sur des copies **mutées** et exige la détection. **Sorties** : rapport machine (verdict `PASS` / `OFFLINE_PASS` / `FAIL`, un verdict par contrôle avec classe et statut `RECOMPUTED`/`REVERIFIED`/`COVERED`, liste des références pendantes, résumé par classe) + rapport lisible + code de sortie (`0` tout vert ; `1` échec d'intégrité ; `2` usage ; `3` réseau indisponible).

**Les 8 calculs déterminants (classe A)** : (A1) chaînes des 3 flux et têtes ; (A2) self-hash du dossier ; (A3) empreintes des entrées listées ; (A4) re-rendu du dossier **identique octet à octet** ; (A5) verdicts de politique recalculés sur les intentions enregistrées (y compris les refus) ; (A6) empreinte du snapshot du graphe ; (A7) signaux reconstruits depuis les fixtures (comparaison champ à champ) ; (A8) croisement intention ↔ reçu (fonction pure).

**Les 6 tests de mutation (auto-test)** : M1 modifier 1 octet du dossier → détecté par A2 ; M2 modifier 1 caractère dans le journal d'exécution → détecté par A1 + divergence de tête ; M3 modifier 1 chiffre dans la décision machine → détecté par A3 et A4 ; M4 modifier un montant dans un reçu brut → détecté par l'empreinte du reçu journalisée (règle de format : chaque entrée « reçu » porte l'empreinte du reçu brut) ; M5 retirer un fichier → détecté par l'inventaire du manifeste ; M6 modifier le vérificateur lui-même → détecté par l'empreinte (un vérificateur ne se certifie pas lui-même : distribution **double**, module du dépôt + copie gelée dans le paquet). **Cas limites exigés** : nominal, donnée absente, donnée invalide → rapport explicite, jamais d'exception, codes de sortie stables.

**Critères de succès (mesurables)** : 8/8 calculs classe A recalculés hors-ligne ; 100 % des verdicts de politique identiques après recalcul ; 6/6 mutations détectées et nommées ; zéro référence pendante ; rejeu hors-ligne complet sur une machine **sans dépôt ni client RPC** ; cas dégradés 2/2 ; contrôles B au moins sur une exécution et un refus ; 100 % des sorties LLM étiquetées « couvertes » ; durée cible < 5 s ; le vérificateur ne se certifie pas.

**Ce que le vérificateur ne fait pas** (écrit dans son rapport) : il ne rejoue pas le raisonnement LLM (il en vérifie la couverture) ; il ne prouve pas la véracité des sources externes ; il ne détecte pas une falsification coordonnée (réécrire le contenu **et** recalculer tous les hash) — c'est précisément la valeur de l'ancrage ; il ne prouve rien de ce qui n'a pas été journalisé.

### 5.7.5 L'ancrage : empreinte publiée obligatoire, registre public conditionnel

| Option | Coût | Ce que ça prouve / ne prouve pas |
|---|---|---|
| Aucun ancrage | 0 | Intégrité interne vérifiable **si le paquet est reçu intact** ; rien sur la datation |
| **(ii) Empreinte publiée — OBLIGATOIRE** | ~5 min | Le digest du paquet + l'empreinte du zip sont publiés (matériel de soumission, README du dépôt, copie horodatée) : **la version soumise est datée par des tiers**. C'est le minimum retenu, exécuté dès la confection du paquet |
| (iii) Ancrage dans un registre d'attestations public (testnet) — **conditionnel** | quasi nul (+ clé de testnet déjà prévue) | Existence et datation **indépendantes de nous** ; toute personne lit l'attestation et compare au digest. Conditions vertes requises : run on-chain vert, vérificateur vert, ≥ J-1 avant la soumission — sinon **reporté sans regret**. Un testnet n'est pas une preuve de production, et **une empreinte prouve l'intégrité et la datation, pas la véracité** |

Faits mesurés (15/10/2026) : le registre d'attestations est **présent et vérifié** sur Base Sepolia (contrat principal et registre de schémas, implémentations lues au slot standard) ; coût d'une attestation ≈ 0,0000007–0,0015 ETH au prix du gaz mesuré ; **la même procédure s'appliquera telle quelle sur le réseau principal** le jour venu — « ce qui change n'est pas l'architecture, c'est le montant ». Le script d'ancrage est un utilitaire séparé (jamais une action de l'agent), la clé reste hors dépôt, et l'ancre porte un digest unique, recopiable à la main par un membre du jury.

### 5.7.6 Ce que l'audit prouve — et ce qu'il ne prouve pas

**Il prouve** (8 points, texte de référence) : (1) **Intégrité** — rien n'a été modifié depuis le scellé (toute altération casse une chaîne ou le self-hash) ; (2) **Reconstruitibilité** — chaque calcul déterminant est recalculé hors-ligne par un tiers, mêmes entrées, mêmes versions, mêmes sorties ; (3) **Correspondance intention ↔ exécution** — ce que le système voulait faire, ce qu'il a été autorisé à faire, ce qui s'est réellement passé sont trois objets distincts et comparés ; (4) **Bornage du mandat** — ce que l'agent **pouvait** faire est un fait public daté ; le pire cas est un nombre fini et lisible ; (5) **Admissibilité temporelle** — chaque fait porte ses horloges ; ce qui n'était pas admissible à l'instant de la décision en est exclu ; (6) **Conservation des refus** — refus, rejets, quarantaines, abstentions : journalisés et comptés ; (7) **Indépendance des canaux** — deux canaux de la même archive ne comptent jamais comme deux confirmations ; (8) **Imputabilité** — chaque étape attribuée à un composant versionné, avec ses entrées et sorties.

**Il ne prouve pas** (8 points) : (1) la **véracité** des sources externes (un oracle peut se tromper même avec toutes les chaînes de hachage valides) ; (2) la **justesse** des hypothèses ou la qualité des décisions ; (3) toute **performance financière** — non revendiquée ; (4) l'**exhaustivité** (ce qui n'est pas journalisé n'y figure pas) ; (5) le **texte des appels LLM n'est pas rejoué** — il est couvert par le journal ; (6) l'absence de **bugs** dans les composants amont (contrats tiers, fournisseurs de données) ; (7) la **conformité juridique** d'une juridiction ; (8) une empreinte ancrée prouve l'intégrité et la datation, **pas la véracité**.

**Formulations interdites** (appliquées partout, y compris au pitch) : « la blockchain nous décharge juridiquement » (faux : la chaîne prouve des faits, elle ne répartit pas la responsabilité) ; « l'agent est audité » quand seuls les contrats amont le sont (on audite **la politique**) ; « zéro risque », « impossible à détourner » (contredit par les incidents publics 2026 des modules amont) ; « rejouable/reproductible » **sans qualifier la classe** (A/B/C) ; « preuve de véracité » pour un ancrage.

---

## 5.8 Bloc G — Évaluation et apprentissage

### 5.8.1 Le pipeline des résultats (« outcomes ») — trois producteurs distincts

Le vocabulaire est gelé, parce que le confondre fabrique de fausses preuves :

| Objet | Définition | Producteur | Entre dans la calibration ? |
|---|---|---|---|
| **Prévision gelée** | énoncé d'un événement futur, critère de résolution et horizon, haché, jamais modifié | composant déterministe, **signé par un humain** | oui — c'est la brique `p` |
| **Résultat (outcome)** | ce qui a été observé à l'horizon, écrit **après** la fenêtre | résolveur déterministe (archives) ou opérateur attesté (hors chaîne) | oui — c'est la brique `y` |
| **Reçu (receipt)** | la chaîne a-t-elle exécuté l'action autorisée | vérificateur de reçu (existant) | **non** — preuve d'exécution, pas de prévision |
| **Score** | `(p−y)²` par prévision, puis agrégats | recalculable à tout moment | c'est l'agrégat |

**Trois producteurs, jamais mélangés** : (1) le **résolveur déterministe** écrit le résultat d'une prévision gelée à partir du corpus figé (règle de résolution gelée : « dépeg soutenu = écart > 1 % persistant ≥ 2 observations », convention de prix gelée par source) — une divergence entre deux exécutions du résolveur est un bug bloquant ; (2) le **vérificateur de reçu** atteste l'exécution (transaction, bloc, statut, journal de transfert décodé, comparaison à l'allowlist) — cela sert la sûreté et l'inventaire « 0 action hors enveloppe », **pas** le score ; (3) un **opérateur nommé** écrit, avec attestation datée et références, les résultats **hors chaîne** (obligation honorée, épisode sans série de prix) — publiés **séparément**, jamais agrégés sans drapeau. Le distinguo est un principe : **le reçu prouve l'action, pas la décision** ; une prévision peut se résoudre sans aucune transaction, et une transaction peut exister sans prévision.

**Deux horizons, gelés avant observation** : `H_class = 6 h` (événement « dépeg soutenu ») et `T` = fin de fenêtre d'épisode (métriques de perte). Un même forecast peut avoir deux outcomes (un par horizon). Formats : prévision = {identifiants, épisode, énoncé, règle de résolution, horizon, `p`, origine de `p`, état d'observation au gel, signature, empreinte, chaînage} ; résultat = {identifiant, référence + empreinte de la prévision, horizon, `y`, valeurs observées, mode de résolution, références de preuve, horodatage, chaînage}. **Règles opposables** : liaison par empreinte (un résultat dont l'empreinte ne correspond plus est rejeté) ; append-only ; une correction est un nouveau résultat avec référence de remplacement (les deux apparaissent au rapport) ; interdiction d'écrire un résultat avant l'horizon (garde de code, testée) ; interdiction de modifier `p` après gel ; interdiction de faire produire `p` par un LLM. **Ce qui n'est PAS un résultat** : la valeur de marché d'une position qu'on n'a pas vendue (valorisation ≠ réalisation), une opinion de modèle, un prix d'agrégateur présenté comme réalisable, un résultat partiel présenté comme final.

### 5.8.2 Calibration — métriques, exemple vérifié, seuils

Métriques spécifiées (toutes implémentables en bibliothèque standard, contrainte projet) : **score de Brier** `BS = (1/N) Σ (p−y)²` ; **décomposition de Murphy** `BS = REL − RES + UNC` évaluée **sur les mêmes intervalles gelés que l'ECE** (l'identité devient exacte, donc testable) ; **ECE** (erreur de calibration attendue) à **10 intervalles fixes gelés d'avance** ; **courbe de fiabilité** par intervalle avec effectifs ; **bornes de Wilson** (intervalle de confiance d'une proportion) ; **bootstrap par blocs** (rééchantillonnage circulaire par blocs de 6–12 h, 10 000 réplications, graine fixée) ; **compétence vs climatologie** (`BSS`). [FAIT SOURCÉ — Brier 1950 ; Murphy 1973 ; Naeini et al. 2015 ; Wilson 1927]

**Exemple chiffré vérifié (« réponse connue », test unitaire de référence)** — `p = [0,2 ×5 ; 0,8 ×5]`, `y = [0,0,0,0,0, 1,1,0,1,1]` :

| Grandeur | Valeur |
|---|---|
| `BS` | **0,100000** |
| `REL` | **0,020000** |
| `RES` | **0,160000** |
| `UNC` | **0,240000** |
| identité `REL − RES + UNC` | **0,100000 = BS** ✔ |
| `ECE` (10 intervalles fixes) | **0,100000** |
| climatologie `ȳ` | **0,400000** |

Ce vecteur est le test de référence : il détecte en une exécution toute erreur d'intervalle, de formule ou d'identité.

**Bornes de Wilson à recopier dans chaque rapport** (extrait vérifié) : 0 réussite sur 6 → borne supérieure **39,0 %** ; sur 12 → **24,2 %** ; sur 36 → **9,6 %** ; sur 100 → **3,7 %**. Phrase obligatoire partout où un « 0 échec » apparaît : **« 0/6 ne signifie pas taux nul, mais taux compatible avec jusqu'à ≈ 39 % »**.

**Quand peut-on dire « calibré » — cascade de garde-fous** :

| Effectif N (prévisions gelées résolues) | Ce qui est publié | Libellé |
|---|---|---|
| N < 5 | rien | « NON CALCULÉ — effectif insuffisant » |
| 5 ≤ N < 30 | `BS`, `REL`, `RES`, `UNC`, climatologie, liste des prévisions (sans revendication d'ECE) | **« non conclusionnel »** |
| 30 ≤ N < 100 | idem + intervalles + courbe de fiabilité | **« non conclusionnel »** |
| N ≥ 100 | tout + `BSS` avec borne basse | revendication possible, sous 5 conditions |

**Les 5 conditions pour écrire « calibré »** : N ≥ 100 prévisions gelées **hors échantillon** ; ECE ≤ 0,05 avec borne haute d'intervalle ≤ 0,08 ; courbe sans déviation systématique ; compétence (borne basse de `BSS` > 0) ; **≥ 2 familles d'épisodes disjointes** — et le jeu n'a servi à aucun réglage (déclaratif + journal des variantes). Avec notre effectif réaliste (5–12), l'état par défaut est donc « non conclusionnel » : **le document le publie au lieu de le maquiller**. Garde-fous permanents : publier N et la climatologie partout ; ne jamais fusionner DEV et EVAL ; ne jamais moyenner les regrets positif et négatif ; pas d'intervalles re-découpés après avoir vu les résultats ; hacher le code de scoring et les prévisions (un rapport sans empreinte n'est pas vérifiable).

**Ce qui reste « non établi »** (à recopier tel quel) : la calibration de la prévision tant que N < 100 ; la transférabilité d'un régime à un autre (non-stationnarité — on peut la mesurer, pas la garantir) ; la couverture des événements rares (la garantie est conditionnelle à des hypothèses violées par construction en crise : on publie couverture prédite vs empirique, jamais une garantie nue) ; la confiance verbalisée d'un LLM (interdite par construction) ; `P(obligation)` (hypothèse signée, pas une estimation calibrée). Et le principe de séparation : **la qualité d'une décision ≠ la calibration d'une prévision** — le Brier mesure les prévisions, la perte évitée/le P&L mesurent les décisions ; aucun score unique ne remplace l'autre.

### 5.8.3 Le moteur de rejeu — deux modes officiels

| Mode | Ce qui est rejoué | Déterminisme | Réseau | Étiquette affichée |
|---|---|---|---|---|
| **REPLAY-JOURNAL** | le journal d'agents + le magasin de réponses hachées : la séquence est relue étape par étape, rien n'est recalculé | **bit-à-bit garanti par construction** (chaînage vérifié à la lecture) | aucun | `REPLAY (journal, rseth-2026-04, t_sim=…)` |
| **REPLAY-ARCHIVE** | les appels LLM **sont recalculés** sur les données archivées (corpus figé + blocs fixes), versions épinglées, température 0 | **non garanti** : « même décision, texte différent » — c'est un résultat à publier, pas un échec | fournisseur LLM (aucun « live » : toutes les lectures chaîne passent par des blocs fixes) | `REPLAY (archive, données archivées)` |
| *(hors rejeu)* LIVE | données courantes | non déterministe par nature | oui | `LIVE` |

**Horloge simulée** (`t_sim`) : strictement monotone, pilotée par les événements du corpus ; **seule autorité PIT** — tenter d'admettre un objet dont l'horodatage dépasse `t_sim` **abandonne le run** (violation PIT) et l'incident est écrit. Double horodatage obligatoire dans chaque artefact (temps simulé pour le PIT, temps réel pour l'audit d'exécution) : confondre les deux est la faille classique (« le rejeu a l'air d'avoir prédit parce que ses timestamps sont ceux du rejeu »).

**Sources admissibles** : corpus figé (manifeste : fichiers + empreintes + dates de récupération + bornes) ; blocs fixes pour toute lecture chaîne (une ancre par jour, résolue et cachée ; **aucun « latest »** dans un run de rejeu — garde de code) ; configurations gelées (fonctions de perte, comparateurs, fenêtres, seuils, hypothèses, modèles épinglés) ; journal + magasin de réponses. Le moteur refuse de démarrer si une empreinte du manifeste ne correspond pas au disque.

**Marquage obligatoire** : champ de provenance dans tout artefact (`mode`, `replay_id`, bornes simulées, empreintes du corpus et du code) ; bannière en tête de toute sortie écran/html ; suffixe de nommage des fichiers ; **interdiction d'effets** — un rejeu ne signe jamais et n'émet jamais de transaction (les intentions produites sont marquées « simulées » et la politique s'exécute en mode sec) ; journal des rejeux append-only. **Ce que le rejeu ne prouvera jamais** (à ne pas revendiquer) : la performance financière, la supériorité prédictive, ou la reproductibilité du texte des modèles.

### 5.8.4 Jeux DEV / EVAL, embargos, publication

| Épisode | Jeu | Rôle |
|---|---|---|
| USDC / SVB (mars 2023) | **DÉVELOPPEMENT** | réglages, débogage, mesure des coûts ; contamination assumée (l'épisode est dans les données d'entraînement de tout modèle 2026) |
| stETH / Celsius (mai–juin 2022) | **DÉVELOPPEMENT — backtest long** | contrôle de longue série, test de non-régression des seuils |
| rsETH / KelpDAO (avril 2026) | **ÉVALUATION #1 (principal)** | exécuté **une fois** après gel ; abstention après le gel = réponse attendue |
| USD0++ (janvier 2025) | **ÉVALUATION #2 (secondaire)** | second cas d'évaluation, mécanisme différent (débasement contractuel) ; contamination probable assumée |
| Fenêtres CALME 2022–23 / 2025–26 | DEV / EVAL | faux signaux, friction, placebo |
| xUSD (novembre 2025) | hors jeu | qualitatif seul (pas de perte évitée quantifiable honnêtement) |

**Les 4 embargos (règles de séparation)** : (1) **paramètres** — aucune constante de la fonction de perte, des seuils, des hypothèses économiques ou des intervalles de calibration n'est modifiable après la **première exécution sur EVAL** ; toute modification **invalide** l'évaluation (re-étiquetage obligatoire — pas « affaiblit ») ; (2) **données** — la bande de 24 h précédant chaque fenêtre EVAL est retirée du DEV (initialisation uniquement) ; (3) **inspection** — avant le gel, personne n'inspecte les fenêtres EVAL au-delà de ce qui est déjà publié ; après la première exécution, le jeu est **brûlé** ; (4) **calibration croisée** — les quantiles utilisés pour toute revendication d'évaluation sont calculés **hors** des mois des fenêtres CALME d'évaluation (sinon la calibration « voit » le jeu — la fuite la plus sournoise) ; vérification mécanique : le script d'évaluation **refuse d'écrire** sans gel présent, refuse une seconde exécution sans mention « ré-exécutée (invalide pour la revendication) », et refuse toute fenêtre CALME EVAL chevauchant la période de calibration déclarée.

**Publiable avant la soumission** : le gel complet haché, la démonstration DEV (étiquetée DEV), le squelette de rapport de calibration à N=0, la spécification du harnais, les coûts de rejeu mesurés. **Interdit avant la première exécution EVAL** : tout résultat EVAL à quelque titre que ce soit ; toute moyenne agrégée DEV/EVAL ; toute revendication de supériorité ; toute liste de fenêtres EVAL modifiée après ouverture. **Position recommandée** : publier le pré-enregistrement + DEV, et écrire explicitement « évaluation gelée, non encore exécutée » — c'est plus fort qu'un chiffre contaminé.

### 5.8.5 Le harnais — comparateurs et métriques par persona

**Comparateurs (labels gelés)** : **A0 = ne rien faire** (l'adversaire décisif du regret) ; **A1 = règle de seuil** (décote ≥ 50 bps pendant 15 min → réduction bornée) ; **A2 = l'agent ORVYREN** (rejeu journal en priorité, sinon archive k=3) ; **B0 = placebo apparié** (même nombre et mêmes tailles d'actions que A2, horodatages tirés uniformément, **M ≥ 200 tirages, graine fixée** ; on publie la **distribution** et le percentile de A2) ; **AX0 = règle historique du dépôt** (0,99 × 2 observations → réduction fixe ; 2 signaux sur la fenêtre principale, **0 faux signal** sur la fenêtre contrôle 15–18/02/2023) ; **O = oracle ex post faisable** (borne inférieure du regret, pas une vérité terrain). **Deux phrases gelées avant l'exécution** : si A2 ne bat pas B0, la valeur n'est pas dans le **choix du moment** ; si A2 ne bat pas A1, elle n'est pas dans la **délibération** — on l'écrit.

**Boucle** : pour chaque jeu (sous garde de gel) → pour chaque fenêtre → pour chaque configuration, générer les actions, calculer richesse/loss/regret avec la fonction gelée, agréger par fenêtre et par persona, puis intervalles (Wilson, bootstrap par blocs) ; **budgets égaux** entre A2 et ses variantes ; **unité d'analyse = la fenêtre** (jamais l'heure) ; vecteur de métriques, jamais un score unique.

**Métriques persona DAO** : **SD1** perte évitée matérielle — `(L(A0) − L(A2))` en % de l'exposition **conditionnellement à l'obligation**, les deux facteurs publiés, + second affichage en **jours de roulage** (référence : 44 932 $/jour) — cible ≥ 5 % (à valider) ; **SD2** friction maîtrisée — coût cumulé en calme ≤ 10 % de la perte évitée de crise ; **SD3** anticipation — antériorité ≥ 6 h sur ≥ 1 épisode EVAL et délai de réaction ≤ 60 min ; **SD4** supériorité — regret moyen strictement inférieur à A1 **et** B0, avec intervalles, regrets positif/négatif séparés ; **SD5** traçabilité — 100 % des actions avec provenance + empreinte, 0 action hors enveloppe ; **SD6** honnêteté — mentions « non conclusionnel » où la puissance manque.

**Métriques persona desk** : **ST1** ΔP&L net cumulé tous coûts inclus (frais, slippage mesuré, financement) > 0 avec intervalle de confiance ; **ST2** qualité d'exécution — slippage réalisé ≤ 30 bp sur une sortie de stablecoin en stress ; **ST3** risque borné — drawdown maximal ≤ 20 % du capital alloué par épisode ; **ST4** risque ajusté — Sharpe/Sortino **corrigé du nombre de variantes** (multiplicité des essais), borne basse d'intervalle > 0, sinon « non conclusionnel » ; **ST5** supériorité vs A1/B0 avec intervalles ; **ST6** asymétrie déclarée — l'agent est un put (coût certain, gain conditionnel), scénarios publiés. Deux P&L publiés (avec et sans financement) ; la re-entrée est modélisée pour le desk, pas pour la DAO.

**Règle de langage** : tout tableau porte son effectif N et sa validité (« non conclusionnel si N < 100 ») ; regrets séparés jamais moyennés ; échecs inclus au journal des variantes.

### 5.8.6 Apprentissage : ce qui est révisé en v1 — rien d'automatique

**Constat gelé, écrit noir sur blanc** : en v1, **aucune** boucle d'apprentissage n'écrit dans la décision. Ce qui est automatique est un **calcul** (résolution des prévisions à l'horizon ; scores recalculables ; vérification des chaînages ; promotion journal → graphe par validateurs déterministes ; portes d'admission des données ; comptabilité des coûts/latences/variantes) — pas une **révision**. Aucun seuil, aucun prior, aucun prompt, aucune politique ne se modifie sans une **intervention humaine** sous forme de gel versionné et haché. Toute révision humaine suit la même mécanique (nouvelle version datée + empreinte + motif + entrée au journal des variantes, échecs inclus) ; la cadence de revue est trimestrielle + à chaque déclencheur (dérive détectée, nouvel épisode, changement de version de modèle). Les boucles avancées (calibration continue, seuils par quantiles en ligne, méta-apprentissage) sont des **propositions V2**, étiquetées comme telles dans le document 3/4 — rien de tout cela n'est dans le périmètre.

## 5.9 Bloc H — Interface & Opérations

### 5.9.1 Décision d'hébergement : FULL LOCAL pour la v1 (gelé, ajusté)

La démonstration et la v1 tournent **100 % en local, hors-ligne** : base SQLite + corpus archivé + mode rejeu ; seuls les runs on-chain passent par le RPC public de Base Sepolia (aucun serveur à héberger). Les options d'hébergement (service web en lecture seule, base PostgreSQL gratuite permanente) sont **reportées** : elles restent la cible post-concours, sans impact sur l'architecture (migration contenue dans le module store). Corollaire de la même décision : **la préparation de la vidéo de démonstration est reportée** — elle dépend de la construction de l'interface, qui elle-même suit le gel.

### 5.9.2 Les écrans de la démonstration (12 écrans spécifiés)

Contraintes actées, valables pour tout écran : **rendu déterministe** pour l'enregistrement (mode rejeu journal bit-à-bit ; si un écran exige du direct, il est tourné à part et étiqueté) ; **mode hors-ligne** partout (corpus archivé, SQLite, captures d'avance pour les écrans chaîne) ; **marquage obligatoire** (bandeau de mode + horloge simulée affichée — jamais un rejeu présenté comme du direct) ; **aucune dépendance** (HTML statique autonome, sans JavaScript ni ressource externe).

| # | Écran | Contenu | Preuve à l'écran | Mode |
|---|---|---|---|---|
| 1 | Fenêtre & PIT | 520 observations archivées, couverture par heure/place, instant simulé | manifeste du corpus | rejeu journal |
| 2 | Graphe | sources → observations → claims → relations ; **contradictions affichées** | requête du graphe as-of | rejeu journal |
| 3 | Branches en évolution | H1/H2/H3 avec leur **timeline d'états** datée et référencée | journal filtré + table des branches | rejeu journal |
| 4 | Timeline des réflexions | deux colonnes (explorateur / critique) avançant étape par étape, objections visibles | journal par agent | rejeu journal |
| 5 | Recherche & coût | tâche choisie, motif, coût réel, **ce qui n'a PAS été recherché** | journal + table des tâches | rejeu journal |
| 6 | Dossier de décision | action candidate + explication **recalculée** (chiffres du moteur) | dossier 1 page + JSON machine | rejeu journal |
| 7 | Refus par la politique | ALLOW/DENY/REQUIRE_APPROVAL avec règles violées ; compteur de signatures = 0 | verdicts de politique | rejeu journal |
| 8 | Refus & quarantaine | lignes rejetées/quarantainées : la mémoire interne n'a pas contaminé le graphe ; test d'injection | journal + banc de tests | rejeu journal |
| 9 | Coût par décision | appels, tokens, latence, USD par rôle (table de prix datée) | journal | rejeu journal |
| 10 | Chaîne — run A | intention → politique ALLOW → simulation → transaction → reçu ; soldes avant/après, allowance | reçu + module (onglet permissions) | direct capturé |
| 11 | Chaîne — run C | rejets par la chaîne : statuts d'échec, sélecteurs de revert, soldes inchangés ; frontière de période (limite assumée montrée) | reçus + gaz perdu | direct capturé |
| 12 | Journal & kill switch | journal chaîné exporté + vérification indépendante en direct ; latences K1 chronométrées | journal + reçus + diff de permissions | direct capturé |

**Minimum non négociable** pour une vidéo ≤ 5 min : écrans 1, 3, 4, 6, 7, 8 + au moins 12. Les écrans 10–11 exigent le portefeuille testnet financé (chemin critique) ; s'ils glissent, la vidéo reste montrable en rejeu seul, avec les runs chaîne démontrés par captures + reçus dès qu'ils sont exécutés.

### 5.9.3 Interface produit (direction) et intégration continue

Direction produit (au-delà de la démo, priorisée) : dossier de décision servi (existant) → **liste des refus + quarantaines** (extension triviale) → **timeline branches & réflexions** (dès que les agents existent) → file d'approbation (V1.5) → alertes et monitoring des agents (V2) → statut de trésorerie à double valorisation (V2, « le tableau de bord qui vend le produit »). **Garde-fou transverse : tout est en lecture seule ; aucune route d'écriture en v1** ; la file d'approbation, quand elle viendra, se fera par **signature du portefeuille de l'humain** — jamais par un bouton qui déclencherait une clé serveur.

Intégration continue (existante : tests + pipeline de bout en bout + collecte hors-ligne) ; **ajouts acceptés** : contrôle « aucun secret » (recherche d'empreintes de clés privées et de fichiers d'environnement dans les artefacts), cohérence du registre de décisions, construction des documents, et exécution du vérificateur sur des journaux de fixtures. Chaque ajout ≤ un demi-jour, aucun ajout qui ralentit le chemin critique.

### 5.9.4 Runbook opérationnel

- **Démarrage** : pipeline complet en une commande (qualité → décision → politique → audit ; échec bruyant) ; page dossier en local ; montage chaîne la veille (coffre, module, rôle, allowance, signer financé ; vérification de version du module avant chaque période d'exécution) ; contrôle de santé avant toute session (coût de santé : une requête ; empreinte du corpus conforme ; version de politique affichée).
- **Arrêt d'urgence** : §5.5.6 (K0 ≤ 5 min ; K1 ≤ 60 min ; procédure humaine d'incident écrite, message type, et rappel : le kill switch n'annule pas une transaction déjà incluse).
- **Mise à jour de politique** : fichier versionné + banc de sûreté vert **avant** déploiement ; si l'enveloppe on-chain change, c'est **par la DAO** dans l'app de permissions (jamais par l'agent) ; **test de dérive** rejoué ; version incrémentée et citée dans chaque entrée de journal ; diff conservé.
- **Rotation de clé** : nouvelle EOA (clé hors dépôt/logs/LLM) → attribuer le rôle à la nouvelle, retirer à l'ancienne (une transaction) → alimenter le gaz → vérifier membre == vrai → journaliser la rotation (type d'événement dédié).
- **Incidents & veille** : veille sur les communiqués de sécurité du module amont (test automatique de version au démarrage) ; surveillance des événements (attributions de rôle, consommations d'allowance, transferts) et des anomalies (destinataire nouveau, montant inhabituel, rafale) ; alertes minimales (refus répétés sur la même intention, échec de vérification de reçu, rupture de chaînage du journal, absence de battement de cœur) ; rétention : graphe et journaux append-only.

### 5.9.5 Sécurité de l'interface

| Principe | État |
|---|---|
| Aucun secret côté client | **acquis** : interface = HTML statique sans JavaScript ni ressource externe ; aucune clé jamais requise par l'interface ; contrôle de non-fuite ajouté à l'intégration continue |
| Lecture seule par défaut | **acquis** : seules les méthodes de lecture ; toute autre route → erreur propre ; en-tête anti-cache |
| Bind local par défaut | **acquis** : écoute sur l'adresse locale ; l'exposition publique, si un jour, passe derrière le proxy de l'hébergeur |
| En-têtes de sécurité | à ajouter avant toute exposition (politique de sécurité de contenu restrictive, anti-sniffing, anti-cadrage) |
| Séparation des privilèges | **structurelle** : l'interface n'exécute rien ; la politique est hors LLM ; l'exécution n'accepte qu'un verdict ALLOW ; la clé vit dans un processus séparé, hors LLM / graphe / journaux / dépôt |

**Règle d'or de l'interface (à retenir)** : « *l'interface **montre** et **instruit** (construit des objets non signés), elle ne **signe** jamais et ne **détient** jamais de secret.* »

---

# 6. Décisions gelées — le registre complet

Ce tableau est le condensé du registre de gel v1 (15/10/2026). Toute contradiction entre ce document et une note antérieure se tranche ici. Les ajustements du 15/10 (interface locale, vidéo reportée) et les confirmations des organisateurs du 14/10 sont intégrés.

## 6.1 Bloc A — Agents

| # | Décision | Statut |
|---|---|---|
| A1 | **Multi-agent réel — MA-B** : instances séparées minimales (orchestrateur + critique adversarial, processus distincts, journaux propres, outils bornés) ; extension multi-agents complète plus tard, sans refonte | GELÉ |
| A2 | Modèles via API : **DeepSeek flash** (principal) + **MiMo flash/pro** (secondaire/critique) ; clés fournies par l'équipe ; plafond mensuel par défaut : **20 $** | GELÉ (défaut) |
| A3 | Critique sur un **second modèle dès la v1** (adversarial cross-modèle) | GELÉ |
| A4 | **Mémoire interne** : journal d'agents append-only **séparé du graphe** ; promotion uniquement par validateurs déterministes ; branches LLM à **poids nul** | GELÉ |
| A5 | Budgets par décision : **≤ 30 appels LLM · ≤ 12 outils · ≤ 10 min · ≤ 0,10 $** ; arrêt fail-closed | GELÉ |
| A6 | Rétention du journal d'agents : **intégrale** | GELÉ |

## 6.2 Bloc B — Graphe

| # | Décision | Statut |
|---|---|---|
| B1 | Catalogue **34 relations / 4 familles** (preuve & dérivation 8 · structure & exposition 15 · mécanisme économique 3 · contrainte & permission 8) + **record 17 champs**, énumération machine-vérifiable + tests de conformité | GELÉ |
| B2 | **SQLite pour le concours** → **PostgreSQL (gratuit permanent)** cible post-concours ; le **store** est le seul point d'accès | GELÉ |
| B3 | **ML v1** : embeddings pour la recherche sémantique ; anomalies **hors chemin décisionnel** (étiquetées « inféré par modèle ») ; réseaux de neurones de graphe post-concours ; **rien d'appris dans le confirmatoire** | GELÉ |
| B4 | Techniques : anti-reorg 2 blocs (démo) / tags safe+finalized (prod) ; suivre l'implémentation derrière les proxies ; **une source par quantité** ; conditions en énumération ; export de l'ontologie en vocabulaire PROV-O en annexe ; un graphe + vues multi-chaînes ; local prioritaire | GELÉ |

## 6.3 Bloc C — Décision

| # | Décision | Statut |
|---|---|---|
| C1 | Discipline **ACH** (falsifiabilité obligatoire, réfutation d'abord — pas la matrice seule) + record d'hypothèse **12 champs** + cycle **7 états** | GELÉ |
| C2 | **RDOF v1** déterministe (« quel prédicat réfute le leader au moindre coût ») ; testé contre l'ordre fixe **avant** toute activation d'une valeur d'information (derrière interface, `VOI_NOT_ESTIMABLE` autorisé) | GELÉ |
| C3 | Abstention **A1–A5** + format enrichi + table **ESCALATE vs NO-ACTION** | GELÉ |
| C4 | Actions : **8 DAO + 4 desk** ; v1 implémentée = transfert borné (démo) ; le reste **simulé** | GELÉ |
| C5 | Prix : **double convention** — alerte sur le **plus bas**, décision sur **clôture + plus bas** | GELÉ |
| C6 | Horizon de classification **H_class = 6 h** | GELÉ |
| C7 | `P(obligation)` / scénarios : signés par le responsable d'équipe (défaut) + **sensibilité publiée** | GELÉ (défaut) |

## 6.4 Bloc D — Politique

| # | Décision | Statut |
|---|---|---|
| D1 | Set v1 = **14 règles**, codes de refus stables, **fail-closed** | GELÉ |
| D2 | Approbation : démo = **file + signature EIP-712** (TTL 2 h, canal local) ; produit = file multi-rôles + file du coffre multi-signatures / module de délai | GELÉ |
| D3 | Asymétrie : **réduire = immédiat ; augmenter = procédure complète** | GELÉ |
| D4 | Kill switch : **K0 ≤ 5 min · K1 ≤ 60 min** ; coffre de démo 2/3 = responsable + 2 (défaut) | GELÉ (défaut) |
| D5 | Ancrage du hâchage de politique dans un registre public : **reporté post-concours** | GELÉ |

## 6.5 Bloc E — Exécution

| # | Décision | Statut |
|---|---|---|
| E1 | Signer démo : **clé jetable en variable d'environnement** (jamais dépôt/logs/prompts), gaz par robinets gratuits, **détruite après la démo** ; bibliothèque : dépendance de signature isolée (défaut) ; produit : backend de clé remplaçable (hors v1) | GELÉ (défaut) |
| E2 | Run ALLOW : **100 USDC** | GELÉ |
| E3 | Échange / approbation de jeton **simulés en v1** ; prêt Aave = v2 | GELÉ |
| E4 | Après reorg : **escalade humaine** | GELÉ |
| E5 | Runbook : **deux USDC distincts** sur Base Sepolia (Circle = transferts ; Aave = lectures/prêt) nommés explicitement | GELÉ |

## 6.6 Bloc F — Audit

| # | Décision | Statut |
|---|---|---|
| F1 | Journal **3 flux chaînés SHA-256** + paquet **12 pièces** + empreinte du paquet | GELÉ |
| F2 | **Vérificateur** `python -m orvyren.verify` (essai T10) | GELÉ |
| F3 | **Empreinte publiée obligatoire** ; ancrage public **conditionnel** (runs chaîne + vérificateur verts avant la date limite) | GELÉ (conditionnel) |
| F4 | Textes « prouve / ne prouve pas » en français (interne) et anglais (paquet), verbatim | GELÉ |

## 6.7 Bloc G — Évaluation

| # | Décision | Statut |
|---|---|---|
| G1 | DEV = USDC + stETH + fenêtres calmes 2022-23 ; **EVAL = rsETH + USD0++ + fenêtres calmes 2025-26** ; xUSD qualitatif | GELÉ |
| G2 | **Embargo de calibration croisée** | GELÉ |
| G3 | Comparateurs **A0/A1/A2/B0** (+ AX0) | GELÉ |
| G4 | GO : modules de perte + comparateurs + calibration (~1,5 j) + **5-10 prévisions gelées DEV avant la date limite** | GELÉ (GO) |

## 6.8 Bloc H — Interface & Ops *(ajusté par l'équipe, 15/10)*

| # | Décision | Statut |
|---|---|---|
| H1 | Spécification d'interface (12 écrans) ; **préparation vidéo REPORTÉE** (dépend de la construction de l'interface) | GELÉ (ajusté) |
| H2 | Interface v1 = **lecture seule** ; approbations en V1.5 | GELÉ |
| H3 | **Hébergement : 100 % local pour commencer** ; service web + base gratuite = options ultérieures | GELÉ (ajusté) |
| H4 | Ajouts d'intégration continue acceptés (secrets, registre, documents, vérificateur) | GELÉ |

## 6.9 Bloc I — Gouvernance & documents

| # | Décision | Statut |
|---|---|---|
| I1 | Protocole de gel : **dossier de décision type ADR** + registre unique + paquet haché (le gel v1 = première version du paquet) | GELÉ |
| I2 | **Règle 0 : aucune mention d'un système amont** dans les documents ; les concepts sont **redéfinis en propre** (horloges temporelles, chaîne de provenance, record de relation, labels épistémiques, identifiants canoniques, nom du graphe, pré-enregistrement haché) | GELÉ |
| I3 | **4 documents finaux** : explicatif · technique (celui-ci) · propositions/écartés · plan d'implémentation | GELÉ |
| I4 | Ordre : **gel → documents → implémentation** | GELÉ |

## 6.10 Bloc J — Soumission & conformité

| # | Décision | Statut |
|---|---|---|
| J1 | Inscription + dépôt : gérés par l'équipe ; correspondance avec les organisateurs traitée (confirmations du 14/10, §4.4) | GELÉ |
| J2 | Portefeuille testnet : **aucun argent réel** — robinets publics gratuits ; clé jetable détruite après ; procédure dans le kit de démonstration | GELÉ |
| J3 | Kit de démonstration : **GO — en construction** | GELÉ |

## 6.11 Points restants (non bloquants, défauts proposés)

1. Plafond de budget API : **20 $/mois** (défaut). 2. Détenteurs des clés du coffre de démonstration 2/3 : responsable + 2 (défaut). 3. Signature de `P(obligation)` : responsable d'équipe (défaut). 4. Durées de vie : intention **15 min**, approbation **2 h** (défauts). 5. Fenêtres des périodes calmes d'évaluation : bornes exactes à figer au lancement de l'évaluation.

---

# 7. Périmètre v1 — ce qui commence juste après ce document

Le gel est fait ; les documents sont écrits ; **l'implémentation commence**. Voici la liste précise de ce qui est construit, dans l'ordre d'attaque (chaque lot est démontrable par une commande et un artefact) :

**Lot 1 — Le socle d'agents et la mémoire interne** (bloc A) : module agents (orchestrateur, explorateur, critique) avec appels d'API épinglés (fichier de configuration versionné + test de fumée) ; table `agent_journal` + magasin de contenus hachés ; application des budgets (4 compteurs) et des 5 conditions d'arrêt ; registre d'outils v1 ; banc anti-injection ; branchement des deux modes de rejeu.

**Lot 2 — Le graphe v1** (bloc B) : record de relation 17 champs + énumération des 34 relations + tests de conformité (types sujet/objet) ; horloges (`valid_from/valid_to`, `ts_published`) et requêtes « as-of » à deux filtres + test de l'invariant PIT ; ajout `source_family_id` + `extract_method` ; contrat de tests des 8 requêtes noyau sur les épisodes mesurés ; recherche sémantique d'appoint (si le budget le permet, sinon déclarée absente).

**Lot 3 — La décision généralisée** (bloc C) : record d'hypothèse 12 champs + cycle 7 états + checklist de falsifiabilité ; mécanisme RDOF + comparaison à l'ordre fixe ; format d'abstention enrichi + table ESCALATE/NO-ACTION ; catalogues d'actions (8+4) ; dossier 3 axes ; double convention de prix et H_class inscrits dans le gel d'évaluation.

**Lot 4 — La politique v1** (bloc D) : `policy_v1.yaml` + version + empreinte embarqués dans chaque verdict ; les règles ajoutées par le set v1 (fonction scopée, exposition/solde, fraîcheur, pause, alignement, budget) + tests associés (frontière de période, décimales, rejeu par contenu, solde/plancher, pause, dérive) ; test de dérive (étage hors-ligne en intégration continue + étage live) ; flux d'approbation EIP-712 (TTL 2 h) ; runbook d'incident opérationnel.

**Lot 5 — L'exécution autonome bornée** (bloc E) : service signataire isolé (préflight 12 contrôles, envoi sérialisé, retries bornés, confirmations, machine d'états) ; vérification de reçu durcie (unicité du journal de transfert, empreinte du reçu, codes de non-conformité) ; les 5 runs de démonstration ; script de re-vérification des adresses ; rappel des deux USDC dans le runbook.

**Lot 6 — L'audit et le vérificateur** (bloc F) : branchement des 3 flux + manifeste + liaisons + sceau ; paquet 12 pièces ; vérificateur T10 (8 calculs classe A, contrôles B, 6 mutations, cas dégradés, double distribution) ; publication de l'empreinte (obligatoire) ; ancrage public si les 3 conditions sont vertes, sinon reporté sans regret.

**Lot 7 — L'évaluation** (bloc G) : modules perte + comparateurs + calibration (test de référence BS = 0,10) ; registre de fenêtres DEV/EVAL + vérificateur d'embargos ; **5-10 prévisions gelées sur DEV** avant la date limite (elles seront « non conclusionnelles » mais réelles) ; gel G1–G6 haché ; premier rapport de calibration squelette.

**Lot 8 — L'interface de démonstration** (bloc H) : écrans 1–9 en lecture seule (rejeu journal) + page d'audit existante enrichie (refus, quarantaines) ; en-têtes de sécurité si exposition ; préparation vidéo **quand l'interface est stable** (report assumé).

**Ordre et dépendances** : 1 → 2 → 3 sont séquentiels (l'agent lit le graphe, la décision lit les deux) ; 4 et 6 peuvent avancer en parallèle des précédents sur leurs parties pures (règles, vérificateur) ; 5 dépend du montage testnet (wallet financé — côté équipe) ; 7 dépend du gel (déjà fait) et se parallélise tôt (modules indépendants) ; 8 ferme la boucle. **Définition de « v1 terminée »** : les 5 runs exécutés et vérifiés ; le paquet d'audit vert hors-ligne (8/8 + 6/6 mutations) ; l'empreinte publiée ; le rapport DEV + Brier à effectif réel publié avec ses limites ; 0 action hors enveloppe sur toutes les exécutions ; suite de tests verte (aucun échec, aucun saut ajouté).

---

# 8. Limites assumées et hors-v1

**Limites structurelles (elles ne disparaissent pas avec plus de code)** :

1. **Le kill switch n'annule pas une transaction déjà incluse** et ne court-circuite pas la mémoire des nœuds ; la protection réelle est le plafond (le dommage par bloc est borné) et la fenêtre courte décision→envoi.
2. **Les prix de testnet ne sont pas des données de marché** (mesuré : deux étages de frais du même couple cotant 4 674 et 2 479 au même instant). La démonstration prouve le **chemin d'exécution**, jamais la qualité d'exécution ; l'économie est simulée sur données réelles.
3. **Aucune performance financière n'est revendiquée** : pas de rendement, pas de « perte évitée » non conditionnée, pas de supériorité prédictive — l'évaluation le mesurera ou dira « non conclusionnel ».
4. **Le texte des LLM n'est pas reproductible** (non-déterminisme d'inférence documenté) ; la reproductibilité repose sur le journal des réponses, pas sur « même modèle, même prompt ». Aucun paramètre de graine n'est documenté chez les fournisseurs consultés.
5. **Les garanties sur événements rares sont trompeuses par construction** : la classe d'intérêt (rupture de peg) est minoritaire ; seules des couvertures conditionnelles par sous-population sont publiées, jamais une garantie globale.
6. **Un oracle peut être faux malgré un reçu parfait** : l'audit prouve l'intégrité et la correspondance, pas la véracité. Contre une falsification coordonnée interne, seule l'empreinte publiée (et l'ancrage public quand il est vert) apporte une ancre externe.
7. **Le mode de défaillance « reorg »** est géré par politique (2 blocs en démo ; tags safe/finalized en production) et escalade humaine — pas par un mécanisme infaillible.
8. **La valeur d'information (VoI) n'est pas activée** : l'ordonnancement peut renvoyer `VOI_NOT_ESTIMABLE` ; la VoI n'est jamais un point de défaillance.

**Hors périmètre v1 (documenté, avec condition de réouverture naturelle)** :

| Élément | Statut | Condition de réouverture |
|---|---|---|
| Échange et approbation de jetons exécutés (pas seulement simulés) | V2 | conditions on-chain écrites + testées par attaque + vérification de reçu spécifiée |
| Prêt Aave (fourniture/retrait/remboursement) | V2 | montage multi-étapes + signature déployée re-vérifiée le jour J |
| Module de délai on-chain pour la classe « hors enveloppe » | V2 | non testé sur Base Sepolia à ce jour |
| Prédiction de liens par réseaux de neurones de graphe, plongements de nœuds, complétion | Post-concours | protocole pré-enregistré, masquage sans fuite, baseline de comparaison |
| GraphRAG / index documentaire massif | Post-concours | maintenance amont ; provenance à reconstruire |
| Base PostgreSQL + recherche vectorielle en production | Post-concours | migration contenue dans le store |
| Ancrage public systématique (registre d'attestations) | Conditionnel | 3 conditions vertes (§5.7.5) |
| Banques / institutions (conformité, custodian, multi-chaînes complet) | Phase 2 | table de relations déjà en place (§5.3.2, `REGULATED_BY`) |
| VoI (EVPI/EVSI) dans la boucle | V2 | probabilités gelées + calibrées, test d'acceptation |
| Enregistrement de l'invariant inter-chaînes « destination » | Chantier | archive L2 gratuite non résolue à ce jour (bloqueur identifié) |
| Approbations dans l'interface (V1.5) | V1.5 | après l'interface lecture seule |
| Alerting produit multi-canal | V2 | canal à trancher |
| Historique de carnet d'ordres (profondeur) sur places centralisées | Non calculable avec les sources actuelles | source payante ou approximation par trades — non nécessaire à la v1 |
| Cibles chiffrées de desks (Sharpe, drawdown) | [NON TROUVÉ] | aucune source publique ; nous n'en inventons aucune |
| Distribution publique de scénarios de dépeg / `P(obligation)` | [NON TROUVÉ] | hypothèse signée en attendant, sensibilité publiée |

**Écartés explicitement (avec la raison)** : base graphe embarquée archivée par son éditeur (support nul) ; base graphe SaaS (seconde base à synchroniser, zéro bénéfice à notre échelle) ; RDF comme stockage (vocabulaire d'export seulement) ; sources payantes (Kaiko, CoinGecko Pro, Dune payant) — aucun besoin de la v1 ; télémétrie fournie par un tiers (l'exploitant du module exécute, il n'alerte pas — la télémétrie est **notre** apport).

---

# 9. Glossaire complet

**Abstention (A1–A5)** — décision de ne pas conclure : A1 entrée manquante, A2 contradiction non résolue, A3 décision non identifiable sous budget, A4 hors enveloppe/politique, A5 convention de mesure ambiguë. Toujours produite avec la liste de ce qui manque et de ce qui changerait le verdict.
**ACH (analyse d'hypothèses concurrentes)** — discipline : énumérer les hypothèses (y compris minoritaires), chercher à les **réfuter**, conserver les preuves pour et contre, évaluer la sensibilité. ORVYREN en garde la discipline, pas le format matriciel.
**`agent_journal`** — journal append-only de la mémoire interne des agents (réflexions, plans, propositions, coûts), séparé du graphe, chaîné par hash, jamais lu par le moteur de décision.
**Allowance** — mécanisme de plafond d'accumulation on-chain : un montant rechargeable par période, consommé à l'exécution. Un plafond d'accumulation n'est pas un plafond glissant strict (d'où le compteur hors chaîne).
**Ancrage** — publication ou inscription d'une empreinte dans un support externe (matériel de soumission, registre d'attestations public) pour dater et figer une version. Prouve l'intégrité et la datation, **pas la véracité**.
**A0 / A1 / A2 / B0** — comparateurs d'évaluation : A0 = ne rien faire ; A1 = règle de seuil ; A2 = l'agent ORVYREN ; B0 = placebo apparié (mêmes actions, horodatages tirés au hasard, M ≥ 200). AX0 = règle historique du dépôt. O = oracle ex post faisable.
**Brier (score de)** — `(1/N) Σ (p−y)²` : qualité d'une série de prévisions probabilistes. Décomposable en fiabilité, résolution, incertitude.
**CALME (fenêtre)** — fenêtre sans stress (critère mécanique : écart au peg < 0,5 % sur toute la fenêtre) servant à mesurer les faux signaux et la friction.
**Calibration** — accord entre probabilités annoncées et fréquences observées. « Calibré » est un mot contrôlé : N ≥ 100 + 5 conditions ; sinon « non conclusionnel ».
**Catalogue d'actions** — liste fermée et versionnée des actions bornées par persona (8 trésorerie, 4 desk), chacune avec déclencheur, bornes, coût, effet attendu, applicabilité on-chain.
**Claim (affirmation)** — énoncé dérivé d'observations (ex. « décote > 1 % pendant 12 h »), porté par le graphe avec provenance et statut.
**Contradiction** — relation explicite entre deux constats incompatibles. Jamais fusionnée ni effacée ; non résolue, elle bloque la conclusion.
**DEV / EVAL** — jeux de développement (réglages permis) et d'évaluation (une exécution, après gel, sous embargo). Séparés par 4 embargos.
**Double verrou** — (1) politique déterministe hors LLM ; (2) permissions on-chain votées. L'agent exécute seul **dans** l'enveloppe ; la limite survit à sa compromission.
**Dossier de décision** — l'objet d'une page (md + html auto-haché) qui réunit verdicts (3 axes), faits discriminants, calculs, budget, prévision gelée et provenance. Point de jonction des trois flux.
**Drift test (test de dérive)** — vérification exécutable que la politique hors chaîne ≡ (ou ≤) l'enveloppe on-chain ; 10 contrôles ; échec ou impossibilité ⇒ SAFE MODE.
**ECE (erreur de calibration attendue)** — moyenne des écarts de calibration par intervalle, à 10 intervalles **fixes gelés d'avance** ; jamais d'intervalles re-découpés après coup.
**EIP-712** — standard de signature de données structurées (utilisé pour l'approbation humaine : la signature lie identifiant, empreinte d'intention, version de politique, expiration).
**Embargo** — règle interdisant de toucher aux paramètres (après première exécution EVAL), d'utiliser les 24 h précédant une fenêtre EVAL en DEV, d'inspecter les fenêtres EVAL avant gel, et de calibrer sur les mois d'évaluation (calibration croisée).
**Enveloppe** — l'ensemble des permissions bornées accordées à l'agent sur la chaîne (cibles, fonctions, conditions, plafonds, quota d'appels), voté et révocable par les propriétaires.
**Escalade (ESCALATE)** — remise documentée à un humain : action hors enveloppe, information introuvable par les instruments, ou intégrité en échec. Distincte du NO-ACTION documenté.
**Fail-closed** — en cas d'état illisible, incohérent ou indisponible, le système refuse l'action (ne suppose jamais que tout va bien).
**Fait porteur** — fait qui peut déclencher une décision : exige vérification on-chain, ou document officiel, ou deux familles de sources indépendantes.
**Graphe (de connaissance financier typé)** — le dépôt append-only des faits, entités et relations horodatés et sourcés d'ORVYREN ; chaque relation est un record à 17 champs, chaque fait porte ses horloges.
**H_class** — horizon court de classification des prévisions : 6 h.
**Horloges (temporelles multiples)** — les horodatages distincts portés par chaque fait : événement, publication, observation, validité, révision. La décision n'utilise que le connaissable (intersection).
**Idempotence** — garantir qu'une intention ne s'exécute pas deux fois : registre persistant par identifiant **et** par empreinte de contenu.
**INV-AUTH** — invariant d'autorisation : rejeu, redémarrage et expiration ne recréent pas de budget ; politique et intention exactes liées au reçu.
**INV-DEPENDENCE** — deux canaux issus de la même famille d'archive ne comptent jamais comme deux confirmations.
**INV-INTEGRITY** — une preuve déterminante invalide ne produit jamais d'action ; toute altération d'un artefact casse une chaîne de hachage.
**INV-PIT (point-in-time)** — modifier le futur, ou publier une correction après coup, ne change pas une décision passée ; une donnée non admissible à l'instant de la décision est exclue.
**Intention (intent)** — l'objet borné que l'agent propose (chaîne, compte, action, actif, montant en chaîne décimale, destinataire, fonction, paramètres, expiration, idempotence, provenance). Ce n'est pas du calldata : la construction du calldata vient après l'autorisation.
**Kill switch (K0–K3)** — les leviers d'arrêt : K0 pause hors chaîne (immédiate) ; K1 retrait du rôle (1 transaction) ; K2 désactivation du module ; K3 asphyxie du gaz.
**MA-B** — topologie multi-agent gelée : orchestrateur + critique adversarial sur 2ᵉ modèle, instances séparées, journaux propres, budgets durs.
**Manifeste** — l'objet de clôture d'un run : têtes et compteurs des trois flux, versions, RPC et blocs, inventaire des fichiers. Sceau de jonction (liaisons + empreinte du manifeste).
**ML-1 / ML-2** — ML implémenté en v1 hors chemin décisionnel : ML-1 = recherche sémantique (embeddings) ; ML-2 = anomalies statistiques du graphe (règles déterministes, étiquetées « inféré par modèle »).
**Outcome (résultat)** — la résolution observée d'une prévision gelée à son horizon, écrite après coup par un résolveur déterministe (ou un opérateur attesté, publié séparément).
**P(obligation)** — hypothèse explicite sur la probabilité qu'une obligation de paiement survienne pendant la fenêtre ; signée, gelée, avec sensibilité publiée. Aucune source publique : c'est une hypothèse, pas une estimation calibrée.
**Paquet d'audit** — le livrable vérifiable : 12 pièces (README, dossier, décision machine, extras, 3 flux, manifeste, reçus/politique, vérificateur gelé, empreintes, ancrage optionnel), zippé, empreinte publiée.
**PIT (point-in-time)** — voir INV-PIT. Sur la chaîne, l'instant exact est le bloc.
**Politique (verrou 1)** — le service déterministe hors LLM qui applique les 14 règles, émet un verdict et des codes stables, et porte sa version et son empreinte.
**Préflight** — les 12 contrôles avant toute signature (verdict, chaîne, expiration, idempotence, pause, module, adresses, nonce, soldes, gaz, simulation, estimation). Un seul échec bloque.
**Prévision gelée** — énoncé futur haché et signé avant l'issue, avec critère de résolution et horizon ; une prévision non gelée n'entre dans aucun calcul.
**Provenance (chaîne de)** — Source → Observation → Extraction → Affirmation → Relation → Hypothèse → Prévision → Résultat ; chaque flèche est une ligne de lien stockée. Aucun chiffre sans remontée à une source horodatée.
**RDOF (recherche discriminante ordonnée par falsification)** — le mécanisme de recherche v1 : 5 règles déterministes, réfutation d'abord, coût mesuré ; s'arrête quand la décision est stable ou le budget épuisé.
**Receipt (reçu)** — la preuve d'exécution on-chain (statut, bloc, journaux d'événements), croisée champ à champ avec l'intention. Il prouve l'action, pas la décision.
**Record de relation** — l'enregistrement à 17 champs qui décrit une relation du graphe (famille, type, extrémités, mécanisme, signe, conditions, statut épistémique, cycle de vie, validation, horloges, provenance, extraction, chaîne, confiance, charge utile).
**Rejeu (REPLAY-JOURNAL / REPLAY-ARCHIVE)** — les deux modes officiels : relecture bit-à-bit du journal (aucun réseau) ; ou recalcul sur données archivées à version épinglée (« même décision, texte différent »). Marquage obligatoire ; un rejeu ne signe jamais.
**Runway (jours de roulage)** — nombre de jours de dépenses couverts par la trésorerie ; unité naturelle de la perte pour une DAO (référence : 44 932 $/jour).
**SAFE MODE** — état de la politique en cas de dérive d'enveloppe ou de vérification impossible : refus de toute action autonome, tout journalisé ; les lectures et dossiers restent permis.
**Signer** — le service isolé qui détient la clé d'exécution, reçoit un verdict déjà tranché et ne signe qu'un ALLOW ; séparé du LLM, du graphe et de la politique.
**Snapshot (du graphe)** — empreinte SHA-256 stable des lignes courantes + compteurs, figée par décision et référencée dans le dossier.
**Statut épistémique** — les 7 étiquettes d'une affirmation : fait vérifié, rapporté, statistique, causal documenté, causal hypothèse, inféré par modèle, rejeté. Conservé dans **chaque** document qui cite l'affirmation.
**T10 (essai du vérificateur)** — l'essai au cœur de la promesse : un tiers recalcule sans réseau chaque calcul déterminant ; toute mutation détectée ; zéro référence pendante.
**Testnet** — Base Sepolia : la chaîne d'exécution de la démonstration (acceptée par les organisateurs) ; aucun argent réel ; clé jetable.
**Triple mémoire** — graphe (faits), journal d'agents (raisonnement), journal d'exécution (chaîne) + le dossier qui les joint. Aucun mélange, une seule direction d'écriture.
**ULID** — identifiant unique trié par temps, utilisé par tous les objets (décisions, journaux, relations, approbations).
**Valeur retenue / valeur réalisable** — ce que l'oracle retient contre ce qu'une vente (ou sortie) produirait réellement pour la taille de la trésorerie. Le cœur du problème ORVYREN.
**VoI (valeur d'information)** — le gain espéré d'une recherche avant de la payer ; hors v1 (interface, `VOI_NOT_ESTIMABLE` autorisé), testée contre l'ordre fixe avant activation.
**Wilson (bornes de)** — intervalle de confiance d'une proportion, utilisé partout où un « 0 échec » pourrait être surinterprété (0/6 ≠ 0 %).
**Zodiac Roles (module de permissions)** — le standard on-chain des permissions granulaires pour coffres multi-signatures (portée par fonction, conditions, allowances, quota d'appels), révocable par le propriétaire ; adopté par la cible du projet.

---

# 10. Sources publiques

Toutes les sources ci-dessous ont été consultées le **15 octobre 2026** (sauf mention de date contraire). Chaque fait de ce document adossé à une source renvoie à cette liste par son contenu.

**Marchés et épisodes de référence**

1. Réserve fédérale (FEDS Notes) — *In the Shadow of Bank Runs: SVB and Stablecoins* — 17/12/2025 — https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html
2. Chainalysis — *Inside the KelpDAO Bridge Exploit* — 23/04/2026 — https://www.chainalysis.com/blog/kelpdao-bridge-exploit-april-2026/
3. Galaxy Research — *KelpDAO/LayerZero Exploit Drains $290m* — 22/04/2026 — https://www.galaxy.com/insights/research/kelpdao-layerzero-exploit-defi
4. Rapport d'incident rsETH (gouvernance Aave) — 20/04/2026 — https://governance.aave.com/t/rseth-incident-report-april-20-2026/24580
5. Jump Crypto — *The Depegging of UST* — https://jumpcrypto.com/resources/the-depegging-of-ust
6. Nansen / CoinDesk — liens Terra ↔ stETH — 29/06/2022 — https://www.coindesk.com/business/2022/06/29/nansen-casts-blame-for-steth-de-peg-on-terra
7. ENS DAO — IPS 6.46 (politique d'investissement) — 08/05/2026 — https://discuss.ens.domains/t/6-46-social-2026-endowment-investment-policy-update/22106
8. Revue KPK H1 2026 de l'Endowment ENS — 14/08/2026 — https://discuss.ens.domains/t/kpk-h1-2026-review-for-the-ens-endowment/22358

**Décision, incertitude, calibration**

9. Heuer — *Psychology of Intelligence Analysis* — CIA, 1999 — https://cia.gov/resources/csi/static/Pyschology-of-Intelligence-Analysis.pdf
10. CIA — *A Tradecraft Primer* — 03/2009 — https://cia.gov/resources/csi/static/Tradecraft-Primer-apr09.pdf
11. Mandel, Karvetski & Dhami — *Boosting intelligence analysts' judgment accuracy* — Judgment and Decision Making 13(6), 11/2018 — DOI 10.1017/S1930297500006628
12. *Effects of task structure and confirmation bias* — Cognitive Research 9:37, 13/06/2024 — DOI 10.1186/s41235-024-00560-y
13. *Automated Hypothesis Validation with Agentic Sequential Falsifications* — arXiv:2502.09858, 14/02/2025
14. *Accurate but Not Humble* (humilité épistémique des agents) — arXiv:2610.12360, 08/10/2026
15. Chow — *On Optimum Recognition Error and Reject Tradeoff* — IEEE Trans. Inf. Theory, 1970 — DOI 10.1109/tit.1970.1054406
16. *Machine learning with a reject option: a survey* — Machine Learning 113, 29/03/2024 — DOI 10.1007/s10994-024-06534-x
17. *Cost-Sensitive Conformal Prediction and Human-in-the-Loop Abstention* — arXiv:2607.27143, 29/07/2026
18. Brier — *Verification of forecasts expressed in terms of probability* — Monthly Weather Review 78(1), 1950
19. Murphy — *A New Vector Partition of the Probability Score* — J. Appl. Meteor. 12(4), 1973 — DOI 10.1175/1520-0450(1973)012<0595:ANVPOT>2.0.CO;2
20. Naeini, Cooper & Hauskrecht — *Obtaining Well Calibrated Probabilities* — AAAI 2015 — https://ojs.aaai.org/index.php/AAAI/article/view/9602
21. Wilson — *Probable Inference* — JASA 22(158), 1927 — DOI 10.1080/01621459.1927.10502953
22. Gneiting & Raftery — *Strictly Proper Scoring Rules* — JASA 102(477), 2007 — https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf

**Temporalité, graphes, stockage**

23. Kulkarni & Michels — *Temporal features in SQL:2011* — SIGMOD Record, 12/2012 — https://sigmod.org/publications/sigmodRecord/1209/pdfs/07.industry.kulkarni.pdf
24. Fowler — *Bitemporal History* — 07/04/2021 — https://martinfowler.com/articles/bitemporal-history.html
25. PostgreSQL 19 (beta) — tables temporelles — https://www.postgresql.org/docs/19/ddl-temporal-tables.html
26. PostgreSQL — requêtes de graphe SQL/PGQ — EDB, 18/02/2025 — https://enterprisedb.com/blog/representing-graphs-postgresql-sqlpgq
27. pgvector — https://github.com/pgvector/pgvector (v0.8.6)
28. W3C — PROV-O (recommandation 30/04/2013) — https://www.w3.org/TR/prov-o/
29. Zep/Graphiti — mémoire temporelle d'agents — arXiv:2501.13956, 2025 — https://github.com/getzep/graphiti
30. Kuzu — archivage du projet — The Register, 14/10/2025 — https://theregister.com/software/2025/10/14/kuzudb-graph-database-abandoned-community-mulls-options/1142229
31. Neon (offre gratuite) — https://neon.com/pricing ; Render (expiration du PostgreSQL gratuit) — 20/05/2024 — https://render.com/changelog/free-postgresql-instances-now-expire-after-30-days-previously-90
32. GLiNER — https://github.com/urchade/GLiNER · REBEL — EMNLP 2021 Findings — https://aclanthology.org/2021.findings-emnlp.204.pdf · LangExtract — https://github.com/google/langextract
33. Microsoft GraphRAG (mode maintenance) — https://github.com/microsoft/graphrag · HippoRAG 2 — arXiv:2502.14802 · DeFiGuard — arXiv:2406.11157

**Instruments on-chain et sécurité**

34. Zodiac — guide du modificateur de délai — https://docs.zodiac.eco/developers/delay/guide
35. Zodiac Roles — post-mortem de juin 2026 (Gnosis Guild) — engineering.gnosisguild.org
36. Safe — transactions à signatures hors chaîne — https://docs.safe.global/core-api/transaction-service-guides/transactions
37. Fireblocks — fenêtres d'expiration des approbations (5 min–24 h ; politique : 7 j) — https://support.fireblocks.io/hc/en-us/articles/360015963760
38. Tenderly — destinations d'alertes — https://docs.tenderly.co/monitoring/alerts/destinations/overview
39. Attestations : contrats EAS sur Base/Base Sepolia — https://github.com/coinbase/verifications (table des pré-déploiements) ; https://docs.attest.org
40. Banque des règlements internationaux (BIS) — *Payments in the age of AI agents* (C. Waller), discours du 05/10/2026 — https://www.bis.org/speeches/20261005-payments-age-ai-agents ; version Réserve fédérale — https://www.federalreserve.gov/newsevents/speech/waller20260928a.htm

**Concurrence et marché des agents (positionnement)**

41. Openfort — *Agent wallets in 2026* — 13/09/2026 — https://openfort.io (analyse de neuf plateformes)
42. QuillAudits — risques des portefeuilles d'agents (injection de prompt, clés de session) — 29/08/2026 — https://quillaudits.com
43. Chaos Labs — oracles de risque sous limites pré-approuvées — 26/11/2024 et 03/07/2025 — https://chaoslabs.xyz
44. LlamaRisk — oracle de risque en production (« bounded role », méthodologie publiée) — 2026 — https://llamarisk.com
45. *DeXposure-Claw* (supervision humaine, résolution hebdomadaire) — arXiv:2606.19501, 17/06/2026
46. *Policy Decision Record* (journal de décision auditable — chantier ouvert) — arXiv:2601.04583, 08/01/2026

**Modèles et reproductibilité**

47. DeepSeek — tarifs et modèles (page officielle, consultée le 15/10/2026) — https://api-docs.deepseek.com/quick_start/pricing ; limites — https://api-docs.deepseek.com/quick_start/rate_limit
48. MiMo (Xiaomi) — tarifs et modèles (consultés le 15/10/2026) — https://mimo.mi.com/docs/price/pay-as-you-go ; poids ouverts MIT — https://mimo.mi.com/docs/en-US/news/latest/v2-6
49. Alternatives tarifaires vérifiées : Zhipu/Z.ai — https://docs.z.ai/guides/overview/pricing ; Moonshot/Kimi — https://platform.kimi.ai/docs/pricing/chat ; MiniMax — https://platform.minimax.io/docs/guides/pricing ; Alibaba Model Studio — https://alibabacloud.com/help/en/model-studio/model-pricing
50. Thinking Machines — *Defeating Nondeterminism in LLM Inference* — 10/09/2025 — https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference ; *The Token Not Taken* — arXiv:2606.08998, 08/06/2026
51. Mémoire multi-agents (problème ouvert de cohérence) — arXiv:2603.10062 (09/03/2026) ; gouvernance des mémoires partagées — arXiv:2606.24535 (23/06/2026)
52. LangGraph — persistance et rejeu — https://docs.langchain.com/oss/python/langgraph/persistence

---

## Note finale

Ce document est la **référence technique de la v1 gelée le 15 octobre 2026**. Il a été écrit pour être lu seul : chaque chiffre est mesuré et reproductible depuis le dépôt, chaque affirmation externe est sourcée (URL + date), chaque décision est datée et chaque limite est écrite au lieu d'être cachée. Ce qui n'y est pas n'est pas dans la v1. Toute révision suit le protocole de gel (§5.5.6) : une nouvelle version datée et hachée, jamais une modification silencieuse.

*Fin du document.*
