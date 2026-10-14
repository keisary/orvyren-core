# R3 — Évaluation et stress-testing d'un agent IA financier
## État de l'art, protocole pour ORVYREN-Core, benchmark multi-cas
**Version : 1.0 — 14 octobre 2026, 23 h UTC.** Recherche documentaire et vérifications réseau effectuées le 14 octobre 2026.
Public visé : jury du concours FinTech Shenzhen 2026 (thème F — *Autonomous On-chain Wallet*), relecteurs techniques, membres de l'équipe.

**Règle de lecture.** Chaque affirmation porte un statut.
`MESURÉ` = vérifié par nos propres appels API le 14/10/2026 (commande et réponse citées).
`SOURCÉ` = document public daté, lu directement.
`SECONDAIRE` = presse, blog d'éditeur ou résumé, non ouvert à la source primaire.
`HYPOTHÈSE` = jugement de conception, non démontré.
`NON TROUVÉ` = recherché sans résultat exploitable.

Ce document ne remplace pas une évaluation : il définit **ce qu'il faut mesurer, comment, et ce qu'on a le droit d'écrire**. Aucun chiffre de performance d'ORVYREN n'est revendiqué ici.

---

## 0. Pourquoi cette pièce existe

Le dossier V0.2 et `FREEZE_V1.md` déclarent déjà cinq métriques d'acceptation (§12.2) : provenance 100 %, 0 action hors politique sur ≥ 6 attaques, 10 parcours E2E consécutifs, comparaison baseline, coût par décision. Ces métriques sont **des critères de complétude de démonstration**, pas des mesures de qualité de décision. Elles prouvent que le système fait ce qu'il dit ; elles ne prouvent pas qu'il décide mieux qu'une règle simple.

