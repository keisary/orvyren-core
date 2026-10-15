# Notes de synthèse W2-D (matière brute consolidée) — 15/10/2026

Fichier de travail, non livrable. Sources : `raw_w2d/web_lot1.json`, `web_lot2.json`, `web_lot3.json`, `pages/`, `calculs_w2d.json` + `W2A_donnees_episodes.md`, `W2B_signaux_detection.md`, `R3_evaluation_benchmark.md`.

## 1. Faits retenus pour le persona DAO (risque / anticipation)
- ENS IPS 6.46 (post kpk 8/5/2026, vote social passé, thread fermé 11/8/2026) — objectif primaire : préservation + rendement réel couvrant les charges sans éroder le principal ; secondaire : croissance. Risque := (1) P(ne pas honorer une obligation de liquidité/trésorerie) ; (2) P(perte du principal). Runway min ≈ 49,34 M$ = 3 ans de charges, « Unconditional, supersedes the 60/40 target ». Charges 2025 = 16,4 M$ (rapport Steakhouse). Buffer timelock = 6 mois d'USDC. Benchmark = moyenne pondérée TVL 60/40 (5 plus grands vaults ETH / 5 plus grands vaults stablecoin), APY glissant 30 j recalculé le 1er jour ouvré. Faible risque ≥ 90 % (redeemable ≤ 7 j), modéré ≤ 10 % (réversible ≤ 30 j). Suivi : MTM quotidien, **rapport de drawdown mensuel**, **contrôle hebdo du runway**, alertes temps réel Hypernative, Zodiac Roles Modifier v2. Concentration ≤ 30 %/protocole, RWA ≤ 5 %, EURC ≤ 5 % du stable, LSD ≤ 20 % du consensus (25 % DVT), pas de CEX pour l'ETH, mainnet only. Revue : underperformance vs benchmark 2 trimestres consécutifs.
- KPK Monthly Treasury Report June 2026 (27/7/2026) — séparation « strategy yield » vs « mark-to-market » ; capital utilisation (ENS ≈ 99 %, dYdX 79,73 %, Balancer ≈ 95 %, Nexus ≈ 97 %) ; déploiement (CoW 77 %) ; concentration ; « over $8bn deployed onchain, 16 000+ transactions, zero funds lost ».
- Compound RFP (comp.xyz/7867, consulté 15/10/2026) — soumission = « Risk framework + at least one stress scenario » ; profil de liquidité (lockups, notices, unstaking, redemption windows) exigé ; critères pondérés (frais 10 %...).
- Eco (stablecoin treasury 2026 / stablecoin depeg) — composants de politique (allocation, whitelists, custody, yield, reporting cadence) ; rendements 4,1–11,8 % APY ; 6 causes de dépeg ; diversification ≥ 2 émetteurs ; surveillance de la composition de la Curve 3pool. USDC 0,87 $ ; récupération ≥ 0,99 en 48 h.
- Fed FEDS 17/12/2025 — 40 Md$ de retraits SVB en 1 jour ; 22 h vendredi : Circle annonce 3,3 Md$ bloqués (≈ 8 %) ; PSM DAI vidés « en heures » ; DAI perd aussi sa parité ; résolution FDIC/Trésor/Fed.
- BPI — USDC jusqu'à 0,87 $ ; run dès le 9 mars ; Binance et Coinbase suspendent les conversions USDC→USD ; USDe 0,65 $ le 10/10/2025.
- ENS forum, « Independent Risk Teardown » (riskypete/Sentralis, 14/7/2026) — liquidité de sortie en deux régimes, files de redemption, coût d'un mandat d'options ≈ 70 k$/an par million.

## 2. Faits retenus pour le persona desk (rentabilité)
- Keyrock (guide, sans date) — delta-neutre revendiqué ; capital = profondeur ; spread resserré comme indicateur.
- DWF Labs (13/9/2024, maj 5/9/2025) — 10 critères : capital/profondeur ; **uptime ≥ 95 %** (via Outlier Ventures) ; couverture multi-venues ; conformité ; transparence + métriques hebdomadaires ; SLA 24/7.
- Thèse MM (diva-portal) — Sharpe prioritaire, R_f = 0 par convention ; métriques secondaires : valeur terminale, P&L, trades, inventaire moyen.
- IBKR Quant — Drawdown_t = Equity_t / max_{u≤t} Equity_u − 1 ; MaxDD = min ; Sortino ; IR ; drawdown → **déleveraging forcé** pour les stratégies contraintes en capacité.
- ScienceDirect (S1110866525002324) — SoR = (R_p−R_f)/σ_d ; MDD ; IR = (R_p−R_b)/TE ; MDD 20–30 % en stress pour les méthodes classiques.
- JKP (snippet) — 10 bp par dollar échangé changent le Sharpe (1,86).
- NeH Capital (2/10/2026, snippet) — diagnostics : realised spread, inventory duration, markout after fills, pertes en volatilité.
- XR Academy (snippet) — Net P&L = V·S + V·R − V·AS − V·EC − I·HC·T − OC − K·CC.
- DSR / False Strategy Theorem (Bailey & López de Prado) — tests multiples ; « aucun seuil de Sharpe au-delà duquel on peut rejeter qu'une stratégie est fausse » ; il faut consigner tous les essais.

