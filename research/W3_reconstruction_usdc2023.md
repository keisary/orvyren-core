# W3-B — Reconstruction de l'épisode USDC mars 2023 (SVB)

**Projet ORVYREN** — sous-agent W3-B. Livrables : `scripts/reconstruct_usdc2023_episode.py`,
`evidence/episode_usdc_2023-03.json`, `tests/test_usdc_episode_2023.py`, `research/W3_reconstruction_usdc2023.md` (ce document).
**Date d'exécution** : 15 octobre 2026 (heures UTC). Toutes les valeurs de ce document proviennent
d'une exécution réelle du script (mode réseau, `eth.drpc.org` / `eth-mainnet.public.blastapi.io`,
APIs publiques sans clé) ; aucune valeur n'est estimée ni recopiée sans vérification.

Ce chantier **complète** W2-A/W2-B et le corpus (`corpus/usdc_observations.csv`, produit par
`collect_corpus.py`) sans le dupliquer : le corpus fournit le pas horaire 09→15 mars sur
Bitstamp/Binance/DeFiLlama + la référence documentaire Circle ; W3 ajoute **OKX**, l'**oracle
Chainlink horaire**, l'**état Aave V3 USDC horaire** et les **signaux dérivés** (décote, dispersion,
divergence), dans un unique fichier de preuve relançable.

---

## 1. Ce que fait le script

`scripts/reconstruct_usdc2023_episode.py` — **autonome, stdlib uniquement** (aucun import de `src/`,
testé par `SelfContainedTest.test_script_imports_stdlib_only`), relançable, déterministe.

Fenêtre : **2023-03-10 00:00Z → 2023-03-14 00:00Z**, **pas horaire, 97 points**.

