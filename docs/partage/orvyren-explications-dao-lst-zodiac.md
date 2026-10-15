# ORVYREN — EXPLICATIONS : DAO, trésoreries on-chain, Ethereum+Base+LST, critère de mesure, Zodiac Roles

**15 octobre 2026.** Réponses aux questions de l'équipe, avec exemples par région et chiffres sourcés (recherches U1/U2/P1 + vérifications du 15/10).

---

## 1. DAO, organisations DeFi — et qui a réellement une trésorerie on-chain ?

### Les définitions, simplement

**Une DAO** (Decentralized Autonomous Organization) : une organisation **sans siège ni patron**, dont les règles et la caisse vivent sur la blockchain. Les détenteurs d'un **token de gouvernance** votent les décisions — y compris les dépenses. Sa **trésorerie on-chain** est un (ou plusieurs) **coffre multi-signatures** que le vote contrôle : rien ne sort sans que les signataires désignés (ou un vote exécuté automatiquement) l'autorisent.

**Une organisation DeFi** : une organisation qui construit ou exploite un service financier sur la blockchain (échange, prêt, staking, stablecoin…). Sa structure typique est **double** :
- une **fondation / des labs** (une équipe avec un statut juridique classique) qui développe ;
- une **DAO** qui gouverne le protocole et **détient la trésorerie** (les frais générés, les tokens, les réserves).

### Qui a une trésorerie on-chain ? — les 7 familles

| Famille | Exemples | Ordre de grandeur |
|---|---|---|
| **DAOs de protocoles** (le cœur de cible) | Uniswap, Arbitrum, Lido, Aave, ENS, Sky, Optimism | des centaines de M$ à quelques Md$ |
| **Fondations / labs** | Uniswap Foundation, Ethereum Foundation (partiellement) | budgets opérationnels |
| **Sociétés de gestion embauchées par les DAOs** | karpatkey (GnosisDAO, Balancer, ENS), Steakhouse Financial (Sky, Lido), Block Analitica (Sky), Llama (Uniswap) | — *(ce sont les concurrents directs — et les futurs utilisateurs)* |
| **Desks & market makers** | Wintermute, GSR, Amber, Keyrock | inventaires de plusieurs Md$ |
| **Protocoles eux-mêmes** | coffres de sécurité (Aave Safety Module), bridges, L2 | réserves |
| **Fonds crypto** (hedge funds, VC) | inventaires partiellement on-chain | variable |
| **Entreprises crypto-natives et classiques** | exchanges, Coinbase ; trésoreries « bitcoin » (MicroStrategy, Metaplanet) | conservation surtout, peu de gestion active |

### Exemples par région (chiffres à leur date)

**Amérique du Nord** — les plus gros : **Uniswap DAO** (~2,3 à 4,8 Md$ selon la date, surtout en tokens UNI — la plus grosse trésorerie de DAO), **Arbitrum DAO** (~3,0 Md$ en 2023), **Optimism Collective**, **ENS DAO** (écosystème UK/US ; sa dotation est passée de ~890 M$ à 101,6 M$ puis 67,7 M$ — la chute est typique : les trésoreries fondent avec le marché). Côté entreprises : Coinbase, MicroStrategy.

**Europe** — **Sky (ex-MakerDAO)**, fondé au Danemark : ~2,1 Md$ de positions en actifs tokenisés (RWA) — l'exemple le plus sophistiqué ; **GnosisDAO** (Allemagne) ; **Aave** (Royaume-Uni) ; **Lido** (contributeurs européens) ; **Safe** (Allemagne — l'entreprise derrière le coffre multisig que tout le monde utilise).

**Asie** — **Mantle** (ex-BitDAO, lié à Bybit, Hong Kong) : une des plus grosses trésoreries mondiales (1,9–2,8 Md$), très diversifiée (ETH, USDC, USDT + token natif MNT) — **c'est l'exemple phare asiatique**. L'Asie a **moins** de grosses DAOs pour une raison simple : l'environnement réglementaire y est plus contraint ; les hubs sont Hong Kong, Singapour, Japon (Astar), avec des structures juridiques hybrides (fondations).

### Lecture pour ORVYREN

La cible n'est donc pas « les entreprises en général » mais **les organisations dont LA CAISSE EST SUR LA BLOCKCHAIN** : DAOs de protocoles, fondations crypto, fonds, desks. Leur point commun : **tout est public** (on peut lire leurs positions et leur historique), **elles paient déjà** pour de la gestion de trésorerie (karpatkey, Steakhouse…), et **elles ont déjà accepté** le principe d'une délégation bornée (voir §5, Zodiac).

