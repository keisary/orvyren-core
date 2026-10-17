# ORVYREN — Rapport de complétion vs le projet imaginé (2026-10-17)

**Méthode** (et pourquoi pas un % unique) : « ce qu'on a imaginé » vit dans trois périmètres
distincts — (1) le **contrat v1 gelé** (`FREEZE_V2.md`, 46 décisions) qui se juge en
« livré + preuve » ; (2) la **vision produit** (`ORVYREN_DOC1.md` §6, `DOC2` §5-7), qui se juge
en « briques du cycle » ; (3) l'**univers complet des idées** (`ORVYREN_DOC3.md`, 53 propositions
+ 8 pistes de cible), où « écarté/reporté » est un **résultat livré** (la décision documentée),
pas un échec. Un pourcentage unique mélangerait ces trois choses — on donne donc trois taux,
chacun avec sa définition et ses preuves vérifiables dans le dépôt.

---

## Cercle 1 — Le contrat v1 gelé (`FREEZE_V2.md`, 46 décisions)

| Famille | Livrées + preuve | Partielles (pièce manquante identifiée) | Reportées (la décision EST « reporter ») |
|---|---|---|---|
| **A — Agents (6)** | 4 : MA-B journaux/processus (W2 fusionné), `agent_journal` (A4), budgets fail-closed (A5, tests), rétention (A6) | 2 : **A2 clé DeepSeek/MiMo absente** (partie live non exécutée) · A3 critique 2ᵉ modèle : structure prête, jamais tourné en live | — |
| **B — Graphe (4)** | 3 : B1 (34 relations / 17 champs, tests), B2 (SQLite + `store.py` unique), B4 (anti-reorg, enum, INV-PIT) | 1 : **B3 — ML-1 embeddings non implémenté** (aucun lot DOC4 ne le portait ; pgvector incompatible SQLite) ; ML-2 « MODEL-INFERRED » non livré (la détection d'anomalies existante est corpus, pas architecturale) | — |
| **C — Décision (7)** | 6 : C1 ACH, C2 RDOF (+essai vs ordre fixe), C3 abstention A1–A5, C4 8+4 catalogues, C5 double convention (1151,52 bps mesuré), C6 H_class=6 h | 1 : C7 — G6 *signé par défaut chef d'équipe* : **feuille de signature `frozen/G6_FEUILLE_DE_SIGNATURE.md` pas encore signée** | — |
| **D — Politique (5)** | 3 : D1 (14 règles, dérive PASS), D3 (asymétrie), D4 (kill switch K0/K1 — run D réel) | 1 : D2 — verdicts `REQUIRE_APPROVAL` ✓ mais **file + signature EIP-712 (TTL 2 h) non implémentée** | 1 : D5 (EAS) |
| **E — Exécution (5)** | 5 : E1 (clé jetable env, jamais dépôt), E2 (**run A réel 100 USDC**), E3 (swap/approve simulés), E4 (escalade reorg), E5 (2 USDC nommés) | — | — |
| **F — Audit (4)** | 3 : F1 (3 flux + paquet v2 + digest), F2 (vérificateur T10 : OFFLINE_PASS 16/16, mutations 6/6), F4 (textes FR+EN verbatim) | — | **1 ouverte obligatoire : F3 « empreinte publiée »** — le `bundle_digest` du paquet n'est **pas encore publié** (EAS = conditionnel, non exécuté — conforme au gel) |
| **G — Évaluation (4)** | 4 : G1 (DEV/EVAL registre), G2 (embargo implementé + testé), G3 (A0/A1/A2/B0+AX0), G4 (loss/comparators/calibration + **8 prévisions DEV gelées** ≥ 5-10 exigées) | — | — |
| **H — UI & Ops (4)** | 3 : H2 (lecture seule = état actuel), H3 (full local), H4 (ajouts CI) | 1 : H1 — **écrans W8 non construits** (`ui/server.py` = 3 routes ; 12 écrans à faire ; préparation vidéo reportée par le gel lui-même) | — |
| **I — Gouvernance (4)** | 4 : I1 (ADR-0001 + paquet ; **ADR-0002 actée le 17/10**), I2 (**règle 0 vérifiée : 0 occurrence du nom interdit**), I3 (4 documents), I4 (ordre respecté) | — | — |
| **J — Soumission (3)** | 3 : J1 (email envoyé/répondu, côté Jovanny), J2 (wallet testnet, robinets gratuits), J3 (kit de démo) | — | — |

**Taux cercle 1 : 38/46 pleines (83 %) · 6 partielles (13 %) · 1 reportée (2 %) · 1 ouverte
obligatoire (F3).** Pondéré par l'avancement réel des partielles : **≈ 87-90 % du contrat v1.**

Côté **`DOC4 §6` (les 8 lignes « terminé »)** : W1 ✓ · W2 ✓ · W3 ✓ · W4 ✓ · W5 ✓ · W6 ✓ · W7 ✓ ·
**W8 partiel** (écrans, index ADR + contrôle CI, build `dist/docs/`) → **7/8 = 87,5 %**.
La définition d'ensemble « v1 terminée » (8 lignes vertes **simultanément** + T10 par un tiers
externe + docs finaux cohérents) n'est **pas encore** satisfaite : les deux critères restants
sont W8 et la relecture T10 par une personne qui n'a pas écrit le code.