| Brique | Source | Méthode |
|---|---|---|
| (a) Binance | `api.binance.com/api/v3/klines` USDCUSDT 1 h | 59 points (paire cotée à partir du 11/03 14:00 UTC) |
| (a) OKX | `/api/v5/market/history-candles` USDC-USDT 1H | 97 points, pagination `after` |
| (a) Bitstamp | `/api/v2/ohlc/usdcusd` step=3600 | 97 points (filtrage client : l'API renvoie les 1000 dernières bougies) |
| (a) DeFiLlama | `coins.llama.fi/chart/ethereum:0xA0b8…eB48?period=1h` | 95 points horaires |
| (b) Oracle | Chainlink `USDC / USD` `0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6`, `latestRoundData()` `0xfeaf968c` | 97 lectures, une par heure, **au bloc** de l'heure |
| (c) Aave V3 | aEthUSDC `0x98C2…16F5c` `totalSupply()` + USDC `balanceOf(aEthUSDC)` | 97 lectures, U = 1 − cash/supply |
| (d) Signaux | calculés en sortie | décote, dispersion, divergence (formules §1.2) |

### 1.1 Recherche bloc ↔ timestamp (dichotomie locale)

Exigence : lire `latestRoundData()` **au bloc** de chaque heure. `BlockIndex` :

1. **ancres mesurées** : couples (bloc 16 794 041 ↔ 2023-03-10 00:00:00Z) et (bloc 16 820 846 ↔
   2023-03-13 18:00:00Z), extraits de `research/raw_w2b/aave_usdc_util_mar2023.json` ;
2. **dichotomie locale** (`local_search`) : estimation par interpolation, puis encadrement par
   recherche expansive unilatérale et dichotomie à interpolation — plus grand bloc b tel que
   ts(b) ≤ cible. Convergent même si le rythme de bloc dérive (testé sur un faux RPC synthétique
   à dérive sinusoïdale) ;
3. **affinage par lots** (`resolve_hours`) : les 97 heures sont résolues en 4 tours et
   **463 sondes JSON-RPC en 6 requêtes groupées** (blastapi accepte les tableaux JSON-RPC ;
   drpc renvoie HTTP 500 dessus — testé). Contrôle final : ts(bloc) ≤ heure < ts(bloc+1) pour
   chacune des 97 heures.

Contrôle croisé indépendant (15/10/2026, les **deux** RPC publics concordent au bit) :
bloc 16 803 515 = 2023-03-11 07:59:59Z → oracle **0,8833** ; bloc 16 803 809 = 08:59:59Z →
0,9236 ; bloc 16 805 000 = 12:59:59Z → 0,90687439.

### 1.2 Signaux dérivés (conventions écrites dans le JSON)

- **décote** `D(t) = (1 − p)/1 × 10 000` bps, avec `p` = plus bas horaire par venue (prix
  « stress ») ; deux variantes stockées : `decote_min_bps` (pire prix) et `decote_median_bps`
  (médiane inter-venues — référence robuste).
- **dispersion** `σ_disp = (max − min)/max × 10 000` bps sur les plus bas horaires des venues
  retenues (convention de W2-B, celle qui reproduit « 870 bps »).
- **divergence** `Δ = (médiane_inter_venues − oracle) × 10 000` bps ; **Δ < 0 ⇒ l'oracle est
  au-dessus du marché** (la valorisation retenue surévalue).
- Série Aave : `U = 1 − cash/supply`, avec supply = aEthUSDC.totalSupply, cash = USDC.balanceOf(aEthUSDC).

### 1.3 Sortie

`evidence/episode_usdc_2023-03.json` (~132 Ko) : fenêtre, sources (endpoint + nombre de points +
mode réseau/cache par source), `facts` (minima par venue avec horodatage, dispersion, divergences,
Aave), `w2b_comparison` (contrôle automatique contre les chiffres publiés), et `hourly` —
97 lignes `{utc, ts, venues{low,high,last,volume,n}, market{min,max,median,lowest_venue},
signals{...}, oracle{price,block,updated_at,roundId}, aave{supply,cash,utilisation,block}}`.

---

## 2. Faits clés de W2-B : reproduction (contrôle automatique en sortie de script)

| Fait W2-B | Attendu | Mesuré W3 | Verdict |
|---|---|---|---|
| Agrégat DeFiLlama (min) | 0,876675 (11/03 07:57:53Z) | **0,876675** | reproduit |
| Bitstamp (min) | 0,80526 (11/03 07:00Z) | **0,80526** | reproduit |
| OKX (min) | 0,8698 (11/03 07:00Z) | **0,8698** | reproduit |
| Binance (min) | 0,8820 (11/03 14:00Z) | **0,8820** | reproduit |
| Dispersion inter-venues | ~870 bps | **870,07 bps** (Bitstamp → Binance) | reproduit |
| Oracle Chainlink (min publié) | 0,90687439 (11/03 12:59:35Z) | valeur **présente** dans la série | reproduit (cf. §3.1) |

Interprétations mesurées, par heure cette fois :

- **pire décote de la fenêtre = 1 947,4 bps** (Bitstamp 0,80526) ; décote médiane maximale
  **1 302 bps** (11/03 07:00, OKX 0,8698 / Bitstamp 0,80526 / DeFiLlama 0,876675) ;
- **dispersion maximale à une même heure = 1 047,7 bps** (11/03 08:00 : Bitstamp 0,825 /
  OKX 0,877 / DeFiLlama 0,921553) — le chiffre 870 bps de W2-B compare des minima de fenêtre
  atteints à des heures différentes, la mesure horaire stricte est encore plus forte ;
- **divergence oracle/marché (même heure)** : extrême **−558,9 bps le 11/03 à 03:00 UTC** —
  l'oracle affichait encore 0,99065 alors que la médiane des venues était ~0,935 : la
  valorisation retenue surévalue le collatéral de ~5,6 % au moment le plus chaud, avant que
  l'oracle ne rattrape ;
- le « Bitstamp 0,8627 » du brief, **non reproduit par W2-B**, est expliqué ici : c'est la
  **clôture** de la bougie horaire Bitstamp de 07:00 UTC (`close = 0,86267`), dont le plus bas
  est 0,80526 et le plus haut 0,88020 — même heure, trois lectures différentes ;
- **Aave V3 USDC** : série horaire complète (97 points, contre 20 points à pas de 6 h dans
  raw_w2b). Validation croisée au bloc ancré 16 820 846 : valeurs **identiques** aux mesures
  W2-B (supply 87 945 114,67 / cash 48 943 835,52 / U = 0,4435). Sur la fenêtre :
  U part de 0,6443 (10/03), culmine à 0,8727 (11/03 03:00, ruée sur les retraits), puis
  **s'effondre à 0,2754** (12/03 23:00) sous les dépôts de refuge — la thèse « utilisation →
  100 % = gel » n'est pas illustrée sur cet épisode, conforme à W2-B.

---

## 3. Apports nouveaux (échantillonnage horaire dense)

### 3.1 Correction : le minimum de l'oracle est 0,8833, pas 0,90687

W2-B échantillonnait l'oracle **tous les 1 000 blocs** (~3,35 h, 17 points, dont un trou).
L'échantillonnage horaire (97 points) voit une mise à jour **manquée par cette grille** :
**0,8833 à 07:53:23 UTC le 11 mars** (bloc 16 803 515), soit **−235,7 bps sous le minimum
publié**. La valeur de W2-B (0,90687439, mise à jour 12:59:35) reste exacte et présente dans la
série — c'était le minimum **de sa grille**, pas de la journée. Vérifié deux fois, sur deux RPC
indépendants.

Conséquence sur l'écart oracle/minima de venues (recalculé, bps) : Bitstamp **780,4** /
OKX 135,0 / DeFiLlama 66,2 / Binance 13,0. Autrement dit : même avec le minimum dense, l'oracle
**sous-estimait la décote** face à la venue la plus stressée (Bitstamp, 7,8 %) au plus fort de la
crise ; face à l'agrégat DeFiLlama l'écart se réduit à 66 bps (l'agrégat et l'oracle se suivent
de près — ce sont deux lectures amorties du même marché).

### 3.2 Le signal de divergence a un signe utile dans les deux sens

Au pic (03:00 UTC), **l'oracle surévalue** (Δ ≈ −559 bps) : le danger pour un prêteur qui valorise
au prix de l'oracle. Quelques heures plus tard, à 08:00 UTC, l'oracle (0,8833, déjà repassé) est
**sous** le marché (Δ ≈ +382 bps vs DeFiLlama) : la sur-réaction de l'oracle devient un signal de
rebond. Le fichier stocke les deux extrêmes par heure et par fenêtre.

### 3.3 Reproductibilité et robustesse

- relance réseau complète : ~2 minutes (venues ~15 s, blocs ~50 s, oracles+Aave ~15 s) ;
- `--from-cache` : reconstruction **hors-ligne** depuis `research/raw_w2b/` —
  **les 6 faits W2-B sont reproduits à l'identique** dans ce mode (la série oracle se réduit
  alors à la grille W2-B, `dense_min = 0,90687439`, comportement documenté dans le JSON) ;