État au 14/10/2026 (`MESURÉ`, exécution locale) :
- corpus USDC/SVB : **1 375 observations** agrégées, 6 sources, fenêtre principale + fenêtre témoin ;
- couverture qualité : **145 / 145 heures** avec ≥ 2 venues indépendantes (Binance 83 h, Bitstamp 145 h, DeFiLlama 145 h, séries d'offre 7 j) ;
- baseline **A0** (seuil 0,99 × 2 observations consécutives) : **2 signaux** en fenêtre principale, **0** en fenêtre témoin ;
- verdicts d'hypothèses pré-enregistrées : H1 **REFUTED**, H2 **SUPPORTED**, H3 **REFUTED** ;
- décision : `ACTION_RECOMMENDED` (transfert de 100 USDC de test) ;
- tests : **116 tests définis, 114 passés + 2 ignorés** (`pytest -q`, 2,40 s).

Ce qui manque, et que ce rapport construit : **un protocole d'évaluation falsifiable** (§B), **un benchmark multi-cas avec vérité terrain publique** (§C), et **la liste des pièges qui rendent une évaluation malhonnête** (§D).

## 0.1 — Articulation avec les autres pièces du dossier

| Pièce | Ce qu'elle apporte | Ce que R3 (ce document) en fait |
|---|---|---|
| `R1_orchestration_VOI.md` | formules EVPI / EVPPI / EVSI ; orchestrateur sous budget ; registre de branches `CREATED → UNDER_TEST → SUPPORTED/REFUTED/ARCHIVED` | l'ablation **A−R** (§B.4) est la **mesure** de la valeur de l'information achetée : le budget de recherche est retiré et redéployé, on mesure le regret par USDC dépensé, pas le nombre d'appels |
| `AXES_AMELIORATION_FULGURANTE.md`, AXE E | « l'évaluation qui rend les affirmations crédibles » | §B (protocole) et §D (honnêteté) en sont l'implémentation |
| `AXES_AMELIORATION_FULGURANTE.md`, AXE G | calibration et apprentissage gouverné | §B.1 M2/M3 (Brier + décomposition, ECE) et §A.19 fournissent les métriques et la règle « pas de confiance verbalisée comme probabilité » |
| `FREEZE_V1.md` | décisions D1–D12, dont D11 (« score de Brier si ≥ 5 prévisions gelées ») | §B.1 M2 fixe la formule, la décomposition et le seuil d'application ; §B.6 les chiffre en effort |
| `corpus/README.md` | 1 375 observations, règles d'usage des sources | §C.8 (fenêtres témoins) et §D.9 (sources non indépendantes) prolongent ces règles |

---

# (a) État de l'art — 16 points

## A.1 — Benchmarks de questions/réponses financières

**1. Vals AI — Finance Agent v1.1** `SOURCÉ`
Papier : *Finance Agent Benchmark: Benchmarking LLMs on Real-world Financial Research Tasks*, arXiv:2508.00828, soumis le **20 mai 2025** (<https://arxiv.org/abs/2508.00828>). Leaderboard v1.1 consulté le **14/10/2026** (<https://www.vals.ai/benchmarks/finance_agent>).
Ce que c'est : **537 questions expertes** réparties en **9 catégories** de tâches (retrieval quantitatif/qualitatif, earnings, tendances, modélisation financière, analyse de marché), construites avec des praticiens de banques, hedge funds et private equity. Un *harness* agentique fournit Google Search et l'accès EDGAR. Notation par **LLM-as-judge à rubriques** — évaluation point par point contre la solution experte, pas globalement.
Chiffres du papier (v1.0) : meilleur modèle (OpenAI o3) **46,8 %** de précision, coût moyen **3,79 $/question**.
Rafraîchissement v1.1 (« début 2026 ») : contrôle qualité des données par AfterQuery avec des experts (Goldman Sachs, Silver Lake, Citadel cités) ; passage de dates relatives à des **dates absolues** ; moteur de recherche SerpAPI → **Tavily** ; soumission via un *tool call* `submit` ; **juge GPT-5.2 en mode de 3 évaluations** pour réduire la variance ; consigne de ne pas arrondir les calculs intermédiaires.
État du leaderboard au 14/10/2026 : Claude Opus 4.7 **64,37 % ± 2,79**, Claude Sonnet 4.6 63,33 %, DeepSeek V4 60,39 % (cité à titre d'illustration de la progression, pas comme référence à battre).
**Ce que ça mesure** : la capacité à produire une **réponse** correcte et sourcée à une question d'analyste, coût et latence associés.
**Ce que ça ne mesure pas** : aucune **décision** (le benchmark ne demande jamais d'agir), aucun **coût du refus** (l'abstention n'est pas une catégorie scorée), aucune **exécution** (pas de transaction, pas d'état modifié), aucune **allocation bornée** (pas de notion de montant, de plafond, ou de perte), aucune **reproductibilité bit-à-bit**, et pas de mesure de ce qui se passe quand la donnée est **contradictoire entre sources**.

**2. FinanceComplexQA** `SOURCÉ`
arXiv:2607.19238, soumis le **21 juillet 2026** (<https://arxiv.org/abs/2607.19238>) ; code : <https://github.com/buaacxf/FinanceComplexQA>.
Ce que c'est : **2 026 tâches de deep research** portant sur **1 009 documents financiers** industriels (mise en page complexe), produites à partir d'un *skill* de synthèse de documents financiers (Finance-LaTeX SKILL) qui a généré **2 000 documents et 6 000 paires question-réponse**. Bilingue chinois/anglais, 6 scénarios et 7 types de tâches. Évaluation par **Agent-as-a-Judge** (un agent évalue un agent) avec **métriques multiples**, sur des réponses ouvertes. Étude d'échecs dédiée : calcul numérique, raisonnement multi-sauts, synthèse, analyse sectorielle.
**Ce que ça mesure** : la qualité d'une **réponse argumentée** produite en lisant de vrais documents, et la capacité d'un juge automatique à la noter finement.
**Ce que ça ne mesure pas** : rien d'actionnable. Pas d'action, pas de montant, pas d'exécution, pas de coût de transaction. Le « Agent-as-a-Judge » introduit de plus une **dépendance circulaire** (des agents jugent des agents) que le benchmark atténue par des références stables mais qui reste une mesure de génération, pas de vérité terrain externe.

**3. FinanceBench** `SOURCÉ` (papier) + `SECONDAIRE` (chiffres presse)
arXiv:2311.11944, **20 novembre 2023** (<https://arxiv.org/abs/2311.11944>) ; annonce Patronus AI (<https://www.patronus.ai/announcements/patronus-ai-launches-financebench-the-industrys-first-benchmark-for-llm-performance-on-financial-questions>).
Ce que c'est : **10 231 questions** en *open-book QA* sur des sociétés cotées, avec réponses et chaînes de preuve (*evidence strings*). Résultats annoncés par l'éditeur : GPT-4 Turbo avec retrieval **échoue 81 %** du temps ; en contexte long, **21 %**.
**Ce que ça mesure** : la fidélité d'extraction et le raisonnement arithmétique sur des documents publics.
**Ce que ça ne mesure pas** : toute forme de décision, d'exécution, d'incertitude quantifiée. La phrase de l'éditeur résume l'écart : « la marge d'erreur est simplement trop grande pour des applications financières » — constat sur la **réponse**, pas sur l'**action**.

**4. FinBen** `SOURCÉ`
arXiv:2402.12659, **NeurIPS 2024** (Datasets & Benchmarks Track) ; code <https://github.com/The-FinAI/FinBen>.
Ce que c'est : le benchmark financier le plus large en couverture — **35–36 datasets, 23–24 tâches**, sept familles de compétences (information extraction, analyse de sentiment, NER, Q&A, génération de texte, gestion des risques, détection de fraude, prévision), trois niveaux de difficulté.
Limites **reconnues par les auteurs eux-mêmes** (section Limitations) : contraintes de calcul limitant le nombre de modèles évalués ; données **américaines et anglophones** ; taille restreinte des jeux ; pas d'usage décisionnel recommandé.
**Ce que ça mesure** : un profil de compétences NLP financières.
**Ce que ça ne mesure pas** : la décision, et de l'aveu des auteurs, pas non plus la robustesse hors marché américain.

## A.2 — Benchmarks d'agents (le déplacement du curseur)

**5. AgentBench** `SOURCÉ`
arXiv:2308.03688, **7 août 2023** (v3 révisée le 4 octobre 2025), publié **ICLR 2024** (<https://arxiv.org/abs/2308.03688>).
Ce que c'est : **8 environnements distincts** (OS, base de données, jeux, raisonnement, etc.) pour évaluer le LLM *en tant qu'agent*, avec package d'évaluation. Résultat principal : écart fort entre modèles commerciaux et open-source ≤ 70 B ; causes d'échec = raisonnement long, prise de décision, suivi d'instructions.
**Ce que ça mesure** : la compétence agentique générique dans des environnements interactifs.
**Ce que ça ne mesure pas** : aucun environnement financier, aucune contrainte réglementaire, aucune exécution on-chain, aucune conséquence pécuniaire.

**6. τ-bench** `SOURCÉ`
arXiv:2406.12045, **17 juin 2024**, Sierra Research (<https://arxiv.org/abs/2406.12045>) ; site <https://taubench.com/>.
Ce que c'est : conversations simulées utilisateur/agent avec outils et **règles métier** (domaines retail et airline). Évaluation par **comparaison de l'état final de la base de données avec l'état objectif annoté** — mesure déterministe, pas d'LLM-as-judge pour le verdict final. Métrique phare : **pass^k** = fraction des tâches réussies sur **les k essais**, par opposition à pass@k.
Résultat : les agents de function-calling « state-of-the-art » (ex. GPT-4o) réussissent **< 50 %** des tâches et sont incohérents — **pass^8 < 25 %** en retail.
Formellement : pass@k ≈ 1 − (1−p)^k *monte* avec k ; pass^k ≈ p^k *s'effondre*. Un agent à 70 % de réussite n'a que ~0,70⁸ ≈ 6 % de chances de réussir 8 fois de suite.
**Ce que ça mesure** : la **fiabilité sous répétition** d'un agent qui suit des règles, avec un état vérifiable.
**Ce que ça ne mesure pas** : la qualité *économique* de la décision. Un agent peut être parfaitement reproductible et prendre systématiquement la mauvaise décision.

**7. τ²-bench** `SOURCÉ`
arXiv:2506.07982, **9 juin 2025** (<https://arxiv.org/abs/2506.07982>).
Ce que c'est : extension en **dual-control** (Dec-POMDP) où **l'agent et l'utilisateur modifient tous deux l'état du monde** avec des outils. Générateur de tâches compositionnel, simulateur d'utilisateur contraint par l'environnement. Point le plus utile pour nous : **« analyse fine des performances par de multiples ablations, en séparant les erreurs de raisonnement des erreurs de communication/coordination »**.
**Ce que ça mesure** : la coordination et la robustesse d'un agent à deux mains, plus la **décomposition des causes d'échec par ablation**.
**Ce que ça ne mesure pas** : la finance (domaine telecom), ni le coût du risque.

**8. Agent Market Arena (AMA) / « When Agents Trade »** `SOURCÉ`
arXiv:2510.11695, octobre 2025 (<https://www.alphaxiv.org/abs/2510.11695v1>).
Ce que c'est : premier benchmark **lifelong, temps réel, multi-marchés** pour agents de trading, avec données vérifiées, actualités contrôlées par des experts, 4 architectures d'agents (InvestorAgent, TradeAgent, HedgeFundAgent, DeepFundAgent) × 5 backbones LLM. Contrôle qualité humain explicite : **2 experts financiers indépendants** échantillonnent quotidiennement les résumés.
Résultat cité : **l'architecture d'agent explique plus de variance que le choix du modèle**.
**Ce que ça mesure** : la performance **live** (non backtestable à l'avance) d'agents de trading sur crypto et actions.
**Ce que ça ne mesure pas** : notre objet. Un agent de trading optimise un rendement sur une position continue ; ORVYREN produit une **action bornée, plafonnée, auditée**. AMA ne mesure ni la politique de permissions, ni le refus, ni la traçabilité de provenance.

**9. AI-Trader** `SECONDAIRE` (résumé consulté, papier non ouvert)
arXiv:2512.10971, décembre 2025. Positionné comme « le premier benchmark entièrement automatisé, live et **data-uncontaminated** » pour agents LLM en décision financière. **Utilité pour nous** : le terme *data-uncontaminated* nomme explicitement le problème de contamination (le cas de test est déjà dans les données d'entraînement du modèle) — voir §D.1.

**10. InvestorBench** `SECONDAIRE` (résumé d'éditeur, 2 juin 2026)
<https://beancount.io/it/bean-labs/research-logs/2026/06/02/investorbench-llm-agent-financial-decision-making> — « la plupart des benchmarks finance testent si les LLM peuvent répondre à des questions ; InvestorBench demande si un agent peut **décider** ». Signal de tendance : la littérature 2026 se déplace effectivement de la réponse vers la décision. Aucun chiffre repris ici (non ouvert).

**Synthèse A.1–A.2 — la case vide.** Sur les dix benchmarks ci-dessus, **aucun** ne mesure les six propriétés que le thème F rend obligatoires : (i) l'action **exécutée** et son état résultant vérifiable ; (ii) l'action **bornée** (plafond par transaction et cumulé) ; (iii) le **refus** correctement motivé ; (iv) la **provenance** de chaque claim déterminant ; (v) le coût du **faux positif** (agir sans raison) ; (vi) la chaîne complète *corpus → hypothèse → décision → politique → exécution*, jugée de bout en bout sur données publiques archivées. C'est précisément la niche d'ORVYREN, et c'est un argument de différenciation **défendable** à condition de le formuler comme une **lacune des benchmarks existants**, jamais comme « personne ne fait cela ».

## A.3 — Ce que les régulateurs demandent (et ce qui a changé en 2026)

**11. UK Treasury Committee — rapport « AI in financial services » (HC 684)** `SOURCÉ`
Publié le **20 janvier 2026** : <https://publications.parliament.uk/pa/cm5901/cmselect/cmtreasy/684/report.html> ; communiqué : <https://committees.parliament.uk/committee/158/treasury-committee/news/211401/current-approach-to-ai-in-financial-services-risks-serious-harm-to-consumers-and-wider-system/>.
Faits saillants lus directement : **> 75 %** des firmes britanniques de services financiers utilisent l'IA, l'adoption la plus forte chez les assureurs et banques internationales ; **84 soumissions écrites** ; quatre sessions de témoignages oraux ; la régulation. Recommandations structurantes : (i) **le BoE et la FCA doivent conduire des stress tests spécifiques à l'IA** ; (ii) la FCA doit publier d'ici fin 2026 des orientations pratiques sur l'application des règles de protection des consommateurs à l'IA et sur l'accountability des *senior managers* ; (iii) le Trésor doit désigner les principaux fournisseurs d'IA et de cloud comme **Critical Third Parties (CTP)** d'ici fin 2026. Constat central du rapport : **ni le BoE ni la FCA ne conduisent de stress test IA spécifique** (cyber ou marché), et **aucune organisation n'a été désignée** sous le régime CTP plus d'un an après sa création.
Formulation exacte de la recommandation (citée in extenso dans la réponse des régulateurs) : *« To build firms' readiness for AI-driven market shocks, the Bank of England and the Financial Conduct Authority must conduct AI-specific stress testing. »*
Texte de la recommandation issu de la réponse des régulateurs : `SOURCÉ` (<https://publications.parliament.uk/pa/cm5901/cmselect/cmtreasy/1791/report.html>, §3 *TSC recommendations for the Bank*).

**12. Réponses des régulateurs (HC 1791 — septième rapport spécial)** `SOURCÉ`
Publié le **16 avril 2026** : <https://publications.parliament.uk/pa/cm5901/cmselect/cmtreasy/1791/report.html>. Les réponses ont été fournies par HMT (18 mars 2026), la FCA (18 mars 2026) et la Banque d'Angleterre (**1er avril 2026**). Le détail de la lettre du BoE est directement accessible : <https://www.bankofengland.co.uk/-/media/boe/files/letter/2026/response-to-tsc-inquiry-report-on-ai-in-financial-services> (Sarah Breeden, Deputy Governor for Financial Stability, 1er avril 2026).

Points à retenir, cités depuis la lettre :
- **Herding / comportements corrélés** — la phrase clé, à connaître par cœur : *« Separately, the Bank is pursuing work on simulation methods with international counterparts to better understand the conditions under which **AI agents trading in financial markets could demonstrate correlated behaviour or “herding”** and so potentially exacerbate procyclical dynamics to amplify a stress scenario. This work could also explore how such dynamics could be mitigated, for example through exploring how **agents' objective functions should best take account of public policy objectives**. »*
- **Tests** : le BoE fait de l'analyse de scénarios sur les trajectoires d'investissement/adoption de l'IA et travaille à **incorporer des scénarios IA dans les tests cyber et opérationnels** du secteur.
- Le BoE récuse la caractérisation « wait and see » et rappelle que la PRA a publié dès 2023 les **Model Risk Management Principles (SS1/23)**, volontairement agnostiques à la technologie et focalisés sur les résultats, avec des facteurs pertinents pour les modèles d'IA : **appétit au risque, tiering des modèles, explicabilité/interprétabilité, données et sur-apprentissage, validation indépendante, surveillance continue** (source : <https://www.bankofengland.co.uk/prudential-regulation/publication/2023/may/model-risk-management-principles-for-banks-ss> — SS1/23, mai 2023, entrée en vigueur le **17 mai 2024**).
- Le FPC a quatre domaines de focus IA depuis **avril 2025** : (1) IA dans la décision financière cœur des banques/assureurs ; (2) IA dans les marchés financiers ; (3) risques opérationnels liés aux fournisseurs d'IA ; (4) environnement de cyber-menace. Référence : *Financial Stability in Focus*, avril 2025 (<https://www.bankofengland.co.uk/financial-stability-in-focus/2025/april-2025>).
- **AI Consortium** (BoE + FCA, créé en mai 2025) : quatre axes dont *« l'évolution des “cas limites” de l'IA »* et *« la contagion accélérée par l'IA dans les marchés financiers »* ; rapport attendu en 2026.
- Réponse de la FCA : **AI Live Testing** et **Supercharged Sandbox** (avec NayaOne, AWS, Nvidia) ; **AI Update 2024** (cadre existant : Consumer Duty, SM&CR, résilience opérationnelle) ; **Mills Review** sur l'impact de l'IA sur le retail à horizon 2030+ ; publication d'un **rapport d'évaluation du AI Live Testing fin 2026 / début 2027**. La FCA écrit explicitement que les firmes doivent **intégrer l'IA dans leurs propres tests de scénarios de résilience opérationnelle**, et que les tests de scénarios conjoints viendront avec les désignations CTP.

**13. FSB — « Sound Practices for Responsible Adoption of AI »** `SOURCÉ`
Consultation publiée le **10 juin 2026** : <https://fsb.org/2026/06/sound-practices-for-responsible-adoption-of-artificial-intelligence-ai-consultation-report> (PDF : <https://fsb.org/uploads/P100626.pdf>). Réponses attendues jusqu'au **22 juillet 2026** ; réponses publiques publiées en août 2026 ; événement de sensibilisation le 7 juillet 2026.
Contenu : **12 sound practices** organisées le long du cycle de vie de l'IA (gouvernance d'entreprise, développement, déploiement), avec études de cas réels d'institutions financières. Question de consultation n° 3, directement pertinente pour nous : les pratiques équilibrent-elles correctement la gestion des risques de **toutes** les formes d'IA et celle des risques liés aux **formes émergentes et complexes, telles que la GenAI et l'IA agentique** ?
À compléter par le rapport antérieur du FSB, *Monitoring Adoption of AI and Related Vulnerabilities in the Financial Sector*, **10 octobre 2025** (<https://www.fsb.org/uploads/P101025.pdf>), qui documente les **lacunes de données** empêchant le suivi de l'adoption de l'IA.

**14. Bank of England — Financial Stability Report, juillet 2026** `SOURCÉ`
Publié le **7 juillet 2026** : <https://www.bankofengland.co.uk/financial-stability-report/2026/july-2026> (PDF : <https://www.bankofengland.co.uk/-/media/boe/files/financial-stability-report/2026/financial-stability-report-july-2026.pdf>).
Éléments lus : *« Recent rapid advances in frontier Artificial Intelligence (AI) capabilities have increased financial stability risks related to cyber and operational resilience »* ; le FPC y présente **son cadre prospectif de suivi des implications macrofinancières des développements de l'IA** ; sur les marchés, concentration accrue des indices sur un petit nombre de valeurs liées à l'IA et **hausse significative du levier des hedge funds**, avec le risque d'un *« disorderly unwind »*. La phrase sur les positions corrélées est directement transposable à l'argumentaire ORVYREN : *« high concentration, correlated momentum-driven positions that can exacerbate volatility as markets fall »*.

**15. « Evidence pack » : ce qu'un dossier doit contenir** `SECONDAIRE` (source praticien, pas texte réglementaire)
Aveni, *AI agent stress testing for financial services: what good looks like*, **10 juin 2026** (<https://aveni.ai/blog/ai-agent-stress-testing-financial-services/>).
Cette source est un cabinet, pas un régulateur : à citer comme **pratique de marché**, jamais comme exigence. Elle est néanmoins utile parce qu'elle nomme trois artefacts repris partout dans les programmes de conformité 2026 :
1. **failure mode inventory** — chaque catégorie d'échec identifiée, avec fréquence, sévérité et conditions de déclenchement ;
2. **remediation log** — pour chaque mode d'échec : ce qui a été changé, quand, et comment cela a été retesté ;
3. **residual risk statement** — ce qui reste non testable, les conditions auxquelles l'agent n'a pas été exposé, et la surveillance requise après déploiement.
Elle rappelle aussi que le *stress testing* d'agents n'est **ni** la validation de modèle au sens SS1/23 (écrit pour des modèles déterministes), **ni** du red teaming générique (OWASP Top 10 for LLM Applications), **ni** du QA rétrospectif (échantillonner 3 % des interactions ne dit rien des 97 % restants). Et que l'accountability retombe sur le *senior manager* nommé (SMCR), pas sur l'agent.
**Pour ORVYREN** : ces trois artefacts sont reproductibles en 6 jours et transforment un dossier de concours en dossier lisible par un risk officer. Ils sont proposés en §B.6.

**16. Angle manquant côté régulateur** `NON TROUVÉ`
Recherché sans résultat : un texte réglementaire publié (FCA, PRA, BoE, ESMA, BCE) qui **définisse formellement le contenu obligatoire d'un « evidence pack » IA** ou qui fixe un format de stress test IA opposable. La recommandation du TSC est une **injonction aux régulateurs**, pas encore un cadre publié ; la FCA annonce un rapport d'évaluation du AI Live Testing fin 2026/début 2027. **Conséquence honnête** : toute revendication de conformité à un « standard de stress test IA » serait fausse au 14/10/2026. On peut seulement revendiquer une **convergence de vocabulaire** avec la littérature émergente.

## A.4 — Mesurer une qualité de décision

**17. Brier score et sa décomposition** `SOURCÉ`
Score de Brier (Brier 1950) pour un événement binaire : `BS = (1/N) · Σ (p_t − y_t)²`, avec `p_t` la probabilité publiée et `y_t ∈ {0,1}` l'issue observée. Décomposition de **Murphy (1973)**, *A New Vector Partition of the Probability Score*, **Journal of Applied Meteorology 12(4), 595–600** (<https://doi.org/10.1175/1520-0450(1973)012<0595:ANVPOT>2.0.CO;2>) :
`BS = REL − RES + UNC`, où
`REL = Σ_b (n_b/N)(p̄_b − ȳ_b)²` (fiabilité : à quel point la probabilité annoncée correspond à la fréquence observée),
`RES = Σ_b (n_b/N)(ȳ_b − ȳ)²` (résolution : à quel point les prévisions séparent les cas),
`UNC = ȳ(1 − ȳ)` (incertitude : propriété de l'échantillon, pas du modèle).
**Pourquoi c'est le bon outil ici** : REL et RES se compensent parfois, donc un BS global identique peut cacher un modèle « chanceux ». Publier les trois termes sépare l'honnêteté (REL) de la compétence (RES). Un système qui annonce toujours 0,5 a un REL parfait et un RES nul.

**18. ECE et courbes de fiabilité** `SOURCÉ`
**ECE** (Expected Calibration Error) popularisé par Naeini, Cooper & Hauskrecht, *Obtaining Well Calibrated Probabilities Using Bayesian Binning*, **AAAI 2015** (<https://ojs.aaai.org/index.php/AAAI/article/view/9602>). Formule binned standard :
`ECE = Σ_b (n_b/N) · |acc(b) − conf(b)|`, avec `B` bins (10 est la convention), `acc(b)` la justesse empirique du bin, `conf(b)` la confiance moyenne annoncée.
**Piège à documenter** : l'ECE dépend du **nombre de bins** et du **nombre d'observations**. Avec nos 46 observations de la fenêtre principale, un ECE à 10 bins a en moyenne ~4,6 points par bin — l'ECE sera **bruité et non comparable** entre deux systèmes. Recommandation en §B.5 : rapporter ECE **avec** la courbe de fiabilité et l'IC bootstrap, et refuser toute conclusion tirée d'un ECE sur < 100 observations.

**19. Calibration des réseaux profonds et des LLM** `SOURCÉ` (Guo) + `SECONDAIRE` (études 2024–2026)
Guo, Pleiss, Sun & Weinberger, *On Calibration of Modern Neural Networks*, **ICML 2017**, arXiv:1706.04599 (<https://arxiv.org/html/1706.04599v2>) : les réseaux modernes sont systématiquement **sur-confiants** ; le **temperature scaling** (un seul paramètre, division des logits par T) est la méthode post-hoc la plus efficace. Établit que la calibration est un problème distinct de la précision.
Pour les LLM : la synthèse *A Survey of Confidence Estimation and Calibration in LLMs*, arXiv:2311.08298 (<https://www.alphaxiv.org/abs/2311.08298>) documente que la **confiance verbalisée** (le modèle qui écrit « je suis sûr à 85 % ») est mal calibrée, et que deux signaux coexistent et divergent : la probabilité des tokens et la confiance exprimée en langage.
Études 2024–2026 `SECONDAIRE` : *Mind the Confidence Gap* (février 2025) rapporte que les modèles entraînés par RLHF émettent majoritairement des scores de confiance entre 80 % et 100 %, avec des ECE pouvant **atteindre 0,30** sur des tâches intensives en connaissance ; l'étude arXiv:2601.08064 (**janvier 2026**, <https://arxiv.org/html/2601.08064v1>) sur la confiance sous variations de langue ; la synthèse zylos.ai (18 avril 2026) qui cite arXiv:2601.07767 (janvier 2026) : les modèles savent verbaliser leur incertitude, mais **ne l'utilisent pas pour guider leurs propres décisions**.
**Conséquence de conception pour ORVYREN** : ne **jamais** utiliser la confiance verbalisée d'un LLM comme signal de contrôle interne, et ne jamais la présenter comme une probabilité calibrée. La probabilité publiée doit provenir d'un **estimateur explicite et testable** (comptage empirique sur les fenêtres de calibration, ou modèle de comptage simple), pas d'une phrase du modèle.

**20. Conformal prediction — garanties sans hypothèse de distribution** `SOURCÉ`
- Fondement accessible : Angelopoulos & Bates, *A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification*, arXiv:2107.07511 (<https://arxiv.org/abs/2107.07511>). Idée : à partir d'un **score de non-conformité** et d'un ensemble de calibration échangeable, produire des intervalles avec **couverture marginale garantie** `≥ 1 − α` **sans hypothèse sur la distribution**.
- Limite en finance : l'échangeabilité est violée par la non-stationnarité. Travaux récents : *Conformal Prediction for Time-series Forecasting with Change Points* (**CPTC**, Sun & Yu, **NeurIPS 2025**, <https://github.com/Rose-STL-Lab/CPTC>) ; *Adaptive Conformal Anomaly Detection with Time Series Foundation Models*, arXiv:2604.20122, **ICLR 2026** (<https://arxiv.org/html/2604.20122v1>).
**Pourquoi c'est décisif pour un jury** : avec **un seul épisode de crise**, aucune garantie de fréquence n'est calculable de façon classique. Le conformal déplace la revendication : au lieu de « notre seuil est bon », on écrit « pour tout α, sous échangeabilité, la probabilité de non-couverture est ≤ α », puis on **mesure la couverture empirique** sur les fenêtres témoins. C'est une revendication bornée, vérifiable et honnête — exactement le registre attendu.

**21. Petit échantillon et dépendance temporelle** `SOURCÉ`
Le bootstrap i.i.d. est invalide sur des séries horaires autocorrélées. Il faut un **block bootstrap** (blocs de longueur fixe avec ou sans recouvrement, ou *stationary bootstrap* de Politis & Romano). Implémentation vérifiable et documentée : paquet **arch** de Kevin Sheppard — `CircularBlockBootstrap`, `StationaryBootstrap`, `MovingBlockBootstrap` (<https://arch.readthedocs.io/en/stable/bootstrap/timeseries-bootstraps.html>). Note d'implémentation lue dans la doc : le *moving block bootstrap* ne boucle pas et **sous-échantillonne systématiquement les extrémités** de la série ; la doc recommande donc de préférer le *circular* ou le *stationary* bootstrap. Nous suivrons cette recommandation.

**22. Regret — le concept de qualité de décision** `SOURCÉ`
- Acception théorique de la décision : **Bell, D. E., *Regret in Decision Making under Uncertainty*, Operations Research 30(5), 961–981, 1982** (<https://pubsonline.informs.org/doi/10.1287/opre.30.5.961>) ; développements ultérieurs sur regret et déception (Loomes & Sugden, *Testing for Regret and Disappointment in Choice under Uncertainty*, Economic Journal 97(388), 118–29, 1987 — `SECONDAIRE`, entrée bibliographique).
- Acception algorithmique (celle que nous utiliserons) : le **regret** est l'écart de perte entre la politique et le meilleur choix **ex post** (l'oracle). Définition opérationnelle en §B.1.
**Attention à ne pas confondre** : le « regret » psychologique (l'émotion) et le regret algorithmique (une distance à l'oracle). Le jury doit voir la formule, pas le mot.

**23. Protocoles d'ablation et pré-enregistrement** `SOURCÉ`
- *The Model Proposes, the Code Disposes: A Pre-Registered Ablation of a Verifier-and-Acceptance Stage*, arXiv:2609.15887, 2026 (<https://arxiv.org/html/2609.15887v1>). Intérêt méthodologique : une **ablation confirmatoire pré-enregistrée**, avec statistiques exactes et **pilote échoué divulgué**. C'est le modèle de rédaction à imiter : hypothèse, métrique, seuil de décision, et publication des cas où ça n'a pas marché.
- *ABGEN: Evaluating Large Language Models in Ablation Study Design*, **ACL 2025** (<https://aclanthology.org/2025.acl-long.611.pdf>) : benchmark qui évalue la capacité à **concevoir** des ablations — utile comme source de taxonomie (retrait de composant, sensibilité aux hyperparamètres, alternatives de conception).
- τ²-bench (point 7) fournit l'exemple le plus proche de notre besoin : **ablations séparant les erreurs de raisonnement des erreurs de coordination**.
- Rappel élémentaire mais décisif : une ablation ne vaut que si **les budgets sont égaux**. Comparer un système à 40 appels LLM avec un système à 3 appels ne mesure pas la valeur du composant, mais la valeur du budget.

---

# (b) Protocole d'évaluation RECOMMANDÉ pour ORVYREN

## B.0 — Les quatre règles non négociables

1. **Pré-enregistrement.** Hypothèses, métriques, fenêtres et critères de réfutation sont écrits et **horodatés dans le dépôt avant** l'exécution. Un critère modifié après avoir vu les résultats rend l'évaluation invalide — pas « plus faible », invalide. `FREEZE_V1.md` applique déjà cette règle à H1–H3 ; elle doit couvrir aussi les métriques de décision.
2. **Budgets égaux.** Pour la comparaison A0 ↔ A2 et pour toutes les ablations : même plafond d'appels, de tokens et de temps **par décision**. Les économies d'un composant retiré ne sont pas réinvesties ailleurs sans être déclarées.
3. **L'unité d'analyse est la fenêtre (ou l'épisode), pas l'heure.** 145 observations horaires d'un même épisode ne sont pas 145 preuves indépendantes : elles sont **une** crise. Toute agrégation qui traite les heures comme des tirages indépendants gonfle artificiellement la significativité. C'est la faute la plus fréquente et la plus facile à démonter par un jury.
4. **Le vecteur, pas le scalaire.** Aucun score unique. On publie un **vecteur** de métriques avec intervalles, plus la mention explicite des axes non mesurés.

## B.1 — Les six métriques, avec formules

Notations. Fenêtre `w` (principale ou témoin). Prix d'agrégateur `P_t` en USD ; position exposée `E = 100 USDC` (valeur de démonstration) ; action `a ∈ {NO-ACTION, RÉDUIRE(100)}` ; coût de transaction aller-retour `c` (à documenter, même s'il est nul en testnet).

**M1 — Regret de décision par fenêtre** (métrique principale)
Pour chaque fenêtre `w`, on définit la perte réalisée de l'action choisie, évaluée **ex post** sur la fenêtre :
- `L(NO-ACTION) = E · max(0, 1 − min_{t∈w} P_t) + 0` (perte de valeur si le prix décroche et qu'on n'a rien fait) ;
- `L(RÉDUIRE) = c + E · max(0, (1 − P_{t_action})) − E · max(0, 1 − min_{t∈w} P_t)` — formulation à figer avant l'exécution ; l'important est qu'elle soit **écrite et gelée**, pas qu'elle soit parfaite.
Regret : `R(w) = L(a_choisie) − min_a L(a)`.
On rapporte `R(w)` en **basis points de l'exposition** (bp / 100 USDC) et un **regret normalisé** `R̃(w) = R(w) / |L(NO-ACTION) − L(RÉDUIRE)|` quand le dénominateur est non nul.
**Deux regrets séparés, à ne jamais agréger** : `R⁻` (regret d'avoir agi — coût du faux positif) et `R⁺` (regret de n'avoir rien fait — coût du faux négatif). Un système prudent et un système nerveux ont des profils opposés ; les moyens se compensent et masquent tout.
**Oracle explicite** : l'oracle est calculé **sur la fenêtre** avec la fonction de perte gelée. C'est un oracle *ex post* de la même famille d'actions — pas un oracle omniscient sur les prix futurs.

**M2 — Brier score et décomposition de Murphy**
`BS = (1/N) Σ_t (p_t − y_t)²`, `y_t = 1` si un dépeg soutenu (définition gelée : écart > 1 % persistant ≥ 2 observations) a été observé dans l'horizon `H` (gelé, ex. 6 h) à partir de `t`.
Rapporter `BS`, `REL`, `RES`, `UNC` et la **climatologie** `ȳ` (taux de base). Sans le taux de base, un BS de 0,05 ne veut rien dire.
Seuil d'application : **≥ 5 prévisions gelées** (déjà prévu en `FREEZE_V1.md`, D11). En dessous, écrire `NON CALCULÉ — N insuffisant`.

**M3 — ECE et courbe de fiabilité**
`ECE = Σ_b (n_b/N) |acc(b) − conf(b)|`, 10 bins par défaut, **plus** la courbe de fiabilité complète (une ligne par bin : `n_b`, `conf(b)`, `acc(b)`).
Règle ORVYREN : **ne pas publier d'ECE sans la courbe ni l'IC bootstrap**, et afficher la mention « ECE non conclusionnel si N < 100 » quand c'est le cas. Utiliser de préférence `BS` (M2) quand N est petit, car il ne dépend pas du binning.

**M4 — Conformal / garantie sans distribution**
Statistique de non-conformité `s_t = |P_t − 1|` (ou `max(0, 1 − P_t)` si l'on ne veut tester que la déviation baissière).
Calibration sur un ensemble de fenêtres témoins `C` (non-crise), seuil `q = Quantile_{(1−α)(1+1/|C|)}({s_t : t ∈ C})` (la correction `(1+1/|C|)` est le facteur standard de couverture finie).
Décision : alerter si `s_t > q`. Rapporter :
- `α` choisi **avant** l'exécution ;
- la **couverture empirique** sur les fenêtres témoins restantes (cible `1 − α`, tolérance explicitement annoncée) ;
- le **taux de détection** sur la fenêtre de crise.
**Ce que ça apporte au dossier** : on remplace « notre seuil 0,99 est le bon » (invérifiable) par « pour α = 0,10, la couverture empirique mesurée est X sur Y fenêtres témoins » (vérifiable). Si la couverture échoue, on le publie — l'échec d'une garantie est un résultat.

**M5 — Fiabilité sous répétition : pass^k, en distinguant déterminisme et robustesse**
ORVYREN est **déterministe** sur un corpus donné : `pass^k = 1` par construction. Le publier comme un score de fiabilité serait un abus de vocabulaire (et un jury informé le remarquera, cf. τ-bench où `pass^k` mesure une variance réelle). On rapporte donc **trois choses distinctes** :
- **D1 — déterminisme** : sur `k = 10` rejeux du même corpus, **hash identique** du dossier de décision (`sha256`). C'est une propriété vérifiable mécaniquement.
- **D2 — stabilité sous perturbation** : taux de décisions identiques sur `M` perturbations **pré-définies** (permutation de l'ordre des sources ; injection d'une observation manquante ; décalage du timestamp de collecte de ±1 h ; ajout d'une venue supplémentaire). Rapporter le vecteur de résultats, y compris les cas où la décision change.
- **D3 — stabilité sous reformulation de prompt** : si un LLM intervient, `k` reformulations de la même question ; rapporter la distribution des sorties, pas seulement la modale.
**Formulation à utiliser devant le jury** : « la répétabilité au sens de pass^k est une conséquence du déterminisme ; notre risque de défaillance n'est donc pas la variance d'échantillonnage, mais la **sensibilité aux hypothèses** — d'où D2 et l'ablation. »

**M6 — Sûreté et coût**
- **Sûreté** : `0` action hors politique sur `≥ 6` attaques pré-enregistrées (déjà en V0.2). **Proposition** : monter à **12 attaques** en ajoutant — injection de prompt via donnée de marché, donnée de prix contradictoire entre deux sources, prix nul/négatif, horodatage futur, doublon d'intent, actif au mauvais nombre de décimales. Le taux de `DENY` correct sur ces cas se rapporte comme une **fraction** (n/N) et non comme « 0 échec », car « 0 sur 6 » a un intervalle de confiance énorme (borne supérieure ≈ 39 % à 95 %, cf. B.5).
- **Coût** : appels, tokens, latence et coût monétaire **par décision**, et surtout le **coût par décision utile** (coût total / nombre de décisions non triviales). C'est ce second chiffre qui intéresse un acheteur.

## B.2 — Les comparateurs (l'axe le plus important du dossier)

Un système isolé n'a pas de performance. Il faut un **gradient de comparateurs** :

| Code | Système | Rôle | Coût |
|---|---|---|---|
| **O** | Oracle *ex post* sur la fenêtre | borne inférieure du regret | hors ligne |
| **A0** | Seuil fixe 0,99 × 2 obs (existant) | **l'adversaire à battre** | ~0 |
| **A1** | Seuil 0,99 + confirmation ≥ 2 venues indépendantes | règle simple améliorée | ~0 |
| **A2** | Politique complète ORVYREN (corpus → graphe → hypothèses → branche → critique → politique) | le système revendiqué | plafonné, mesuré |
| **A−x** | Ablations de A2 (voir B.4) | attribution des composants | budget identique |
| **B0** | **Placebo apparié** : même nombre total d'actions que A2, déclenchées à des horodatages **tirés au hasard** dans la même fenêtre (graine fixée, `M ≥ 200` tirages) | sépare « détecter » de « bouger » | ~0 |
| **H** | Aucune action + documentation humaine (le « bons sens » écrit) | contrôle d'interprétabilité | humain |

**B0 est la comparaison la plus honnête et la moins coûteuse à produire.** Si A2 ne bat pas B0 sur le regret, alors la valeur du système n'est **pas** dans le choix du moment, et il faut l'écrire. Cette phrase, dans un dossier de concours, vaut plus que n'importe quel gain marginal.

## B.3 — Le design expérimental

1. **Fenêtres.** Fenêtre principale (crise) + `N_c` fenêtres témoins appariées (même source, même granularité, durée identique). Objectif réaliste sur 6 jours : `N_c = 6` à `12`. **Proposition** : `N_c = 12` (six paires 2022–2023, cf. §C.8).
2. **Appariement.** Chaque paire contient une fenêtre de stress et une fenêtre calme de même longueur. Les comparaisons sont **appariées** (mêmes heures de la journée, même jour de la semaine quand c'est possible).
3. **Gel.** Écrire dans le dépôt, avant exécution : (i) les hypothèses de décision ; (ii) la fonction de perte M1 ; (iii) le taux de base `ȳ` attendu ; (iv) le seuil `α` du conformal ; (v) le seuil de décision de l'évaluation (« on conclut A2 > A0 si … »).
4. **Journal des échecs.** Chaque exécution ratée, chaque hypothèse `REFUTED`, chaque fenêtre où le système se trompe **apparaît dans le rapport final**. Un dossier sans échec déclaré est un dossier non exécuté.
5. **Deux jeux.** Les cas 1–3 servent à **régler** ; les cas 4+ servent à **tester**, une fois, sans retouche. Si un réglage est fait après avoir vu le jeu de test, la mention « jeu de test contaminé » doit apparaître.

## B.4 — Matrice d'ablation

Chaque ligne retire **un** composant de A2, tous les autres paramètres et le budget restant inchangés.

| Variante | Composant retiré | Ce que l'ablation teste | Métriques de sortie |
|---|---|---|---|
| **A2** | — (référence) | — | M1–M6 complet |
| **A−G** | Graphe de provenance (lecture directe du CSV) | la valeur du graphe : détection de contradiction, point-in-time | provenance %, contradictions détectées, M1 |
| **A−C** | Critique adversarial (agent critique retiré) | la valeur du second regard | M1, nombre d'hypothèses réfutées correctement, M3 |
| **A−H** | Hypothèses pré-enregistrées (décision directe sur données) | la valeur de la structure hypothético-déductive | M1, taux d'`INCONCLUSIVE` correct |
| **A−R** | Branche de recherche (valeur d'information) ; budget redéployé déclaré | la valeur de l'information achetée | M1 par USDC dépensé, M6 coût |
| **A−V** | Confirmation multi-venues (agrégateur seul) | la valeur de la redondance de sources | faux signaux sur témoins, M4 couverture |
| **A−S** | Contrainte de plafond (montant libre) | la valeur de la borne (le plafond protège-t-il ou coûte-t-il ?) | M1⁻ / M1⁺ séparés |
| **B0** | Le contenu informatif lui-même (placebo apparié) | le système apporte-t-il **plus** que le fait d'agir ? | M1 |

**Trois pièges d'ablation, à écrire dans le rapport** : (1) retirer un composant change parfois la **distribution des données d'entrée**, pas seulement le raisonnement — l'isoler explicitement ; (2) une ablation sur un seul épisode ne peut rien démontrer (voir B.5) ; (3) les composants interagissent : A−G et A−C peuvent être **non additifs**, et le dire est un signe de sérieux, pas de faiblesse.

## B.5 — Petit échantillon : ce qui est honnête de calculer

**Le chiffre qui décide de tout.** Pour comparer deux systèmes sur une proportion (ex. taux de faux signaux), à α = 0,05 bilatéral et puissance 0,80 (approximation normale, calcul effectué le 14/10/2026) :

| Taux système 1 | Taux système 2 | Fenêtres nécessaires **par groupe** |
|---|---|---|
| 0,50 | 0,30 | **93** |
| 0,50 | 0,35 | **170** |
| 0,40 | 0,15 | **49** |
| 0,90 | 0,60 | **32** |

**Lecture honnête** : détecter un gain modéré de taux d'erreur demande **de l'ordre de 100 fenêtres par groupe**. C'est hors de portée en 6 jours — et c'est aussi hors de portée pour la plupart des publications du domaine. La conclusion à écrire noir sur blanc dans le rapport : **« ce dossier ne démontre pas une supériorité statistique ; il démontre la faisabilité d'une mesure et publie des intervalles. »**

**Ce qui est calculable proprement :**

1. **Intervalles de Wilson** sur les proportions (méthode recommandée plutôt que l'intervalle normal pour les petits n). Valeurs calculées pour nos tailles réelles :

| n | p = 1/n | p = 2/n | p = 3/n |
|---|---|---|---|
| 6 | ±0,267 | ±0,302 | ±0,312 |
| 12 | ±0,170 | ±0,201 | ±0,222 |
| 24 | ±0,098 | ±0,118 | ±0,133 |
| 36 | ±0,068 | ±0,083 | ±0,095 |

Autrement dit : « 0 échec sur 6 » ne signifie **pas** « taux d'échec nul », mais « taux compatible avec jusqu'à ~39 % à 95 % » (borne supérieure de Wilson). Toute communication sur les tests de sûreté doit porter cette phrase.

2. **Test de McNemar exact** pour les comparaisons appariées entre systèmes sur les mêmes fenêtres. Calculs effectués : avec 12 paires, il faut **au moins 6 fenêtres discordantes toutes dans le même sens** pour atteindre p = 0,031 ; à 5 discordances, p = 0,0625 (non significatif). À **24 paires**, il faut ≥ 8 discordances alignées (p = 0,008) mais 8 contre 2 donne p = 0,109 — la dissymétrie est impitoyable. **Conclusion opérationnelle** : publier la table de contingence `[[n11, n10],[n01, n00]]` complète, jamais un « avant/après » agrégé.

3. **Bootstrap par blocs** pour toute statistique sur série horaire : `CircularBlockBootstrap` ou `StationaryBootstrap` (paquet `arch`), longueur de bloc **6 à 12 h** (justification : la persistance du signal de dépeg dans notre corpus est de l'ordre de plusieurs heures ; la longueur doit être ≥ l'échelle d'autocorrélation, et l'arbitrage doit être déclaré). **10 000 réplications**, graine fixée, IC à 95 % par la méthode percentile. Ne **jamais** publier un IC bootstrap i.i.d. sur ces séries.

4. **Conformal (M4)** : garantie valable **sous échangeabilité**. Sur des fenêtres de crise, l'échangeabilité est fausse — il faut l'écrire : *« la garantie de couverture est conditionnelle à l'échangeabilité entre fenêtres de calibration et fenêtres d'application ; cette hypothèse est violée par construction en période de crise, ce que nous mesurons en comparant la couverture prédite à la couverture empirique. »* Cette phrase est plus forte qu'une garantie annoncée sans nuance.

5. **Un seul épisode de crise : ne rien moyenner.** Avec un épisode, on publie : la table du regret heure par heure (`R_t`), le regret cumulé en fin de fenêtre, le détail des décisions. Le regret cumulé est une **trajectoire observée**, pas une estimation — c'est parfaitement défendable si on ne l'habille pas d'une p-valeur.

## B.6 — Ce qui est mesurable en 6 jours vs plus tard

**Faisable d'ici le 20/10/2026** (extension directe du code existant, `MESURÉ` comme déjà fait pour A0) :

| # | Livrable | Effort | Bloque sur |
|---|---|---|---|
| 1 | `evaluation/loss.py` : fonction de perte M1 **gelée et hashée** | 0,5 j | aucune |
| 2 | Regret par fenêtre pour A0, A1, A2, B0 sur la fenêtre principale (100 USDC) | 0,5 j | fonction de perte |
| 3 | 12 fenêtres témoins supplémentaires collectées (boucle de timestamps DeFiLlama + Binance) | 0,5 j | quota API (cf. §D.12) |
| 4 | Brier + REL/RES/UNC sur les prévisions gelées (≥ 5) | 0,5 j | prévisions gelées |
| 5 | Courbe de fiabilité + IC bootstrap par blocs (`arch`) | 0,5 j | #4 |
| 6 | Conformal split sur fenêtres témoins : seuil `q`, couverture empirique | 0,5 j | #3 |
| 7 | Placebo B0 (200 tirages, graine fixée) | 0,5 j | #2 |
| 8 | Ablations A−G, A−C, A−R, A−V sur la fenêtre principale | 1 j | architecture modulaire |
| 9 | 12 attaques de politique (au lieu de 7) + bornes supérieures de Wilson | 0,5 j | politique |
| 10 | **Evidence pack** : inventaire des modes de défaillance, journal de remédiation, déclaration de risque résiduel | 0,5 j | #1–#9 |
| 11 | Section « Ce que nous ne revendiquons pas » dans la doc technique | 0,5 j | — |

Total ≈ 6 j de travail cumulé, mais **1–2 j de chemin critique** si les items 3, 4 et 8 sont menés en parallèle des travaux d'exécution déjà planifiés. **Priorité si le temps manque** : #1, #2, #7, #10. Le placebo et la fonction de perte sont les deux pièces qui distinguent un dossier d'ingénierie d'un dossier scientifique.

**Reporté après le concours** : benchmark multi-cas complet (§C.1–C.7) ; conformal adaptatif avec change points (CPTC) ; calibration sur ≥ 100 observations ; comparaison inter-modèles LLM à budget égal ; test en conditions live (AMA-style) ; revue indépendante par un tiers qui n'a pas écrit le code.

## B.7 — Ce que nous ne revendiquons pas (à recopier dans la doc technique)

1. **Aucune supériorité statistique** n'est démontrée : `N = 1` épisode de crise, ≤ 12 fenêtres témoins. La puissance requise pour un effet modéré est de l'ordre de 100 fenêtres par groupe (B.5).
2. **Aucune validation de conformité réglementaire** : au 14/10/2026, il n'existe pas de cadre de stress test IA opposable publié (§A.16, `NON TROUVÉ`). La convergence est de vocabulaire.
3. **Aucune garantie de performance économique future.** Le backtest sur des épisodes passés est **contaminé** par la mémoire des modèles et ne constitue pas une prédiction.
4. **Aucune preuve de causalité** : si la valeur est préservée après une réduction d'exposition, cela ne démontre pas que la réduction l'a causé.
5. **Aucun audit de sécurité exhaustif** : 12 attaques ne sont pas un audit.
6. **La provenance n'est pas la vérité** : une source traçable peut être fausse (déjà en V0.2 §12.2).

---

# (c) Benchmark multi-cas : cas proposés, données publiques, vérité terrain

## C.0 — Architecture du benchmark

**Objectif** : sortir du cas unique en gardant l'honnêteté. Trois niveaux d'étiquette, à ne jamais mélanger.

- **Vérité terrain L1 — fait documenté.** Un événement daté, attribuable à une source primaire (communiqué d'émetteur, décision de justice, dépôt de bilan, régulateur). Elle **ne dépend pas du prix** : « Circle annonce que 3,3 Md$ de réserves sont chez SVB le 11/03/2023 » est un fait, « USDC a dépeggé » est un jugement sur données.
- **Vérité terrain L2 — étiquette de fenêtre.** `CRISE` / `CALME`, définie par un seuil **gelé** sur les données (ex. `CALME` ⟺ `max|P_t − 1| < 0,5 %` sur toute la fenêtre). Elle est **reproductible par un tiers sur les mêmes données** — c'est la seule définition acceptable.
- **Vérité terrain L3 — contre-factuel de décision.** L'action optimale *ex post*, calculée avec la fonction de perte gelée de §B.1. Elle dépend d'hypothèses explicites (horizon, coût, taille de position). Elle doit **toujours** être publiée avec ses hypothèses.

**Règle d'or** : L3 n'est **jamais** présentée comme un fait. Deux équipes honnêtes avec des fonctions de perte différentes obtiendront des L3 différents — et c'est normal.

**Nom de travail** : `ORVYREN-Crisis-7` (1 cas principal documenté + 6 cas candidats + les fenêtres témoins). **Score = vecteur**, jamais un scalaire composite. Un benchmark qui agrège tout en un nombre encourage l'optimisation de ce nombre (§D.1).

---

## C.1 — USDC / SVB, mars 2023 — **cas principal, acquis**

| Élément | Valeur |
|---|---|
| Fenêtre principale | 2023-03-09 → 2023-03-15, pas horaire |
| Fenêtre témoin | 2023-02-15 → 2023-02-18, pas horaire |
| Statut des données | `MESURÉ` — corpus collecté et archivé, **1 375 observations** |
| Sources | DeFiLlama `coins.llama.fi/prices/historical/{ts}` (agrégateur) ; Bitstamp `api/v2/ohlc/usdcusd` ; Binance `api/v3/klines?symbol=USDCUSDT` ; DeFiLlama `stablecoins.llama.fi/stablecoincharts/{all,Ethereum}?stablecoin=2` (offre) ; déclaration Circle |
| Vérification indépendante du depeg | `MESURÉ` (rapport du 14/10/2026) : DeFiLlama renvoie USDC à **0,9044** le 11/03/2023 à 12 h UTC, après 1,001 le 10/03 et retour à 0,993 le 13/03 |
| **Vérité terrain L1** | Circle, communiqué : **3,3 Md$ de réserves USDC (≈ 8 % des réserves totales) détenus chez Silicon Valley Bank** ; accès aux fonds rétabli après les mesures des autorités. URL : <https://www.circle.com/pressroom/3-3-billion-of-usdc-reserve-risk-removed-dollar-de-peg-closes> |
| **Vérité terrain L2** | `CRISE` (min observé 0,876675 sur l'agrégat, 11/03 08 h UTC — `MESURÉ`, `baseline_report.json`) |
| **Vérité terrain L3** | *ex post*, réduire l'exposition avant le 11/03 ~08 h UTC minimise la perte sur la fenêtre ; le premier signal A0 arrive le 11/03 à 03 h UTC (valeur 0,9798) |
| Rôle | cas de référence, démonstration de bout en bout |
| Limite | `N = 1` épisode → aucun résultat inférentiel ; risque de contamination (épisode de 2023, très documenté) |

## C.2 — UST / Terra, mai 2022 — **cas candidat n° 1**

| Élément | Valeur |
|---|---|
| Fenêtre de crise | 2022-05-07 → 2022-05-16 (à figer) |
| Données | `MESURÉ` (14/10/2026) : DeFiLlama `coins.llama.fi/prices/historical/{ts}/coingecko:terrausd` **répond** et renvoie `symbol = USTC` (UST est devenu USTC après la refonte) ; DeFiLlama `coingecko:luna` **ne répond pas** (`{"coins":{}}`) → la série LUNA n'est **pas** disponible par cette voie |
| Données (2) | `MESURÉ` : Binance `api/v3/klines?symbol=USTUSDT&interval=1h` renvoie des données **depuis 1652054400 (2022-05-09 00:00 UTC)**, ex. 0,9952 le 09/05 ; **0,7604** le 12/05 à 00:00 UTC |
| **Vérité terrain L1** | UST perd son ancrage et **ne le retrouve jamais** ; la chaîne Terra est **arrêtée les 12–13 mai 2022**. Sources de contexte : *Anatomy of a Run: The Terra Luna Crash* (LSE Research Online, <https://researchonline.lse.ac.uk/id/eprint/140488/>) ; *Anatomy of a Stablecoin's failure: the Terra-Luna case*, arXiv:2207.13914 (<https://arxiv.org/html/2207.13914v3>) — `SECONDAIRE` pour les détails factuels, à confirmer en source primaire avant citation dans le dossier final |
| **Vérité terrain L2** | `CRISE`, sans ambiguïté (déviation > 20 %) |
| **Vérité terrain L3** | réduire dès le premier écart > 1 % domine fortement ; l'oracle est presque « réduire immédiatement » |
| Rôle | **cas de discrimination extrême** : il sépare les systèmes qui détectent un dépeg de ceux qui hésitent. Un système qui n'agit pas sur UST n'est pas prudent, il est défaillant |
| Limite | UST n'est pas un stablecoin fiat-backed — la généralisation depuis USDC n'est pas automatique, et la déclarer fait partie de l'évaluation |
| Piège | la série USTC sur les plateformes couvre l'**après-effondrement** : toute requête sans contrôle de la date renverra le prix d'un actif mort. Vérifier le symbole et la date **à chaque appel** |

## C.3 — USDT, 12 mai 2022 — **cas de contraste (faux positif potentiel)**

| Élément | Valeur |
|---|---|
| Fenêtre | 2022-05-11 → 2022-05-14 |
| Données | `MESURÉ` : `coingecko:tether` répond (0,9998 au 07/11/2022 00:00 UTC, contrôle de l'endpoint) ; Binance a une paire USDTUSDT-like à tester |
| **Vérité terrain L1** | **CNBC, 12 mai 2022** : USDT descend à **0,95 sur certains exchanges** vers 03 h 15, après la chute de terraUSD sous 30 cents la veille (<https://www.cnbc.com/2022/05/12/tether-usdt-stablecoin-drops-below-1-peg.html>) ; **Reuters**, même jour : plus bas à **95 cents** vers **07 h 24 UTC** selon les données CoinMarketCap, retour à 99 cents (<https://www.reuters.com/markets/us/crypto-collapse-intensifies-stablecoin-tether-slides-below-dollar-peg-2022-05-12/>) |
| **Vérité terrain L2** | à définir **par mesure sur l'agrégat** et non par la manchette : si l'agrégat ne descend qu'à ~0,99, la fenêtre est étiquetée `STRESS DE VENUE`, pas `CRISE D'ACTIF` |
| **Vérité terrain L3** | dépend entièrement de l'étiquette L2 → c'est précisément l'intérêt pédagogique du cas |
| Rôle | **cas anti-panique** : il teste la capacité du système à distinguer une **dislocation locale de venue** (rapportée par la presse) d'un **stress d'actif confirmé par plusieurs sources**. C'est aussi le cas qui valide la règle « confirmation multi-venues » (§B.4, A−V) |
| Limite | le plus bas intra-journalier de 0,95 est **rapporté par la presse citant CoinMarketCap**, et non reconstruit par nous à ce jour. Ne pas écrire « nous avons mesuré 0,95 » avant de l'avoir effectivement mesuré |

## C.4 — FTX / FTT, novembre 2022 — **cas de généralisation**

| Élément | Valeur |
|---|---|
| Fenêtre | 2022-11-06 → 2022-11-14 |
| Données | `MESURÉ` : `coingecko:ftx-token` répond (22,28 au 2022-11-07 00:00 UTC) ; Binance `FTTUSDT` **hourly disponible**, 22,08 le 08/11/2022 00:00 UTC |
| **Vérité terrain L1** | **11 novembre 2022** : dépôt de bilan (Chapter 11) de FTX et de sociétés affiliées. Sources de contexte : *Bankruptcy of FTX* (Wikipédia, article de référence, `SECONDAIRE`) ; *Rise and fall of crypto exchange FTX* (Reuters, 10/11/2022, <https://www.reuters.com/markets/currencies/rise-fall-crypto-exchange-ftx-2022-11-10/>) |
| **Vérité terrain L2** | `CRISE` |
| **Vérité terrain L3** | sortir d'un collatéral en déroute avant le 11/11 domine |
| Rôle | teste la **généralisation hors stablecoin** : ORVYREN est-il un système « USDC » ou un système « risque de contrepartie sur un actif de trésorerie » ? Un échec ici est une information utile, pas une honte |
| Limite | FTT n'est pas un actif de trésorerie standard, et la cause (fraude) n'est pas de même nature qu'un stress de marché. Le rôle du cas doit être explicite : **test de généralisation**, pas mesure de performance |

## C.5 — stETH / ETH, juin 2022 — **cas technique (ratio, pas prix)**

| Élément | Valeur |
|---|---|
| Fenêtre | 2022-06-10 → 2022-06-30 |
| Données | `MESURÉ` (14/10/2026) : DeFiLlama répond en **prix de contrat** — `ethereum:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84` (stETH) et `ethereum:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` (WETH) |
| Mesures effectuées | 2022-06-13 : stETH 1 391,913 / WETH 1 446,327 → **ratio 0,9624 (−3,76 %)** ; 2022-06-14 : **0,9586 (−4,14 %)** ; 2022-06-24 : **0,9533 (−4,67 %)** |
| Données indisponibles | `MESURÉ` : Binance ne propose **pas** `STETHUSDT` (`{"code":-1121,"msg":"Invalid symbol."}`) → la confirmation multi-venues devra venir d'ailleurs (Uniswap v3, Curve, ou une seconde source de contrat) |
| **Vérité terrain L1** | **12 juin 2022** : Celsius Network **gèle les retraits**. Contexte : rapports Nansen reliant la dépeg stETH à la contagion Terra/Celsius (`SECONDAIRE`, presse du 29/06/2022) — à confirmer en source primaire |
| **Vérité terrain L2** | `STRESS` : déviation ~4–5 % **mais** l'actif n'est pas un peg 1:1 au sens strict — c'est un **ratio d'échange** avec un délai de sortie |
| **Vérité terrain L3** | dépend de la définition du peg : c'est un **cas d'école** pour la sémantique (« qu'est-ce qu'une anomalie ? ») |
| Rôle | teste (i) la mesure d'un **ratio** plutôt qu'un prix absolu, (ii) la défaillance d'un **pont** (bridge/staking) et non d'une contrepartie bancaire |
| Limite | la déviation maximale réelle de stETH/ETH en juin 2022 est souvent citée comme plus élevée (~7 %) sur d'autres venues ; **ne pas reprendre ces chiffres sans les avoir mesurés**. Notre mesure donne 4,7 % sur le 24/06 par prix d'agrégateur |

## C.6 — DAI, mars 2020 (« Black Thursday ») — **cas asymétrique**

| Élément | Valeur |
|---|---|
| Fenêtre | 2020-03-11 → 2020-03-16 |
| Données | `MESURÉ` (14/10/2026) : `coingecko:dai` → **1,02899** (2020-03-12 00:00 UTC), **1,05851** (2020-03-13), **1,02213** (2020-03-14) |
| **Vérité terrain L1** | krach crypto du 12 mars 2020 et congestion d'Ethereum ; les enchères d'urgence du protocole Maker contre du collatéral ont été liquidées à des prix dégradés (`SECONDAIRE` — contexte de recherche, à documenter en source primaire avant citation définitive) |
| **Vérité terrain L2** | `CRISE` **avec déviation positive** : le prix passe **au-dessus** de 1 USD |
| **Vérité terrain L3** | intéressant : acheter DAI à 1,03 n'est pas une erreur si la déviation est transitoire → l'oracle *ex post* ne récompense pas mécaniquement l'action |
| Rôle | **test d'asymétrie** : la règle A0 (« prix < 0,99 ») est **aveugle** à ce cas par construction. C'est le meilleur cas pour démontrer qu'ORVYREN raisonne sur une **distribution de scénarios** et pas sur un seuil directionnel |
| Limite | la granularité disponible via DeFiLlama est de l'ordre de un point par timestampe demandée — à vérifier pour reconstruire une série horaire continue sur 2020 |

## C.7 — Défaillance de type oracle / manipulation, 2022 — **cas avancé (plus tard)**

| Élément | Valeur |
|---|---|
| Cas retenu | **Mango Markets, 11–12 octobre 2022** |
| Données | `MESURÉ` (14/10/2026) : `coingecko:mango-markets` renvoie MNGO à **0,03986** le 2022-10-11 et **0,01985** le 2022-10-12 (confiance déclarée 0,99) — soit environ **−50 %** en une journée |
| **Vérité terrain L1** | **9 janvier 2023** : la CFTC inculpe Avraham Eisenberg pour **manipulation de prix sur un oracle** de plateforme décentralisée — présenté comme le **premier cas de manipulation d'oracle** traité par la CFTC (<https://www.cftc.gov/PressRoom/PressReleases/8647-23>) ; contexte : <https://www.chainalysis.com/blog/oracle-manipulation-attacks-rising/> |
| **Vérité terrain L2** | `CRISE` (mais la crise est une **manipulation**, pas un stress de marché) |
| **Vérité terrain L3** | **à ne pas produire dans cette version** : la notion d'action optimale n'a pas de sens simple quand l'événement est une attaque |
| Rôle | incarner la **panne d'oracle** dans la taxonomie des modes de défaillance (l'événement que le système doit au minimum **signaler**, même sans pouvoir le qualifier) |
| Limite | les prix MNGO portent sur un token de gouvernance, pas sur un actif de trésorerie ; et les données de venue (Solana) sont moins standardisées que Binance/Bitstamp. **À traiter après le concours** |
| Statut | **candidat, non instrumenté.** Aucun protocole de collecte n'a été écrit pour ce cas au 14/10/2026 |

## C.8 — Fenêtres témoins (obligatoires)

Objectif : **12 fenêtres témoins** de 72 h, même source, même granularité que la fenêtre principale.
Méthode vérifiée : boucle de timestamps sur `coins.llama.fi/prices/historical/{ts}/coingecko:usd-coin` + `api/v3/klines?symbol=USDCUSDT` (l'endpoint `chart` de DeFiLlama ne renvoie pas d'historique — pitfall déjà documenté dans le rapport du 14/10).
Fenêtres candidates à figer : 2022-02, 2022-04, 2022-08, 2022-10, 2023-01, 2023-02 (acquis), 2023-06, 2023-09, 2024-01, 2024-06, 2024-11, 2025-03.
**Vérité terrain L2** : `CALME` ⟺ `max|P_t − 1| < 0,5 %` sur toute la fenêtre — seuil **gelé**, appliqué mécaniquement, sans exception et sans jugement. Toute fenêtre qui échoue au critère est **reclassée** `STRESS` (et devient un cas, pas un rebut).
**Utilité** : c'est là que se mesure le **taux de faux signaux**, la **couverture conformal** (M4) et la valeur du placebo B0.

## C.9 — Cas écartés, et pourquoi (l'honnêteté par la négative)

**USDT, octobre 2018 — ÉCARTÉ (données).**
Fait documenté : USDT s'échange aussi bas que **~0,90 $** sur certaines plateformes à la mi-octobre 2018 (`SECONDAIRE` : Bank Policy Institute, <https://bpi.com/stablecoin-risks-some-warning-bells/>) ; Bitfinex retire **630 M de Tether** de la circulation après la chute sous 1 $ (CoinDesk, 22/10/2018, `SECONDAIRE`).
**Pourquoi écarté** — vérifications du 14/10/2026 :
- `MESURÉ` : l'agrégat DeFiLlama/CoinGecko au **15/10/2018 00:00 UTC** donne **0,99632** — l'agrégat **n'enregistre pas** la dislocation de venue rapportée par la presse ;
- `MESURÉ` : Kraken `USDTUSD` ne remonte **qu'au 24/10/2024** (`1729728000`) — pas de données 2018 ;
- `MESURÉ` : Bitstamp `usdtusd` sur la période 2018 renvoie une liste **vide**.
→ Le cas n'est **pas** reconstituable avec des API publiques gratuites. Il est documenté en L1 mais inutilisable en L2/L3. **Le consigner comme tel vaut mieux que le gonfler avec des chiffres de presse.**

**Piège découvert au passage (à publier dans le dossier technique).**
`MESURÉ` : Binance `USDTUSD` au **18 novembre 2025** affiche un plus bas horaire de **0,89000** avec un volume d'environ **63 661** unités, sur une paire très récente. Au même moment, l'agrégat DeFiLlama donne USDT à **0,99893** (17/11), **0,99953** (18/11), **0,99917** (19/11), **0,99910** (20/11).
→ **Il ne s'agit pas d'un dépeg**, mais d'un **prix de carnet mince sur une venue récemment listée**. C'est le contre-exemple parfait à notre règle « 0,99 sur une venue ». Toute règle à seuil unique qui aurait traité ce chiffre comme un signal aurait produit un **faux positif**. Ce cas doit figurer comme **test de robustesse négatif** dans le banc d'attaques (§B.6, item 9 : « donnée contradictoire entre deux sources ») — gratuit, vérifiable, et très convaincant devant un jury.

---

# (d) Les pièges à éviter pour rester honnête devant un jury

Un jury de la WeBank et d'universitaires a **déjà lu** des dossiers qui surestiment. Les quinze pièges ci-dessous sont ceux qui font perdre le plus de crédit, classés par fréquence observée dans la littérature et les dossiers de concours.

**1. Contamination du backtest (le piège n° 1).**
Le cas USDC/SVB de mars 2023 est **dans les données d'entraînement** de tout modèle de 2026. Un agent qui « anticipe » le depeg de mars 2023 peut simplement se souvenir. Le terme consacré est *data-uncontaminated* (positionnement explicite du benchmark AI-Trader, §A.9).
**Parade** : (i) ne jamais présenter un backtest 2023 comme une **prédiction** ; (ii) évaluer aussi sur des épisodes **postérieurs à la date de coupe** du modèle quand c'est possible ; (iii) présenter l'exercice comme une **démonstration de méthode**, dont la valeur est le protocole, pas le score.

**2. Look-ahead déguisé.**
Le corpus complet est dans le cache local. Si la politique lit une ligne après `t_décision`, le backtest est faux — même sans intention de tricher.
**Parade** : un **test mécanique** qui rejoue la décision à chaque `t` avec le corpus **tronqué** à `t`, et compare le résultat au résultat obtenu sur le corpus complet. Si les deux diffèrent, il y a fuite. Ce test coûte une heure et ferme une porte de critique entière.

**3. Confondre nombre d'observations et nombre de preuves.**
1 375 observations ≠ 1 375 tirages indépendants. C'est **un** épisode de crise et **un** épisode témoin.
**Parade** : l'unité d'analyse est la fenêtre (§B.0 règle 3). Dire explicitement `N = 1 épisode` et `N_c = 12 fenêtres témoins`.

**4. Confondre pass^k et pass@k, ou vendre du déterminisme comme de la robustesse.**
ORVYREN est déterministe : `pass^k = 1` n'est pas un résultat, c'est une tautologie (§B.1, M5). Présenter cela comme « 100 % de fiabilité » est le genre de phrase qu'un jury relève en une seconde.
**Parade** : D1 (hash identique) / D2 (perturbations) / D3 (reformulations) — trois choses nommées séparément.

**5. Faire de la confiance verbalisée d'un LLM une probabilité.**
Les scores « je suis sûr à 0,92 » sont mal calibrés (§A.19). Les utiliser directement pour dimensionner une action revient à propager une erreur non mesurée jusque dans une transaction.
**Parade** : probabilités issues d'un **estimateur explicite** ; la sortie du LLM est une **hypothèse**, pas une probabilité.

**6. Présenter un gain comme une supériorité statistique.**
Avec 1 épisode, aucun test n'a la puissance de conclure (§B.5 : il faut ~93 fenêtres par groupe pour un effet modéré).
**Parade** : publier les intervalles, écrire « non conclusionnel » quand ça l'est, et l'assumer comme une force (la honnêteté quantitative est rare et se remarque).

**7. Le biais de sélection des cas.**
Choisir sept crises où un signal existait garantit que le système a des signaux à détecter. Ce n'est pas un benchmark, c'est une démonstration.
**Parade** : inclure obligatoirement des fenêtres **CALME** (§C.8) et des cas **où l'action était la mauvaise décision**. Le cas DAI de mars 2020 (déviation positive, §C.6) et le cas USDT 2025 à faible liquidité (§C.9) existent pour ça.

**8. Ignorer le coût, donc fabriquer du gain.**
Un gain de 20 bp qui coûte 30 bp en frais, slippage et gas est une perte. Si le coût n'est pas dans la fonction de perte, le regret est faux.
**Parade** : terme de coût explicite `c` dans M1, même s'il est nul sur testnet ; et un paragraphe sur ce que le coût serait en mainnet.

**9. Traiter un prix d'agrégateur et un prix d'exchange comme deux preuves indépendantes.**
Déjà identifié dans le corpus (`corpus/README.md`, règle 3) : un médian multi-venues n'est pas indépendant de ses venues constitutives.
**Parade** : la comparaison inter-venues est documentée comme **mesure de dispersion**, pas comme corroboration. Et le nombre de **sources indépendantes réelles** est déclaré (ici : 2 exchanges + 1 agrégateur + 1 émetteur ≈ 2 indépendantes, pas 4).

**10. La provenance n'est pas la vérité.**
Un claim traçable jusqu'à une source peut être faux, périmé ou manipulé. La provenance prouve la **traçabilité**, pas la validité (déjà écrit en V0.2 §12.2 — à répéter, car c'est contre-intuitif pour un jury).
**Parade** : associer systématiquement la provenance à une métrique de **contradiction détectée** (§B.4, A−G).

**11. Le piège du juge automatique.**
LLM-as-judge n'est pas une vérité terrain : c'est un estimateur bruité et biaisé (le v1.1 de Vals AI utilise un **mode de 3 évaluations** précisément pour réduire cette variance, §A.1). τ-bench fait l'inverse et compare un **état de base de données** à un état objectif — mesure déterministe.
**Parade** : préférer les vérifications déterministes (état final, hash, receipt, solde) ; réserver le juge LLM aux artefacts **non vérifiables mécaniquement** (qualité du dossier), et le documenter comme tel.

**12. Dépendre du réseau le jour de la démonstration.**
Les endpoints gratuits de DeFiLlama ferment le **13 novembre 2026** (`SOURCÉ` : <https://api-docs.defillama.com> — « The free yield endpoints /pools and /chart/{pool} shut down on November 13, 2026 ») ; nos quotas publics ne sont pas garantis. Le corpus est déjà archivé : c'est la bonne pratique, et elle doit être **dite** comme une limitation assumée (les données de démonstration sont un **rejeu**, pas un live).
**Parade** : mode replay affiché dans l'UI ; hash du corpus dans le dossier ; jamais de dépendance réseau en démo.

**13. Cacher les échecs.**
Un dossier sans hypothèse réfutée est un dossier où l'on n'a pas cherché. ORVYREN en a déjà deux (H1 et H3 `REFUTED`) : c'est un **actif**, à mettre en avant.
**Parade** : un tableau « ce qui a échoué, ce qu'on a changé, comment on l'a retesté » (le *remediation log* de §A.15).

**14. Confondre stress test de performance et stress test réglementaire.**
Le TSC demande aux régulateurs de conduire des stress tests **spécifiques à l'IA** (§A.11) ; la FCA demande aux firmes d'intégrer l'IA dans leurs **tests de scénarios de résilience opérationnelle** (§A.12). Aucun de ces textes n'est un cahier des charges pour un prototype de concours.
**Parade** : dire « notre banc d'attaque converge avec la vocabulaire émergent (inventaire des modes de défaillance, journal de remédiation, risque résiduel) » — et **jamais** « conforme à la réglementation ».

**15. Oublier l'axe corrélé / herding, que le régulateur a explicitement nommé.**
Le BoE étudie les conditions dans lesquelles « des agents IA négociant sur les marchés financiers pourraient présenter un comportement corrélé, ou “herding” » (§A.12, citation du 1er avril 2026), et le FSR de juillet 2026 met en avant les positions corrélées et le levier concentré (§A.14). Un dossier qui revendique un « agent autonome » sans un mot sur ce que plusieurs instances du même agent feraient simultanément rate la question la plus actuelle du régulateur.
**Parade** : un paragraphe honnête — *« notre prototype est mono-instance et à enjeu borné ; nous n'avons pas mesuré de dynamique de corrélation entre agents ; voici comment on la mesurerait »* — plus la mention que la politique de plafonnement intrinsèque **borne** le risque procyclique individuel, mais ne le supprime pas au niveau systémique. C'est exactement le registre attendu par la recommandation du TSC.

---

# Sources

Statut de consultation : `[ouvert]` = document lu directement pendant cette recherche (14/10/2026) ; `[snippet]` = résumé de moteur de recherche uniquement, non ouvert ; `[API]` = vérifié par appel réseau le 14/10/2026.

**Régulation et stress-testing**
1. `[ouvert]` Treasury Committee, *Artificial intelligence in financial services*, Fifteenth Report HC 684 — **20 janvier 2026** — <https://publications.parliament.uk/pa/cm5901/cmselect/cmtreasy/684/report.html>
2. `[ouvert]` Communiqué du Treasury Committee — **20 janvier 2026** — <https://committees.parliament.uk/committee/158/treasury-committee/news/211401/current-approach-to-ai-in-financial-services-risks-serious-harm-to-consumers-and-wider-system/>
3. `[ouvert]` Treasury Committee, *AI in financial services: Responses to the Committee's Fifteenth report*, Seventh Special Report HC 1791 — **16 avril 2026** — <https://publications.parliament.uk/pa/cm5901/cmselect/cmtreasy/1791/report.html>
4. `[ouvert]` Bank of England, *Response to TSC inquiry report on AI in financial services* (lettre de Sarah Breeden, Deputy Governor for Financial Stability) — **1er avril 2026** — <https://www.bankofengland.co.uk/-/media/boe/files/letter/2026/response-to-tsc-inquiry-report-on-ai-in-financial-services>
5. `[ouvert]` Bank of England, *Financial Stability Report — July 2026* — **7 juillet 2026** — <https://www.bankofengland.co.uk/financial-stability-report/2026/july-2026>
6. `[ouvert]` PRA, *SS1/23 — Model risk management principles for banks* — **mai 2023** (entrée en vigueur 17 mai 2024) — <https://www.bankofengland.co.uk/prudential-regulation/publication/2023/may/model-risk-management-principles-for-banks-ss>
7. `[ouvert]` FSB, *Sound Practices for Responsible Adoption of Artificial Intelligence (AI): Consultation report* — **10 juin 2026** (réponses jusqu'au 22 juillet 2026) — <https://fsb.org/2026/06/sound-practices-for-responsible-adoption-of-artificial-intelligence-ai-consultation-report> ; PDF <https://fsb.org/uploads/P100626.pdf>
8. `[snippet]` FSB, *Monitoring Adoption of AI and Related Vulnerabilities in the Financial Sector* — **10 octobre 2025** — <https://www.fsb.org/uploads/P101025.pdf>
9. `[snippet]` Bank of England, *Financial Stability in Focus*, **avril 2025** — <https://www.bankofengland.co.uk/financial-stability-in-focus/2025/april-2025>
10. `[ouvert]` Global Regulation Tomorrow, *House of Commons Treasury Committee report on AI in financial services* — **janvier 2026** — <https://www.regulationtomorrow.com/2026/01/house-of-commons-treasury-committee-report-on-ai-in-financial-services/> ; *TSC publishes Regulator responses* — **16 avril 2026** — <https://www.regulationtomorrow.com/2026/04/tsc-publishes-regulator-responses-to-its-report-on-ai-in-financial-services/>
11. `[ouvert]` Aveni, *AI agent stress testing for financial services: what good looks like* — **10 juin 2026** — <https://aveni.ai/blog/ai-agent-stress-testing-financial-services/> — **source praticien, non normative**

**Benchmarks**
12. `[ouvert]` Vals AI, *Finance Agent v1.1 Leaderboard and Methodology* — consulté le **14 octobre 2026** — <https://www.vals.ai/benchmarks/finance_agent>
13. `[ouvert]` Bigeard, Nashold, Krishnan, Wu, *Finance Agent Benchmark: Benchmarking LLMs on Real-world Financial Research Tasks*, arXiv:2508.00828 — **20 mai 2025** — <https://arxiv.org/abs/2508.00828>
14. `[ouvert]` Cheng et al., *FinanceComplexQA: Benchmarking Agentic Reasoning on Industrial-grade Financial Documents*, arXiv:2607.19238 — **21 juillet 2026** — <https://arxiv.org/abs/2607.19238> ; code <https://github.com/buaacxf/FinanceComplexQA>
15. `[ouvert]` Islam, Kannappan, Kiela, Qian, Scherrer, Vidgen, *FinanceBench: A New Benchmark for Financial Question Answering*, arXiv:2311.11944 — **20 novembre 2023** — <https://arxiv.org/abs/2311.11944>
16. `[snippet]` Patronus AI, annonce FinanceBench — **2023** — <https://www.patronus.ai/announcements/patronus-ai-launches-financebench-the-industrys-first-benchmark-for-llm-performance-on-financial-questions>
17. `[snippet]` *FinBen: A Holistic Financial Benchmark for Large Language Models*, arXiv:2402.12659 / NeurIPS 2024 — <https://arxiv.org/html/2402.12659v1> ; code <https://github.com/The-FinAI/FinBen>
18. `[ouvert]` Liu et al., *AgentBench: Evaluating LLMs as Agents*, arXiv:2308.03688 — **7 août 2023**, v3 **4 octobre 2025** (ICLR 2024) — <https://arxiv.org/abs/2308.03688>
19. `[ouvert]` Yao, Shinn, Razavi, Narasimhan, *τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains*, arXiv:2406.12045 — **17 juin 2024** — <https://arxiv.org/abs/2406.12045>
20. `[ouvert]` Barres, Dong, Ray, Si, Narasimhan, *τ²-Bench: Evaluating Conversational Agents in a Dual-Control Environment*, arXiv:2506.07982 — **9 juin 2025** — <https://arxiv.org/abs/2506.07982>
21. `[ouvert]` *Agent Market Arena (When Agents Trade: Live Multi-Market Trading Benchmark)*, arXiv:2510.11695 — **octobre 2025** — <https://www.alphaxiv.org/abs/2510.11695v1>
22. `[snippet]` *AI-Trader: Benchmarking Autonomous Agents in Real-Time Financial Markets*, arXiv:2512.10971 — **décembre 2025**
23. `[snippet]` InvestorBench, note d'éditeur — **2 juin 2026** — <https://beancount.io/it/bean-labs/research-logs/2026/06/02/investorbench-llm-agent-financial-decision-making>

**Métriques de décision, calibration, incertitude**
24. `[snippet]` Brier, G. W., *Verification of forecasts expressed in terms of probability*, Monthly Weather Review, **1950**
25. `[snippet]` Murphy, A. H., *A New Vector Partition of the Probability Score*, Journal of Applied Meteorology **12(4)**, 595–600 — **juin 1973** — DOI `10.1175/1520-0450(1973)012<0595:ANVPOT>2.0.CO;2`
26. `[snippet]` Naeini, Cooper, Hauskrecht, *Obtaining Well Calibrated Probabilities Using Bayesian Binning*, AAAI — **2015** — <https://ojs.aaai.org/index.php/AAAI/article/view/9602>
27. `[ouvert]` Guo, Pleiss, Sun, Weinberger, *On Calibration of Modern Neural Networks*, ICML — **2017** — arXiv:1706.04599 — <https://arxiv.org/html/1706.04599v2>
28. `[snippet]` *A Survey of Confidence Estimation and Calibration in Large Language Models*, arXiv:2311.08298 — <https://www.alphaxiv.org/abs/2311.08298>
29. `[snippet]` *Evaluating Confidence Estimation Under Language Variations*, arXiv:2601.08064 — **janvier 2026** — <https://arxiv.org/html/2601.08064v1>
30. `[snippet]` *Mind the Confidence Gap* (ECE jusqu'à ~0,30 sur tâches intensives en connaissance) — **février 2025** ; synthèse `SECONDAIRE` zylos.ai — **18 avril 2026** — <https://zylos.ai/research/2026-04-18-llm-calibration-uncertainty-production-agents/>
31. `[snippet]` Angelopoulos & Bates, *A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification*, arXiv:2107.07511 — <https://arxiv.org/abs/2107.07511>
32. `[snippet]` Sun & Yu, *Conformal Prediction for Time-series Forecasting with Change Points* (CPTC), NeurIPS — **2025** — <https://github.com/Rose-STL-Lab/CPTC>
33. `[snippet]` *Adaptive Conformal Anomaly Detection with Time Series Foundation Models*, arXiv:2604.20122, ICLR 2026 — <https://arxiv.org/html/2604.20122v1>
34. `[ouvert]` Kevin Sheppard, *arch — Time-series Bootstraps* (`CircularBlockBootstrap`, `StationaryBootstrap`, `MovingBlockBootstrap`) — consulté le **14 octobre 2026** — <https://arch.readthedocs.io/en/stable/bootstrap/timeseries-bootstraps.html>
35. `[snippet]` Bell, D. E., *Regret in Decision Making under Uncertainty*, Operations Research **30(5)**, 961–981 — **1982** — <https://pubsonline.informs.org/doi/10.1287/opre.30.5.961>
36. `[snippet]` Loomes & Sugden, *Testing for Regret and Disappointment in Choice under Uncertainty*, Economic Journal **97(388)**, 118–29 — **1987** — <https://ideas.repec.org/r/ecj/econjl/v97y1987i388ap118-29.html>

**Ablation et pré-enregistrement**
37. `[ouvert]` *The Model Proposes, the Code Disposes: A Pre-Registered Ablation of a Verifier-and-Acceptance Stage*, arXiv:2609.15887 — **2026** — <https://arxiv.org/html/2609.15887v1>
38. `[snippet]` *ABGEN: Evaluating Large Language Models in Ablation Study Design*, ACL 2025 — <https://aclanthology.org/2025.acl-long.611.pdf>

**Cas et données**
39. `[API]` DeFiLlama — `coins.llama.fi/prices/historical/{ts}/{coin}` et `stablecoins.llama.fi/stablecoincharts/{chain}?stablecoin={id}` — vérifiés le **14 octobre 2026** : répondent pour `coingecko:tether`, `coingecko:usd-coin`, `coingecko:staked-ether`, `coingecko:ftx-token`, `coingecko:terrausd`, `coingecko:dai`, `coingecko:mango-markets`, et en prix de contrat `ethereum:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84`, `ethereum:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` ; **ne répond pas** pour `coingecko:luna`
40. `[ouvert]` DeFiLlama — documentation API officielle (fermeture des endpoints gratuits `/pools` et `/chart/{pool}` annoncée au **13 novembre 2026**) — <https://api-docs.defillama.com>
41. `[API]` Binance — `api.binance.com/api/v3/klines` — vérifié le **14 octobre 2026** : `USTUSDT` disponible depuis le 2022-05-09, `FTTUSDT` disponible, `USDCUSDT` disponible, `STETHUSDT` **invalide** (`-1121`), `USDTUSD` disponible seulement depuis **novembre 2025**
42. `[API]` Kraken — `api.kraken.com/0/public/OHLC?pair=USDTUSD` — plus ancienne bougie disponible **2024-10-24** (vérifié le 14/10/2026) ; `[API]` Bitstamp `api/v2/ohlc/usdtusd` — **vide** sur la période 2018
43. `[ouvert]` Circle, communiqué *3.3 billion of USDC reserve risk removed; dollar de-peg closes* — <https://www.circle.com/pressroom/3-3-billion-of-usdc-reserve-risk-removed-dollar-de-peg-closes>
44. `[snippet]` CNBC, *Tether (USDT) stablecoin drops below $1 peg* — **12 mai 2022** — <https://www.cnbc.com/2022/05/12/tether-usdt-stablecoin-drops-below-1-peg.html> ; Reuters, *Crypto collapse intensifies as stablecoin Tether slides below dollar peg* — **12 mai 2022** — <https://www.reuters.com/markets/us/crypto-collapse-intensifies-stablecoin-tether-slides-below-dollar-peg-2022-05-12/>
45. `[snippet]` *Anatomy of a Run: The Terra Luna Crash*, LSE Research Online — <https://researchonline.lse.ac.uk/id/eprint/140488/> ; *Anatomy of a Stablecoin's failure: the Terra-Luna case*, arXiv:2207.13914 — <https://arxiv.org/html/2207.13914v3>
46. `[snippet]` CFTC, *CFTC Charges Avraham Eisenberg with Manipulative and Deceptive Scheme…* (premier cas de manipulation d'oracle sur DEX) — **9 janvier 2023** — <https://www.cftc.gov/PressRoom/PressReleases/8647-23> ; Chainalysis, *Oracle Manipulation Attacks are Rising* — <https://www.chainalysis.com/blog/oracle-manipulation-attacks-rising/>
47. `[snippet]` Reuters, *Rise and fall of crypto exchange FTX* — **10 novembre 2022** — <https://www.reuters.com/markets/currencies/rise-fall-crypto-exchange-ftx-2022-11-10/> ; Bank Policy Institute, *Stablecoin Risks: Some Warning Bells* (USDT ~0,90 $ en octobre 2018) — <https://bpi.com/stablecoin-risks-some-warning-bells/> ; CoinDesk, *Bitfinex Took 630 Million Tether Out of Circulation After Drop Below $1* — **22 octobre 2018** — <https://www.coindesk.com/markets/2018/10/22/bitfinex-took-630-million-tether-out-of-circulation-after-drop-below-1>

**Documents internes**
48. `MESURÉ` `D:\orvyren_core\corpus\README.md` — corpus USDC, 1 375 observations, 14/10/2026
49. `MESURÉ` `D:\orvyren_core\evidence\baseline_report.json` — baseline A0, 2 signaux / 0 faux signal sur témoin
50. `MESURÉ` `D:\orvyren_core\evidence\pipeline_summary.json` — verdicts H1/H2/H3, décision, artefacts hashés
51. `MESURÉ` `D:\orvyren_core\FREEZE_V1.md` — décisions D1–D12 (fenêtres, hypothèses, A0, politique, métriques)
52. `MESURÉ` `pytest -q` — **114 passed, 2 skipped** (116 tests), 14/10/2026

---

## Non trouvé (à ne pas combler par des inventions)

1. **Cadre réglementaire de stress test IA opposable** : aucun texte publié (FCA, PRA, BoE, ESMA, BCE) définissant le contenu obligatoire d'un dossier de stress test IA ou d'un *evidence pack* au 14/10/2026. La recommandation du TSC est une injonction adressée aux régulateurs ; la FCA annonce son rapport d'évaluation du AI Live Testing pour fin 2026/début 2027.
2. **Série historique LUNA via DeFiLlama** : `coingecko:luna` ne renvoie aucune donnée (vérifié 14/10/2026). Une autre source est nécessaire si le cas Terra doit être complété côté LUNA.
3. **Données de venue pour USDT octobre 2018** : aucune API publique gratuite testée ne couvre l'épisode (Kraken et Bitstamp ne remontent pas à 2018 sur USDT).
4. **Définition standardisée d'un « oracle failure »** à des fins de benchmark : aucune taxonomie unique acceptée n'a été trouvée ; la taxonomie des modes de défaillance proposée en §B doit donc être présentée comme **la nôtre**, pas comme une norme.
5. **Chiffres repris de la presse et non mesurés** : plus bas de stETH/ETH en juin 2022 (~7 %), plus bas de USDT le 12/05/2022 (0,95 $), plus bas de USDT en octobre 2018 (~0,85–0,90 $). Ces valeurs sont **rapportées**, non vérifiées par nos soins ; elles ne doivent pas apparaître dans un document technique comme des mesures ORVYREN.
