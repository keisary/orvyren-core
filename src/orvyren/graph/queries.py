"""The 8 core graph queries Q1–Q8 (B2 §6.1) — the store's test contract.

Each query is a pure function over ``Sequence[RelationRecord]`` (the
17-field record of B2 §3.0), deterministic and offline. They are written as
**the store's test contracts** (DOC4 lot L1.4): the fixtures under
``fixtures/graphs/`` carry the measured values of the three episodes (USDC
2023-03, stETH 2022-06, rsETH 2026-04) and the tests assert the queries
reproduce the published figures of W2-B/W3.

Query map (B2 §6.1):
- Q1 :func:`q1_consolidated_exposure` — treasury exposure, direct + indirect,
  bounded closure on HOLDS / DEPOSITED_IN / COLLATERALIZES. Transitive HOLDS
  is **never** closed (B2 §6.3: holding ≠ controlling).
- Q2 :func:`q2_dependency_paths` — who depends on a node, with channel, sign
  and per-hop decay; only DEPENDS_ON / AFFECTS are traversed (never bare
  closure), and SUPPORTS / REFUTES / CONTRADICTS / CORRELATES_WITH are
  structurally untraversable (invariant).
- Q3 :func:`q3_open_contradictions` — unresolved CONTRADICTS pairs.
- Q4 :func:`q4_pit_state` — the graph as known at T (world ∩ knowledge).
- Q5 :func:`q5_episode_timeline` — events between T1 and T2 with the
  event-time and tx-time clocks kept separate.
- Q6 :func:`q6_provenance_walk` — decision → claims → observations → sources,
  every hop carrying its content fingerprint (hash).
- Q7 :func:`q7_concentration` — debt backed by an asset, its weight,
  supply/cap and HHI.
- Q8 :func:`q8_permission_state` — role membership and allowances as-of a
  block, revocations included.

Standard library only.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from orvyren.graph.models import fingerprint
from orvyren.graph.record import (RelationRecord, record_as_dict,
                                  record_from_dict)
from orvyren.graph.temporal import covers, pit_at

__all__ = [
    "q1_consolidated_exposure",
    "q2_dependency_paths",
    "q3_open_contradictions",
    "q4_pit_state",
    "q5_episode_timeline",
    "q6_provenance_walk",
    "q7_concentration",
    "q8_permission_state",
    "load_fixture_records",
    "DEPENDENCY_KINDS",
    "FORBIDDEN_PROPAGATION_KINDS",
]

#: Q2 traverses only these kinds (B2 §6.1/§6.3).
DEPENDENCY_KINDS = frozenset({"DEPENDS_ON", "AFFECTS"})

#: B2 §6.3 invariants: never propagate along these kinds.
FORBIDDEN_PROPAGATION_KINDS = frozenset(
    {"SUPPORTS", "REFUTES", "CONTRADICTS", "CORRELATES_WITH"})

#: Q1 expansion after the initial HOLDS (bounded, never transitive HOLDS).
_Q1_EXPANSION_KINDS = frozenset(
    {"DEPOSITED_IN", "COLLATERALIZES", "REHYPOTHECATED_TO"})

#: Q6 provenance edges (B2 §3.2 family 1).
_PROVENANCE_KINDS = frozenset({"EXTRACTED_FROM", "DERIVED_FROM", "OBSERVED_FROM"})


def load_fixture_records(path: str) -> Tuple[RelationRecord, ...]:
    """Load a ``fixtures/graphs/*.json`` file into validated-ready records."""
    import json
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return tuple(record_from_dict(item) for item in data["records"])


def _visible(records: Sequence[RelationRecord],
             as_of: Optional[str]) -> Tuple[RelationRecord, ...]:
    """World-validity filter (open when ``as_of`` is None)."""
    if as_of is None:
        return tuple(records)
    return tuple(record for record in records if covers(record, as_of))


# ---------------------------------------------------------------------------
# Q1 — consolidated exposure of a treasury.
# ---------------------------------------------------------------------------
def q1_consolidated_exposure(records: Sequence[RelationRecord], holder: str,
                             as_of: Optional[str] = None,
                             max_depth: int = 3) -> Dict[str, Any]:
    """Direct + indirect exposure of ``holder``, grouped by protocol.

    Depth 0: ``HOLDS`` edges of the holder. Deeper hops expand only along
    ``DEPOSITED_IN`` / ``COLLATERALIZES`` / ``REHYPOTHECATED_TO`` — a second
    ``HOLDS`` edge is **never** traversed (holding ≠ controlling).
    """
    visible = _visible(records, as_of)
    direct: List[Dict[str, Any]] = []
    indirect: List[Dict[str, Any]] = []
    for record in visible:
        if record.kind == "HOLDS" and record.src == holder:
            direct.append({"asset": record.dst, "relation_id": record.relation_id,
                           "payload": dict(record.payload)})
    frontier = [(item["asset"], 0) for item in direct]
    seen = {asset for asset, _ in frontier}
    while frontier:
        asset, depth = frontier.pop(0)
        if depth >= max_depth:
            continue
        for record in visible:
            if record.kind in _Q1_EXPANSION_KINDS and record.src == asset:
                indirect.append({
                    "asset": asset,
                    "protocol": record.dst,
                    "kind": record.kind,
                    "depth": depth + 1,
                    "relation_id": record.relation_id,
                    "payload": dict(record.payload),
                })
                if record.dst not in seen:
                    seen.add(record.dst)
                    frontier.append((record.dst, depth + 1))
    protocols = sorted({item["protocol"] for item in indirect})
    return {"holder": holder, "direct": sorted(direct, key=lambda i: i["asset"]),
            "indirect": sorted(indirect, key=lambda i: (i["depth"], i["asset"],
                                                        i["protocol"])),
            "protocols": protocols}


# ---------------------------------------------------------------------------
# Q2 — bounded dependency paths.
# ---------------------------------------------------------------------------
def q2_dependency_paths(records: Sequence[RelationRecord], node: str,
                        as_of: Optional[str] = None, max_depth: int = 3,
                        decay: float = 0.5) -> List[Dict[str, Any]]:
    """Who depends on ``node``, through which channel, with sign and decay.

    ``DEPENDS_ON`` edges are read incoming (X depends on Y = edge X→Y), and
    ``AFFECTS`` edges outgoing (Cause→Effect). Weight decays per hop; depth is
    bounded and cycles are cut. Only DEPENDS_ON / AFFECTS are traversed.
    """
    visible = _visible(records, as_of)
    paths: List[Dict[str, Any]] = []
    queue: List[Tuple[str, List[RelationRecord]]] = [(node, [])]
    seen = {node}
    while queue:
        current, trail = queue.pop(0)
        if len(trail) >= max_depth:
            continue
        for record in visible:
            if record.kind not in DEPENDENCY_KINDS:
                continue
            if record.kind == "DEPENDS_ON" and record.dst != current:
                continue
            if record.kind == "AFFECTS" and record.src != current:
                continue
            dependent = record.src if record.kind == "DEPENDS_ON" else record.dst
            if dependent in seen:
                # Cycles (and diamond re-entries) are cut: each dependent is
                # emitted exactly once — a cycle-closure path adds no decision
                # value and the traversal stays bounded.
                continue
            seen.add(dependent)
            hop = trail + [record]
            signs = [r.sign_prior for r in hop]
            sign = _sign_product(signs)
            paths.append({
                "dependent": dependent,
                "path": [node] + [r.src if r.kind == "DEPENDS_ON" else r.dst
                                  for r in hop],
                "relations": [r.relation_id for r in hop],
                "kinds": [r.kind for r in hop],
                "channels": [r.mechanism for r in hop],
                "sign": sign,
                "weight": decay ** len(hop),
            })
            queue.append((dependent, hop))
    paths.sort(key=lambda item: (item["dependent"], item["relations"]))
    return paths


def _sign_product(signs: Sequence[str]) -> str:
    product = 1
    for sign in signs:
        if sign == "+":
            continue
        if sign == "-":
            product = -product
        else:
            return "ambigu"
    return "+" if product > 0 else "-"


# ---------------------------------------------------------------------------
# Q3 — open contradictions.
# ---------------------------------------------------------------------------
def q3_open_contradictions(records: Sequence[RelationRecord]) -> List[Dict[str, str]]:
    """Unresolved CONTRADICTS pairs (neither side rejected nor superseded)."""
    open_pairs = []
    for record in records:
        if record.kind != "CONTRADICTS":
            continue
        if record.validation_status == "REJECTED" or record.superseded_by:
            continue
        open_pairs.append({"claim_a": record.src, "claim_b": record.dst,
                           "relation_id": record.relation_id})
    open_pairs.sort(key=lambda item: (item["claim_a"], item["claim_b"]))
    return open_pairs


# ---------------------------------------------------------------------------
# Q4 — PIT state.
# ---------------------------------------------------------------------------
def q4_pit_state(records: Sequence[RelationRecord],
                 as_of: str) -> Tuple[RelationRecord, ...]:
    """The graph as known at T: world validity ∩ knowledge (INV-PIT)."""
    return pit_at(records, as_of)


# ---------------------------------------------------------------------------
# Q5 — episode timeline.
# ---------------------------------------------------------------------------
def q5_episode_timeline(records: Sequence[RelationRecord], t1: str,
                        t2: str) -> List[Dict[str, Any]]:
    """Records between T1 and T2, clocks kept separate.

    ``event_time`` is the world clock (``valid_from``), ``tx_time`` the system
    clock (``inserted_at``); ordering is (event_time, tx_time).
    """
    entries = []
    for record in records:
        event_time = record.valid_from
        tx_time = record.inserted_at
        in_window = ((event_time and t1 <= event_time < t2)
                     or (tx_time and t1 <= tx_time < t2))
        if not in_window:
            continue
        entries.append({"relation_id": record.relation_id, "kind": record.kind,
                        "src": record.src, "dst": record.dst,
                        "event_time": event_time, "tx_time": tx_time,
                        "payload": dict(record.payload)})
    entries.sort(key=lambda item: (item["event_time"] or item["tx_time"],
                                   item["tx_time"]))
    return entries


# ---------------------------------------------------------------------------
# Q6 — provenance walk with hashes.
# ---------------------------------------------------------------------------
def q6_provenance_walk(records: Sequence[RelationRecord],
                       start_id: str) -> Dict[str, Any]:
    """Decision → claims → observations → sources, each hop hashed.

    Follows EXTRACTED_FROM / DERIVED_FROM / OBSERVED_FROM edges (family 1);
    every returned hop carries the content fingerprint of its record.
    """
    by_src: Dict[str, List[RelationRecord]] = {}
    for record in records:
        if record.kind in _PROVENANCE_KINDS:
            by_src.setdefault(record.src, []).append(record)
    chain: List[Dict[str, Any]] = []
    visited = set()
    frontier = [start_id]
    while frontier:
        current = frontier.pop(0)
        if current in visited:
            continue
        visited.add(current)
        for record in sorted(by_src.get(current, ()), key=lambda r: r.relation_id):
            chain.append({
                "from": current,
                "to": record.dst,
                "relation_id": record.relation_id,
                "kind": record.kind,
                "fingerprint": fingerprint(record_as_dict(record)),
                "source_family_id": record.source_family_id,
                "provenance_refs": list(record.provenance_refs),
            })
            frontier.append(record.dst)
    return {"origin": start_id, "chain": chain,
            "hashes_complete": all(hop["fingerprint"] for hop in chain)}


# ---------------------------------------------------------------------------
# Q7 — concentration aggregates.
# ---------------------------------------------------------------------------
def q7_concentration(records: Sequence[RelationRecord], asset: str,
                     as_of: Optional[str] = None) -> Dict[str, Any]:
    """Debt backed by ``asset``: markets, weight, supply/cap and HHI."""
    visible = _visible(records, as_of)
    collateral: Dict[str, float] = {}
    supply_cap_ratio: Optional[float] = None
    debt_backed = 0.0
    for record in visible:
        if record.kind == "COLLATERALIZES" and record.src == asset:
            amount = _number(record, "amount")
            if amount is not None:
                collateral[record.dst] = collateral.get(record.dst, 0.0) + amount
        if (record.kind in ("CONSTRAINS", "DEPOSITED_IN")
                and asset in (record.src, record.dst)):
            ratio = _supply_cap_ratio(record)
            if ratio is not None:
                supply_cap_ratio = ratio
        if record.kind == "OWES":
            amount = _number(record, "amount")
            if amount is not None:
                debt_backed += amount
    total = sum(collateral.values())
    shares = {market: amount / total for market, amount in collateral.items()} \
        if total else {}
    hhi = sum(share * share for share in shares.values())
    return {"asset": asset, "collateral_by_market": dict(sorted(collateral.items())),
            "w_a": max(shares.values()) if shares else 0.0,
            "debt_backed": debt_backed,
            "supply_cap_ratio": supply_cap_ratio,
            "hhi": hhi}


def _number(record: RelationRecord, key: str) -> Optional[float]:
    value = record.payload.get(key)
    return float(value) if isinstance(value, (int, float)) else None


def _supply_cap_ratio(record: RelationRecord) -> Optional[float]:
    cap = _number(record, "supply_cap")
    supply = _number(record, "supply")
    if cap and supply is not None:
        return supply / cap
    return None


# ---------------------------------------------------------------------------
# Q8 — permission state as-of a block.
# ---------------------------------------------------------------------------
def q8_permission_state(records: Sequence[RelationRecord], subject: str,
                        as_of: Optional[str] = None,
                        as_of_block: Optional[int] = None) -> Dict[str, Any]:
    """Role membership / allowances / revocations of ``subject``.

    On-chain facts are anchored (chain_ref); a fact is visible as-of block B
    when its anchor block <= B and its validity intervals (world time and
    block-native bounds) contain ``as_of`` / ``as_of_block``.
    """
    roles: List[Dict[str, Any]] = []
    allowances: List[Dict[str, Any]] = []
    revoked: List[Dict[str, Any]] = []
    visible = []
    for record in records:
        if as_of is not None and not covers(record, as_of):
            continue
        if (as_of_block is not None and record.chain_ref is not None
                and record.chain_ref.block > as_of_block):
            continue
        # Block-native PIT bounds (field 11b): half-open [valid_from_block,
        # valid_to_block), same inclusivity as the SQL API's validity filter.
        if as_of_block is not None:
            if (record.valid_from_block is not None
                    and record.valid_from_block > as_of_block):
                continue
            if (record.valid_to_block is not None
                    and as_of_block >= record.valid_to_block):
                continue
        visible.append(record)
    # Pass 1 — membership of the subject.
    for record in visible:
        if record.kind == "MEMBER_OF" and record.src == subject:
            roles.append({"role": record.dst, "relation_id": record.relation_id,
                          "block": record.chain_ref.block if record.chain_ref else None,
                          "payload": dict(record.payload)})
    role_names = {item["role"] for item in roles}
    # Pass 2 — allowances granted to those roles (B2 §3.2: Role → Target/Function).
    for record in visible:
        if record.kind == "ALLOWS" and record.src in role_names:
            allowances.append({"role": record.src, "target": record.dst,
                               "relation_id": record.relation_id,
                               "payload": dict(record.payload)})
    # Pass 3 — revocations touching the subject or one of its roles
    # (REVOKES: Authority → Right/Subject, B2 §3.2 4.3).
    for record in visible:
        if record.kind != "REVOKES":
            continue
        if (record.dst == subject or record.dst in role_names
                or record.payload.get("subject") == subject):
            revoked.append({"right": record.dst, "relation_id": record.relation_id,
                            "payload": dict(record.payload)})
    return {"subject": subject,
            "roles": sorted(roles, key=lambda i: i["role"]),
            "allowances": sorted(allowances, key=lambda i: (i["role"], i["target"])),
            "revoked": sorted(revoked, key=lambda i: i["right"])}
