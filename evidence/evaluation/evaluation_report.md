> **DEV** — rapport d'évaluation — jeu `dev` — N = 4 — non conclusionnel : N < 100 (cascade B7 §b.3)

# Rapport d'évaluation ORVYREN — DEV

*hash de contenu* : `b3ef5eab4d26b540ed5046938c420ba580d3181396b58f6b985b095a7e7d5fbf` · *généré* : 2026-10-17T01:24:24Z · *fenêtres sautées* : 0

**Paramètres** : q = 100.0 · p_ref = 1.0 · k = 0.0 · tirages B0 = 200

> paramètres de démonstration DEV : q = 100 USDC (montant mobilisable du dossier), p_ref = 1,0, k = 0 (coûts non mesurés en DEV) — à geler pour l'EVAL

## Fenêtres (N = 4)

| Fenêtre | Statut | L(A0) | L(A1) | L(AX0) | L(A2) | R(A2) |
|---|---|---|---|---|---|---|
| `dev-usdc-2023-03` | OK | 0.0614 | 0.5762 | 2.0174 | 0.1287 | 0.4466 |
| `dev-usdc-2023-02-temoin` | OK | -0.3000 | -0.3000 | -0.3000 | — | — |
| `dev-steth-2022-06` | OK | 2.6353 | 2.8462 | — | — | — |
| `dev-steth-2022-05-calme` | OK | 0.2227 | 0.2227 | — | — | — |

## Agrégats par config (N affiché par ligne ; R⁻ ≠ R⁺, jamais moyennés ensemble)

| Config | N | L moyen | R⁺ moyen | R⁻ moyen |
|---|---|---|---|---|
| A0 | 4 | 0.6548 | 0.9190 | 0.0000 |
| A1 | 4 | 0.8363 | 1.1004 | 0.0000 |
| AX0 | 2 | 0.8587 | 1.6677 | 0.0000 |
| A2 | 1 | 0.1287 | 0.4466 | 0.0000 |

## Supériorité & placebo

- Statut des tests de supériorité : **NON CALCULÉ — N < 100** — tests de supériorité (Wilson, McNemar exact, bootstrap par blocs) exécutés seulement quand N ≥ 100 — le harnais refuse de publier un score agrégé unique (B7 §e.5)

## Limites (écrites avant lecture)

- Aucun score agrégé unique ; regrets R⁻/R⁺ publiés séparément (W2-D piège n°8).
- O = borne inférieure du regret (exécution au meilleur instant observé) — pas une vérité terrain.
- Substitutions DEV (P_exec = prix observé, k = 0, A2 = dossier déterministe) déclarées dans chaque fenêtre.

*Rapport reproductible : hash de contenu `b3ef5eab4d26b540ed5046938c420ba580d3181396b58f6b985b095a7e7d5fbf` (champs d'exécution réels exclus).*