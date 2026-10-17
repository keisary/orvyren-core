"""Relation catalogue: machine-verifiable enum of the 34 relation kinds.

Source of truth
---------------
``B2_GRAPHE_ETUDE.md`` §3.0–§3.3 (archive ``D:/orvyren_archive_2026-10-15/``):
34 relation kinds in 4 families, with allowed subject/object node kinds,
direction, transitivity and a one-line semantics. The catalogue is the piece
ORVYREN produces (no public DeFi relation catalogue was found — B2 §3.3), so
the enums here are normative for every relation record.

Node kinds
----------
``NodeKind`` mixes the 9 node classes of B2 §3.0 (``ORGANISATION``, ``ACTIF``,
``CONTRAT``, ``ADRESSE``, ``CHAINE``, ``UNITE``, ``PREUVE``, ``DECISION``,
``GOUVERNANCE``) with the concrete kinds named by the catalogue cells
(``STABLECOIN``, ``OBSERVATION``, ``SAFE`` …). ``KIND_CLASS`` maps every
concrete kind to its class (a class maps to itself).

Subject/object tokens
---------------------
A ``RelationSpec`` lists allowed tokens, not raw kinds. ``token_matches``
accepts a kind when the token is the kind itself, its class, a wildcard
(``ENTITE``, ``SUJET``, ``CIBLE``) or a declared role set (``AUTORITE``,
``DROIT``). Rendering choices for the few catalogue cells that name things
absent from the B2 node table are marked ``# mapping note`` below:
``"Token"`` → ``ACTIF``, ``"Protocol"`` → its own kind ``PROTOCOLE``,
``"Verifier configuration"`` → ``CONFIG_VERIF``,
``"Institution"`` → ``INSTITUTION``.

Standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, Mapping, Tuple

__all__ = [
    "FAMILIES",
    "FAMILY_PROOF",
    "FAMILY_STRUCTURE",
    "FAMILY_MECHANISM",
    "FAMILY_CONSTRAINT",
    "NodeKind",
    "KIND_CLASS",
    "WILDCARDS",
    "ROLE_SETS",
    "token_matches",
    "DIRECTED",
    "SYMMETRIC",
    "RelationSpec",
    "RELATION_CATALOG",
    "catalog_stats",
    "SIGN_PRIOR",
    "EPISTEMIC_STATUS",
    "LIFECYCLE",
    "VALIDATION_STATUS",
    "EXTRACT_METHOD",
    "MECHANISM_LABELS",
]

# --------------------------------------------------------------------------
# Families (B2 §3.1) — four golden-rule families.
# --------------------------------------------------------------------------
FAMILY_PROOF = "PROOF_DERIVATION"          # 1. Proof and derivation (8)
FAMILY_STRUCTURE = "STRUCTURE_EXPOSURE"    # 2. Structure and exposure (15)
FAMILY_MECHANISM = "ECONOMIC_MECHANISM"    # 3. Economic mechanism (3)
FAMILY_CONSTRAINT = "CONSTRAINT_PERMISSION"  # 4. Constraint and permission (8)

FAMILIES: Tuple[str, ...] = (
    FAMILY_PROOF,
    FAMILY_STRUCTURE,
    FAMILY_MECHANISM,
    FAMILY_CONSTRAINT,
)

# --------------------------------------------------------------------------
# Node kinds (B2 §3.0 table) + kinds named by catalogue cells.
# --------------------------------------------------------------------------
class NodeKind:
    """String constants for node kinds (plain strings: records serialise)."""

    # Classes (B2 §3.0).
    ORGANISATION = "ORGANISATION"   # issuer, DAO, company, custodian, regulator
    ACTIF = "ACTIF"                 # stablecoin, LST, lending token, LP, share
    CONTRAT = "CONTRAT"             # market, pool, bridge/OApp, oracle, module, Safe
    ADRESSE = "ADRESSE"             # treasury, EOA, multisig
    CHAINE = "CHAINE"
    UNITE = "UNITE"                 # USD, ETH, index
    PREUVE = "PREUVE"               # Source, Observation, Claim, Document, ExtractionRun
    DECISION = "DECISION"           # Hypothesis, Branch, Decision, Intent, Execution, Outcome
    GOUVERNANCE = "GOUVERNANCE"     # Role, Permission, Timelock
    # Organisation members.
    EMETTEUR = "EMETTEUR"
    DAO = "DAO"
    SOCIETE = "SOCIETE"
    DEPOSITAIRE = "DEPOSITAIRE"
    REGULATEUR = "REGULATEUR"
    # Asset members.
    STABLECOIN = "STABLECOIN"
    LST = "LST"
    TOKEN_PRET = "TOKEN_PRET"
    LP = "LP"
    PART = "PART"
    # Contract members.
    MARCHE = "MARCHE"               # e.g. Aave reserve
    POOL = "POOL"
    PONT_OAPP = "PONT_OAPP"
    ORACLE_FEED = "ORACLE_FEED"
    MODULE = "MODULE"
    SAFE = "SAFE"
    FACILITE = "FACILITE"           # mapping note: "Facility" (2.6)
    PROTOCOLE = "PROTOCOLE"         # mapping note: "Protocol" (2.12, 4.7)
    # Address members.
    TRESORERIE = "TRESORERIE"
    EOA = "EOA"
    MULTISIG = "MULTISIG"
    # Proof members.
    SOURCE = "SOURCE"
    OBSERVATION = "OBSERVATION"
    CLAIM = "CLAIM"
    DOCUMENT = "DOCUMENT"
    EXTRACTION_RUN = "EXTRACTION_RUN"
    # Decision members.
    HYPOTHESE = "HYPOTHESE"
    BRANCHE = "BRANCHE"
    DECISION_NODE = "DECISION_NODE"
    INTENT = "INTENT"
    EXECUTION = "EXECUTION"
    OUTCOME = "OUTCOME"
    # Governance members.
    ROLE = "ROLE"
    PERMISSION = "PERMISSION"
    TIMELOCK = "TIMELOCK"
    # Structural kinds named by catalogue cells.
    RELATION = "RELATION"           # subject of EXTRACTED_FROM / DERIVED_FROM
    CLASSE = "CLASSE"               # object of IS_A
    DETTE = "DETTE"                 # object of OWES / COLLATERALIZES
    POSITION = "POSITION"           # subject of OWES
    PARAMETRE = "PARAMETRE"         # subject of CONSTRAINS
    REGLE = "REGLE"                 # subject of CONSTRAINS
    INSTITUTION = "INSTITUTION"     # mapping note: "Institution" (4.1)
    ACTION = "ACTION"               # object of CONSTRAINS
    VARIABLE = "VARIABLE"           # cause/effect of AFFECTS
    INSTRUMENT = "INSTRUMENT"       # cause/effect of AFFECTS
    DROIT = "DROIT"                 # object of REVOKES
    FONCTION = "FONCTION"           # object of ALLOWS
    CONFIG_VERIF = "CONFIG_VERIF"   # mapping note: "Verifier configuration" (2.14)
    REGIME_LICENCE = "REGIME_LICENCE"  # object of REGULATED_BY


#: Every declared node kind.
NODE_KINDS: FrozenSet[str] = frozenset(getattr(NodeKind, name) for name in dir(NodeKind)
                                       if name.isupper())

#: Concrete kind -> node class (a class maps to itself).
KIND_CLASS: Dict[str, str] = {
    NodeKind.EMETTEUR: NodeKind.ORGANISATION,
    NodeKind.DAO: NodeKind.ORGANISATION,
    NodeKind.SOCIETE: NodeKind.ORGANISATION,
    NodeKind.DEPOSITAIRE: NodeKind.ORGANISATION,
    NodeKind.REGULATEUR: NodeKind.ORGANISATION,
    NodeKind.STABLECOIN: NodeKind.ACTIF,
    NodeKind.LST: NodeKind.ACTIF,
    NodeKind.TOKEN_PRET: NodeKind.ACTIF,
    NodeKind.LP: NodeKind.ACTIF,
    NodeKind.PART: NodeKind.ACTIF,
    NodeKind.MARCHE: NodeKind.CONTRAT,
    NodeKind.POOL: NodeKind.CONTRAT,
    NodeKind.PONT_OAPP: NodeKind.CONTRAT,
    NodeKind.ORACLE_FEED: NodeKind.CONTRAT,
    NodeKind.MODULE: NodeKind.CONTRAT,
    NodeKind.SAFE: NodeKind.CONTRAT,
    NodeKind.FACILITE: NodeKind.CONTRAT,
    NodeKind.TRESORERIE: NodeKind.ADRESSE,
    NodeKind.EOA: NodeKind.ADRESSE,
    NodeKind.MULTISIG: NodeKind.ADRESSE,
    NodeKind.SOURCE: NodeKind.PREUVE,
    NodeKind.OBSERVATION: NodeKind.PREUVE,
    NodeKind.CLAIM: NodeKind.PREUVE,
    NodeKind.DOCUMENT: NodeKind.PREUVE,
    NodeKind.EXTRACTION_RUN: NodeKind.PREUVE,
    NodeKind.HYPOTHESE: NodeKind.DECISION,
    NodeKind.BRANCHE: NodeKind.DECISION,
    NodeKind.DECISION_NODE: NodeKind.DECISION,
    NodeKind.INTENT: NodeKind.DECISION,
    NodeKind.EXECUTION: NodeKind.DECISION,
    NodeKind.OUTCOME: NodeKind.DECISION,
    NodeKind.ROLE: NodeKind.GOUVERNANCE,
    NodeKind.PERMISSION: NodeKind.GOUVERNANCE,
    NodeKind.TIMELOCK: NodeKind.GOUVERNANCE,
}
for _kind in NODE_KINDS:
    KIND_CLASS.setdefault(_kind, _kind)

#: Wildcard tokens: any node kind is accepted ("any entity" of B2 §3.0 for
#: SUPERSEDES/SAME_AS, and the generic placeholders "Subject", "Target").
WILDCARDS: FrozenSet[str] = frozenset({"TOUT", "SUJET", "CIBLE"})

#: Role tokens: a kind matches when it plays that role. ``ENTITE`` is an
#: *economic* entity of the world layer (B2 §3.0: organisation, asset, contract,
#: address, chain) — a claim or a hypothesis is NOT an entity here; the
#: revision/alias rules that apply to any object use the ``TOUT`` wildcard.
#: Authority = an organisation or a control/governance address.
_ECONOMIC_CLASSES = frozenset({
    NodeKind.ORGANISATION, NodeKind.ACTIF, NodeKind.CONTRAT, NodeKind.ADRESSE,
})
_ECONOMIC_KINDS = frozenset(
    kind for kind in NODE_KINDS if KIND_CLASS.get(kind) in _ECONOMIC_CLASSES
) | {NodeKind.CHAINE, NodeKind.PROTOCOLE, NodeKind.POSITION, NodeKind.DETTE,
     NodeKind.INSTITUTION}

ROLE_SETS: Mapping[str, FrozenSet[str]] = {
    "ENTITE": _ECONOMIC_KINDS,
    "AUTORITE": frozenset({
        NodeKind.ORGANISATION, NodeKind.EMETTEUR, NodeKind.DAO, NodeKind.SOCIETE,
        NodeKind.DEPOSITAIRE, NodeKind.REGULATEUR, NodeKind.INSTITUTION,
        NodeKind.SAFE, NodeKind.MULTISIG, NodeKind.TIMELOCK, NodeKind.ROLE,
    }),
    "DROIT": frozenset({NodeKind.PERMISSION, NodeKind.ROLE}),
}


def token_matches(token: str, kind: str) -> bool:
    """True when a node ``kind`` is accepted by an allowed ``token``."""
    if token in WILDCARDS:
        return True
    if token == kind:
        return True
    if KIND_CLASS.get(kind) == token:
        return True
    return kind in ROLE_SETS.get(token, frozenset())


# --------------------------------------------------------------------------
# Relation spec (one catalogue row).
# --------------------------------------------------------------------------
DIRECTED = "DIRECTED"
SYMMETRIC = "SYMMETRIC"

TRANSITIVITY_N = "N"   # non-transitive
TRANSITIVITY_T = "T"   # transitive
TRANSITIVITY_Q = "Q"   # quasi-transitive, bounded (never a bare closure)


@dataclass(frozen=True)
class RelationSpec:
    """One row of the B2 §3.2 catalogue (machine-checkable)."""

    ref: str                 # catalogue row, ex. "2.11"
    kind: str                # relation kind, ex. "COLLATERALIZES"
    family: str              # one of FAMILIES
    subjects: FrozenSet[str]  # allowed subject tokens
    objects: FrozenSet[str]   # allowed object tokens
    direction: str           # DIRECTED | SYMMETRIC
    transitivity: str        # N | T | Q
    semantics: str           # one-line semantics (English rendering of B2 §3.2)
    origin: str              # "M" MIMIR/RC, "D" DeFi/on-chain, "N" new (B2 §3.3)
    origin_detail: str       # origin cell of B2 §3.2 (English rendering)


def _spec(ref: str, kind: str, family: str, subjects: Tuple[str, ...],
          objects: Tuple[str, ...], direction: str, transitivity: str,
          semantics: str, origin: str, origin_detail: str) -> RelationSpec:
    return RelationSpec(ref=ref, kind=kind, family=family,
                        subjects=frozenset(subjects), objects=frozenset(objects),
                        direction=direction, transitivity=transitivity,
                        semantics=semantics, origin=origin,
                        origin_detail=origin_detail)


_SPECS: Tuple[RelationSpec, ...] = (
    # ---- Family 1 — Proof and derivation (8) ------------------------------
    _spec("1.1", "OBSERVED_FROM", FAMILY_PROOF, ("OBSERVATION",), ("SOURCE",),
          DIRECTED, TRANSITIVITY_N,
          "The measurement comes from this source (endpoint, retrieval timestamp, limits).",
          "M", "M (MIMIR chain §10.5)"),
    _spec("1.2", "EXTRACTED_FROM", FAMILY_PROOF, ("CLAIM", "RELATION"),
          ("DOCUMENT", "OBSERVATION"), DIRECTED, TRANSITIVITY_N,
          "The element was extracted from this document/passage (offsets + versioned extraction run).",
          "M", "M (§10.5, Extraction)"),
    _spec("1.3", "DERIVED_FROM", FAMILY_PROOF, ("CLAIM", "RELATION"),
          ("OBSERVATION", "CLAIM"), DIRECTED, TRANSITIVITY_N,
          "Fact computed from parents through a versioned recipe.",
          "M", "M (RC DERIVED_FROM)"),
    _spec("1.4", "SUPPORTS", FAMILY_PROOF, ("CLAIM",), ("HYPOTHESE",),
          DIRECTED, TRANSITIVITY_N,
          "This finding supports this hypothesis — with no economic transmission whatsoever.",
          "M", "M (RC ; code `supports`)"),
    _spec("1.5", "REFUTES", FAMILY_PROOF, ("CLAIM",), ("HYPOTHESE",),
          DIRECTED, TRANSITIVITY_N,
          "This finding refutes this hypothesis under a pre-declared criterion.",
          "N", "M (falsification) / N (explicit kind)"),
    _spec("1.6", "CONTRADICTS", FAMILY_PROOF, ("CLAIM",), ("CLAIM",),
          SYMMETRIC, TRANSITIVITY_N,
          "Two incompatible findings coexist (never merged) — a research signal.",
          "N", "M (§REQ-KNOW-003) / N (explicit kind)"),
    _spec("1.7", "SUPERSEDES", FAMILY_PROOF, ("TOUT",), ("TOUT",),
          DIRECTED, TRANSITIVITY_T,
          "The revision replaces the previous one without erasing it (reconstructibility).",
          "M", "M (§13.4) / code (revisions)"),
    _spec("1.8", "SAME_AS", FAMILY_PROOF, ("TOUT",), ("TOUT",),
          SYMMETRIC, TRANSITIVITY_N,
          "Resolved alias: two references = one canonical identity (dated, revisable decision).",
          "N", "M (§10.4) / N (explicit kind)"),
    # ---- Family 2 — Structure and exposure (15) --------------------------
    _spec("2.1", "IS_A", FAMILY_STRUCTURE, ("ENTITE", "ACTIF"), ("CLASSE",),
          DIRECTED, TRANSITIVITY_T,
          "Taxonomy (USDC IS_A stablecoin; rsETH IS_A LST) — serves class-based queries.",
          "N", "N"),
    _spec("2.2", "PART_OF", FAMILY_STRUCTURE, ("ENTITE", "CONTRAT"), ("ENTITE",),
          DIRECTED, TRANSITIVITY_T,
          "Structural membership (aEthUSDC PART_OF Aave V3; reserve PART_OF pool).",
          "N", "N"),
    _spec("2.3", "DEPLOYED_ON", FAMILY_STRUCTURE, ("CONTRAT", "ACTIF"), ("CHAINE",),
          DIRECTED, TRANSITIVITY_N,
          "Presence of a contract/issuance on this chain (multi-chain made explicit).",
          "D", "D"),
    _spec("2.4", "ISSUED_BY", FAMILY_STRUCTURE, ("ACTIF",), ("ORGANISATION",),
          DIRECTED, TRANSITIVITY_N,
          "The asset is issued by this entity.", "M", "M (RC)"),
    _spec("2.5", "TARGETS_PEG", FAMILY_STRUCTURE, ("ACTIF",), ("UNITE", "ACTIF"),
          DIRECTED, TRANSITIVITY_N,
          "Target parity (1 USD, 1 ETH) — a target, not a guarantee.", "D", "D"),
    _spec("2.6", "REDEEMABLE_VIA", FAMILY_STRUCTURE, ("ACTIF",),
          ("FACILITE", "CONTRAT"), DIRECTED, TRANSITIVITY_N,
          "Redemption/time-lock through this facility (delays and conditions in the payload).",
          "M", "M (RC)"),
    _spec("2.7", "CUSTODIED_AT", FAMILY_STRUCTURE, ("ACTIF",),
          ("DEPOSITAIRE", "CONTRAT"), DIRECTED, TRANSITIVITY_N,
          "The asset rests with this custodian (wrapping, PSM, escrow).", "M", "M (RC)"),
    _spec("2.8", "HOLDS", FAMILY_STRUCTURE, ("ADRESSE", "ENTITE"), ("ACTIF",),
          DIRECTED, TRANSITIVITY_N,
          "Holds N units at (chain, block); role: treasury / liquidity / collateral / custody.",
          "M", "M (RC)"),
    _spec("2.9", "OWES", FAMILY_STRUCTURE, ("POSITION", "ENTITE"), ("DETTE",),
          DIRECTED, TRANSITIVITY_N,
          "Owes N units on this market (liability exposure, rate, maturity).",
          "M", "M (RC)"),
    _spec("2.10", "DEPOSITED_IN", FAMILY_STRUCTURE, ("ACTIF",), ("MARCHE", "POOL"),
          DIRECTED, TRANSITIVITY_N,
          "Deposit into a market/protocol (Aave reserve, Curve pool) — an exposure path.",
          "D", "D"),
    _spec("2.11", "COLLATERALIZES", FAMILY_STRUCTURE, ("ACTIF",), ("DETTE", "MARCHE"),
          DIRECTED, TRANSITIVITY_N,
          "Serves as collateral for this debt on this market (LTV/LT parameters in the payload).",
          "D", "D"),
    _spec("2.12", "REHYPOTHECATED_TO", FAMILY_STRUCTURE, ("ACTIF",), ("PROTOCOLE",),
          DIRECTED, TRANSITIVITY_N,
          "The asset received is re-pledged/re-hypothecated to this protocol (chain of rights).",
          "D", "D"),
    _spec("2.13", "BRIDGED_VIA", FAMILY_STRUCTURE, ("ACTIF",), ("PONT_OAPP",),
          DIRECTED, TRANSITIVITY_N,
          "The issuance on this chain depends on this bridge (mint/burn, cross-chain invariant).",
          "D", "D"),
    _spec("2.14", "VERIFIED_BY", FAMILY_STRUCTURE, ("PONT_OAPP",), ("CONFIG_VERIF",),
          DIRECTED, TRANSITIVITY_N,
          "The bridge's security rests on these verifiers (count, DVN type).",
          "D", "D (KelpDAO case)"),
    _spec("2.15", "PRICED_BY", FAMILY_STRUCTURE, ("MARCHE", "ACTIF"), ("ORACLE_FEED",),
          DIRECTED, TRANSITIVITY_N,
          "Valuation backed by this feed (type, `description()`, heartbeat, cap).",
          "D", "D (W2B 1.3/4.1)"),
    # ---- Family 3 — Economic mechanism (3) -------------------------------
    _spec("3.1", "AFFECTS", FAMILY_MECHANISM, ("VARIABLE", "ENTITE", "INSTRUMENT"),
          ("VARIABLE", "ENTITE", "INSTRUMENT"), DIRECTED, TRANSITIVITY_Q,
          "Mechanism M transmits a change from Cause to Effect (sign, horizon, "
          "conditions, epistemic status).", "M", "M (§11.2 ; RC)"),
    _spec("3.2", "DEPENDS_ON", FAMILY_MECHANISM, ("ENTITE",), ("ENTITE",),
          DIRECTED, TRANSITIVITY_Q,
          "X depends economically on Y (channel + sensitivity in the payload).",
          "N", "M (§6.3 conditional) / N (explicit kind)"),
    _spec("3.3", "CORRELATES_WITH", FAMILY_MECHANISM, ("ENTITE",), ("ENTITE",),
          SYMMETRIC, TRANSITIVITY_N,
          "Observed statistical link — STATISTICAL status mandatory, never causal, never chained.",
          "N", "M (§0.3 labels) / N (explicit kind)"),
    # ---- Family 4 — Constraint and permission (8) ------------------------
    _spec("4.1", "CONSTRAINS", FAMILY_CONSTRAINT, ("PARAMETRE", "REGLE", "INSTITUTION"),
          ("MARCHE", "ACTIF", "ACTION"), DIRECTED, TRANSITIVITY_N,
          "Limits behaviour (supplyCap, LTV=0, freeze, timelock) — a dated state or parameter.",
          "M", "M (RC)"),
    _spec("4.2", "AUTHORIZES", FAMILY_CONSTRAINT, ("AUTORITE",), ("SUJET",),
          DIRECTED, TRANSITIVITY_N,
          "Grants a right to this subject (scope, instruments, dates, grant proof).",
          "M", "M (RC)"),
    _spec("4.3", "REVOKES", FAMILY_CONSTRAINT, ("AUTORITE",), ("DROIT", "SUJET"),
          DIRECTED, TRANSITIVITY_N,
          "Revokes a right (dated event: on-chain tx or decision).", "M", "M (RC)"),
    _spec("4.4", "MEMBER_OF", FAMILY_CONSTRAINT, ("ADRESSE",), ("ROLE",),
          DIRECTED, TRANSITIVITY_N,
          "Is a member of this role at (chain, block) — on-chain fact `AssignRoles`.",
          "D", "D (Zodiac ; W2C)"),
    _spec("4.5", "ALLOWS", FAMILY_CONSTRAINT, ("ROLE",), ("CIBLE", "FONCTION"),
          DIRECTED, TRANSITIVITY_N,
          "The role allows this target/function (allowlist, period allowances).",
          "D", "D (Zodiac)"),
    _spec("4.6", "ADMINISTERED_BY", FAMILY_CONSTRAINT, ("CONTRAT", "MODULE"),
          ("SAFE", "MULTISIG"), DIRECTED, TRANSITIVITY_N,
          "The contract's admin/owner is this address (`owner()`, module enabled).",
          "D", "D"),
    _spec("4.7", "GOVERNED_BY", FAMILY_CONSTRAINT, ("PROTOCOLE", "CONTRAT"),
          ("DAO", "TIMELOCK"), DIRECTED, TRANSITIVITY_N,
          "Parameters are governed by this instance (thresholds, delays).", "D", "D"),
    _spec("4.8", "REGULATED_BY", FAMILY_CONSTRAINT, ("ENTITE", "ACTIF"),
          ("REGIME_LICENCE",), DIRECTED, TRANSITIVITY_N,
          "Regulatory oversight (banks phase, out of the demo — table kept for the vision).",
          "D", "D (optional)"),
)

#: kind -> spec. The machine-verifiable catalogue.
RELATION_CATALOG: Mapping[str, RelationSpec] = {spec.kind: spec for spec in _SPECS}


def catalog_stats() -> Dict[str, int]:
    """Counts per family (B2 §3.2: 8 / 15 / 3 / 8 = 34)."""
    stats = {family: 0 for family in FAMILIES}
    for spec in _SPECS:
        stats[spec.family] += 1
    return stats


# --------------------------------------------------------------------------
# Record-level enums (B2 §3.0 record fields 5, 6, 8, 9, 10, 14).
# --------------------------------------------------------------------------
#: Field 6 — sign prior (MIMIR §11.2: "+ / − / ambigu").
SIGN_PRIOR: Tuple[str, ...] = ("+", "-", "ambigu")

#: Field 8 — epistemic status (MIMIR §0.3): what we believe we know.
EPISTEMIC_STATUS: Tuple[str, ...] = (
    "FACT", "REPORTED", "STATISTICAL", "CAUSAL-DOCUMENTED",
    "CAUSAL-HYPOTHESIS", "MODEL-INFERRED", "REJECTED",
)

#: Field 9 — lifecycle: where the relation stands in its own cycle.
LIFECYCLE: Tuple[str, ...] = (
    "DISCOVERED", "EVALUATING", "ACTIVE", "WEAKENING", "SUSPENDED", "REJECTED",
)

#: Field 10 — validation status: did it pass the validation gate.
VALIDATION_STATUS: Tuple[str, ...] = (
    "PENDING", "VALIDATED", "QUARANTINED", "REJECTED",
)

#: Field 14 — extraction method (RC §2.3).
EXTRACT_METHOD: Tuple[str, ...] = ("RULE", "ONCHAIN_READ", "LLM_EXTRACT", "HUMAN")

#: Field 5 — recommended mechanism labels (MIMIR §11.2). The catalogue cell is
#: open ("LIQUIDITY, REDEMPTION, …"), so records are checked for a non-empty
#: upper-case label only; this set is the documented v1 vocabulary.
MECHANISM_LABELS: FrozenSet[str] = frozenset({
    "LIQUIDITY", "REDEMPTION", "FUNDING", "PEG", "ORACLE", "CUSTODY", "GOVERNANCE",
})
