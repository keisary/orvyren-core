# ORVYREN — B4 · ÉTUDE DU BLOC POLITIQUE & AUTORISATION

**15 octobre 2026.** Chantier « bloc 4 » de la carte `research/SYSTEME_ZONES_OMBRE.md` (§4, questions 4.1-4.3). Objet : consolider la **spécification finale de la politique v1** (verrous déterministes hors LLM), le **flux REQUIRE_APPROVAL**, la **formalisation/versionnage**, le **mapping policy ↔ Zodiac + test de dérive**, la **procédure d'incident** et le **schéma `PolicyDecision`**, et trancher ce qui reste ouvert.

Conventions de statut : **FAIT SOURCÉ** (claim adossé à une source citée, URL + date), **MESURÉ** (chiffre produit par le dépôt ou l'outillage interne, reproductible), **CONCEPTION/PROPOSITION** (choix d'ingénierie à valider en revue d'équipe). « Non trouvé » remplace toute donnée que les sources consultées n'établissent pas.

Documents de base : `SYSTEME_ZONES_OMBRE.md` §4 · `W2C_enveloppe_execution.md` (mécanique Zodiac, signer, matrice 12 attaques, runbook, plan de démo §g) · `B3_DECISION_ETUDE.md` (catalogues d'actions bornées, 3 axes, ESCALATE) · `ARCHITECTURE_V1.md` §2-3 (règle de dépendance, contrats) · V0.2 §10.1-10.4 (pipeline, niveaux T0-T4, sécurité) · code : `src/orvyren/policy/__init__.py`, `tests/test_policy.py`, `src/orvyren/execution/{guard,intents}.py`, `src/orvyren/audit/dossier.py`.

---

## 0. Résumé exécutif (ce que ce document tranche ou propose)

1. **Set v1 = 14 règles (P1-P14)** : les 8 règles codées et testées (R1-chaîne → R8-action) deviennent le socle, complétées par 6 règles nécessaires à la v1 complète : **fonction scopée (P4)**, **exposition/solde (P7)**, **fraîcheur d'intent (P9)**, **pause (P11)**, **alignement d'enveloppe (P12)**, **budget (P14)**. Codes de refus stables, exhaustifs (§a.2-a.3) ; les cas déjà couverts (NaN/infini, cumul invalide, injection) sont conservés tels quels.
2. **Flux REQUIRE_APPROVAL** : quatre options réelles comparées (§b) — file d'approbation Safe native, timelock Zodiac Delay, bot d'ops + app d'approbation, lien signé EIP-712. Recommandation v1-démo : **file d'approbation ORVYREN minimale, ancrée par une signature EIP-712 du mandant** (le canal notifie, la signature autorise). Direction produit : file multi-rôles avec SLA configurables (précédent chiffré : Fireblocks, 5 min-24 h, défaut 2 h ; demandes de changement de politique : 7 jours) et, côté chaîne, **Zodiac Delay** pour la classe T3.
3. **Formalisation** : « **code = source de vérité de la sémantique ; `policy.yaml` = source de vérité des paramètres ; le banc de tests = preuve ; le document = description** ». `policy_version` (MAJOR.MINOR) + `policy_hash` dans **chaque** verdict et chaque entrée de journal ; procédure de changement en 6 étapes avec règle d'asymétrie (réduire un plafond = immédiat ; augmenter = procédure complète).
4. **Mapping Zodiac** : sur 14 règles, **4 pleinement exprimables on-chain** (P2 cible, P3 destinataire, P4 fonction scopée, P5 montant par condition), **4 partiellement** (P1 chaîne par instance, P6 cumul par allowance, P11 arrêt par révocation, P13 périmètre par défaut) et **5 non exprimables** (P7 solde/exposition, P8 expiration native, P9 fraîcheur, P10 rejeu, P14 budget) ; P12 est l'objet même du **test de dérive** (script stdlib + test offline en CI ; divergence ou impossibilité de vérifier → **SAFE MODE** : refus de tout autonome, journal `ENVELOPE_DRIFT/UNVERIFIED`).
5. **Incident** : K0 (pause hors chaîne, immédiat) → K1 `assignRoles(false)` (1 tx DAO, ~1,64 s/bloc Base mesuré) → K2 `disableModule` → K3 asphyxie gaz ; délais cibles (K0 ≤ 5 min après détection, K1 ≤ 60 min — le seul délai non compressible est la coordination humaine) ; communication, journal chaîné, redémarrage conditionné au test de dérive + procédure de changement.
6. **`PolicyDecision` v1** : verdict + `reasons[]` + `rules_evaluated[]` (existant) enrichis de `decision_id`, `intent_hash`, `policy_version`, `policy_hash`, `envelope_ref`, bloc `approval`, `context_used` ; interfaces B3 (l'intent borné entre, le verdict sort) et B5 (l'exécution n'accepte **que** `ALLOW`, refus journalisé sinon).

---

## (a) Set v1 des règles — liste finale, règle par règle

### a.1 Principes de conception

- **Déterministe et hors LLM** : la politique est un service pur (`Intent`, `PolicyConfig`, état local → `PolicyDecision`) ; le modèle de langage n'entre jamais ici (ARCHITECTURE_V1 §2 : `policy` n'importe ni `research` ni un adaptateur LLM). FAIT SOURCÉ (code + doc).
- **Fail-closed** : tout état inaccessible, illisible ou invalide (compteur, solde, pause, alignement d'enveloppe) vaut **refus**, jamais « on suppose que tout va bien ».
- **Deny-by-default** : tout ce qui n'est pas explicitement autorisé est refusé (même philosophie que le module Zodiac ; W2C §a.2).
- **Codes de refus stables** : SCREAMING_SNAKE_CASE, jamais renommés ni réutilisés pour un autre sens ; un code déprécié reste dans le registre et n'est plus émis. C'est ce registre qui rend le journal opposable et rejouable.
- **Évaluation complète** : toutes les règles applicables sont évaluées et **tous** les codes en échec sont renvoyés (comportement actuel du code) — le dossier de refus montre *tout* ce qui ne va pas, pas seulement la première barrière heurtée.
- **Précédence du verdict** : `DENY` > `REQUIRE_APPROVAL` > `ALLOW`. Un FAIL de règle dure (P1-P12, P14) ⇒ DENY ; aucun FAIL et action hors périmètre autonome ⇒ REQUIRE_APPROVAL ; sinon ALLOW.
- **Trois classes d'action** (héritage du code, à conserver) : `ACTIONS_AUTONOMES = {transfer}` ; `ACTIONS_SOUS_APPROBATION = {swap, approve, change_policy, revoke}` → jamais autonomes ; tout le reste ⇒ DENY (`ACTION_UNKNOWN`).
- **Garde structurelle (pré-politique)** : le schéma de l'intent rejette champs inconnus, types incorrects, quantités négatives, adresses mal formées (V0.2 §10.2 point 2 — FAIT SOURCÉ). Codes : `SCHEMA_UNKNOWN_FIELD`, `SCHEMA_TYPE`, `SCHEMA_ADDRESS`, `SCHEMA_MISSING`. La politique ne reçoit qu'un objet déjà validé (quarantaine des anomalies).

### a.2 Table du set v1 (14 règles)

Colonne « Code » = règle du code actuel (`src/orvyren/policy/__init__.py`). Colonne « Zodiac » = exprimable on-chain (détail §d).

| # | Règle | Déclencheur | Portée | Verdict / code(s) de refus | Code actuel | Zodiac |
|---|---|---|---|---|---|---|
| **P1** | Chaîne épinglée | `intent.chain_id ∉ allowed_chain_ids` (démo : {84532} ; prod : {8453}) | Tout intent | DENY · `CHAIN_NOT_ALLOWED` | R1-chain (existe) | partiel (instance par chaîne) |
| **P2** | Actif/contrat autorisé | adresse actif (normalisée) ∉ allowlist | Tout intent | DENY · `ASSET_NOT_ALLOWED` | R2-asset (existe) | oui (cible) |
| **P3** | Destinataire allowlisté | adresse destinataire ∉ allowlist (comparaison insensible à la casse) | transfer | DENY · `RECIPIENT_NOT_ALLOWED` | R3-recipient (existe) | oui (condition) |
| **P4** | Fonction scopée | la paire (cible, sélecteur) ou le type d'opération ∉ registre v1 | Tout intent | DENY · `TARGET_NOT_ALLOWED` / `FUNCTION_NOT_ALLOWED` / `OPERATION_NOT_ALLOWED` | **à ajouter** (le code ne connaît que `action`) | oui (scopeFunction) |
| **P5** | Plafond par transaction | montant non fini / ≤ 0 / > `max_per_tx` | transfer | DENY · `AMOUNT_NOT_FINITE` / `AMOUNT_INVALID` / `AMOUNT_ABOVE_TX_CAP` | R4-amount (existe) | oui (condition + allowance) |
| **P6** | Cumul glissant 24 h | `cumul_glissant(24 h) + montant > max_cumulative` ; compteur invalide | transfer | DENY · `AMOUNT_ABOVE_PERIOD_CAP` / `CUMULATIVE_INVALID` | R5-cumulative (existe ; compteur externe à spécifier) | partiel (allowance ; rafale de frontière assumée) |
| **P7** | Exposition / solde max | solde illisible ; `montant > solde` ; solde post-action < plancher ; exposition post-action > plafond | transfer | DENY · `BALANCE_UNREADABLE` / `BALANCE_INSUFFICIENT` / `FLOOR_BREACH` / `EXPOSURE_ABOVE_CAP` | **à ajouter** | non |
| **P8** | Permission (mandat) active | `permission_expires_at` absent ; `now ≥ expiry` | Tout intent | DENY · `PERMISSION_MISSING` / `PERMISSION_EXPIRED` | R6-permission (existe) | non (pas d'expiry natif) |
| **P9** | Fraîcheur de l'intent | `now − created_at > ttl_intent` ; `created_at > now + skew` | Tout intent | DENY · `INTENT_STALE` / `INTENT_NOT_YET_VALID` | **à ajouter** | non |
| **P10** | Idempotence (rejeu) | `intent_id` déjà vu **ou** `intent_hash` (contenu canonique) déjà vu | Tout intent | DENY · `INTENT_ALREADY_PROCESSED` | R7-idempotency (existe ; ajouter la dédup par hash) | non (mitigé : nonce + quota d'appels) |
| **P11** | Pause / kill switch | drapeau pause actif ; pré-vol : agent plus membre du rôle | Tout intent | DENY · `PAUSED` / `AGENT_NOT_MEMBER` | **à ajouter** (K0/K1 décrits W2C §d.4) | partiel (K1/K2 oui ; « pause » non) |
| **P12** | Alignement d'enveloppe | config on-chain ≠ politique attendue ; vérification impossible | Toute évaluation | DENY (SAFE MODE) · `ENVELOPE_DRIFT` / `ENVELOPE_UNVERIFIED` | **à ajouter** (test §d) | n/a (c'est l'objet du test) |
| **P13** | Périmètre d'action | action inconnue → DENY ; action connue hors autonome → approbation | Tout intent | DENY · `ACTION_UNKNOWN` ; **REQUIRE_APPROVAL** · `ACTION_NEEDS_HUMAN_APPROVAL` | R8-action (existe) | partiel (§b) |
| **P14** | Budget de décision | budget de recherche/raisonnement épuisé ou incohérent | Tout intent | DENY · `BUDGET_EXCEEDED` / `BUDGET_UNREADABLE` | **à ajouter** (V0.2 §10.2) | non |

### a.3 Détail par règle (déclencheur exact, cas limites, justification)

**P1 — Chaîne épinglée.** Déclencheur : `chain_id` hors liste. En démo, la liste est exactement `{84532}` ; en production `{8453}` (Base) tant que l'enveloppe n'est déployée que là (W2C §g.8 : mêmes contrats, seul le `maxRefill` change). Cas limite : la **source de vérité** du `chain_id` est le RPC interrogé, pas le champ de l'intent seul — le pré-vol comparera `eth_chainId` du RPC épinglé au `chain_id` attendu (attaque #6 de W2C : « mauvaise chaîne au niveau RPC »). Le refus de P1 est donc doublé par le pré-vol d'exécution (B5).

**P2 — Actif autorisé.** L'actif *est* un contrat (adresse ERC-20) ; l'allowlist v1 contient l'USDC de test Circle Base Sepolia `0x036CbD53842c5426634e7929541eC2318f3dCF7e` (adresse vérifiée W2C §g.0, code 1 798 o — MESURÉ 2026-10-15). Normalisation : `strip().lower()` (déjà dans le code). `bool`/non-string ⇒ échec de la garde structurelle.

**P3 — Destinataire allowlisté.** Comparaison insensible à la casse ; l'allowlist est matérialisée par la condition Zodiac `Or(EqualTo(B), EqualTo(C))` sur le paramètre 0 de `transfer` (W2C §g.1 étape 3). v1-démo : ensemble à 2 adresses (réserve + une seconde), comme dans le plan de démo. L'ajout d'un destinataire est un **changement de paramètre** (MINOR, §c) et une tx DAO on-chain — jamais une décision de l'agent.

**P4 — Fonction scopée (ajout).** Registre v1 `action → (cible, sélecteur, schéma de paramètres, opération)` :

| action | cible | sélecteur | opération | Vérifié par |
|---|---|---|---|---|
| `transfer` | USDC de test | `transfer(address,uint256)` (`0xa9059cbb`, standard ERC-20) | `CALL` uniquement | P3 (param 0), P5/P6 (param 1) |
| `swap` | — | — | — | hors enveloppe v1 → REQUIRE_APPROVAL, jamais autonome |
| `approve` | — | — | — | idem |
| `change_policy` / `revoke` | — | — | — | idem (et **jamais** exécutables par l'agent : `onlyOwner`) |

Justification : c'est la règle n° 1 d'hygiène Zodiac — « autoriser une cible entière laisse passer n'importe quel calldata » (W2C §a.7 #3). Le registre est **le** mécanisme qui fait correspondre un intent lisible à un calldata exact, et il porte la table de correspondance fonction↔politique (§d).

**P5 — Plafond par transaction.** Trois codes : `AMOUNT_NOT_FINITE` (NaN/±infini — refus net **avant** toute comparaison ; c'est la correction du constat de revue F07 : `nan > 100` et `nan <= 100` sont tous deux faux, un NaN passerait silencieusement), `AMOUNT_INVALID` (≤ 0, ou non numérique), `AMOUNT_ABOVE_TX_CAP` (> 100 USDC en démo). Le montant est en **unités décimales canoniques du jeton** (6 décimales USDC) ; la canonicalisation (155.0 → 155000000) et son test anti « calldata mal décimé » (attaque #5 W2C) sont exigés avant signature — un débit de 1 000 000× doit être refusé par le plafond, pas découvrir l'erreur on-chain.

**P6 — Cumul glissant par période (compteur 24 h).** Spécification v1 :
- **Fenêtre glissante**, calculée `[now − 24 h, now]`, jamais une fenêtre calendaire (le calendaire est attaquable — W2C §d.3, attaque #2).
- **Clé du compteur** : par actif ; option v1.1 par (actif, destinataire). Chaque entrée stocke (intent_hash, montant, horodatage de receipt, statut).
- **Cycle de vie en deux phases**, calqué sur la sémantique on-chain (`_flushCommit` : l'allowance n'est consommée que si l'exécution réussit — W2C §a.2) : à l'ALLOW, **réservation** (statut `RESERVED`) ; au receipt `status = 1`, **engagement** (`COMMITTED`) ; en cas d'échec/revert, **libération** (`RELEASED`). Le compteur somme `COMMITTED + RESERVED` (le RESERVED protège des exécutions concurrentes). Le registre est append-only (`intent` + `execution` AV1 §4).
- **Invalide ⇒ refus** : compteur illisible, négatif, NaN (`CUMULATIVE_INVALID`) — jamais de « valeur supposée ». Si le montant est non fini, la règle est `SKIPPED` avec note (comportement actuel).
- **Limite assumée (W2C #2)** : le plafond on-chain est un plafond **d'accumulation** (`refill` par intervalle, plafonné à `maxRefill`) ; une dépense à `T−1 s` puis `T+1 s` de la frontière peut engager jusqu'à `maxRefill + refill` on-chain. Le compteur glissant hors chaîne est donc **le verrou strict** de cette frontière ; on dimensionne côté chaîne `maxRefill == refill` (pire cas ≈ 2 périodes) et on le documente dans le dossier concours au lieu de le nier (test dédié, §a.5).

**P7 — Exposition / solde max (ajout).** Quatre codes : `BALANCE_UNREADABLE` (lecture du solde impossible — fail-closed), `BALANCE_INSUFFICIENT` (montant > solde du compte payeur pour l'actif), `FLOOR_BREACH` (solde post-action < plancher configuré — ex. réserve opérationnelle DAO), `EXPOSURE_ABOVE_CAP` (exposition post-action à l'actif/émetteur > plafond — part de la trésorerie). Entrées : **instantané de portefeuille** (V0.2 §9.1 étape 1 ; B3 §d les utilise déjà pour borner `x*`), pas une lecture ad hoc. Portée : tout sauf le NO-ACTION documenté. Le plancher et le plafond d'exposition sont des paramètres v1 (MINOR) ; valeurs à trancher (§g). Le rapport au prix (valorisation oracle vs réalisable) reste l'affaire de B3 — la politique ne juge pas la qualité du prix, elle borne les quantités et l'état.

**P8 — Permission active.** `PERMISSION_MISSING` si `permission_expires_at` est `None` (refus par défaut, déjà testé : `test_11_permission_absente`), `PERMISSION_EXPIRED` si `now ≥ expiry`. La permission = le mandat (durée, plafonds, allowlists) — son expiration **hors chaîne** est la seule qui existe : `Allowance` Zodiac n'a **aucun** champ d'expiration (W2C §a.7 #1, vérifié dans `Types.sol`). Conséquence opérationnelle : une **révocation planifiée** (tâche) doit être programmée à l'échéance ; sinon l'échéance hors chaîne seule laisse la clé capable d'exécuter (limite documentée, attaque #9).

**P9 — Fraîcheur de l'intent (ajout).** `INTENT_STALE` si l'âge de l'intent dépasse le TTL (PROPOSITION : 15 min en démo, paramétrable) ; `INTENT_NOT_YET_VALID` si `created_at` est dans le futur au-delà d'un décalage d'horloge toléré (60 s). Justification : entre la décision (B3) et l'envoi, le monde bouge ; un intent ancien est un intent dont les prémisses (prix, état de stress) ne sont plus vérifiées, et W2C recommande « délais courts entre décision et envoi » (§d.4). L'intent porte `created_at` (RFC 3339 UTC, tz-aware) ; la politique vérifie l'horloge.

**P10 — Idempotence.** Deux détections : `intent_id` déjà vu (comportement actuel) **et** `intent_hash` — hash du contenu canonique (intent_id exclu) déjà vu — pour attraper la resoumission du même contenu sous un nouvel id. Registre persistant append-only (W2C §d.3 : « l'idempotence métier est une notion hors chaîne : `id = keccak(intention_normalisée)` »). Côté chaîne, les amortisseurs sont le nonce EOA (doublon brut rejeté) et le quota d'appels `CallWithinAllowance` (W2C §e #1) ; la chaîne, elle, **laisse** rejouer une transaction encore autorisée.

**P11 — Pause / kill switch.** Trois canaux, du plus rapide au plus fort (table complète §e) :
- `PAUSED` : drapeau du service de signature (K0) — toute nouvelle signature est refusée ; posé par l'astreinte, **jamais levé par l'agent** (règle : la levée exige un humain + entrée de journal).
- `AGENT_NOT_MEMBER` : pré-vol — si `Roles.roles(AGENT).members(agent)` est faux (K1/K2 exécutés), refus immédiat et journal (c'est la détection de la révocation DAO côté agent).
- Auto-pause (PROPOSITION) : la surveillance qui détecte un motif anormal (destinataire nouveau, rafale, montant inhabituel — W2C annexe 3) peut poser `PAUSED` sans humain (sens sûr uniquement).

**P12 — Alignement d'enveloppe (ajout).** Règle de **configuration**, pas de contenu d'intent : la politique v1 doit être **≤** l'enveloppe votée (plafonds ≤ allowances, allowlists = conditions, chaîne = instance). Vérifiée par le **test de dérive** (§d.3) au démarrage, avant chaque fenêtre d'exécution et en CI (fixture). Si la vérification échoue **ou est impossible** (RPC injoignable) → **SAFE MODE** : refus de toute action autonome (`ENVELOPE_DRIFT` / `ENVELOPE_UNVERIFIED`), alerte, journal. Le mode sûr ne bloque pas les lectures ni les dossiers — il bloque l'exécution.

**P13 — Périmètre d'action.** `ACTION_UNKNOWN` ⇒ DENY (tout ce qui n'est ni `transfer` ni une action connue sous approbation — ex. `bridge`, testé) ; `swap|approve|change_policy|revoke` ⇒ REQUIRE_APPROVAL `ACTION_NEEDS_HUMAN_APPROVAL` (déjà testé : `test_09`, `test_10`). `change_policy` est le cas emblématique : l'agent ne peut **jamais** modifier sa propre enveloppe (invariant I3 W2C : aucun rôle d'administration).

**P14 — Budget de décision (ajout, optionnel v1).** V0.2 §10.2 point 3 liste « budget » parmi les vérifications de politique, et W2-D rappelle que « le coût du raisonnement entre dans la perte ». Règle : refuser l'exécution si le budget de la décision (recherche/LLM) est épuisé ou illisible — `BUDGET_EXCEEDED` / `BUDGET_UNREADABLE`. Rattachée au dossier de décision (B3 §e.2 : `B_max` gelé). Marquée optionnelle : si l'équipe juge la v1 trop large, elle peut sortir du set sans casser les invariants — mais la trace de budget doit rester dans le dossier.

### a.4 Cas déjà couverts (à conserver tel quel)

| Cas | Test | Code émis |
|---|---|---|
| Destinataire hors allowlist | `test_01` | `RECIPIENT_NOT_ALLOWED` |
| Montant > plafond tx | `test_02` | `AMOUNT_ABOVE_TX_CAP` |
| Actif hors allowlist | `test_03` | `ASSET_NOT_ALLOWED` |
| Mauvais chain ID | `test_04` | `CHAIN_NOT_ALLOWED` |
| Intent rejoué | `test_05` | `INTENT_ALREADY_PROCESSED` |
| Permission expirée | `test_06` | `PERMISSION_EXPIRED` |
| Injection de données externe | `test_07` | (la `justification` est ignorée : seule la structure compte ; la forgerie réelle est refusée par `RECIPIENT_NOT_ALLOWED`) |
| Cumul dépassé | `test_08` | `AMOUNT_ABOVE_PERIOD_CAP` |
| Action sous approbation | `test_09` | `ACTION_NEEDS_HUMAN_APPROVAL` (REQUIRE_APPROVAL) |
| Action inconnue | `test_10` | `ACTION_UNKNOWN` |
| Permission absente | `test_11` | `PERMISSION_MISSING` |
| **NaN / infini** | (code, revue F07) | `AMOUNT_NOT_FINITE` |
| **Cumul invalide** | (code) | `CUMULATIVE_INVALID` |
| Cas nominal | `test_00` | `ALLOW` (aucun code) |

MESURÉ : le banc complet (`python -m pytest tests/ -q`, 15/10/2026) est **221 passed, 2 skipped** ; la politique seule = 12 tests, « 0 action hors politique ». C'est la mesure « sûreté des actions » de V0.2 §12.4 (cible ≥ 6 attaques — déjà dépassée).

### a.5 Tests à ajouter pour le set v1 (PROPOSITION, par ordre de priorité)

1. **P6 frontière de période** (attaque #2) : compteur glissant refuse la seconde dépense encadrant la frontière (le test documente la limite on-chain).
2. **P4 fonction scopée** : paire (cible, sélecteur) inconnue ⇒ `FUNCTION_NOT_ALLOWED` ; `DELEGATECALL` ⇒ `OPERATION_NOT_ALLOWED`.
3. **P5 décimales** (attaque #5) : `155.0 → 155000000` vs `155000000000000000000` ; le second est refusé.
4. **P10 dédup par contenu** : même `intent_hash`, `intent_id` différent ⇒ refus.
5. **P9 fraîcheur** : intent âgé > TTL ⇒ `INTENT_STALE` (et horloge future ⇒ `INTENT_NOT_YET_VALID`).
6. **P7 solde/exposition** : fixtures de portefeuille — solde insuffisant, plancher, plafond d'exposition ; lecture impossible ⇒ refus.
7. **P11 pause** : drapeau actif ⇒ `PAUSED` (aucune signature émise) ; agent non membre ⇒ `AGENT_NOT_MEMBER`.
8. **P12 dérive** : fixture de config on-chain conforme ⇒ PASS ; un plafond dérivé ⇒ SAFE MODE (test offline §d.4).

### a.6 Ce que la politique ne fait pas (frontières, à écrire noir sur blanc)

- Elle **ne juge pas les prix**, ne choisit pas de venue, ne calcule pas la perte évitée : c'est B3 (économique). Elle borne et autorise.
- Elle **ne signe pas** et ne détient aucune clé (W2C d.2) : elle rend un verdict ; le signer isolé n'exécute qu'un ALLOW.
- Elle **ne remplace pas** l'enveloppe on-chain : elle est le premier verrou, l'enveloppe le second (double verrou, W2C d.1).
- Elle **ne détecte pas** les anomalies de marché : c'est B2/W2-B (surveillance) ; elle applique l'état qu'on lui donne (pause incluse).

---

## (b) Flux REQUIRE_APPROVAL — options, comparaison, recommandation

### b.1 Le besoin, tel qu'établi

- La classe T3 existe déjà dans la conception : « Actions au-delà des limites ou qui changent l'exposition/configuration. L'approbation est externe au LLM ; la démo peut montrer le blocage sans l'exécuter » (V0.2 §10.3 — FAIT SOURCÉ). Le code la matérialise (REQUIRE_APPROVAL pour `swap|approve|change_policy|revoke`) mais **le flux d'approbation n'est pas implémenté** (carte §4.1 : « Flux d'approbation non implémenté » ; B3 A-D8 le cite comme « flux REQUIRE_APPROVAL à implémenter », « via file d'approbation (T3, Delay) »).
- Ce que le flux doit garantir : (i) **aucune exécution sans humain** pour T3 ; (ii) l'approbation est **explicite, attribuable et horodatée** ; (iii) elle **expire** (une approbation dormante ne doit pas s'exécuter une semaine plus tard) ; (iv) tout est journalisé et relisible ; (v) le canal de notification n'est **pas** l'autorité (il est falsifiable : phishing, faux bots).
- Contexte de direction produit (FAIT SOURCÉ) : le discours de C. Waller (Fed) à Sibos 2026 décrit les deux modèles d'agents de paiement et la conclusion qui nous concerne — « **The buyer may specify some constraints and set up guardrails, but the agent operates autonomously** » pour le modèle délégué, et les réseaux de cartes « include methods of **registering agents** and **logging cardholders' approvals** to conduct agentic payments » (BIS, 2026-10-05 ; Fed, 2026-09-29). Autrement dit : la trace d'approbation est déjà un objet réglementaire en formation — notre journal d'approbation va dans ce sens.

### b.2 Les quatre options réelles (sources + dates)

**Option A — File d'approbation Safe native (queue multisig + service de transactions).**
Mécanique : une transaction est **proposée** (par un owner ou un délégataire) avec sa signature ; les autres owners **signent le `safeTxHash`** (EIP-712) et confirment ; l'exécution se fait quand le seuil (n-of-m) est atteint. La collecte de signatures peut être **hors chaîne** (API) puis exécutée par n'importe qui. Source : Safe Docs « Transactions with off-chain signatures » (docs.safe.global, consulté 2026-10-15) : `proposeTransaction(...)` puis `signHash(safeTxHash)` + `confirmTransaction(...)` puis `executeTransaction(...)` — FAIT SOURCÉ. La file se lit dans l'app (`app.safe.global/transactions/queue`) ; dans les produits multisig (Coinshift), les transactions s'exécutent **dans l'ordre des nonces** et un owner qui atteint le seuil peut « Approve and Execute » en une étape (docs.coinshift.xyz, consulté 2026-10-15 — FAIT SOURCÉ). Un **Guard** peut poser des restrictions au-dessus du n-of-m (Safe Docs, page mise à jour 27/08/2026) — mais un Guard cassé bloque la Safe (DoS), donc l'introduire est un engagement d'audit.
Pour ORVYREN : c'est le mécanisme par défaut de la cible (trésoreries DAO déjà sur Safe). Coût : chaque approbation = une signature de plus, pas de contexte riche (le dossier de décision doit vivre à côté), et il faut une vraie Safe n-of-m en démo (plan W2C : Safe 2/3).

**Option B — Timelock on-chain : Zodiac Delay Modifier.**
Mécanique : une tx mise en file par un module activé s'exécute **après un cooldown** (sauf annulation du owner) ; paramètres `(owner, avatar, target, cooldown, expiration)`. Le guide officiel : « Pick the cooldown so that your owners can really react: **One hour is too short for a weekend attack. Common values are 1 to 7 days** » ; `expiration = 0` = jamais expirée (bloque la file) ; annulation : `setTxNonce(n)` (tx Safe du owner, à signer **pendant** le cooldown) ; exécution : `executeNextTx(data identique)` par n'importe qui ; surveillance par `queueNonce`/`txNonce` + événement `TransactionAdded` (docs.zodiac.eco « Delay guide », consulté 2026-10-15 — FAIT SOURCÉ). W2C §c.1 le désigne déjà comme « le bon outil pour le niveau T3 ».
Pour ORVYREN : c'est la **forme on-chain du REQUIRE_APPROVAL** — mais son sens juridique est inverse : une entrée en file s'exécute *si personne ne s'y oppose* (veto), tandis qu'un REQUIRE_APPROVAL attend une approbation *positive*. Les deux sont utiles : Delay = « fenêtre de réaction » pour des actions hors enveloppe déjà décidées par des humains ; notre flux = « demande d'accord » pour une intention de l'agent. Noter : non testé sur Base Sepolia par l'équipe (W2C §c.1), à intégrer en phase 2.

**Option C — Bot d'ops + app d'approbation (notifications push, approbation hors canal).**
Mécanique : une alerte structurée est livrée à un canal d'équipe (Telegram/Slack/e-mail), l'approbation se fait dans une **app ou console authentifiée**. Preuves réelles : Tenderly livre ses alertes vers **email, Slack, Telegram, Discord, Sentry, PagerDuty** ou un webhook (docs.tenderly.co « Alert Destinations », consulté 2026-10-15 — FAIT SOURCÉ) ; Fireblocks : notifications d'approbation **dans l'app mobile**, fenêtre d'autorisation configurable **5 min – 24 h (défaut 2 h)**, demandes de **changement de politique expirant à 7 jours**, modèle « premier match » avec action `Approved by` (approbateurs humains) et règle finale block-all (support.fireblocks.io, consulté 2026-10-15 — FAIT SOURCÉ). Caveat de sécurité : les canaux de chat sont un vecteur de phishing connu (ex. drain de multisig via une session WalletConnect proposée par un faux « MEV bot » Telegram, incident 2024 documenté par onchainattack.org — source secondaire, non vérifiée dans le détail).
Pour ORVYREN : excellent **canal de notification** et modèle de SLA ; à ne pas transformer en autorité. « Non trouvé » : un bot Telegram **officiel** Safe/Gnosis Guild pour approuver une transaction (voir §b.6).

**Option D — Lien signé / approbation par signature EIP-712 hors chaîne.**
Mécanique : la demande d'approbation est un objet signé (hash canonique + version + expiration) ; l'approbateur la signe (EIP-712) avec **son** portefeuille — c'est la primitive réelle déjà utilisée par l'écosystème : Safe fait signer le `safeTxHash` et collecte les signatures hors chaîne via son API (Option A, même primitive) ; Snapshot fait signer des messages pour des votes hors chaîne (site snapshot.org — source secondaire, non détaillée ici). Aucune spécification normalisée de « lien d'approbation de trésorerie » n'a été trouvée (« non trouvé ») ; ce qui est standard, c'est **la signature EIP-712 d'un hash de contenu** et sa vérification.
Pour ORVYREN : c'est la brique minimale qui rend une approbation **cryptographiquement attribuable** sans nouvelle infrastructure ; le « lien » n'est qu'un porteur (page locale en démo, e-mail/Slack plus tard) et le lien **ne remplace pas** la vérification de la signature.

### b.3 Tableau comparatif

| Critère | A · File Safe native | B · Zodiac Delay (timelock) | C · Bot d'ops + app | D · Lien signé EIP-712 |
|---|---|---|---|---|
| Nature | Approbation multisig (n-of-m) | Veto/fenêtre de réaction on-chain | Notification + approbation authentifiée | Signature hors chaîne attribuable |
| Ce qui est prouvé au tiers | Signatures des owners + tx on-chain | Événements on-chain (`TransactionAdded`, exécution/annulation) | Rien on-chain ; dépend du journal de l'app | Signature EIP-712 vérifiable contre le hash |
| Latence typique | Minutes (coordination) | Cooldown 1-7 j (recommandé) + coordination | Secondes-minutes (notification) | Secondes-minutes |
| Coût d'introduction | Élevé en démo (Safe 2/3 + UI) ; nul en prod (déjà là) | Moyen (module + tests) ; non testé Base Sepolia | Faible (webhook + bot) | Faible (hash + endpoint) |
| Force | Standard de la cible ; « Approve and Execute » ; ordre des nonces | Opposable on-chain ; annulation par le owner ; aucune confiance dans notre logiciel | SLA chiffrés (Fireblocks) ; joignable 24/7 | Minimal, journalisable, composable avec A/B |
| Faiblesse | Pas de contexte (dossier à côté) ; lourde en démo solo | Veto, pas accord ; `expiration=0` piégeux ; module en plus (surface d'attaque) | Le canal est falsifiable (phishing) ; pas d'audit on-chain | Discipline de vérification ; un lien seul n'authentifie rien |
| Sources | Safe Docs ; Coinshift | docs.zodiac.eco (guide/reference) | Tenderly ; Fireblocks | Safe Docs (EIP-712 `safeTxHash`) |

### b.4 Recommandation — flux v1-démo (PROPOSITION détaillée)

**« La file d'approbation ORVYREN : un canal notifie, une signature autorise. »**

1. **Création** : un verdict `REQUIRE_APPROVAL` (ex. I3 `change_policy`, ou un `transfer` hors plafond après revue B3) crée un enregistrement `approval` : `approval_id`, `intent_id`, `intent_hash`, `decision_id`, `policy_version` + `policy_hash`, `requested_at`, `expires_at` (**défaut 2 h, configurable 5 min-24 h — calé sur le précédent Fireblocks ; changements de politique : 7 jours**, même précédent), dossier de décision joint (hash), résumé lisible.
2. **Notification** : entrée de journal + affichage dans la page d'audit ; optionnellement webhook/bot (Slack/Telegram) via un canal de type « alert destination » (précédent Tenderly). La notification contient **le hash et le lien vers le dossier**, jamais des instructions d'exécution.
3. **Décision humaine** : l'approbateur signe, avec **son propre portefeuille**, un message EIP-712 `Approval(approval_id, intent_hash, policy_version, expires_at)` ; un refus est une action UI journalisée (`REJECTED`) — pour la démo, une signature de rejet optionnelle.
4. **Vérification** : le service de politique (jamais le LLM) vérifie la signature, l'identité (allowlist d'approbateurs), la non-expiration et le non-rejeu (`approval_id` unique) ; le verdict humain est attaché à l'intent (`authorization_verdict` passe de REQUIRE_APPROVAL à APPROVED/REJECTED dans le dossier).
5. **Suite** : si l'action reste **dans l'enveloppe** (cas B3 « dossier prêt à signer »), l'instruction **non signée** est remise à l'humain qui exécute dans son wallet (montage v1 actuel : `guard.py`, « unsigned instruction + human execution ») ; si elle en sort, on prépare une transaction Safe à **proposer** (Option A) — et en phase 2 c'est le **Delay** (Option B) qui portera la classe T3 on-chain.
6. **Clôture** : entrées de journal `APPROVAL_REQUESTED` / `APPROVED` / `REJECTED` / `EXPIRED` + la signature ; le dossier de décision (1 page, SHA-256) gagne la ligne « approbation ».

En démo : I3 (`change_policy`) montre le flux complet *sans exécution* (conforme V0.2 §10.3 : « la démo peut montrer le blocage sans l'exécuter »), + un cas « T3 approuvé puis exécuté par l'humain » si le temps le permet. Le run D (kill switch) de W2C §g.5 reste inchangé.

### b.5 Direction produit (au-delà de la démo)

- **File multi-rôles** : initiateur ≠ approbateur ≠ exécutant (séparation des tâches ; précédent Fireblocks « Approval groups » + politique premier-match avec `Approved by`) ; quorum configurable par classe d'action (T3 standard : 1 approbateur ; changement de politique/enveloppe : comité + DAO).
- **SLA** : expiration par défaut 2 h (5 min-24 h) pour les actions ; 7 jours pour les changements de politique (précédents Fireblocks) ; escalade si proche de l'échéance ; une approbation expirée ne s'exécute jamais.
- **Canal** : notification bot (Slack pour les desks, Telegram pour les petites équipes DAO), lien profond vers le dossier ; **jamais** d'approbation dans le canal lui-même.
- **Côté chaîne** : T3 hors enveloppe → Safe queue (approbation multisig) puis, pour les actions récurrentes bornées, **Delay** avec cooldown 1-7 j ; T4 (pause/revoke) reste au DAO (clé DAO uniquement).
- **Conformité direction** : « logging cardholders'/owners' approvals » est nommé comme composant attendu des specs agentiques (Waller/BIS 2026) — notre journal d'approbations chaîné est exactement cet objet.

### b.6 Données journalisées pour une approbation (à geler)

`approval_id` (ULID) · `intent_id` · `intent_hash` · `decision_id` · `policy_version` · `policy_hash` · `verdict` + `reasons[]` d'origine · hash du dossier · `requested_at` · `expires_at` · canal(x) de notification · approbateur (adresse + rôle) · signature EIP-712 (ou référence) · décision `APPROVED|REJECTED|EXPIRED` · horodatage de la décision · conséquence (`tx_hash` ou « aucune exécution », motif) · `prev_hash` (chaîne du journal). Règle : **une approbation est un enregistrement immuable** ; une correction crée une nouvelle entrée.

### b.7 « Non trouvé » (à ne pas inventer)

- Aucun **bot Telegram officiel** de Safe/Gnosis Guild pour approuver une transaction multisig n'a été trouvé (les résultats sont des blogs promotionnels ou des bots tiers non documentés) — la notification d'ops documentée passe par des fournisseurs (Tenderly) et l'approbation par des apps (Fireblocks, Coinshift, Safe{Wallet}).
- Aucune **norme** « lien signé d'approbation de trésorerie » n'a été trouvée ; la primitive standard est la signature EIP-712 d'un hash.
- Aucun **SLA contractuel** de kill switch (déjà noté W2C annexe 2) — les délais proposés §e sont des cibles internes, pas un engagement.

---

## (c) Formalisation & versionnage de la politique

### c.1 Qui fait autorité

**PROPOSITION (recommandation ferme)** : la politique se formalise en **bundle à quatre pièces**, et l'autorité est répartie :

| Pièce | Contenu | Autorité |
|---|---|---|
| `policy/policy_v1.yaml` (à créer) | **paramètres** : chaînes, actifs, destinataires, plafonds (tx, 24 h), TTL d'intent, plancher/plafond d'exposition, TTL d'approbation, liste d'approbateurs, version | Source de vérité des **paramètres** |
| `src/orvyren/policy/__init__.py` | **sémantique** des règles (l'ordre, les codes, les vérifications) | Source de vérité de la **sémantique** |
| `tests/test_policy.py` + banc de sûreté | preuves exécutables (nominal + attaques + cas limites) | La **preuve** — aucun changement sans test |
| Ce document + `raw_b4/` | description, justifications, sources | La **description** (jamais l'autorité) |

Le code reste la source de vérité (il est ce qui s'exécute), mais la phrase exacte à écrire dans le dossier technique est : « *la politique appliquée est identifiée par une version et un hash ; le texte ne peut pas diverger silencieusement du code parce que c'est le code qui émet le verdict et le hash qui identifie le bundle* ». L'enveloppe on-chain votée par la DAO est la **borne supérieure** : la politique hors chaîne doit être ≤ l'enveloppe (P12).

### c.2 Version et hash dans chaque verdict

- **`policy_version`** : `vMAJOR.MINOR` — **MAJOR** = changement de sémantique ou du set de règles (ajout/suppression, changement d'un verdict, nouvel ordre) ; **MINOR** = changement de paramètre (plafond, destinataire, TTL). Exemple : `v1.0` initiale ; `v1.1` plafond 100 → 150.
- **`policy_hash`** : `sha256( JSON canonique(policy_v1.yaml) ⊕ sha256(code du module policy) )` — identifie les **octets exacts** ; c'est lui qui est recopié dans le journal et le dossier (le versioning lisible sert aux humains, le hash aux machines).
- **Portée** : chaque `PolicyDecision` (§f) et chaque entrée de journal de politique portent `policy_version` + `policy_hash` ; le dossier de décision (1 page) les cite ; l'exigence INV-AUTH de la revue croisée (« rejeu, redémarrage, expiration ne recréent pas de budget ; politique et intention exactes liées au reçu ») est ainsi outillée.
- Le montage W2C le prévoyait déjà : l'exemple d'entrée de journal porte `"policy":{"verdict":"ALLOW","rules":[{"id":"cap_tx_100","ok":true}],"policy_version":"v1.3"}` (W2C §d.5) — on ajoute le hash.

### c.3 Procédure de changement de règle (6 étapes)

1. **Proposition** : un enregistrement ADR-style (`docs/adr/`) décrit le changement, la règle touchée, l'impact (plafonds, allowlists), les tests modifiés. Rédigeable par un humain ou assisté par LLM — **jamais appliqué par un LLM** (la politique n'est pas accessible en écriture au processus agent).
2. **PR + tests** : `policy_v1.yaml` (et/ou code) + tests nouveaux ; le banc complet doit rester vert (`pytest`, 0 échec — règle projet).
3. **Test de dérive** : si le changement touche une borne couplée à Zodiac (plafonds, allowlists, chaîne), l'ordre est **d'abord l'on-chain, ensuite l'off-chain** : on **réduit** d'abord côté chaîne (sens sûr), on **augmente** d'abord côté politique après vote on-chain. Le rapport de dérive (§d) est joint au PR.
4. **Revue et signature** : deux personnes aujourd'hui (auteur ≠ approbateur) ; cible produit : **comité de risque désigné par la DAO**, vote gouverné pour l'enveloppe on-chain.
5. **Version + registre** : bump `policy_version`, calcul du `policy_hash`, ajout d'une ligne au **registre de versions** (table append-only `policy_release` : version, hash, auteur, date, diff, liens). Jamais de réécriture d'historique.
6. **Déploiement + vérification** : redémarrage du service de politique → entrée `POLICY_RELEASE` au journal → test de dérive au démarrage (SAFE MODE si échec).

**Asymétrie d'urgence** (PROPOSITION) : **réduire** un plafond, retirer un destinataire ou activer la pause sont des changements « sens sûr » que l'astreinte peut appliquer **immédiatement** (journalisés, régularisés sous 24 h par la procédure) ; **toute augmentation** suit les 6 étapes complètes. Cette asymétrie est le pendant hors chaîne des règles onlyOwner côté chaîne.

### c.4 Qui décide

- **Aujourd'hui (concours)** : l'équipe — le fichier de politique est modifié par PR, revu par 2 membres ; le chaud et le froid sont séparés (l'agent tourne avec une politique lue en lecture seule).
- **Cible produit** : la DAO vote l'**enveloppe** (module Zodiac) ; un **comité de risque** qu'elle désigne gère la politique off-chain dans ces bornes ; l'équipe ORVYREN édite le logiciel, pas les mandats.
- **Interdit structurel** : l'agent (et le LLM en général) ne peut ni lire la clé, ni modifier la politique, ni approuver — trois frontières testées (règle de dépendance AV1 §2 pour l'import ; `guard.py` pour l'exécution ; P12/dérive pour la config).

---

## (d) Mapping systématique policy ↔ Zodiac + test de dérive

### d.1 Table de correspondance règle ↔ condition on-chain

Enveloppe de référence (plan de démo W2C §g.1 étape 3, Base Sepolia) : rôle `AGENT` (`0x4147454e54…`), cible USDC de test, fonction scopée `transfer(address,uint256)`, condition param 0 = `Or(EqualTo(B), EqualTo(C))`, condition param 1 = `WithinAllowance(usdc_daily)`, allowance `usdc_daily` (`refill=300e6, maxRefill=300e6, period=86400`), quota `CallWithinAllowance(calls_daily)=10/jour`, **rien d'autre**.

| Règle | Exprimable on-chain ? | Condition / paramètre Zodiac exact | Ce qui reste 1er verrou hors chaîne |
|---|---|---|---|
| P1 chaîne | **partiel** | L'instance du module est par chaîne (module `0xF296…83D5` par avatar ; déploiement propre pour la Safe de démo — W2C §g.0) ; le chainId est implicite | L'épinglage du RPC et le contrôle `eth_chainId` au pré-vol (attaque #6) |
| P2 actif/contrat | **oui** | Cible USDC uniquement (toute autre cible = refus par défaut) | — |
| P3 destinataire | **oui** | Condition sur param 0 : `Or(EqualTo(B), EqualTo(C))` | La politique garde la liste lisible + l'égalité exacte avec la condition (dérive si divergence) |
| P4 fonction scopée | **oui** | `scopeFunction(USDC, transfer(address,uint256))`, operation `CALL` seulement ; `Clearance.Function` (jamais `Clearance.Target`) | La table action→sélecteur (registre) et le refus `DELEGATECALL` |
| P5 plafond/tx | **oui** (à écrire) | Condition sur param 1 (`LessThan`/`WithinAllowance`) + allowance ; **attention** : sans condition explicite sur le montant, un transfert unique jusqu'à `maxRefill` est possible après accumulation | Le plafond texte (100) et le test « décimales » |
| P6 cumul 24 h | **partiel** | `usdc_daily` : `refill=300e6, maxRefill=300e6, period=86400` — plafond **d'accumulation**, rafale de frontière `maxRefill+refill` (W2C §a.2, attaque #2) | **Le compteur glissant strict** (fenêtre glissante) ; dimensionner `maxRefill == refill` |
| P7 exposition/solde | **non** | Les conditions Zodiac ne lisent ni solde global, ni portefeuille, ni intention (« la chaîne ne connaît pas les prix » — W2C §a.7 #4) | Solde, plancher, exposition : 100 % hors chaîne |
| P8 permission/expiration | **non** | `Allowance` n'a **aucun** champ d'expiration (W2C §a.7 #1) | Expiration hors chaîne + **révocation planifiée** ; alternative `period=0` (usage unique) |
| P9 fraîcheur intent | **non** | Aucune sémantique de temps/intention dans les conditions | TTL d'intent 100 % hors chaîne |
| P10 idempotence | **non** | La chaîne **autorise** le rejeu d'une tx encore permise ; amortisseurs : nonce EOA + `CallWithinAllowance` (quota d'appels) | Registre d'intents (`intent_id` + hash), statut RESERVED/COMMITTED |
| P11 pause/kill | **partiel** | `assignRoles(false)` / `disableModule` = l'arrêt on-chain (K1/K2) ; il n'existe pas de « pause » du rôle | Le drapeau K0 (pause de signature), la levée de pause par humain |
| P12 alignement | **n/a** | — | L'objet même du test de dérive (ci-dessous) |
| P13 périmètre d'action | **partiel** | Ce qui n'est pas scopé est refusé par la chaîne (donc `swap` est de facto interdit en v1) ; le « REQUIRE_APPROVAL » lui-même n'existe pas on-chain | La table des classes T2/T3 + le flux d'approbation (§b) ; en v2, la classe T3 on-chain via **Delay** |
| P14 budget | **non** | Aucun équivalent | Budget de décision |

**Synthèse (comptage) :** 4 règles pleinement exprimables (P2, P3, P4, P5 — la dernière avec une condition explicite sur le montant), 4 partiellement (P1, P6, P11, P13), 5 non exprimables (P7, P8, P9, P10, P14), et P12 qui est par nature l'objet du test. C'est exactement la raison d'être du double verrou : **l'enveloppe borne le pire cas, la politique hors chaîne porte le jugement et la précision.**

### d.2 Pourquoi il faut un test de dérive

Les deux couches peuvent diverger silencieusement : un plafond hors chaîne augmenté sans mise à jour on-chain (l'action passera — l'enveloppe est plus permissive que prévu ? non : l'intent serait refusé par la chaîne, dérivant en échecs), ou l'inverse — **le cas dangereux** : une enveloppe on-chain élargie (nouvelle cible, destinataire, allowance augmentée) que la politique hors chaîne ne « voit » pas. W2C insiste : « la portée doit être écrite fonction par fonction » (§a.7 #3) et « la politique est publiée et datée on-chain » (§a.2). Le test de dérive transforme cette promesse en **vérification exécutable**.

### d.3 Spécification du test de dérive (PROPOSITION)

**Nom** : `envelope_drift_check`. **Entrées** : `policy_v1.yaml` (attendue), `envelope.json` (référence : chaîne, adresses, codehash du module, config attendue du rôle) et la config lue on-chain. **Sortie** : `envelope_drift_report.json` (`checks[]` PASS/FAIL/UNKNOWN + valeurs lues + `block_number` + RPC + horodatage) et un code de sortie (0 = conforme, ≠0 = dérive).

Contrôles (v1) :
1. **Chaîne** : `eth_chainId` du RPC épinglé == chaîne attendue (84532 démo / 8453 prod).
2. **Module** : `eth_getCode(module)` non vide ; sha256 du code == codehash épinglé (`bf4438c3197d3ecc…`, 24 409 o — MESURÉ W2C §a.3) → détecte un module réétiqueté/version non suivie.
3. **Membres** : `Roles.roles(AGENT).members(agent) == true` ; aucun autre membre ; (l'agent n'a aucun droit d'administration — testé séparément par la matrice #7).
4. **Cibles** : l'ensemble des cibles du rôle == {USDC} attendu ; toute cible en `Clearance.Target` (portée large) = **dérive critique** (mode d'erreur n° 1, W2C §a.7 #3).
5. **Fonctions** : pour chaque paire (cible, sélecteur) attendue, clearance `Function` + `ExecutionOptions` compatible ; toute fonction non attendue = dérive.
6. **Conditions** : condition destinataire lue == `Or(EqualTo(B), EqualTo(C))` ; condition montant == celle attendue (paramètre 1) ; toute condition absente = dérive (un montant non conditionné peut consommer l'allowance en un coup).
7. **Allowances** : `allowances(AGENT, usdc_daily)` (mapping public confirmé au code : `mapping(bytes32 => Allowance) public allowances`, W2C `_Core.sol`) → `refill == maxRefill == 300e6`, `period == 86400` ; contrainte de cohérence : `policy.max_per_tx ≤ min(refill, maxRefill)` et `policy.max_cumulative_24h ≤ maxRefill`, et `maxRefill == refill` (pour que la rafale de frontière reste ≈ 2 périodes).
8. **Quota d'appels** : `CallWithinAllowance(calls_daily) == policy.max_calls_24h` (10/jour).
9. **Expiration/processus** : la politique hors chaîne a une échéance ≤ la **révocation planifiée** enregistrée (tâche) ; l'absence des deux = dérive (limite connue : pas d'expiry natif).
10. **Version/avis** : version du module suivie vs avis de sécurité connus (post-mortems 2026 : ERC-1271 v2.1.0 → v2.1.1, padding MultiSend — W2C §a.6) ; codehash pinné = garde.

**Lecture d'état** : getters du module et/ou **subgraph officiel** (`gnosisguild.squids.live/roles:production`, W2C §a.4) et **app de diff** (`roles.gnosisguild.org/.../diff/...`) pour l'inspection humaine. Les noms exacts de tous les getters (cibles/conditions) sont **à confirmer sur le contrat déployé** au moment de l'implémentation — les extraits de code du dossier confirment `allowances(...)` public et `Roles.roles(AGENT).members(agent)` (utilisé dans le plan de démo), pas l'intégralité des accesseurs.

**Régime** : « 3 états » — PASS (exécution autonome permise), DRIFT (SAFE MODE : refus de tout autonome + alerte + journal `ENVELOPE_DRIFT`), UNVERIFIED (RPC injoignable/incohérent : SAFE MODE `ENVELOPE_UNVERIFIED`). Le mode sûr est un **état de la politique**, pas une exception du logiciel : il se prouve dans le journal.

### d.4 Implémentation (deux étages)

1. **Offline (CI, obligatoire)** : test `tests/test_policy_zodiac_conformance.py` qui compare `policy_v1.yaml` à une **fixture** de config on-chain (`fixtures/roles_agent_config.json`, capturée une fois par script et versionnée) — tourne sans réseau, détecte toute dérive introduite par un changement de l'un des deux côtés. C'est l'étage qui protège les revues de PR.
2. **Live (à l'exécution)** : `scripts/run_drift_check.py` (stdlib, `eth_call` sur `sepolia.base.org`), lancé au démarrage du service, avant chaque fenêtre de démo/exécution et périodiquement (ex. toutes les 15 min) ; écrit `evidence/envelope_drift_report.json`. En production, la même mécanique tourne en tâche de fond ; l'alerte part sur le canal d'ops (§b).

---

## (e) Procédure d'incident / kill switch

### e.1 Qui peut arrêter quoi (leviers, latences)

Dérivé de W2C §d.4 (mécanique mesurée) :

| Niveau | Action | Qui | Latence | Ce que ça arrête |
|---|---|---|---|---|
| K0 | **PAUSE hors chaîne** (drapeau du service de signature) | ORVYREN (astreinte) | immédiat | toute nouvelle signature de l'agent |
| K1 | `assignRoles(agent, [AGENT], [false])` | **Safe DAO** (seuil de signatures) | 1 tx ; Base ≈ 1,64 s/bloc (**MESURÉ** 2026-10-15 : 620 blocs / 1 016 s) ; la latence réelle = coordination humaine (minutes) | toute exécution ultérieure du rôle par l'agent |
| K2 | `disableModule(prev, rolesModule)` | Safe DAO | idem K1 | le module entier (tous ses rôles) |
| K3 | Retrait des ETH de gaz | Safe DAO | idem K1 | la capacité à payer le gaz (« asphyxie ») |

**Qui possède la clé de la DAO en démo** : la Safe 2/3 de démonstration (3 clés de test distinctes côté équipe/utilisateur — W2C §g.1). **En production** : les signataires de la trésorerie. L'agent ne peut jamais déclencher K0-K3 contre lui-même dans le sens permissif : il peut seulement **poser** la pause (sens sûr) ; la **levée** exige un humain.

**Ce que le kill switch ne peut pas faire** (à écrire, W2C §d.4) : annuler une transaction déjà incluse ; battre de vitesse une transaction déjà dans la mempool et séquencée avant la révocation. La protection pratique est : plafonds faibles (le dommage par bloc est borné par l'allowance), délais courts décision→envoi, surveillance des intentions.

### e.2 Runbook (détection → clôture), avec délais cibles

| Étape | Actions | Acteur | Délai cible (PROPOSITION) |
|---|---|---|---|
| 1. Détection | Surveillance : événements `AssignRoles`/`ConsumeAllowance`/`Transfer` + anomalies (destinataire nouveau, montant inhabituel, rafale, exécution hors profil — W2C annexe 3) ; alerte sur le canal d'ops | Automate + astreinte | ≤ 15 min (cadence de surveillance 1-15 min) |
| 2. Qualification | Attribuer la sévérité : **S1** clé compromise / exécution non conforme ; **S2** dérive d'enveloppe ou d'instrument (codehash, allowance) ; **S3** avis de sécurité amont (Zodiac/Gnosis) ; **S4** dégradation (RPC, dépendance) | Astreinte | ≤ 15 min |
| 3. Confinement | **S1/S2 ⇒ K0 immédiat** (pause) ; demander K1 en parallèle à la DAO ; vérifier le pré-vol (`AGENT_NOT_MEMBER`) | ORVYREN ; DAO pour K1 | K0 ≤ 5 min après qualification ; **K1 ≤ 60 min** (coordination — le seul délai non compressible) |
| 4. Vérification | `Roles.roles(AGENT).members(agent) == false` ; aucun `Transfer` non conforme ; soldes ; allowance restante ; lister les intents en vol | Astreinte | ≤ 15 min après K1 |
| 5. Communication | Interne : canal d'ops + responsables. Externe (si fonds DAO) : message factuel au forum/gouvernance — quoi s'est passé, ce qui est arrêté, exposition maximale possible (chiffre : le pire cas on-chain est borné par l'allowance), prochaine mise à jour | Responsable désigné | interne ≤ 30 min ; externe ≤ 4 h (cible) |
| 6. Journal | Consigner : chronologie, hashes de transactions, entrées du journal chaîné, décisions, acteurs, valeurs lues on-chain (bloc) — **append-only**, jamais réécrit | Astreinte | en continu |
| 7. Post-mortem | Cause racine, portée exacte, correctifs (politique, enveloppe, code), tests ajoutés ; décision de redémarrage | Équipe/comité | ≤ 72 h |
| 8. Redémarrage | Conditions : cause comprise ; correctifs fusionnés (procédure §c.3) ; **test de dérive PASS** ; DAO ré-assigne le rôle ; plafonds réduits pour la première période ; entrées `POLICY_RELEASE` + `RESTART` au journal | Équipe + DAO | selon revue |

Note d'honnêteté (W2C §d.4) : « le seul délai non compressible est humain ». Aucun SLA contractuel n'existe (« non trouvé », W2C annexe 2) — les délais ci-dessus sont des cibles internes.

### e.3 Communication — principes (PROPOSITION)

- **Dire d'abord le pire cas chiffré** (« l'exposition maximale on-chain était bornée à X USDC vers les destinataires Y », ou « inconnue, voici ce qu'on sait ») — jamais de « tout va bien » non prouvé.
- **Ne jamais promettre l'impossible** : ne pas annoncer l'annulation d'une transaction incluse (impossible), ne pas promettre une garantie que l'amont ne donne pas (« WITHOUT ANY WARRANTY » — W2C §a.1).
- Un canal par audience : ops (temps réel), gouvernance (factuel, horodaté), public (si nécessaire).
- Après l'incident : publier le correctif et sa preuve (rapport de dérive, tests) — c'est le même standard que les post-mortems Zodiac (W2C §a.6).

### e.4 Veille (à intégrer au runbook)

- Suivre les communiqués Zodiac/Gnosis Guild (`@zodiaceco`, `engineering.gnosisguild.org` — W2C annexe 3) ; **vérifier la version du module avant chaque période d'exécution** (le test de dérive le fait : contrôle 2 et 10) ; migrer si l'app Roles signale une version vulnérable.
- Surveiller `AssignRoles`, `SetDefaultRole`, `ConsumeAllowance` (W2C annexe 3).
- La télémétrie est **notre apport** (W2C §a.7 #7 : « le module exécute, il n'alerte pas » ; OZ Defender éteint au 1er juillet 2026 — U2).

---

## (f) Schéma final du `PolicyDecision` et interfaces

### f.1 L'existant (à conserver)

```python
@dataclass
class PolicyDecision:
    verdict: str            # ALLOW | DENY | REQUIRE_APPROVAL
    reasons: list           # codes de refus (stables)
    rules_evaluated: list   # [{"rule": "R1-chain", "result": "OK|FAIL|SKIPPED", "code": ..., "note": ...}]
    def as_dict(self): ...
```

MESURÉ : ce format est déjà produit dans `evidence/policy_execution_demo.json` (verdict, deny_codes, rules_evaluated par cas I1/I2/I3) et consommé par le dossier d'audit. **Il ne faut pas le casser** : le schéma v1 **étend** (champs additifs) et fige le sérialiseur canonique.

### f.2 Schéma v1 proposé (champs additifs, PROPOSITION)

| Champ | Type | Rôle | Statut |
|---|---|---|---|
| `decision_id` | ULID | identifiant du verdict (append-only) | nouveau |
| `intent_id` · `intent_hash` | str · hex | lien vers l'intent ; `intent_hash` = keccak/sha256 du contenu canonique (celui du registre d'idempotence) | nouveau |
| `verdict` | enum {ALLOW, DENY, REQUIRE_APPROVAL} | le verdict (INV : seule sortie d'autorisation) | existant |
| `reasons` | [code] | codes en échec (ordre canonique) | existant |
| `rules_evaluated` | [{rule, result, code?, note?}] | trace complète, y compris `SKIPPED` | existant |
| `policy_version` | str (vMAJOR.MINOR) | version lisible | nouveau |
| `policy_hash` | hex | octets exacts du bundle (§c.2) | nouveau |
| `envelope_ref` | {chain_id, module, role_key, codehash, checked_at, drift} | lien vers l'enveloppe on-chain et l'état du test de dérive | nouveau |
| `approval` | null ou {approval_id, required, channel, expires_at, state} | présent si REQUIRE_APPROVAL | nouveau |
| `context_used` | {now, cumulative_24h, balance, exposure, pause, sources[]} | valeurs lues pour décider (+ source de chaque lecture) | nouveau |
| `evaluator` | str | « orvyren-policy v0.1 (déterministe) » — jamais un LLM | nouveau |
| `created_at` / `decided_at` | RFC 3339 UTC | horodatage | nouveau |

Exemple :

```json
{
  "decision_id": "01J...", "intent_id": "I1", "intent_hash": "0x9f...",
  "verdict": "ALLOW", "reasons": [],
  "rules_evaluated": [
    {"rule": "P1-chain", "result": "OK", "note": "84532"},
    {"rule": "P5-amount", "result": "OK", "note": "100.0 <= 100.0"},
    {"rule": "P6-cumulative", "result": "OK", "note": "150.0 <= 300.0"}
  ],
  "policy_version": "v1.0", "policy_hash": "sha256:ab...",
  "envelope_ref": {"chain_id": 84532, "module": "0xF296...83D5", "role_key": "AGENT",
                   "codehash": "bf4438c3197d3ecc...", "checked_at": "2026-10-15T12:00:00Z", "drift": "PASS"},
  "approval": null,
  "context_used": {"now": "2026-10-15T12:00:01Z", "cumulative_24h": 150.0, "balance": 480.0,
                   "exposure": 0.42, "pause": false, "sources": ["portfolio_snapshot#..."]},
  "evaluator": "orvyren-policy v0.1 (déterministe)",
  "created_at": "2026-10-15T12:00:01Z", "decided_at": "2026-10-15T12:00:01Z"
}
```

Règles de forme : sérialisation **canonique** (JSON trié, nombres en unités décimales avec leur actif) ; `as_dict()` conservé avec ses trois clés historiques (compatibilité) ; le hash du verdict est calculé sur la forme canonique et chaîné dans le journal.

### f.3 Interfaces (B3 ↔ policy ↔ B5), rappel et delta

- **B3 → policy** (AV1 §3) : `Intent{action, chaîne, actif, montant, destinataire, intent_id}` + (v1) `created_at`, `expiration`, `justification`, `decision_ref` (dossier B3), `x*` et bornes de B3 §d. La politique reçoit aussi `PolicyConfig` (params §c) et l'état local (compteur, solde/portefeuille, pause, dérive). Sortie : `PolicyDecision`.
- **Le lien avec les 3 axes de B3** (R6 de B3) : `epistemic_verdict` (CONCLUANT/INCONCLUSIVE) et `economic_action` (catalogue §d) sont **calculés avant** ; `authorization_verdict` **est** `PolicyDecision.verdict`. `REQUIRE_APPROVAL ⇒ ESCALATE` (B3 §c.4, §e.2 étape 8) : c'est le raccord exact du flux §b.
- **policy → B5 (exécution)** : seul un verdict `ALLOW` est acceptable ; `guard.py` lève `PolicyViolationError` sinon (déjà en place, message spécifique pour REQUIRE_APPROVAL). Le pré-vol (`eth_call`, `chainId`) précède la signature ; le journal B5 (W2C §d.5) porte l'entrée `POLICY` avec `verdict`, `rules`, `policy_version` (+ `policy_hash` v1) ; l'entrée `APPROVAL` s'intercale pour T3 ; le dossier d'audit (AV1 §4 `policy_decision`) cite la décision.
- **Base de données** : tables `intent`, `policy_decision`, `execution` (AV1 §4) + nouvelles tables proposées `approval` et `policy_release` (append-only, `provenance_refs[]`).

---

## (g) Questions ouvertes (à trancher en revue d'équipe)

1. **Canal du flux d'approbation en démo** : page d'audit seule (recommandé pour la démo) ou bot Slack/Telegram en plus (effet vitrine) ? La recommandation §b tient dans les deux cas.
2. **Valeurs initiales des paramètres v1** : TTL d'intent (15 min proposé), exposition maximale (part de trésorerie ? montant ?), plancher de solde (DAO : semaines de runway ? desk : marge ?), `max_calls_24h` (10 proposé, aligné W2C), TTL d'approbation (2 h proposé ; 7 j pour changements de politique).
3. **Approbateurs** : qui signe en démo (1 clé équipe ? 2 ?) et en produit (rôles, quorum, séparation initiateur/approbateur) ?
4. **Delay modifier en v1 ou v2** : l'intégrer à la démo durcit la preuve on-chain du T3 mais n'est **pas testé** sur Base Sepolia (W2C §c.1) → PROPOSITION : v2, documenté.
5. **Réduction d'urgence des plafonds** : qui peut la faire (astreinte ? 2 signatures ?) et fenêtre de régularisation.
6. **Ancrage du `policy_hash`** : EAS (reporté V0.2 §10.6 / carte §6.3) ou inscription dans l'événement de gouvernance Zodiac ? À confirmer avant le dossier final.
7. **Propriétaire du test de dérive** : cadence, qui est alerté, où vit le rapport (`evidence/`), et version de la fixture.
8. **Seuils de sévérité d'incident** (S1-S4) : validation par l'équipe ; qui est « l'astreinte » en démo (toi).
9. **Extension du registre d'actions** (quand `swap` entre dans l'enveloppe : cibles, fonctions, conditions slippage — dépend de B3/W2-C v2).
10. **Réconciliation W2C §d.3** : le compteur glissant « par actif et par destinataire » — v1 mono-actif mono-destinataire : garder l'option par destinataire ou la garder hors scope ?

---

## Sources (URL + dates de consultation)

**Web (consultées le 2026-10-15, sauf mention)** :
1. Safe Docs — Transactions with off-chain signatures : https://docs.safe.global/core-api/transaction-service-guides/transactions
2. Safe Docs — Propose and confirm transactions : https://docs.safe.global/sdk/api-kit/guides/propose-and-confirm-transactions
3. Safe Docs — Safe Transaction Service API (overview) : https://docs.safe.global/core-api/transaction-service-overview
4. Safe Docs — Safe Guards : https://docs.safe.global/safe-smart-account/guards *(page mise à jour 27 août 2026)*
5. Zodiac Docs — Delay guide : https://docs.zodiac.eco/developers/delay/guide
6. Zodiac Docs — Delay reference : https://docs.zodiac.eco/developers/delay/reference
7. Coinshift Docs — Queue : https://docs.coinshift.xyz/business/coinshift-walkthrough/transaction-management/queue
8. Fireblocks — How Policies work : https://support.fireblocks.io/hc/en-us/articles/29210922951580-How-Policies-work
9. Fireblocks — Approval and signing notification expiration : https://support.fireblocks.io/hc/en-us/articles/360015963760
10. Fireblocks — Approval groups : https://support.fireblocks.io/hc/en-us/articles/29184265622556-Approval-groups
11. Tenderly Docs — Alert Destinations : https://docs.tenderly.co/monitoring/alerts/destinations/overview
12. BIS — « Payments in the age of AI agents », C. Waller, 2026-10-05 : https://www.bis.org/speeches/20261005-payments-age-ai-agents (discours du 29 septembre 2026, Sibos Miami)
13. Federal Reserve — même discours : https://www.federalreserve.gov/newsevents/speech/waller20260928a.htm
14. Llama (contexte) — https://github.com/llamaxyz/llama
15. (Rejeté comme preuve) blogs « Telegram approvals » promotionnels ; onchainattack.org (incident WalletConnect « fake MEV-bot », 2024) — contexte qualitatif seulement.

**Interne (D:\orvyren_core)** : `research/SYSTEME_ZONES_OMBRE.md` §4 · `research/W2C_enveloppe_execution.md` (a.2-a.7, c.1-c.3, d.1-d.5, e, f, g.0-g.8, annexes) · `research/B3_DECISION_ETUDE.md` (§c.4, §d, §e, §h) · `ARCHITECTURE_V1.md` (§2-4) · V0.2 §10.1-10.4 (`C:\Users\User\fintechathon_recherche\orvyren_v02\`) · `src/orvyren/policy/__init__.py`, `tests/test_policy.py`, `src/orvyren/execution/{guard,intents}.py`, `src/orvyren/audit/dossier.py` · `FREEZE_V1.md` D9/D10 · `research/REVUE_CROISEE_ET_CADRE_CONCRET.md` (INV-AUTH) · `evidence/policy_execution_demo.json` · `research/U2_defi_organisations.md` (Defender sunset 01/07/2026) · raw : `research/raw_b4/`.

## Annexe — « non trouvé » (à ne pas combler par des inventions)

1. Bot Telegram **officiel** d'approbation Safe/Gnosis Guild — non trouvé (§b.7).
2. Norme « lien signé » d'approbation de trésorerie — non trouvée ; la primitive standard est la signature EIP-712 d'un hash.
3. SLA contractuel de kill switch — non trouvé (déjà W2C annexe 2).
4. Fichier `abi.ts` du module (tentative de lecture brute dans les archives W2C) : 404 — les noms exacts de tous les getters de cible/condition restent « à confirmer sur le contrat déployé » (§d.3).
5. Coût d'un audit de politique tiers (ThirdGuard) — non trouvé (W2C annexe 2).
6. Valeur « standard » du TTL d'intent (fraîcheur) — aucune source normative trouvée ; la proposition (15 min) est un choix d'ingénierie fondé sur W2C (« délais courts entre décision et envoi »), pas un standard.
