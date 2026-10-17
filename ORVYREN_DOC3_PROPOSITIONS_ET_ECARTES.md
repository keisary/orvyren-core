# ORVYREN — PROPOSITIONS, ÉCARTÉS & HORIZON V2
### Document 3/4 — la mémoire des refus, des pistes et des conditions de réouverture

**Version 1.0 — 15 octobre 2026.** Compagnon du gel v2 (`FREEZE_V2.md`) et du document 1 (« ORVYREN en clair »).
**Objet** : rassembler **toutes** les propositions issues des recherches — autres utilisateurs possibles (banques, équipes de trading), améliorations classées V2, et **tous les éléments écartés qui restent pertinents** pour une amélioration future. Rien ici n'est livré pour la v1 : ce document est un **horizon**, pas un plan de travail directement exécutable (le plan d'implémentation est le document 4/4).

---

## Comment lire ce document

Deux natures d'énoncés, toujours distinguées :

| Étiquette | Signification |
|---|---|
| **[RÉSULTAT SOURCÉ]** | Constat établi par une recherche : source externe (URL + date) ou mesure interne reproductible. Ce n'est pas une opinion de l'équipe. |
| **[PROPOSITION]** | Idée d'amélioration, non validée, non gelée. Elle n'engage rien tant qu'un essai ou une décision d'équipe ne l'a pas fermée. |
| **[NON TROUVÉ]** | Ce qu'on a cherché sans le trouver. Écrit pour ne pas être comblé par une invention. |
| **[HYPOTHÈSE]** | Valeur ou paramètre posé par l'équipe, faute de source publique — toujours signalé comme tel. |

Chaque entrée écartée porte **quatre informations obligatoires** : *ce qu'elle apporte* · *pourquoi elle n'est pas en v1* · *quand la rouvrir* · *coût estimé*.

---

# 1. INTRODUCTION — STATUT ET PROCÉDURE

## 1.1 Ce que ce document n'est pas

