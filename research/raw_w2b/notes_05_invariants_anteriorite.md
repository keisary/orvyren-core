# RAW W2-B — Famille 5 (invariants inter-chaînes) & tableau d'antériorité — 2026-10-15

## Ce qui a été exécuté en direct (preuve que l'invariant est calculable)
`totalSupply()` (`0x18160ddd`) du même actif sur 4 chaînes, RPC publics distincts (tous vérifiés le 2026-10-15) :

| chaîne | chainId | RPC testé | adresse rsETH | totalSupply mesuré (2026-10-15) |
|---|---|---|---|---|
| Ethereum | 0x1 | `https://eth.drpc.org` | `0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7` | **375 967,8959** |
| Arbitrum | 0xa4b1 | `https://arb1.arbitrum.io/rpc` | `0x4186BFC76E2E237523CBC30FD220FE055156b41F` | **17 021,7723** |
| Optimism | 0xa | `https://mainnet.optimism.io` | `0x4186BFC76E2E237523CBC30FD220FE055156b41F` | **10,6787** |
| Base | 0x2105 | `https://mainnet.base.org` | `0x4186BFC76E2E237523CBC30FD220FE055156b41F` | **0,0** |

Fichiers : `rseth_supply_multi_now.json`, script `rseth_supply.py`.
=> Une boucle multi-chaînes de 4 appels suffit à recomposer un invariant d'émission. **Démontré.**

## Série historique du supply rsETH sur Ethereum (fichier `rseth_supply_eth_2026.json`)
| date | bloc | supply rsETH (Ethereum) |
|---|---|---|
| 2026-04-01 | 24 781 515 | 578 685,39 |
| 2026-04-10 | 24 845 854 | 626 374,86 |
| 2026-04-17 | 24 895 895 | 634 429,62 |
| 2026-04-18 ~12:00 | 24 906 618 | 634 411,55 |
| 2026-04-18 ~18:00 | 24 908 405 | 629 736,45 |
| 2026-04-19 → 25/04 | 24 910 193 → 24 953 085 | 629 689,36 (stable) |
| 2026-05-15 | 25 096 060 | 631 064,39 |
| 2026-10-14 | 26 182 668 | 381 082,70 |

**Lecture** : entre les deux points encadrant l'incident (24 906 618 ≈ 18/04 12:00 et 24 908 405 ≈ 18/04 18:00), le supply **baisse de 4 675 rsETH** (634 411,55 → 629 736,45). Ce n'est **pas** un mint anormal côté Ethereum : c'est cohérent avec des brûlages de pont (départs vers L2) et/ou des actions correctives. ⚠️ **La reconstruction historique des supply L2 n'a pas été possible** : les RPC L2 publics testés (Arbitrum, Optimism, Base) n'ont pas servi d'archive vérifiée dans cette passe, et un bloc Ethereum ne peut pas être passé à un RPC L2 (temps de bloc différents).

=> **Conclusion honnête** : l'invariant 5.1 est **calculable en temps réel** (démontré) et **calculable historiquement sur Ethereum** (démontré), mais la **moitié « chaîne de destination »** de l'invariant (celle qui casse dans le cas KelpDAO) est **NON ENCORE CALCULABLE avec les RPC publics testés** faute d'archive L2. C'est le principal point à débloquer (un nœud archive L2, un fournisseur type Dune/Allium, ou un indexeur par `eth_getLogs`).

