# Handoff Sprint 2 — W4 (Politique & Sécurité) — lot `feat/policy-14-rules`

**De :** Uriel (UnoriginalDude14) · **Pour :** keisary · **Date :** 2026-10-16
**Branche :** `feat/policy-14-rules` · **Commit :** `71737e5`
**Fait par :** Cally (agent d'Uriel) — pour revue, **pas mergé** (seul le coordinateur merge).

Ce fichier est un **handoff** : les commandes ci-dessous sont à coller telles quelles
(terminal ou Hermes). Aucune n'écrit hors du dépôt, toutes en lecture seule sauf mention.

---

## 0. Puller la branche

```bash
cd ~/orvyren_core 2>/dev/null || cd /chemin/vers/orvyren-core
git fetch origin feat/policy-14-rules
git checkout feat/policy-14-rules
git log --oneline -1   # attendu : 71737e5 policy: v1 set completed to 14 rules...
```

## 1. Vérifier (offline, ~6 s)

```bash
python -m pytest tests/ -q            # attendu : 478 passed, 4 skipped
```

ou sans pytest :

```bash
python -m unittest discover -s tests  # attendu : Ran 478 tests ... OK (skipped=4)
```

## 2. Test de dérive — offline (conformité politique ↔ fixture)

```bash
python scripts/run_drift_check.py --offline --quiet
```

Attendu : `PASS` (code de sortie 0). Sans `--quiet`, imprime les 10 contrôles D1–D10.

## 3. Test de dérive — live (lecture seule, Base Sepolia)

```bash
python scripts/run_drift_check.py --rpc --quiet
```

Attendu : `PASS` (code 0). Vérifie chainId, empreintes de bytecode épinglées, et
**rejoue les refus** du paquet d'audit du 16/10 par `eth_call` (membre du rôle,
condition destinataire, dépassement d'allowance). Jamais de signature, jamais de tx.

**Codes de sortie** : `0` PASS · `2` DRIFT (SAFE MODE) · `3` UNVERIFIED (SAFE MODE) · `4` usage.

## 4. Démo dérive simulée (preuve que SAFE MODE se déclenche)

```bash
python -m unittest tests.test_policy_zodiac_conformance -v
```

Les 6 dérives simulées (allowance réduite, cible large, quota modifié, destinataires
vides, révocation retirée, clé de rôle changée) doivent toutes donner `DRIFT` + SAFE MODE.

## 5. Ouvrir la PR

```
https://github.com/keisary/orvyren-core/pull/new/feat/policy-14-rules
```

Sujet suggéré : `policy: v1 set completed to 14 rules (P-numbering) + policy_v1.yaml, drift check`
Corps : copier le message du commit (`git log -1 --format=%B`).

---

## Ce que contient le lot (récap)

| Pièce | Rôle |
|---|---|
| `src/orvyren/policy/__init__.py` | 14 règles (P1–P14), `PolicyState` fail-closed, empreinte d'intent, version+hash dans chaque verdict |
| `src/orvyren/policy/miniyaml.py` | mini-lecteur YAML strict **stdlib** (pas de PyYAML — cœur stdlib-only) |
| `policy_v1.yaml` | source de vérité des **paramètres** (DOC2 §5.5.3) |
| `scripts/run_drift_check.py` | 10 contrôles de dérive, offline + live, verdict → SAFE MODE |
| `fixtures/roles_agent_config.json` | fixture d'enveloppe réelle (proxy 45 o + singleton 24 409 o, sondes replay) |
| `evidence/envelope_drift_report.json` | rapport live versionné (verdict PASS) |
| `docs/decisions/ADR-0002-*.md` | contrat bundle/version + procédure de changement 6 étapes |
| `tests/test_policy*.py` | banc complété : 14 règles, frontières, conformance, dérives simulées |

Les artefacts dépendants ont été **régénérés** (dossier, policy demo, pipeline summary,
quality report) à cause du passage R→P : empreintes recalculées.

---

## Reste à faire (hors de ce lot)

1. **W5 — wiring du kit** : brancher `PolicyReference.as_policy_config` → `load_policy()` +
   construire un `PolicyState` complet (pause, membre, solde, enveloppe, budget).
   Tant que c'est pas fait, le kit tourne en **mode legacy** (`SKIPPED` pour
   P4/P7/P9/P11/P12/P14) — documenté dans ADR-0002.
2. **Getters Roles** : confirmer les getters du module (B4 §d.3 annexe 4) pour passer
   D4–D8 du mode fixture au mode lecture directe.
3. **W3 — RDOF** : en attente des lots W1/W2 (graphe + registre d'hypothèses).
4. **Docstrings kit** : `scripts/demo/common.py` mentionne encore « règles R1–R8 »
   (fichier W5, non touché ici) — à aligner en P1–P14 au moment du wiring.

## Note

Rien n'a été touché hors de `feat/policy-14-rules` : `master` est intact, le kit démo
(`scripts/demo/`) est intact, aucun secret ni clé dans le dépôt (scan CI sur les fichiers
ajoutés : rien de suspect).
