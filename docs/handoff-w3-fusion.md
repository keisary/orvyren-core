# Handoff — W3 : fusion des deux implémentations (17/10/2026)

**Contexte.** Deux W3 ont été menés en parallèle : `e9c0bbd` (keisary —
« RDOF v1 discriminating search + 3 separated axes + abstention A1-A5 + bounded
action catalogues ») et la branche `Unoriginal` (Uriel — « W3 RDOF v1 +
DecisionRecord + catalogues YAML »). Comparaison des deux arbres faite le 17/10,
puis fusion « le meilleur des deux » sur master :

- **cœur conservé de keisary** : les effets des prédicats sont calculés par
  **contre-épreuve réelle** (re-classification du corpus gelé avec injection
  d'issue) — jamais codés en dur — et l'essai T02/HYP-02R est intégré ;
- **pièces ajoutées depuis `Unoriginal`** : les trois exigences du [DONE] qui
  manquaient (la commande, `actions_v1.yaml`, le test « aucun nombre d'agent »)
  et le lot L3.1 (branchement registre de W2).

## Ajouté par la fusion

- **La commande** `python -m orvyren.decide --case usdc-2023-03 --replay`
  (`src/orvyren/decide.py`) : corpus gelé → `run_case` → `build_dossier`
  (3 axes + RDOF + abstention) → enregistrement registre W2 → **DecisionRecord**
  écrit dans `evidence/decision_record_usdc-2023-03.json` : 3 axes séparés,
  `intent` borné (ou NO-ACTION/INCONCLUSIVE), rationale, `evidence_refs[]`,
  coût réel de recherche. Le dossier machine `evidence/decision_usdc-2023-03.json`
  reste produit par `run_decision.py` (inchangé).
- **`config/actions_v1.yaml`** : source de vérité des 12 actions (8 DAO + 4 desk,
  contenu de keisary conservé au mot près), chargée par `catalog.py` avec le
  mini-YAML strict stdlib de W4 ; `check_applicability` (test d'applicabilité
  par action) ; chargement fail-closed testé.
- **L3.1** (`src/orvyren/decision/records.py`) : hypothèses falsifiables
  (critères S/R obligatoires, pas de p∅ silencieux, prédicats instrumentés
  uniquement) enregistrées dans le registre d'hypothèses de W2. Un nombre
  produit par un agent ne peut pas déclencher un critère (refus testé).
- **Tests ajoutés** : `tests/test_decide_cli.py` (la commande, 3 axes,
  INCONCLUSIVE sur entrée manquante, déterminisme octet),
  `tests/test_decision_records.py` (L3.1), `tests/test_actions_catalog_yaml.py`
  (12 actions, applicabilité par action, fail-closed).

## Non repris de la branche `Unoriginal` (et pourquoi)

- `decision/rdof.py` d'Uriel : remplacé par celui de keisary — mêmes 5 règles
  (évaluabilité, effets, ordonnancement gelé, exécution, arrêts c1/c2) mais
  effets par re-classification réelle et comparaison à l'ordre fixe intégrée.
- `abstention.py`, `price.py`, `axes` d'Uriel : la version câblée sur les
  verdicts réels et le service de politique (axe 3) est conservée.
- La branche `Unoriginal` reste poussée sur origin pour l'historique.

## Vérifications

- `python -m unittest discover -s tests` → **755 tests — OK (751 verts, 4 sautés)**
  (4 sautés : 2 live-RPC opt-in + 2 conditionnels `eth-account`).
- `python run_pipeline.py` → vert (qualité → décision → politique → audit).
- `PYTHONPATH=src python -m orvyren.decide --case usdc-2023-03 --replay` →
  exit 0 ; record : `epistemic_verdict=CONCLUANT`, `economic_action=CONVERTIR/TRANSFÉRER`,
  RDOF arrêt c1 après 1 recherche (**P-6.3**, 0,65 s), 3 hypothèses `CREATED`
  au registre.
- Deux exécutions de la commande → fichiers identiques à l'octet près.

## À noter (hors périmètre de la fusion)

- `evidence/decision_usdc-2023-03.json` committé date de `355da23` (v0, sans
  axes) : il se régénère enrichi (axes + RDOF + abstention) via
  `python run_decision.py`. Un rafraîchissement global des artefacts
  (`decision_*`, dossier, `pipeline_summary`) reste à faire par le coordinateur
  lors du prochain passage — la régénération change les horodatages du dossier.
