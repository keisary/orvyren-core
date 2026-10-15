# B5 — ÉTUDE DU BLOC EXÉCUTION (carte des zones d'ombre, §5)

**Projet ORVYREN** — agent wallet on-chain autonome borné (concours FinTech Shenzhen 2026, thème F).
**Rédigé le 2026-10-15 (UTC).** Chantier B5 (consolidation du bloc « EXÉCUTION », statut **DIRECTION** dans
`research/SYSTEME_ZONES_OMBRE.md` §5).
**Méthode** : partie de `research/W2C_enveloppe_execution.md` (en entier) + V0.2 §10 + le code existant
(`src/orvyren/execution/`, `tests/test_execution.py`) ; **faits nouveaux mesurés par RPC Base Sepolia**
(`https://sepolia.base.org`, `eth_chainId`, `eth_getCode`, `eth_call`) le **2026-10-15**, matière brute et
reproductible dans `research/raw_b5/` (scripts + sorties + décodage Python). Défauts de source : tout ce qui
n'est pas vérifiable est marqué **« non trouvé »** ; les jugements sont marqués **PROPOSITION**.

Étiquettes : **FAIT SOURCÉ** (source externe, URL + date) · **MESURÉ** (notre mesure RPC du 2026-10-15, avec
bloc) · **FAIT INTERNE** (code/dépôt, fichier cité) · **PROPOSITION** (choix à valider) · **OUVERT**.

**Ce que ce document tranche** (5 points ouverts de la carte §5) :
1. **Signer v1-démo** : spécification complète de la clé jetable d'équipe (+ direction produit argumentée) ;
2. **Catalogue d'intents v1** : schéma final aligné V0.2 §10.2 et **faisabilité testnet vérifiée** pour
   1–2 actions supplémentaires (swap Uniswap v3, Aave) ;
3. **Préflight & envoi** : checklist de simulation/vérifications, retries bornés, confirmations, reorgs ;
4. **Vérification du receipt** : champs exacts, correspondance intent↔logs, échec de première classe, audit ;
5. **Plan des 5 runs de démo mis à jour** (W2C §g) avec critères de succès mesurables, scripts et dépendances.

---

## 0. Résumé exécutif (15 lignes)

1. **Le signer de la démo est une EOA jetable, membre du rôle `AGENT`, dont la clé ne vit que dans une variable
   d'environnement du service de signature** — jamais dans le dépôt, les logs, les prompts ni les captures ;
   elle est générée localement, financée par robinet, détruite à la fin de la démo (spec §a.1).
2. **Direction produit : garder la structure à double verrou et rendre le backend de clé remplaçable.** En
   démo : EOA + env var. En production : clé non exportable dans un HSM/TEE (AWS KMS, Turnkey, CDP) ou
   signature MPC ; les passkeys (RIP-7212 sur Base) servent le niveau humain (T3). Le différenciant ORVYREN
   n'est pas le backend de clés — c'est le premier verrou (politique déterministe) + le journal (§a.2).
