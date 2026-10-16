#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — CLI racine : vérificateur tiers T10 (paquets d'audit v2).

Alias pratique de ``PYTHONPATH=src python -m orvyren.verify`` (le paquet n'est
pas installé ; la forme module reste disponible pour l'intégration).

Usage :
    python run_verify.py <paquet.zip|dossier> [--rpc URL] [--mutate-test] [--json rapport.json]
    python run_verify.py . --offline

Un paquet d'audit livré à un tiers embarque sa **copie gelée** du vérificateur
(``verify/orvyren_verify.py``) : le tiers n'a besoin ni du dépôt ni d'autre
chose que la bibliothèque standard — voir ``README_AUDIT.md`` dans le paquet.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))

from orvyren.verify.engine import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
