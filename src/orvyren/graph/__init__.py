"""Evidence graph: objects, append-only store and provenance checks.

Depends on ``quality`` only (contract: ``quality -> graph``). Objects are
frozen dataclasses; every content-bearing object can be fingerprinted with a
canonical JSON serialisation, which is what makes the audit trail verifiable.
"""
