# benchmark A0/A2 — provenance de la jambe A2 placebo (2026-10-18)

Annexe honnête au rapport `report.md` / `report.json` de ce répertoire (générés
par `run_benchmark_ab.py`, inchangés ici). À lire avec la table comparée.

## Ce qui a changé par rapport au rapport précédent

* **Avant** : jambe A2 de `placebo-calm-2023-03` = `not_executed`, motif
  `E_CASE_UNKNOWN: fixtures/agents/placebo-calm-2023-03/run_inputs.json missing`
  (3 runs).
* **Après** (ce rapport) : les 3 jambes A2 placebo **s'exécutent** — N scored
  12/12, bannière small-N intacte, aucune revendication de supériorité
  (N=12 < 100, G1).

## Origine des réponses A2 du placebo (étiquetage obligatoire)

* Case agent : `fixtures/agents/placebo-calm-2023-03/run_inputs.json` —
  **fixture SYNTHÉTIQUE** (`"synthetic": true`) : valeurs = paramètres déclarés
  de `fixtures/benchmark/cases.json` (`synthetic_corpus` : `price_base` 1.0,
  `price_wiggle` ±0.00010, `supply_value` constant), lignes estampillées
  `synthetic: true`, refs fabriquées du namespace
  `observation:synthetic/placebo-calm-2023-03/…`. **Aucune observation du
  monde, aucun chiffre réel inventé.**
* Magasin de réponses : `fixtures/agents/store_placebo-calm-2023-03/` —
  graine **scriptée** (`python scripts/agents_seed_demo.py --case
  placebo-calm-2023-03`), `SEED.json` déclare l'origine `scripted-demo`. Ce
  n'est **pas** une session live : les réponses LLM sont le scénario scripté de
  démonstration du script de seed (identique pour les deux cases), rejouées via
  le chemin d'enregistrement réel. Le rejeu `--replay journal` est
  déterministe et hors-ligne.

## Ce que la jambe A2 placebo mesure — et ce qu'elle ne mesure pas

* Mesuré (vrai code du produit) : sur ce case, les claims du scénario scripté
  citent `observation:chainlink/…` et `observation:bitstamp/…` que la série
  synthétique n'**observe pas** → la porte P0-6 les refuse visiblement
  (`status: REJECTED`, motif `E_REF_NOT_OBSERVED: …`, 2 claims par run dans
  `journal_orchestrator.jsonl`) ; sans preuve admissible la règle
  d'abstention forcée (DOC2 §5.2.4) met `inconclusive: true` → verdict
  **abstention**, `ARRET-1`, ACH vide (« aucune preuve »). La déclaration du
  case attend « NO_ACTION ou abstention justifiée » sur un placebo : les 3 runs
  sont `match`.
* **Non mesuré** : le comportement d'un LLM live sur un cas calme. La jambe
  rejoue un scénario scripté ; elle ne prouve ni ne réfute la qualité du
  raisonnement agent en live.

## Deux détails de rendu à connaître (décisions du propriétaire)

* `report.md` cite encore `expect_agents_note` de `cases.json` (« the A2 leg is
  not executable ») : note **périmée** depuis la graine — voir
  `docs/ECARTS_REGISTRE.md` F-1.
* La colonne « claims rejected (provenance) » affiche `0` alors que les
  journaux montrent 2 refus `E_REF_NOT_OBSERVED` par run : le compteur
  (`bench.count_provenance_rejections`) ne compte que
  `validation.provenance_ok == False` — voir `docs/ECARTS_REGISTRE.md` F-2.

## Reproduire

```bash
python scripts/agents_seed_demo.py --case placebo-calm-2023-03   # refuse sans --force si le store existe
python run_benchmark_ab.py --cases usdc-2023-03 placebo-calm-2023-03 \
    --runs 3 --out-dir evidence/benchmark_ab
```
