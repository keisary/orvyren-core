# ORVYREN — Synthèse consolidée des audits critiques (18 octobre 2026)

> Source : deux documents joints, en réalité **le même audit** (contenu strictement identique) — un seul audit critique du 18/10, fondé sur le code GitHub publié + les revues de code du 17 et 18/10. L'auteur n'a pas pu cloner/exécuter le projet (constats sur code publié, certains à confirmer par test d'intégration).

---

## 1. Constat central (en une phrase)

**ORVYREN n'a pas un problème de fonctionnalités manquantes, mais un problème de connexions** : des composants solides (politique déterministe, boucle d'agents bornée, provenance, graphe on-chain, contrôle on-chain) **ne sont pas reliés entre eux de façon à produire une valeur financière démontrable**.

Deux niveaux de réussite distincts :
- ✅ construire les composants (fait : 1073 tests, 16 174 nœuds, agents LIVE, démo permissions)
- ❌ démontrer qu'ils résolvent ensemble un problème financier (pas fait : `EVAL N=0`, Q2 = 0 chemin, aucune supériorité mesurée)

**Décision stratégique : ni rewrite, ni empilement de features.** Corriger les connexions, rendre les agents utiles, démontrer sur un seul cas d'usage cohérent.

## 2. Les 3 blocages prioritaires

| # | Blocage | Fait observable |
|---|---------|-----------------|
| B1 | **Les agents ne sont pas branchés sur le vrai graphe** | `run_agents.py` → `build_v1_registry(fixtures=...)` : outils = lecteurs de données figées. Le vrai registre (`graph_tools.py` → `build_graph_registry`, branché sur SQLite) existe mais n'est **pas utilisé** par le worker. |
| B2 | **La contribution des agents à la décision n'est pas prouvée** | Agents, moteur de décision et exécuteur = 3 chemins séparés, pas une boucle intégrée dont on peut mesurer l'effet. |
| B3 | **La valeur ajoutée n'est pas validée** | `EVAL N=0`. Le run du 17/10 (18 appels LLM, 12 outils, 137 s, 0,0192 $, ARRET-2, critique FRAGILE → REQUIRE_APPROVAL) prouve que la boucle *tourne*, pas qu'elle *améliore* la décision. |

## 3. Inventaire complet des défauts

### P0 — bloquants produit

| ID | Défaut | Correction exigée |
|----|--------|-------------------|
| **P0-1** | Chemin principal des agents sur données figées (fixtures) ; `GraphQueryTool` renvoie le snapshot sans interroger le graphe ; `compute_signal` recopie un signal pré-calculé ; deux registres d'outils non unifiés | **Un seul registre**, code d'outils commun, seul le fournisseur de données change : `LIVE` = vrai graphe/sources, `REPLAY` = réponses enregistrées de ces mêmes interfaces, `FIXTURE` = données simulées explicitement marquées. Le registre du worker = celui testé en E2E. |
| **P0-2** | Agents → décision → exécuteur = chemins disjoints ; une découverte d'agent peut ne rien changer à la décision | **Chaîne de données unique** avec run_id partagé et contrats structurés : Snapshot vérifié → Recherche agents → Arbitre déterministe → Décision + politique (ALLOW/DENY/REQUIRE_APPROVAL) → Exécution + évaluation. Chaque étape consomme et référence les artefacts de la précédente. |
| **P0-3** | Graphe volumineux mais sémantiquement pauvre : 8 types d'arêtes peuplés, **0 arête `DEPENDS_ON`/`AFFECTS`** → Q2 = 0 chemin, aucune liquidation, aucune permission Safe/Zodiac dans le slice | Partir des **requêtes financières exigées**, puis : données sources → relations justifiables uniquement → test d'intégration avec chemin réel attendu → traçabilité jusqu'à l'événement source → abstention explicite (`NO_PATH`/`NOT_INGESTED`) si lacune. **Jamais de relation causale inventée pour remplir le graphe.** |
| **P0-4** | Décision/action incohérentes : « transférer 100 USDC » ne réduit pas le risque de décrochage USDC ; double logique décisionnelle (`build_decision_record` vs moteur RDOF) | Chaque action = **objectif économique mesurable + fonction de perte + conséquence attendue**. Question test : *« si on n'avait pas agi / agi autrement, quel risque aurait changé ? »* — si non calculable → abstention ou limite annoncée, pas de « réduction de risque démontrée ». Unifier sur une décision canonique. |
| **P0-5** | `EVAL N=0` : aucune preuve de gain décisionnel ; 3 rejeux archivés trop limités | **Benchmark A0/A1/A2** sur mêmes épisodes et budgets : A0 = moteur déterministe seul, A1 = recherche fixe non adaptative, A2 = ORVYREN complet. Mesurer qualité de décision (décisions incorrectes, événements manqués, abstentions justifiées, coût, latence, conséquences financières), + **cas placebo, données contradictoires, infos manquantes**. Seuil de supériorité : N≥100. |
| **P0-6** | **Faille de provenance** : les références d'un claim ne sont pas comparées aux références réellement observées → un claim peut citer une source inventée (le hash de journal ne protège pas contre un claim faux) | Pour chaque claim : vérifier que chaque référence appartient à l'ensemble observé (ou source autorisée), que le contenu matche le hash, que l'observation est admissible à l'instant de la décision, statut épistémique explicite, claim/preuves séparés. **Référence inconnue = rejet ou quarantaine**, jamais remplacée par une source « similaire ». |

