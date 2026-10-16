#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — vérificateur du paquet de gel `frozen/` (hors-ligne).

Trois contrôles, dans cet ordre :

1. **empreintes** — les manifestes ``G1..G6.sha256`` existent et concordent avec
   les fichiers qu'ils référencent (``orvyren.evaluation.windows.verify_frozen_package``) ;
2. **chaînes** — ``forecasts_dev.jsonl`` (``prev_hash`` + empreinte auto-portée)
   et ``outcomes_dev.jsonl`` (chaînage + liaison par empreinte
   prévision ↔ outcome) ;
3. **recalcul intégral** — le paquet est reconstruit dans un répertoire
   temporaire par ``scripts/freeze_sprint0.py`` et comparé **octet à octet** :
   c'est la preuve que `frozen/` est recalculable hors-ligne.

Sortie : une ligne par contrôle, puis le verdict. Code de sortie 0 si tout
concorde, 1 sinon (utilisable en CI). Aucun accès réseau.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys
import tempfile
import time
from typing import Optional, Sequence

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REPO_ROOT = os.path.dirname(SCRIPTS_DIR)
sys.path.insert(0, os.path.join(DEFAULT_REPO_ROOT, "src"))

from orvyren.evaluation import forecasts as forecasts_mod  # noqa: E402
from orvyren.evaluation import outcomes as outcomes_mod  # noqa: E402
from orvyren.evaluation import windows as windows_mod  # noqa: E402


def _load_builder():
    spec = importlib.util.spec_from_file_location("freeze_sprint0", os.path.join(SCRIPTS_DIR, "freeze_sprint0.py"))
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    return builder


def verify(frozen_dir: str, repo_root: str, recalc: bool = True) -> bool:
    ok = True

    # 1. empreintes G1..G6
    try:
        hashes = windows_mod.verify_frozen_package(frozen_dir)
        for name in sorted(hashes):
            print(f"[OK]   {name}.sha256 vérifié ({hashes[name][:16]}…)")
    except Exception as exc:  # noqa: BLE001 — le rapport doit tout montrer
        print(f"[KO]   paquet de gel : {exc}")
        ok = False

    # 2. chaînes prévisions / outcomes
    forecasts_path = os.path.join(frozen_dir, "forecasts_dev.jsonl")
    outcomes_path = os.path.join(frozen_dir, "outcomes_dev.jsonl")
    try:
        records = forecasts_mod.load_forecasts(forecasts_path)
        ids = forecasts_mod.verify_forecast_chain(records, path=forecasts_path)
        print(f"[OK]   forecasts_dev.jsonl : {len(ids)} prévisions, chaîne vérifiée")
    except Exception as exc:  # noqa: BLE001
        print(f"[KO]   forecasts_dev.jsonl : {exc}")
        ok = False
        records = []
    try:
        outcomes = outcomes_mod.load_outcomes(outcomes_path)
        ids_out = outcomes_mod.verify_outcome_chain(outcomes, path=outcomes_path)
        print(f"[OK]   outcomes_dev.jsonl : {len(ids_out)} outcomes, chaîne vérifiée")
        by_id = {record["forecast_id"]: record for record in records}
        for outcome in outcomes:
            outcomes_mod.check_link(by_id[outcome["forecast_id"]], outcome)
        print(f"[OK]   liaison prévision ↔ outcome par empreinte : {len(outcomes)}/{len(records)}")
    except Exception as exc:  # noqa: BLE001
        print(f"[KO]   outcomes_dev.jsonl : {exc}")
        ok = False

    if not recalc:
        return ok

    # 3. recalcul intégral hors-ligne dans un répertoire temporaire
    started = time.perf_counter()
    builder = _load_builder()
    tmp = tempfile.mkdtemp(prefix="orvyren_frozen_recalc_")
    try:
        builder.build_all(tmp, repo_root=repo_root)
        elapsed = time.perf_counter() - started
        names = sorted(os.listdir(frozen_dir))
        mismatches = []
        for name in names:
            source = os.path.join(frozen_dir, name)
            rebuilt = os.path.join(tmp, name)
            if not os.path.isfile(rebuilt):
                mismatches.append(name)
                continue
            with open(source, "rb") as handle:
                left = handle.read().replace(b"\r\n", b"\n")
            with open(rebuilt, "rb") as handle:
                right = handle.read().replace(b"\r\n", b"\n")
            if left != right:
                mismatches.append(name)
        extra = sorted(set(os.listdir(tmp)) - set(names))
        if mismatches or extra:
            print(f"[KO]   recalcul : écarts {mismatches or ''} {('en trop: ' + str(extra)) if extra else ''}")
            ok = False
        else:
            print(f"[OK]   recalcul hors-ligne identique octet à octet ({len(names)} fichiers, {elapsed:.2f} s)")
    except Exception as exc:  # noqa: BLE001
        print(f"[KO]   recalcul hors-ligne : {exc}")
        ok = False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return ok


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Vérifie frozen/ : empreintes, chaînes, recalcul hors-ligne.")
    parser.add_argument("--frozen", default=None, help="répertoire du paquet (défaut : <repo>/frozen)")
    parser.add_argument("--repo-root", default=None, help="racine du dépôt (défaut : parent de scripts/)")
    parser.add_argument("--no-recalc", action="store_true", help="saute le recalcul intégral (rapide)")
    args = parser.parse_args(argv)
    repo_root = args.repo_root or DEFAULT_REPO_ROOT
    frozen_dir = args.frozen or os.path.join(repo_root, "frozen")
    ok = verify(frozen_dir, repo_root, recalc=not args.no_recalc)
    print("VERDICT : " + ("paquet de gel CONFORME" if ok else "ÉCARTS DÉTECTÉS — ne pas revendiquer"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
