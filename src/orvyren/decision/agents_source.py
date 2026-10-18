#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — agents run -> DecisionRecord bridge (the missing wire).

``orvyren.decide.build_decision_record`` replays a frozen USDC corpus and never
looks at what the reasoning agents produced: the LLM chain stays decorative.
This module closes that gap. It reads ONE sealed agents run directory and
returns a payload of the same *shape* as a DecisionRecord, built only from what
the run actually recorded.

Hard rules implemented here:

1. **No invented figure.** A value the artefacts do not carry is reported as
   ``"unavailable"`` (or ``None`` for the action/intent slots) — never zero,
   never an estimate, never a silent default.
2. **Determinism.** No wall-clock is read, no ``os.listdir`` order is trusted,
   every list is built in a stable order: two calls on the same directory
   serialise identically (``json.dumps(..., sort_keys=True)``).
3. **Honest abstention.** ``outcome.inconclusive`` or
   ``escalation == REQUIRE_APPROVAL`` -> no economic action, no intent,
   ``authorization_verdict = REQUIRE_APPROVAL``, and ``what_would_change``
   copies ``outcome.non_recherche`` verbatim (never summarised, never
   reworded). This is the normal v1 path: a motivated abstention is not a
   failure.
4. **A bounded intent needs a declared bounded action.** Only a conclusive run
   whose ``run.json`` / ``run_outcome.json`` carries an explicit ``intent``
   block yields one; a missing action, chain, asset or amount means no intent
   at all (an amount is never derived, a recipient is never invented).
5. **Provenance comes from the journals.** Every ``evidence_refs`` entry is a
   ``{"source": "agents_journal:<role>", "value": <chain head>}`` pair whose
   head was *recomputed* from the journal file and matches the sealed outcome.
6. **Live runs are not bit-replayable.** Their payloads embed measured
   wall-time and realised cost, so ``source.replayable`` is ``False`` with a
   declared reason. ``AgentsNotReplayable`` is never raised for that: a sealed
   live run stays usable evidence for a decision.

Only ``run.json``, ``run_outcome.json`` and ``journal_<role>.jsonl`` are ever
opened. No key, no secret, no network, no git.

Standard library only.
"""

from __future__ import annotations

import json
import os
from dataclasses import fields as _dataclass_fields
from typing import Any, Dict, List, Mapping, Optional, Tuple

from orvyren.agents.journal import GENESIS_HASH, JournalEntry, entry_hash

__all__ = [
    "SCHEMA",
    "UNAVAILABLE",
    "AgentsSourceError",
    "AgentsNotReplayable",
    "build_decision_from_agents",
]

#: DecisionRecord schema — identical to ``orvyren.decide.SCHEMA`` (measured;
#: the value is asserted against it by the test bench, never duplicated in
#: prose). A record built from a run therefore parses with the same consumers.
SCHEMA = "orvyren-decision-record/v1"

#: Run artefacts this module understands.
RUN_SCHEMA = "orvyren/agent-run/v1"
OUTCOME_SCHEMA = "orvyren/agent-run-outcome/v1"
RUN_FILENAME = "run.json"
OUTCOME_FILENAME = "run_outcome.json"
JOURNAL_FILENAME_TEMPLATE = "journal_%s.jsonl"

#: Declared absence marker (rule 1). Never a zero, never a guess.
UNAVAILABLE = "unavailable"

#: The only authorization verdict the agents side can state on its own: an
#: agents run never evaluates the policy, so a conclusive one leaves the axis
#: unevaluated (``None``) and an abstaining one brakes on human approval.
REQUIRE_APPROVAL = "REQUIRE_APPROVAL"

#: Replay a journal run bit-for-bit is the REPLAY-JOURNAL path; a live run is
#: not, by construction (measured wall-time and cost enter its payloads).
REPLAYABLE_MODES = ("journal",)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

#: Journal columns accepted by the shared line schema; any other key in a line
#: is ignored here (the journal writer already quarantined it, if it cared).
_JOURNAL_FIELDS = frozenset(field.name for field in _dataclass_fields(JournalEntry))

#: Keys an explicit bounded action must carry. A missing one means "no intent".
_ACTION_REQUIRED_KEYS = ("action", "chain_id", "asset", "amount")


class AgentsSourceError(Exception):
    """An agents run cannot be turned into a decision payload.

    Raised for a missing directory, a missing/unreadable ``run_outcome.json``,
    a journal that is absent although the sealed outcome declares it, or a
    journal chain that no longer recomputes (the sealed head would be a lie).
    """


class AgentsNotReplayable(AgentsSourceError):
    """A caller asked for a bit-identical replay of a run that cannot offer it.

    ``build_decision_from_agents`` never raises it: it *declares*
    ``source.replayable = False`` and returns the record (rule 6). The class
    exists for callers that require replay and want to catch the refusal.
    """


# ---------------------------------------------------------------------------
# Small deterministic readers
# ---------------------------------------------------------------------------
def _read_json_object(path: str, label: str) -> Dict[str, Any]:
    """Read one JSON object, or raise :class:`AgentsSourceError`."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except OSError as exc:
        raise AgentsSourceError("%s unreadable: %s" % (label, exc))
    except ValueError as exc:
        raise AgentsSourceError("%s is not valid JSON: %s" % (label, exc))
    if not isinstance(payload, dict):
        raise AgentsSourceError("%s is not a JSON object" % label)
    return payload


