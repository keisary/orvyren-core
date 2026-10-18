# ADR-0002 — Politique v1 : set de 14 règles, `policy_v1.yaml` et test de dérive (Sprint 2 / W4)

**Date :** 2026-10-16 · **Statut : ACCEPTÉE** — actée le 2026-10-17 (chef d'équipe, mandat de
finalisation du périmètre restant ; régie par le protocole `docs/decisions/`) · **Portée :** bloc D
(politique) — implémentation du gel `FREEZE_V2.md` §D1.

## Contexte

Le gel v2 (D1) impose un **set v1 de 14 règles**, des **codes de refus stables** et un
fonctionnement **fail-closed** (DOC2 §5.5.2). L'état mesuré du dépôt au 15/10 (DOC4 §0) :
service de politique **[PARTIEL]** — règles P4/P7/P9/P11/P12/P14 absentes, `policy_v1.yaml`
inexistant, test de conformité/dérive absent. Le jalon S2 exige « une décision complète
traverse graphe → RDOF → décision → **14 règles** → intent en une commande », et le test de
conformité doit **attraper une dérive simulée (fixture modifiée → SAFE MODE)**.

## Options examinées

1. **Parser YAML tiers (PyYAML) pour `policy_v1.yaml`** — rejetée : le cœur est
   stdlib-only (DOC4 §1.4) et aucune exception n'est justifiée pour un fichier de
   paramètres (une exception ne s'ajoute que par PR justifiée, `LICENSES.md` à jour).
2. **Garder `policy.demo.json` (kit) comme source des paramètres** — rejetée : le gel
   nomme `policy_v1.yaml` comme **source de vérité des paramètres** (DOC2 §5.5.3) ; le kit
   démo en reste un consommateur.
3. **Implémenter les 6 règles manquantes + un mini-lecteur YAML strict + le test de dérive
   à deux étages (offline en CI, live à l'exécution)** — **retenue**.

## Décision

1. **Libellés alignés sur le gel v2** : R1–R8 (FREEZE_V1 D9) → **P1–P14** (DOC2 §5.5.2).
   Les **codes de refus ne changent pas** (stables, jamais renommés ni réutilisés) ; une
   règle non évaluée apparaît `SKIPPED` avec son motif — jamais silencieuse.
2. **Règles complétées** : **P4** fonction scopée (opérations + paires cible/sélecteur),
   **P7** exposition/solde (solde, plancher, plafond d'exposition), **P9** fraîcheur
   (TTL 15 min, tolérance d'horloge 60 s), **P11** pause / appartenance au rôle,
   **P12** alignement d'enveloppe (→ SAFE MODE), **P14** budget de décision. **P10**
   étendu à l'**empreinte de contenu** (re-soumission du même contenu = refus) ;
   garde **anti-erreur de décimales** en P5. Les règles « d'état » s'activent quand
   l'appelant fournit un `PolicyState` et sont alors **fail-closed** (un champ requis
   illisible est un refus ; les règles non fournies restent `SKIPPED`, mode legacy).
3. **`policy_v1.yaml`** (racine) = source de vérité des **paramètres**, chargée par
   `orvyren.policy.load_policy()` via un **mini-YAML strict stdlib**
   (`src/orvyren/policy/miniyaml.py` — refuse tout ce qu'il ne comprend pas). Chaque
   verdict porte **`policy_version`** (vMAJOR.MINOR) et **`policy_hash`** = empreinte du
   YAML canonique **combinée à l'empreinte du code du module** (DOC2 §5.5.3).
4. **Test de dérive** `scripts/run_drift_check.py` — les **10 contrôles** (D1–D10,
   DOC2 §5.5.4), en deux étages : **offline** (`policy_v1.yaml` ↔ fixture versionnée
   `fixtures/roles_agent_config.json`, sans réseau, exécutable en CI) et **live**
   (chainId, empreintes de bytecode épinglées, sondes comportementales par `eth_call`).
   Verdicts **PASS / DRIFT / UNVERIFIED** ; DRIFT et UNVERIFIED ⇒ **SAFE MODE** (refus de
   toute action autonome) ; rapport `evidence/envelope_drift_report.json` ; les contrôles
   non couverts (getters du module à confirmer, avis de sécurité) sont `SKIPPED` avec motif.
5. **Fixture d'enveloppe** : `fixtures/roles_agent_config.json` — capture réelle du
   montage de démo (proxy module 45 o + singleton 24 409 o épinglés, Safe, USDC, rôle,
   conditions, allowances, quota) + sondes de replay issues du paquet d'audit du 16/10.

## Procédure de changement de politique (6 étapes — opposable)

1. **Proposition** type « dossier de décision » : changement, règle touchée, impact,
   tests modifiés — rédigeable par un humain ou assistée, **jamais appliquée par un
   LLM** (le processus agent n'a **aucun** accès en écriture à la politique).
2. **PR + tests** : banc complet vert obligatoire.
3. **Si le changement touche une borne couplée on-chain** : d'abord on-chain, ensuite
   hors chaîne (on réduit d'abord = sens sûr ; on augmente côté politique après vote
   on-chain) ; **rapport de dérive joint**.
4. **Revue et signature par deux personnes** (auteur ≠ approbateur).
5. **Incrément de version + empreinte** + ligne au registre de versions append-only.
6. **Déploiement** + entrée de journal + **test de dérive au démarrage** (SAFE MODE si
   échec).

Asymétrie d'urgence (gelée) : **réduire** un plafond / retirer un destinataire /
activer la pause = « sens sûr », applicable immédiatement (journalisé, régularisé sous
24 h) ; **toute augmentation** suit la procédure complète.

## Conséquences

- **Positives** : les 14 règles existent et sont testées (refus + frontières) ; toute
  dérive fixture↔politique est détectée mécaniquement (y compris **simulée** : les tests
  la transforment en SAFE MODE) ; le verdict devient opposable (version + empreinte) ;
  le test de dérive live est rejouable par l'équipe (`--rpc`, lecture seule).
- **Contraintes** : le kit de démo reste en **mode legacy** (`SKIPPED` pour
  P4/P7/P9/P11/P12/P14) tant que W5 n'aura pas branché `load_policy` + `PolicyState` —
  c'est le **travail d'intégration restant du jalon S2**. Les docstrings du kit
  mentionnent encore « R1–R8 » (propriétaire W5). Les artefacts `evidence/` dépendants
  (dossier, `policy_execution_demo.json`, `pipeline_summary.json`, `quality_report.json`)
  ont été **régénérés** — empreintes recalculées en conséquence.
- **Coût** : ~0 (stdlib, hors-ligne ; l'étage live est en lecture seule).

## Reste à faire

1. **W5** : brancher le kit — `PolicyReference.as_policy_config` → `load_policy()` +
   construction d'un `PolicyState` complet (pause, appartenance, solde, enveloppe, budget).
2. Confirmer les **getters** du module Roles (B4 §d.3 annexe 4) pour passer D4–D8 du mode
   « conformité fixture » au mode « lecture directe » (les sondes D3/D6/D7 sont déjà
   comportementales, pas des getters).

## Références

`FREEZE_V2.md` §D1 · the v1 design notes (archived out of the repository) §5.5 (§5.5.2 règles, §5.5.3
bundle/version, §5.5.4 dérive) · the v1 design notes (archived out of the repository) §W4 (L4.1–L4.4) ·
`policy_v1.yaml` · `src/orvyren/policy/` · `scripts/run_drift_check.py` ·
`fixtures/roles_agent_config.json` · `evidence/envelope_drift_report.json`.
