# W5 — Exécution & Démo testnet : bilan des lots L5.1–L5.6

Statut : **livré**. Références : `ORVYREN_DOC4.md` §W5, B5 (exécution), B6 §1.3.
Démo on-chain exécutée le **2026-10-16** sur Base Sepolia (chainId 84532,
testnet uniquement — aucune valeur réelle). Les scripts de montage/hygiène
manquants (L5.2) ont été ajoutés le jour de la revue W5/W6.

| Lot | Contenu spec | Livrable dans l'arbre | Preuve | Statut |
| --- | --- | --- | --- | --- |
| **L5.1** | Kit de démo : Safe 2/3 + module Roles v2 + rôle `AGENT` + allowance `usdc_daily` ; deux USDC distincts nommés (Circle = transferts, Aave = lectures) ; robinets gratuits | `scripts/demo/setup_chain.py`, `scripts/demo/dao_assign_roles.py`, `scripts/demo/policy.demo.json`, `scripts/demo/config.example.env` | adresses mesurées dans `.env` ; rôle bytes32 `0x4147454e54…` ; allowance refill 300e6 / période 86400 | ✅ |
| **L5.2** | Scripts de montage & hygiène : `generate_signer_key`, `check_env_hygiene`, `verify_addresses` (getCode + chainId + blockNumber, **arrêt si écart**), `faucet_check` | `scripts/demo/generate_signer_key.py`, `check_env_hygiene.py`, `verify_addresses.py`, `faucet_check.py` (**ajoutés 16/10**) + `tests/test_env_hygiene.py` | smoke : 10 adresses mappées (Safe/Module/USDC = contrats, agent/propriétaires = EOA, chainId 84532 ✓) ; hygiène **OK** (280 fichiers suivis scannés, 0 clé versionnée, `.gitignore` ✓) ; clé dérivée == `ORVYREN_AGENT_ADDRESS` | ✅ |
| **L5.3** | Service signataire isolé — seul lecteur de la clé, processus séparé, nonce/retries bornés | `scripts/demo/signer.py` (**nom dans l'arbre** ; rôle identique à `signer_service.py` de la spec — écart de nommage déclaré) | invariants S2/S3/S7/S10 ; mode `--dry-run` par défaut, `--execute` refusé sur placeholders ; runs A–E signés par ce module | ✅ |
| **L5.4** | Préflight **12 contrôles** (dont simulation `eth_call`) + politique de confirmations + **anti-reorg 2 blocs** | `scripts/demo/preflight.py` (P1–P12 + test de dérive D1–D10 ; 1 échec ⇒ aucune signature) | rapport préflight du run ; couvert par `tests/test_demo_kit.py` | ✅ |
| **L5.5** | Vérification de reçu (champs exacts, correspondance intent ↔ logs, cas revert/partiel) + liaison vers l'audit | `scripts/demo/verify_receipt.py` + `scripts/build_audit_packet.py` (v2 : contrôle A8 du vérificateur) | 13 reçus réels cross-checkés (A8 PASS) ; refus chaîne `status 0x0` + sélecteur `0xfd8e9f28` (NoMembership) journalisés | ✅ |
| **L5.6** | Exécution des **5 runs** + captures (reçus, blocs, émetteur/destinataire, statuts `0x0`, chronométrage kill switch) | `evidence/demo_runs/rseth/` : `audit.jsonl`, `receipts/` (13), `report.md`, `runA_console.log`…`runE_console.log`, `policy.effective.json`, `intent_registry.json` | tx on-chain Base Sepolia ; export E : **écart journal ↔ chaîne = 0** | ✅ |

## Écarts déclarés (jamais cachés)

- **L5.3** : implémenté sous le nom `signer.py` (la spec disait `signer_service.py`) — même rôle, même isolation.
- **Flux « agent » (raisonnement)** : la démo d'exécution tourne **sans LLM** (clé DeepSeek absente au montage) ; le paquet d'audit déclare le flux agent **absent avec raison** dans le manifeste — aucun flux simulé n'est jamais présenté comme réel.
- **`scripts/demo/build_audit_packet.py`** : builder historique du kit (v1) ; le paquet complet T10 est construit par `scripts/build_audit_packet.py` (v2, racine du dépôt).
- **Journal v1** : les tentatives refusées hors chaîne (run B) ont un `POLICY`/`OUTCOME` sans `INTENT` (trou de journalisation du kit v1) — le vérificateur les classe en **écarts déclarés** (liste explicite dans le rapport), jamais en silences.

## Reproductibilité / commandes

```bash
python scripts/demo/verify_addresses.py --rpc      # adresses : contrats/EOA + chainId (arrêt si écart)
python scripts/demo/faucet_check.py --rpc          # ETH agent + USDC Safe (robinets gratuits)
python scripts/demo/check_env_hygiene.py           # rien de versionné, aucune valeur de clé suivie
python scripts/demo/generate_signer_key.py --check # adresse dérivée == déclarée
python scripts/demo/demo.py --run A --dry-run      # répétition hors chaîne (aucune signature)
python scripts/build_audit_packet.py --session evidence/demo_runs/rseth --case rseth
```

Suite W6 (vérificateur tiers T10) : `python run_verify.py <paquet>` (ou
`PYTHONPATH=src python -m orvyren.verify <paquet>`) — et, pour un tiers sans
dépôt, la copie gelée embarquée : `python verify/orvyren_verify.py .` — voir
`README_AUDIT.md` livré dans chaque paquet d'audit.
