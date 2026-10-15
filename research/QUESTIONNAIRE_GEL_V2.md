# QUESTIONNAIRE DE GEL v2 — ORVYREN
**15 octobre 2026.** Les 9 blocs du système sont étudiés (B1 agents · B2 graphe · B3 décision · B4 politique · B5 exécution · B6 audit · B7 évaluation · B8 UI/Ops · B9 gouvernance). Chaque étude contient : recommandations + options + questions ouvertes. Ce questionnaire les rassemble — **réponds dans le chat par numéro** (ex. « A1=MA-B, A2 ok, ... »). Les recommandations des sous-agents sont marquées ⭐ : si tu valides tout, réponds « j'accepte toutes les ⭐ sauf… ».
*Une fois tes réponses faites : je prépare le paquet de gel v2, puis j'écris les 4 documents.*

---

## A — AGENTS & ARCHITECTURE v1 (le plus structurant)
- **A1. Multi-agent réel** : ⭐ **MA-B** = instances séparées minimales (orchestrateur + critique en processus distincts, journaux propres, mêmes outils bornés) — +2-4 j, sans refonte ; alternative MA-C = 4 services complets (~3× coût, risque cohérence) ; MA-A = monolithe à rôles (« pas réel »). → **Ton choix ?**
- **A2. Modèles** : ⭐ principal = **DeepSeek flash** ; secondaire = **MiMo flash** (critique). Clés API : tu fournis les deux ? Plafond budget ? (coût réel mesuré : **0,004–0,036 $/décision**).
- **A3. Critique sur 2ᵉ modèle dès v1** (adversarial cross-modèle) : ⭐ oui.
- **A4. Mémoire interne** : ⭐ design `agent_journal` B1 (table append-only séparée du graphe ; promotion uniquement par validateurs déterministes ; branches LLM à **poids nul**) — OK ?
- **A5. Budgets par décision** : ⭐ ≤30 appels LLM · ≤12 outils · ≤10 min · ≤0,10 $ — OK ou ajuster ?
- **A6. Rétention du journal** : ⭐ intégral (volume faible).

## B — GRAPHE (DFKG)
- **B1. Catalogue** : ⭐ **34 relations / 4 familles + record 17 champs** → base du gel ? Des types à ajouter/retirer ?
- **B2. Stockage** : ⭐ SQLite pour le concours ; **Postgres (Neon free permanent)** cible, migration après le 20/10 — OK ?
- **B3. DL/ML v1** (ta demande : implémenter, pas théoriser) : ⭐ **ML-1** embeddings (pgvector, recherche sémantique) + **ML-2** détection d'anomalies **hors chemin décisionnel** (étiquette MODEL-INFERRED) ; GNN/link-prediction post-concours ; règle : **rien d'appris dans le confirmatoire** — OK ?
- **B4. Techniques** (recos prêtes, je les tranche avec toi en revue) : anti-reorg ⭐2 blocs démo / safe+finalized prod · proxies ⭐s suivre l'implémentation · quantités ⭐une source par quantité · conditions de mécanisme ⭐enum (pas de DSL) · export ⭐PROV-O annexe · multi-chaînes ⭐un graphe + vues · Neon en vidéo ⭐local prioritaire.

