# raw_b7 — matière brute et index (chantier B7 : APPRENTISSAGE & ÉVALUATION)

**Date : 15 octobre 2026.** Auteur : sous-agent B7. Ce dossier porte la matière brute du livrable
`research/B7_EVALUATION_ETUDE.md` (outcomes, calibration Brier/ECE/Wilson, replay engine 2 modes,
jeux DEV/EVAL, harnais A0/A1/A2/B0, apprentissage v1/v2). Aucun fichier existant modifié ; aucun commit git.

## Contenu du dossier

| Fichier | Nature |
|---|---|
| `NOTES_b7_matiere_brute.md` | ce fichier : index + extraits de référence (faits/passages utilisés, avec fichier source et ligne) |
| `exemples_calibration.json` | calculs du 15/10/2026 12:52 UTC : bornes de Wilson (n=5..100, k=0..3), exemple KAT `BS=0,10 / REL=0,02 / RES=0,16 / UNC=0,24 / ECE=0,10`, conversions runway |
| `exemples_calibration_sortie.txt` | copie texte du même calcul (trace de sortie du script) |

Script d'origine : exécuté en ligne dans le terminal du sous-agent (heredoc Python) le 2026-10-15 ;
le JSON est la trace reproductible (formules : Wilson standard z=1,959964 ; bins fixes de largeur 0,1).

## Extraits sources (fichier : lignes) — faits réutilisés dans le livrable