3. **Catalogue d'intents v1 : schéma final défini** (§b.1) : `chain_id, account, action, asset, amount
   (décimal → base units), recipient, function, params, expiry, idempotency_key` + champs d'audit. Le champ
   `amount` en **chaîne décimale**, pas en flottant (correction à porter au code, qui utilise `float`).
4. **Faisabilité testnet vérifiée par RPC le 2026-10-15** (§b.2) : Uniswap v3 (routeur, fabrique, quoter,
   routes internes) **déployés** sur Base Sepolia, pools USDC/WETH **liquides avec quotes en direct** ;
   Aave v3 (Pool, réserve USDC active non gelée, aToken/vDebtToken) **déployé**. **Sélecteurs vérifiés** par
   keccak local + bytecode + appels réels — trois hypothèses amont corrigées (§b.2.d, annexe E).
5. **Découverte opérationnelle : il y a DEUX USDC sur Base Sepolia** — le USDC du robinet Circle
   (`0x036CbD…CF7e`, utilisé par le pool Uniswap) et le USDC d'Aave (`0xba50Cd2A…4d5f`, réserve de
   lending). **Ils ne sont pas interchangeables** ; le plan de démo doit nommer lequel sert à quoi (§b.2).
6. **Les prix du testnet ne sont pas des données de marché** (confirmé par mesure : deux étages de frais du
   même couple cotent 4 674 et 2 479 USDC/WETH au même instant ; le pool Aave cote un prix absurde). La démo
   prouve le **chemin d'exécution**, jamais l'économie (§b.2, §e).
7. **Classement des actions** : `transfer` ERC-20 = **implémenté v1** (politique + calldata + vérification de
   receipt déjà codés, hors ligne) ; `swap` et `approve` = **préparés/simulés en v1**, exécution en v2 ;
   Aave `supply/withdraw/repay` = **v2** (repay exige une dette — montage multi-étapes).
8. **Préflight (§c)** : 12 vérifications avant signature (config, verdict, idempotence, nonce, gaz, soldes,
   simulation `eth_call`, estimation) ; **aucune signature si la simulation revert**.
9. **Confirmations** : la démo attend **2 blocs** après le receipt ; la production utilise les tags
   `safe` puis `finalized` — **vérifié** : `sepolia.base.org` sert `eth_getBlockByNumber("safe")` et
   `("finalized")` (2026-10-15). Base : ~1,64 s/bloc mesuré par W2C (sur Base **mainnet**).
10. **Reorgs (§c.4)** : politique minimale écrite — relire le receipt à profondeur, détecter la disparition
   ou le changement de `blockHash`, re-simuler et re-vérifier la politique avant toute re-soumission ;
    jamais de double exécution (registre d'idempotence + contrôle des soldes/logs).
11. **Vérification du receipt (§d)** : champs exacts + codes de mismatch déjà codés (`NO_TRANSFER_LOG`,
    `TOKEN_CONTRACT_MISMATCH`, `SENDER_MISMATCH`, `RECIPIENT_MISMATCH`, `AMOUNT_MISMATCH`,
    `TRANSACTION_FAILED`, `CHAIN_ID_*`) ; ajouts v1 : unicité du log Transfer (`LOG_COUNT_AMBIGUOUS`),
    contrat du module dans les logs, lecture d'allowance (« WARN » si non vérifiable).
12. **Un échec est un résultat de première classe** (§d.4) : un `status = 0x0` est journalisé, son revert
    (sélecteur) capturé par rejeu `eth_call`, son coût en gaz enregistré — jamais masqué (exigence
    V0.2 §12.4).
13. **Plan des 5 runs mis à jour** (§e) : chaque run a des **critères de succès mesurables** (statuts,
    deltas de soldes, compteur de signatures, correspondance journal/chaîne) + la liste des **13 scripts**
    à produire + dépendances (wallet, robinets) + **protocole de re-vérification des adresses** avant
    exécution.
14. **Rien ici ne modifie le statut juridique ni les limites amont** : les limites de W2C §a.7 (pas
    d'expiration native, rafale de frontière de période, pas de télémétrie incluse, contrats sans garantie)
    restent valides et doivent figurer au dossier concours.
15. **Reste ouvert** (§f) : bibliothèque de signature (hors stdlib), montant des runs (50 vs 100 USDC),
    spec de l'`approve` borné, qui détient les clés du Safe de démo, profondeur de confirmation retenue.

---

## (a) SIGNER v1-DÉMO ET DIRECTION PRODUIT (question 5.1)

### a.1 Spécification du signer de démonstration (v1-démo)

**Objet** : une EOA dédiée, **membre du rôle Zodiac `AGENT`** d'une Safe de démonstration, qui paie son
propre gaz et n'a **aucun** droit d'administration. C'est le montage déjà retenu par W2C §d.2 (FAIT SOURCÉ :
post-mortem Gnosis Guild, 19 juin 2026, qui distingue les membres EOA ; `ModuleManager.sol` v1.4.1
`enableModule` sans contrôle `isContract`).

| # | Exigence | Règle exacte |
|---|---|---|
| S1 | **Génération** | Clé générée localement sur le poste (`secrets.token_bytes(32)` → clé secp256k1), **jamais** dérivée d'une phrase mnémonique réutilisée, **jamais** copiée dans un chat. |
| S2 | **Stockage** | Uniquement en **variable d'environnement du processus de signature** (`ORVYREN_PRIVATE_KEY`, nom déjà reconnu comme sensible par `guard.py` → FAIT INTERNE). Fichier `.env` local **non versionné** (`.gitignore`), permissions restreintes. |
| S3 | **Interdits absolus** | Jamais dans : le dépôt (aucun commit), un prompt LLM, un log, un message d'erreur, une capture d'écran de démo, un ticket, un rapport. Le module `guard.py` ne lit **que les noms** des variables sensibles (`present_secret_env_names`) et masque les URL RPC porteuses de clé (`mask_rpc_url`) — tests existants dans `tests/test_execution.py` (FAIT INTERNE). |
| S4 | **Portée** | Membre du rôle `AGENT` (`0x4147454e54…`), cibles/fonctions/conditions/allowances fixées par la politique on-chain (W2C §g.1). Zéro droit d'admin : `allowTarget`, `scopeFunction`, `setAllowance`, `assignRoles`, `enableModule` **revert** depuis cette clé (test on-chain prévu, matrice #7). |
| S5 | **Financement gaz** | Robinets Base Sepolia (ETH de test). Budget : les frais mesurés le 2026-10-15 sont de **0,006 gwei** (`eth_gasPrice`) → un transfert ≈ 50 000 gaz ≈ **3 × 10⁻⁷ ETH** ; **0,01 ETH couvre des milliers de transactions de démo** (MESURÉ : `rpc_b5_probe3_output.txt`). Le gaz est une ligne budgétaire **distincte** du plafond métier (W2C §d.3). |
| S6 | **Financement actif** | USDC de test via le robinet Circle (Base Sepolia) vers la **Safe**, pas vers l'agent — l'agent ne détient jamais les fonds. Vérifier le solde de la Safe avant chaque run. |
| S7 | **Isolation du processus** | Le service de signature est un **processus séparé** ; il n'expose qu'une API : `intent autorisé (ALLOW) → tx signée + hash`. Il ne connaît ni le LLM, ni le graphe, ni la politique (il la reçoit déjà tranchée). Invariant I1 de W2C §d.1 : le LLM ne voit jamais de clé. |
| S8 | **Rotation / révocation** | Changer d'agent = **1 transaction de la Safe** : `assignRoles(nouvelle, [AGENT], [true])` + `assignRoles(ancienne, [AGENT], [false])`. En démo, la rotation est **démontrée** (run D) puis la clé jetable est détruite. |
| S9 | **Cycle de vie démo** | Après les 5 runs : retirer le rôle, vérifier `Roles.roles(AGENT).members(agent) == false` par `eth_call`, archiver la sortie **sans la clé**, supprimer le `.env`. Une clé de démo compromise après révocation est sans portée. |
| S10 | **Traçabilité** | Le journal d'audit enregistre l'**adresse** du signer et son **rôle**, jamais la clé. Chaque exécution référence `intent_id` + `policy_version` (W2C §d.5). |

**Bibliothèque de signature — OUVERT (Q1 §f).** Le cœur du dépôt est en **stdlib seul** (convention projet) :
or `hashlib` ne fournit **pas Keccak-256** et la stdlib n'a **pas de secp256k1**. Le service signataire devra
donc soit ajouter une dépendance isolée (`eth-account`, MIT ; ou `coincurve`), soit s'appuyer sur un outil
externe (`cast` de Foundry). **PROPOSITION** : réserver la dépendance au seul processus signataire, la
déclarer dans `LICENSES.md`, et garder `src/orvyren/execution/` pur (lecture seule) tant que la phase de
construction n'est pas ouverte.

**Ce que la clé ne peut PAS faire (à écrire, pas à cacher)** : dépasser `maxRefill` par période, envoyer vers
un destinataire hors liste, appeler une cible non autorisée, modifier la politique ou le module, vider la
Safe. Si la clé fuite, le pire cas est **un nombre connu** : « au plus `maxRefill` par période, uniquement
vers les destinataires autorisés » (W2C §e, attaque #11 ; §f.2.2).

**Évolution par rapport au code actuel (à assumer explicitement).** Le code de démo actuel
(`run_execution_demo.py`) fonctionne en mode « **instruction non signée + exécution humaine** » : l'agent
produit le calldata, un humain exécute dans son wallet, la vérification du receipt est en lecture seule.
Ce mode est solide pour la preuve documentaire, mais il n'est **pas** l'exécution autonome qu'exige le
thème F (« agent wallet / exécution on-chain autonome ») : présenté comme le produit, il échoue à ce critère.
La v1-démo B5 ajoute donc le **service signataire isolé** (S7–S9) qui exécute **dans l'enveloppe on-chain** ;
le mode « instruction humaine » est conservé comme **mode de repli/manuel** (si un robinet ou le module
tombe), jamais comme mode principal de la démonstration.

### a.2 Direction produit : options réelles comparées

Quatre familles de porteurs de clé pour l'agent, avec ce qui est **sourcé** à ce jour :

| Option | Mécanique | Ce qu'elle apporte | Ce qu'elle ne règle pas | Sources (consultées 2026-10-15) |
|---|---|---|---|---|
| **A. EOA chaude + limites on-chain** (choix actuel) | EOA membre de rôle, clé en variable d'environnement ; l'enveloppe Zodiac borne tout | Simple, testable, précédents DAO (ENS×kpatkey, Balancer, GnosisDAO, Scroll) ; aucune dépendance à un éditeur pour l'application de la politique | La clé est en clair **quelque part** (mémoire du processus) ; pas de politique côté porteur de clé | W2C §a/b/d ; `research/W2C_enveloppe_execution.md` |
| **B. KMS** | Clé secp256k1 **non exportable** dans un HSM cloud ; l'agent appelle une API de signature (`Sign`) | La clé ne sort jamais du HSM ; journalisation des appels ; rotation par création de clé + réassignation du rôle | Le KMS ne connaît **pas** la politique métier (pas de plafond par période, pas de liste blanche) → le second verrou on-chain reste **indispensable** | AWS KMS : `KeySpec` accepte `ECC_SECG_P256K1` et « KMS keys with ECC_SECG_P256K1 can be used only to sign and verify messages » — https://docs.aws.amazon.com/kms/latest/APIReference/API_CreateKey.html (FAIT SOURCÉ) |
| **C. Module Safe dédié** | L'agent est un **contrat** module de la Safe (ou un validateur de session ERC-7579 sur un compte 7579) ; pas de clé EOA | Pas de clé à voler ; logique de validation programmable | Change de socle si le client n'est pas en ERC-7579 ; les modules Safe ont les **pleins pouvoirs** du compte par conception (W2C §a.7.5) → surface d'audit ; un Guard cassé peut bloquer la Safe (FAIT SOURCÉ : avertissement Safe cité par Fireblocks, https://fireblocks.com/report/compare-transaction-policy-engine — « a broken Guard can cause a denial of service for a Safe ») | W2C §a.5, §c.1 ; docs.safe.global (via la revue Fireblocks) |
| **D. MPC / TEE / passkeys** | La clé est **partagée** (MPC) ou vit dans un **enclave** (TEE) ; la signature est produite par un service qui applique aussi des règles ; passkeys = WebAuthn (P-256) vérifié on-chain | Pas de clé entière sur un disque ; politiques au niveau du signataire ; passkeys = UX humaine (T3/approbations) | Fournisseur de confiance (enclave du vendor) ; coût et dépendance ; la portée métier fine (par fonction/paramètre) n'y est pas toujours exprimable | Turnkey : « AI agent wallets with policy-scoped signing… Private keys never leave the secure enclave » — https://docs.turnkey.com/solutions/company-wallets/overview (FAIT SOURCÉ). Coinbase CDP : walles serveur en **AWS Nitro Enclaves**, policy engine (allowlists, limites, KYT) — https://docs.cdp.coinbase.com/wallets/security-and-policies/security-overview et https://coinbase.com/developer-platform/discover/launches/cdp-wallets-launch (FAIT SOURCÉ). Fordefi : « the API Signer holds the first of two MPC shares… does not require human intervention to sign a transaction » — https://docs.fordefi.com/developers/getting-started/set-up-an-api-signer (FAIT SOURCÉ). Fireblocks : policy engine dans des enclaves Intel SGX, règles signées par quorum — https://fireblocks.com/report/compare-transaction-policy-engine (FAIT SOURCÉ). Passkeys sur Base : précompile `P256VERIFY` (RIP-7212) à `0x0000000000000000000000000000000000000100`, activée Fjord (Base Sepolia 29 mai 2024, Mainnet 10 juillet 2024), gaz 3 450 → 6 900 (Azul) — https://docs.base.org/specifications/base-protocol/execution/precompiles (FAIT SOURCÉ) |

**Lecture comparative.** Toutes les options ci-dessus **déplacent** le problème « où est la clé » ; aucune ne
remplace le second verrou. Le raisonnement qui tient devant un jury technique (et qui est déjà celui de W2C)
est : **deux verrous indépendants** — (1) une politique déterministe hors-chaîne qui vit à côté du LLM, et
(2) des permissions on-chain que même une clé volée ne peut pas étendre. Le porteur de clé (A/B/C/D) est une
**ligne d'intégration**, pas l'architecture.

**Recommandation (PROPOSITION)** :

1. **Démo concours** : option **A** (EOA + env var) — la seule qui soit démontrable de bout en bout sur
   Base Sepolia sans dépendance payante, et celle dont la sécurité ne repose *pas* sur la promesse d'un
   tiers. La clé jetable est documentée comme telle (S1–S9).
2. **Produit, phase 1 (trésoreries DAO)** : option **A′** = même architecture, backend remplacé par un
   **service de signature non exportable** (KMS B ou enclave D). Critère de choix : le client possède déjà
   un KMS cloud (→ B) ou veut une politique vendor (→ D). Dans les deux cas, l'adresse du signer reste un
   **membre de rôle** : rotation = 1 transaction de la DAO (S8).
3. **Produit, phase 2 (institutions)** : MPC à parts séparées (Fordefi/Fireblocks-style) quand la
   trésorerie dépasse le seuil où l'on veut que *personne* ne détienne la clé entière ; c'est aussi le
   chemin naturel pour la conformité (règles signées par quorum, KYT).
4. **Passkeys (RIP-7212/WebAuthn)** : à réserver au **niveau T3** (approbation humaine) et à l'onboarding —
   pas au signer autonome de l'agent : un agent n'a pas de biométrie.
5. **Invariant à conserver quoi qu'il arrive** : le signer n'a **aucun** droit d'administration, et le
   retrait du rôle suffit à l'arrêter (W2C §d.1, invariants I3/I5). Toute option qui exigerait de donner à
   l'agent un droit d'admin sur la Safe doit être refusée — c'est le critère d'élimination.

**Écart de sécurité démo → prod, à dire au dossier** : la démo utilise une clé en clair dans un processus ;
la production ne doit pas. La transition ne change **pas** l'architecture (mêmes rôles, mêmes conditions,
mêmes plafonds) : elle change le backend qui produit la signature et le montant du `maxRefill`
(W2C §g.8, parité production).

---

## (b) CATALOGUE D'INTENTS v1 ET FAISABILITÉ TESTNET (question 5.2)

### b.1 Schéma final de l'intent (PROPOSITION — aligné V0.2 §10.2 + ajouts)

**Rappel source** : V0.2 §10.2 exigè que « le moteur produit une intention structurée : chain ID, compte,
action, actif, quantité, destinataire/contrat, fonction, paramètres et justification » et que « le schéma
rejette les champs inconnus, les types incorrects, les quantités négatives, les adresses mal formées ou les
appels non autorisés » (FAIT SOURCÉ : `ORVYREN_Document_de_reference_V0_2.docx` §10.2). La carte §5.2
ajoute `expiry` et `idempotency_key` (déjà exigés par V0.2 §10.4 : « expiration de la permission »,
« Idempotence »).

```jsonc
{
  "schema_version": "intent/v1",
  "intent_id": "01J…",                  // ULID (unique, trié par temps)
  "idempotency_key": "0x…64 hex…",      // keccak256(JSON canonique SANS intent_id ni created_at)
  "chain_id": 84532,                    // Base Sepolia (8453 en prod) — épinglé
  "account": "0x…",                     // la Safe (avatar) qui exécute — PAS l'agent
  "action": "transfer",                 // transfer | swap | supply | withdraw | repay | approve | change_policy
  "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",   // contrat du jeton
  "amount": "50.0",                     // CHAÎNE décimale ASCII (jamais un flottant)
  "amount_base_units": "50000000",      // entier dérivé, revérifié (décimales du contrat)
  "recipient": "0x…",                   // destinataire (transfer) ou contrat cible (swap/supply…)
  "function": "transfer(address,uint256)",  // signature exacte, obligatoire
  "params": {"to": "0x…", "value": "50000000"},  // paramètres canoniques ordonnés
  "expiry": "2026-10-16T12:00:00Z",     // RFC 3339 UTC — au-delà : refus, sans exception
  "created_at": "2026-10-15T12:00:00Z",
  "justification": "réduction d'exposition — 50 USDC vers réserve",  // ≤ 200 caractères, texte libre tracé
  "policy_version": "v1.3",             // version du texte de politique appliqué
  "source": {"decision_id": "…", "case": "usdc-2023-03", "signal": "…"}   // traçabilité amont (B3/B4)
}
```

**Règles de validation (déterministes, hors LLM)** :

1. **Champs inconnus rejetés** (pas de quarantaine en v1 exécution : un champ non prévu = refus) ; types
   stricts ; `amount` en notation décimale à point, refus des notations scientifiques.
2. `amount_base_units` **recalculé** par le validateur depuis `amount` + `decimals()` du contrat lu par RPC
   (protection contre l'erreur de décimale, matrice #5).
3. Adresses normalisées en minuscules — **aucune réparation** (comportement déjà codé :
   `normalize_address` refuse sans corriger — FAIT INTERNE `chain.py`).
4. `action ∈ catalogue` ; couple (action, fonction, params) **contraint** : `transfer` impose
   `function == "transfer(address,uint256)"` et `params.to == recipient`.
5. `expiry > now` et `expiry ≤ now + TTL` (TTL démo : 24 h, valeur `PERMISSION_TTL` existante).
6. `idempotency_key` absent du registre d'intents (persistant, append-only).
7. L'intent **n'est pas** du calldata : la construction du calldata est une étape distincte après `ALLOW`
   (séparation testée dans le code : `build_instruction` ne produit qu'une instruction **non signée` —
   FAIT INTERNE `run_execution_demo.py`).

