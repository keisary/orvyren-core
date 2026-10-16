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
``"Token"`` → ``ACTIF``, ``"Protocole"`` → its own kind ``PROTOCOLE``,
``"Configuration vérificateurs"`` → ``CONFIG_VERIF``,
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
FAMILY_PROOF = "PROOF_DERIVATION"          # 1. Preuve et dérivation (8)
FAMILY_STRUCTURE = "STRUCTURE_EXPOSURE"    # 2. Structure et exposition (15)
FAMILY_MECHANISM = "ECONOMIC_MECHANISM"    # 3. Mécanisme économique (3)
FAMILY_CONSTRAINT = "CONSTRAINT_PERMISSION"  # 4. Contrainte et permission (8)

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
    ORGANISATION = "ORGANISATION"   # émetteur, DAO, société, dépositaire, régulateur
    ACTIF = "ACTIF"                 # stablecoin, LST, token de prêt, LP, part
    CONTRAT = "CONTRAT"             # marché, pool, pont/OApp, oracle, module, Safe
    ADRESSE = "ADRESSE"             # trésorerie, EOA, multisig
    CHAINE = "CHAINE"
    UNITE = "UNITE"                 # USD, ETH, indice
    PREUVE = "PREUVE"               # Source, Observation, Claim, Document, ExtractionRun
    DECISION = "DECISION"           # Hypothèse, Branche, Décision, Intent, Exécution, Outcome
    GOUVERNANCE = "GOUVERNANCE"     # Rôle, Permission, Timelock
    # Organisation members.
    EMETTEUR = "EMETTEUR"
    DAO = "DAO"
    SOCIETE = "SOCIETE"
    DEPOSITAIRE = "DEPOSITAIRE"
    REGULATEUR = "REGULATEUR"
    # Actif members.
    STABLECOIN = "STABLECOIN"
    LST = "LST"
    TOKEN_PRET = "TOKEN_PRET"
    LP = "LP"
    PART = "PART"
    # Contrat members.
    MARCHE = "MARCHE"               # ex. réserve Aave
    POOL = "POOL"
    PONT_OAPP = "PONT_OAPP"
    ORACLE_FEED = "ORACLE_FEED"
    MODULE = "MODULE"
    SAFE = "SAFE"
    FACILITE = "FACILITE"           # mapping note: "Facilité" (2.6)
    PROTOCOLE = "PROTOCOLE"         # mapping note: "Protocole" (2.12, 4.7)
    # Adresse members.
    TRESORERIE = "TRESORERIE"
    EOA = "EOA"
    MULTISIG = "MULTISIG"
    # Preuve members.
    SOURCE = "SOURCE"
    OBSERVATION = "OBSERVATION"
    CLAIM = "CLAIM"
    DOCUMENT = "DOCUMENT"
    EXTRACTION_RUN = "EXTRACTION_RUN"
    # Décision members.
    HYPOTHESE = "HYPOTHESE"
    BRANCHE = "BRANCHE"
    DECISION_NODE = "DECISION_NODE"
    INTENT = "INTENT"
    EXECUTION = "EXECUTION"
    OUTCOME = "OUTCOME"
    # Gouvernance members.
    ROLE = "ROLE"
    PERMISSION = "PERMISSION"
    TIMELOCK = "TIMELOCK"
    # Structural kinds named by catalogue cells.
    RELATION = "RELATION"           # sujet de EXTRACTED_FROM / DERIVED_FROM
    CLASSE = "CLASSE"               # objet de IS_A
    DETTE = "DETTE"                 # objet de OWES / COLLATERALIZES
    POSITION = "POSITION"           # sujet de OWES
    PARAMETRE = "PARAMETRE"         # sujet de CONSTRAINS
    REGLE = "REGLE"                 # sujet de CONSTRAINS
    INSTITUTION = "INSTITUTION"     # mapping note: "Institution" (4.1)
    ACTION = "ACTION"               # objet de CONSTRAINS
    VARIABLE = "VARIABLE"           # cause/effet de AFFECTS
    INSTRUMENT = "INSTRUMENT"       # cause/effet de AFFECTS
    DROIT = "DROIT"                 # objet de REVOKES
    FONCTION = "FONCTION"           # objet de ALLOWS
    CONFIG_VERIF = "CONFIG_VERIF"   # mapping note: "Configuration vérificateurs" (2.14)
    REGIME_LICENCE = "REGIME_LICENCE"  # objet de REGULATED_BY


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