- Ce n'est **pas** un gel : rien de ce qui suit n'est décidé. Les décisions de la v1 vivent dans `FREEZE_V2.md` ; ce document n'en contredit aucune.
- Ce n'est **pas** une liste d'idées en vrac : chaque entrée a été extraite des études de recherche du projet (les neuf études de bloc B1 → B8/B9, les rapports R1–R3, les recherches utilisateurs U1/U2, la recherche problème P1, les chantiers de la vague 2 W2-A → W2-E, le registre d'hypothèses).
- Ce n'est **pas** une promesse de feuille de route : certaines propositions pourraient être abandonnées définitivement, et ce serait un résultat légitime (une hypothèse réfutée est un acquis).

## 1.2 Le principe qui structure l'horizon : *écarté ≠ rejeté*

Trois raisons expliquent la quasi-totalité des reports, et il faut les distinguer parce qu'elles se rouvrent différemment :

1. **La contrainte de temps** (concours : soumission le 20/10/2026, finale annoncée 21–23/11/2026). Un report de calendrier se rouvre dès que le calendrier change — c'est la catégorie la plus facile à rouvrir. Exemples : second épisode d'évaluation, interface produit complète, cession simulée.
2. **La contrainte de démonstrabilité** (la démo doit être jouable hors-ligne, sans dépendance payante, sans tenir le rôle d'un tiers — voir `FREEZE_V2.md` §5–6). Un report pour cause de démonstrabilité se rouvre quand la brique devient testable sur testnet, ou quand le produit sort du cadre de la démo. Exemples : mandat on-chain, ancrage permanent, service de signature non exportable.
3. **La contrainte épistémique** (la discipline du projet : rien d'appris n'entre dans le chemin confirmatoire ; un modèle **propose**, le pipeline déterministe **dispose**). Un report de cette catégorie est le plus **lent** à rouvrir : il exige un essai pré-enregistré, un critère de succès fixé **avant**, et un résultat publié même s'il contredit l'équipe. Exemples : extension ML du graphe, ordre de recherche appris, calibration continue des seuils.

## 1.3 Ce que la v1 gèle, et qui ne se rediscute pas ici

Pour éviter toute confusion : ce qui suit est **gelé** au 15/10/2026 (référence : `FREEZE_V2.md`) et n'est donc **pas** proposé à la réouverture dans ce document — les entrées correspondantes n'apparaissent ici qu'en tant que **conséquences** (ce que le gel laisse de côté).

- **Agents** : multi-agent réel minimal (orchestrateur + critique adversarial, processus distincts) ; deux modèles par API ; critique sur 2ᵉ modèle dès la v1 ; mémoire interne append-only séparée du graphe ; budgets par décision ; rétention intégrale du journal.
- **Graphe** : catalogue de 34 relations / 4 familles + record enrichi ; SQLite pour le concours, PostgreSQL en cible ; ML v1 limité (recherche sémantique d'appoint + anomalies hors chemin décisionnel) ; rien d'appris dans le confirmatoire.
- **Décision** : discipline de falsifiabilité, réfutation d'abord ; mécanisme déterministe (« quel prédicat réfute le leader au moindre coût ») testé contre un ordre fixe **avant** toute activation de la valeur de l'information ; abstention de première classe ; 8 actions DAO + 4 actions desk ; double convention de prix ; horizon de classification à 6 h.
- **Politique** : 14 règles, codes de refus stables, fail-closed ; approbation par file + signature EIP-712 en démo, file multi-rôles + Safe en produit ; asymétrie réduire/augmenter ; kill switch à deux niveaux ; ancrage public de politique **reporté post-concours**.
- **Exécution** : signer de démo = clé jetable (jamais dans le dépôt, détruite après) ; librairie isolée ; plafonds de démonstration ; swap et approbation **simulés** ; Aave en v2 ; après réorg, escalade humaine ; deux jetons de test distincts nommés.
- **Audit** : journal à trois flux chaînés + paquet de pièces + empreinte ; vérificateur tiers ; empreinte publiée **obligatoire**, ancrage on-chain **conditionnel** ; textes « ce que l'audit prouve / ne prouve pas » figés.
- **Évaluation** : jeux de développement et d'évaluation séparés, embargo ; comparateurs A0/A1/A2/B0 ; fonction de perte + comparateurs + calibration à livrer ; prévisions gelées avant l'ouverture du jeu d'évaluation.
- **UI & Ops** : interface v1 en lecture seule ; hébergement **entièrement local** pour commencer ; préparation vidéo reportée.
- **Gouvernance** : protocole de décision écrit (ADR + registre + paquet haché ; registre en vigueur : `docs/decisions/README.md` — ADR-0001 gel · ADR-0002 politique v1 · ADR-0003 recherche sémantique → V2) ; aucun nom propre du système amont dans les documents finaux — concepts repris et **redéfinis en propre** ; quatre documents finaux ; ordre gel → documents → implémentation.

## 1.4 Comment on rouvre une proposition (procédure opposable)

Toute contestation d'une décision acceptée est instruite par un **document de décision de révision** qui répond **par écrit** aux quatre questions :

1. **Qu'est-ce qui dépend de cette décision ?** — liste des documents, décisions et modules impactés.
2. **Qu'est-ce que ça coûte de changer ?** — jours de travail, budget d'appels de modèles, re-tests, re-gel.
3. **Qu'est-ce qui est vérifiable ?** — si la réponse est « oui », on écrit un **essai pré-enregistré** : critère de succès fixé **avant** l'exécution, résultat publié **même s'il contredit** l'équipe.
4. **Quelle preuve nous ferait changer d'avis ?** — la condition de falsification, écrite à l'avance.

**Conditions de réouverture — une seule suffit à ouvrir une révision :**

| # | Condition | Exemple concret |
|---|---|---|
| **R1** | Un essai pré-enregistré mesure un résultat **contraire** à la décision | Le mécanisme déterministe fait moins bien que l'ordre fixe sur ≥ 3 fenêtres → la discipline de recherche est revue |
| **R2** | Une **faille** de sécurité ou un incident (chaîne, clé, injection) | Un refus contourné par un calldata mal décimé → le banc d'attaques et la politique sont revus |
| **R3** | La **contrainte externe** change (règlement du concours, date, coût d'un fournisseur) | Un hébergeur gratuit change ses conditions → la décision d'hébergement est rouverte |
| **R4** | Le **coût de changement** est ré-estimé et devient faible (< 1 jour) | Une bibliothèque standard couvre désormais le besoin sans travail supplémentaire |
| **R5** | Le **responsable du gel** ouvre la révision explicitement | Décision d'équipe assumée et datée, avec justification écrite |

**Sans R1–R5, on ne rouvre pas.** C'est la règle qui protège les derniers jours avant la soumission — et qui, après le concours, garantit que chaque réouverture a une raison écrite plutôt qu'une envie.

**Deux disciplines de forme** (à tenir dans tout ce qui suit) :

- **Toute révision est datée et versionnée** — jamais une réécriture silencieuse. Une version antérieure reste lisible. Le journal des variantes inclut même les révisions **ratées**.
- **Une entrée sans condition de réouverture écrite est une entrée incomplète.** C'est le critère de qualité principal de ce document.

---

# 2. AUTRES UTILISATEURS POSSIBLES

## 2.0 Vue d'ensemble des candidats

La recherche utilisateur a départagé trois familles, puis écarté ou reporté plusieurs pistes. Le tableau donne le verdict et la raison décisive ; les sections suivantes détaillent chaque piste.

| Piste | Verdict | Raison décisive (une ligne) |
|---|---|---|
| **Trésoreries d'organisations on-chain** (protocoles, DAO, fonds) | **Retenue — cible n°1 de la v1** | Tout son périmètre est public on-chain : un agent peut réellement lire, vérifier et agir. |
| **Équipes de trading crypto** (desks, teneurs de marché, fonds) | **Retenue — cible secondaire** | Besoin identifié (la « jambe on-chain » de l'exécution sous limites), mais les grandes firmes construisent en interne. |
| **Banques & institutions financières** | **Reportée — phase 2 (2027-2028)** | Marché réel et industrialisé, mais données sur registres permissionnés, supervision humaine imposée, cycles d'achat longs. |
| **Régulateurs / superviseurs** | **Écartée comme client — conservée comme destinataire de la valeur** | Ils déclarent manquer de métriques et de données ; ce n'est pas un acheteur, c'est la preuve d'une demande institutionnelle. |
| **Grand public / particuliers** | **Écartée** | Profils de la première version abandonnés : aucun des mécanismes du système (provenance, borne, abstention) n'a de valeur perçue par un particulier. |
| **Prop firms & plateformes d'évaluation** | **Écartée** | L'automatisation par API et robots y est déjà la norme ; peu de traction pour un agent on-chain. |
| **Entreprises non crypto / PME (trésoriers)** | **Reportée — non priorisée** | Rôle modélisé comme acteur observé, pas comme acheteur : aucune preuve documentée de disposition à payer. |
| **[PROPOSITION] Assurance / risk transfer** | **Non instruite** | Aucune source trouvée sur un porteur de risque qui voudrait payer pour une décision vérifiable ; à ne pas présenter sans preuve. |

---

## 2.1 Banques et institutions financières — synthèse chiffrée

### Ce que la recherche a établi [RÉSULTAT SOURCÉ]

L'étude des acteurs bancaires (chantier « étude des acteurs bancaires », 15/10/2026) documente une industrialisation **réelle** mais **récente**, et des volumes qui restent modestes :

| Fait mesuré | Chiffre | Source + date |
|---|---|---|
| Production réelle de tokenisation chez l'infrastructure post-marché américaine | > 30 firmes participantes (BNP Paribas, BlackRock, Goldman Sachs, J.P. Morgan, State Street, Société Générale, Circle, Nasdaq, CME…) ; service de tokenisation lancé en octobre 2026 | Communiqué DTCC, 15/07/2026 — `https://www.dtcc.com/press-releases/2026/dtcc-turns-tokenization-into-reality` |
| Volume traité par l'infrastructure de règlement | 4,7 quadrillions $ de transactions titres (2025) ; 114 T$ sous garde / asset servicing | Communiqué DTCC, 15/07/2026 (même source) |
| Pilote fondateur collatéral / appels de marge | 14 nœuds, 100 transactions exécutées (dont **appels de marge satisfaits en temps réel**, retours de marge, close-out) | PRNewswire, 23/09/2024 — `https://www.prnewswire.com/news-releases/dtcc-and-digital-asset-complete-successful-pilot-to-test-collateral-and-margin-optimization-through-tokenization-302255589.html` |
| Dépôts tokenisés institutionnels | > 7 Md$ / jour en moyenne, > 4 000 Md$ cumulés depuis le lancement | Forbes, 28/07/2026 — `https://www.forbes.com/sites/digital-assets/2026/07/28/americas-biggest-banks-are-building-one-deposit-token-history-is-the-hard-part/` |
| Règlement de repo intraday | 5 Md$ le premier mois, puis jusqu'à 1 Md$/jour | The Block, 07/08/2025 ; confirmé par le rapport ICMA *DLT and repo, Part I*, juin 2026 |
| Essais de monnaie de banque centrale | 64 participants de marché, ~1,6 Md€ réglés | BCE, rapport de juin 2025 — `https://www.ecb.europa.eu/press/pubbydate/2025/html/ecb.exploratoryworknewtechnologies202506.en.html` |
| Prototype multi-devises (banques centrales + institutions) | ~800 000 CHF, 17 scénarios (9 000 à 125 000 CHF) en test « valeur réelle » (juillet 2026) | BIS — `https://www.bis.org/project/agora` (page mise à jour le 27/05/2026) |
| Règlement en monnaie de banque centrale de titres tokenisés (zone euro) | Lancement de la solution le 21/09/2026 ; mise en œuvre complète prévue 2028 | Banque de France, 21/09/2026 — `https://www.banque-france.fr/en/press-release/eurosystem-brings-central-bank-money-tokenised-finance` |
| Intention institutionnelle | ~60 % des investisseurs institutionnels interrogés prévoient d'augmenter leur allocation ; exposition moyenne attendue ×2 en trois ans | State Street, *2025 Digital Assets Outlook*, 09/10/2025 |

**En une phrase, ce que la recherche conclut** : en 2025-2026, les grandes banques ne font pas de finance décentralisée ; elles industrialisent (1) la garde régulée, (2) les jetons de dépôt et stablecoins de règlement, (3) la tokenisation du collatéral et des flux post-marché — sur des rails **permissionnés ou semi-publics** (registres privés, réseaux à confidentialité sélective), avec des pilotes réels mais des volumes encore modestes.

### Pourquoi ce n'est pas la cible de la v1

Quatre freins, tous documentés :

1. **La donnée est invisible.** Un jeton de dépôt institutionnel est **permissionné** et réservé à des clients identifiés ; une partie des conversions de titres a lieu sur un réseau **privé**. Un agent qui ne lit que le public on-chain est **structurellement aveugle** sur une grande partie du périmètre bancaire. *C'est le critère décisif du projet : la donnée d'abord.*
2. **La supervision humaine est imposée.** Le règlement européen sur l'intelligence artificielle impose, pour les systèmes à haut risque, une supervision humaine effective et une double vérification dans certaines catégories (article 14 et annexe III) ; applicabilité générale des obligations principales annoncée au 02/08/2026. Un rapport du Conseil de stabilité financière (14/11/2024) ajoute : dépendances tierces, corrélations de marché, risque de modèle et gouvernance des données — les cadres existants « pourraient ne pas être suffisamment complets ». Conséquence : l'institution ne délègue **jamais** la décision d'exposition, l'appétit au risque, ni les clés.
3. **Tout outil externe devient un tiers à contractualiser.** La résilience opérationnelle numérique (règlement européen applicable depuis le 17/01/2025) impose un **registre des arrangements contractuels avec les tiers** et un droit d'audit, d'interruption et de sortie. Un agent externe doit accepter ce cadre avant de vendre quoi que ce soit.
4. **Le cycle d'achat est incompatible avec une démonstration de concours.** Ventes longues, comités, pilotes encadrés : ce n'est pas un premier client pour un système livré en quelques jours.

### Ce qu'elle apporte quand même (trois cas d'usage défendables)

Trois cas d'usage sont **documentés par des preuves réelles**, et constituent le meilleur gabarit de ce qu'ORVYREN sait faire :

| Cas d'usage | Ce que l'agent ferait | Preuves de la douleur |
|---|---|---|
| **UC1 — Collatéral & appels de marge** | Surveiller l'éligibilité d'un panier préapprouvé, anticiper et honorer les appels de marge, substituer et retourner du collatéral, journaliser pour l'audit | Workflows d'appels de marge et de clôture testés (23/09/2024) ; nantissement de collatéral et workflows de marge en **production** (15/07/2026) ; repo intraday jusqu'à 1 Md$/jour (07/08/2025) |
| **UC2 — Trésorerie tokenisée multi-chaînes** | Allouer et déplacer la trésorerie tokenisée entre chaînes et venues de garde pour honorer les fenêtres de règlement, sous plafonds par chaîne et par actif, avec réconciliation | Dépôts tokenisés permissionnés pour le règlement 24/7 (17/06/2025) ; plateforme à > 7 Md$/jour (28/07/2026) ; stablecoins d'entreprise sur trois chaînes (10/06/2025 et 20/02/2025) |
| **UC3 — Veille on-chain & réaction de contrepartie** | Surveiller les risques de premier ordre (perte d'ancrage, gel d'adresses, suspension de réseau, anomalie de réserves), appliquer un **playbook défensif préapprouvé**, sinon escalader | Fragilité des stablecoins documentée par la banque des règlements internationaux (29/06/2025) ; pouvoir de blocage/sanctions prévu par la loi américaine sur les stablecoins de paiement (18/07/2025) ; infrastructure multi-chaînes (15/07/2026). **Honnêteté : aucun incident public 2025-2026 ne montre une banque ayant laissé un système automatisé réagir seul à une perte d'ancrage — ce cas est extrapolé, non observé.** |

### Quand la rouvrir, et à quelles conditions

**Fenêtre de réouverture : phase 2 (2027-2028)**, avec un **coin d'entrée dès 2026** : présenter les trois cas ci-dessus comme **gabarit de l'enveloppe bornée** (c'est le meilleur argument de vision devant un jury), en réservant le déploiement bancaire à la phase suivante.

**Conditions de crédibilité** (toutes doivent être vraies) :

1. L'agent s'intègre aux **interfaces de garde et de registre existantes** (plateformes de custody, réseaux d'entreprise) — jamais d'accès direct aux clés, jamais une dépendance au seul réseau public.
2. Enveloppe bornée **vérifiable** : listes blanches d'actifs, de contreparties et de chaînes ; plafonds ; fenêtres horaires ; **double validation au-dessus d'un seuil** ; kill switch ; journal d'audit exportable.
3. Positionnement **opérations** (collatéral, marge, trésorerie, veille) — jamais « décision d'investissement ».
4. Séquence imposée : **observation / proposition d'abord**, exécution ensuite par paliers — la seule séquence qu'un responsable des risques acceptera.
5. **Partenaire d'entrée** : un fournisseur d'infrastructure ou un bac à sable de régulateur, pas une vente directe en salle de marché.

**Coût estimé du chantier** : élevé. Les trois conditions qui pèsent le plus sont l'intégration aux registres permissionnés (partenariat, plusieurs semaines de travail d'intégration), la conformité (dossier tiers, auditabilité) et la preuve de conformité à la supervision humaine. À l'échelle du concours : **non engageable** ; à l'échelle produit : un chantier de plusieurs mois conditionné à un partenaire.

---

## 2.2 Équipes de trading crypto (desks, teneurs de marché, fonds) — en détail

### Ce que la recherche a établi [RÉSULTAT SOURCÉ]

Le second persona est **retenu à la marge** : la v1 développe deux personas avec des objectifs distincts, mais le desk reste la **cible secondaire** et son traitement reste volontairement plus léger.

| Fait | Détail | Source + date |
|---|---|---|
| Le risque est déjà structuré comme une enveloppe | Une des firmes étudiées décrit un « moteur de risque » qui surveille l'exposition en continu et **fait respecter des limites**, avec un poste de responsable du risque couvrant le trading (spot et dérivés), la trésorerie et les investissements, « y compris les expositions à travers les environnements centralisés **et** décentralisés » | Fiche de poste publique (étudiée le 15/10/2026) |
| Les grandes firmes construisent en interne | Les teneurs de marché majeurs recrutent pour **construire et mettre à l'échelle** leurs systèmes de gestion du risque | Offres d'emploi publiques (15/10/2026) |
| La vitesse est la variable critique | > 19 Md$ de liquidations en ~1 jour, 1,6 M de comptes touchés (10/10/2025) ; marchés bloqués à 100 % d'utilisation (avril 2026) | Presse financière + rapport d'incident, 2025-2026 |
| Budgets d'outillage | **NON TROUVÉ** : aucun chiffre public de budget d'un desk pour ce type d'outil dans la matière collectée | — |

### Ce que ce persona apporte au projet

1. **Un second jeu d'objectifs et de critères** : rentabilité (P&L net après frais, glissement et financement), asymétrie de l'aller-retour, coût du capital — c'est-à-dire une lecture **économique** du même système, là où la trésorerie lit une lecture **de protection**.
2. **Un cas d'usage concret et borné** : la « jambe on-chain » de l'exécution (liquidité décentralisée, coffres, couverture, règlement) sous limites d'exposition codées et en 24/7.
3. **Une preuve de généralité** : le même mécanisme de décision bornée, avec une autre fonction de perte — l'argument le plus utile contre « votre système ne marche que pour un cas ».

### Ce que la recherche énumère comme actions bornées du persona desk [RÉSULTAT SOURCÉ]

Quatre actions bornées ont été définies pour le persona desk (contre huit pour la trésorerie) — réduction d'exposition, protection, gestion d'inventaire, sortie de position risquée — chacune avec son déclencheur épistémique, son seuil économique, ses bornes et son coût. Les métriques associées : P&L net, regret par fenêtre, drawdown maximal, ratio de Sharpe **avec borne basse** (et non un point), avec la règle « aucune supériorité statistique revendiquée » sur un échantillon aussi petit.

### Pourquoi ce n'est pas la cible principale de la v1

1. **Concurrence interne** : les grandes firmes construisent leur moteur de risque ; elles n'achètent pas un « cerveau » de trading.
2. **P&L invisible** : la valeur d'une réduction d'exposition se prouve par un regret mesuré, pas par une attribution claire — un desk compare un coût d'outil à un alpha qu'il croit détenir.
3. **Conformité** : une licence d'établissement impose un cadre documentaire que le produit devrait alimenter — travail non fait en v1.
4. **Contrainte de temps** : deux personas v1 avec deux protocoles de mesure, c'est déjà le maximum ; le desk reste traité en **second** si le temps le permet.

### Quand la rouvrir

- **À la marge** : dès que la v1 du persona trésorerie est démontrée (même fonction de décision, autre fonction de perte — c'est un changement de paramètres, pas d'architecture).
- **Pour de bon** : quand deux conditions sont réunies — (a) le protocole de mesure *forward* (publication de décisions avant résultat) a tourné au moins une fois ; (b) un acheteur est identifié : les **fonds et desks plus petits** qui n'ont pas d'équipe de risque dédiée, plutôt que les grandes firmes.

**Coût estimé** : le volet « mesures et fonction de perte desk » est **déjà spécifié** dans la recherche sur les objectifs et la mesure ; le coût résiduel est l'implémentation du harnais (compté dans le lot évaluation de la v1) et la production des deux P&L (hors et avec coût de financement). Pour un déploiement commercial réel : coût de conformité non chiffré et **NON TROUVÉ** dans la littérature publique.

---

## 2.3 Autres candidats écartés, et pourquoi

| Candidat | Ce qu'il apportait | Pourquoi écarté / reporté | Quand rouvrir | Coût |
|---|---|---|---|---|
| **Grand public / particuliers** — écarté | Un marché large, une démonstration facile (une interface, un bouton) | Les profils grand public de la première version ont été **abandonnés** au profit de trois familles d'organisations : la valeur du système (provenance recalculable, abstention motivée, enveloppe bornée) est une valeur **institutionnelle** — un particulier n'achète ni la traçabilité ni le refus | Jamais comme client principal ; un mode « consultation » (lecture seule) resterait un produit d'appel, et **aucun élément de recherche ne le justifie** aujourd'hui | Nul tant que non rouvert ; l'ouvrir créerait un coût d'interface et de support qu'aucune preuve ne finance |
| **Plateformes d'évaluation / comptes propres** — écarté | Un modèle économique clair (capital simulé, partage de profits), des interfaces de programmation ouvertes | L'automatisation par interface et robots y est déjà la **norme** (matière brute : « peu de traction pour un agent on-chain ») ; sortir du périmètre on-chain ferait perdre exactement ce qui distingue le projet | Non prévu | Faible techniquement, élevé en perte de positionnement |
| **Régulateurs / superviseurs** — écarté comme client, conservé comme **destinataire** | La preuve d'une **demande institutionnelle documentée** : plusieurs autorités ont nommé le problème et déclaré manquer d'**outils de mesure** (« données on-chain et off-chain », « lacunes de surveillance », « surveillance supplémentaire justifiée » pour les stablecoins, contrats autonomes qui « canalisent et amplifient la contagion » — note de la Réserve fédérale, 17/12/2025) | Un superviseur n'achète pas un agent d'exécution : il veut des métriques et des sources. Le servir demanderait un autre produit (tableaux de bord, indices de risque), hors périmètre | Si un axe « données et métriques » devient un produit à part — ce qui suppose un cadre de licence de données aujourd'hui **NON TROUVÉ** | Non chiffré |
| **Entreprises non crypto / PME (trésoriers)** — reportée, non priorisée | Un besoin universel : protéger une trésorerie exposée à un actif numérique | Elles figurent dans la recherche comme **acteurs à modéliser** (observés par le système), pas comme acheteurs ; aucune disposition à payer documentée ; et le critère « donnée d'abord » joue contre elles — leur exposition n'est pas observable publiquement | Si un segment (importateurs/exportateurs, trésoriers détenant des stablecoins) devient documentable, par exemple via une exigence de reporting | Inconnu ; **NON TROUVÉ** |

**Ce que ces écartements ont en commun** : à chaque fois, ce n'est pas la technique qui bloque mais **la donnée** (exposition non observable), **la valeur perçue** (ce que l'acheteur reconnaît comme un problème), ou **le positionnement** (ce que le produit serait obligé de devenir). C'est la même grille qui a retenu la trésorerie d'organisation on-chain comme cible n°1.

---

# 3. PROPOSITIONS PAR BLOC DU SYSTÈME

Neuf blocs : **A** agents · **B** graphe · **C** décision · **D** politique · **E** exécution · **F** audit · **G** évaluation · **H** interface & opérations · **I** gouvernance. Chaque entrée suit la même forme : *idée & apport* · *pourquoi pas en v1* · *quand rouvrir* · *coût*.

## A — Agents

### A.1 Équipe multi-agents complète (quatre agents en services séparés)

| | |
|---|---|
| **Idée & apport** | Passer de deux instances (orchestrateur + critique) à **quatre agents** en processus/services distincts — planificateur, explorateur, critique, rédacteur — avec un protocole de messages explicite et un arbitre. Démonstrabilité forte du caractère « multi-agent » ; séparation nette des rôles ; possibilité de faire tourner l'exploration en parallèle.
| **Pourquoi pas en v1** | Coût multiplié : environ **30 appels de modèle par décision**, soit ~3× la forme retenue (0,013–0,036 $ par décision) ; **risque de cohérence élevé** — quatre journaux à réconcilier, problème ouvert dans la littérature citée par l'étude ; la latence perçue en démonstration devient élevée ; enfin la v1 gelée écarte explicitement le multi-agent parallèle non borné. |
| **Quand rouvrir** | Quand un essai à **budget de calcul égal** montrera un gain net : comparer « un second critique » à « une seconde passe du même modèle ». C'est exactement l'hypothèse déjà enregistrée sur la valeur d'un second critique. La voie est préparée : la forme retenue impose que **chaque rôle écrive dans son propre journal** et que la communication passe par des **objets sérialisables** — passer à l'équipe complète ne demanderait alors aucune refonte. |
| **Coût** | +2 à 4 jours pour la forme intermédiaire (deux instances) ; ~5 à 8 jours pour l'équipe complète, plus le budget d'appels. Source : étude du bloc agents §1.3–1.5 et §9 (proposition MA-A/MA-B/MA-C). |

### A.2 Modèles auto-hébergés (locaux) à la place des interfaces payantes

| | |
|---|---|
| **Idée & apport** | Exécuter les modèles sur une machine de l'équipe plutôt que via une interface facturée à l'appel. Coût marginal nul après installation ; indépendance vis-à-vis d'un fournisseur et d'une coupure réseau ; aucune donnée ne sort de la machine.
| **Pourquoi pas en v1** | Aucune infrastructure matérielle garantie le jour de la démonstration ; temps de mise en place et de quantification non planifié ; et le besoin réel de la démo — **fonctionner hors-ligne** — est déjà couvert autrement : le mode de rejeu depuis le journal archivé rend la démonstration indépendante d'un accès réseau. |
| **Quand rouvrir** | Si le budget d'appels devient un obstacle réel (le plafond par défaut est de 20 $/mois), ou si un client exige que **rien** ne sorte de son périmètre — argument de souveraineté des données. |
| **Coût** | Élevé et matériel : dépend du modèle visé (quantification, mémoire, vitesse). Non chiffré dans les recherches ; à estimer avant toute décision. |

### A.3 Orchestration avancée (rôle explorateur séparé, arbitre, reprise de plan)

| | |
|---|---|
| **Idée & apport** | Ajouter un rôle d'exploration autonome séparé, un arbitre de désaccord entre agents, et la reprise de plan en cas d'échec d'outil. Exploration plus large, meilleure gestion des impasses, désaccords tracés et arbitrés.
| **Pourquoi pas en v1** | Le budget par décision est un **garde-fou de simplicité** (bornes d'appels, d'outils, de temps et de coût, arrêt en cas d'échec) ; multiplier les rôles rend l'arrêt plus difficile à démontrer. La reprise après erreur existe déjà, classe par classe. |
| **Quand rouvrir** | En même temps que A.1 (l'équipe complète apporte naturellement le rôle d'exploration séparé) ; jamais avant que les journaux par rôle soient tenus. |
| **Coût** | Inclus dans le coût de A.1 si rouvert ensemble ; sinon 2 à 3 jours. |

### A.4 Repli automatique entre fournisseurs de modèles

| | |
|---|---|
| **Idée & apport** | Si le fournisseur principal échoue, basculer automatiquement sur le second (ou un troisième). Robustesse en démonstration et en production ; le mode « rejeu depuis le journal » rend le repli non critique **pour la démo**, mais indispensable pour un service continu.
| **Pourquoi pas en v1** | Non nécessaire à la démonstration (le rejeu hors-ligne couvre le cas de panne) ; le développement du repli (gestion des clés, des formats, des tests de fumée) n'apporte rien au jury et prend une journée. |
| **Quand rouvrir** | Dès qu'il y a un usage continu (surveillance permanente, service à un client), ou si le fournisseur principal annonce une indisponibilité. |
| **Coût** | ~1 jour ; plus le suivi (une clé par rôle, tests de fumée datés). Source : étude du bloc agents, question ouverte Q4. |

### A.5 Rédaction du dossier par un modèle de langage — **écarté**

| | |
|---|---|
| **Idée & apport** | Confier la rédaction du dossier de décision à un modèle au lieu du gabarit déterministe actuel. Style plus fluide, adaptation au lecteur.
| **Pourquoi écartée** | **Aucun gain, un risque net** : l'invariant fondateur est qu'aucun chiffre ne vient d'un modèle ; le dossier doit rester **recalculable** par un tiers. Un texte généré est plus difficile à vérifier et peut introduire des affirmations non sourcées. |
| **Quand rouvrir** | Uniquement comme **couche de présentation séparée** (résumé destiné à un humain, clairement étiqueté, ne remplaçant jamais le dossier de référence). |
| **Coût** | Faible (1 jour) mais bénéfice non démontré. |

### A.6 Banc d'attaques anti-injection étendu

| | |
|---|---|
| **Idée & apport** | Ajouter des cas d'essai où un document ou une donnée mise en cache contient des instructions, pour vérifier que l'agent ne les suit pas. Couverture du risque nommé comme principal pour les agents outillés en 2026 : l'injection par le contenu.
| **Pourquoi pas en v1** | Les essais existent au niveau de la politique (attaques pré-déclarées) mais pas encore au niveau des documents lus par l'agent ; le sujet est identifié comme **piste de critère sécurité** pour le concours, pas encore outillé. |
| **Quand rouvrir** | Dès que l'agent lit des documents externes (communiqués, rapports) — donc dès que la voie d'extraction documentaire est activée. |
| **Coût** | ~0,5 à 1 jour (jeu d'essai) ; le risque est réel et documenté pour la catégorie. Source : étude du bloc agents §5.6. |

## B — Graphe

### B.1 Base de graphe dédiée (moteur spécialisé) — **écartée pour la v1**

| | |
|---|---|
| **Idée & apport** | Stocker le graphe dans un moteur de base de données orienté graphe plutôt que dans des tables relationnelles. Requêtes de chemins natives, index d'arêtes, algorithmes de graphe intégrés.
| **Pourquoi écartée** | Trois constats **sourcés** : (1) le moteur embarqué le plus cité — **Kuzu** — a été **archivé le 10/10/2025** (équipe acquise par Apple ; installations existantes fonctionnelles, support amont arrêté), et les forks communautaires ne sont **pas matures** ; (2) un moteur en ligne gratuit plafonne à 200 000 nœuds / 400 000 relations — **inutile à notre échelle** (quelques milliers de nœuds en v1) et ajoute une **seconde base à synchroniser** ; (3) une base documentaire RDF serait un alignement d'export, pas un stockage. À l'inverse, une base relationnelle moderne propose depuis 2025 des **requêtes de graphe en SQL standard** (propriété-graphe) — les requêtes de chemins deviennent du SQL ordinaire, sans second moteur. |
| **Quand rouvrir** | Si le volume dépasse franchement les milliers de nœuds **et** que les requêtes de chemins deviennent le goulot ; évaluer alors le **fork actif** du moteur archivé (positionné « base graphe pour fichiers analytiques »), mais **hors trajectoire concours**. |
| **Coût** | Migration estimée ~1 à 2 jours après le concours (le point d'accès unique au magasin est déjà isolé, ce qui contenait la migration). Source : étude du bloc graphe §2 (matrice comparative, sources Kuzu/The Register 14/10/2025, offres d'hébergement consultées le 15/10/2026). |

### B.2 Chaîne de génération augmentée par la recherche (famille « GraphRAG »)

| | |
|---|---|
| **Idée & apport** | Indexer un corpus documentaire (dossiers, communiqués) en entités et communautés pour répondre à des questions larges sur le corpus. Réponses « globales » sur un grand corpus de documents, utiles à un agent de recherche.
| **Pourquoi pas en v1** | L'outil de référence de cette famille est **en maintenance depuis 2025** (plus de nouvelles fonctionnalités) ; l'indexation coûte cher (un appel de modèle par document) et doit être refaite à chaque ajout ; surtout, les entités et communautés **générées par un modèle** ont une provenance à reconstruire et un **risque de fuite confirmatoire** (le système pourrait « découvrir » une relation parce qu'elle est déjà dans le modèle, pas dans les faits). |
| **Quand rouvrir** | Pour la **couche documents** uniquement, et seulement quand l'extraction documentaire bornée sera stable : comparer alors l'outil de référence avec ses variantes actives (architectures légères, à mémoire épisodique, à index paresseux) sur un jeu d'essai tenu à l'écart. |
| **Coût** | Non chiffré ; dépend du corpus. À traiter comme un chantier de recherche appliquée, pas comme une amélioration de routine. Source : étude du bloc graphe §5.2–5.3 (état des dépôts consultés le 15/10/2026). |

### B.3 Réseaux de neurones sur graphe & prédiction de liens (dont temporels)

| | |
|---|---|
| **Idée & apport** | Apprendre à **deviner les relations manquantes** du graphe (par exemple un pont non enregistré, une exposition non déclarée) avant qu'elles ne cassent. Capacité d'alerte sur ce que la carte curatée ignore — la promesse la plus séduisante techniquement du dossier.
| **Pourquoi pas en v1** | C'est de la **recherche appliquée**, avec un précédent en finance décentralisée mais aucun déploiement standard ; l'entraînement et l'étiquetage demandent des jours ; le **risque de fuite temporelle est élevé** (un modèle entraîné sur la période évaluée triche sans le vouloir) ; et surtout, les sorties ne peuvent être que des **hypothèses** étiquetées comme inférées par un modèle — jamais des faits. Le gel v2 est explicite : rien d'appris dans le chemin confirmatoire. |
| **Quand rouvrir** | **Post-concours uniquement**, sous un protocole déjà pré-enregistré : masquage par périodes et par familles de relations (sans fuite), métriques doubles — précision@k **et** fraction d'inférences disposant d'une provenance complète —, budget de calcul **égal** à celui d'une règle simple, comparaison à des témoins triviaux (voisins communs, règles). Candidats : prédiction de liens temporels, familles classiques d'incorporation de graphe de connaissance. |
| **Coût** | ≥ 1 à 2 semaines ; dépend de la qualité de l'étiquetage. Source : étude du bloc graphe §5.2–5.3 et registre d'hypothèses (hypothèse « extension ML du graphe »). |

### B.4 Incorporations de nœuds (représentations vectorielles d'entités)

| | |
|---|---|
| **Idée & apport** | Représenter chaque entité par un vecteur appris pour mesurer des similarités et proposer des candidats de liens. Regroupements, détection d'entités proches, amorçage de la résolution d'entités.
| **Pourquoi pas en v1** | Les vecteurs ne sont **pas interprétables** : ils ne peuvent servir que de **générateur d'hypothèses**, jamais de preuve. En v1, la recherche sémantique d'appoint (voir B.5) couvre déjà le besoin de similarité sur les textes. |
| **Quand rouvrir** | Avec B.3, dans le même programme, et sous la même contrainte d'étiquetage. |
| **Coût** | Faible en calcul (petit graphe, processeur suffisant), mais le coût réel est la **validation** du protocole. |

### B.5 Recherche sémantique d'appoint (vecteurs + extension de base de données) — **retenue en v1, à étendre**

| | |
|---|---|
| **Idée & apport** | Retrouver des documents ou affirmations proches d'une requête, en s'appuyant sur une extension vectorielle de la base relationnelle. Un outil de documentation pour l'agent de recherche, et un **générateur de candidats** pour la résolution d'entités.
| **Pourquoi elle est déjà là** | Coût quasi nul en local, hébergement gratuit durable possible, et le résultat est une **liste de candidats** — la décision ne cite que des affirmations validées. C'est la seule brique apprise tolérée près du chemin de décision, et elle n'y produit jamais de chiffre. |
| **Ce qu'il reste à faire (V2)** | Étendre l'index au-delà des textes : indexer les **patrons d'épisodes** (« ce qui ressemble à avril 2026 ») pour accélérer la reconnaissance d'un nouvel incident. |
| **Quand rouvrir** | Dès que le volume de documents dépasse ce qu'un index lexical peut trier — c'est un seuil à mesurer, pas à supposer. |
| **Coût** | Extension de l'index : ~1 jour une fois la base migrée vers l'hébergement cible. |

### B.6 Multi-chaînes étendu (au-delà du périmètre gelé)

| | |
|---|---|
| **Idée & apport** | Étendre la couverture à d'autres réseaux (par exemple Arbitrum, Polygon) et à d'autres familles d'actifs (jetons de staking liquide additionnels, actifs tokenisés, actifs enveloppés). Couverture du vrai périmètre du risque : les incidents de 2026 viennent de **ponts et de configurations de vérification**, pas d'une seule chaîne.
| **Pourquoi pas en v1** | Le périmètre gelé est volontairement étroit (réseau principal + une chaîne d'exécution économique) ; chaque chaîne ajoutée demande sa lecture d'état, ses conventions d'adresses, ses tests. Le choix méthodologique est « **un** graphe, des **vues** multi-chaînes » — l'extension est donc additive, pas structurante. |
| **Quand rouvrir** | Quand le premier cas multi-chaînes sera reproductible de bout en bout (le gel prévoit déjà ce mode d'extension) : critère = un épisode dont la cause est inter-chaînes, rejoué avec deux vues. |
| **Coût** | 2 à 5 jours par chaîne ajoutée (connecteurs, qualité, tests), hors extension des jeux de données historiques. |

### B.7 Export formel des relations (vocabulaire standard de provenance)

| | |
|---|---|
| **Idée & apport** | Publier l'ontologie et l'export des relations dans un format d'échange standard (type provenance W3C), **en annexe**, sans l'utiliser comme stockage. Crédibilité auprès d'un lecteur technique (posture de standard), lisibilité pour un tiers.
| **Pourquoi pas en v1** | Aucun besoin fonctionnel ; l'export est un livrable de priorité faible, à faire **après** les pièces de soumission. |
| **Quand rouvrir** | Dès qu'un tiers (client, auditeur, partenaire) demande l'export ; ou au moment de la publication du dépôt. |
| **Coût** | ~0,5 jour. Source : étude du bloc graphe, recommandation R8. |

### B.8 Anomalies statistiques sur les **métriques du graphe** (sans apprentissage)

| | |
|---|---|
| **Idée & apport** | Surveiller le graphe **lui-même** : changement de degré, apparition d'un nouveau type d'arête, rupture de chemin, concentration soudaine. Détection d'une évolution anormale **de la structure de connaissance** (par exemple un nouveau pont qui apparaît dans le graphe de collatéral).
| **Pourquoi pas en v1** | Utile mais non démontré comme signal : aucune quantification du gain. À noter qu'il s'agit d'une **règle**, pas d'un modèle — donc entièrement traçable et compatible avec la discipline du projet. |
| **Quand rouvrir** | En même temps que l'extension du banc de signaux, si un épisode concret motive la règle. |
| **Coût** | Faible (une règle + un seuil versionné) ; ~0,5 à 1 jour. Source : étude du bloc graphe §5.2. |

## C — Décision

### C.1 Valeur de l'information complète (arrêt de recherche calculé)

| | |
|---|---|
| **Idée & apport** | Décider **combien** chercher en calculant la valeur d'une recherche avant de la lancer : ne chercher que ce qui peut changer la décision ; arrêter quand la valeur nette devient négative. Économie de recherche et défense intellectuelle (« nous savons ne pas chercher ») ; la littérature récente en fait la règle des agents cohérents bayésiens, avec un gain mesuré face à des seuils réglés à la main dans 18 conditions sur 20.
| **Pourquoi pas en v1** | La valeur calculée dépend de **probabilités crédibles**, que la v1 n'a pas encore (les branches sont qualitatives au départ) ; et une bibliothèque non validée sur nos propres fenêtres ne peut pas devenir un point de rupture de la démonstration. Le gel retient un mécanisme **déterministe** — « quel prédicat réfute l'hypothèse dominante au moindre coût » — testé **contre un ordre fixe**, derrière une interface unique. Tant que les conditions ne sont pas réunies, le service renvoie simplement « valeur non estimable » et le mécanisme déterministe prend la main **sans changer le résultat**. |
| **Quand rouvrir** | Trois conditions cumulatives : (a) des probabilités **gelées et calibrées** sur un nombre de cas suffisant (seuil à définir) ; (b) journalisation complète disponible ; (c) un essai concluant — la petite expérience de mécanique (« valeurs = énumération ; aucun outil inutile acheté ; budget respecté ») passée avec succès. Si l'essai échoue, **documenter l'abandon** : c'est aussi un résultat. |
| **Coût** | Moyen : le calcul d'arrêt peut être une bibliothèque standard ; ~2 à 4 jours avec l'essai et l'intégration derrière l'interface. Source : étude du bloc décision §b.3 ; rapport de recherche sur l'orchestration et la valeur de l'information. |

### C.2 Branches probabilisées et calibrées

| | |
|---|---|
| **Idée & apport** | Remplacer les branches qualitatives (probabilité vide) par des probabilités numériques dès que la calibration le permet. Comparabilité des hypothèses, calcul de valeur de l'information possible, mesure de qualité (score de Brier, décomposition fiabilité/résolution/incertitude, erreur de calibration attendue).
| **Pourquoi pas en v1** | « Une probabilité inventée dégrade la preuve. » La v1 travaille **qualitatif d'abord** : prévision **gelée avant** observation, scoring a posteriori, statut « non établi » sous un nombre insuffisant d'observations. Un modèle de langage ne produit **jamais** une probabilité dans le chemin de décision. |
| **Quand rouvrir** | En **séquence**, pas en débat : quand les prévisions gelées seront scorées et que le nombre de cas atteindra le seuil de calibration (de l'ordre de la centaine pour une courbe exploitable). Rien ne s'oppose à faire les deux — l'un après l'autre. |
| **Coût** | Faible techniquement (les métriques sont déjà spécifiées) ; le coût réel est **le temps de collecte** des observations. |

### C.3 Simulation de scénarios et tirages Monte-Carlo

| | |
|---|---|
| **Idée & apport** | Pondérer les décisions par un **jeu de scénarios** (réalisé, non-rétablissement à 48 h, guérison lente, venue unique contrainte…) avec des probabilités, plutôt que par un scénario unique. Une revendication **économique** distincte de la revendication de décision (espérance sur scénarios pondérés, en plus du regret par fenêtre) ; robustesse aux hypothèses. La pratique existe chez les fournisseurs de notation, qui annoncent par exemple **100 000 simulations Monte-Carlo par marché** (acquis par un acteur de données en septembre 2025).
| **Pourquoi pas en v1** | Le jeu de scénarios du persona desk doit être **gelé avec ses probabilités** — et aucune distribution publique de scénarios de perte d'ancrage n'existe : les probabilités seraient des hypothèses d'équipe. Le gel les confie à une **signature nommée** (le responsable du bloc mesure), avec **sensibilité publiée**. |
| **Quand rouvrir** | Avant l'ouverture du jeu d'évaluation, sous forme de gel ; puis à chaque révision majeure (nouvel épisode, nouvelle classe d'actifs). |
| **Coût** | ~0,5 jour pour la rédaction et la signature ; le calcul lui-même est du dénombrement, pas de la simulation lourde. Source : recherche sur les objectifs et la mesure §B.0–B.4 et §(f) points 7 et 11. |

### C.4 Apprentissage des seuils (calibration par quantiles)

| | |
|---|---|
| **Idée & apport** | Remplacer les seuils réglés à la main par des seuils **calibrés sur l'historique** : un percentile élevé déclenche l'alerte, un percentile très élevé déclenche la qualification d'épisode, avec contre-validation sur plusieurs épisodes et périodes de contrôle. Des seuils défendables, mesurés, reproductibles — et un taux de faux positifs chiffré (cible : moins de 1 % des heures, et moins de 0,1 % pour la détection d'épisode).
| **Pourquoi pas en v1** | Le plan de calibration dépend d'une **collecte de séries** (10 à 20 h) et surtout d'une discipline d'embargo ; le régler pendant la période d'évaluation invaliderait celle-ci. Les seuils v1 restent **provisoires** et documentés comme tels. |
| **Quand rouvrir** | Après le concours : exécuter le plan **mois par mois**. Garde-fous impératifs : jamais pendant qu'une fenêtre d'évaluation est ouverte ; ne jamais calibrer sur les mois réservés à l'évaluation ; chaque révision **rejoue d'abord** le jeu de développement (non-régression) puis re-gèle. |
| **Coût** | 10 à 20 h de collecte + 1 à 2 jours d'analyse ; chaque révision ultérieure ~0,5 jour. Source : chantier de compléments de signaux, §5. |

### C.5 Cession simulée et politique de ré-entrée

| | |
|---|---|
| **Idée & apport** | Modéliser une **vente réelle** (cession) et, pour le persona desk, une **ré-entrée** dans la même fenêtre, avec le coût complet de l'aller-retour. Elle répond à l'objection la plus forte contre la démonstration actuelle : **transférer un actif entre deux portefeuilles de la même entité ne réduit pas le risque d'émetteur**. Une cession simulée raconte une histoire économiquement vraie (avec coût de glissement et de sortie).
| **Pourquoi pas en v1** | Une action on-chain de cession (échange contre un actif plus sûr) demande une fonctionnalité d'échange qui n'est **pas exécutable** en v1 (échange et approbation restent simulés) ; et le marché exécutable en période de crise n'est pas mesuré (la profondeur s'effondre). |
| **Quand rouvrir** | Dès que la démonstration doit porter sur une **réduction de risque réelle** et non sur la chaîne de contrôle : c'est la voie recommandée (considérer la démonstration actuelle comme un test de la chaîne de contrôle **et** ajouter la cession simulée). |
| **Coût** | Inclus dans la fonction de perte et le harnais (~1 jour) ; l'exécution réelle d'un échange : voir E.3. |

### C.6 État explicite « sortie fermée » (distinct du prix)

| | |
|---|---|
| **Idée & apport** | Représenter la **fermeture de la sortie** (marché gelé, retraits bloqués) comme un état distinct du prix, et non comme une variation de prix. Fidélité à l'épisode de référence d'avril 2026 : le marché a été **gelé à la seconde près** avec un oracle qui affichait encore un prix. Un système qui ne voit que le prix croit pouvoir sortir ; un système qui voit la fermeture sait qu'il est **déjà trop tard**.
| **Pourquoi pas en v1** | Aucune série de profondeur d'exécution n'est disponible au pire de la crise des stablecoins (seuls les prix et les soldes de réserve l'ont été) ; l'état « sortie fermée » serait donc porté à la main, sans source systématique. C'est un chantier ouvert de la recherche sur les signaux. |
| **Quand rouvrir** | Quand la mesure de profondeur au pire de la crise sera faite (échelle `get_dy` sur les pools actifs pendant les fenêtres historiques). |
| **Coût** | ~1 à 2 jours de mesure + schéma ; dépend de la disponibilité des archives de contrats. |

### C.7 Multi-épisodes simultanés et budget de recherche partagé

| | |
|---|---|
| **Idée & apport** | Gérer plusieurs épisodes en cours en parallèle, avec un registre de branches global ou par cas, et un budget de recherche partagé. Réalisme opérationnel : en période de stress, plusieurs marchés cassent en même temps (avril 2026 : plusieurs protocoles en quelques heures).
| **Pourquoi pas en v1** | Le registre v1 est conçu **par cas** ; le partage de budget entre cas est une décision non tranchée (question ouverte documentée). |
| **Quand rouvrir** | Quand la surveillance continue deviendra un mode nominal (et non une démonstration sur un épisode rejoué). |
| **Coût** | ~1 à 2 jours (arbitrage de budget, ordonnancement d'épisodes). |

### C.8 Catalogues d'actions étendus (actions non démontrables)

| | |
|---|---|
| **Idée & apport** | Passer du catalogue restreint (transfert borné en démonstration, le reste simulé) à l'ensemble des actions décrites : échange, approbation, dépôt/retrait de prêt, remboursement, et les actions desk. Couverture produit complète ; une action passe de « simulée » à « exécutable » selon une règle explicite : conditions on-chain écrites **et testées par attaque**, vérification de reçu spécifiée, run de refus correspondant existant.
| **Pourquoi pas en v1** | Le gel est explicite : v1 = transfert borné ; échange et approbation **simulés** ; prêt en v2. Le catalogue se développe par paliers, jamais « parce qu'on a confiance ». |
| **Quand rouvrir** | Palier par palier, en respectant la règle de croissance (voir E.3 et E.4). |
| **Coût** | 1 à 3 jours par action (politique + vérification de reçu + tests). |

## D — Politique & autorisation

### D.1 Modificateur de délai (coffre-fort de temps) on-chain pour les actions hors enveloppe

| | |
|---|---|
| **Idée & apport** | Pour les actions hors enveloppe déjà décidées par des humains, utiliser un module de **délai** : la transaction est mise en file et ne s'exécute qu'après un temps de refroidissement, sauf annulation par le propriétaire. Une **fenêtre de réaction opposable on-chain**, sans dépendre de la confiance dans notre logiciel : chaque entrée produit des événements on-chain vérifiables ; l'annulation est une transaction du propriétaire.
| **Pourquoi pas en v1** | **Non testé sur le réseau de démonstration** ; sémantique **inverse** de celle du flux d'approbation (une entrée en file s'exécute *si personne ne s'y oppose*, tandis que notre flux attend une approbation **positive**) ; et c'est un module supplémentaire, donc une surface d'attaque à instruire. Le guide officiel recommande des temps de refroidissement de **1 à 7 jours** (« une heure est trop court pour une attaque de week-end »), incompatibles avec une démonstration en direct. |
| **Quand rouvrir** | Phase 2 / produit : après le flux d'approbation de la v1, en complément, pour la classe d'actions hors enveloppe. |
| **Coût** | Moyen : module + tests + run de démonstration ; ~2 à 3 jours. Source : étude du bloc politique §b.2–b.5 et chantier de l'enveloppe d'exécution §c.1. |

### D.2 Attestation publique de la politique (empreinte on-chain) — **reportée**

| | |
|---|---|
| **Idée & apport** | Publier une **attestation on-chain** de l'empreinte de la politique (version, code, plafonds) pour que l'état de l'enveloppe soit lisible par un tiers au moment de la décision. Rendre l'enveloppe **opposable et datée** sans avoir à faire confiance à nos fichiers ; un arc de provenance entre l'empreinte de politique, la décision et le reçu.
| **Pourquoi reportée** | Le gel est explicite : **reporté post-concours**. L'empreinte publiée (canal statique, coût nul) est **obligatoire** et suffit à la démonstration ; l'attestation on-chain est un **ajout additif** qui ne doit pas devenir un prérequis. |
| **Quand rouvrir** | Post-concours, dès que les conditions vertes sont réunies (run d'exécution réel effectué, vérificateur tiers vert). Coût quasi nul en gaz sur réseau de test. |
| **Coût** | ~1 jour (script + schéma + transaction). Source : étude du bloc audit §3 (option iii) et gel §4 (D5). |

### D.3 File d'approbation multi-rôles (séparation de tâches)

| | |
|---|---|
| **Idée & apport** | Séparer strictement **initiateur ≠ approbateur ≠ exécutant**, avec un quorum **par classe d'action** (une approbation pour une action standard ; un comité pour un changement d'enveloppe) et un service de niveaux de service (délais d'expiration, escalade). Conformité aux modèles organisationnels établis : les plateformes institutionnelles documentent des groupes d'approbation, une fenêtre d'autorisation configurable (5 minutes à 24 heures, défaut 2 heures) et des demandes de changement de politique expirant à 7 jours. Un régulateur a même décrit, en 2026, que les dispositifs agentiques devront **enregistrer les agents et journaliser les approbations**.
| **Pourquoi pas en v1** | La démonstration n'a qu'un approbateur ; la conception produit est écrite mais l'implémentation (rôles, quorum, escalade) n'est pas dans le périmètre. |
| **Quand rouvrir** | En produit (phase 1 trésoreries), dès qu'un client a plus d'un signataire — c'est-à-dire presque toujours. |
| **Coût** | ~2 à 3 jours (schéma, rôles, tests) ; les valeurs de délai sont déjà sourcées (précédents cités). Source : étude du bloc politique §b.5–b.6. |

### D.4 Module d'allocation du multisig standard — **écarté**

| | |
|---|---|
| **Idée & apport** | Utiliser le module d'allocation du coffre-fort multi-signatures le plus répandu pour donner une autorisation bornée à l'agent. Un mécanisme éprouvé, déjà utilisé dans l'écosystème.
| **Pourquoi écarté** | Il est **absent du réseau de démonstration** (vérifié : pas de bytecode sur Base Sepolia). Le déployer nous-mêmes signifierait « code audité, **déploiement non audité** » — un coût doublé pour une portée moindre. **À éviter dans le temps imparti.** |
| **Quand rouvrir** | Jamais en v1 ; si un client l'exige, préférer une voie déjà vérifiée. |
| **Coût** | Écarté pour cause de coût/risque ; le rouvrir impliquerait un déploiement à auditer. Source : rapport de recherche sur les permissions on-chain §7.3 point 6. |

### D.5 Garde on-chain (contrôle au-dessus du seuil multisig) — **écarté en v1**

| | |
|---|---|
| **Idée & apport** | Ajouter un contrôle on-chain qui applique des restrictions **au-dessus** du seuil multi-signatures. Un contrôle supplémentaire au niveau du compte.
| **Pourquoi écarté** | Un garde cassé peut provoquer un **déni de service du coffre-fort** (avertissement documenté dans les sources de sécurité des fournisseurs de coffre). L'introduire est un **engagement d'audit** qu'une démonstration de quelques jours ne peut pas honorer. |
| **Quand rouvrir** | Avec un audit dédié, en produit. |
| **Coût** | Élevé (audit) ; non chiffré. Source : étude du bloc politique §b.2 (option A) et rapport de recherche sur les permissions on-chain §5. |

### D.6 Banc d'attaques étendu (de 7 à 12)

| | |
|---|---|
| **Idée & apport** | Passer de sept attaques pré-déclarées à douze, en ajoutant : frontière de période (dépense doublée en limite de période), révocation en cours d'exécution, manipulation d'oracle, accumulation sur plusieurs transactions, calldata mal décimé. Couverture des attaques réelles contre les enveloppes bornées — dont une faille **documentée et reconnue** par les fournisseurs (jusqu'à 2× le budget autour d'une frontière de période). Publier une **borne supérieure** d'échec (borne de Wilson) au lieu de « 0 échec sur N ».
| **Pourquoi pas en v1** | Effort restant identifié comme priorité haute mais non engagé (~0,5 jour) ; la v1 communique sur les attaques déjà testées, avec la limite assumée. |
| **Quand rouvrir** | Avant la soumission si le temps le permet (recommandé) ; sinon immédiatement après, car c'est un argument de sécurité à faible coût. |
| **Coût** | ~0,5 jour + le coût de la rédaction des bornes. Source : axes d'amélioration (axe K) et rapport d'évaluation §B.6 item 9. |

### D.7 Budget de risque explicite par épisode et plafond de taille d'action

| | |
|---|---|
| **Idée & apport** | Introduire deux paramètres de politique : une **perte maximale par épisode** et un **plafond de taille d'action**, pour que la politique soit bornée par construction. Une politique dont l'exposition maximale est un paramètre explicite, auditable, plutôt qu'une conséquence implicite des plafonds unitaires.
| **Pourquoi pas en v1** | Aucune source publique n'énonce un tel plafond pour une trésorerie : les documents de politique des organisations interrogées imposent un **rapport** de baisse, pas un **plafond**. Le paramètre existerait donc sans ancrage. |
| **Quand rouvrir** | Quand un client fournira sa propre valeur — c'est un paramètre de mandat, pas un réglage interne. |
| **Coût** | ~0,5 jour (schéma + politique + tests). Source : recherche sur les objectifs et la mesure §(f) point 10 ; étude du bloc politique. |

## E — Exécution & porteur de clé

### E.1 Service de signature non exportable (module matériel, enclave, ou calcul multipartite)

| | |
|---|---|
| **Idée & apport** | Ne plus jamais mettre la clé en clair dans un processus : la clé vit dans un module matériel non exportable, une enclave, ou est **partagée** entre plusieurs parties (calcul multipartite), et l'agent appelle un service de signature. La clé ne sort jamais du périmètre protégé ; les appels de signature sont journalisés ; la rotation se fait par création de clé et réassignation du rôle. Les offres du marché documentent les trois familles : clés secp256k1 non exportables chez les fournisseurs d'infonuagique, enclaves matérielles avec moteur de règles, signatures réparties avec « première part » chez le signataire d'interface.
| **Pourquoi pas en v1** | La démonstration utilise une **clé jetable** en variable d'environnement, créée et **détruite** après la démonstration, avec des jetons de test gratuits — c'est la seule voie **démontrable sans dépendance payante** et dont la sécurité ne repose pas sur la promesse d'un tiers. Le gel assume cet écart **démo → production** et le documente. Point capital : ces options **déplacent** le problème « où est la clé » ; aucune ne remplace le second verrou (les permissions on-chain bornent ce qu'une clé volée peut faire). |
| **Quand rouvrir** | **Phase 1 produit (trésoreries)** : même architecture, backend de signature remplacé par un service non exportable — le critère de choix est simple : le client possède déjà un module matériel dans son nuage (option matérielle) ou veut une politique appliquée par le fournisseur (option enclave). L'adresse du signer reste un **membre de rôle** : la rotation est **une transaction**. **Phase 2 (institutions)** : signatures réparties quand la trésorerie dépasse le seuil où *personne* ne doit détenir la clé entière — chemin naturel pour la conformité. |
| **Coût** | ~2 à 4 jours par option (adaptateur, tests, rotation documentée) ; le choix dépend d'un fournisseur. Source : étude du bloc exécution §a.2 (quatre familles comparées, sources consultées le 15/10/2026). |

### E.2 Mandat on-chain borné (autorisation par la chaîne, type « permission périodique »)

| | |
|---|---|
| **Idée & apport** | Ajouter au-dessus de la politique hors chaîne une **permission bornée délivrée par la chaîne** : un montant par période (par exemple 300 unités sur 24 h), une expiration, une révocation native, une adresse de session pour l'agent. Ni l'agent ni un bug de la politique ne peuvent franchir ce plafond. La démonstration la plus forte du thème : **un refus prononcé par la chaîne elle-même** (transaction annulée, visible publiquement), la révocation en une transaction, et une autorité qui ne dépend plus de notre logiciel. Les contrats du standard retenu ont été **vérifiés présents sur le réseau de démonstration** (gestionnaire de délégation déployé, exécuteur déployé) ; un repli équivalent existe chez un autre fournisseur, entièrement scriptable côté serveur.
| **Pourquoi pas en v1** | Le standard est un **brouillon** (un changement de nom de méthode est possible d'ici la finale) ; l'octroi exige un portefeuille compatible **et un humain**, non automatisable en démonstration sans navigateur pilotable — c'est le risque n°1 du plan ; le compte de session doit payer le gaz (robinets plafonnés) ; et surtout **la permission n'est pas un limiteur instantané** : autour d'une frontière de période, jusqu'à **2× le budget en quelques secondes** — limite reconnue du mécanisme, à ne jamais présenter comme un plafond par transaction. Le gel retient donc : politique hors chaîne + file d'approbation signée en démonstration, permissions on-chain **reportées**. |
| **Quand rouvrir** | Dès que les trois conditions sont réunies : (a) un environnement navigateur pilotable ou le repli scriptable choisi ; (b) la matrice d'autorité gelée (quelle contrainte vit sur la chaîne, quelle contrainte vit dans la politique — le **désalignement est volontaire et doit être expliqué**) ; (c) une capture vidéo de secours enregistrée dès que ça marche. Ordre d'intégration chiffré : environ **4 à 5 jours-homme**, dont 1 jour de mise en place d'environnement. |
| **Coût** | ~4 à 5 jours (dont le repli ~1 jour). Source : rapport de recherche sur les permissions on-chain §7.1–7.3 (contrats vérifiés sur Base Sepolia le 14/10/2026). |

### E.3 Échange (swap) borné exécutable

| | |
|---|---|
| **Idée & apport** | Passer de l'échange **simulé** (devis + instruction préparée) à l'échange **exécuté dans l'enveloppe**, avec conditions on-chain sur le montant minimal reçu et le destinataire. La brique manquante de la cession réelle (voir C.5) : sans échange exécutable, on ne peut pas démontrer une **réduction de risque**, seulement une chaîne de contrôle.
| **Pourquoi pas en v1** | La faisabilité a été **mesurée** (la fonction d'échange existe et s'exécute sur le routeur déployé ; la variante avec date limite est **absente** du routeur — leçon de vérification consignée), mais l'échange reste sous approbation en v1, car il faut écrire les conditions on-chain (montant minimal, destinataire = l'entité) et les tester par attaque. |
| **Quand rouvrir** | Après l'approbation multi-rôles (D.3) ou le mandat on-chain (E.2) — c'est l'un des deux qui doit l'encadrer. |
| **Coût** | 1 à 2 jours (conditions + tests + vérification de reçu), hors la partie on-chain du mandat. |

### E.4 Prêt (dépôt / retrait / remboursement) en action de plein droit

| | |
|---|---|
| **Idée & apport** | Rendre exécutables les actions de prêt : déposer, retirer, rembourser. Couverture du mandat réel d'une trésorerie (la sortie d'une position prêtée est le geste de défense le plus courant).
| **Pourquoi pas en v1** | Le gel place le prêt en **v2**. Deux obstacles mesurés : le remboursement exige une dette préalable (montage multi-étapes) ; et la **signature réellement déployée** du remboursement diffère de la forme « v3 » attendue — le sélecteur usuel est **absent du bytecode** ; l'appel devra être construit sur la signature déployée, **revérifiée le jour J**. Le gel de l'enveloppe exige une position préalable. |
| **Quand rouvrir** | Après construction du scénario de démonstration avec position préalable (le montage est identifié). |
| **Coût** | 2 à 3 jours (dont un montage multi-étapes de scénario). Source : étude du bloc exécution §b.2–b.3 et annexe « sélecteurs : la leçon de vérification ». |

### E.5 Approbation d'allocation bornée (allowance) — spec à écrire

| | |
|---|---|
| **Idée & apport** | Exécuter une approbation **bornée** (montant exact, jamais infinie) vers un contrat autorisé — nécessaire à tout protocole qui tire des fonds. Débloque la plupart des actions de protocole (échange, prêt, coffre).
| **Pourquoi pas en v1** | La spécification d'approbation bornée est une **question ouverte** de l'étude : politique de remise à zéro, cumul, erreurs partielles, condition on-chain sur le couple (destinataire autorisé, montant). La v1 se contente de la **simuler**. |
| **Quand rouvrir** | Avec E.3/E.4 — c'est la même famille d'intents. |
| **Coût** | ~1 jour (spécification + politique + tests). |

### E.6 Clés d'accès (passkeys) pour l'approbation humaine

| | |
|---|---|
| **Idée & apport** | Utiliser l'authentification sans mot de passe (signature vérifiable on-chain via une précompilation standard) pour les approbations humaines et l'accès initial. Expérience utilisateur forte (biométrie) et vérification on-chain native.
| **Pourquoi pas en v1** | **Un agent n'a pas de biométrie** : la réserver au niveau d'approbation humaine (T3) et à l'accès initial, jamais au signataire autonome. Le gel ne l'incorpore pas. |
| **Quand rouvrir** | En produit, quand une interface d'approbation sera livrée (voir H.2). |
| **Coût** | ~1 à 2 jours (intégration côté interface) ; la précompilation est disponible sur le réseau ciblé. |

### E.7 Module de compte / validateur de session — **écarté en v1**

| | |
|---|---|
| **Idée & apport** | Faire de l'agent un **contrat** (module du coffre-fort, ou validateur d'un compte de nouvelle génération) plutôt qu'un porteur de clé. Plus de clé à voler ; logique de validation programmable.
| **Pourquoi écarté** | Les modules du coffre-fort ont, **par conception, les pleins pouvoirs du compte** — surface d'audit maximale ; et un compte de nouvelle génération changerait de socle si le client n'est pas équipé. Le critère d'élimination posé par la recherche est explicite : **toute option qui exigerait de donner à l'agent un droit d'administration doit être refusée.** |
| **Quand rouvrir** | Si un client impose un socle de compte programmable et finance l'audit d'intégration. |
| **Coût** | Élevé (audit de module) ; non chiffré. Source : étude du bloc exécution §a.2 (option C). |

## F — Audit, preuve & vérifiabilité

### F.1 Ancrage permanent du dossier (datation indépendante)

| | |
|---|---|
| **Idée & apport** | Publier sur une chaîne une **attestation** de l'empreinte du dossier de décision (un seul condensat de 32 octets), non révocable, lisible par n'importe qui. Datation et existence **indépendantes de l'équipe** : un tiers lit l'attestation et compare au digest recalculé. Coût quasi nul (fractions de millionième d'unité de gaz sur réseau de test) ; artefact cliquable pour un jury.
| **Pourquoi pas en v1 (en tout cas pas comme prérequis)** | Le gel retient **l'empreinte publiée obligatoire** (coût nul : condensats dans le dossier, le matériel de soumission, une copie horodatée) et l'ancrage on-chain **conditionnel** : exécuté seulement si trois conditions sont vertes (run d'exécution réel effectué, vérificateur tiers vert, au moins un jour avant la soumission). C'est un **ajout additif** — il ne doit conditionner ni la démonstration, ni l'export. Rappel de cadrage : **un réseau de test n'est pas une preuve de production**, et une empreinte prouve l'intégrité du dossier ancré, **pas sa véracité**. |
| **Quand rouvrir** | Post-concours pour un paquet de production (mêmes adresses de pré-déploiement sur le réseau principal — « ce qui change n'est pas l'architecture, c'est le montant ») ; et comme **rituel de publication** à chaque version majeure de documents. |
| **Coût** | ~1 à 2 heures de script + une transaction ; procédure identique du test à la production. Source : étude du bloc audit §3. |

### F.2 Audit de l'auditeur (relecteur externe du vérificateur)

| | |
|---|---|
| **Idée & apport** | Faire tester le **vérificateur tiers** par quelqu'un qui n'a pas écrit son code — le modèle de contrôle « qui contrôle le contrôleur ». Ferme la boucle de crédibilité : un outil qui prétend détecter six mutations doit être **lui-même** mis à l'épreuve par un tiers. C'est la seule façon de transformer « notre vérificateur dit oui » en « un tiers peut le contredire ».
| **Pourquoi pas en v1** | Le relecteur externe arrive **après** le concours (disponibilité). La v1 publie l'auto-test de détection (six mutations) et l'assume comme un auto-test, pas comme un audit. |
| **Quand rouvrir** | Dès qu'un relecteur est disponible ; à répéter à chaque évolution majeure du vérificateur. |
| **Coût** | ~0,5 jour pour un passage de relecture (six mutations) ; non bloquant. Source : étude du bloc audit, question ouverte QO-6. |

### F.3 Horodatage complémentaire (ancrage hors chaîne)

| | |
|---|---|
| **Idée & apport** | Utiliser un service d'horodatage public (par exemple ancrage dans une chaîne de blocs de référence) comme **variante gratuite** de l'ancrage — utile si le réseau ciblé devient indisponible. Une seconde source de datation, indépendante de l'écosystème du projet.
| **Pourquoi pas en v1** | **NON TROUVÉ** : le statut réel du service n'a pas été vérifié dans le cadre des recherches ; l'introduire sans vérification serait un pari. |
| **Quand rouvrir** | Exploration post-concours, avec vérification préalable du service (conditions d'usage, durabilité). |
| **Coût** | Inconnu ; ~0,5 jour d'investigation. Source : étude du bloc audit, question ouverte QO-10. |

### F.4 Preuve cryptographique d'exécution (enclave, preuve statistique, preuve à divulgation nulle) — **écarté**

| | |
|---|---|
| **Idée & apport** | Remplacer la **reconstruction déterministe** (notre preuve actuelle) par une preuve cryptographique : exécution dans une enclave attestée, preuve statistique d'échantillonnage, ou preuve à divulgation nulle. Une preuve « machine » d'exécution correcte, sans avoir à rejouer le calcul.
| **Pourquoi écarté** | Ce sont des **définitions différentes** de « vérifiable » : elles prouvent qu'un calcul a eu lieu, pas que la **décision** est reproductible à partir de sources datées. Le projet revendique la **provenance recalculable** — un tiers rejoue la décision avec les données archivées et la politique gelée. Enfin, ces technologies sont portées par des acteurs dont le produit a reculé (un pionnier de la preuve à divulgation nulle s'est repositionné hors finance décentralisée). |
| **Quand rouvrir** | Si un client exige une attestation d'exécution **en plus** de la reconstruction (cumul, pas substitution) — c'est un axe de veille concurrentielle. |
| **Coût** | Élevé ; dépend du fournisseur. Source : recherche de concurrence (§a, §d catégorie 7), 15/10/2026. |

### F.5 Flux continu du journal (publication au fil de l'eau)

| | |
|---|---|
| **Idée & apport** | Publier le journal de décisions **en continu** (flux consultable), plutôt qu'un paquet livré à la fin. Crédibilité maximale devant un jury industriel : la valeur se mesure au **flux produit avant que le résultat ne soit connu**. C'est la même logique que la publication de prévisions gelées.
| **Pourquoi pas en v1** | Suppose un service en ligne permanent et une politique de rétention/exposition des extraits — deux décisions non tranchées (retention intégrale pour le paquet de démonstration, extraits publics à définir). |
| **Quand rouvrir** | Après le premier passage réussi en mode *forward* (voir G.2). |
| **Coût** | ~1 à 2 jours (service + filtrage des extraits publiables). |

## G — Évaluation, calibration & apprentissage

### G.1 Calibration continue et alertes de dérive

| | |
|---|---|
| **Idée & apport** | Un traitement **périodique** qui, à chaque nouveau résultat observé, met à jour les tables de calibration et les courbes, et **alerte** en cas de dérive (erreur de calibration glissante au-dessus d'un seuil, test du signe qui bascule, score de Brier qui passe sous zéro). L'alerte **propose** un re-gel à un humain — jamais un re-gel automatique. Une mesure vivante de la qualité des prévisions, et la détection du moment où le système « décroche ».
| **Pourquoi pas en v1** | **Prérequis de volume** : une centaine d'observations résolues pour une courbe exploitable. En v1, les prévisions gelées se comptent en unités ; le statut « non établi » est la seule déclaration honnête. |
| **Quand rouvrir** | Quand le nombre de résultats résolus atteint le seuil, ce qui suppose la rétention des séries et un rythme d'épisodes — donc après plusieurs mois d'exploitation. |
| **Coût** | ~1 à 2 jours (traitement, tableaux de bord, règles d'alerte) ; quasi nul ensuite. Source : étude du bloc évaluation §f.3 (proposition V2-A). |

### G.2 Passage en avant (*forward*) — publication de décisions avant résultat

| | |
|---|---|
| **Idée & apport** | Faire tourner le système en continu pendant **4 à 6 semaines** (week-ends compris), chaque décision étant **écrite et hachée avant** que l'issue soit connue. C'est la seule voie pour trois choses que le rejeu ne peut pas donner : l'exécution et la latence réelles, la **surprise** (des fenêtres que personne n'a choisies), et la crédibilité devant un jury industriel.
| **Pourquoi pas en v1** | Le concours se termine avant qu'une telle fenêtre soit écoulée ; et la règle d'honnêteté doit être écrite d'avance : si **aucun** épisode ne survient (cas le plus probable), on publiera « 0 perte évitée observée — la démonstration porte sur la préparation, pas sur le gain ». |
| **Quand rouvrir** | Dès la fin du concours, sur la base gelée des paramètres. Métriques : les mêmes que le harnais, **plus** le taux de déclenchement, la latence et le coût par décision utile. Puissance attendue : **0 à 1 événement exploitable** — donc aucune supériorité revendicable, seulement une **faisabilité opérationnelle**. |
| **Coût** | ~1 à 2 jours de mise en place + 4 à 6 semaines de fonctionnement (charge faible mais surveillance humaine nécessaire). Source : recherche sur les objectifs et la mesure §(d). |

### G.3 Conformité statistique (intervalles et garanties de couverture)

| | |
|---|---|
| **Idée & apport** | Ajouter des intervalles conformes (et leur variante adaptative) aux sorties du système, pour donner une garantie de couverture aux décisions. Une base quantitative pour l'abstention : la recherche montre que le pire cas est la **sous-couverture des classes minoritaires** (jusqu'à 0,5 % de couverture effective) — or l'événement d'intérêt du projet **est** la classe minoritaire ; la variante conditionnelle, sous budget de revue humaine, réduit le coût de décision attendu.
| **Pourquoi pas en v1** | La validité des garanties repose sur l'**échangeabilité** des observations, propriété douteuse sur des séries temporelles financières ; et l'échantillon v1 est minuscule. L'évaluation v1 se limite à la mesure descriptive. |
| **Quand rouvrir** | Quand la calibration atteindra une centaine d'observations (même condition que G.1) ; la variante adaptative avec points de changement est une exploration à part entière. |
| **Coût** | ~1 jour pour la version simple ; recherche pour la variante adaptative. Source : rapport d'évaluation §B.5 et §B.6 ; étude du bloc décision §c.1. |

### G.4 Méta-apprentissage (trois sous-propositions à lisibilité décroissante)

| | |
|---|---|
| **Idée & apport** | Trois apprentissages de nature différente : **(C1)** sélection de composants à budget égal (par exemple second critique spécialisé contre seconde passe du même modèle — apprentissage **organisationnel**) ; **(C2)** ordre de recherche **appris** (compter quels prédicats réfutent réellement, à partir de l'historique du journal, en gardant l'ordre déterministe gelé comme repli) ; **(C3)** conformal adaptatif (voir G.3). C1 est le candidat V2 **le plus défendable** (aucun risque épistémique) ; C2 promet un gain d'efficacité de recherche **si** le journal existe en volume.
| **Pourquoi pas en v1** | C2 est **interdit tant que le journal n'existe pas** en volume suffisant (et la v1 vient à peine de le créer) ; C3 dépend de G.3. |
| **Quand rouvrir** | C2 : quand le journal comportera assez de réfutations enregistrées par type de prédicat pour que le comptage signifie quelque chose. C1 : dès qu'un essai à budget égal est planifié. |
| **Coût** | C1 : 2 à 4 jours si mesuré. C2 : 2 à 3 jours d'ingénierie + la dérive d'évaluation. Source : étude du bloc évaluation §f.3 (proposition V2-C). |

### G.5 Interdits d'apprentissage (garde-fous à porter au gel)

| | |
|---|---|
| **Idée & apport** | Écrire noir sur blanc ce que le système **n'a pas le droit d'apprendre** : pas de bandit ni d'apprentissage par renforcement sur la politique avant un passage en avant **prolongé** ; pas d'auto-modification de prompt ni de seuil par un modèle ; pas d'usage d'un résultat du jeu d'évaluation pour régler quoi que ce soit (le jeu reste « brûlé ») ; pas d'ajustement fin sur les épisodes d'évaluation ; toute boucle d'apprentissage passe par un **gel humain** et un journal des variantes. Elle protège la seule chose que le projet revendique : l'honnêteté de la mesure.
| **Pourquoi pas en v1** | Ces interdits **sont** la doctrine de la v1 ; les rappeler dans le registre V2 évite qu'une amélioration future les contourne par inadvertance : le nombre d'épisodes requis pour un apprentissage par renforcement est hors d'échelle (0 à 1 événement en 4 à 6 semaines). |
| **Quand rouvrir** | Jamais « rouvrir » — ce sont des conditions **permanentes** ; seule leur portée peut changer avec un volume d'exploitation supérieur. |
| **Coût** | Nul (rédaction). Source : étude du bloc évaluation §f.3 (proposition V2-D). |

### G.6 Cas historiques supplémentaires (2ᵉ et 3ᵉ épisodes)

| | |
|---|---|
| **Idée & apport** | Ajouter des épisodes de référence : un cas technique sur un ratio de staking liquide (juin 2022), un cas candidat n°1 sur un écosystème stablecoin effondré (mai 2022), un cas de contraste (faux positif potentiel, mai 2022), un cas de généralisation (novembre 2022), un cas asymétrique (mars 2020). Deux points de mesure au lieu d'un ; c'est l'argument le plus efficace contre « votre système ne marche que sur un cas ».
| **Pourquoi pas en v1** | Le gel retient un jeu de développement (deux actifs) et un jeu d'évaluation (deux autres) — c'est déjà le maximum tenable ; et l'ajout d'un cas exige la collecte complète (prix multi-venues, état on-chain, **fenêtres témoins**) puis la reconstruction des signaux. |
| **Quand rouvrir** | Après le concours, en commençant par le cas le plus proche techniquement (ratio de staking liquide) ; le cas **écarté pour cause de données** doit rester écarté : un épisode de 2018 n'est pas reconstituable avec des interfaces publiques gratuites (agrégat qui n'enregistre pas la dislocation, historique de place absent, autre place vide) — le consigner vaut mieux que le gonfler avec des chiffres de presse. |
| **Coût** | ~2 à 3 jours par épisode (collecte + reconstruction + tests de qualité) ; variable selon la disponibilité des archives. Source : rapport d'évaluation §C.0–C.9. |

### G.7 Cas qualitatif sans série de prix — critères de réintégration

| | |
|---|---|
| **Idée & apport** | Un incident de 2025 (perte invisible, actif valorisé à prix fixe) n'a **aucune série de prix** exploitable : le traiter comme un cas **qualitatif** seulement, et écrire les critères qui permettraient un jour de le réintégrer quantitativement. Honnêteté : ne pas exclure en silence, ne pas inventer une série. Critères proposés : existence d'une série, profondeur mesurable, vérité terrain de sortie.
| **Pourquoi pas en v1** | Aucune des trois conditions n'est remplie. |
| **Quand rouvrir** | Si un fournisseur de données publie une série exploitable, ou si la reconstruction devient possible (archive de contrats). |
| **Coût** | ~0,5 jour de vérification des critères. Source : recherche sur les données d'épisodes. |

### G.8 Comparaison inter-modèles à budget égal

| | |
|---|---|
| **Idée & apport** | Comparer plusieurs modèles de langage sur la même tâche, à **budget d'appels égal** (et non « au meilleur des essais »). Une réponse défendable à la question « pourquoi ce modèle ? » — aujourd'hui la réponse est une décision d'équipe, pas une mesure.
| **Pourquoi pas en v1** | Le jeu de mesures est trop petit pour distinguer des modèles ; et la comparaison n'apporte rien à la démonstration. |
| **Quand rouvrir** | Après le passage en avant et la collecte de prévisions scorées. |
| **Coût** | 1 à 2 jours + budget d'appels. Source : rapport d'évaluation §B.6 (« reporté après le concours »). |

## H — Interface & opérations

### H.1 Hébergement géré (plateforme + base hébergée) — **reporté**

| | |
|---|---|
| **Idée & apport** | Servir le système depuis une plateforme d'hébergement avec base managée, plutôt qu'en local. Accessibilité (démonstration à distance), persistance, sauvegardes.
| **Pourquoi reporté** | Le gel retient **entièrement local pour commencer** : la démonstration doit être **impossible à casser** par une panne réseau, et l'hébergement géré ajoute un risque d'expiration (les offres gratuites de base de données expirant après 30 jours) que la cible retenue évite (offre gratuite durable). Le gel v2 ajuste explicitement cette ligne. |
| **Quand rouvrir** | Dès que l'interface produit existera (H.2) et qu'un accès à distance sera requis — c'est-à-dire en produit, pas en démonstration. |
| **Coût** | ~1 à 2 jours (déploiement, secrets, sauvegardes, test hors-ligne de secours) ; postes gratuits suffisants au volume visé. |

### H.2 Interface produit complète (au-delà de la lecture seule)

| | |
|---|---|
| **Idée & apport** | Livrer l'interface complète : écrans de suivi, file d'approbation actionnable, historique des dossiers, tableaux de bord d'évaluation. Un produit utilisable par un trésorier non technique ; c'est la **condition d'adoption** réelle.
| **Pourquoi pas en v1** | La v1 est en **lecture seule** ; les approbations sont prévues pour la version intermédiaire ; et la préparation vidéo dépend de la construction de l'interface (reportée au gel). |
| **Quand rouvrir** | Immédiatement après la démonstration, en commençant par la file d'approbation (c'est le seul écran qui débloque l'usage réel). |
| **Coût** | Non chiffré précisément ; la spécification d'écrans existe (base : liste des écrans) — estimer 1 à 2 semaines pour une version utilisable. |

### H.3 Surveillance continue & veille opérationnelle

| | |
|---|---|
| **Idée & apport** | Passer d'un mode « épisode déclenché » à une **surveillance permanente** (multi-actifs, reprise après incident, journal d'épisodes), avec veille sur les dépendances (fermetures d'interfaces, changements de conditions). C'est la forme sous laquelle le produit crée de la valeur : la détection d'un épisode pendant un week-end.
| **Pourquoi pas en v1** | Trois raisons : (a) le gel privilégie une démonstration reproduisible ; (b) **une interface publique de données utilisée par le projet a annoncé sa fermeture au 13/11/2026** — un système continu dépendrait de connecteurs à remplacer, travail non planifié ; (c) un service permanent a un coût d'exploitation (surveillance, astreinte) hors périmètre. |
| **Quand rouvrir** | Après remplacement du connecteur en fin de vie, et après le passage en avant réussi. |
| **Coût** | ~1 à 2 semaines (connecteurs, ordonnanceur, reprise, alertes). |

### H.4 Renforcement de l'intégration continue (tests supplémentaires)

| | |
|---|---|
| **Idée & apport** | Ajouter des contrôles automatiques : tests de dérive entre politique et permissions on-chain, tests de conformité du schéma de graphe, tests de non-régression sur jeux gelés. Empêche les régressions silencieuses — en particulier le **test de dérive** entre la politique hors chaîne et l'enveloppe on-chain, spécifié mais non implémenté.
| **Pourquoi pas en v1** | Les ajouts sont acceptés au gel mais non tous écrits ; priorité aux chemins critiques de la démonstration. |
| **Quand rouvrir** | Progressivement ; le test de dérive **avant** toute exécution on-chain réelle. |
| **Coût** | ~0,5 à 1 jour par contrôle. Source : étude du bloc politique §d.2–d.4 ; gel §8 (H4). |

## I — Gouvernance & méthode

### I.1 Rituels de revue et journal des variantes

| | |
|---|---|
| **Idée & apport** | Une **cadence de revue** : trimestrielle (calée sur le rythme des rapports de trésorerie des organisations cibles) **plus** à chaque déclencheur (dérive détectée, nouvel épisode, changement de version de modèle). Chaque révision produit un **nouveau gel haché** et une entrée au journal des variantes — **y compris les révisions ratées**. Elle rend la réouverture gouvernable : on sait **qui** a changé **quoi**, **quand** et **pourquoi** ; rien ne se modifie en silence.
| **Pourquoi pas en v1** | La v1 n'a pas d'historique à réviser ; le registre de décisions et le paquet haché existent, le rituel n'a pas encore tourné. |
| **Quand rouvrir** | Dès la fin de la période de concours (première revue à trois mois), puis à chaque déclencheur. |
| **Coût** | ~0,5 jour par revue (documentation), plus le coût des essais décidés. Source : étude du bloc évaluation §f.2 ; protocole de gel §6. |

### I.2 Rôles nommés (responsable du gel, exécutant à l'aveugle, relecteur externe)

| | |
|---|---|
| **Idée & apport** | Nommer explicitement : **qui gèle** (les paramètres de mesure), **qui exécute l'évaluation sans avoir écrit le code** (exécutant dit « aveugle »), **qui relit** sans avoir écrit le code. Supprime l'auto-évaluation complaisante : c'est le seul mécanisme qui distingue un résultat d'un vœu.
| **Pourquoi pas en v1** | Le relecteur externe arrive après le concours ; l'équipe est petite ; le gel prévoit la signature des hypothèses par le chef d'équipe en attendant. |
| **Quand rouvrir** | Dès qu'une évaluation non triviale est planifiée (le premier passage en avant). |
| **Coût** | Nul à faible (nomination + procédure écrite) ; ~0,5 jour. Source : recherche sur les objectifs et la mesure §(f) point 12 ; rapport d'évaluation Q1. |

### I.3 Posture d'intégration : « intégrer avant de construire »

| | |
|---|---|
| **Idée & apport** | Tenir un **inventaire** par brique : ce que le projet intégré (**wallets d'agents, moteurs de politique, rails d'exécution, coffres-forts multi-signatures, modules de permissions, oracles de risque**) contre ce qu'il construit (le jugement sur un graphe de collatéral, l'abstention, la provenance recalculable). Elle évite de reconstruire une commodité — et la recherche de concurrence est formelle : l'**enveloppe est commoditisée** (neuf plateformes d'agent wallets en 2026, politique appliquée on-chain chez la plupart). Deux leçons de marché appuient la posture : deux produits d'automatisation « entreprise » ont **fermé en 2026** (arrêt définitif d'un service historique au 1er juillet 2026 ; rachat et arrêt d'un autre au 17 avril 2026) — vendre l'enveloppe seule ne tient pas économiquement.
| **Pourquoi pas en v1** | L'intégration demande des dépendances externes ; la démonstration du concours privilégie la bibliothèque standard et le hors-ligne. La posture est donc **documentée** et appliquée aux pièces non critiques. |
| **Quand rouvrir** | En produit : la sélection des briques d'intégration (et la sortie des briques fermées) est le premier chantier. |
| **Coût** | Analyse ~1 à 2 jours ; intégration variable (1 à 5 jours par brique). Source : recherche de concurrence §d–§f. |

### I.4 Liste de veille concurrentielle (signaux qui réduiraient l'espace)

| | |
|---|---|
| **Idée & apport** | Surveiller cinq signaux précis, à revérifier avant la finale : (1) les **oracles de risque gouvernés** étendent leur périmètre au-delà des paramètres de protocole (positions, trésoreries, multi-protocoles) ; (2) l'acteur le plus proche (générateur de stratégies avec coffre-fort et permissions) ajoute une couche **autonome** de réduction de risque ; (3) un fournisseur de wallet d'agent embarque un moteur de risque de graphe ; (4) un travail de recherche voisin (prévision de réseaux d'exposition, tickets de supervision) est **productisé** par un acteur financé ; (5) un produit de « contexte certifié » passe du conseil à l'**exécution conditionnée**. Elle protège l'argument différenciant — et elle est **honnête** : l'étude conclut qu'**aucun acteur ne coche les cinq axes**, et que le croisement (graphe multi-actifs + agent de trésorerie + provenance recalculable + abstention + double enveloppe) est ce qui résiste.
| **Pourquoi pas en v1** | C'est un rituel de veille, pas un livrable. |
| **Quand rouvrir** | Avant la finale (21–23/11/2026), puis trimestriellement. |
| **Coût** | ~0,5 jour par passage. Source : recherche de concurrence §d–§e, 15/10/2026. |

---

# 4. LES DOUZE POINTS OUVERTS DE LA MESURE

La recherche sur les objectifs et la mesure a laissé **douze points à trancher par l'équipe**. Le gel v2 en a fermé une partie par défaut (souvent : « le chef d'équipe signe »). Le tableau donne, pour chacun : **question** · **statut au 15/10/2026** · **options** · **ce qui la ferme**.

| # | Question | Statut au 15/10/2026 | Options et proposition | Ce qui la ferme |
|---|---|---|---|---|
| **1** | **Objet de l'objectif : regret ou espérance ?** | Fermé par défaut — les deux, publiés **séparément** | Le **regret par fenêtre** est la métrique de *décision* (comparable entre systèmes, indépendante du scénario réalisé) ; l'**espérance sur scénarios pondérés** est la revendication *économique*. Reste à désigner qui signe les probabilités de scénarios | Nommer le signataire et figer les valeurs de départ (0,5 j) |
| **2** | **Unité de compte de la DAO : dollars, jours de run**, ou les deux ? | Fermé par défaut — les deux, **jours en premier** | Les jours de survie (« runway ») sont l'unité native d'une trésorerie ; les dollars en annexe. La conversion dépend d'un **coût de fonctionnement de référence** (une référence externe documentée : 16,4 M$/an) — **quel paramètre pour ORVYREN ?** | Choix du paramètre de référence (0,25 j) |
| **3** | **Convention de valorisation : valeur terminale ou liquidation ?** | **Ouvert** — décision attendue avant le gel de la fonction de perte | Proposition : **liquidation** pour la DAO (plus prudente, cohérente avec une politique d'investissement exigeant un remboursement en 7 jours) ; **terminale + financement** pour le desk. Le paramètre doit être **gelé** car il change le signe des résultats | Gel de la fonction de perte avec la convention retenue (0,25 j) |
| **4** | **Faut-il modéliser la ré-entrée ?** | Fermé par défaut — oui pour le desk, non pour la DAO | Desk : ré-entrée dans la même fenêtre, coût d'aller-retour explicite. DAO : la ré-entrée relève de la politique de réallocation, pas de l'agent | Gel (0,25 j) |
| **5** | **Seuils chiffrés** (perte évitée ≥ 5 %, friction ≤ 10 %, antériorité ≥ 6 h, glissement ≤ 30 bp, baisse ≤ 20 %, ratio de Sharpe > 0 avec borne basse > 0) | **Ouvert** — ce sont des **propositions, pas des faits** | À valider, ajuster ou remplacer **avant** l'ouverture du jeu d'évaluation : un seuil choisi après avoir vu les résultats n'a aucune valeur probante | Gel avant évaluation (0,5 j) |
| **6** | **Probabilité d'obligation de sortie, par fenêtre** (persona DAO) | **Ouvert** — hypothèse signée | Aucune source publique n'existe (fréquence réelle des ventes forcées pendant une crise) : c'est une **hypothèse** à justifier par un raisonnement explicite (calendrier de charges, appels de marge, rachats) et à publier **avec sa sensibilité** — c'est le paramètre le plus déterminant de l'exemple chiffré | Rédaction + signature (0,5 j) |
| **7** | **Jeu de scénarios du persona desk** : lesquels, avec quelles probabilités, gelés par qui ? | **Ouvert** — proposition minimale faite | Quatre scénarios proposés : (i) réalisé, (ii) non-rétablissement à 48 h, (iii) guérison lente (5 jours), (iv) venue unique contrainte. À geler et publier avec le P&L | Gel + publication (0,25 j) |
| **8** | **Épisodes de développement / évaluation** et sort du cas sans série de prix | **Tranché** — développement : deux actifs « calmes » 2022-23 ; évaluation : deux actifs 2025-26 ; le cas sans série reste **qualitatif** | Reste à figer les **fenêtres précises** de la période calme du jeu d'évaluation (≥ 6 fenêtres, bornes, exclusion de la calibration) | Liste exacte des fenêtres (0,5 j) |
| **9** | **Niveau d'autonomie revendiqué : l'agent propose ou exécute ?** | **Hors de la mesure** — tranché côté politique/exécution | Le système **exécute dans son enveloppe** (exécution bornée) ; la mesure ne dépend pas du niveau, elle mesure l'action et le refus. Reste : écrire la **formulation publique** exacte (l'agent exécute seul **dans** l'enveloppe, la clé n'a aucune valeur intrinsèque hors de l'enveloppe) | Formulation portée au dossier (0,25 j) |
| **10** | **Budget de risque explicite par épisode et plafond de taille d'action** | **Ouvert** — paramètres de politique | À introduire pour que la politique soit bornée **par construction** ; aucune valeur de référence publique côté trésorerie (« NON TROUVÉ » : les documents de politique imposent un rapport de baisse, pas un plafond) | Valeur fournie par un mandat client, ou gel d'une valeur par défaut (0,5 j) |
| **11** | **Coût de capital et financement** (persona desk) | Fermé par défaut — **deux P&L** publiés | Publier un P&L **hors financement** et un P&L **avec financement**, et laisser la différence visible ; le taux retenu est une hypothèse signée | Valeur + publication (0,25 j) |
| **12** | **Qui gèle, qui rejoue** : responsable du gel, exécutant « aveugle », relecteur externe | **Ouvert** — à nommer | Nommer trois rôles, même si le relecteur externe arrive après le concours. Le gel prévoit, par défaut, la signature du chef d'équipe pour les paramètres non tranchés | Nomination écrite (0,25 j) |

**Lecture d'ensemble** : sur douze points, **quatre** sont structurellement fermés par défaut (1, 2, 4, 11) et un est tranché (8). Les sept autres — convention de valorisation, seuils, probabilités, scénarios, fenêtres, budget de risque, rôles — sont des **gelages de paramètres** : chacun coûte moins d'une demi-journée, mais chacun **change le sens des résultats** s'il est fait après coup. C'est la raison pour laquelle la mesure a ses propres conditions de réouverture : un paramètre gelé puis modifié après ouverture du jeu d'évaluation **invalide** l'évaluation (et le dit).

---

# 5. REGISTRE DES HYPOTHÈSES & QUESTIONS DE RECHERCHE RESTANTES

## 5.1 Registre des hypothèses (statut au 15/10/2026)

Chaque hypothèse est écrite pour être **attaquable** : un énoncé, un critère de soutien, un critère de réfutation, un coût. Toutes sont **ouvertes** — aucune n'est un résultat. Statuts d'atelier : `OUVERTE` · `CONVERTIE EN EXIGENCE` · `ÉLIMINÉE` · `FUSIONNÉE`.

| ID | Énoncé (une phrase) | Statut | Label | Réfutation écrite (ce qui la tuerait) |
|---|---|---|---|---|
| **HYP-01** | Un graphe typé (entités, relations, provenance, horodatages multiples) réduit les conclusions prématurées par rapport à un pipeline plat, **à budget égal** | OUVERTE — la plus stratégique | HYPOTHÈSE CAUSALE | Performances identiques au pipeline plat sur ≥ 3 fenêtres, **ou** coût de structure non justifié |
| **HYP-02** | Une politique d'arrêt par **valeur de l'information** égale ou dépasse les seuils réglés à la main sur nos propres fenêtres | OUVERTE | STATISTIQUE | La politique de valeur consomme plus de budget pour une qualité égale, **ou** l'incertitude des probabilités rend le calcul inexploitable |
| **HYP-03** | Le **registre de branches** (3 à 5 hypothèses explicites avec réfutation enregistrée) améliore la qualité de décision mesurée par le regret, et **bat un placebo apparié** | OUVERTE | HYPOTHÈSE CAUSALE | Pas de gain sur le regret, ou gain indistinguable du placebo |
| **HYP-04** | Le **label épistémique change la décision** : une conclusion reposant uniquement sur des relations « hypothèse causale » est plus souvent classée non concluante | **CONVERTIE EN EXIGENCE** (la tester serait tautologique : si la règle interdit d'agir, observer plus d'abstentions ne prouve rien) | — | — (une reformulation en hypothèse empirique exigerait un design humain distinct, jugé trop coûteux) |
| **HYP-05** | Le **double verrou** (politique + mandat on-chain) empêche 100 % des actions hors enveloppe sur un banc de 12 attaques, **mais** introduit un effet de frontière de période mesurable (dépense doublée en limite de période) | OUVERTE | STATISTIQUE | Une attaque passe, **ou** l'effet de frontière est exploitable en pratique |
| **HYP-06** | La calibration des probabilités est meilleure quand elles sont élicitées **avant** exécution, en cadrage « recherche de bug », que par confiance déclarée | OUVERTE | STATISTIQUE | Pas d'écart entre les deux modes, ou écart inverse |
| **HYP-07** | Une extension apprise du graphe (représentations vectorielles / prédiction de liens) retrouve des **relations manquantes** de la carte curatée, mesurée en précision@k sur des relations tenues à l'écart | OUVERTE (programme post-concours) — absorbe l'ancienne hypothèse de compromis traçabilité | INFÉRÉ PAR MODÈLE | Précision@k au niveau des témoins triviaux, **ou** inférences sans provenance complète |
| **HYP-08** | L'**observation multi-acteurs** (banques, infrastructures, régulateurs) améliore la précision du diagnostic par rapport aux seules données de marché (détection plus précoce ou moins de faux signaux) | OUVERTE | HYPOTHÈSE CAUSALE | Aucune amélioration hors échantillon, **ou** amélioration qui disparaît quand on tient compte du coût des données |
| **HYP-09** | La décision bornée (réduction d'exposition) a un regret inférieur à la règle simple sur les épisodes, **nette des coûts**, sans supériorité statistique revendiquée | **ÉLIMINÉE** — conséquence directe du constat « transférer entre deux portefeuilles de la même entité ne réduit pas le risque d'émetteur » | — | — (une **nouvelle** hypothèse la remplace si une cession simulée est retenue — voir C.5) |
| **HYP-10** | Un tiers indépendant peut **recalculer** la décision à partir des seules sources archivées, y compris la remontée résultat → source | OUVERTE | FAIT (testable) | Un tiers ne peut pas rejouer au moins un maillon de la chaîne |
| **HYP-11** | La **séparation des rôles** (proposer / réfuter / valider / exécuter) réduit le taux de décisions fausses sur le banc adversarial par rapport à un agent unique | OUVERTE | HYPOTHÈSE CAUSALE | Aucune différence à budget égal (c'est précisément l'essai de sélection de composants, G.4) |
| **HYP-12** | L'**abstention** produit un regret inférieur à une action forcée quand la preuve manque (fenêtres à données trouées) | OUVERTE | STATISTIQUE | Le regret de l'abstention dépasse celui de l'action forcée sur les fenêtres trouées |
| **HYP-13** | Les **acteurs bancaires/financiers** produisent des comportements corrélés détectables, signal exploitable avant le mouvement de prix | OUVERTE — **très expérimentale** | HYPOTHÈSE CAUSALE | Le signal n'est qu'un artefact d'agrégation, ou disparaît sous contrôle de volatilité |
| **HYP-14** | *(fusionnée)* Une carte de relations apprise améliore le pouvoir prédictif mais **dégrade la traçabilité** — mesurer le compromis | **FUSIONNÉE AVEC HYP-07** | INFÉRÉ PAR MODÈLE | Mesure du compromis intégrée à HYP-07 (précision **et** provenance complète) |
| **HYP-15** | La **propagation bornée** (délais, décroissance, itération limitée) surpasse une propagation libre du graphe, y compris avec un graphe enrichi par apprentissage | OUVERTE — **reformulée** : comparer à « rien » et à « un saut », pas à une propagation libre (mauvais témoin) | INFÉRÉ PAR MODÈLE | La propagation bornée ne fait pas mieux que les deux témoins |

**Ce que le registre dit globalement** : quatre hypothèses portent sur la **structure** (graphe, branches, rôles, propagation), trois sur la **mesure** (calibration, abstention, recalculation), trois sur la **décision sous incertitude** (valeur de l'information, double verrou, scénarios), deux sur les **données** (multi-acteurs, comportements corrélés), une sur le **compromis** prédiction/traçabilité. Aucune n'est un résultat : le projet revendique la **faisabilité de la mesure**, pas une supériorité.

## 5.2 Questions de recherche encore ouvertes (à ne pas refermer par une intuition)

| # | Question | Pourquoi elle compte |
|---|---|---|
| 1 | **Apprentissage × graphe sans perte de traçabilité** : quelles méthodes réellement déployables sur un graphe financier temporel **sans** dégrader la reconstituabilité ? Quelles garanties de provenance pour une relation apprise ? | Conditionne l'autorisation d'un futur programme d'apprentissage (HYP-07) |
| 2 | **Types de relation** : la liste actuelle (statut épistémique + portée + cycle de vie) est-elle suffisante pour le domaine bancaire/stabilité, ou faut-il d'autres familles (contrainte réglementaire, mécanisme de liquidité) ? | Détermine la généralisation du catalogue au-delà du cas |
| 3 | **Données publiques sur les acteurs bancaires** : quelles données publiques et datées permettent d'observer dépôts, réserves, expositions **sans accès privilégié** ? | Conditionne HYP-08 et HYP-13 |
| 4 | **Regret d'une réduction d'exposition** : comment mesurer proprement le regret quand la vérité terrain est « ce qui aurait été le mieux après coup », et quelles précautions anti-optimisme du témoin ? | Cœur de la crédibilité de la mesure économique |
| 5 | **Robustesse de la valeur de l'information** quand les probabilités sont subjectives et les coûts hétérogènes (latence, argent, réputation) | Conditionne C.1 |
| 6 | **Comportements corrélés (herding)** : comment tester sans se raconter d'histoires (contrôles, placebo, pré-enregistrement) ? Sujet réglementaire actif | Conditionne HYP-13 |
| 7 | **Abstention comme décision de premier ordre** en finance : quelle littérature 2025-2026 ? | Cadre la revendication « refuser est une fonctionnalité » |
| 8 | **Quels 2ᵉ/3ᵉ cas historiques sont réellement exploitables** avec des sources publiques gratuites ? | Conditionne G.6 |

## 5.3 Ce qui reste **NON TROUVÉ** (à ne jamais combler par une invention)

1. **Objectifs chiffrés publiés par une équipe de trading nommée** (ratio cible, budget de baisse, tolérance de glissement, coût du capital interne) — aucune source publique trouvée le 15/10/2026 : les objectifs du persona desk sont une **reconstruction par métriques de la profession**.
2. **Budget de risque chiffré par une organisation cible** (perte maximale par épisode) — les documents de politique imposent un **rapport** de baisse, pas un **plafond**.
3. **Distribution publique de scénarios de perte d'ancrage** → les probabilités de scénarios sont **nos hypothèses**.
4. **Sensibilité de la probabilité d'obligation de sortie** pour une trésorerie → hypothèse.
5. **Série de prix exploitable** pour l'incident qualitatif de 2025 → cas exclu de l'évaluation quantitative.
6. **Profondeur d'exécution des stablecoins au pire de la crise** → non mesurée (chantier ouvert).
7. **Prix et budgets d'outillage** des fournisseurs de risque et des plateformes de gestion → non publics (sur devis) ; pour les desks : aucune donnée.
8. **Statut réel d'un service d'horodatage complémentaire** (ancrage hors chaîne) → non vérifié.
9. **Aucune évaluation publiée** d'une méthode d'hypothèses concurrentes intégrée à un agent financier → le projet ne peut pas s'appuyer sur un précédent académique pour cette brique.

---

# 6. TABLEAU RÉCAPITULATIF GÉNÉRAL

**Légende** — *Quand rouvrir* : **T1** = dès que le temps/les moyens le permettent (post-concours immédiat) · **T2** = conditionné à un prérequis identifié · **T3** = produit / phase 2 · **J** = jamais (sauf condition permanente à rediscuter). *Coût* : en jours-homme, ordre de grandeur.

## 6.1 Autres utilisateurs

| Proposition | Pourquoi pas en v1 | Quand rouvrir | Coût | Source (sujet de recherche) |
|---|---|---|---|---|
| **Banques & institutions** — cas 1 : collatéral & appels de marge | Données sur registres permissionnés ; agent externe = tiers à contractualiser ; supervision humaine imposée | T3 (phase 2, 2027-2028), avec un coin d'entrée 2026 (argument de vision) | Élevé (partenariat + intégration, plusieurs mois) | Étude des acteurs bancaires (§a–§f) |
| **Banques** — cas 2 : trésorerie tokenisée multi-chaînes | Idem + cycles d'achat longs | T3 | Élevé | Idem |
| **Banques** — cas 3 : veille on-chain & réaction de contrepartie | Cas **extrapolé, non observé en production** ; à présenter avec cette réserve | T3 | Moyen à élevé | Idem (§e) |
| **Équipes de trading** — second persona (fonction de perte desk) | Second persona traité **après** le premier si le temps le permet | T1 (le protocole est déjà spécifié) | Faible à moyen (implémentation du harnais) | Recherche sur les objectifs et la mesure (§A.2, §B.4) |
| **Équipes de trading** — vente d'une « jambe DeFi » aux desks | Les grandes firmes construisent en interne ; conformité ; P&L invisible | T2 (un acheteur identifié : fonds/desks sans équipe de risque) | Non chiffré | Étude des organisations et de la gestion (§E) |
| **Grand public / particuliers** | Valeur perçue nulle (ni traçabilité, ni refus) ; profils abandonnés | J | — | Cadre de définition §01 |
| **Plateformes d'évaluation / compte propre** | Automatisation déjà standard ; perte du positionnement on-chain | J | Faible | Étude des organisations (§E.1) |
| **Régulateurs / superviseurs** | N'achètent pas un agent ; veulent des métriques | T2 (si un axe « données & métriques » devient un produit) | Non chiffré | Recherche problème (§« demande institutionnelle ») |
| **Entreprises non crypto / PME** | Rôle d'acteur observé, pas d'acheteur documenté | T2 | Inconnu (NON TROUVÉ) | Axes d'amélioration §2 |
| **Assurance / transfert de risque** | Aucune source d'un porteur de risque intéressé | J (en l'état) | — | — |

## 6.2 Agents

| Proposition | Pourquoi pas en v1 | Quand rouvrir | Coût | Source |
|---|---|---|---|---|
| **Équipe multi-agents complète** (4 agents, services séparés) | ~30 appels/décision (≈3×), risque de cohérence sur 4 journaux, latence | T2 (essai à budget égal, HYP-11) | +2-4 j (forme intermédiaire) ; 5-8 j (complète) | Étude du bloc agents §1.3-1.5, §9 |
| **Modèles auto-hébergés** | Pas d'infrastructure garantie le jour J ; hors-ligne déjà couvert par le rejeu | T2 (budget d'appels bloquant ou exigence de souveraineté) | Élevé (matériel) ; non chiffré | Étude du bloc agents §2 |
| **Orchestration avancée** (explorateur séparé, arbitre) | Le budget borné est l'argument ; reprise déjà gérée par classe | T2 (avec A.1) | 2-3 j | Étude du bloc agents §4.4-4.5 |
| **Repli multi-fournisseur** | Non nécessaire à la démo (rejeu hors-ligne) | T1 (usage continu) | ~1 j | Étude du bloc agents Q4 |
| **Rédaction du dossier par un modèle** | Aucun chiffre ne vient d'un modèle ; dossier recalculable exigé | J (sauf couche de présentation séparée) | ~1 j | Étude du bloc agents §1.5 |
| **Banc anti-injection étendu** | Non outillé ; risque réel et documenté | T1 (dès lecture de documents externes) | 0,5-1 j | Étude du bloc agents §5.6 |

## 6.3 Graphe

| Proposition | Pourquoi pas en v1 | Quand rouvrir | Coût | Source |
|---|---|---|---|---|
| **Base de graphe dédiée** | Moteur embarqué archivé (10/10/2025) ; offre gratuite inutile à notre échelle ; 2ᵉ base à synchroniser | T2 (volume + requêtes de chemins goulot) | ~1-2 j (migration, magasin isolé) | Étude du bloc graphe §2.3 |
| **Famille « GraphRAG »** | Outil de référence en maintenance ; coût d'indexation ; provenance à reconstruire, fuite confirmatoire | T2 (couche documents) | Non chiffré | Étude du bloc graphe §5.2 |
| **GNN / prédiction de liens / KGC** | Recherche appliquée ; fuite temporelle ; sorties = hypothèses | T1 sous protocole pré-enregistré (HYP-07) | ≥1-2 semaines | Étude du bloc graphe §5.2-5.3 |
| **Incorporations de nœuds** | Non interprétables → générateur d'hypothèses seulement | T1 (avec B.3) | Faible en calcul, coût en validation | Étude du bloc graphe §5.2 |
| **Recherche sémantique étendue** (patrons d'épisodes) | v1 : socle retenu, extension non faite | T1 (volume) | ~1 j | Étude du bloc graphe §5.2-5.3 |
| **Multi-chaînes étendu** | Périmètre volontairement étroit ; chaque chaîne = connecteurs + tests | T2 (premier cas inter-chaînes reproductible) | 2-5 j par chaîne | Cadre de définition §04 |
| **Export formel des relations (type provenance W3C)** | Aucun besoin fonctionnel ; priorité faible | T1 (demande d'un tiers / publication du dépôt) | ~0,5 j | Étude du bloc graphe R8 |
| **Anomalies sur métriques du graphe** | Gain non quantifié (mais règle traçable) | T2 (extension du banc de signaux) | 0,5-1 j | Étude du bloc graphe §5.2 |

## 6.4 Décision

| Proposition | Pourquoi pas en v1 | Quand rouvrir | Coût | Source |
|---|---|---|---|---|
| **Valeur de l'information complète** | Dépend de probabilités calibrées absentes ; ne doit pas être un point de rupture | T2 (calibration + journal + essai concluant) | 2-4 j | Étude du bloc décision §b.3 ; rapport d'orchestration |
| **Branches probabilisées** | « Une probabilité inventée dégrade la preuve » — qualitatif d'abord | T2 (prévisions scorées, N suffisant) | Faible (métriques déjà spécifiées) | Étude du bloc décision §f |
| **Simulation de scénarios / Monte-Carlo** | Pas de distribution publique ; hypothèses à signer | T2 (gel avant évaluation) | ~0,5 j (+ collecte) | Recherche objectifs & mesure §B.0-B.4 |
| **Apprentissage des seuils (quantiles)** | Dépend d'une collecte (10-20 h) et d'un embargo strict | T1, mois par mois, hors fenêtres d'évaluation | 10-20 h + 1-2 j | Chantier compléments de signaux §5 |
| **Cession simulée / ré-entrée** | Échange non exécutable en v1 ; profondeur de crise non mesurée | T1 (avec la fonction de perte) | ~1 j (+ E.3) | Recherche objectifs & mesure §(d), §(f) 4 |
| **État « sortie fermée »** | Aucune série de profondeur au pire de la crise | T2 (mesure de profondeur) | 1-2 j | Recherche signaux (§f) |
| **Multi-épisodes simultanés** | Registre v1 par cas ; budget partagé non tranché | T2 (surveillance continue) | 1-2 j | Étude du bloc décision §h.2 |
| **Catalogues d'actions étendus** | Règle de croissance exigeante (conditions + reçu + run de refus) | T1 par paliers | 1-3 j par action | Étude du bloc décision §d |

## 6.5 Politique, exécution, audit

| Proposition | Pourquoi pas en v1 | Quand rouvrir | Coût | Source |
|---|---|---|---|---|
| **Modificateur de délai on-chain (T3)** | Non testé sur le réseau de démo ; sémantique de veto ≠ approbation ; 1-7 j de refroidissement | T3 (phase produit) | 2-3 j | Étude du bloc politique §b.2-b.5 |
| **Attestation publique de la politique** | **Reportée (gel)** — l'empreinte publiée suffit ; additif | T2 (post-concours, conditions vertes) | ~1 j | Étude du bloc audit §3 ; gel D5 |
| **File d'approbation multi-rôles** | Un seul approbateur en démo | T3 (premier client multi-signataires) | 2-3 j | Étude du bloc politique §b.5-b.6 |
| **Module d'allocation du multisig** | Absent du réseau de démo ; déploiement non audité | J | — | Rapport permissions on-chain §7.3 |
| **Garde on-chain** | Un garde cassé bloque le compte → engagement d'audit | T3 (avec audit) | Élevé, non chiffré | Étude du bloc politique §b.2 |
| **Banc d'attaques 7 → 12** | Non engagé ; argument de sécurité à faible coût | T1 (avant soumission si possible) | ~0,5 j | Axes d'amélioration (axe K) ; rapport d'évaluation §B.6 |
| **Budget de risque par épisode** | Aucune valeur de référence publique | T2 (valeur fournie par un mandat) | ~0,5 j | Recherche objectifs & mesure §(f) 10 |
| **Service de signature non exportable (KMS/enclave/MPC)** | Démo = clé jetable détruite après ; dépendance payante uniquement en produit | T3 (phase 1 produit ; MPC en phase 2) | 2-4 j par option | Étude du bloc exécution §a.2 |
| **Mandat on-chain borné (permission périodique)** | Standard en brouillon ; octroi humain non automatisable ; frontière de période (2×) | T2 (navigateur pilotable ou repli scriptable) | 4-5 j | Rapport permissions on-chain §7.1-7.3 |
| **Échange (swap) exécutable** | Conditions on-chain à écrire + tester ; v1 = simulé (gel) | T1 (après D.3 ou E.2) | 1-2 j | Étude du bloc exécution §b.3 |
| **Prêt exécutable (dépôt/retrait/remboursement)** | Gelé en v2 ; signature déployée ≠ forme attendue ; position préalable | T1 (scénario multi-étapes) | 2-3 j | Étude du bloc exécution §b.2-b.3 |
| **Approbation d'allocation bornée** | Spécification ouverte (remise à zéro, cumul, partiels) | T1 (avec E.3/E.4) | ~1 j | Étude du bloc exécution §b.3 |
| **Passkeys (approbation humaine)** | Un agent n'a pas de biométrie | T3 (interface d'approbation) | 1-2 j | Étude du bloc exécution §a.2 |
| **Module de compte / validateur de session** | Modules = pleins pouvoirs du compte → audit ; change de socle client | T3 (si imposé et financé) | Élevé | Étude du bloc exécution §a.2 |
| **Ancrage permanent du dossier** | Empreinte publiée obligatoire ; ancrage **conditionnel** (gel) | T1 (rituel de publication) puis post-concours pour la production | 1-2 h | Étude du bloc audit §3.2 |
| **Audit de l'auditeur** | Relecteur disponible après le concours | T1 | ~0,5 j | Étude du bloc audit QO-6 |
| **Horodatage complémentaire hors chaîne** | Statut du service NON TROUVÉ | T1 (exploration) | ~0,5 j | Étude du bloc audit QO-10 |
| **Preuve cryptographique d'exécution** | Définition différente de « vérifiable » ; acteurs en recul | T3 (exigence client en **cumul**) | Élevé | Recherche concurrence §d (cat. 7) |
| **Flux continu du journal** | Suppose un service permanent + politique d'extraits | T2 (après G.2) | 1-2 j | Étude du bloc audit §1.5-1.6 |

## 6.6 Évaluation, interface, gouvernance

| Proposition | Pourquoi pas en v1 | Quand rouvrir | Coût | Source |
|---|---|---|---|---|
| **Calibration continue + alertes de dérive** | Prérequis de volume (≈100 observations) | T2 (N suffisant) | 1-2 j | Étude du bloc évaluation §f.3 (V2-A) |
| **Passage en avant (4-6 semaines)** | Le concours se termine avant ; puissance 0-1 événement | T1 (dès la fin du concours) | 1-2 j + 4-6 semaines | Recherche objectifs & mesure §(d) |
| **Intervalles conformes (et variante adaptative)** | Échangeabilité douteuse sur séries temporelles ; N minuscule | T2 (avec G.1) | ~1 j (+ recherche) | Rapport d'évaluation §B.5-B.6 |
| **Méta-apprentissage C1 (sélection de composants)** | Non mesuré | T1 (essai à budget égal) | 2-4 j | Étude du bloc évaluation §f.3 |
| **Méta-apprentissage C2 (ordre de recherche appris)** | Journal insuffisant ; interdit tant que le journal n'existe pas | T2 (volume de réfutations) | 2-3 j | Étude du bloc évaluation §f.3 |
| **Interdits d'apprentissage** | Doctrine permanente (pas de bandit/RL avant passage en avant prolongé) | J (conditions permanentes) | Nul | Étude du bloc évaluation §f.3 (V2-D) |
| **2ᵉ/3ᵉ épisodes historiques** | Gel limite à 2+2 ; collecte lourde | T1 (le plus proche : ratio de staking liquide) | 2-3 j par épisode | Rapport d'évaluation §C |
| **Cas qualitatif sans série de prix** | Aucune série, aucune profondeur, pas de vérité terrain | T2 (critères de réintégration) | ~0,5 j | Recherche données d'épisodes |
| **Comparaison inter-modèles à budget égal** | Jeu de mesures trop petit | T2 (après G.2) | 1-2 j + appels | Rapport d'évaluation §B.6 |
| **Hébergement géré (plateforme + base)** | Gelé : entièrement local d'abord ; expirations des offres gratuites | T3 (interface produit) | 1-2 j | Étude interface & gouvernance §3 |
| **Interface produit complète** | v1 en lecture seule ; approbations en version intermédiaire ; vidéo reportée | T1 (en commençant par la file d'approbation) | 1-2 semaines (estimation) | Étude interface & gouvernance §1-2 |
| **Surveillance continue & veille** | Dépendance en fin de vie (fermeture au 13/11/2026) ; coût d'astreinte | T2 (connecteur remplacé + passage en avant réussi) | 1-2 semaines | Étude interface & gouvernance §3-4 |
| **Renforcement de l'intégration continue** | Ajouts acceptés, non tous écrits | T1 ; test de dérive **avant** exécution on-chain réelle | 0,5-1 j par contrôle | Étude du bloc politique §d.2-d.4 |
| **Rituels de revue + journal des variantes** | Pas d'historique à réviser en v1 | T1 (première revue à trois mois) | ~0,5 j par revue | Étude du bloc évaluation §f.2 |
| **Rôles nommés (gel / exécutant aveugle / relecteur)** | Relecteur après le concours ; petite équipe | T1 (avant la première évaluation non triviale) | ~0,5 j | Recherche objectifs & mesure §(f) 12 |
| **Posture « intégrer avant de construire »** | Dépendances externes ; priorité au hors-ligne en démo | T3 (sélection des briques en produit) | 1-2 j d'analyse + 1-5 j/brique | Recherche concurrence §d-§f |
| **Veille concurrentielle (5 signaux)** | Rituel, pas livrable | T1 (avant la finale) puis trimestriel | ~0,5 j par passage | Recherche concurrence §d-§e |

---

# ANNEXE A — Fonctionnement d'une réouverture, pas à pas (mode d'emploi)

1. **Choisir l'entrée** dans le tableau §6 et vérifier qu'elle a bien quatre champs remplis. Une entrée sans condition de réouverture est incomplète — la compléter avant de l'instruire.
2. **Vérifier la condition de réouverture** (R1 à R5, §1.4). Si aucune n'est remplie, la révision est **refusée** : c'est la règle, pas une opinion.
3. **Écrire le document de révision** (une page) : les quatre questions, les sources, le coût ré-estimé.
4. **Si la réponse à la question 3 est « c'est vérifiable »** : écrire l'essai **avant** de l'exécuter (critère de succès, jeu de données, embargo), l'exécuter, publier le résultat — **y compris s'il contredit** l'équipe.
5. **Sinon** (décision de valeur) : le responsable du gel tranche, et l'écrit **avec sa date et sa raison**.
6. **Mettre à jour** : nouvelle version du document concerné, entrée au journal des variantes, nouveau gel haché. L'ancienne version reste lisible.

---

# ANNEXE B — Sources externes principales (URL + date)

*Chaque affirmation externe citée dans ce document vient de la liste suivante. Les éléments internes renvoient aux fichiers de recherche du dépôt (études de bloc, rapports R1–R3, chantiers de la vague 2, recherches U1/U2/P1).*

**Institutions financières classiques**
- DTCC, communiqué « DTCC Turns Tokenization Into Reality » — 15/07/2026 — `https://www.dtcc.com/press-releases/2026/dtcc-turns-tokenization-into-reality` DTCC + Digital Asset, pilote collatéral & marge — 23/09/2024 — `https://www.prnewswire.com/news-releases/dtcc-and-digital-asset-complete-successful-pilot-to-test-collateral-and-margin-optimization-through-tokenization-302255589.html`
- Forbes, dépôts tokenisés et volumes bancaires — 28/07/2026 — `https://www.forbes.com/sites/digital-assets/2026/07/28/americas-biggest-banks-are-building-one-deposit-token-history-is-the-hard-part/` Banque centrale européenne, travaux exploratoires (64 participants, 1,6 Md€) — juin 2025 — `https://www.ecb.europa.eu/press/pubbydate/2025/html/ecb.exploratoryworknewtechnologies202506.en.html`
- Banque de France / Eurosystème, règlement en monnaie de banque centrale — 21/09/2026 — `https://www.banque-france.fr/en/press-release/eurosystem-brings-central-bank-money-tokenised-finance` BIS, projet multi-devises (Agorá) — page mise à jour le 27/05/2026 — `https://www.bis.org/project/agora`
- OCC, lettre interprétative 1183 (garde crypto, réserves de stablecoins) — 07/03/2025 — `https://www.occ.gov/news-issuances/news-releases/2025/nr-occ-2025-16.html` State Street, *2025 Digital Assets Outlook* (~60 % des institutionnels) — 09/10/2025 — `https://investors.statestreet.com/investor-news-events/press-releases/news-details/2025/State-Street-Issues-2025-Digital-Assets-Outlook-Institutions-Double-Down-on-Tokenization/default.aspx`
- BNP Paribas rejoint le consortium euro stablecoin — 02/12/2025 — `https://www.reuters.com/business/finance/group-european-banks-announce-euro-stablecoin-plans-2025-12-02/`

**Réglementation & supervision**
- AI Act, article 14 « supervision humaine » — texte : `https://artificialintelligenceact.eu/article/14/` ; Commission européenne : `https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai` FSB, implications de l'IA pour la stabilité financière — 14/11/2024 — `https://www.fsb.org/2024/11/fsb-assesses-the-financial-stability-implications-of-artificial-intelligence/`
- DORA, résilience opérationnelle numérique (applicable depuis le 17/01/2025) — `https://www.eiopa.europa.eu/digital-operational-resilience-act-dora_en` BIS, norme prudentielle crypto (publication finale 17/07/2024) — `https://www.bis.org/media-releases/20240717-basel-committee-publishes-final-disclosure-framework-banks-cryptoasset-exposures-and-targeted`

**Technique & fournisseurs**
- Spécification d'autorisation de portefeuille (ERC-7715) — `https://eips.ethereum.org/EIPS/eip-7715` Safe, transactions à signatures hors chaîne (EIP-712) et file d'attente — `https://docs.safe.global`
- Zodiac, guide du module de délai (cooldown 1-7 jours) — `https://docs.zodiac.eco` AWS KMS, clés secp256k1 (signature uniquement) — `https://docs.aws.amazon.com/kms/latest/APIReference/API_CreateKey.html`
- Turnkey (enclave, clés non exportables) — `https://docs.turnkey.com/solutions/company-wallets/overview` Coinbase CDP Wallets (enclaves Nitro, moteur de règles) — `https://docs.cdp.coinbase.com/wallets/security-and-policies/security-overview`
- Fordefi, signataire d'API (première part de signature répartie) — `https://docs.fordefi.com/developers/getting-started/set-up-an-api-signer` Base, précompilation de vérification de signature (passkeys) — `https://docs.base.org/specifications/base-protocol/execution/precompiles`
- Offre de données vectorielles et hébergement gratuit durable — `https://github.com/pgvector/pgvector`, `https://neon.com/pricing` Kuzu (moteur de graphe archivé) — `https://github.com/kuzudb/kuzu` ; couverture presse — 14/10/2025 — `https://theregister.com/software/2025/10/14/kuzudb-graph-database-abandoned-community-mulls-options/1142229`
- GraphRAG (mode maintenance) — `https://github.com/microsoft/graphrag`

**Marché, concurrence & économie des acteurs**
- Chaos Labs quitte son mandat de gestion du risque — 06/04/2026 — `https://governance.aave.com/t/chaos-labs-is-leaving-aave/24386` Galaxy Research, analyse de l'incident d'avril 2026 (292 M$, 13 Md$ de valeur évaporée en 48 h) — 22/04/2026 — `https://galaxy.com/insights/research/kelpdao-layerzero-exploit-defi`
- Rapport de trésorerie d'une grande organisation (baisse de 157,5 à 121,0 M$ en 4 mois) — posté 04/06/2026 — `https://research.lido.fi/t/lido-financial-report-for-q1-2026/11623` Revue semestrielle d'un fonds de dotation (101,6 → 67,7 M$, frais 0,50 %/an) — 14/08/2026 — `https://discuss.ens.domains/t/kpk-h1-2026-review-for-the-ens-endowment/22358`
- Vaults à exécution automatisée et permissions par stratégie (concurrence directe à surveiller) — `https://almanak.co` Oracles de risque gouvernés (mise à jour de paramètres en minutes, limites pré-approuvées) — `https://chaoslabs.xyz` ; oracle de risque d'un fournisseur de recherche — `https://llamarisk.com`
- Fin de vie d'un service d'automatisation historique — 01/07/2026 — `https://openzeppelin.com/news/doubling-down-on-open-source-and-phasing-out-defender` Neuf plateformes d'agent wallets (enveloppe commoditisée) — 13/09/2026 — `https://openfort.io`

**Mesure & méthodologie**
- Note de la Réserve fédérale sur la faillite bancaire de mars 2023 et son effet sur les stablecoins — 17/12/2025 — `https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html` Règle de rejet (abstention coût-optimale) — Chow, IEEE Trans. Inf. Theory, 1970
- Revue *Machine learning with a reject option* — 29/03/2024 — doi 10.1007/s10994-024-06534-x Prédiction conforme sensible au coût et abstention avec humain dans la boucle — arXiv:2607.27143 — 29/07/2026
- Ratio de Sharpe déflaté (multiplicité des essais) — Bailey & López de Prado, *Journal of Portfolio Management*, 2014 — `https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf` Pré-enregistrement gelé et haché — pratique générale ; référence interne de méthode (`FREEZE`/gel, §6.5 du protocole)

---

# ANNEXE C — Ce que ce document ne fait pas

1. **Il ne remplace pas le gel.** Les décisions de la v1 sont dans le document de gel ; ici, tout est proposition, écarté, ou condition de réouverture.
2. **Il n'ordonne pas le travail.** Le séquencement est dans le plan d'implémentation (document 4/4).
3. **Il ne promet rien.** Aucune entrée n'a de date d'engagement ; plusieurs pourraient être abandonnées, et ce document prévoit explicitement que **la réfutation d'une hypothèse est un résultat**.
4. **Il ne cache pas les trous.** Les « NON TROUVÉ » sont écrits comme tels, et les lignes de coût qui ne sont pas chiffrables le disent.
5. **Il ne cite aucune source nommée qui ne soit publique.** Les renvois internes pointent vers des fichiers du dépôt ; les affirmations externes portent URL et date.

*Fin du document 3/4 — propositions, écartés et horizon V2. Statut : propositions **non gelées** ; rien ici ne modifie le gel v2 du 15 octobre 2026.*