**Écarts code actuel → schéma v1** (à porter lors de la construction, pas maintenant — phase recherche) :
ajout de `account`, `function`, `params`, `expiry`, `idempotency_key`, `schema_version`, `policy_version`,
`source` ; passage de `amount: float` à `amount: str` (décimal) ; `intent_id` ULID au lieu de « I1 ».

### b.2 Faisabilité testnet vérifiée (MESURÉ — Base Sepolia, 2026-10-15)

Toutes les vérifications ci-dessous ont été faites par RPC public `https://sepolia.base.org` (lecture seule),
entre les blocs **48 150 148 et 48 150 201** (dernier bloc : `2026-10-15T12:51:30Z`). Sorties brutes :
`research/raw_b5/rpc_b5_probe_output.txt`, `rpc_b5_probe2_output.txt`, `rpc_b5_probe3_output.txt`,
décodage : `b5_decoded_rpc.json`. **Rappel W2C : les adresses sont re-vérifiées au moment de l'exécution**
(protocole §e.7) — cette section prouve la *faisabilité*, elle ne fige pas les adresses.

**a) `transfer` ERC-20 (action v1 — implémentée).**

| Objet | Adresse | Vérification du 2026-10-15 |
|---|---|---|
| USDC de test (Circle) | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` | `eth_getCode` → 1 798 o ; `symbol()` = « USDC » ; `decimals()` = 6 |
| USDC d'Aave v3 (Base Sepolia) | `0xba50Cd2A20f6DA35D788639E581bca8d0B5d4D5f` | `eth_getCode` → 3 981 o ; `symbol()` = « USDC » ; `decimals()` = 6 |
| WETH (pré-déploiement OP-stack) | `0x4200000000000000000000000000000000000006` | code 2 041 o ; « WETH » ; 18 décimales |

⚠️ **Deux USDC distincts sur Base Sepolia** (MESURÉ) : le pool Uniswap USDC/WETH que nous avons sondé est
adossé au **USDC Circle** (`token0()` du pool = `0x036CbD…`), tandis que la réserve de lending Aave est le
**USDC d'Aave** (`0xba50Cd2A…`, absent de la liste des réserves sous l'autre adresse). Un transfert de démo
utilise le USDC Circle (robinet Circle) ; toute action Aave devrait utiliser le USDC d'Aave (robinet Aave) —
**deux jetons différents, deux robinets différents**. À écrire dans le runbook ; c'est le genre de détail qui
fait échouer une démo en direct.

**b) `swap` (Uniswap v3 — action supplémentaire n° 1).** FAIT SOURCÉ pour les adresses (page de déploiement
Uniswap v3, reprises du référentiel `evm-onchain-verification`) **et** MESURÉ pour la présence du code et la
liquidité :

| Objet | Adresse | Mesure 2026-10-15 |
|---|---|---|
| SwapRouter02 | `0x94cC0AaC535CCDB3C01d6787D6413C739ae12bc4` | code 24 497 o |
| Fabrique v3 | `0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24` | code 24 535 o |
| QuoterV2 | `0xC5290058841028F1614F3A6F0F5816cAd0df5E27` | code 8 273 o |
| NonfungiblePositionManager | `0x27F971cb582BF9E50F397e4d29a5C7A34f11faA2` | code 24 384 o |
| UniversalRouter | `0x492E6456D9528771018DeB9E87ef7750EF184104` | code 19 540 o |
| Pool USDC(Circle)/WETH, frais 3000 | `0x46880b404cd35c165eddeff7421019f8dd25f4ad` | `liquidity()` = **325 268 175 666 787** ; `slot0` → prix implicite ≈ **4 674 USDC/WETH** |
| Pool USDC(Circle)/WETH, frais 500 | `0x94bfc0574ff48e92ce43d495376c477b1d0eeec0` | non détaillé (existe) |
| Pool USDC(Aave)/WETH, frais 3000 | `0x92266210facf124f190fbad79aa230dfb85926ce` | `liquidity()` = 4 957 986 963 561 ; prix implicite **absurde** (tick ≈ −262 183) |

**Quotes vivantes (QuoterV2, à l'instant des mesures)** :
- 50 USDC(Circle) → **0,010640665689211078 WETH** via frais 3000 (estimation gaz 89 932) ;
- 50 USDC(Circle) → **0,020174945161605429 WETH** via frais 500 (14 ticks franchis, estimation gaz 455 019) ;
- 50 USDC(Aave) → 2,0344522573641 WETH via frais 3000 (prix non représentatif).

**Conclusion swap** : l'action est **matériellement faisable sur Base Sepolia** (routeur + pools + quotes en
direct), mais **les prix ne sont pas des données de marché** — deux étages de frais du même couple cotent
4 674 et 2 479 USDC/WETH au même instant, et le pool adossé au USDC d'Aave cote un prix sans rapport. Donc :
la démo d'un swap sur testnet prouve le **chemin d'exécution** (approve → swap → receipt), jamais la qualité
d'exécution ; toute évaluation économique d'un swap se fait en **simulation sur données réelles** (skill
`evm-onchain-verification` : « Testnet prices are not market data »).

**c) Aave v3 (action supplémentaire n° 2 : supply/withdraw/repay).** FAIT SOURCÉ : adresses officielles du
référentiel `aave-address-book` (`src/AaveV3BaseSepolia.sol`, consulté 2026-10-15) **et** MESURÉ :

| Objet | Adresse | Mesure 2026-10-15 |
|---|---|---|
| Pool (proxy) | `0x8bAB6d1b75f19e9eD9fCe8b9BD338844fF79aE27` | code 1 853 o ; `getReservesList()` → **6 réserves** : USDC `0xba50…`, USDT `0x0a21…`, WBTC `0x5411…`, WETH `0x4200…0006`, cbETH `0xd171…`, LINK `0x810d…` (symboles lus par RPC) |
| PoolAddressesProvider | `0xE4C23309117Aa30342BFaae6c95c6478e0A4Ad00` | code 6 697 o (le candidat deviné `0xE4C2330912aa…` → **0 o** : adresse inventée, écartée par la mesure) |
| PoolConfigurator | `0x0Bf6bdFF4da24C272BC524d521Ab0db20601D384` | non testé ce jour (source : address-book) |
| Oracle | `0x943b0dE18d4abf4eF02A85912F8fc07684C141dF` | code 2 662 o |
| Data provider | `0xBc9f5b7E248451CdD7cA54e717a2BFe1F32b566b` | code 7 435 o |
| aToken USDC | `0x10F1A9D11CDf50041f3f8cB7191CBE2f31750ACC` | code 1 853 o (proxy) ; confirmé dans `getReserveData` |
| Variable debt token USDC | `0xFB3e85601b7fEb3691bbb8779Ef0E1069E347204` | code 1 853 o ; confirmé |

**État de la réserve USDC (décodage `getReserveData`, config + taux)** : `isActive = 1`, `isFrozen = 0`,
`borrowingEnabled = 1`, LTV 82,5 %, seuil de liquidation 86 %, bonus 105 %, facteur de réserve 10 %,
**supplyCap = 0 (pas de plafond)**, borrowCap = 0, `liquidityIndex` ≈ 1,2448, taux d'offre ≈ 0,235 %,
taux d'emprunt variable ≈ 1,179 %. WETH : `isActive = 1`, `isFrozen = 0`, LTV 83,5 %, supplyCap = 2 500,
borrowCap = 1 200, taux 2,08 % / 3,51 %. (La réserve USDC d'Aave est donc **utilisable** : ni gelée, ni
pausée.)

**Ce que « repay » implique** : `repay` rembourse une **dette** ; une Safe neuve n'a pas de dette. Un run
Aave complet serait : `supply` collatéral → `borrow` → `repay` (3+ transactions, 3+ intents, plusieurs
venues). **Classement : v2** (§b.3). Pour la personne « trésorerie DAO », l'action pertinente est plutôt
`withdraw` (réduire l'exposition) — également v2, qui exige une position `supply` préalable.

**d) Vérification des sélecteurs de fonction (MESURÉ — 2026-10-15).** Une implémentation **Keccak-256 en
Python pur** (validée sur les vecteurs connus `keccak256("")` et `keccak256("abc")`) a permis de calculer les
sélecteurs localement — l'annuaire public 4byte.directory s'étant révélé **bruité** (plusieurs hex pour une
même signature). Trois résultats qui changent des hypothèses :

1. **`exactInputSingle` du SwapRouter02 = `0x04e45aaf`** (7 champs, sans `deadline`) : **vérifié
   fonctionnellement** — un `eth_call` sur le routeur déployé exécute la fonction et revert avec
   `STF` (Error(string) d'Uniswap) faute d'approbation ; la variante `0x414bf389` (avec `deadline`) est
   **absente** du routeur déployé (revert vide, contrôle négatif à l'appui).
2. **`repay` sur le Pool Aave de Base Sepolia porte la signature `repay(address,uint256,uint256,address)`
   (`0x573ade81`)** — présente dans le bytecode de l'implémentation (`0xE9fb…783A`, slot EIP-1967 du proxy
   vérifié) — et **pas** la forme usuelle de la documentation `repay(address,uint256,address)`
   (`0x5ceae9c4`, absente). Leçon générale : **la signature d'appel doit être prise du contrat déployé, pas
   de la documentation** ; à re-tester le jour de l'implémentation.
3. **Le module Roles de Base Sepolia renvoie `NotAuthorized(address)` (`0x4a0bfec1`)** quand un non-membre
   appelle `execTransactionWithRole` — et non `NoMembership` comme le supposait W2C §e (#3) : à la démo,
   journaliser le **sélecteur constaté**. Sélecteurs clés du module vérifiés présents dans son bytecode :
   `execTransactionWithRole` `0xc6fe8747`, `…ReturnData` `0x2b99e506`, `assignRoles` `0x957ed2b3`,
   `allowTarget` `0x7b0da5b2`.

Détail complet : `research/raw_b5/SELECTEURS_VERIFIES.md` (avec le topic0 `Transfer` recalculé —
**égal** à la constante de `verify.py`).

### b.3 Classement des actions : implémenté v1 / simulé / v2

| Action | Fonction (calldata) | Verdict politique v1 (code) | Statut d'implémentation | Preuve / condition |
|---|---|---|---|---|
| **`transfer`** ERC-20 vers destinataire allowlisté | `transfer(address,uint256)` `0xa9059cbb` | `ALLOW` si toutes les règles passent (R1–R8) | **IMPLÉMENTÉ v1** (politique + garde + calldata + vérification de receipt, **hors ligne**, testé) | FAIT INTERNE : `intents.py`, `chain.py`, `verify.py`, `guard.py`, `tests/test_execution.py` |
| **`swap`** via routeur Uniswap v3 (`exactInputSingle`) | `exactInputSingle((address,address,uint24,address,uint256,uint256,uint160))` `0x04e45aaf` — **vérifié fonctionnellement** sur le SwapRouter02 déployé (revert `STF` = la fonction s'exécute ; la variante avec `deadline` `0x414bf389` est **absente** du routeur déployé) | `REQUIRE_APPROVAL` en v1 (dans `ACTIONS_SOUS_APPROBATION`) | **SIMULÉ v1 / préparé** (quote QuoterV2 + instruction) ; **v2** = exécution dans l'enveloppe (condition Zodiac sur `minOut`/receveur=avatar) | Faisabilité mesurée §b.2.b ; politique on-chain à écrire (matrice #4, #10) |
| **`approve`** borné (jeton → routeur/Pool) | `approve(address,uint256)` `0x095ea7b3` (keccak vérifié) | `REQUIRE_APPROVAL` en v1 | **SIMULÉ v1 / technique** ; **v2** = exécution bornée (montant exact, jamais d'approbation infinie), condition on-chain sur le couple (spender, montant) | Nécessaire à tout protocole qui tire des fonds ; spec d'approbation bornée = OUVERT (Q7) |
| **`supply` / `withdraw` Aave** | `supply(address,uint256,address,uint16)` `0x617ba037` et `withdraw(address,uint256,address)` `0x69328dec` — **présents dans le bytecode du Pool déployé** ; `supply` exécute (revert `InvalidAmount()` `0x2c5211c6` sans fonds) | hors périmètre v1 (action inconnue → `DENY`) | **v2** — réserve USDC active vérifiée, mais position préalable requise | §b.2.c |
| **`repay` Aave** | ⚠️ la signature **déployée** sur Base Sepolia est `repay(address,uint256,uint256,address)` `0x573ade81` (forme avec `rateMode`) — le sélecteur keccak de la forme « v3 » `repay(address,uint256,address)` (`0x5ceae9c4`) est **absent du bytecode** du Pool | hors périmètre v1 (`DENY`) | **v2** — exige une dette (montage multi-étapes) ; **et** l'appel devra être construit sur la signature réellement déployée, re-vérifiée le jour J | §b.2.c + `raw_b5/SELECTEURS_VERIFIES.md` |
| `change_policy`, `revoke` | — (jamais autonomes) | `REQUIRE_APPROVAL` (code) | v1 : démontre le blocage (run B3 du plan) | FAIT INTERNE : `policy/__init__.py` `ACTIONS_SOUS_APPROBATION` |

**Règle de croissance du catalogue (PROPOSITION)** : une action passe de « simulée » à « exécutable » quand
(i) ses conditions Zodiac sont écrites et testées par attaque, (ii) sa vérification de receipt est
spécifiée (§d), et (iii) son run de refus correspondant existe. Tant que les trois ne sont pas vrais,
l'action reste `REQUIRE_APPROVAL` ou `DENY` — jamais « exécutée parce qu'on a confiance ».

---

## (c) PRÉFLIGHT & ENVOI (question 5.3 — première moitié)

### c.1 Checklist de préflight (avant toute signature)

Reprise de V0.2 §10.2.4-5 (« une simulation ou une vérification d'état précède l'envoi » ; « un signer
isolé signe seulement une intention autorisée ») et de W2C §d.3. **Aucune signature** si un seul contrôle
échoue. Codes stables en minuscules pour le journal.

| # | Contrôle | Mécanisme | Échec → code |
|---|---|---|---|
| P1 | Verdict de politique **ALLOW** tracé | `assert_allowed(decision)` (existe) | `policy_not_allow` |
| P2 | Chaîne épinglée | `eth_chainId` == 84532 (8453 en prod) — refus si ≠ | `chain_id_mismatch` |
| P3 | `expiry` de l'intent non dépassée | horloge UTC du service | `intent_expired` |
| P4 | Idempotence | `idempotency_key` absent du registre persistant (append-only) | `intent_already_processed` |
| P5 | Pause (kill switch hors-chaîne K0) | drapeau du service de signature | `agent_paused` |
| P6 | Politique on-chain = attendue | lecture du module (version/commit déployé) ; W2C Annexe 3 : vérifier la version **avant** chaque période d'exécution | `module_version_unknown` |
| P7 | Adresses cibles re-vérifiées | `eth_getCode` non vide pour chaque contrat de l'intent (voir §e.7) | `target_code_missing` |
| P8 | Nonce | `eth_getTransactionCount(agent, pending)` ; **un seul vol en cours** (sérialisation stricte du signer) | `nonce_conflict` |
| P9 | Soldes | ETH agent ≥ 2 × estimation de gaz ; solde ERC-20 de la Safe ≥ montant (+ tout frais du jeton : USDC standard, pas de frais de transfert) | `insufficient_gas_balance` / `insufficient_token_balance` |
| P10 | Gaz | prix lu (`eth_gasPrice`, `baseFeePerGas`, `maxPriorityFeePerGas`) ; plafond de sécurité : refus si le prix dépasse **10 × la médiane observée** (protection contre un RPC menteur ou un pic) — mesures du 2026-10-15 : baseFee 0,005 gwei, priorité 0,001 gwei, `gasPrice` 0,006 gwei | `gas_price_out_of_bounds` |
| P11 | **Simulation** `eth_call` du calldata **exact**, depuis l'adresse de l'agent, au dernier bloc | Refus si revert (message décodé si possible) ; variante `execTransactionWithRoleReturnData` pour lire la valeur de retour du module | `simulation_revert` |
| P12 | Estimation gaz | `eth_estimateGas` du même calldata ; garder `gasLimit = 1,25 × estimation` (plafonné) | `gas_estimate_failed` |

**Note simulation** : la simulation est exécutée **depuis la clé de l'agent** et non depuis une adresse
neutre — c'est le seul moyen de faire évaluer la politique du module (rôle, allowances, conditions) dans les
mêmes conditions que l'exécution réelle. Le code actuel n'a **pas** encore cette étape (FAIT INTERNE :
`chain.py` est lecture seule) : elle appartient au service signataire v1 (script `preflight.py`, §e.6).

### c.2 Envoi, nonce, retries bornés

- **Type de transaction** : EIP-1559 (type 2) — Base est compatible ; `maxFeePerGas`, `maxPriorityFeePerGas`
  dérivés des lectures P10, avec plafond.
- **Sérialisation** : **une transaction en vol à la fois** par signer (le nonce est la séquence ; le
  parallélisme est interdit au niveau du service). Si une transaction est en vol, la suivante attend le
  receipt ou l'expiration du délai (`timeout_inclusion`).
- **Retries réseau (bornés)** : les erreurs de **transport/RPC** (timeouts, 5xx, « already known ») se
  réessayent **3 fois** avec backoff exponentiel (1 s, 4 s, 16 s), **sur la même transaction signée**
  (même hash, même nonce) — re-broadcast idempotent.
- **Ce qui ne se réessaye jamais** : un `revert` de simulation, un refus de politique, un `status = 0x0`
  (l'échec est un résultat : §d.4). On ne « retente » pas une attaque interdite.
- **Après N blocs sans inclusion** : la transaction est marquée `PENDING_STALE` (voire droppée par le
  mempool) ; deux options, documentées et journalisées : (i) re-broadcast tel quel ; (ii) **remplacement**
  (même nonce, frais relevés d'au moins +10 %) — jamais une nouvelle transaction avec un nonce plus haut
  pour « contourner » un blocage, car cela réordonnerait un vol entier. Toute reprise exige de **re-vérifier
  P4/P5** (idempotence + pause).
- **Journalisation** : chaque tentative (`kind: SUBMIT_ATTEMPT`) et chaque erreur ont une entrée, y compris
  les échecs — le journal doit raconter la panne, pas seulement le succès.

### c.3 Politique de confirmations (profondeur de blocs)

| Contexte | Politique PROPOSITION | Justification |
|---|---|---|
| **Démo Base Sepolia** | receipt `status = 0x1` + **attendre 2 blocs** avant de déclarer `CONFIRMED`, puis vérifier (§d) | blocs Base ≈ 1,64 s (mesure W2C du 2026-10-15, **sur Base mainnet** : 620 blocs/1 016 s) → ≈ 3,3 s ; suffisant pour l'anti-reorg local |
| **Production (garder la porte ouverte)** | tag **`safe`** pour l'action courante, tag **`finalized`** pour clore l'entrée d'audit | MESURÉ : `sepolia.base.org` sert `eth_getBlockByNumber("safe")` et `("finalized")` (2026-10-15) — donc la stratégie est exécutable telle quelle ; OP-stack : `safe` = séquencé vers L1, `finalized` = finalisé L1 |
| **Valeur > plafond quotidien / opérations de politique** | `finalized` obligatoire | cohérence avec la logique « le pire cas est un nombre » |

### c.4 Gestion minimale des reorgs (PROPOSITION)

1. **Enregistrer** `blockNumber` **et** `blockHash` du receipt dès qu'il est lu (le hash de bloc est la
   clé de détection).
2. **Relire** le receipt après la fenêtre de confirmation (2 blocs en démo) — et **revérifier** que
   `blockHash` est inchangé.
3. **Détection** : (i) `eth_getTransactionReceipt(tx)` renvoie `null` alors qu'il avait renvoyé un receipt →
   `REORGED` ; (ii) même tx, `blockHash` différent → `REORGED`.
4. **Réaction** : repasser par **P4 (idempotence)**, **P5 (pause)** et la **simulation** ; si l'intent est
   toujours `ALLOW` et non exécuté (`VERIFY` négatif), ré-émettre la transaction ; sinon marquer
   `UNRESOLVED` et alerter un humain. **Ne jamais double-exécuter** : avant toute ré-émission, contrôler le
   registre d'intentions **et** l'état on-chain (le log `Transfer` de l'ancienne inclusion peut réapparaître
   inchangé après le reorg).
5. **Formuler honnêtement** : Base est un L2 à séquenceur centralisé, les reorgs y sont courts mais pas
   impossibles ; la protection pratique est la fenêtre courte décision→envoi + plafonds faibles (W2C §d.4),
   et la confirmation `safe`/`finalized` en production (mesuré ci-dessus).
6. **Machine à états d'exécution** (à implémenter dans le service) :
   `PREPARED → SIMULATED → SUBMITTED → INCLUDED → CONFIRMED → VERIFIED` ;
   branches : `ABORTED` (préflight), `FAILED` (revert on-chain), `PENDING_STALE`, `REORGED`, `UNRESOLVED`.

---

## (d) VÉRIFICATION DU RECEIPT (question 5.3 — seconde moitié)

### d.1 Champs exacts vérifiés

Le code actuel (`verify.py`, FAIT INTERNE) vérifie déjà : `status` de succès, `chainId` (attaché par
l'appelant — les receipts JSON-RPC n'en portent pas), contrat du jeton, expéditeur, destinataire, montant,
et l'existence d'un log `Transfer`. La spécification v1 fige ces contrôles :

| Contrôle | Valeur attendue | Code de mismatch |
|---|---|---|
| Statut | `status == 0x1` (ou `1`/`true`) ; **absent ≠ succès** | `TRANSACTION_FAILED` / `RECEIPT_STATUS_MISSING` |
| Chaîne | `chainId == 84532` (lu séparément par le client, attaché au receipt) | `CHAIN_ID_MISSING` / `CHAIN_ID_MISMATCH` / `CHAIN_ID_INVALID` |
| Contrat du jeton | `logs[*].address == intent.asset` (minuscules) | `TOKEN_CONTRACT_MISMATCH` |
| Événement | `topics[0] == 0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` (keccak `Transfer(address,address,uint256)`) et **exactement 3 topics** | `NO_TRANSFER_LOG` |
| Expéditeur | `topics[1]` (20 derniers octets du mot) == **Safe (avatar)** — la Safe, pas l'agent | `SENDER_MISMATCH` |
| Destinataire | `topics[2]` == `intent.recipient` | `RECIPIENT_MISMATCH` |
| Montant | `data` (entier) == `amount_base_units` — **comparaison entière**, jamais flottante | `AMOUNT_MISMATCH` |
| Enveloppe | `receipt.to` == module Roles (l'appel passe par le module) ; `receipt.from` == adresse de l'agent | *(ajout v1 : `WRONG_EXECUTOR` / `WRONG_TARGET`)* |
| Module | au moins un log émis par l'adresse du module (`ConsumeAllowance` attendu côté Zodiac, cf. W2C §d.5) | *(ajout v1, informatif : `MODULE_EVENT_ABSENT` → WARN)* |

**Ajouts proposés v1** (au-delà du code, PROPOSITION) : n'utiliser que les champs ci-dessus — un contrôle
qui ne peut pas être mappé à un champ exact du receipt JSON-RPC est un contrôle non vérifié.

### d.2 Correspondance intent ↔ logs (règle d'unicité)

- Le code actuel choisit le « meilleur » log parmi ceux du jeton (score : expéditeur > destinataire >
  montant — FAIT INTERNE). **v1 durcit** : s'il y a plus d'un log `Transfer` du jeton dans le receipt, et
  qu'**aucun** ou **plus d'un** ne correspondent exactement à (avatar, destinataire, montant), le résultat
  est marqué `LOG_COUNT_AMBIGUOUS` → vérification **non concluante**, revue humaine (jamais un « ok »
  optimiste). Un seul log correspondant exactement = conforme.
- La comparaison d'adresses est insensible à la casse (normalisation minuscule) ; le montant est comparé en
  **unités de base** (entier) ; la normalisation ne répare jamais une adresse malformée (`0x…40 hex` sinon
  refus).

### d.3 Cas d'échec, de revert et partiel

| Cas | Ce que l'on capture | Journal |
|---|---|---|
| Revert on-chain (`status = 0x0`) | receipt + **rejeu `eth_call` au bloc du receipt** pour extraire la donnée de revert (sélecteur + message si décodable) ; coût de gaz réel | `RECEIPT` (échec) + `OUTCOME: EXECUTION_FAILED` |
| Transaction abandonnée / jamais incluse | état `PENDING_STALE` puis décision humaine ; jamais de faux « CONFIRMED » | `OUTCOME: NOT_INCLUDED` |
| Partiel / ambigu | `LOG_COUNT_AMBIGUOUS`, log du ou des logs trouvés (décodés) | `OUTCOME: VERIFY_INCONCLUSIVE` |
| Receipt indisponible (nœud) | nouvelle lecture bornée (3 essais, backoff) puis `UNRESOLVED` | `VERIFY_ERROR` |

**Un échec est un résultat de première classe** (exigence V0.2 §12.4 : la démo « … ne prétend pas que le
refus a produit une transaction d'exécution réussie » ; FAIT SOURCÉ). Concrètement : (i) le dossier de
décision contient la ligne d'échec avec le même poids qu'un succès ; (ii) les runs C de la démo **sont** des
échecs on-chain affichés (statut `0x0`, sélecteur de revert, gaz perdu) ; (iii) le rapport final liste les
résultats négatifs (V0.2 §12.4 dernier point).

### d.4 Liaison vers l'audit

- Un fichier `audit.jsonl` **chaîné par hash** (`record_hash = keccak(prev_hash || canonical_json(record))`,
  format W2C §d.5) ; une entrée par étape : `INTENT` → `POLICY` → `SIMULATION` → `SUBMIT` → `RECEIPT` →
  `VERIFY` → `OUTCOME`.
- Chaque enregistrement porte : `ts`, `intent_id`, `idempotency_key`, `policy_version`, `chain_id`, `rpc`,
  `nonce`, `tx_hash`, `block_number`, `block_hash`, et le résultat de vérification (avec ses codes de
  mismatch).
- **Opposabilité** (W2C §d.5) : chaque `tx_hash` est relisible (`eth_getTransactionReceipt`), les logs
  `Transfer` sont recoupés avec l'intention, la chaîne de hash détecte toute réécriture ; la politique
  appliquée est identifiée par version.
- **Script de vérification tiers** (`audit_export_verify.py`, §e.6) : relit tous les `tx_hash` du journal,
  recalcule les transferts depuis les logs et compare à l'intention — c'est le run E de la démo.
- **Écart assumé v1** : la consommation d'allowance n'est pas vérifiée par lecture directe dans le code
  actuel ; v1 : l'attester par l'événement du module (si présent) **ou** journaliser un `WARN`, et planifier
  la lecture d'allowance (app Roles / subgraph) en v1.5. Ne pas prétendre l'avoir vérifiée quand ce n'est
  pas le cas.

---

## (e) LES 5 RUNS DE DÉMO, MIS À JOUR (question 5.4)

Base : W2C §g (plan complet, adresses vérifiées le 2026-10-15). Ce qui **change** ici : schéma d'intent v1,
préflight §c.1, vérifications §d, critères de succès **mesurables** par run, scripts nommés, dépendances, et
protocole de re-vérification des adresses. Durée cible totale : **8 minutes** (W2C).

### e.0 Montage (à faire la veille — non chronométré en démo)

Repris de W2C §g.1 : Safe « DAO » 2/3 sur Base Sepolia ; déploiement + activation du module Roles **pour
cette Safe** (instance propre — l'adresse `0xF296…83D5` est le déploiement officiel du code, pas un module
partagé) ; politique `AGENT` (cible USDC, fonction `transfer` scopée, condition destinataire
`Or(EqualTo(B), EqualTo(C))`, montant `WithinAllowance(usdc_daily)` avec `refill = maxRefill = 300e6`,
`period = 86400`, quota `calls_daily = 10/jour`) ; signer EOA (§a.1) ; financement robinets ; politique
hors-chaîne versionnée (`policy.yaml`) — **exécutée par un module déterministe, pas par le LLM**.

Contrôles de montage (à journaliser) : `Roles.owner() == Safe` ; `Roles.roles(AGENT).members(agent) == true` ;
`safe.balanceOf(USDC) == montant attendu` ; `agent.balanceETH > 0` ; **`verify_addresses.py` OK** (§e.7).

### e.1 RUN A — ALLOW dans l'enveloppe (les deux verrous disent oui)

| Étape | Contenu (mise à jour) |
|---|---|
| A0 | Intent v1 : `transfer`, `asset = USDC Circle`, `amount = "50.0"`, `recipient = B`, `expiry = J+1`, `idempotency_key = keccak(…)` |
| A1 | Verrou hors-chaîne : `POLICY {ALLOW}` — règles `cap_tx_100 ✓`, `rolling_24h_300 ✓`, `dest_in_allowlist ✓`, `chain=84532 ✓`, `intent_not_seen ✓` (journal `INTENT` + `POLICY`) |
| A2 | **Préflight §c.1** (12 contrôles) ; simulation `eth_call` de `execTransactionWithRole(USDC, 0, transfer(B,50e6), 0, AGENT, true)` depuis l'agent → pas de revert |
| A3 | Envoi de la tx signée (service signataire) ; `SUBMIT` journalisé (hash, nonce) |
| A4 | Receipt : `status = 0x1` ; attendre **2 blocs** ; vérification §d.1 |
| Préuves à l'écran | statut ; log `Transfer` (from = Safe, to = B, value = 50 000 000) ; `balanceOf(Safe)` et `balanceOf(B)` avant/après (sélecteur `0x70a08231`) ; consommation d'allowance si lisible (sinon WARN) ; entrées `RECEIPT` + `VERIFY` |
| **Critères de succès mesurables** | (1) `receipt.status == 1` ; (2) **exactement un** log Transfer correspondant exactement ; (3) Δsolde Safe = −50 000 000, Δsolde B = +50 000 000 ; (4) compteur de signatures du service = **1** ; (5) présence des 7 `kind` de journal pour cet `intent_id` ; (6) `blockHash` stable après 2 blocs |

### e.2 RUN B — DENY par la politique hors-chaîne (le LLM propose, le système refuse)

| Cas | Intent | Verdict attendu | Preuve |
|---|---|---|---|
| B1 | `transfer(B, 150 USDC)` | `DENY` (`AMOUNT_ABOVE_TX_CAP` ; et cumul > 300) | journal `POLICY{DENY}`, **0 signature**, pas de `tx_hash` |
| B2 | `transfer(D_non_listé, 20 USDC)` | `DENY` (`RECIPIENT_NOT_ALLOWED`) — attaque #12 | idem |
| B3 | rejeu de l'intent A (même `idempotency_key`) ×3 | `DENY` (`INTENT_ALREADY_PROCESSED`) — attaque #1 | idem |
| B4 | `change_policy` | `REQUIRE_APPROVAL` (jamais autonome) | idem (démontre le blocage sans exécution, V0.2 §10.3 T3) |

**Critères de succès mesurables** : compteur de signatures = **0** sur l'ensemble du run ; `nonce` de
l'agent **inchangé** ; soldes inchangés ; 4 entrées `POLICY{DENY|REQUIRE_APPROVAL}` avec codes exacts ;
aucun `tx_hash` émis.

### e.3 RUN C — DENY par la chaîne (on contourne volontairement le verrou hors-chaîne)

On fabrique **directement** les calldatas interdits avec la clé de l'agent (attaque #11) — le message :
« la sécurité ne repose pas sur le logiciel ORVYREN ».

| Cas | Calldata forcé | Attendu |
|---|---|---|
| C1 | `execTransactionWithRole(USDC, 0, transfer(B, 500e6), 0, AGENT, true)` | **revert** (`AllowanceExceeded`-style) ; tx incluse avec `status = 0x0`, gaz perdu |
| C2 | `execTransactionWithRole(USDC, 0, transfer(D_non_listé, 1e6), 0, AGENT, true)` | **revert** (condition de destinataire) |
| C3 | `Roles.allowTarget(…)` puis `Safe.enableModule(attaquant)` depuis la clé agent | **reverts** `onlyOwner` / `GS*` (attaque #7) — journaliser le **sélecteur constaté**, pas un nom supposé |
| C4 | boucle « 100 + 100 + 100 + 100 » | les 3 premières passent, la 4ᵉ **revert** (dépassement cumulé on-chain, #8) |
| C5 | frontière de période (#2) | deux tx encadrant la frontière **passent on-chain** (limite assumée) mais le compteur **glissant** hors-chaîne refuse la seconde (`DENY{rolling_24h_300}`) — le journal montre la limite à côté de la preuve |

**Critères de succès mesurables** : chaque cas C1/C2/C4-4ᵉ → `status == 0x0` **et** sélecteur de revert
capturé **et** absence de tout log `Transfer` correspondant **et** soldes inchangés ; C3 → revert des deux
appels ; C5 → 2 receipts `status == 1` + 1 entrée `DENY` hors-chaîne ; le coût de gaz de chaque échec est
enregistré (c'est le prix de l'attaque).

### e.4 RUN D — Kill switch (mesuré)

1. L'agent prépare une intention `ALLOW` (100 USDC) **sans l'envoyer**.
2. La DAO exécute `assignRoles(agent, [AGENT], [false])` (2 signatures sur 3) — **chronométrer** :
   (a) collecte des signatures, (b) inclusion (Base ≈ 1,64 s/bloc mesuré), (c) effet.
3. L'agent tente sa transaction : **revert** — sélecteur **mesuré** le 2026-10-15 sur le module de Base
   Sepolia : `NotAuthorized(address)` = `0x4a0bfec1` (un non-membre qui appelle `execTransactionWithRole`) ;
   **journaliser le sélecteur constaté**, pas le nom supposé (`NoMembership` dans la doc amont).
4. Vérification indépendante : `Roles.roles(AGENT).members(agent) == false` (`eth_call`).
5. Variante K2 : `disableModule(prev, rolesModule)` (périmètre plus large) ; reset ensuite
   (`assignRoles(...,true)`).

**Critères de succès mesurables** : latences (a)(b)(c) affichées ; receipt de la tentative agent
`status == 0x0` (ou non incluse si suffisamment retardée — les deux issues sont documentées comme valides) ;
membre = false après révocation ; fenêtre d'arrêt journalisée.

### e.5 RUN E — Journal et audit (la partie qui vend ORVYREN)

1. Export `audit.jsonl` (chaîne de hash) + `report.md` lisible.
2. **Vérification indépendante en direct** : un script relit chaque `tx_hash`
   (`eth_getTransactionReceipt`), recalcule les transferts depuis les logs, compare aux intentions →
   affiche « N exécutions conformes, M refus hors-chaîne, K tentatives forcées refusées par la chaîne ».
3. Optionnel : afficher le **diff de politique** (app Roles) pour prouver l'état de l'enveloppe au moment
   des faits.
4. Réconciliation des compteurs : le nombre d'événements `Transfer` du jeton dans la fenêtre de démo doit
   égaler le nombre d'exécutions ALLOW (hors transferts de financement du montage — à filtrer par adresse).

**Critères de succès mesurables** : chaîne de hash **recalculée OK** (aucune écriture détectée) ; écart
journal↔chaîne = **0** ; le rapport liste explicitement les refus et les échecs (première classe) ;
adresses des contreparties du rapport = adresses vérifiées en §e.0.

### e.6 Scripts à produire (liste — noms indicatifs)

| # | Script | Rôle | Run |
|---|---|---|---|
| 1 | `scripts/b5/generate_signer_key.py` | Génère la clé jetable localement (jamais imprimée), écrit le `.env` non versionné | Montage |
| 2 | `scripts/b5/check_env_hygiene.py` | Vérifie `.gitignore`, scan du dépôt (aucune clé), noms des variables sensibles présents (`guard.present_secret_env_names`) | Montage + avant chaque run |
| 3 | `scripts/b5/verify_addresses.py` | Re-vérifie par `eth_getCode` chaque adresse du plan (taille attendue), `eth_chainId`, numéro de bloc ; **arrêt si écart** | Montage + jour de démo |
| 4 | `scripts/b5/faucet_check.py` | Contrôle des soldes (ETH agent ≥ seuil, USDC Safe ≥ seuil) avant démo | Montage |
| 5 | `scripts/b5/build_intent.py` | Construit/valide un intent v1 (canonical JSON, `idempotency_key`, `expiry`) | Tous |
| 6 | `scripts/b5/preflight.py` | Les 12 contrôles §c.1 (dont `eth_call` de simulation) | Tous (ALLOW) |
| 7 | `scripts/b5/signer_service.py` | Service signataire isolé : reçoit `intent ALLOW`, signe, envoie, gère nonce/retries ; **seul** lecteur de la clé | Tour A |
| 8 | `scripts/b5/verify_receipt_run.py` | Vérification §d (réutilise `orvyren.execution.verify`) + détection reorg | Tour A |
| 9 | `scripts/b5/run_c_force.py` | Fabrique et envoie les calldatas interdits (C1–C5), capture les sélecteurs de revert | Tour C |
| 10 | `scripts/b5/run_d_killswitch.py` | Chronométrage du kill switch + vérification d'état | Tour D |
| 11 | `scripts/b5/journal.py` | Append `audit.jsonl` chaîné par hash (utilisé par tous) | Tous |
| 12 | `scripts/b5/audit_export_verify.py` | Export + vérification tierce du journal (relecture chaîne) | Tour E |
| 13 | `scripts/b5/setup_safe_and_module.md` | Procédure de montage (Safe{Wallet} ou scripts `packages/evm` du dépôt Zodiac) | Montage |

**Dépendances** : Python 3.11 (poste) ; **service signataire** : bibliothèque de signature hors stdlib
(OUVERT Q1) ; **Safe{Wallet} web** (ou `safe-cli`) pour la Safe 2/3 ; robinets Base Sepolia (ETH) et Circle
(USDC) ; RPC `https://sepolia.base.org` (limites de débit publiques — prévoir un RPC de repli) ; navigateur
pour l'app Roles (diff de politique) ; horloge UTC fiable. Aucun service payant.

