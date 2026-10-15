# W2-C — Matière brute et vérifications (journal de collecte)

Toutes les vérifications RPC de ce fichier ont été exécutées le **2026-10-15** (UTC)
par `raw_w2c/rpc_check.sh` (curl → `eth_chainId`, `eth_blockNumber`, `eth_getCode`).
Aucune donnée n'est reprise de mémoire : adresses issues des sources citées, puis
présence de code vérifiée sur la chaîne.

## 1. Zodiac Roles v2 — contrats (source : README du dépôt, consulté 2026-10-15)

| Contrat | Adresse | Source |
|---|---|---|
| Roles | `0xF2964CE6161ce0e75964Fe7927cE114cb0B283D5` | https://raw.githubusercontent.com/gnosisguild/zodiac-modifier-roles/main/README.md |
| Integrity | `0x6a6Af4b16458Bc39817e4019fB02BD3b26d41049` | idem |
| Packer | `0x869718c939652084bc491fbc5ce0d3c1d5b309f0` | idem |
| MultiSendUnwrapper | `0xB4Cd4bb764C089f20DA18700CE8bc5e49F369efD` | idem |
| AvatarIsOwnerOfERC721 | `0x91B1bd7BCC5E623d5CE76b0152253499a9C819d1` | idem |
| MorphoBundler3Unwrapper | `0x7533922A155DC6b4Cc0ae4E74D70a73bc86dD3E8` | idem |

### Résultats `eth_getCode` (2026-10-15)

| Chaîne | Contrat | Bloc | Taille code | sha256(code) |
|---|---|---|---|---|
| Ethereum (chainId 0x1, rpc publicnode) | Roles | 26 195 069 | 24 409 o | bf4438c3197d3ecc… |
| Base (0x2105, mainnet.base.org) | Roles | 52 621 844 | 24 409 o | bf4438c3197d3ecc… |
| Base Sepolia (0x14a34, sepolia.base.org) | Roles | 48 132 375 | 24 409 o | bf4438c3197d3ecc… |
| Base Sepolia | Integrity | 48 132 375 | 5 637 o | 7de9d97c32597ff9… |
| Base Sepolia | Packer | 48 132 375 | 2 138 o | 2f2f7a0d0d3a695b… |
| Base Sepolia | MultiSendUnwrapper | 48 132 375 | 2 096 o | 7b71c2d6d38f6cc0… |
| Base Sepolia | AvatarIsOwnerOfERC721 | 48 132 375 | 811 o | 9c424574b576f6c6… |
| Base Sepolia | MorphoBundler3Unwrapper | 48 132 306 | **absent (0x)** | — |
| Base Sepolia | USDC (Circle test) `0x036CbD53842c5426634e7929541eC2318f3dCF7e` | 48 132 303 | 1 798 o | 2842683d1ea26f4d… |

