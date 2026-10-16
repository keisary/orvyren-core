# Rapport de calibration — SQUELETTE (N = 0)

> **NON CALCULÉ — N insuffisant** · **Jeu : (non renseigné — DEV et EVAL ne sont jamais fusionnés)** ·
> Date : 2026-10-16 · Référence normative : B7 §b.3–b.4, DOC2 §5.8.2 · Paquet de gel : `frozen/` (G1–G6, `Gx.sha256`).
>
> Ce fichier est le **squelette officiel à N = 0** exigé par le pré-enregistrement
> (FREEZE_V2 §7 ; B7 §d.3 : « Rapport de calibration **squelette** avec `N=0`
> ("non calculé") »). Il ne contient **aucun chiffre inventé** : chaque section
> indique ce qui sera publié et à quelle condition. Le seuil D11 (5 prévisions
> gelées résolues) n'est pas atteint dans ce rapport-ci ; 8 prévisions DEV
> existent par ailleurs (`frozen/forecasts_dev.jsonl`), mais leur rapport
> officiel suivra la même structure — avec le libellé « non conclusionnel ».

## 1. Périmètre et hashes

| Champ | Valeur |
|---|---|
| Jeu | *à renseigner : `dev` **ou** `eval` — jamais les deux dans un même rapport* |
| Épisodes | *à renseigner (fenêtres DEV : `dev-usdc-2023-03`, `dev-usdc-2023-02-temoin`, `dev-steth-2022-06`, `dev-steth-2022-05-calme` — cf. `frozen/G3_fenetres.md`)* |
| `N` (prévisions gelées résolues) | **0** |
| Période | *à renseigner* |
| `code_hash` | *calculé à la génération : `sha256` de `src/orvyren/evaluation/calibration.py` (courant : `frozen/G5_plan_analyse.md` §entête)* |
| `data_hash` | *calculé à la génération : `sha256` du corpus figé concerné* |
| Liste des `forecast_id` | *lien vers `frozen/forecasts_dev.jsonl` (chaîne `prev_hash` vérifiée)* |

Bannière obligatoire de tout artefact : **`DEV`** ou **`EVAL`** ou
**`REPLAY (journal/archive)`** — jamais implicite (B7 §c.5).

## 2. Tableau global

| Grandeur | Valeur | Condition de publication |
|---|---|---|
| `N` | 0 | publié tel quel |
| `ȳ` (climatologie) | — | exigé dès `N ≥ 5` (B7 §b.3) |
| `BS` (+ IC bootstrap) | — | `N ≥ 5` ; IC à `N ≥ 30` |
| `REL` / `RES` / `UNC` | — | `N ≥ 5` (identité `REL − RES + UNC = BS` exacte) |
| `ECE` (10 intervalles fixes) | — | calculable dès `N ≥ 5` ; **sans revendication** sous `N < 100` |
| `BSS` (+ borne basse d'IC) | — | `N ≥ 100` |
| **Verdict** | **« NON CALCULÉ — N insuffisant »** | seuil D11 (`N < 5`) |

## 3. Courbe de fiabilité

*Une ligne par intervalle (`bin`, `n_b`, `conf_b`, `acc_b`, IC de Wilson) —
intervalles vides **affichés**, jamais silencieux (B7 §b.1 C3/C4). Vide à `N = 0`.*

## 4. Décomposition par famille

*Par persona, par type d'événement (A/D/T), par épisode — **avec `N` affiché par
cellule** (B7 §b.4 item 4). Vide à `N = 0`.*

## 5. Annexe des prévisions

*Table `forecast_id | p | y | (p−y)² | horizon | résolveur`. Vide à `N = 0` ;
pour le jeu DEV courant, voir `frozen/FORECASTS_DEV.md` (8 prévisions, N=8,
libellé « non conclusionnel »).*

## 6. Anomalies et corrections

*Aucune : `N = 0`. Les corrections d'outcomes (`supersedes`), prévisions non
résolues (`UNRESOLVED`) et quarantaines seront listées ici **telles quelles** —
une prévision non résolue n'est pas cachée (B7 §a.5.4).*

## 7. Limites — en toutes lettres (obligatoires)

1. **N < 100 ⇒ « non établi »** : la calibration de la prévision reste **non
   établie** tant que `N < 100` hors échantillon (B7 §b.5) ; avec l'effectif
   réaliste du dossier (5–12 fenêtres), c'est l'état **par défaut** jusqu'après
   le concours.
2. **Contamination** : les épisodes 2022–2023 (et probablement 2025) sont dans
   les données d'entraînement des modèles de 2026 — le dossier démontre la
   **méthode**, pas une capacité prédictive.
3. **Non-échangeabilité** : toute couverture (conformale ou empirique) est
   conditionnelle à l'échangeabilité, violée par construction en crise ; on
   publie couverture prédite **et** empirique, jamais une garantie nue.
4. **Transférabilité** : la calibration mesurée sur un régime ne se transporte
   pas à un autre régime — on peut la mesurer, pas la garantir.
5. **Deux choses distinctes** : le Brier mesure les **prévisions**, la perte
   évitée / le P&L mesurent les **décisions** ; aucun score unique ne remplace
   l'autre, aucun scalaire agrégé n'est publié.
6. **`P(obligation)` et `p_s`** : hypothèses **signées** (G6), pas des
   estimations calibrées ; aucune fréquence publique n'existe (B7 §b.5 ;
   W2-D « Non trouvé » 4–6).

## 8. Verdict — langage contrôlé

> **NON CALCULÉ — N insuffisant.** Aucune revendication de calibration n'est
> émise (le mot « calibré » exige les **cinq conditions** de B7 §b.3 : `N ≥ 100`
> hors échantillon, `ECE ≤ 0,05` avec borne haute d'IC ≤ 0,08, courbe sans
> déviation systématique, borne basse de `BSS` > 0, ≥ 2 familles d'épisodes
> disjointes — et aucune revendication « calibré » sans ces cinq conditions,
> quelle que soit la pression du calendrier).

**Phrase obligatoire** (à recopier partout où un « 0 échec » apparaît, B7 §b.2) :
« 0/6 ne signifie pas taux nul, mais taux compatible avec jusqu'à ≈ 39 %
(borne supérieure de Wilson). »

---

*Comment ce squelette se remplit : `python run_calibration.py` (à construire,
B7 §e.6 item 7) lira `frozen/forecasts_dev.jsonl` + `frozen/outcomes_dev.jsonl`,
vérifiera le paquet de gel (`verify_frozen_package`), refusera `N < 5` et
écrira `calibration/rapports/<date>_<set>.md` + `.json`. Aucune écriture de
seuil : un rapport ne modifie rien (B7 §b.4).*
