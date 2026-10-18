# ORVYREN — agent wallet on-chain autonome et vérifiable

**2026 Shenzhen International FinTech Competition — International Track, thème F « Agent Wallet / Autonomous On-chain Wallet ».**

ORVYREN est un système d'agents qui transforme des signaux financiers publics en **décisions bornées et vérifiables** : il croise les sources, formule des hypothèses concurrentes, cherche le fait qui les départage, décide — ou s'abstient honnêtement (« il manque ceci ») —, n'exécute que dans une enveloppe autorisée (politique déterministe hors LLM + permissions on-chain), et laisse une trace qu'un tiers peut recalculer.

**Statut (18/10/2026)** : v1 **gelée** (`FREEZE_V2.md`) · suite de tests : **1418 tests — OK (3 sautés)** (mesurée le 18/10/2026 ; pytest : 1 415 passed + 289 subtests) · **W1 graphe clos** (8 requêtes noyau Q1–Q8, snapshots PIT hashés, corpus CALME/USD0++) · **W2 agents MA-B fusionné** (boucle bornée, 2 processus, rejeu déterministe) · **W3 décision/RDOF livré** (recherche discriminante déterministe, 3 axes séparés, abstention A1–A5, catalogue paramétré `config/actions_v1.yaml`, décision en une commande `python -m orvyren.decide`, L3.1 registre d'hypothèses W2) · **politique v1 : 14 règles** (dérive offline+live PASS — ADR-0002 actée le 17/10) · **démo testnet exécutée on-chain : 5 runs A→E sur Base Sepolia** — hashes vérifiables, paquet d'audit reproductible (kit + runbook : `DEMO_KIT.md`) · **W5 exécution/démo formalisé** (lots L5.1–L5.6 : `docs/W5_lots_L5.1-L5.6.md` ; scripts montage + hygiène ajoutés) · **W6 vérificateur tiers T10 livré** (`python run_verify.py` — contrôles A/B/C recomputés, `--mutate-test` 6/6 ; paquet v2 à vérificateur gelé versionné dans `evidence/audit_packets/`) · **W7 rejeu & évaluation livrés** (`run_replay.py` : REPLAY-JOURNAL bit-à-bit — k=10 → hash identique — et REPLAY-ARCHIVE (clé requise, refus explicite sinon) ; harnais DEV A0/A1/AX0/A2/B0 + portes de gel/verrou/embargo ; `run_evaluation.py`, `run_calibration.py` ; artefacts `evidence/evaluation/` & `evidence/calibration_report.*`). · **W8 livré** (UI locale hors-ligne : `/ui` — 12 écrans bandeau mode + horloge ; registre ADR + contrôle CI ; build `dist/docs/` ; règle 0 testée) · **ADR-0002 actée le 17/10** · **ADR-0003** (recherche sémantique/ML-1 → V2) · **F3 : empreintes du paquet publiées** (`evidence/audit_packets/README.md`) · **Agents LIVE exécutés** (17/10 — boucle MA-B réelle : DeepSeek V4.1-Flash + MiMo V2.6-Pro, processus séparés ; `DONE/ARRET-2`, critique FRAGILE → `REQUIRE_APPROVAL`, 0,0192 $ — session scellée `evidence/agents_live/`) · **REPLAY-ARCHIVE k=3 exécuté** (distribution publiée telle quelle : 2× `ARRET-2`, 1× `ARRET-3` fail-closed — `evidence/replay/`) · **prompt `orch-p1.1.0`** (évaluation désambiguïsée pour les modèles live ; re-scellement visible : magasin scripté re-seedé + dossier de rejeu régénéré).

## Résultats du slice 10 h

- **Graphe v3** : Aave v3 Base, **15 000 événements**, **12 937 relations**, **16 174 nœuds**, **8 types de relations** ; base SQLite de 50 Mo hors dépôt, snapshot versionné `evidence/ui_snapshot.json`.
- **API SQL read-only** : Q1/Q2/Q4/Q5/Q6/Q7/Q8 + snapshot ; Q1 **81,6 ms p50** sur 12,9k relations.
- **Agents** : tool calling natif + fallback JSON strict ; outils `graph_query`, `graph_path`, `graph_snapshot` ; mémoire working/episodic/semantic.
- **UI** : trois panneaux Situation / Graphe / Décision, modes `LIVE` / `REPLAY`, source explicite.
- **Limites** : EVAL **N=0**, Q8 **NOT_INGESTED**, Q2 sans arête dans ce slice, aucun `LIQUIDATED_IN`, pas de 10⁵ événements, pas de SQL/PGQ ni de base graphe externe.

## Documentation (tout à la racine)

| Fichier | Rôle |
|---|---|
| `FREEZE_V2.md` | **registre des décisions gelées** (autorité sur tout le reste) |
| `DEMO_KIT.md` | runbook de la démo testnet : robinets **gratuits**, Safe + module, 5 runs |
| `ARCHITECTURE_V1.md` | carte des modules du code |
| `SECURITY_SELF_ASSESSMENT.md` | auto-évaluation sécurité (niveaux de permission, risques connus) |
| `LICENSES.md` | composants tiers et licences |

## Démarrage rapide

```bash
python -m pytest tests/ -q                                   # 1486 tests (3 skipped) — measured 2026-10-18
PYTHONPATH=src python -m orvyren.decide --case usdc-2023-03 --replay   # décision complète en une commande (3 axes, hors-ligne)
python run_pipeline.py                                       # pipeline complet (corpus archivé)
python scripts/reconstruct_rseth_episode.py --from-cache     # reconstruction hors-ligne (idem steth / usdc)
python scripts/demo/demo.py --run A --dry-run --session demo_runs/session_dry   # kit démo testnet (dry-run)
python run_audit.py --serve                                  # UI locale : /ui (12 écrans), /panels (3 panneaux), /api/panels
PYTHONPATH=src python -m orvyren.graph.api --db D:/orvyren_10h_2026-10-17/graph_v3.sqlite \
  q1 --holder 0xbe00a0de23a02a85d7fb7451ab9b69d84fd61fe3 \
  --as-of 2026-10-17T11:12:57+00:00 --block 52723115
python run_replay.py journal --case usdc-2023-03             # REPLAY-JOURNAL bit-à-bit (k=10 → hash identique)
python scripts/adr_index.py --check                          # registre ADR : numérotation sans trou + README à jour
```

## Reproduire la démo testnet (équipe)

Aucune clé et aucun résultat local ne voyagent dans git : chaque personne crée **son** wallet jetable (`DEMO_KIT.md` §2 — une commande), le finance par les robinets gratuits (§3 — captcha humain une fois), puis rejoue la séquence (§4 → §6, commandes copiables telles quelles).

```bash
python -m pip install -r requirements.txt             # eth-account — seule dépendance du signataire
cp scripts/demo/config.example.env scripts/demo/.env  # puis renseigner clés jetables + adresses (§5)
python scripts/demo/setup_chain.py --self-test        # contrôles hors ligne avant tout --execute
# séquence exacte des 5 runs (A→E, kill switch inclus) : DEMO_KIT.md §6
python scripts/build_audit_packet.py --session <session> --case rseth --out-dir dist/audit_packets  # paquet v2 : vérificateur gelé + HASHES + mutations
python run_verify.py dist/audit_packets/<paquet>.zip         # vérification tierce (OFFLINE_PASS attendu)
```

Ce qui reste **local par design** : les clés (`scripts/demo/.env`, `owners.env` — gitignorés) et les sessions d'exécution (`demo_runs/`, `dist/` — produites à l'exécution). Le **paquet d'audit** (`dist/audit_packets/*.zip`) est la pièce à transmettre : il ne contient que des données publiques (reçus, journal chaîné, hashes). L'exemplaire de référence des runs A→E du 16/10 est **versionné** : `evidence/audit_packets/` (zip + sha256 + mode de vérification).

