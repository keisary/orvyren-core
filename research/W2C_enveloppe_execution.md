# W2-C — L'enveloppe d'exécution réelle : Zodiac Roles v2, signer limité, sécurité, responsabilité, démo testnet

**Projet ORVYREN** — agent wallet on-chain autonome borné (concours FinTech Shenzhen 2026, thème F).
**Rédigé le 2026-10-15 (UTC)**. Méthode : sources primaires uniquement (dépôts, docs officielles,
propositions de gouvernance, RPC public), chaque adresse vérifiée par `eth_getCode` sur la chaîne
concernée. Toute affirmation non sourçable est marquée **« non trouvé »**. La matière brute et les
preuves RPC sont archivées dans `research/raw_w2c/` (voir `raw_w2c/W2C_evidence_verifications.md`).

**Ce que ce document tranche** : (a) l'enveloppe native à utiliser en phase 1 est **Zodiac Roles
Modifier v2** sur Safe, parce qu'elle est *déjà* le standard des trésoreries DAO et qu'elle porte
trois verrous que les alternatives n'ont pas ; (b) le signer de l'agent doit être une **EOA isolée
membre d'un rôle** (aucune clé dans le LLM, aucun droit d'administration) ; (c) la démo testnet
prouve le double verrou **ALLOW / DENY-hors-chaîne / DENY-par-la-chaîne** sur Base Sepolia, avec un
kill switch mesuré et un journal d'audit vérifiable.

### Résumé exécutif (10 lignes)

1. **L'enveloppe existe déjà et elle est déployée** : le contrat `Roles` de Zodiac
   (`0xF2964CE6161ce0e75964Fe7927cE114cb0B283D5`) a **exactement le même bytecode** (24 409 o,
   sha256 `bf4438c3197d3ecc…`) sur Ethereum, Base et **Base Sepolia** — vérifié par `eth_getCode`
   le 2026-10-15 ; ses bibliothèques (`Integrity`, `Packer`, `MultiSendUnwrapper`) sont présentes sur
   le testnet de la démo.
2. **Le bon modèle d'autonomie est T2 dans une enveloppe déjà votée** : un rôle `bytes32` avec
   périmètre par cible/fonction/paramètre, **allowances** (`refill`/`maxRefill`/`period`) et quotas
   d'appels — la « clé » de l'agent n'est pas un accès au trésor, c'est **un mandat**.
