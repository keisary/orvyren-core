#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — service de politique (verdict déterministe, hors LLM).

Rôle : recevoir un *intent* structuré et rendre un verdict ALLOW / DENY /
REQUIRE_APPROVAL avec les règles évaluées et des codes de raison stables.
Le modèle de langage n'entre pas ici : la politique est appliquée par ce code.

Règles implémentées (proposition D9 de FREEZE_V1.md) :
  R1  chaîne autorisée (Base Sepolia, 84532)
  R2  actif autorisé (jeton de test allowlisté)
  R3  destinataire autorisé (allowlist)
  R4  montant > 0 et <= plafond par transaction
  R5  plafond cumulé sur la fenêtre de permission
  R6  permission non expirée
  R7  idempotence : un intent déjà vu est refusé (pas de double envoi)
  R8  type d'action hors périmètre -> REQUIRE_APPROVAL ; hors liste -> DENY

Exécution des tests : python -m unittest discover -s tests -v
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable

ALLOWED_CHAIN_ID = 84532                     # Base Sepolia
ALLOWED_ASSET = "0x036cbd53842c5426634e7929541eC2318f3dCF7e"   # USDC de test (Circle, Base Sepolia)
MAX_PER_TX = 100.0                           # 100 USDC de test
MAX_CUMULATIVE = 300.0                       # 300 USDC de test
PERMISSION_TTL = timedelta(hours=24)
ACTIONS_AUTONOMES = {"transfer"}             # exécutables sans humain, si toutes les règles passent
ACTIONS_SOUS_APPROBATION = {"swap", "approve", "change_policy", "revoke"}  # jamais autonomes ici


@dataclass(frozen=True)
class Intent:
    """Demande d'opération structurée — non autorisée par nature."""
    intent_id: str
    action: str                     # transfer | swap | approve | change_policy | revoke
    chain_id: int
    asset: str                      # adresse du jeton
    amount: float                   # en unités du jeton
    recipient: str                  # adresse destinataire ou contrat
    created_at: datetime
    justification: str = ""


@dataclass
class PolicyConfig:
    allowed_chain_ids: frozenset = frozenset({ALLOWED_CHAIN_ID})
    allowed_assets: frozenset = frozenset({ALLOWED_ASSET})
    allowed_recipients: frozenset = frozenset()
    max_per_tx: float = MAX_PER_TX
    max_cumulative: float = MAX_CUMULATIVE
    permission_expires_at: datetime | None = None


@dataclass
class PolicyDecision:
    verdict: str                    # ALLOW | DENY | REQUIRE_APPROVAL
    reasons: list = field(default_factory=list)
    rules_evaluated: list = field(default_factory=list)

    def as_dict(self):
        return {"verdict": self.verdict, "reasons": self.reasons,
                "rules_evaluated": self.rules_evaluated}


def _norm(addr: str) -> str:
    return (addr or "").strip().lower()


def evaluate(intent: Intent, config: PolicyConfig, now: datetime | None = None,
             seen_intent_ids: Iterable[str] = (), cumulative_spent: float = 0.0) -> PolicyDecision:
    """Rend le verdict déterministe pour un intent donné."""
    now = now or datetime.now(timezone.utc)
    reasons, evaluated = [], []

    def fail(rule, code):
        evaluated.append({"rule": rule, "result": "FAIL", "code": code})
        reasons.append(code)

    def ok(rule, note=""):
        evaluated.append({"rule": rule, "result": "OK", "note": note})

    # R0 — périmètre d'action
    if intent.action not in ACTIONS_AUTONOMES and intent.action not in ACTIONS_SOUS_APPROBATION:
        fail("R8-action", "ACTION_UNKNOWN")
        return PolicyDecision("DENY", reasons, evaluated)

    # R1 — chaîne autorisée
    (ok if intent.chain_id in config.allowed_chain_ids else
     lambda *_: fail("R1-chain", "CHAIN_NOT_ALLOWED"))("R1-chain", str(intent.chain_id))
    if reasons:
        return PolicyDecision("DENY", reasons, evaluated)

    # R2 — actif autorisé
    if _norm(intent.asset) not in {_norm(a) for a in config.allowed_assets}:
        fail("R2-asset", "ASSET_NOT_ALLOWED")
    else:
        ok("R2-asset")

    # R3 — destinataire autorisé
    if _norm(intent.recipient) not in {_norm(r) for r in config.allowed_recipients}:
        fail("R3-recipient", "RECIPIENT_NOT_ALLOWED")
    else:
        ok("R3-recipient")

    # R4 — montant par transaction
    if intent.amount <= 0:
        fail("R4-amount", "AMOUNT_INVALID")
    elif intent.amount > config.max_per_tx:
        fail("R4-amount", "AMOUNT_ABOVE_TX_CAP")
    else:
        ok("R4-amount", f"{intent.amount} <= {config.max_per_tx}")

    # R5 — plafond cumulé
    if cumulative_spent + max(intent.amount, 0) > config.max_cumulative:
        fail("R5-cumulative", "AMOUNT_ABOVE_PERIOD_CAP")
    else:
        ok("R5-cumulative", f"{cumulative_spent + max(intent.amount, 0)} <= {config.max_cumulative}")

    # R6 — permission
    if config.permission_expires_at is None:
        fail("R6-permission", "PERMISSION_MISSING")
    elif now >= config.permission_expires_at:
        fail("R6-permission", "PERMISSION_EXPIRED")
    else:
        ok("R6-permission", config.permission_expires_at.isoformat())

    # R7 — idempotence
    if intent.intent_id in set(seen_intent_ids):
        fail("R7-idempotency", "INTENT_ALREADY_PROCESSED")
    else:
        ok("R7-idempotency")

    if reasons:
        return PolicyDecision("DENY", reasons, evaluated)

    # Action hors périmètre autonome mais connue : jamais seul, toujours revue humaine
    if intent.action in ACTIONS_SOUS_APPROBATION:
        evaluated.append({"rule": "R8-action", "result": "REQUIRE_APPROVAL",
                          "code": "ACTION_NEEDS_HUMAN_APPROVAL"})
        return PolicyDecision("REQUIRE_APPROVAL", ["ACTION_NEEDS_HUMAN_APPROVAL"], evaluated)

    evaluated.append({"rule": "R8-action", "result": "OK", "note": intent.action})
    return PolicyDecision("ALLOW", [], evaluated)


def default_config(reserve_recipient: str, ttl_hours: int = 24,
                   now: datetime | None = None) -> PolicyConfig:
    """Configuration de démonstration : une chaîne, un actif, un destinataire, une échéance."""
    now = now or datetime.now(timezone.utc)
    return PolicyConfig(
        allowed_recipients=frozenset({_norm(reserve_recipient)}),
        permission_expires_at=now + timedelta(hours=ttl_hours),
    )