### W2D_objectifs_mesure.md
- §0 pt 3–4 (l.23–24) : bug de la fonction de perte antérieure ; `écart_bugué − écart_vrai = q·(1 − P_T)`.
- §B.1 (l.183–199) : fonction de richesse `W_T(conserver)=C+q·P_T`, `L(a)`, `R_w(a)` ; regrets `R⁻`/`R⁺` séparés.
- §B.3 (l.245–264) : unités DAO (jours de runway ; opex 44 932 $/j ; plancher 49,34 M$) ; perte évitée conditionnelle `E = P(oblig)·(perte|oblig) − (1−P)·coût`.
- §B.4 (l.268–293) : ΔP&L net desk ; Sharpe/Sortino/MaxDD ; seuil `x·(P_T−P_exec) > k` ; l'agent est un put.
- §B.6 (l.315–326) : les six tests de la fonction de perte (T1 neutralité … T6 référence dégénérée).
- §C.1 (l.334–345) : comparateurs (A0 = rien faire, A1 = seuil, A2 = agent, B0 = placebo M≥200, A−x, O).
- §C.2 (l.347–362) : DEV (USDC, stETH, calme 22–23) / EVAL (rsETH, USD0++, calme 25–26) / exclu (xUSD) ; quatre embargos ; SHA-256.
- §C.3 (l.364–372) : `variants.log` (DSR exige le nombre d'essais).
- §C.4 (l.374–411) : seuils SD1–SD6 (DAO) et ST1–ST6 (desk) ; anti-optimisme (Wilson, bootstrap blocs 6–12 h, McNemar, DSR).
- §C.5 (l.413–425) : gels G1–G7, J0 = 2026-10-16 proposé.
- §(e) (l.457–525) : exemple USDC — pertes évitées 110 912 $ / 120 324 $ / 258 578 $ ; prime −800 000 $ ; desk −4,2 % / +10,8 % / +18,27 %.
- §(f) (l.529–542) : les 12 points à trancher.

### R3_evaluation_benchmark.md
- §B.0 (l.196–201) : pré-enregistrement, budgets égaux, unité = fenêtre, vecteur.
- §B.1 M1–M6 (l.203–243) : regret M1 ; Brier M2 (y = dépeg soutenu > 1 % ≥ 2 obs, horizon H) ; ECE M3 (10 bins, non conclusionnel si N < 100) ; conformal M4 ; pass^k/D1–D3 M5 ; sûreté/coût M6.
- §B.2 (l.245–259) : comparateurs (nommage « A0 = seuil fixe » — collision résolue en B7) ; B0 placebo.
- §B.5 (l.286–318) : puissance ≈ 93 fenêtres/groupe (0,50 vs 0,30) ; Wilson n=6 → 0/6 sup. ≈ 39 % ; McNemar 12 paires → ≥ 6 discordances (p = 0,031) ; bootstrap par blocs 6–12 h / 10 000 répl. ; échangeabilité violée en crise.
- §C.8 (l.461–467) : fenêtres témoins (12 × 72 h ; `CALME` ⟺ max|P−1| < 0,5 %).
- §C.9 (l.469–483) : piège Binance USDT 18/11/2025 (prix mince ≠ dépeg).
- §A.4 (l.154–193) : Brier/Murphy/ECE/Guo/conformal ; confiance verbalisée interdite.

### B1_AGENTS_ETUDE.md
- R-6 (l.23) et §6.3 (l.642–651) : modes REPLAY-JOURNAL / LIVE-REPLAY / LIVE ; INV-PIT ; F20-D8.
- §6.2 (l.630–640) : déterminisme (Thinking Machines 2025-09-10 ; arXiv:2606.08998 ; pas de `seed` trouvé ; IDs de modèles mobiles).
- §3.4 (l.324–368) : schéma `agent_journal` (16 champs, chaînage `prev_hash`, magasin de payloads).
- §3.5 (l.370–380) : promotion journal → graphe (validateurs déterministes, branche p=0).
- §6.4–6.5 (l.653–675) : script de démo (9 écrans) ; coûts (3 épisodes ≈ 0,0396 $ ; 12 appels/épisode).
- §7 (l.695–706) : Q1–Q8 (dont rétention du journal, export, critique second modèle).

### B3_DECISION_ETUDE.md
- §b.2 (l.145–198) : RDOF (5 règles, arrêt c1/c2/c3) ; §b.3 (l.200–205) : VoI derrière interface (v2).
- §c (l.209–268) : abstention A1–A5 ; format INCONCLUSIVE ; ESCALATE vs NO-ACTION.
- §f (l.390–399) : qualitatif d'abord ; prévision gelée = {énoncé, critère, horizon, date, SHA-256} ; scoring Brier plus tard ; « non établi » sous N.
- §g.4 (l.457–459) : réconciliation close/low (0,86267 vs 0,80526) — à geler avant G1.

### W3C_complements_signaux.md
- §1–2 : séries xUSD (457 h CoinGecko ; 411 swaps reconstruits) et USD0++ (635 h ; 610 swaps ; écart 0,31 %).
- §5 (l.204–229) : plan de calibration 12 mois (P99/P99,9, escalade, 10–20 h de collecte).

### Preuves et code
- `evidence/episode_usdc_2023-03.json` : minima (Bitstamp 0,80526 ; DeFiLlama 0,876675 ; Binance 0,8820 ; oracle min dense 0,8833 à 07:53:23Z), dispersions (870,07 / 1047,7 bps), divergence max −558,9 bps à 03:00.
- `evidence/episode_rseth_2026-04.json` : cap 99,9989 % à 18:00 (bloc 24 908 406) ; gel 19:03:59 (bloc 24 908 723, dichotomie 14 étapes) ; oracle 2 526,76 → 2 513,66 → 2 419,21.
- `evidence/episode_steth_2022-06.json` : premier franchissement 200 bps le 13/05/2022 (213,74 bps ; 66,90 la veille) ; pire 692,51 bps (1 stETH) le 14/06 10:00Z.
- `evidence/baseline_report.json` : AX0 = 2 signaux fenêtre principale (11/03 03:00 ; 13/03 06:00), 0 sur contrôle.
- `corpus/manifest.json` : 520 observations, collecte 2026-10-14T15:47Z.
- `src/orvyren/decision/baseline.py` : règle gelée D6 (0,99 × 2 obs → réduction 100 $).
- `src/orvyren/execution/verify.py` : codes de mismatch de reçu (voir comptage ci-dessous).
- `src/orvyren/quality/checks.py` : data gate (≥ 2 venues indépendantes) ; `normalize.py` : rejets explicites.
- `research/DECISIONS_ET_PROCHAINES_ETAPES.md` : « à trancher » (12 points ; xUSD ; etc.) ; deadline 20/10 15:59 UTC ; 221 tests verts.

## Vérifications faites pendant la rédaction (2026-10-15)

- `date -u` = jeu. 15 oct. 2026 12:50 UTC.
- `git status` : untracked = `research/raw_b4/`, `raw_b5/`, `raw_b6/` (autres chantiers) ; **aucun commit effectué par B7**.
- Décompte des codes de mismatch de `verify.py` : **10 codes** (`NO_TRANSFER_LOG`, `TOKEN_CONTRACT_MISMATCH`, `SENDER_MISMATCH`, `RECIPIENT_MISMATCH`, `AMOUNT_MISMATCH`, `TRANSACTION_FAILED`, `RECEIPT_STATUS_MISSING`, `CHAIN_ID_MISSING`, `CHAIN_ID_MISMATCH`, `CHAIN_ID_INVALID`) — le livrable dit « 10 codes » (corrigé après vérification).
- URL Wilson 1927 vérifiée par recherche web : <https://doi.org/10.1080/01621459.1927.10502953> (JASA 22(158):209–212) — la recherche Naeini/AAAI a échoué côté moteur (backend) ; l'URL AAAI reste citée telle que fournie par R3.

## Non trouvé (constaté pendant le chantier)

- Aucun format standard public d'outcome de prévision pour agents financiers (le format proposé est une conception ORVYREN alignée sur la chaîne B2).
- Aucun seuil industriel/réglementaire publié de calibration (ECE/N minimal) pour ce type de système.
- Aucun paramètre `seed` documenté chez DeepSeek/MiMo (reconfirmé : pages officielles consultées le 15/10/2026, archive `raw_b1/`).
