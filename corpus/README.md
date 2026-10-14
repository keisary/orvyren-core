# Corpus USDC — cas pilote ORVYREN (épisode SVB, mars 2023)

Collecte reproductible : `python collect_corpus.py` (réseau) ou `--offline` (rejeu de l'archive).
Dernière collecte : 2026-10-14T15:02:07+00:00
Observations unifiées : **520** (voir `usdc_observations.csv`).

## Fenêtres
- principale (depeg) : 2023-03-09 → 2023-03-15, pas horaire ;
- témoin (hors crise) : 2023-02-15 → 2023-02-18, pas horaire.

## Sources et limites

| Source | Endpoint | Enregistrements | Limite à afficher |
|---|---|---|---|
| DeFiLlama | `coins.llama.fi/prices/historical/{ts}/{coin}` | 145 | Agrégateur : prix médian multi-venues, retard et couverture à vérifier ; quota public non garanti (voir doc API). |
| DeFiLlama | `coins.llama.fi/prices/historical/{ts}/{coin}` | 73 | Agrégateur : prix médian multi-venues, retard et couverture à vérifier ; quota public non garanti (voir doc API). |
| Bitstamp | `www.bitstamp.net/api/v2/ohlc/usdcusd/` | 145 | Une seule place de marché : profondeur et spreads locaux ; la dislocation observée peut être propre à cette venue. |
| Binance | `api.binance.com/api/v3/klines` | 83 | Marché USDC/USDT : dislocation relative à un autre stablecoin, pas absolue. Paire ouverte par Binance le 11/03/2023 14:00 UTC (fin de l'auto-conversion USDC→BUSD) : aucune observation Binance avant le pic de crise. |
| DeFiLlama | `https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=2` | 37 | Série quotidienne, granularité grossière ; couvre l'on-chain observable uniquement. |
| DeFiLlama | `https://stablecoins.llama.fi/stablecoincharts/Ethereum?stablecoin=2` | 37 | Série quotidienne, granularité grossière ; couvre l'on-chain observable uniquement. |
| Circle | `https://www.circle.com/pressroom/3-3-billion-of-usdc-reserve-risk-removed-dollar-de-peg-closes` | 1 | Une déclaration d'émetteur ne tranche pas seule les hypothèses de risque ; à corroborer. |

## Règles d'usage
1. Les prix de testnet ne servent **jamais** de contexte de décision (V0.2 §3.5).
2. Toute analyse historique n'utilise que les informations disponibles à l'instant simulé (point-in-time).
3. Un prix d'agrégateur et un prix d'exchange ne sont pas deux preuves indépendantes par construction ;
   la comparaison Bitstamp / Binance / DeFiLlama est conservée pour mesurer les écarts **entre venues**.
4. La déclaration de l'émetteur est enregistrée comme référence documentaire : elle doit être lue et citée,
   jamais reformulée automatiquement.