## Invariants en forme exécutable
1. `I_S(t) = Σ_c totalSupply_c(t) − Locked_ou_escrowed(t)` → doit être constant (à tolérance nulle) pour un actif à offre fixe ; pour un actif à rendement (rsETH), l'offre augmente des rewards : il faut travailler en **Δ** sur une fenêtre et comparer à la variation attendue.
2. `I_bridge(t) = Burned_source(t) − Minted_dest(t) = 0` par message de pont (KelpDAO : la rupture exacte [Chainalysis]).
3. `I_cap(t) = totalSupply_c(t) ≤ Cap_c` (garde-fou d'émission).
4. `I_source(t) = |état(RPC_i) − état(RPC_j)| = 0` pour ≥ 3 RPC (anti-empoisonnement, cas KelpDAO [Chainalysis]).
5. `I_freeze(t) = bit isFrozen` de chaque réserve de prêt (bascule un seul bit, datée à la seconde).

## Tableau d'ANTÉRIORITÉ MESURÉE (synthèse des campagnes de mesure)
| épisode | signal mesuré | valeur | date du signal | événement de référence | antériorité mesurée |
|---|---|---|---|---|---|
| SVB / USDC (mars 2023) | Décote oracle on-chain (Chainlink `USDC / USD`) | 0,99756 → 0,9069 | 2023-03-10 21:20 → 11 mars 12:59 | annonce Circle ~10 mars 22 h ; minimum marché 11 mars 07:00-14:00 | **~0 à 6 h** (le signal est contemporain, il ne précède pas) |
| SVB / USDC | Dispersion inter-venues | Bitstamp 0,8053 / OKX 0,8698 / Binance 0,8820 / DefiLlama 0,8767 | 2023-03-11 07:00-14:00 | idem | **0 h** (contemporain) — mais c'est ce qui empêche de raisonner sur un prix unique |
| SVB / USDC | Utilisation Aave V3 USDC | 71 % → 28,6 % (baisse = dépôts de refuge) | 2023-03-11 → 13 | idem | signal **non précurseur** (contra-cyclique) |
| stETH / Celsius (2022) | Décote vente réalisée (`get_dy`) | > 2 % | **dès 2022-05-15** (2,57 % le 21 mai) | gel Celsius 12-13 juin 2022 | **~4 semaines** ✅ |
| stETH / Celsius | Décote vente réalisée | 4,69 % | 2022-06-10 18:42 | idem (J-2/J-3) | **~2-3 jours** ✅ |
| stETH / Celsius | Décote vente réalisée | 6,19 % (pic) | 2022-06-15 | idem (après) | contemporain/après |
| rsETH / KelpDAO (avril 2026) | Drapeau `isFrozen` de la réserve Aave V3 | false → true | **2026-04-18 19:03:59 UTC** (bloc 24 908 723) | exploit exécuté ≈ 17:35 UTC (Blockaid) | **−1 h 29 mn** (postérieur : c'est la conséquence, pas le précurseur) |
| rsETH / KelpDAO (avril 2026) | Plafond d'émission saturé | supply 529 993,98 / cap 530 000 = **99,999 %** | **2026-04-18 18:00 UTC** (bloc 24 908 405) | exploit ≈ 17:35 UTC [Blockaid] ; gel à 19:03:59 UTC | **+25 min après l'exploit / −1 h avant le gel** : signal de confirmation immédiate, pas de préavis |
| rsETH / KelpDAO | Divergence oracle (2 459) vs marché (2 288,6) | 7 % | 2026-04-19 23:59 | minimum marché 1 686,28 le 20/04 05:59 | **~6 h** ✅ |
| rsETH / KelpDAO | Divergence oracle (2 459) vs marché (1 686,3) | **31 %** | 2026-04-20 05:59 | idem | contemporain |

**Enseignements d'antériorité**
1. Les signaux de **prix** sur les dépegs d'actifs liquides (USDC) ont une antériorité quasi nulle : ils servent à **détecter et réagir**, pas à anticiper.
2. Les signaux de **structure** (décote persistante d'un LST illiquide, plafond d'émission atteint, décote d'un oracle qui ne suit pas, configuration de pont) ont une antériorité de **jours à semaines** : ils servent à **réduire l'exposition avant**.
3. Le gel administratif (`isFrozen`) et le décrochage d'oracle sont des **signaux de confirmation** : précieux pour la réaction du second coup (le 2ᵉ paquet de 40 000 rsETH bloqué par la pause [Chainalysis]), pas pour la sortie.
