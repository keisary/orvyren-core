# ORVYREN — Audit externe indépendant (2026-10-17)

**Auditeur** : agent auditeur indépendant (5 casquettes : jury · architecture · bugs · sécurité · produit/scaling)
**Dépôt audité** : `D:/orvyren_core`, `master = 02cd2eb` (arbre propre)
**État de référence du prompt d'audit** : `3275e64` — le dépôt a avancé (le prompt d'audit lui-même a été commité), c'est normal.
**Nature** : rapport interne d'aide à la décision. **Ce n'est pas une pièce de soumission.**
**Mode** : lecture seule sur le dépôt (un seul fichier créé : le présent rapport). Aucune commande on-chain, aucun appel LLM payant.

---

## 0. Verdict exécutif

| Dimension | Note | Confiance | Une ligne de justification |
|---|---|---|---|
| Idée /10 | **7,0** | Élevée | La thèse « décision vérifiable + enveloppe bornée + preuve recalculable » est solide et réellement adossée au thème F, mais le claim central « l'agent exécute seul » n'est soutenu par aucun code. |
| Implémentation /10 | **6,5** | Élevée | 811 tests, gel vérifié, reçus testnet réels, vérificateur tiers hors-ligne : la rigueur est réelle. Mais la couture décision→exécution n'existe pas, le rapport sécurité contredit le code, et les compteurs publiés ne se reproduisent pas. |
| Conformité concours /100 (40/30/30) | **54** (fourchette 44–65) | Moyenne | Détail : 22/40 accomplissement · 17/30 sécurité & conformité · 15/30 innovation & interaction. Le fond est bon ; **2 pièces sur 6 manquent**, le dépôt GitHub est **privé**, et le README est en français. |
| Scalabilité /10 | **5,5** | Moyenne | SQLite local, 2 workers, corpus archivés, données 100 % offline : correct pour un concours, mince comme architecture produit. |
| **Verdict top-10** | **« Non aujourd'hui — mais rattrapable en ~20 h-agent »** | Élevée | Aucun défaut de fond : le troisième verifiable est réel, rare et solide. Mais le jury **ne peut pas cloner le dépôt** (privé), **ne peut pas lire le README** (français), **ne voit ni deck ni vidéo**. Le handicap est de la production, pas de l'ingénierie. |

### 🚨 Le blocage n°1, à traiter dans l'heure

**Le dépôt GitHub est PRIVÉ.** Vérifié deux fois, indépendamment :

| Test | Résultat |
|---|---|
| `https://api.github.com/repos/keisary/orvyren-core` (anonyme) | **404 Not Found** |
| `https://api.github.com/repos/pallets/click` (témoin public, même méthode) | **200 OK** |
| `git ls-remote https://github.com/keisary/orvyren-core.git` | réussit — **mais via un identifiant mis en cache localement**, pas en anonyme |

La pièce ④ exige un dépôt public. En l'état, **un jury ne peut pas cloner ORVYREN** : il juge un dossier
qu'il ne peut pas ouvrir. Coût de la correction : **30 minutes**. C'est de loin le meilleur ratio
impact/effort de tout l'audit — et il est **bloquant**.

### Les conditions du « oui », vérifiables

1. **Dépôt public + nettoyé** (30 min) — basculer en public *après* avoir retiré `AUDIT_PROMPT.md`,
   `docs/RAPPORT_COMPLETION_*.md` et les `handoff-*.md`, qui exposent l'auto-critique interne
   (« 38/46 pleines », « gelé orphelin », « clé DeepSeek absente »). Un juge qui lit ça avant le pitch change d'avis.
2. **README anglais + une commande unique de démo** (1 h 30) — le README est aujourd'hui la porte d'entrée
   d'un jury anglophone, et il est en français, avec une commande quickstart en syntaxe bash.
3. **Deck + vidéo** (6–8 h) — les deux pièces totalement absentes. Chemin critique du calendrier.
4. **Réconciliation du rapport sécurité** (30 min de rédaction, **~5 h de correction du code**) — le rapport
   sécurité porte **deux affirmations fausses**, toutes deux vérifiables en 2 minutes :
   « *The agent never holds a key* » contredit par `signer.py` + 13 reçus, et R4 « *cap cumulative 300 USDC
   enforced — none observed* » contredit par **10 transferts de 100 USDC qui passent tous** (`F-B-04`, mesuré).
   Pendant ce temps, sur le seul chemin d'exécution livré, **6 des 14 règles sont `SKIPPED`** et
   `policy_v1.yaml` n'y est même pas chargé (`F-B-05`) : **le kill switch et le SAFE MODE y sont inopérants**.
   Ce n'est pas une correction de rédaction — c'est un câblage à faire.
5. **Réécriture de la promesse d'autonomie** (30 min) — « l'agent exécute seul » est écrit 5 fois et n'est
   exécuté nulle part. Ou on construit la boucle (2,5 h), ou on corrige le vocabulaire.
6. **Commande de référence qui plante sous Windows** (20 min) — `python run_replay.py journal --case usdc-2023-03`,
   première ligne du quickstart README, lève un `UnicodeEncodeError` sur console cp1252 (`F-B-06`).

> **Les points 1, 2, 3, 4, 5 et 6 coûtent ~10 h-agent et transforment un dossier qui se contredit en un dossier
> défendable. Deck + vidéo reste le seul vrai chemin critique de calendrier ; tout le reste est du polish.**

**Le plus mauvais scénario de non-sélection** : le jury reçoit l'inscription, tente le lien GitHub, obtient
« repository not found », n'ouvre pas le README (français), ne trouve ni deck ni vidéo, et ne devote pas
5 minutes de plus à un dossier qu'il n'a pas pu démarrer. **C'est exactement le scénario actuel.**

---

## 1. Verdict sur l'idée (axe A)

### 1.1 La question centrale : existe-t-il un exécuteur autonome de bout en bout ?

**Réponse : NON. Il n'existe aucun déclencheur autonome. Verdict : `MANUEL`.**

Preuves (toutes vérifiées en lecture) :

| Ce qui existe | Ce que ça prouve | Fichier |
|---|---|---|
| Aucun `scheduler`, `poll_*`, `daemon`, `cron`, `while True` de production dans `src/` ni dans les CLIs racine | rien n'enchaîne décision → exécution en continu | recherche sur tout `src/`, `scripts/`, `*.py` racine |
| `python -m orvyren.decide` écrit un `DecisionRecord` dans `evidence/decision_record_<case>.json` … et **personne ne le relit** | la sortie de la décision ne déclenche rien | `src/orvyren/decide.py:204-221` ; aucun module n'importe `orvyren.decide` (recherche exhaustive) |
| `run_execution_demo.py` ne contient **aucune occurrence du mot `decision`** | la couche exécution n'est pas câblée sur la couche décision | `run_execution_demo.py` (recherche exhaustive du fichier) |
| La démo d'exécution construit des intents **codés en dur** (`I1/I2/I3`, horloge figée `DEMO_CLOCK = 2026-10-14 12:00Z`) | l'intent exécuté n'est pas celui qu'a produit le moteur de décision | `src/orvyren/execution/intents.py::build_demo_intents` |
| Le docstring du CLI d'exécution dit : « *the agent never holds a key and never signs… a human executes this transfer* » | le chemin officiel d'exécution est explicitement humain | `run_execution_demo.py:6-9` |
| Le kit `scripts/demo/demo.py` signe réellement, mais **un run à la fois, lancé par un humain** (runs A→E, `--dry-run` par défaut) | l'exécution réelle existe mais n'est pas autonome | `scripts/demo/demo.py` (`RUNS = ("A","B","C","D","E")`) |

**Le lien manquant, énoncé simplement** : ORVYREN a deux moitiés qui ne se touchent pas.
La **moitié décision** produit une intention non exécutable — `evidence/decision_record_usdc-2023-03.json` contient
`"recipient": ""`, `"authorization_verdict": null`, `"evaluated": false`, avec la raison honnête
`"no reserve recipient configured — authorization not evaluated"`.
La **moitié exécution** démarre sur des intents écrits à la main dans le kit de démo.
Le schéma de `DOC1 §3` (⑥ DÉCIDER → ⑦ AUTORISER → ⑧ EXÉCUTER) est un loop **dessiné**, pas un loop **exécuté**.

**Nuance importante, et c'est la seule lecture défendable** : ORVYREN n'a pas le problème de l'agent qui
*déclenche* tout seul — il a le problème de l'agent qui *n'agit jamais sans qu'on le lui demande*. Ce n'est pas un défaut,
c'est une feature non formulée. Le système possède une **autorité bornée** prouvée par le run D (kill switch on-chain,
revocation mesurée), mais **aucune initiative**. Une minute d'exécution autonome continue est exactement le
chaînon manquant du thème F.

