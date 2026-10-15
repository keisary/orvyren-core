# ORVYREN — REGISTRE DES DÉCISIONS & PROCHAINES ÉTAPES

**15 octobre 2026** (matin UTC) · Décompte : soumission **20 octobre 2026, 15 h 59 UTC** (23 h 59 heure de Singapour) = **5 jours 8 heures**.
*Date de soumission vérifiée sur la page officielle le 15/10 : « Registration and submission deadline — 20 October 2026. Due to high anticipated interest, the organizers reserve the right to close registration early without prior notice, while the submission deadline for all registered teams remains as 20 Oct. » Une fiche tierce (bjultra.com) indiquait le 16/10 — écart écarté (piste/source non officielle).*

---

## 1. DÉCISIONS TRANCHÉES (validées)

| # | Décision | Date |
|---|---|---|
| D1 | Concours : Shenzhen International FinTech 2026, International Track, **thème F** (Agent Wallet / Autonomous On-chain Wallet), équipe Ascencia Keyce Togo | 12/10 |
| D2 | **Exécution autonome bornée** : l'agent *exécute seul* dans l'enveloppe ; le LLM ne touche jamais aux clés ; la politique vit hors du LLM | 14–15/10 |
| D3 | **ORVYREN est autonome** (pas une brique de MIMIR) ; héritage sémantique de MIMIR (ontologie, six horloges, labels épistémiques). D9bis abandonnée | 15/10 |
| D4 | **Cible principale : trésoreries on-chain d'organisations (DAOs/protocoles)** d'abord ; desks de trading ensuite si le temps ; banques = phase 2 (vision) | 14–15/10 |
| D5 | **Deux personas, objectifs distincts** : DAO = prévision/anticipation du risque ; desk = rentabilité | 14–15/10 |
| D6 | **Problème officiel = candidat B** : « la valorisation retenue s'écarte silencieusement du prix réalisable ; la dégradation est annoncée des jours à des semaines à l'avance par des signaux publics dispersés » | 15/10 |
| D7 | Sécurité : **testnet par défaut** pour la preuve on-chain ; jamais de fonds réels ; pas de jeton, pas de promesse de rendement (conformité) | 13–14/10 |
| D8 | Process : autonomie longue accordée (recherche/exécution sur disque) ; les agents ne touchent pas à git ; **l'email aux organisateurs ne part jamais sans validation** du chef d'équipe | 13–15/10 |
| D9 | Langues : livrables du concours en **anglais** ; travail interne en **français** | 13/10 |

## 2. DÉCISIONS DE CONCEPTION MÛRES (recommandées par la recherche — prêtes à geler)

| Sujet | Décision recommandée | Réf. |
|---|---|---|
| Enveloppe d'exécution (phase 1) | **Zodiac Roles v2 sur Safe** (bytecode vérifié identique sur Base Sepolia) + signer **EOA isolé** sans droits d'admin + **kill switch** en 1 transaction + journal opposable. Limites assumées : pas d'expiration native ; rafale de frontière de période → compteur glissant hors chaîne en premier verrou | W2-C |
| Épisodes | Démo = **rsETH/KelpDAO (avril 2026)** ; évaluation quantitative = **USD0++ (janv. 2025)** et **USDC (mars 2023)** ; backtest long = **stETH (2022)** ; bad debt Aave = conséquence du rsETH (pas un épisode à part) | W2-A/B, W3 |
| Données | **100 % gratuit** : archive on-chain via `eth.drpc.org`→`blastapi` (testé 2021→2026) ; prix minute via Binance/OKX/Kraken/Bitstamp/DeFiLlama ; aucune dépendance payante | W2-A, W3 |
| Mesure | **Fonction de perte corrigée** (richesse + actions faisables) ; protocole **A0/A1/A2/B0 placebo** ; seuils par persona ; **pré-enregistrement avant toute évaluation** | W2-D |
| Signaux | Table des familles + seuils candidats (décote ≥ 50 bps/15 min ; dispersion > 100 bps ; divergence oracle > 100 bps/1 h ; etc.) ; 3–5 signaux à implémenter d'abord | W2-B |
| Positionnement | « **Vendre la décision, offrir l'exécution** » ; différenciation = décision vérifiable × graphe de collatéral × abstention documentée ; **intégrer** les standards existants (posture d'intégration §5) | W2-E |

## 3. À TRANCHER (ouvert)