- Bitstamp a connu un **timeout transitoire** pendant les tests (WinError 10060) ;
  le script a basculé automatiquement sur le cache en le déclarant (`"mode":
  "cache-fallback"` + erreur enregistrée) ; la relance a fonctionné (97 points réseau).
  Aucun échec silencieux : chaque repli est écrit dans `sources`.

---

## 4. Tests

`tests/test_usdc_episode_2023.py` — **32 tests, zéro réseau** :

| Groupe | Contenu |
|---|---|
| Parseurs | fixtures **réelles** de raw_w2b (bougie Binance 0,8820 ; bougie OKX 0,8698 ; bougie Bitstamp low 0,80526/close 0,86267 ; 2 points DeFiLlama) + tri OKX + filtre de fenêtre |
| Signaux | décote 1 233,25 bps ; dispersion **870,068 bps** (le chiffre W2-B) ; signe de la divergence |
| Décodeurs | `latestRoundData()` sur le retour ABI réel du minimum W2-B ; refus des payloads courts ; `balanceOf` aligné 32 octets ; U Aave = 0,42574151916397907 (valeur publiée W2-B, à 1e-12) |
| BlockIndex | dichotomie locale exacte sur chaîne synthétique (dérive sinusoïdale), expansion de fenêtre (avant/après les ancres), `resolve_hours` par lots + encadrement de chacune des 40 heures |
| Pipeline cache | reconstruction `--from-cache` sur les fichiers du dépôt : 97 points, alignement horaire, **6/6 faits W2-B**, heure 07:00 du 11/03 (0,80526 / 0,8698 / 0,876675 / 0,86267, décote 1 947,4 bps, σ 814,6 bps) |
| Preuve | structure du JSON, faits reproduits, minimum dense de l'oracle, série Aave |
| Autonomie | analyse AST : imports **stdlib uniquement**, aucun import `orvyren`/`src` |