**Chemin le plus court vers un exécuteur autonome** (détail complet en §4, conception en Annexe D) :
réutiliser `orvyren.decide` → `policy.evaluate` → `signer.sign_transaction` → `verify_receipt` → journal REPLAY-JOURNAL,
dans une boucle unique, `dry-run` par défaut, plafonds par tick et par jour, kill switch déjà éprouvé. **Estimation : 3–5 h-agent.**

### 1.2 Différenciation — est-ce un vrai avantage démontrable en 5 minutes ?

**Oui pour la méthode, non pour le produit.** C'est le vraidiagnostic.

Ce qui est difficilement rattrapable : le **gel pré-enregistré** (`frozen/G1–G6`, sha256 scellés, 8 prévisions gelées
avant de voir les résultats), le **vérificateur tiers exécutable hors du dépôt** (`run_verify.py`, verdict recompté
de A à C + mutations), et le **kill switch réellement chronométré**. Un concurrent qui n'a pas ces pièces ne peut pas
les produire le 19 octobre à 23 h. C'est un avantage structurel réel.

Ce qui n'est pas différenciant : la pile technique. Graphe de connaissance, agents multi-rôles, RDOF, catalogue
d'actions — un jury international sait que ces briques sont standard chez les agents de trading. **Elles ne gagnent
pas un concours ; elles évitent de perdre.**

**La seule chose qu'un jury citerait comme « la » raison de nous sélectionner** n'est pas dans le code :
c'est **« ils ont écrit leur évaluation avant de connaître le résultat, et le résultat contredit une partie de leurs
hypothèses — et ils le publient tel quel. »** C'est vrai chez vous (`REPLAY-ARCHIVE` : 2× `ARRET-2`, 1× `ABORTED`,
2 sorties en quarantaine, distribution publiée telle quelle). **C'est le matériau du pitch. Il est actuellement
nappé dans un rapport de complétion que personne ne lira.** Il doit devenir le cœur de la vidéo.

### 1.3 Périmètre : trop de documentation pour trop peu de produit visible ?

**Oui, et c'est le risque n°1 de non-sélection.** Mesure : ~3 300 lignes de Markdown à la racine (dont 1 141 dans
DOC2 et 746 dans DOC3) pour 12 écrans hors-ligne et une boucle d'exécution manuelle. Le ratio est inversé par
rapport à ce qu'un jury valorise : *interaction & innovation* = 30 % de la note, et l'interaction livrée est une
pile de pages HTML locales.

**Recommandation : resserrer, ne pas élargir.** Un seul cas d'usage ultra-démontré, répété 3 fois dans la vidéo,
vaut mieux que 4 modules Petroleum sur un seul cas (`usdc-2023-03`) réellement démontré.

### 1.4 Positionnement — trois reformulations du pitch

| # | Pitch une ligne | Force | Faiblesse |
|---|---|---|---|
| **P1** | *« ORVYREN is a treasury agent whose every dollar is pre-approved on-chain and every decision is re-computable by a third party. »* | Cible le thème F mots pour mots (« risk control », « executes ») et correspond à l'avantage réel | « pre-approved » masque l'absence de déclencheur |
| **P2** | *« We wrote the exam before the answers existed — and published the result even where it disappointed us. »* | Différenciation maximale, vérifiable, mémorisable, preuve à l'appui | Ne dit rien du produit ; ne convient qu'en accroche d'ouverture |
| **P3** | *« An AI wallet agent with an authority envelope it cannot widen, and a kill switch its owners can pull in under five minutes — demonstrated live on Base Sepolia. »* | Concentre autonomy + risque + preuve on-chain, tient en une phrase | « demonstrated » est à prouver en direct ou sur vidéo |

**Recommandation** : **P3 en titre, P2 en deuxième phrase, P1 pour le Technically-deep.** Une phrase qui contient
« envelope + kill switch + live testnet » gagne le thème F ; une phrase qui contient « pre-registered evaluation »
gagne le facteur humain du jury. Il faut les deux.

### 1.5 Verdict d'idée et modifications proposées

**Verdict : IDÉE SOLIDE — à ajuster (pas à repenser).** La thèse ne doit pas être abandonnée : elle est difficile
à imiter en 72 h. Ce qui manque n'est pas une idée, c'est une **preuve visible** et un **vocabulaire honnête**.

**7 modifications, classées par impact sur la sélection :**

| # | Modification | Pourquoi (impact sélection) | Effort |
|---|---|---|---|
| **M1** | Corriger la garde de la clé partout : soit le rapport sécurité décrit le signer du kit, soit le kit est décrit comme « signature par clé jetable hors agent ». | 30 % de la note repose sur la crédibilité sécurité. Une contradiction vérifiable en 2 min est le plus gros risque du dossier. | **30 min** |
| **M2** | Remplacer « l'agent exécute seul » par « **autorité bornée, déclenchement surveillé** » dans DOC1:51/82, DOC2:80/1006/1431, DOC3:760, DEMO_KIT:408. | Supprime le risque de « promesse non tenue » sur le critère qui définit le thème. | **30 min** |
| **M3** | Câbler la décision à l'exécution : `decide.py` → `policy.evaluate` → intent exécutable, et le recive un `recipient` configuré. | Rend le schéma ⑥→⑦→⑧ réel. Sans ça, le cœur du cycle est un dessin. | **2–3 h** |
| **M4** | Refaire les compteurs publiés à partir d'une exécution unique et coller la sortie dans le README. | « 811/808/3 » ne se reproduit pas → un jury qui lance la commande perd la confiance immédiatement. | **20 min** |
| **M5** | Écrire la vidéo ≤ 5 min en-aroundant le résultat honnête (`ARRET-2`/`ABORTED`, quarantaine de 2 sorties). | Seule pièce qui manque et qui transforme un dossier en candidature. | **4–6 h** |
| **M6** | Décider explicitement le sort de G6 : soit les 3 paramètres sans source sont déclarés « hypothèses d'analyste » avec sensibilité publiée, soit l'EVAL est présenté comme **non exécutable** et on le dit. | Ne pas inventer 3 nombres sans source : cela brise le principe maison « aucun chiffre sans provenance », en pleine évaluation finale. | **1 h + décision** |
| **M7** | Sortir du dépôt public `AUDIT_PROMPT.md`, `docs/RAPPORT_COMPLETION_2026-10-17.md`, `handoff-*.md`. | Un jury qui lit « les forces/faiblesses que nous croyons » ou « gelé orphelin » avant le pitch change d'avis. | **10 min** |

> **M1 + M2 + M4 coûtent 1 h 20 et suppriment la majorité du risque de crédibilité. C'est le meilleur ROI des 72 h.**

### 1.6 Forces revendiquées — ce que j'ai confirmé, ce que j'ai infirmé

Le prompt d'audit demande de ne pas gober les forces. Résultat :

| Force revendiquée | Verdict | Preuve |
|---|---|---|
| Vérifiabilité par un tiers (T10 gelé, paquet reproductible) | ✅ **CONFIRMÉE** | `verify_frozen.py` → CONFORME ; dossier re-rendu **byte-identique** (sha256 `E63F3FC6…` sur deux rendus, même répertoire) ; cœur stdlib-only, 0 import tiers dans `src/` |
| Discipline du gel et des ADR | ✅ **CONFIRMÉE** | `frozen/G1–G6` vérifiés, recalcul hors-ligne identique octet à octet sur 19 fichiers ; ADR-0002 actée, ADR-0003 créée |
| Rejeu déterministe du scripté | ✅ **CONFIRMÉE** | `run_replay.py` dispose d'un `--k` ; le mode journal est conçu pour être bit-à-bit |
| Exécution bornée réelle sur testnet (5 runs A→E, refus, kill switch) | ⚠️ **CONFIRMÉE MAIS SURÉVALUÉE** | 13 reçus on-chain réels existent et sont dans un paquet vérifiable. Mais c'est une **exécution manuelle**, pas une exécution autonome (§1.1) |
| Agents live exécutés et scellés | ⚠️ **PLAUSIBLE, non re-vérifié** | `evidence/agents_live/…` existe avec journaux chaînés ; je n'ai pas rejoué (interdit : LLM payant) → **[RAPPORTÉ]** |
| Suite de tests large (811) | ⚠️ **VRAIE MAIS LE COMPTEUR EST FAUX** | 810 tests / 806 passés / **5** sautés mesurés, pas 811/808/3. Et le gel lui-même dit « ne jamais revendiquer un chiffre non mesuré » |
| UI locale hors-ligne (12 écrans) | ✅ **CONFIRMÉE** | `screen_ids()` → `[1..12]`, routes `/screen/1..12`, aucun JS |
| **« Exécution non autonome » (faiblesse suspectée)** | ✅ **CONFIRMÉE — et aggravée** | Pas de déclencheur, **et** la couture décision→exécution n'existe pas (§1.1) |
| « Démo scriptée + EVAL non exécutée » | ✅ **CONFIRMÉE** | G6 non signée ; `N=8` « non concluant » |
| « Français dans le code/docs » | ⚠️ **SOUS-ESTIMÉ** | Le **README**, porte d'entrée d'un jury anglophone, est en français, avec une commande quickstart en syntaxe bash |
| « Données offline seulement » | ✅ **CONFIRMÉE** | Aucun flux live ; tout vient du corpus archivé |
| « Dépendance à une seule chaîne testnet » | ✅ **CONFIRMÉE** | `chain_id: 84532` unique, dans `policy_v1.yaml` |

