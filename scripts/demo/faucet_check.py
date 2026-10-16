#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — kit de démo testnet (W5, L5.2) : **faucet / soldes avant run**.

Vérifie avant chaque run ce qui est indispensable :

* **agent** : solde ETH ≥ seuil (il paie le gaz) ;
* **Safe** : solde USDC ≥ seuil (c'est elle qui détient les fonds — l'avance
  exécute *en tant que* Safe via Roles) ;
* propriétaires : soldes ETH rapportés (information).

Si un seuil n'est pas atteint, le script sort en ``exit 1`` et rappelle les
robinets gratuits (testnet uniquement — aucune valeur réelle).

CLI :

    python scripts/demo/faucet_check.py [--rpc] [--min-eth 0.0005] [--min-usdc 1]
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional

try:  # paquet (``demo.faucet_check``)
    from . import common
except ImportError:  # exécution directe : python scripts/demo/faucet_check.py
    _sys_dir = os.path.dirname(os.path.abspath(__file__))
    if _sys_dir not in sys.path:
        sys.path.insert(0, _sys_dir)
    import common  # type: ignore  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ENV = os.path.join(HERE, ".env")
DEFAULT_OWNERS = os.path.join(HERE, "owners.env")

USDC_DECIMALS = 6  # USDC Circle (test) — jamais l'USDC d'Aave (B5 §b.2)

FAUCET_HINTS = [
    "ETH Base Sepolia : https://portal.cdp.coinbase.com/products/faucet (gratuit)",
    "USDC test Circle : https://faucet.circle.com (gratuit, choisir Base Sepolia)",
]

EXIT_OK = 0
EXIT_NOT_READY = 1
EXIT_USAGE = 2


def eth_balance(rpc_url: str, address: str) -> int:
    return int(common.eth_get_balance(rpc_url, address) or 0)


def usdc_balance(rpc_url: str, usdc_address: str, holder: str) -> int:
    data = common.SELECTOR_BALANCE_OF + common.enc_address(holder)
    payload = common.eth_call(rpc_url, usdc_address, data)
    return common.decode_word_uint(payload or "0x")


def run(*, env: Dict[str, str], rpc_url: Optional[str],
        min_eth: float, min_usdc: float) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "mode": "rpc" if rpc_url else "offline",
        "thresholds": {"min_eth_agent": min_eth, "min_agent_usdc": min_usdc},
        "balances": {}, "checks": [], "faucets": FAUCET_HINTS,
    }
    agent = env.get("ORVYREN_AGENT_ADDRESS", "")
    safe = env.get("ORVYREN_SAFE_ADDRESS", "")
    usdc = env.get("ORVYREN_USDC_ADDRESS", "")
    owners = [env.get(key, "") for key in ("ORVYREN_OWNER1_ADDRESS", "ORVYREN_OWNER2_ADDRESS",
                                           "ORVYREN_OWNER3_ADDRESS")]
    if not rpc_url:
        report["checks"].append({"id": "F0", "status": "SKIPPED",
                                 "detail": "offline — soldes non lus ; passer --rpc"})
        report["verdict"] = "OFFLINE_PASS"
        return report
    if not (agent and safe and usdc):
        report["checks"].append({"id": "F0", "status": "FAIL",
                                 "detail": "agent/Safe/USDC absents de l'env"})
        report["verdict"] = "FAIL"
        return report

    try:
        agent_eth_wei = eth_balance(rpc_url, agent)
        safe_usdc = usdc_balance(rpc_url, usdc, safe)
        agent_usdc = usdc_balance(rpc_url, usdc, agent)
        owner_eth = {address: eth_balance(rpc_url, address) for address in owners if address}
    except Exception as exc:
        report["checks"].append({"id": "F1", "status": "FAIL",
                                 "detail": "rpc indisponible : %s" % exc})
        report["verdict"] = "FAIL"
        return report

    agent_eth = agent_eth_wei / 1e18
    report["balances"] = {
        "agent_eth": agent_eth, "agent_eth_wei": agent_eth_wei,
        "safe_usdc": safe_usdc / 10 ** USDC_DECIMALS, "safe_usdc_base_units": safe_usdc,
        "agent_usdc": agent_usdc / 10 ** USDC_DECIMALS,
        "owner_eth": {address: wei / 1e18 for address, wei in owner_eth.items()},
    }
    ready = True
    if agent_eth < min_eth:
        ready = False
        report["checks"].append({"id": "F2.agent_eth", "status": "FAIL",
                                 "detail": "agent %.6f ETH < seuil %.6f — robinet ETH requis"
                                           % (agent_eth, min_eth)})
    else:
        report["checks"].append({"id": "F2.agent_eth", "status": "PASS",
                                 "detail": "agent %.6f ETH ≥ seuil %.6f" % (agent_eth, min_eth)})
    if safe_usdc / 10 ** USDC_DECIMALS < min_usdc:
        ready = False
        report["checks"].append({"id": "F3.safe_usdc", "status": "FAIL",
                                 "detail": "Safe %.6f USDC < seuil %.6f — robinet USDC requis"
                                           % (safe_usdc / 10 ** USDC_DECIMALS, min_usdc)})
    else:
        report["checks"].append({"id": "F3.safe_usdc", "status": "PASS",
                                 "detail": "Safe %.6f USDC ≥ seuil %.6f"
                                           % (safe_usdc / 10 ** USDC_DECIMALS, min_usdc)})
    report["verdict"] = "READY" if ready else "NOT_READY"
    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="faucet_check.py",
        description="ORVYREN (W5/L5.2) — soldes avant run : ETH agent, USDC Safe, "
                    "robinets gratuits rappelés. Testnet uniquement.")
    parser.add_argument("--env-file", default=DEFAULT_ENV)
    parser.add_argument("--rpc", action="store_true", help="lecture en ligne (lecture seule)")
    parser.add_argument("--rpc-url", default=None)
    parser.add_argument("--min-eth", type=float, default=0.0005,
                        help="seuil ETH de l'agent (défaut 0,0005)")
    parser.add_argument("--min-usdc", type=float, default=1.0,
                        help="seuil USDC de la Safe (défaut 1)")
    parser.add_argument("--out", default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    env = common.load_session_env(args.env_file)
    rpc_url = args.rpc_url or (env.get("ORVYREN_RPC_URL_BASE_SEPOLIA") if args.rpc else None)
    if args.rpc and not rpc_url:
        print("faucet_check: --rpc exige --rpc-url ou ORVYREN_RPC_URL_BASE_SEPOLIA", file=sys.stderr)
        return EXIT_USAGE
    report = run(env=env, rpc_url=rpc_url, min_eth=args.min_eth, min_usdc=args.min_usdc)
    if args.out:
        common.write_json(args.out, report)
    if not args.quiet:
        for check in report["checks"]:
            print("  [%s] %s — %s" % (check["status"], check["id"], str(check["detail"])[:180]))
        if report["verdict"] in ("NOT_READY", "FAIL"):
            for hint in FAUCET_HINTS:
                print("  robinet : %s" % hint)
        print("VERDICT: %s" % report["verdict"])
    return EXIT_OK if report["verdict"] in ("READY", "OFFLINE_PASS") else EXIT_NOT_READY


if __name__ == "__main__":
    sys.exit(main())