## 3. Formules gelables
- Noyau : W_T(conserver) = C + q·P_T ; W_T(céder x) = C + x·P_exec − k + (q−x)·P_T ; L(a) = W_t0 − W_T(a) ; R_w(a) = L(a) − min_{b∈F} L(b).
- Bug antérieur (R3 §B.1 M1) : L(NO-ACTION) = E·max(0, 1−min_t P_t) ; L(RÉDUIRE) = c + E·max(0,1−P_action) − E·max(0,1−min_t P_t). Identité : écart_bugué − écart_vrai = q·(1 − P_T). Exemple minimal : q = 100, P_exec = 1,00, P_T = min = 0,90 → affiché 20, réel 10.
- DAO : Perte évitée = L(A0) − L(A) ; en jours de runway = ÷ (opex annuel/365 = 44 932 $/j) ; conditionnel : E = P(obligation)×(perte évitée | obligation) − (1−P(obligation))×coût aller-retour.
- Desk : ΔP&L net = x·P_exec + (q−x)·P_T − q·P_ref − k − financement − opex ; bp = ÷(q·P_ref)×10 000 ; Sharpe/Sortino/MaxDD sur la série de décisions ; seuil d'action : x·(P_T − P_exec) > k_aller-retour + financement.

## 4. Protocole (extrait)
- Comparateurs : O (oracle in-family), A0 (rien faire), A1 (seuil D ≥ 50 bp / 15 min → réduction bornée), A2 (agent), B0 (placebo apparié, M ≥ 200, graine fixée), A−x (ablations).
- DEV = USDC 2023 + stETH 2022 (+ calmes) ; EVAL = rsETH 2026 + USD0++ 2025 (+ calmes) ; xUSD exclu (pas de série de prix).
- Embargo : paramètres gelés ; bande de 24 h avant l'ouverture d'une fenêtre EVAL retirée du DEV ; inspection interdite avant gel ; gel = commit signé + SHA-256.
- Journal des variantes obligatoire (nécessaire au DSR).
- Seuils DAO : SD1 perte évitée ≥ 5 % de l'exposition exposée (conditionnel) ; SD2 friction calme ≤ 10 % de la perte évitée ; SD3 antériorité ≥ 6 h + réaction ≤ 60 min ; SD4 R̄(A2) < R̄(A1) et < R̄(B0) ; SD5 traçabilité 100 % ; SD6 mentions d'honnêteté.
- Seuils desk : ST1 ΔP&L net > 0 (tous coûts) ; ST2 slippage ≤ 30 bp + taille ≤ Depth_100bp ; ST3 MaxDD ≤ 20 % du capital alloué ; ST4 Sharpe > 0 avec borne basse d'IC > 0 (sinon « non conclusionnel ») ; ST5 > A1 et > B0 ; ST6 asymétrie (put) déclarée.

## 5. Chiffres calculés (voir calculs_w2d.json)
- opex ENS mensuel = 1 366 666,67 $ ; journalier = 44 931,51 $ ; plancher = 49 340 000 $.
- Unités USDC nécessaires pour payer 1 366 667 $ : à 0,8820 → 1 549 509 (+182 842 ; +4,07 j) ; à 0,876675 → 1 558 921 (+192 254 ; +4,28 j) ; à 0,80526 → 1 697 174 (+330 508 ; +7,36 j).
- Perte évitée vs pré-positionnement à 0,95 : 110 912 $ (2,47 j) à 0,8820 ; 120 324 $ (2,68 j) à 0,876675 ; 258 578 $ (5,75 j) à 0,80526.
- 20 M$ : sortie 0,95 → retour 0,99 = −800 000 $ (−4,00 %).
- Espérance avec P(obligation) = 20 % : −617 818 $.
- Desk 2 M$, k = 20 bp = 4 000 $ : (0,95→0,99) = −84 000 $ (−4,20 %) ; (0,98→0,99) = −24 000 $ (−1,20 %) ; (0,99→0,88) = +216 000 $ (+10,80 %) ; (0,99→0,80526) = +365 480 $ (+18,27 %).
- Dispersion mesurée : Binance 0,8820 − Bitstamp 0,80526 = 767 bp ; décote Bitstamp 19,47 % ; Binance 11,80 %.

## 6. Non trouvé
- Objectifs chiffrés publiés par un desk nommé (Wintermute/GSR/Keyrock/Amber) : aucun.
- Budget de risque chiffré (perte max par épisode, drawdown budgété) dans une politique de DAO : aucun (l'IPS ENS impose un rapport de drawdown, pas un plafond).
- Cibles de Steakhouse / Block Analitica / Lido / Aave / Sky : non trouvées (recherche du 15/10/2026 sans résultat exploitable).
- Distribution de probabilité publique de scénarios de dépeg : aucune.
- Série de prix exploitable pour xUSD (nov. 2025) : aucune.
- Sensibilité de P(obligation) pour une trésorerie de DAO : non trouvée.
- Profondeur d'exécution des stablecoins au pire de la crise USDC (échelle get_dy) : non mesurée.

## 7. Empreinte du livrable
- `D:\\orvyren_core\\research\\W2D_objectifs_mesure.md` — sha256 = `60cff03d11360cc6e9b764b5d9f7a18abb5be68903b2b57553f2b5387b912b1d` (76852 octets, 598 lignes), figé le 2026-10-15 06:55 (heure locale).
