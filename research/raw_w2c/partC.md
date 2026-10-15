
## (d) Architecture du signer limité

### d.1 Schéma textuel (flux d'une exécution T2)

```
                        ┌──────────────────────────────────────────────┐
   [1] LLM / planificateur  (jamais de clé, jamais de calldata signé)
        │  propose une INTENTION structurée (JSON, pas une tx)
        ▼
   [2] MOTEUR DE POLITIQUE  (hors LLM, déterministe, testable)
        │  entrées : intention + état local (quotas, nonces) + lecture chaîne
        │  sortie  : ALLOW | DENY + raison + hash d'intention
        │  ── PREMIER VERROU (c'est ici que vit le "non") ──
        ▼ (ALLOW seulement)
   [3] CONSTRUCTEUR D'APPEL   calldata = Roles.execTransactionWithRole(
        │                       to=USDC, value=0, data=transfer(dest,montant),
        │                       operation=CALL, roleKey=AGENT, shouldRevert=true)
        │  + simulation `eth_call` sur le RPC épinglé (pré-vol) → refus si revert
        ▼
   [4] REGISTRE D'INTENTIONS (anti-rejeu)   id = keccak(intention)
        │  refuse si id déjà exécuté/en vol ; réserve le quota local
        ▼
   [5] SIGNER ISOLÉ (processus séparé / matériel ; clé jamais en clair dans
        │  le LLM, les logs, le dépôt ; pas de droit d'administration)
        ▼  une signature ECDSA sur UNE transaction
   [6] RPC ÉPINGLÉ (chainId vérifié = 84532 / 8453 ; refus si autre)
        ▼
   [7] CHAÎNE : Safe (avatar) ← module Zodiac Roles v2  ── SECOND VERROU ──
        │  _authorize : rôle du signer ? cible autorisée ? fonction scopée ?
        │  conditions : destinataire ∈ liste blanche ; montant ≤ allowance ;
        │  allowance consommée seulement si l'exécution réussit
        ▼
   [8] EFFET ON-CHAIN (transfert USDC) + événements (ConsumeAllowance…)
        ▼
   [9] JOURNAL D'AUDIT (JSONL chaîné par hash, exportable)  ← opposition tiers
        + [10] SURVEILLANCE : seuils, alerte, PAUSE hors-chaîne ; la DAO garde
          le KILL SWITCH on-chain (revokeRoles / disableModule), 1 transaction
```

**Invariants** (à tester unitairement, cf. projet : `src/`, `tests/`) :
I1 le LLM ne voit jamais de clé ni ne signe ; I2 aucune exécution sans verdict ALLOW
tracé ; I3 l'agent ne possède aucun rôle d'administration (il ne peut pas modifier la
politique) ; I4 toute action exécutée a une entrée de journal vérifiable contre la chaîne ;
I5 le retrait du rôle par la DAO suffit à arrêter l'agent (aucune autre dépendance).

### d.2 Où vit la clé de l'agent

- **Membre de rôle = adresse dédiée** (EOA ; validé par Safe v1.4.1 `enableModule` sans contrôle
  `isContract`, cf. a.5 — et par le post-mortem qui distingue les membres EOA).
- **Isolation** : processus séparé (service de signature), clé chargée depuis un magasin de
  secrets/keystore chiffré ou un matériel ; **jamais** dans le contexte du LLM, jamais dans un log,
  jamais dans le dépôt (règle projet déjà posée par le skill `evm-onchain-verification` :
  « isolated signer that never enters a prompt, a log or the repo »).
