# ORVYREN — audit packet (rseth, run 01M526YS)

Testnet only (Base Sepolia, chainId 84532). No real funds were involved.
This packet is the execution-side record of the ORVYREN demo session
(`run_id = 01M526YS3FMDNS6Z9EJYJPPG1E`), assembled offline by `scripts/demo/build_audit_packet.py`.

## How to verify (offline, no network, no repository needed)

```bash
unzip audit_packet_rseth_01M526YS.zip && cd audit_packet_rseth_01M526YS
# 1) file integrity: every file against HASHES.txt (and the bundle digest)
python verify/verify_hashes.py .
# 2) execution journal: recompute the SHA-256 chain of audit.jsonl line by line
python verify/verify_hashes.py . --journal audit.jsonl
# 3) (optional, with network) re-read every tx hash and re-match it to its intent
python verify/verify_hashes.py . --rpc https://sepolia.base.org
```

`HASHES.txt` lists the sha256 of every file except itself, followed by
`bundle_digest = sha256(canonical_json(sorted(files \ {dossier_*.md, dossier_*.html, HASHES.txt})))`.

## What this audit packet proves

(1) **Integrity** — no byte of the dossier or its journals has changed since sealing: any alteration breaks a hash chain or the dossier self-hash (INV-INTEGRITY).
(2) **Recomputability** — every determinant computation (policy verdicts, dossier re-rendering, graph snapshot, intent↔receipt matching) is recomputed **offline** by a third party from the supplied pieces alone: same inputs, same versions, same outputs.
(3) **Intent↔execution correspondence** — each recorded transaction is tied to an intent and a policy verdict and cross-checked against the public receipt (status, block, logs).
(4) **Bounded mandate** — what the agent *could* do is a public, dated on-chain fact; the worst case is a finite, readable number.
(5) **Point-in-time admissibility (INV-PIT)** — every fact carries event and retrieval timestamps; data inadmissible at decision time is excluded from the decision path.
(6) **Refusals preserved** — policy denials, rejections, quarantines and abstentions are journaled and counted.
(7) **Channel independence (INV-DEPENDENCE)** — two channels from the same archive never count as two confirmations.
(8) **Accountability** — every step is attributed to a versioned component with its inputs and outputs.

## What this audit packet does not prove

(1) The **truthfulness** of external sources — an oracle can be wrong while every hash is valid.
(2) The **soundness** of hypotheses or the quality of decisions.
(3) Any **financial performance** (returns, avoided loss, superiority over a baseline) — none is claimed.
(4) **Completeness** — the packet covers signer actions and journaled steps; anything not journaled is not in it.
(5) **LLM call text is not replayed** (inference nondeterminism); it is **covered by the journal**.
(6) Absence of **bugs** in upstream components.
(7) **Legal or regulatory compliance** in any jurisdiction.
(8) A **sealed digest** (if anchored) proves the integrity and dating of the anchored dossier, **not its truthfulness**.

## Packet inventory

- `baseline_report.json` — extra: baseline_report.json
- `quality_report.json` — extra: quality_report.json
- `policy_execution_demo.json` — extra: policy_execution_demo.json
- `audit.jsonl` — journal d'exécution chaîné
- `receipts/0x17e94df4255b0f09132c4952ab90a199ed678df383c7e90db356c2590274ff05.json` — reçu brut
- `receipts/0x2d7eae5f5ab0917e629c0f8194b884ae4e968ecb21dfd2ce1f3494297060bf96.json` — reçu brut
- `receipts/0x34819b1da9f76417c3f480b6cd91c0ba41818092cb12690e0f5c8af363525641.json` — reçu brut
- `receipts/0x43bd6bf606afb2a02772ec20321428837b0d903c61853eed73e0bf7a53da0247.json` — reçu brut
- `receipts/0x508b13cf13b55fc17b44e2eb12bc7345d078e5284c62271a7c1b0098b81fefc9.json` — reçu brut
- `receipts/0x7548461ed0e49cf3b21a43377ffcf20b9de7e415fa746b252edebe212ba1b4ab.json` — reçu brut
- `receipts/0x82827c701e03852ae0e2176be1984ddfbc2420228cd9cd8db73986e2f6734f53.json` — reçu brut
- `receipts/0x8e6beda64ca8a9da6e839dd406cf7262eaeb986b602a2ad6e3ade5caff491d9e.json` — reçu brut
- `receipts/0xd7e2a7ae60a4438357b1222bb1d744d153a49dc07a8f2c0c995cd2145e0eee44.json` — reçu brut
- `receipts/0xd9d3b2fd9e54b8c5067e14c25f0336be1e3b59e4f754d53d53363f62aaf4c3a5.json` — reçu brut
- `receipts/0xe79f7771eecb1be4847ebcbfec864bf45b5b367a2ebbbc5dc115a56b6e09804e.json` — reçu brut
- `receipts/0xe9be566f82424857a0fff1406a452f7b99fbd0c1ee3cd0dfb021160e4227272b.json` — reçu brut
- `receipts/0xf3731d3bab01949c33be43cb687367a47680b55738966ed5b644319cd4356446.json` — reçu brut
- `policy/policy.effective.json` — politique versionnée
- `policy/policy.demo.json` — politique de démo
- `policy/intent_registry.json` — registre d'idempotence
- `policy/signatures.jsonl` — journal des signatures (compteur)
- `manifest.json` — manifeste de session
- `report.md` — rapport lisible
- `README_AUDIT.md` — mode d'emploi de vérification (EN)
- `verify/verify_hashes.py` — vérificateur hors-ligne minimal
- `verify/VERIFY_NOT_BUILT.txt` — note sur l'absence du vérificateur T10 complet
- `manifest.json` — manifeste du paquet
- `anchor/README_ANCHOR.txt` — note d'ancrage (reporté)
- `HASHES.txt` — sha256 de chaque fichier + bundle_digest
