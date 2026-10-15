echo "### A. Aave address book (raw GitHub) — recherche rsETH"
curl -s -m 25 "https://raw.githubusercontent.com/bgd-labs/aave-address-book/main/src/AaveV3Ethereum.sol" -o AaveV3Ethereum.sol -w "HTTP %{http_code} size=%{size_download}\n"
grep -n -i -E "rsETH|USDC =|WETH =" AaveV3Ethereum.sol | head -20
echo "### B. DefiLlama yields — pools aave-v3 avec rsETH"
curl -s -m 40 "https://yields.llama.fi/pools" -o yields_pools.json -w "HTTP %{http_code} size=%{size_download}\n"
python - <<'PY'
import json
d=json.load(open('yields_pools.json'))
rows=[p for p in d['data'] if p.get('project')=='aave-v3' and 'rsETH' in (p.get('symbol') or '')]
for p in rows[:20]:
    print(p['chain'], p['symbol'], p['pool'], 'tvl=',p.get('tvlUsd'))
PY
