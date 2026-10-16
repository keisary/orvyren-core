# G6 — Feuille de signature des hypothèses économiques

**Statut global : PROPOSÉ — en attente de signature.** 2026-10-16T00:00:00Z.
Protocole : FREEZE_V2 §C7 (« G6 signé par le chef d'équipe (défaut) + sensibilité publiée »).

Instructions : le signataire **coche** chaque paramètre qu'il valide, remplace les valeurs
marquées `NOT DONE` par ses propres valeurs (avec justification écrite), puis date et signe.
Tant que la feuille n'est pas signée, aucun résultat EVAL ne peut être revendiqué.

## Paramètres d'hypothèses économiques

| # | Paramètre | Valeur PROPOSÉE | Source de la proposition | COCHER |
|---|---|---|---|---|
| 1 | `opex_ref` (jours de runway) | 44 932 $/jour | ENS IPS 6.46 : 16,4 M$/an ÷ 365 (W2-D §A.1.1/E.1) | ☐ validé ☐ modifié → …………… |
| 2 | `P(obligation)` — exemple DEV USDC | 0,20 | valeur de travail de W2-D §E.2(b), explicitement non sourcée | ☐ validé ☐ modifié → …………… |
| 3 | `P(obligation)` — par fenêtre EVAL | NOT DONE (à fournir) | aucune source publique (W2-D §Non trouvé 6) | ☐ fourni ci-dessous |
| 4 | Scénarios desk (liste) | réalisé · non-rétablissement 48 h · guérison lente 5 j · venue unique contrainte 0,80526 | W2-D §(f) 7 | ☐ validé ☐ modifié → …………… |
| 5 | `p_s` (probabilités des scénarios) | NOT DONE (à fournir) | aucune distribution publique (W2-D §Non trouvé 4) | ☐ fourni ci-dessous |
| 6 | `r_capital` (financement desk) | NOT DONE (à fournir) | B7 Q16 — non trouvé | ☐ fourni ci-dessous |
| 7 | Coût d'aller-retour (illustration desk) | 20 bp | W2-D §E.3 (« hypothétique, à mesurer ») | ☐ validé ☐ modifié → …………… |

## Valeurs à fournir (le cas échéant)

* `P(obligation)` par fenêtre EVAL (justification écrite par fenêtre) :
* `p_s` des scénarios desk (avec sensibilité) :
* `r_capital` (source ou hypothèse écrite) :

## Signatures

| Rôle | Nom | Date (UTC) | Signature / hash du commit de signature |
|---|---|---|---|
| Chef d'équipe (défaut, FREEZE_V2 §C7) | | | |
| Témoin (optionnel) | | | |

**Rappel d'embargo** : après la première exécution EVAL, toute modification de ces
paramètres **invalide** l'évaluation (re-étiquetage obligatoire) — pas « affaiblit » (B7 §d.2.1).
