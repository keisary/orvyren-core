#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — CLI de l'exécuteur autonome (dry-run par défaut).

Une commande, une boucle bornée :

    python run_executor.py --case usdc-2023-03 --ticks 5 --dry-run

Chaque tick : décision replay (``build_decision_record``) -> intent borné ->
``policy.evaluate`` avec un ``PolicyState`` réel (pause, solde, enveloppe,
budget) et le cumul 24 h d'un ledger persistant -> verdict journalisé. Un
verdict ALLOW en dry-run produit un rapport DRY-RUN sans signature ; avec
``--execute`` le signataire isolé est importé paresseusement, signe, diffuse et
le reçu est vérifié — sans clé ou sans ``eth-account``, le run est refusé avant
le premier tick (code 4).

Codes de sortie : 0 run terminé · 2 configuration/destinataire · 3 pause
(kill switch) · 4 exécution réelle indisponible · 5 erreur d'exécution
(ledger/journal/réseau/reçu).

Aucune clé n'est lue en dry-run. Aucun secret n'est imprimé dans quelque mode
que ce soit.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime
from typing import Any, Callable, Mapping, Optional

ROOT = os.path.dirname(os.path.abspath(__file__))
if os.path.join(ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "src"))

from orvyren.execution import loop as executor  # noqa: E402
from orvyren.execution.chain import ChainError  # noqa: E402

DEFAULT_CASE = "usdc-2023-03"
DEFAULT_POLICY = os.path.join(ROOT, "policy_v1.yaml")
DEFAULT_RUN_DIR = os.path.join(ROOT, "demo_runs", "executor")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_executor.py",
        description="ORVYREN — exécuteur autonome borné : décision -> politique "
                    "(état réel) -> journal chaîné. Dry-run par défaut, aucune clé lue.")
    parser.add_argument("--case", default=DEFAULT_CASE,
                        help="identifiant de cas rejoué (défaut : %(default)s)")
    parser.add_argument("--ticks", type=int, default=1,
                        help="nombre de ticks (défaut : %(default)s)")
    parser.add_argument("--interval-s", type=float, default=0.0,
                        help="attente entre ticks, en secondes (défaut : %(default)s)")
    parser.add_argument("--max-usd", type=float, default=None,
                        help="plafond par tick en USDC (optionnel) — au-delà, refus fail-closed")
    parser.add_argument("--recipient", default=None,
                        help="destinataire de réserve demandé — doit figurer dans la liste "
                             "blanche résolue (ORVYREN_RECIPIENT_B/C)")
    parser.add_argument("--policy", default=DEFAULT_POLICY,
                        help="chemin de policy_v1.yaml (défaut : racine du dépôt)")
    parser.add_argument("--fixture", default=None,
                        help="fixture d'enveloppe (défaut : celle déclarée par policy_v1.yaml)")
    parser.add_argument("--ledger", default=None,
                        help="ledger JSON 24 h (défaut : demo_runs/executor/<case>/ledger.json)")
    parser.add_argument("--journal", default=None,
                        help="journal JSONL chaîné (défaut : demo_runs/executor/<case>/journal.jsonl)")
    parser.add_argument("--json", action="store_true",
                        help="sortie machine (un objet JSON sur stdout)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=None,
                      help="aucune signature, aucune clé lue (défaut)")
    mode.add_argument("--execute", action="store_true",
                      help="signature et diffusion réelles (exige ORVYREN_PRIVATE_KEY + eth-account)")
    return parser


def _human(summary: Mapping[str, Any]) -> None:
    counts = summary["counts"]
    policy = summary["policy"]
    envelope = summary["envelope"]
    print("ORVYREN — exécuteur autonome ({})".format(summary["mode"]))
    print("  case       : {}  ({} tick(s) exécuté(s))".format(summary["case"], summary["ticks_run"]))
    print("  politique  : {}  hash {}  ({})".format(
        policy.get("version"), str(policy.get("policy_hash") or "")[:16],
        policy.get("path") or "policy_v1.yaml"))
    print("  enveloppe  : {} (source: {})".format(envelope.get("status"), envelope.get("source")))
    print("  destinataire: {}".format(summary["recipient"]))
    print("  ledger     : {}  ({:.2f} USDC consommés / 24 h avant le run)".format(
        summary["ledger"]["path"] or "(mémoire)", summary["ledger"]["spent_24h_before"]))
    print("  journal    : {}".format(summary["journal"]["path"]))
    print("  tick  intent                                        montant  verdict   outcome")
    for record in summary["records"]:
        intent = record.get("intent") or {}
        codes = ", ".join(record.get("reasons") or []) or "-"
        print("  {:>4}  {:<46} {:>7.2f}  {:<8}  {}".format(
            record.get("tick", 0), str(intent.get("intent_id") or "-")[:46],
            float(intent.get("amount") or 0.0), str(record.get("verdict") or "-"),
            str(record.get("outcome") or "-")))
        if codes != "-" or record.get("error"):
            print("        refus: {} {}".format(codes, record.get("error") or "").rstrip())
    chain_state = summary["journal"]
    print("  chaîne du journal : {}".format(
        "VALIDE ({} enregistrement(s))".format(chain_state["records"])
        if chain_state["ok"] else "ROMPUE — {}".format(chain_state["error"])))
    print("  bilan      : {} ALLOW · {} DENY · {} DRY-RUN · {} signé(s) · {} erreur(s)".format(
        counts["allow"], counts["deny"], counts["dry_run"], counts["signed"], counts["errors"]))
    print("  consommé 24 h après le run : {:.2f} USDC".format(summary["ledger"]["spent_24h_after"]))
    if summary["paused"]:
        print("  PAUSE / kill switch ENGAGÉ — aucun transfert autonome n'a été autorisé.")


