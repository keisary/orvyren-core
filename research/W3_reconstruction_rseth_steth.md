# W3-A — Reconstruction exécutable des épisodes rsETH (avril 2026) et stETH (juin 2022)

**Version 1 — 2026-10-15.** Sous-agent W3-A. Dépôt `D:\orvyren_core`.

**Livrables de cette note**

| Livrable | Rôle |
|---|---|
| `src/orvyren/data/{__init__,rpc,aave,curve,chainlink}.py` | couche données : lecture d'archive Ethereum en bibliothèque standard |
| `scripts/reconstruct_rseth_episode.py` | reconstruit l'épisode rsETH/KelpDAO en JSON de preuve |
| `scripts/reconstruct_steth_episode.py` | reconstruit l'épisode stETH/Celsius (décote **réalisable** Curve) en JSON de preuve |
| `evidence/episode_rseth_2026-04.json` | preuve mesurée, 100 points horaires + blocs clés |
| `evidence/episode_steth_2022-06.json` | preuve mesurée, série mai-juillet 2022 + zoom horaire 10-17 juin |
| `tests/test_data_layer.py` | 44 tests hors-ligne (fixtures = JSON archivés W2-A/W2-B) |
| `scripts/recon_common.py` | résolution bloc↔horodatage, parallélisation, écriture atomique |

**Règle de lecture** : chaque chiffre de cette note vient d'un appel réel effectué le 2026-10-15
via `https://eth.drpc.org` / `https://eth-mainnet.public.blastapi.io`, ou d'un fichier de
`research/raw_w2a/` / `research/raw_w2b/` explicitement cité. Rien n'est estimé sans le dire.

---

## 0. Résumé exécutif

1. **La couche données ne coûte aucune dépendance** : uniquement `urllib`/`http.client`, `json`,
   `datetime`. Elle lit l'état **à un bloc d'archive** (2022 → 2026) sur les deux RPC publics
   gratuits déjà validés par W2-A/W2-B, avec bascule d'endpoint, timeouts et erreurs typées.
2. **L'épisode rsETH est reconstruit à la seconde** : 100 points (horaire 2026-04-17T00:00Z →
   2026-04-21T00:00Z + les 5 instants clés), saturation du plafond d'émission à
   **99,9989 % (529 993,9827 / 530 000)** le 18/04 à 18:00 UTC, et surtout le **gel daté par
   recherche dichotomique : dernier bloc non gelé 24 908 722 (19:03:47), premier bloc gelé
   **24 908 723 = 2026-04-18T19:03:59Z** (14 appels). Pendant ce temps l'oracle de la réserve
   reste à **2 526,76 $** à l'exploit, **2 513,66 $** au gel et **2 419,21 $** le 20/04 : la
   « valorisation retenue » continue d'afficher un collatéral qui n'a plus de prix de sortie.
3. **Découverte d'ABI mesurée** : le feed Aave `Capped rsETH / ETH / USD`
   (`0x7292C95A…139c3`) **réverte sur `latestRoundData()`** ; seuls `description()`,
   `decimals()` et `latestAnswer()` répondent. La couche données le gère (repli documenté) et
   vérifie au passage que `AaveOracle.getAssetPrice(rsETH)` **égale** `latestAnswer()` sur les
   5 blocs clés.
4. **L'épisode stETH est reconstruit en décote réalisable** (`get_dy(1,0,X)` sur le pool Curve
   stETH/ETH, sens vérifié : coin 1 = stETH → coin 0 = ETH) sur **253 points** (journalier
   2022-05-01 → 2022-07-31 + horaire 2022-06-10 → 2022-06-17), 0 erreur :
   **régime > 2 % dès le 2022-05-13** (213,7 bps, contre 66,9 bps la veille),
   **pic 6,93 % (692,5 bps) le 2022-06-14 à 10:00 UTC** (755,4 bps pour 10 000 stETH),
   **6,42 % à 22:00 le 15 juin**, **3,84 % le 30 juin** ; plancher de calme 0,082 % le
   1er mai 2022. **227 des 253 points restent au-dessus de 2 %**, jusqu'au 31 juillet inclus.
   Le point de référence de W2-B (bloc 14 970 000, 15/06 22:43:58, **6,185 %**) est reproduit à
   l'identique par les tests depuis l'archive.
