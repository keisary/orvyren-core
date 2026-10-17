#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — root CLI: third-party T10 verifier (audit packets v2).

Convenience alias of ``PYTHONPATH=src python -m orvyren.verify`` (the package is
not installed; the module form remains available for integration).

Usage:
    python run_verify.py <packet.zip|directory> [--rpc URL] [--mutate-test] [--json report.json]
    python run_verify.py . --offline

An audit packet delivered to a third party embeds its **frozen copy** of the
verifier (``verify/orvyren_verify.py``): the third party needs neither the
repository nor anything beyond the standard library — see ``README_AUDIT.md``
inside the packet.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))

from orvyren.verify.engine import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
