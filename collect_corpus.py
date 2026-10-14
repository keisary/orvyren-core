#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — collecteur de corpus (cas pilote USDC / SVB, mars 2023).

Collecte, horodate et archive les observations nécessaires au cas :
  1. DeFiLlama  — prix USDC (agrégateur) heure par heure, requête par timestamp
                  (endpoint `prices/historical` : c'est le seul qui répond pour
                   l'historique ; `chart` renvoie 0 point — constat du 14/10/2026).
  2. Bitstamp   — OHLC horaire USDC/USD (source d'exchange indépendante).
  3. Binance    — klines horaires USDC/USDT (deuxième source d'exchange).
  4. DeFiLlama  — offre en circulation d'USDC par chaîne (quotidien, agrégat + Ethereum).
  5. Référence documentaire — déclaration Circle du 12-13/03/2023 (métadonnée, non scrapée).

Sorties (dans corpus/) :
  raw/<source>/*.json   réponses brutes horodatées
  manifest.json         manifeste de source : url, heure de collecte, nb d'enregistrements, limites
  usdc_observations.csv observations unifiées (timestamp_utc, venue, type, valeur)
  README.md             note de provenance et limites

Contrat de fenêtre : chaque série est re-vérifiée contre ses bornes déclarées
avant écriture (`validate_archived_windows`) ; une ligne hors fenêtre fait
échouer la collecte (exit 2) au lieu d'entrer silencieusement dans l'archive.
Ce garde-fou existe parce qu'un cache d'avant le filtre de fenêtre a déjà été
réutilisé et a expédié 855 lignes Bitstamp hors fenêtre (constat du 14/10/2026).

Usage :
  python collect_corpus.py                # collecte complète (≈ 4 min, réseau requis)
  python collect_corpus.py --offline      # rejoue uniquement le corpus archivé
Dépendances : stdlib uniquement.
"""

import argparse
import csv
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(BASE, "corpus")
RAW = os.path.join(CORPUS, "raw")
UA = {"user-agent": "curl/8.5.0", "accept": "application/json"}

# Fenêtre principale : depeg USDC (SVB) — du 9 au 15 mars 2023, pas horaire.
MAIN_START = dt.datetime(2023, 3, 9, 0, 0, tzinfo=dt.timezone.utc)
MAIN_END = dt.datetime(2023, 3, 15, 0, 0, tzinfo=dt.timezone.utc)
# Fenêtre témoin (hors crise) : 15-18 février 2023.
CTRL_START = dt.datetime(2023, 2, 15, 0, 0, tzinfo=dt.timezone.utc)
CTRL_END = dt.datetime(2023, 2, 18, 0, 0, tzinfo=dt.timezone.utc)

USDC_TOKEN = "ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
CIRCLE_STATEMENT = {
    "source": "Circle",
    "title": "USDC reserves and Silicon Valley Bank — statement",
    "url": "https://www.circle.com/pressroom/3-3-billion-of-usdc-reserve-risk-removed-dollar-de-peg-closes",
    "publication_date": "2023-03-12",
    "usage": "Source primaire de l'émetteur : information annoncée à une date donnée (fait documentaire).",
    "limit": "Une déclaration d'émetteur ne tranche pas seule les hypothèses de risque ; à corroborer.",
    "note": "Métadonnée enregistrée manuellement : le texte de la déclaration doit être lu et cité, pas scrapé automatiquement.",
}


def fetch_json(url, retries=3, pause=1.5):
    """GET JSON avec reprises ; renvoie (donnée, heure_de_collecte_iso) ou lève."""
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as fh:
                raw = fh.read()
            return json.loads(raw.decode("utf-8", "replace")), dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(pause * (attempt + 1))
    raise RuntimeError(f"échec après {retries} tentatives : {url} ({last})")


FORCE = False  # mis à True par --force : ignore le cache et recollecte tout


def cached_or_fetch(sub, name, url, builder):
    """Idempotence de collecte : si le fichier brut existe déjà et que --force n'est pas
    demandé, on le relit au lieu de refaire les appels réseau (coûteux : ~1 s/appel).
    `builder()` doit renvoyer la liste d'enregistrements construite depuis la réponse."""
    path = os.path.join(RAW, sub, name)
    if os.path.exists(path) and not FORCE:
        rows = json.load(open(path, encoding="utf-8"))
        if rows:  # un cache vide (collecte échouée) ne doit jamais être réutilisé
            print(f"  {sub}/{name}: {len(rows)} enregistrements (réutilisés du cache)")
            return rows, True
        print(f"  {sub}/{name}: cache vide → nouvelle tentative réseau")
    rows = builder()
    save_raw(sub, name, rows)
    print(f"  {sub}/{name}: {len(rows)} enregistrements (collectés)")
    return rows, False


def ensure_dirs():
    for sub in ("defillama", "bitstamp", "binance", "circle", "supply"):
        os.makedirs(os.path.join(RAW, sub), exist_ok=True)


def save_raw(sub, name, payload):
    path = os.path.join(RAW, sub, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    return os.path.relpath(path, BASE)


def hours(start, end):
    t, out = start, []
    while t <= end:
        out.append(int(t.timestamp()))
        t += dt.timedelta(hours=1)
    return out


def parse_iso(value):
    """Parse the ISO-8601 strings this module writes (``Z`` suffix accepted)."""
    text = str(value).strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    return dt.datetime.fromisoformat(text)


def validate_archived_windows(prices, bitstamp, binance, supply):
    """Refuse a collection whose rows fall outside their declared windows.

    Every series is re-checked against its declared bounds *after* collection,
    before anything is written: a cache that predates the window filter (the
    855-row Bitstamp incident of 2026-10-14) must fail loudly here instead of
    slipping into the archive. Returns the list of violations (empty = OK).
    """
    problems = []

    def check(label, rows, start, end, field="timestamp_utc"):
        for row in rows:
            when = parse_iso(row[field])
            if not (start <= when <= end):
                problems.append(
                    "%s: %s outside [%s, %s]"
                    % (label, row[field], start.isoformat(), end.isoformat()))
                return

    for label, window in (("main", (MAIN_START, MAIN_END)), ("control", (CTRL_START, CTRL_END))):
        check("defillama %s" % label, prices.get(label, []), *window)
    check("bitstamp main", bitstamp, MAIN_START, MAIN_END)
    check("binance main", binance, MAIN_START, MAIN_END)
    supply_start = MAIN_START - dt.timedelta(days=15)
    supply_end = MAIN_END + dt.timedelta(days=15)
    for label, rows in supply.items():
        check("supply %s" % label, rows, supply_start, supply_end, field="date_utc")
    return problems


def collect_defillama_prices(manifest, sleep=1.1):
    """Prix USDC heure par heure via l'endpoint prices/historical (une requête par point)."""
    series = {}
    for label, (start, end) in (("main", (MAIN_START, MAIN_END)), ("control", (CTRL_START, CTRL_END))):
        def build(start=start, end=end):
            out = []
            for ts in hours(start, end):
                url = f"https://coins.llama.fi/prices/historical/{ts}/{USDC_TOKEN}"
                data, retrieved = fetch_json(url)
                entry = data.get("coins", {}).get(USDC_TOKEN, {})
                out.append({
                    "timestamp_utc": dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat(timespec="seconds"),
                    "price": entry.get("price"),
                    "confidence": entry.get("confidence"),
                    "retrieved_at": retrieved,
                })
                time.sleep(sleep)
            return out
        rows, reused = cached_or_fetch("defillama", f"usdc_prices_{label}.json", None, build)
        series[label] = rows
        manifest.append({
            "source": "DeFiLlama", "endpoint": "coins.llama.fi/prices/historical/{ts}/{coin}",
            "window": label, "records": len(rows),
            "file": f"corpus/raw/defillama/usdc_prices_{label}.json", "from_cache": reused,
            "limits": "Agrégateur : prix médian multi-venues, retard et couverture à vérifier ; quota public non garanti (voir doc API).",
        })
    return series


def collect_bitstamp(manifest):
    """OHLC horaire USDC/USD sur Bitstamp, depuis le 9 mars 2023 (API publique, sans clé)."""
    def build():
        out, start = [], int(MAIN_START.timestamp())
        while True:
            url = f"https://www.bitstamp.net/api/v2/ohlc/usdcusd/?step=3600&limit=1000&start={start}"
            data, retrieved = fetch_json(url)
            batch = data.get("data", {}).get("ohlc", [])
            if not batch:
                break
            for candle in batch:
                ts = int(candle["timestamp"])
                if ts > int(MAIN_END.timestamp()):
                    continue
                out.append({
                    "timestamp_utc": dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat(timespec="seconds"),
                    "close": float(candle["close"]), "low": float(candle["low"]),
                    "high": float(candle["high"]), "volume": float(candle["volume"]),
                    "retrieved_at": retrieved,
                })
            last = int(batch[-1]["timestamp"])
            if last <= start or last >= int(MAIN_END.timestamp()):
                break
            start = last + 3600
            time.sleep(0.7)
        return out
    rows, reused = cached_or_fetch("bitstamp", "usdcusd_ohlc.json", None, build)
    manifest.append({
        "source": "Bitstamp", "endpoint": "www.bitstamp.net/api/v2/ohlc/usdcusd/",
        "window": "main", "records": len(rows), "file": "corpus/raw/bitstamp/usdcusd_ohlc.json",
        "from_cache": reused,
        "limits": "Une seule place de marché : profondeur et spreads locaux ; la dislocation observée peut être propre à cette venue.",
    })
    return rows


def collect_binance(manifest):
    """Klines horaires USDC/USDT (source d'exchange indépendante de Bitstamp)."""
    def build():
        out = []
        start = int(MAIN_START.timestamp() * 1000)
        end = int(MAIN_END.timestamp() * 1000)
        while start < end:
            url = ("https://api.binance.com/api/v3/klines?symbol=USDCUSDT&interval=1h"
                   f"&startTime={start}&endTime={end}&limit=1000")
            data, retrieved = fetch_json(url)
            if not isinstance(data, list) or not data:
                break
            for k in data:
                out.append({
                    "timestamp_utc": dt.datetime.fromtimestamp(k[0] / 1000, dt.timezone.utc).isoformat(timespec="seconds"),
                    "close": float(k[4]), "low": float(k[3]), "high": float(k[2]), "volume": float(k[5]),
                    "retrieved_at": retrieved,
                })
            start = int(data[-1][0]) + 3600 * 1000
            if len(data) < 1000:
                break
            time.sleep(0.5)
        return out
    rows, reused = cached_or_fetch("binance", "usdcusdt_klines.json", None, build)
    manifest.append({
        "source": "Binance", "endpoint": "api.binance.com/api/v3/klines", "window": "main",
        "records": len(rows), "file": "corpus/raw/binance/usdcusdt_klines.json", "from_cache": reused,
        "limits": "Marché USDC/USDT : mesure une paire contre un autre stablecoin, donc une dislocation relative, pas absolue.",
    })
    return rows


def collect_supply(manifest):
    """Offre en circulation USDC (quotidien) — agrégat et Ethereum."""
    out = {}
    # Fenêtre élargie : la crise ± 15 jours, pour pouvoir comparer à une période calme proche.
    lo = (MAIN_START - dt.timedelta(days=15)).timestamp()
    hi = (MAIN_END + dt.timedelta(days=15)).timestamp()

    def parse_ts(value):
        """L'endpoint renvoie la date sous trois formes possibles :
        epoch numérique (int/float), epoch encodé en chaîne ("1678320000"), ou ISO ("2023-03-09").
        Constat du 14/10/2026 : stablecoincharts renvoie une CHAÎNE contenant l'epoch."""
        if isinstance(value, (int, float)):
            return dt.datetime.fromtimestamp(float(value), dt.timezone.utc)
        text = str(value).strip()
        if text.isdigit():
            return dt.datetime.fromtimestamp(float(text), dt.timezone.utc)
        text = text.replace("Z", "+00:00")
        if "T" not in text and len(text) == 10:
            text += "T00:00:00+00:00"
        return dt.datetime.fromisoformat(text)

    for label, url in (
        ("aggregate", "https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=2"),
        ("ethereum", "https://stablecoins.llama.fi/stablecoincharts/Ethereum?stablecoin=2"),
    ):
        def build(url=url):
            data, retrieved = fetch_json(url)
            rows = []
            for point in (data if isinstance(data, list) else []):
                raw_date = point.get("date")
                if raw_date is None:
                    continue
                try:
                    when = parse_ts(raw_date)
                except (ValueError, TypeError):
                    continue
                if not (lo <= when.timestamp() <= hi):
                    continue
                usd = (point.get("totalCirculatingUSD") or {}).get("peggedUSD")
                if usd is None:
                    usd = (point.get("totalCirculating") or {}).get("peggedUSD")
                rows.append({
                    "date_utc": when.isoformat(timespec="seconds"),
                    "circulating_usd": usd,
                    "retrieved_at": retrieved,
                })
            return rows
        try:
            rows, reused = cached_or_fetch("supply", f"usdc_circulating_{label}.json", url, build)
        except Exception as exc:  # source indisponible : on le consigne, on n'invente rien
            print(f"  supply {label}: ÉCHEC ({exc})")
            manifest.append({"source": "DeFiLlama", "endpoint": url, "window": "crise ±15 j",
                             "records": 0, "file": None, "from_cache": False,
                             "limits": f"Indisponible lors de la collecte : {exc}"})
            continue
        out[label] = rows
        manifest.append({"source": "DeFiLlama", "endpoint": url, "window": "crise ±15 j",
                         "records": len(rows),
                         "file": f"corpus/raw/supply/usdc_circulating_{label}.json",
                         "from_cache": reused,
                         "limits": "Série quotidienne, granularité grossière ; couvre l'on-chain observable uniquement."})
    save_raw("circle", "circle_statement_reference.json", CIRCLE_STATEMENT)
    manifest.append({"source": "Circle", "endpoint": CIRCLE_STATEMENT["url"], "window": "12/03/2023",
                     "records": 1, "file": "corpus/raw/circle/circle_statement_reference.json", "from_cache": False,
                     "limits": CIRCLE_STATEMENT["limit"]})
    return out


def write_csv(prices, bitstamp, binance, supply):
    path = os.path.join(CORPUS, "usdc_observations.csv")
    n = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        # lineterminator explicite : le défaut du module csv est '\r\n', ce qui
        # rendrait le fichier dépendant du style d'écriture et casserait la
        # comparaison directe sha256sum <-> empreinte enregistrée (LF partout).
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["timestamp_utc", "venue", "metric", "value", "extra", "retrieved_at"])
        for label, rows in prices.items():
            for r in rows:
                if r["price"] is None:
                    continue
                w.writerow([r["timestamp_utc"], "defillama", "price_usd", r["price"],
                            f"confidence={r['confidence']}", r["retrieved_at"]]); n += 1
        for r in bitstamp:
            w.writerow([r["timestamp_utc"], "bitstamp", "close_usd", r["close"],
                        f"low={r['low']}", r["retrieved_at"]]); n += 1
        for r in binance:
            w.writerow([r["timestamp_utc"], "binance", "close_usdcusdt", r["close"],
                        f"low={r['low']}", r["retrieved_at"]]); n += 1
        for label, rows in supply.items():
            for r in rows:
                if r["circulating_usd"] is None:
                    continue
                w.writerow([r["date_utc"], f"defillama_supply_{label}", "circulating_usd",
                            r["circulating_usd"], "", r["retrieved_at"]]); n += 1
    print(f"  CSV: {n} observations → {os.path.relpath(path, BASE)}")
    return n


def write_readme(manifest, n_obs):
    path = os.path.join(CORPUS, "README.md")
    lines = [
        "# Corpus USDC — cas pilote ORVYREN (épisode SVB, mars 2023)",
        "",
        "Collecte reproductible : `python collect_corpus.py` (réseau) ou `--offline` (rejeu de l'archive).",
        f"Dernière collecte : {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}",
        f"Observations unifiées : **{n_obs}** (voir `usdc_observations.csv`).",
        "",
        "## Fenêtres",
        f"- principale (depeg) : {MAIN_START.date()} → {MAIN_END.date()}, pas horaire ;",
        f"- témoin (hors crise) : {CTRL_START.date()} → {CTRL_END.date()}, pas horaire.",
        "",
        "## Sources et limites",
        "",
        "| Source | Endpoint | Enregistrements | Limite à afficher |",
        "|---|---|---|---|",
    ]
    for m in manifest:
        lines.append(f"| {m['source']} | `{m['endpoint']}` | {m['records']} | {m['limits']} |")
    lines += [
        "",
        "## Règles d'usage",
        "1. Les prix de testnet ne servent **jamais** de contexte de décision (V0.2 §3.5).",
        "2. Toute analyse historique n'utilise que les informations disponibles à l'instant simulé (point-in-time).",
        "3. Un prix d'agrégateur et un prix d'exchange ne sont pas deux preuves indépendantes par construction ;",
        "   la comparaison Bitstamp / Binance / DeFiLlama est conservée pour mesurer les écarts **entre venues**.",
        "4. La déclaration de l'émetteur est enregistrée comme référence documentaire : elle doit être lue et citée,",
        "   jamais reformulée automatiquement.",
    ]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"  README → {os.path.relpath(path, BASE)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="rejoue l'archive sans réseau")
    parser.add_argument("--force", action="store_true", help="recollecte tout, ignore le cache local")
    args = parser.parse_args()
    ensure_dirs()
    manifest_path = os.path.join(CORPUS, "manifest.json")

    global FORCE
    FORCE = bool(args.force)

    if args.offline:
        if not os.path.exists(manifest_path):
            print("Aucun corpus archivé. Lancez une collecte en ligne d'abord."); sys.exit(1)
        data = json.load(open(manifest_path, encoding="utf-8"))
        print(f"REPLAY — corpus du {data['collected_at']} : {sum(m['records'] for m in data['sources'])} enregistrements.")
        return

    if os.path.exists(manifest_path):
        print("Un corpus existe déjà (une collecte par jour suffit) ; il sera écrasé.\n")
    manifest = []
    print("Collecte du corpus USDC (mars 2023)…")
    prices = collect_defillama_prices(manifest)
    bitstamp = collect_bitstamp(manifest)
    binance = collect_binance(manifest)
    supply = collect_supply(manifest)
    problems = validate_archived_windows(prices, bitstamp, binance, supply)
    if problems:
        print("CONTRAT DE FENÊTRE VIOLÉ — écriture du corpus refusée :")
        for problem in problems[:10]:
            print("  " + problem)
        sys.exit(2)
    n_obs = write_csv(prices, bitstamp, binance, supply)
    write_readme(manifest, n_obs)
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump({"collected_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                   "windows": {"main": [MAIN_START.isoformat(), MAIN_END.isoformat()],
                               "control": [CTRL_START.isoformat(), CTRL_END.isoformat()]},
                   "observations": n_obs, "sources": manifest}, fh, ensure_ascii=False, indent=1)
    print(f"Manifest → {os.path.relpath(manifest_path, BASE)}")


if __name__ == "__main__":
    main()