5. **Le banc de tests grandit sans casser l'existant** : **44 tests ajoutés** (0 accès réseau),
   suite complète **223 tests OK** (`python -m unittest discover -s tests`), contre 147 avant.

---

## 1. Couche données (`src/orvyren/data/`)

### 1.1 `rpc.py` — client d'archive

* **Bascule d'endpoint** : chaque requête parcourt `https://eth.drpc.org` puis
  `https://eth-mainnet.public.blastapi.io` ; une erreur de transport est réessayée sur le même
  endpoint (`retries`, `backoff`), une erreur JSON-RPC passe à l'endpoint suivant, sauf si elle
  est **contractuelle** (`execution reverted`, `invalid opcode`…) : dans ce cas on s'arrête, la
  réponse est identique partout.
* **Erreurs claires** : `RpcError` (méthode + endpoints + dernière cause), `RpcRangeError` pour
  `eth_getLogs` (limite mesurée : **10 000 blocs par requête** sur les paliers gratuits).
* **`get_logs`** pagine automatiquement toute plage en tranches ≤ 10 000 blocs et refuse
  `chunk_size > MAX_GET_LOGS_RANGE` (plutôt que d'envoyer une requête qui sera rejetée).
* **Recherche bloc↔horodatage** (`block_at_timestamp`) : ancres mesurées (voir tableau §1.5),
  estimation sécante + **garde de bisection**, et vérification du plancher
  `ts(bloc) <= cible < ts(bloc+1)` faite par l'appelant (`recon_common.resolve_blocks`).
* **Grille de blocs** (`resolve_blocks` / `resolve_blocks_parallel`) : pour une grille
  croissante, le bloc suivant est **estimé linéairement** depuis le point précédent
  (horodatage en cache + temps de bloc mesuré, 13,35 s avant Le Merge / 12,09 s après) ; si
  l'estimation est déjà le bloc-plancher, elle est gardée telle quelle, sinon une recherche
  sécante tourne dans une fenêtre de ±400 blocs autour d'elle. Chaque point est **vérifié
  contre la chaîne** (`ts(bloc) <= cible < ts(bloc+1)`), un échec élargit la fenêtre, et la
  grille est résolue **en parallèle par tranches contiguës**. Mesuré : 9,9 s/point en
  séquentiel → **2,07 s/point avec 5 tranches** sur une grille horaire ; une grille
  *journalière* (pas de 24 h, pire cas d'estimation, temps de bloc de juin 2022 à ~14,3 s
  contre une moyenne de 13,35 s) coûte ~10 s/point en séquentiel, dont une seule recherche
  pleine fenêtre par tranche. Le plan de blocs est écrit dans le JSON dès la fin de cette
  phase, pour qu'un run interrompu n'ait pas à la refaire : les 253 blocs de l'épisode stETH
  (soit ~9 minutes de recherche à 5 tranches) sont ainsi rejouables hors-ligne.
* **Transport keep-alive** (`HttpTransport`) : une connexion persistante par endpoint. Mesuré :
  ~0,65 s/appel séquentiel sur `eth.drpc.org`, ~0,36 s sur blastapi ; 8 fils → **12,4 appels/s**
  (la reconstruction rsETH de 2 000+ lectures tient en ~9 minutes au lieu de > 20).
* **Codec ABI** : `encode_uint/int/address`, `decode_words/uint/int/address/string` (la chaîne
  dynamique sert à lire `description()`).

**Deux pièges mesurés, corrigés et testés** (ils ont réellement cassé une exécution) :

1. **Le bloc 0 n'a pas d'horodatage** (`timestamp = 0x0`) : le temps de genèse réel
   (2015-07-30T15:26:28Z) est porté par le **bloc 1**. Une ancre sur le bloc 0 modèle la chaîne
   comme démarrant au 1er janvier 1970, et la recherche converge alors vers le bloc 0 en
   épuisant ses 64 itérations (mesuré sur la cible 2022-05-01, le 2026-10-15). Les ancres
   partent donc du bloc 1, et la garde de bisection garantit la progression même si un modèle
   est faux.
2. **Les horodatages mis en cache doivent être réellement mesurés** : la table d'ancres a été
   vérifiée bloc par bloc contre la chaîne (deltas **+0 s** sur les 6 ancres) ; la version
   initiale contenait une coquille (`14720000 → 1651782002` au lieu de `1651791602`).

### 1.2 `aave.py` — réserve Aave V3

* `getReserveData` (`0x35ea6a75`) décodé en 13 champs nommés ; **mot de configuration** décodé
  bit à bit : LTV (0-15), seuil de liquidation (16-31), bonus (32-47), décimales (48-55),
  `isActive` (56), **`isFrozen` (57)**, `borrowingEnabled` (58), `paused` (60), `borrowCap`,
  `supplyCap`, catégorie e-mode. Valeurs de référence mesurées : LTV `0`, seuil `7500`,
  bonus `10750`, décimales `18`, `supplyCap` `530 000`, `borrowCap` `1`.
* `reserve_state(asset, bloc)` : supply aToken, `cash` (solde du sous-jacent porté par l'aToken),
  dette variable, **deux utilisations** (`utilisation` = dette/supply, définition utilisée pour
  WETH ; `utilisation_cash_gap` = 1 − cash/supply, définition du signal 2.1 de W2-B), `cap_ratio`
  (supply aToken / supplyCap), prix oracle.
* `find_freeze_block` : dichotomie sur le bit `isFrozen`, bornée par un bloc non gelé et un bloc
  gelé, datée des deux côtés.

### 1.3 `curve.py` — prix **réalisable**

* `get_dy(i, j, dx)` (`0x5e0d443f`), `balances(i)`, `coins(i)`.
* **Sens vérifié** : `coins(0)` = `0xEeee…EEeE` (ETH), `coins(1)` = stETH
  (`0xae7ab9…7fE84`) → **vendre est `get_dy(1, 0, X)`**, prix = `dy/dx`, décote = `1 − dy/dx`.
* Objet `SwapQuote` : montants, prix, **décote en points de base**, sérialisation JSON.
  Échelle d'exécution pour 1 / 100 / 1 000 / 10 000 stETH.

### 1.4 `chainlink.py` — oracle au bloc

* `latestRoundData()` (`0xfeaf968c`), `latestAnswer()` (`0x50d25bcd`), `description()`
  (`0x7284e416`), `decimals()` (`0x313ce567`) ; `RoundData.age_seconds()` pour la fraîcheur.
* **Cas mesuré** : sur le feed plafonné rsETH, `latestRoundData()` réverte →
  `ChainlinkFeed.price()` retombe sur `latestAnswer()` et l'indique (`"method": "latestAnswer"`,
  `updated_at = null`). Les autres feeds (STETH/ETH en 18 décimales, USDC/USD et ETH/USD en 8)
  répondent normalement.

### 1.5 Ancres bloc↔horodatage vérifiées (2026-10-15)

| Bloc | Horodatage | Chaîne | Écart |
|---|---|---|---|
| 1 | 2015-07-30T15:26:28Z | idem | +0 s |
| 14 720 000 | 2022-05-05T23:00:02Z | idem | +0 s |
| 14 970 303 | 2022-06-16T00:01:03Z | idem | +0 s |
| 15 537 394 | 2022-09-15T06:42:59Z (The Merge) | idem | +0 s |
| 16 801 143 | 2023-03-10T23:59:59Z | idem | +0 s |
| 24 908 723 | 2026-04-18T19:03:59Z (gel rsETH) | idem | +0 s |

Cibles testées en fenêtre complète (bloc 1 → tête), toutes conformes au plancher
`ts(bloc) <= cible < ts(bloc+1)` : 2022-05-01 → 14 688 629 ; 2022-05-15 → 14 776 687 ;
2022-06-10 → 14 935 368 ; **2022-06-15T22:43:58Z → 14 970 000** ; 2022-07-31 → 15 246 903 ;
2023-03-11T12:59:59Z → 16 805 000 ; 2026-04-18T19:03:59Z → 24 908 723.

---

## 2. Épisode rsETH / KelpDAO — `evidence/episode_rseth_2026-04.json`

**Mode de production** : `rpc` (réseau), `meta.complete = true`, **100 / 100 points**,
0 point en erreur, grille = horaire 3600 s du 2026-04-17T00:00Z au 2026-04-21T00:00Z + les 5
instants clés (exploit, saturation, gel Guardian, gel on-chain, 20/04 00:00Z).
Réserve suivie : Aave V3 Ethereum Core — rsETH (collatéral), WETH et USDC.

### 2.1 Les chiffres cibles

| Mesure | Valeur reconstruite | Où |
|---|---|---|
| Saturation du plafond rsETH | **0,9999886466** = 529 993,9827 / 530 000 (**99,9989 %**) | 2026-04-18T18:00:00Z, bloc 24 908 406 |
| Dernier bloc **non gelé** | 24 908 722 — 19:03:47 UTC | recherche dichotomique, 14 itérations |
| Premier bloc **gelé** | **24 908 723 — 2026-04-18T19:03:59Z** | idem |
| Oracle rsETH retenu à l'exploit | **2 526,7563881 $** | bloc 24 908 282 = 17:34:59 UTC |
| Oracle rsETH retenu au gel | 2 513,66460329 $ | bloc 24 908 723 |
| Oracle rsETH retenu le 20/04 | 2 419,21294349 $ | bloc 24 917 376 = 2026-04-19T23:59:59Z |
| Pic de l'oracle (session) | 2 631,56608381 $ | 2026-04-17T17:00:00Z |
| Utilisation WETH | 88,605 % → 90,582 % → 100,0023 % | 17:35 → gel → 20/04 00:00Z |
| Pic d'utilisation WETH | **1,0000793** (100,008 %) | 2026-04-19T08:00:00Z, bloc 24 912 596 |
| Utilisation rsETH | ≈ 0,008 % (dette ≈ 42,08 rsETH) | toute la fenêtre |
| Vérification oracle | 5 / 5 : `AaveOracle.getAssetPrice(rsETH)` **=** `latestAnswer()` du feed plafonné | blocs clés |

Lecture : **le marché rsETH n'a jamais été bloqué par une utilisation à 100 %** (U ≈ 0,008 %) —
la correction factuelle de W2-B est reproduite ; le verrou est le **gel administratif** d'une
réserve dont l'LTV était déjà 0, après une **vague de dépôts de collatéral** portant le marché à
0,001 % de son plafond. Et pendant 29 heures, la valorisation retenue du collatéral est restée
dans une bande 2 419-2 632 $ alors que ce collatéral n'avait plus de prix de sortie mesurable.

### 2.2 Chronologie portée dans le fichier (`events`)

| Instant (UTC) | Fait | Source |
|---|---|---|
| 2026-04-18T17:35Z | exploit exécuté (89 567 rsETH en collatéral, ~190 M$ de WETH empruntés) | Messari |
| 2026-04-18T18:00Z | plafond d'émission rsETH saturé à 99,9989 % (mesuré) | `research/W2B` signal 2.5 |
| 2026-04-18T18:52Z | gel des marchés annoncé par le Guardian (77 min après le drain) | Galaxy |
| 2026-04-18T19:03:59Z | `isFrozen` 0 → 1 : plus personne ne sort (bloc 24 908 723) | dichotomie on-chain |
| 2026-04-20T00:00Z | WETH gelé, LTV WETH → 0 ; bad debt publié (123,7 / 230,1 M$) | rapport d'incident Aave |

### 2.3 Coût et provenance

`rpc_provenance` : endpoints utilisés, nombre de clients, nombre d'appels, erreurs,
`reads_per_point` documenté (15 `eth_call` par point + 2-3 `eth_getBlockByNumber` pour le
plancher de bloc). Le mode `cache` (voir §5) reconstruit la même forme depuis les JSON de
W2-A/W2-B, avec la liste des fichiers lus (`cache_files`) et **la liste des étiquettes
re-placées** (`label_repairs`).

* **Épisode stETH** (le plus lourd) : 2 530 appels, 6 clients, **0 erreur**, 253 points,
  répartition drpc 770 / blastapi 1 760.
* **Épisode rsETH** : **1 538 appels**, 6 clients, 0 erreur, 100 points (répartition
  blastapi 1 050 / drpc 488), grille de blocs + recherche de gel + 5 vérifications d'oracle
  incluses. **Relancé une seconde fois** (même commande, `--no-resume`) : les chiffres clés
  sont identiques au bit près — saturation 0,9999886466022144 à 18:00Z, gel 24 908 723
  (2026-04-18T19:03:59Z, 14 itérations), oracle 2 419,21294349 $ le 20/04, pic d'utilisation
  WETH 1,0000792945348582 le 19/04 à 08:00Z.

---

## 3. Épisode stETH / Celsius — `evidence/episode_steth_2022-06.json`

**Mode de production** : `rpc` (réseau), `meta.complete = true`, **253 / 253 points**, 0 erreur,
**2 530 appels** répartis sur 6 clients (2 530 appels, 0 erreur, blastapi 1 760 / drpc 770).
Grille : journalier 2022-05-01T00:00Z → 2022-07-31T00:00Z + horaire
2022-06-10T00:00Z → 2022-06-17T00:00Z. Chaque point porte les 4 tailles (1 / 100 / 1 000 /
10 000 stETH), la réponse du feed Chainlink `STETH / ETH` et les soldes du pool.

### 3.1 Les chiffres reconstruits

| Mesure (décote réalisable de vente) | Valeur | Instant / bloc |
|---|---|---|
| Plancher de calme, 1 stETH | **8,18 bps** (0,082 %) | 2022-05-01T00:00Z, bloc 14 688 629 |
| Entrée en régime > 2 % | **213,7 bps** (2,14 %), contre 66,9 bps la veille | **2022-05-13T00:00Z**, bloc 14 764 083 |
| Pic de l'épisode, 1 stETH | **692,5 bps (6,925 %)** | **2022-06-14T10:00Z**, bloc 14 961 150 |
| Pic, 1 000 stETH | 698,4 bps (6,984 %) | idem |
| Pic, 10 000 stETH | 755,4 bps (7,554 %) | idem |
| 15 juin 00:00Z (1 / 1 000 / 10 000) | 478,7 / 482,3 / 517,6 bps | bloc 14 964 552 |
| 15 juin 22:00Z (1 / 1 000 / 10 000) | 642,2 / 647,6 / 699,6 bps | bloc 14 969 823 |
| 28 juin / 30 juin (1 stETH) | 335,2 / 384,4 bps | blocs 15 036 953 / 15 047 598 |
| 31 juillet (1 stETH) | 263,5 bps | bloc 15 246 903 |
| Points > 200 bps | **227 / 253** | 2022-05-13 → 2022-07-31 inclus |

Deux lectures immédiates :

* **L'antériorité est plus longue que la mesure de W2-B** : leur échantillonnage par blocs
  (pas de 20 000 blocs) plaçait la première décote > 2 % le 21 mai ; la grille journalière
  montre que le régime > 2 % était déjà là le **13 mai 2022**, soit **30 jours avant le gel
  des retraits Celsius (12-13 juin)**.
* **L'oracle « retenu » et le prix réalisable divergent** : au bloc 14 961 150 (14/06 10:00Z),
  le feed `STETH / ETH` affiche **0,941992** quand une vente de 1 stETH ne rend que 0,93075
  (692,5 bps) et une vente de 10 000 stETH 0,92446 — l'écart oracle/réalisable atteint
  **119-186 bps** selon la taille. Le pool, lui, est complètement déséquilibré :
  **107 069 ETH pour 501 506 stETH** le 14 juin (ratio 4,68), contre 814 989 / 832 550
  (ratio 1,02) le 1er mai — c'est la mesure directe de « la liquidité secondaire a fondu ».

### 3.2 Points de référence W2-B, reproduits depuis l'archive

Ces cinq blocs (mesurés par W2-B) sont vérifiés par `tests/test_data_layer.py` à partir du prix
archivé (`get_dy` reconstruit) : 14 720 000 → 6,57 bps ; 14 820 000 → 256,8 bps ;
14 940 000 → 468,7 bps ; **14 970 000 → 618,55 bps (6,185 %)** ; 15 040 000 → 380,2 bps.

### 3.3 Méthode

`get_dy(1, 0, X)` (stETH → ETH) sur le pool Curve
`0xDC24316b9AE028F1497c275EB9192a3Ea0f67022`, pour X ∈ {1, 100, 1 000, 10 000} stETH, à chaque
bloc de la grille. Le sens est vérifié dans les tests : `coins(0)` = `0xEeee…EEeE` (ETH),
`coins(1)` = stETH.

---

## 4. Tests (`tests/test_data_layer.py`)

44 tests, **aucun accès réseau** (un transport factice est injecté dans le client, un client
bouchon dans les lecteurs Aave/Curve/Chainlink). Fixtures : `research/raw_w2b/*.json`,
`research/raw_w2a/*.json` et les fichiers `evidence/` eux-mêmes.

| Groupe | Ce qu'il verrouille |
|---|---|
| `CodecTests` (5) | mots ABI 256 bits, complément à deux, adresses, refus des entrées invalides, décodage de `description()` |
| `ArchiveRpcTests` (9) | bascule d'endpoint, erreur contractuelle non rejouée, erreur de nœud → endpoint suivant, plancher du bloc (chaîne synthétique), cache des horodatages, pagination `getLogs` (0-9999 / 10000-19999 / 20000-24999), `RpcRangeError`, validation des arguments |
| `AaveTests` (6) | décodage des mots de configuration archivés (gelé / non gelé / en pause), égalité avec le décodage de W2-B, état de réserve vs saturation archivée (cap_ratio, U, prix oracle), dichotomie du gel |
| `CurveTests` (5) | `get_dy` → prix et décote des 18 mesures archivées, valeurs de juin (618,5 bps) et de calme, monotonicité en taille, ordre des coins, échelle (une requête par taille) |
| `ChainlinkTests` (3) | `latestRoundData` (18 décimales, fraîcheur), repli `latestAnswer` du feed plafonné, adresses mesurées |
| `TimelineTests` (6) | `utc_iso`/`parse_utc`, grille inclusive, `resolve_blocks` (plancher vérifié, estimation d'abord, coût en lectures), changement de temps de bloc au Merge, `resolve_blocks_parallel` |
| `ReconstructionScriptTests` (6) | reconstruction cache rsETH (saturation, gel daté, réparations d'étiquettes) et stETH (repères 2022), résumé lisible, estimation bloc→temps, **exécution CLI `--from-cache`** de bout en bout (fichier écrit, mode, `limitations`) |
| `EvidenceFileTests` (4) | forme et auto-cohérence des deux JSON de preuve : clés horodatées triées, `cap_ratio = supply/cap`, `isFrozen` monotone, décote = `1 − prix`, échelle monotone en taille |

**Résultat** : `python -m pytest tests/ -q` → **221 passed, 2 skipped** ;
`python -m unittest discover -s tests` → **223 tests, OK (2 skipped)** — les 2 ignorés sont les
tests RPC « live » opt-in déjà présents (`ORVYREN_LIVE_RPC=1`), et les nouveaux tests ne
touchent jamais au réseau (transport factice injecté).

---

## 5. Relance et modes

```bash
python scripts/reconstruct_rseth_episode.py                  # réseau (horaire + blocs clés)
python scripts/reconstruct_rseth_episode.py --from-cache     # hors-ligne (JSON W2-A/W2-B)
python scripts/reconstruct_steth_episode.py --workers 6      # réseau
python scripts/reconstruct_steth_episode.py --from-cache     # hors-ligne
python scripts/reconstruct_steth_episode.py --no-resume      # repart de zéro
```

* **Écriture atomique et incrémentale** : le JSON est réécrit (`os.replace`) après chaque point ;
  un run interrompu se reprend tout seul (`--resume` par défaut) sur les points déjà mesurés.
* **Repli honnête** : si la toute première lecture échoue, le script bascule en `--from-cache`,
  l'annonce sur `stderr` et l'écrit dans `meta.mode` (jamais de mélange silencieux).
* **`--from-cache`** relit les JSON archivés (`research/raw_w2a`, `research/raw_w2b`), ce qui rend
  les deux livrables reproductibles **sans réseau** ; les fichiers lus sont listés dans
  `meta.cache_files` et, pour rsETH, les **étiquettes UTC re-placées** dans `label_repairs`.
* Deux scripts lancés en parallèle saturent les endpoints publics gratuits (mesuré : un run est
  tombé en repli cache) : **les lancer l'un après l'autre**.

---

## 6. Limites assumées (ce que ces fichiers ne prouvent pas)

1. **Étiquettes horaires des JSON archivés** : dans `raw_w2b/aave_rseth_reserveconfig.json`, la
   ligne étiquetée `2026-04-18T12:00:00` porte le bloc 24 911 049, qui vaut en réalité
   **2026-04-19T02:49:47Z** (vérifié on-chain), et la grille 12 h de `aave_rseth_apr2026.json`
   dérive de ~14,8 h. Le mode `--from-cache` **re-place** ces lignes à l'heure estimée
   (ancre : bloc 24 908 723 = 19:03:59Z) et journalise chaque déplacement dans `label_repairs` ;
   le mode réseau, lui, ne dépend d'aucune étiquette.
2. **rsETH** : la couche données ne lit **que la valorisation retenue** (oracle plafonné) pour ce
   collatéral ; il n'existe pas de prix de sortie mesurable d'un rsETH volé/non adossé, et le
   fichier le dit (`limitations`). Le bad debt (123,7 / 230,1 M$) exige le registre des comptes,
   hors périmètre.
3. **stETH** : `get_dy` est un **devis au bloc** (état du pool, frais et slippage inclus), pas
   une exécution ; les sorties CEX de juin 2022 existaient aussi et ne sont pas modélisées.
   Rappel : les retraits Lido étaient fermés avant Shapella (avril 2023) — le pool Curve était
   alors le seul exutoire on-chain, ce qui est précisément ce qui rend cette décote réalisable.
4. **Provenance** : le premier fichier rsETH produit comptait les appels du seul client
   coordinateur (la phase métrique tourne sur un client par fil, le client n'étant pas *thread-safe*) ;
   `recon_common.merge_provenance` agrège désormais tous les clients du run.
5. **Fraîcheur** : le feed plafonné rsETH n'expose aucun `updatedAt` (voir §1.4) — l'âge de
   l'oracle rsETH est donc **non mesurable** ; le feed stETH/ETH, lui, expose le sien.

---

## 7. Fichiers produits et mode d'emploi

| Fichier | Nature |
|---|---|
| `src/orvyren/data/__init__.py` | exports + `utc_iso`, `parse_utc`, `time_grid` |
| `src/orvyren/data/rpc.py` | client d'archive, codec ABI, pagination `getLogs` |
| `src/orvyren/data/aave.py` | réserve Aave V3, gel, `cap_ratio`, oracle |
| `src/orvyren/data/curve.py` | `get_dy` → prix et décote réalisables |
| `src/orvyren/data/chainlink.py` | feeds Chainlink au bloc (+ repli feed plafonné) |
| `scripts/recon_common.py` | chemins, JSON atomique, `resolve_blocks`, pool de fils, provenance |
| `scripts/reconstruct_rseth_episode.py` | épisode rsETH (réseau / cache) |
| `scripts/reconstruct_steth_episode.py` | épisode stETH (réseau / cache) |
| `tests/test_data_layer.py` | 44 tests hors-ligne |
| `evidence/episode_rseth_2026-04.json` | 100 points + gel daté + vérifications d'oracle |
| `evidence/episode_steth_2022-06.json` | décote réalisable 1/100/1000/10000 stETH |

Aucune dépendance ajoutée, aucun fichier existant modifié en dehors de l'ajout de
`src/orvyren/data/`, `scripts/`, `tests/test_data_layer.py` et des deux JSON de `evidence/`.