---

## 3. « Ethereum + Base + LST » — pourquoi ce périmètre ?

### Pourquoi Ethereum est obligatoire

C'est là que vit **la profondeur réelle** : la majorité des stablecoins en circulation, la majorité des tokens de staking, les plus gros marchés de prêt (Aave) et d'échange (Uniswap). **Le « graphe de collatéral » du problème (section 02 du cadre) est essentiellement un graphe Ethereum.** Un agent qui ne regarderait que Base verrait une copie en réduction — il raterait le vrai risque.

### Pourquoi Base en plus

Base est une **couche 2 (L2)** : une chaîne construite **au-dessus d'Ethereum** (par Coinbase), qui exécute vite et **beaucoup moins cher**, tout en héritant de la sécurité d'Ethereum. Deux raisons de l'avoir :
1. **C'est le choix du concours** (thème F) — l'exécution démontrée y est économique ;
2. L'agent doit faire des **opérations fréquentes** (rééquilibrages, petites sorties) : les frais Ethereum les rendraient absurdes.

**Répartition logique** : *Ethereum = voir et protéger* (le collatéral réel), *Base = opérer* (exécution bon marché). Les deux sont utiles, pas redondants.

### Qu'est-ce qu'un LST ?

**LST = Liquid Staking Token.** Quand tu « stakes » (bloques) ton ETH pour gagner des intérêts, tu ne peux normalement plus le bouger. Avec un LST, tu reçois un **reçu utilisable** : par exemple Lido te donne **1 stETH pour 1 ETH staké**. Ce reçu : (a) continue de gagner le rendement de staking, (b) **s'échange et se prête comme n'importe quel token** — c'est donc devenu **l'un des tout premiers collatéraux** de la DeFi.

**rsETH** (= « restaked ETH ») : la version empilée — on prend du stETH (déjà un reçu), on le « restake » (Kelp/EigenLayer) pour un rendement supplémentaire. Même logique, **plus de couches de risque**.

### Pourquoi ils sont au centre de NOTRE problème

**Les LST sont du collatéral — donc le lieu où le risque vit.** Deux précédents réels :
- **Juin 2022** : pendant la crise Celsius/3AC, **stETH a décroché d'environ 7 %** par rapport à l'ETH (pénurie de liquidité pour en sortir) → les positions de prêt adossées au stETH ont vacillé ;
- **18 avril 2026** : incident **rsETH/KelpDAO ≈ 292 M$** — pont compromis, gel d'utilisation à 100 %, **fenêtre de réaction de 46 à 77 minutes**.

Le mécanisme est toujours le même : *un actif qui sert de garantie perd sa valeur ou sa liquidité → les prêts qu'il garantit deviennent risqués → si personne ne réagit, la perte cascade*. **Un agent qui ne surveille que les stablecoins raterait la moitié du problème (rsETH n'est pas un stablecoin).** D'où : stablecoins **+ LST** = le graphe de collatéral complet.

---

## 5. Le critère « perte évitée nette + temps de réaction » — expliqué

### Le problème que ce critère résout

Comment prouver qu'ORVYREN fait **mieux**, sans promettre de profit ? Un rendement dépend du marché : même un bon système peut perdre dans un mauvais marché, et un système inutile peut gagner par chance. Le « profit » est donc **invérifiable en peu de temps** — et le promettre serait malhonnête. La **perte évitée** et le **temps de réaction** dépendent, eux, de **notre système seul**. On peut les mesurer, les prouver, et en répondre devant un jury.

### « Perte évitée » — comment on la mesure concrètement

