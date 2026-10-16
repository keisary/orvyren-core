# ORVYREN — GEL v2 (registre des décisions gelées)

**15 octobre 2026.** Ce document remplace `FREEZE_V1.md` (périmé par les corrections successives). Il fige les décisions v1 sur la base du **questionnaire de gel du 15/10** (archivé hors dépôt — voir `README.md` §Archives) et des réponses d'équipe : **toutes les recommandations ont été acceptées**, avec deux ajustements (UI/Ops : full local, vidéo reportée ; Soumission : gérée par l'équipe) — et intègre les **confirmations des organisateurs du 14/10/2026**.

## 0. Confirmations externes (organisateurs — 14 octobre 2026)
1. **Preuve d'exécution** : le **testnet est pleinement accepté** — agent sur **Base Sepolia** + hashes réellement vérifiables (reçus, blocs, émetteur, destinataire) satisfont l'Appendice 2 ; **mainnet non requis**.
2. **Documents d'inscription** : pièces d'identité **nationales acceptées** (à la place des passeports) ; passeports à compléter seulement si finalistes.
3. **Modèles IA** : **aucune restriction** ; les modèles à restrictions régionales (GPT, Claude…) sont à la charge de l'équipe côté accès → nos choix (DeepSeek, MiMo) n'ont pas cet enjeu.
4. Inscription à faire **au plus vite** (fermeture anticipée possible). **Gérée par Jovanny.**

## 1. A — Agents
| # | Décision | Statut |
|---|---|---|
| A1 | **Multi-agent réel — MA-B** : instances séparées minimales (orchestrateur + critique adversarial, processus distincts, journaux propres, outils bornés) ; extension multi-agents complète plus tard, sans refonte | GELÉ |
| A2 | Modèles via API : **DeepSeek flash** (principal) + **MiMo flash** (secondaire/critique) ; clés fournies par l'équipe ; plafond mensuel défaut : 20 $ | GELÉ (défaut) |
| A3 | Critique sur **2ᵉ modèle dès v1** (adversarial cross-modèle) | GELÉ |
| A4 | **Mémoire interne** : `agent_journal` append-only **séparé du graphe** ; promotion uniquement par validateurs déterministes ; branches LLM à **poids nul** | GELÉ |
| A5 | Budgets par décision : **≤30 appels LLM · ≤12 outils · ≤10 min · ≤0,10 $** ; arrêt fail-closed | GELÉ |
| A6 | Rétention du journal : **intégrale** | GELÉ |

## 2. B — Graphe
- **B1** — Catalogue **34 relations / 4 familles** (preuve & dérivation 8 · structure & exposition 15 · mécanisme économique 3 · contrainte & permission 8) + **record 17 champs**, enum machine-vérifiable + tests de conformité. **GELÉ**
- **B2** — **SQLite pour le concours** → **PostgreSQL/Neon** cible post-concours ; `store.py` seul point d'accès. **GELÉ**
- **B3** — **ML v1** : ML-1 embeddings (pgvector, recherche sémantique) ; ML-2 anomalies **hors chemin décisionnel** (MODEL-INFERRED) ; GNN post-concours ; **rien d'appris dans le confirmatoire**. **GELÉ**
- **B4** — Techniques : anti-reorg 2 blocs (démo) / safe+finalized (prod) ; proxies = suivre l'implémentation ; **une source par quantité** ; conditions en **enum** ; export PROV-O en annexe ; un graphe + vues multi-chaînes ; local prioritaire. **GELÉ**

