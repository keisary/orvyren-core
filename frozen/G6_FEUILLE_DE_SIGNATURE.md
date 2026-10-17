# G6 — Feuille de signature des hypothèses économiques

**Statut global : SIGNÉ — validé le 2026-10-17.** 2026-10-16T00:00:00Z.
Protocole : FREEZE_V2 §C7 (« G6 signé par le chef d'équipe (défaut) + sensibilité publiée »).
Signataire : **AKUE-BITCHI Adote Jovanny** — validation électronique du chef d'équipe — autorisation explicite dans la session Hermes du 2026-10-17 ; une copie manuscrite scannée peut être jointe à la soumission.

Instructions : le signataire coche chaque paramètre validé, renseigne les valeurs
marquées `NOT DONE`, date et signe. Les valeurs ci-dessous sont celles de la
première EVAL ; toute modification après cette exécution exige une re-signature
nommée et un re-étiquetage.

## Paramètres d'hypothèses économiques

| # | Paramètre | Valeur signée | Source de la proposition | COCHER |
|---|---|---|---|---|
| 1 | `opex_ref` (jours de runway) | 44 932 $/jour | ENS IPS 6.46 : 16,4 M$/an ÷ 365 (W2-D §A.1.1/E.1) | ☑ validé ☐ modifié → …………… |
| 2 | `P(obligation)` — exemple DEV USDC | 0,20 | valeur de travail de W2-D §E.2(b), explicitement non sourcée | ☑ validé ☐ modifié → …………… |
| 3 | `P(obligation)` — par fenêtre EVAL | **0,20 par fenêtre EVAL** | aucune source publique (W2-D §Non trouvé 6) ; hypothèse de travail signée | ☑ fourni ci-dessous |
| 4 | Scénarios desk (liste) | réalisé · non-rétablissement 48 h · guérison lente 5 j · venue unique contrainte 0,80526 | W2-D §(f) 7 | ☑ validé ☐ modifié → …………… |
| 5 | `p_s` (probabilités des scénarios) | **0,25 / 0,25 / 0,25 / 0,25** | aucune distribution publique (W2-D §Non trouvé 4) ; prior uniforme signé | ☑ fourni ci-dessous |
| 6 | `r_capital` (financement desk) | **0 %** (cash) | B7 Q16 — aucune source ; base cash sans financement | ☑ fourni ci-dessous |
| 7 | Coût d'aller-retour (illustration desk) | 20 bp | W2-D §E.3 (« hypothétique, à mesurer ») | ☑ validé ☐ modifié → …………… |

## Valeurs à fournir (le cas échéant)

* `P(obligation)` par fenêtre EVAL (justification écrite par fenêtre) : **0,20 pour chaque
  fenêtre EVAL** — hypothèse de travail non sourcée, identique à la valeur DEV ; aucune
  fréquence publique de ventes forcées n'existe. La sensibilité `P*` est publiée avec le P&L.
* `p_s` des scénarios desk (avec sensibilité) : **0,25 / 0,25 / 0,25 / 0,25** — prior uniforme
  explicitement non calibré ; sensibilité publiée avec le P&L et le rapport.
* `r_capital` (source ou hypothèse écrite) : **0 %** — desk financé sur cash, sans financement ;
  les variantes de sensibilité 5 % et 10 % sont publiées avec le P&L.

## Signatures

| Rôle | Nom | Date (UTC) | Signature / hash du commit de signature |
|---|---|---|---|
| Chef d'équipe (défaut, FREEZE_V2 §C7) | AKUE-BITCHI Adote Jovanny | 2026-10-17 | validation électronique du chef d'équipe — autorisation explicite dans la session Hermes du 2026-10-17 ; une copie manuscrite scannée peut être jointe à la soumission |
| Témoin (optionnel) | | | |

**Rappel d'embargo** : après la première exécution EVAL, toute modification de ces
paramètres **invalide** l'évaluation (re-étiquetage obligatoire) — pas « affaiblit » (B7 §d.2.1).
