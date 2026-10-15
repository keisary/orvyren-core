# RAW W2-B — Famille 2 : utilisation des marchés de prêt — 2026-10-15

## Formule vérifiée
`U_r = 1 − cash_r / S_r` avec `cash_r = underlying.balanceOf(aToken)` (`0x70a08231`) et `S_r = aToken.totalSupply()` (`0x18160ddd`).
Endpoint : `eth_call` sur RPC public (archive disponible : `https://eth.drpc.org`, `https://eth-mainnet.public.blastapi.io`).

## Adresses vérifiées (source : `bgd-labs/aave-address-book`, récupéré 2026-10-15)
`raw_w2b/AaveV3Ethereum.sol`, `raw_w2b/AaveV3Arbitrum.sol`
- Aave V3 Ethereum — Pool `0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2` ; Oracle `0x54586bE62E3c3580375aE3723C145253060Ca0C2`
- USDC `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` / aEthUSDC `0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c`
- rsETH `0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7` / aEthrsETH `0x2D62109243b87C4bA3EE7bA1D91B0dD0A074d7b1` / vToken `0x6De3E52A1B7294A34e271a508082b1Ff4a37E30e` / feed oracle `0x7292C95A5f6A501a9c4B34f6393e221F2A0139c3`
- WETH `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` / aEthWETH `0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8`
- Aave V3 Arbitrum — Pool `0x794a61358D6845594F94dc1DB02A252b5b4814aD`, Oracle `0xb56c2F0B653B2e0b10C9b928C8580Ac5Df02C7C7`, rsETH `0x4186BFC76E2E237523CBC30FD220FE055156b41F`, aArbrsETH `0x6b030Ff3FB9956B1B69f475B77aE0d3Cf2CC5aFa`

## Mesure A — USDC sur Aave V3 Ethereum (aujourd'hui)
Bloc 26 195 096 (2026-10-15 02:56 UTC) : `S = 2 381 563 177,57 USDC` ; `cash = 139 534 235,54 USDC` → **U = 94,1411 %**.
Fichier : `decode1_output.txt`.

## Mesure B — USDC sur Aave V3 Ethereum pendant la crise SVB (mars 2023) → fichier `aave_usdc_util_mar2023.json`
| UTC | supply (M USDC) | cash (M USDC) | U |
|---|---|---|---|
| 2023-03-09 00:00 | 62,43 | 19,35 | 69,00 % |
| 2023-03-10 12:00 | 63,79 | 22,53 | 64,68 % |
| 2023-03-11 00:00 | 58,98 | 17,09 | **71,02 %** |
| 2023-03-11 12:00 | 78,97 | 45,35 | 42,57 % |
| 2023-03-12 00:00 | 86,63 | 57,41 | 33,73 % |
| 2023-03-13 00:00 | 104,52 | 74,58 | **28,65 %** |
| 2023-03-13 18:00 | 87,95 | 48,94 | 44,35 % |

=> **L'utilisation a BAISSÉ (69 % → 28,6 %) pendant la crise SVB sur Aave V3** : les dépôts ont afflué (refuge) et les sorties ont été servies. La thèse « utilisation → 100 % = gel » n'est **pas** illustrée par cet épisode sur Aave V3. Elle est illustrée par le rsETH (ci-dessous) sous une autre forme : **le gel administratif**.

## Mesure C — Marché rsETH sur Aave V3 Ethereum (avril 2026) → `aave_rseth_apr2026_v2.json` (ancre vérifiée), `run_rseth3.py`
⚠️ Correction : la première passe utilisait un modèle linéaire de bloc qui dérive de ~15 h en 2026. La série ci-dessous est recalée sur une **ancre vérifiée** (bloc 24 908 723 = 2026-04-18 19:03:59 UTC, lu par `eth_getBlockByNumber`), et contrôlée sur 2 points (écart final ≤ 11 min).

