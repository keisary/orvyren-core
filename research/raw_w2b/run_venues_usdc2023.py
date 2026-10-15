import json, urllib.request, datetime

UA={"User-Agent":"Mozilla/5.0 (orvyren-research)"}
def get(url):
    try:
        req=urllib.request.Request(url, headers=UA)
        return json.loads(urllib.request.urlopen(req, timeout=40).read().decode())
    except Exception as e:
        return {"__error__": str(e)}

out={}
# Fenetre : 2023-03-10 12:00 UTC -> 2023-03-12 12:00 UTC
t0=1678449600; t1=1678622400
# BINANCE USDCUSDT 1h
r=get(f"https://api.binance.com/api/v3/klines?symbol=USDCUSDT&interval=1h&startTime={t0*1000}&endTime={t1*1000}&limit=1000")
out["binance_USDCUSDT_klines"]=r
# BITSTAMP USDC/USD 1h
r=get(f"https://www.bitstamp.net/api/v2/ohlc/usdcusd/?step=3600&limit=1000&start={t0}&end={t1}")
out["bitstamp_usdcusd"]=r
# KRAKEN USDCUSD OHLC 1h
r=get(f"https://api.kraken.com/0/public/OHLC?pair=USDCUSD&interval=60&since={t0}")
out["kraken_usdcusd_ohlc"]=r
# OKX USDC-USDT 1H
r=get(f"https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1H&after={t1*1000}&limit=100")
out["okx_usdcusdt"]=r
# DefiLlama chart (agregat) 1h
r=get(f"https://coins.llama.fi/chart/ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48?start={t0}&span=48&period=1h")
out["defillama_chart_usdc"]=r
json.dump(out, open("venues_usdc_mar2023.json","w"))
# Resume : min par venue sur la fenetre
def show(name, pts):
    pts=[p for p in pts if p and isinstance(p[0],(int,float))]
    if not pts: print(name,"aucun point"); return
    lo=min(pts,key=lambda p:p[1])
    print(f"{name}: min={lo[1]} @ {datetime.datetime.utcfromtimestamp(lo[0]).isoformat()}Z ; n={len(pts)}")
B=[(int(k[0])//1000, float(k[3])) for k in out["binance_USDCUSDT_klines"] if isinstance(k,list)]
show("Binance USDCUSDT (low)", B)
try:
    bs=[(int(o["timestamp"]), float(o["low"])) for o in out["bitstamp_usdcusd"]["data"]["ohlc"]]
    show("Bitstamp USDC/USD (low)", bs)
except Exception as e: print("bitstamp err", e, str(out["bitstamp_usdcusd"])[:200])
try:
    kk=out["kraken_usdcusd_ohlc"]["result"]; key=[x for x in kk if x!="last"][0]
    K=[(int(o[0]), float(o[3])) for o in kk[key]]
    show("Kraken USDCUSD (low)", K)
except Exception as e: print("kraken err", e, str(out["kraken_usdcusd_ohlc"])[:200])
try:
    if out["okx_usdcusdt"].get("data"):
        O=[(int(o[0])//1000, float(o[3])) for o in out["okx_usdcusdt"]["data"]]
        show("OKX USDC-USDT (low)", O)
    else: print("okx:", str(out["okx_usdcusdt"])[:200])
except Exception as e: print("okx err", e)
try:
    D=[(p[0]//1000, p[1]) for p in out["defillama_chart_usdc"]["coins"]["ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"]["prices"]]
    show("DefiLlama agregat USDC (min)", D)
except Exception as e: print("llama err", e, str(out["defillama_chart_usdc"])[:300])
