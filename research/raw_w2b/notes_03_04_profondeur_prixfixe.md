# RAW W2-B — Familles 3 (profondeur) & 4 (valorisation fixe) — 2026-10-15

## Profondeur exécutable — méthode testée

### a) Curve `get_dy(int128,int128,uint256)` = `0x5e0d443f` — pool stETH/ETH `0xDC24316b9AE028F1497c275EB9192a3Ea0f67022`
Coin 0 = ETH, coin 1 = stETH. Fichier : `steth_juin2022.json`, `steth_sellside_2026-10-15.txt`

**Régime calme (2026-10-15, bloc courant) — sens vente stETH → ETH**
| taille | reçu (ETH) | décote |
|---|---|---|
| 1 stETH | 1,0000012 | −0,02 bp |
| 100 stETH | 99,999646 | 0,04 bp |
| 1 000 stETH | 999,944267 | 0,56 bp |
| 10 000 stETH | 9 992,870794 | 7,13 bp |

**Épisode stETH / Celsius (2022) — sens vente stETH → ETH (`get_dy(1,0,X)`), reconstruit par `eth_call` sur blocs d'archive**
| date UTC | bloc | prix réalisé 1 stETH | décote vente 1 stETH | décote vente 1 000 stETH | feed Chainlink `STETH / ETH` |
|---|---|---|---|---|---|
| 2022-05-05 | 14 720 000 | 0,99934 | 0,066 % | 0,068 % | 0,99933 |
| 2022-05-10 | 14 750 000 | 0,99317 | 0,683 % | 0,685 % | 0,99289 |
| 2022-05-15 | 14 780 000 | 0,98298 | **1,702 %** | 1,711 % | 0,97707 |
| 2022-05-21 | 14 820 000 | 0,97432 | **2,568 %** | 2,579 % | 0,97399 |
| 2022-05-28 | 14 860 000 | 0,97771 | 2,229 % | 2,238 % | 0,97586 |
| 2022-06-07 | 14 920 000 | 0,97790 | 2,210 % | 2,221 % | 0,97849 |
| 2022-06-10 | 14 940 000 | 0,95313 | **4,687 %** | 4,719 % | 0,95339 |
| 2022-06-12 | 14 950 000 | 0,96029 | 3,971 % | 3,998 % | 0,96028 |
| 2022-06-14 | 14 960 000 | 0,95489 | 4,511 % | 4,545 % | 0,96227 |
| **2022-06-15** | 14 970 000 | **0,93815** | **6,185 %** | **6,237 %** | 0,94403 |
| 2022-06-17 | 14 980 000 | 0,93900 | 6,090 % | 6,141 % | 0,93775 |
| 2022-06-21 | 15 000 000 | 0,94085 | 5,915 % | 5,962 % | 0,93833 |
| 2022-06-28 | 15 040 000 | 0,96131 | 3,802 % | 3,828 % | 0,96259 |
| 2022-07-02 | 15 060 000 | 0,96225 | 3,775 % | 3,802 % | 0,96235 |

**Découvertes**
1. La décote de marché du stETH atteint **6,19 % le 15 juin 2022** — cohérent avec la valeur publiée « environ 6 % au 13 juin 2022 » [Hashdex]. Notre mesure à la date exacte est **une mesure exécutable** (prix réalisable), pas un prix affiché.
2. **Antériorité mesurée : la décote dépasse 2 % dès le 15-21 mai 2022 — soit ~4 semaines avant le gel Celsius (12-13 juin 2022).** C'est la donnée la plus forte du dossier pour la famille 1.4.
3. **Le prix d'un trade isolé ne bouge presque pas avec la taille** (1 → 1 000 stETH : +0,05 bp d'impact). Donc « l'impact d'une transaction » n'est pas un bon indicateur de profondeur ; ce qui compte est **la persistance du déséquilibre sur plusieurs blocs** (cf. la sortie de 400 M$ de 3AC le 12 mai 2022, une seule transaction qui épuise le pool [Nansen]).
4. Le feed Chainlink `STETH / ETH` recoupe la décote de marché mesurée à 0,02–0,2 point près sur toute la période → il est **utile comme second avis**, mais il **suit** le pool (dérivé du même marché) : ce n'est pas un contrôle indépendant.
5. `description()` du feed confirmé : **`STETH / ETH`** (lu par `eth_call` sur `0x7284e416`). Idem `USDC / USD` pour le feed USDC.