| UTC | bloc | aEthrsETH supply (rsETH) | cash (rsETH) | U | prix oracle Aave (USD) |
|---|---|---|---|---|---|
| 2026-04-16 00:00 | 24 888 748 | 481 469,68 | 481 427,60 | 0,0087 % | 2 524,49 |
| 2026-04-17 00:10 | 24 895 896 | 480 708,30 | 480 666,23 | 0,0088 % | 2 518,61 |
| 2026-04-18 00:00 | 24 903 044 | 481 818,50 | 481 776,43 | 0,0087 % | 2 591,12 |
| 2026-04-18 06:00 | 24 904 831 | 481 818,55 | 481 776,48 | 0,0087 % | 2 577,11 |
| 2026-04-18 12:00 | 24 906 618 | 481 268,58 | 481 226,51 | 0,0087 % | 2 510,51 |
| **2026-04-18 18:00** | 24 908 405 | **529 993,98** | 529 951,91 | 0,0079 % | 2 529,34 |
| 2026-04-18 19:03 | 24 908 718 | 529 482,81 | 529 440,73 | 0,0079 % | 2 513,66 |
| 2026-04-19 00:00 | 24 910 192 | 525 805,59 | 525 763,51 | 0,0080 % | 2 517,78 |
| 2026-04-20 06:00 | 24 919 128 | 525 801,65 | 525 759,57 | 0,0080 % | 2 429,53 |
| 2026-04-25 00:00 | 24 953 081 | 525 786,11 | 525 744,04 | 0,0080 % | 2 476,01 |

=> **U ≈ 0,008 % (essentiellement zéro emprunt)** : sur Aave V3 Ethereum, le marché rsETH n'a **pas** été gelé par saturation d'utilisation. Le brief (« gel à 100 % d'utilisation ») n'est **pas reproduit** sur ce marché : la cause du gel est un **drapeau de gel administratif** (mesure D).
=> **Fait majeur mesuré** : entre le 18/04 12:00 et 18:00 UTC, le collatéral déposé passe de **481 268,58 → 529 993,98 rsETH (+48 725 rsETH en 6 h)** et le **`supplyCap` de 530 000 rsETH est atteint à 99,999 %**. Le marché est saturé à son plafond au moment même de l'incident (rappel : 89 567 rsETH déposés sur Aave pour emprunter 190 M$ de WETH selon OpenZeppelin).
=> Le prix oracle Aave reste entre **2 429 et 2 591 $** du 16 au 25 avril, alors que le prix de marché tombe à **1 686,28 $** le 20/04 à 05:59 UTC (fichier `defillama_rseth_apr2026.json`).

## Mesure D — Drapeaux de la réserve rsETH, par `Pool.getReserveData` (`0x35ea6a75`), mot 0 = configuration
Fichiers : `aave_rseth_reserveconfig.json`, `aave_rseth_freeze_block.json`, script `freeze_search.py`
- LTV = 0 ; liquidationThreshold = 75 % ; liquidationBonus = 1,075 ; decimals = 18 ; reserveFactor = 15 % ; **supplyCap = 530 000 rsETH** ; eMode = 0 ; `isActive = true` ; `borrowingEnabled = false`.
- **`isFrozen` : false → true**. Recherche dichotomique exacte :
  - **dernier bloc NON gelé : 24 908 722 — 2026-04-18 19:03:47 UTC**
  - **premier bloc GELÉ : 24 908 723 — 2026-04-18 19:03:59 UTC**
- Un autre bit (position 60, interprété comme « paused ») passe à 1 au bloc 24 957 514 (≈ 2026-04-25) puis revient à 0 (06-01 et 10-14).
- Aucun autre bit ne change : le basculement du 18 avril est **un seul bit**.

=> **C'est LA mesure d'antériorité de la famille 2** : le gel de la réserve rsETH est daté on-chain à la seconde (19:03:59 UTC le 18/04/2026), soit **~1 h 29 après** l'exécution de l'exploit documentée par Blockaid (≈ 17:35 UTC [Blockaid]). À partir de ce bloc, plus aucune sortie de rsETH depuis Aave V3 Ethereum n'est possible.
=> Le club des signaux exploitables : (i) `isFrozen` bascule (1 appel, 1 bit), (ii) `supplyCap` atteint (525 805 / 530 000 = 99,2 %), (iii) U ≈ 0 (le marché est un simple dépôt, pas un marché de crédit → un gel sec est plus probable qu'une liquidation).

## Non testé / limites
- Aave V3 **Arbitrum** historique : `arb1.arbitrum.io/rpc` n'accepte pas l'appel au bloc demandé (bloc Ethereum passé à un RPC Arbitrum) → **non testé**, à refaire avec un bloc Arbitrum dérivé de son propre temps de bloc.
- Compound (V2/V3), Morpho : formules identifiées, **non testées** ici.
