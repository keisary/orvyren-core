# ADR-0001 — Gel G1–G6 v1 : paquet d'évaluation pré-enregistré (Sprint 0)

**Date :** 2026-10-16 · **Statut : ACCEPTÉE (v1)** · **Décideur :** chef d'équipe
(protocole de gel FREEZE_V2 §I1) · **Portée :** bloc G (évaluation) uniquement.

## Contexte

Le concours Shenzhen FinTech 2026 (thème F) impose un protocole d'évaluation
**pré-enregistré** : l'évaluation doit être gelée, hachée et opposable **avant**
toute exécution sur le jeu d'évaluation (FREEZE_V2 §7 G1–G6 ; B7 §d.2 ; DOC2
§5.8.4). Au 15/10/2026, l'état du dépôt était : **zéro prévision gelée**, gel
G1–G6 non signé, paquet `frozen/` inexistant, couche `evaluation/` absente
(B7 §0.11 — blocages recensés). Sans pré-enregistrement, aucun chiffre publié
n'est défendable : un résultat non gelé est indistinguable d'un réglage a
posteriori.

## Options examinées

1. **Attendre la fin du harnais complet** (items 1–7 de B7 §e.6) avant de geler
   quoi que ce soit — rejetée : le calendrier de soumission (J2, « inscription au
   plus vite ») ne le permet pas, et un gel partiel est plus fort que pas de gel.
2. **Geler les seuls paramètres textuels** (déclaration G4/G6) — rejetée : sans
   code gelé et sans prévisions hachées, le gel ne vérifie rien mécaniquement.
3. **Geler la couche minimale exécutable** : fonction de perte + comparateurs +
   calibration + fenêtres + prévisions/outcomes, avec le paquet `frozen/`
   recalculable hors-ligne et 5–10 prévisions DEV hachées — **retenue** (c'est le
   chemin critique identifié par B7 §e.7 : « items 1, 2, 5 + le gel G1–G2 hashés
   + un run DEV »).

## Décision

1. **G1–G6 v1 gelés** dans `frozen/` : G1 perte, G2 comparateurs, G3 fenêtres +
   embargos, G4 seuils persona (**PROPOSÉ**), G5 plan d'analyse, G6 hypothèses
   économiques (**PROPOSÉ — en attente de signature**, `G6_FEUILLE_DE_SIGNATURE.md`).
2. Chaque document porte un manifeste `Gx.sha256` (format `sha256sum`) ; la porte
   `verify_frozen_package` **refuse toute écriture** (prévision/outcome/EVAL)
   si un manifeste manque ou ne concorde pas.
3. **8 prévisions DEV pré-enregistrées** (`frozen/forecasts_dev.jsonl`), chaînées
   par `prev_hash`, chacune avec `p` issue d'un **comptage empirique déterministe**
   (fenêtres de calibration, fenêtre cible exclue — LOO), résolues par le
   résolveur déterministe (`frozen/outcomes_dev.jsonl`, règle `sustained_depeg_v1`
   et `calm_window_v1`). Résultat : N = 8, ȳ = 0,5 — libellé de la cascade
   **« non conclusionnel »** (B7 §b.3), publié tel quel.
4. **Le paquet est recalculable hors-ligne** (`python scripts/freeze_sprint0.py`,
   preuve `python scripts/verify_frozen.py` : recalcul octet à octet en < 2 s).
5. **Ce qui n'est pas dérivable n'est pas inventé** : fenêtres CALME EVAL
   2025–2026 (B7 Q6), `Depth_ε`, `r_capital`, `P(obligation)` EVAL, `p_s` desk —
   écrits **NOT DONE** avec motif dans G3 §4 et G6 §1.
6. **Collision d'étiquettes tranchée** conformément à B7 §e.1 : A0 = NO-ACTION,
   A1 = seuil, A2 = agent, B0 = placebo (M ≥ 200, graine fixée), AX0 = règle
   gelée du dépôt (déléguée à `decision/baseline.py`), O = oracle faisable.

## Conséquences

* **Positives** : l'évaluation devient opposable dès maintenant ; toute
  modification ultérieure d'une constante G1–G6 détectable mécaniquement
  (hash) ; la chaîne prévision → outcome est vérifiable par un tiers hors-ligne ;
  la démonstration DEV existe (méthode), sans aucune revendication de performance.
* **Contraintes** : toute modification de `loss.py`, `comparators.py`,
  `windows.py`, `calibration.py`, `forecasts.py`, `outcomes.py` **oblige à
  régénérer `frozen/`** (les documents G portent les empreintes du code) ; après
  la première exécution EVAL, toute modification de G1–G6 **invalide**
  l'évaluation (re-étiquetage obligatoire, pas « affaiblissement » — B7 §d.2.1).
* **Coût** : ~0 (hors-ligne, stdlib, quelques secondes de recalcul).
* **Reste à faire (non bloquant pour la soumission)** : signature G6
  (chef d'équipe), harnais A0/A1/A2/B0 (B7 §e.6 items 6–7), fenêtres CALME
  EVAL 2025–2026, une passe EVAL unique après gel.

## Références

`FREEZE_V2.md` §7 et §I1 · the v1 design notes (archived out of the repository) §5.8 ·
B7 §d.2, §e.1, §e.6, §e.7, §b.2–b.4 (archive) · W2-D §B.1/B.6, §C.4 (archive) ·
`frozen/` (paquet v1, empreintes `Gx.sha256`).
