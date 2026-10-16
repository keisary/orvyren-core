#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — service de politique (verrou 1, déterministe, hors LLM).

Rôle : recevoir un *intent* structuré et rendre un verdict ALLOW / DENY /
REQUIRE_APPROVAL avec les règles évaluées et des codes de raison stables.
Le modèle de langage n'entre pas ici : la politique est appliquée par ce code.

Set v1 : **14 règles** (DOC2 §5.5.2 / FREEZE_V2 D1) :
  P1  chaîne épinglée           P8  permission (mandat) active
  P2  actif autorisé            P9  fraîcheur de l'intention
  P3  destinataire autorisé     P10 idempotence (identifiant + empreinte)
  P4  fonction scopée           P11 pause / kill switch
  P5  plafond par transaction   P12 alignement d'enveloppe (SAFE MODE)
  P6  cumul glissant 24 h       P13 périmètre d'action
  P7  exposition / solde        P14 budget de décision

Historique des étiquettes : R1–R8 (FREEZE_V1, D9) → P1–P14 (FREEZE_V2, D1).
Les **codes de refus sont inchangés** (codes stables, DOC2 §5.5.1) ; une règle
non évaluée apparaît `SKIPPED` avec son motif — jamais silencieuse.

Principes (DOC2 §5.5.1) : fail-closed, deny-by-default, codes stables,
évaluation complète des règles applicables, verdict DENY > REQUIRE_APPROVAL > ALLOW.

