# B8+B9 — INTERFACE & OPÉRATIONS · GOUVERNANCE DE SPÉCIFICATION — ÉTUDE

**15 octobre 2026** · Statut global : **PROPOSITION** (à trancher en revue d'équipe ; alimente le gel v2). Ce document couvre les blocs §8 (INTERFACE & OPÉRATIONS) et §9 (GOUVERNANCE DE SPÉCIFICATION) de `research/SYSTEME_ZONES_OMBRE.md`, et prépare les **4 documents finaux** (écrits après le gel).

**Sources internes lues** : `SYSTEME_ZONES_OMBRE.md` §8-9 · `ARCHITECTURE_V1.md` §5-6 · `src/orvyren/ui/server.py` (page audit v0, 250 lignes) · `research/B1_AGENTS_ETUDE.md` §6 (9 écrans + modes REPLAY) · `research/W2C_enveloppe_execution.md` §(d) et §(g) (signer, kill switch, journal, 5 runs) · `dist/docs/ORVYREN_EXPLIQUE_SIMPLEMENT.md` Partie 5 (méthode de révision) · `research/DECISIONS_ET_PROCHAINES_ETAPES.md` (D1-D9, notamment D3 « ORVYREN autonome » et D9 langues) · `research/B2_GRAPHE_ETUDE.md` §1.3/§2.3/§5.3 (horloges, Neon/Render, DL/ML) · `research/AXES_AMELIORATION_FULGURANTE.md` §1 (socle à redéfinir) · `FREEZE_V1.md` (à remplacer) · `.github/workflows/tests.yml` (CI existante).
**Sources web** : pratiques ADR/decision logs/RFC — 8 sources datées en §6, matière brute dans `research/raw_b89/`.

Convention de statuts : **[FAIT SOURCÉ]/[FAIT — code]** = constaté · **[DIRECTION]** = déjà pré-décidé (AV1/W2-C/DPE) · **[PROPOSITION]** = proposé ici, à trancher · **[NON TROUVÉ]** = cherché, pas trouvé.

Décompte : soumission **20/10/2026 15:59 UTC** (5 jours). Cette étude ne bloque pas la soumission ; elle prépare le **processus de gel** et la **spécification UI/ops**.

---

# PARTIE A — INTERFACE & OPÉRATIONS

## 1. Écrans de démo (minimal)

### 1.1 Contraintes (actées, à respecter par tout écran)

| # | Contrainte | Mise en œuvre | Réf. |
|---|---|---|---|
| C1 | **Rendu déterministe pour la vidéo** | Mode **REPLAY-JOURNAL** bit-à-bit (aucun appel réseau, séquence rejouée depuis `agent_journal` + magasin de réponses hashées) ; textes et chiffres figés dans la capture ; si un écran exige du live, il est tourné à part et étiqueté. | B1 §6.2-6.3 : « rejouer les réponses enregistrées est déterministe par construction — c'est le seul mode qu'on peut garantir devant un jury » |
| C2 | **Mode hors-ligne** | Tout tourne sans réseau : corpus archivé (`corpus/`, 520 observations), SQLite, `--replay` partout (déjà : README « Replay is offline by design ») ; seuls les écrans chaîne (10-12) exigent le RPC Base Sepolia — adresses et reçus sont **capturés d'avance** pour la vidéo. | AV1 §5 « Démo hors-ligne » ; F20-D8 |
| C3 | **Marquage REPLAY** | Bandeau permanent en haut de chaque écran + étiquette par écran : `REPLAY (journal, 2023-03)` / `REPLAY (live, données archivées)` / `LIVE` — et l'horloge **simulée** affichée (as_of). Jamais un écran replay présenté comme du direct. | B1 §6.3 (libellés adoptés tels quels) |
| C4 | **Rendu sans dépendance** | HTML statique autonome (le dossier existe déjà en `.md` + `.html` autonome, `evidence/dossier_usdc-2023-03.html`) ; pas de JS requis : la vidéo montre des pages servies par `run_audit.py --serve` ou ouvertes en fichier. | [FAIT — code] `src/orvyren/ui/server.py` (« no third-party dependency, no external asset, no JavaScript ») |

### 1.2 La séquence d'écrans (9 écrans B1 + 3 écrans chaîne)

Les **écrans 1-9** sont la timeline de démo de `B1 §6.4` (reprise à l'identique, seule la colonne « mode » est ajoutée). Les **écrans 10-12** intègrent le plan de démo testnet de `W2C §(g)` — ils couvrent « rejets par la chaîne » et « journal d'audit » demandés par la carte §8.1.

| Écran | Nom | Contenu affiché | Preuve à l'écran | Mode |
|---|---|---|---|---|
| 1 | **Fenêtre & PIT** | 520 observations archivées, couverture par heure/venue, `as_of` (horloge simulée) | manifeste du corpus (`corpus/manifest.json`) | REPLAY-JOURNAL |
| 2 | **Graphe** | sources → observations → claims → relations ; **contradictions affichées** (prix oracle vs réalisable) | requête `graph_query(as_of)` | REPLAY-JOURNAL |
| 3 | **Branches en évolution** | H1/H2/H3 avec timeline d'états `CREATED → EXPLORING → WEAKENED → REFUTED` / `SUPPORTED`, chaque transition datée et référencée (états initiaux et critères de réfutation **pré-enregistrés**) | `agent_journal` filtré `kind ∈ {BRANCH_UPDATE, REFLECTION}` + table `branches` | REPLAY-JOURNAL |
| 4 | **Timeline des réflexions agents** | deux colonnes (explorateur / critique) qui avancent étape par étape ; l'**objection** qui a déclenché la recherche suivante est visible | `agent_journal` filtré par `agent_id` | REPLAY-JOURNAL |
| 5 | **Recherche & coût** | tâche choisie, motif, `cout_reel`, `non_recherche[]` (ce qu'on a décidé de NE PAS chercher) | `research_task` + journal | REPLAY-JOURNAL |
| 6 | **Dossier de décision** | action candidate + rationale **recalculée** (les chiffres viennent du moteur, pas du LLM) ; page dossier 1 page | `evidence/decision_usdc-2023-03.json` + `dossier_usdc-2023-03.md/.html` | REPLAY-JOURNAL |
| 7 | **Refus par la politique** | ALLOW / DENY / REQUIRE_APPROVAL avec règles violées (`cap_tx_100`, `dest_in_allowlist`…) ; compteur de signatures = 0 | `policy_decision` + `policy_execution_demo.json` | REPLAY-JOURNAL |
| 8 | **Refus & quarantaine** | lignes `REJECTED`/`QUARANTINED` du journal : la mémoire interne n'a pas contaminé le graphe ; au moins un DENY + un test d'injection (6 cas anti-injection de B1 §5.6) | journal + banc de tests | REPLAY-JOURNAL (fixtures) |
| 9 | **Coût par décision** | appels, tokens, latence, USD par rôle — table de prix **datée** | journal + table de prix B1 §2 [MESURÉ : < 0,10 USD le replay complet] | REPLAY-JOURNAL |
| 10 | **Chaîne — RUN A (ALLOW, deux verrous)** | intention 50 USDC → politique ALLOW → simulation `eth_call` OK → tx signée → reçu `status 0x1` ; vérifications : log `Transfer`, `balanceOf` avant/après, allowance consommée | `audit.jsonl` + `eth_getTransactionReceipt` + onglet Permissions de l'app Roles | LIVE (capturé ; étiquette `LIVE`) |
| 11 | **Chaîne — rejets par la chaîne (RUN C)** | C1 `AllowanceExceeded`, C2 destinataire non listé, C3 admin refusé `onlyOwner`/`GS*`, C4 4ᵉ tx > cumul → **statuts `0x0`** affichés ; frontière de période : 2 tx chaîne acceptées vs compteur glissant hors-chaîne `DENY{rolling_24h_300}` | statuts de reçus + sélecteurs de revert + soldes inchangés | LIVE (capturé) |
| 12 | **Journal d'audit & kill switch (RUN E)** | `audit.jsonl` chaîné par hash exporté + vérification indépendante (un script relit les `tx_hash`, recalcule les transferts, compare à l'intention) ; K1 chronométré (`assignRoles(false)`, ~1,64 s/bloc Base, latence réelle = coordination humaine) | journal exportable + reçus + diff de politique Roles | LIVE (capturé) |

**Minimum non négociable pour la vidéo ≤ 5 min** : écrans 1, 3, 4, 6, 7, 8 (le cœur « décision vérifiable + refus ») **+ au moins l'écran 12** (journal d'audit = la promesse produit). Les écrans 10-11 exigent le wallet testnet financé = **chemin critique** (pièce ⑥ du registre des étapes) ; s'ils glissent, la vidéo reste montrable en REPLAY-JOURNAL seul, avec les runs chaîne démontrés par captures + reçus dès qu'ils sont exécutés.

## 2. Interface produit (direction)

Constat §8.1 : l'existant est **une page d'audit v0** ([FAIT — code] `src/orvyren/ui/server.py` : routes `GET /` → dernier dossier HTML, `GET /api/dossier` → JSON du dossier, `GET /api/health` ; serveur stdlib, lecture seule, 503 propre sans dossier). La direction produit ci-dessous s'y adosse sans la réécrire.

| Fonction | Dépend de | Version | Priorité | Notes |
|---|---|---|---|---|
| **Dossier de décision** (1 page + empreintes) — existant | audit (fait) | **V1** (avant soumission) | ① (déjà là) | Servi par `run_audit.py --serve` ; HTML autonome joignable sans serveur |
| **Liste des refus + quarantaines** (journal filtrable, lecture seule) | audit + journal agents | **V1** | ② — sert les écrans 7-8 de la démo | Extension triviale de la page : une route qui lit `audit.jsonl`/journal et rend en HTML statique |
| **Timeline branches & réflexions agents** (écran 3-4) | registre branches + `agent_journal` (bloc Agents) | **V1** (dès que les agents existent) | ② | Donne la démo multi-agent à l'écran |
| **File d'approbation `REQUIRE_APPROVAL`** | politique (bloc 4, flux non implémenté) | **V1.5 / V2** | ③ | Voir ci-dessous — dépend d'une décision du bloc 4 |
| **Alertes** (seuil de signal dépassé, action agent, incident) | capteurs W2-B + politique | **V2** | ④ | Aujourd'hui : e-mail/console ; cible : notification (canal à trancher) |
| **Monitoring des agents** (lecture des journaux par rôle, budgets consommés, arrêts) | journal par agent (B1 §3.4) | **V2** | ④ | Lecture seule, jamais d'action |
| **Statut de trésorerie** (exposition, double valorisation oracle/réalisable, runway) | portefeuille réel (bloc 3.7, aujourd'hui fixtures) | **V2** | ⑤ | « Le tableau de bord qui vend le produit » (DAO) |

**File d'approbation — recommandation** [PROPOSITION] : l'approbation humaine d'un `REQUIRE_APPROVAL` se fait par **signature du wallet de l'humain** (la décision est un objet signé : intent + verdict + timestamps), pas par un bouton qui déclencherait une clé serveur. Canal minimal V1.5 : page « approuver/refuser » qui **construit la transaction non signée** (même mécanique que le flux actuel « l'humain exécute, l'agent vérifie ») + lien de vérification. Canaux alternatifs (Telegram/email) = option du bloc 4 — coût d'un bot ≈ 0,5–1 j ; **à trancher en revue** (question 4.1 de la carte).
**Garde-fou transverse** : toutes ces vues sont **en lecture seule** ; aucune route d'écriture en V1 (cohérent avec §5 Sécurité UI).

## 3. Hébergement & CI

### 3.1 Décisions concrètes

| Objet | Décision | Réf. / statut |
|---|---|---|
| **Démo (vidéo + soutenance)** | **100 % locale, hors-ligne** : SQLite + corpus + `--replay` ; les runs on-chain passent par le RPC public `https://sepolia.base.org` (aucun serveur à héberger) | [DIRECTION] AV1 §5, F20-D8 ; W2C §g |
| **Page publique du dossier (post-soumission)** | Fichier **HTML autonome** (déjà produit par l'audit) → hébergeable tel quel : Render **static site** / GitHub Pages / n'importe quel hébergeur statique. Zéro secret, zéro base. | [PROPOSITION] |
| **Service web** | **Render web free** (FastAPI ou serveur stdlib), lecture seule, pour la « vitrine » (dossier + API `/api/health`, `/api/dossier` déjà définies) | [DIRECTION] AV1 §5 (« Render web gratuit ») |
| **Base Postgres** | **Neon free — permanent** (1 Go/projet, 100 CU-h ; vérifié par B2 le 15/10/2026). **Ne pas utiliser Render free PG : il expire à 30 jours** (changelog Render 20/05/2024) | [FAIT SOURCÉ — B2] ; cible de migration post-concours, SQLite reste la base du concours |
| **Replay local** | Mode par défaut de la démo et des tests : aucune dépendance réseau (le CI le prouve déjà : `collect_corpus.py --offline`) | [FAIT — code] `.github/workflows/tests.yml` |
| **Réserve** | Question ouverte B2 QO-8 : si le free tier Neon (scale-to-zero 5 min, 100 CU-h) ne tient pas le direct, démo SQLite locale + Postgres en miroir | [PROPOSITION B2, à vérifier avant toute démo publique live] |

### 3.2 Où tourne quoi (table unique)

| Environnement | Composant | Où |
|---|---|---|
| Développement | pipeline Python, tests, UI locale | poste du développeur (Windows) ; Python 3.11 stdlib |
| Démo/jury | replay hors-ligne + dossier HTML | poste (vidéo) ; fichier HTML autonome |
| Démo on-chain | 5 runs Base Sepolia (Safe 2/3 + module Roles + signer EOA) | chaîne testnet via RPC public ; clés **côté équipe**, jamais dans le dépôt/LLM/logs |
| CI | tests + pipeline + check hors-ligne | GitHub Actions (`tests.yml`), sur chaque push/PR |
| Post-soumission | service de lecture + API | Render web free (lecture seule) |
| Post-soumission | Postgres cible | Neon free (migration contenue dans `store.py`, ~1-2 j selon B2/R3) |

### 3.3 CI — état et ajouts proposés

**Existant** [FAIT — code] `tests.yml` : `unittest discover` (banc de sûreté + décision + corpus), `run_pipeline.py` de bout en bout, `collect_corpus.py --offline` (preuve que le replay marche sans réseau).
**Ajouts proposés** [PROPOSITION] (faible coût, chaque ajout ≤ 0,5 j) :
1. **Secrets check** : `grep` interdit pour `0x[0-9a-f]{64}` (clés privées) et fichiers `.env` — bloque une fuite par accident ;
2. **ADR index check** : le registre `docs/decisions/` doit rester consistant (numérotation, statuts) — script local (voir §6) ;
3. **Doc build** : `md2docx.py` pour les documents finaux (existant : `C:\Users\User\fintechathon_recherche\md2docx.py` → `dist/docs/`) ;
4. **Vérification du journal d'audit** : `audit/` a déjà l'outil de contrôle ; le faire tourner sur `audit.jsonl` de fixtures.

## 4. Runbook opérationnel

> État : ce runbook spécifie la cible ; les items marqués ☐ ne sont pas encore implémentés (documenter tel quel, jamais d'écart silencieux).

### 4.1 Démarrage

1. **Pipeline complet** : `python run_pipeline.py` (qualité → décision → politique → audit ; échoue bruyamment).
2. **Page dossier** : `python run_audit.py --serve` → `http://127.0.0.1:8000` (routes `/`, `/api/dossier`, `/api/health`).
3. **Démo chaîne (veille)** : exécuter le montage W2C §g.1 (Safe 2/3, module Roles, rôle `AGENT`, allowance `usdc_daily` 300/24 h, signer EOA financé) ; **vérifier** la version du module avant chaque période d'exécution (veille Zodiac, W2C Annexe 3) ; noter `balanceOf(Safe)` de départ.
4. **Contrôle de santé avant toute session** : `curl /api/health` = `{"ok": true}` ; hash du corpus conforme au manifeste ; `policy_version` affichée (W2C §d.5 point 5).

### 4.2 Arrêt d'urgence (kill switch)

| Niveau | Action | Qui | Effet | Réf. |
|---|---|---|---|---|
| K0 | PAUSE hors-chaîne (drapeau du service de signature) | astreinte ORVYREN | immédiat : plus aucune signature | W2C §d.4 |
| K1 | `assignRoles(agent, [AGENT], [false])` | Safe DAO (seuil signatures) | toute exécution ultérieure revert `NoMembership` ; 1 tx (~1,64 s/bloc Base mesuré 15/10) ; latence réelle = coordination humaine (minutes) | W2C §g.5 |
| K2 | `disableModule(prev, rolesModule)` | Safe DAO | le module entier | idem |
| K3 | retrait du gaz (ETH) de l'agent | Safe DAO | arrêt par asphyxie | idem |
| ☐ | **Procédure humaine d'incident** : qui convoque la signature DAO, en combien de temps, message type | équipe | à écrire (carte §4.3 — « le processus humain reste à définir ») | |

Honnêteté (à écrire dans les documents finaux) : le kill switch **n'annule pas** une tx déjà incluse, ni ne court-circuite la mempool ; le pire cas par bloc est borné par l'allowance (W2C §d.4, §g.7).

### 4.3 Mise à jour de politique

1. **Fichier** : `policy.yaml` versionné (plafonds, glissant 24 h, allowlist, chaîne épinglée) + code déterministe — déjà la règle W2C §g.1.7.
2. **Test obligatoire** : banc de sûreté (7 attaques + NaN/infini/cumul) **avant** tout déploiement de nouvelle version.
3. **Chaîne** : si l'enveloppe change (allowance, cible, destinataire), mise à jour par la **DAO** dans l'app Roles (jamais par l'agent — il n'a aucun droit d'admin) ; **test de dérive** = re-jouer la table de correspondance règle hors-chaîne ↔ condition on-chain (carte §4.2, W2C §b).
4. **Traçabilité** : `policy_version` incrémentée, référencée dans chaque entrée de journal ; le diff de politique est conservé (W2C §g.6.3).

### 4.4 Rotation de clé

1. Créer la nouvelle EOA (clé hors dépôt, hors logs, hors LLM — la règle du projet).
2. `assignRoles(nouvelle, [AGENT], [true])` **puis** `assignRoles(ancienne, [AGENT], [false])` — 1 transaction DAO (W2C §d.2).
3. Alimenter le gaz de la nouvelle adresse ; vérifier `Roles.roles(AGENT).members(nouvelle)` = `true`.
4. Archiver l'événement de rotation dans le journal (kind `KEY_ROTATION` — à ajouter au schéma ☐).

### 4.5 Incidents & veille

- **Veille amont** : communiqués Zodiac/Gnosis Guild (`@zodiaceco`, `engineering.gnosisguild.org`) ; l'app Roles signale les modules vulnérables → **test automatique de version au démarrage** (☐ à intégrer, W2C Annexe 3).
- **Surveillance des événements** : `AssignRoles`, `SetDefaultRole`, `ConsumeAllowance` ; alerte si exécution hors profil attendu (destinataire nouveau, montant inhabituel, rafale).
- **Monitoring logs/alertes** : journal `audit.jsonl` chaîné (toute réécriture est détectable) ; `GET /api/health` pour la liveness ; alertes minimales (☐) : (a) verdict `DENY` répété sur la même intention, (b) échec de vérification de reçu, (c) rupture du chaînage du journal, (d) absence de heartbeat worker.
- **Rétention** : graphe append-only sans limite ; journal append-only — question Q3 de B1 (rétention) à trancher au gel (§9).

## 5. Sécurité UI

| Principe | État | Action/Preuve |
|---|---|---|
| **Aucun secret côté client** | [FAIT] : UI = HTML statique sans JS ni asset externe ; aucune clé n'est jamais requise par l'UI (l'agent n'a pas de clé dans le processus de raisonnement) | Ajouter au CI un grep « pas de clé/clé privée dans les artefacts servis » (§3.3.1) |
| **Auth minimale** | [À FAIRE] : en exposition publique, protéger l'accès par token/Basic (géré par l'hébergeur) — la V1 n'a **aucune** route d'écriture donc l'exposition se limite à la lecture | Si file d'approbation (V1.5) : session + jeton + **signature wallet humain** pour approuver (jamais une clé serveur) |
| **Lecture seule par défaut** | [FAIT] : handler GET/HEAD uniquement ; toute autre route → 404 JSON ; `Cache-Control: no-store` ; le serveur ne peut pas planter sur une requête (garde défensive) | Conserver ; toute nouvelle route d'écriture exige une revue de sécurité dédiée |
| **Bind local par défaut** | [FAIT] : `127.0.0.1:8000` par défaut | Pour l'exposition publique : bind derrière le proxy de l'hébergeur |
| **En-têtes** | [À FAIRE] : ajouter CSP restrictive (`default-src 'none'; style-src 'unsafe-inline'`), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` | 0,5 j |
| **Séparation des privilèges** | [FAIT — conception] : l'UI n'exécute rien ; `policy` hors LLM ; `execution` ne reçoit qu'un intent ALLOW ; la clé de l'agent vit dans un processus séparé, hors LLM/logs/dépôt | Invariants I1-I5 (W2C §d.1) testés |

**Règle d'or UI (à écrire dans le document technique)** : « l'interface **montre** et **instruit** (construit des objets non signés), elle ne **signe** jamais et ne **détient** jamais de secret. »

---

# PARTIE B — GOUVERNANCE DE SPÉCIFICATION

## 6. Protocole de gel v2 (ADR + registre unique + révision)

### 6.1 Ce que dit la carte §9, et l'état

- §9.2 : `FREEZE_V1.md` (14/10) est **périmé** par les corrections (autonomie bornée, cible DAO/desk, épisodes) — le remplacer une fois les blocs A-C tranchés. [FAIT]
- §9.5 : livrable suivant du chantier = **une note de décision par bloc** (options, conséquences, recommandation, coût de changement), puis le gel v2. [FAIT]
- La méthode de révision existe déjà (explainer Partie 5 : 4 questions + essai pré-enregistré + décision de valeur datée). [FAIT]
- **Ce qui manque** : un format et un registre uniques, des conditions de réouverture, un versionnage. → Proposition ci-dessous.

### 6.2 Format ADR retenu (Nygard + extensions MADR)

**Format [PROPOSITION — à adopter]**, un fichier = une décision, dans `docs/decisions/` (dossier voisin du code, versionné avec lui — la recommandation constante de la littérature : Thoughtworks, Nygard) :

```markdown
# ADR-NNN — Titre court (phrase nominale)
- Statut : proposed | accepted | deprecated | superseded by ADR-MMM
- Date : AAAA-MM-JJ (dernière mise à jour)
- Décisionnaires : (qui a accepté)
- Confirmé par : (ce qui, mécaniquement, prouve que la décision tient — test, CI, revue)
## Contexte et problème
## Options considérées
### Option A — …  · + arguments · − arguments · coût de changement
### Option B — …
## Décision retenue et justification
## Conséquences (positives / négatives / neutres)
## Conditions de réouverture (voir §6.4)
## Références (URL + date de consultation ; fichiers internes)
```

Pourquoi ce mélange : Nygard (2011) donne le squelette minimal (Titre/Contexte/Décision/Statut/Conséquences) ; MADR ajoute **Options considérées + Drivers + Conséquences +/- + « comment la conformité sera confirmée »** — exactement ce que la méthode d'équipe exige déjà (les « notes de décision par bloc » de §9.5 avec options et coût de changement). Le champ « Confirmé par » reprend l'idée MADR de *confirmation* (un test ou un contrôle vérifie que la décision est respectée) — cohérent avec la culture « vérifiable » du projet.

### 6.3 Registre unique

- **Emplacement** : `docs/decisions/` (créé par ADR-0001, à la première utilisation).
- **Fichiers** : `NNNN-titre-court.md`, numérotation **séquentielle, jamais réutilisée** ; `README.md` = index (numéro, titre, statut, date) — maintenu à la main (équipe de 2-5 personnes : pas d'outillage, cf. §6.7).
- **Unicité** : toute décision gelée vit **ici**, une seule fois ; les documents finaux **référencent** les ADR au lieu de ré-expliquer. Le gel v2 = un lot d'ADR `accepted` + un paquet haché (§6.5).
- **Statuts** : `proposed` (débat ouvert) · `accepted` (gelé) · `deprecated` · `superseded by ADR-MMM`. Une réouverture produit un **nouvel** ADR qui supersède ; on ne réécrit jamais un ADR accepté (jamais de réécriture silencieuse — règle déjà posée, explainer Partie 5 point 5).
- **Premiers ADR proposés (ordre de gel)** [PROPOSITION] : `ADR-0001` Adopter ce protocole · `ADR-0002` Gel v2 — topologie multi-agent (bloc A) · `ADR-0003` Gel v2 — DL/ML dans le graphe (bloc B) · `ADR-0004` Gel v2 — généralisation de la décision (bloc C) · puis les blocs 4-8 (politique, exécution, audit, interface/ops, mesure). Les 12 points W2-D §(f) et l'édit du cadre entrent comme ADR ou comme annexes du gel.

### 6.4 Procédure de révision (les 4 questions) et conditions de réouverture

Procédure (reprise de l'explainer Partie 5, rendue opposable) — toute contestation d'une décision acceptée déclenche un **ADR de révision** qui répond par écrit aux 4 questions :
1. **Qu'est-ce qui dépend de cette décision ?** (liste des documents/ADR/code impactés)
2. **Qu'est-ce que ça coûte de changer ?** (jours, budget API, re-tests, re-gel)
3. **Qu'est-ce qui est vérifiable ?** (si oui → essai pré-enregistré, critère de succès fixé avant, résultat publié même s'il contredit)
4. **Quelle preuve nous ferait changer d'avis ?** (condition de falsification écrite à l'avance)

**Conditions de réouverture** (une seule suffit à ouvrir un ADR de révision) :
- **R1** : un essai pré-enregistré mesure un résultat contraire à l'ADR ;
- **R2** : une faille de sécurité ou un incident (chaîne, clé, injection) ;
- **R3** : la contrainte externe change (règlement du concours, deadline, coût d'un fournisseur ;
- **R4** : le coût de changement est ré-estimé et devient faible (< 1 j) ;
- **R5** : le responsable du gel (rôle à nommer, carte 3.12 « responsable du gel ») ouvre la révision explicitement.

Sans R1-R5 : **on ne rouvre pas** — c'est la règle qui protège les 5 jours restants et l'après-concours.

### 6.5 Versionnage des documents + paquet de gel

- **Documents finaux** : version `vX.Y` en tête ; **Y** = correction/typo sans changement de décision, **X** = changement de décision (implique un ADR accepté) ; **changelog en tête** (date, version, nature), jamais de modification silencieuse.
- **Paquet de gel (v2)** : (1) lot d'ADR `accepted` ; (2) `GEL_V2.md` = index figé + **sha256** du lot (fichiers + commit) ; (3) note de version par document ; (4) date + décisionnaires. Chaque run/évaluation référence le hash du paquet (pratique de pré-enregistrement haché — reprise généraliste, cf. §7.1).
- **Gel v2 remplace** `FREEZE_V1.md` : FREEZE_V1 passe en `superseded` (son contenu utiles — valeurs D1-D12 — migre en ADR avec les corrections).

### 6.6 Recherche web — pratiques ADR / decision logs / RFC (8 sources, consultées le 15/10/2026)

| # | Source | Date | Ce qu'on en reprend |
|---|---|---|---|
| S1 | Nygard, M. — *Documenting Architecture Decisions* — https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions | publié 2011-11-15 | Format 5 parties (Titre/Contexte/Décision/Statut/Conséquences) ; fichiers `adr-NNN.md` dans le dépôt ; numérotation séquentielle non réutilisée ; 1-2 pages, « une conversation avec le futur développeur » ; statuts proposed/accepted/deprecated/superseded |
| S2 | adr.github.io — hub ADR (« the collection of ADRs … constitute its *decision log* ») — https://adr.github.io/ | consulté 2026-10-15 | Définition AD + ADR + **decision log** ; racine « Sustainable Architectural Decisions » (Zdun et al., Y-statements) ; références AWS Prescriptive Guidance |
| S3 | MADR — *Markdown Architectural Decision Records* (template) — https://adr.github.io/madr/ et https://github.com/adr/madr | consulté 2026-10-15 (v4) | Sections **Options considérées**, **Drivers**, **Conséquences +/-**, **Confirmation** (« how the implementation/compliance can be confirmed ») ; métadonnées date/décisionnaires ; « any important decision » (pas seulement architecturales) |
| S4 | Thoughtworks Technology Radar — *Lightweight Architecture Decision Records* (Adopt) — https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records | blip 2016-11 (Trial) → Adopt 2017-11 ; page maj 2018-05-15 | Stockage **dans le contrôle de version** (pas wiki) pour rester synchrone avec le code ; « pour la plupart des projets, aucune raison de ne pas l'utiliser » |
| S5 | Thoughtworks Technology Radar vol.29 — *Lightweight approach to RFCs* (Adopt) — https://www.thoughtworks.com/content/dam/thoughtworks/documents/radar/2023/09/tr_technology_radar_vol_29_en.pdf | 2023-09 | RFC = document formel pour la décision en équipe ; « utilisés comme processus pour **réviser et ratifier** les ADR » → notre revue d'équipe = RFC léger, l'ADR enregistre le résultat |
| S6 | InfoQ — *Architecture Decision Records at Spotify* (d'après labs.spotify.com, J. Blake) — https://www.infoq.com/news/2020/04/architecture-decision-records | 2020-04-13 (article Spotify 2020-04-14) | 3 cas « évidents » d'écrire un ADR : documenter une décision passée non consignée ; finaliser un changement majeur (RFC → ADR) ; standardiser via revue. Bénéfices mesurés : onboarding, passation, alignement |
| S7 | adr-tools (N. Pryce, co-auteur du concept) — https://github.com/adr/adr-tools (successeur : log4brains) | consulté 2026-10-15 (v3.0) | Outillage léger autorisé si besoin : `adr new`, numérotation auto, **`adr new -s N`** (supersession, met à jour le statut de l'ancien) — équivalent script possible sans dépendance |
| S8 | Y-statements (Zimmermann, « software sustainability ») — https://adr.github.io/ et présentation ABB — https://www.inf.usi.ch/…/usi-guestlectureabbv11.pdf | consulté 2026-10-15 (source 2011-2012) | Forme courte d'une décision : « Dans le contexte de …, face à …, nous décidons …, pour obtenir …, en acceptant … » — utile pour l'index du registre (une ligne par ADR) |

**Ce qu'on adopte** : format S1+S3 ; registre dans le dépôt S4 ; RFC léger avant chaque ADR contesté S5 ; « confirmation » MADR (un test ou contrôle par ADR accepté) ; index Y-statement (une ligne) S8.
**Ce qu'on écarte** : publication statique type Log4Brains (pas de public non-git à servir avant longtemps) ; outillage CLI imposé (l'écriture à la main suffit à l'échelle 2-5 personnes — coût 0) ; tout processus lourd de type « board d'architecture » (pas d'équipe pour le tenir).

### 6.7 Notes d'exécution

- Le registre devient un **livrable de planification** : chaque note de décision de bloc A/B/C (§9.5) s'écrit **directement** comme ADR `proposed`, puis passe `accepted` en revue.
- L'alerte « sources » : tout ADR cite ses sources (URL + date) — même discipline que les documents finaux (§7.2).

## 7. Règle de rédaction des documents finaux

### 7.1 « Aucune mention de MIMIR » — règle et redéfinitions propres (exigence d'équipe)

**Règle [ACTÉE — équipe]** : les 4 documents finaux ne mentionnent **jamais** MIMIR (le mentionner réclamerait de fournir ses documents, hors périmètre). Corollaire : chaque concept hérité doit être **redéfini en propre**, en langage auto-portant, dans ORVYREN. (D3 acte déjà qu'ORVYREN est autonome tout en prenant l'héritage sémantique — c'est précisément cette dette de vocabulaire qu'on solde ici.) La règle s'applique aussi aux sources : on cite la **littérature générale** (bitemporel Snodgrass/Fowler, pré-enregistrement, PROV-O, etc.), jamais MIMIR.

| # | Concept repris (à ne pas nommer « MIMIR ») | Proposition de définition auto-portante (FR) | Où ça vit |
|---|---|---|---|
| 1 | **Horloges temporelles multiples** (ex-« six horloges ») | « Chaque fait du graphe porte plusieurs horodatages distincts : (a) **temps de l'événement** — quand le fait s'est produit dans le monde ; (b) **temps de publication** — quand l'information est devenue publique ; (c) **temps d'observation** — quand notre système l'a réellement lue (et l'a notée) ; (d) **temps d'effet** — quand la règle/mécanisme prend effet ; (e) **fenêtre de validité** — jusqu'à quand le fait est vrai ; (f) **temps de révision** — quand une correction a été apportée. La décision n'utilise que des faits dont le temps de publication et le temps d'observation sont ≤ l'instant simulé (anti-fuite du futur). » En v1 : (a)(b)(c) actives + (e)(f) portées ; (d) fusionné avec (e). | Schéma `graph` ; A2, SPEC v1 |
| 2 | **Chaîne de provenance** | « Chaque élément de connaissance est relié à sa source par une chaîne explicite de maillons, chaque maillon étant une ligne de lien stockée : **Source → Observation → Extraction → Affirmation (claim) → Relation → Hypothèse → Prévision → Résultat**. Aucun chiffre n'existe dans le dossier de décision s'il ne peut pas être remonté jusqu'à une source horodatée ; un claim sans observation parente est rejeté par le magasin. » | `graph/provenance.py` ; docs finaux §graphe |
| 3 | **Record de relation enrichi** | « Toute relation du graphe est un enregistrement typé : nom et famille (preuve & dérivation · structure & exposition · mécanisme économique · contrainte & permission), cause et effet (références), mécanisme (étiquette), conditions d'application, portée (régime, horizon), statut épistémique, signe attendu (+/−/ambigu), provenance (document ou référence), cycle de vie (découverte → évaluation → active → affaiblie → suspendue → rejetée). Une relation de preuve (`SUPPORTS`) n'autorise aucune propagation causale ; une corrélation porte un statut statistique, jamais « causale ». » | B2 §3 (catalogue 4 familles = pièce à figer) |
| 4 | **Labels épistémiques de causalité** | « Toute affirmation porte un label, conservé dans **chaque** document qui la cite : `FACT` (fait vérifié) · `REPORTED` (rapporté par une source) · `STATISTICAL` (association mesurée, sans mécanisme) · `CAUSAL-DOCUMENTED` (mécanisme documenté) · `CAUSAL-HYPOTHESIS` (mécanisme plausible, non prouvé) · `MODEL-INFERRED` (sorti d'un modèle, jamais un fait) · `REJECTED`. Une hypothèse ne devient jamais silencieusement une base acquise. » Statuts d'atelier associés : `DECIDED` / `DIRECTION` / `CANDIDATE` / `OPEN` / `REJECTED` / `DEFERRED`. | X (transverse) ; à reprendre tel quel dans les 4 docs |
| 5 | **Identifiants canoniques** | « ORVYREN nomme ses objets par préfixe + numéro : `VAR` variable · `SER` série · `EVT` événement · `OBS` observation · `CLM` affirmation · `REL` relation · `SCN` scénario · `FCT` prévision · `THS` thèse de trading · `OUT` résultat. Les identifiants externes (ids de série, adresses) sont des **champs de preuve**, jamais des clés. » | graph v1 |
| 6 | **Le nom du graphe** (ex-« DFKG ») | « ORVYREN construit un **graphe de connaissance financier typé** : un dépôt en ajout seul de faits, d'entités et de relations horodatés et sourcés, orienté vers la documentation d'un risque de collatéral et des décisions qui en découlent. » (Le mot « collatéral » porte la spécificité ORVYREN.) | docs finaux ; pitch |
| 7 | **Pré-enregistrement gelé et haché** | « Avant toute évaluation, le paquet de pré-enregistrement (hypothèses, seuils, critères de réfutation, règle de décision) est figé, **daté et haché (SHA-256)** ; chaque exécution d'audit référence ces empreintes. Une modification ultérieure crée une nouvelle version datée — l'ancienne reste lisible. » | `FREEZE`/gel ; audit |

**Contrôle qualité [PROPOSITION]** : une passe `grep -i mimir` sur les 4 documents finaux (et leurs exports) avant validation = 0 occurrence exigée. Piste pour la relecture : le mot « MIMIR » est un nom propre facile à filtrer — le vrai risque est le **vocabulaire orphelin** (six horloges, REL-, labels) utilisé *sans* sa définition ; d'où la table ci-dessus.

### 7.2 Politique de sources (documents finaux)

1. **Chaque affirmation externe** porte : URL + **date** (publication si connue ; sinon date de consultation « consulté le JJ/MM/AAAA »).
2. **Étiquettes conservées** : `[FAIT SOURCÉ]`, `[MESURÉ]`, `[NON TROUVÉ]`, `[PROPOSITION]` — jamais un chiffre sans étiquette ni trace.
3. **« Non trouvé » s'écrit** : si une information n'a pas été trouvée, on l'écrit (plusieurs annexes « non trouvé » existent déjà, ex. W2-C Annexe 2) — on n'invente pas, on ne « complète » pas par plausibilité.
4. **Références internes** : fichiers du dépôt + dates (déjà la pratique des rapports W2-x/B-x).
5. **Bibliographie unique** par document final, en fin, triée ; les faits partagés (prix, adresses) sont référencés une fois dans le document technique et pointés ailleurs.

### 7.3 Langue des documents finaux

- **Décision d'équipe [ACTÉE]** : les **4 documents finaux** (ceux de §8) s'écrivent en **français** — ce sont les documents de travail faisant foi pour l'équipe et le socle des traductions.
- **Articulation avec D9** (livrables du concours en anglais) : les pièces de **soumission** (document technique EN, deck, vidéo, README) restent en anglais ; elles sont **adaptées/traduites depuis les documents finaux FR**. La traduction est un livrable de la phase « pièces concours », pas une réécriture.
- Le README et le code restent en anglais (règle AV1 §5) ; les notes internes en français.

## 8. Carte des 4 documents finaux (spécification)

> Statut : tous **post-gel** (bloc « documents finaux » de la carte §9.5). Ils remplacent l'actuel empilement `V0.2 + AV1 + FREEZE + synthèses` par **quatre objets aux rôles distincts**. Chacun référence les ADR du gel (§6) au lieu de re-décider.

### 8.1 Document 1 — « ORVYREN expliqué simplement » (explicatif)

| Attribut | Spécification |
|---|---|
| **Audience** | Jury non technique, décideurs, partenaires DAO ; toute personne en 10 minutes |
| **Contenu** | Le problème (valorisation retenue ≠ prix réalisable, signaux dispersés) ; ce qu'ORVYREN est / n'est pas ; le cycle en 10 étapes avec **l'exemple USDC mars 2023 et un encadré rsETH 2026** ; ce qui existe vs ce qui reste ; la promesse (décision vérifiable, abstention, refus opposables) |
| **Longueur** | **1-2 pages** (≈ 800-1200 mots) + **2-3 schémas** dont `figures/orvyren_cycle_complet.png` (existe) |
| **Structure** | 1 Problème · 2 Ce que c'est (et pas) · 3 Le cycle en 10 étapes (tableau) · 4 Un cas réel · 5 Ce qui est vérifiable · 6 Où ça va (V2/banques en une ligne) |
| **Critères de qualité** | Zéro jargon non défini ; chaque chiffre cité est traçable (renvoi au doc 2) ; **0 occurrence** de vocabulaire non défini (§7.1) ; lisible par un non-spécialiste seul |
| **Source** | Adapté de `dist/docs/ORVYREN_EXPLIQUE_SIMPLEMENT.md` (déjà bon candidat — dégraisser les 20 décisions vers le doc 3) |

### 8.2 Document 2 — Document technique complet (v1)

| Attribut | Spécification |
|---|---|
| **Audience** | Jury technique, comité d'évaluation, futurs collaborateurs, auditeurs |
| **Contenu** | Architecture des modules et interfaces (AV1 §2-3), agents (topologie gelée, boucle, budgets, prompts/schémas), graphe (schéma définitif, relations, horloges, pipeline), décision généralisée, politique & autorisation, exécution (double verrou), audit/vérification (reconstructibilité), mesure (W2-D), interface & ops (Partie A de ce document), sécurité (matrice d'attaques W2-C), **ADR référencés** ; séparation explicite **« spécifié » vs « réalisé aujourd'hui »** |
| **Longueur** | ~30-50 pages (cible), annexes non comptées |
| **Structure** | 1 Contexte & portée · 2 Exigences · 3 Architecture (modules/interfaces) · 4 Agents · 5 Graphe · 6 Décision · 7 Politique · 8 Exécution & double verrou · 9 Audit & vérifiabilité · 10 Mesure & évaluation · 11 Interface & opérations · 12 Sécurité · 13 Limites & ce qui n'est pas revendiqué · 14 Glossaire · 15 Bibliographie |
| **Critères de qualité** | Chaque affirmation étiquetée ou sourcée (URL+date) ; chaque invariant de conception a son test (ou un « à tester » daté) ; les ADR du gel sont la source unique des décisions ; les sections « limites » (honnêteté) sont obligatoires ; **0 MIMIR** |
| **Est déjà là** | V0.2 (EN), ARCHITECTURE_V1, FREEZE, VAGUE2, CADRE, B1/B2/B3, W2-C/D — à **réorganiser**, pas à réécrire |

### 8.3 Document 3 — Propositions, écartés & V2 (« la banque »)

| Attribut | Spécification |
|---|---|
| **Audience** | Équipe et successeurs ; toute personne qui demande « pourquoi pas X ? » |
| **Contenu** | **Registre des écartés avec raison** (ex. Kuzu archivé 10/2025 ; GraphRAG en maintenance ; Neo4j inutile à l'échelle ; ERC-7715 reporté ; EAS reporté) ; options V2 priorisées : 2e/3e épisodes (stETH backtest, UST), VoI (T02), probabilisation + calibration, extension ML du graphe (HYP-07R), banques/institutions (phase 2, U1), desk (persona 2), cession simulée (HYP-09R), passe « intégration » (inventaire intégrer/construire, posture §5 du registre) ; registre HYP complet (statuts, conditions de réouverture) |
| **Longueur** | 10-20 pages, **entrées atomiques** (une proposition = un bloc nommé, daté, statut) |
| **Structure** | Par thème : A. écarts assumés (avec la condition qui les rouvrirait) · B. améliorations prouvables (essai pré-enregistré associé) · C. extensions produit (banques, desks, multi-chaînes) · D. dette technique planifiée (migration Postgres, rétention journal, …) |
| **Critères de qualité** | Rien n'est « rejeté » sans raison écrite ni **condition de réouverture** (R1-R5 du §6.4) ; chaque entrée distingue *idée / coût / gain attendu / comment on saurait* |
| **Alimenté par** | `AXES_AMELIORATION_FULGURANTE.md` (HYP-01…15), R1/R2/R3, B2 §7 (questions ouvertes), revues |

### 8.4 Document 4 — Plan d'implémentation (modules & sprints)

| Attribut | Spécification |
|---|---|
| **Audience** | Collaborateurs qui codent (et le responsable de planning) |
| **Contenu** | Découpage en **modules** (carte AV1 §2 : connectors, quality, graph, branches, research, decision, policy, execution, audit, ui) ; **lots de travail ordonnés** avec dépendances ; critères d'acceptation **testables** par lot (ex. « registre de branches : 8 transitions d'état testées ») ; responsabilités ; jalons ; inventaire « intégrer vs construire » par brique (posture d'intégration actée) ; environnement (stdlib, CI, secrets) |
| **Structure** | 1 Principes (stdlib, replay, invariants) · 2 Vue des modules · 3 Lots L1…Ln (objectif, entrées/sorties, définition de fini, tests, estimation) · 4 Ordre et parallélisation · 5 Risques & dépendances externes (wallet, faucet, clés) · 6 Définition de « v1 terminée » |
| **Longueur** | 10-15 pages + tableau des lots |
| **Critères de qualité** | Chaque lot est **démontrable** (une commande, un artefact) ; estimation en jours-homme ; aucun lot ne contredit un ADR accepté ; le premier lot est exécutable dans la semaine |
| **Base** | Ordonnancement proposé : boucle agent (bloc A) → graphe v1 (bloc B) → décision généralisée (bloc C) → UI/ops V1.5 → enveloppe prod ; réutilise W3-D (kit démo) comme premier livrable si non consommé |

**Articulation entre les 4** : doc 1 = la porte d'entrée ; doc 2 = la référence technique (cite les ADR) ; doc 3 = la mémoire des refus et l'horizon ; doc 4 = l'action. **Règle anti-divergence** : les 4 sont générés au même moment du gel, partagent le paquet haché (§6.5) et toute mise à jour ultérieure suit §6.4-6.5.

## 9. Note d'orientation pour le gel v2 (multi-agent réel + DL/ML implémentés)

**Exigence d'équipe à refléter dans la v1 [ACTÉE, orientation]** : la v1 doit inclure (i) le **multi-agent réel** (instances d'agents séparées) et (ii) des décisions **DL/ML implémentées** — pas seulement théoriques. La v1 recommandée par B1 (Option C, monolithe, rôles logiques) et la position B2 (« rien d'appris dans le chemin de décision », au plus pgvector) ne satisfont pas **littéralement** l'exigence (i). Il faut donc poser la question de périmètre, options et coûts **chiffrés**, pour la revue de gel :

### Q-GEL-01 — Multi-agent : quelle forme pour la v1 ?

| Option | Description | Coût / risque | Réf. |
|---|---|---|---|
| **MA-A** | Monolithe, rôles logiques (orchestrateur/explorateur/critique), un seul service — recommandation B1 | Coût faible (coutures déjà posées) ; **ne satisfait pas « instances séparées »** (multi-agent « logique ») | B1 §1.4-1.5 |
| **MA-B (proposée)** | **Instances séparées minimales** : orchestrateur et critique (au minimum) en **processus distincts**, même dépôt, échange par objets sérialisables via la table de jobs/HTTP ; chaque agent = instance propre avec son `agent_id` et son journal ; explorateur séparé si le temps le permet | **+2-4 j dev** ; latence et coût modestes (2 instances, DeepSeek flash ≈ $0,013-0,036/décision) ; risque de cohérence faible si la règle « objets sérialisables uniquement » est tenue dès la v1 (B1 §1.5 l'a déjà prévue) | B1 §1.3/1.5 (« passer de C à B plus tard ne demande pas de refonte si deux règles tenues ») |
| **MA-C** | Option B complète : 4 agents (planificateur, explorateur, critique, rédacteur) en services/processus + protocole de messages + arbitre | ~30 appels/décision ≈ 3× MA-B ; **risque de cohérence élevé** (4 journaux à réconcilier — la littérature citée par B1 le qualifie de problème ouvert) ; contredit AV1 §6 (« pas de multi-agent parallèle ») | B1 §1.3 et §1.5 |
| Q-GEL-01-a | La démo doit-elle **montrer** les instances (deux fenêtres de logs/processus à l'écran) ou seulement les journaux ? | Effet vidéo vs coût de tournage (~0,5 j) | écrans 3-4 (Partie A §1) |
| Q-GEL-01-b | « Instances séparées » = processus sur la même machine (acceptable) ou services déployés séparément (Render ×2) ? | Coût hébergement (free tiers) + latence réseau | AV1 §5 |

**Recommandation [PROPOSITION]** : **MA-B** — c'est le plus petit incrément qui répond à l'exigence (« instances séparées » réelles, démontrables à l'écran par les journaux par agent), sans le risque de cohérence de MA-C, et il prépare MA-C sans refonte (contrats sérialisables). À trancher en revue, puis **ADR-0002**.

### Q-GEL-02 — DL/ML : quoi est IMPLÉMENTÉ en v1 ?

| Option | Description | Coût | Statut |
|---|---|---|---|
| **ML-0** | Rien (B2 : « rien d'appris dans le chemin de décision ») | 0 | **insuffisant seul** face à l'exigence « DL/ML implémenté » |
| **ML-1 (proposée, socle)** | **Recherche sémantique d'appoint** (embeddings + `pgvector`) : retrouver documents/claims similaires, **générateur de candidats** pour la résolution d'entités ; jamais un fait, jamais un chiffre ; sorties étiquetées `MODEL-INFERRED` | Quasi nul en local (sentence-transformers) ; Neon free (pgvector) pour l'hébergement | B2 §5.2-5.3 [DIRECTION B2] |
| **ML-2 (proposée, add-on)** | **Détection d'anomalies** sur les séries de signaux (ex. robuste : z-score MAD / règles apprises simples) **hors chemin de décision** : sert au déclenchement de la surveillance (pré-épisode), chaque alerte étiquetée et journalisée ; comparée à la baseline à seuil fixe (A0) | 1-2 j ; nécessite pré-enregistrement (faux positifs mesurés sur fenêtre témoin) | [PROPOSITION] — cohérent W2-B (seuils) et W2-D (mesure) |
| **ML-3** | Link prediction/GNN expérimental (node2vec/GraphSAGE, KGC) — programme HYP-07R | ≥ 1-2 semaines, post-concours | **post-concours** (B2 §5.3 : « expérimental post-concours, si et seulement si le graphe v1 tourne ») |
| Invariants à ne pas casser (toutes options) | (a) aucun ML dans le **chemin confirmatoire** de la décision ; (b) toute inférence ML porte `MODEL-INFERRED` + provenance ; (c) la reconstruction (T10) doit rester possible : un modèle qui casse la reconstituabilité est **écarté** | — | B2 §5.3 ; REVUE_CROISEE |

**Recommandation [PROPOSITION]** : **ML-1 + ML-2** implémentés en v1 (satisfait « DL/ML implémenté » sans toucher la discipline épistémique), ML-3 au programme post-gel (document 3, HYP-07R). À trancher en revue, puis **ADR-0003**.
*Nuance à acter* : l'exigence « ML implémenté » doit s'entendre « implémenté **et borné par la traçabilité** » — les invariants ci-dessus font partie de la décision, pas de l'implémentation.

### Q-GEL-03 — Questions de périmètre complémentaires à porter au questionnaire de gel

1. **Q3.1** — Les 4 documents finaux (§8) sont-ils validés comme **le** jeu de livrables internes, avec la règle « 0 MIMIR » (§7.1) et le français (§7.3) ?
2. **Q3.2** — Qui est le **responsable du gel** (nommé) et qui arbitre les réouvertures (conditions R1-R5) ?
3. **Q3.3** — Le registre ADR (`docs/decisions/`) est-il adopté **tel quel** (§6.2) et le gel v2 devient-il `ADR-0001…N` + `GEL_V2.md` haché ?
4. **Q3.4** — File d'approbation : canal V1.5 (page signée / CLI / messagerie) — question 4.1 de la carte, coût 0,5-1 j.
5. **Q3.5** — Composant « inventaire intégrer vs construire » (posture actée) : qui le produit, sous quelle forme (annexe du doc 2 ou du doc 4) ?

### 9.4 Rappel de ce que ce document ne fait pas

- Il ne gèle rien : tout est `proposed` jusqu'à la revue (formats et questions sont prêts à être versés en ADR).
- Il ne re-vérifie pas Render/Neon (repris de B2, 15/10/2026) ni les prix des modèles (repris de B1 §2, 15/10/2026).
- Il n'a pas exécuté les runs testnet (état : plan W2-C §(g) prêt ; wallet côté équipe = chemin critique soumission).

---

## Sources web (consultées le 15/10/2026 sauf mention)

1. Nygard, M. — *Documenting Architecture Decisions* — https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions (publié 2011-11-15).
2. adr.github.io — *Architectural Decision Records* — https://adr.github.io/.
3. MADR — https://adr.github.io/madr/ et template https://github.com/adr/madr/blob/main/template/adr-template.md.
4. Thoughtworks — *Lightweight Architecture Decision Records* — https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records (blip 2016-11 → Adopt 2017-11 ; page mise à jour 2018-05-15).
5. Thoughtworks — *Technology Radar vol. 29* (« Lightweight approach to RFCs », Adopt) — https://www.thoughtworks.com/content/dam/thoughtworks/documents/radar/2023/09/tr_technology_radar_vol_29_en.pdf (2023-09).
6. InfoQ — *Architecture Decision Records at Spotify* — https://www.infoq.com/news/2020/04/architecture-decision-records (2020-04-13 ; article Spotify du 2020-04-14).
7. adr-tools — https://github.com/adr/adr-tools (consulté 2026-10-15).
8. Zimmermann, O. — Y-statements / *Making Architectural Knowledge* — https://www.inf.usi.ch/sites/inf.usi.ch/files/storage/attachments/document/usi-guestlectureabbv11.pdf (diapositives 2011-2012 ; consultées 2026-10-15).

Matière brute et notes de collecte : `research/raw_b89/`.

---

*Changelog — v0.1 (15/10/2026) : première version ; couvre §8.1-8.2 et §9.1-9.5 de la carte ; écrans 1-9 repris de B1 §6.4 + écrans 10-12 construits depuis W2-C §g ; protocole de gel proposé (ADR Nygard+MADR, registre, réouverture R1-R5, versionnage) ; règle « 0 MIMIR » + 7 redéfinitions ; carte des 4 documents finaux ; note Q-GEL-01/02 (multi-agent réel, ML implémenté). Statuts : tout [PROPOSITION] sauf mention contraire.*
