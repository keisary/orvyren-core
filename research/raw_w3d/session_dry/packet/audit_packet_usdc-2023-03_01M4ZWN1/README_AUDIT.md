# ORVYREN — audit packet (usdc-2023-03, run 01M4ZWN1)

Testnet only (Base Sepolia, chainId 84532). No real funds were involved.
This packet is the execution-side record of the ORVYREN demo session
(`run_id = 01M4ZWN1JW9E9GWQ5CXMAAE6AT`), assembled offline by `scripts/demo/build_audit_packet.py`.

## How to verify (offline, no network, no repository needed)

```bash
unzip audit_packet_usdc-2023-03_01M4ZWN1.zip && cd audit_packet_usdc-2023-03_01M4ZWN1
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

- `dossier_usdc-2023-03.md` — dossier md (self-hash)
- `dossier_usdc-2023-03.html` — dossier html (self-hash)
- `decision_usdc-2023-03.json` — vérité machine du dossier
- `baseline_report.json` — extra: baseline_report.json
- `quality_report.json` — extra: quality_report.json
- `policy_execution_demo.json` — extra: policy_execution_demo.json
- `audit.jsonl` — journal d'exécution chaîné
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