def _load_journal(path: str, role: str) -> Tuple[List[Dict[str, Any]], str]:
    """Return ``(lines, chain_head)`` for one journal, recomputing the chain.

    The head is recomputed with the very hash the writer used
    (``agents.journal.entry_hash``), so a rewritten line can never pass for a
    sealed one. An empty file yields the genesis head.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw_lines = [line for line in handle.read().splitlines() if line.strip()]
    except OSError as exc:
        raise AgentsSourceError("journal unreadable for role %r: %s" % (role, exc))

    lines: List[Dict[str, Any]] = []
    previous = GENESIS_HASH
    for index, raw in enumerate(raw_lines):
        try:
            data = json.loads(raw)
        except ValueError as exc:
            raise AgentsSourceError("journal line %d of role %r is not JSON: %s"
                                    % (index, role, exc))
        if not isinstance(data, dict):
            raise AgentsSourceError("journal line %d of role %r is not an object"
                                    % (index, role))
        payload = {key: value for key, value in data.items() if key in _JOURNAL_FIELDS}
        if payload.get("prev_hash", GENESIS_HASH) != previous:
            raise AgentsSourceError("journal chain broken at role %r line %d (%s)"
                                    % (role, index, payload.get("journal_id", "?")))
        try:
            entry = JournalEntry(**payload)
        except TypeError as exc:
            raise AgentsSourceError("journal line %d of role %r has a schema "
                                    "failure: %s" % (index, role, exc))
        previous = entry_hash(entry)
        lines.append(payload)
    return lines, previous


def _relative_run_dir(run_dir: str) -> str:
    """Repository-relative POSIX path when inside the repo, absolute otherwise."""
    absolute = os.path.abspath(run_dir)
    try:
        relative = os.path.relpath(absolute, _REPO_ROOT)
    except ValueError:  # different drive on Windows
        return absolute.replace("\\", "/")
    if relative == os.pardir or relative.startswith(os.pardir + os.sep):
        return absolute.replace("\\", "/")
    return relative.replace("\\", "/")


def _as_bool_text(value: bool) -> str:
    return "true" if value else "false"


def _text(value: Any) -> str:
    """Declared text or ``UNAVAILABLE`` — never a coerced empty string."""
    if value is None:
        return UNAVAILABLE
    text = str(value).strip()
    return text if text else UNAVAILABLE


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> List[Any]:
    if isinstance(value, (list, tuple)):
        return list(value)
    return []


# ---------------------------------------------------------------------------
# Artefact normalisation
# ---------------------------------------------------------------------------
def _normalise_hypotheses(run_payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Hypotheses as declared by ``run.json`` (list or id-keyed dict), sorted.

    Only the declared fields are copied: the agents' ``etat`` (UNDER_TEST, ...)
    is kept under its own name — it is *not* a decision verdict and must not be
    read as one. A missing probability stays ``unavailable`` (never 0).
    """
    raw = run_payload.get("hypotheses")
    items: List[Dict[str, Any]] = []
    if isinstance(raw, Mapping):
        for key in sorted(raw):
            item = dict(_mapping(raw[key]))
            item.setdefault("id", key)
            items.append(item)
    else:
        for entry in _sequence(raw):
            if isinstance(entry, Mapping):
                items.append(dict(entry))
    items.sort(key=lambda item: str(item.get("id", "")))

    hypotheses: List[Dict[str, Any]] = []
    for item in items:
        criteria = _mapping(item.get("criteres"))
        hypotheses.append({
            "id": _text(item.get("id")),
            "enonce": _text(item.get("enonce")),
            "agent_state": _text(item.get("etat")),
            "support_criterion": _text(criteria.get("S")),
            "refutation_criterion": _text(criteria.get("R")),
            "probability_declared": _text(item.get("p")),
        })
    return hypotheses


