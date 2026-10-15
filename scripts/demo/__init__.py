#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — kit de démo testnet (W3-D).

Paquet ``scripts/demo`` : tout ce qui est nécessaire pour exécuter les **5 runs
de démonstration** (A ALLOW, B DENY hors chaîne, C DENY par la chaîne, D kill
switch, E journal/audit) sur Base Sepolia (chainId 84532) dès qu'un wallet
financé existe, **plus** les auto-tests hors chaîne (dry-run) qui tournent
sans réseau ni clé.

Règles du kit :

* **stdlib uniquement** — le SEUL module autorisé à importer une bibliothèque
  externe est :mod:`scripts.demo.signer` (``eth-account``, isolé, jamais
  importé par les autres modules) ;
* **aucun secret** : la clé ne vit que dans l'environnement du processus de
  signature (``ORVYREN_PRIVATE_KEY``), jamais dans un fichier, un journal ou
  une sortie écran ;
* **aucune transaction n'est envoyée en dry-run** ; en mode ``--execute`` le
  kit envoie uniquement ce que le préflight a autorisé ;
* **journal append-only chaîné SHA-256** (format B6 §1.3).

Références : ``FREEZE_V2.md`` E1/E2/E5 · ``research/B5_EXECUTION_ETUDE.md``
(§b intent, §c préflight 12 contrôles, §d receipt, §e runs) ·
``research/B4_POLITIQUE_ETUDE.md`` (14 règles, test de dérive 10 contrôles,
K0-K3) · ``research/B6_AUDIT_ETUDE.md`` (journal 3 flux, paquet 12 pièces) ·
``research/W2C_enveloppe_execution.md`` §g (montage Safe 2/3 + module Roles).

Aucun module d'ici n'a d'effet de bord à l'import.
"""

__all__ = ["common", "calls", "intents", "signer", "preflight", "demo", "verify_receipt",
           "build_audit_packet"]
