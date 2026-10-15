#!/bin/bash
# W3-C — Sonde 1 : endpoints de prix pour xUSD (Stream Finance, nov. 2025) et USD0++ (Usual, janv. 2025)
# Exécuté le 2026-10-15 (hôte Windows, git-bash). Chaque appel est sauvé brut + code HTTP.
cd "$(dirname "$0")"
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
XUSD=0xE2Fc85BfB48C4cF147921fBE110cf92Ef9f26F94      # Staked Stream USD (StreamVault), Ethereum
USD0PP=0x35D8949372D46B7a3D5A56006AE77B215fc69bC0    # USD0++ (Usual), Ethereum
TS_XUSD=$(date -u -d "2025-11-05 12:00:00" +%s)      # milieu de l'incident xUSD
TS_USD0=$(date -u -d "2025-01-11 12:00:00" +%s)      # milieu de l'incident USD0++
echo "TS_XUSD=$TS_XUSD  TS_USD0=$TS_USD0"
echo

probe() { # $1 = label, $2 = url, $3 = fichier de sortie
  code=$(curl -s -A "$UA" -H 'Accept: application/json' -w '%{http_code}' --max-time 45 "$2" -o "$3")
  size=$(wc -c < "$3")
  echo "[$code] $1 -> $3 (${size} octets)  $2"
  head -c 300 "$3"; echo; echo "---"
}

echo "== GeckoTerminal =="
probe "GT network eth"        "https://api.geckoterminal.com/api/v2/networks/eth" "gt_net_eth.json"
probe "GT token xUSD"         "https://api.geckoterminal.com/api/v2/networks/eth/tokens/$XUSD" "gt_xusd_token.json"
probe "GT pools xUSD"         "https://api.geckoterminal.com/api/v2/networks/eth/tokens/$XUSD/pools" "gt_xusd_pools.json"
probe "GT token USD0++"       "https://api.geckoterminal.com/api/v2/networks/eth/tokens/$USD0PP" "gt_usd0pp_token.json"
probe "GT pools USD0++"       "https://api.geckoterminal.com/api/v2/networks/eth/tokens/$USD0PP/pools" "gt_usd0pp_pools.json"

echo "== DEX Screener =="
probe "DS token xUSD"         "https://api.dexscreener.com/latest/dex/tokens/$XUSD" "ds_xusd.json"
probe "DS token USD0++"       "https://api.dexscreener.com/latest/dex/tokens/$USD0PP" "ds_usd0pp.json"

echo "== DefiLlama coins =="
probe "LL historical xUSD"    "https://coins.llama.fi/prices/historical/$TS_XUSD/ethereum:$XUSD" "ll_xusd_hist.json"
probe "LL historical USD0++"  "https://coins.llama.fi/prices/historical/$TS_USD0/ethereum:$USD0PP" "ll_usd0pp_hist.json"
probe "LL chart USD0++ janv"  "https://coins.llama.fi/chart/ethereum:$USD0PP?start=$(date -u -d '2025-01-08 00:00:00' +%s)&end=$(date -u -d '2025-01-16 00:00:00' +%s)&period=1h" "ll_usd0pp_chart_jan2025.json"
probe "LL chart xUSD oct-nov" "https://coins.llama.fi/chart/ethereum:$XUSD?start=$(date -u -d '2025-10-28 00:00:00' +%s)&end=$(date -u -d '2025-11-18 00:00:00' +%s)&period=1h" "ll_xusd_chart_nov2025.json"
echo "FIN SONDE 1"
