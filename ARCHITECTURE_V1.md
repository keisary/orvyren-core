# ORVYREN-Core — ARCHITECTURE V1 (module, interfaces, communication)

*14 octobre 2026. Ce document répond à la seule question qui manquait avant de coder : **comment les modules sont découpés, qui parle à qui, et par quel mécanisme.** Il complète `FREEZE_V1.md` (valeurs à geler) et la V0.2 (conception). Statut des décisions : ✅ figé ici, ☐ à valider par l'équipe.*

---

## 1. Modèle d'exécution (décision structurante)

**✅ Un monolithe modulaire, un seul processus, un worker en tâche de fond.** Pas de microservices, pas de broker, pas de file distribuée.

- **`api` (FastAPI)** — sert la page d'audit et quelques routes de lecture. *Ne calcule rien de financier*, ne décide rien.
- **`worker` (boucle dans le même dépôt, lancée par commande)** — collecte le corpus, met à jour le graphe, exécute les tâches de recherche. Les tâches et leur état vivent dans une **table de jobs en base** (pas de Redis) : reprise après plantage, rejeu possible.
- **Pipeline (fonctions pures)** — tout le raisonnement (graphe → branches → décision → politique) s'exécute **en appel de fonction dans le processus**, avec des `dataclass` en entrée/sortie. Une décision complète est **une commande CLI** : `python -m orvyren.decide --case usdc-2023-03 --replay`.

**Pourquoi** : la démo doit être rejouable et auditable, pas distribuée. Le document V0.2 §11.1 recommande déjà le monolithe modulaire ; ceci en donne la forme exacte.

## 2. Carte des modules

```
orvyren_core/
├── src/orvyren/
│   ├── connectors/        lectures externes — AUCUNE décision
│   │   ├── defillama.py   prix historiques (1 req/timestamp), séries d'offre
│   │   ├── exchanges.py   Bitstamp OHLC, Binance klines
│   │   └── rpc.py         lecture chaîne (Base Sepolia + mainnet en lecture seule)
│   ├── quality/           normalisation, unités, détection d'anomalies → Observation
│   ├── graph/             objets, store, provenance
│   │   ├── models.py      dataclasses : Source, Observation, Claim, Relation, Hypothesis, Decision…
│   │   ├── store.py       SEUL point d'accès base (Postgres ; SQLite pour les tests)
│   │   └── provenance.py  chaîne de provenance, snapshots point-in-time
│   ├── branches/          registre d'hypothèses (états CREATED→…→ARCHIVED), deltas
│   ├── research/          planificateur de tâches + exécution bornée (budget, arrêt)
│   ├── decision/          moteur financier
│   │   ├── exposure.py    exposition de démonstration
│   │   ├── scenarios.py   scénarios et incertitudes
│   │   ├── engine.py      décision candidate ou NO-ACTION
│   │   └── baseline.py    A0 : règle de seuil fixe (l'adversaire)
│   ├── policy/            service d'autorisation déterministe  ✅ déjà écrit et testé
│   ├── execution/         signer isolé, envoi, vérification du receipt
│   ├── audit/             dossier de décision (1 page), preuves, manifeste
│   └── ui/                page unique d'audit (rendu HTML côté serveur)
├── tests/                 banc de sûreté (7 attaques) ✅ + tests décision/baseline/corpus
├── corpus/                données archivées + manifeste ✅
├── docs/                  doc technique EN, ADR, rapport sécurité
├── evidence/              hash, receipt, refus, dossiers de décision produits
└── FREEZE_V1.md · ARCHITECTURE_V1.md · README.md
```

**Règle de dépendance (vérifiée par test)** : `connectors → quality → graph → branches → research → decision → policy → execution → audit → ui`. Un module ne peut importer que ceux situés **avant** lui dans cette chaîne. En particulier :
- `policy` n'importe **jamais** `research` ni un adaptateur LLM ;
- `execution` n'accepte **qu'un intent déjà autorisé** (`PolicyDecision.verdict == ALLOW`) ;
- `connectors` ne connaît ni `decision` ni `policy` ;
- l'adaptateur LLM (s'il est utilisé) n'est appelé **que** depuis `research` (extraction, formulation de tâches) et **jamais** pour produire un chiffre.

## 3. Interfaces (contrats entre modules)

