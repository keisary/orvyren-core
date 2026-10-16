# ORVYREN — agent wallet on-chain autonome et vérifiable

**2026 Shenzhen International FinTech Competition — International Track, thème F « Agent Wallet / Autonomous On-chain Wallet ».**

ORVYREN est un système d'agents qui transforme des signaux financiers publics en **décisions bornées et vérifiables** : il croise les sources, formule des hypothèses concurrentes, cherche le fait qui les départage, décide — ou s'abstient honnêtement (« il manque ceci ») —, n'exécute que dans une enveloppe autorisée (politique déterministe hors LLM + permissions on-chain), et laisse une trace qu'un tiers peut recalculer.

**Statut (17/10/2026)** : v1 **gelée** (`FREEZE_V2.md`) · suite de tests : **751 verts, 4 sautés** · **W1 graphe clos** (8 requêtes noyau Q1–Q8, snapshots PIT hashés, corpus CALME/USD0++) · **W2 agents MA-B fusionné** (boucle bornée, 2 processus, rejeu déterministe) · **W3 décision/RDOF livré** (recherche discriminante déterministe, 3 axes séparés, abstention A1–A5, catalogue paramétré `config/actions_v1.yaml`, décision en une commande `python -m orvyren.decide`, L3.1 registre d'hypothèses W2) · **politique v1 : 14 règles** (dérive offline+live PASS — ADR-0002 à acter) · **démo testnet exécutée on-chain : 5 runs A→E sur Base Sepolia** — hashes vérifiables, paquet d'audit reproductible (kit + runbook : `DEMO_KIT.md`).

## Documentation (tout à la racine)

| Fichier | Rôle |
|---|---|
| `ORVYREN_DOC1_EXPLICATION_SIMPLE.md` | comprendre ORVYREN en 2-3 pages (schémas + cas réels chiffrés) |
| `ORVYREN_DOC2_TECHNIQUE_COMPLET.md` | document technique complet — philosophie → architecture v1 → décisions |
| `ORVYREN_DOC3_PROPOSITIONS_ET_ECARTES.md` | tout ce qui a été exploré, écarté et classé V2 (banques, ML avancé, VoI…) |
| `ORVYREN_DOC4_PLAN_IMPLEMENTATION.md` | plan de travail : workstreams, sprints, répartition par personne |
| `FREEZE_V2.md` | **registre des décisions gelées** (autorité sur tout le reste) |
| `DEMO_KIT.md` | runbook de la démo testnet : robinets **gratuits**, Safe + module, 5 runs |
| `ARCHITECTURE_V1.md` | carte des modules du code |
| `SECURITY_SELF_ASSESSMENT.md` | auto-évaluation sécurité (niveaux de permission, risques connus) |
| `LICENSES.md` | composants tiers et licences |

## Démarrage rapide

```bash
python -m pytest tests/ -q                                   # 751 verts, 4 sautés attendus
python run_pipeline.py                                       # pipeline complet (corpus archivé)
python scripts/reconstruct_rseth_episode.py --from-cache     # reconstruction hors-ligne (idem steth / usdc)
python scripts/demo/demo.py --run A --dry-run --session demo_runs/session_dry   # kit démo testnet (dry-run)
```

## Reproduire la démo testnet (équipe)

Aucune clé et aucun résultat local ne voyagent dans git : chaque personne crée **son** wallet jetable (`DEMO_KIT.md` §2 — une commande), le finance par les robinets gratuits (§3 — captcha humain une fois), puis rejoue la séquence (§4 → §6, commandes copiables telles quelles).

```bash
python -m pip install -r requirements.txt             # eth-account — seule dépendance du signataire
cp scripts/demo/config.example.env scripts/demo/.env  # puis renseigner clés jetables + adresses (§5)
python scripts/demo/setup_chain.py --self-test        # contrôles hors ligne avant tout --execute
# séquence exacte des 5 runs (A→E, kill switch inclus) : DEMO_KIT.md §6
python scripts/demo/build_audit_packet.py --session <session> --case rseth --out dist/audit_packets
```

Ce qui reste **local par design** : les clés (`scripts/demo/.env`, `owners.env` — gitignorés) et les sessions d'exécution (`demo_runs/`, `dist/` — produites à l'exécution). Le **paquet d'audit** (`dist/audit_packets/*.zip`) est la pièce à transmettre : il ne contient que des données publiques (reçus, journal chaîné, hashes). L'exemplaire de référence des runs A→E du 16/10 est **versionné** : `evidence/audit_packets/` (zip + sha256 + mode de vérification).

## Structure du dépôt

```
orvyren_core/
├── src/orvyren/      # le système : data · quality · graph · policy · decision · execution · audit · ui
├── scripts/          # reconstructions d'épisodes (--from-cache) + demo/ (kit testnet)
├── tests/            # 755 tests, hors-ligne
├── fixtures/         # mesures archivées (15/10) utilisées par les tests et les modes hors-ligne
├── evidence/         # preuves : épisodes reconstruits (rsETH 2026, stETH 2022, USDC 2023) + dossiers
├── corpus/           # observations USDC/SVB mars 2023 (rejeu hors-ligne)
├── figures/          # figures du projet
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
4. **Archives hors dépôt** : les matériaux de recherche intermédiaires (études, matières brutes, historique) sont archivés dans `D:\orvyren_archive_2026-10-15\` ; leurs conclusions sont gelées dans `FREEZE_V2.md` et décrites dans les DOC 1–4.

## Licence

MIT — voir `LICENSE`. Composants et outils tiers : `LICENSES.md`.