def main(argv: Optional[list] = None, env: Optional[Mapping[str, str]] = None,
         clock: Optional[Callable[[], datetime]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    environment = os.environ if env is None else env
    now_fn = clock or executor.utcnow

    if args.ticks < 0:
        print("ERREUR : --ticks doit être >= 0", file=sys.stderr)
        return executor.EXIT_USAGE
    if args.interval_s is not None and (not math.isfinite(args.interval_s) or args.interval_s < 0):
        print("ERREUR : --interval-s doit être un nombre fini >= 0", file=sys.stderr)
        return executor.EXIT_USAGE
    if args.max_usd is not None and (not math.isfinite(args.max_usd) or args.max_usd < 0):
        print("ERREUR : --max-usd doit être un nombre fini >= 0", file=sys.stderr)
        return executor.EXIT_USAGE

    policy_path = args.policy if os.path.isabs(args.policy) else os.path.join(ROOT, args.policy)
    if not os.path.exists(policy_path):
        print("ERREUR : policy_v1.yaml introuvable : {}".format(policy_path), file=sys.stderr)
        return executor.EXIT_USAGE
    if args.fixture and not os.path.exists(args.fixture):
        print("ERREUR : fixture d'enveloppe introuvable : {}".format(args.fixture), file=sys.stderr)
        return executor.EXIT_USAGE

    try:
        recipient, recipients = executor.collect_recipients(args.recipient, environment)
    except executor.RecipientError as exc:
        print("ERREUR destinataire : {}".format(exc), file=sys.stderr)
        return executor.EXIT_USAGE

    try:
        bundle = executor.load_bundle(policy_path, recipients)
    except executor.PolicyLoadError as exc:
        print("ERREUR politique : {}".format(exc), file=sys.stderr)
        return executor.EXIT_USAGE
    allowed = {str(address).lower() for address in bundle.config.allowed_recipients}
    if recipient not in allowed:
        print("ERREUR destinataire : {} hors liste blanche de policy_v1.yaml "
              "({} destinataire(s) résolu(s) : {}). Renseigner ORVYREN_RECIPIENT_B/C "
              "ou --recipient.".format(recipient, len(allowed), ", ".join(sorted(allowed)) or "aucun"),
              file=sys.stderr)
        return executor.EXIT_USAGE

    try:
        executor.apply_permission_window(bundle, now_fn())
    except executor.PolicyLoadError as exc:
        print("ERREUR politique : {}".format(exc), file=sys.stderr)
        return executor.EXIT_USAGE

    signer = None
    if args.execute:
        try:
            signer = executor.preflight_signer(env=environment)
        except executor.ExecuteUnavailable as exc:
            print("ERREUR --execute : {}".format(exc), file=sys.stderr)
            return executor.EXIT_EXECUTE

    run_dir = os.path.join(DEFAULT_RUN_DIR, executor.safe_case(args.case))
    journal_path = args.journal or os.path.join(run_dir, "journal.jsonl")
    ledger_path = args.ledger or os.path.join(run_dir, "ledger.json")

    try:
        summary = executor.run_loop(
            bundle,
            case=args.case,
            recipient=recipient,
            journal_path=journal_path,
            ledger_path=ledger_path,
            ticks=args.ticks,
            interval_s=args.interval_s,
            dry_run=not args.execute,
            max_usd=args.max_usd,
            policy_path=policy_path,
            fixture_path=args.fixture,
            env=environment,
            clock=now_fn,
            signer=signer,
            rpc_url=str(environment.get("ORVYREN_RPC_URL_BASE_SEPOLIA") or "") or None,
        )
    except (executor.LedgerError, executor.JournalError, executor.PolicyLoadError) as exc:
        print("ERREUR exécution : {}".format(exc), file=sys.stderr)
        return executor.EXIT_RUNTIME
    except ChainError as exc:
        print("ERREUR réseau : {}".format(exc), file=sys.stderr)
        return executor.EXIT_RUNTIME

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        _human(summary)

    if summary["stopped"] or summary["counts"]["errors"]:
        return executor.EXIT_RUNTIME
    if summary["paused"]:
        return executor.EXIT_PAUSED
    if not summary["journal"]["ok"]:
        print("ERREUR : chaîne du journal invalide — {}".format(summary["journal"]["error"]),
              file=sys.stderr)
        return executor.EXIT_RUNTIME
    return executor.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
