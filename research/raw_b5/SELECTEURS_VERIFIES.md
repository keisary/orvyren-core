# B5 — sélecteurs vérifiés (Base Sepolia, 2026-10-15)

Méthode : implémentation **Keccak-256 en Python pur** (`keccak_selectors.py`, validée sur les vecteurs
`keccak256("")` et `keccak256("abc")`), puis **vérification fonctionnelle** (`eth_call`) et/ou
**recherche dans le bytecode déployé** (`eth_getCode` → présence du sélecteur comme immediate PUSH4 dans le
dispatcher). Contrôles négatifs inclus (`0xdeadbeef`, `0x0d1e2f3a` absents partout où testés).

| Signature canonique | Sélecteur | Vérification | Où |
|---|---|---|---|
| `transfer(address,uint256)` | `0xa9059cbb` | keccak + tests internes `tests/test_execution.py` | jeton USDC Circle |
| `approve(address,uint256)` | `0x095ea7b3` | keccak | — |
| `balanceOf(address)` | `0x70a08231` | keccak + usage repo | — |
| `Transfer(address,address,uint256)` (topic0) | `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | keccak — **égal** à la constante de `verify.py` | — |
| `quoteExactInputSingle((address,address,uint256,uint24,uint160))` | `0xc6a5026a` | **usage réel** : quote vivante obtenue (50 USDC → WETH) | QuoterV2 `0xC529…5E27` |
| `exactInputSingle((address,address,uint24,address,uint256,uint256,uint160))` (SwapRouter02, sans deadline) | `0x04e45aaf` | **fonctionnel** : revert `STF` (Error(string)) → la fonction s'exécute | SwapRouter02 `0x94cC0A…2bc4` |
| `exactInputSingle(…,uint256,uint160)` (variante v1, avec deadline) | `0x414bf389` | **absent** du SwapRouter02 déployé (revert vide) | — |
| `supply(address,uint256,address,uint16)` | `0x617ba037` | bytecode **PRÉSENT** + fonctionnel (revert `InvalidAmount()` `0x2c5211c6`) | Pool Aave `0x8bAB…aE27` |
| `withdraw(address,uint256,address)` | `0x69328dec` | bytecode **PRÉSENT** | Pool Aave |
| `borrow(address,uint256,uint256,uint16,address)` | `0xa415bcad` | bytecode **PRÉSENT** | Pool Aave |
| `getReserveData(address)` | `0x35ea6a75` | bytecode PRÉSENT + usage réel | Pool Aave |
| `getReservesList()` | `0xd1946dbc` | bytecode PRÉSENT + usage réel | Pool Aave |
| `getUserAccountData(address)` | `0xbf92857c` | usage réel (retour de données valide) | Pool Aave |
| `repay(address,uint256,uint256,address)` (forme avec `rateMode`) | `0x573ade81` | bytecode **PRÉSENT** (impl. `0xE9fb…783A`, slot EIP-1967 du proxy vérifié) | Pool Aave |
| `repay(address,uint256,address)` (forme « v3 » usuelle) | `0x5ceae9c4` | bytecode **ABSENT** → l'appel repay doit se construire sur la signature réellement déployée | Pool Aave |
| `execTransactionWithRole(address,uint256,bytes,uint8,bytes32,bool)` | `0xc6fe8747` | bytecode PRÉSENT + **fonctionnel** : revert `NotAuthorized(address)` `0x4a0bfec1` depuis un non-membre | module Roles `0xF296…83D5` |
| `execTransactionWithRoleReturnData(…)` | `0x2b99e506` | bytecode PRÉSENT | module Roles |
| `assignRoles(address,bytes32[],bool[])` | `0x957ed2b3` | bytecode PRÉSENT | module Roles |
| `allowTarget(bytes32,address,uint8)` | `0x7b0da5b2` | bytecode PRÉSENT | module Roles |
| erreur `NotAuthorized(address)` | `0x4a0bfec1` | identifiée par brute force keccak — **c'est ce que le module renvoie** quand un non-membre appelle `execTransactionWithRole` | module Roles |

Notes :
- `0x4a0bfec1` **remplace** le `NoMembership` supposé par W2C §e (#3) : à la démo, journaliser le sélecteur
  constaté (`NotAuthorized(address)`), pas un nom supposé.
- L'annuaire public 4byte.directory s'est révélé **bruité** (plusieurs hex pour une même signature texte,
  entrées fantaisistes) — d'où le calcul local du keccak dans cette étude.
- Scripts : `keccak_selectors.py`, `probe_selectors.py`, `probe_roles_repay.py`, `probe_bytecode.py`,
  `probe_bruteforce.py` (tous dans `raw_b5/`, sorties `.txt`).