### e.7 Protocole de re-vérification des adresses (avant chaque exécution)

W2C l'annonce : « les adresses seront re-vérifiées au moment de l'exécution ». Protocole : exécuter
`verify_addresses.py` (script 3) qui, pour **chaque** adresse du plan (module Roles, libs, SafeL2,
fabrique, MultiSendCallOnly, USDC Circle, USDC Aave, WETH, SwapRouter02, fabrique Uniswap, Quoter,
Aave Pool, aToken, vToken, oracle, data provider, EAS) : (i) appelle `eth_getCode` et compare la **taille**
à la valeur attendue (tableaux §b.2 + W2C §g.0) ; (ii) vérifie `eth_chainId == 0x14a34` ; (iii) enregistre
`blockNumber` + horodatage. **Tout écart = arrêt de la démo** (les adresses officielles peuvent être
redéployées ; un testnet peut être réinitialisé sans préavis — c'est précisément pourquoi la mesure prime
sur la mémoire).

---

## (f) QUESTIONS OUVERTES (à trancher en revue d'équipe)

1. **Q1 — Bibliothèque de signature** : le service signataire ne peut pas être en stdlib seule (pas de
   Keccak/secp256k1). `eth-account` (MIT, Python) ou `cast` (Foundry) ? La dépendance doit rester isolée
   et déclarée (`LICENSES.md`).
