# 50_competition — Positionnement, barème, démo et risques

**Auteur / agent** : Hermes-orchestrateur (deepseek-flash, session recherche V2).
**Date** : 2026-10-17.
**Chantier** : `50_competition`.
**Statut** : INTERNE — recherche V2, ne pas soumettre.
**Périmètre** : positionnement, barème 40/30/30, pièces, démo, risques, claims honnêtes.
**Fichiers lus** : `fintechathon_recherche/concours/rules_texte.txt`, `form_texte.txt`, `ORVYREN_Selection_Cas_Usage_V0_1.txt`, `ORVYREN_DOC1_EXPLICATION_SIMPLE.md`, `docs/AUDIT_EXTERNE_2026-10-17.md`, `10_graph__schema-cible__hermes__2026-10-17.md`, `10_graph__audit-34-relations__hermes__2026-10-17.md`.

---

## 0. Verdict

Le positionnement actuel risque de présenter **un noyau de preuve** comme un **agent wallet complet**. Le jury verrait un prototype mono-cas, pas un système ambitieux. Le bon angle est :

> **ORVYREN est l'agent de risque de trésorerie on-chain qui transforme un signal dispersé en dossier de décision prouvé, avec une action bornée par policy.**

Le graphe est l'innovation ; la sécurité est la couche de confiance ; l'exécution est la dernière étape, pas le produit.

---

## 1. Barème

| Critère | Poids | Ce que le jury attend |
|---|---:|---|
| Accomplissement | **40 %** | Le système fonctionne, de bout en bout, sur un cas réel |
| Sécurité | **30 %** | Pas de clé exposée, policy hors LLM, refus, preuve |
| Innovation | **30 %** | Une idée qui n'est pas un énième agent générique |
| Bonus Challenge | 0–5 | Ambition, impact, qualité |

**Conséquence** : 70 % du score dépend de l'exécution et de la sécurité, mais 30 % de l'innovation. Un agent qui exécute sans graphe est banal ; un graphe sans exécution est une démo. Il faut **les deux**, avec le graphe comme différence.

---

## 2. Les six pièces

1. **Document technique EN** : architecture, données, graphe, agents, policy, sécurité, évaluation, limites.
2. **Deck ≤10 min** : problème, persona, démo, graphe, sécurité, résultats, roadmap.
3. **Vidéo ≤5 min (optionnelle)** : une démo réelle, pas une animation.
4. **Code + README + GitHub + déploiement + tests** : reproductible, clean clone, Docker.
5. **Rapport sécurité EN** : menaces, contrôles, tests, limites.
6. **Preuves on-chain** : tx, reçus, refus, kill switch, audit.

**Règle** : ne pas produire les pièces 1–3 avant que le système (C1/C2 + ingestion + Q1/Q4/Q6/Q7/Q8 + un écran) tourne. Sinon on documente un prototype.

---

## 3. Positionnement

### 3.1 Ce qu'on vend

**Pour l'opérateur de trésorerie on-chain** : un espace d'enquête qui répond à « mon exposition est-elle menacée, pourquoi, avec quelles preuves, et quelle action bornée est admissible ? »

### 3.2 Ce qu'on ne vend pas

- Pas un chatbot de prix.
- Pas un swarm multi-agent.
- Pas un dashboard de 12 écrans.
- Pas une base graphe pour elle-même.
- Pas une promesse de rendement.

### 3.3 La différence

| Composant | Générique | ORVYREN |
|---|---|---|
| Agents | LLM + outils | Oui, mais pas la différence |
| Sécurité | policy/signature | Oui, nécessaire |
| Graphe | parfois | **Cœur** : temporel, provenance, épistémique, décisionnel |
| Preuve | logs | **Décision → source**, hash, snapshot |
| Produit | démo | **Espace d'enquête** |

---

## 4. Démo 5 minutes

1. **0:00–0:30** : persona + question ; portefeuille, bloc, mode.
2. **0:30–1:30** : graphe Q1/Q7/Q8 ; exposition, concentration, permissions.
3. **1:30–2:30** : trois hypothèses ; fait manquant ; recherche outillée.
4. **2:30–3:30** : preuves, contradiction, PIT.
5. **3:30–4:15** : décision, policy ALLOW/DENY/REQUIRE_APPROVAL.
6. **4:15–5:00** : action/refus, reçu, provenance Q6, snapshot, limites.

**Règle** : le graphe doit apparaître dans les 30 premières secondes ; le jury doit voir le système, pas une suite d'écrans.

---

## 5. Claims autorisés / interdits

| Claim | Statut |
|---|---|
| « 34 types de relations définis » | **Oui**, préciser « 13 utilisés en fixtures, 1 dans le graphe live » |
| « 520 observations, 4 relations live » | **Oui**, mais ce n'est pas un graphe peuplé |
| « 16 relations / 10⁵ événements » | **Non** ; 8–10 relations, 10k+ événements |
| « multi-agent complet » | **Non** ; orchestrateur + chercheur + critique |
| « EVAL concluante » | **Non** ; N=0 |
| « SQL/PGQ » | **Non** ; patch reverté |
| « policy hors LLM, fail-closed » | **Oui**, tests |
| « preuve on-chain » | **Oui** si tx/reçu vérifiés |
| « zéro clé » | **Non** ; l'agent a une clé testnet isolée, jamais exposée |

---

## 6. Risques

| Risque | Impact | Mitigation |
|---|---|---|
| Prototype mono-cas | élimination | slice Aave + persona + 8–10 relations |
| Graphe décoratif | faible innovation | Q1/Q7/Q8 au centre |
| Données fixtures présentées live | discrédit | modes LIVE/REPLAY/SYNTHETIC |
| `SECURITY_SELF_ASSESSMENT.md:11` faux | sécurité | corriger avant soumission |
| Reçus natifs vs ERC-20 | incohérence | trancher et documenter |
| EVAL N=0 | pas de performance | ne pas revendiquer |
| Trop de docs, pas de système | élimination | C1/C2 + ingestion d'abord |
| Dépôt public trop tôt | risque | rester privé jusqu'à préparation |

---

## 7. Plan de soumission

| Jour | Livrable |
|---|---|
| J1 | C1/C2 + ingestion 10k events |
| J2 | Q1/Q4/Q6/Q7/Q8 SQL + écran d'enquête |
| J3 matin | démo 5 min + preuves + tests |
| J3 après-midi | doc technique EN + rapport sécurité + README |
| J3 soir | soumission |

**Vidéo** : optionnelle ; seulement si la démo est stable. Pas d'animation à la place d'une preuve.

---

## 8. Conditions top 10

- Un système qui tourne, pas un prototype.
- Un graphe visible et utile, pas un décor.
- Une sécurité prouvée, pas déclarative.
- Une démo claire en 5 min.
- Des claims honnêtes, des limites explicites.
- Une équipe qui peut expliquer chaque choix.

---

## 9. Sources

- `fintechathon_recherche/concours/rules_texte.txt` (barème, deadline, pièces).
- `form_texte.txt` (inscription, équipe).
- `ORVYREN_Selection_Cas_Usage_V0_1.txt` (persona, cas).
- `docs/AUDIT_EXTERNE_2026-10-17.md` (scores, risques).
- `10_graph__schema-cible__hermes__2026-10-17.md`.
- `10_graph__audit-34-relations__hermes__2026-10-17.md`.
- `10_graph__contradiction-72h-scope__codex__2026-10-17.md`.
- `10_graph__contradiction-sqlpgq-et-index__minimax-code__2026-10-17.md`.
