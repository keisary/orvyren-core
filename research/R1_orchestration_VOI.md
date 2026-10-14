# R1 — Orchestration d'agent Bayes-consistante et Value of Information (VOI)

**Projet :** ORVYREN-Core — moteur de décision financière vérifiable (concours FinTech Shenzhen 2026, thème F « Agent Wallet »)
**Objet :** combler les manques (1) agent autonome, (2) registre de branches, (3) quantification de la valeur d'une recherche, (4) calibration.
**Règle de rédaction :** chaque affirmation externe porte une URL et une date de publication. Aucune source inventée. Les sources que je n'ai pas pu ouvrir intégralement sont signalées explicitement (§0).
**Date de compilation :** 14 octobre 2026.

---

## §0 — Statut de vérification des sources (à lire avant tout)

| Source | Ce que j'ai ouvert | Statut |
|---|---|---|
| arXiv:2605.00742 | Page `abs` + **texte intégral HTML v1** (113 937 caractères, §1 à Appendice C lus) | **Vérifié intégralement** |
| hal-05480691 | **Métadonnées complètes via l'API HAL officielle** (`api.archives-ouvertes.fr`) : titre, 29 auteurs, abstract, `producedDate`, licence, URL du fichier | **Métadonnées vérifiées ; PDF non ouvert** — le fichier `bayes_in_ai_paper.pdf` est protégé par un challenge anti-bot (« Making sure you're not a bot! »), et le navigateur du poste n'a pas pu démarrer (Chromium absent). Les règles concrètes citées proviennent donc du texte arXiv du même travail (§3 ci-dessous). |
| ACL 2026.acl-long.1987 | **PDF intégral téléchargé et lu** (430 lignes, formules, Algorithmes, annexes A/B/C) | **Vérifié intégralement** |
| ACM 10.1145/3696410.3714773 | Page ACM : abstract complet, historique de publication, références | **Abstract + métadonnées vérifiés ; PDF complet non ouvert** (accès « Premium » requis pour le corps de l'article) |
| Autres | Voir colonne « statut » dans le tableau §1 | Vérifié selon mention |

**Conséquence honnête :** les règles extraites de hal-05480691 et le corps de l'article ACM reposent respectivement sur le texte arXiv du même travail et sur l'abstract de l'éditeur. Je ne présente nulle part comme « lu » ce qui ne l'a pas été.

---

## §1 — État de l'art en 15 points (URL + date)

### 1. Le papier de position : l'orchestration d'agents doit être Bayes-consistante

**Papamarkou, T., Alquier, P., Bauer, M., Buntine, W., Davison, A., Dziugaite, G. K., … Zaytsev, A. (2026).** *Position: agentic AI orchestration should be Bayes-consistent.*
`https://arxiv.org/abs/2605.00742` — **v1 : 1er mai 2026** ; v2 : 6 mai 2026 (dates relevées via l'API arXiv `export.arxiv.org/api/query?id_list=2605.00742`).
Texte intégral : `https://arxiv.org/html/2605.00742v1`

**Thèse exacte (citation du §Position) :** « this position paper argues that LLMs need not be explicitly Bayesian, while AI systems that orchestrate LLM agents should be making decisions at least consistent with Bayesian reasoning. » Le LLM reste un **prédicteur boîte noire** ; la structure bayésienne vit dans le **control layer** (belief state sur des variables latentes de niveau tâche + politique fondée sur l'utilité espérée ou la valeur de l'information).

**Règles concrètes extractibles pour un agent financier :**

- **Règle d'arrêt / de nouvel appel (le cœur de notre besoin) :** « **An additional agent call is justified only when its expected value of information exceeds its cost.** » (§4.1). Reformulé au §4.2 : « further agent queries are warranted only when their expected value of information exceeds their cost. »
- **Stopping par masse postérieure :** « A possible rule is to terminate once the posterior places sufficient mass on one hypothesis, for example, when `max_h r_t(h)` exceeds a user-specified confidence threshold. » (§4.2)
- **Action de Bayes à l'arrêt :** si l'on s'arrête en `t`, l'action optimale est `a*_t = argmax_a Σ_{h∈H} u(a,h) r_t(h)` (§4.2) — c'est **exactement** le formalisme `ALLOW / DENY / REQUIRE_APPROVAL` d'ORVYREN, avec `u(a,h)` la matrice coût/bénéfice par hypothèse.
- **Mise à jour de croyance tempérée par la fiabilité de la source :** `r_t(h) ∝ r_{t-1}(h) · p_{i_t}(z_t | h)^{α_{i_t}}` (équation 2 ; équation 1 pour une variable de résultat binaire). `α_i` est une pondération de fiabilité **distincte** du likelihood, qui « downweights sources that are noisy, miscalibrated, or statistically dependent ». Les `α_i` peuvent être mis à jour en ligne par un schéma à poids exponentiels `w_i ∝ exp(−β L_i)` à partir de la log-loss cumulée `L_i` de chaque source.
- **7 propriétés attendues d'un contrôleur bayésien** (§2) : (1) utilités et coûts **modélisés**, pas constants ; (2) gain de qualité de décision à faible surcoût (latence/mémoire faibles vs inférence) ; (3) **distillation** de l'historique en un belief state quasi-suffisant (mémoire bornée) ; (4) intégration humains / multi-agents comme observations probabilistes ; (5) **schémas typés** compatibles écosystèmes agentiques ; (6) multimodalité ; (7) **contrôles utilisateur simples** (seuil de confiance, échelle de coût) sans exposer la mécanique bayésienne.
- **7 design patterns réutilisables** (§4.3) : tâche-level belief factoring ; messages comme observations ; mises à jour pondérées par la fiabilité ; **dependence-aware evidence pooling** ; contrôle par utilité **ou** par valeur de l'information (routing, arrêt, abstention, escalade, budget) ; postérieures cross-task pour le routing ; **distillation du belief state**.
- **Règle de robustesse :** « The practical mitigation is to make updates conservative via recalibration from measurable outcomes, likelihood tempering, dependence-aware evidence pooling, and **abstention or escalation when posterior confidence is fragile**. » (§2)

**Avertissements explicites de la source (à reprendre tels quels) :** les exemples sont « **not intended as an exhaustive taxonomy or as fully instantiated end-to-end algorithms**, but as suggestive starting points » (§4). Les défis ouverts listés au §5 incluent « dependence-aware evidence pooling under shared model or retrieval pipelines, robust uncertainty quantification for high-dimensional agent messages under shift, and **scalable approximations to multi-step value-of-information in combinatorial orchestration** ».

### 2. La même position, déposée plus tôt sur HAL

**Papamarkou et al. (2026).** *Position: Agentic AI systems should be making Bayes-consistent decisions.* **ESSEC Working Papers**, `https://hal.science/hal-05480691` — **écrit / déposé le 27 janvier 2026**, **diffusé le 4 mars 2026**, dernière modification d'indexation 15 juillet 2026. Licence CC BY-NC-ND 4.0. Fichier : `https://hal.science/hal-05480691/file/bayes_in_ai_paper.pdf`.
*(Métadonnées obtenues via l'API HAL : **29 auteurs** sur le dépôt HAL contre **30** sur l'arXiv, Jes Frellsen figurant en plus côté arXiv ; abstract **quasiment** identique — une différence de formulation relevée : « requires Bayesian principles at **the orchestration level of** the agentic system » (arXiv) contre « at the level of the agentic system » (HAL). **PDF non ouvert** — voir §0.)*

**Intérêt pour le dossier de concours :** le dépôt HAL (**27 janvier 2026**, diffusé **4 mars 2026**) est **antérieur** à l'arXiv v1 (1er mai 2026). La règle « un appel n'est justifié que si son EVOI > son coût » est donc publiable comme **antérieure au printemps 2026**, avec deux identifiants vérifiables. La version OpenReview existe également (`https://openreview.net/pdf?id=ydcX7UoHA3`) — **non lue intégralement** (consultée uniquement via un extrait de moteur de recherche, ne pas s'en servir comme source unique).

### 3. Value of Information pour la décision de communiquer / demander / s'arrêter

**Dong, Y. R., Hu, T., Hui, Z., Zhang, C., Vulić, I., Bobu, A., & Collier, N. (2026).** *Value of Information: A Framework for Human–Agent Communication.* **ACL 2026, Long Papers**, pp. 42879–42896, San Diego, juillet 2026. `https://aclanthology.org/2026.acl-long.1987/` — PDF : `https://aclanthology.org/2026.acl-long.1987.pdf` — DOI : `10.18653/v1/2026.acl-long.1987`.

**Formalisme complet, directement transposable (équations 1–5) :**

| Étape | Formule | Rôle dans ORVYREN |
|---|---|---|
| Utilité espérée d'une décision | `EU(a|b) = E_{θ~b}[U(θ,a)] = Σ_{θ∈Θ} b(θ) U(θ,a)` (1) | `a ∈ {ALLOW, DENY, REQUIRE_APPROVAL}`, `θ ∈ {H1, H2, H3}` |
| Valeur d'agir maintenant | `V(b) = max_{a∈A} EU(a|b)` (2) | baseline A0 : que vaut la décision avec les croyances actuelles |
| Valeur après une question | `V_post(b,q) = Σ_{y∈Y} p(y|q,b) · V(b_y)` (3) | espérance sur les réponses possibles d'une source |
| **Valeur de l'information** | `VoI(q) = V_post(b,q) − V(b)` (4) | gain d'utilité attendu de la recherche |
| **Règle de décision** | `NetVoI(q) = VoI(q) − c` (5) ; on pose la question `q*` de plus forte valeur positive ; **si `max_q NetVoI(q) ≤ 0`, on s'arrête et on commet l'action** | critère d'arrêt explicite, sans seuil à régler |

**Algorithme 1 du papier (extrait fidèle) :** `Require: Instruction S; action set A; utility U(θ,a); question generator GenQ; belief updater Update; cost c(·); clarification budget K_max` → à chaque tour : générer les questions candidates, calculer `V₀ = V(b)`, échantillonner les réponses plausibles, calculer `VoI(q)`, sélectionner `q* = argmax VoI(q)`, **`if VoI(q*) ≤ 0 then break`** (« clarification not worthwhile »), sinon poser la question, observer, mettre à jour. Sortie : `a* ∈ argmax E[U(θ,a)]`.

**Résultats empiriques (4 domaines : 20 Questions, diagnostic médical, réservation de vol, e-commerce) :**
- La méthode VOI « matches or exceeds the best manually-tuned baselines in **18 of 20 conditions**, achieving utility gains of **up to 1.36 points** in high-cost settings » (abstract + §1).
- Exemple chiffré : Mixed 20Q, `c = 0.01`, VOI = **14.14** contre la meilleure baseline à seuil réglée (`τ = 0.90`) = **11.49** (§6.1).
- Table 1 (Gemini-2.5-Flash) : à `c = 0.05`, VOI 5.01 contre 3.65 (meilleure baseline) → +1.36 ; à `c = 0.20`, VOI −0.96 contre 0.00 pour « No Question » → **le VOI décide correctement de ne pas chercher quand c'est trop cher**.
- **Échec documenté du « ressenti » du modèle** : la baseline « Adaptive Prompting » (on demande au LLM s'il se sent assez confiant) « is inconsistent and consistently lower than more structured methods. This is because the decision to communicate is based on the model's internal "feeling" of confidence, **which is often poorly calibrated** » (§6.1).
- **Échec documenté du seuil fixe** : « the optimal τ is highly sensitive and must be manually selected for each task and cost combination, making it impractical for real-world deployment » (§6.1). Les stratégies à nombre fixe de tours sont « fundamentally suboptimal » (courbe en U inversé).
- **Coût de calcul explicite :** la politique VOI coûte `O(T·K·|Q|)` (T tours, K réponses possibles, |Q| questions candidates) contre `O(T)` pour les baselines — « so VoI incurs roughly **10 times** computational cost than these baselines » (Annexe B, Table 2), avec `K=2`, `|Q|=5` dans leurs expériences.
- **Analyse de calibration (Annexe, Figure 3) :** les modèles sont « reasonably calibrated in Animal Guessing game but **less calibrated for Medical Diagnosis** ».
- **Limites déclarées :** espace de questions restreint à des questions fermées (oui/non, QCM) pour rendre `Y` fini ; le belief `b(θ)` est **estimé par le LLM**, pas par un likelihood analytique ; modèle de coût **linéaire** `c(H) = T·c` (limite reconnue : « Accurately modeling the nuances of human cognitive load is a major, open research challenge ») ; l'article porte sur *quand* communiquer, pas *quoi* générer.

### 4. EVOI + bandits conversationnels : rendre le calcul tractable avec garanties

**Li, Z., Liu, M., Dai, X., & Lui, J. C. S. (2025).** *Towards Efficient Conversational Recommendations: Expected Value of Information Meets Bandit Learning.* **WWW '25 (ACM Web Conference 2025)**, Sydney — **publié le 22 avril 2025**. `https://dl.acm.org/doi/10.1145/3696410.3714773`
*(Abstract + historique de publication vérifiés ; corps de l'article non accessible sans abonnement.)*

**Ce que la source établit :** « The *expected value of information (EVOI)*, which computes the expected reward improvement, provides a principled criterion for query selection. **However, it is computationally expensive and lacks theoretical performance guarantees.** » La contribution : `gradient-based EVOI`, qui « replaces the complex Bayesian updates in conventional EVOI with efficient stochastic gradient descent », plus des `smoothed key term contexts` ; deux algorithmes (**ConTS-EVOI** pour Thompson Sampling, **ConUCB-EVOI** pour UCB) avec des bornes de regret plus serrées, « offering a **√d improvement** in their dependence on the time horizon T ». Validation sur données synthétiques et réelles.

**Lecture pour ORVYREN :** le VOI exact est coûteux et sans garantie de borne ; l'approximation par gradient en donne. C'est un argument **pour** une approximation one-step documentée plutôt que pour un calcul exact.

### 5. Le cas « coûts asymétriques » : orchestrer plusieurs LLM plutôt qu'un seul

**Amin, D. (2026).** *Bayesian Orchestration of Multi-LLM Agents for Cost-Aware Sequential Decision-Making.* `https://arxiv.org/abs/2601.01522` — **soumis le 4 janvier 2026**.

**Résultat négatif démontré :** « The dominant design queries a single LLM for a posterior over states, thresholds "confidence," and acts; **we prove this is inadequate for sequential decisions with costs**. » Le cadre proposé traite les LLM comme des **modèles de vraisemblance approximatifs** (et non des classifieurs) : élicitation par `contrastive prompting`, agrégation multi-modèles par statistiques robustes, mise à jour bayésienne sous priors explicites, sélection d'action par coût espéré, **collecte d'information par value of information**, et mitigation de biais par ensemble.

**Chiffres (screening de CV, 1000 CV, 5 LLM : GPT-4o, Claude 4.5 Sonnet, Gemini Pro, Grok, DeepSeek), coûts : 40 000 USD par embauche manquée, 2 500 USD par entretien, 150 USD par entretien téléphonique :**
- réduction du coût total de **294 000 USD (34 %)** contre la meilleure baseline mono-LLM ;
- parité démographique améliorée de 45 % (écart maximal entre groupes : de 22 à 5 points de pourcentage) ;
- ablations : **51 %** de l'économie attribuée à l'agrégation multi-LLM, **43 %** à la mise à jour séquentielle, **20 %** à la collecte d'information déclenchée par le **désaccord** entre modèles (*disagreement-triggered information gathering*).

**Pertinence directe :** ORVYREN est précisément un problème à **coûts asymétriques** (un DENY à tort et un ALLOW à tort n'ont pas le même coût). L'article fournit la structure `likelihood → posterior → expected cost → VOI` et un déclencheur opérationnel : **ne rechercher que lorsque les sources divergent**.

### 6. Les formules canoniques EVPI / EVPPI / EVSI

**Heath, A., Kunst, N., Jackson, C., et al. (2020).** *Calculating the Expected Value of Sample Information in Practice: Considerations from Three Case Studies.* **Medical Decision Making**, 40(3):314–326 — **publié en ligne le 16 avril 2020**. `https://pmc.ncbi.nlm.nih.gov/articles/PMC7968749/` — DOI `10.1177/0272989X20912402` — PMID 32297840 (dates vérifiées via l'API PubMed E-utilities).
*(Source de référence pour les formules ; volontairement plus ancienne que 2025, car c'est la formulation standard.)*

- **EVPPI** (valeur de l'information parfaitement *parfaite* sur un sous-ensemble de paramètres `φ`) :
  `EVPPI = E_φ[ max_t E_{θ|φ}[NB_t(θ)] ] − max_t E_θ[NB_t(θ)]` — leur équation (1).
- **EVSI** (valeur de l'information *imparfaite*, i.e. d'un échantillon / d'une collecte réelle) :
  `EVSI = E_X[ max_t E_{θ|X}[NB_t(θ)] ] − max_t E_θ[NB_t(θ)]` — leur équation (2).
  **Propriété clé :** « EVSI is bounded above by the EVPPI for φ » → **l'EVPI est le plafond de ce qu'on doit payer** pour une recherche ; c'est le garde-fou budgétaire naturel d'ORVYREN.
- **Estimateur par Monte Carlo imbriqué** (leur équation 3) : `EVSI ≈ (1/S) Σ_s max_t μ_t(X_s) − max_t (1/S) Σ_s μ_t(X_s)`.
- **Coût de calcul** : « In each example, the approximation methods took **minutes or hours** to achieve reasonably accurate EVSI estimates, whereas the traditional Monte Carlo method took **weeks**. »
- Ici `NB_t(θ)` = net benefit de la décision `t` ; **transposition directe** pour ORVYREN : remplacer `NB_t(θ)` par `−coût(a, h)` et les actions `t` par `ALLOW / DENY / REQUIRE_APPROVAL`.

### 7. Optimal experimental design : choisir LA prochaine observation

**Wu, D., Liang, L., & Yang, H. (2026).** *Beyond Expected Information Gain: Stable Bayesian Optimal Experimental Design with Integral Probability Metrics and Plug-and-Play Extensions.* `https://arxiv.org/abs/2604.21849` — **soumis le 23 avril 2026**.

**Ce que cela donne pour le choix de la source suivante :** le standard BOED « selects designs by maximizing **expected information gain (EIG)**, commonly defined through the **Kullback-Leibler (KL) divergence** ». Mais : « classical evaluation of EIG often involves challenging **nested expectations**, and even advanced variational methods leave the underlying log-density-ratio objective unchanged. As a result, **support mismatch, tail underestimation, and rare-event sensitivity** remain intrinsic concerns for KL-based BOED. »

**Remède proposé :** remplacer les divergences de densité par des **integral probability metrics (IPM)** — Wasserstein, Maximum Mean Discrepancy (MMD), Energy Distance — avec des garanties théoriques montrant « stronger geometry-aware stability under **surrogate-model error and prior misspecification** » et des « highly concentrated credible sets ».

**Lecture pour ORVYREN :** pour choisir entre agrégateur / exchange / offre / on-chain / documents, le critère « réduction d'entropie / divergence KL » est le standard, **mais** il est fragile précisément dans le régime qui nous intéresse (événements rares = décrochage de stablecoin ; priors mal spécifiés). L'alternative IPM est plus stable — **mais** (voir §3(c)) sa validation empirique reste récente et non financière.

### 8. Garde-fous numériques #1 : le LLM comme « canonicalizer », le solveur comme décideur

**Bruno, A. (2026).** *Moxia: A Trust-First Neuro-Symbolic Execution Architecture for Self-Explaining Mathematical Reasoning* (« formerly AXIOM »). `https://arxiv.org/abs/2606.00671` — **v1 : 30 mai 2026 ; v3 : 12 août 2026**.

**Le principe exact :** « Its language model is **strictly a canonicalizer**: it rewrites informal problem text into a narrow schema consumed by a **deterministic Computer-Algebra-System (CAS) pipeline, which derives and verifies the answer or abstains as a first-class output**. »

**Le problème qu'il résout (formulation décisive pour notre dossier) :** « Frontier large language models achieve impressive accuracy on mathematical reasoning benchmarks, but they expose **no verification pathway: at the API level, a confident-wrong answer is indistinguishable from a confident-right one**. […] This is not a defect of any particular model — it is a structural property of the **prompt-in-text-out interface** itself. » (formulation présente dans le HTML v1, `https://arxiv.org/html/2606.00671v1`)

**Mesures rapportées (v3) :** 4 783 routes déployées, **71 % répondent sans invoquer le LLM** ; sur MATH-500 (jamais vu à la conception) **89,2 % (446/500) avec zéro réponse « confident-wrong »** ; sur le split MATH complet 90,2 % (4 510/5 000) avec **une** réponse confident-wrong ; le chemin « rule-only » traite le benchmark arithmétique lm-eval (20 000 enregistrements) à **100 %, ~1 ms/enregistrement**, « Output bit-equivalence across runs is guaranteed by construction — no sampling, no stochasticity » ; 479 fichiers de tâches exportent un théorème Lean 4, **445 acceptés par le kernel Lean avec Mathlib** — avec l'avertissement honnête de l'auteur : « **that gate covers a fixture corpus, so live output is generated, not machine-checked** ».

**Transposition ORVYREN :** le prix USDC, le ratio de réserves, le volume on-chain **doivent** être produits par un composant déterministe à partir d'une source horodatée ; le LLM ne fait que *router et canonicaliser* vers le schéma ; et **l'abstention est une sortie de première classe** — ce qui justifie formellement notre `REQUIRE_APPROVAL`.

### 9. Garde-fous #2 : vérifier la conformité de politique par solveur SMT

**Winston, C., Winston, C., & Just, R. (2026).** *Solver-Aided Verification of Policy Compliance in Tool-Augmented LLM Agents.* `https://arxiv.org/abs/2603.20449` — **soumis le 20 mars 2026**.

« We introduce an **SMT solver-aided framework** to enforce tool-use policy compliance in TaLLM agents. […] we use an LLM-assisted, human-guided approach to translate natural-language-specified tool-use policies into formal logic (**SMT-LIB-2.0**) constraints over agent-observable state and tool arguments. **At runtime, planned tool calls are intercepted and checked against the constraints using the Z3 solver as a pre-condition to the tool call. Tool invocations that violate the policy are blocked.** » Évaluation sur **TauBench** : « solver-aided policy checking **reduces policy violations while maintaining overall task accuracy** ». Les auteurs notent qu'aucun travail existant n'intégrait une telle vérification formelle **directement dans la boucle de planification du tool-use**.

**Transposition directe :** notre instruction on-chain non signée est déjà interceptée avant exécution — formaliser la politique `ALLOW/DENY/REQUIRE_APPROVAL` en contraintes vérifiées **avant** l'appel d'outil est l'état de l'art publié.

### 10. Garde-fous #3 : contrats typés par primitive et trace vérifiée par étape

**Bhat, V., Vaghasiya, J., & Gonzalez, E. A. (2026).** *Forethought: Verifiable Reasoning from Neurosymbolic Primitive Programming.* `https://arxiv.org/abs/2607.04096` — **soumis le 5 juillet 2026**.

« We decompose reasoning into a library of **primitives** — narrow reasoning operations implemented either symbolically or as fine-tuned SLMs — each carrying a **typed *output contract* that specifies the properties its output must satisfy**. […] an engine that **verifies each primitive's output against its contract and produces a per-step verified trace**. » Le programme de raisonnement est « an analyzable data structure rather than an opaque chain », donc **inspectable et modifiable avant déploiement** (« auditable at design time »). Gain mesuré : ~30 % relatif sur cinq benchmarks, et un modèle non-raisonneur augmenté rivalise avec un modèle de raisonnement dédié « while requiring roughly three orders of magnitude less post-training investment ».

**Transposition :** chaque outil d'ORVYREN (collecteur, extracteur, évaluateur de divergence) doit déclarer un **contrat de sortie typé** vérifié automatiquement, et la trace vérifiée par étape doit atterrir dans le dossier d'audit.

### 11. Garde-fous #4 : le « determinism layer » — retour d'expérience industriel

**Stack Overflow (2026).** *Part 1: Make your AI agents boring: the determinism layer* — **7 octobre 2026**. `https://stackoverflow.blog/2026/10/07/part-1-make-your-ai-agents-boring-the-determinism-layer/`
*(Statut : **article de blog d'ingénierie, non évalué par les pairs**. À citer comme pratique industrielle documentée, jamais comme preuve scientifique — voir §4.)*

Points directement applicables à ORVYREN :

- « **An agent is a pure function** from context to a *proposed* decision […]. It has no authority to change the world. A separate, dumb, heavily-tested component — the **substrate** — applies proposals, and only after the required approval. » Le contrat type `Agent.propose(ctx) -> Proposal` avec `routing: Literal["auto","hitl_recommended","hitl_required","reject"]` **est presque mot pour mot notre `ALLOW / REQUIRE_APPROVAL / DENY`**.
- Le `Proposal` porte `reasoning: list[str]` et `evidence: list[dict]`, est `frozen=True`, et **le substrat est le seul mutateur** → « a jailbroken or buggy agent produces a bad *proposal*, not a bad *action* ».
- **Graphe fixe plutôt que boucle ReAct libre** : `entry → load context → reason (LLM) → output guardrail → verify → judge (sampled) → compose confidence → route → prepare proposal → record → exit`. Le tableau comparatif : boucle ReAct libre = « Latency / cost: **unbounded** » ; graphe fixe = « **bounded, predictable** ».
- **Sortie structurée obligatoire** : trois méthodes (JSON Schema / `response_format`, tool-calling typé, grammar-constrained decoding), puis **valider et retenter avec un nombre de tentatives borné, et échouer en fermant** (`raise NonConformingOutput()` — « fail closed — never hand downstream a guess »).
- « an enum is itself a guardrail » — et l'avertissement : « **structure constrains *form*, not *correctness*. A perfectly valid `{"decision":"approve","confidence":0.99}` can be completely wrong.** »
- Piège listé noir sur blanc : « **"Confidence" lifted from the model. Miscalibrated; compose it from independent signals instead.** »
- Boucle bornée (« quatre rails ») : cap dur `MAX_STEPS`, allow-list d'outils par capacité, une ligne de trace par itération, et **la sortie finale reste une PROPOSITION** ; si le cap est atteint → `escalate("hit step cap", trace)` routé `hitl_required`.
- Registre immuable : « If you can `UPDATE` the ledger it's not an audit trail. »

### 12. Sur-confiance agentique mesurée

**Kaddour, J., Patel, S., Dovonon, G., Richter, L., Minervini, P., & Kusner, M. J. (2026).** *Agentic Uncertainty Reveals Agentic Overconfidence.* `https://arxiv.org/abs/2602.06948` — **soumis le 6 février 2026**.

- Résultat principal : « **All results exhibit agentic overconfidence: some agents that succeed only 22% of the time predict 77% success.** »
- Contre-intuitif : « **pre-execution assessment with strictly less information tends to yield better discrimination than standard post-execution review**, though differences are not always significant. »
- Le meilleur étalonnage obtenu par : « **Adversarial prompting reframing assessment as bug-finding** achieves the best calibration. »

**C'est la source la plus directement utile pour le volet (4) « calibration » du projet** : notre protocole de prévisions gelées doit être comparé à des prévisions post-exécution, et l'élicitation doit être **reframée en recherche de bugs** plutôt qu'en auto-évaluation de réussite.

### 13. Pourquoi les probabilités du LLM ne sont pas un belief state

**Falck, F., Wang, Z., Holmes, C., et al. (2024).** *Is In-Context Learning in Large Language Models Bayesian? A Martingale Perspective.* **ICML 2024**, PMLR v235 — juillet 2024. `https://proceedings.mlr.press/v235/falck24a.html`

« In three experiments, we provide evidence for **violations of the martingale property**, and deviations from a Bayesian scaling behaviour of uncertainty, **falsifying** » l'interprétation de l'ICL comme inférence bayésienne. *(Source citée et reprise par le papier de position §2 : « empirical diagnostics implied by posterior predictive processes under standard assumptions, such as exchangeability and martingale constraints, are often **violated by in-context predictions of pretrained LLMs** ».)*

### 14. Pourquoi le token-level n'est pas le task-level

Repris du papier de position (§2, `https://arxiv.org/html/2605.00742v1`) : « Token-level predictive distributions can be **sharp while the system remains uncertain about the task-level latent variable that matters for action selection**, and conversely, a diffuse next-token distribution can coexist with high confidence about the underlying semantic answer. » Ce point est adossé à une littérature sur l'incertitude **syntaxique vs sémantique** et à des travaux sur l'incertitude épistémique des LLM. **Conséquence opérationnelle :** ne jamais brancher la politique d'arrêt d'ORVYREN sur des probabilités de tokens ou sur une « confiance » verbale, mais sur une postérieure **discrète sur les 3 hypothèses**.

### 15. Ancrage du cas : le décrochage USDC de mars 2023 (les faits, pour l'exemple)

- **Federal Reserve, FEDS Notes (2025).** *In the Shadow of Bank Runs: Lessons from the Silicon Valley Bank Failure and Its Impact on Stablecoins* — **17 décembre 2025**. `https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html` — « At **10 p.m. on Friday evening**, Circle announced that it was unable to withdraw **$3.3 billion** of USDC reserves from SVB (**around 8% of total reserves at the time**), sparking a wave of redemption requests for the stablecoin. »
- **Circle (2023).** *$3.3 Billion of USDC Reserve Risk Removed, Dollar De-peg Closes* — **publié le 13 mars 2023** (dateline Boston, 12 mars 2023). `https://www.circle.com/pressroom/3-3-billion-of-usdc-reserve-risk-removed-dollar-de-peg-closes` — « The $3.3B USDC reserve deposit held at Silicon Valley Bank, **about 8% of the USDC total reserve** » ; le 11 mars, Circle indiquait une collatéralisation de **77 % (32,4 Md USD)** en T-bills et **23 % (9,7 Md USD)** en cash.
- **Diop, P. O., Chevallier, J., & Sanhaji, B. (2024).** *Collapse of Silicon Valley Bank and USDC Depegging: A Machine Learning Experiment.* **FinTech (MDPI)** 3(4):569–590 — **13 décembre 2024**. `https://www.mdpi.com/2674-1032/3/4/30` — « the SVB incident triggered a series of depegging events, with varying effects across stablecoins » et USDC « was particularly vulnerable due to its reliance on SVB reserves » ; analyse sur données journalières d'octobre 2022 à novembre 2023.
- **Reuters (2023).** *Circle assures market after stablecoin USDC breaks dollar peg* — **11 mars 2023**. `https://www.reuters.com/business/crypto-firm-circle-reveals-33-bln-exposure-silicon-valley-bank-2023-03-11/`

**Utilité méthodologique :** ces sources donnent les **faits horodatés** que nos trois hypothèses doivent discriminer — et le Fed note montre que l'information décisive (le sauvetage des déposants) est arrivée **le dimanche 12 mars**, c'est-à-dire *pendant* la fenêtre de décision. C'est exactement le régime où une règle d'arrêt par EVOI a de la valeur.

---

## §2 — Les 3 algorithmes recommandés pour ORVYREN

Conventions : `H = {H1, H2, H3}` (perturbation locale / stress réel / artefact), `p = (p1,p2,p3)` la postérieure, `A = {ALLOW, DENY, REQUIRE_APPROVAL}`, `u(a,h)` l'utilité (négative du coût) de l'action `a` si l'hypothèse `h` est vraie, `S` l'ensemble des sources (agrégateur, exchanges, carnet d'ordres, on-chain, documents).

### Algorithme 1 — `OrchestrateurVOI` : boucle planifier → agir → évaluer → s'arrêter, sous budget

> **Fondé sur :** la règle « un appel supplémentaire n'est justifié que si son EVOI > son coût » et la mise à jour tempérée `r_t(h) ∝ r_{t-1}(h) p(z|h)^{α}` (arXiv:2605.00742, §4.1–4.2) ; l'équation `NetVoI(q) = VoI(q) − c` et l'arrêt si `max NetVoI ≤ 0` (ACL 2026, éq. 4–5, Algorithme 1) ; le plafond `EVSI ≤ EVPPI` (Med Decis Making 2020, éq. 1–2) ; l'allocation par coût espéré (arXiv:2601.01522).

```
ENTRÉES
  H, p0                      # 3 hypothèses pré-enregistrées + priors (gelés, journalisés)
  u: (a, h) -> float         # utilité de l'action a si h vraie  (ALLOW/DENY/REQUIRE_APPROVAL)
  S = [(source, c_s, lat_s)] # coût monétaire + latence par source, mesurés, pas estimés au feeling
  alpha = {source: alpha_i}  # pondérations de fiabilité (init 1.0, mises à jour depuis les résultats)
  B_max                      # budget (appels + latence cumulée) ; B_max <= EVPI_estime
  eps                        # masse postérieure en dessous de laquelle une branche est archivée
  tau                        # seuil de masse pour ARRÊT-PAR-CONFIANCE (garde-fou, pas critère principal)

SORTIES
  action ∈ A ; p_final ; dossier_audit = [(t, source, z_t, p_avant, p_apres, VoI_t, cout_t, motif)]

1  p <- p0 ; B <- 0 ; trace <- []
2  repeter:
3      V0 <- max_{a in A} sum_{h} u(a,h) * p(h)          # équation (2) ACL : valeur d'agir MAINTENANT
4      pour chaque source s in S non encore épuisée:      # sélection = argmax sur le gain NET
5          si c_s + lat_s > B_max - B: continuer
6          VoI_s <- E_{z ~ p(z|s,p)}[ V0_apres_mise_a_jour(p, s, z) ] - V0      # une étape (one-step lookahead)
7          prod <- (VoI_s, s)
8      s* <- argmax prod tel que VoI_{s*} > c_{s*}
9      si aucun s* (ou max_h p(h) >= tau): break          # << RÈGLE D'ARRÊT : plus rien ne vaut son coût
10     z   <- appeler(s*)                                 # observation réellement collectée
11     pour h in H: p(h) <- p(h) * L_s(z, h)^{alpha[s*]}  # équation (2) arXiv : likelihood TEMPÉRÉ
12     p <- p / sum(p)                                    # normalisation
13     alpha[s*] <- maj_alpha(alpha[s*], logloss_observee)  # exp(-beta * L_i), arXiv §4.1
14     B <- B + c_{s*} + lat_{s*} ; tracer(trace, ...)
15     p <- archiver_branches(p, eps)                     # voir Algorithme 2
16 si max_h p(h) < tau_fragile:                           # postérieure fragile
17     action <- REQUIRE_APPROVAL                         # abstention / escalade, arXiv §2 & §4.3 pattern 5
18 sinon:
19     action <- argmax_{a in A} sum_h u(a,h) * p(h)      # équation de l'action de Bayes, arXiv §4.2
20 retourner action, p, trace
```

**Décisions de conception imposées par les sources :**
`VoI_s` est calculé **une étape** en avant : la source est explicite que le VOI exact multi-étapes est intractable et que l'approximation one-step, voire « l'estimateur appris », est la mise en œuvre prévue (Limitation 3 + mitigation, arXiv:2605.00742). `B_max` est plafonné par l'EVPI estimé (propriété `EVSI ≤ EVPPI`).
**Où placer le LLM :** uniquement pour *générer* les observations candidates `z` et *canonicaliser* les documents vers le schéma — **jamais** pour fournir `p`, `u`, `c_s` ou un nombre (voir Algorithme 3).

### Algorithme 2 — `RegistreDeBranches` : cycle de vie CREATED → UNDER_TEST → SUPPORTED/REFUTED/ARCHIVED

> **C'est le manque (2) du projet — promis par le document de conception §7 et absent du prototype.**
> **Fondé sur :** les design patterns « task-level belief factoring », « messages as observations », « reliability-weighted updates » et « dependence-aware evidence pooling » (arXiv:2605.00742, §4.3) ; la contrainte de mémoire bornée via distillation (`belief-state distillation`) ; l'archivage des branches de faible masse est l'analogue de l'abstention conservatrice recommandée au §2.

```
ENTRÉES
  H0                 # hypothèses pré-enregistrées (gelées, horodatées, hashées)
  eps                # masse en dessous de laquelle une branche est ARCHIVED (ex. 0.02)
  theta_support      # seuil de passage à SUPPORTED (ex. p(h) >= 0.8 ET log-BF >= 3)
  theta_refute       # seuil de passage à REFUTED  (ex. p(h) <= 0.05)

SORTIES
  registre = [ (id, enonce, p(h), statut, historique_statuts, preuves[] ) ]
  # historique_statuts est append-only : jamais de réécriture (cf. §1 point 11)

etat(h) initial = CREATED  pour tout h in H0
a chaque observation z_t d'une source s:
    maj_posterieure(p, z_t, s)
    pour h in H0:
        si p(h) >= theta_support et etat(h) in (CREATED, UNDER_TEST):
            etat(h) <- SUPPORTED ; journaliser(appui = preuves(h))
        sinon si p(h) <= theta_refute:
            etat(h) <- REFUTED   ; journaliser(raison = preuves(h))
        sinon si source_jamais_utilisee_pour(h):
            etat(h) <- UNDER_TEST
    # creation dynamique : le LLM PROPOSE une nouvelle branche, l'humain/verificateur la valide
    pour chaque h_new proposee par le LLM (issue := liste de {enonce, source_url, timestamp}):
        si valide_schema(h_new) et non_dupliquee(h_new):
            ajouter(h_new, etat=CREATED, p=0, provenance=h_new.issue)   # p=0 : n'influence PAS la politique
    archiver(h) si p(h) < eps                                            # etat <- ARCHIVED, p gele
retourner registre
```

**Deux règles non négociables :**
(a) une branche **`CREATED` par le LLM démarre à `p = 0`** et n'entre dans le calcul d'utilité qu'après validation et affectation d'un prior explicite — sinon le LLM influence la politique par la porte de derrière ;
(b) `ARCHIVED` n'est **pas** une suppression : c'est la distillation bornée exigée par le pattern 7, et la trace reste auditable.

### Algorithme 3 — `Garde-fouNumerique` : « LLM propose, solveur dispose »

> **C'est le garde-fou du manque (4)/(1) : les chiffres d'ORVYREN ne doivent jamais sortir du LLM.**
> **Fondé sur :** le LLM « strictly a canonicalizer » + CAS déterministe + « abstains as a first-class output » (arXiv:2606.00671) ; le contrôle pré-condition par solveur Z3 avant l'appel d'outil (arXiv:2603.20449) ; les contrats typés et la trace vérifiée par étape (arXiv:2607.04096) ; le fail-closed, le cap de boucle et l'allow-list du determinism layer (Stack Overflow, 2026-10-07) ; le principe « agent pur → Proposal, substrat seul mutateur ».

```
ENTRÉES
  proposition   # sortie du LLM : JSON strict, AUCUN champ numérique libre
  schema        # JSON Schema / modèle typé ; enum ferme {ALLOW, DENY, REQUIRE_APPROVAL}
  politique     # contraintes formelles (SMT-LIB-2.0) sur l'instruction on-chain et ses arguments
  registre_faits # faits horodatés : (valeur, unite, source_url, timestamp_utc, hash_contenu)

SORTIES
  decision ∈ {ALLOW, DENY, REQUIRE_APPROVAL}  # ou ABSTAIN si une vérification échoue
  dossier_audit = { proposition_brute, verifications[], preuves[], motif, hash }

1  si non valide(proposition, schema): retenter(<= 2, en reinjectant l'erreur) sinon ABSTAIN  # fail closed
2  pour chaque champ numerique revendique par le LLM: ABSTAIN  # invariant : aucun nombre produit par le LLM
3  pour chaque chiffre de la decision:
4      f <- resoudre(chiffre, registre_faits)          # lookup dans les faits, PAS de recalcul LLM
5      si f est absent ou si f.timestamp sort de la fenetre de validite: ABSTAIN
6      chiffre <- recalculer_deterministe(f.valeur, f.unite)     # solveur/CAS, pas le LLM
7  sat <- z3.verifier(politique, etat_observable, args_outil)     # PRE-CONDITION a l'appel d'outil
8  si sat == UNSAT: bloquer(l'outil), decision <- REQUIRE_APPROVAL, journaliser(sat)
9  decision <- proposition.decision si coherente avec max_h u(a,h) p(h), sinon REQUIRE_APPROVAL
10 journaliser_append_only(dossier_audit)             # jamais de UPDATE, uniquement des ajouts
11 retourner decision, dossier_audit
```

**Invariant central à écrire dans le dossier de concours :** *tout chiffre affiché par ORVYREN est traçable à un triplet `(valeur, source_url, timestamp_utc)` présent dans le registre de faits, recalculé par un composant déterministe* — c'est exactement l'architecture publiée « canonicalizer + solveur déterministe + abstention » (arXiv:2606.00671) et la vérification par solveur en pré-condition (arXiv:2603.20449).

---

## §3 — Ce qui est démontré vs ce qui reste spéculatif

### (a) Démontré (mesuré, évalué, ou prouvé par les sources primaires)

| # | Affirmation | Statut | Source |
|---|---|---|---|
| 1 | La règle « un appel d'agent supplémentaire n'est justifié que si son EVOI > son coût » est le critère d'orchestration explicite de l'état de l'art. | Position argumentée (position paper), cohérente avec la théorie de la décision | arXiv:2605.00742 §4.1–4.2, 2026-05-01 |
| 2 | Une politique `NetVoI(q) > 0` égale ou dépasse les meilleures baselines réglées à la main dans 18/20 conditions, jusqu'à +1,36 point d'utilité, et **sans réglage de seuil**. | **Empiriquement démontré** (4 domaines, 2 modèles) | ACL 2026, 2026-07 |
| 3 | L'arrêt fondé sur le « ressenti » de confiance du modèle est **moins bon** et instable. | **Empiriquement démontré** | ACL 2026 §6.1 |
| 4 | Le seuil de confiance optimal est très sensible et doit être réglé manuellement par tâche et par coût. | **Empiriquement démontré** | ACL 2026 §6.1 |
| 5 | « Interroger un seul LLM pour une postérieure puis seuiller la confiance » est **inadéquat** pour les décisions séquentielles à coûts. | **Prouvé + expérimenté** | arXiv:2601.01522, 2026-01-04 |
| 6 | L'auto-évaluation de réussite des agents est sur-confiante (22 % de réussite réelle annoncée à 77 %). | **Mesuré** | arXiv:2602.06948, 2026-02-06 |
| 7 | La pré-évaluation (avant exécution) discrimine mieux que la revue post-exécution, et le cadrage « bug-finding » étalonne le mieux. | **Mesuré** (différences parfois non significatives — nuance de la source) | arXiv:2602.06948 |
| 8 | Vérifier les appels d'outil par solveur SMT en **pré-condition** réduit les violations de politique en maintenant la précision. | **Démontré** (TauBench) | arXiv:2603.20449, 2026-03-20 |
| 9 | Une architecture « LLM = canonicalizer + solveur déterministe + abstention » atteint 0 réponse confident-wrong sur un jeu tenu à l'écart, et 100 % sur l'arithmétique sans le LLM. | **Démontré** (préprint, 4 783 routes) | arXiv:2606.00671 v1 2026-05-30 / v3 2026-08-12 |
| 10 | Les sorties structurées/contraintes réduisent les sorties malformées mais **ne garantissent pas la justesse**. | Établi et rappelé par la source | Stack Overflow, 2026-10-07 (blog) ; illustré par arXiv:2606.00671 |
| 11 | Les formules EVPPI/EVSI et la borne `EVSI ≤ EVPPI` sont standard ; l'estimation exacte est coûteuse. | **Établi** (méthode de référence) | Med Decis Making 2020-04-16 |
| 12 | L'EVOI exact est coûteux et sans garantie de borne ; une variante par gradient en fournit. | **Prouvé** (bornes de regret) | WWW '25, 2025-04-22 |
| 13 | Les LLM pré-entraînés violent la propriété de martingale en ICL → ils ne sont pas des agents d'inférence bayésienne. | **Réfutation empirique publiée** | ICML 2024, PMLR v235 |

### (b) Encore spéculatif, non démontré, ou hors de portée

| # | Ce qui n'est PAS démontré | Pourquoi c'est important pour ORVYREN |
|---|---|---|
| 1 | **Aucun orchestrateur bayésien de bout en bout n'est déployé et évalué.** Les auteurs écrivent que leurs exemples sont « not intended as […] fully instantiated end-to-end algorithms ». | Nous ne pouvons pas prétendre « reproduire un résultat » sur l'orchestrateur : nous *instancions* un patron. Formuler ainsi dans le dossier. |
| 2 | **Le VOI exact multi-étapes est intractable.** La source recommande explicitement des approximations (comparer le coût d'un appel à une estimation de réduction d'incertitude ou de perte espérée, en un pas ou par prédicteur appris). | Notre Algorithme 1 est une approximation *assumée*, pas une garantie d'optimalité — à écrire tel quel. |
| 3 | **Passer d'une postérieure sur 3 hypothèses à un résultat financier général n'est pas démontré.** Tous les résultats empiriques des sources portent sur des domaines autres que les marchés (recommandation, 20Q, diagnostic, CV, e-commerce). | La valeur d'ORVYREN est la *méthode*, pas un claim de performance de marché. |
| 4 | **La « dependence-aware evidence pooling » reste un défi ouvert** explicitement listé. Nos 5 sources de données ne sont pas conditionnellement indépendantes (agrégateurs branchés sur les mêmes exchanges). | Le `α_i` tempéré est une *atténuation*, pas une correction : le dossier doit le dire. |
| 5 | **Les garanties des métriques IPM pour le BOED sont récentes et non testées en finance** ; l'article est de 2026 et porte sur des problèmes inverses/scientifiques. | Utilisable comme justification d'un choix de critère, pas comme résultat reproduit. |
| 6 | **Le belief `b(θ)` estimé par le LLM n'a pas de validation contre une distribution de vérité terrain** — l'analyse de calibration de l'article ACL mesure seulement la justesse de l'argmax, faute de distribution connue. | Nous devons concevoir dès maintenant le protocole de calibration (prévisions gelées vs réalisé) et non supposer la calibration. |
| 7 | **Le modèle de coût est simplifié (linéaire) dans toutes les sources consultées.** | Nos coûts (latence, tokens, coût d'opportunité, coût de réputation d'un faux DENY) devront être explicites et paramétrables, sans prétendre à l'exactitude. |
| 8 | **L'architecture « canonicalizer + CAS » vient d'un préprint mono-auteur** et son gate Lean « covers a fixture corpus, so live output is generated, not machine-checked ». | Citer le *principe* comme architecture publiée ; ne pas citer les chiffres comme standards. |
| 9 | **Les articles de blog (Stack Overflow) ne sont pas évalués par les pairs.** | À citer comme pratique d'ingénierie, jamais comme preuve. |
| 10 | **La sémantique « EVOI » n'est pas uniforme** entre les sources (EVOI = valeur d'une question chez ACM/ACL ; VOI = gain d'utilité ; EVPI/EVPPI/EVSI en économie de la santé). | Le dossier doit **définir une seule notation** et s'y tenir, pour éviter un faux désaccord apparent. |

---

## §4 — Pièges documentés et remèdes

| # | Piège | Preuve | Remède pour ORVYREN |
|---|---|---|---|
| 1 | **Confiance verbale du LLM mal calibrée.** Le modèle « se sent » confiant, la politique suit, l'arrêt est faux. | ACL 2026 §6.1 : « based on the model's internal "feeling" of confidence, which is often **poorly calibrated** » ; arXiv:2602.06948 : 22 % de réussite annoncés à 77 % | Le belief state est une postérieure discrète sur `{H1,H2,H3}`, mise à jour par likelihood pondérée. Aucun nombre de confiance produit par le LLM n'entre dans la politique. « Compose it from independent signals instead » (Stack Overflow). |
| 2 | **Post-exécution : meilleure perception, pire discrimination.** La revue de sa propre sortie *après* coup discrimine moins bien que la pré-évaluation. | arXiv:2602.06948 | Éliciter la confiance **avant** exécution et geler la prévision ; reframer l'évaluation en « **recherche de bugs** » (meilleur étalonnage mesuré). |
| 3 | **Seuils fragiles.** Un `τ` réglé sur un cas ne généralise ni au domaine ni au coût. | ACL 2026 §6.1 ; arXiv:2601.01522 (preuve d'inadéquation) | Remplacer les seuils par `NetVoI(q) = VoI(q) − c`. Garder `tau` uniquement comme **garde-fou d'arrêt supérieur**, jamais comme critère principal. |
| 4 | **Évidence corrélée = sur-confiance.** Reprompting du même modèle, pipelines de retrieval partagés, agrégateurs alimentés par les mêmes exchanges. | arXiv:2605.00742 §2 et §4.1 : « repeated tool calls can yield correlated evidence » ; « dependence-aware evidence pooling » est un **défi ouvert** (§5) | `α_i` de fiabilité **distincts** du likelihood (équation 2), *likelihood tempering*, et documentation explicite des dépendances connues entre nos sources. Ne jamais multiplier naïvement les likelihoods. |
| 5 | **Token-level ≠ task-level.** Une distribution de tokens pointue peut coexister avec une grande incertitude sur l'hypothèse qui détermine l'action. | arXiv:2605.00742 §2 | Belief sur des variables de **niveau tâche** (`H1/H2/H3`), jamais sur des probabilités de tokens. |
| 6 | **Structure ≠ justesse.** Un JSON parfaitement valide peut être complètement faux (`{"decision":"approve","confidence":0.99}`). | Stack Overflow, 2026-10-07 : « structure constrains *form*, not *correctness* » ; arXiv:2606.00671 : « a confident-wrong answer is indistinguishable from a confident-right one » | Étage de **vérification déterministe** après l'étage LLM + solveur SMT en pré-condition (arXiv:2603.20449). Échec → `ABSTAIN` (fail closed). |
| 7 | **Coûts cachés : la VOI n'est pas gratuite.** | ACL 2026 Annexe B : `O(TK|Q|)` ≈ **10×** le coût des baselines ; Med Decis Making : Monte Carlo « weeks » contre « minutes or hours » ; Stack Overflow : boucle libre = latence/coût « **unbounded** » | (a) budget `B_max` explicite ; (b) plafond `B_max ≤ EVPI` ; (c) cap dur sur le nombre d'itérations + allow-list de sources ; (d) mesurer et journaliser `c_s` et `lat_s` réels. |
| 8 | **Fragilité des critères KL / EIG.** Support mismatch, sous-estimation des queues, sensibilité aux événements rares — exactement le régime d'un décrochage. | arXiv:2604.21849, 2026-04-23 | Préférer un critère ancré sur la **réduction de perte espérée décisionnelle** (VOI, éq. 4) plutôt que la seule réduction d'entropie ; envisager des divergences plus stables (MMD, Wasserstein) en documentant l'incertitude. |
| 9 | **Le LLM comme source de chiffres.** Le modèle « calcule » un ratio de réserves ou un prix. | arXiv:2606.00671 : le LLM est *strictement* canonicalizer ; chemin « rule-only » sans LLM à 100 % | **Invariant Algorithme 3** : tout chiffre résolu dans un registre de faits `(valeur, source_url, timestamp)` et recalculé par un composant déterministe. Aucun champ numérique libre dans le schéma de sortie du LLM. |
| 10 | **Audit mutable.** Un journal modifiable n'est pas une preuve. | Stack Overflow : « If you can `UPDATE` the ledger it's not an audit trail » | Journal **append-only** ; l'`ARCHIVED` du registre de branches est un état, pas une suppression. |
| 11 | **Sur-claim de type « Bayes garantit la performance ».** Le cadre bayésien garantit la *cohérence*, pas la justesse du modèle. | arXiv:2605.00742 §6 : « the controller's posterior is only as well founded as the observation models and evidence channels used to update it » ; arXiv:2607.04096 | Écrire « cohérent avec les principes bayésiens » et non « bayésien optimal » ; exposer la traçabilité des likelihoods. |
| 12 | **Confondre les notations EVPI / EVPPI / EVSI / EVOI / VOI** dans un même document. | Pratiques divergentes entre Med Decis Making (2020), ACM (2025) et ACL (2026) | Poser une table de notation unique dans le dossier avant toute formule. |

---

## §5 — Cinq affirmations sûres pour le dossier du concours

Chacune est appuyée sur au moins une source vérifiée, et formulée **sans sur-claim**.

**A1 — Sur la règle d'arrêt et de recherche.**
> « Un appel d'agent ou d'outil supplémentaire n'est justifié que si la valeur d'information attendue excède son coût ; c'est le critère d'orchestration explicite retenu par l'état de l'art en orchestration d'agents bayésienne. »
> **Source :** Papamarkou et al., *Position: agentic AI orchestration should be Bayes-consistent*, arXiv:2605.00742, 1er mai 2026 (§4.1 : « An additional agent call is justified only when its expected value of information exceeds its cost » ; §4.2). Version ESSEC Working Paper antérieure : `hal-05480691`, 27 janvier 2026.

**A2 — Sur l'arrêt par valeur de l'information plutôt que par seuil.**
> « Une politique d'arrêt fondée sur la valeur de l'information (`VoI(q) − c`) égale ou dépasse les meilleures baselines à seuil de confiance réglées manuellement dans 18 des 20 conditions testées, avec un gain allant jusqu'à 1,36 point d'utilité, et ce sans aucun réglage de seuil ; les approches fondées sur le "ressenti" de confiance du modèle sont au contraire instables et moins bonnes. »
> **Source :** Dong et al., *Value of Information: A Framework for Human–Agent Communication*, ACL 2026 Long Papers, pp. 42879–42896, juillet 2026, `https://aclanthology.org/2026.acl-long.1987/` (abstract ; §6.1 ; Table 1 ; éqs. 4–5).

**A3 — Sur l'inadéquation du seuillage de confiance mono-LLM en décision séquentielle à coûts asymétriques.**
> « Pour des décisions séquentielles à coûts asymétriques, le schéma dominant — demander à un unique LLM une distribution postérieure puis seuiller sa confiance — a été **prouvé inadéquat** ; les architectures correctes traitent le LLM comme un modèle de vraisemblance approximatif et sélectionnent les actions par coût espéré et par valeur de l'information. »
> **Source :** Amin, D., *Bayesian Orchestration of Multi-LLM Agents for Cost-Aware Sequential Decision-Making*, arXiv:2601.01522, 4 janvier 2026 (abstract : « we prove this is inadequate for sequential decisions with costs »).

**A4 — Sur le fait que les chiffres ne doivent pas provenir du LLM.**
> « Les architectures publiées de raisonnement vérifiable placent le modèle de langage **strictement** en canonisateur : la dérivation, la vérification et le calcul sont confiés à un pipeline déterministe, l'**abstention étant une sortie de première classe**. La raison est structurelle : au niveau de l'API, une réponse confiante et fausse est indiscernable d'une réponse confiante et juste. »
> **Source :** Bruno, A., *Moxia (formerly AXIOM): A Trust-First Neuro-Symbolic Execution Architecture…*, arXiv:2606.00671 (v1 30 mai 2026 ; v3 12 août 2026). Compléments : vérification de politique par solveur **Z3** en pré-condition d'appel d'outil (Winston, Winston & Just, arXiv:2603.20449, 20 mars 2026) et contrats typés à trace vérifiée par étape (Bhat et al., arXiv:2607.04096, 5 juillet 2026).

**A5 — Sur la sur-confiance et le protocole de calibration.**
> « L'auto-évaluation de confiance des agents est mesurablement sur-confiate : des agents qui réussissent 22 % du temps prédisent 77 % de succès ; la pré-évaluation (avant exécution) discrimine mieux que la revue post-exécution, et le cadrage de l'élicitation en "recherche de bugs" donne le meilleur étalonnage. »
> **Source :** Kaddour, J., Patel, S., Dovonon, G., Richter, L., Minervini, P., & Kusner, M. J., *Agentic Uncertainty Reveals Agentic Overconfidence*, arXiv:2602.06948, 6 février 2026.

> **Deux affirmations de repli** (si l'on veut élargir) :
> **A6 —** « Les LLM pré-entraînés ne se comportent pas comme des agents d'inférence bayésienne : la propriété de martingale est violée en in-context learning. » → Falck et al., ICML 2024, PMLR v235, juillet 2024, `https://proceedings.mlr.press/v235/falck24a.html`.
> **A7 —** « L'EVPI constitue le plafond de ce qu'il est rationnel de payer pour une recherche d'information : la valeur de l'information imparfaite (EVSI) est bornée supérieurement par la valeur de l'information parfaite (EVPPI). » → Heath et al., *Medical Decision Making* 40(3):314–326, 16 avril 2020, `https://pmc.ncbi.nlm.nih.gov/articles/PMC7968749/` (éqs. 1–2).

---

## §6 — Implications directes pour ORVYREN (synthèse opérationnelle)

1. **Le manque (3) — quantification de la valeur d'une recherche — se comble avec les équations (2)–(5) de l'article ACL** appliquées à `u(a,h)` avec `a ∈ {ALLOW, DENY, REQUIRE_APPROVAL}` et `h ∈ {H1,H2,H3}`. Le prototype « va chercher un fait discriminant » doit devenir « va chercher le fait de `NetVoI` maximal, et s'arrête si `max NetVoI ≤ 0` ».
2. **Le manque (1) — boucle autonome — devient l'Algorithme 1**, avec budget `B_max`, cap d'itérations et allow-list de sources (recommandations convergentes de ACL 2026 et du determinism layer).
3. **Le manque (2) — registre de branches — devient l'Algorithme 2**, avec la règle de sûreté « toute branche CREATED par le LLM démarre à `p = 0` » et un cycle de vie append-only.
4. **Le manque (4) — calibration — s'appuie sur Kaddour et al. (2026)** : prévisions **gelées avant exécution**, reframées en « recherche de bugs », comparées au réalisé ; et jamais de confiance auto-déclarée dans la politique.
5. **Décision architecturale la plus rentable pour le concours :** formaliser et documenter l'invariant « **les chiffres ne viennent jamais du LLM** » (Algorithme 3) — il est adossé à trois architectures publiées en 2026 et il est directement démontrable par le code et le dossier d'audit existants.

---

## Sources

Toutes les URL ci-dessous ont été enregistrées et vérifiées via un registre local (`sources.py`, ledger `orvyren_ledger.json`) au moment de la consultation. Dates relevées sur la page elle-même ou via une API officielle (arXiv, HAL, PubMed E-utilities).

1. Papamarkou, T. et al. — *Position: agentic AI orchestration should be Bayes-consistent* — arXiv:2605.00742 (v1 2026-05-01, v2 2026-05-06) — https://arxiv.org/abs/2605.00742
2. Idem, texte intégral HTML v1 — https://arxiv.org/html/2605.00742v1
3. Papamarkou, T. et al. — *Position: Agentic AI systems should be making Bayes-consistent decisions* — ESSEC Working Papers, hal-05480691, écrit/déposé 2026-01-27, diffusé 2026-03-04 — https://hal.science/hal-05480691 (métadonnées via API HAL ; PDF non ouvert, voir §0)
4. Version de soumission (OpenReview) — https://openreview.net/pdf?id=ydcX7UoHA3 (non lue intégralement)
5. Dong, Y. R., Hu, T., Hui, Z., Zhang, C., Vulić, I., Bobu, A., Collier, N. — *Value of Information: A Framework for Human–Agent Communication* — ACL 2026 Long Papers, pp. 42879–42896, juillet 2026 — https://aclanthology.org/2026.acl-long.1987/
6. Idem, PDF intégral — https://aclanthology.org/2026.acl-long.1987.pdf
7. Li, Z., Liu, M., Dai, X., Lui, J. C. S. — *Towards Efficient Conversational Recommendations: Expected Value of Information Meets Bandit Learning* — WWW '25, publié 2025-04-22 — https://dl.acm.org/doi/10.1145/3696410.3714773
8. Amin, D. — *Bayesian Orchestration of Multi-LLM Agents for Cost-Aware Sequential Decision-Making* — arXiv:2601.01522, 2026-01-04 — https://arxiv.org/abs/2601.01522
9. Kaddour, J., Patel, S., Dovonon, G., Richter, L., Minervini, P., Kusner, M. J. — *Agentic Uncertainty Reveals Agentic Overconfidence* — arXiv:2602.06948, 2026-02-06 — https://arxiv.org/abs/2602.06948
10. Winston, C., Winston, C., Just, R. — *Solver-Aided Verification of Policy Compliance in Tool-Augmented LLM Agents* — arXiv:2603.20449, 2026-03-20 — https://arxiv.org/abs/2603.20449
11. Wu, D., Liang, L., Yang, H. — *Beyond Expected Information Gain: Stable Bayesian Optimal Experimental Design…* — arXiv:2604.21849, 2026-04-23 — https://arxiv.org/abs/2604.21849
12. Bruno, A. — *Moxia (formerly AXIOM): A Trust-First Neuro-Symbolic Execution Architecture for Self-Explaining Mathematical Reasoning* — arXiv:2606.00671 (v1 2026-05-30, v3 2026-08-12) — https://arxiv.org/abs/2606.00671
13. Bhat, V., Vaghasiya, J., Gonzalez, E. A. — *Forethought: Verifiable Reasoning from Neurosymbolic Primitive Programming* — arXiv:2607.04096, 2026-07-05 — https://arxiv.org/abs/2607.04096
14. Stack Overflow — *Part 1: Make your AI agents boring: the determinism layer* — 2026-10-07 (blog, non peer-reviewed) — https://stackoverflow.blog/2026/10/07/part-1-make-your-ai-agents-boring-the-determinism-layer/
15. Heath, A., Kunst, N., Jackson, C. et al. — *Calculating the Expected Value of Sample Information in Practice: Considerations from Three Case Studies* — Medical Decision Making 40(3):314–326, epub 2020-04-16 — https://pmc.ncbi.nlm.nih.gov/articles/PMC7968749/
16. Falck, F. et al. — *Is In-Context Learning in Large Language Models Bayesian? A Martingale Perspective* — ICML 2024, PMLR v235 — https://proceedings.mlr.press/v235/falck24a.html
17. Federal Reserve (FEDS Notes) — *In the Shadow of Bank Runs: Lessons from the Silicon Valley Bank Failure and Its Impact on Stablecoins* — 2025-12-17 — https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html
18. Circle — *$3.3 Billion of USDC Reserve Risk Removed, Dollar De-peg Closes* — 2023-03-13 (dateline 2023-03-12) — https://www.circle.com/pressroom/3-3-billion-of-usdc-reserve-risk-removed-dollar-de-peg-closes
19. Diop, P. O., Chevallier, J., Sanhaji, B. — *Collapse of Silicon Valley Bank and USDC Depegging: A Machine Learning Experiment* — FinTech (MDPI) 3(4):569–590, 2024-12-13 — https://www.mdpi.com/2674-1032/3/4/30
20. Reuters — *Circle assures market after stablecoin USDC breaks dollar peg* — 2023-03-11 — https://www.reuters.com/business/crypto-firm-circle-reveals-33-bln-exposure-silicon-valley-bank-2023-03-11/

*Note : 20 sources enregistrées ; 5 sources fermées (voir §0) n'ont pas pu être ouvertes intégralement et sont signalées comme telles à chaque endroit où elles sont invoquées.*