2. **Q2 — Montants des runs** : W2C §g.2 utilise 50 USDC pour le run A ; le code de démo utilise **100**
   (`intents.py` I1) — incohérence à corriger. PROPOSITION : run A = 50 USDC (marge pour le cumul 24 h et
   les runs C).
3. **Q3 — USDC de la démo** : transfert = USDC **Circle** ; toute démo Aave = USDC **Aave** (jeton
   différent, robinet différent). Décider si la démo reste « transfert seul » en v1 (recommandé) — le swap
   et Aave sont v2.
4. **Q4 — Profondeur de confirmation en démo** : 2 blocs (proposition) ; ou basculer directement sur
   `safe`/`finalized` (disponible, vérifié) au prix de quelques secondes de plus.
5. **Q5 — Clés du Safe de démo (2/3)** : qui détient les 3 clés ? (Sécurité organisationnelle ; au moins
   deux personnes distinctes — sinon le « 2 sur 3 » est décoratif.)
6. **Q6 — Politique de reorg** : ré-émission automatique (si toujours ALLOW et non exécuté) ou escalade
   humaine systématique ? La proposition §c.4 fait les deux (auto borné, sinon humain) — à valider.
7. **Q7 — Spec `approve` borné** : montant exact vs approbation `2^256−1` (interdite) ; refus des
   approbations vers des contrats non allowlistés ; v1 = jamais exécuté (REQUIRE_APPROVAL) — à écrire pour
   v2.
