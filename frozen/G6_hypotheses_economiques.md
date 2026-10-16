# G6 — Hypothèses économiques (gel v1, statut PROPOSÉ — en attente de signature)

**Statut : PROPOSÉ — non signé.** 2026-10-16T00:00:00Z. Tant que la feuille
`G6_FEUILLE_DE_SIGNATURE.md` n'est pas signée, ces hypothèses restent des
propositions : aucune revendication EVAL ne peut s'appuyer dessus.
Sources : W2-D §B.3/B.4, §E.2, §(f) 1–7 et 11–12 ; B7 §b.5, §e.3/e.4, Q1 ; FREEZE_V2 §C7.

## 1. Paramètres et valeurs proposées

| Paramètre | Valeur proposée | Statut | Source / justification |
|---|---|---|---|
| `opex_ref` (jours de runway) | **44 932 $/jour** | PROPOSÉ (référence externe déclarée) | ENS IPS 6.46 : 16,4 M$/an de charges 2025 ; conversion calculée 16 400 000 ÷ 365 (W2-D §A.1.1, §E.1 ; B7 Q13) |
| `P(obligation)` — fenêtre USDC DEV (exemple de calcul) | **0,20** | HYPOTHÈSE non sourcée | valeur de travail de W2-D §E.2(b) — « hypothèse à figer, non sourcée » ; aucune fréquence publique de ventes forcées n'existe |
| `P(obligation)` — fenêtres EVAL | **NOT DONE — à proposer par le signataire** | à signer | aucune source publique (W2-D §Non trouvé 6) ; le signataire doit fournir une justification écrite par fenêtre |
| Scénarios desk `p_s` | **4 scénarios** : (i) réalisé, (ii) non-rétablissement à 48 h, (iii) guérison lente (5 j), (iv) venue unique contrainte (0,80526 — contrefactuel) | liste PROPOSÉE ; **probabilités NOT DONE** | W2-D §(f) 7 ; aucune distribution publique de scénarios de dépeg (W2-D §Non trouvé 4) : les `p_s` seront des hypothèses signées, publiées avec le P&L |
| `r_capital` (taux de financement desk) | **NOT DONE — à proposer** | à signer | aucune source trouvée (B7 Q16) ; les deux P&L (hors et avec financement) sont publiés pour que la différence reste visible (W2-D §(f) 11) |
| Coût d'aller-retour desk (illustratif) | 20 bp (`k = 4 000 $` sur 2 M$) | PROPOSÉ (illustration) | W2-D §E.3 — « hypothétique, à mesurer réellement » |

## 2. Règles attachées (gelées)

* la perte évitée n'est **jamais** publiée inconditionnellement :
  `E[perte évitée] = P(oblig) · (perte | oblig) − (1 − P(oblig)) · coût_AR`, les deux facteurs visibles ;
* toute modification de `P(obligation)`, des `p_s` ou de `r_capital` exige une **re-signature nommée**
  + justification + sensibilité publiée (B7 §f.2) ;
* une prévision `p` ne peut **jamais** être produite par un LLM (interdit par construction, B7 §a.5.5).

## 3. Sensibilité exigée

Pour chaque fenêtre où `P(obligation)` entre dans un verdict, publier la sensibilité du
signe de `E[perte évitée]` à `P(obligation)` : la valeur de bascule est calculable
exactement (`P* = coût_AR / (perte|oblig + coût_AR)`) — elle doit figurer au dossier.