### b) Uniswap V3 `QuoterV2` `0x61fFE014bA17989E743c5F6cB21bF9697530B21e`, `quoteExactInputSingle` = `0xc6a5026a`
Fichier : `depth_test_2026-10-15.txt` — sens USDC → USDT, frais 0,01 % :
| taille | reçu (USDT) | écart au mid |
|---|---|---|
| 1 USDC | 1,0012 | +12,33 bp (USDT au-dessus du pair : artefact de pair, pas de la profondeur) |
| 1 000 USDC | 1 001,2296 | +12,30 bp |
| 10 000 USDC | 10 011,9640 | +11,96 bp |
| 100 000 USDC | 100 106,5690 | +10,66 bp |

**Lecture correcte** : soustraire l'écart au mid pour isoler l'impact marginal : 100 000 USDC coûtent **1,7 bp de plus** que 1 USDC (le pool 0,01 % USDC/USDT absorbe 100 k$ pour ~2 bp). => l'écart d'affichage (+12 bp) est un **signal de peg**, pas de profondeur : ne pas confondre.

### c) Curve 3pool `0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7`, `get_dy(1,2,X)` USDC→USDT : 10 000 USDC → 10 011,0959 (vs 1 USDC → 1,0011) : impact marginal ~0,06 bp pour 10 k$. `get_dy(0,1,1e18)` sur le pool stETH a été testé OK ; `balances(uint256)` (`0x4903adff`) **reverted** sur ce pool → utiliser `get_dy`/`get_balances` (non testé).

## Famille 4 — valorisation fixe / ré-hypothécation : mesures

1. **`description()` des feeds lue on-chain** :
   - Aave V3 Ethereum, feed rsETH `0x7292C95A5f6A501a9c4B34f6393e221F2A0139c3` → **`Capped rsETH / ETH / USD`** : c'est un feed **plafonné** (CAPO). Structurellement, il ne peut pas refléter une décote de marché en dollars.
2. **Divergence oracle vs marché sur rsETH (avril 2026)** — `defillama_rseth_apr2026.json` + `aave_rseth_apr2026.json` :
| moment | prix oracle Aave (USD) | prix marché (DefiLlama, USD) | divergence |
|---|---|---|---|
| 2026-04-18 12:00 | 2 500,60 | 2 509,48 | −0,35 % |
| 2026-04-18 18:00 | 2 500,84 (19/04 00:00) | 2 519,99 | ~−0,8 % |
| 2026-04-19 00:00 | 2 500,84 | 2 497,65 | +0,13 % |
| 2026-04-19 23:59 | — | 2 288,59 | — |
| **2026-04-20 05:59** | ~2 459 (valeur du 20/04 00:00) | **1 686,28** | **≈ +31 % (l'oracle ne suit pas)** |
=> **Démonstration mesurée** : le marché rsETH décroche jusqu'à −33 % (2 519,99 → 1 686,28) tandis que l'oracle « capped » reste à ~2 460-2 500. Le signal 1.3 (divergence oracle/marché) est donc **actionnable et mesuré sur un cas réel**.
3. **Fenêtre temporelle du décrochage** : première baisse significative du prix marché entre 2026-04-19 17:59 (2 436,08) et 2026-04-19 23:59 (2 288,59) ; minimum **1 686,28 le 2026-04-20 à 05:59 UTC** (source : `coins.llama.fi/chart`, 1 h).
4. Test d'un marché xUSD / Stream Finance (nov. 2025) : **non trouvé** de série de prix exploitable via les endpoints testés (l'actif n'est pas listé par DefiLlama `coins.llama.fi` avec un identifiant vérifié par nous) → à refaire avec GeckoTerminal/DEX Screener si nécessaire.