8. **Q8 — Où vit le service signataire** (poste local pour la démo ; hébergement pour le produit) et qui
   peut le redémarrer — lié au K0 (pause hors-chaîne).
9. **Q9 — Ancrage EAS du dossier** (carte §6.3, statut REPORTÉ) : confirmer le report pour v1 ; le
   predeploy EAS est présent sur Base Sepolia (MESURÉ : code non vide à `0x42…0021`).
10. **Q10 — Preuve testnet et organisateurs** : V0.2 §10.5 laisse ouvert « les transaction hashes d'un
    testnet suffisent-ils ? ». Envoyer la question aux organisateurs **seulement après validation du
    message par l'utilisateur** (règle projet — aucun email autonome).

---

## Annexe A — Sources externes consultées (2026-10-15 sauf mention)

1. Zodiac Roles v2 — mécanique, déploiements, limites, matrice d'attaques : `research/W2C_enveloppe_execution.md`
   (rapport interne du 2026-10-15, lui-même adossé aux dépôts et docs officiels Gnosis Guild, ENS, karpatkey…).
2. AWS KMS — `CreateKey` (`ECC_SECG_P256K1`, « sign and verify messages ») :
   https://docs.aws.amazon.com/kms/latest/APIReference/API_CreateKey.html
3. Turnkey — portefeuilles d'entreprise, signature pilotée par politiques, clés en enclave, « AI agent
   wallets with policy-scoped signing » : https://docs.turnkey.com/solutions/company-wallets/overview