### P1 — sûreté, temps, tests, reproductibilité

| ID | Défaut | Correction |
|----|--------|------------|
| **P1-1** | Bornes non appliquées : `deadline_s` accepté mais ignoré, `limit=-1` et `max_depth` non bornés dans les outils graphe | Validation stricte, maxima dans le code, horloge monotone, arrêt effectif aux limites — identique en exécution et en rejeu. |
| **P1-2** | Temps : Q5 filtre `as_of` sur `event_time` mais pas `observation_time` (donnée publiée après coup = non admissible) ; comparaisons d'horodatages en texte avec offsets hétérogènes | Règles temporelles définies **une seule fois**, appliquées partout ; UTC normalisé ; tests adverses (révisions tardives, offsets, publication post-instant simulé). |
| **P1-3** | API politique permissive : `state=None` → P7/P11/P12/P14 en `SKIPPED` | État **obligatoire** en mode production, séparation explicite simulation/production, refus si éléments de vérification manquants. |
| **P1-4** | Q8 ne résout pas les allowances des rôles ; permissions Safe/Zodiac absentes du slice → `NOT_INGESTED` (bon comportement, mais démo sécurité et démo graphe non reliées) | Ingérer les permissions du scénario choisi ; leur **absence bloque explicitement l'action** et reste visible dans le dossier d'audit. |
| **P1-5** | Verrouillage expérimental : cascade G5 sur le libellé et non le contenu, hashes de code Gx non vérifiés, embargo calibration facultatif (`--calibration-periods`) | Paramètres indispensables, contrôle des artefacts réellement utilisés, séparation stricte données d'élaboration / d'évaluation. |
| **P1-6** | 1073 tests verts mais harnais dégradé : assertions tautologiques, objets jamais connectés au parcours testé, empreintes comparées à elles-mêmes, fuites tmp/fichiers ouverts, skips masquants ; 69 mypy + 49 Bandit (faible/moyen) | **Retirer les tests qui ne prouvent rien**, renforcer tests de contrats/intégration. 6 invariants à tester : référence inventée rejetée / observation non admissible exclue / changement de données → hypothèse mise à jour / info manquante → abstention / intention politique = intention exécutée / reçu vérifiable (actif, destinataire, montant, réseau). |
| **P1-7** | Graphe réel non reproductible depuis un clone (base Aave 50 Mo + brut d'ingestion hors dépôt, sur machine Windows locale) | Jeu de démo **redistribuable** (sous-ensemble déterministe OK), manifeste de provenance, scripts de reconstruction du graphe. Un tiers doit rejouer la démo hors ligne. |
| **P2** | Gouvernance doc : `FREEZE_V2.md` annoncé autorité vs doc technique « référence de vérité » ; versions multiples coexistantes | Un document = périmètre livré réellement, un registre = décisions et écarts, non-implémenté marqué comme tel. |

## 4. Ce qu'il faut ABSOLUMENT préserver

- Politique déterministe séparée des modèles
- Boucle d'agents bornée + critique adversariale (budget, escalade, coût maîtrisé)
- Provenance, intégrité des journaux, rejeu
- Graphe bâti sur données on-chain réelles
- Politique d'autorisation + contrôle on-chain (la démo : 1 succès + 12 reverts volontaires)
- Permission interdite au LLM d'exécuter (`execute_intent` exclu du registre de recherche) — **ne jamais donner au LLM le pouvoir de signer ou contourner la politique**

## 5. Plan de correction en 6 étapes (ordre strict)

| Étape | Action | Critère de sortie |
|-------|--------|-------------------|
| **1** | Réparer l'intégration **agents ↔ graphe** : un seul registre, modes LIVE/REPLAY/FIXTURE, références validées | Un agent récupère une preuve depuis le vrai graphe et l'utilise dans une branche d'hypothèse vérifiable ; le journal montre la requête, params, références et provenance |
| **2** | Unifier **raisonnement → décision → exécution** : run_id partagé, contrats structurés entre étapes | Le journal démontre quelle observation a modifié quelle hypothèse, pourquoi le moteur a choisi cette action, comment la politique l'a autorisée/bloquée |
| **3** | Valider le **scénario financier** de bout en bout : risque observé → action à effet justifiable | Dossier : risque initial, alternatives, action retenue, résultat attendu — sans confondre transfert opérationnel et réduction d'exposition |
| **4** | Fermer les **défauts de sûreté** : références inventées, bornes, point-in-time, état politique obligatoire, verrouillage benchmark | Tests négatifs prouvant que données/paramètres manquants, contradictoires ou interdits **bloquent** le parcours |
| **5** | Prouver la **valeur ajoutée des agents** : benchmark A0/A1/A2 + placebos | Résultats montrant quand les agents aident, quand ils n'apportent rien, quand ils doivent s'abstenir — sans revendication de supériorité au-delà de l'échantillon |
| **6** | Rendre le produit **démontrable par un tiers** : parcours unique, données redistribuables, commandes, résultats versionnés | Un évaluateur part du dépôt, exécute, inspecte les sources et vérifie les assertions sans explication orale |

**Gel fonctionnel jusqu'à l'étape 4 minimum** : aucun nouvel outil, modèle, agent ou relation avant que la chaîne ne soit intégrée et démontrée.

## 6. Chaîne cible (contrats entre étapes)

```
┌─────────────────────┐
│ 1. SNAPSHOT VÉRIFIÉ │  instant de référence, sources, observations, provenance
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 2. RECHERCHE AGENTS │  hypothèses concurrentes, requêtes utiles, preuves
│    (propose/cherche)│  contradictoires — outils LIVE = vrai graphe
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 3. ARBITRE DÉTERM.  │  vérif. des références (P0-6), critères falsifiables,
│    (admissible ?)   │  calcul de risque — rejette les refs inventées
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 4. DÉCISION +       │  action candidate OU abstention
│    POLITIQUE        │  → ALLOW / DENY / REQUIRE_APPROVAL (état obligatoire)
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 5. EXÉCUTION +      │  intention autorisée = intention exécutée, reçu,
│    ÉVALUATION       │  résultat réel comparé à la prévision
└─────────────────────┘
         run_id partagé + artefacts référencés d'une étape à l'autre
```

## 7. Échéance et priorisation (contexte ajouté — commentaire @keisary, 18/10)

> « Le diagnostic est exact : excellent socle de vérification/traçabilité, mais **les agents n'influencent aucune décision et rien ne vit sans rejeu**. ~61 h avant le **20/10 15:59 UTC**. Priorité : **brancher les agents au chemin de décision** et **aligner les pièces de soumission sur le code réel**. »

Mesure au 18/10 02:39 UTC : **61 h 20 restantes**. Le plan 6 étapes (§5) est donc compressé ; les critères de sortie restent, les volumes non. Le benchmark N≥100 (P0-5) est **explicitement reporté après soumission** — on ne revendique aucune supériorité, on montre une chaîne intégrée et honnête.

### Plan horodaté (fenêtre glissante, ordre strict)

| Fenêtre | Objectif | Contenu | Critère |
|---------|----------|---------|---------|
| **H0–H12** | Agents branchés au graphe réel (P0-1 + P0-6) | Unifier `tools.py`/`graph_tools.py` en un registre à 3 modes (LIVE/REPLAY/FIXTURE) ; `run_agents.py`/`worker.py` appellent le registre branché ; validation des références d'un claim contre l'ensemble observé (ref inconnue → rejet/quarantaine) | Un run LIVE journalise une requête graphe réelle + provenance ; test négatif : claim à référence inventée rejeté |
| **H12–H24** | Chaîne décisionnelle unique (P0-2 + P0-4) | `run_id` partagé agents → arbitre → décision canonique (RDOF, pas `build_decision_record` en parallèle) → politique → exécuteur ; chaque étape consomme l'artefact précédent ; action = objectif économique déclaré ou abstention | Le journal relie une observation à un changement d'hypothèse, à la décision et au verdict de politique |
| **H24–H36** | Scénario financier + graphe pertinent (P0-3) | Cas démo = épisode rsETH 2026-04 ; n'ingérer que les relations justifiables ; Q2 sans arête → `NO_PATH` documenté comme lacune ; permissions absentes → `NOT_INGESTED` bloquant | Dossier : risque → alternatives → action/abstention → effet attendu, chaque donnée remonte à sa source |
| **H36–H48** | Sûreté (P1-1, P1-2, P1-3) | Bornes réelles (`deadline_s` monotone, `limit`/`max_depth` bornés) ; Q5 filtre aussi `observation_time` ; comparaisons temporelles en datetime aware ; `state=None` → refus en mode production | Tests négatifs verts : paramètres interdits/manquants bloquent le parcours |
| **H48–H56** | Mini-benchmark honnête (P0-5 réduit) | A0 vs A2 sur le/les épisodes de démo + 1 cas placebo, budgets identiques ; rapport sans revendication de supériorité (N≪100) | Tableau A0/A2 + « quand les agents aident / n'apportent rien / s'abstiennent » |
| **H56–H61** | Pièces de soumission alignées sur le code réel (P2, P1-7 réduit) | Compteurs README/DOC4/DEMO_KIT = `Ran N tests` mesuré ; hiérarchie doc : un doc = périmètre livré, registre des écarts ; sous-ensemble de démo reproductible + manifeste ; runbook unique | Un évaluateur clone, exécute le runbook et vérifie les assertions sans explication orale |

### Reporté après soumission (déclaré, pas caché)
Benchmark N≥100 avec placebos complets · ingestion permissions Safe/Zodiac · nettoyage complet du harnais de tests (69 mypy / 49 Bandit) · dataset redistribuable complet · capacité live hors épisodes de référence.

### Interdits pendant la fenêtre
Aucun nouvel outil, agent, modèle ou type de relation · aucune relation causale inventée · aucune revendication d'ÉVAL positive · pas de 3ᵉ chemin d'outils · pas de « patch silencieux » d'un module gelé (re-scellement visible).

## 8. Le test ultime de crédibilité

> Si ORVYREN avait choisi de ne pas agir, ou d'agir autrement, quel risque ou quelle perte aurait changé ?

Si cette différence n'est pas calculable → le système peut démontrer son portefeuille de composants, mais **pas** présenter l'opération comme une réduction de risque démontrée.

Et la comparaison qui transforme le projet en produit : **A2 vs A0** — si les agents ne trouvent jamais de preuve nouvelle ni ne changent la qualité de la décision, on change leur rôle/outils/méthode, on ne prétend pas qu'ils sont utiles parce que la boucle tourne.