3. **Le précédent est ENS × karpatkey** (2023→2026, EP 5.12/5.14, Updates #8/#9/#10), plus Balancer,
   GnosisDAO et Scroll : la gouvernance accepte de voter une politique de permissions, et l'usage a
   tenu face à un incident majeur (juin 2026 : l'Endowment ENS a été confirmé non affecté).
4. **Les alternatives sont soit trop étroites** (Coinbase Spend Permissions : pas d'appel arbitraire ;
   Safe Allowance Module : pas de portée fonctionnelle **et absent de Base Sepolia**), **soit un
   changement de socle** (session keys ERC-7579, ERC-7715/7710 dont la portée fonctionnelle n'est pas
   couverte par le flux 7715).
5. **Deux limites on-chain à écrire, pas à cacher** : pas d'expiration native d'une permission ;
   rafraîchissement des allowances **par intervalles entiers** → rafale possible jusqu'à
   `maxRefill + refill` sur deux blocs (d'où un compteur **glissant** hors-chaîne comme premier verrou).
6. **Deux incidents amont en 2026** (contournement ERC-1271 de v2.1.0, ~85 M$ de valeur attribuable
   sécurisée à 99,77 % ; contournement de frontière MultiSend) — donc : suivre les versions, tester le
   commit déployé, prévoir la migration.
7. **Le signer** est une EOA dédiée, membre du rôle, qui paie son gaz, sans aucun droit
   d'administration (testé : `allowTarget`/`assignRoles`/`enableModule` revert depuis cette clé).
8. **Kill switch** : `assignRoles(...,false)` ou `disableModule` par la DAO — 1 transaction, bloc Base
   mesuré à 1,64 s ; ce qui reste non compressible est humain ; une transaction déjà incluse n'est pas
   annulable (à dire).
9. **Responsabilité** : la seule affirmation juridique sourçable est celle de Chaos Labs (avril 2026) —
   la responsabilité du risk management DeFi « remains fundamentally undefined ». Ce qu'on peut
   vendre, c'est un **mandat délimité** + un **journal opposable**, pas une immunité.
10. **La démo** : 5 étapes sur Base Sepolia — ALLOW dans l'enveloppe ; DENY hors-chaîne (zéro
    signature) ; DENY par la chaîne (exécution forcée avec la clé agent → revert) ; kill switch
    chronométré ; journal exporté et revérifié contre la chaîne.

### Sommaire

(a) [Zodiac Roles v2 : mécanique exacte, déploiements vérifiés, limites](#a-zodiac-roles-v2--mécanique-exacte-déploiements-vérifiés-limites) ·
(b) [Précédents réels d'usage](#b-précédents-réels-dusage-2023-2026) ·
(c) [Alternatives au même niveau : comparaison](#c-alternatives-au-même-niveau--comparaison) ·
(d) [Architecture du signer limité](#d-architecture-du-signer-limité) ·
(e) [Matrice des 12 attaques](#e-matrice-des-12-attaques) ·
(f) [Cadre de responsabilité](#f-cadre-de-responsabilité) ·
(g) [Plan de démo testnet](#g-plan-de-démo-testnet--le-double-verrou-base-sepolia-chainid-84532) ·
[Annexe 1 — Sources](#annexe-1--sources-consultées-le-2026-10-15-sauf-mention) ·
[Annexe 2 — « non trouvé »](#annexe-2--ce-qui-est-resté--non-trouvé--à-ne-pas-inventer) ·
[Annexe 3 — Veille](#annexe-3--fournisseur-dincidents-et-veille-à-intégrer-au-runbook)

---

## (a) Zodiac Roles v2 : mécanique exacte, déploiements vérifiés, limites

### a.1 Ce qu'est le module

Zodiac Roles Modifier est un **module de compte intelligent** (Gnosis Guild) qui s'attache à un
avatar — typiquement un Safe — et impose une politique de permissions par rôle sur les appels que
le rôle déclenche. Le contrat « miroir » l'interface du Safe, ce qui lui permet de se placer
**entre les modules et le Safe** : `Zodiac Roles Modifier is an onchain permissions module for
smart accounts. […] The smart contract module attaches to any avatar (a Safe or other web3
account)` ([docs.roles.gnosisguild.org](https://docs.roles.gnosisguild.org/), consulté 2026-10-15).
Licence LGPL-3.0+, Solidity 0.8.21, evm shanghai ; dépôt
[gnosisguild/zodiac-modifier-roles](https://github.com/gnosisguild/zodiac-modifier-roles)
(dernier commit vu : `3a429ab` du 13 oct. 2026, consulté 2026-10-15).
Le dépôt est explicite sur l'avertissement légal : `All contracts are WITHOUT ANY WARRANTY; without
even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE` (README, 2026-10-15).

### a.2 Mécanique exacte (lue dans le code source, 2026-10-15)

**Clés et structure.** Un rôle est identifié par une **clé `bytes32`** (étiquette ≤ 32 caractères,
jeu `a-z 0-9 _` — tutoriel
[« Lower Safe Threshold for Routine Transactions »](https://github.com/gnosisguild/zodiac-modifier-roles/blob/main/packages/docs/content/tutorials/lower-threshold-routine-transactions.mdx)).
Chaque rôle porte : des **membres** (`mapping(address => bool)`), des **cibles** (`TargetAddress {
Clearance clearance; ExecutionOptions options; }`) et une **config de portée** par fonction
(`mapping(bytes32 => bytes32) scopeConfig`). `Clearance ∈ {None, Target, Function}` et
`ExecutionOptions ∈ {None, Send, DelegateCall, Both}` (`Types.sol`, consulté 2026-10-15).
Autrement dit : un rôle autorise une **liste blanche de cibles**, et pour chaque cible soit
« toute la cible » (`Clearance.Target`), soit **uniquement certaines fonctions** avec **conditions
sur les paramètres** (`Clearance.Function`). Tout ce qui n'est pas explicitement autorisé est refusé
par défaut.

**Flux d'exécution.** Le membre du rôle (module ou EOA — voir a.5) appelle :
`execTransactionWithRole(address to, uint256 value, bytes data, Operation operation, bytes32
roleKey, bool shouldRevert) → bool` (ou `execTransactionWithRoleReturnData`, qui renvoie les
données de retour). Le module évalue la politique (`_authorize`), prépare le **débit des
allowances** (`_flushPrepare`), exécute (`exec(to, value, data, operation)` — c'est-à-dire
`avatar.execTransactionFromModule(...)`), puis **ne consomme les allowances que si l'exécution a
réussi** (`_flushCommit` ; la docs le confirme : « If the condition evaluates to false or executing
the call reverts, allowances will not be updated »
[docs — Conditions](https://docs.roles.gnosisguild.org/general/conditions)). Si
`shouldRevert = true` et que l'appel échoue, tout est annulé (`ModuleTransactionFailed`).
Source : `Roles.sol`, lignes 153-200, https://raw.githubusercontent.com/gnosisguild/zodiac-modifier-roles/main/packages/evm/contracts/Roles.sol (2026-10-15).

**Octroi / modification.** `assignRoles(address module, bytes32[] roleKeys, bool[] memberOf)
external onlyOwner` — « Assign (true) or revoke (false) ». `assignRoles` **active aussi le module**
sur l'avatar s'il ne l'est pas (`if (!isModuleEnabled(module)) enableModule(module);`). Les
fonctions de construction de permissions sont : `allowTarget`, `revokeTarget`, `scopeTarget`,
`allowFunction`, `revokeFunction`, `scopeFunction`, `setAllowance`
(`PermissionBuilder.sol`, lignes 57-158, consulté 2026-10-15). Chaque changement est un **appel du
propriétaire du module** (le Safe de la DAO, donc une transaction gouvernée) et émet un événement
`AssignRoles` / `SetDefaultRole` / `RolesModSetup` — la politique est donc **publiée et datée
on-chain**, pas dans un document privé.

**Conditions (arbres sur calldata).** Une condition est un **arbre** : chaque nœud a un `paramType`
(`Static`, `Dynamic`, `Tuple`, `Array`, `AbiEncoded`, `Calldata`, `None`), un `operator` et une
`compValue`. Opérateurs disponibles (`Types.sol`, enum `Operator`, consulté 2026-10-15) :
`Pass`, `And`, `Or`, `Nor`, `Matches`, `ArraySome`, `ArrayEvery`, `ArraySubset`,
`EqualToAvatar`, `EqualTo`, `GreaterThan`, `LessThan`, `SignedIntGreaterThan`,
`SignedIntLessThan`, `Bitmask`, `Custom`, `WithinAllowance`, `EtherWithinAllowance`,
`CallWithinAllowance`. Les opérateurs d'allowance ne marchent que sur des valeurs `uint` en clair,
la valeur Ether de la transaction, ou comme **quota d'appels** (`CallWithinAllowance` décrémente
de 1). Source :
[docs — Conditions](https://docs.roles.gnosisguild.org/general/conditions) (2026-10-15).
Exemple canonique de portée sur une fonction : le swap Balancer (le doc impose que vendeur et
receveur soient l'avatar) ; `AvatarIsOwnerOfERC721` existe comme condition personnalisée déployée
pour les positions NFT Uniswap.

**Allowances (plafonds par période).** Structure (`Types.sol`) :
`struct Allowance { uint128 refill; uint128 maxRefill; uint64 period; uint128 balance; uint64
timestamp; }` — `period` en secondes, `0` = **usage unique non rechargé** ; `refill` ajouté par
période ; `maxRefill` plafond d'accumulation ; `balance` disponible ; `timestamp` du dernier
rafraîchissement. Tous les champs sont modifiables manuellement
([docs — Allowances](https://docs.roles.gnosisguild.org/general/allowances), 2026-10-15).
**Sémantique exacte du rechargement** (`AllowanceTracker.sol::_accruedAllowance`) : le
rafraîchissement est calculé **par intervalles entiers** —
`elapsedIntervals = (now − timestamp) / period`, puis `balance += refill × elapsedIntervals`
plafonné à `maxRefill` ; le `timestamp` avance de `elapsedIntervals × period`. Les allowances se
consomment sur `WithinAllowance` (champ `uint` du calldata), `EtherWithinAllowance` (valeur native)
et `CallWithinAllowance` (quota d'appels). Trois conséquences opérationnelles :

1. le plafond on-chain est un **plafond d'accumulation** (`maxRefill`), pas un plafond glissant
   par seconde : une période calme remplit le seau, une rafale peut le vider ;
2. le pire cas de rafale sur deux blocs adjacents est **`maxRefill + refill`** (voir attaque #2) ;
3. `period = 0` fournit nativement un motif « **une seule fois** » (consommation unique), utile
   pour un mandat à usage unique.

**Déballage (unwrapping).** Pour vérifier les appels passés en lot (`Safe MultiSend`) ou via des
agrégateurs, le module « déballe » la transaction et contrôle chaque sous-appel : adaptateurs
`MultiSendUnwrapper` (`0xB4Cd4bb764C089f20DA18700CE8bc5e49F369efD`) et `MorphoBundler3Unwrapper`
(`0x7533922A155DC6b4Cc0ae4E74D70a73bc86dD3E8`) — c'est le composant qui a porté les deux bugs de
2026 (a.6).

### a.3 Déploiements vérifiés (RPC, 2026-10-15)

Le README liste le contrat **Roles à la même adresse sur 18 chaînes**, dont Mainnet, Base et
**Base Sepolia** (README du dépôt, consulté 2026-10-15). J'ai vérifié par `eth_getCode` que le
code existe **et qu'il est identique** sur les trois chaînes du dossier :

| Chaîne | Bloc au moment du test | Taille du code | sha256(code rôle) |
|---|---|---|---|
| Ethereum mainnet | 26 195 069 | 24 409 o | `bf4438c3197d3ecc…` |
| Base (8453) | 52 621 844 | 24 409 o | `bf4438c3197d3ecc…` (identique) |
| Base Sepolia (84532) | 48 132 375 | 24 409 o | `bf4438c3197d3ecc…` (identique) |

Adresse : `0xF2964CE6161ce0e75964Fe7927cE114cb0B283D5`. Les bibliothèques et adaptateurs sont
également présents sur Base Sepolia : `Integrity 0x6a6Af4b16458Bc39817e4019fB02BD3b26d41049`
(5 637 o), `Packer 0x869718c939652084bc491fbc5ce0d3c1d5b309f0` (2 138 o),
`MultiSendUnwrapper 0xB4Cd4bb764C089f20DA18700CE8bc5e49F369efD` (2 096 o),
`AvatarIsOwnerOfERC721 0x91B1bd7BCC5E623d5CE76b0152253499a9C819d1` (811 o).
**Absent sur Base Sepolia** : `MorphoBundler3Unwrapper` (renvoie `0x`) — l'unwrapping Morpho n'est
donc pas testable sur ce testnet. Détail des preuves : `raw_w2c/W2C_evidence_verifications.md`.

Côté Safe (le socle), Base Sepolia porte la pile standard vérifiée le 2026-10-15 : singleton
`Safe 0x41675C…461a` / `SafeL2 0x29fcB4…C762`, fabrique
`0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67`, `CompatibilityFallbackHandler 0xfd0732Dc…Ec99`,
`MultiSend 0x38869bf6…B526`, `MultiSendCallOnly 0x40A2aCCb…130D`.

**Adresses de référence d'un déploiement réel (ENS, Ethereum mainnet)** — vérifiées présentes :
module Roles de l'Endowment `0x703806E61847984346d2D7DDd853049627e50A40` (proxy, 45 o) et Safe
avatar `0x4F2083f5fBede34C2714aFfb3105539775f7FE64` (171 o), tous deux issus de la proposition
[EP 5.14](https://docs.ens.domains/dao/proposals/5.14) (consultée 2026-10-15).

### a.4 Outillage

- **Application Zodiac Roles** — visualisation des permissions, **comparaison de politique (diff)**
  avant/après chaque mise à jour : `https://roles.gnosisguild.org` (l'EP 5.14 pointe directement
  une URL de diff : `roles.gnosisguild.org/eth:0x703806…0A40/roles/MANAGER/diff/…`).
- **App Zodiac du Safe App Store** — ajout du module et écriture des rôles via l'onglet
  « Write Contract » (`assignRoles`) ; c'est la procédure documentée du tutoriel Gnosis Guild.
- **Zodiac Pilot** — enregistre des appels réels puis les rejoue/valide pour construire les
  permissions (même tutoriel).
- **SDK TypeScript** `zodiac-roles-sdk` → renommé `@zodiaceco/sdk` (commit du 13 oct. 2026),
  packages `sdk`, `deployments`, `app`, `subgraph` (README, 2026-10-15) ;
  documentation SDK : https://docs.roles.gnosisguild.org/sdk/api.
- **Subgraph** : `https://gnosisguild.squids.live/roles:production/api/graphql` (README) — lecture
  indexée des rôles/permissions, utile pour l'audit hors-chaîne.
- **DeFi Kit (karpatkey)** : bibliothèque de permissions Zodiac « curated for safe interaction with
  DeFi protocols », SDK + API REST + playground — `https://kit.karpatkey.com/` et
  `https://github.com/karpatkey/defi-kit` (consultés 2026-10-15). Un endpoint typique :
  `GET /eth:0x…/manager/allow/cowswap/swap?sell=DAI&buy=WETH`.

### a.5 Qui peut être membre (point décisif pour un agent autonome)

Une **EOA peut être membre d'un rôle** : l'incident de juin 2026 distingue explicitement les
membres EOA (« Role members that are EOAs » n'étaient pas exposés —
[post-mortem](https://engineering.gnosisguild.org/posts/zodiac-post-mortem), 19 juin 2026), et
`Safe v1.4.1 ModuleManager.enableModule` **ne vérifie pas** que l'adresse est un contrat (source
`ModuleManager.sol` v1.4.1, consulté 2026-10-15). Cela permet au signer de l'agent d'être une **EOA
isolée qui paie son propre gaz** et appelle `execTransactionWithRole` directement, sans détenir de
clé de la Safe. C'est le montage retenu en (d).

### a.6 Audits et incidents (le dossier doit les citer)

**Audits** (dépôt, `packages/evm/docs`, consulté 2026-10-15) :
`Audit01_RolesV2_Apr2023_G0Group.pdf`, `Audit02_RolesV2_May2023_Omniscia.pdf`,
`Audit03_RolesV2_1_Nov2023_Ominiscia.pdf`, `Audit04_Roles-V2_1_Nov2023_G0Group.pdf`. Toutes les
failles identifiées ont été résolues au commit `a19c0ebd…` (README). L'EP 5.12 cite ces audits comme
argument de vote : « The Zodiac Roles Modifier v2 contract has been rigorously audited by G0 Group,
the internal auditing team of Gnosis DAO, and by Omniscia »
([docs.ens.domains/dao/proposals/5.12](https://docs.ens.domains/dao/proposals/5.12)).
La page sécurité de l'éditeur revendique également une revue par **Gnosis**
(https://www.zodiac.eco/security, consultée 2026-10-15), avec le slogan opérationnel « policy the
chain enforces […] a compromised dashboard, an overbroad keeper, a signer tricked into approving
the wrong call ».

**Incident 1 — contournement ERC-1271 (v2.1.0), juin 2026.** Cause racine : le contrôle de
signature ERC-1271 acceptait le magic value `0x1626ba7e` **sans vérifier que le `staticcall` au
contrat signataire avait réussi**. Exploitable seulement si un Safe avec CompatibilityFallbackHandler
était **membre de rôle** (Roles v2.1.0) ou module (Delay v1.1.0). Chiffres du post-mortem :
~49 800 comptes identifiés (dont 46 669 Gnosis Pay, 2 227 avatars Roles à risque) ; valeur
attribuable à risque côté Roles **~85,47 M$ → ~200 k$** après confinement (~99,77 % sécurisé,
**aucune perte confirmée** côté Roles) ; pertes confirmées hors Gnosis Pay **~4 500 $** ; réseaux
touchés Gnosis, Base, Ethereum ; patchs **Delay v1.1.1** et **Roles v2.1.1** déployés après audit ;
divulgation publique le 2 juin 2026, post-mortem le 19 juin 2026
(https://engineering.gnosisguild.org/posts/zodiac-post-mortem). **L'endowment ENS a été confirmé
non affecté** par kpk le 4 juin 2026 : « our assessment confirmed no impact on the endowment, and
no action is required on the side of ENS. Even without the patch, the Avatar Safe permission
framework would have prevented the issue from resulting in any loss of funds »
(https://discuss.ens.domains/t/security-update-zodiac-roles-modifier-v2-and-delay-modifier-v1-1-0/22161).

**Incident 2 — contournement de permissions via MultiSend (padding ABI).** Le contrôle de bornes de
`MultiSendUnwrapper._validateEntries` utilisait `data.length` (qui inclut jusqu'à 31 octets de
rembourrage ABI) au lieu de la frontière réelle du payload interne : un lot MultiSend forgé pouvait
faire **valider un calldata différent de celui exécuté** sur les 1 à 31 derniers octets, avec pour
exemple canonique `Aave Pool.withdraw(address asset, uint256 amount, address to)` où `to` tombe dans
la zone de rembourrage (validation d'un destinataire autorisé, exécution vers `address(0)`, fonds
détruits). Conditions : l'attaquant doit **déjà détenir un rôle**. Correctif dans le commit
`1ddde84db9024c6c1898d1f4cf5dabded3e824f1` ; l'app Roles affiche un avertissement et propose une
migration en un clic pour les modules encore vulnérables
(https://grego.ai/reports/safe-abi-padding-permission-checks, consulté 2026-10-15 ; **date de
publication non trouvée sur la page**).

### a.7 Limites connues (à écrire noir sur blanc dans le dossier concours)

1. **Pas d'expiration native d'un rôle ni d'une allowance** : `Allowance` ne contient aucun champ
   d'expiration (source `Types.sol`). L'expiration doit être obtenue par processus : `period = 0`
   (usage unique), non-rechargement, ou **révocation planifiée** (transaction gouvernée, éventuellement
   via le module Zodiac Delay) + surveillance. Sinon c'est une limite assumée hors-chaîne.
2. **Rafale de frontière de période** : jusqu'à `maxRefill + refill` engagés sur deux blocs
   adjacents (démonstration en (e) #2). Le plafond on-chain n'est donc pas un plafond glissant
   strict : il doit être doublé d'un **compteur glissant hors-chaîne** (premier verrou) et d'un
   dimensionnement `maxRefill == refill` si l'on veut que le pire cas soit ≈ 2 périodes.
3. **La portée doit être écrite fonction par fonction** : autoriser une cible entière
   (`Clearance.Target`) laisse passer **n'importe quel calldata** vers cette cible — c'est le mode
   d'erreur le plus dangereux d'une politique mal écrite. Le défaut est sûr (rien d'autorisé =
   refus), l'excès de portée ne l'est pas.
4. **Les conditions ne comprennent pas la sémantique** : le module compare des mots de calldata,
   il n'évalue ni un prix, ni un oracle, ni une intention. Tout ce qui relève du jugement (prix
   acceptable, limite de slippage implicite, choix de venue) reste **hors-chaîne** — d'où
   l'architecture à double verrou.
5. **Le module a les pleins pouvoirs du Safe par construction** : « modules […] have full access to
   execute transactions, send funds » (grego.ai, 2026-10-15) ; un module mal configuré ou bogué est
   un risque au niveau du trésor entier. C'est la raison d'être des audits et des migrations (deux
   bugs majeurs en 2026, tous deux corrigés et publiés).
6. **Dette opérationnelle de gouvernance** : chaque nouvelle venue/protocole exige une **mise à jour
   de permissions votée** — l'ENS en est à plusieurs mises à jour par an (« Update #8 », « #9 » via
   EP 6.41, « Update #10 » en projet), avec des audits de politique indépendants (ThirdGuard) devenus
   standard depuis l'EP 5.14. Le coût caché d'une enveloppe bornée est **gouvernance + audit de
   politique**, pas la blockchain.
7. **Pas de surveillance incluse** : le module exécute, il n'alerte pas. L'outillage de monitoring
   historique (OZ Defender) est en fin de vie (1er juillet 2026 selon le corpus U2 du projet,
   `research/U2_defi_organisations.md`) → un agent qui exploite Zodiac doit **apporter sa propre
   télémétrie** (événements `ConsumeAllowance`, `AssignRoles`, subgraph, journal hors-chaîne).
8. **Avertissement de garantie** : contrats « WITHOUT ANY WARRANTY » (README) — à recopier dans
   l'annexe juridique du dossier, ne jamais promettre une garantie que l'amont ne donne pas.

---

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

## (d) Architecture du signer limité

### d.1 Schéma textuel (flux d'une exécution T2)

```
                        ┌──────────────────────────────────────────────┐
   [1] LLM / planificateur  (jamais de clé, jamais de calldata signé)
        │  propose une INTENTION structurée (JSON, pas une tx)
        ▼
   [2] MOTEUR DE POLITIQUE  (hors LLM, déterministe, testable)
        │  entrées : intention + état local (quotas, nonces) + lecture chaîne
        │  sortie  : ALLOW | DENY + raison + hash d'intention
        │  ── PREMIER VERROU (c'est ici que vit le "non") ──
        ▼ (ALLOW seulement)
   [3] CONSTRUCTEUR D'APPEL   calldata = Roles.execTransactionWithRole(
        │                       to=USDC, value=0, data=transfer(dest,montant),
        │                       operation=CALL, roleKey=AGENT, shouldRevert=true)
        │  + simulation `eth_call` sur le RPC épinglé (pré-vol) → refus si revert
        ▼
   [4] REGISTRE D'INTENTIONS (anti-rejeu)   id = keccak(intention)
        │  refuse si id déjà exécuté/en vol ; réserve le quota local
        ▼
   [5] SIGNER ISOLÉ (processus séparé / matériel ; clé jamais en clair dans
        │  le LLM, les logs, le dépôt ; pas de droit d'administration)
        ▼  une signature ECDSA sur UNE transaction
   [6] RPC ÉPINGLÉ (chainId vérifié = 84532 / 8453 ; refus si autre)
        ▼
   [7] CHAÎNE : Safe (avatar) ← module Zodiac Roles v2  ── SECOND VERROU ──
        │  _authorize : rôle du signer ? cible autorisée ? fonction scopée ?
        │  conditions : destinataire ∈ liste blanche ; montant ≤ allowance ;
        │  allowance consommée seulement si l'exécution réussit
        ▼
   [8] EFFET ON-CHAIN (transfert USDC) + événements (ConsumeAllowance…)
        ▼
   [9] JOURNAL D'AUDIT (JSONL chaîné par hash, exportable)  ← opposition tiers
        + [10] SURVEILLANCE : seuils, alerte, PAUSE hors-chaîne ; la DAO garde
          le KILL SWITCH on-chain (revokeRoles / disableModule), 1 transaction
```

**Invariants** (à tester unitairement, cf. projet : `src/`, `tests/`) :
I1 le LLM ne voit jamais de clé ni ne signe ; I2 aucune exécution sans verdict ALLOW
tracé ; I3 l'agent ne possède aucun rôle d'administration (il ne peut pas modifier la
politique) ; I4 toute action exécutée a une entrée de journal vérifiable contre la chaîne ;
I5 le retrait du rôle par la DAO suffit à arrêter l'agent (aucune autre dépendance).

### d.2 Où vit la clé de l'agent

- **Membre de rôle = adresse dédiée** (EOA ; validé par Safe v1.4.1 `enableModule` sans contrôle
  `isContract`, cf. a.5 — et par le post-mortem qui distingue les membres EOA).
- **Isolation** : processus séparé (service de signature), clé chargée depuis un magasin de
  secrets/keystore chiffré ou un matériel ; **jamais** dans le contexte du LLM, jamais dans un log,
  jamais dans le dépôt (règle projet déjà posée par le skill `evm-onchain-verification` :
  « isolated signer that never enters a prompt, a log or the repo »).
- **Zéro privilège administratif** : le membre de rôle ne peut appeler ni `assignRoles`,
  ni `allowTarget`/`scopeFunction`, ni `setAllowance` (toutes `onlyOwner` = la Safe). **Test
  on-chain** de cette affirmation dans la matrice (#7).
- **Rotation** : changer d'agent = `assignRoles(nouvelle_adresse, [AGENT], [true])` +
  `assignRoles(ancienne, [AGENT], [false])` — 1 transaction DAO.

### d.3 Quotas côté agent, nonce, idempotence, gaz

- **Quotas locaux (premier verrou)** : plafond par transaction, **compteur glissant 24 h**
  (fenêtre glissante, pas calendaire — le calendaire est attaquable, cf. #2), par actif et par
  destinataire ; ces compteurs vivent dans le moteur de politique, pas dans le LLM.
- **Nonce** : nonce EOA standard pour l'unicité de la transaction ; mais **l'idempotence métier est
  une notion hors-chaîne** : `id = keccak(intention_normalisée)` dans un registre persistant
  (append-only). Rejouer la *même* intention renvoie un refus (« déjà exécutée »). Côté chaîne,
  l'amortisseur est `CallWithinAllowance` (quota d'appels) + les plafonds d'allowance.
- **Gaz** : l'agent paie son propre gaz (EOA membre) → il doit être **financé en ETH**. Options, par
  ordre de préférence : (i) testnet : robinet ; (ii) production : virement périodique depuis la
  trésorerie, lui-même borné (une permission « gas top-up » séparée, plafonnée, vers l'adresse de
  l'agent — jamais l'inverse) ; (iii) relais/paymaster (hors phase 1). Le montant de gaz est exclu
  du plafond métier : c'est une ligne budgétaire **distincte et surveillée**.
- **Simulation pré-vol** : `eth_call` du calldata exact sur le RPC épinglé avant signature ; un
  revert en simulation = pas de signature (évite de brûler du gaz et d'émettre un échec).

### d.4 Kill switch : qui, comment, en combien de temps

| Niveau | Action | Qui | Latence | Ce que ça arrête |
|---|---|---|---|---|
| K0 | **PAUSE hors-chaîne** (drapeau du service de signature) | ORVYREN (astreinte) | immédiat | Toute nouvelle signature de l'agent |
| K1 | **`assignRoles(agent, [AGENT], [false])`** (retrait du rôle) | Safe DAO (seuil de signatures) | 1 transaction ; sur Base **1,64 s/bloc mesuré** le 2026-10-15 (620 blocs en 1 016 s, blocs 52 621 844 → 52 622 464) — la latence réelle est la **coordination humaine** (minutes) | Toute exécution ultérieure du rôle par l'agent |
| K2 | **`disableModule(prev, rolesModule)`** | Safe DAO | idem K1 | Le module entier (tous les rôles de ce module) |
| K3 | Retrait des ETH de gaz / désactivation du financement | Safe DAO | idem | La capacité à payer le gaz (arrêt « par asphyxie ») |

**Ce qu'un kill switch ne peut pas faire** (à écrire honnêtement) : annuler une transaction **déjà
incluse** dans un bloc ; elle ne peut pas non plus empêcher une transaction déjà dans la mempool
d'être incluse si elle est séquencée avant la révocation. Sur Base (séquenceur centralisé, ordre
d'arrivée ~FIFO, pas d'enchère de priorité type marché de gaz L1), la protection pratique est :
délais courts entre décision et envoi, plafonds faibles, surveillance des intentions, et le fait
que **le dommage maximal par bloc est borné par l'allowance**. Ce raisonnement (« le pire cas est
un nombre connu ») est plus fort qu'une promesse d'annulation instantanée.

### d.5 Journal d'audit exportable

Format recommandé : **JSONL append-only, chaîné par hash** (`record_hash =
keccak(prev_hash || canonical_json(record))`), un enregistrement par étape :

```json
{"ts":"2026-10-15T12:00:01Z","intent_id":"0x…","kind":"INTENT","intent":{...},
 "policy":{"verdict":"ALLOW","rules":[{"id":"cap_tx_100","ok":true}],"policy_version":"v1.3"},
 "chain":{"id":84532,"rpc":"sepolia.base.org"},"nonce":17}
{"ts":"…","intent_id":"0x…","kind":"SIMULATION","ok":true,"gas_estimate":…}
{"ts":"…","intent_id":"0x…","kind":"SUBMIT","tx_hash":"0x…"}
{"ts":"…","intent_id":"0x…","kind":"RECEIPT","status":1,"block":48133012,
 "logs":[{"address":"0x036C…","topic0":"0xddf2…","from":"0x4F20…","to":"0x…","value":"50000000"}],
 "allowance_after":{"usdc_daily":"250000000"}}
{"ts":"…","intent_id":"0x…","kind":"VERIFY","recomputed_from_chain":true}
```

**Vérifiabilité par un tiers** (c'est ce qui rend le journal *opposable* et non déclaratif) :
1. chaque `tx_hash` est relisible via `eth_getTransactionReceipt` (statut, bloc, logs) ;
2. les logs `Transfer` (topic0 `0xddf252ad…`) sont recoupés avec l'intention (destinataire, montant) ;
3. l'état des allowances après coup est lisible dans le module Roles (ou via `ConsumeAllowance`) ;
4. la chaîne de hash détecte toute réécriture du journal ;
5. la politique appliquée est identifiée par `policy_version` (le texte de politique est versionné).

---

## (e) Matrice des 12 attaques

Légende des contrôles : **P** = politique hors-chaîne (premier verrou, déterministe) ·
**C** = chaîne (module Zodiac / Safe) · **N** = nonce/registre d'intentions · **M** = surveillance
et processus (humain/ops) · **S** = secret/signer isolé.
« Test qui le prouve » = test reproductible sur Base Sepolia (ou test unitaire quand la chaîne ne
peut pas être mise en cause).

| # | Attaque | Vecteur concret | Contrôle qui l'attrape | Test qui le prouve |
|---|---|---|---|---|
| 1 | **Rejeu d'intention** | Le même calldata signé/envoyé deux fois (retry réseau, duplication, copie par un tiers) | **N** (registre `intent_id`) + **C** (nonce EOA : la 2ᵉ tx avec le même nonce est rejetée ; si le nonce a avancé, l'allowance a déjà été débitée) | Test : soumettre 2× la même transaction signée brute → la 2ᵉ est rejetée (`nonce too low`) ; et 2× la même *intention* → refus P « déjà exécutée », aucune tx émise |
| 2 | **Frontière de période (dépense 2×)** | Dépenser le solde juste avant le rafraîchissement puis à nouveau juste après : jusqu'à **`maxRefill + refill`** sur deux blocs (arithmétique : `elapsedIntervals = (now − ts)/period`, `balance += refill × elapsedIntervals`, plafond `maxRefill` — code `AllowanceTracker.sol`) | **P** (compteur **glissant** 24 h ≠ fenêtre calendaire) + **M** (alerte) ; **C** borne le montant unitaire mais **ne détecte pas** la rafale | Test : avec `refill=100, maxRefill=100, period=86 400`, dépenser 100 à T−1 s de la frontière puis 100 à T+1 s → **la chaîne accepte les deux** ; le compteur glissant hors-chaîne refuse la seconde (journal : DENY `rolling_24h_300`). Ce test documente la limite on-chain au lieu de la nier |
| 3 | **Révocation pendant une exécution en cours** | La DAO révoque pendant qu'une tx de l'agent est en vol / dans la mempool | **C** (la révocation bloque tout ce qui n'est pas encore exécuté) + **M** (surveillance des intentions) | Test : envoyer une tx agent qui traîne (gaz faible) puis, dans le même intervalle, exécuter `assignRoles(...,false)` depuis la Safe → la tx de l'agent **revert** (`NoMembership`) alors que la révocation est confirmée. Variante à documenter : si la tx agent est incluse *avant* la révocation, elle s'exécute — d'où le plafond faible |
| 4 | **Manipulation d'oracle de prix** | Faire exécuter un swap à un prix absurde (oracle manipulé, pool piégé, route empoisonnée) | **P** (bornes de prix hors-chaîne : prix de référence multi-venues, écart max) + **C** (conditions sur les paramètres : `EqualToAvatar` sur receveur, `GreaterThan` sur `minOut`, portée sur la fonction exacte du routeur) | Test : intention de swap dont `minOut` est inférieur au seuil → **P refuse** (aucune signature). Test chaîne : poster un calldata avec `minOut=0` sur une fonction autorisée mais dont la condition exige `minOut > seuil` → revert. Rappel : **la chaîne ne connaît pas les prix** ; ne jamais prétendre le contraire |
| 5 | **Calldata mal décimé** | Décalage de décimales (6 vs 18), unités, ou **rembourrage ABI** exploité par un lot (bug MultiSend réel : 1 à 31 octets de fin divergents) | **P** (canonicalisation + validation de schéma avant signature, conversion décimale testée) + **C** (conditions sur montants) + **M** (contrôle post-exécution) | Test unitaire : `155.0 → 155000000` vs `155000000000000000000` — un débit de 1 000 000× est refusé par le plafond. Test chaîne : reproduire le motif du rapport grego.ai (calldata forgé dont les derniers octets diffèrent) sur un module **à jour** → refus ; et vérifier le SHA/commit du `MultiSendUnwrapper` déployé **avant** la démo |
| 6 | **Mauvaise chaîne au niveau RPC** | Le client pointe une autre chaîne (testnet/mainnet, fork, RPC menteur) : l'agent « exécute » ailleurs, ou lit un état faux | **P/C** (épinglage `chainId` : refus si ≠ 84532 en test / ≠ 8453 en prod ; adresses vérifiées par chaîne) + **M** | Test : configurer un RPC Ethereum mainnet → le pré-vol refuse (`chain_id_mismatch`), aucune signature ; test symétrique : recevoir une tx signée pour 8453 et vérifier qu'elle est rejetée par le RPC/la politique |
| 7 | **Tentative de changement d'allowlist par l'agent** | L'agent (ou un attaquant qui a sa clé) appelle `allowTarget`, `scopeFunction`, `setAllowance`, `assignRoles`, `enableModule` | **C** : ces fonctions sont `onlyOwner` (la Safe), le membre du rôle n'a **aucun** pouvoir d'administration | Test : depuis l'adresse agent, `eth_call` puis tx réelle sur `Roles.allowTarget(...)` et `Safe.enableModule(attaquant)` → revert (`OwnableUnauthorizedAccount`/`GS` *) ; journaliser les deux reverts |
| 8 | **Dépassement cumulé** | Multiplier les petites transactions pour dépasser le plafond journalier | **C** (`WithinAllowance` débite à chaque exécution réussie) + **P** (compteur glissant) + **N** | Test : boucle de 4 × 100 USDC avec plafond 300/jour → les 3 premières passent, la 4ᵉ **revert** on-chain (`AllowanceExceeded`), et le compteur hors-chaîne l'aurait refusée avant signature |
| 9 | **Permission expirée** | Faire exécuter un mandat dont la durée est écoulée (personne n'a révoqué) | **P** (date d'expiration dans la politique hors-chaîne, refus) + **M** (tâche planifiée de révocation) ; **la chaîne n'a pas d'expiration native** (pas de champ `expiry` dans `Allowance` — vérifié dans le code) | Test : fixer une expiration à T ; après T, une intention valide par ailleurs est refusée par **P** ; **et** exécuter le calldata directement depuis la clé agent → il **passe encore** (limite assumée, à documenter) ; puis vérifier que la révocation planifiée l'arrête |
| 10 | **Sandwich / slippage** | Extraction de valeur autour du swap de l'agent (MEV) ; l'agent subit un prix dégradé | **P** (borne de slippage explicite, prix de référence, taille maximale par rapport à la profondeur du pool) + **C** (conditions `GreaterThan`/`LessThan` sur les paramètres, receveur = avatar comme dans l'exemple Balancer des docs) | Test : simulé — fixer une borne de slippage, soumettre une intention qui l'excède → refus P ; sur chaîne, un calldata dont `minOut` viole la condition → revert. (Testnet : profondeur non représentative → le test de qualité d'exécution se fait en simulation, cf. skill : « Testnet prices are not market data ») |
| 11 | **Clé d'agent compromise** | Vol de la clé du signer (poste, dépendance, fuite de log) | **C** (le périmètre du rôle **est** la borne : cibles, fonctions, paramètres, destinataires, allowances) + **P/N** côté attaquant s'il n'a pas le registre + **M** (détection de motif anormal → pause + révocation) | Test rouge (red team, clé volontairement utilisée hors politique) : (i) 500 USDC au-delà du plafond → revert ; (ii) transfert vers une adresse hors liste → revert ; (iii) appel admin → revert ; (iv) drain complet de la Safe → **impossible** (le rôle ne le permet pas). Résultat à écrire : « l'attaquant obtient au plus `maxRefill` par période, uniquement vers les destinataires autorisés » |
| 12 | **Inscription d'un destinataire non autorisé** | Faire ajouter/employer une adresse de destination pirate (nouveau destinataire « approuvé » injecté, ou contrat malveillant en bout de chaîne) | **C** (condition de liste blanche sur l'adresse de destination) + **P** (liste des bénéficiaires figée par mandat) + **M** | Test : intention vers une adresse non listée → **P refuse** ; forcer le calldata depuis la clé agent → **revert** (condition de destinataire). Test complémentaire : tenter de modifier la liste = #7 (impossible) |

\* Le nom exact du revert dépend de la version du module/Safe ; le test doit journaliser le
sélecteur constaté, pas un nom supposé.

### e.1 Les trois attaques les plus « convaincantes » pour un jury (à jouer en démo)

1. **#5 calldata mal décimé** : c'est l'erreur la plus banale et la plus destructrice ; la démo
   montre un refus *avant* signature **et** un revert *si on force*.
2. **#11 clé compromise** : le seul scénario où l'on accepte que l'attaquant *ait* la clé — et la
   démonstration que le pire cas est un nombre fini, vers des destinataires autorisés.
3. **#2 frontière de période** : le jury technique y voit de la rigueur (limite on-chain reconnue et
   couverte par le premier verrou), pas une faiblesse cachée.

---

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
   (Base : 1,64 s/bloc mesuré le 2026-10-15), (c) l'effet : la tx de l'agent **revert**
   (`NoMembership`) ; le rôle est inactif.
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