Sur le **même épisode**, avec la **même information disponible au même moment**, on compare trois comportements :
1. **A0 — ne rien faire** : le portefeuille subit (cas USDC : jusqu'à ~10 % de chute au pire du décrochage) ;
2. **A1 — la règle simple** (l'adversaire) : « si le prix passe sous 0,99 pendant 2 heures, réduire » ;
3. **A2 — ORVYREN** : analyse, décide, exécute dans son enveloppe.

On regarde la **valeur finale** de chaque portefeuille, **nette de tous les coûts** (frais de réseau, slippage, coût du raisonnement lui-même). **Perte évitée = ce que A2 préserve en plus de A0/A1.** Exemple : 100 k$ en trésorerie ; traversée du décrochage quasi intacte grâce à une réduction de 100 $ à temps, contre −10 k$ pour celui qui n'a rien fait → **perte évitée mesurée : quelques milliers de dollars sur cet épisode**, et on publie le chiffre avec son calcul.

**La précision qui rend le chiffre honnête — le regret** : on ne compare pas à la meilleure action « connue après coup » (personne n'est devin), mais à la meilleure action **réellement faisable sur le moment** : les options disponibles, le prix exécutable, la liquidité de l'instant. C'est ce qui distingue une mesure d'une fable.

### « Temps de réaction » — la valeur la plus incontestable

C'est le délai entre **le moment où l'information publique apparaît** et **le moment où l'action est exécutée**. Pourquoi c'est décisif pour notre cible : l'incident rsETH offrait une **fenêtre de 46 à 77 minutes** ; un trésorier humain qui dort, qui est en réunion ou qui panique ne l'attrape pas. Une **alerte sans exécution ne sauve rien** : ce qui compte est la chaîne complète *détecter → décider → exécuter*. C'est exactement ce qu'un agent fait et qu'un humain seul ne peut pas.

### Pourquoi ces deux-là, et pas « le rendement »

| Critère | Dépend de… | Prouvable en peu de temps ? |
|---|---|---|
| Rendement | du marché (pas de nous) | Non |
| Perte évitée | de notre décision et de nos coûts | **Oui** (sur épisodes documentés) |
| Temps de réaction | de notre architecture | **Oui, mécaniquement** |

**Conclusion proposée** : le critère principal = *« perte évitée nette sur épisodes documentés + temps de réaction mesuré »*, avec le rendement présenté plus tard, uniquement s'il est démontré hors échantillon.

---

## 6. Zodiac Roles — qu'est-ce que c'est, et pourquoi c'est notre verrou

### Le contexte : comment une DAO garde son argent

Une DAO garde sa trésorerie dans un **Safe** (ex-Gnosis Safe) : un **coffre-fort multi-signatures**. Pour en faire sortir un dollar, il faut par exemple **3 signatures sur 5 personnes**. C'est parfaitement sûr… et parfaitement inadapté au quotidien : chaque rééquilibrage hebdomadaire exigerait une réunion de signataires.

### La solution : Zodiac Roles

**Zodiac** est une boîte à outils de **modules** qui se branchent sur le Safe (construits par Gnosis Guild). Le module **Roles Modifier** permet de définir des **rôles autorisés** assignés à des adresses externes :

> *« L'adresse X peut appeler le contrat Y, avec la fonction Z, sur l'actif A, pour un montant ≤ N, sans autre signature. »*

Trois propriétés qui en font le verrou parfait pour ORVYREN :
1. **La limite est appliquée par le coffre lui-même, sur la blockchain** — pas par notre logiciel, pas par un accord de confiance. Même si l'agent est piraté ou « devient fou », il **ne peut pas** dépasser son rôle ;
2. **Le rôle est révocable** par un vote de la DAO — le pouvoir final reste aux humains ;
3. **Chaque élargissement est une décision de gouvernance** — l'agent ne peut jamais élargir lui-même ses droits (c'est notre règle T4, appliquée par la chaîne).

### C'est déjà en production chez une DAO majeure

**ENS DAO** a donné à **karpatkey** (société de gestion professionnelle) un rôle Zodiac v2 pour opérer son **fonds de dotation** : « seules les transactions pré-approuvées passent », et chaque nouvelle stratégie de rendement est un **vote** (propositions EP 5.12, EP 5.14 : *mise à jour des permissions de la dotation*). Autrement dit : **le modèle « agent/société qui exécute dans une enveloppe bornée, votée par la DAO » est déjà la pratique de l'écosystème** — ORVYREN ne demande pas d'inventer la confiance, il s'installe dans un standard accepté.

### Ce que ça donne chez nous — les deux verrous

```
DÉCISION (agent + LLM) → INTENTION structurée
        │
        ▼
VERROU 1 (hors chaîne, notre code)  : politique déterministe — plafonds, allowlists, expiration, idempotence
        │  ALLOW
        ▼
VERROU 2 (sur la chaîne, Zodiac)    : le Safe refuse tout ce qui sort du rôle voté par la DAO
        │
        ▼
EXÉCUTION par l'agent (il signe seul, dans son rôle) → reçu vérifié → journal
```

Le verrou 1 est le nôtre (rapide, flexible, testé). Le verrou 2 est celui de la chaîne (impossible à contourner par l'agent). **C'est la différence entre « notre logiciel promet de se limiter » et « la blockchain l'oblige »** — et c'est exactement ce que le thème F (« agent wallet ») attend.
