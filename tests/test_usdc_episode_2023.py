#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests W3-B — reconstruction de l'épisode USDC mars 2023.

Banc de test de `scripts/reconstruct_usdc2023_episode.py`, **entièrement
hors-ligne** :

  * parseurs et signaux sur fixtures locales (valeurs réelles extraites de
    `fixtures/raw_w2b/` le 2026-10-15 — chaque fixture est citée) ;
  * recherche dichotomique bloc <-> timestamp sur un faux RPC synthétique
    (aucun appel réseau) ;
  * reconstruction complète en mode `--from-cache` depuis les JSON bruts du
    dépôt, puis vérification des faits clés de W2-B ;
  * le fichier de preuve `evidence/episode_usdc_2023-03.json` est contrôlé
    (structure, alignement horaire, faits reproduits) s'il est présent.

Exécution : ``python -m pytest tests/ -q`` (ou ciblé :
``python -m pytest tests/test_usdc_episode_2023.py -q``).
"""

import ast
import importlib.util
import json
import math
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(ROOT, "scripts", "reconstruct_usdc2023_episode.py")
RAW_W2B = os.path.join(ROOT, "fixtures", "raw_w2b")
EVIDENCE_PATH = os.path.join(ROOT, "evidence", "episode_usdc_2023-03.json")

_spec = importlib.util.spec_from_file_location("reconstruct_usdc2023_episode", SCRIPT_PATH)
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

# ---------------------------------------------------------------------------
# Fixtures réelles (fixtures/raw_w2b/, mesurées le 2026-10-15)
# ---------------------------------------------------------------------------

#: Bougie Binance USDCUSDT 1 h ouverte le 2023-03-11 14:00 UTC (min de W2-B).
BINANCE_ROW = [1678543200000, "1.00000000", "1.00000000", "0.88200000", "0.91290000",
               "108959660.00000000", 1678546799999, "99089712.08660000", 27487,
               "38341506.00000000", "34895611.26770000", "0"]

#: Bougies OKX USDC-USDT, l'une portant le minimum 0,8698 (07:00 UTC).
OKX_ROW_MIN = ["1678518000000", "0.8949", "0.8994", "0.8698", "0.8787",
               "102699036.415701", "90704990.3656136072", "90704990.3656136072", "1"]
OKX_ROW_PREV = ["1678514400000", "0.9298", "0.9392", "0.8901", "0.8949",
                "63056686.2636", "57753348.9395770944", "57753348.9395770944", "1"]

#: Bougie Bitstamp usdcusd 1 h de 07:00 UTC (low 0,80526 ; close 0,86267).
BITSTAMP_ROW_MIN = {"timestamp": "1678518000", "open": "0.87879", "high": "0.88020",
                    "low": "0.80526", "close": "0.86267", "volume": "859447.32116"}

LLAMA_COIN = "ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
#: Deux points DeFiLlama réels (dont le minimum 0,876675 du 11/03 07:57:53 UTC).
LLAMA_PAYLOAD = {"coins": {LLAMA_COIN: {"symbol": "USDC", "decimals": 6, "confidence": 0.99,
                                        "prices": [
                                            {"timestamp": 1678449651, "price": 1.0019133810854473},
                                            {"timestamp": 1678521473, "price": 0.876675},
                                        ]}}}


def _words(*values):
    return "0x" + "".join(f"{v:064x}" for v in values)


#: Retour ABI réel de latestRoundData() — round du minimum Chainlink de W2-B
#: (bloc 0x1006c88, updatedAt 1678539575).
CHAINLINK_HEX = _words(36893488147419104266, 90687439, 1678539575, 1678539575, 1678539575)

#: Raws Aave réels (aEthUSDC totalSupply / USDC balanceOf au 2023-03-11 12:00).
AAVE_SUPPLY_RAW = 78973957356818
AAVE_CASH_RAW = 45351464777335
AAVE_U_W2B = 0.42574151916397907  # valeur publiée par W2-B pour ce couple


# ---------------------------------------------------------------------------
# 1. Parseurs de venues
# ---------------------------------------------------------------------------

class VenueParsersTest(unittest.TestCase):

    def test_parse_binance_klines(self):
        pts = M.parse_binance_klines([BINANCE_ROW])
        self.assertEqual(len(pts), 1)
        p = pts[0]
        self.assertEqual(p["ts"], 1678543200)          # ms -> s
        self.assertAlmostEqual(p["high"], 1.0)
        self.assertAlmostEqual(p["low"], 0.882)
        self.assertAlmostEqual(p["last"], 0.9129)
        self.assertAlmostEqual(p["volume"], 108959660.0)

    def test_parse_okx_candles_orders_ascending(self):
        # OKX renvoie le plus récent d'abord : le parseur doit trier.
        pts = M.parse_okx_candles([OKX_ROW_MIN, OKX_ROW_PREV])
        self.assertEqual([p["ts"] for p in pts], [1678514400, 1678518000])
        self.assertAlmostEqual(pts[1]["low"], 0.8698)
        self.assertAlmostEqual(pts[1]["volume"], 102699036.415701)

    def test_parse_bitstamp_ohlc(self):
        pts = M.parse_bitstamp_ohlc([BITSTAMP_ROW_MIN])
        self.assertEqual(pts[0]["ts"], 1678518000)
        self.assertAlmostEqual(pts[0]["low"], 0.80526)
        self.assertAlmostEqual(pts[0]["last"], 0.86267)
        self.assertAlmostEqual(pts[0]["volume"], 859447.32116)

    def test_parse_llama_chart(self):
        pts = M.parse_llama_chart(LLAMA_PAYLOAD)
        self.assertEqual(len(pts), 2)
        self.assertAlmostEqual(pts[1]["low"], 0.876675)
        self.assertIsNone(pts[1]["volume"])

    def test_parse_llama_chart_unknown_coin_is_empty(self):
        self.assertEqual(M.parse_llama_chart({"coins": {}}), [])

    def test_filter_window_keeps_only_period(self):
        pts = [{"ts": t, "low": 1.0, "high": 1.0, "last": 1.0, "volume": None}
               for t in (M.WINDOW_START_TS - 1, M.WINDOW_START_TS, M.WINDOW_END_TS)]
        kept = M.filter_window(pts)
        self.assertEqual([p["ts"] for p in kept],
                         [M.WINDOW_START_TS, M.WINDOW_END_TS])


# ---------------------------------------------------------------------------
# 2. Signaux dérivés
# ---------------------------------------------------------------------------

class SignalsTest(unittest.TestCase):

    def test_discount_bps(self):
        self.assertAlmostEqual(M.discount_bps(1.0), 0.0)
        self.assertAlmostEqual(M.discount_bps(0.876675), 1233.25, places=6)
        self.assertIsNone(M.discount_bps(None))

    def test_dispersion_bps_reproduces_w2b_870(self):
        # minima de venues mesurés par W2-B : Bitstamp 0,80526 -> Binance 0,8820
        value = M.dispersion_bps([0.80526, 0.8698, 0.876675, 0.882])
        self.assertAlmostEqual(value, 870.068, places=3)

    def test_dispersion_bps_needs_two_venues(self):
        self.assertIsNone(M.dispersion_bps([]))
        self.assertIsNone(M.dispersion_bps([0.9]))

    def test_divergence_bps_sign(self):
        # oracle 0,90687439 vs DefiLlama 0,876675 -> marché SOUS l'oracle (-302 bps)
        value = M.divergence_bps(0.876675, 0.90687439)
        self.assertAlmostEqual(value, -301.9939, places=3)
        self.assertAlmostEqual(M.divergence_bps(0.95, 0.90), 500.0, places=6)


# ---------------------------------------------------------------------------
# 3. Décodeurs (Chainlink, ERC20, Aave)
# ---------------------------------------------------------------------------

class DecodersTest(unittest.TestCase):

    def test_decode_latest_round_data_matches_w2b_min(self):
        d = M.decode_latest_round_data(CHAINLINK_HEX)
        self.assertEqual(d["answer_raw"], 90687439)
        self.assertAlmostEqual(d["answer"], 0.90687439, places=12)
        self.assertEqual(d["updatedAt"], 1678539575)
        self.assertEqual(d["roundId"], 36893488147419104266)

    def test_decode_latest_round_data_rejects_short_payload(self):
        with self.assertRaises(ValueError):
            M.decode_latest_round_data("0x1234")

    def test_decode_uint256(self):
        self.assertEqual(M.decode_uint256(_words(78973957356818)), 78973957356818)
        with self.assertRaises(ValueError):
            M.decode_uint256("")

    def test_sel_balance_of_is_32_byte_aligned(self):
        data = M.sel_balance_of(M.AAVE_A_USDC)
        self.assertTrue(data.startswith("0x70a08231"))
        self.assertEqual(len(data), 10 + 64)  # sélecteur + 1 mot ABI
        self.assertEqual(data[10:34], "0" * 24)  # adresse alignée à droite
        self.assertEqual(data[34:], M.AAVE_A_USDC[2:].lower())

    def test_aave_row_from_raw_matches_w2b_documented_u(self):
        row = M.aave_row_from_raw(AAVE_SUPPLY_RAW, AAVE_CASH_RAW)
        self.assertAlmostEqual(row["supply_usdc"], 78973957.356818, places=6)
        self.assertAlmostEqual(row["cash_usdc"], 45351464.777335, places=6)
        self.assertAlmostEqual(row["utilisation"], AAVE_U_W2B, places=12)


# ---------------------------------------------------------------------------
# 4. Agrégation horaire
# ---------------------------------------------------------------------------

class BucketTest(unittest.TestCase):

    def test_bucket_by_hour_low_high_last_volume(self):
        hours = [1678406400, 1678410000]
        pts = [
            {"ts": 1678406401, "low": 0.99, "high": 1.00, "last": 0.995, "volume": 10.0},
            {"ts": 1678407199, "low": 0.97, "high": 0.99, "last": 0.98, "volume": 5.0},
            {"ts": 1678410000, "low": 0.95, "high": 0.96, "last": 0.951, "volume": 1.0},
            {"ts": 1678413600, "low": 0.01, "high": 0.01, "last": 0.01, "volume": 9.0},  # hors fenêtre
        ]
        buckets = M.bucket_by_hour(pts, hours)
        self.assertEqual(set(buckets), {1678406400, 1678410000})
        first = buckets[1678406400]
        self.assertAlmostEqual(first["low"], 0.97)
        self.assertAlmostEqual(first["high"], 1.00)
        self.assertAlmostEqual(first["last"], 0.98)   # dernière observation de l'heure
        self.assertAlmostEqual(first["volume"], 15.0)
        self.assertEqual(first["n"], 2)
        self.assertNotIn(1678413600, buckets)


# ---------------------------------------------------------------------------
# 5. Recherche dichotomique bloc <-> timestamp (faux RPC synthétique)
# ---------------------------------------------------------------------------

_B0, _TS0 = 16_800_000, 1_678_539_600  # bloc/timestamp d'ancrage synthétiques


def _synth_ts(block):
    """Faux historique de blocs : rythme ~12 s plus une dérive sinusoïdale."""
    return _TS0 + round(12.05 * (block - _B0)) + int(45 * math.sin((block - _B0) / 6500.0))


def _synth_true_block(target):
    """Vérité terrain par balayage local (indépendante de la dichotomie)."""
    b = _B0 + int((target - _TS0) / 12.05) - 500
    while _synth_ts(b + 1) <= target:
        b += 1
    while _synth_ts(b) > target:
        b -= 1
    return b


def _make_index(seed=None, hours_span=40):
    """BlockIndex branché sur le faux RPC (aucun réseau) + compteurs de sondes."""
    counters = {"single": 0, "batch": 0}

    def fake_call(method, params):
        counters["single"] += 1
        return {"timestamp": hex(_synth_ts(int(params[0], 16)))}

    def fake_batch(calls):
        counters["batch"] += len(calls)
        return [fake_call(m, p) for m, p in calls]

    if seed is None:
        seed = [(_B0, _TS0),
                (_B0 + 310 * hours_span, _TS0 + 3600 * hours_span)]
    idx = M.BlockIndex(call=fake_call, batch=fake_batch, seed=seed)
    return idx, counters


class BlockIndexTest(unittest.TestCase):

    def test_local_search_exact_on_synthetic_chain(self):
        idx, _ = _make_index()
        for i in (0, 5, 17, 39):
            target = _TS0 + 3600 * i + 17  # cible volontairement décalée
            self.assertEqual(idx.local_search(target), _synth_true_block(target),
                             f"cible {target}")

    def test_local_search_expands_window_far_from_seed(self):
        idx, _ = _make_index()
        target = _TS0 + 3600 * 300  # ~12 jours après les ancres
        self.assertEqual(idx.local_search(target), _synth_true_block(target))

    def test_local_search_boundary_before_seed(self):
        idx, _ = _make_index()
        target = _TS0 - 3600 * 5
        self.assertEqual(idx.local_search(target), _synth_true_block(target))

    def test_resolve_hours_batched_and_brackets(self):
        idx, counters = _make_index()
        hours = [_TS0 + 3600 * i for i in range(40)]
        resolved = idx.resolve_hours(hours)
        self.assertEqual(set(resolved), set(hours))
        for h in hours:
            b = resolved[h]
            self.assertLessEqual(_synth_ts(b), h)
            self.assertLess(_synth_ts(b + 1), h + 10 ** 9)
            self.assertEqual(b, _synth_true_block(h))
        self.assertGreater(counters["batch"], 0)
        self.assertGreater(len(idx.cache), 40)

    def test_align_series_to_hours_carry_forward(self):
        sparse = {1678406400: {"price": 1.0}, 1678420800: {"price": 0.9}}
        hours = [1678406400, 1678410000, 1678420800, 1678424400, 1678428000]
        aligned = M.align_series_to_hours(hours, sparse)
        self.assertEqual(aligned[1678406400]["aligned"], True)
        self.assertEqual(aligned[1678410000]["aligned"], False)
        self.assertAlmostEqual(aligned[1678410000]["price"], 1.0)  # propagation
        self.assertAlmostEqual(aligned[1678424400]["price"], 0.9)
        self.assertEqual(aligned[1678428000]["aligned"], False)


# ---------------------------------------------------------------------------
# 6. Reconstruction complète hors-ligne (--from-cache, fichiers du dépôt)
# ---------------------------------------------------------------------------

@unittest.skipUnless(os.path.exists(os.path.join(RAW_W2B, "venue_minima_usdc_2023.json")),
                     "raw_w2b absent")
class FromCachePipelineTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.doc = M.build_evidence(from_cache=True, raw_dir=RAW_W2B,
                                   out_path=None, verbose=False)

    def test_window_and_hourly_shape(self):
        self.assertEqual(self.doc["mode"], "from-cache")
        self.assertEqual(self.doc["window"]["n_points"], 97)
        self.assertEqual(len(self.doc["hourly"]), 97)
        ts_list = [row["ts"] for row in self.doc["hourly"]]
        self.assertEqual(ts_list, sorted(ts_list))
        self.assertEqual(ts_list[0], M.WINDOW_START_TS)
        self.assertEqual(ts_list[-1], M.WINDOW_END_TS)
        for row in self.doc["hourly"]:
            self.assertEqual(row["ts"] % 3600, 0)

    def test_all_w2b_facts_reproduced(self):
        comp = self.doc["w2b_comparison"]
        for key, check in comp.items():
            self.assertTrue(check["reproduced"], f"{key} non reproduit: {check}")
        self.assertAlmostEqual(comp["defillama_min"]["measured"], 0.876675, places=9)
        self.assertAlmostEqual(comp["bitstamp_min"]["measured"], 0.80526, places=9)
        self.assertAlmostEqual(comp["okx_min"]["measured"], 0.8698, places=9)
        self.assertAlmostEqual(comp["binance_min"]["measured"], 0.882, places=9)
        self.assertAlmostEqual(comp["dispersion_bps"]["measured"], 870.07, delta=0.5)

    def test_oracle_w2b_value_present_in_cached_series(self):
        check = self.doc["w2b_comparison"]["oracle_min"]
        self.assertTrue(check["w2b_value_present_in_series"])
        self.assertEqual(check["w2b_value_utc"], "2023-03-11T12:59:35Z")

    def test_hour_of_stress_contains_w2b_measurements(self):
        row = next(r for r in self.doc["hourly"] if r["utc"] == "2023-03-11T07:00:00Z")
        self.assertAlmostEqual(row["venues"]["bitstamp"]["low"], 0.80526, places=9)
        self.assertAlmostEqual(row["venues"]["okx"]["low"], 0.8698, places=9)
        self.assertAlmostEqual(row["venues"]["defillama"]["low"], 0.876675, places=9)
        # bitstamp close de l'heure = 0,86267 (le « 0,8627 » du brief)
        self.assertAlmostEqual(row["venues"]["bitstamp"]["last"], 0.86267, places=9)
        self.assertAlmostEqual(row["signals"]["decote_min_bps"], 1947.4, places=1)
        self.assertAlmostEqual(row["signals"]["sigma_disp_bps"], 814.6, places=1)

    def test_derived_signals_present_everywhere_expected(self):
        for row in self.doc["hourly"]:
            sig = row["signals"]
            for key in ("decote_min_bps", "decote_median_bps", "sigma_disp_bps",
                        "divergence_bps", "divergence_defillama_bps"):
                self.assertIn(key, sig)
            if row["oracle"] is not None:
                # l'horodatage de l'oracle ne peut pas être postérieur à l'heure lue
                self.assertLessEqual(row["oracle"]["updatedAt"], row["ts"])
            if row["oracle"] is not None and row["market"]["median"] is not None:
                self.assertIsNotNone(sig["divergence_bps"])
            elif row["market"]["median"] is None:
                self.assertIsNone(sig["divergence_bps"])


# ---------------------------------------------------------------------------
# 7. Fichier de preuve (evidence/episode_usdc_2023-03.json), s'il existe
# ---------------------------------------------------------------------------

@unittest.skipUnless(os.path.exists(EVIDENCE_PATH), "preuve pas encore générée")
class EvidenceFileTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(EVIDENCE_PATH, "r", encoding="utf-8") as fh:
            cls.ev = json.load(fh)

    def test_schema_and_window(self):
        self.assertEqual(self.ev["schema"], "orvyren.evidence.episode-usdc-2023-03.v1")
        self.assertIn(self.ev["mode"], ("network", "from-cache"))
        self.assertEqual(self.ev["window"]["start_utc"], "2023-03-10T00:00:00Z")
        self.assertEqual(self.ev["window"]["end_utc"], "2023-03-14T00:00:00Z")
        self.assertEqual(len(self.ev["hourly"]), self.ev["window"]["n_points"])

    def test_all_w2b_facts_reproduced_in_evidence(self):
        for key, check in self.ev["w2b_comparison"].items():
            self.assertTrue(check["reproduced"], f"{key}: {check}")
        self.assertAlmostEqual(self.ev["facts"]["minima"]["bitstamp"]["low"],
                               0.80526, places=9)
        self.assertAlmostEqual(self.ev["facts"]["minima"]["defillama"]["low"],
                               0.876675, places=9)
        self.assertAlmostEqual(
            self.ev["facts"]["signals"]["dispersion_window_bps"]["value_bps"],
            870.07, delta=0.5)

    def test_oracle_dense_minimum(self):
        """Correction W3 : l'échantillonnage horaire voit l'oracle plus bas.

        En mode réseau, le minimum dense mesuré est 0,8833 (11/03 07:53:23) ;
        la valeur de W2-B (0,90687439) doit rester présente dans la série.
        En mode cache, la série est celle de W2-B elle-même.
        """
        check = self.ev["w2b_comparison"]["oracle_min"]
        self.assertTrue(check["w2b_value_present_in_series"])
        dense = check["dense_min"]
        if self.ev["mode"] == "network":
            self.assertAlmostEqual(dense, 0.8833, places=9)
            self.assertEqual(check["dense_min_utc"], "2023-03-11T07:53:23Z")
            self.assertLess(dense, check["w2b"])
        else:
            self.assertAlmostEqual(dense, 0.90687439, places=9)

    def test_aave_series_refuge_flow(self):
        """U baisse pendant la crise (dépôts de refuge) — fait W2-B §2."""
        u = self.ev["facts"]["signals"]["aave_usdc_utilisation"]
        self.assertLess(u["min"], u["start"])  # au moins un creux plus bas
        self.assertGreater(u["n"], 90)
        rows = [row for row in self.ev["hourly"]
                if row.get("aave") and row["aave"].get("utilisation") is not None]
        self.assertGreater(len(rows), 90)
        for row in rows:
            self.assertGreater(row["aave"]["utilisation"], 0.0)
            self.assertLess(row["aave"]["utilisation"], 1.0)

    def test_control_source_mode_recorded(self):
        for name, info in self.ev["sources"].items():
            self.assertIn(info["mode"], ("network", "cache", "cache-fallback"), name)


# ---------------------------------------------------------------------------
# 8. Contrainte de conception : script autonome, stdlib uniquement
# ---------------------------------------------------------------------------

class SelfContainedTest(unittest.TestCase):

    def test_script_imports_stdlib_only(self):
        with open(SCRIPT_PATH, "r", encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module != "__future__":
                    modules.add(node.module.split(".")[0])
        allowed = {"argparse", "json", "os", "sys", "time", "urllib", "datetime", "statistics"}
        self.assertTrue(modules <= allowed, f"imports hors stdlib: {modules - allowed}")
        self.assertNotIn("orvyren", modules)  # aucun import depuis src/


if __name__ == "__main__":
    unittest.main()
