> **EVAL** — rapport d'évaluation — jeu `eval` — N = 0 — non conclusionnel : N < 100 (cascade B7 §b.3)

# Rapport d'évaluation ORVYREN — EVAL

*hash de contenu* : `c2ed9ca28f3fa0aef491e31a5201549138749e6aa93003db03bf8a11b56e41ff` · *généré* : 2026-10-17T09:09:51Z · *fenêtres sautées* : 2

**Paramètres** : q = 100.0 · p_ref = 1.0 · k = 0.0 · tirages B0 = 200

> paramètres de démonstration DEV : q = 100 USDC (montant mobilisable du dossier), p_ref = 1,0, k = 0 (coûts non mesurés en DEV) — à geler pour l'EVAL

## Fenêtres (N = 0)

| Fenêtre | Statut | L(A0) | L(A1) | L(AX0) | L(A2) | R(A2) |
|---|---|---|---|---|---|---|
| `eval-rseth-2026-04` | SKIPPED | — | — | — | — | — |
| `eval-usd0pp-2025-01` | SKIPPED | — | — | — | — | — |

## Supériorité & placebo

- Statut des tests de supériorité : **NON CALCULÉ — N < 100** — tests de supériorité (Wilson, McNemar exact, bootstrap par blocs) exécutés seulement quand N ≥ 100 — le harnais refuse de publier un score agrégé unique (B7 §e.5)

## Limites (écrites avant lecture)

- Aucun score agrégé unique ; regrets R⁻/R⁺ publiés séparément (W2-D piège n°8).
- O = borne inférieure du regret (exécution au meilleur instant observé) — pas une vérité terrain.
- Substitutions DEV (P_exec = prix observé, k = 0, A2 = dossier déterministe) déclarées dans chaque fenêtre.

*Rapport reproductible : hash de contenu `c2ed9ca28f3fa0aef491e31a5201549138749e6aa93003db03bf8a11b56e41ff` (champs d'exécution réels exclus).*