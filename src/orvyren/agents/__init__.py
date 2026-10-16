"""Agent-side artefacts: the private reasoning journal (``agent_journal``).

Separate from the evidence graph by design (DOC4 L2.3): journal lines are
private reasoning, never injected anywhere without a **promotion**, and a
promotion goes through **deterministic validators** only. LLM-proposed
branches carry **zero weight** until validated.

Standard library only.
"""