#: Wildcard tokens: any node kind is accepted ("toute entité" of B2 §3.0 for
#: SUPERSEDES/SAME_AS, and the generic placeholders "Sujet", "Cible").
WILDCARDS: FrozenSet[str] = frozenset({"TOUT", "SUJET", "CIBLE"})

#: Role tokens: a kind matches when it plays that role. ``ENTITE`` is an
#: *economic* entity of the world layer (B2 §3.0: organisation, actif, contrat,
#: adresse, chaîne) — a claim or a hypothesis is NOT an entity here; the
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
    semantics: str           # one-line semantics (French, from B2 §3.2)
    origin: str              # "M" MIMIR/RC, "D" DeFi/on-chain, "N" new (B2 §3.3)
    origin_detail: str       # verbatim origin cell of B2 §3.2


def _spec(ref: str, kind: str, family: str, subjects: Tuple[str, ...],
          objects: Tuple[str, ...], direction: str, transitivity: str,
          semantics: str, origin: str, origin_detail: str) -> RelationSpec:
    return RelationSpec(ref=ref, kind=kind, family=family,
                        subjects=frozenset(subjects), objects=frozenset(objects),
                        direction=direction, transitivity=transitivity,
                        semantics=semantics, origin=origin,
                        origin_detail=origin_detail)


