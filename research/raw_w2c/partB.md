
## (b) Précédents réels d'usage (2023-2026)

### b.1 ENS DAO × karpatkey — le cas de référence

**Mise en place (2023).** Le fonds de dotation ENS (Endowment) est logé dans une Safe contrôlée par
la DAO ; karpatkey (kpk) en est le gestionnaire de mandat, avec des **permissions bornées portées
par Zodiac Roles** et non par une garde de clés. Le fil d'origine décrit l'architecture : les fonds
sont transférés à « a newly created SAFE provided by kpk and owned by the DAO » et le mandat
s'exécute via « a list of Zodiac Roles Modifier permissions for the Manager Role »
([Endowment initiation, 20 janv. 2023](https://discuss.ens.domains/t/endowment-initiation/15952)).
Montants de l'époque : trésorerie totale **67,45 M$**, dotation initiale **32 298 ETH (~51,45 M$)**,
déploiement progressif en trois tranches mensuelles de ~33 %, 16 M$ conservés hors dotation (2 ans
de dépenses) ; stratégies ETH-neutres et USD-neutres sur Compound v2, Aura, Curve,
Stakewise/Uniswap v3 ; **100 % des rendements reconvertis en stablecoins**.

**Pourquoi ce montage compte.** Le gestionnaire ne détient **aucune clé** de la Safe : il détient un
rôle. « The Zodiac Roles Modifier facilitates karpatkey's proxy management of the Endowment by
ensuring that only pre-approved transactions, defined by the permissions policy voted on by the DAO,
can be executed » ([EP 5.12, mai 2024](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173)).
C'est **exactement le modèle T2 d'ORVYREN** : exécution autonome, mais dans une enveloppe que la
gouvernance fixe et que la chaîne applique.

**Migration v2 (EP 5.12, 2024, statut « Passed »).** Bascule vers Roles v2 avec apports directs pour
le cas d'usage agent : **allowances (plafonds de dépense)**, **outil de portée de calldata élargi**,
**conditions logiques avancées**, **compatibilité DeFi Kit**, **visualisation et comparaison de
politique dans l'app Roles**. La proposition cite explicitement les audits G0 Group et Omniscia
([docs.ens.domains/dao/proposals/5.12](https://docs.ens.domains/dao/proposals/5.12), consultée
2026-10-15 ; [fil de discussion](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173)).

**Extensions de permissions (EP 5.14, statut « Passed »).** Nouvelles permissions : dépôt osETH sur
Aave v3, staking/mint sur Stakewise v3 (Genesis Vault), pools WETH/osETH sur Balancer et Aura,
swaps (WETH↔osETH sur Balancer, USDC↔osETH sur Uniswap v3, RPL↔WETH, routes CoW Swap), et
**annulation d'ordre CoW** (« Unsign order on Cow Protocol »). Le texte indique : « the new
permissions have also been audited by ThirdGuard, an independent 3rd-party » et annonce que
**l'audit indépendant de la politique devient la pratique standard** pour les mises à jour de
permissions ([docs.ens.domains/dao/proposals/5.14](https://docs.ens.domains/dao/proposals/5.14),
consultée 2026-10-15). La proposition fournit les adresses (module `0x703806E6…0A40`, avatar
`0x4F2083f5…7FE64`), le lien du payload, un Safe de test, et l'URL de diff de permissions dans
l'app — le tout vérifiable.

**Régime de croisière (2026).** Le rythme des mises à jour s'accélère : EP 6.41 = « Update #9 »,
un « Update #10 » est en projet, et un *temp check* de juillet 2026 discute un **plafonnement
automatique (rate limiting) de l'Endowment** — la gouvernance qui resserre l'enveloppe une fois
l'exécution déléguée ([sidebar du fil sécurité ENS](https://discuss.ens.domains/t/security-update-zodiac-roles-modifier-v2-and-delay-modifier-v1-1-0/22161),
[Temp Check rate limiting](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234), consultés 2026-10-15).
**Ce que ça a coûté / rapporté** (revue kpk H1 2026, 14 août 2026) : frais **221 275 $ pour le
semestre (~0,50 % annualisé)**, rendement brut **3,12 %** contre **2,80 %** de benchmark (soit
2,62 % net), rendement produit **1,37 M$ ≈ 31 % des revenus de la DAO** sur la période ; les actifs
de l'Endowment baissent sur le semestre du fait du *mark* ETH, pas du rendement
([KPK H1 2026 Review](https://discuss.ens.domains/t/kpk-h1-2026-review-for-the-ens-endowment/22358),
page archivée dans `raw_u2/pages/`, consultée 2026-10-15). Les chiffres d'actifs : 101,6 M$ en
janvier 2026 → 67,7 M$ en juin 2026 (`research/U2_defi_organisations.md`, qui cite la revue).

**Leçon d'incident.** Lors de la faille ERC-1271 de juin 2026, la Safe de l'Endowment n'utilisait
pas le CompatibilityFallbackHandler : « no impact on the endowment » — et kpk ajoute que **même sans
le patch**, l'enveloppe de permissions aurait empêché toute perte. C'est l'argument le plus fort du
dossier : *la défense en profondeur a tenu* (source : fil sécurité ENS, 4 juin 2026).

### b.2 Autres organisations

| Organisation | Usage documenté | Source (consultée 2026-10-15) |
|---|---|---|
| **Balancer** | Migration Zodiac Roles Modifier v2 annoncée simultanément à celle d'ENS ; catégorie « Karpatkey Updates » active sur le forum Balancer | [post kpk (LinkedIn, 2024)](https://www.linkedin.com/posts/kpk-io_our-zodiac-roles-modifier-v2-migration-proposals-activity-7212789172007235584-RjNd) ; [catégorie forum](https://forum.balancer.fi/c/general-chat/karpatkey-updates/21) |
| **GnosisDAO** | GIP-148 (RFP de gestion de trésorerie) : « SAFE multisig, with Zodiac roles modifier permissions to be granted to » l'attributaire (Avantgarde) — modèle repris d'un mandat de gestion de trésorerie | [GIP-148](https://forum.gnosis.io/t/gip-148-request-for-proposals-treasury-management-services-for-gnosis-dao/11957) |
| **Scroll** | Réponse de kpk au RFP trésorerie : « We have developed a custom permissions layer based on the audited Zodiac Roles modifier to provide fine-grained control over treasury activities » ; de même, le RFP liste « Safe + Zodiac Roles Modifier (trust-minimized) » parmi les approches | [RFP Scroll](https://forum.scroll.io/t/request-for-proposals-dao-treasury-management/1047) |
| **Lagoon** | Documentation de curation : décrit Safe + Zodiac Roles comme le motif de délégation de curation | [docs.lagoon.finance](https://docs.lagoon.finance/curation-solutions/safe-and-zodiac-roles-modifier) |
| **Gnosis Pay / OZ** | Déploiements de masse (46 669 comptes touchés en juin 2026) — preuve de la généralité du motif module-Safe, pas un cas de trésorerie | [post-mortem](https://engineering.gnosisguild.org/posts/zodiac-post-mortem) |

### b.3 Ce que les précédents enseignent (utilisable dans une soutenance)

1. **Le motif a 3 ans de gouvernance** : ENS (2023→2026), Balancer, GnosisDAO, Scroll — les
   trésoreries savent et acceptent de voter une *politique de permissions*.
2. **Le coût explicite est la gouvernance** : chaque extension = proposition + audit de politique
   (ThirdGuard chez ENS) + diff public. Un agent qui n'ajoute **aucune** charge de gouvernance
   (parce qu'il n'exécute que dans l'enveloppe existante) est précisément ce que ces organisations
   peuvent acheter sans nouveau vote.
3. **Le risque est opérationnel, pas cryptographique** : les deux incidents de 2026 sont des bugs de
   *vérification de frontière* dans les adaptateurs, pas des casses de Safe ni du chiffrement ; la
   réponse a été patch + migration + alerte dans l'app. Un déployeur doit donc **suivre les versions**
   et **prévoir la migration** (procédure écrite, testée).
4. **La responsabilité du gestionnaire est encadrée par un mandat écrit** (IPS ENS, permissions
   votées) — pas par la confiance. C'est le cadre que l'agent doit épouser (§ f).

---

## (c) Alternatives au même niveau : comparaison

Toutes les lignes s'appuient sur du code vérifié ou de la documentation officielle, et indiquent ce
qui est **vérifiable** par un tiers. Vérifications RPC du 2026-10-15 en colonne dédiée.

### c.1 Tableau comparatif

| Primitive | Modèle | Plafonds / portée | Ce qui est vérifiable | État Base Sepolia (2026-10-15) | Verdict pour ORVYREN phase 1 |
|---|---|---|---|---|---|
| **Zodiac Roles v2** (Safe) | Module de compte : le rôle est membre, l'exécution passe par le module, la condition est évaluée **par la chaîne** | Allowances (`refill`/`maxRefill`/`period`), conditions par fonction et par paramètre, listes blanches de cibles/destinataires, quotas d'appels (`CallWithinAllowance`) | Tout : rôles, membres, portée et allowances lisibles on-chain ; événements `AssignRoles`/`ConsumeAllowance` ; app de diff ; subgraph | **Présent** : Roles `0xF296…83D5` (24 409 o, code identique mainnet/Base) + libs `Integrity`/`Packer`/`MultiSendUnwrapper` | **Retenu.** Seule primitive qui combine (i) conservation du même Safe, (ii) périmètre par fonction, (iii) plafonds + quotas, (iv) antécédent de gouvernance DAO |
| **Safe Allowance Module** | Module historique de la Safe : un « délégué » peut dépenser un token jusqu'à un plafond périodique | Uniquement ERC-20 : montant par période, par token ; **pas** de portée par fonction ni de liste de destinataires au niveau fonction | Contrat public, mais déploiement à vérifier par chaîne (l'adresse canonique **n'est pas** présente partout) | **Absent** sur Base Sepolia (`0xCFbFaC74…3134` → `0x`) ; présent sur Ethereum et Base mainnet (15 003 o, bytecode identique) | Non pour la phase 1 : pas de portée fonctionnelle, et **pas déployé sur le testnet de la démo** — un design qui s'appuie dessus ne serait pas démontrable |
| **ERC-7715 / ERC-7710** (MetaMask Smart Accounts Kit) | Permission *demandée par une app à un portefeuille* ; l'application est le bénéficiaire ; exécution via `DelegationManager` | Types de permission : transferts de tokens, flux, périodiques ; **la portée « appel de fonction arbitraire » n'est pas couverte par 7715** (elle passe par 7710/`createDelegation`) | Adresses de `DelegationManager` publiées ; code vérifiable ; spécification publique | **Présent** : `DelegationManager 0xdb9B1e94B5b69Df7e401DDbedE43491141047dB3` (11 503 o, code présent ETH/Base/Base Sepolia ; bytecode non identique entre chaînes) | Non en phase 1 : le flux 7715 est orienté « l'utilisateur autorise une app », pas « la DAO donne un mandat à un agent » ; et la portée fonctionnelle exige le chemin 7710, plus jeune. À suivre comme standard (live Polygon avril 2026, puis Arbitrum) |
| **Coinbase Spend Permissions** | Le `SpendPermissionManager` devient *propriétaire* du compte Coinbase Smart Wallet et déplace des tokens pour un `spender` | **Native + ERC-20 uniquement**, plafond par période, `start`/`end`, salt ; « does **not** enable apps to make arbitrary external calls » (README) | Adresse publiée, contrat public, code vérifiable | **Présent** : `0xf85210B21cC50302F477BA56686d2019dC9b67Ad` (12 610 o ; ETH non testé) | Non : périmètre trop étroit (pas d'appel arbitraire → pas de dépôt/retrait/supply DeFi) et suppose un compte Coinbase |
| **Session keys ERC-7579** (ZeroDev, Kernel, Rhinestone, Biconomy) | Validateurs modulaires sur comptes 7579 : une clé de session signe des appels, un module valide les règles | Variable : portée sur sélecteurs, plafonds, expiration — selon le validateur | Dépend de l'implémentation et du compte ; vérifiable on-chain mais **le compte doit être 7579** | Non applicable : Safe **n'est pas** un compte ERC-7579 ; la migration de compte est un prérequis | Non pour une DAO déjà sur Safe : changer de socle de garde pour obtenir l'enveloppe est un coût politique prohibitif |
| **Zodiac Delay Modifier** (complément) | Module de délai : les transactions passent par une file d'attente annulable | Pas un plafond : un **délai** de révélation/annulation | Contrat public, audité | Non testé (hors périmètre) | À utiliser **en complément** : c'est le bon outil pour le niveau T3 (hors enveloppe → approbation humaine) |

### c.2 Pourquoi Zodiac est le meilleur choix en phase 1 (argumentaire prêt à soutenir)

1. **Aucune migration de garde.** La cible (trésoreries DAO) est déjà sur Safe. Zodiac s'ajoute
   comme module ; l'agent ne change rien à la structure de propriété. Les alternatives 7579/Coinbase
   exigent, elles, un autre compte.
2. **Périmètre au niveau fonction ET paramètre.** C'est la seule primitive disponible aujourd'hui qui
   exprime « transférer USDC jusqu'à 100 par transaction, 300 par jour, uniquement vers X et Y » —
   les autres expriment des montants, pas des intentions.
3. **Antécédent de gouvernance accepté** (b.1/b.2) : la démonstration « ça s'insère dans un standard
   déjà voté » est faite dans le dossier par ENS, Balancer, GnosisDAO, Scroll — et **audité** (4
   rapports, plus des audits de politique côté ENS).
4. **Le verrou est vérifiable par un tiers** : permissions lisibles, événements on-chain, diffs
   publics. Un agent ORVYREN peut donc prouver *ce qu'il pouvait faire*, pas seulement ce qu'il a fait.
5. **Réversible en une transaction** (§ d.4) : la DAO garde le pouvoir d'arrêter, immédiatement et
   sans coordination technique avec ORVYREN.
6. **Open source, sans dépendance à un éditeur pour l'application de la politique** : la page
   sécurité de Zodiac revendique que l'interface n'est pas une dépendance requise pour l'exécution
   (« if it goes down you can sign through another interface or execute against the contracts
   directly » — https://www.zodiac.eco/security, 2026-10-15).

### c.3 Où Zodiac ne suffit PAS (et ce que ORVYREN doit apporter)

- **Le jugement** (prix, choix de venue, opportunité) reste hors-chaîne → politique hors-chaîne
  obligatoire (premier verrou), car les conditions Zodiac ne lisent ni oracle ni intention.
- **L'expiration** n'est pas native → planificateur de révocation + surveillance.
- **L'idempotence** n'existe pas on-chain : rejouer une transaction encore autorisée est *permis* par
  la chaîne → registre d'intentions hors-chaîne + quotas d'appels (`CallWithinAllowance`) comme
  amortisseur.
- **La télémétrie** : le module n'alerte pas → journal exportable et surveillance d'événements
  (c'est un des apports différenciants d'ORVYREN, pas une redite).

---