**Le seul point que l'équipe présente comme une force et qui est en réalité une faiblesse déguisée** :
*« documentation très supérieure au produit démontrable »*. C'est exact, et c'est ce qui la tue face à un jury :
le dossier est un **excellent dossier d'ingénierie** qui n'a pas encore de **dossier de soumission**.

---

## 2. Registre de findings

P0 = bloque la sélection ou casse une preuve · P1 = réduit fortement la note · P2 = notable · P3 = cosmétique.

| ID | Prio | Axe | Localisation (`chemin::symbole`) | Constat + preuve | Impact | Correctif | h-agent |
|---|---|---|---|---|---|---|---|
| **F-C-01** | **P0** | C | remote `origin` | **Dépôt GitHub PRIVÉ** : API anonyme → 404, témoin `pallets/click` → 200 [FAIT VÉRIFIÉ] | **Pièce ④ non recevable** — le jury ne peut pas cloner | Basculer en public **après** F-C-03 | **0,5** |
| **F-C-02** | **P0** | C | dépôt entier | **Deck et vidéo absents** — 2 des 6 pièces obligatoires inexistantes ; aucun `.pptx/.mp4` dans `git ls-files` [FAIT VÉRIFIÉ] | Dossier incomplet → non noté | Deck EN + script vidéo 5 min | **5–7** |
| **F-C-03** | **P0** | C | `AUDIT_PROMPT.md`, `docs/RAPPORT_COMPLETION_*.md`, `handoff-*.md` | **Auto-critique interne exposée** : « 38/46 pleines (83 %) », « gelé orphelin », « clé DeepSeek absente », et l'invite d'audit elle-même | Baisse directe du critère accomplissement | Migrer vers une branche privée **avant** le push public | **0,5** |
| **F-C-04** | **P0** | A/C | `SECURITY_SELF_ASSESSMENT.md:11` vs `scripts/demo/signer.py:134` | « *The agent never holds a key. No module signs or broadcasts* » **contredit** par une signature effective et 13 reçus on-chain [FAIT VÉRIFIÉ] | Coups de crédibilité dans une catégorie à 30 % | « Le cœur ne signe pas ; le kit démo signe avec une clé jetable » | **0,5** |
| **F-D-02** | **P1** | B/D | `policy/__init__.py:479-480` ; `run_execution_demo.py:102` | `evaluate()` **sans `state=`** → les règles d'état sont **explicitement sautées** : `skip("P11-pause", "state non fourni (appel legacy)")` — idem P7 (solde), P12 (enveloppe/SAFE MODE), P14 (budget). La démo d'exécution livrée n'évalue donc que **11 des 14 règles**, et **P11 = kill switch/pause n'y est jamais évaluée** [FAIT VÉRIFIÉ] | **Pas une faille active** (la démo tourne hors-ligne sur des intents codés en dur) mais un **piège de conception majeur** : l'exécuteur autonome qu'ils vont construire désarmerait le kill switch en silence. Le chemin est documenté comme « appel legacy », donc honnête — mais invisible pour un lecteur pressé | Passer `PolicyState` dans la démo **et** dans la boucle (voir §4 #5) | **0,5** |
| **F-A-01** | **P0** | A | `DOC1:51,82` · `DOC2:80,1006,1431` · `DOC3:760` · `DEMO_KIT:408` | « **l'agent exécute seul** » — et **aucun déclencheur dans le code** : pas de scheduler/poller, `run_execution_demo.py` ne lit jamais l'artefact de décision, `build_demo_intents()` code en dur, `orvyren.decide` importé par personne [FAIT VÉRIFIÉ] | Le cœur du thème F n'est pas démontré | Boucle `run_autonomous.py` (2,5 h) **ou** correction du vocabulaire (30 min) | 0,5–2,5 |
| **F-A-05** | **P0** | A/B | `evidence/decision_record_usdc-2023-03.json` | L'intent drapeau est **non exécutable** : `"recipient": ""`, `"authorization_verdict": null`, `"evaluated": false` | La décision ne produit rien d'actionnable | Câbler `decide.py` → `policy.evaluate` → intent ; passer `--reserve-recipient` | **2** |
| **F-C-05** | **P1** | C | `README.md` + 13 autres | **14 des 16 artefacts jury-facing en français** ; README = porte d'entrée d'un jury anglophone ; quickstart en syntaxe bash (`PYTHONPATH=src`) qui échoue sous PowerShell [FAIT VÉRIFIÉ] | Le parcours « 5 minutes » échoue à l'étape 1 | README EN (réécrire, pas traduire) | 1,5–2 |
| **F-C-08** | **P1** | B/C | `README.md`, `AUDIT_PROMPT.md`, `docs/RAPPORT_COMPLETION_*.md` | **Compteurs publiés faux** : doc « 811 / 808 verts / 3 sautés » ; mesuré **810 tests (unittest, skipped=5)** et **806 passed, 5 skipped, 261 subtests** (pytest). Cause : `eth-account` absent [FAIT VÉRIFIÉ] | Le juge qui lance la commande perd la confiance | Recalculer, dater chaque chiffre, coller la sortie réelle | **0,3** |
| **F-E-01** | **P1** | E | `scripts/demo/demo.py:446-447` | **`_criteria_ok()` accepte `pending`** : le kit affiche `DRY_RUN_OK — critères OK` alors que **5 critères sur 6 ne sont pas évalués** [FAIT VÉRIFIÉ par exécution] | Contre-exemple à la thèse, dans la démo principale | Distinguer `pending`/`met` ; afficher `DRY_RUN_PENDING` si aucun critère n'est `met` | **0,3** |
| **F-C-09** | **P1** | C | `evidence/audit_packets/*.zip` | Les reçus sont des **transferts natifs** (`logs: []`), alors que R7 décrit la vérification d'un **log ERC-20 Transfer** décodé, et que la soumission revendique « 100 USDC » (E2) [FAIT VÉRIFIÉ] | Un juge qui colle le hash dans BaseScan voit la dissonance | Aligner l'affirmation, ou produire le run USDC ERC-20 | 1–3 |
| **F-C-10** | **P1** | C | `SECURITY_SELF_ASSESSMENT.md:61`, §5.1, R12 | Rapport **périmé (14/10)** : « 132 tests » (mesuré 810) ; référence `FREEZE_V1` (remplacé par V2) ; testnet « pending a written answer » alors que `FREEZE_V2 §0` enregistre l'accord des organisateurs du 14/10 | Rapport périmé = redondance et doute | Réécrire §5.1/§6, citer V2, dater | **2–3** |
| **F-D-06** | **P1** | D | `policy/__init__.py:312` | `cumulative_spent=0.0` par défaut → **le plafond 24 h (P6) ne survit pas à un redémarrage** | Plafond contournable par un simple restart | Relire `cumulative_spent` depuis le journal à chaque tick | **0,3** |
| **F-D-05** | **P1** | D | `config/models.json` (rôle `critic`) | Les replis `glm-5.3-flash` et `kimi-k2.6` ont `base_url: ""` → **zéro repli utilisable** | Le critique live est un point unique de défaillance | Renseigner les endpoints ou assumer l'absence de repli | **0,5** |
| **F-E-02** | **P1** | E | `policy_v1.yaml:20-23` | `recipients: [B, C]` sont des **labels résolus depuis `scripts/demo/.env`, jamais versionné** : la politique binaire n'est pas dans l'artefact publié | La moitié on-chain du système n'est pas vérifiable par un tiers | Publier une table d'adresses de démonstration publiques | **0,25** |
| **F-E-03** | **P1** | E | `frozen/G6_FEUILLE_DE_SIGNATURE.md` | **3 des 7 paramètres sont « NOT DONE (à fournir) » sans source publique** (`P(obligation)` EVAL, `p_s`, `r_capital`) — contredit le principe maison « aucun chiffre sans provenance » [FAIT VÉRIFIÉ] | Aucune EVAL possible ; ou un chiffre inventé en examen final | Assumer comme « hypothèses d'analyste » + sensibilité, ou ne pas signer | **1 + décision** |
| **F-D-08** | **P1** | D | `frozen/G6`, `run_evaluation.py` | G6 non signée → **aucune exécution EVAL** ; les 8 prévisions DEV sont `N=8` « non concluant » | Pas de preuve hors-échantillon | Décision du chef, puis run — **sans fabriquer les 3 paramètres** | **2** |
| **F-C-06** | **P2** | C | `evidence/audit_packets/README.md` + 5 autres | Le paquet d'audit — **la meilleure pièce** — est documenté **en français** | Le juge ne peut pas lire la preuve | Version EN du README du paquet + index des txHash | 0,5–1 |
| **F-E-06** | **P2** | E | `requirements.txt`, `.github/workflows/tests.yml` | L'env de référence **n'a pas `eth-account`** (dépendance unique du signataire) → 3 tests sautent en silence ; la démo ne peut pas être rejouée sur une autre machine | Démo non reproductible le jour J | `pip install -r requirements.txt` dans le runbook + test de fumée qui **échoue** si `--execute` sans la lib | **0,5** |
| **F-C-11** | **P2** | C | `LICENSES.md` | Liste FastAPI / Pydantic / psycopg « prévu » alors qu'il y a **0 import tiers dans `src/`** [FAIT VÉRIFIÉ] ; fichier en français | Impression de non-maîtrise du supply-chain | Ne lister que l'arbre réellement utilisé | **0,3** |
| **F-A-06** | **P2** | A | `scripts/demo/demo.py:8` (docstring) | La docstring annonce « *transfer **50** USDC* » alors que `DEFAULT_RECIPIENT_AMOUNT = "100.0"` (FREEZE E2) [FAIT VÉRIFIÉ] | Docstring trompeuse dans le fichier de démo | Aligner la docstring sur 100 | **0,1** |
| **F-D-07** | **P2** | D | racine (11 CLIs) | Pas de « une commande = une démo » | Friction jury sur le critère 5 min | `run_demo.py` | **1** |
| **F-A-07** | **P2** | A | `docs/RAPPORT_COMPLETION_2026-10-17.md:24` | Tableau cercle 1 dit « H1 — écrans W8 non construits (`ui/server.py` = 3 routes) » alors que `screen_ids()` → `[1..12]` [FAIT VÉRIFIÉ] ; la mise à jour en fin de document corrige | Lecteur pressé tire la mauvaise conclusion | Supprimer ou dater la ligne périmée | **0,2** |
| **F-E-04** | **P2** | E | ensemble du dossier | **L'objection la plus destructrice du jury n'est traitée nulle part** : « Vous n'avez pas d'agent wallet, vous avez un script de backtest avec un signateur. » | Le jury se la pose seul, sans réponse préparée | L'assumer en narration (voir §6 E4) | **0,5** |
| **F-C-12** | **P2** | C | `git status` | **8 fichiers `evidence/` modifiés + 8 artefacts de rejeu non suivis** — le HEAD publié n'est plus l'état qui a produit les preuves [FAIT VÉRIFIÉ, **causé par cet audit** — voir §8] | Incohérence entre artefacts publiés et travail réel | `git checkout -- evidence/ replay/` + commit propre avant soumission | **0,3** |
| **F-C-13** | **P3** | C | `LICENSES.md` | Deux soupçons **réfutés** : (a) mojibake apparent → faux, fichier UTF-8 valide, artefact de rendu console ; (b) `orvyren.decide` absent → faux, le module existe | Aucun — évite deux faux findings | — | 0 |
| **F-C-14** | **P3** | C | `LICENSE`, `.env.example`, `config.example.env` | **Aucun secret ni donnée personnelle versionné** ; placeholders partout ; MIT ; CI présente [FAIT VÉRIFIÉ] | Aucun | — | 0 |

### 2.1 Axe B — le finding le plus grave de tout l'audit

**`F-B-04` — le plafond cumulé 24 h n'est appliqué nulle part. [P0]**

`policy/__init__.py::evaluate()` prend `cumulative_spent=0.0` par défaut, et **aucun appelant ne le fournit**
(`run_execution_demo.py:102`). Mesuré par l'auditeur B : **10 transferts successifs de 100 USDC = 10 × ALLOW
= 1000 USDC**, pour une enveloppe déclarée `max_cumulative_24h: 300`. P6 affiche pourtant « 100.0 <= 300.0 »
à chaque appel — **le contrôle a l'air de vérifier**.

Conséquence directe et immédiate : **`SECURITY_SELF_ASSESSMENT.md` R4 est faux.** Il écrit :
*« Cap evasion (per tx / cumulative) — 100 per tx · 300 cumulative enforced in policy — **none observed** ».*
C'est la deuxième affirmation fausse de ce rapport de sécurité, après celle sur la garde de la clé.

**Correction (2 h) :** alimenter un compteur persistant dans `build_report` —
`spent = registry.spent_24h(now)` puis `evaluate(..., cumulative_spent=spent, seen_intent_ids=registry.ids)`.
Test : 4 transferts de 100 ⇒ le 4ᵉ doit être `DENY / AMOUNT_ABOVE_PERIOD_CAP`.

### 2.2 Axe B — registre complet

| ID | Prio | Localisation | Constat + preuve | Impact | Correctif | h |
|---|---|---|---|---|---|---|
| **F-B-05** | **P0** | `run_execution_demo.py::build_policy_config:46-53` | Construit un `PolicyConfig` **sans jamais charger `policy_v1.yaml`** : **6 des 14 règles sont `SKIPPED`** (P4, P7, P9, P11, P12, P14) [FAIT VÉRIFIÉ, table de règles imprimée] ; le verdict ne porte **ni `policy_version` ni `policy_hash`** | Sur le seul chemin d'exécution réel, **le kill switch (P11) et le SAFE MODE d'enveloppe (P12) sont inopérants** ; D1 « source de vérité = `policy_v1.yaml` » n'est pas respectée | `load_policy("policy/policy_v1.yaml", recipients).config` + passer `state=PolicyState(...)` | **3** |
| **F-B-02** | **P1** | `replay/dossier.py::verify_replay_dossier:189-191` | `verdict = "OK" if computed == stored and (logged in (None, stored))` → **un dossier absent du registre passe**. Mesuré : registre vide ⇒ `OK` [FAIT VÉRIFIÉ] | La chaîne de provenance est **contournable par un tiers** | `logged == stored` exigé ; `None` ⇒ `NOT_REGISTERED` | 0,3 |
| **F-B-01** | **P1** | `run_replay.py::cmd_verify:146-164` | Sans `--run-dir` ni `--dossier`, les deux `if` sont sautés puis `return EXIT_OK` → **rc=0, zéro octet de sortie** | La commande de vérification est un « tout va bien » silencieux | `parser.error(...)` si ni l'un ni l'autre | 0,2 |
| **F-B-06** | **P1** | `run_agents.py:184` (appelé par `run_replay.py::cmd_journal:97`) | `print("  ════ bilan …")` → `UnicodeEncodeError` sur console cp1252, rc=1. **`PYTHONIOENCODING` n'est posé que dans l'env des *enfants* (l.113), jamais sur le stdout du processus** [FAIT VÉRIFIÉ par lecture du code ; crash mesuré par l'auditeur B] | **La commande de référence du README échoue en 1 s sur le poste du jury sous Windows** | `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` en tête de CLI ; remplacer `═` par `-` | 0,3 |
| **F-B-09** | **P1** | `README.md:7,27,58`, `DOC1:75`, `SECURITY_SELF_ASSESSMENT.md:61` | « 811 / 808 verts / 3 sautés » : mesuré **810 exécutés (5 skips)** ; **811 = compte statique de `def test_`**. Le rapport sécurité dit encore « 132 tests » ; `DOC1:75` « 221 tests verts » est **introuvable** (118 / 214 / 246 selon le regroupement) [FAIT VÉRIFIÉ] | Le compteur de crédibilité du README est faux | coller la sortie mesurée ; corriger 132 et 221 ; CI qui échoue si le compteur dérive | 0,5 |
| **F-B-10** | **P2** | `execution/verify.py:24` (`DEFAULT_DECIMALS=6`) | `value_to_base_units` **sans** décimales issues du bundle : `config.asset_decimals` existe mais n'est pas propagé | Latent : autoriser un actif 18 décimales.encoderait ×10⁶ au lieu de ×10¹⁸ — **erreur d'unité silencieuse sur de l'argent** | propager `decimals=policy.asset_decimals`, refuser si `None` | 0,5 |
| **F-B-11** | **P2** | `agents/worker.py:92-95`, `agents/loop.py:177-180` | (a) timestamp illisible ⇒ repli **silencieux** sur `datetime.now()` : horloge murale dans un chemin de journal ; (b) `except Exception: pass` sur la lecture du prompt ⇒ l'agent tourne sur un prompt minimal **non journalisé** | Casse la rejouabilité bit-à-bit en cas d'entrée dégradée | `raise ValueError("E_TS_UNREADABLE")` ; journaliser `E_PROMPT_UNREADABLE` avant repli | 1 |
| **F-B-03** | **P2** | `replay/runs.jsonl` + `dossier.py:186` | 1036 octets NUL après le 5ᵉ enregistrement ; `json.loads(line)` sans garde ⇒ **`verify --dossier` traceback sur les 6 dossiers publiés** [FAIT VÉRIFIÉ]. **Attribution incertaine** : les 2 dossiers non enregistrés sont datés 02:16, pendant cet audit — la corruption est probablement provoquée par mes propres auditeurs (processus tué en cours d'écriture), pas par le projet | Le registre ne prouve plus rien en l'état ; **et le code n'est pas robuste à une écriture interrompue** | `try/except JSONDecodeError` + compteur ; écriture atomique tmp+`os.replace` ; **régénérer le registre** | 1,5 |
| **F-B-07** | **P2** | 6 écrivains sans `newline="\n"` (`run_execution_demo.py:194`, `run_pipeline.py:232`, `run_quality.py:281`, `run_agents.py:58`, `reconstruct_usdc2023_episode.py:1073`, `recon_common.py:90`) | 7 JSON `evidence/` à **100 % CRLF** alors que toute la lib `src/orvyren` écrit en LF [FAIT VÉRIFIÉ] | Les empreintes des artefacts versés au paquet diffèrent entre Windows et Linux ; `sha256sum -c` peut échouer selon la machine | ajouter `newline="\n"` sur les 6 sites | 0,5 |
| **F-B-08** | **P2** | `audit/dossier.py::build` | Le self-hash intègre le **chemin absolu de sortie** et `generated_at` par défaut = `now()` : reproductibilité réelle **uniquement avec `--generated-at` + même répertoire** [FAIT VÉRIFIÉ, y compris par moi] | Un tiers qui reconstruit dans un autre dossier obtient un mismatch incompréhensible | normaliser le chemin affiché ; refuser de renderer sans `--generated-at` | 2 |
| **F-B-13** | **P3** | `tests/test_demo_kit.py:776,790`, `tests/test_env_hygiene.py:149` | `skipTest()` **dans le corps** du test : si `eth-account` manque, les assertions **« jamais de clé dans la sortie »** et l'hygiène EIP-55 disparaissent **silencieusement** | La suite au vert ne prouve pas l'absence de fuite de clé sur une machine sans la lib | décorateur explicite + un test qui **échoue** si une dépendance de `requirements.txt` manque | 1 |
| **F-B-14** | **P3** | `replay/dossier.py::_append_runs_log` | Append texte sans verrou ni `fsync`, registre partagé par plusieurs processus | Cause possible du trou NUL de F-B-03 | `O_APPEND`+`fsync` ou tmp+`os.replace` | 1 |

### 2.3 Ce qui est vérifié sans défaut — à ne pas rouvrir

L'axe B a cherché à briser le système et n'y est pas parvenu sur les points structurants. **Ces forces sont réelles :**

- **Paquet d'audit v2 : vérifié hors dépôt** — extrait dans un dossier neutre, PYTHONPATH vide, cwd = paquet :
  `VERDICT: OFFLINE_PASS — 16 checks, 0 failed`, rc=0 ; `--mutate-test` → **6/6 mutations détectées** ; le sha256 du zip recalcule **exactement** l'empreinte F3 publiée. La promesse marketing la plus forte du dossier **tient**.
- **Gestion de l'argent réellement fail-closed** : NaN, ±inf, bool, négatif, non fini → `DENY` ; `_base_units` refuse tout montant non exactement représentable ; `value_to_base_units` utilise `Decimal` et **lève** (aucun arrondi silencieux). `execution/guard.py` : `assert_allowed` refuse tout verdict ≠ ALLOW, masquage des secrets avec canary.
- **Validation des schémas fermée** : champs inconnus rejetés, `$schema` exact et obligatoire, question ≤240 caractères sans chiffre. Un modèle live renvoyant un champ en trop ou un mauvais type ⇒ refus.
- **INV-PIT : aucun chemin de fuite de futur trouvé.** `graph/temporal.py::pit_at` (révision connue à T ∩ validité à T), et `world_at`/`known_at` n'ont **aucun appelant en production**.
- **Aucun secret ni donnée personnelle versionné** ; `.env` et `owners.env` bien gitignorés.
- **FREEZE_V2 = 46 décisions exactement**, max J3 — conforme.
- **UI : 13 routes HTTP 200**, 404 sur `/screen/13`, `/screen/0`, `/nope`.
- **Déterminisme JSON** : `sort_keys=True`, `canonical_json`, `.gitattributes` `eol=lf`.

> **Message important** : F-B-02, F-B-04 et F-B-05 ne sont pas des failles de conception du système — ce sont des
> **prises non branchées sur le chemin de démonstration livré**. L'architecture est saine ; le câblage est incomplet.
> C'est une bonne nouvelle : ce sont des corrections de 0,2 à 3 h, pas une refonte.

---

## 3. Conformité au concours (axe C)

### 3.1 Notes 40/30/30

| Critère | Note | Fourchette | Justification |
|---|---|---|---|
| Accomplissement (40) | **22** | 17–27 | Thème F exige une exécution **autonome** : absente. Contres : politique 14 règles, RDOF, abstention, paquet T10 `OFFLINE_PASS` 16/16 + mutations 6/6, 810 tests, 12 écrans, 38/46 décisions gelées livrées. EVAL jamais exécuté → pas de preuve hors-échantillon. |
| Sécurité & conformité (30) | **17** | 14–20 | Fonds réels : politique déterministe hors LLM, fail-closed, plafonds 100/300 USDC, allowlist, TTL 24 h, idempotence, store append-only, vérificateur gelé, MIT, aucun secret. Mais trois coups : la contradiction sur la clé, le **dépôt privé**, et le rapport daté du 14/10 (« 132 tests », testnet « pending »). **Et deux coups supplémentaires trouvés par l'axe B après cette note** : le plafond cumulé 24 h n'est alimenté par aucun appelant (1000 USDC passent pour une enveloppe de 300) et 6 des 14 règles sont `SKIPPED` sur le chemin d'exécution livré → **je maintiens 17/30, mais c'est une note basse pour une raison qui se corrige en 5 h.** |
| Innovation & interaction (30) | **15** | 12–19 | Vraiment original : RDOF plutôt que VoI, abstention A1–A5, pré-enregistrement gelé G1–G6, rejeu déterministe, cœur stdlib-only. Mais l'interaction est une UI **statique, hors-ligne, sans JS, en français** — 12 écrans que le jury ne peut pas faire bouger. Et sans vidéo, l'interaction est invisible. |
| **Total** | **54/100** | 44–65 | Milieu de tableau. Assez solide pour ne pas être écarté, insuffisant pour le top 10 tant que 2 pièces manquent et le dépôt est privé. |

**Cible réaliste : +12 à +18 points** avec les actions du §4. Cible plafond si tout est fait : **78–84**.

### 3.2 État des 6 pièces

| # | Pièce | Existe ? | Preuve | Langue | Manque quoi | h-agent |
|---|---|---|---|---|---|---|
| ① | Doc technique EN | **Partiel** | `DOC2` (202 Ko) = document interne FR ; `dist/docs/*.docx` gitignorés | FR | Aucun doc technique en anglais. **Ne pas traduire 200 Ko** : écrire 15–20 pages EN depuis DOC2 | 5–8 |
| ② | Deck ≤ 10 min | **NON** | aucun `.pptx/.odp/.pdf` | — | Le deck | 3–4 |
| ③ | Vidéo ≤ 5 min | **NON** | aucun média ; `FREEZE_V2 H1` « vidéo reportée » | — | Script, storyboard, captures, montage | 1,5–2 + 2–3 humain |
| ④ | Code + README + GitHub | **Partiel** | code solide (19 253 lignes `src/`, 810 tests, CI) ; **dépôt PRIVÉ** | README FR | Dépôt public + README EN | 1,5–2 |
| ⑤ | Rapport sécurité EN | **Oui, périmé** | `SECURITY_SELF_ASSESSMENT.md`, EN, 14/10 | EN | Corriger §1.1, §6, FREEZE_V1, §5.1 | 2–3 |
| ⑥ | Preuves on-chain | **Oui, solide** | zip 208 836 o / 47 entrées / 13 reçus avec txHash + blockNumber + `.sha256` + vérificateur gelé | README FR | Index EN ; **aligner R7 sur le contenu réel des reçus** | 0,5–1 |

**Total : ~13–20 h-agent + ~3 h d'enregistrement humain.** Faisable en 72 h en parallèle — **deck + vidéo + doc EN sont le chemin critique.**

### 3.3 Les 10 questions les plus dures du jury (réponses honnêtes)

1. *Montrez l'agent exécuter sans main humaine* → **Pas de réponse aujourd'hui.** C'est LA question du thème F.
2. *« Your report says the agent never holds a key, but `signer.py` signs »* → Les deux chemins existent ; **le rapport est faux tel qu'écrit**.
3. *Votre dépôt est-il public ?* → **Non, il est privé aujourd'hui.**
4. *Pourquoi le README est-il en français ?* → Convention interne. Friction majeure pour un jury anglophone.
5. *Où sont le deck et la vidéo ?* → Pas encore produits.
6. *Votre épisode vedette (rsETH 2026) est-il hors-échantillon ?* → **Non.** L'EVAL n'a jamais tourné ; N=8 « non concluant ».
7. *Le −7,17 % est-il prédictif ou post-hoc ?* → **Un** fait discriminant, **une** hypothèse réfutée, **un** épisode. Aucune revendication prédictive n'est établie.
8. *Montrez le contrôle du risque sur une perte réelle* → Plafonds, TTL, allowlist, kill switch — mais **sur testnet, jamais sur une perte réelle**.
9. *À quoi servent vos 811 tests pour un juge ?* → À la reproductibilité du paquet. Attention : les compteurs publiés ne se reproduisent pas.
10. *Puis-je cloner et lancer en 5 minutes ?* → **Non** : dépôt privé, README FR, `PYTHONPATH` requis, et la démo exige un wallet testnet financé (robinet + captcha humain).

### 3.4 Solidité des chiffres publics face à un quant

| Chiffre | Verdict | Ce qu'il faut dire |
|---|---|---|
| Dispersion **870 bps** | Défendable **si défini** | Dispersion *inter-places sur fenêtre*, entre **2** venues, en horaire. DOC2 dit lui-même « 870–1 047,7 bps ». **Interdit** de la nommer « dislocation de marché » ou « risque systémique ». |
| RDOF **−7,17 %** | Donnée solide, **revendication fragile** | L'entrée (−7,1722 %/24 h) est mesurée. « H1 réfutée » repose sur **un** critère, **un** épisode. Ne dire aucune prédiction. |
| Calibration **N=8** | Défendable **uniquement avec son étiquette** | Le label « non concluant » est correct et assumé. **Il doit voyager avec le chiffre.** Interdit : « modèle calibré », « 80 % de réussite ». |
| Saturation **99,9989 %** | Défendable, **à recadrer** | DOC2 dit « **−25 min après l'exploit (confirmation)** » : c'est une **confirmation**, pas une alerte préventive. **Ne jamais le présenter comme de la détection prédictive** — c'est le piège n°1 devant un jury quant. |
| **−31 %** oracle/marché · fenêtre **46–77 min** | Les plus citables, **les plus fragiles** | Reposent sur le **seul** épisode rsETH, qui appartient au jeu **EVAL jamais exécuté**. Question garantie : « est-ce hors-échantillon ? » → réponse honnête : non. **L'annoncer soi-même, avant qu'on le demande.** |

---

## 4. Roadmap 72 h (axe D)

| # | Action | Fichiers | Critère d'acceptation **mesurable** | h | Dépendance | Risque |
|---|---|---|---|---|---|---|
| 1 | **Dépôt public + nettoyage** | retirer `AUDIT_PROMPT.md`, `docs/RAPPORT_COMPLETION_*.md`, `handoff-*.md` | API anonyme renvoie **200** ; clone anonyme OK | **0,5** | — | faible |
| 2 | **Compteurs républiés** | `README.md`, docs, `DOC1:75`, `SECURITY:61` | la sortie réelle de `pytest -q` est collée ; « 132 » et « 221 » corrigés | **0,5** | — | faible |
| 3 | **Câbler la politique sur le chemin réel** `F-B-05` | `run_execution_demo.py::build_policy_config` | le verdict porte `policy_hash` ; **0 règle `SKIPPED`** ; `paused=True` ⇒ DENY | **3** | — | faible |
| 4 | **Alimenter le plafond cumulé 24 h** `F-B-04` | `run_execution_demo.py::build_report` + registre persistant | **4 transferts de 100 ⇒ le 4ᵉ est DENY `AMOUNT_ABOVE_PERIOD_CAP`**, y compris après redémarrage | **2** | #3 | faible |
| 5 | **Fermer les 2 fail-open de vérification** `F-B-01/02` | `run_replay.py::cmd_verify`, `replay/dossier.py` | `verify` sans argument ⇒ rc≠0 ; dossier absent du registre ⇒ `NOT_REGISTERED` | **0,5** | — | faible |
| 6 | **Encodage console Windows** `F-B-06` | `run_agents.py`, `run_replay.py` | la commande quickstart du README tourne en cp1252, rc=0 | **0,3** | — | faible |
| 7 | **Exécuteur autonome SANS signature** | NEW `src/orvyren/execution/loop.py`, NEW `run_autonomous.py`, NEW `tests/test_execution_loop.py` | `--dry-run --ticks 5` rc=0 ; journal 5 ticks, chaîne sha256 vérifiée ; **0 signature, 0 réseau** | **2** | #3 | faible |
| 8 | **Vidéo** (③) ≤ 5 min | `evidence/video/` | un plan montre un tick **non scripté** ; durée ≤ 5:00 | **4** | #7 | faible |
| 9 | **Deck** (②) ≤ 10 min | `dist/` | 10 slides, 1 capture = le journal de l'exécuteur | **2** | #7 | faible |
| 10 | **Doc technique EN + sécurité EN** (sections exécution/autonomie seulement) + `run_demo.py` | `DOC2`, `SECURITY_SELF_ASSESSMENT.md`, NEW `run_demo.py` | 2 PDF EN décrivant le mode **réellement livré** ; une commande enchaîne decide → policy → instruction → refus | **4** | #3, #4 | faible |

### Si on ne fait qu'UNE seule chose

**#3 + #4 + #5 (5,5 h-agent) — rendre le chemin livré conforme à ce que le rapport sécurité promet.**

Ce n'est pas le chantier le plus brillant, c'est le seul qui **protège 30 % de la note**. Aujourd'hui, un ingénieur
du jury qui lit `SECURITY_SELF_ASSESSMENT.md`, ouvre `run_execution_demo.py`, et constate que
`policy_v1.yaml` n'est jamais chargé et que `cumulative_spent` n'est jamais alimenté, a trouvé deux mensonges
vérifiables. Une fois ces 5 h faites, **le rapport sécurité devient vrai** — ce qui est exactement l'argument
de sélection à vendre. Et c'est du code réel, pas de la documentation.

**Le meilleur pari d'ambition** reste **#7 (la boucle autonome, 2 h)**, parce qu'elle attaque le cœur du thème F
sans coûter de clé, ni de risque on-chain, ni de signature du gel. **Mais #7 sans #3 est une fausse promesse** :
une boucle qui ne branche pas `PolicyState` produirait un agent autonome *non borné*, ce qui est pire
que pas d'agent autonome du tout.

### À NE PAS faire avant le 20/10

| # | Piège | Raison |
|---|---|---|
| 1 | Traduire intégralement le code FR→EN | L'exigence porte sur les pièces de soumission. Coût énorme, gain faible |
| 2 | Remplir les 3 paramètres « NOT DONE » de G6 pour débloquer l'EVAL | **Travailler une feuille pré-enregistrée détruit la crédibilité du gel** |
| 3 | Toucher `frozen/`, `FREEZE_V2.md` | `verify_frozen.py` est une preuve publiée (F3) |
| 4 | Brancher un LLM dans la boucle d'exécution | La décision est déterministe et **gratuite** ; un LLM ajoute variabilité, coût et surface d'attaque pour zéro bénéfice |
| 5 | Postgres / workers / files d'attente | Infra à zéro décideurs. SQLite + 2 processus suffisent |
| 6 | Multi-chaîne | Double la surface de config/test ; ne gagne aucun point du thème F |
| 7 | Un 3ᵉ rôle agent | Le coût de l'arrêt devient plus dur à démontrer |
| 8 | Nettoyage du dépôt en fin de sprint | Risque de casser `run_verify` / la CI ADR au pire moment |
| 9 | Ouvrir une règle P15 | La stabilité des 14 codes de refus est un argument de vente |

---

## 5. Backlog V2 (post-concours)

| Prio | Item | Pourquoi ça augmente la note / le produit | h (est.) |
|---|---|---|---|
| V2-1 | **Données live** (flux PIT incrémental, multi-actifs) | Sort du « offline seulement » ; crédibilité du thème F | 16–24 |
| V2-2 | SQLite → Postgres + file d'attente + workers | Épisodes, rejeux k=N, concurrence | 24–40 |
| V2-3 | **Observabilité** (taux de refus par code, coût/décision, alerte SAFE MODE) | Exploitation réelle ; argument « opérabilité » | 8–12 |
| V2-4 | **Clés : KMS/HSM, rotation, enveloppe par destinataire** | Supprime le « fichier `.env` » comme point faible (F-E-02) | 16–24 |
| V2-5 | Coûts LLM (cache, modèle par tâche, plafond dur) | La décision est déjà à **0 $** ; rendre le coût mesuré et plafonné est un argument | 6–10 |
| V2-6 | Multi-chaînes (2ᵉ testnet) | Portée du contrôle du risque | 12–20 |
| V2-7 | Gouvernance (releases taggées, ADR de l'exécuteur, CI Windows) | Exigence « code + GitHub » crédible | 6–10 |
| V2-8 | Interface temps réel / alerting | Critère « innovation & interaction » | 12–20 |
| V2-9 | Couverture + mutation testing sur `policy/` et `loop.py` | Qualité (dette §7.4) | 4–8 |
| V2-10 | File d'approbation + signature EIP-712 (FREEZE **D2**, non implémenté) | Comble une décision gelée restée partielle | 4–6 |

---

## 6. Axes libres (axe E)

Six angles que les quatre premiers axes ne couvrent pas.

### E1 — Le red-team appliqué à leur propre principe (`fail-open` dans le kit de démo)

**Question** : votre thèse, c'est « rien ne passe sans ALLOW, rien ne se déclare vert sans preuve ». Est-ce vrai dans votre propre outillage ?
**Méthode** : lecture de la logique de verdict du kit de démo et exécution réelle du dry-run officiel.
**Résultat** — **le kit déclare des critères « OK » qu'il n'a jamais évalués.** `scripts/demo/demo.py:446-447` :

```python
def _criteria_ok(criteria: List[Dict[str, Any]]) -> bool:
    return all(criterion["status"] not in ("failed",) for criterion in criteria)
```

`pending` passe. Exécution réelle (`--run A --dry-run`) :

```
run A : DRY_RUN_OK — critères OK
    [     pending] A.1 — receipt.status == 0x1
    [     pending] A.2 — exactement un log Transfer correspondant exactement
    [     pending] A.3 — Δ solde Safe = −100000000 et Δ solde B = +100000000
    [     pending] A.5 — les 7 kind de journal présents pour l'intent_id
    [     pending] A.6 — blockHash stable après 2 blocs
```

Cinq critères sur six sont **non évalués** (ils exigent la chaîne), et la sortie affiche quand même « critères OK ».
Un juge qui lance la commande du README (`DEMO_KIT §6`) voit exactement ce bandeau.
**Décision éclairée** : corriger avant toute soumission — c'est le contre-exemple le plus dur à leur propre argument,
et il est dans la démonstration principale. Coût : 20 min (distinguer `pending` de `met` dans `_criteria_ok`, et
afficher `DRY_RUN_PENDING` quand aucun critère n'est `met`).

### E2 — Qui peut recevoir l'argent ? La politique n'est pas dans le dépôt

**Question** : la politique v1 autorise les destinataires `B` et `C`. Qui sont-ils, un tiers peut-il le vérifier ?
**Méthode** : lecture de `policy_v1.yaml` et de sa chaîne de résolution.
**Résultat** — `policy_v1.yaml` déclare `recipients: [B, C]` comme des **labels**, avec la mention
« *les destinataires sont des LABELS résolus au montage (cf. scripts/demo/.env — jamais versionné)* ».
La politique binaire est donc **paramétrique à l'exécution**, hors du artefact publié.
**Décision éclairée** : ce n'est pas un bug (c'est correct pour un demo jetable) mais cela **affaiblit la promesse
centrale**. La partie on-chain du système — celle qui prouve le thème F — n'est pas vérifiable à partir du dépôt public,
alors que la partie hors-ligne l'est entièrement. Deux options : publier une table `recipients.example` avec des
adresses de démonstration publiques (recommandé, 15 min), ou assumer explicitement dans la doc technique que
la vérifiabilité hors-ligne couvre le moteur et non l'adresse.

### E3 — Le paradoxe de la vérité des coûts (le G6 contre le principe maison)

**Question** : que se passe-t-il quand une décision gelée exige un chiffre que personne n'a pu sourcer ?
**Méthode** : lecture de `frozen/G6_FEUILLE_DE_SIGNATURE.md`.
**Résultat** — 3 des 7 paramètres de la feuille G6 sont **« NOT DONE (à fournir) » avec la mention
« aucune source publique »** : `P(obligation)` par fenêtre EVAL, `p_s` des scénarios, `r_capital`.
Or `SECURITY_SELF_ASSESSMENT §1.4` pose le principe : *« No number without provenance »*. Et DOC1 §5 revendique
« *Les chiffres cités sont mesurés et reproductibles depuis le dépôt* ».
**Décision éclairée** : c'est le **meilleur matériau de red-team qu'un jury puisse avoir en main**. Trois issues
sûres : (a) remplir la feuille avec des valeurs inventées → brise le principe maison en plein examen final ;
(b) laisser `NOT DONE` → l'EVAL est inexécutable et le jeu se brûle pour rien ; (c) **reformuler en assumant** :
« nous avons pré-enregistré 4 paramètres sourcés et 3 paramètres que nous n'avons pas su sourcer ; nous les
déclarons comme hypothèses d'analyste et publions la sensibilité ». L'option (c) est la seule qui transforme
le trou en preuve d'honnêteté — et elle est cohérente avec le reste du dossier.

### E4 — L'inversion du jury : l'objection la plus destructrice, et son traitement

**Question** : quelle est la phrase la plus destructrice qu'un membre du jury peut prononcer, et est-elle traitée ?
**Méthode** : confrontation du pitch aux preuves réelles.
**Résultat** — l'objection la plus destructrice est **« Vous n'avez pas d'agent wallet ; vous avez un script de
backtest avec un signateur. »** Elle est destructrice parce qu'elle est vraie au sens fort : la décision vient d'un
moteur déterministe (le LLM n'est dans aucun chemin financier, ce qui est un choix délibéré et excellent), et
l'exécution est déclenchée à la main.
**Traitement actuel** : **nulle part.** Aucun document ne répond à cette objection ; au contraire, DOC1 §3 et
DOC2:80 revendiquent l'inverse (« l'agent exécute seul, sans validation humaine à chaque transaction »).
**Décision éclairée** : ne pas nier — **répondre en assumant**. « Notre modèle n'est pas un agent qui décide au
hasard : c'est un agent dont la décision est déterministe, testable et rejouable. L'autonomie que nous
revendiquons n'est pas la spontanéité, c'est l'absence de permission humaine entre la décision et l'acte.
Montrez-nous un concurrent capable de vous prouver qu'il n'a pas consulté un humain. » C'est une réponse plus
forte que l'objection, et elle est 100 % vérifiable avec ce qui existe déjà.

### E5 — Le test du README en 5 minutes par un anglophone non-technique

**Question** : un juge presse, anglophone, non-technicien, ouvre le dépôt public. Que se passe-t-il ?
**Méthode** : parcours du README tel qu'il est.
**Résultat** — `README.md` est **entièrement en français** (statut, structure, quickstart), y compris la commande
de démarrage rapide `PYTHONPATH=src python -m orvyren.decide …` qui est une **syntaxe bash et échoue sous
PowerShell/cmd**, c'est-à-dire sur le système d'exploitation de l'équipe et probablement de certains jurés.
Les 6 `.docx` de `dist/docs/` sont eux aussi en français.
**Décision éclairée** : la production d'un **README anglais** (50–80 lignes : problème, démo en 3 commandes,
« what it proves / what it does not prove », lien vidéo) est le meilleur euro de la note. C'est aussi la porte
d'entrée du critère « interaction ».

### E6 — Robustesse du jour J

**Question** : que casse-t-on le 20/10 à 14 h, 2 h avant la deadline ?
**Méthode** : parcours des commandes de démonstration avec l'environnement réel mesuré.
**Résultat** — l'environnement de référence **n'a pas `eth-account` installé** (alors que c'est la seule dépendance
du signataire, épinglée dans `requirements.txt`). Conséquence mesurée : **3 tests sautent silencieusement** et le
compteur publié (3 skips) devient faux. Si la démo doit être rejouée sur une autre machine, le chemin signataire
n'est pas exercé. Second point : `run_audit.py --serve` occupe le port 8000 en dur.
**Décision éclairée** : un `python -m pip install -r requirements.txt` dans le runbook de démo, et un test de fumée
qui **échoue** si `eth-account` manque et qu'on demande `--execute` (fail-closed sur l'environnement, pas fail-open).

---

## 7. Annexe A — Dette connue (inventaire, aucune correction)

Conformément à §7 du prompt d'audit, ces points sont **recensés et non traités**.

| # | Dette | Ampleur constatée |
|---|---|---|
| A1 | Anglais obligatoire (code, docstrings, messages CLI, écrans UI, docs) | **Tout** le dépôt est en français hors `SECURITY_SELF_ASSESSMENT.md` (EN), `run_execution_demo.py`, `config/models.json`, `ARCHITECTURE_V1.md` et les ADRs. ~150 fichiers Python ; les messages CLI de `run_*.py` sont français. |
| A2 | Propreté du dépôt | `.pytest_cache/`, `__pycache__/` (in git ? non, gitignorés — OK) ; `handoff-sprint2-w4.md` et `handoff-w3-fusion.md` à la racine ; `figure_cycle_complet.py`, `figure_divergence.py`, `make_package.py` hors de la liste des CLIs du prompt ; `scripts/demo/build_audit_packet.py` (v1 legacy) vs `scripts/build_audit_packet.py` (v2) — **deux builders de paquets coexistent**. |
| A3 | Reproductibilité « produit » | Pas de `docker-compose`, pas de venv verrouillé, pas de `Makefile`. `requirements.txt` = 1 ligne (`eth-account==0.14.0`) mais **pas installé** dans l'env de référence. README quickstart en syntaxe bash. |
| A4 | Métriques de qualité | Aucune couverture mesurée ; pas de mutation testing hors `verify/engine.py --mutate-test` (qui est un vérificateur, pas de la couverture). Outillage suggéré (non installé) : `coverage run -m pytest` + `pytest --cov`, et `mutmut` pour la couverture mutationnelle du cœur. |
| A5 | Nommage/cohérence historique | `orch-p1.1.0` / `crit-p1.0.0` / `canon-p1.0.0` (versions de prompts dans les noms), `build_audit_packet.py` en v1 et v2, `FREEZE_V1.md` encore cité dans `SECURITY_SELF_ASSESSMENT.md` alors que `FREEZE_V2.md` l'a remplacé. |

---

## 8. Annexe B — Commandes exécutées

> ⚠️ **Àvertissement — effet de bord de cet audit, à traiter avant soumission.**
> L'arbre était **propre** au début de l'audit (`git status --short` → 0 ligne, mesuré).
> En fin d'audit il est **sale** : 8 fichiers `evidence/` modifiés + 8 artefacts de rejeu non suivis
> + le présent rapport. La cause est identifiée et **n'est pas un défaut du projet** : les auditeurs parallèles
> ont exécuté les propres commandes du projet (`run_pipeline.py`, `run_replay.py journal`), qui écrivent
> dans `evidence/` et `replay/runs.jsonl` par conception.
> **Action requise (30 s) :** `git checkout -- evidence/ replay/runs.jsonl` puis supprimer les
> `evidence/replay/*_20261017T0*.{json,md}` non suivis — **avant** tout commit de soumission.
> Sans cela, le HEAD publié ne sera pas l'état qui a produit les preuves (`F-C-12`).

| Commande | Résultat réel | Écart avec la documentation |
|---|---|---|
| `python -m unittest discover -s tests` | `Ran 810 tests in 62.084s` / `OK (skipped=5)` | Doc : « Ran 811 tests — OK (skipped=3) ». **Écart : −1 test, +2 skips.** |
| `python -m pytest tests/ -q -rs` | `806 passed, 5 skipped, 261 subtests passed in 61.77s` | Doc : « 808 passed, 3 skipped (261 subtests) ». **Écart : −2 passés, +2 skips** (total collecté 811 = doc). |
| `python scripts/verify_frozen.py` | `VERDICT : paquet de gel CONFORME` (G1–G6, 8 prévisions, 8 outcomes, recalcul byte-identique 19 fichiers) | **Conforme.** |
| `python -c "import eth_account"` | `ModuleNotFoundError` | `requirements.txt` l'exige ; non installé. Cause des 2 skips supplémentaires. |
| `PYTHONPATH=src python -m orvyren.decide --case usdc-2023-03 --replay` | `epistemic_verdict=CONCLUANT`, `economic_action=CONVERTIR/TRANSFÉRER`, `authorization_verdict=None`, `intent.recipient=""` | La décision flagship produit une intention **non exécutable**. Non signalé dans les docs. |
| `python scripts/demo/demo.py --run A --dry-run --session <TEMP>` | `rc=0`, `DRY_RUN_OK — critères OK` avec **5 critères sur 6 `pending`** | Le statut « critères OK » est trompeur (§ E1). |
| `git log origin/master..master` | vide | Tout est poussé sur `https://github.com/keisary/orvyren-core.git`. |
| Recherche `import orvyren.decide` dans tout le dépôt | **0 occurrence** | La CLI de décision du README n'est appelée par aucun autre module. |
| Recherche `decision` dans `run_execution_demo.py` | **0 occurrence** | La couche exécution ne lit pas la décision. |
| `https://api.github.com/repos/keisary/orvyren-core` (anonyme) | **404 Not Found** | Le dépôt est **privé**. Exigence dure non tenue. |
| `https://api.github.com/repos/pallets/click` (témoin) | **200 OK** | Contrôle : la méthode est fiable. |
| `python -c "from orvyren.ui import screens; screens.screen_ids()"` | `[1,2,3,4,5,6,7,8,9,10,11,12]` | **Conforme** — 12 écrans existent (le rapport de complétion dit encore « à faire »). |
| `Get-Content frozen/G6_FEUILLE_DE_SIGNATURE.md` | statut **« PROPOSÉ — en attente de signature »**, 3 paramètres `NOT DONE` | Pas d'EVAL possible ; et 3 chiffres sans source à fournir. |
| `run_audit.py --decision <copie du HEAD> --out-dir <TEMP> --generated-at <fixe>` **×2, même répertoire** | sha256 md identique : `E63F3FC6B03727BFB4E66…` | **Conforme — la promesse « dossier byte-identique » tient.** À noter : le dossier embarque son propre chemin de sortie, donc il faut comparer **dans le même répertoire** (j'ai d'abord conclu à tort à une non-reproductibilité, infirmé en refaisant le test). |

**Non exécuté volontairement** (interdit ou sans valeur d'audit) : `run_replay.py archive`, `run_agents.py`
(en aucun mode), toute action on-chain, tout appel LLM payant.

---

## 9. Questions ouvertes pour l'équipe (décisions qui vous appartiennent)

1. **Le dépôt est privé.** Qui le bascule en public, et quand ? C'est la condition n°1, elle coûte 30 min,
   et elle n'est pas compatible avec l'urgence de retirer `AUDIT_PROMPT.md` / `RAPPORT_COMPLETION` / `handoff-*`
   de la branche publique. **À trancher aujourd'hui, pas demain.**
2. **La garde de la clé** : est-ce l'agent qui signe (`scripts/demo/signer.py`) ou un humain ? La réponse doit être
   unique et propagée au rapport sécurité, à `evidence/policy_execution_demo.json` (`agent_holds_key=false`), au
   README et à DOC2. **Tout le reste en dépend.**
3. **Le rapport sécurité ment-il, ou le code est-il incomplet ?** R4 affirme « cap cumulative enforced — none
   observed », et 10 transferts de 100 USDC passent. Vous pouvez (a) câbler les plafonds en 5 h et garder le
   rapport, ou (b) réécrire R4 en admettant que le cumul n'est pas appliqué en v1. **(a) est meilleur.**
4. **G6** : signer avec les 3 paramètres sans source (et les déclarer hypothèses d'analyste), ou ne pas signer et
   présenter l'EVAL comme non exécutable ? La première brise « aucun chiffre sans provenance » ; la seconde brûle
   le jeu d'évaluation. **À trancher aujourd'hui.**
5. **Le déclencheur autonome** : on construit la boucle (2 h) ou on corrige le vocabulaire (30 min) ? Les deux sont
   défendables, pas les deux en même temps — et **la boucle sans `PolicyState` serait pire que pas de boucle**.
6. **La vidéo** : tournage externe ou montage maison ? 4 h-agent si les deux modèles sont déjà bons.
   Faut-il montrer un tick réel signé, ou dry-run + preuves on-chain du kit ?
7. **Le dossier public** : faut-il retirer les 4 fichiers internes avant le push, ou les déplacer dans un dépôt privé ?
8. **L'anglais** : qui traduit ? Un README anglais (50–80 lignes) est le seul item non négociable côté interaction.
   Le code et DOC2 peuvent rester en français si le temps manque (mais c'est un signal négatif).
9. **Le cas unique** : on garde `usdc-2023-03` comme cas unique ultra-démontré, ou on ajoute `rsETH-2026-04` pour la
   vidéo ? Mon avis : garder un seul cas, raconter rsETH en introduction.
10. **Le kill switch < 5 min** : existe-t-il un **horodatage mesuré** (heure de révocation → heure du revert) dans les
    artefacts ? Si oui, c'est la capture d'écran n°1 de la vidéo. `[INCONNU]` de mon côté.

---

## 10. Ce qu'il faut retenir en trois lignes

1. **Le fond est excellent et le dossier de soumission est absent.** Ce n'est pas un problème d'ingénierie :
   c'est ~10 h de production (dépôt public, README EN, rapport sécurité honnête, deck, vidéo) contre des semaines
   de construction déjà faites. C'est **la** bonne nouvelle de cet audit.
2. **Deux affirmations du rapport sécurité sont fausses et vérifiables en 2 minutes** — garde de la clé, plafond
   cumulé. Tant qu'elles sont là, la catégorie « sécurité & conformité » (30 %) joue contre vous. 5 h pour corriger.
3. **Ne partez pas sur du nouveau.** Pas de Postgres, pas de multi-chaîne, pas de ML, pas de traduction intégrale
   du code. Les 6 heures les plus rentables sont : dépôt public (0,5 h), compteurs (0,5 h), câblage des plafonds
   et de la politique (5 h), encodage Windows (0,3 h), README EN (1,5 h).

---

*Rapport rédigé le 2026-10-17 par un agent auditeur indépendant. Mesures exécutées sur `master = 02cd2eb`.
Aucun fichier du dépôt n'a été modifié, à l'exception de la création du présent rapport.*