## Structure du dépôt

```
orvyren_core/
├── src/orvyren/      # le système : data · quality · graph · policy · decision · execution · agents · audit · ui
├── scripts/          # reconstructions d'épisodes (--from-cache), ingestion Aave + demo/ (kit testnet)
├── tests/            # 1418 tests, hors-ligne
├── fixtures/         # mesures archivées (15/10) utilisées par les tests et les modes hors-ligne
├── evidence/         # preuves : épisodes reconstruits (rsETH 2026, stETH 2022, USDC 2023) + dossiers
├── corpus/           # observations USDC/SVB mars 2023 (rejeu hors-ligne)
└── docs/decisions/   # registre ADR (décisions futures, format Nygard/MADR)
```

## Reproductibilité (faits mesurés, vérifiables)

- Le corpus est **archivé** (`corpus/`) : le pipeline, les reconstructions d'épisodes et les tests tournent **hors-ligne**.
- Les artefacts de décision rejouent **byte-identiques** ; les dossiers se reconstruisent à l'identique avec un self-hash SHA-256 recalculable par n'importe quel outil.
- Les documents ne revendiquent rien qui ne soit mesuré : chaque chiffre cité est reconstruit dans `evidence/` (blocs, reçus, séries) avec ses sources publiques (URL + date).

## Règles non négociables

1. **Aucun calcul financier ne sort d'un modèle de langage** — les agents structurent et expliquent ; des fonctions déterministes calculent, vérifient, refusent.
2. **Point-in-time** : une analyse historique n'utilise que ce qui était disponible à l'instant simulé.
3. **Testnet uniquement** pour l'exécution (les prix de testnet ne servent jamais de contexte de marché).
4. **Archives hors dépôt** : les matériaux de recherche intermédiaires et les notes de conception v1 ne sont pas versionnés ; leurs conclusions sont gelées dans `FREEZE_V2.md`.

## Licence

MIT — voir `LICENSE`. Composants et outils tiers : `LICENSES.md`.