- **Zéro privilège administratif** : le membre de rôle ne peut appeler ni `assignRoles`,
  ni `allowTarget`/`scopeFunction`, ni `setAllowance` (toutes `onlyOwner` = la Safe). **Test
  on-chain** de cette affirmation dans la matrice (#7).
- **Rotation** : changer d'agent = `assignRoles(nouvelle_adresse, [AGENT], [true])` +
  `assignRoles(ancienne, [AGENT], [false])` — 1 transaction DAO.

### d.3 Quotas côté agent, nonce, idempotence, gaz

- **Quotas locaux (premier verrou)** : plafond par transaction, **compteur glissant 24 h**
  (fenêtre glissante, pas calendaire — le calendaire est attaquable, cf. #2), par actif et par
  destinataire ; ces compteurs vivent dans le moteur de politique, pas dans le LLM.
- **Nonce** : nonce EOA standard pour l'unicité de la transaction ; mais **l'idempotence métier est
  une notion hors-chaîne** : `id = keccak(intention_normalisée)` dans un registre persistant
  (append-only). Rejouer la *même* intention renvoie un refus (« déjà exécutée »). Côté chaîne,
  l'amortisseur est `CallWithinAllowance` (quota d'appels) + les plafonds d'allowance.
- **Gaz** : l'agent paie son propre gaz (EOA membre) → il doit être **financé en ETH**. Options, par
  ordre de préférence : (i) testnet : robinet ; (ii) production : virement périodique depuis la
  trésorerie, lui-même borné (une permission « gas top-up » séparée, plafonnée, vers l'adresse de
  l'agent — jamais l'inverse) ; (iii) relais/paymaster (hors phase 1). Le montant de gaz est exclu
  du plafond métier : c'est une ligne budgétaire **distincte et surveillée**.
- **Simulation pré-vol** : `eth_call` du calldata exact sur le RPC épinglé avant signature ; un
  revert en simulation = pas de signature (évite de brûler du gaz et d'émettre un échec).

### d.4 Kill switch : qui, comment, en combien de temps

| Niveau | Action | Qui | Latence | Ce que ça arrête |
|---|---|---|---|---|
| K0 | **PAUSE hors-chaîne** (drapeau du service de signature) | ORVYREN (astreinte) | immédiat | Toute nouvelle signature de l'agent |
| K1 | **`assignRoles(agent, [AGENT], [false])`** (retrait du rôle) | Safe DAO (seuil de signatures) | 1 transaction ; sur Base ~2 s/bloc une fois signée — la latence réelle est la **coordination humaine** (minutes) | Toute exécution ultérieure du rôle par l'agent |
| K2 | **`disableModule(prev, rolesModule)`** | Safe DAO | idem K1 | Le module entier (tous les rôles de ce module) |
| K3 | Retrait des ETH de gaz / désactivation du financement | Safe DAO | idem | La capacité à payer le gaz (arrêt « par asphyxie ») |

**Ce qu'un kill switch ne peut pas faire** (à écrire honnêtement) : annuler une transaction **déjà
incluse** dans un bloc ; elle ne peut pas non plus empêcher une transaction déjà dans la mempool
d'être incluse si elle est séquencée avant la révocation. Sur Base (séquenceur centralisé, ordre
d'arrivée ~FIFO, pas d'enchère de priorité type marché de gaz L1), la protection pratique est :
délais courts entre décision et envoi, plafonds faibles, surveillance des intentions, et le fait
que **le dommage maximal par bloc est borné par l'allowance**. Ce raisonnement (« le pire cas est
un nombre connu ») est plus fort qu'une promesse d'annulation instantanée.

### d.5 Journal d'audit exportable

Format recommandé : **JSONL append-only, chaîné par hash** (`record_hash =
keccak(prev_hash || canonical_json(record))`), un enregistrement par étape :

```json
{"ts":"2026-10-15T12:00:01Z","intent_id":"0x…","kind":"INTENT","intent":{...},
 "policy":{"verdict":"ALLOW","rules":[{"id":"cap_tx_100","ok":true}],"policy_version":"v1.3"},
 "chain":{"id":84532,"rpc":"sepolia.base.org"},"nonce":17}
{"ts":"…","intent_id":"0x…","kind":"SIMULATION","ok":true,"gas_estimate":…}
{"ts":"…","intent_id":"0x…","kind":"SUBMIT","tx_hash":"0x…"}
{"ts":"…","intent_id":"0x…","kind":"RECEIPT","status":1,"block":48133012,
 "logs":[{"address":"0x036C…","topic0":"0xddf2…","from":"0x4F20…","to":"0x…","value":"50000000"}],
 "allowance_after":{"usdc_daily":"250000000"}}
{"ts":"…","intent_id":"0x…","kind":"VERIFY","recomputed_from_chain":true}
```

