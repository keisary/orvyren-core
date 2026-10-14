# ORVYREN-Core — DÉCISIONS À GELER AVANT DE CODER (V1, 14 octobre 2026)

**Réponse courte à la question « le document V0.2 suffit-il pour lancer le travail ? » : oui, comme base de conception — mais pas encore comme spécification d'exécution.** La V0.2 définit le cas, les sorties de décision, les hypothèses, les principes, les niveaux de permission, les métriques et les phases P0–P5. Il manque dix valeurs concrètes que personne ne peut deviner à ta place. Ce document les propose toutes avec une valeur par défaut : **coche, corrige ou rejette — puis on code.**

> Règle : toute valeur ci-dessous est une **proposition**, pas une décision de l'équipe. Les valeurs marquées « préenregistrées » doivent être figées **avant** de regarder les résultats, sinon l'évaluation ne vaut rien.

---

## 1. Décisions de périmètre (bloquent le plan de travail)

| # | Décision | Valeur proposée | Statut |
|---|---|---|---|
| D1 | Cas pilote | Décision de trésorerie face à l'anomalie USDC (mars 2023) — fenêtre principale **9 → 15 mars 2023**, pas horaire | ☐ à geler |
| D2 | Fenêtre témoin (contrôle) | **15 → 18 février 2023** (même source, même granularité) | ☐ à geler |
| D3 | Deux sources + une référence documentaire | DeFiLlama (agrégateur) + Bitstamp **et** Binance (exchanges indépendants) + déclaration Circle du 12/03/2023 | ☐ à geler |
| D4 | Ce qui est exclu de N1 | multi-chaîne, base graphe, multi-agent, attestation EAS, ERC-7715, mainnet réel | ☐ à geler |
| D5 | Réseau d'exécution | **Base Sepolia (84532)**, actifs de test uniquement | ☐ à geler |

## 2. Hypothèses et critères de réfutation (préenregistrés — sinon l'évaluation est invalide)

| # | Hypothèse | Critère de soutien (proposé) | Critère de réfutation (proposé) |
|---|---|---|---|
| H1 | Perturbation locale de liquidité | Écart > 1 % sur **une** venue, agrégat < 0,5 % sous l'ancrage, et retour à ± 0,1 % en moins de 12 h | Écart > 1 % persistant sur ≥ 2 venues indépendantes pendant > 12 h |
| H2 | Stress large sur l'actif ou l'émetteur | Écart > 1 % simultané sur ≥ 2 venues indépendantes **et** baisse de l'offre en circulation > 1 % en 24 h, **ou** communication officielle datée | Signaux isolés à une venue et aucune évolution d'offre ni confirmation indépendante |
| H3 | Artefact de données ou de marché | Unité/contrat/horodatage incohérents, ou divergence non explicable entre deux sources de natures distinctes | Confirmation cohérente par ≥ 2 sources indépendantes et vérification de contrat |

**Sortie obligatoire** : le système doit pouvoir conclure **INCONCLUSIVE** et le prouver par écrit (quelle observation manquait, à quel coût elle était disponible).

## 3. Baseline A0 (l'adversaire du projet)

| # | Décision | Valeur proposée |
|---|---|---|
| D6 | Règle fixe de référence | « Si le prix d'agrégateur < 0,99 pendant **2 observations horaires consécutives** → réduire l'exposition de 100 USDC ; sinon NO-ACTION » |
| D7 | Ce que la baseline démontre | Sa simplicité, et son **taux de faux signaux** sur la fenêtre témoin — c'est la comparaison qui donne du sens à A2 |

## 4. Action bornée et politique (bloquent l'implémentation wallet)

| # | Décision | Valeur proposée |
|---|---|---|
| D8 | Action de démonstration | Transfert de **100 USDC de test** (jeton de test Circle, Base Sepolia) du wallet « trésorerie » vers le wallet « réserve » ; plus tard, option swap testnet via `SwapRouter02` (étiqueté démonstration technique) |
| D9 | Six règles de politique | (1) chaîne = 84532 uniquement ; (2) actif allowlisté = USDC de test ; (3) destinataire allowlisté (1 adresse de réserve) ; (4) plafond **100 USDC/transaction** et **300 USDC cumulés** ; (5) expiration de la permission à 24 h ; (6) idempotence par `intent_id` — hors de ces règles : DENY, et REQUIRE_APPROVAL pour tout changement d'exposition ou de configuration |

## 5. Tests, métriques, livrables

| # | Décision | Valeur proposée |
|---|---|---|
| D10 | Sept attaques du banc de sûreté | destinataire hors allowlist · montant > plafond · actif hors allowlist · mauvais chain ID · intent rejoué · permission expirée · injection de données externe |
| D11 | Métriques d'acceptation | provenance 100 % des claims déterminants · **0** action hors politique sur 7 tests · **10** parcours E2E consécutifs · coût par décision mesuré · comparaison A0 vs A2 · score de Brier si ≥ 5 prévisions gelées |
| D12 | Livrables du concours | doc technique EN · deck ≤ 10 min · **vidéo ≤ 5 min (tournée à J5)** · code + README + tests + LICENSES · rapport sécurité (T0–T4 × risques × tests) · preuves (hash, receipt, refus) — tableau de répartition dans `EVALUATION_V0_2.md` §4 |

---

## 6. Ce que ces gels débloquent, dans l'ordre

1. **Collecteur de corpus** (`collect_corpus.py` — déjà écrit et en cours d'exécution) : D1, D2, D3.
2. **Moteur de décision + baseline** : D6, D7, H1–H3 (critères), D11.
3. **Politique + wallet de test** : D5, D8, D9, D10 — nécessite le wallet financé (action humaine : faucets Base + Circle).
4. **Dossier de décision, UI d'audit, livrables** : D12.

## 7. Ce qui n'a pas besoin d'être décidé maintenant

Base graphe spécialisée · attestation EAS · ERC-7715 · multi-agent parallèle · multi-chaîne · FIBO · mainnet réel · nom de domaine et marque. La V0.2 les a déjà reportés ; on n'y revient qu'avec un benchmark à l'appui.

## 8. Ce qui reste **inconnu** et ne peut pas être gelé sans réponse externe

| Inconnu | Conséquence tant qu'il n'est pas levé | Méthode |
|---|---|---|
| Testnet accepté comme preuve d'exécution | la démo peut être jugée insuffisante | email envoyé aux organisateurs (en attente) |
| Documents d'identité acceptés (passeport expiré) | l'inscription peut être refusée | même email |
| Clôture anticipée des inscriptions | risque de ne pas être reçu du tout | envoyer le formulaire dès la réponse |
| Accès aux faucets (jetons de test) | bloque D8 | actions humaines, 3 faucets en réserve |

---

**Prochaine action** : cocher les valeurs D1–D12 (5 minutes), puis lancer le dépôt : `src/` (connecteurs, graphe, décision, politique, exécution), `tests/` (banc de sûreté), `docs/`, `evidence/`.
