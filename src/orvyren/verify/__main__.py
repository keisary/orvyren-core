#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Entry point: ``python -m orvyren.verify <target> [options]`` (B6 §2.3)."""

import sys

from .engine import main

if __name__ == "__main__":
    sys.exit(main())
