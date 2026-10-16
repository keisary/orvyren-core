#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — kit de démo testnet : **vérification du reçu** (B5 §d).

Contrôles exacts (uniquement des champs exacts du reçu JSON-RPC ; un contrôle
qui ne peut pas être mappé à un champ exact n'existe pas ici) :

======================  =====================================================  ==========================
Contrôle                Valeur attendue                                        Code de mismatch
======================  =====================================================  ==========================
Statut                  ``status == 0x1`` (absent ≠ succès)                    ``TRANSACTION_FAILED`` / ``RECEIPT_STATUS_MISSING``
Chaîne                  ``chainId == 84532`` (attaché par l'appelant)          ``CHAIN_ID_*``
Contrat du jeton        ``logs[*].address == intent.asset``                    ``TOKEN_CONTRACT_MISMATCH``
Événement               ``topics[0]`` Transfer et **exactement 3 topics**      ``NO_TRANSFER_LOG``
Expéditeur              ``topics[1]`` == **Safe (avatar)**                     ``SENDER_MISMATCH``
Destinataire            ``topics[2]`` == ``intent.recipient``                  ``RECIPIENT_MISMATCH``
Montant                 ``data`` == ``amount_base_units`` (entier)             ``AMOUNT_MISMATCH``
Enveloppe               ``receipt.to`` == module, ``receipt.from`` == agent    ``WRONG_TARGET`` / ``WRONG_EXECUTOR``
Unicité                 +1 log Transfer du jeton sans correspondance exacte  ``LOG_COUNT_AMBIGUOUS``
Module                  au moins un log émis par le module (informatif)        ``MODULE_EVENT_ABSENT`` (WARN)
======================  =====================================================  ==========================

Ajouts de la v1 : la règle d'**unicité** (B5 §d.2 — jamais un « ok » optimiste),
la relecture anti-reorg (``blockNumber`` + ``blockHash`` + profondeur 2 blocs,
B5 §c.4) et, en cas de ``status = 0x0``, le **rejeu ``eth_call`` au bloc du reçu**
pour extraire la donnée de revert (un échec est un résultat de première classe).

CLI :

    python scripts/demo/verify_receipt.py --receipt recu.json --intent intent.json \
        --safe 0x… --module 0x… --agent 0x… [--rpc] [--confirmation-blocks 2] [--out report.json]
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

try:
    from . import common
except ImportError:  # exécution directe
    _sys_dir = os.path.dirname(os.path.abspath(__file__))
    if _sys_dir not in sys.path:
        sys.path.insert(0, _sys_dir)
    import common  # type: ignore  # noqa: E402

from orvyren.execution import verify as base_verify  # noqa: E402

# Codes additionnels de la v1 (B5 §d.1) — les codes du code existant restent inchangés.
LOG_COUNT_AMBIGUOUS = "LOG_COUNT_AMBIGUOUS"
WRONG_TARGET = "WRONG_TARGET"
WRONG_EXECUTOR = "WRONG_EXECUTOR"
MODULE_EVENT_ABSENT = "MODULE_EVENT_ABSENT"       # informatif (WARN), ne fait pas échouer
REORGED = "REORGED"
RECEIPT_UNAVAILABLE = "RECEIPT_UNAVAILABLE"

EXIT_OK = 0
EXIT_MISMATCH = 1
EXIT_USAGE = 2


def _address(value: Any) -> Optional[str]:
    """Adresse normalisée (minuscules), ou None si la valeur n'est pas une adresse."""
    if not common.is_address(value):
        return None
    return common.normalize_address(value)


def exact_transfer_matches(receipt: Dict[str, Any], *, token: str, sender: str, recipient: str,
                           amount_base_units: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Logs Transfer du jeton : ``(tous, correspondances exactes)``."""
    logs = receipt.get("logs") or []
    token_logs = [log for log in logs if isinstance(log, dict)
                  and base_verify.is_transfer_log(log, token)]
    exact: List[Dict[str, Any]] = []
    for log in token_logs:
        try:
            decoded = base_verify.decode_transfer(log)
        except ValueError:
            continue
        if (decoded["from"] == sender and decoded["to"] == recipient
                and decoded["value_base_units"] == amount_base_units):
            exact.append(decoded)
    return token_logs, exact


def verify_full(receipt: Dict[str, Any], *, intent: Dict[str, Any], safe: str, module: str,
                agent: str, chain_id: int = common.CHAIN_ID_DEMO,
                decimals: int = 6) -> Dict[str, Any]:
    """Vérification complète d'un reçu contre l'intent autorisé (fonction pure)."""
    if not isinstance(receipt, dict):
        raise ValueError("receipt doit être un objet")
    safe_n = common.normalize_address(safe, "safe")
    module_n = common.normalize_address(module, "module")
    agent_n = common.normalize_address(agent, "agent")
    token = common.normalize_address(intent.get("asset"), "intent.asset")
    recipient = common.normalize_address(intent.get("recipient"), "intent.recipient")
    amount_base_units = int(intent.get("amount_base_units"))

    expected = {
        "token": token,
        "from": safe_n,
        "to": recipient,
        "amount_usdc": intent.get("amount"),
        "chain_id": chain_id,
        "decimals": decimals,
    }
    base = base_verify.verify_receipt(receipt, expected)
    mismatches: List[str] = list(base["mismatches"])
    warnings: List[str] = []

    token_logs, exact = exact_transfer_matches(receipt, token=token, sender=safe_n,
                                               recipient=recipient, amount_base_units=amount_base_units)
    # Règle d'unicité (B5 §d.2) : dès qu'il y a PLUSIEURS logs Transfer du jeton et que le
    # nombre de correspondances exactes n'est pas exactement 1, la vérification est ambiguë
    # (jamais un « ok » optimiste). Un seul log du jeton qui ne correspond pas = mismatch
    # ordinaire (AMOUNT_MISMATCH / RECIPIENT_MISMATCH…), pas une ambiguïté.
    if len(token_logs) > 1 and len(exact) != 1:
        mismatches.append(LOG_COUNT_AMBIGUOUS)

    receipt_to = _address(receipt.get("to"))
    receipt_from = _address(receipt.get("from"))
    envelope: Dict[str, Any] = {"receipt.to": receipt_to, "receipt.from": receipt_from,
                                "expected_module": module_n, "expected_agent": agent_n}
    if receipt_to is not None and receipt_to != module_n:
        mismatches.append(WRONG_TARGET)
    if receipt_from is not None and receipt_from != agent_n:
        mismatches.append(WRONG_EXECUTOR)

    module_logs = [log for log in (receipt.get("logs") or []) if isinstance(log, dict)
                   and _address(log.get("address")) == module_n]
    if not module_logs:
        warnings.append(MODULE_EVENT_ABSENT)

    return {
        "ok": not mismatches,
        "mismatches": mismatches,
        "warnings": warnings,
        "log_counts": {"token_transfer_logs": len(token_logs), "exact_matches": len(exact)},
        "transfer": base.get("transfer"),
        "expected": base.get("expected"),
        "envelope": envelope,
        "status": receipt.get("status"),
        "block_number": common.hex_to_int(receipt.get("blockNumber")) if receipt.get("blockNumber") else None,
        "block_hash": receipt.get("blockHash"),
        "tx_hash": receipt.get("transactionHash"),
    }


def reorg_check(*, tx_hash: str, receipt_block_number: Optional[int], receipt_block_hash: Optional[str],
                rpc_url: str, confirmation_blocks: int = 2, timeout: int = common.RPC_TIMEOUT_SECONDS) -> Dict[str, Any]:
    """Relecture anti-reorg (B5 §c.4) : hash de bloc inchangé + profondeur de confirmation."""
    result: Dict[str, Any] = {"tx_hash": tx_hash, "confirmation_blocks": confirmation_blocks}
    try:
        fresh = common.rpc(rpc_url, "eth_getTransactionReceipt", [tx_hash], timeout)
        head = common.eth_block_number(rpc_url, timeout)
    except Exception as exc:
        result.update({"status": "UNRESOLVED", "code": RECEIPT_UNAVAILABLE, "error": str(exc)})
        return result
    if fresh is None:
        result.update({"status": "REORGED", "code": REORGED,
                       "note": "le reçu a disparu : reorg probable — re-vérifier P4/P5 avant toute re-émission"})
        return result
    result["block_number"] = common.hex_to_int(fresh.get("blockNumber"))
    result["block_hash"] = fresh.get("blockHash")
    result["confirmations"] = (head - result["block_number"] + 1) if result["block_number"] is not None else None
    if receipt_block_hash and str(fresh.get("blockHash")).lower() != str(receipt_block_hash).lower():
        result.update({"status": "REORGED", "code": REORGED,
                       "note": "blockHash différent de celui consigné"})
        return result
    if receipt_block_number is not None and result["block_number"] != receipt_block_number:
        result.update({"status": "REORGED", "code": REORGED,
                       "note": "numéro de bloc différent de celui consigné"})
        return result
    if (result["confirmations"] or 0) < int(confirmation_blocks):
        result["status"] = "PENDING_CONFIRMATION"
        return result
    result["status"] = "CONFIRMED"
    return result


def wait_for_confirmations(*, tx_hash: str, receipt_block_number: Optional[int], receipt_block_hash: Optional[str],
                           rpc_url: str, confirmation_blocks: int = 2, timeout_seconds: int = 45,
                           poll_seconds: float = 3.0) -> Dict[str, Any]:
    """``reorg_check`` avec **attente bornée** jusqu'à la profondeur voulue (blocs Base ≈ 2 s).

    Ne bloque jamais au-delà de ``timeout_seconds`` : au-delà, l'état ``PENDING_CONFIRMATION``
    est rendu tel quel — jamais d'attente infinie ; un reorg avéré rend la main immédiatement.
    """
    import time as _time
    started = _time.monotonic()
    deadline = started + max(0, int(timeout_seconds))
    result: Dict[str, Any] = {}
    while True:
        result = reorg_check(tx_hash=tx_hash, receipt_block_number=receipt_block_number,
                             receipt_block_hash=receipt_block_hash, rpc_url=rpc_url,
                             confirmation_blocks=confirmation_blocks)
        if result.get("status") in ("CONFIRMED", "REORGED"):
            break
        if _time.monotonic() >= deadline:
            break
        _time.sleep(min(poll_seconds, max(0.1, deadline - _time.monotonic())))
    result["waited_seconds"] = round(_time.monotonic() - started, 2)
    return result


def replay_revert(*, rpc_url: str, tx_hash: str, block_number: Optional[int],
                  timeout: int = common.RPC_TIMEOUT_SECONDS) -> Dict[str, Any]:
    """Rejeu ``eth_call`` au bloc du reçu pour extraire la donnée de revert (échec de 1re classe)."""
    try:
        tx = common.rpc(rpc_url, "eth_getTransactionByHash", [tx_hash], timeout)
        if not isinstance(tx, dict):
            return {"status": "TX_UNAVAILABLE"}
        call = {"from": tx.get("from"), "to": tx.get("to"),
                "data": tx.get("input"), "value": tx.get("value")}
        tag = hex(int(block_number)) if block_number is not None else "latest"
        try:
            output = common.rpc(rpc_url, "eth_call", [call, tag], timeout)
            return {"status": "NO_REVERT", "output": output}
        except common.chain_client.RpcError as exc:
            return {"status": "REVERT", "revert_selector": common.revert_selector(exc.data),
                    "error_message": exc.message, "data": exc.data}
    except Exception as exc:
        return {"status": "REPLAY_FAILED", "error": str(exc)}


# --- CLI ---------------------------------------------------------------------


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verify_receipt.py",
        description="ORVYREN — vérification d'un reçu d'exécution contre l'intent autorisé (B5 §d). "
                    "Lecture seule ; aucune signature.")
    parser.add_argument("--receipt", required=True, help="reçu JSON (eth_getTransactionReceipt)")
    parser.add_argument("--intent", required=True, help="intent v1 autorisé (JSON)")
    parser.add_argument("--safe", required=True, help="adresse de la Safe (avatar) — expéditeur attendu")
    parser.add_argument("--module", required=True, help="adresse du module Roles — cible attendue (receipt.to)")
    parser.add_argument("--agent", required=True, help="adresse de l'agent — receipt.from attendu")
    parser.add_argument("--chain-id", type=int, default=common.CHAIN_ID_DEMO,
                        help="chaîne attendue (défaut 84532) ; le reçu doit porter chainId")
    parser.add_argument("--decimals", type=int, default=6, help="décimales du jeton (USDC = 6)")
    parser.add_argument("--confirmation-blocks", type=int, default=2, help="profondeur anti-reorg (défaut 2)")
    parser.add_argument("--rpc", action="store_true", help="relecture anti-reorg + rejeu du revert (lecture seule)")
    parser.add_argument("--rpc-url", default=os.environ.get("ORVYREN_RPC_URL_BASE_SEPOLIA")
                        or common.DEFAULT_RPC_URL)
    parser.add_argument("--out", help="écrire le rapport JSON à ce chemin")
    args = parser.parse_args(argv)

    try:
        receipt = common.load_json(args.receipt)
        intent = common.load_json(args.intent)
    except (OSError, ValueError) as exc:
        print("ERREUR: fichier illisible: {}".format(exc), file=sys.stderr)
        return EXIT_USAGE
    if not isinstance(receipt, dict) or not isinstance(intent, dict):
        print("ERREUR: --receipt et --intent doivent être des objets JSON", file=sys.stderr)
        return EXIT_USAGE

    try:
        report = verify_full(receipt, intent=intent, safe=args.safe, module=args.module,
                             agent=args.agent, chain_id=args.chain_id, decimals=args.decimals)
    except ValueError as exc:
        print("ERREUR: {}".format(exc), file=sys.stderr)
        return EXIT_USAGE

    if args.rpc:
        tx_hash = report.get("tx_hash")
        if tx_hash:
            report["reorg"] = reorg_check(tx_hash=tx_hash, receipt_block_number=report.get("block_number"),
                                          receipt_block_hash=report.get("block_hash"),
                                          rpc_url=args.rpc_url,
                                          confirmation_blocks=args.confirmation_blocks)
        if str(report.get("status")).lower() in ("0x0", "0"):
            if tx_hash:
                report["revert_replay"] = replay_revert(rpc_url=args.rpc_url, tx_hash=tx_hash,
                                                        block_number=report.get("block_number"))

    if args.out:
        common.write_json(args.out, report)

    status = str(report.get("status"))
    print("ORVYREN — vérification du reçu {}… : {}".format(
        str(report.get("tx_hash") or "?")[:18], "CONFORME" if report["ok"] else "NON CONFORME"))
    print("  statut on-chain : {}".format(status))
    print("  log Transfer (jeton) : {} (correspondances exactes : {})".format(
        report["log_counts"]["token_transfer_logs"], report["log_counts"]["exact_matches"]))
    if report.get("transfer"):
        transfer = report["transfer"]
        print("  transfert décodé : {} → {} : {} unités de base".format(
            common.short_address(transfer["from"]), common.short_address(transfer["to"]),
            transfer["value_base_units"]))
    if report["mismatches"]:
        print("  mismatchs : {}".format(", ".join(report["mismatches"])))
    if report["warnings"]:
        print("  avertissements : {}".format(", ".join(report["warnings"])))
    if "reorg" in report:
        print("  anti-reorg : {} (profondeur {})".format(report["reorg"].get("status"),
                                                         report["reorg"].get("confirmations")))
    if "revert_replay" in report:
        print("  rejeu du revert : {}".format(report["revert_replay"]))

    if not report["ok"]:
        return EXIT_MISMATCH
    if report.get("reorg", {}).get("status") == "REORGED":
        return EXIT_MISMATCH
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
