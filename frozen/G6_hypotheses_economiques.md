# G6 — Hypothèses économiques (gel v1, statut SIGNÉ)

**Statut : SIGNÉ — validation électronique du chef d'équipe le 2026-10-17.** 2026-10-16T00:00:00Z.
Signataire : **AKUE-BITCHI Adote Jovanny** — validation électronique du chef d'équipe — autorisation explicite dans la session Hermes du 2026-10-17 ; une copie manuscrite scannée peut être jointe à la soumission. La feuille
`G6_FEUILLE_DE_SIGNATURE.md` porte la validation ; les valeurs ci-dessous sont
celles sur lesquelles la première EVAL s'exécute.
Sources : W2-D §B.3/B.4, §E.2, §(f) 1–7 et 11–12 ; B7 §b.5, §e.3/e.4, Q1 ; FREEZE_V2 §C7.

## 1. Paramètres et valeurs signées

| Paramètre | Valeur signée | Statut | Source / justification |
|---|---|---|---|
| `opex_ref` (jours de runway) | **44 932 $/jour** | VALIDÉ (référence externe déclarée) | ENS IPS 6.46 : 16,4 M$/an de charges 2025 ; conversion calculée 16 400 000 ÷ 365 (W2-D §A.1.1, §E.1 ; B7 Q13) |
| `P(obligation)` — fenêtre USDC DEV (exemple de calcul) | **0,20** | VALIDÉ (hypothèse non sourcée) | valeur de travail de W2-D §E.2(b) — « hypothèse à figer, non sourcée » ; aucune fréquence publique de ventes forcées n'existe |
| `P(obligation)` — fenêtres EVAL | **0,20 par fenêtre EVAL** | SIGNÉ — hypothèse de travail non sourcée | aucune source publique (W2-D §Non trouvé 6) ; valeur DEV conservée pour toutes les fenêtres EVAL, avec justification écrite et sensibilité `P*` publiée |
| Scénarios desk `p_s` | **4 scénarios** : (i) réalisé, (ii) non-rétablissement à 48 h, (iii) guérison lente (5 j), (iv) venue unique contrainte (0,80526 — contrefactuel) ; **p_s = 0,25 / 0,25 / 0,25 / 0,25** | SIGNÉ — liste et prior uniforme non calibrés | W2-D §(f) 7 ; aucune distribution publique de scénarios de dépeg (W2-D §Non trouvé 4) : les `p_s` sont des hypothèses signées, publiées avec le P&L et leur sensibilité |
| `r_capital` (taux de financement desk) | **0 %** (desk financé sur cash) | SIGNÉ — hypothèse de travail | aucune source trouvée (B7 Q16) ; base « cash sans financement », sensibilités 5 % et 10 % publiées avec le P&L |
| Coût d'aller-retour desk (illustratif) | 20 bp (`k = 4 000 $` sur 2 M$) | VALIDÉ (illustration) | W2-D §E.3 — « hypothétique, à mesurer réellement » |

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

## 4. Signature

Validé par **AKUE-BITCHI Adote Jovanny** le **2026-10-17** — validation électronique du chef d'équipe — autorisation explicite dans la session Hermes du 2026-10-17 ; une copie manuscrite scannée peut être jointe à la soumission.
Une copie manuscrite scannée peut être jointe à la soumission ; la validation
électronique de référence est ce document et `G6_FEUILLE_DE_SIGNATURE.md`.