Exécution : `python -m pytest tests/test_usdc_episode_2023.py -q` → **32 passed**.
Suite **complète** : `python -m pytest tests/ -q` → **214 passed, 5 skipped, 0 échec**
(base avant W3-B : 145 passed, 2 skipped ; le total augmente de 32, aucun test existant cassé).

> Remarque (15/10/2026 07:10) : pendant la rédaction, `tests/test_data_layer.py` (agent parallèle
> W3-A/W3-C, fichier en cours d'écriture) affichait 4 échecs momentanés ; ces tests ne référencent
> aucun fichier de W3-B et sont repassés au vert une fois l'agent parallèle stabilisé — la suite
> finale ci-dessus le confirme. Aucun fichier existant n'a été modifié par W3-B.

---

## 5. Limites et blocages (honnêtes)

1. **Kraken** : exclu du script — la pagination `Trades` ne remonte pas correctement à mars 2023
   (constat W2-B confirmé : l'échantillon retombe sur 2026). Sources publiques utilisables pour ce
   venue restant à trouver.
2. **Coinbase** : `USDC-USD` toujours en 404 sans compte — l'épicentre du dépeg reste absent du
   dataset, remplacé par Binance/OKX/Bitstamp/DeFiLlama (déjà l'impasse nommée par W2-A).
3. **DeFiLlama** : couverture horaire incomplète (95/97 heures) et ToS « usage personnel non
   commercial » — à traiter avant une soumission publique.
4. **Bitstamp** : disparition/limites de profondeur — sa bougie 0,80526 est peut-être peu
   exécutable en taille réelle ; le JSON la traite comme « stress de venue », pas comme prix
   de référence (conforme à la lecture W2-B).
5. **Chainlink est un suiveur amorti** : même horaire, il ne détecte pas le pire du marché en
   avance ; il est conservé comme **détecteur de désaccord** (famille 1.3 de W2-B), pas comme
   référence de prix. Le fichier le dit explicitement via ses deux variantes de divergence.
6. **Pas de carnet d'ordres historique** : la profondeur exécutable minute par minute reste hors
   de portée (limite déjà nommée par W2-B) ; ce chantier ne prétend mesurer que des prix OHLC.
7. **Mode cache** : en `--from-cache`, les venues sont bornées à la fenêtre des fichiers bruts
   (03-10 12:00 → 03-12 12:00) et l'oracle/Aave prennent la grille de raw_w2b (3,35 h / 6 h) ;
   chaque source porte son horodatage réel (`sample_utc`, `aligned`) — aucune valeur n'est
   extrapolée.

---

## 6. Relance (commandes exactes)

```bash
python scripts/reconstruct_usdc2023_episode.py                 # réseau -> evidence/episode_usdc_2023-03.json
python scripts/reconstruct_usdc2023_episode.py --from-cache    # hors-ligne (raw_w2b)
python scripts/reconstruct_usdc2023_episode.py --out <chemin>  # autre destination
python -m pytest tests/test_usdc_episode_2023.py -q            # 32 tests, zéro réseau
```

Codes de sortie : `0` si les 6 faits W2-B sont reproduits, `1` sinon (utilisable comme garde CI).
