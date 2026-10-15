import json, urllib.request, datetime, time
UA={"User-Agent":"Mozilla/5.0 (orvyren-research)"}
def get(url):
    try:
        return json.loads(urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=40).read().decode())
    except Exception as e: return {"__error__":str(e)}
t0=1678449600; t1=1678622400
res={}
def show(name,pts):
    pts=[(int(p[0]),float(p[1])) for p in pts if p is not None]
    if not pts: print(name,"aucun point"); return None
    lo=min(pts,key=lambda p:p[1])
    print(f"{name}: min={lo[1]} @ {datetime.datetime.utcfromtimestamp(lo[0]).isoformat()}Z ; n={len(pts)}")
    return {"venue":name,"min":lo[1],"ts_min":lo[0],"ts_min_utc":datetime.datetime.utcfromtimestamp(lo[0]).isoformat()+"Z","n":len(pts)}
S=[]
# Bitstamp minute
r=get(f"https://www.bitstamp.net/api/v2/ohlc/usdcusd/?step=60&limit=1000&start={1678492800}&end={1678560000}")
json.dump(r,open("bitstamp_minutes.json","w"))
if "data" in r: S.append(show("Bitstamp USDC/USD (1m)", [(o["timestamp"],o["low"]) for o in r["data"]["ohlc"]]))
# Kraken trades paging
cursor=1678480000; allt=[]
for i in range(12):
    k=get(f"https://api.kraken.com/0/public/Trades?pair=USDCUSD&since={cursor}")
    if "result" not in k or "USDCUSD" not in k.get("result",{}): break
    tr=k["result"]["USDCUSD"]
    if not tr: break
    allt+= tr
    last=float(k["result"]["last"])
    if len(tr)<1000: break
    cursor=last; time.sleep(0.5)
json.dump({"n":len(allt),"last":last},open("kraken_trades_meta.json","w"))
S.append(show("Kraken USDCUSD (trades)", [(t[2],t[0]) for t in allt]))
# OKX 1m? use 1H already; add 1m
r=get(f"https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1H&after={t1*1000}&limit=100")
if r.get("data"): S.append(show("OKX USDC-USDT (1H)", [(int(o[0])//1000,o[3]) for o in r["data"]]))
# DefiLlama
d=get(f"https://coins.llama.fi/chart/ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48?start={t0}&span=48&period=1h")
json.dump(d,open("defillama_chart_usdc.json","w"))
try:
    pr=d["coins"]["ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"]["prices"]
    S.append(show("DefiLlama (agregat 1h)", [(p["timestamp"],p["price"]) for p in pr]))
except Exception as e: print("llama err",e)
json.dump(S,open("venue_minima_usdc_2023.json","w"),indent=1)
print(json.dumps(S,indent=1))
