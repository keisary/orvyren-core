#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — policy <-> on-chain envelope drift check (10 checks, DOC2 §5.5.4).

Two stages:
  --offline (default): compliance of `policy_v1.yaml` <-> versioned envelope
      fixture (`fixtures/roles_agent_config.json`) — no network;
  --rpc              : offline stage + chain reads (chainId, contract code)
      and probe replays (eth_call) — READ ONLY, never a signature, never a
      transaction.

Output: JSON report (default `evidence/envelope_drift_report.json`).
Three verdicts (DOC2 §5.5.4):
  PASS        — every executed check passes;
  DRIFT       — at least one divergence => SAFE MODE: no autonomous action allowed;
  UNVERIFIED  — verification impossible (RPC unreachable, incomplete capture) => SAFE MODE.
A check that cannot run is `SKIPPED` with its reason written down — never silent.

Exit codes: 0 PASS · 2 DRIFT · 3 UNVERIFIED · 4 usage.

Implementation note: this script (W4) reuses the JSON-RPC client and read-only
helpers of the demo kit (`scripts/demo/common.py`); it imports neither `signer`
nor anything that holds a key.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _path in (os.path.join(ROOT, "src"), os.path.join(ROOT, "scripts"), ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from orvyren.execution.chain import ChainError, RpcError  # noqa: E402
from orvyren.policy import load_policy  # noqa: E402
from demo import common  # noqa: E402

EXIT_OK, EXIT_DRIFT, EXIT_UNVERIFIED, EXIT_USAGE = 0, 2, 3, 4

STATUS_PASS = "PASS"
STATUS_DRIFT = "DRIFT"
STATUS_UNVERIFIED = "UNVERIFIED"
STATUS_SKIPPED = "SKIPPED"

FIXTURE_SCHEMA = "orvyren-roles-agent-config/v1"
CHECK_ORDER = ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10"]


def _check(check_id: str, name: str, status: str, detail: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"id": check_id, "family": "drift", "name": name, "status": status,
            "detail": detail or {}}


def _base_units(amount: float, decimals: int) -> int:
    return int(round(float(amount) * (10 ** decimals)))


# --- offline stage: policy <-> fixture ---------------------------------------


def offline_checks(bundle, fixture: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    checks: Dict[str, Dict[str, Any]] = {}
    data, cfg = bundle.data, bundle.config
    role = fixture.get("role") or {}

    # D3 (offline part) — role identity (membership is verified in --rpc)
    key_fixture = str(fixture.get("role_key") or "").lower()
    key_policy = str(data.get("role_key") or "").lower()
    checks["D3"] = _check("D3", "membres du rôle AGENT",
                          STATUS_PASS if key_fixture and key_fixture == key_policy else STATUS_DRIFT,
                          {"role_key_fixture": fixture.get("role_key"),
                           "role_key_policy": data.get("role_key"),
                           "note": "sonde comportementale d'appartenance exécutée en mode --rpc"})

    # D4 — role targets == expected set; broad clearance forbidden
    targets = role.get("targets") or []
    fixture_targets = {str(t.get("address") or "").lower(): str(t.get("clearance") or "") for t in targets}
    broad = sorted(addr for addr, clearance in fixture_targets.items()
                   if clearance.lower() != "function")
    policy_targets = set(cfg.allowed_targets)
    if broad:
        status, detail = STATUS_DRIFT, {"cibles_portee_large": broad,
                                        "note": "Clearance.Target = n'importe quel calldata (mode d'erreur n° 1)"}
    elif set(fixture_targets) != policy_targets:
        status, detail = STATUS_DRIFT, {"fixture": sorted(fixture_targets), "policy": sorted(policy_targets)}
    else:
        status, detail = STATUS_PASS, {"targets": sorted(fixture_targets)}
    checks["D4"] = _check("D4", "cibles du rôle (clearance)", status, detail)

    # D5 — functions ((target, selector) pairs == expected, Function/CALL scope)
    functions = role.get("functions") or []
    fixture_functions = {(str(f.get("target") or "").lower(), str(f.get("selector") or "").lower())
                         for f in functions}
    bad_scope = [f.get("target") for f in functions
                 if str(f.get("clearance") or "").lower() != "function"
                 or str(f.get("operation") or "").upper() != "CALL"]
    if bad_scope:
        status, detail = STATUS_DRIFT, {"portee_invalide": bad_scope}
    elif fixture_functions != set(cfg.allowed_functions):
        status, detail = STATUS_DRIFT, {"fixture": sorted(fixture_functions),
                                        "policy": sorted(map(tuple, cfg.allowed_functions))}
    else:
        status, detail = STATUS_PASS, {"functions": sorted(fixture_functions)}
    checks["D5"] = _check("D5", "fonctions du rôle (cible, sélecteur)", status, detail)

    # D6 — conditions: recipients and allowance
    conditions = role.get("conditions") or {}
    param0 = conditions.get("param0") or {}
    param1 = conditions.get("param1") or {}
    values = {str(v).lower() for v in (param0.get("values") or [])}
    resolved = set(cfg.allowed_recipients)
    missing = sorted(resolved - values)
    unresolved = data.get("_unresolved_recipients") or []
    if str(param0.get("kind") or "") != "or_equal":
        status, detail = STATUS_DRIFT, {"param0": param0, "attendu": "or_equal"}
    elif str(param1.get("kind") or "") != "within_allowance":
        status, detail = STATUS_DRIFT, {"param1": param1, "attendu": "within_allowance"}
    elif missing:
        status, detail = STATUS_DRIFT, {"destinataires_absents_de_la_condition": missing}
    else:
        status, detail = STATUS_PASS, {"values": sorted(values),
                                       "non_resolus": unresolved}
        if unresolved:
            detail["pending"] = "destinataires non résolus (labels sans adresse de session) — à vérifier au montage"
    checks["D6"] = _check("D6", "conditions (destinataires + allowance)", status, detail)

    # D7 — allowances: bounds and consistency with the policy parameters
    allowance = (role.get("allowances") or {}).get("usdc_daily") or {}
    refill = allowance.get("refill_base_units")
    max_refill = allowance.get("max_refill_base_units")
    problems: List[str] = []
    if not isinstance(refill, int) or not isinstance(max_refill, int):
        problems.append("allowance illisible (refill/maxRefill absents)")
    elif cfg.asset_decimals is not None:
        per_tx = _base_units(cfg.max_per_tx, cfg.asset_decimals)
        cumulative = _base_units(cfg.max_cumulative, cfg.asset_decimals)
        if per_tx > min(refill, max_refill):
            problems.append(f"plafond par transaction {per_tx} > min(refill, maxRefill) {min(refill, max_refill)}")
        if cumulative > max_refill:
            problems.append(f"cumul 24 h {cumulative} > maxRefill {max_refill}")
        if refill != max_refill:
            problems.append("refill != maxRefill (la rafale de frontière de période n'est plus bornée)")
    if data.get("allowance_refill_base_units") != refill \
            or data.get("allowance_max_refill_base_units") != max_refill:
        problems.append("allowances de la fixture != paramètres policy_v1.yaml")
    checks["D7"] = _check("D7", "allowances (refill / maxRefill / période)",
                          STATUS_DRIFT if problems else STATUS_PASS,
                          {"problems": problems} if problems
                          else {"refill": refill, "max_refill": max_refill,
                                "period_seconds": allowance.get("period_seconds")})

    # D8 — call quota
    quota = role.get("call_quota") or {}
    policy_quota = data.get("max_calls_24h")
    try:
        quota_ok = (isinstance(quota.get("max_per_period"), int)
                    and policy_quota is not None
                    and quota["max_per_period"] == int(policy_quota))
    except (TypeError, ValueError):
        quota_ok = False
    checks["D8"] = _check("D8", "quota d'appels / jour",
                          STATUS_PASS if quota_ok else STATUS_DRIFT,
                          {"fixture": quota.get("max_per_period"),
                           "policy": policy_quota})

    # D9 — deadlines: policy <= recorded scheduled revocation
    policy_revocation = data.get("revocation_scheduled_at")
    fixture_revocation = fixture.get("revocation_scheduled_at")
    if not policy_revocation or not fixture_revocation:
        checks["D9"] = _check("D9", "échéance de révocation planifiée", STATUS_DRIFT,
                              {"policy": policy_revocation, "fixture": fixture_revocation,
                               "note": "absence = échéance hors chaîne non suivie"})
    else:
        try:
            ok = common.parse_rfc3339(str(policy_revocation)) <= common.parse_rfc3339(str(fixture_revocation))
        except Exception as exc:  # noqa: BLE001 — invalid date format = drift
            ok = False
            checks["D9"] = _check("D9", "échéance de révocation planifiée", STATUS_DRIFT,
                                  {"error": str(exc)})
        if "D9" not in checks:
            checks["D9"] = _check("D9", "échéance de révocation planifiée",
                                  STATUS_PASS if ok else STATUS_DRIFT,
                                  {"policy": policy_revocation, "fixture": fixture_revocation})

    # D10 — module version/advisory: not tracked in v1
    checks["D10"] = _check("D10", "version / avis de sécurité du module", STATUS_SKIPPED,
                           {"note": "non suivis en v1 — l'empreinte du bytecode épinglée (D2) sert de garde"})
    return checks


# --- live stage: chain reads + replays ---------------------------------------


def replay_probe(probe: Dict[str, Any], rpc_url: str, timeout: int) -> Dict[str, Any]:
    call: Dict[str, Any] = {"to": common.normalize_address(probe["to"]), "data": probe["data"]}
    if probe.get("from"):
        call["from"] = common.normalize_address(probe["from"])
    try:
        result = common.rpc(rpc_url, "eth_call", [call, "latest"], timeout)
        return {"probe": probe.get("id"), "outcome": "success", "result": str(result)[:80],
                "ok": bool((probe.get("expect") or {}).get("success"))}
    except RpcError as exc:
        selector = common.revert_selector(getattr(exc, "data", None))
        expected = (probe.get("expect") or {}).get("revert_selector")
        return {"probe": probe.get("id"), "outcome": "revert", "revert_selector": selector,
                "expected": expected,
                "ok": expected is not None and selector == str(expected).lower()}
    except ChainError as exc:
        return {"probe": probe.get("id"), "outcome": "unavailable", "error": str(exc)[:160],
                "ok": None}


def live_checks(bundle, fixture: Dict[str, Any], rpc_url: str, timeout: int,
                checks: Dict[str, Dict[str, Any]]) -> None:
    """Complete checks D1/D2/D3 and attach the probes to their target checks."""
    # D1 — chain
    try:
        chain_id = common.eth_chain_id(rpc_url, timeout)
        if chain_id != fixture.get("chain_id"):
            checks["D1"] = _check("D1", "chaîne (eth_chainId)", STATUS_DRIFT,
                                  {"observed": chain_id, "expected": fixture.get("chain_id")})
        else:
            checks["D1"] = _check("D1", "chaîne (eth_chainId)", STATUS_PASS, {"chain_id": chain_id})
    except ChainError as exc:
        checks["D1"] = _check("D1", "chaîne (eth_chainId)", STATUS_UNVERIFIED, {"error": str(exc)[:200]})

    # D2 — contract code (module, singleton, safe, USDC Circle)
    refs: List[tuple] = [("module", fixture.get("module"))]
    singleton = (fixture.get("module") or {}).get("singleton")
    if singleton:
        refs.append(("singleton", singleton))
    if fixture.get("avatar"):
        refs.append(("safe", fixture["avatar"]))
    contracts = fixture.get("contracts") or {}
    for label in ("usdc_circle_base_sepolia",):
        if label in contracts:
            refs.append((label, {"address": contracts[label]["address"],
                                 "code_size_expected": contracts[label]["code_size_bytes"],
                                 "code_sha256_expected": contracts[label]["code_sha256"]}))
    try:
        mismatches, observed = [], {}
        for label, ref in refs:
            if not ref or not ref.get("address"):
                continue
            code = common.eth_get_code(rpc_url, ref["address"], "latest", timeout)
            body = code[2:] if code.startswith("0x") else code
            size = len(body) // 2
            sha = hashlib.sha256(bytes.fromhex(body)).hexdigest() if body else ""
            observed[label] = {"size": size, "sha256": sha}
            if size != ref.get("code_size_expected") or sha != ref.get("code_sha256_expected"):
                mismatches.append(label)
        checks["D2"] = _check("D2", "module (code + empreinte épinglée)",
                              STATUS_DRIFT if mismatches else STATUS_PASS,
                              {"observed": observed, "mismatches": mismatches})
    except (ChainError, ValueError, KeyError, TypeError) as exc:
        checks["D2"] = _check("D2", "module (code + empreinte épinglée)", STATUS_UNVERIFIED,
                              {"error": str(exc)[:200]})

    # D3/D6/D7 — behavioural probes (replays of the measured refusals)
    evidence: Dict[str, List[Dict[str, Any]]] = {}
    for probe in fixture.get("probes") or []:
        result = replay_probe(probe, rpc_url, timeout)
        for target in probe.get("proves") or []:
            evidence.setdefault(target, []).append(result)
    for check_id, results in evidence.items():
        if check_id not in checks or not results:
            continue
        entry = checks[check_id]
        entry["detail"]["probes"] = results
        if any(r.get("ok") is False for r in results):
            entry["status"] = STATUS_DRIFT
        elif all(r.get("ok") is None for r in results):
            entry["detail"]["probes_note"] = "sondes indisponibles (nœud) — verdict inchangé, à rejouer"


# --- report ------------------------------------------------------------------


def build_report(*, bundle, fixture, fixture_path: str, policy_path: str,
                 mode: str, rpc_url: Optional[str], timeout: int) -> Dict[str, Any]:
    checks = offline_checks(bundle, fixture)
    if mode == "rpc":
        live_checks(bundle, fixture, rpc_url or common.DEFAULT_RPC_URL, timeout, checks)
    else:
        checks["D1"] = _check("D1", "chaîne (eth_chainId)", STATUS_SKIPPED,
                              {"note": "mode --offline : lecture chaîne non demandée"})
        checks["D2"] = _check("D2", "module (code + empreinte épinglée)", STATUS_SKIPPED,
                              {"note": "mode --offline : lecture chaîne non demandée"})

    ordered = [checks[key] for key in CHECK_ORDER if key in checks]
    summary = {status: sum(1 for c in ordered if c["status"] == status)
               for status in (STATUS_PASS, STATUS_DRIFT, STATUS_UNVERIFIED, STATUS_SKIPPED)}
    if summary[STATUS_DRIFT]:
        verdict = STATUS_DRIFT
    elif summary[STATUS_UNVERIFIED]:
        verdict = STATUS_UNVERIFIED
    else:
        verdict = STATUS_PASS
    safe_mode_reasons = [c["id"] for c in ordered if c["status"] in (STATUS_DRIFT, STATUS_UNVERIFIED)]
    report = {
        "schema": "orvyren-envelope-drift-report/v1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": mode,
        "policy": {"path": policy_path, "version": bundle.version,
                   "policy_hash": bundle.policy_hash, "yaml_sha256": bundle.yaml_sha256},
        "fixture": {"path": fixture_path, "captured_at": fixture.get("captured_at"),
                    "capture_block": fixture.get("capture_block")},
        "checks": ordered,
        "summary": summary,
        "verdict": verdict,
        "safe_mode": verdict != STATUS_PASS,
        "safe_mode_reasons": safe_mode_reasons,
        "pending": fixture.get("pending") or [],
    }
    if mode == "rpc":
        report["rpc_url"] = common.mask_rpc_url(rpc_url or common.DEFAULT_RPC_URL)
    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_drift_check.py",
        description="ORVYREN — policy <-> on-chain envelope drift check (10 checks, "
                    "DOC2 §5.5.4). Read only; verdict PASS / DRIFT / UNVERIFIED => SAFE MODE.")
    parser.add_argument("--policy", default=os.path.join(ROOT, "policy_v1.yaml"),
                        help="policy parameters (default: policy_v1.yaml)")
    parser.add_argument("--fixture", help="envelope fixture (default: the one declared by policy_v1.yaml)")
    parser.add_argument("--recipients", help="JSON file label->address to resolve session recipients")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="no network (default)")
    mode.add_argument("--rpc", action="store_true", help="chain reads + probe replays (read only)")
    parser.add_argument("--rpc-url", default=os.environ.get("ORVYREN_RPC_URL_BASE_SEPOLIA") or common.DEFAULT_RPC_URL)
    parser.add_argument("--timeout", type=int, default=common.RPC_TIMEOUT_SECONDS)
    parser.add_argument("--out", default=os.path.join(ROOT, "evidence", "envelope_drift_report.json"))
    parser.add_argument("--quiet", action="store_true", help="print the verdict only")
    args = parser.parse_args(argv)

    recipients = common.load_json(args.recipients) if args.recipients else None
    try:
        bundle = load_policy(args.policy, recipients)
    except Exception as exc:  # noqa: BLE001 — fichier de politique invalide = erreur d'usage
        print("CONFIG ERROR (policy): {}".format(exc), file=sys.stderr)
        return EXIT_USAGE

    fixture_path = args.fixture or bundle.data.get("envelope_fixture") \
        or os.path.join("fixtures", "roles_agent_config.json")
    if not os.path.isabs(fixture_path):
        fixture_path = os.path.join(ROOT, fixture_path)
    try:
        fixture = common.load_json(fixture_path)
    except Exception as exc:  # noqa: BLE001
        print("ERROR unreadable fixture: {} ({})".format(fixture_path, exc), file=sys.stderr)
        return EXIT_USAGE
    if not isinstance(fixture, dict) or fixture.get("schema") != FIXTURE_SCHEMA:
        print("ERROR fixture: expected schema {}".format(FIXTURE_SCHEMA), file=sys.stderr)
        return EXIT_USAGE

    report = build_report(bundle=bundle, fixture=fixture, fixture_path=fixture_path,
                          policy_path=args.policy, mode="rpc" if args.rpc else "offline",
                          rpc_url=args.rpc_url, timeout=args.timeout)

    if args.out:
        common.write_json(args.out, report)

    if args.quiet:
        print(report["verdict"])
    else:
        print("ORVYREN — drift check ({}): verdict {} — safe_mode {}".format(
            report["mode"], report["verdict"], report["safe_mode"]))
        for check in report["checks"]:
            print("  [{}] {:<10} {}".format(check["status"], check["id"], check["name"]))
        if report["safe_mode"]:
            print("  SAFE MODE : {}".format(", ".join(report["safe_mode_reasons"])))

    if report["verdict"] == STATUS_DRIFT:
        return EXIT_DRIFT
    if report["verdict"] == STATUS_UNVERIFIED:
        return EXIT_UNVERIFIED
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