4. Coinbase CDP — sécurité des wallets serveur (TEE AWS Nitro, credentials P-256) :
   https://docs.cdp.coinbase.com/wallets/security-and-policies/security-overview ; annonce CDP Wallets
   (policy engine, latence < 200 ms) : https://coinbase.com/developer-platform/discover/launches/cdp-wallets-launch
5. Fordefi — API Signer (une part de MPC chez le client, signature sans humain) :
   https://docs.fordefi.com/developers/getting-started/set-up-an-api-signer
6. Fireblocks — comparatif des moteurs de politique (enclaves SGX, règles signées par quorum ; avertissement
   Safe sur les Guards) : https://fireblocks.com/report/compare-transaction-policy-engine ; suite Agentic
   Payments : https://www.fireblocks.com/blog/agentic-payments-suite-psp-fintech
7. Base — précompiles (`P256VERIFY`, RIP-7212, adresse `0x…0100`, Fjord/Azul) :
   https://docs.base.org/specifications/base-protocol/execution/precompiles ; calendrier des hardforks :
   https://docs.base.org/upgrades/overview
8. Aave — référentiel d'adresses Base Sepolia (`src/AaveV3BaseSepolia.sol`) :
   https://raw.githubusercontent.com/bgd-labs/aave-address-book/main/src/AaveV3BaseSepolia.sol