**Lecture** : le contrat `Roles` a le **même bytecode** (même longueur, même sha256)
sur Ethereum, Base et Base Sepolia → déploiement déterministe multi-chaînes, rôle du
module identique partout. L'adaptateur Morpho n'existe pas sur Base Sepolia (attendu :
Morpho Bundler3 n'y est pas déployé — « non trouvé » côté Base Sepolia).

## 2. Pile Safe sur Base Sepolia (2026-10-15)

| Contrat | Adresse | Taille code | sha256(code) |
|---|---|---|---|
| Safe (singleton 1.4.1) | `0x41675C099F32341bf84BFc5382aF534df5C7461a` | 23 579 o | 525c99ddd57e1e33… |
| SafeL2 (singleton 1.4.1) | `0x29fcB43b46531BcA003ddC8FCB67FFE91900C762` | 24 421 o | afbd74993cd89f8a… |
| SafeProxyFactory 1.4.1 | `0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67` | 3 054 o | b99512bcd406d913… |
| CompatibilityFallbackHandler 1.4.1 | `0xfd0732Dc9E303f09fCEf3a7388Ad10A83459Ec99` | 5 637 o | 08d95a93e5542f9e… |
| MultiSendCallOnly 1.4.1 | `0x40A2aCCbd92BCA938b02010E17A5b8929b49130D` | 410 o | 46b21f924acbeb53… |
| MultiSend 1.4.1 | `0x38869bf66a61cF6bDB996A6aE40D5853Fd43B526` | 629 o | a2375c36b73eea33… |

## 3. Alternatives — présence du code (2026-10-15)

| Module | Adresse | Ethereum | Base | Base Sepolia |
|---|---|---|---|---|
| Safe Allowance Module | `0xCFbFaC74C26F8647cBDb8c5caf80BB5b32E43134` | présent, 15 003 o, sha 9df7b828… | présent, 15 003 o, sha 9df7b828… (bytecode identique) | **absent (0x)** |
| Coinbase SpendPermissionManager | `0xf85210B21cC50302F477BA56686d2019dC9b67Ad` | non testé | présent, 12 610 o, sha 44945ba3… | présent, 12 610 o, sha f3bf35db… |
| MetaMask DelegationManager | `0xdb9B1e94B5b69Df7e401DDbedE43491141047dB3` | présent, 11 503 o | présent, 11 503 o | présent, 11 503 o |

Adresses SpendPermissionManager issues de https://raw.githubusercontent.com/coinbase/spend-permissions/main/README.md
(chains listées : Base Sepolia, Optimism Sepolia, Ethereum Sepolia / Base, Ethereum,
Optimism, Arbitrum, Polygon, Zora, BSC, Avalanche).
Adresse DelegationManager issue de https://github.com/MetaMask/delegation-framework/blob/main/documents/Deployments.md (v1.3.0, Base Sepolia).
Note : longueurs identiques mais sha différents entre chaînes pour SpendPermissionManager
et DelegationManager → immutables/paramètres spécifiques à la chaîne ; « code présent »
n'implique pas bytecode identique.

## 4. Adresses ENS vérifiées (Ethereum mainnet, bloc 26 195 402, 2026-10-15)

| Objet | Adresse | Taille code | Source |
|---|---|---|---|
| Roles Modifier v2 de l'Endowment ENS | `0x703806E61847984346d2D7DDd853049627e50A40` | 45 o (proxy) | EP 5.14 (docs.ens.domains) |
| Safe « Endowment » (avatar) | `0x4F2083f5fBede34C2714aFfb3105539775f7FE64` | 171 o (proxy Safe) | EP 5.14 |

## 5. Extraits de code faisant foi (lus dans le dépôt, 2026-10-15)

**AllowanceTracker.sol** (accrual des allowances) — `_accruedAllowance` :
```solidity
if (allowance.period == 0 || blockTimestamp < (allowance.timestamp + allowance.period)) {
    return (allowance.balance, allowance.timestamp);
}
uint64 elapsedIntervals = (blockTimestamp - allowance.timestamp) / allowance.period;
if (allowance.balance < allowance.maxRefill) {
    balance = allowance.balance + allowance.refill * elapsedIntervals;
    balance = balance < allowance.maxRefill ? balance : allowance.maxRefill;
} else { balance = allowance.balance; }
timestamp = allowance.timestamp + elapsedIntervals * allowance.period;
```
→ Le rafraîchissement se fait **par intervalles entiers** (pas en continu à la seconde),
et le solde est plafonné à `maxRefill`. Conséquence chiffrée : une dépense juste avant
la frontière d'intervalle puis une juste après permet d'engager jusqu'à
**maxRefill + refill** en deux blocs (voir matrice des 12 attaques, #2).

**Types.sol** — `struct Allowance { uint128 refill; uint128 maxRefill; uint64 period; uint128 balance; uint64 timestamp; }`
(« If set to 0, the allowance is for one-time use and won't be replenished »).
**Aucun champ d'expiration** dans la structure.

**Types.sol** — `enum Clearance { None, Target, Function }`,
`enum ExecutionOptions { None, Send, DelegateCall, Both }`,
`enum AbiType { None, Static, Dynamic, Tuple, Array, Calldata, AbiEncoded }`,
`enum Operator { Pass, And, Or, Nor, Matches, ArraySome, ArrayEvery, ArraySubset,
EqualToAvatar, EqualTo, GreaterThan, LessThan, SignedIntGreaterThan, SignedIntLessThan,
Bitmask, Custom, WithinAllowance, EtherWithinAllowance, CallWithinAllowance }`.

**Roles.sol** — `assignRoles(address module, bytes32[] roleKeys, bool[] memberOf) external onlyOwner`
(« Assign (true) or revoke (false) ») ; `assignRoles` **active le module** sur l'avatar s'il
ne l'est pas déjà ; `execTransactionWithRole(to, value, data, operation, roleKey, shouldRevert)`
et `execTransactionWithRoleReturnData(...)` ; événements `AssignRoles`, `SetDefaultRole`,
`RolesModSetup`, `ConsumeAllowance` (AllowanceTracker.sol).

**Safe v1.4.1 ModuleManager.sol** — `enableModule(address module)` ne vérifie PAS que le
module est un contrat (uniquement non nul, non sentinelle, non déjà présent) → une **EOA
peut être membre d'un rôle** et appeler `execTransactionWithRole` en payant son propre gaz.

## 6. Incident et audits (dates)

- Audit01 RolesV2 Apr2023 G0Group.pdf · Audit02 RolesV2 May2023 Omniscia.pdf ·
  Audit03 RolesV2_1 Nov2023 Omniscia.pdf · Audit04 Roles-V2_1 Nov2023 G0Group.pdf —
  http://github.com/gnosisguild/zodiac-modifier-roles/tree/main/packages/evm/docs (consultés 2026-10-15).
- Post-mortem ERC-1271 (v2.1.0 → v2.1.1), publié 19 juin 2026, exploitation le 1er juin 2026,
  divulgation publique le 2 juin 2026 — https://engineering.gnosisguild.org/posts/zodiac-post-mortem
- Rapport de contournement MultiSend (padding ABI) — https://grego.ai/reports/safe-abi-padding-permission-checks
  (correctif : commit `1ddde84db9024c6c1898d1f4cf5dabded3e824f1` ; date de publication non affichée sur la page = **non trouvé**).
- ENS : confirmation d'absence d'impact (kpk, 4 juin 2026) —
  https://discuss.ens.domains/t/security-update-zodiac-roles-modifier-v2-and-delay-modifier-v1-1-0/22161