## C — DÉCISION
- **C1.** ⭐ Discipline **ACH** (falsifiabilité obligatoire, réfutation d'abord — pas la matrice seule) + record **12 champs** + cycle **7 états** — OK ?
- **C2.** ⭐ **RDOF v1** : ordonnancement **déterministe** par falsification (« quel prédicat réfute le leader au moindre coût »), testé contre l'ordre fixe **AVANT** toute VoI — OK ?
- **C3.** ⭐ Abstention **A1–A5** + format enrichi (ce qui manque / ce qui changerait le verdict / delta décision) + table **ESCALATE vs NO-ACTION** — OK ?
- **C4. Catalogues d'actions** : ⭐ 8 actions DAO + 4 desk (liste §d du B3) ; v1 implémentées = transfert (démo) ; le reste spécifié/simulé — tu valides la liste ?
- **C5. Conventions de prix** (close vs low — impacte TOUS les seuils, à figer avant G1) : (a) low partout (prudent) · (b) close partout · (c) ⭐ double : alerte sur low, décision sur close+low. → **Choix ?**
- **C6.** ⭐ Horizon de classe **H_class = 6 h** — OK ?
- **C7. G6** (P(obligation), scénarios p_s) : qui signe (toi ? membre désigné ?) — méthode ⭐ sensibilité publiée.

## D — POLITIQUE & AUTORISATION
- **D1.** ⭐ Set v1 = **14 règles** (8 existantes + 6 ajouts : fonction scopée, exposition max, fraîcheur d'intent, pause/kill, alignement d'enveloppe, budget) — OK ?
- **D2. Flux d'approbation** : ⭐ démo = **file + signature EIP-712** du mandant (TTL 2 h) ; produit = file multi-rôles + Safe queue/Delay — OK ? Canal démo : ⭐ fichier local (pas de bot tiers).
- **D3.** ⭐ Asymétrie : **réduire** un plafond = immédiat ; **augmenter** = procédure complète — OK ?
- **D4. Kill switch** : ⭐ K0 pause ≤5 min ; K1 `assignRoles(false)` ≤60 min ; **qui détient les clés du Safe 2/3 démo** (toi + 2 membres ?)
- **D5.** EAS pour le policy_hash : ⭐ reporté post-concours — OK ?

## E — EXÉCUTION
- **E1. Signer démo** : ⭐ clé jetable en variable d'environnement, gaz faucet, détruite après — OK ? **Librairie de signature** : (a) ⭐ eth-account (pip, isolé dans le service signataire) · (b) cast/Foundry (binaire) · (c) secp256k1 maison — choix ?
- **E2. Montant du run ALLOW** : (a) ⭐ 100 USDC (cohérent plan W2-C, plafond tx = 100) · (b) 50 USDC. → choix ?
- **E3.** ⭐ swap/approve = **simulés v1** ; Aave = v2 — OK ?
- **E4. Après reorg** : ⭐ escalade humaine (pas de ré-émission automatique) — OK ?
- **E5.** Deux USDC sur Base Sepolia (Circle `0x036C…` / Aave `0xba50…`) : ⭐ runbook nomme les deux (transferts → Circle ; lectures marché → Aave) — OK ?

## F — AUDIT & VÉRIFIABILITÉ
- **F1.** ⭐ Journal unifié **3 flux chaînés SHA-256** + paquet 12 pièces + bundle_digest (correction : SHA-256 partout, pas keccak) — OK ?
- **F2.** ⭐ Vérificateur tiers `python -m orvyren.verify` (offline/rpc/mutate-test) — OK ? (pièce T10, non négociable)
- **F3. Ancrage** : ⭐ empreinte publiée **obligatoire** ; EAS seulement si run E + T10 verts **avant le 18/10 23:59** — OK ?
- **F4.** Textes « ce que l'audit prouve / ne prouve pas » (FR+EN) : ⭐ recopiés verbatim dans le paquet — OK ?

## G — ÉVALUATION
- **G1. Jeux** : ⭐ DEV = USDC + stETH (backtest) + calme 2022-23 ; **EVAL = rsETH + USD0++ + calme 2025-26** ; xUSD = qualitatif — OK ?
- **G2.** ⭐ Embargo calibration croisée (les quantiles P99 ne recouvrent PAS les fenêtres CALME EVAL) — OK ?
- **G3.** ⭐ Étiquettes : **A0** = ne rien faire · **A1** = seuil · **A2** = agent · **B0** = placebo (M≥200) ; l'ancienne règle D6 du code → **AX0** — OK ?
- **G4.** GO pour implémenter `loss.py` + `comparators.py` + `calibration.py` (~1,5 j) et produire **5-10 prévisions gelées DEV avant le 20/10** ? ⭐ oui (livrable minimal opposable).

## H — UI & OPS
- **H1.** ⭐ Écrans de démo (**12** ; minimum vidéo = 6) — à valider sur la liste B89.
- **H2.** ⭐ Interface v1 = **lecture seule** ; approbations = V1.5 — OK ?
- **H3.** ⭐ Hébergement : démo **locale hors-ligne** + Render web free + **Neon** (pas de PG Render qui expire à 30 j) — OK ?
- **H4.** ⭐ Ajouts CI (secrets-check, index ADR, build docs, check journal) — OK ?

## I — GOUVERNANCE & DOCUMENTS
- **I1.** ⭐ Protocole de gel : **ADR** (Nygard/MADR) + `docs/decisions/` + paquet de gel hashé remplaçant FREEZE_V1 — OK ?
- **I2.** ⭐ **Règle 0 : aucune mention de MIMIR** ; les 7 concepts repris sont **redéfinis en propre** (liste B89 §B7 : horloges temporelles, chaîne de provenance, record de relation, labels épistémiques, identifiants canoniques, nom du graphe, pré-enregistrement haché) — OK ?
- **I3.** ⭐ Les **4 documents finaux** : (1) explicatif 1-2 p avec schémas · (2) technique complet 30-50 p FR · (3) propositions/écartés/V2 · (4) plan d'implémentation — OK ?
- **I4.** Rédaction dans cet ordre après tes réponses — OK ?

## J — SOUMISSION (hors système, impératif calendaire)
- **J1.** Email organisateurs : **GO d'envoi** ? (toujours en attente)
- **J2.** Wallet testnet : qui crée/finance (toi ? un membre ?) — nécessaire pour le run E et la pièce ⑥.
- **J3.** Kit de démo W3-D : GO de lancement dès que le wallet existe ?

---
*Défaut : tout point non tranché explicitement recevra une proposition de défaut dans le paquet de gel, marquée comme telle.*
