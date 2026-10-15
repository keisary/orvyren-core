# raw_b89 — Lectures internes (constats et lignes clés), 15/10/2026

Extraits de travail (fichier:ligne) ayant servi à rédiger `research/B89_UI_GOUVERNANCE_ETUDE.md`.

## SYSTEME_ZONES_OMBRE.md (§8-9)
- §8.1 Interface : « périmètre démo (dossier de décision + refus + journal) vs produit (alertes, file d'approbation, monitoring de l'agent) » — AV1 page audit v0 (HTML) ; V0.2 §5.1 ; statut PARTIEL.
- §8.2 Déploiement : « où tourne quoi (Render+Neon gratuits), CI, alerte sur action agent » — statut DIRECTION.
- §9.1 Ordre : Bloc A (agents) → Bloc B (graphe) → Bloc C (décision) → puis 4-8.
- §9.2 : nouveau gel (v2) — remplacer FREEZE_V1 une fois A-C tranchés.
- §9.4 : principe d'intégration (intégrer l'existant éprouvé d'abord ; construire le différenciant).
- §9.5 : livrable suivant = note de décision par bloc → gel v2.

## ARCHITECTURE_V1.md §5-6
- §5 : Python 3.11 stdlib+fastapi/pydantic/psycopg/httpx ; `--replay` obligatoire ; secrets jamais dans le dépôt ; CI GitHub Actions (unittest + pipeline + replay) ; branches main/feat ; licence MIT ; hébergement Render web gratuit + Postgres Neon.
- §6 : exclus volontairement — microservices, broker, base graphe, multi-agent parallèle, EAS, ERC-7715, mainnet réel, auth multi-utilisateurs, interface multi-vues.
- §7 : dépôt GitHub pas encore créé (action équipe) ; collaborateurs à fournir ; GO sur valeurs.

## src/orvyren/ui/server.py (page audit v0)
- « Offline, stdlib-only HTTP server » ; routes `GET /` (dernier dossier HTML, 503 propre sinon), `GET /api/dossier`, `GET /api/health` (`{"ok": true, "version": …}`).
- « Read-only handler; every route is guarded so a request cannot kill it. » ; GET/HEAD uniquement ; `Cache-Control: no-store` ; « No third-party dependency, no external asset, no JavaScript. » ; bind par défaut 127.0.0.1:8000.

## B1_AGENTS_ETUDE.md §6 (démo)
- §6.2 : non-déterminisme établi (Thinking Machines Lab 2025-09-10 ; LLM-42 arXiv:2601.17768) → « rejouer les réponses enregistrées est déterministe par construction ».
- §6.3 : 3 modes — REPLAY-JOURNAL (bit-à-bit), LIVE-REPLAY (recalcul borné), LIVE ; étiquettes à l'écran.
- §6.4 : table des 9 écrans (Fenêtre&PIT ; Graphe ; Branches ; Réflexions par agent ; Recherche&coût ; Décision ; Verrous ; Refus&quarantaine ; Coût par décision).
- §6.5 : coût replay complet < $0,10 [MESURÉ].
- §1.3-1.5 : Options A/B/C ; recommandation R-1 = Option C monolithe ; règles préparant B sans refonte (journal par rôle ; objets sérialisables) ; coût B ~30 appels ≈ $0,036/décision ; littérature cohérence multi-agent (arXiv:2603.10062, arXiv:2606.24535).

## W2C_enveloppe_execution.md §(d) et §(g)
- §d.1 : chaîne à 10 étapes (LLM → politique → calldata → registre d'intentions → signer → RPC épingle → Safe/Roles → effet → journal → surveillance) ; invariants I1-I5.
- §d.2 : rotation = assignRoles(nouvelle,true) + assignRoles(ancienne,false), 1 tx DAO.
- §d.3 : quotas locaux (glissant 24 h), idempotence keccak(intention), gaz = ligne séparée, simulation pré-vol.
- §d.4 : kill switch K0-K3 (K1 = 1,64 s/bloc Base mesuré 15/10 ; latence réelle = coordination humaine).
- §d.5 : journal JSONL chaîné (record_hash = keccak(prev||canonical_json)) ; 5 règles de vérifiabilité ; policy_version.
- §(g) : 5 runs — A (ALLOW 50 USDC), B (DENY hors-chaîne B1/B2), C (DENY chaîne C1-C4 + frontière de période), kill (K1 mesuré), journal/audit ; prérequis wallet testnet = chemin critique ; §g.7 : ce que la démo ne prouve PAS (prix, absence de bug, expiration, annulation, conformité) ; §g.8 : parité production.

## dist/docs/ORVYREN_EXPLIQUE_SIMPLEMENT.md — Partie 5 (méthode)
- 4 questions : qu'est-ce qui dépend / coût de changer / vérifiable / quelle preuve ferait changer d'avis ; si vérifiable → essai pré-enregistré ; si valeur → décision datée ; « toute révision est datée et versionnée — jamais une réécriture silencieuse ».

## DECISIONS_ET_PROCHAINES_ETAPES.md
- D3 (15/10) : ORVYREN autonome (pas une brique de MIMIR) ; héritage sémantique ; D9bis abandonnée.
- D9 : livrables concours EN ; travail interne FR.
- §4.1 : 6 pièces soumission ; pièce ⑥ (hashes tx réelles) = manquante critique ; wallet/faucet côté équipe.
- §5 : posture d'intégration (catalogue de briques intégrables).

## B2_GRAPHE_ETUDE.md
- §2.3/§2.4 : Neon free permanent ; Render free PG expire 30 j ; SQLite base du concours ; migration ≈ 1-2 j post-concours ; QO-8 (100 CU-h, scale-to-zero 5 min — suffisant pour la vidéo ? sinon SQLite local + miroir).
- §1.3 : trois horloges minimales + validité + révision (proposition) ; appelées « six horloges » chez la source.
- §5.3 : v1 = rien d'appris dans le chemin de décision ; embeddings pgvector en appoint ; HYP-07R post-concours ; tout sortant ML = MODEL-INFERRED + provenance.

## AXES_AMELIORATION_FULGURANTE.md §1
- §1.2 identifiants canoniques (VAR/SER/EVT/OBS/CLM/REL/SCN/FCT/THS/OUT).
- §1.3 six horloges : event, publication, observation, effective, validity, revision.
- §1.4 chaîne de provenance : Source → Observation → Extraction → Claim → Relation → Hypothesis → Prediction → Outcome.
- §1.5 record de relation : 10 champs (relation_id, cause/effect, mechanism, conditions, regime/horizon scope, epistemic_status, sign_prior, provenance, lifecycle).
- §1.6 labels : FACT, REPORTED, STATISTICAL, CAUSAL-DOCUMENTED, CAUSAL-HYPOTHESIS, MODEL-INFERRED, REJECTED ; statuts DECIDED/DIRECTION/CANDIDATE/OPEN/REJECTED/DEFERRED.

## État technique constaté (15/10/2026)
- `.github/workflows/tests.yml` : unittest + `run_pipeline.py` + `collect_corpus.py --offline`.
- `evidence/` : dossier usdc (md/html), decision json, policy_execution_demo.json, graph.sqlite, etc.
- README : « Quick start (no dependencies, no network, no secrets) » ; replay offline by design ; byte-stabilité décrite.
- `docs/` : REVIEW_KIT.md, SECURITY_SELF_ASSESSMENT.md, partage/ ; `docs/decisions/` n'existe pas encore (à créer, ADR-0001).
- git status : propre ; pas de commit fait par cette étude (règle subagent).
