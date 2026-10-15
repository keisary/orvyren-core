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
