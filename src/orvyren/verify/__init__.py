"""ORVYREN verify package — third-party verifier T10 (W6).

`python -m orvyren.verify <target>` recomputes the determinant checks of an
audit packet offline (B6_AUDIT_ETUDE.md §2). See engine.py for the full
specification and the module docstrings for the frozen-packet distribution.
"""

from .engine import main, render_markdown, verify_packet  # noqa: F401

__all__ = ["main", "verify_packet", "render_markdown"]
