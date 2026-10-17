# `frozen/` — paquet de gel « Sprint 0 » (G1–G6 + prévisions DEV)

**Date de gel : 2026-10-16T00:00:00Z** · Généré par `scripts/freeze_sprint0.py` · Vérifié par
`scripts/verify_frozen.py`.

## Contenu

| Fichier | Rôle |
|---|---|
| `G1_fonction_de_perte.md` | G1 — formules de perte, conventions, six tests |
| `G2_comparateurs.md` | G2 — A0/A1/A2/B0/AX0/O, paramètres, phrases gelées |
| `G3_fenetres.md` | G3 — registre DEV/EVAL, embargos, porte de gel |
| `G4_seuils.md` | G4 — seuils persona (VALIDÉ) |
| `G5_plan_analyse.md` | G5 — métriques, cascade, rapport |
| `G6_hypotheses_economiques.md` | G6 — hypothèses économiques (SIGNÉ) |
| `G6_FEUILLE_DE_SIGNATURE.md` | Feuille de signature du chef d'équipe |
| `Gx.sha256` | Manifestes sha256sum des documents ci-dessus |
| `forecasts_dev.jsonl` | Prévisions DEV gelées, chaînées par `prev_hash` |
| `outcomes_dev.jsonl` | Résolutions déterministes, chaînées |
| `FORECASTS_DEV.md` | Lecture FR des prévisions (provenance, ȳ, Wilson) |
| `README.md` | Ce fichier (non auto-référencé : voir note) |

## Vérifier (2 minutes, hors-ligne)

```bash
# 1. Empreintes des manifestes de gel
python scripts/verify_frozen.py          # tout : sha256 + chaînes + recalcul complet
cd frozen && sha256sum -c G1.sha256      # (idem G2..G6 ; GNU coreutils)
# 2. Recalcul intégral du paquet dans un répertoire temporaire et comparaison octet à octet
python scripts/freeze_sprint0.py --out /tmp/frozen_recalc
```

## Ce qui est gelé, ce qui ne l'est pas

* **GELÉ** : les six documents, leurs empreintes, les 9 prévisions DEV (hash chaîné) et leurs
  résolutions déterministes ;
* **VALIDÉ / SIGNÉ le 2026-10-17** : G4 (seuils persona, validés) et G6 (hypothèses
  économiques, signées par **AKUE-BITCHI Adote Jovanny**) — l'EVAL peut être revendiquée à partir de ce paquet ;
* **NOT DONE (jamais inventé)** : fenêtres CALME EVAL 2025–2026 (B7 Q6) et `Depth_ε` —
  voir `G3_fenetres.md` §4 ; les hypothèses G6 précédemment manquantes sont désormais
  signées (P(obligation) EVAL = 0,20 ; `p_s` uniformes ; `r_capital` = 0 %).

## Empreintes des manifestes (recopiables)

| Manifeste | sha256 |
|---|---|
| `G1.sha256` | `e4a962426fd4e4b0c5109dfc9a817d7832a3cb6d2c62635e17ad6e562dc20581` |
| `G2.sha256` | `412b374b6195fa0f5fce42817cd0395f3861f8430ec4f1d6414c57c2006159a2` |
| `G3.sha256` | `37acc25fc99df6abd031ef9664e89aa2f3e87edc75ea83fa4848be4075d244e9` |
| `G4.sha256` | `6c3cbeb13e0fe47240caa9124945b944aeef1fed9e058e93f6d473e021f81974` |
| `G5.sha256` | `e3cb04c3bb5db95a594a1e59918dc622b73fd68eaeca19deb1353ad5aa03f21f` |
| `G6.sha256` | `e42e7da0529d244abbe2e29894e9494623e25fdc642324c213a2c12e5ce9c0c2` |

*Note : `README.md` et `FORECASTS_DEV.md` ne figurent pas dans les manifestes Gx (ils ne sont pas
des documents gelés au sens du protocole) ; leurs empreintes sont vérifiées par `verify_frozen.py`
lors du recalcul octet à octet.*

## Attention — quand régénérer

Les documents G1, G2, G3, G5 portent les **empreintes du code** (`loss.py`, `comparators.py`,
`windows.py`, `calibration.py`, `forecasts.py`, `outcomes.py`) : toute modification de ces
fichiers **oblige à régénérer le paquet** (`python scripts/freeze_sprint0.py`), sinon
`verify_frozen.py` signale l'écart — c'est voulu (un gel qui ne correspond plus au code
n'est plus un gel). Après la première exécution EVAL, modifier quoi que ce soit dans G1–G6
**invalide** l'évaluation (re-étiquetage obligatoire).