def _normalise_verdicts(hypotheses: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Per-hypothesis slot in the decision record's verdict shape.

    The agents side produces no decision verdict (no SUPPORTED/REFUTED): the
    slot is present, declared ``unavailable``, and carries the agents' own
    state so a reader can see what was actually decided upstream.
    """
    verdicts: Dict[str, Dict[str, Any]] = {}
    for item in hypotheses:
        verdicts[item["id"]] = {
            "verdict": UNAVAILABLE,
            "agent_state": item["agent_state"],
            "source": "run.json:hypotheses[].etat",
        }
    return verdicts


def _normalise_critique(critique: Mapping[str, Any]) -> Dict[str, Any]:
    """The critic report as declared — counts are measured, never estimated."""
    findings = [entry for entry in _sequence(critique.get("findings"))
                if isinstance(entry, Mapping)]
    types = sorted({_text(entry.get("type")) for entry in findings})
    gravities = sorted({_text(entry.get("gravite")) for entry in findings})
    return {
        "schema": _text(critique.get("$schema")),
        "verdict": _text(critique.get("verdict_lecture")),
        "findings_count": len(findings),
        "finding_types": types,
        "gravities": gravities,
        "preuves_manquantes": list(_sequence(critique.get("preuves_manquantes"))),
        "note": critique.get("note") if isinstance(critique.get("note"), str) else "",
    }


def _normalise_lacunes(run_payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Declared gaps, copied field by field and sorted by ``lacune_id``."""
    lacunes = [dict(entry) for entry in _sequence(run_payload.get("lacunes"))
               if isinstance(entry, Mapping)]
    lacunes.sort(key=lambda entry: str(entry.get("lacune_id", "")))
    return lacunes


def _declared_action(run_payload: Mapping[str, Any],
                     outcome_payload: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    """The explicit bounded action, wherever the run declared one.

    Accepted locations (closed list, in this order): ``run.json:intent``,
    ``run_outcome.json:intent``, ``run_outcome.json:outcome.intent``. Nothing
    is inferred from free text, from a journal DECISION_DRAFT line or from the
    critique: a draft is not a bounded action.
    """
    for holder in (run_payload, outcome_payload,
                   _mapping(outcome_payload.get("outcome"))):
        candidate = holder.get("intent")
        if isinstance(candidate, Mapping):
            return candidate
    return None


def _build_intent(action: Mapping[str, Any], case_id: str,
                  recipient_address: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """Bounded intent from a declared action, or ``(None, declared reason)``.

    Every field is copied from the declaration; nothing is computed. A missing
    amount, asset, action or chain means no intent — the decision abstains.
    """
    missing = [key for key in _ACTION_REQUIRED_KEYS
               if action.get(key) in (None, "", [])]
    if missing:
        return None, "declared action incomplete (missing: %s)" % ", ".join(sorted(missing))
    recipient = action.get("recipient")
    if not (isinstance(recipient, str) and recipient.strip()):
        recipient = recipient_address or ""
    intent = {
        "intent_id": _text(action.get("intent_id")) if action.get("intent_id")
        else "intent-%s-agents" % case_id,
        "action": action.get("action"),
        "chain_id": action.get("chain_id"),
        "asset": action.get("asset"),
        "amount": action.get("amount"),
        "recipient": recipient,
    }
    return intent, "declared in the run artefacts"


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------
def build_decision_from_agents(run_dir: str, *, case_id: str = None,
                               recipient_address: str = "") -> Dict[str, Any]:
    """Build a DecisionRecord payload from one sealed agents run directory.

    ``run_dir`` is a directory holding ``run_outcome.json`` (and, normally,
    ``run.json`` plus one ``journal_<role>.jsonl`` per role). ``case_id``
    overrides the case declared by the artefacts; ``recipient_address`` is only
    used to fill an already-declared bounded action's empty recipient — it
    never creates one.

    Deterministic and offline. Raises :class:`AgentsSourceError` on a missing
    or inconsistent artefact; *never* raises for a live (non-replayable) run —
    that is declared in ``source.replayable`` instead (rule 6).
    """
    if run_dir is None or not str(run_dir).strip():
        raise AgentsSourceError("run_dir is empty")
    root = os.path.abspath(str(run_dir))
    if not os.path.isdir(root):
        raise AgentsSourceError("run directory not found: %s" % root)

    outcome_path = os.path.join(root, OUTCOME_FILENAME)
    if not os.path.isfile(outcome_path):
        raise AgentsSourceError("%s missing in %s" % (OUTCOME_FILENAME, root))
    outcome_payload = _read_json_object(outcome_path, OUTCOME_FILENAME)
    if "schema" not in outcome_payload:
        raise AgentsSourceError("%s carries no schema: not an agents run outcome"
                                % OUTCOME_FILENAME)

    run_path = os.path.join(root, RUN_FILENAME)
    run_payload: Dict[str, Any] = {}
    if os.path.isfile(run_path):
        run_payload = _read_json_object(run_path, RUN_FILENAME)

    # -- journals: the only provenance this module is allowed to claim ------
    declared_journals = _mapping(outcome_payload.get("journals"))
    roles = set(declared_journals)
    for candidate in ("orchestrator", "critic"):
        if os.path.isfile(os.path.join(root, JOURNAL_FILENAME_TEMPLATE % candidate)):
            roles.add(candidate)
    if not roles:
        raise AgentsSourceError("no agent journal found in %s" % root)

    chain_heads: Dict[str, str] = {}
    journal_lines: Dict[str, int] = {}
    first_run_id = ""
    for role in sorted(roles):
        path = os.path.join(root, JOURNAL_FILENAME_TEMPLATE % role)
        if not os.path.isfile(path):
            raise AgentsSourceError("journal for role %r is missing in %s "
                                    "(the sealed outcome declares it)" % (role, root))
        lines, head = _load_journal(path, role)
        declared_head = _mapping(declared_journals.get(role)).get("chain_head")
        if declared_head and declared_head != head:
            raise AgentsSourceError(
                "declared chain head for role %r does not match the journal "
                "(%s != %s)" % (role, declared_head, head))
        chain_heads[role] = head
        journal_lines[role] = len(lines)
        if not first_run_id and lines:
            candidate = lines[0].get("run_id")
            if isinstance(candidate, str) and candidate.strip():
                first_run_id = candidate.strip()

    # -- declared identity -------------------------------------------------
    declared_case = run_payload.get("case_id") or outcome_payload.get("case_id")
    if case_id:
        case_value, case_source = str(case_id), "argument"
    elif isinstance(declared_case, str) and declared_case.strip():
        case_value = declared_case.strip()
        case_source = "run.json" if run_payload.get("case_id") else OUTCOME_FILENAME
    else:
        case_value, case_source = UNAVAILABLE, UNAVAILABLE

    mode_declared = run_payload.get("mode") or outcome_payload.get("mode")
    mode = _text(mode_declared)
    replayable = mode in REPLAYABLE_MODES
    if replayable:
        replayable_reason = ("journal run: the hash-chained journals are the "
                             "replay source (REPLAY-JOURNAL)")
    elif mode == "live":
        replayable_reason = ("live run: payloads embed measured wall-time and "
                             "realised cost, so bit-identical replay is not "
                             "possible (use REPLAY-ARCHIVE recalculation)")
    else:
        replayable_reason = ("mode %r is not declared replayable" % mode)

    run_id = (run_payload.get("run_id") if isinstance(run_payload.get("run_id"), str)
              and str(run_payload.get("run_id")).strip() else "")
    run_id = run_id or first_run_id or UNAVAILABLE

    # -- outcome: the honest branch ---------------------------------------
    outcome = _mapping(outcome_payload.get("outcome"))
    outcome_declared = bool(outcome)
    inconclusive = bool(outcome.get("inconclusive")) if outcome_declared else True
    escalation = outcome_payload.get("escalation")
    escalation_text = _text(escalation)
    abstain = inconclusive or escalation_text == REQUIRE_APPROVAL or not outcome_declared

    triggers: List[str] = []
    if not outcome_declared:
        triggers.append("outcome block missing (fail-closed)")
    else:
        if inconclusive:
            triggers.append("outcome.inconclusive=true")
        if escalation_text == REQUIRE_APPROVAL:
            triggers.append("escalation=REQUIRE_APPROVAL")

    non_recherche = _sequence(outcome.get("non_recherche"))
    stop_condition = _text(outcome.get("stop_condition"))
    state = _text(outcome.get("state"))
    motif = _text(outcome.get("motif"))
    budget_used = outcome.get("budget_used") if isinstance(outcome.get("budget_used"),
                                                          Mapping) else UNAVAILABLE
    budget_declared = run_payload.get("budget") if isinstance(run_payload.get("budget"),
                                                             Mapping) else UNAVAILABLE

    critique = _normalise_critique(_mapping(outcome_payload.get("critique")))
    hypotheses = _normalise_hypotheses(run_payload)
    verdicts = _normalise_verdicts(hypotheses)
    lacunes = _normalise_lacunes(run_payload)

    action = _declared_action(run_payload, outcome_payload)
    intent: Optional[Dict[str, Any]] = None
    economic_action = None
    authorization_verdict: Optional[str] = None
    authorization_note = ("not evaluated: an agents run does not evaluate the "
                          "policy (the orchestrator does)")

    if abstain:
        intent = None
        economic_action = None
        authorization_verdict = REQUIRE_APPROVAL
        abstract_reason = "abstention: no economic action and no intent produced"
    elif action is None:
        abstract_reason = ("conclusive run without a declared bounded action: "
                           "no economic action, no intent")
    else:
        intent, intent_reason = _build_intent(action, case_value, recipient_address)
        if intent is None:
            abstract_reason = "conclusive run, %s: no intent" % intent_reason
        else:
            economic_action = action.get("action")
            abstract_reason = "conclusive run, intent %s" % intent_reason

    if inconclusive and outcome_declared:
        epistemic_verdict = "INCONCLUSIVE"
    elif critique["verdict"] != UNAVAILABLE:
        epistemic_verdict = critique["verdict"]
    else:
        epistemic_verdict = UNAVAILABLE

    rationale_parts = [
        "agents run %s (%s): state %s, stop %s, inconclusive %s, escalation %s"
        % (run_id, mode, state, stop_condition, _as_bool_text(inconclusive),
           escalation_text),
        "outcome motif: %s" % motif,
        "critique %s (%d finding(s))" % (critique["verdict"],
                                         critique["findings_count"]),
        "journals: %s" % ", ".join("%s %d line(s)" % (role, journal_lines[role])
                                   for role in sorted(journal_lines)),
        abstract_reason,
    ]
    if abstain:
        rationale_parts.append("authorization REQUIRE_APPROVAL (no policy "
                               "evaluation was possible without an action)")

    evidence_refs = [{"source": "agents_journal:%s" % role,
                      "value": chain_heads[role]}
                     for role in sorted(chain_heads)]

    abstention_payload = None
    if abstain:
        abstention_payload = {
            "epistemic_verdict": "INCONCLUSIVE" if inconclusive else None,
            "triggers": triggers,
            "motif": motif,
            "stop_condition": stop_condition,
            "state": state,
            "what_would_change_the_verdict": list(non_recherche),
            "action": None,
        }

    record: Dict[str, Any] = {
        "schema": SCHEMA,
        "case": case_value,
        "mode": mode,
        "epistemic_verdict": epistemic_verdict,
        "economic_action": economic_action,
        "authorization_verdict": authorization_verdict,
        "intent": intent,
        "rationale": " ; ".join(rationale_parts),
        "evidence_refs": evidence_refs,
        "what_would_change": list(non_recherche) if abstain else [],
        "abstention": abstention_payload,
        "hypotheses": hypotheses,
        "verdicts": verdicts,
        "lacunes": lacunes,
        "critique": critique,
        "escalation": escalation_text,
        "outcome_state": state,
        "stop_condition": stop_condition,
        "outcome_motif": motif,
        "research_cost": {
            "budget": budget_used,
            "budget_declared": budget_declared,
            "arret": stop_condition,
            "arret_regle": motif,
            "state": state,
        },
        "axes": {
            "epistemic_verdict": epistemic_verdict,
            "economic_action": economic_action,
            "authorization_verdict": authorization_verdict,
            "authorization_note": authorization_note,
        },
        "source": {
            "kind": "agents",
            "run_dir": _relative_run_dir(root),
            "run_id": run_id,
            "run_schema": _text(run_payload.get("schema")),
            "outcome_schema": _text(outcome_payload.get("schema")),
            "mode": mode,
            "case_id_source": case_source,
            "chain_heads": {role: chain_heads[role] for role in sorted(chain_heads)},
            "journal_lines": {role: journal_lines[role] for role in sorted(journal_lines)},
            "journals_verified": {role: True for role in sorted(chain_heads)},
            "replayable": replayable,
            "replayable_reason": replayable_reason,
            "artefacts": {
                "run_json": bool(run_payload),
                "run_outcome_json": True,
                "journals": sorted(chain_heads),
            },
        },
    }
    return record
