# ORVYREN — CARTE DES DÉCISIONS SYSTÈME (zones d'ombre à trancher)

**15 octobre 2026.** État : on a renforcé **l'extérieur** du projet (utilisateur cible, personas, problème, données, faisabilité, enveloppe, mesure). Ce document liste **l'intérieur** — le système lui-même : agents, modèle, graphe, relations, logiques, fonctionnement exact — tout ce qui manque pour que le projet soit viable (a) **en démo** (replay de l'historique) et (b) **en inference** (fonctionnement réel). Sans ces décisions, le document technique ne peut pas être écrit (à part pour décrire un existant partiel).

Statuts : **[OUVERT]** rien n'est décidé · **[DIRECTION]** une proposition existe, à valider · **[PARTIEL]** une pièce existe mais incomplète.
Colonne « Requis pour » : D = démo viable · I = inference viable · D+I = les deux.
Références : V0.2 = `ORVYREN_Document_de_reference_V0_2` · AV1 = `ARCHITECTURE_V1.md` · MIMIR = design technique MIMIR (DFKG) · A2 = revue Astra-2 · RC = revue croisée · R1/R2/R3 = recherches · W2-x/W3-x = rapports de vagues · F20 = carte des 20 décisions (`ORVYREN_EXPLIQUE_SIMPLEMENT`).

---

## 0. ÉTAT DES LIEUX (en une page)

**Ce qui existe** : politique déterministe testée (8 règles, attaques) · moteur de décision **figé sur UN cas** (USDC 2023) · couche données vérifiée + 3 épisodes probants (rsETH, stETH, USDC) · graphe SQLite append-only v0 (provenance, 12 déclencheurs) · dossier d'audit v1 · pipeline CLI · enveloppe Zodiac étudiée (W2-C) · mesure conçue (W2-D) · signaux définis (W2-B).

**Ce qui manque pour parler de « système »** : **aucun agent** (pas de boucle planifier→outil→évaluer→arrêter) · **aucun modèle LLM choisi** · schéma de graphe **v0 partiel** (pas la version définitive) · liste des **relations exactes** non figée (familles seulement) · **construction** du graphe non spécifiée · décision **généralisée** (1 cas figé ≠ système) · **DL/ML dans le graphe** : question non tranchée · interface produit, déploiement, calibration : v0 ou absents.

**AV1 (14/10) = carte des modules**, pas spécification système — et il précède les corrections (autonomie bornée, agents absents, modèle absent, cible DAO/desk). Il devra être **mis à niveau** une fois les décisions ci-dessous prises.

**La règle de base actée** : un agent = **un cerveau (LLM) + des bras (outils) + une mémoire (le graphe)**. Tout ce qui suit la spécifie.

---

## 1. LES AGENTS (le cerveau et les bras) — le plus grand trou

| # | Question à trancher | Propositions déjà passées | Requis | Statut |
|---|---|---|---|---|
| 1.1 | **Quels agents, quels rôles, combien ?** Rôle définitif de chacun (entrées → sorties → budget → conditions d'arrêt) | V0.2 §8.2 : *orchestrateur + 2 rôles logiques (explorateur, critique)* pour la 1ʳᵉ tranche, « le multi-agent n'est pas un but » · MIMIR : agents spécialisés · AXES : agents d'exploration d'hypothèses | D+I | **OUVERT** |
| 1.2 | **Quel(s) modèle(s) LLM derrière les agents ?** Fournisseur, modèle exact, hébergé/local, version épinglée, repli si panne, coût par décision budgété | V0.2 §8.2 : « un seul modèle peut suffire en 1ʳᵉ tranche » · contrainte : sorties structurées strictes, **le LLM ne produit jamais un chiffre** · W2-D : le coût du raisonnement entre dans la perte · Rien de décidé sur le fournisseur | D+I | **OUVERT** |
| 1.3 | **Mémoire des agents** : que retient un agent entre deux étapes, et où ? | Définition actée (toi) : *la mémoire = le graphe* · V0.2 : état de tâche + registre de branches · Interdit implicite : pas de mémoire conversationnelle non traçable | D+I | **OUVERT** (à formaliser) |
| 1.4 | **La boucle agent** : planifier → appeler un outil → évaluer → s'arrêter/exécuter. Spécification exacte, conditions d'arrêt, plafonds (recherches, appels, temps, coût), reprise après erreur | V0.2 §7.3/7.4 (budgets, arrêt obligatoire), §8 (rôles) · AV1 : module `research` **absent du code** | D+I | **OUVERT** |
| 1.5 | **Registre d'outils** : liste exacte des outils v1 (lecture prix, RPC, documents ; calcul de signaux ; écriture graphe) avec schémas JSON, timeouts, comportement en panne, journal | V0.2 §8.3 (contrat d'outil complet) · Règle : outils d'**action** réservés à l'exécution, jamais exposés à l'agent de recherche · Anti-injection (critère piste nationale) | D+I | **DIRECTION** |
| 1.6 | **Prompts système + schémas de sortie** de chaque agent (rien n'est écrit) : instructions, JSON schemas, quarantaine des champs inconnus, tests anti-injection | V0.2 §5.3 : « sorties LLM validées selon un schéma strict ; champs inconnus rejetés ou mis en quarantaine » | D+I | **OUVERT** |
| 1.7 | **Mode agents en démo vs inference** : en démo, les agents tournent-ils **en direct** (borné, sur données archivées — recommandé : c'est le produit) ou leurs sorties sont-elles rejouées ? En inference : providers, quotas, latence, coûts | V0.2 §13.2 : la démo exécute recherche + décision ; §11.2 : stack à choisir · F20-D8 : rejeu hors-ligne obligatoire pour la sûreté | D+I | **OUVERT** |

## 2. LE GRAPHE (le DFKG) — socle du projet, à spécifier pour de bon

| # | Question à trancher | Propositions déjà passées | Requis | Statut |
|---|---|---|---|---|
| 2.1 | **Schéma définitif v1** : objets, champs, enums, index, versionnement — un seul document qui fait foi (fini le v0 partiel) | V0.2 §6.4 (ontologie : Finance/EVM/Preuves) · AV1 §4 (16 tables, ULID, append-only) · MIMIR (chaîne Source→…→Outcome, six horloges) · Code : SQLite v0 | D+I | **PARTIEL** |
| 2.2 | **Les types de relation EXACTS** (ta question directe) : liste exhaustive — nom, sens, types sujet/objet autorisés, transitivité, statut de validation, qui peut les créer | RC : **4 familles** (preuve & dérivation · structure & exposition · mécanisme économique · contrainte & permission) mais **la liste interne n'est pas écrite** · MIMIR §5 : le record Relation (10 champs) et ses types à extraire et adapter · Invariant : `SUPPORTS` n'autorise **aucune** propagation causale | D+I | **OUVERT** |
| 2.3 | **DL/ML dans le graphe — oui/non/quoi ?** (ta deuxième question) : quel(s) modèle(s) ML, pour quelle tâche (résolution d'entités ? liens manquants ? anomalies ? priorisation ?), et comment la traçabilité reste intacte | Toi : « on peut l'adapter/améliorer avec du DL/ML, très expérimental » · AXES : embeddings/link prediction envisagés · A2 : « la valeur prédictive du graphe et du ML reste à établir » · Contrainte : aucune perte de reconstruibilité | D+I (principe) | **OUVERT** |
| 2.4 | **Construction du graphe (pipeline)** : extraction par type de source (structurée = règles ; textes = LLM + validation), canonisation/entités, dédoublonnage, qualité, snapshots point-in-time, politique de révision | V0.2 §6 (provenance, qualité) · W2-A/B (sources vérifiées, capteurs) · RC : six horloges · AV1 : module `quality` existe (v0) | D+I | **OUVERT** |
| 2.5 | **Stockage cible** : Postgres (recommandé) vs SQLite (actuel) vs base graphe ; moment de la migration | V0.2 §6.5 : Postgres recommandé, pas de base graphe sans benchmark · AV1 : Postgres, SQLite en test · Code : SQLite · A2 : pas de migration avant le concours | I (D peut rester SQLite) | **DIRECTION** |
| 2.6 | **Interrogation & inférence** : les requêtes dont la décision a besoin (expositions, chemins de dépendance, contradictions) ; règles d'inférence autorisées ; performance | AV1 §3 (contrats) · RC (invariants INV-DEPENDENCE…) | D+I | **OUVERT** |

## 3. LA DÉCISION (les logiques financières) — 1 cas figé ≠ système

| # | Question à trancher | Propositions déjà passées | Requis | Statut |
|---|---|---|---|---|
| 3.1 | **Record définitif des branches/hypothèses** : champs + cycle de vie complet (états, transitions) | V0.2 §7.1/7.2 · A2 : registre `branches` (module absent du code) · Code : 3 blocs figés | D+I | **PARTIEL** |
| 3.2 | **Génération des hypothèses** : par l'agent (ton exigence) — avec quels garde-fous ? (falsifiabilité obligatoire, pas de branche inventée sans critère de réfutation) | V0.2 §7.1 (branche = objet contrôlé, pas des paragraphes libres) · Toi : « ça se fait par l'agent avec son raisonnement » | D+I | **OUVERT** |
| 3.3 | **Recherche discriminante & VoI** : v1 = règle déterministe (« quel fait départage ? ») puis VoI derrière interface ; critère de passage | V0.2 §7.3 (score VoI/coût pour ordonner) · R1 : VoI derrière interface, repli déterministe, `VOI_NOT_ESTIMABLE` autorisé · A2 : T02 reportable | D (v1) | **DIRECTION** |
| 3.4 | **Scénarios & probabilités** : qui produit quoi (agent vs modèle), quand on gèle, comment on score plus tard (Brier/ECE) | F20-D10/A2 : qualitatif d'abord, probabilités seulement gelées et calibrées | D+I (D : qualitatif suffit) | **OUVERT** |
| 3.5 | **Règle de décision GÉNÉRALISÉE** : le moteur actuel est figé sur USDC (« transférer 100 de test »). Catalogue d'actions par persona : transférer ? convertir en stable ? réduire/sortir des positions ? ne rien faire ? ESCALATE ? + sizing (desk) et règle de trésorerie (DAO : réserves, runway) | W2-D : seuil d'action desk `x·(P_T−P_exec) > coût d'aller-retour` ; DAO : perte évitée conditionnelle + jours de runway · V0.2 §9.1 (chaîne de décision) | D+I | **PARTIEL** |
| 3.6 | **Abstention généralisée** : conditions + format (« INCONCLUSIVE + ce qui manque ») au-delà du cas USDC | RC : 3 sorties séparées (épistémique/économique/autorisation) · Chemin INCONCLUSIVE déjà prouvé sur USDC | D+I | **PARTIEL** |
| 3.7 | **Portefeuille & exposition** : lecture réelle (soldes on-chain) vs fixtures ; **double valorisation** (prix oracle vs prix réalisable = cœur de W2-B) ; modèle DAO vs desk | V0.2 §9.1 · W2-B (signaux « valeur retenue vs réalisable » mesurés) · Code : fixtures 500/350/100 | D+I | **PARTIEL** |

## 4. POLITIQUE & AUTORISATION (les verrous)

| # | Question à trancher | Propositions déjà passées | Requis | Statut |
|---|---|---|---|---|
| 4.1 | **Spécification finale des règles v1** + **flux REQUIRE_APPROVAL** (qui approuve, par quel canal : UI ? Telegram ? email ?) + versionnage | Code : 8 règles + attaques testées · AV1 : `policy` figée · Flux d'approbation **non implémenté** | D+I | **PARTIEL** |
| 4.2 | **Mapping politique ↔ enveloppe on-chain** : correspondance règle ↔ condition Zodiac + test de dérive | W2-C : exemple complet (rôle AGENT, caps, allowlist) ; table de correspondance systématique à écrire | D+I | **DIRECTION** |
| 4.3 | **Procédure d'incident / kill switch** : qui, quand, comment on communique, journal | W2-C : mécanique (1 tx, mesurée) ; le processus humain reste à définir | I (D : mentionné) | **DIRECTION** |

## 5. EXÉCUTION (déjà très couverte par W2-C — reste à construire)

| # | Question à trancher | Propositions déjà passées | Requis | Statut |
|---|---|---|---|---|
| 5.1 | **Signer v1** : clé jetable d'équipe en démo (env var, hors dépôt), direction produit (délégation ?), nonce/gas/idempotence | W2-C : EOA isolée membre du rôle, sans admin ; matrice 12 attaques · V0.2 §10.4 (modèle sécurité) | D+I | **DIRECTION** |
| 5.2 | **Catalogue d'intents v1** : actions autorisées (v1 : transfert ERC-20 ; v2 : swap ?) + schéma final | V0.2 §10.2 (champs de l'intent) | D | **OUVERT** |
| 5.3 | **Simulation + vérification du receipt** : règles exactes de contrôle + liens vers l'audit | Code : `verify.py` v0 · W2-C (runs C : rejets par la chaîne) | D | **PARTIEL** |
| 5.4 | **Les 5 runs de démo** : montage et exécution (ALLOW / DENY hors chaîne / DENY par la chaîne / kill switch / journal) | W2-C §(g) : plan complet, adresses vérifiées | D | **DIRECTION** (à exécuter) |

## 6. AUDIT & VÉRIFIABILITÉ (la promesse du produit)

| # | Question à trancher | Propositions déjà passées | Requis | Statut |
|---|---|---|---|---|
| 6.1 | **Format définitif du journal** : entrées, chaînage par hash, export, outil de vérification | Code : dossier v1 (sha256) · W2-C : `audit.jsonl` chaîné | D+I | **PARTIEL** |
| 6.2 | **Vérificateur tiers (reconstructibilité, essai T10)** : un tiers rejoue et recalcule la décision — l'outil | A2 : T10 = premier essai du lot (non négociable) | D | **OUVERT** |
| 6.3 | **Ancrage on-chain du dossier (EAS)** : retenu ou pas pour v1 | V0.2 §10.6 : étudié, reporté si menace le flux · Chaîne : EAS présent sur Base Sepolia | — | **REPORTÉ** (à confirmer) |

## 7. APPRENTISSAGE & ÉVALUATION (la boucle qui révise)

| # | Question à trancher | Propositions déjà passées | Requis | Statut |
|---|---|---|---|---|
| 7.1 | **Outcomes & calibration** : enregistrement du résultat réel, scoring (Brier/ECE, Wilson), révision des méthodes | V0.2 §9.3/12 · W2-D : protocole complet prêt à geler | I (post-concours surtout) | **OUVERT** |
| 7.2 | **Replay engine (PIT)** : horloge simulée, marquage « REPLAY », données admissibles à l'instant T, snapshots | V0.2 §6.2/13.2 · Code : `--replay` partiel · RC : INV-PIT | D | **PARTIEL** |
| 7.3 | **Jeux DEV / EVAL** : quels épisodes dans quel jeu, gel, embargo | W2-D §(f) — fait partie des 12 points | D+I | **OUVERT** |

## 8. INTERFACE & OPÉRATIONS

| # | Question à trancher | Propositions déjà passées | Requis | Statut |
|---|---|---|---|---|
| 8.1 | **Interface** : périmètre démo (dossier de décision + refus + journal) vs produit (alertes, file d'approbation, monitoring de l'agent) | AV1 : page audit v0 (HTML) · V0.2 §5.1 (interface minimale) | D (minimal) | **PARTIEL** |
| 8.2 | **Déploiement, secrets, monitoring** : où tourne quoi (Render+Neon gratuits), CI, alerte sur action agent | AV1 §5 (décisions déjà posées) · CI existe (GitHub Actions) | D+I | **DIRECTION** |

## 9. GOUVERNANCE DE SPÉCIFICATION

- **9.1 Ordre de traitement proposé** (les fondations d'abord — tout le reste en dépend) :
  **Bloc A — Agents** (1.1→1.7, dont le modèle : 1.2) → **Bloc B — Graphe** (2.1→2.4, 2.6, dont relations exactes : 2.2 et DL/ML : 2.3) → **Bloc C — Décision généralisée** (3.1→3.7) → puis le reste (4-8), en réutilisant W2-C/W2-D déjà mûrs. **Le document technique s'écrit APRÈS A-C.**
- **9.2 Nouveau gel (v2)** : `FREEZE_V1` est périmé par les corrections (autonomie, cible, épisodes) — le remplacer une fois A-C tranchés.
- **9.3 Références croisées** : les **12 points W2-D §(f)** (mesure) appartiennent au même atelier de décision ; la carte F20 (20 décisions) reste la référence **historique** de l'existant, plusieurs lignes périmées.
- **9.4 Principe d'intégration (remarque d'équipe du 15/10)** : pour chaque brique, **intégrer l'existant éprouvé d'abord** (SDK LLM standard, Postgres, Zodiac, Chainlink, Blockscout, templates UI), et construire seulement le différenciant (graphe de collatéral, décisions vérifiables, abstention, double enveloppe). L'inventaire « intégrer vs construire » sera établi bloc par bloc.
- **9.5 Livrable suivant de ce chantier** : une **note de décision par bloc** (A, puis B, puis C) — options, conséquences, recommandation, coût de changement — pour trancher en revue d'équipe, puis le gel v2.

---

*Tout est reproductible depuis `D:\orvyren_core`. Ce document ne remplace pas les rapports cités : il les organise en questions à trancher.*
