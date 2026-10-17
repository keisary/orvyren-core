"""Hypothesis record (12 fields), 7-state lifecycle and the 5 transition rules.

Source of truth: ``B3_DECISION_ETUDE.md`` §a.3 (record), §a.4 (cycle), §a.5
(checklist) — archive ``D:/orvyren_archive_2026-10-15/``.

Record — 12 fields (§a.3): ``id`` (ULID, never reused), ``case_id``, ``enonce``
(one falsifiable sentence with mechanism and scope), ``criteres`` (>= 1 support
criterion S and **>= 1 refutation criterion R, mandatory**; each criterion =
predicate + threshold + admissible sources + window), ``preuves_pour`` and
``preuves_contre`` (both lists are maintained — neither may be left out),
``inconnues``, ``etat``, ``p`` (**never a number**: empty until frozen, then
the frozen label + freeze ref), ``histoire`` (append-only), ``provenance``
(logical author = role name), ``relations``.

Lifecycle — 7 states (§a.4):
``CREATED -> UNDER_TEST -> SUPPORTED | REFUTED | INCONCLUSIVE``;
``CREATED -> MERGED_INTO`` (validated merge, pointer to the retained record);
any state -> ``ARCHIVED`` (state, never a deletion); ``ARCHIVED -> UNDER_TEST``
(wake-up: same id, same history).

The 5 transition rules (§a.4) are enforced by :class:`HypothesisRegistry`:
1. SUPPORTED requires an explicitly satisfied S criterion, REFUTED an
   explicitly satisfied R one — otherwise INCONCLUSIVE, never a default state.
2. One transition per observation, journalised with its refs — no silent
   update (a ref may drive at most one transition).
3. ARCHIVED is not a deletion: the record and its history stay retrievable and
   a wake-up reuses the same id and history.
4. MERGED_INTO / SPLIT_FROM: a merge needs equivalent statements (validated
   semantic dedup; the deterministic path accepts exact duplicates only) and
   contradictions must stay visible (G7) — contradictory records cannot merge.
5. An ARCHIVED record can never satisfy a mandatory proof (REQ-LABEL): the
   state counts, not the history.

Standard library only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

__all__ = [
    "Criterion",
    "HistoryEntry",
    "HypothesisRecord",
    "HypothesisRegistry",
    "HYPOTHESIS_STATES",
    "HYPOTHESIS_FIELD_GROUPS",
    "HYPOTHESIS_FIELD_GROUP_COUNT",
    "P_LABELS",
    "ALLOWED_TRANSITIONS",
    "RELATION_LINK_KINDS",
    "TRANSITION_RULES",
    "validate_hypothesis",
    "record_to_dict",
    "record_from_dict",
]

# --------------------------------------------------------------------------
# Enums and constants (§a.3–§a.4).
# --------------------------------------------------------------------------
#: Field 8 — the 7 lifecycle states.
HYPOTHESIS_STATES: Tuple[str, ...] = (
    "CREATED", "UNDER_TEST", "SUPPORTED", "REFUTED", "INCONCLUSIVE",
    "MERGED_INTO", "ARCHIVED",
)

#: Field 9 — frozen probability labels. NEVER a number (numbers live only in
#: the calibration annex); ``None`` means empty (not frozen yet).
P_LABELS: Tuple[str, ...] = ("improbable", "possible", "probable")

#: Field 12 — allowed relation link kinds (B3 §a.3). MERGED_INTO / SPLIT_FROM
#: are registry-level links, outside the 34-kind graph catalogue of B2 §3.2.
RELATION_LINK_KINDS: Tuple[str, ...] = (
    "DERIVED_FROM", "SUPPORTS", "CONTRADICTS", "SUPERSEDES",
    "MERGED_INTO", "SPLIT_FROM",
)

#: The 5 transition rules (§a.4), quoted as machine-checked obligations.
TRANSITION_RULES: Tuple[str, ...] = (
    "R1 SUPPORTED needs a satisfied S criterion, REFUTED a satisfied R one; "
    "otherwise INCONCLUSIVE — never a default state.",
    "R2 one transition per observation, journalised with its refs; no silent update.",
    "R3 ARCHIVED is not a deletion: same id, same history on wake-up.",
    "R4 MERGED_INTO/SPLIT_FROM need equivalent statements and keep contradictions "
    "visible (G7).",
    "R5 an ARCHIVED record can never satisfy a mandatory proof (REQ-LABEL).",
)

#: §a.4 diagram, as a machine-verifiable transition map.
ALLOWED_TRANSITIONS: Mapping[str, Tuple[str, ...]] = {
    "CREATED": ("UNDER_TEST", "MERGED_INTO", "ARCHIVED"),
    "UNDER_TEST": ("SUPPORTED", "REFUTED", "INCONCLUSIVE", "MERGED_INTO", "ARCHIVED"),
    "SUPPORTED": ("UNDER_TEST", "MERGED_INTO", "ARCHIVED"),
    "REFUTED": ("UNDER_TEST", "MERGED_INTO", "ARCHIVED"),
    "INCONCLUSIVE": ("UNDER_TEST", "MERGED_INTO", "ARCHIVED"),
    "MERGED_INTO": ("ARCHIVED",),
    "ARCHIVED": ("UNDER_TEST",),
}

#: The 12 field groups of §a.3 (field 9 groups ``p`` and its freeze ref).
HYPOTHESIS_FIELD_GROUPS: Tuple[Tuple[str, ...], ...] = (
    ("id",),                          # 1
    ("case_id",),                     # 2
    ("enonce",),                      # 3
    ("criteres",),                    # 4
    ("preuves_pour",),                # 5
    ("preuves_contre",),              # 6
    ("inconnues",),                   # 7
    ("etat",),                        # 8
    ("p", "p_gel_ref"),               # 9
    ("histoire",),                    # 10
    ("provenance",),                  # 11
    ("relations",),                   # 12
)

HYPOTHESIS_FIELD_GROUP_COUNT = 12


# --------------------------------------------------------------------------
# Records.
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Criterion:
    """One falsifiability criterion (§a.3 field 4, §a.5 checklist)."""

    nom: str                 # "soutien" | "refutation"
    predicat: str            # executable-by-our-instruments predicate
    seuil: str               # threshold
    sources: Tuple[str, ...]  # admissible sources (named, with step + convention)
    fenetre: str             # observation window, ex. "t-48h..t+24h"


@dataclass(frozen=True)
class HistoryEntry:
    """One append-only history line (§a.3 field 10)."""

    utc: str                 # ISO-8601
    transition: str          # state entered (or "CREATED")
    raison: str
    refs: Tuple[str, ...] = ()
    dossier_hash: str = ""


@dataclass(frozen=True)
class HypothesisRecord:
    """The 12-field falsifiable hypothesis record (§a.3)."""

    id: str
    case_id: str
    enonce: str
    criteres: Tuple[Criterion, ...] = ()
    preuves_pour: Tuple[str, ...] = ()
    preuves_contre: Tuple[str, ...] = ()
    inconnues: Tuple[str, ...] = ()
    etat: str = "CREATED"
    p: Optional[str] = None
    p_gel_ref: str = ""
    histoire: Tuple[HistoryEntry, ...] = ()
    provenance: Mapping[str, Any] = field(default_factory=dict)
    relations: Tuple[str, ...] = ()


# --------------------------------------------------------------------------
# Validation.
# --------------------------------------------------------------------------
def _norm_statement(text: str) -> str:
    """Normalised statement for the deterministic merge dedup (rule 4)."""
    return " ".join(text.split()).casefold()


def validate_hypothesis(record: HypothesisRecord) -> Tuple[str, ...]:
    """Conformance check of a record against §a.3; ``E_*`` rejection codes."""
    errors: List[str] = []

    def reject(code: str) -> None:
        errors.append(code)

    # Fields 1–3.
    if not str(record.id or "").strip():
        reject("E_HYP_ID_EMPTY")
    if not str(record.case_id or "").strip():
        reject("E_HYP_CASE_EMPTY")
    if not str(record.enonce or "").strip():
        reject("E_HYP_ENONCE_EMPTY")

    # Field 4 — >= 1 S criterion and >= 1 R criterion, each complete.
    noms = set()
    for criterion in record.criteres:
        noms.add(criterion.nom)
        if (not str(criterion.predicat or "").strip()
                or not str(criterion.seuil or "").strip()
                or not criterion.sources or not str(criterion.fenetre or "").strip()):
            reject("E_HYP_CRITERION_INCOMPLETE")
    if "soutien" not in noms:
        reject("E_HYP_NO_SUPPORT_CRITERION")
    if "refutation" not in noms:
        reject("E_HYP_NO_REFUTATION_CRITERION")

    # Fields 5–7 — both proof lists are maintained (never left out).
    if record.preuves_pour is None or record.preuves_contre is None:
        reject("E_HYP_PROOF_LIST_MISSING")

    # Field 8.
    if record.etat not in HYPOTHESIS_STATES:
        reject("E_HYP_STATE_UNKNOWN")

    # Field 9 — never a number; a frozen label needs its freeze ref.
    if record.p is not None:
        if not isinstance(record.p, str) or record.p not in P_LABELS:
            reject("E_HYP_P_NOT_LABEL")
        if not str(record.p_gel_ref or "").strip():
            reject("E_HYP_P_NO_GEL_REF")

    # Field 10 — append-only history, every entry complete.
    for entry in record.histoire:
        if (not str(entry.utc or "").strip() or not str(entry.transition or "").strip()
                or not str(entry.raison or "").strip()):
            reject("E_HYP_HISTORY_INCOMPLETE")

    # Field 11 — provenance: logical author (role name), version, date.
    provenance = record.provenance or {}
    for key in ("auteur", "modele", "date"):
        if not str(provenance.get(key, "")).strip():
            reject("E_HYP_PROVENANCE_INCOMPLETE")
            break

    # Field 12 — relation links: "KIND:target_id".
    for link in record.relations:
        kind, sep, target = link.partition(":")
        if not sep or kind not in RELATION_LINK_KINDS or not target.strip():
            reject("E_HYP_RELATION_UNKNOWN")

    return tuple(errors)


# --------------------------------------------------------------------------
# JSON round-trip (B3 §a.3 skeleton keys).
# --------------------------------------------------------------------------
def record_to_dict(record: HypothesisRecord) -> Dict[str, Any]:
    """Plain dict with the exact keys of the §a.3 JSON skeleton."""
    return {
        "id": record.id,
        "case_id": record.case_id,
        "enonce": record.enonce,
        "criteres": [
            {"nom": c.nom, "predicat": c.predicat, "seuil": c.seuil,
             "sources": list(c.sources), "fenetre": c.fenetre}
            for c in record.criteres
        ],
        "preuves_pour": list(record.preuves_pour),
        "preuves_contre": list(record.preuves_contre),
        "inconnues": list(record.inconnues),
        "etat": record.etat,
        "p": record.p,
        "p_gel_ref": record.p_gel_ref,
        "histoire": [
            {"utc": e.utc, "transition": e.transition, "raison": e.raison,
             "refs": list(e.refs), "dossier_hash": e.dossier_hash}
            for e in record.histoire
        ],
        "provenance": dict(record.provenance),
        "relations": list(record.relations),
    }


def record_from_dict(data: Mapping[str, Any]) -> HypothesisRecord:
    """Build a record from the §a.3 JSON skeleton (both proof lists required)."""
    missing = [key for key in ("preuves_pour", "preuves_contre") if key not in data]
    if missing:
        raise ValueError("E_HYP_PROOF_LIST_MISSING: %s" % ", ".join(missing))
    return HypothesisRecord(
        id=data["id"],
        case_id=data["case_id"],
        enonce=data["enonce"],
        criteres=tuple(
            Criterion(nom=c["nom"], predicat=c["predicat"], seuil=c["seuil"],
                      sources=tuple(c["sources"] or ()), fenetre=c["fenetre"])
            for c in (data.get("criteres") or ())
        ),
        preuves_pour=tuple(data.get("preuves_pour") or ()),
        preuves_contre=tuple(data.get("preuves_contre") or ()),
        inconnues=tuple(data.get("inconnues") or ()),
        etat=data.get("etat", "CREATED"),
        p=data.get("p"),
        p_gel_ref=data.get("p_gel_ref", ""),
        histoire=tuple(
            HistoryEntry(utc=e["utc"], transition=e["transition"],
                         raison=e["raison"], refs=tuple(e.get("refs") or ()),
                         dossier_hash=e.get("dossier_hash", ""))
            for e in (data.get("histoire") or ())
        ),
        provenance=dict(data.get("provenance") or {}),
        relations=tuple(data.get("relations") or ()),
    )


# --------------------------------------------------------------------------
# Registry — the 5 transition rules.
# --------------------------------------------------------------------------
class HypothesisRegistry:
    """In-memory registry of hypothesis records (append-only, never deletes).

    Every state change returns a **new** frozen record whose ``histoire`` has
    one appended line; the registry keeps the latest revision and refuses any
    operation that would lose a trace (rules 1–5 of §a.4).
    """

    def __init__(self) -> None:
        self._records: Dict[str, HypothesisRecord] = {}

    # -- reads -------------------------------------------------------------
    def get(self, hypothesis_id: str) -> HypothesisRecord:
        return self._records[hypothesis_id]

    def all(self) -> Tuple[HypothesisRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))

    def __len__(self) -> int:
        return len(self._records)

    # -- creation ----------------------------------------------------------
    def create(self, record: HypothesisRecord) -> HypothesisRecord:
        """Register a CREATED record; ids are never reused (§a.3 field 1)."""
        if record.id in self._records:
            raise ValueError("E_HYP_ID_TAKEN: %s" % record.id)
        errors = validate_hypothesis(record)
        if errors:
            raise ValueError(", ".join(errors))
        if record.etat != "CREATED":
            raise ValueError("E_HYP_CREATE_STATE: %s" % record.etat)
        self._records[record.id] = record
        return record

    # -- rule 1 + rule 2 ---------------------------------------------------
    def transition(self, hypothesis_id: str, to_state: str, raison: str,
                   refs: Sequence[str], criteres_satisfaits: Sequence[str] = (),
                   utc: str = "") -> HypothesisRecord:
        """Apply one journalised transition (rules 1 and 2).

        ``criteres_satisfaits`` names the criteria explicitly satisfied by an
        observation: SUPPORTED needs a ``soutien`` one, REFUTED a
        ``refutation`` one. ``refs`` carries the observation refs that drive
        the transition — one ref drives at most one transition (rule 2).
        """
        record = self._records[hypothesis_id]
        if to_state not in HYPOTHESIS_STATES:
            raise ValueError("E_HYP_STATE_UNKNOWN: %s" % to_state)
        if to_state not in ALLOWED_TRANSITIONS[record.etat]:
            raise ValueError("E_HYP_TRANSITION_FORBIDDEN: %s -> %s"
                             % (record.etat, to_state))
        if not raison.strip():
            raise ValueError("E_HYP_TRANSITION_NO_RAISON")
        if not refs:
            raise ValueError("E_HYP_TRANSITION_NO_REFS")

        # Rule 1 — evidence-driven states need the matching criterion.
        satisfied = set(criteres_satisfaits)
        if to_state == "SUPPORTED" and "soutien" not in satisfied:
            raise ValueError("E_HYP_SUPPORTED_WITHOUT_S_CRITERION")
        if to_state == "REFUTED" and "refutation" not in satisfied:
            raise ValueError("E_HYP_REFUTED_WITHOUT_R_CRITERION")

        # Rule 2 — one transition per observation ref, no silent update.
        used = {ref for entry in record.histoire for ref in entry.refs}
        clashes = used.intersection(refs)
        if clashes:
            raise ValueError("E_HYP_HISTORY_REF_REUSED: %s" % ", ".join(sorted(clashes)))

        entry = HistoryEntry(utc=utc, transition=to_state, raison=raison,
                             refs=tuple(refs))
        updated = replace(record, etat=to_state, histoire=record.histoire + (entry,))
        self._records[hypothesis_id] = updated
        return updated

    # -- rule 3 ------------------------------------------------------------
    def archive(self, hypothesis_id: str, raison: str, refs: Sequence[str],
                utc: str = "") -> HypothesisRecord:
        """Move to ARCHIVED — a state, never a deletion (rule 3)."""
        return self.transition(hypothesis_id, "ARCHIVED", raison, refs, utc=utc)

    def wake(self, hypothesis_id: str, raison: str, refs: Sequence[str],
             utc: str = "") -> HypothesisRecord:
        """Wake an ARCHIVED record: same id, same history (rule 3)."""
        record = self._records[hypothesis_id]
        if record.etat != "ARCHIVED":
            raise ValueError("E_HYP_WAKE_NOT_ARCHIVED: %s" % record.etat)
        return self.transition(hypothesis_id, "UNDER_TEST", raison, refs, utc=utc)

    # -- rule 4 ------------------------------------------------------------
    def merge(self, merged_id: str, retained_id: str, raison: str,
              refs: Sequence[str], utc: str = "") -> HypothesisRecord:
        """MERGED_INTO: merge only equivalent statements, keep the trace.

        The deterministic path accepts exact statement duplicates only (the
        semantic dedup is a reviewed step on top). Contradictory records can
        never be merged (G7): the contradiction stays visible.
        """
        merged = self._records[merged_id]
        retained = self._records[retained_id]
        if merged_id == retained_id:
            raise ValueError("E_HYP_MERGE_SELF")
        if _norm_statement(merged.enonce) != _norm_statement(retained.enonce):
            raise ValueError("E_HYP_MERGE_NOT_EQUIVALENT")
        for record, other in ((merged, retained), (retained, merged)):
            for link in record.relations:
                kind, _, target = link.partition(":")
                if kind == "CONTRADICTS" and target == other.id:
                    raise ValueError("E_HYP_MERGE_CONTRADICTION")
        updated = self.transition(merged_id, "MERGED_INTO", raison, refs, utc=utc)
        updated = replace(updated,
                          relations=updated.relations + ("MERGED_INTO:%s" % retained_id,))
        self._records[merged_id] = updated
        return updated

    # -- rule 5 ------------------------------------------------------------
    def can_satisfy_proof(self, hypothesis_id: str) -> bool:
        """Rule 5 (REQ-LABEL): an ARCHIVED record never satisfies a proof."""
        return self._records[hypothesis_id].etat != "ARCHIVED"

    # -- persistence (JSONL, append-only friendly) -------------------------
    def dump_jsonl(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            for record in self.all():
                handle.write(json.dumps(record_to_dict(record), ensure_ascii=False,
                                        sort_keys=True) + "\n")

    @classmethod
    def load_jsonl(cls, path: str) -> "HypothesisRegistry":
        registry = cls()
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    record = record_from_dict(json.loads(line))
                    if record.id in registry._records:
                        # §a.3 field 1: an id is never reused — a duplicated
                        # line is a traceability break, never a silent overwrite.
                        raise ValueError("E_HYP_ID_TAKEN: %s (duplicate line in %s)"
                                         % (record.id, path))
                    registry._records[record.id] = record
        return registry