| De | Vers | Contrat (entrée → sortie) |
|---|---|---|
| `connectors` | `quality` | `(url, params) → PayloadBrut{source, url, retrieved_at, body}` |
| `quality` | `graph` | `PayloadBrut → Observation{source_id, ts_event, ts_retrieved, valeur, unité, qualité, empreinte}` |
| `graph` | `branches` | `graph_version → SnapshotFigé{id, instant, claims[]}` ; une branche **référence** un snapshot, ne le copie pas |
| `branches` | `research` | `Hypothesis{énoncé, état, critères_de_réfutation} → ResearchTask{question, budget, critère_discriminant, échéance}` |
| `research` | `graph` | `ResearchTask → Claim[]` rattachés aux observations, **avec coût réel** |
| `decision` | `policy` | `Intent{action, chaîne, actif, montant, destinataire, intent_id} → PolicyDecision{ALLOW\|DENY\|REQUIRE_APPROVAL, règles, motifs}` |
| `policy` | `execution` | `Intent autorisé → TxHash + Receipt vérifié` (ou échec **enregistré comme échec**) |
| `execution` | `audit` | `Receipt + état final → Dossier de décision{1 page, hash SHA-256, limites}` |

**Deux invariants** : (1) *aucun module ne renvoie de chiffre non tracé* — un `Claim` sans `Observation` parente est rejeté par `graph.store` ; (2) *le LLM ne traverse aucune frontière de calcul* — il propose des structures, `quality`/`graph`/`policy` les valident ou les rejettent.

## 4. Stockage (schéma minimal, Postgres ; SQLite en test)

`source` · `observation` · `claim` · `relation` · `graph_version` · `hypothesis` · `branch_delta` · `research_task` · `job` · `portfolio_snapshot` · `intent` · `policy_decision` · `execution` · `outcome` · `decision_dossier` · `calibration`.

Toutes les tables : `id` (ULID), `created_at` (UTC ISO-8601), `provenance_refs[]`. Historique **append-only** : une révision crée une ligne, elle n'écrase pas.

## 5. Conventions et outillage

| Sujet | Décision |
|---|---|
| Langage | Python 3.11 (le poste) ; aucune dépendance exotique |
| Dépendances | `fastapi`, `pydantic`, `psycopg[binary]` (ou `sqlite3` en test), `httpx` ; tests en `unittest` (déjà en place) |
| Démo hors-ligne | `--replay` obligatoire partout (le corpus et la décision doivent tourner sans réseau) |
| Secrets | jamais dans le dépôt ; `.env.example` + variables d'environnement ; clé privée hors du processus de raisonnement |
| CI | GitHub Actions : `unittest` (banc de sûreté + décision + corpus en replay) à chaque push |
| Branches / commits | `main` protégée à la main ; branches `feat/<sujet>` ; messages impératifs en anglais (`add policy deny codes`) |
| Licence | **MIT** (code de l'équipe ; les composants tiers restent sous leur licence, listés dans `LICENSES.md`) |
| Hébergement démo | Render (web gratuit) + Postgres Neon (gratuit) ; la machine locale ne sert qu'au développement |
| Langue des artefacts | UE : code, README, docs et vidéo **en anglais** (exigence du concours) ; notes internes en français |

## 6. Ce qui n'est pas dans l'architecture (et pourquoi)

Microservices · broker de messages · base graphe · multi-agent parallèle · attestation EAS (reportée après le flux vertical) · ERC-7715 · mainnet avec fonds réels · authentification multi-utilisateurs · interface multi-vues. Chacune ne revient qu'avec un besoin mesuré (règle V0.2 §11.4).

## 7. Réponse à « qu'est-ce qui manque avant de commencer ? »

**Rien de bloquant sur le plan technique** — le cas est choisi, l'architecture est ci-dessus, le corpus existe, la politique est testée. Il manque exactement **trois choses, toutes à toi** :

1. **Le dépôt GitHub** : il n'existe pas encore. Je peux le créer et pousser (`keisary`, compte détecté sur cette machine) ou tu le crées et je pousse. Il faut aussi décider : **privé au départ (recommandé)** → public à la soumission, ou public tout de suite.
2. **Les collaborateurs** : donne-moi leurs pseudos GitHub (2–5 membres au total, exigence du règlement).
3. **Le feu vert sur les valeurs** : `FREEZE_V1.md` D1–D12 + l'architecture ci-dessus. Un simple « GO avec les valeurs par défaut » suffit — je gèle et je pars.

**Puis j'enchaîne dans cet ordre** (le corpus et la politique sont déjà faits) : moteur de décision + baseline A0 sur le corpus → registre de branches + une recherche discriminante → dossier de décision → wallet de test (transfert + refus) → page d'audit → doc technique EN + rapport de sécurité + support de la vidéo.