1. **Les 12 points de W2-D §(f)** : objet de l'objectif ; unité de compte ; convention de valorisation ; règle de ré-entrée ; seuils chiffrés par persona ; P(obligation) ; scénarios desk ; jeux DEV/EVAL ; niveau d'autonomie précis ; budget de risque par épisode ; coût du capital ; responsable du gel.
2. **Édits du cadre §04/05/06** (listés en fin de `VAGUE2_SYNTHESE.md` §6).
3. **xUSD** : réintégrer au quantitatif ? (série 457 h trouvée par W3-C, après l'exclusion prononcée par W2-D)
4. **Inventaire d'intégration** : briques à intégrer vs à construire (Safe, Zodiac, Chainlink, Blockscout, DeFiLlama, ERC-7715… = à intégrer ; graphe de collatéral + décision vérifiable + abstention = à construire).
5. **Email organisateurs** : 2 questions (testnet accepté comme preuve ? ; carte d'identité acceptable pour passeports expirés ?) — message prêt, **en attente de validation**.
6. **Phase construction** : quand et dans quel ordre (kit de démo testnet d'abord ?).

## 4. PROCHAINES ÉTAPES — PAR HORIZON

### 4.1 Cette semaine — LA SOUMISSION (priorité absolue, prime sur la construction)

**Les 6 pièces et leur état :**

| # | Pièce | État | Matière disponible |
|---|---|---|---|
| 1 | Documentation technique (architecture, algorithmes, sécurité) | À assembler **EN** | V0.2, ARCHITECTURE_V1, FREEZE_V1, VAGUE2, CADRE |
| 2 | Deck ≤ 10 min | À construire | Synthèse + pitch W2-E (« vendre la décision ») |
| 3 | Vidéo démo ≤ 5 min | À tourner (après la démo) | Script à écrire ; jamais en direct |
| 4 | Code source (README, lien GitHub, instructions, tests) | **Prêt sur disque** (221 tests verts) | Push GitHub côté équipe + README EN |
| 5 | Rapport d'auto-évaluation sécurité (permissions + risques connus) | À assembler **EN** | W2-C (matrice 12 attaques, limites), SECURITY_SELF_ASSESSMENT (Astra) |
| 6 | **Preuves d'exécution = hashes de transactions réelles** | ⚠ **PIÈCE MANQUANTE CRITIQUE** — la démo Base Sepolia n'a pas été exécutée | Kit à produire (W3-D) ; wallet testnet + faucet côté équipe |

**Actions, par responsable :**
- **Équipe (aujourd'hui/demain)** : ① valider + envoyer l'**email aux organisateurs** (il conditionne l'inscription ; inscriptions fermables tôt) ; ② créer/financer le **wallet testnet** Base Sepolia (faucet) ; ③ créer le dépôt GitHub et pousser (ou donner le go).
- **Moi (sur go)** : **W3-D** = kit de démo testnet → exécution des 5 runs (ALLOW / DENY hors chaîne / DENY par la chaîne / kill switch / journal) → hashes + reçus ; assemblage EN des pièces ① et ⑤ ; squelette du deck ②.
- **Ensemble** : vidéo ③ ; soumission **avant le 20/10 15 h 59 UTC**, tampon le 19/10.
- **Risques** : (a) recevabilité des documents d'identité (question email pendante) ; (b) fermeture anticipée des inscriptions ; (c) la pièce ⑥ dépend du wallet/faucet = chemin critique.

### 4.2 Après la soumission — construction du produit
- Boucle complète : détection → décision → autorisation → exécution → vérification → apprentissage (tranche MVP) ; intégrations Zodiac + politique + journal ; calibration des seuils (plan W3-C, ~10–20 h de collecte).

### 4.3 Décisions de gel (avant construction)
- Les 12 points W2-D ; édits du cadre ; jeux DEV/EVAL.

## 5. POSTURE D'INTÉGRATION (remarque d'équipe du 15/10 — actée)

Principe : **une solution qui intègre ce qui existe déjà, en plus de sa nouveauté, est supérieure** à une solution qui réinvente ; ne pas rejeter une brique « déjà faite ». Conséquences pratiques :
- La lecture concurrentielle (W2-E) est un **catalogue de briques intégrables**, pas une liste d'exclusions : Zodiac/Safe, Chainlink, Blockscout, DeFiLlama, workflows rejouables de LlamaRisk, oracles de risque type Chaos — tout ce qui est éprouvé s'intègre ; on n'écarte que le fermé/incompatible/mort.
- Notre nouveauté reste : graphe de collatéral multi-protocole + décision vérifiable/abstention + double enveloppe.
- L'**inventaire d'intégration** (§3.4) devient un livrable de planification explicite.

---
*Sources : rapports W2-A→E, W3-A/B/C (`research/`), synthèse `VAGUE2_SYNTHESE.md`, page officielle du concours (consultée le 15/10). Tout est reproductible depuis le dépôt `D:\orvyren_core`.*
