
## (f) Cadre de responsabilité

### f.1 Le fait de départ (à citer, il donne la crédibilité au dossier)

Chaos Labs, en quittant son rôle de risk manager d'Aave (6 avril 2026), a écrit noir sur blanc ce
que le secteur ne dit pas d'habitude : « The first is legal and institutional exposure. Risk
management in DeFi, whether as a risk manager or vault curator, carries liability that remains
fundamentally undefined. There is no regulatory framework, no safe harbor, and no settled law that
answers the question of what a risk manager or curator owes when a protocol fails. If things work,
the work is invisible. If things break, the blame is not. »
Source : [Chaos Labs Is Leaving Aave](https://governance.aave.com/t/chaos-labs-is-leaving-aave/24386),
6-7 avril 2026, consulté 2026-10-15 ; reprise presse :
[crypto.news — « Chaos Labs exits Aave after risk clash and legal fears »](https://crypto.news/chaos-labs-exits-aave-after-risk-clash-and-legal-fears/) ;
contexte budgétaire (refus d'un budget de 5 M$, marge négative) :
[CoinDesk, 6 avril 2026](https://www.coindesk.com/tech/2026/04/06/aave-loses-key-risk-manager-chaos-labs-amid-contributor-exodus-and-disputes).
À noter aussi : LlamaRisk a repris la charge en critiquant le modèle « boîte noire » centralisé
([LlamaRisk, continuité](https://governance.aave.com/t/llamarisk-ensuring-continuity-of-aaves-risk-management/24397)).

**Traduction opérationnelle pour ORVYREN** : on ne peut pas promettre d'immunité juridique, et toute
formulation qui la suggérerait est fausse et dangereuse. Ce qu'on peut promettre, c'est un
**périmètre** et une **preuve**.

### f.2 Ce qu'on peut écrire honnêtement dans le dossier du concours

1. **Le mandat est voté, pas interprété.** L'agent n'agit que dans une politique que l'organisation
   a **votée et publiée on-chain** (chez ENS : propositions de permissions ; chez ORVYREN : la
   politique de permissions du module, versionnée, avec diff public). L'agent ne détient aucun
   pouvoir de la modifier (test #7).
2. **Le pire cas est un nombre.** Le dommage maximal est borné par des paramètres lisibles :
   `maxRefill` de l'allowance, liste blanche de destinataires, périmètre de fonctions, quotas
   d'appels. On peut écrire « pire cas par période = X USDC, vers ces 3 adresses » — c'est une
   phrase vérifiable, contrairement à « l'agent est sécurisé ».
3. **Le journal est opposable.** Chaque action est reliée à (i) une intention, (ii) un verdict de
   politique, (iii) un hash de transaction et (iv) un reçu de chaîne recoupé. Un tiers (DAO, auditeur,
   assureur, régulateur, juge) peut reconstituer qui a décidé quoi, avec le code de politique en
   vigueur. C'est exactement ce qui manque dans le modèle « boîte noire » décrié par LlamaRisk.
4. **L'humain garde le dernier mot structurellement.** L'agent ne peut **jamais** élargir ses droits :
   la clé d'administration reste dans la Safe de l'organisation (le dossier doit montrer que ce
   n'est pas une promesse mais une contrainte `onlyOwner` du contrat — test #7).
5. **La séparation des rôles est explicite.** ORVYREN fournit l'exécution bornée et la preuve ;
   l'organisation conserve la décision (politique, plafonds, venants) et le kill switch. Toute
   répartition de responsabilité se lit alors dans un document **et** dans le code — c'est la
   meilleure position disponible tant que « no settled law » reste vrai.
6. **Les limites amont sont recopiées, pas contournées.** Contrats « WITHOUT ANY WARRANTY »
   (README Zodiac) ; LGPL-3.0+ ; audit G0/Omniscia et historique d'incidents (a.6) cités dans
   l'annexe risque, avec les patchs appliqués et la procédure de migration.

### f.3 Ce qu'il ne faut PAS écrire (pièges classiques)

- « La blockchain nous décharge juridiquement » — faux : la chaîne prouve les faits, elle ne répartit
  pas la responsabilité.
- « La responsabilité est transférée à la DAO » — non : le prestataire conserve la responsabilité de
  ce qu'il **construit** (politique mal écrite, clé mal gardée, bug d'orchestration), la DAO de ce
  qu'elle **décide** (mandat, plafonds).
- « L'agent est audité » si seuls les contrats amont le sont : chez ENS, la pratique est d'auditer
  **la politique de permissions** elle-même (ThirdGuard, EP 5.14). À reprendre : auditer la
  politique, pas seulement hériter de l'audit du module.
- Toute affirmation de type « zéro risque », « impossible à détourner » : contredite par les deux
  incidents de 2026 documentés en a.6.

### f.4 Ce que l'enveloppe + le journal apportent, concrètement

| Bénéfice | Preuve à montrer |
|---|---|
| **Délimitation du mandat** (ce que l'agent pouvait faire) | Politique de permissions on-chain + diff public + version de politique dans le journal |
| **Traçabilité complète** (ce qu'il a fait, et pourquoi) | JSONL chaîné + reçus + logs `Transfer` + `ConsumeAllowance` |
| **Interruption unilatérale par l'organisation** | `assignRoles(...,false)` / `disableModule` — 1 transaction, sans dépendre d'ORVYREN (§ d.4) |
| **Recevabilité en cas de litige** | Chaîne de hash + équivalence intention/exécution vérifiée indépendamment |
| **Base d'assurance / souscription** | Pire cas chiffré + historique d'exécution vérifiable = données qu'un assureur peut tarifer |
| **Réduction du risque d'exploitation** | Pas de clé chez le gestionnaire (le modèle ENS) + plafonds + liste blanche |

*Note de méthode* : ce document ne constitue pas un avis juridique ; les formulations ci-dessus sont
choisies parce qu'elles restent vraies indépendamment du droit applicable (le point Chaos Labs
établit qu'aucun cadre stabilisé n'existe au 6 avril 2026 — c'est la seule affirmation juridique
sourçable).

---

## (g) Plan de démo testnet — le double verrou (Base Sepolia, chainId 84532)

**Ce que la démo doit prouver en 8 minutes** : (1) l'agent exécute **seul** dans l'enveloppe ;
(2) la politique hors-chaîne refuse ce qui sort de l'enveloppe **avant** toute signature ;
(3) **même si on force l'exécution**, la chaîne refuse ; (4) la DAO peut arrêter l'agent en une
transaction ; (5) tout est vérifiable dans un journal exportable.

### g.0 Prérequis et adresses (vérifiés le 2026-10-15 sur Base Sepolia)

| Objet | Adresse / valeur | Statut |
|---|---|---|
| Roles Modifier v2 (module) | `0xF2964CE6161ce0e75964Fe7927cE114cb0B283D5` | code présent, 24 409 o |
| Bibliothèques du module | `Integrity 0x6a6Af4b1…1049` · `Packer 0x869718c9…09f0` · `MultiSendUnwrapper 0xB4Cd4bb7…efD` | code présent |
| SafeL2 singleton 1.4.1 | `0x29fcB43b46531BcA003ddC8FCB67FFE91900C762` | code présent |
| SafeProxyFactory 1.4.1 | `0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67` | code présent |
| MultiSendCallOnly 1.4.1 | `0x40A2aCCbd92BCA938b02010E17A5b8929b49130D` | code présent |
| USDC de test (Circle) | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` | code présent (1 798 o) |
| WETH pré-déploiement | `0x4200000000000000000000000000000000000006` | pré-déploiement OP-stack |
| RPC | `https://sepolia.base.org` | `eth_chainId` = `0x14a34` |

**Note de déploiement importante** : le module Roles est un **module par avatar**. L'adresse
`0xF296…83D5` est le déploiement « officiel » (même clé sur 18 chaînes) ; pour le démo on déploie
**sa propre instance** de module pour la Safe de démonstration (script du dépôt `packages/evm`), puis
on l'active. Ne pas réutiliser une instance qui appartient à quelqu'un d'autre — « non trouvé »
indique qu'une instance partagée multi-avatars n'est pas le modèle documenté.

**Encodage des clés** : rôle `AGENT` →
`0x4147454e54000000000000000000000000000000000000000000000000000000` (étiquette ≤ 32 caractères
`a-z 0-9 _`) ; allowance `usdc_daily` → même principe. Source de la règle :
[tutoriel Gnosis Guild](https://github.com/gnosisguild/zodiac-modifier-roles/blob/main/packages/docs/content/tutorials/lower-threshold-routine-transactions.mdx) (2026-10-15).

### g.1 Étape 0 — Montage (scripté, à faire la veille)

1. **Créer la Safe « DAO » 2/3** sur Base Sepolia (Safe{Wallet} ou `safe-cli`) — 3 clés de test
   distinctes, seuil 2. **Vérifier** : `eth_getCode` de la Safe ≠ `0x`.
2. **Déployer + activer le module Roles** sur cette Safe (script `packages/evm`, ou app Zodiac) ;
   renseigner `owner` = la Safe, `avatar` = la Safe, `target` = la Safe (appel `setUp`).
   **Vérifier** : événement `RolesModSetup` dans le reçu ; `Roles.owner()` = Safe.
3. **Définir la politique** (app Roles / SDK / DeFi Kit) :
   - rôle `AGENT`, cible `USDC` (`0x036CbD…CF7e`), **fonction scopée** `transfer(address,uint256)` ;
   - condition sur le paramètre 0 (destinataire) : `Or(EqualTo(B), EqualTo(C))` ;
   - condition sur le paramètre 1 (montant) : `WithinAllowance(usdc_daily)` ;
   - allowance `usdc_daily` : `refill = 300e6`, `maxRefill = 300e6`, `period = 86400`
     (USDC a 6 décimales) ; option démo « à usage unique » : `period = 0` ;
   - quota d'appels : `CallWithinAllowance(calls_daily)` = 10/jour (amortisseur anti-rejeu) ;
   - **rien d'autre** : aucune autre cible, aucun `Clearance.Target` large.
4. **Créer le signer agent** : EOA dédiée (clé hors dépôt, hors logs, hors LLM) ; **lui assigner le
   rôle** : `assignRoles(agentEOA, [AGENT], [true])` (auto-active le module si besoin).
   **Vérifier** : `Roles.roles(AGENT).members(agent)` → `true` (via `eth_call`).
5. **Financer le gaz** : envoyer du testnet ETH à l'agent (robinet Base Sepolia). **Vérifier** :
   solde > 0, `eth_call` d'une transaction témoin.
6. **Alimenter la Safe** : USDC de test (robinet Circle, Base Sepolia) vers la Safe. Noter le solde
   de départ (`balanceOf(Safe)`).
7. **Écrire la politique hors-chaîne** (fichier versionné `policy.yaml` + code) : plafond par
   transaction 100 USDC, compteur **glissant** 24 h 300 USDC, destinataires autorisés {B, C},
   chaîne épinglée 84532 (et 8453 en prod), prix de référence / bornes de slippage si swap.
   **La politique est exécutée par un module déterministe, pas par le LLM.**

### g.2 Étape 1 — RUN A : ALLOW dans l'enveloppe (les deux verrous disent oui)

1. Intention : `transfer(dest=B, 50 USDC)`.
2. **Verrou 1 (hors-chaîne)** : verdict `ALLOW` — règles : `cap_tx_100 ✓`, `rolling_24h_300 ✓`
   (50 ≤ 300), `dest_in_allowlist ✓`, `chain=84532 ✓`, `intent_not_seen ✓`.
   Journal : `INTENT` + `POLICY{ALLOW}`.
3. Pré-vol : `eth_call` sur
   `Roles.execTransactionWithRole(USDC, 0, transfer(B,50e6), 0, AGENT, true)` depuis l'adresse agent
   → simulation `true` (pas de revert).
4. Envoi : tx signée par l'agent → **reçu `status = 0x1`**.
5. **Vérifications indépendantes** (à afficher à l'écran) :
   - `eth_getTransactionReceipt` : statut `0x1`, adresse du contrat module dans les logs ;
   - log `Transfer` (topic0 `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`)
     avec `from = Safe`, `to = B`, `value = 50000000` ;
   - `balanceOf(Safe)` et `balanceOf(B)` avant/après (`eth_call`, sélecteur `0x70a08231`) ;
   - **consommation d'allowance** : lire l'allowance `usdc_daily` (ou l'événement `ConsumeAllowance`)
     → `balance = 250e6` ;
   - entrée `RECEIPT` + `VERIFY` dans le journal.

### g.3 Étape 2 — RUN B : DENY par la politique hors-chaîne (le LLM propose, le système refuse)

1. Deux intentions de refus à jouer (les deux doivent produire **zéro transaction**) :
   - **B1** : `transfer(dest=B, 150 USDC)` → dépasse le plafond par transaction (100) et, cumulé,
     le glissant 24 h (50 + 150 > 300) → `DENY{cap_tx_100}` ;
   - **B2** : `transfer(dest=D_non_listé, 20 USDC)` → `DENY{dest_in_allowlist}` (attaque #12).
2. **Preuve du refus** : afficher la ligne de journal (`POLICY{DENY, rule, reason}`), le **compteur de
   signatures = 0** du service de signature, et l'absence de tout `tx_hash`. Vérifier
   `balanceOf(Safe)` inchangé et `nonce` de l'agent inchangé.
3. Variante « l'agent insiste » : rejouer 3 fois → journal : 3 refus, 0 signature (idempotence #1).

### g.4 Étape 3 — RUN C : DENY par la chaîne (on contourne volontairement le verrou hors-chaîne)

But : montrer que **la sécurité ne repose pas sur le logiciel ORVYREN**. On prend la clé de l'agent
et on fabrique **directement** le calldata de la transaction interdite (comme le ferait un attaquant
qui a volé la clé) — attaque #11.

1. **C1** : `execTransactionWithRole(USDC, 0, transfer(B, 500e6), 0, AGENT, true)` —
   au-delà de l'allowance → **revert** (`AllowanceExceeded` côté module ; la tx est incluse avec
   `status = 0x0` — le gaz est perdu, c'est le coût de l'attaque).
2. **C2** : `execTransactionWithRole(USDC, 0, transfer(D_non_listé, 1e6), 0, AGENT, true)` →
   **revert** (condition de destinataire ; attaque #12).
3. **C3 (admin)** : depuis la clé agent, appeler `Roles.allowTarget(...)` puis
   `Safe.enableModule(attaquant)` → **reverts** `onlyOwner`/`GS*` (attaque #7).
4. **C4 (chaîne)** : répéter la boucle « 100 + 100 + 100 + 100 » → la 4ᵉ revert
   (dépassement cumulé #8) ; et démontrer la **frontière de période** (#2) : deux tx encadrant la
   frontière passent on-chain (limite assumée) mais **le compteur glissant hors-chaîne refuse la
   seconde** — le journal montre `DENY{rolling_24h_300}` à côté de deux exécutions chaîne acceptées.
5. **Preuve affichée** : statuts `0x0`, sélecteurs de revert capturés dans le journal, soldes
   inchangés (aucun `Transfer` émis), et une capture d'écran de l'onglet *Permissions* de l'app
   Roles montrant la politique exacte.

### g.5 Étape 4 — KILL SWITCH (mesuré)

1. L'agent soumet une intention `ALLOW` (100 USDC) — mais **avant** l'exécution, la DAO exécute
   `assignRoles(agent, [AGENT], [false])` (2 signatures sur 3).
2. `chronométrer` : (a) temps de collecte des signatures, (b) temps jusqu'à l'inclusion
   (Base ~2 s/bloc), (c) l'effet : la tx de l'agent **revert** (`NoMembership`) ; le rôle est
   inactif.
3. Variante K2 : `disableModule(prev, rolesModule)` → même effet, périmètre plus large.
4. **Message de la démo** : « l'organisation arrête l'agent sans nous appeler, avec ses propres
   clés, en une transaction » — et « le seul délai non compressible est humain ».
5. Reset pour la suite : ré-assigner le rôle (`assignRoles(...,true)`), journaliser la fenêtre
   d'arrêt.

### g.6 Étape 5 — Journal et audit (la partie qui vend ORVYREN)

1. Exporter `audit.jsonl` (chaîne de hash) + un rapport lisible (`report.md`).
2. **Vérification indépendante** en direct : un script relit les `tx_hash` via
   `eth_getTransactionReceipt`, recalcule les transferts depuis les logs et compare à l'intention
   → « 3 exécutions conformes, 4 refus, 1 tentative forcée refusée par la chaîne ».
3. Optionnel mais fort : afficher le **diff de politique** de l'app Roles
   (`roles.gnosisguild.org/<chaîne>:<safe>/...`) pour prouver l'état exact de l'enveloppe au moment
   des faits.

### g.7 Ce que la démo ne prouve PAS (à dire avant qu'on le demande)

- Le **prix** et la qualité d'exécution (testnet non représentatif — cf. skill
  `evm-onchain-verification` : « Testnet prices are not market data ») ;
- l'**absence de bug** dans le module amont (deux incidents 2026 documentés → on suit les versions et
  on teste le commit déployé, #5) ;
- l'**expiration native** des permissions (elle n'existe pas : limite assumée, #9) ;
- l'**annulation** d'une transaction déjà incluse (#3) ;
- la **conformité juridique** dans une juridiction donnée (§ f.3).

### g.8 Parité production (une ligne pour le dossier)

Sur mainnet, la même démo devient : Safe réelle de la trésorerie → module Roles déployé pour cette
Safe (mêmes contrats, mêmes conditions) → membre de rôle = signer isolé de l'agent → politique
hors-chaîne inchangée → kill switch = vote/signature de la DAO. **Ce qui change n'est pas
l'architecture, c'est le montant du `maxRefill`.**

---

## Annexe 1 — Sources (consultées le 2026-10-15 sauf mention)

1. Docs Zodiac Roles — introduction : https://docs.roles.gnosisguild.org/
2. Docs — Conditions (paramType, opérateurs) : https://docs.roles.gnosisguild.org/general/conditions
3. Docs — Allowances (structure, période, consommation) : https://docs.roles.gnosisguild.org/general/allowances
4. Dépôt + README (adresses, audits, licence) : https://github.com/gnosisguild/zodiac-modifier-roles et https://raw.githubusercontent.com/gnosisguild/zodiac-modifier-roles/main/README.md
5. Code source lu : `Roles.sol`, `Types.sol`, `AllowanceTracker.sol`, `PermissionBuilder.sol`, `ModuleManager.sol` (Safe v1.4.1) — URLs `raw.githubusercontent.com` correspondantes.
6. Tutoriel « Lower Safe Threshold for Routine Transactions » : https://github.com/gnosisguild/zodiac-modifier-roles/blob/main/packages/docs/content/tutorials/lower-threshold-routine-transactions.mdx
7. Post-mortem ERC-1271 (v2.1.0 → v2.1.1), 19 juin 2026 : https://engineering.gnosisguild.org/posts/zodiac-post-mortem
8. Rapport de contournement MultiSend (padding ABI) : https://grego.ai/reports/safe-abi-padding-permission-checks
9. Page sécurité Zodiac : https://www.zodiac.eco/security
10. Rapports d'audit : https://github.com/gnosisguild/zodiac-modifier-roles/tree/main/packages/evm/docs (4 PDF : G0 Group avr. 2023, Omniscia mai 2023, Omniscia nov. 2023, G0 Group nov. 2023)
11. ENS — Endowment initiation (20 janv. 2023) : https://discuss.ens.domains/t/endowment-initiation/15952
12. ENS — EP 5.12 (Roles v2 migration) : https://docs.ens.domains/dao/proposals/5.12 et https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173
13. ENS — EP 5.14 (nouvelles permissions, audit ThirdGuard) : https://docs.ens.domains/dao/proposals/5.14
14. ENS — mise à jour sécurité Zodiac (4 juin 2026) : https://discuss.ens.domains/t/security-update-zodiac-roles-modifier-v2-and-delay-modifier-v1-1-0/22161
15. ENS — Temp Check « rate limiting » (juillet 2026) : https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234
16. ENS — revue kpk H1 2026 (14 août 2026 ; frais 221 275 $, brut 3,12 %, net 2,62 %, 1,37 M$ de rendement) : https://discuss.ens.domains/t/kpk-h1-2026-review-for-the-ens-endowment/22358
17. karpatkey DeFi Kit : https://kit.karpatkey.com/ et https://github.com/karpatkey/defi-kit
18. GnosisDAO — GIP-148 : https://forum.gnosis.io/t/gip-148-request-for-proposals-treasury-management-services-for-gnosis-dao/11957
19. Scroll — RFP trésorerie (réponse kpk) : https://forum.scroll.io/t/request-for-proposals-dao-treasury-management/1047
20. Balancer — catégorie « Karpatkey Updates » : https://forum.balancer.fi/c/general-chat/karpatkey-updates/21 ; annonce kpk (2024) : https://www.linkedin.com/posts/kpk-io_our-zodiac-roles-modifier-v2-migration-proposals-activity-7212789172007235584-RjNd
21. Aave — « Chaos Labs Is Leaving Aave » (6 avril 2026) : https://governance.aave.com/t/chaos-labs-is-leaving-aave/24386 ; couverture : https://crypto.news/chaos-labs-exits-aave-after-risk-clash-and-legal-fears/ ; https://www.coindesk.com/tech/2026/04/06/aave-loses-key-risk-manager-chaos-labs-amid-contributor-exodus-and-disputes ; réponse LlamaRisk : https://governance.aave.com/t/llamarisk-ensuring-continuity-of-aaves-risk-management/24397
22. Safe — déploiements v1.4.1 (JSON officiels) : `safe-deployments` (proxy_factory, safe_l2, multi_send_call_only, compatibility_fallback_handler)
23. Safe Allowance Module — adresse canonique `0xCFbFaC74…3134` (module historique `safe-modules`) ; absent de Base Sepolia (vérifié le 2026-10-15)
24. Coinbase Spend Permissions — README (adresses + périmètre) : https://raw.githubusercontent.com/coinbase/spend-permissions/main/README.md ; docs CDP : https://docs.cdp.coinbase.com/coinbase-wallet/improve-ux/spend-permissions
25. MetaMask Smart Accounts Kit — délégation (ERC-7710) : https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview ; déploiements : https://github.com/MetaMask/delegation-framework/blob/main/documents/Deployments.md
26. ERC-7715 — état et limites (types de permission ; portée fonction = 7710) : https://relay.link/blog/erc-7715-agentic-payments-crosschain (live Polygon, avril 2026) ; https://github.com/MetaMask/smart-accounts-kit/issues/263 (11 juin 2026)
27. RPC utilisés : `https://ethereum-rpc.publicnode.com` (0x1), `https://mainnet.base.org` (0x2105), `https://sepolia.base.org` (0x14a34) — `eth_getCode`, `eth_blockNumber`, `eth_chainId`, 2026-10-15
28. Contexte interne projet : `research/U2_defi_organisations.md`, `research/CADRE_DEFINITION_01-06.md`, `raw_u2/pages/discuss_ens_domains_t_kpk_h1_2026_review_for_the_ens_endowment_22358.txt`

## Annexe 2 — Ce qui est resté « non trouvé » (à ne pas inventer)

1. **Date de publication du rapport grego.ai** sur le contournement MultiSend — absente de la page.
2. **Version exacte de `MultiSendUnwrapper` déployée** sur Base Sepolia (le correctif est identifié
   par un commit, pas par une adresse/version lisible) → à déterminer avant la démo (comparer le
   sha256 du code déployé avec un build du commit corrigé).
3. **Montant notionnel exact des permission updates ENS 2026** (le nombre de propositions est
   documenté — Update #8/#9, #10 en projet — mais pas de tableau chiffré par mise à jour).
4. **Coût des audits de politique ThirdGuard** (aucun montant public trouvé).
5. **Instance Roles partagée multi-avatars** : le modèle documenté est « un module par avatar » ;
   aucune source ne décrit de déploiement mutualisé (le déploiement déterministe produit la même
   adresse sur des chaînes différentes, pas sur des avatars différents d'une même chaîne).
6. **Frais kpk pour Balancer / GnosisDAO** (les 0,50 % sont documentés pour ENS ; « non trouvé »
   pour les autres mandats dans les pages consultées).
7. **Délai contractuel d'un kill switch** : aucune source ne chiffre un SLA de révocation ;
   la latence annoncée en § d.4 est une mesure de chaîne (blocs Base ~2 s) + coordination humaine,
   pas un engagement contractuel.
8. **Données de testnet représentatives pour les swaps** (profondeur, prix) : non disponibles par
   construction — la qualité d'exécution se teste en simulation sur des données réelles.

## Annexe 3 — Fournisseur d'incidents et veille (à intégrer au runbook)

- Suivre les communiqués Zodiac/Gnosis Guild (compte `@zodiaceco`, `engineering.gnosisguild.org`) et
  **vérifier la version du module** avant chaque période d'exécution.
- L'app Roles signale les modules sur une version vulnérable et propose la migration (grego.ai,
  2026-10-15) — intégrer cette vérification au démarrage de l'agent (test automatique).
- Surveiller les événements `AssignRoles`, `SetDefaultRole`, `ConsumeAllowance` ; alerter sur toute
  exécution hors du profil attendu (destinataire nouveau, montant inhabituel, rafale).