---

## Cercle 2 — La vision produit (`DOC1 §6` + `DOC2`)

Les 6 briques promises « juste après le gel » :

| Brique (DOC1 §6) | État | Preuve |
|---|---|---|
| Agents réels (orchestrateur + critique, modèles par API) | ✅ structure (2 processus, 2 journaux, critique cross-modèle) · 🟡 live non exécuté (clé) | `run_agents.py --replay journal` k=10 identique |
| Graphe de connaissance (34 types, provenance, horloges) | ✅ | `graph/catalog.py`, Q1–Q8, snapshots PIT `sha256sum -c` |
| Décision (hypothèses, RDOF, abstention, catalogues) | ✅ | trace USDC −7,172196 %, 69 tests |
| Double verrou (politique hors LLM + permissions on-chain) | ✅ | 14 règles + rôle Zodiac AGENT (runs réels) |
| La preuve (reçu public + journal 3 flux + vérificateur tiers) | ✅ | paquet v2 : OFFLINE_PASS 16/16, `--mutate-test` 6/6 |
| Le replay (épisodes réels, réflexions visibles) | ✅ moteur · 🟡 vitrine écrans = W8 | `run_replay.py journal --k 10` → hash identique |

**Taux cercle 2 : ≈ 90 %** — les fondations sont toutes debout et prouvées ; les 10 % restants
sont la **vitrine** (écrans W8) et la **preuve live** des agents (clé DeepSeek).

---

## Cercle 3 — L'univers complet des idées (`DOC3` : 53 propositions A–H + 8 pistes de cible)

| Catégorie | Nombre | État |
|---|---|---|
| **Écartées** (avec motif sourcé + conditions de réouverture) | ~25 | ✅ **traitées** — « la mémoire des refus » EST le livrable DOC3 |
| **Reportées post-concours** (V2/V3, avec quand-rouvrir) | ~14 | ✅ traitées décisionnellement · 0 % construites **par choix gelé** |
| **Retenues pour la v1** (mappées dans le gel : MA-B, RDOF, abstention, 14 règles, T10, harnais…) | ~12 | ✅ livrées — **sauf le cluster ML** (B4/B5 ↔ FREEZE B3 — embeddings / recherche sémantique : non implémenté) |
| **À rouvrir sous condition** | 2-3 | ✅ documentées |
| **Pistes de cible** (trésoreries DAO ✓ n°1, desks ✓ n°2, banques reportées, régulateurs/grand public/PME/assurance écartés) | 8 | ✅ tranchées, cibles v1 implémentées |

**Taux cercle 3 : ~98 % « traité »** (décidé + documenté + justifié, preuves DOC3) ; mais
**conversion en produit = uniquement le sous-ensemble v1 (~22 %)** — c'est le principe même de
DOC3 (« écarté ≠ rejeté »).

**Le seul « gelé orphelin » identifié** : **B3/B5 — ML-1 embeddings / recherche sémantique**
(gelé dans FREEZE_V2 §2 B3, « retenue en v1, à étendre » dans DOC3 B.5, **aucun lot DOC4 ne le
porte, aucune ligne de code**). Options : micro-implémentation SQLite (FTS/LIKE borné, 0,5 j) ou
reclassement V2 par ADR — à trancher, c'est la seule incohérence gel↔plan.