## 3. C — Décision
- **C1** — Discipline **ACH** (falsifiabilité obligatoire, réfutation d'abord — pas la matrice seule) + record d'hypothèse **12 champs** + cycle **7 états**. **GELÉ**
- **C2** — **RDOF v1** déterministe (« quel prédicat réfute le leader au moindre coût ») ; testé contre l'ordre fixe **avant** VoI (derrière interface, `VOI_NOT_ESTIMABLE` autorisé). **GELÉ**
- **C3** — Abstention **A1–A5** + format enrichi + table **ESCALATE vs NO-ACTION**. **GELÉ**
- **C4** — Actions : **8 DAO + 4 desk** ; v1 implémenté = transfert borné (démo) ; reste simulé. **GELÉ**
- **C5** — Prix : **double convention** — alerte sur le **low**, décision sur **close + low**. **GELÉ**
- **C6** — **H_class = 6 h**. **GELÉ**
- **C7** — G6 (P(obligation), p_s) : signé par le chef d'équipe (défaut) + sensibilité publiée. **GELÉ (défaut)**

## 4. D — Politique
- **D1** — Set v1 = **14 règles**, codes de refus stables, fail-closed. **GELÉ**
- **D2** — Approbation : démo = **file + signature EIP-712** (TTL 2 h, canal local) ; produit = file multi-rôles + Safe queue/Delay. **GELÉ**
- **D3** — Asymétrie : réduire = immédiat ; augmenter = procédure complète. **GELÉ**
- **D4** — Kill switch : **K0 ≤5 min · K1 ≤60 min** ; Safe démo 2/3 = chef d'équipe + 2 (défaut). **GELÉ (défaut)**
- **D5** — EAS policy_hash : **reporté post-concours**. **GELÉ**

## 5. E — Exécution
- **E1** — Signer démo : **clé jetable env var** (jamais dépôt/logs/prompts), gaz par robinets gratuits, **détruite après la démo** ; librairie : **eth-account** isolé (défaut) ; produit : backend de clé remplaçable (hors v1). **GELÉ (défaut)**
- **E2** — Run ALLOW : **100 USDC**. **GELÉ**
- **E3** — swap/approve **simulés v1** ; Aave = v2. **GELÉ**
- **E4** — Après reorg : **escalade humaine**. **GELÉ**
- **E5** — Runbook : **deux USDC distincts** Base Sepolia (Circle = transferts ; Aave = lectures) nommés. **GELÉ**

## 6. F — Audit
- **F1** — Journal **3 flux chaînés SHA-256** + paquet 12 pièces + bundle_digest. **GELÉ**
- **F2** — **Vérificateur** `python -m orvyren.verify` (T10). **GELÉ**
- **F3** — **Empreinte publiée obligatoire** ; EAS conditionnel (run E + T10 verts avant le 18/10 23:59). **GELÉ (conditionnel)**
- **F4** — Textes « prouve / ne prouve pas » FR+EN verbatim. **GELÉ**

## 7. G — Évaluation
- **G1** — DEV = USDC + stETH + calme 2022-23 ; **EVAL = rsETH + USD0++ + calme 2025-26** ; xUSD qualitatif. **GELÉ**
- **G2** — **Embargo calibration croisée**. **GELÉ**
- **G3** — **A0/A1/A2/B0** (+ AX0). **GELÉ**
- **G4** — GO : `loss.py` + `comparators.py` + `calibration.py` (~1,5 j) + **5-10 prévisions gelées DEV avant le 20/10**. **GELÉ (GO)**

## 8. H — UI & Ops *(ajusté par l'équipe, 15/10)*
- **H1** — Spécification d'UI (base : liste des écrans) ; **préparation vidéo REPORTÉE** (dépend de la construction de l'interface). **GELÉ (ajusté)**
- **H2** — Interface v1 = **lecture seule** ; approbations V1.5. **GELÉ**
- **H3** — **Hébergement : FULL LOCAL pour commencer** ; Render/Neon = options ultérieures. **GELÉ (ajusté)**
- **H4** — Ajouts CI acceptés. **GELÉ**

## 9. I — Gouvernance & documents
- **I1** — Protocole de gel : **ADR** + `docs/decisions/` + paquet hashé (ce document = v1 du paquet). **GELÉ**
- **I2** — **Règle 0 : aucune mention de MIMIR** dans les documents ; concepts repris **redéfinis en propre** (horloges temporelles, chaîne de provenance, record de relation, labels épistémiques, identifiants canoniques, nom du graphe, pré-enregistrement haché). **GELÉ**
- **I3** — Les **4 documents finaux** (explicatif · technique · propositions/écartés · plan d'implémentation). **GELÉ**
- **I4** — Ordre : gel → documents → implémentation. **GELÉ**

## 10. J — Soumission
- **J1** — Inscription + dépôt : **gérés par Jovanny** ; email **envoyé et répondu** (voir §0).
- **J2** — Wallet testnet : **aucun argent réel** — robinets publics gratuits (ETH de test + USDC de test) ; clé jetable détruite après ; procédure dans le kit de démo.
- **J3** — Kit de démo (W3-D) : **GO — en construction**.

## 11. Points restants (non bloquants, défauts proposés)
1. Plafond budget API (défaut : 20 $/mois). 2. Détenteurs clés Safe 2/3 démo (défaut : chef d'équipe + 2). 3. Signature G6 (défaut : chef d'équipe). 4. TTLs : intent 15 min, approbation 2 h. 5. Fenêtres CALME EVAL précises (à figer en G1, proposition B7).

*Références internes : les matériaux de recherche (questionnaire de gel, études B1→B9, matières brutes) sont archivés hors dépôt (voir README, section Archives). Confirmations organisateurs du 14/10/2026.*