_SPECS: Tuple[RelationSpec, ...] = (
    # ---- Famille 1 — Preuve et dérivation (8) -----------------------------
    _spec("1.1", "OBSERVED_FROM", FAMILY_PROOF, ("OBSERVATION",), ("SOURCE",),
          DIRECTED, TRANSITIVITY_N,
          "La mesure provient de cette source (endpoint, horodatage de récupération, limites).",
          "M", "M (chaîne MIMIR §10.5)"),
    _spec("1.2", "EXTRACTED_FROM", FAMILY_PROOF, ("CLAIM", "RELATION"),
          ("DOCUMENT", "OBSERVATION"), DIRECTED, TRANSITIVITY_N,
          "L'élément a été extrait de ce document/passage (offsets + run d'extraction versionné).",
          "M", "M (§10.5, Extraction)"),
    _spec("1.3", "DERIVED_FROM", FAMILY_PROOF, ("CLAIM", "RELATION"),
          ("OBSERVATION", "CLAIM"), DIRECTED, TRANSITIVITY_N,
          "Fait calculé à partir de parents, via une recette versionnée.",
          "M", "M (RC DERIVED_FROM)"),
    _spec("1.4", "SUPPORTS", FAMILY_PROOF, ("CLAIM",), ("HYPOTHESE",),
          DIRECTED, TRANSITIVITY_N,
          "Ce constat soutient cette hypothèse — sans aucune transmission économique.",
          "M", "M (RC ; code `supports`)"),
    _spec("1.5", "REFUTES", FAMILY_PROOF, ("CLAIM",), ("HYPOTHESE",),
          DIRECTED, TRANSITIVITY_N,
          "Ce constat réfute cette hypothèse selon un critère pré-déclaré.",
          "N", "M (falsification) / N (kind explicite)"),
    _spec("1.6", "CONTRADICTS", FAMILY_PROOF, ("CLAIM",), ("CLAIM",),
          SYMMETRIC, TRANSITIVITY_N,
          "Deux constats incompatibles coexistent (jamais fusionnés) — signal de recherche.",
          "N", "M (§REQ-KNOW-003) / N (kind explicite)"),
    _spec("1.7", "SUPERSEDES", FAMILY_PROOF, ("TOUT",), ("TOUT",),
          DIRECTED, TRANSITIVITY_T,
          "La révision remplace l'ancienne sans l'effacer (reconstruibilité).",
          "M", "M (§13.4) / code (révisions)"),
    _spec("1.8", "SAME_AS", FAMILY_PROOF, ("TOUT",), ("TOUT",),
          SYMMETRIC, TRANSITIVITY_N,
          "Alias résolu : deux références = une identité canonique (décision datée, révisable).",
          "N", "M (§10.4) / N (kind explicite)"),
    # ---- Famille 2 — Structure et exposition (15) ------------------------
    _spec("2.1", "IS_A", FAMILY_STRUCTURE, ("ENTITE", "ACTIF"), ("CLASSE",),
          DIRECTED, TRANSITIVITY_T,
          "Taxonomie (USDC IS_A stablecoin ; rsETH IS_A LST) — sert les requêtes par classe.",
          "N", "N"),
    _spec("2.2", "PART_OF", FAMILY_STRUCTURE, ("ENTITE", "CONTRAT"), ("ENTITE",),
          DIRECTED, TRANSITIVITY_T,
          "Appartenance structurelle (aEthUSDC PART_OF Aave V3 ; réserve PART_OF pool).",
          "N", "N"),
    _spec("2.3", "DEPLOYED_ON", FAMILY_STRUCTURE, ("CONTRAT", "ACTIF"), ("CHAINE",),
          DIRECTED, TRANSITIVITY_N,
          "Présence d'un contrat/émission sur cette chaîne (multi-chaînes explicite).",
          "D", "D"),
    _spec("2.4", "ISSUED_BY", FAMILY_STRUCTURE, ("ACTIF",), ("ORGANISATION",),
          DIRECTED, TRANSITIVITY_N,
          "L'actif est émis par cette entité.", "M", "M (RC)"),
    _spec("2.5", "TARGETS_PEG", FAMILY_STRUCTURE, ("ACTIF",), ("UNITE", "ACTIF"),
          DIRECTED, TRANSITIVITY_N,
          "Parité visée (1 USD, 1 ETH) — une cible, pas une garantie.", "D", "D"),
    _spec("2.6", "REDEEMABLE_VIA", FAMILY_STRUCTURE, ("ACTIF",),
          ("FACILITE", "CONTRAT"), DIRECTED, TRANSITIVITY_N,
          "Redemption/time-lock auprès de cette facilité (délais, conditions en payload).",
          "M", "M (RC)"),
    _spec("2.7", "CUSTODIED_AT", FAMILY_STRUCTURE, ("ACTIF",),
          ("DEPOSITAIRE", "CONTRAT"), DIRECTED, TRANSITIVITY_N,
          "L'actif repose chez ce dépositaire (wrapping, PSM, escrow).", "M", "M (RC)"),
    _spec("2.8", "HOLDS", FAMILY_STRUCTURE, ("ADRESSE", "ENTITE"), ("ACTIF",),
          DIRECTED, TRANSITIVITY_N,
          "Détient N unités à (chaîne, bloc) ; rôle : trésorerie / liquidité / collatéral / custody.",
          "M", "M (RC)"),
    _spec("2.9", "OWES", FAMILY_STRUCTURE, ("POSITION", "ENTITE"), ("DETTE",),
          DIRECTED, TRANSITIVITY_N,
          "Doit N unités sur ce marché (exposition au passif, taux, échéance).",
          "M", "M (RC)"),
    _spec("2.10", "DEPOSITED_IN", FAMILY_STRUCTURE, ("ACTIF",), ("MARCHE", "POOL"),
          DIRECTED, TRANSITIVITY_N,
          "Dépôt dans un marché/protocole (réserve Aave, pool Curve) — chemin d'exposition.",
          "D", "D"),
    _spec("2.11", "COLLATERALIZES", FAMILY_STRUCTURE, ("ACTIF",), ("DETTE", "MARCHE"),
          DIRECTED, TRANSITIVITY_N,
          "Sert de collatéral à cette dette sur ce marché (paramètres LTV/LT en payload).",
          "D", "D"),
    _spec("2.12", "REHYPOTHECATED_TO", FAMILY_STRUCTURE, ("ACTIF",), ("PROTOCOLE",),
          DIRECTED, TRANSITIVITY_N,
          "L'actif reçu est réengagé/ré-hypothéqué vers ce protocole (chaîne des droits).",
          "D", "D"),
    _spec("2.13", "BRIDGED_VIA", FAMILY_STRUCTURE, ("ACTIF",), ("PONT_OAPP",),
          DIRECTED, TRANSITIVITY_N,
          "L'émission sur cette chaîne dépend de ce pont (mint/burn, invariant inter-chaînes).",
          "D", "D"),
    _spec("2.14", "VERIFIED_BY", FAMILY_STRUCTURE, ("PONT_OAPP",), ("CONFIG_VERIF",),
          DIRECTED, TRANSITIVITY_N,
          "La sécurité du pont repose sur ces vérificateurs (nombre, type de DVN).",
          "D", "D (cas KelpDAO)"),
    _spec("2.15", "PRICED_BY", FAMILY_STRUCTURE, ("MARCHE", "ACTIF"), ("ORACLE_FEED",),
          DIRECTED, TRANSITIVITY_N,
          "Valorisation adossée à ce feed (type, `description()`, heartbeat, plafond).",
          "D", "D (W2B 1.3/4.1)"),
    # ---- Famille 3 — Mécanisme économique (3) ----------------------------
    _spec("3.1", "AFFECTS", FAMILY_MECHANISM, ("VARIABLE", "ENTITE", "INSTRUMENT"),
          ("VARIABLE", "ENTITE", "INSTRUMENT"), DIRECTED, TRANSITIVITY_Q,
          "Le mécanisme M transmet une variation de Cause vers Effet (signe, horizon, "
          "conditions, statut épistémique).", "M", "M (§11.2 ; RC)"),
    _spec("3.2", "DEPENDS_ON", FAMILY_MECHANISM, ("ENTITE",), ("ENTITE",),
          DIRECTED, TRANSITIVITY_Q,
          "X dépend économiquement de Y (canal + sensibilité en payload).",
          "N", "M (§6.3 conditionnel) / N (kind explicite)"),
    _spec("3.3", "CORRELATES_WITH", FAMILY_MECHANISM, ("ENTITE",), ("ENTITE",),
          SYMMETRIC, TRANSITIVITY_N,
          "Lien statistique constaté — statut STATISTICAL obligatoire, jamais causal, jamais chaîné.",
          "N", "M (§0.3 labels) / N (kind explicite)"),
    # ---- Famille 4 — Contrainte et permission (8) ------------------------
    _spec("4.1", "CONSTRAINS", FAMILY_CONSTRAINT, ("PARAMETRE", "REGLE", "INSTITUTION"),
          ("MARCHE", "ACTIF", "ACTION"), DIRECTED, TRANSITIVITY_N,
          "Limite le comportement (supplyCap, LTV=0, gel, timelock) — état ou paramètre daté.",
          "M", "M (RC)"),
    _spec("4.2", "AUTHORIZES", FAMILY_CONSTRAINT, ("AUTORITE",), ("SUJET",),
          DIRECTED, TRANSITIVITY_N,
          "Accorde un droit à ce sujet (périmètre, instruments, dates, preuve d'octroi).",
          "M", "M (RC)"),
    _spec("4.3", "REVOKES", FAMILY_CONSTRAINT, ("AUTORITE",), ("DROIT", "SUJET"),
          DIRECTED, TRANSITIVITY_N,
          "Révoque un droit (événement daté : tx on-chain ou décision).", "M", "M (RC)"),
    _spec("4.4", "MEMBER_OF", FAMILY_CONSTRAINT, ("ADRESSE",), ("ROLE",),
          DIRECTED, TRANSITIVITY_N,
          "Est membre de ce rôle à (chaîne, bloc) — fait on-chain `AssignRoles`.",
          "D", "D (Zodiac ; W2C)"),
    _spec("4.5", "ALLOWS", FAMILY_CONSTRAINT, ("ROLE",), ("CIBLE", "FONCTION"),
          DIRECTED, TRANSITIVITY_N,
          "Le rôle autorise cette cible/fonction (allowlist, allowances période).",
          "D", "D (Zodiac)"),
    _spec("4.6", "ADMINISTERED_BY", FAMILY_CONSTRAINT, ("CONTRAT", "MODULE"),
          ("SAFE", "MULTISIG"), DIRECTED, TRANSITIVITY_N,
          "L'admin/propriétaire du contrat est cette adresse (`owner()`, module enabled).",
          "D", "D"),
    _spec("4.7", "GOVERNED_BY", FAMILY_CONSTRAINT, ("PROTOCOLE", "CONTRAT"),
          ("DAO", "TIMELOCK"), DIRECTED, TRANSITIVITY_N,
          "Les paramètres sont gouvernés par cette instance (seuils, délais).", "D", "D"),
    _spec("4.8", "REGULATED_BY", FAMILY_CONSTRAINT, ("ENTITE", "ACTIF"),
          ("REGIME_LICENCE",), DIRECTED, TRANSITIVITY_N,
          "Encadrement réglementaire (phase banques, hors démo — table conservée pour la vision).",
          "D", "D (optionnel)"),
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
