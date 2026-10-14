"""Audit dossier package (ORVYREN-Core v0.1).

``orvyren.audit.dossier`` renders the one-page, tamper-evident decision
dossier (Markdown + self-contained HTML) from the engine's JSON artefacts.
"""

from .dossier import build  # noqa: F401

__all__ = ["build"]