9. Uniswap v3 — adresses par chaîne (reprises du référentiel de la skill `evm-onchain-verification`,
   consulté 2026-10-15) : https://docs.uniswap.org/contracts/v3/reference/deployments/base-deployments
10. V0.2 — `C:\Users\User\fintechathon_recherche\orvyren_v02\ORVYREN_Document_de_reference_V0_2.docx`
    (§10.1–10.6 : intention, pipeline, niveaux T0–T4, modèle de sécurité, réseau/preuve, attestation).
11. Dépôt ORVYREN — `ARCHITECTURE_V1.md` §3 (contrats entre modules), `src/orvyren/execution/*.py`,
    `tests/test_execution.py`, `run_execution_demo.py`.

## Annexe B — Mesures RPC du 2026-10-15 (Base Sepolia, bloc 48 150 148 → 48 150 201)

- `eth_chainId` = `0x14a34` (84532) ; dernier bloc lu : 48 150 201 à **2026-10-15T12:51:30Z**.
- Gaz : `eth_gasPrice` = 0,006 gwei ; `baseFeePerGas` = 0,005 gwei ; `maxPriorityFeePerGas` = 0,001 gwei
  → un transfert ≈ 50 000 gaz ≈ **3 × 10⁻⁷ ETH**.
- Tags `safe` et `finalized` servis par `sepolia.base.org` (hashs retournés) — exploitables pour la
  politique de confirmations.
- Tailles de code mesurées (`eth_getCode`) : voir §b.2 (toutes présentes sauf mention contraire ;
  l'adresse Aave `0xE4C2330912aae4f84dfd0f6bc8de73e7d1d1b52d` → **0 o** : candidat deviné, écarté).
- Réserves Aave (6) et état de la réserve USDC décodés dans `raw_b5/b5_decoded_rpc.json`.
- Pools Uniswap : `liquidity()`, `slot0()`, quotes QuoterV2 — valeurs dans §b.2.
- `eth_getCode(0x42…0021)` (EAS) : code présent.

## Annexe C — Ce qui est resté « non trouvé » (à ne pas inventer)

1. **Date de publication du rapport grego.ai** (contournement MultiSend) — déjà « non trouvé » dans W2C ;
   non retesté ici.
2. **Coût des API KMS/enclave pour un usage agent** (AWS KMS, Turnkey, CDP, Fireblocks, Fordefi) : aucun
   tarif vérifié dans cette étude → **non trouvé** ; à chiffrer avant toute recommandation d'achat.
3. **SLA de la latence de signature** des options MPC/TEE (aucun chiffre vérifié ici, hors « < 200 ms »
   marketing CDP) — **non trouvé** (indépendant).
4. **Bonnes pratiques officielles Ethereum/Safe sur la profondeur de confirmation des L2** : aucun
   document normatif trouvé ; la proposition §c.3 s'appuie sur les tags `safe`/`finalized` mesurés.
5. **Fréquence/largeur des reorgs Base Sepolia** : aucune mesure ; hypothèse de reorgs courts (L2 à
   séquenceur unique) — **non mesuré**.
6. **Whether Uniswap v3 on Base Sepolia is officially « supported »** : la page de déploiement liste les
   adresses, mais aucune garantie de maintenance du testnet n'est publiée — « non trouvé ».

## Annexe D — Matière brute (`research/raw_b5/`)

| Fichier | Contenu |
|---|---|
| `rpc_b5_probe.sh` / `rpc_b5_probe_output.txt` | Sondes 1 : chainId, bloc, codes, pools USDC/WETH, réserve Aave, quote QuoterV2 |
| `rpc_b5_probe2.sh` / `rpc_b5_probe2_output.txt` | Sondes 2 : USDC d'Aave, symboles/décimales, pools Aave-USDC, réserves décodables, data provider |
| `rpc_b5_probe3.sh` / `rpc_b5_probe3_output.txt` | Sondes 3 : tags `safe`/`finalized`, gaz, quotes supplémentaires, EAS |
| `decode_rpc.py` / `decode_output.txt` / `b5_decoded_rpc.json` | Décodage (Python stdlib) des sorties : slot0, liquidity, quotes, réserves Aave (bits de configuration) |
| `keccak_selectors.py` / `keccak_selectors_output.txt` / `selectors_keccak.json` | Keccak-256 en Python pur (vecteurs validés) + calcul de tous les sélecteurs |
| `probe_selectors.py` / `probe_selectors_output.txt` | Vérification fonctionnelle des sélecteurs (SwapRouter02 `STF`, contrôle négatif) |
| `probe_roles_repay.py` / `probe_roles_repay_output.txt` | Module Roles (revert non-membre) + repay Aave + décodage `InvalidAmount()` |
| `probe_bytecode.py` / `probe_bytecode_output.txt` | Recherche des sélecteurs dans le bytecode du Pool Aave |
| `probe_bruteforce.py` / `probe_bruteforce_output.txt` | Brute force keccak : `0x4a0bfec1` = `NotAuthorized(address)` ; `repay` déployé = `0x573ade81` |
| `probe_final.py` / `probe_final_output.txt` | topic0 Transfer recalculé ; vues Aave ; supply |
| `SELECTEURS_VERIFIES.md` | **Table récapitulative des sélecteurs vérifiés** (méthode + résultats) |
| `aave_v3_base_sepolia_addressbook.sol` | Référentiel d'adresses Aave v3 Base Sepolia (source) |
| `aws_kms_createkey.html` / `fordefi_api_signer.html` | Pages sources archivées (B5) — AWS KMS `CreateKey`, Fordefi « API Signer » |

### Annexe E — Sélecteurs : la leçon de vérification

Trois hypothèses portées par les études amont se sont révélées fausses à la mesure, et sont corrigées dans
ce document : (i) `exactInputSingle` du SwapRouter02 est `0x04e45aaf`, pas `0x414bf389` (variante v1) ;
(ii) `repay` du Pool Aave Base Sepolia est `0x573ade81` = `repay(address,uint256,uint256,address)`, la
signature de la documentation étant absente du bytecode ; (iii) le revert d'un non-membre sur le module Roles
est `NotAuthorized(address)` (`0x4a0bfec1`), pas `NoMembership`. Tableau complet et méthode :
`raw_b5/SELECTEURS_VERIFIES.md`. **Conséquence pour le plan de démo** : chaque calldata de la démo est
construit depuis le sélecteur **mesuré**, et les scripts de vérification (§e.6, script 3) cherchent la
présence des sélecteurs dans le **bytecode déployé** avant d'envoyer quoi que ce soit.

*Tout est reproductible depuis `D:\orvyren_core` : les scripts de sonde sont dans `research/raw_b5/` et ne
nécessitent que `curl` et Python stdlib. Aucun commit n'a été fait (règle projet : l'orchestrateur committe).*
