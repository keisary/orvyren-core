# G4 — Seuils par persona (gel v1, statut PROPOSÉ)

**Statut : PROPOSÉ — à valider avant la première exécution EVAL** — 2026-10-16T00:00:00Z.
Sources : W2-D §C.4.1 (DAO), §C.4.2 (desk), B7 §e.3/e.4 (métriques). Les valeurs
ci-dessous sont **reprises telles quelles** des documents sources, qui les
marquent explicitement « propositions à valider, pas des faits ».

## 1. Persona DAO (trésorerie)

| Code | Critère | Formulation | Valeur proposée |
|---|---|---|---|
| SD1 | Perte évitée matérielle | `(L(A0) − L(A2)) / q` en % de l'exposition, conditionnellement à l'obligation ; second affichage en jours de runway | ≥ 5 % |
| SD2 | Friction maîtrisée | coût cumulé de A2 sur fenêtres CALME | ≤ 10 % de la perte évitée de crise |
| SD3 | Anticipation | antériorité vs point bas du prix réalisable ; délai de réaction | ≥ 6 h sur ≥ 1 épisode EVAL ; ≤ 60 min |
| SD4 | Supériorité | `R̄(A2) < R̄(A1)` et `< R̄(B0)`, avec intervalles, R⁻/R⁺ séparés | strictement inférieur |
| SD5 | Traçabilité | provenance + hash sur 100 % des actions ; 0 action hors enveloppe | 100 % / 0 |
| SD6 | Honnêteté | « non conclusionnel » partout où la puissance manque ; perte évitée publiée `P × conditionnel` | présent/absent |

## 2. Persona desk (P&L)

| Code | Critère | Formulation | Valeur proposée |
|---|---|---|---|
| ST1 | P&L net cumulé | tous coûts inclus (frais, slippage mesuré, financement) + intervalle bootstrap par blocs | > 0 |
| ST2 | Qualité d'exécution | slippage réalisé vs échelle `get_dy` ; taille ≤ Depth_100bp | ≤ 30 bp en stress |
| ST3 | Risque borné | MaxDD de la série de décisions sur le capital alloué | ≤ 20 % par épisode |
| ST4 | Risque ajusté | Sharpe/Sortino + DSR corrigé du nombre de variantes | borne basse d'IC > 0 sinon « non conclusionnel » |
| ST5 | Supériorité | `ΔP&L(A2) > ΔP&L(A1)` et `> ΔP&L(B0)` avec intervalles | strictement supérieur |
| ST6 | Asymétrie déclarée | agent décrit comme un put ; scénarios `p_s` publiés | présent/absent |

## 3. Anti-optimisme commun (dispositifs obligatoires)

B0 (M ≥ 200, distribution complète) · fenêtres CALME obligatoires dans les deux jeux ·
`ȳ` publié partout · Wilson sur toute proportion · bootstrap par blocs (6–12 h, 10 000
réplications, graine fixée) · DSR/journal des variantes · R⁻/R⁺ séparés + table de
contingence · mention de contamination · « ce que nous ne revendiquons pas » ·
**un scalaire est interdit** (vecteur de métriques + axes non mesurés déclarés).

## 4. NOT DONE

Les seuils SD/ST ne sont **pas encore lus par du code** (le harnais §e.6 items 6–7 n'est pas
construit) : ce document les gèle en tant que déclaration, la vérification exécutable
viendra avec `harness.py`. Toute modification après la première exécution EVAL invalide
l'évaluation (embargo de paramètres).
