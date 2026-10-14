# ORVYREN-Core — KIT DE REVUE POUR LES COLLABORATEURS

**Version partagée** : snapshot du 14 octobre 2026 (voir le hash du ZIP dans le message qui l'accompagne)
**Concours** : 2026 Shenzhen International FinTech Competition — International Track, thème F « Agent Wallet / Autonomous On-chain Wallet » — **échéance 20 octobre 2026, 15:59 UTC**
**But de ce kit** : que chaque membre de l'équipe dispose de tout — le problème, le cas, les données, le code, les preuves, l'état réel — pour chercher les **failles, les faiblesses et les améliorations** sans avoir à poser de questions.

---

## 1. En une page : qu'est-ce qu'ORVYREN-Core ?

Un **moteur de décision financière vérifiable** avec un **journal d'audit** et une **action on-chain bornée par une politique**.

Cas pilote : pendant la faillite de SVB (mars 2023), l'USDC a décroché — mais **pas au même prix selon la source** (Bitstamp 0,8627 · agrégat DeFiLlama 0,8767 · Binance 0,9128). Un portefeuille de trésorerie devait décider : subir, ou réduire l'exposition ? Et surtout : **sur quelle preuve décider** quand les sources se contredisent ?

Ce que fait le système, en 4 étapes exécutables :
1. **qualité** — normalise le corpus, mesure la couverture, refuse d'halluciner les données manquantes ;
2. **décision** — classe trois hypothèses pré-enregistrées (H1 perturbation locale / H2 stress général / H3 artefact), applique une règle de décision gelée **avant** de regarder les résultats, produit une décision motivée avec références ;
3. **politique + exécution** — la décision n'est qu'une *proposition* : un service déterministe hors LLM rend ALLOW / DENY / REQUIRE_APPROVAL ; l'agent **ne détient aucune clé** — il produit une instruction non signée, un humain l'exécute, l'agent vérifie ensuite le reçu on-chain ;
4. **audit** — un dossier d'une page, auto-porteur, avec le sha256 de chaque pièce.

**Ce que ce n'est pas (encore)** : pas de portefeuille réel financé, pas de mainnet, pas de multi-chaîne, pas d'attestation EAS, pas de base graphe dédiée. Le périmètre N1 est volontairement resserré (voir `FREEZE_V1.md` D4).

---

## 2. Démarrer en 3 commandes (10 minutes)

Prérequis : **Python 3.11**, aucune dépendance externe (tout est en bibliothèque standard — aucun `pip install`, aucun secret, aucun réseau requis).

```bash
cd orvyren_core
python -m unittest discover -s tests        # la suite complète (112 tests)
python run_pipeline.py                      # tout le pipeline bout-en-bout + résumé des preuves
python run_audit.py --serve                 # le dossier d'audit servi sur http://127.0.0.1:8000
```

Rejeu hors-ligne garanti : le corpus est archivé dans `corpus/` (`python collect_corpus.py --offline` pour vérifier), aucune étape n'a besoin d'internet. **Les seules étapes optionnelles qui touchent au réseau** : re-collecter le corpus (`--force`) et vérifier un reçu on-chain (si un hash de transaction est fourni).

---

## 3. Ordre de lecture conseillé

| Durée | Fichier | Pourquoi |
|---|---|---|
| 3 min | `README.md` | ce que le dépôt contient, comment l'exécuter |
| 5 min | `FREEZE_V1.md` | les 12 décisions gelées **et pourquoi** — c'est le contrat du projet |
| 10 min | `ARCHITECTURE_V1.md` | modèle d'exécution, carte des modules, règles de dépendance, contrats d'interface |
| 5 min | `corpus/README.md` + `corpus/manifest.json` | d'où viennent les données, leurs limites déclarées |
| 10 min | `evidence/dossier_usdc-2023-03.md` | **la sortie que le jury verra** — une page, avec les chiffres et les limites |
| 20 min | `src/orvyren/policy/__init__.py` + `tests/test_policy.py` | le cœur de la sûreté : 8 règles, 7 attaques, verdict déterministe |
| 20 min | `src/orvyren/decision/` | hypothèses, critères de réfutation, baseline A0, moteur |
| reste | le reste du `src/` | qualité, graphe, exécution, audit, UI |

**Fichier le plus important à attaquer en premier : `src/orvyren/policy/__init__.py`.** C'est lui qui empêche la dérive d'un agent autonome. S'il y a un contournement possible, il doit être trouvé maintenant.

---

## 4. Carte des fichiers (où regarder, pour quoi)

| Chemin | Rôle | À examiner pour… |
|---|---|---|
| `FREEZE_V1.md` | décisions gelées D1–D12 | vérifier qu'aucune valeur n'a été « ajustée » discrètement après coup |
| `ARCHITECTURE_V1.md` | architecture et frontières | incohérences entre modules, dépendances interdites |
| `collect_corpus.py` | collecteur multi-sources | robustesse réseau, cache, rejeu, sources non documentées |
| `corpus/usdc_observations.csv` | **toutes les données brutes** (1 375 lignes) | recalculer les chiffres clés par vous-mêmes |
| `corpus/manifest.json` | provenance de chaque série | vérifier source / date de collecte / limites |
| `figure_divergence.py` → `figures/usdc_divergence.png` | figure du cas | l'intégrité graphique des chiffres affichés |
| `src/orvyren/policy/__init__.py` | verdict ALLOW/DENY/REQUIRE_APPROVAL, hors LLM | **contournements de politique, règles manquantes** |
| `tests/test_policy.py` | les 7 attaques pré-déclarées | quelles attaques **manquent** (rejeu, oracle, cumul, allowlist…) |
| `src/orvyren/decision/scenarios.py` | H1/H2/H3 et critères de réfutation | **falsifiabilité** : les critères sont-ils réellement pré-enregistrés ? |
| `src/orvyren/decision/engine.py` | règle de décision + INCONCLUSIVE | chemins où le moteur conclut sans preuve suffisante |
| `src/orvyren/decision/baseline.py` | baseline A0 (l'adversaire) | équité de la comparaison, faux signaux |
| `src/orvyren/quality/` | normalisation, couverture, `data_gate` | données manquantes traitées silencieusement ? |
| `src/orvyren/graph/` | provenance, chaîne de preuve, append-only | un chiffre déterminant pourrait-il exister **sans** observation parente ? |
| `src/orvyren/execution/` | client RPC, garde, vérification de reçu | vérification du reçu, décodage ERC-20, gestion des échecs |
| `src/orvyren/audit/` + `run_audit.py` | dossier d'une page + serveur local | ce qui manque pour convaincre un jury en 5 minutes |
| `run_pipeline.py` | orchestration bout-en-bout | échecs silencieux, artefacts non vérifiés |
| `evidence/*.json` | **les résultats réels** | recalculer, contredire, comparer |
| `LICENSES.md` | licences des composants et des données | conformité propriété intellectuelle du concours |

---

## 5. Résultats réels déjà obtenus (à contester si faux)

Tout ce qui suit sort du pipeline exécuté le 14 octobre 2026 ; les preuves sont dans `evidence/`.

- **Corpus** : 1 375 observations, 0 rejeté, 0 signalé — 5 séries (agrégat DeFiLlama, Bitstamp, Binance, offre agrégat, offre Ethereum) sur la fenêtre 9–15 mars 2023 + fenêtre témoin 15–18 février.
- **Divergence constatée** : Bitstamp 0,86267 (11/03 07:00Z) · agrégat 0,87667 (08:00Z) · Binance 0,91280 (15:00Z).
- **Offre USDC** : 41,63 → 32,89 Md$ (≈ −21 %) autour de la crise.
- **Hypothèses** : H1 **REFUTED** (8 preuves) · H2 **SUPPORTED** (76 preuves) · H3 **REFUTED** (4 preuves).
- **Décision** : **ACTION_RECOMMENDED** — transfert borné de **100 USDC de test** (trésorerie → réserve), conformément à la règle gelée.
- **Baseline A0** : 2 signaux en fenêtre de crise (premier déclenchement 11/03 03:00Z), **0 en fenêtre témoin** → 0 faux signal.
- **Politique** : `I1 ALLOW` (instruction non signée produite) · `I2 DENY` (`AMOUNT_ABOVE_TX_CAP`, `AMOUNT_ABOVE_PERIOD_CAP`) · `I3 REQUIRE_APPROVAL` (`ACTION_NEEDS_HUMAN_APPROVAL`).
- **Suite de tests** : 112 tests — **1 échec connu en cours de correction** dans `tests/test_decision.py::test_real_corpus_regression_values` (valeur attendue 34 vs calculée 36 pour les heures d'alerte simultanée). Signalé volontairement ici : ne le laissez pas passer en revue.

**Chiffre à vérifier en priorité** : les 34 vs 36 ci-dessus — si la valeur correcte change la conclusion H2, c'est un point critique.

---

## 6. Ce que nous voulons que vous attaquiez (par ordre de priorité)

### A. Sécurité (le plus important — 30 % de la note)
1. **Contournement de politique** : existe-t-il un chemin dans le code qui produit une action sans passer par `evaluate()` ? (cherchez les appels directs à `execution/` sans verdict)
2. **Les 7 attaques suffisent-elles ?** Manquent notamment : rejeu après expiration, changement d'allowlist par l'agent lui-même, oracle de prix manipulé, dépassement par accumulation, signature mal formée, mauvaise chaîne au niveau du RPC, calldata construit avec un décimal erroné.
3. **Vérification du reçu** : peut-on faire accepter un reçu qui ne correspond pas à l'intention autorisée (mauvais destinataire, mauvais montant, autre contrat) ?
4. **Secrets** : confirmer qu'aucune clé, aucun jeton, aucun secret ne peut être journalisé, commité ou affiché.

### B. Finance et méthode (40 % de la note)
5. Les critères de réfutation de H1/H2/H3 sont-ils réellement **falsifiables** et pré-enregistrés ? Une conclusion opposée était-elle atteignable ?
6. La **baseline A0** est-elle une comparaison honnête ou un homme de paille ? Proposez une baseline plus forte (moyenne mobile, bande de Bollinger, règle multi-venue).
7. Le moteur peut-il produire **INCONCLUSIVE** correctement quand une série manque ? Le test le prouve-t-il sur le corpus réel ?
8. La règle de décision gelée est-elle défendable devant un jury de fintech (pas seulement cohérente avec elle-même) ?

### C. Données et provenance
9. Chaque chiffre déterminant a-t-il une observation parente ? (voir `evidence/graph.sqlite`, `provenance.ok`)
10. La couverture est inégale (Binance 83 h sur 145, Bitstamp 145 h) : est-ce déclaré partout où c'est utilisé ? Où cela fausse-t-il une conclusion ?
11. Le corpus est-il rejouable à l'identique ? (`python collect_corpus.py --offline`)

### D. Conformité au concours
12. Une seule soumission par équipe, 2–5 membres, ≥ 60 % non-Chinois, anglais pour tous les livrables.
13. Aucune promesse de rendement, aucun jeton émis, aucun fonds réel — le prototype doit rester un **testnet**.
14. Les 6 pièces obligatoires : doc technique EN · deck ≤ 10 min · **vidéo ≤ 5 min** · code + README + tests + `LICENSES.md` · rapport d'auto-évaluation sécurité · preuves (hash, reçu, refus).

### E. Interaction et innovation (30 % de la note)
15. Qu'est-ce qui manque pour qu'un jury voie une **démonstration** et non une explication ? (le dossier d'une page suffit-il ? que filmer ?)
16. La différenciation face à ERC-8273 / ERC-7715 / AP2 / x402 tient-elle ? (le projet revendique « producteur de décisions vérifiables », pas « portier de l'exécution »)

---

## 7. Comment proposer une amélioration (format imposé)

Un fichier par proposition, ou une issue avec ce format :

```
PROBLÈME  : une phrase.
PREUVE    : fichier:ligne (ou commande + sortie).
IMPACT    : pourquoi ça compte (sécurité / score / faisabilité).
PROPOSITION : le correctif, en 1–3 phrases.
TEST      : le test qui prouverait que c'est corrigé (nom + assertion).
PRIORITÉ  : P0 (bloque la soumission) / P1 (important) / P2 (confort).
```

**Règles** :
- Ne **jamais** modifier `corpus/` (c'est une preuve archivée) ni les fichiers `evidence/` à la main.
- Un constat sans fichier:ligne n'est pas un constat — il sera renvoyé.
- « Je n'aime pas » n'est pas une revue ; chaque critique doit nommer le critère qu'elle sert.

---

## 8. État d'avancement exact (14/10, ~14:40 UTC — décompte : 6 jours)

**Fait et exécuté** : corpus multi-sources + manifeste · moteur de décision + baseline A0 · politique + banc de sûreté · couche qualité/graphe/provenance · couche exécution (instruction non signée + vérification de reçu) · dossier d'audit + serveur local · orchestrateur bout-en-bout · figure du cas.

**Reste à faire (dans l'ordre)** : corriger le test signalé en §5 · documentation technique EN + rapport de sécurité · wallet de test financé (action humaine : faucets) · tournage de la vidéo ≤ 5 min (à J5) · deck ≤ 10 min · vérification finale de conformité · dépôt GitHub rendu public à la soumission.

**Inconnues externes (en attente de réponse des organisateurs)** : testnet accepté comme preuve d'exécution ? · carte d'identité acceptée pour les passeports expirés ? · clôture anticipée des inscriptions (risque).

---

## 9. Comment être sûr de travailler sur la bonne version

Le ZIP partagé contient un `MANIFEST.sha256`. Vérification :

```bash
sha256sum -c MANIFEST.sha256     # Linux/macOS/Git-Bash
```

Si un hash ne correspond pas, vous ne travaillez pas sur le snapshot annoncé — redemandez le paquet.
