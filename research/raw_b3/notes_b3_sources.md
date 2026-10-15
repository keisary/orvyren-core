# B3 — NOTES DE MATIÈRE BRUTE (chantier DÉCISION)

**Date de collecte : 15 octobre 2026.** Sauvegarde progressive : ce fichier + les JSON/PDF/MD extraits du dossier `raw_b3/`.
Règle : chaque item = affirmation + source + date. « non trouvé » écrit tel quel. FAIT SOURCÉ / MESURÉ (interne) / CONCEPTION.

---

## 1. ACH et techniques analytiques structurées (bloc a)

- **Heuer, R. J. — *Psychology of Intelligence Analysis*, CIA, 1999** (PDF officiel : https://cia.gov/resources/csi/static/Pyschology-of-Intelligence-Analysis.pdf). ACH = méthode en 8 étapes ; la plus importante : construire la matrice hypothèses×preuves et **réfuter** plutôt que confirmer. FAIT SOURCÉ (page/index accessible ; texte intégral non extrait par nos outils le 15/10).
- **CIA — *A Tradecraft Primer: Structured Analytic Techniques for Improving Intelligence Analysis*, mars 2009** (https://cia.gov/resources/csi/static/Tradecraft-Primer-apr09.pdf, extrait partiel). Constats cités : « Analysts seldom generate a full set of explanations or hypotheses at the outset » ; matrice ACH d'exemple (Aum Shinrikyo) avec **scores d'incohérence** par hypothèse (H d'abord classées, evidence en lignes). FAIT SOURCÉ (extrait).
- **Mandel, D. R., Karvetski, C. W., Dhami, M. K. — "Boosting intelligence analysts' judgment accuracy: What works, what fails?", Judgment and Decision Making 13(6):607–621, novembre 2018** (PDF extrait : `mandel_karvetski_2018_jdm.md` ; DOI 10.1017/S1930297500006628). Résultat : le groupe ACH a **mieux évalué l'utilité de l'information** mais le groupe contrôle a été **un peu plus exact et cohérent** ; « ACH failed to improve accuracy » ; la **recalibration (coherentization) + agrégation** a réduit l'erreur absolue moyenne de **61 %**. FAIT SOURCÉ.
- **"Effects of task structure and confirmation bias in alternative hypotheses evaluation", Cognitive Research: Principles and Implications 9:37, 13 juin 2024** (doi 10.1186/s41235-024-00560-y ; PMC11169332). Étude 1 (N=161) : la présentation **type matrice ACH (hypothèses en colonnes, preuves en lignes) n'a PAS réduit le biais de confirmation** ; la disposition transposée (hypothèses en lignes) l'a réduit ; pas de bénéfice de sensibilité à la crédibilité des preuves. Étude 2 : 62 analystes militaires néerlandais ne montraient majoritairement pas de biais de confirmation. FAIT SOURCÉ (abstract Europe PMC, vérifié).
- **Dhami et al.** (snippet moteur, Applied Cognitive Psychology) : « little evidence exists of how techniques are applied and whether » elles réduisent le biais. SNIPPET (non ouvert) — à citer avec prudence.
- **Heuer & Pherson — *Structured Analytic Techniques for Intelligence Analysis*** : recensé ACM DL (https://dl.acm.org/doi/10.5555/2086751). Édition/date non vérifiées dans nos extractions → citer sans millésime or not at all.
- **Garde-fous falsifiabilité (agents, 2025-2026)** :
  - **Popper — "Automated Hypothesis Validation with Agentic Sequential Falsifications", arXiv:2502.09858, 14 février 2025** (abs + HTML partiel) : agents LLM qui conçoivent et exécutent des expériences de **réfutation** ; contrôle strict du **Type-I error** par test séquentiel ; 6 domaines. FAIT SOURCÉ (abstract).
  - **"Output Discipline Sets the Floor: A Falsification-Guided, Model-Agnostic Agent Protocol for Auditable Hypothesis-Driven Decision Making", arXiv:2610.18298** (extrait Oct 2026) : protocole auditable guidé par la réfutation ; « candidate-bounded format layer » ; connaissance = donnée révisable. PRÉPRINT (extrait partiel).
  - **"Accurate but Not Humble: Evaluating Epistemic Humility in LLM Agents under Knowledge Conflict", arXiv:2610.12360, 8 octobre 2026** : dimensions **Identify / Solve / Escalate (ISE)** ; la précision ne garantit pas l'humilité épistémique ; des agents détectent les conflits mais **ne communiquent pas l'incertitude non résolue**. FAIT SOURCÉ (abstract).

## 2. VoI (bloc b) — déjà couvert par R1 (interne), complété

- R1 (`research/R1_orchestration_VOI.md`, 14/10/2026) : EVPPI/EVSI (Heath et al., Med Decis Making 40(3), epub 16/04/2020 — **EVSI ≤ EVPPI**) ; `NetVoI(q)=VoI(q)−c`, arrêt si ≤ 0 (Dong et al., ACL 2026 Long Papers pp. 42879–42896, juillet 2026 — 18/20 conditions, jusqu'à +1,36 pt, coût ~10×) ; position « Bayes-consistent orchestration » (arXiv:2605.00742 v1 01/05/2026 ; HAL 27/01/2026) ; LLM = modèle de vraisemblance approché (arXiv:2601.01522, 04/01/2026) ; EVOI gradient (WWW'25, 22/04/2025) ; BOED/ IPM plus stable que KL/EIG (arXiv:2604.21849, 23/04/2026). MESURÉ (interne) + FAIT SOURCÉ (pair-reviewed cités dans R1).
- **Nouveau (15/10/2026)** : **"On Open-Ended Information Seeking for Information Elicitation Agents", arXiv:2610.07509, 5 octobre 2026** — les jugements sur la valeur de l'information **varient selon les LLM** (11 modèles) et façonnent le comportement de recherche (breadth vs depth) ; l'histoire d'interaction change l'évaluation de l'information. → argument pour un mécanisme v1 **déterministe** (pas de "ressenti de valeur" du modèle).
- Rappel R1 : dépendance des sources = défi ouvert ; `α_i` de fiabilité ≠ likelihood.

## 3. Abstention / déferral (bloc c)

- **Chow, C. K. — "On Optimum Recognition Error and Reject Tradeoff", IEEE Trans. Inf. Theory, 1970** (doi 10.1109/tit.1970.1054406). La règle de rejet coût-optimal = exiger p(c|x) > seuil dépendant du coût de rejet. FAIT SOURCÉ (métadonnées DOI).
- **"Machine learning with a reject option: a survey", Machine Learning 113:3073–3110, publié 29 mars 2024** (doi 10.1007/s10994-024-06534-x). Taxonomie : rejet **dépendant** (rejet d'ambiguïté, y compris rejet de nouveauté/hors-distribution) vs **intégré** ; évaluation par compromis erreur/rejet ; limites de la règle de Chow quand les distributions sont inconnues. FAIT SOURCÉ (extrait).
- **"Learning to Defer: A Survey"** — preprint Zenodo v1.0, décembre 2025 (DOI 10.5281/zenodo.17843044, Strong, Sun, Rogers, Higham, Noble). Déférence à un humain comme décision jointe. FAIT SOURCÉ (métadonnées). Complément : **Madras et al., "Predict Responsibly…", arXiv:1711.06664** (2018). SNIPPET.
- **"Cost-Sensitive Conformal Prediction and Human-in-the-Loop Abstention…", arXiv:2607.27143, 29 juillet 2026** : le CP marginal **sous-couvre les classes minoritaires rares (jusqu'à 0,5 % de couverture)** ; le CP Mondrian restaure la couverture ; **CP Mondrian + abstention contrôlée par coût** réduit le coût de décision attendu sous budget de revue humaine (15 jeux, 7 modèles, 3 150 runs). FAIT SOURCÉ (abstract).
- Interne : v0 `engine.py` règle 4 (série manquante → INCONCLUSIVE + missing_inputs) déjà prouvée ; RC §2.2 (3 axes ; « INCONCLUSIVE n'est pas NO_ACTION ») ; RC C3/C4.

## 4. DAO — pratiques réelles (bloc d) — sources principales

- **ENS IPS 6.46** (KPK, 8 mai 2026, voté ; thread fermé 11 août 2026) : runway ≥ 3 ans (49,34 M$) « Unconditional. Supersedes the 60/40 » ; redemption ≤ 7 jours pour ≥ 90 % ; alertes temps réel (Hypernative) ; Zodiac Roles v2 ; 60/40. (Copie locale `raw_w2d/pages/…22106.md` ; cité dans W2-D.) FAIT SOURCÉ.
- **KPK H1 2026 review (14 août 2026)** : **l'Endowment ENS sort préventivement de ses positions Aave le 18 avril 2026 (rsETH) et les reconstruit en mai, sans perte** (lending 15,8 M$ mars → 67 $ avril → 15,6 M$ mai) ; frais de mandat 221 275 $ (~0,50 %). (Cité dans U2 §A.2.) FAIT SOURCÉ.
- **MakerDAO, 11-13 mars 2023** : proposition d'urgence (Risk CU) — **réduire le gap du PSM de 950 M$ à 250 M$ DAI/jour et relever `tin` (frais de swap USDC→DAI) à 1 %** ; « 736 M de DAI mintés via le PSM en 24 h, offre nette +296 M » (NewsBTC via cryptonews 13 mars 2023 15:30 UTC). FAIT SOURCÉ (article, extrait complet local `cryptonews.net_news_altcoins_20663169_.md`).
- **Aave — rsETH Incident Report (LlamaRisk, 20 avril 2026, 20:12 UTC)** : invariant du pont « rsETH locké ≥ minté » violé (paquet forgé, DVN 1-of-1, nonce 308 vs 307) ; 116 500 rsETH libérés ; 7 adresses de l'attaquant, health factors 1,01–1,03. (Extrait local.) FAIT SOURCÉ.
- **Aave Guardian / marché** : gel en 77 min (18:52) ; puis LTV→0, gels ; WETH/USDC à ~100 % d'utilisation (contagion le week-end) — MESURÉ (evidence/episode_rseth_2026-04.json : cash USDC Aave = 6 403 $ le 19/04 08:00 UTC ; U WETH 1,0000793). FAIT SOURCÉ (Galaxy 22/04) + MESURÉ.
- **Lido (Q1 2026 report, 4 juin 2026)** : TMC — conversions stables → **sUSDS** ; tranches standard **1 500 ETH**, tranche d'urgence **3 000 ETH** ; don 2 500 stETH (5,74 M$) au fonds DeFi United ; 144 ETH first loss. (Cité dans U2 §A.1.) FAIT SOURCÉ.
- **Eco — Stablecoin Depeg** : défenses = diversifier sur ≥ 2 émetteurs à structures de réserve différentes (« USDC-SVB 2023 a frappé USDC et DAI ensemble ; USDT et PYUSD n'ont pas bougé ») ; surveiller la composition de la 3pool (part > ~70 % → décote attendue). (Copie locale raw_w2d.) FAIT SOURCÉ.
- **Chaos Labs quitte Aave (6 avril 2026)** : budget 3 M$/an refusé, minimum estimé 8 M$ (5,6 % des revenus) ; référentiel 6–10 % (banques). (U2 §B.1.) FAIT SOURCÉ.

## 5. Desk — pratiques et formules (bloc d/e)

- W2-D (interne) : seuil d'action desk **x·(P_T−P_exec) > k_aller-retour + financement** ; P&L net = valorisation − frais − gas − financement ; Sharpe/Sortino/MaxDD ; put en espérance sur scénarios ; DSR/journal des variantes (Bailey & López de Prado, JPM 40(5), 2014).
- **Avellaneda & Stoikov, "High-frequency trading in a limit order book", Quantitative Finance 8(3):217–224, avril 2008** (PDF NYU extrait, métadonnées) : gestion d'inventaire comme risque à optimiser (référence classique). FAIT SOURCÉ (métadonnées).
- **Hedging de depeg** (article depegwatch 19/09/2025, snippet) : assurance via depeg swaps (Cork, Risk Harbor), options (Opyn, Lyra, Ribbon) ; Ethena = delta-neutral spot + short perp (guide 2026, snippet). SNIPPETS — citer comme « pratiques documentées », pas comme résultats.
- Interne : Keyrock « risk engine » (U2), crash 10/10/2025 = 19 Md$ de liquidations (U2).

## 6. Scoring / calibration (bloc f)

- **Brier, G. W. — "Verification of forecasts expressed in terms of probability", Monthly Weather Review 78(1):1–3, janvier 1950** (PDF AMS). FAIT SOURCÉ.
- **Gneiting, T. & Raftery, A. E. — "Strictly Proper Scoring Rules, Prediction, and Estimation", JASA 102(477):359–378, 2007** (PDF Washington). FAIT SOURCÉ.
- Interne : W2-D §C.5 (gels G1–G6, dont probabilités de scénarios gelées avant exécution), R3 (Brier/REL/RES/UNC, « NON CALCULÉ — N insuffisant »), V0.2 §9.3.

## 7. Interne — moteur v0 et épisodes (blocs g)

- `src/orvyren/decision/scenarios.py` : H1/H2/H3 pré-enregistrées, seuils gelés (décote 1 %, tolérance agrégat 0,5 %, récupération 0,1 % < 12 h, persistance > 12 h, baisse d'offre 1 %/24 h) ; verdicts SUPPORTED/REFUTED/INCONCLUSIVE + evidence_refs + missing_inputs.
- `engine.py` : règle pré-enregistrée (H2 SUPPORTED & available_to_move>0 → ACTION_RECOMMENDED : transfert de test 100 USDC D8 ; H1&H2→NO_ACTION ; manque → INCONCLUSIVE règle 4 prioritaire) ; dossier = verdict/action/rationale/conditions/limits/provenance/missing_inputs ; `calibration: null`.
- `baseline.py` : A0 = seuil agrégateur < 0,99 pendant 2 obs → réduction 100 USDC ; 0 faux signal sur la fenêtre contrôle (15-18/02/2023), 2 signaux sur la fenêtre principale (evidence/baseline_report.json).
- `evidence/decision_usdc-2023-03.json` : H1 REFUTED (persistance bitstamp 42 h, binance 45 h) ; H2 SUPPORTED (34 heures simultanées ; baisse d'offre −7,1722 % sur 24 h ; plus bas corpus : bitstamp 0,86267, binance 0,91280) ; H3 REFUTED ; ACTION_RECOMMENDED.
- `evidence/episode_usdc_2023-03.json` (W3-B, 15/10) : dispersion 870,07 bps reproduite ; dispersion horaire max 1 047,7 bps (11/03 08:00) ; divergence oracle/marché extrême **−558,9 bps à 03:00** ; min oracle dense **0,8833** (07:53:23, bloc 16 803 515) — correction de W2-B (0,90687 était le min de sa grille) ; minima venues : Binance 0,8820 / OKX 0,8698 / Bitstamp 0,80526 / DeFiLlama 0,876675 ; Aave U : 0,6443 → pic 0,8727 (11/03 03:00) → 0,2754 (12/03 23:00).
- Conventions corpus v0 (à réconcilier) : `corpus/usdc_observations.csv` = clôtures horaires Bitstamp (min **0,86267**) + DeFiLlama horaire ; W3 = **plus bas** horaires + DeFiLlama chart (min **0,80526**/0,876675). MESURÉ (interne).
- `evidence/episode_rseth_2026-04.json` : cap_ratio max **0,9999886466** (18/04 18:00, bloc 24 908 406) ; gel 24 908 722→723 = **19:03:59** ; oracle retenu 2 526,76 $ à l'exploit / 2 513,66 $ au gel / 2 419,21 $ le 20/04 ; U WETH 88,6 %→accéléré→**100,0079 %** (19/04 08:00) ; WETH gelé + LTV 0 ; USDC Aave : cash **6 403 $** pour 2,47 Md$ de supply le 19/04 08:00 (utilisation-cash ≈ 99,9997 %) ; feed « Capped rsETH / ETH / USD » (latestRoundData réverte).
- `evidence/episode_steth_2022-06.json` (W3-A) : décote réalisable `get_dy` — régime > 2 % dès le **13 mai 2022** (213,7 bps) ; pic **6,925 %** (14/06 10:00, bloc 14 961 150) ; 6,42 % le 15/06 22:00 ; 227/253 points > 200 bps jusqu'au 31/07 ; oracle STETH/ETH 0,941992 vs vente 0,93075 (14/06) — écart 119–186 bps.
- Fenêtres DEV/EVAL (W2-D §C.2) : USDC + stETH = développement ; rsETH + USD0++ = évaluation ; xUSD = qualitatif seulement.

## 8. Divers / pièges de recherche

- Le moteur v0 utilise des fixtures d'exposition (500/350/100 USDC) — démonstration, pas portefeuille réel.
- `corpus` limite : Couverture Bitstamp sparse ; Kraken/Coinbase indisponibles (W3-B §5).
- Non trouvé (15/10/2026) : budgets de risque chiffrés publiés par une DAO ; probabilités publiques de scénarios de dépeg ; cibles chiffrées de desks ; VoI appliquée à la finance par des agents LLM (les cadres trouvés sont génériques) ; vérification d'un usage réel d'ACH par un agent LLM financier.

## 9. Fichiers bruts du dossier raw_b3/

- `web_batch1_ach.json`, `web_batch2_voi_abstention.json`, `web_batch3_dao_desk.json`, `web_batch4_details.json`, `web_batch5_final.json`, `web_batch6_authors.json` — résultats de recherche (titres/URL/snippets).
- `ncbi.nlm.nih.gov_pmc_articles_PMC11169332.md`, `arxiv.org_html_2502.09858v1.md`, `arxiv.org_html_2610.18298v1.md`, `link.springer.com_doi_10.1007_s10994-024-06534-x.md`, `zenodo.org_records_17843044.md` — extraits.
- `abs_2610.07509.md`, `abs_2607.27143.md`, `abs_2502.09858.md`, `abs_2610.12360.md` — abstracts arXiv.
- `mandel_karvetski_2018_jdm.md` — PDF JDM 2018.
- `cia_tradecraft_primer_apr09.md` — extrait du primer CIA.
- `cryptonews.net_news_altcoins_20663169_.md` (MakerDAO), `governance.aave.com_t_rseth-incident-report-april-20-2026_24580_1.md` (LlamaRisk), `www.cambridge.org_..._boosting-intelli.md`.