**Vérifiabilité par un tiers** (c'est ce qui rend le journal *opposable* et non déclaratif) :
1. chaque `tx_hash` est relisible via `eth_getTransactionReceipt` (statut, bloc, logs) ;
2. les logs `Transfer` (topic0 `0xddf252ad…`) sont recoupés avec l'intention (destinataire, montant) ;
3. l'état des allowances après coup est lisible dans le module Roles (ou via `ConsumeAllowance`) ;
4. la chaîne de hash détecte toute réécriture du journal ;
5. la politique appliquée est identifiée par `policy_version` (le texte de politique est versionné).

---

## (e) Matrice des 12 attaques

Légende des contrôles : **P** = politique hors-chaîne (premier verrou, déterministe) ·
**C** = chaîne (module Zodiac / Safe) · **N** = nonce/registre d'intentions · **M** = surveillance
et processus (humain/ops) · **S** = secret/signer isolé.
« Test qui le prouve » = test reproductible sur Base Sepolia (ou test unitaire quand la chaîne ne
peut pas être mise en cause).

| # | Attaque | Vecteur concret | Contrôle qui l'attrape | Test qui le prouve |
|---|---|---|---|---|
| 1 | **Rejeu d'intention** | Le même calldata signé/envoyé deux fois (retry réseau, duplication, copie par un tiers) | **N** (registre `intent_id`) + **C** (nonce EOA : la 2ᵉ tx avec le même nonce est rejetée ; si le nonce a avancé, l'allowance a déjà été débitée) | Test : soumettre 2× la même transaction signée brute → la 2ᵉ est rejetée (`nonce too low`) ; et 2× la même *intention* → refus P « déjà exécutée », aucune tx émise |
| 2 | **Frontière de période (dépense 2×)** | Dépenser le solde juste avant le rafraîchissement puis à nouveau juste après : jusqu'à **`maxRefill + refill`** sur deux blocs (arithmétique : `elapsedIntervals = (now − ts)/period`, `balance += refill × elapsedIntervals`, plafond `maxRefill` — code `AllowanceTracker.sol`) | **P** (compteur **glissant** 24 h ≠ fenêtre calendaire) + **M** (alerte) ; **C** borne le montant unitaire mais **ne détecte pas** la rafale | Test : avec `refill=100, maxRefill=100, period=86 400`, dépenser 100 à T−1 s de la frontière puis 100 à T+1 s → **la chaîne accepte les deux** ; le compteur glissant hors-chaîne refuse la seconde (journal : DENY `rolling_24h_300`). Ce test documente la limite on-chain au lieu de la nier |
| 3 | **Révocation pendant une exécution en cours** | La DAO révoque pendant qu'une tx de l'agent est en vol / dans la mempool | **C** (la révocation bloque tout ce qui n'est pas encore exécuté) + **M** (surveillance des intentions) | Test : envoyer une tx agent qui traîne (gaz faible) puis, dans le même intervalle, exécuter `assignRoles(...,false)` depuis la Safe → la tx de l'agent **revert** (`NoMembership`) alors que la révocation est confirmée. Variante à documenter : si la tx agent est incluse *avant* la révocation, elle s'exécute — d'où le plafond faible |
| 4 | **Manipulation d'oracle de prix** | Faire exécuter un swap à un prix absurde (oracle manipulé, pool piégé, route empoisonnée) | **P** (bornes de prix hors-chaîne : prix de référence multi-venues, écart max) + **C** (conditions sur les paramètres : `EqualToAvatar` sur receveur, `GreaterThan` sur `minOut`, portée sur la fonction exacte du routeur) | Test : intention de swap dont `minOut` est inférieur au seuil → **P refuse** (aucune signature). Test chaîne : poster un calldata avec `minOut=0` sur une fonction autorisée mais dont la condition exige `minOut > seuil` → revert. Rappel : **la chaîne ne connaît pas les prix** ; ne jamais prétendre le contraire |
| 5 | **Calldata mal décimé** | Décalage de décimales (6 vs 18), unités, ou **rembourrage ABI** exploité par un lot (bug MultiSend réel : 1 à 31 octets de fin divergents) | **P** (canonicalisation + validation de schéma avant signature, conversion décimale testée) + **C** (conditions sur montants) + **M** (contrôle post-exécution) | Test unitaire : `155.0 → 155000000` vs `155000000000000000000` — un débit de 1 000 000× est refusé par le plafond. Test chaîne : reproduire le motif du rapport grego.ai (calldata forgé dont les derniers octets diffèrent) sur un module **à jour** → refus ; et vérifier le SHA/commit du `MultiSendUnwrapper` déployé **avant** la démo |
| 6 | **Mauvaise chaîne au niveau RPC** | Le client pointe une autre chaîne (testnet/mainnet, fork, RPC menteur) : l'agent « exécute » ailleurs, ou lit un état faux | **P/C** (épinglage `chainId` : refus si ≠ 84532 en test / ≠ 8453 en prod ; adresses vérifiées par chaîne) + **M** | Test : configurer un RPC Ethereum mainnet → le pré-vol refuse (`chain_id_mismatch`), aucune signature ; test symétrique : recevoir une tx signée pour 8453 et vérifier qu'elle est rejetée par le RPC/la politique |
| 7 | **Tentative de changement d'allowlist par l'agent** | L'agent (ou un attaquant qui a sa clé) appelle `allowTarget`, `scopeFunction`, `setAllowance`, `assignRoles`, `enableModule` | **C** : ces fonctions sont `onlyOwner` (la Safe), le membre du rôle n'a **aucun** pouvoir d'administration | Test : depuis l'adresse agent, `eth_call` puis tx réelle sur `Roles.allowTarget(...)` et `Safe.enableModule(attaquant)` → revert (`OwnableUnauthorizedAccount`/`GS` *) ; journaliser les deux reverts |
| 8 | **Dépassement cumulé** | Multiplier les petites transactions pour dépasser le plafond journalier | **C** (`WithinAllowance` débite à chaque exécution réussie) + **P** (compteur glissant) + **N** | Test : boucle de 4 × 100 USDC avec plafond 300/jour → les 3 premières passent, la 4ᵉ **revert** on-chain (`AllowanceExceeded`), et le compteur hors-chaîne l'aurait refusée avant signature |
| 9 | **Permission expirée** | Faire exécuter un mandat dont la durée est écoulée (personne n'a révoqué) | **P** (date d'expiration dans la politique hors-chaîne, refus) + **M** (tâche planifiée de révocation) ; **la chaîne n'a pas d'expiration native** (pas de champ `expiry` dans `Allowance` — vérifié dans le code) | Test : fixer une expiration à T ; après T, une intention valide par ailleurs est refusée par **P** ; **et** exécuter le calldata directement depuis la clé agent → il **passe encore** (limite assumée, à documenter) ; puis vérifier que la révocation planifiée l'arrête |
| 10 | **Sandwich / slippage** | Extraction de valeur autour du swap de l'agent (MEV) ; l'agent subit un prix dégradé | **P** (borne de slippage explicite, prix de référence, taille maximale par rapport à la profondeur du pool) + **C** (conditions `GreaterThan`/`LessThan` sur les paramètres, receveur = avatar comme dans l'exemple Balancer des docs) | Test : simulé — fixer une borne de slippage, soumettre une intention qui l'excède → refus P ; sur chaîne, un calldata dont `minOut` viole la condition → revert. (Testnet : profondeur non représentative → le test de qualité d'exécution se fait en simulation, cf. skill : « Testnet prices are not market data ») |
| 11 | **Clé d'agent compromise** | Vol de la clé du signer (poste, dépendance, fuite de log) | **C** (le périmètre du rôle **est** la borne : cibles, fonctions, paramètres, destinataires, allowances) + **P/N** côté attaquant s'il n'a pas le registre + **M** (détection de motif anormal → pause + révocation) | Test rouge (red team, clé volontairement utilisée hors politique) : (i) 500 USDC au-delà du plafond → revert ; (ii) transfert vers une adresse hors liste → revert ; (iii) appel admin → revert ; (iv) drain complet de la Safe → **impossible** (le rôle ne le permet pas). Résultat à écrire : « l'attaquant obtient au plus `maxRefill` par période, uniquement vers les destinataires autorisés » |
| 12 | **Inscription d'un destinataire non autorisé** | Faire ajouter/employer une adresse de destination pirate (nouveau destinataire « approuvé » injecté, ou contrat malveillant en bout de chaîne) | **C** (condition de liste blanche sur l'adresse de destination) + **P** (liste des bénéficiaires figée par mandat) + **M** | Test : intention vers une adresse non listée → **P refuse** ; forcer le calldata depuis la clé agent → **revert** (condition de destinataire). Test complémentaire : tenter de modifier la liste = #7 (impossible) |

\* Le nom exact du revert dépend de la version du module/Safe ; le test doit journaliser le
sélecteur constaté, pas un nom supposé.

### e.1 Les trois attaques les plus « convaincantes » pour un jury (à jouer en démo)

1. **#5 calldata mal décimé** : c'est l'erreur la plus banale et la plus destructrice ; la démo
   montre un refus *avant* signature **et** un revert *si on force*.
2. **#11 clé compromise** : le seul scénario où l'on accepte que l'attaquant *ait* la clé — et la
   démonstration que le pire cas est un nombre fini, vers des destinataires autorisés.
3. **#2 frontière de période** : le jury technique y voit de la rigueur (limite on-chain reconnue et
   couverte par le premier verrou), pas une faiblesse cachée.

---