---

## Synthèse — les trois taux

| Périmètre | Taux | Lecture |
|---|---|---|
| **Contrat v1 gelé (FREEZE_V2)** | **≈ 87-90 %** (38/46 pleines ; 6 partielles ; F3 ouverte) | ce qui reste est **nommé** et borné |
| **Vision produit (DOC1/DOC2)** | **≈ 90 %** | reste = écrans (W8) + live (clé) |
| **Univers imaginé (DOC3)** | **≈ 98 % traité** / ~22 % converti en v1 | structurel : le reste est post-concours par décision |

## Ce qui reste, précisément (la liste vraie)

1. **W8** — écrans 1-12 (bandeau de mode + horloge simulée), index ADR + contrôle CI, build
   `dist/docs/` — *(le plus gros morceau, ≈ 7 j-h au plan)*.
2. **F3 — publier l'empreinte** du paquet (`bundle_digest` + `zip.sha256`) — *30 min*.
3. **ADR-0002** à acter (politique v1) + **feuille G6 à signer** (chef d'équipe) — *équipe*.
4. **Clé DeepSeek** → débloque : agents live (A2/A3), REPLAY-ARCHIVE réel, MiMo critique —
   *externe, 1 h de mise en route*.
5. **ML-1 embeddings** — trancher : micro-implémentation ou ADR de reclassement — *0,5 j ou 5 min*.
6. **Première exécution EVAL** (rsETH + USD0++) — après signature G6 ; une passe, publiée telle
   quelle ; jeu « brûlé » — *≈ 1 j*.
7. **Soumission** : doc technique EN, deck ≤ 10 min, vidéo ≤ 5 min (code+README+sécurité+preuves
   déjà prêts) — *deadline 20/10 15:59 UTC*.

*Toutes les affirmations de ce rapport sont vérifiables dans le dépôt : `git log` (fusions),
`python -m pytest tests/ -q` (798 à la rédaction ; 811 après W8), `python run_verify.py` (paquet), `python scripts/verify_frozen.py`
(gel), `grep` cités en place. Rapport rédigé le 2026-10-17 sur `master = e2baf8d`.*

---

## Mise à jour — 17/10/2026 (soir, après ce rapport)

Livré depuis (sur `master`, CI locale verte — **mesure : 811 tests — 808 verts, 3 sautés**) :

- **W8 ✅** — UI locale hors-ligne `/ui` : **12 écrans** (mode + horloge sur chacun), index cliquable,
  routes `/screen/1..12`, aucun JS ni asset externe ; **registre ADR** indexé (`scripts/adr_index.py` +
  contrôle CI) ; **build `dist/docs/`** (7 `.docx`) ; règle 0 (terme interdit) testée en suite.
  Nouveaux tests : `test_ui_routes.py`, `test_adr_index.py`, `test_docs_forbidden_term.py`.
- **ADR-0002 actée** (politique v1) · **ADR-0003** créée et actée (recherche sémantique / ML-1 → V2 —
  le « gelé orphelin » est tranché).
- **F3 ✅** — empreintes publiées dans `evidence/audit_packets/README.md` (sha256 des deux zips ;
  `bundle_digest` v2 `658428691e4a68279dc1d57ee694fbd05258137a17c735028c7424d05269981f` ; EAS conditionnel
  non exécuté — déclaré).
- **Clés vérifiées** : DeepSeek **fonctionnelle** (probe live `deepseek-flash` OK) ; MiMo = clé
  **Token Plan** (`tp-…`) refusée 401 sur tous les endpoints publics — il faut soit l'**URL de base
  exclusive** affichée à côté de la clé dans la console Token Plan, soit une clé **pay-as-you-go** (`sk-…`)
  compatible avec l'endpoint gelé `api.xiaomimimo.com/v1`.

Reste (inchangé) : **feuille G6 à signer** (chef d'équipe) · **agents live + REPLAY-ARCHIVE réel**
(débloqués par la clé MiMo corrigée) · **1ᵉᵉ exécution EVAL** (après signature — jeu brûlé) ·
**soumission** (hors périmètre de cet ordre).