Les règles « d'état » (P7, P11, P12, P14) ne s'activent que si l'appelant
fournit un `PolicyState` — alors **fail-closed** : un champ requis illisible
(None/invalide) est un refus, jamais un « on suppose ». Les paramètres v1
(TTL d'intention, registre de fonctions, décimales) viennent de
`policy_v1.yaml` via `load_policy()` (source de vérité des paramètres,
DOC2 §5.5.3) ; sans eux, les règles concernées sont `SKIPPED` (mode legacy).

Exécution des tests : python -m unittest discover -s tests -v
"""

from __future__ import annotations

import hashlib
import json
import math
import os

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from .miniyaml import MiniYamlError, load_file as _load_yaml_file

ALLOWED_CHAIN_ID = 84532                     # Base Sepolia
ALLOWED_ASSET = "0x036cbd53842c5426634e7929541eC2318f3dCF7e"   # USDC de test (Circle, Base Sepolia)
MAX_PER_TX = 100.0                           # 100 USDC de test
MAX_CUMULATIVE = 300.0                       # 300 USDC de test
PERMISSION_TTL = timedelta(hours=24)
ACTIONS_AUTONOMES = {"transfer"}             # exécutables sans humain, si toutes les règles passent
ACTIONS_SOUS_APPROBATION = {"swap", "approve", "change_policy", "revoke"}  # jamais autonomes ici
TRANSFER_SELECTOR = "0xa9059cbb"             # transfer(address,uint256)

CLOCK_SKEW_TOLERANCE = timedelta(seconds=60)
ENVELOPE_PASS = "PASS"
ENVELOPE_DRIFT = "DRIFT"
ENVELOPE_UNVERIFIED = "UNVERIFIED"

#: Codes de refus (P12) qui déclenchent le SAFE MODE — distincts des états d'enveloppe.
SAFE_MODE_CODES = ("ENVELOPE_DRIFT", "ENVELOPE_UNVERIFIED")

#: Les 14 étiquettes du set v1 — utilisées par le banc de tests comme registre.
RULES_V1 = (
    "P1-chain", "P2-asset", "P3-recipient", "P4-function", "P5-amount",
    "P6-cumulative", "P7-exposure", "P8-permission", "P9-freshness",
    "P10-idempotency", "P11-pause", "P12-envelope", "P13-action", "P14-budget",
)

#: Registre des codes de refus v1 (stables — jamais renommés ni réutilisés).
DENY_CODES_V1 = frozenset({
    "CHAIN_NOT_ALLOWED", "ASSET_NOT_ALLOWED", "RECIPIENT_NOT_ALLOWED",
    "TARGET_NOT_ALLOWED", "FUNCTION_NOT_ALLOWED", "OPERATION_NOT_ALLOWED",
    "AMOUNT_NOT_FINITE", "AMOUNT_INVALID", "AMOUNT_ABOVE_TX_CAP",
    "AMOUNT_ABOVE_PERIOD_CAP", "CUMULATIVE_INVALID",
    "BALANCE_UNREADABLE", "BALANCE_INSUFFICIENT", "FLOOR_BREACH", "EXPOSURE_ABOVE_CAP",
    "PERMISSION_MISSING", "PERMISSION_EXPIRED",
    "INTENT_STALE", "INTENT_NOT_YET_VALID",
    "INTENT_ALREADY_PROCESSED",
    "PAUSED", "AGENT_NOT_MEMBER",
    "ENVELOPE_DRIFT", "ENVELOPE_UNVERIFIED",
    "ACTION_UNKNOWN",
    "BUDGET_EXCEEDED", "BUDGET_UNREADABLE",
})

#: Codes de raison incluant le verdict d'approbation (non-refus).
REASON_CODES_V1 = DENY_CODES_V1 | {"ACTION_NEEDS_HUMAN_APPROVAL"}


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
    # --- paramètres v1 (policy_v1.yaml) — None/vides = règle SKIPPED (legacy) ---
    intent_ttl: timedelta | None = None            # P9
    clock_skew: timedelta = CLOCK_SKEW_TOLERANCE   # P9
    asset_decimals: int | None = None              # P5 (anti-erreur de décimale)
    allowed_operations: frozenset = frozenset()    # P4 (noms d'opérations)
    allowed_targets: frozenset = frozenset()       # P4 (adresses normalisées)
    allowed_functions: frozenset = frozenset()     # P4 ((cible, sélecteur) normalisés)
    operation_calls: dict = field(default_factory=dict)  # P4 (action -> (cible, sélecteur))
    policy_version: str | None = None              # version du bundle (verdict)
    policy_hash: str | None = None                 # empreinte du bundle (verdict)


@dataclass
class PolicyState:
    """État externe fourni par l'appelant — requis si `state` est passé à evaluate().

    Fail-closed : « requis » signifie qu'un champ None/invalide **refuse**.
    Les champs marqués optionnels (None = non configuré) ne bloquent pas.
    """
    paused: bool | None = None                 # P11 (requis ; None = illisible)
    agent_member: bool | None = None           # P11 (requis ; None = illisible)
    envelope_status: str | None = None         # P12 (requis ; DRIFT/UNVERIFIED/None = refus)
    available_balance: float | None = None     # P7 (requis ; None = illisible)
    floor_balance: float | None = None         # P7 (optionnel : plancher de solde)
    exposure: float | None = None              # P7 (optionnel, avec exposure_cap)
    exposure_cap: float | None = None          # P7 (optionnel)
    budget_spent: float | None = None          # P14 (optionnel si budget_cap absent aussi)
    budget_cap: float | None = None            # P14


@dataclass
class PolicyDecision:
    verdict: str                    # ALLOW | DENY | REQUIRE_APPROVAL
    reasons: list = field(default_factory=list)
    rules_evaluated: list = field(default_factory=list)
    policy_version: str | None = None
    policy_hash: str | None = None
    safe_mode: bool = False         # vrai si ENVELOPE_DRIFT / ENVELOPE_UNVERIFIED

    def as_dict(self):
        payload = {"verdict": self.verdict, "reasons": self.reasons,
                   "rules_evaluated": self.rules_evaluated}
        if self.policy_version is not None:
            payload["policy_version"] = self.policy_version
        if self.policy_hash is not None:
            payload["policy_hash"] = self.policy_hash
        return payload


@dataclass
class PolicyBundle:
    """`policy_v1.yaml` chargé : paramètres + identité (version + empreintes)."""
    config: PolicyConfig
    data: dict
    version: str
    yaml_sha256: str
    code_sha256: str
    policy_hash: str


def _norm(addr: str) -> str:
    return (addr or "").strip().lower()


def _finite_number(value) -> bool:
    """True for a real, finite number (bool excluded).

    NaN and infinities must never reach the cap comparisons: in floating
    point, ``float('nan') > 100`` and ``float('nan') <= 100`` are both False,
    so a NaN amount would silently pass the caps (review finding F07).
    """
    return isinstance(value, (int, float)) and not isinstance(value, bool) \
        and math.isfinite(value)


def _aware(moment: datetime) -> datetime:
    """Utc-aware datetime; naive values are read as UTC (documented choice)."""
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def _base_units(amount: float, decimals: int | None) -> Optional[int]:
    """Montant en unités de base du jeton, ou None si non exactement représentable."""
    if decimals is None or not _finite_number(amount):
        return None
    scaled = amount * (10 ** decimals)
    nearest = round(scaled)
    if abs(scaled - nearest) > 1e-6:
        return None
    return int(nearest)


def intent_fingerprint(intent: Intent, decimals: int | None = None) -> str:
    """Empreinte du contenu canonique de l'intent (P10) — indépendante de intent_id.

    Couvre action, chaîne, actif, destinataire et montant (en unités de base
    quand les décimales sont connues) : le même contenu opérationnel re-soumis
    avec un nouvel identifiant est détecté.
    """
    payload = {
        "action": intent.action,
        "chain_id": intent.chain_id,
        "asset": _norm(intent.asset),
        "recipient": _norm(intent.recipient),
    }
    units = _base_units(intent.amount, decimals)
    payload["amount_base_units"] = units if units is not None else ("float:" + repr(intent.amount))
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _policy_code_sha256() -> str:
    """Empreinte du code du module politique (sémantique) — §5.5.3."""
    here = os.path.dirname(os.path.abspath(__file__))
    parts = []
    for name in ("__init__.py", "miniyaml.py"):
        with open(os.path.join(here, name), "rb") as handle:
            parts.append(handle.read())
    return hashlib.sha256(b"|".join(parts)).hexdigest()


def load_policy(path, recipients: Optional[dict] = None) -> PolicyBundle:
    """Charge `policy_v1.yaml` — source de vérité des paramètres (DOC2 §5.5.3).

    `recipients` : table label → adresse (résolution des destinataires de démo,
    le fichier ne contient jamais d'adresse de session). Les entrées du fichier
    qui sont déjà des adresses `0x…` sont acceptées telles quelles.
    """
    data = _load_yaml_file(path)
    if not isinstance(data, dict):
        raise MiniYamlError("policy_v1.yaml doit être un mapping")
    version = str(data.get("policy_version") or "").strip()
    if not version:
        raise MiniYamlError("policy_v1.yaml : 'policy_version' manquant")

    chains = data.get("chain_ids") or ([data["chain_id"]] if data.get("chain_id") is not None else [])
    if not chains:
        raise MiniYamlError("policy_v1.yaml : aucune chaîne autorisée")
    assets = data.get("assets") or ([data["asset"]] if data.get("asset") else [])
    if not assets:
        raise MiniYamlError("policy_v1.yaml : aucun actif autorisé")

    resolved, unresolved = set(), []
    for entry in (data.get("recipients") or []):
        candidate = None
        if isinstance(entry, str) and len(entry) == 42 and entry.startswith("0x"):
            candidate = entry
        elif isinstance(entry, str) and recipients:
            candidate = recipients.get(entry)
        if candidate:
            resolved.add(_norm(candidate))
        else:
            unresolved.append(entry)

    operations, targets, functions, calls = set(), set(), set(), {}
    for entry in (data.get("functions") or []):
        if not isinstance(entry, dict):
            raise MiniYamlError("policy_v1.yaml : 'functions' attend des mappings")
        operation = str(entry.get("operation") or "").strip()
        target = _norm(str(entry.get("target") or ""))
        selector = str(entry.get("selector") or "").strip().lower()
        if not operation or not target or not selector:
            raise MiniYamlError("policy_v1.yaml : entrée 'functions' incomplète (operation/target/selector)")
        operations.add(operation)
        targets.add(target)
        functions.add((target, selector))
        calls[operation] = (target, selector)

    config = PolicyConfig(
        allowed_chain_ids=frozenset(int(c) for c in chains),
        allowed_assets=frozenset(_norm(a) for a in assets),
        allowed_recipients=frozenset(resolved),
        max_per_tx=float(str(data.get("max_per_tx", MAX_PER_TX))),
        max_cumulative=float(str(data.get("max_cumulative_24h", MAX_CUMULATIVE))),
        intent_ttl=(timedelta(minutes=int(data["ttl_intent_minutes"]))
                    if data.get("ttl_intent_minutes") is not None else None),
        clock_skew=timedelta(seconds=int(data.get("clock_skew_seconds",
                                                  int(CLOCK_SKEW_TOLERANCE.total_seconds())))),
        asset_decimals=(int(data["asset_decimals"])
                        if data.get("asset_decimals") is not None else None),
        allowed_operations=frozenset(operations),
        allowed_targets=frozenset(targets),
        allowed_functions=frozenset(functions),
        operation_calls=dict(calls),
        policy_version=version,
    )

    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    yaml_sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    code_sha = _policy_code_sha256()
    bundle_hash = hashlib.sha256((yaml_sha + ":" + code_sha).encode("utf-8")).hexdigest()
    config.policy_hash = bundle_hash
    bundle = PolicyBundle(config=config, data=data, version=version,
                          yaml_sha256=yaml_sha, code_sha256=code_sha, policy_hash=bundle_hash)
    if unresolved:
        bundle.data = dict(data, _unresolved_recipients=list(unresolved))
    return bundle


def evaluate(intent: Intent, config: PolicyConfig, now: datetime | None = None,
             seen_intent_ids: Iterable[str] = (), cumulative_spent: float = 0.0,
             state: Optional[PolicyState] = None,
             seen_intent_hashes: Iterable[str] = ()) -> PolicyDecision:
    """Rend le verdict déterministe pour un intent donné (14 règles applicables).

    `state` : instantané d'état externe (P7/P11/P12/P14). S'il est fourni, les
    champs requis doivent être lisibles — sinon refus (fail-closed).
    `seen_intent_hashes` : empreintes déjà traitées (P10, dédup par contenu).
    """
    now = _aware(now or datetime.now(timezone.utc))
    reasons, evaluated = [], []

    def fail(rule, code, note=""):
        entry = {"rule": rule, "result": "FAIL", "code": code}
        if note:
            entry["note"] = note
        evaluated.append(entry)
        reasons.append(code)

    def ok(rule, note=""):
        evaluated.append({"rule": rule, "result": "OK", "note": note})

    def skip(rule, note):
        evaluated.append({"rule": rule, "result": "SKIPPED", "note": note})

    def decision():
        return PolicyDecision("DENY" if reasons else "ALLOW", list(reasons), evaluated,
                              policy_version=config.policy_version,
                              policy_hash=config.policy_hash,
                              safe_mode=any(code in SAFE_MODE_CODES for code in reasons))

    # P13 (pré-politique) — périmètre d'action : action inconnue -> refus net
    if intent.action not in ACTIONS_AUTONOMES and intent.action not in ACTIONS_SOUS_APPROBATION:
        fail("P13-action", "ACTION_UNKNOWN")
        return PolicyDecision("DENY", list(reasons), evaluated,
                              policy_version=config.policy_version,
                              policy_hash=config.policy_hash)

    # P1 — chaîne autorisée
    if intent.chain_id in config.allowed_chain_ids:
        ok("P1-chain", str(intent.chain_id))
    else:
        fail("P1-chain", "CHAIN_NOT_ALLOWED")
    if reasons:
        return PolicyDecision("DENY", list(reasons), evaluated,
                              policy_version=config.policy_version,
                              policy_hash=config.policy_hash)

    # P2 — actif autorisé
    if _norm(intent.asset) not in {_norm(a) for a in config.allowed_assets}:
        fail("P2-asset", "ASSET_NOT_ALLOWED")
    else:
        ok("P2-asset")

    # P3 — destinataire autorisé
    if _norm(intent.recipient) not in {_norm(r) for r in config.allowed_recipients}:
        fail("P3-recipient", "RECIPIENT_NOT_ALLOWED")
    else:
        ok("P3-recipient")

    # P4 — fonction scopée (registre v1 : opérations + paires (cible, sélecteur))
    if not (config.allowed_operations or config.allowed_functions or config.operation_calls):
        skip("P4-function", "registre de fonctions non configuré (legacy)")
    else:
        mapping = config.operation_calls.get(intent.action)
        if mapping is None and intent.action in ACTIONS_SOUS_APPROBATION:
            # action sous approbation : pas d'appel on-chain v1 — P13 tranchera
            skip("P4-function", "action sous approbation — pas d'appel direct en v1")
        elif mapping is None:
            fail("P4-function", "OPERATION_NOT_ALLOWED",
                 f"opération {intent.action} absente du registre actif")
        else:
            target, selector = mapping
            operation_ok = (not config.allowed_operations) or (intent.action in config.allowed_operations)
            if not operation_ok:
                fail("P4-function", "OPERATION_NOT_ALLOWED")
            elif target not in {_norm(t) for t in config.allowed_targets}:
                fail("P4-function", "TARGET_NOT_ALLOWED")
            elif (target, selector) not in {(t, s) for (t, s) in config.allowed_functions}:
                fail("P4-function", "FUNCTION_NOT_ALLOWED")
            else:
                ok("P4-function", f"{intent.action} -> ({target}, {selector})")

    # P5 — plafond par transaction (fini d'abord ; puis décimales ; puis plafond)
    if not _finite_number(intent.amount):
        fail("P5-amount", "AMOUNT_NOT_FINITE")
    elif intent.amount <= 0:
        fail("P5-amount", "AMOUNT_INVALID")
    elif config.asset_decimals is not None and _base_units(intent.amount, config.asset_decimals) is None:
        fail("P5-amount", "AMOUNT_INVALID",
             f"montant non exactement représentable en unités de base ({config.asset_decimals} décimales)")
    elif intent.amount > config.max_per_tx:
        fail("P5-amount", "AMOUNT_ABOVE_TX_CAP")
    else:
        ok("P5-amount", f"{intent.amount} <= {config.max_per_tx}")

    # P6 — cumul glissant (le verrou strict de la frontière de période)
    if not _finite_number(cumulative_spent) or cumulative_spent < 0:
        fail("P6-cumulative", "CUMULATIVE_INVALID")
    elif not _finite_number(intent.amount):
        evaluated.append({"rule": "P6-cumulative", "result": "SKIPPED",
                          "note": "montant non fini (voir P5-amount)"})
    elif cumulative_spent + max(intent.amount, 0) > config.max_cumulative:
        fail("P6-cumulative", "AMOUNT_ABOVE_PERIOD_CAP")
    else:
        ok("P6-cumulative", f"{cumulative_spent + max(intent.amount, 0)} <= {config.max_cumulative}")

    # P7 — exposition / solde (état requis si `state` fourni)
    if state is None:
        skip("P7-exposure", "state non fourni (appel legacy)")
    else:
        balance = state.available_balance
        if balance is None or not _finite_number(balance):
            fail("P7-exposure", "BALANCE_UNREADABLE")
        elif not _finite_number(intent.amount):
            skip("P7-exposure", "montant non fini (voir P5-amount)")
        else:
            if intent.amount > balance:
                fail("P7-exposure", "BALANCE_INSUFFICIENT")
            elif state.floor_balance is not None and _finite_number(state.floor_balance) \
                    and (balance - intent.amount) < state.floor_balance:
                fail("P7-exposure", "FLOOR_BREACH")
            elif state.exposure_cap is not None:
                if state.exposure is None or not _finite_number(state.exposure) \
                        or not _finite_number(state.exposure_cap):
                    fail("P7-exposure", "BALANCE_UNREADABLE", "exposition illisible")
                elif state.exposure + intent.amount > state.exposure_cap:
                    fail("P7-exposure", "EXPOSURE_ABOVE_CAP")
                else:
                    ok("P7-exposure", f"solde {balance}; exposition {state.exposure} + {intent.amount} <= {state.exposure_cap}")
            else:
                ok("P7-exposure", f"solde {balance} (plancher/exposition non configurés)")

    # P8 — permission (mandat) active
    if config.permission_expires_at is None:
        fail("P8-permission", "PERMISSION_MISSING")
    elif now >= config.permission_expires_at:
        fail("P8-permission", "PERMISSION_EXPIRED")
    else:
        ok("P8-permission", config.permission_expires_at.isoformat())

    # P9 — fraîcheur de l'intention
    if config.intent_ttl is None:
        skip("P9-freshness", "TTL d'intention non configuré (legacy)")
    else:
        created = _aware(intent.created_at)
        age = now - created
        if age > config.intent_ttl:
            fail("P9-freshness", "INTENT_STALE", f"âge {age} > TTL {config.intent_ttl}")
        elif -age > config.clock_skew:
            fail("P9-freshness", "INTENT_NOT_YET_VALID",
                 f"horodatage futur de {-age} > tolérance {config.clock_skew}")
        else:
            ok("P9-freshness", f"âge {age}")

    # P10 — idempotence (identifiant OU empreinte de contenu)
    seen_ids = set(seen_intent_ids)
    seen_hashes = set(seen_intent_hashes)
    fingerprint = intent_fingerprint(intent, config.asset_decimals)
    if intent.intent_id in seen_ids:
        fail("P10-idempotency", "INTENT_ALREADY_PROCESSED", "identifiant déjà vu")
    elif fingerprint in seen_hashes:
        fail("P10-idempotency", "INTENT_ALREADY_PROCESSED", "empreinte de contenu déjà vue")
    else:
        ok("P10-idempotency")

    # P11 — pause / kill switch (état requis si `state` fourni)
    if state is None:
        skip("P11-pause", "state non fourni (appel legacy)")
    else:
        if state.paused is None:
            fail("P11-pause", "PAUSED", "état de pause illisible — fail closed")
        elif state.paused:
            fail("P11-pause", "PAUSED")
        elif state.agent_member is None:
            fail("P11-pause", "AGENT_NOT_MEMBER", "appartenance au rôle illisible — fail closed")
        elif not state.agent_member:
            fail("P11-pause", "AGENT_NOT_MEMBER")
        else:
            ok("P11-pause")

    # P12 — alignement d'enveloppe (SAFE MODE)
    if state is None:
        skip("P12-envelope", "state non fourni (appel legacy)")
    else:
        status = str(state.envelope_status or "").strip().upper()
        if status == ENVELOPE_DRIFT:
            fail("P12-envelope", "ENVELOPE_DRIFT")
        elif status != ENVELOPE_PASS:
            fail("P12-envelope", "ENVELOPE_UNVERIFIED",
                 f"statut d'enveloppe {status or 'absent'} (SAFE MODE)")
        else:
            ok("P12-envelope")

    # P14 — budget de décision (optionnel : None/None = non configuré)
    if state is None:
        skip("P14-budget", "state non fourni (appel legacy)")
    elif state.budget_spent is None and state.budget_cap is None:
        skip("P14-budget", "budget de décision non configuré")
    else:
        spent, cap = state.budget_spent, state.budget_cap
        if spent is None or cap is None or not _finite_number(spent) or not _finite_number(cap) \
                or spent < 0 or cap <= 0:
            fail("P14-budget", "BUDGET_UNREADABLE")
        elif spent >= cap:
            fail("P14-budget", "BUDGET_EXCEEDED", f"{spent} >= {cap}")
        else:
            ok("P14-budget", f"{spent} < {cap}")

    if reasons:
        return decision()

    # P13 (verdict) — action connue hors périmètre autonome : toujours revue humaine
    if intent.action in ACTIONS_SOUS_APPROBATION:
        evaluated.append({"rule": "P13-action", "result": "REQUIRE_APPROVAL",
                          "code": "ACTION_NEEDS_HUMAN_APPROVAL"})
        return PolicyDecision("REQUIRE_APPROVAL", ["ACTION_NEEDS_HUMAN_APPROVAL"], evaluated,
                              policy_version=config.policy_version,
                              policy_hash=config.policy_hash)

    evaluated.append({"rule": "P13-action", "result": "OK", "note": intent.action})
    return PolicyDecision("ALLOW", [], evaluated,
                          policy_version=config.policy_version,
                          policy_hash=config.policy_hash)


def default_config(reserve_recipient: str, ttl_hours: int = 24,
                   now: datetime | None = None) -> PolicyConfig:
    """Configuration de démonstration : une chaîne, un actif, un destinataire, une échéance."""
    now = now or datetime.now(timezone.utc)
    return PolicyConfig(
        allowed_recipients=frozenset({_norm(reserve_recipient)}),
        permission_expires_at=now + timedelta(hours=ttl_hours),
    )
