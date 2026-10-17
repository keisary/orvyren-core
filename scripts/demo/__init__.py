#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — testnet demo kit (W3-D).

``scripts/demo`` package: everything needed to run the **5 demo runs**
(A ALLOW, B off-chain DENY, C chain-level DENY, D kill switch,
E journal/audit) on Base Sepolia (chainId 84532) as soon as a funded wallet
exists, **plus** the off-chain self-tests (dry-run) that run
without network or key.

Kit rules:

* **stdlib only** — the ONLY module allowed to import an external library
  is :mod:`scripts.demo.signer` (``eth-account``, isolated, never
  imported by the other modules);
* **no secret**: the key lives only in the signing process environment
  (``ORVYREN_PRIVATE_KEY``), never in a file, a journal or
  a screen output;
* **no transaction is sent in dry-run**; in ``--execute`` mode the
  kit sends only what the preflight authorized;
* **SHA-256 chained append-only journal** (format B6 §1.3).

References: ``FREEZE_V2.md`` E1/E2/E5 · ``research/B5_EXECUTION_ETUDE.md``
(§b intent, §c 12-check preflight, §d receipt, §e runs) ·
``research/B4_POLITIQUE_ETUDE.md`` (14 rules, 10-check drift test,
K0-K3) · ``research/B6_AUDIT_ETUDE.md`` (3-stream journal, 12-piece packet) ·
``research/W2C_enveloppe_execution.md`` §g (2/3 Safe setup + Roles module).

No module here has an import side effect.
"""

__all__ = ["common", "calls", "intents", "signer", "preflight", "demo", "verify_receipt",
           "build_audit_packet"]
