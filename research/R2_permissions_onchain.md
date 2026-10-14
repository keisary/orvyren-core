# R2 — Permissions on-chain pour agents : état réel (octobre 2026)

**Projet** : ORVYREN-Core — concours FinTech Shenzhen 2026 (International Track), thème F « Agent Wallet / Autonomous On-chain Wallet ».
**Date de rédaction** : 14 octobre 2026 (UTC). **Vérifié le** : 14 octobre 2026, 22:35 UTC.
**Objet** : passer d'un modèle « instruction non signée + vérification du reçu » à une architecture réelle de **délégation bornée on-chain**, déployable en testnet, défendable devant un jury.

**Méthode** : les faits marqués ✅ ont été vérifiés *par appel RPC direct* sur Base Sepolia (chainId 84532 / `0x14a34`) le 14/10/2026 via `https://sepolia.base.org` (voir §10 pour reproduire). Les faits marqués 📄 proviennent de sources primaires (specs EIP, dépôts GitHub, docs officielles) avec URL et date d'accès. Les faits marqués ⚠️ proviennent de sources secondaires (blogs, agrégateurs) non recoupées par une source primaire. **Aucune affirmation n'est inventée : quand l'information n'a pas été trouvée, c'est écrit « non trouvé ».**

---

## 0. Résumé exécutif (à lire si vous ne lisez que 20 lignes)

1. **ERC-7715 est vivant mais toujours en `Draft`** en octobre 2026. Sa forme actuelle définit `wallet_requestExecutionPermissions` (+ `wallet_revokeExecutionPermission`, `wallet_getSupportedExecutionPermissions`, `wallet_getGrantedExecutionPermissions`) ; le couple `wallet_grantPermissions`/`wallet_requestExecutionPermissions` que citent certains articles 2026 est un **alias historique** : la spec à jour utilise `wallet_requestExecutionPermissions`. 📄
2. **L'implémentation de référence est MetaMask** (Advanced Permissions, lancées le 6 avril 2026, dans le Smart Accounts Kit). La spec de *permission* (ERC-7715) est côté wallet ; le *contrat* qui l'exécute est ERC-7710 (DelegationManager + caveat enforcers). 📄
3. **Base Sepolia est supporté** par MetaMask Smart Accounts Kit depuis la v1.5.0 (kit actuel : v2.0.0), pour les smart accounts **et** pour les Advanced Permissions. ✅📄 Vérifié on-chain : le `DelegationManager` v1.3.0 (`0xdb9B…7dB3`), `SimpleFactory`, et les caveat enforcers utiles (`ERC20PeriodTransferEnforcer`, `ERC20TransferAmountEnforcer`, `TimestampEnforcer`, `AllowedTargetsEnforcer`) sont **déployés** sur Base Sepolia (bytecode non vide, tailles relevées).
4. **Coinbase Spend Permissions** est l'alternative la plus *simple à automatiser* (API serveur, pas d'extension navigateur) : `SpendPermissionManager` = `0xf85210B21cC50302F477BA56686d2019dC9b67Ad`, **vérifié déployé sur Base Sepolia** (12 610 octets de runtime — taille identique à celle relevée sur les 8 mainnets par un audit indépendant), audité par Spearbit/Cantina (3 campagnes 2024 + 2 pour SpendRouter en 2026). ✅📄⚠️
5. **Safe Allowance Module** : code audité (audit d'origine octobre 2020, versions v0.1.0/v0.1.1 « released »), mais **PAS déployé sur Base Sepolia** — vérifié on-chain : `eth_getCode` renvoie `0x` pour `0xCFbFaC74…` et `0x1Fb40383…` sur 84532. L'utiliser imposerait de déployer nous-mêmes le module (code audité, **déploiement non audité**). ✅📄
6. **ZeroDev/Kernel** (ERC-7579, permissions composables) supporte Base Sepolia ✅📄 et tous ses contrats/plugins sont annoncés audités (Kalos, ChainLight — rapports présents dans le dépôt `zerodevapp/kernel`, branche `main`) 📄 ; une limitation connue est documentée dans le README (TOB-KERNEL-3 : la révocation n'est pas rétroactive dans le même bundle). 📄
7. **x402** n'est **pas** un système de permission : c'est un rail de paiement HTTP (402 + signature EIP-3009, règlement USDC). Deux pièges majeurs documentés : (a) les SDK clients plafonnent à **1 $ par paiement par défaut** et **ne tiennent aucun cumul** ; (b) le `SpendPermissionManager` de Coinbase **ne connaît pas x402** (zéro occurrence dans le monorepo x402). ⚠️ Un papier 2026 décrit **cinq attaques pratiques** contre x402 (autorisation, binding, anti-rejeu, couche web) testées notamment sur Base Sepolia. 📄
8. **AP2** (Google, sept. 2025) a été **donné à la FIDO Alliance en avril 2026** ; il définit des *mandates* signés (Verifiable Digital Credentials : Intent Mandate, Cart Mandate) — c'est une couche **autorisation/consentement**, pas d'exécution on-chain ; adoption précoce. 📄⚠️
9. **Recommandation ORVYREN** : enveloppe **ERC-7715** (`erc20-token-periodic` : 300 USDC / 86 400 s + règle `expiry` à +24 h) sur Base Sepolia via MetaMask, **doublée** d'une policy hors chaîne (100 USDC/tx, allowlist destinataire, idempotence `intent_id`), avec **fallback Coinbase Spend Permissions** si l'octroi navigateur est un risque le jour J. Démo : un ALLOW, un DENY *par la policy* (0 gaz) et un DENY *par la chaîne* (revert traçable BaseScan), plus une révocation. Détail §7.
10. **Ce qu'on ne peut pas dire** : « standard finalisé », « audité » (sans qualifier), « autonome sans clé », « fonds réels », « rendement ». Détail §9. Rappel réglementaire : le 6 février 2026, la PBOC et plusieurs autorités chinoises ont **étendu l'interdiction crypto aux stablecoins et à la tokenisation d'actifs réels** (📄 loc.gov) — la démo doit rester strictement testnet, sans émission de jeton ni promesse d'investissement.

---

## 1. Le problème posé à ORVYREN

État actuel (documenté dans `ARCHITECTURE_V1.md`, `.env.example`, `src/orvyren/policy/`) :

- l'agent **ne détient aucune clé** : il produit une instruction non signée (calldata ERC-20 exact), un humain exécute, l'agent **vérifie le reçu** (décodage du log `Transfer`, contrôle émetteur/destinataire/montant/contrat) ;
- policy déterministe hors LLM : Base Sepolia **84532**, USDC de test `0x036CbD53842c5426634e7929541eC2318f3dCF7e`, destinataire allowlisté, **100 USDC/tx**, **300 USDC cumulés**, **TTL 24 h**, idempotence par `intent_id` ;
- le thème imposé au concours est littéralement « **Agent Wallet** ».

La question de R2 : **quelle couche de permission on-chain est réelle, déployable en testnet aujourd'hui, et quelle revendication est honnête ?** La réponse doit permettre de dire au jury : « l'agent n'est pas un script qui demande gentiment ; son autorité est un objet on-chain borné, révocable, et le dépassement est refusé par le contrat ».

---

## 2. ERC-7715 — la spec en détail

### 2.1 Méthodes (spec à jour, consultée le 14/10/2026)

Source : 📄 <https://eips.ethereum.org/EIPS/eip-7715> (« Request Permissions from Wallets », statut **Draft**, créé 2024-05-24, auteurs MetaMask/Consensys + co-auteurs, `Requires: EIP-4337, EIP-7710`), consulté le 14/10/2026.

| Méthode | Rôle |
|---|---|
| `wallet_requestExecutionPermissions` | Le dapp/agent **demande** une permission ; le wallet affiche, l'utilisateur approuve/modifie. |
| `wallet_getGrantedExecutionPermissions` | Liste des permissions **accordées et non révoquées**. |
| `wallet_getSupportedExecutionPermissions` | Types de permissions/rules supportés par le wallet (avec `chainIds`). |
| `wallet_revokeExecutionPermission` | **Révocation** (`permissionContext` en entrée). |

> ⚠️ Point de vigilance pour la rédaction du dossier : plusieurs articles 2026 (Relay, 17/04/2026 ; Eco) écrivent `wallet_grantPermissions`. **La spec EIP-7715 actuelle ne définit pas cette méthode** — c'est un nom d'API côté SDK/`viem` (`grantPermissions`) historiquement associé à l'implémentation MetaMask. Le nom à citer dans un dossier technique est **`wallet_requestExecutionPermissions`** (source primaire).

### 2.2 Forme de la requête et de la réponse

```
PermissionRequest = {
  chainId: Hex,                 // EIP-155 (ex. 0x14a34 pour Base Sepolia)
  from?: Address,               // compte cible (optionnel)
  to: Address,                  // "session account" du dapp/agent
  permission: { type, isAdjustmentAllowed, data },
  rules?: [{ type, data }]      // ex. { type:"expiry", data:{timestamp} }
}
PermissionResponse = PermissionRequest & {
  context: Hex,                 // "permissionsContext" opaque (ERC-7710)
  dependencies: [{ factory, factoryData }],   // comptes à déployer si non déployés
  delegationManager: Address
}
```

Points structurants :

- **Une seule signature utilisateur** ouvre droit à N exécutions *dans l'enveloppe* ; l'utilisateur peut être absent au moment de l'exécution (cas agent).
- `isAdjustmentAllowed` : le wallet peut **atténuer** (réduire ou augmenter) la demande pour refléter les conditions de l'utilisateur — donc **la réponse n'est pas garantie égale à la demande**. Le code de l'agent doit **relire la permission accordée** et travailler sur la valeur *réellement accordée*, jamais sur la valeur *demandée*.
- `dependencies` : si le compte n'est pas déployé, le dapp **doit** déployer via `factory`+`factoryData` pour que la permission soit rachetable.
- **Rédemption (ERC-7710)** : appel à `redeemDelegations(bytes[] _permissionContexts, bytes32[] _modes, bytes[] _executionCallData)` sur le `delegationManager`, avec les `Execution{target, value, callData}` encodés selon ERC-7579 (mode `SingleDefault` = `0x00…00`). 📄 <https://eips.ethereum.org/EIPS/eip-7710>, consulté le 14/10/2026.
- **Types de permissions** : la spec **n'est pas exhaustive par construction** (« a permission or rule type is valid as long as both the DApp and the wallet are willing to support it »), chaque nouveau type devant être défini dans un ERC dédié et hériter de `BasePermission`/`BaseRule`. Le seul type *explicitement* illustré dans l'EIP est `native-token-allowance` + règle `expiry`.

### 2.3 Types réellement implémentés par MetaMask (source primaire, 14/10/2026)

📄 <https://docs.metamask.io/smart-accounts-kit/development/get-started/supported-advanced-permissions/> + <https://docs.metamask.io/smart-accounts-kit/development/reference/advanced-permissions/permissions/>

| Type | Kit ≥ | Extension MetaMask ≥ | Paramètres (résumé) |
|---|---|---|---|
| `erc20-token-allowance` | v1.4.0 | >= v13.32.1 | `tokenAddress`, `allowanceAmount`, `startTime?`, `justification?` — plafond **total** (pas de reset) |
| `erc20-token-periodic` | v0.1.0 | >= v13.23.0 | `tokenAddress`, `periodAmount`, `periodDuration` (**secondes**), `startTime?` — **reset à chaque période** |
| `erc20-token-stream` | v0.1.0 | >= v13.23.0 | `amountPerSecond`, `initialAmount?`, `maxAmount?` — déblocage **linéaire** |
| `native-token-allowance` / `periodic` / `stream` | idem | idem | équivalents pour le token natif (ETH) |
| *Token approval revocation* | v1.6.0 | — | révocation d'approbations ERC-20 |

C'est **exactement** la famille de contraintes dont ORVYREN a besoin : montant par période, période en secondes, date de départ, plus les règles (`expiry`, `limited-calls`, etc. — la liste exhaustive des rules n'a pas été extraite ici : *non trouvée*).

### 2.4 Où c'est déployé / qui l'implémente

- **MetaMask** : Advanced Permissions = produit lancé le **6 avril 2026** (📄 <https://metamask.io/news/introducing-advanced-permissions>). Support **Base Sepolia** pour Smart Accounts *et* Advanced Permissions depuis la **v1.5.0** du kit (kit actuel **v2.0.0**) ; mainnets : Base, Ethereum, Polygon, Arbitrum, Optimism, BSC, Berachain, Linea, Monad, Sei, Sonic, Unichain, Gnosis, Citrea… (📄 <https://docs.metamask.io/smart-accounts-kit/development/get-started/supported-networks/>).
- **Polygon** : « ERC-7715 is now live on Polygon » annoncé par le compte officiel Polygon (⚠️ tweet `x.com/0xPolygon/status/2041550102917963908`) ; plusieurs sources secondaires datent la mise en service d'**avril 2026** (⚠️ Relay, 17/04/2026 ; Eco, avril 2026).
- **Coinbase** : implémente le *même modèle* (spender délégué + plafond période) via **Spend Permissions**, mais **pas** via l'API JSON-RPC 7715 (📄 docs CDP + README du dépôt — voir §3.3).
- **Rhinestone / Biconomy** : modules de session keys composables (7579), formats propriétaires ; Biconomy **ne revendique pas** le support ERC-7715 (📄 Eco, avril 2026).
- **Viem** expose des actions typées ERC-7715 (📄 <https://viem.sh/experimental/erc7715/grantPermissions>).

### 2.5 Ce qui est audité — et ce qui ne l'est pas

- Les **contrats** de la pile MetaMask (Delegation Framework : `DelegationManager`, DeleGator, caveat enforcers) : dossiers d'audit présents dans le dépôt (`MetaMask/delegation-framework/audits/` → **Cyfrin** et **Consensys Diligence**), vérifié via l'API GitHub le 14/10/2026. 📄
- La **spec ERC-7715** n'a pas d'audit de sécurité (c'est une spec) ; ses **considérations de sécurité** sont explicites : le wallet **doit** afficher et alerter, le dapp doit demander le minimum et une expiration raisonnable. 📄
- **Non trouvé** : audit public du *handler* de permissions de l'extension MetaMask (Permissions Snap) lui-même ; statistiques de permissions ERC-7715 réellement accordées en production.

### 2.6 Limites et pièges d'ERC-7715

1. **Draft** : noms de méthodes/types/règles et sémantique peuvent changer. Toute intégration doit être isolée derrière une **couche d'adaptation** (`permissions/erc7715_adapter.ts` côté script d'exécution, jamais dans le moteur de décision).
2. **Le dapp doit gérer l'atténuation** : relire `getGrantedExecutionPermissions` et **recalculer** l'enveloppe effective ; ne jamais coder en dur la valeur demandée.
3. **Pas de garantie multi-chaîne** : `chainId` unique par permission (base par base).
4. **Dépendance à un wallet compatissant** : un wallet pourrait accorder moins (ou l'inverse si `isAdjustmentAllowed=true`) ; l'agent doit refuser d'exécuter si l'enveloppe accordée est **inférieure** à ce que la policy exige (sinon on découvre le problème en cours de route).
5. **Phishing** : la spec elle-même reconnaît qu'un dapp malveillant peut demander large ; l'affichage wallet est la dernière ligne de défense humaine — argument à réutiliser dans le dossier (le *human-in-the-loop* n'est pas une faiblesse, c'est le point d'ancrage du consentement).

---

## 3. Modules alternatifs et matures (état + preuves)

### 3.1 Safe (Allowance Module / modules)

- **Rôle** : module installé sur un Safe qui autorise un **delegate** à transférer jusqu'à un montant par période (token par token). C'est l'ancêtre historique du modèle « allowance on-chain ».
- **Audits** : 📄 la fondation Safe publie les rapports **Allowance Module v0.1.0, v0.1.1, v1.0.0** (<https://docs.safefoundation.org/security/audits>, consulté 14/10/2026) ; le dépôt `safe-modules` contient `modules/allowances/docs/AllowanceModuleAuditOct2020.md` (audit d'origine, oct. 2020).
- **Déploiements** : 📄 `safe-global/safe-modules-deployments` — v0.1.0 : **15 réseaux** dont Ethereum (1), Base (8453), Gnosis (100), Polygon (137, adresse différente), Ethereum Sepolia (11155111) ; v0.1.1 : **54 réseaux**. **Base Sepolia (84532) est absent des deux listes.**
- **Vérification on-chain (faite ici)** : ✅ sur Base Sepolia, `eth_getCode(0xCFbFaC74C26F8647cBDb8c5caf80BB5b32E43134)` = `0x` (**non déployé**) ; idem pour l'adresse Polygon `0x1Fb403834C911eB98d56E74F5182b0d64C3b3b4D`. En revanche, le **Safe lui-même existe** sur Base Sepolia — ✅ `SafeL2 v1.4.1` `0x29fcB43b46531BcA003ddC8FCB67FFE91900C762` (24 421 octets) et `SafeProxyFactory v1.4.1` `0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67` → voir liste exacte §10.
- **Portée** : le module gère **un token + une période** par delegate ; il ne contraint ni la cible, ni la méthode, ni le calldata. La révocation se fait via `removeDelegate`/`setAllowance(0)` (transaction Safe). Détail exhaustif : *non audité ici* (code lu seulement par extraits).
- **Prix d'entrée ORVYREN** : il faudrait **déployer le module nous-mêmes** sur 84532 → « code audité, déploiement non audité », plus une étape Safe (enableModule) — coût réel plus élevé que MetaMask pour un bénéfice de portée *inférieur*.

### 3.2 ZeroDev Kernel (session keys / permissions composables)

- **Rôle** : smart account **ERC-7579** ; les « permissions » composent **1 signer + n policies** (spending limits, time windows, target allowlists, selectors). Le module est un *validator*, donc une permission est vérifiée **dans** la validation du UserOp — le modèle le plus proche d'un « compte agent » programmable.
- **Audits** : 📄 « All ZeroDev contracts and plugins are audited unless otherwise noted » (<https://docs.zerodev.app/api-and-toolings/faqs/audits>) ; rapports présents dans `zerodevapp/kernel` branche `main` : `chainlight_v3_0.pdf` (ChainLight), `kalos_v3_plugins.pdf`, `kalos_v1/v2_1/v2_2`, `kalos_webauthn_v1`, `kalos_recovery_v1/v2` (Kalos) — liste obtenue via l'API GitHub le 14/10/2026.
- **Limite connue, documentée par l'équipe** : 📄 README du dépôt — *TOB-KERNEL-3, acknowledged* : la révocation d'un validator dans un même bundle n'invalide pas un UserOp déjà validé (équivalent à ordonner la révocation après la transaction de l'attaquant). À connaître si on joue la carte « révocation immédiate ».
- **Testnet** : ✅📄 Base Sepolia (84532) figure dans les « Supported Networks » ZeroDev (<https://docs.zerodev.app/api-and-toolings/faqs/chains>, consulté 14/10/2026). *(Un candidat d'adresse de factory Kernel a bien renvoyé du code sur 84532, mais son identité n'a pas été confirmée ici → non affirmé.)*
- **Coût d'intégration** : moyen-élevé (SDK `@zerodev/*`, comptes, policies à écrire ou réutiliser ; « you can write your own permissions »).

### 3.3 Coinbase Spend Permissions (Base Account / CDP)

- **Rôle** : un `spender` (l'agent) peut prélever jusqu'à `allowance` par `period`, de `start` à `end`, sur un token donné, via un **singleton qui est owner du smart account**. Le contrat **n'accepte que native + ERC-20** et **rejette les calls externes arbitraires** (c'est un choix de sécurité assumé, pas une limite accidentelle). 📄 README du dépôt.
- **Structure** : `SpendPermission{account, spender, token, allowance(uint160), period(uint48), start, end, salt, extraData}` — signature **EIP-712**, domaine « Spend Permission Manager » v1 ; approbation possible via signature **ERC-6492** (permission signable avant déploiement du compte). 📄 README + `docs/SpendPermissionAccounting.md`.
- **Comptabilité** : un `PeriodSpend{start,end,spend}` par hash de permission ; `_useSpendPermission` additionne et **revert `ExceededSpendPermission(value, allowance)`** au dépassement ; **reset au changement de période** (frontières fixes `start + n*period`, donc **jusqu'à 2× le budget en quelques secondes autour d'une frontière** — c'est documenté et ce n'est **pas** un rate-limit). **Pas de plafond par transaction.** 📄 (docs du dépôt) + ⚠️ analyse indépendante (llm4agents, « Auditing Spend Permissions », citant le contrat de 776 lignes et des relevés on-chain).
- **Audits** : 📄 tableau du README (vérifié le 14/10/2026) — Spearbit via Cantina : *private audit 1* 29/10/2024, *public competition* 11/2024, *private audit 2* 10/12/2024 ; SpendRouter : 18/03/2026 et 21/03/2026.
- **Déploiements** : 📄 README — `SpendPermissionManager` `0xf85210B21cC50302F477BA56686d2019dC9b67Ad`, testnets **Base Sepolia**, Optimism Sepolia, Ethereum Sepolia ; 8 mainnets. ✅ **Vérifié ici sur Base Sepolia** : bytecode présent, 12 610 octets — valeur **identique** à celle relevée sur les 8 mainnets par l'analyse indépendante (byte-diff documenté : 34 octets différents, domaine EIP-712 + chain-id). ⚠️
- **API serveur** : 📄 CDP — `createSpendPermission` / `listSpendPermissions` / `useSpendPermission` / `revokeSpendPermission`, `getCurrentPeriod` (renvoie start/end/spend courant) ; `network: "base-sepolia"`, raccourcis `"usdc"`/`"eth"` sur Base et Base Sepolia. **C'est la voie la plus « scriptable »** : pas d'extension navigateur, clé serveur.
- **Usage réel observé** (⚠️ analyse indépendante citant Base, fenêtre ~18–25/08/2026) : 547 `SpendPermissionUsed`, 368 `SpendPermissionApproved`, 13 `SpendPermissionRevoked` ; 351 permissions, 231 comptes, 331 spenders ; 492/547 spends en USDC pour **15 236,45 USDC** (~31 USDC/spend). **Ratio 331 spenders / 351 permissions ⇒ un spender dédié par permission** — le motif exact d'un agent/session.

### 3.4 Biconomy (Smart Sessions / Nexus) et Rhinestone

- **Biconomy** : 📄 Smart Sessions = délégation d'un signer à un autre, avec **policies** (contrats autorisés, fonctions autorisées, plafonds, fenêtres) ; docs « Contracts & Audits » référencent des audits (Pashov Review, Nexus audits via Cantina/Spearbit ; ⚠️ tweet Biconomy sur les audits Spearbit/Cyfrin). **Rapports non lus ici → contenu des audits : non vérifié.**
- **Rhinestone** : 📄 `module-sdk` documente session keys, transfers planifiés, policies ; modules déployés sur Base/Optimism/Arbitrum (⚠️ Eco, avril 2026). **État d'audit précis : non trouvé** dans le temps imparti.

### 3.5 MetaMask **Agent Wallet** (produit, distinct de la primitive)

📄 <https://docs.metamask.io/agent-wallet/> (consulté 14/10/2026) : CLI `mm` self-custodial pour agents, avec **outflow policy** (plafond glissant **24 h** de valeur sortante, 2FA au dépassement), **Guard Mode** (allowlist d'adresses), simulation + *threat scanning* Blockaid, MEV-protection, couverture « Transaction Protection » jusqu'à 10 000 $/mois. **Base Sepolia figure dans les réseaux supportés du CLI** (📄 supported-chains). Limites assumées : l'outflow **n'est pas** fiable si les transactions ne passent pas par leur backend, et les **signatures (Permit2) ne sont pas comptées**. → À citer comme **convergence produit** (« en 2026, le motif "agent + plafond glissant 24 h + allowlist" est exactement ce que livrent les grands wallets »), et non comme primitive à intégrer.

---

## 4. Paiements machine : x402, AP2, Circle, paymasters

### 4.1 x402 — ce que c'est, ce que ce n'est pas

- **Mécanique** : HTTP `402 Payment Required` + en-tête `X-PAYMENT` ; signature **EIP-3009** (`transferWithAuthorization`) côté client, vérification/règlement par un **facilitateur** (référence `x402.org/facilitator`, producteur `api.cdp.coinbase.com/platform/v2/x402`) ; USDC, surtout sur Base. 📄 docs/README x402 ; ⚠️ synthèses 2026.
- **Adoption (⚠️ sources secondaires, non recoupées)** : open-sourcé par Coinbase en mai 2025 ; **x402 Foundation sous la Linux Foundation** (Cloudflare, Stripe, AWS, Google) début 2026 ; intégration Stripe (fév. 2026) ; adoption **AWS Bedrock AgentCore** (mai 2026) ; chiffres cumulés ~**161,32 M** de paiements / **43,57 M$** réglés (mai 2026). À citer comme « momentum », **pas** comme preuve de robustesse.
- **Failles publiées** : 📄 *Five Attacks on x402 Agentic Payment Protocol* (arXiv **2605.11781**) — cinq attaques pratiques (autorisation, binding, anti-rejeu, traitement web), testbed sur chaînes locales **et Base Sepolia** + trois SDK open-source, avec mitigations proposées. → matière idéale pour montrer au jury qu'on **ne confond pas hype et sécurité**.
- **Le point qui compte pour ORVYREN** : ⚠️ les contrôles de dépense x402 sont **côté client** (défaut **1 $/paiement**) et **sans cumul** ; le budget on-chain (SpendPermissionManager) **ne connaît pas** x402 (aucune occurrence de `SpendPermissionManager` dans le monorepo x402 au 25/08/2026). Conclusion : **un paiement machine robuste = rail (x402) + budget on-chain (permission)** — exactement l'architecture à deux niveaux d'ORVYREN.

### 4.2 AP2 — mandats signés, désormais chez FIDO

- 📄 Google Cloud (announcement) : **AP2** = protocole de coordination des paiements agentiques ; cœur = **mandates** = Verifiable Digital Credentials signés par l'utilisateur (**Intent Mandate** — tâche déléguée sans humain présent, avec plafonds/conditions ; **Cart Mandate** — panier/commande). Signature **ECDSA**, preuve de consentement durable et vérifiable — **rail-agnostique** (cartes **et** stablecoins).
- 📄 **Don d'AP2 à la FIDO Alliance** (avril 2026, v0.2), qui en fait un standard communautaire (FIDO : « Building the Trust Layer for Agentic Payments with AP2 and Verifiable Intent »).
- ⚠️ Statut mi-2026 : « early ; spec + coalition publiées ». **Ce n'est pas une couche d'exécution on-chain** — c'est la couche *autorisation/consentement* qui *peut* référencer un règlement crypto. Utile pour la **narration** (le vocabulaire « mandate » est le bon mot d'ordre 2026) ; inutile pour la **démo**.

### 4.3 Circle programmable wallets / paymasters

- 📄 Circle Wallets : portefeuilles **user-controlled MPC** ou **developer-controlled SCA** (ERC-4337), SDK (ex. `developer_controlled_wallets`), réseaux de test listés (`ETH-SEPOLIA`, `MATIC-AMOY`, `AVAX-FUJI`, `SOL-DEVNET`) — **Base Sepolia n'apparaît pas** dans l'extrait de doc consulté → *non concluant*, à re-vérifier si on veut s'en servir.
- **Paymaster (gas)** : 📄 CDP Bundler&Paymaster sur Base Sepolia, avec **allowlist de contrats** dans la policy (utile : on peut sponsoriser *uniquement* le contrat `redeemDelegations`). C'est la brique qui permet une démo « l'agent paie sans détenir d'ETH » — plausible mais **non testée ici**.

---

## 5. Garde-fous on-chain : ce qui existe comme primitive réutilisable vs ce qu'il faut écrire

### 5.1 Primitives **déjà déployées** (réutilisables telles quelles) — vérifiées sur Base Sepolia le 14/10/2026

| Garde-fou | Primitive existante | État Base Sepolia |
|---|---|---|
| Plafond par période (reset) | `ERC20PeriodTransferEnforcer` `0x474e3Ae7…39aB` (Delegation Framework) / `erc20-token-periodic` (MetaMask) / `SpendPermissionManager.spend` | ✅ déployé |
| Plafond total (sans reset) | `ERC20TransferAmountEnforcer` `0xf100b081…D2Fc` / `erc20-token-allowance` | ✅ déployé |
| Décroissance linéaire (streaming, type vesting) | `ERC20StreamingEnforcer` `0x56c97aE0…b00e` (adresse issue de `documents/Deployments.md`, non testée ici) | 📄 |
| Expiration / fenêtre temporelle | `TimestampEnforcer` `0x1046bb45…c069` ; règle `expiry` de 7715 | ✅ déployé |
| Allowlist de cibles | `AllowedTargetsEnforcer` `0x7F20f61b…4EeB` | ✅ déployé |
| Allowlist de méthodes (selectors) | `AllowedMethodsEnforcer` `0x2c21fD0C…42B5` | 📄 |
| Plafond de valeur native | `ValueLteEnforcer` `0x92Bf1232…6A8F` | 📄 |
| Limitation du nombre d'appels | `LimitedCallsEnforcer` `0x04658B29…5416` | 📄 |
| Contrôle du destinataire (redeemer) | `RedeemerEnforcer` `0xE144b0b2…65c5` | 📄 |
| Révoquer une approbation ERC-20 | `ApprovalRevocationEnforcer` `0xe264F1f0…324A` + type 7715 *Token approval revocation* | 📄 |
| Multi-token par période | `MultiTokenPeriodEnforcer` `0xFB2f1a9B…eBb7` | 📄 |

*(Les adresses « 📄 » proviennent de `documents/Deployments.md` du dépôt `MetaMask/delegation-framework`, déploiement déterministe CREATE2 avec salt `"GATOR"` → mêmes adresses sur tous les réseaux listés, dont Base Sepolia. Je n'ai testé on-chain que celles marquées ✅.)*

### 5.2 Ce qui **n'existe pas** comme primitive standard (à écrire soi-même, ou à porter hors chaîne)

- **Circuit breaker** (arrêt d'urgence global déclenché par une condition de marché) : non trouvé de module audité générique. À implémenter comme (a) **off-chain** : le worker ORVYREN cesse d'émettre des intents (déjà faisable, gratuit) ; (b) **on-chain** : révocation de la permission (`wallet_revokeExecutionPermission`, `disableDelegation`, ou `SpendPermissionManager.revoke`) — c'est la vraie « coupure ».
- **TWAP / slippage guards pour swaps** : partiellement couvert par les enforcers de la DeFi (allowed targets + amount), mais **aucun enforcer standard de « slippage max »** trouvé ; à écrire si on ajoute des swaps (hors périmètre actuel d'ORVYREN : transferts USDC uniquement).
- **Idempotence on-chain** : n'existe pas nativement (les permissions sont des plafonds, pas des séquences). L'`intent_id` reste **hors chaîne** — et c'est très bien ainsi : la couche on-chain est un plafond, la couche policy est le séquenceur. À dire explicitement au jury, c'est un argument de conception, pas un manque.
- **Limite par transaction** : **absente** de `SpendPermissionManager` (documenté) et absente des enforcers de période (qui ne raisonnent qu'en cumul de période). **Donc le plafond 100 USDC/tx d'ORVYREN n'est pas exprimable dans l'enveloppe on-chain** → il reste off-chain. C'est une asymétrie **à assumer** : « la chaîne borne le pire cas cumulé ; la policy borne la granularité, et l'écart est couvert par le contrôle de réception » (voir §7.3).

---

## 6. (a) Tableau comparatif des options

| Nom | Standard / dépôt | Ce que ça garantit | Maturité (preuve chiffrée) | Testnet dispo | Coût d'intégration |
|---|---|---|---|---|---|
| **MetaMask Advanced Permissions (ERC-7715) + Delegation Framework** | ERC-7715 (**Draft**) + ERC-7710 ; `MetaMask/delegation-framework` ; kit `@metamask/smart-accounts-kit` | Permission **par actif, montant, période, expiration**, révocable ; exécution via `redeemDelegations` ; caveats composables (cible, méthode, appels, timestamp) | Kit ≥ v1.5.0 pour Base Sepolia, kit actuel **v2.0.0** ; extension ≥ **13.23.0** (types periodic/stream) ; audits Cyfrin + Consensys Diligence (dépôt) ; contrat produit depuis avril 2026 | **Base Sepolia ✅ (vérifié** : DelegationManager `0xdb9B…7dB3`, factory, 4 enforcers **et** bytecode non vide) | **Moyen** — smart account + extension navigateur pour l'octroi + script de rédemption ; 1 nouvelle dépendance technique |
| **Coinbase Spend Permissions** | `coinbase/spend-permissions` (`SpendPermissionManager`) ; API CDP | Plafond **par token/période** (reset à frontières fixes), `start`/`end`, révocation ; **pas** de call arbitraire, **pas** de plafond par tx | Audits Spearbit/**Cantina** : 29/10/2024, 11/2024, 10/12/2024 (+ SpendRouter 03/2026) ; usage réel ~**547 spends / 7 j** (août 2026), 15 236 USDC, 1 spender par permission | **Base Sepolia ✅ (vérifié** : `0xf85210B2…67Ad`, 12 610 octets — taille identique aux 8 mainnets) | **Faible** — API serveur, pas d'extension ; idéal fallback |
| **Safe Allowance Module** | `safe-global/safe-modules` (+ `safe-modules-deployments`) | Allowance **token + période** pour un **delegate** ; pas de contrôle cible/méthode ; révocation via tx Safe | Code audité (rapports v0.1.0/0.1.1/1.0.0 ; audit d'origine **10/2020**) ; v0.1.0 = 15 réseaux, v0.1.1 = 54 | **Base Sepolia ❌ (vérifié** : code absent pour `0xCFbFaC74…` et `0x1Fb40383…`) — Safe v1.4.1 lui-même ✅ présent | **Élevé** — déploiement du module à notre charge (« audited code, unaudited deployment ») + tx Safe |
| **ZeroDev Kernel (permissions / session keys)** | ERC-7579 ; `zerodevapp/kernel` ; SDK `@zerodev/*` | **1 signer + n policies** : plafonds, fenêtres, allowlists, selectors ; vérifié *dans* `validateUserOp` ; composable et extensible | Audits ChainLight (`chainlight_v3_0.pdf`) + Kalos (`kalos_v3_plugins.pdf`, v1/v2.x) ; **limite connue TOB-KERNEL-3** documentée | **Base Sepolia ✅** (docs) | **Moyen-élevé** — SDK + écriture/reprise de policies |
| **Biconomy Smart Sessions (Nexus)** | `bcnmy/nexus` | Sessions multi-chaînes d'un signer délégué, policies (contrats, fonctions, plafonds, temps) | Audits référencés (Pashov, Cantina/Spearbit — ⚠️ rapports **non lus ici**) ; ne revendique pas ERC-7715 | Base Sepolia : **non vérifié ici** | **Moyen** |
| **Rhinestone Smart Sessions** | modules ERC-7579 + `module-sdk` | Session keys, transfers planifiés, policies ; brique pour d'autres wallets | Déploiements Base/Optimism/Arbitrum (⚠️ secondaire) ; **audit précis non trouvé** | **non trouvé** | **Moyen** |
| **Approbation ERC-20 classique (`approve`+`transferFrom`)** | EIP-20 / EIP-2612 | Rien de plus que « ce contrat peut prendre jusqu'à X » — **pas d'expiration, pas de période, pas de cible** | Universel ; c'est le problème que 7715/7710 cherchent à résoudre | Tous | **Trivial** (et c'est le piège : c'est ce que fait un amateur) |
| **x402** (rail, **pas** une permission) | x402 Foundation (Linux Foundation) ; `X-PAYMENT`, EIP-3009 | *Settlement* d'un paiement HTTP ; **aucun** cumul, **aucune** expiration ; défaut SDK 1 $/paiement | ⚠️ ~161 M paiements / 43,5 M$ (mi-2026) ; **5 attaques publiées** (arXiv 2605.11781, testbed Base Sepolia) | Base Sepolia (facilitateur testnet) | Faible, mais **ne remplace pas** une permission |
| **AP2** (mandats) | Google → **FIDO Alliance** (avril 2026, v0.2) | Preuve de **consentement signé** (Intent/Cart Mandate, VCs, ECDSA) ; rail-agnostique ; **hors chaîne** | Spec + coalition publiées ; adoption « early » (⚠️) | N/A (pas d'exécution on-chain) | Faible (vocabulaire/narration), nul pour la démo |
| **MetaMask Agent Wallet (produit)** | CLI `mm` + Guard Mode | Plafond **glissant 24 h**, allowlist, simulation, threat scanning Blockaid, 2FA au dépassement | Produit lancé 2026 ; **limites documentées** (outflow non fiable hors backend ; Permit2 non compté) | Base Sepolia ✅ (docs CLI) | Faible mais **non composable** avec notre pipeline (produit fermé côté agent) |

---

## 7. (b) Recommandation concrète pour ORVYREN

### 7.0 Principe : trois couches, pas une

```
[1] POLICY (hors chaîne, déterministe, déjà écrit)      → décide ALLOW / DENY / REQUIRE_APPROVAL
[2] MANDATE (on-chain, ERC-7715/7710 ou SpendPermission) → borne ce qui est POSSIBLE, même si [1] est compromis
[3] PROOF (vérification du reçu, déjà écrit)             → prouve ce qui s'est RÉELLEMENT passé
```

Le message au jury : **on ne remplace pas la policy par la chaîne ; on ajoute un plafond que ni l'agent ni un bug de la policy ne peuvent franchir.** C'est la définition d'une délégation bornée.

### 7.1 Choix principal : **ERC-7715 / MetaMask Advanced Permissions sur Base Sepolia**

Pourquoi : (a) testnet supporté et **vérifié on-chain** (contrats présents) ; (b) le type **`erc20-token-periodic`** mappe *exactement* la politique ORVYREN (montant par période + durée de période + départ) ; (c) la révocation est **native et standardisée** (`wallet_revokeExecutionPermission` + `disableDelegation`) ; (d) c'est **le** standard que le thème du concours appelle (« Agent Wallet »), et il est déjà nommé par Polygon/MetaMask en 2026 ; (e) tous les artifacts (context, dependencies, delegationManager) sont **sérialisables** — donc auditables et rejouables, ce qui est la thèse d'ORVYREN.

**Matrice d'autorité proposée (à figer)**

| Contrainte | Où elle vit | Valeur de démo |
|---|---|---|
| Chaîne | on-chain (`chainId`) + policy | Base Sepolia 84532 |
| Actif | on-chain (`tokenAddress`) + policy | USDC test `0x036CbD53842c5426634e7929541eC2318f3dCF7e` |
| Cumul / période | **on-chain** (`erc20-token-periodic`) | `periodAmount` = **300 USDC**, `periodDuration` = **86 400 s** |
| Expiration | **on-chain** (règle `expiry`) | `now + 86 400 s` |
| Bénéficiaire de la permission | **on-chain** (`to` = session account) | adresse de session de l'agent |
| Plafond **par transaction** | **policy** (hors chaîne) | 100 USDC |
| Allowlist destinataire | **policy** (hors chaîne) | wallet « réserve » |
| Idempotence | **policy** (`intent_id`) | table `intent` |
| Vérification finale | **proof** (reçu + log `Transfer`) | déjà implémenté |

Le **désalignement est volontaire et doit être expliqué** : la chaîne ne sait pas faire « 100 par tx » ; elle sait faire « 300 par 24 h ». Donc la chaîne borne le pire cas, la policy borne la finesse.

### 7.2 Chemin d'intégration (ordre d'exécution, ~4–5 jours-homme)

1. **Geler la matrice d'autorité** (§7.1) dans un document + un test : « la permission accordée doit être ≥ ce que la policy exige, sinon REFUS d'exécuter ». *(0,5 j)*
2. **Compte de démonstration** : MetaMask Smart Account v2.0.0, implémentation `Hybrid` (EOA + passkey), sur Base Sepolia ; déployer et noter l'adresse + la tx de déploiement. *(0,5 j)*
3. **Octroi de la permission** (script séparé, hors du moteur de décision) : `wallet_requestExecutionPermissions` avec `{ type: 'erc20-token-periodic', data: { tokenAddress, periodAmount: parseUnits('300',6), periodDuration: 86400 }, rules: [{ type:'expiry', data:{ timestamp: now+86400 } }], isAdjustmentAllowed: true, to: <session account> }`. **L'humain approuve une fois** dans MetaMask ≥ 13.23.0. Persister la réponse (`context`, `dependencies`, `delegationManager`) dans un JSON **hors prompt LLM**. *(1 j, dont le temps de mettre l'environnement navigateur en place)*
4. **Exécution bornée** : après `PolicyDecision == ALLOW`, l'agent appelle `redeemDelegations([context],[SingleDefault], [encodedExecution])` **depuis le session account** (EOA ⇒ besoin d'un peu d'ETH de test ; ou bundler/paymaster CDP avec allowlist sur le contrat `redeemDelegations`). Puis **vérifier le reçu** avec le décodeur existant. *(1–2 j)*
5. **Cas DENY documentés** — les deux, c'est ce qui impressionne :
   - **DENY par la policy** : destinataire hors allowlist ou montant > 100 ⇒ **aucun appel on-chain**, 0 gaz ; on montre la trace `PolicyDecision{DENY}` + le motif.
   - **DENY par la chaîne** : tenter un rachat de **350 USDC** (au-delà du plafond de période) ⇒ **revert** du `ERC20PeriodTransferEnforcer`/du manager ; on montre la **transaction revertée sur BaseScan** (« même si notre policy était corrompue, la chaîne refuse »). *(0,5 j)*
6. **Révocation d'urgence** : `wallet_revokeExecutionPermission` (wallet) puis nouvelle tentative ⇒ échec ; montrer l'état avant/après. *(0,5 j)*
7. **Docs + vidéo (EN)** : les 3 captures (octroi → ALLOW → DENY on-chain → révocation), l'adresse du DelegationManager, le hash de chaque tx. *(0,5 j)*

**Fallback (si l'octroi navigateur est un risque le jour J)** : brancher **Coinbase Spend Permissions** — `createSpendPermission({account, spender: <adresse agent>, token: 'usdc', allowance: 300e6, periodInDays: 1, start, end: now+24h})` via CDP sur `base-sepolia`, puis `useSpendPermission(...)` côté agent. Mêmes steps 5–7 (le DENY par la chaîne est alors le revert `ExceededSpendPermission`). Coût ~1 j, et **entièrement scriptable** : c'est l'assurance-vie de la démo.

### 7.3 Ce qui **casserait** (liste honnête, à connaître avant de s'engager)

1. **ERC-7715 est un Draft** : un changement de nom de méthode ou de type entre aujourd'hui et le jour du concours est possible. → Isoler dans un adaptateur, **figer la version du kit** dans `package.json`, et **enregistrer une démo vidéo de secours** dès que ça marche.
2. **L'octroi ERC-7715 exige un wallet compatible** (extension MetaMask ≥ 13.23.0, desktop). En démo *live* sans navigateur pilotable, **l'octroi ne peut pas être automatisé** ; soit on le prépare avant, soit on passe par Coinbase (API serveur) — c'est le risque n°1 du plan.
3. **Le session account doit payer le gaz** : sans ETH de test, pas de `redeemDelegations`. → paymaster CDP (allowlist sur le contrat) ou faucet Base Sepolia. ⚠️ Le faucet CDP plafonne (ex. **1 USDC par claim, 10 claims/24 h** ; ETH 0,0001/claim) : obtenir 300 USDC de test demande plusieurs claims ou le faucet Circle.
4. **La permission on-chain n'est pas un rate-limit** : autour d'une frontière de période, jusqu'à **2× le budget en quelques secondes** (comportement documenté du manager Coinbase ; le type `periodic` MetaMask a la même sémantique de reset). → Ne **jamais** présenter la permission comme une limite instantanée ; la limite instantanée, c'est la policy.
5. **Pas de plafond par transaction on-chain** (§5.2) → si quelqu'un lit le contrat et demande « et 300 USDC en une seule tx ? », la réponse est : *la chaîne l'autorise, la policy et le contrôle de reçu l'interdisent, et c'est une limite connue documentée ici*. Anticiper la question.
6. **Safe Allowance Module indisponible sur Base Sepolia** ⇒ si on choisit cette voie, il faut déployer le module nous-mêmes : le code est audité mais **le déploiement ne l'est pas**, et le coût double pour une portée moindre. **À éviter dans le temps imparti.**
7. **Révocation non instantanée dans le même bundle** (Kernel/TOB-KERNEL-3) : ne pas promettre une révocation « atomique » ; promettre « révocable, effective à la transaction suivante ».
8. **Le discours « zéro clé » change** : avec une délégation, **l'agent détient bien une clé de session**. C'est **mieux** (elle n'a d'autorité que ce que la chaîne lui reconnaît), mais il faut le dire — sinon un juriste/jury technique relève la contradiction avec la doc actuelle. Formulation retenue : « l'agent détient une clé **sans valeur intrinsèque**, dont l'autorité est un objet on-chain borné, expirable et révocable ».
9. **Faux jeton / fausse preuve** : n'utiliser que l'USDC de test Circle (`0x036CbD…CF7e`, symbole `symbol()` = `"USDC"` vérifié le 14/10/2026). Ne **jamais** déployer un faux « USDC » maison pour la démo : c'est le piège classique et il est démasquable en 10 secondes par un jury.
10. **Sensibilité crypto en Chine** : le 06/02/2026, la PBOC et plusieurs autorités ont étendu l'interdiction aux **stablecoins et à la tokenisation d'actifs réels** (📄 loc.gov, 2026-05-21). La démo doit être **testnet uniquement**, **sans émission de jeton**, **sans promesse de rendement**, **sans référence à un yuan numérique ou à des fonds réels** ; le thème F du concours porte sur l'**agent wallet** (autorisation, sécurité, traçabilité), pas sur l'investissement crypto.

---

## 8. (c) Vérifié vs incertain

### 8.1 ✅ Vérifié on-chain par nous (Base Sepolia, 14/10/2026, `https://sepolia.base.org`)

| Contrat | Adresse | Résultat |
|---|---|---|
| Chain ID | — | `eth_chainId` = `0x14a34` (**84532**) |
| Coinbase `SpendPermissionManager` | `0xf85210B21cC50302F477BA56686d2019dC9b67Ad` | déployé, **12 610** octets |
| MetaMask `DelegationManager` v1.3.0 | `0xdb9B1e94B5b69Df7e401DDbedE43491141047dB3` | déployé, 11 503 octets |
| MetaMask `SimpleFactory` v1.3.0 | `0x69Aa2f9fe1572F1B640E1bbc512f5c3a734fc77c` | déployé, 751 octets |
| `ERC20PeriodTransferEnforcer` | `0x474e3Ae7E169e940607cC624Da8A15Eb120139aB` | déployé, 3 346 octets |
| `ERC20TransferAmountEnforcer` | `0xf100b0819427117EcF76Ed94B358B1A5b5C6D2Fc` | déployé, 2 078 octets |
| `TimestampEnforcer` | `0x1046bb45C8d673d4ea75321280DB34899413c069` | déployé, 1 255 octets |
| `AllowedTargetsEnforcer` | `0x7F20f61b1f09b08D970938F6fa563634d65c4EeB` | déployé, 1 846 octets |
| Safe `AllowanceModule` v0.1.0/0.1.1 | `0xCFbFaC74C26F8647cBDb8c5caf80BB5b32E43134` / `0x1Fb40383…3b4D` | **NON déployé** (`0x`) |
| Safe L2 singleton v1.4.1 | `0x29fcB43b46531BcA003ddC8FCB67FFE91900C762` | déployé, 24 421 octets |
| Safe Proxy Factory v1.4.1 | `0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67` | déployé, 3 054 octets |
| USDC de test (Circle) | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` | déployé ; `symbol()` = `"USDC"` |

### 8.2 📄 Vérifié dans les sources primaires (URL + date d'accès 14/10/2026)

- ERC-7715 : <https://eips.ethereum.org/EIPS/eip-7715> — statut **Draft**, méthodes §2.1, `isAdjustmentAllowed`, `dependencies`, rédemption ERC-7710.
- ERC-7710 : <https://eips.ethereum.org/EIPS/eip-7710> — `redeemDelegations(_permissionContexts, _modes, _executionCallDatas)`, modes ERC-7579, recommandation **de simuler avant de soumettre**.
- MetaMask : réseaux supportés (<https://docs.metamask.io/smart-accounts-kit/development/get-started/supported-networks/> — **Base Sepolia dès v1.5.0**, kit v2.0.0) ; types supportés et versions minimales d'extension ; paramètres des permissions ; guide « execute on MetaMask users behalf » (extension ≥ **13.23.0**) ; news du **06/04/2026** (<https://metamask.io/news/introducing-advanced-permissions>) ; `documents/Deployments.md` (salt `"GATOR"`, adresses v1.3.0, chaînes dont Base Sepolia, audits Cyfrin/Diligence dans `audits/`).
- MetaMask Agent Wallet : <https://docs.metamask.io/agent-wallet/> + `reference/outflow-policy` (fenêtre glissante 24 h, 2FA, Guard Mode, Blockaid, couverture 10 000 $/mois) + `reference/supported-chains` (Base Sepolia 84532).
- Coinbase : `coinbase/spend-permissions` README (adresses, testnets, audits Cantina/Spearbit datés, structure `SpendPermission`, ERC-6492, refus ERC-721, pas d'appels arbitraires) ; `docs/SpendPermissionAccounting.md` (périodes à frontières fixes, reste) ; docs CDP Spend Permissions (API serveur, `base-sepolia`).
- Safe : `safe-modules-deployments` JSON (v0.1.0 = 15 réseaux, v0.1.1 = 54 ; **pas de 84532**) ; liste d'audits <https://docs.safefoundation.org/security/audits> ; `AllowanceModuleAuditOct2020.md`.
- ZeroDev : réseaux supportés (Base Sepolia 84532) ; page audits (« All ZeroDev contracts and plugins are audited… ») ; liste des rapports via API GitHub (ChainLight, Kalos) ; README Kernel (limite TOB-KERNEL-3).
- arXiv **2605.11781** — *Five Attacks on x402 Agentic Payment Protocol* (testbed Base Sepolia).
- Google Cloud / FIDO : AP2 et mandats (Intent/Cart, VCs, ECDSA) ; don à la FIDO Alliance.
- PBOC : <https://www.loc.gov/item/global-legal-monitor/2026-05-21/china-cryptocurrency-ban-extended-to-stablecoins-and-rwa-tokenization/> (circulaire du **06/02/2026**).

### 8.3 ⚠️ Incertain / secondaire (à ne pas citer comme dur)

- Chiffres x402 (161,32 M paiements / 43,57 M$ ; 417 k acheteurs / 83 k vendeurs ; Stripe fév. 2026 ; AWS Bedrock mai 2026) : agrégateurs secondaires.
- Relevés d'usage de `SpendPermissionManager` (547 spends / 7 j, 15 236 USDC, août 2026) : analyse indépendante, non reproduite ici.
- « ERC-7715 en production sur Polygon (avril 2026) » : annonce Polygon (réseau social) + presse spécialisée ; **pas** de page produit primaire consultée.
- Atténuation *effective* en production par l'extension MetaMask (au-delà de la doc) : non vérifiée.
- Contenu des audits Biconomy / Rhinestone : **non lus** → ne pas affirmer.

### 8.4 ❌ Non trouvé

- Statistiques d'usage **ERC-7715** (nombre de permissions accordées en production) : **non trouvé**.
- Audit public du *permissions handler* de l'extension MetaMask : **non trouvé**.
- Support Base Sepolia chez Circle Programmable Wallets : **non trouvé** dans l'extrait consulté.
- Primitive standard de **circuit breaker / slippage guard** audité : **non trouvée** (cf. §5.2).
- État d'audit précis de Rhinestone : **non trouvé**.

---

## 9. (d) Implications pour la soumission au concours

### 9.1 Ce qu'on peut affirmer **sans mentir** (formulations à reprendre telles quelles)

1. « **Deux niveaux d'autorité** : une politique déterministe hors chaîne (100 USDC/tx, 300 cumulés, TTL 24 h, allowlist) **et** une enveloppe de dépense on-chain (permission ERC-20 périodique ERC-7715/7710, `periodAmount = 300 USDC`, `expiry = +24 h`) sur **Base Sepolia** (chainId 84532). »
2. « **Un humain approuve l'enveloppe une fois** ; l'agent exécute à l'intérieur ; le dépassement est refusé par le **contrat**, pas par un prompt. »
3. « Cas **ALLOW** et **DENY** exécutés sur Base Sepolia, **hash de transaction et lien explorer** pour chacun — y compris une **transaction revertée** par le contrat. »
4. « Briques **auditées par des tiers** : Delegation Framework MetaMask (Cyfrin, Consensys Diligence), Spend Permissions Coinbase (Spearbit/Cantina 2024), Allowance Module Safe (audit 2020). **L'audit porte sur le code des briques, pas sur notre intégration** — nous ne revendiquons pas d'audit de notre propre code. »
5. « Les contrats utilisés sont **vérifiés présents sur Base Sepolia** par appel RPC (`eth_getCode`) — preuve reproductible fournie en annexe. »
6. « ERC-7715 est un **draft** à la date de soumission ; nous l'indiquons et nous isolons l'intégration derrière un adaptateur. »
7. « **Aucun fonds réel, aucun jeton émis, aucune promesse de rendement** : uniquement le testnet et l'USDC de test de Circle. »
8. « La révocation est **native** (`wallet_revokeExecutionPermission` / `disableDelegation`) et démontrée. »

### 9.2 Ce qu'on **ne peut pas** affirmer

- ❌ « audité » sans qualifier (dire « briques auditées par des tiers », jamais « notre système est audité »).
- ❌ « standard finalisé / norme ERC-7715 » → c'est un **Draft**.
- ❌ « l'agent ne détient **aucune** clé » → devient « clé de session bornée on-chain, révocable ».
- ❌ « limite de 100 USDC par transaction garantie par la chaîne » → **faux** (le plafond par tx est off-chain).
- ❌ « plafond temps réel / rate-limit » → la sémantique est **par période**, avec un effet de bord 2× aux frontières.
- ❌ « production-ready », « mainnet », « custodian », « conforme réglementaire », « rendement », « notre stablecoin/jeton ».
- ❌ Toute capture d'écran de gains, APY, ou montant en devise réelle.

### 9.3 Ce qu'un jury fintech considérerait comme **impressionnant sans fonds réels**

1. **Le refus produit par la chaîne.** Montrer une transaction **revertée** sur BaseScan parce que l'agent a tenté de dépasser l'enveloppe : c'est la démonstration que l'autorité n'est pas une convention sociale mais une contrainte vérifiable. C'est le moment de la vidéo.
2. **Le refus produit par la policy, à coût zéro.** Même requis, mais **aucun gaz dépensé**, **aucune tx** : la couche décisionnelle filtre avant la chaîne. Montrer les deux refus côte à côte raconte l'architecture complète.
3. **La révocation.** Un clic (ou une commande) et l'agent ne peut plus rien : preuve avant/après avec deux tx.
4. **La provenance.** Chaque étape (octroi, ALLOW, DENY, révocation) avec hash, horodatage, adresse de contrat — le « dossier de décision » d'ORVYREN appliqué à la couche de permission.
5. **L'honnêteté technique.** Dire dans la vidéo : « ERC-7715 est un draft ; la chaîne ne fait pas de limite par transaction ; voici ce que chaque couche garantit et ce qu'elle ne garantit pas ». En fintech, savoir énoncer ses limites est un signal de maturité plus fort qu'une promesse.

### 9.4 Trois pièges à éviter absolument (rappel)

- **Mainnet / fonds réels** : interdit par notre propre cadrage et coûteux en cas d'erreur.
- **Faux jeton** : jamais de token maison présenté comme « USDC » ; utiliser `0x036CbD53842c5426634e7929541eC2318f3dCF7e` (symbole `USDC`, vérifié).
- **Promesses de rendement / vocabulaire crypto-investissement** : d'autant plus en Chine (circulaire PBOC du 06/02/2026 sur les stablecoins et la tokenisation) — la démo est **infrastructure d'autorisation et de traçabilité**, point.

---

## 10. Annexe — reproduire les vérifications (30 secondes)

```bash
RPC=https://sepolia.base.org
# chainId (attendu 0x14a34 = 84532)
curl -s -X POST -H 'content-type: application/json' --data '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' $RPC

# SpendPermissionManager Coinbase (attendu : bytecode non vide)
curl -s -X POST -H 'content-type: application/json' --data '{"jsonrpc":"2.0","id":1,"method":"eth_getCode","params":["0xf85210B21cC50302F477BA56686d2019dC9b67Ad","latest"]}' $RPC | head -c 120

# DelegationManager MetaMask (attendu : bytecode non vide)
curl -s -X POST -H 'content-type: application/json' --data '{"jsonrpc":"2.0","id":1,"method":"eth_getCode","params":["0xdb9B1e94B5b69Df7e401DDbedE43491141047dB3","latest"]}' $RPC | head -c 120

# AllowanceModule Safe (attendu : "0x" => NON déployé sur Base Sepolia)
curl -s -X POST -H 'content-type: application/json' --data '{"jsonrpc":"2.0","id":1,"method":"eth_getCode","params":["0xCFbFaC74C26F8647cBDb8c5caf80BB5b32E43134","latest"]}' $RPC

# USDC de test : symbol() (attendu : "USDC")
curl -s -X POST -H 'content-type: application/json' --data '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0x036CbD53842c5426634e7929541eC2318f3dCF7e","data":"0x95d89b41"},"latest"]}' $RPC
```

*(Sous Windows/git-bash, si `curl` renvoie du HTML, ajouter `-H 'User-Agent: mozilla/5.0'` — observé le 14/10/2026.)*

### Adresses de référence (Base Sepolia sauf mention)

| Objet | Adresse |
|---|---|
| USDC de test (Circle) | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` |
| Coinbase `SpendPermissionManager` | `0xf85210B21cC50302F477BA56686d2019dC9b67Ad` |
| Coinbase `PublicERC6492Validator` | `0xcfCE48B757601F3f351CB6f434CB0517aEEE293D` |
| MetaMask `DelegationManager` v1.3.0 | `0xdb9B1e94B5b69Df7e401DDbedE43491141047dB3` |
| MetaMask `SimpleFactory` v1.3.0 | `0x69Aa2f9fe1572F1B640E1bbc512f5c3a734fc77c` |
| `ERC20PeriodTransferEnforcer` | `0x474e3Ae7E169e940607cC624Da8A15Eb120139aB` |
| `ERC20TransferAmountEnforcer` | `0xf100b0819427117EcF76Ed94B358B1A5b5C6D2Fc` |
| `TimestampEnforcer` | `0x1046bb45C8d673d4ea75321280DB34899413c069` |
| `AllowedTargetsEnforcer` | `0x7F20f61b1f09b08D970938F6fa563634d65c4EeB` |
| Safe v1.4.1 (singleton L2 / factory) | `0x29fcB43b46531BcA003ddC8FCB67FFE91900C762` / `0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67` |

---

## 11. Références (URL + date)

**Specs**
- ERC-7715 — Request Permissions from Wallets (Draft, créé 2024-05-24) : <https://eips.ethereum.org/EIPS/eip-7715> — consulté 14/10/2026.
- ERC-7710 — Smart Contract Delegation : <https://eips.ethereum.org/EIPS/eip-7710> — consulté 14/10/2026.
- ERC-4337 / ERC-7579 (dépendances) : <https://eips.ethereum.org/EIPS/eip-4337>, <https://eips.ethereum.org/EIPS/eip-7579> — consultés 14/10/2026.

**MetaMask**
- Advanced Permissions (concept) : <https://docs.metamask.io/smart-accounts-kit/concepts/advanced-permissions/> — 14/10/2026.
- Réseaux supportés : <https://docs.metamask.io/smart-accounts-kit/development/get-started/supported-networks/> — 14/10/2026.
- Permissions & versions : <https://docs.metamask.io/smart-accounts-kit/development/get-started/supported-advanced-permissions/> et `…/reference/advanced-permissions/permissions/` — 14/10/2026.
- Guide d'exécution : <https://docs.metamask.io/smart-accounts-kit/development/guides/advanced-permissions/execute-on-metamask-users-behalf/> — 14/10/2026.
- Annonce produit : <https://metamask.io/news/introducing-advanced-permissions> — 06/04/2026.
- Dépôt Delegation Framework (+ `documents/Deployments.md`, `audits/`) : <https://github.com/MetaMask/delegation-framework> — 14/10/2026.
- Agent Wallet (outflow policy, chaînes) : <https://docs.metamask.io/agent-wallet/> , `…/reference/outflow-policy/`, `…/reference/supported-chains/` — 14/10/2026.

**Coinbase**
- Spend Permissions (contrat + déploiements + audits) : <https://github.com/coinbase/spend-permissions> — 14/10/2026.
- Docs CDP Spend Permissions : <https://docs.cdp.coinbase.com/wallets/using-wallets/spend-permissions> — 14/10/2026.
- Faucet (plafonds) : <https://coinbase.com/en-gb/developer-platform/products/faucet> — vu 14/10/2026.

**Safe**
- Déploiements modules : <https://github.com/safe-global/safe-modules-deployments> (`src/assets/allowance-module/v0.1.0|v0.1.1`) — 14/10/2026.
- Audits : <https://docs.safefoundation.org/security/audits> — 14/10/2026.
- Audit d'origine Allowance Module (10/2020) : <https://github.com/safe-global/safe-modules/blob/main/modules/allowances/docs/AllowanceModuleAuditOct2020.md> — 14/10/2026.

**ZeroDev / Biconomy / Rhinestone**
- Réseaux supportés : <https://docs.zerodev.app/api-and-toolings/faqs/chains> — 14/10/2026.
- Audits ZeroDev : <https://docs.zerodev.app/api-and-toolings/faqs/audits> ; rapports : <https://github.com/zerodevapp/kernel> (branche `main`, `audits/`) — 14/10/2026.
- Kernel (limite TOB-KERNEL-3) : <https://github.com/zerodevapp/kernel> — 14/10/2026.
- Biconomy Smart Sessions : <https://docs.biconomy.io/new/smart-sessions/introduction> , `…/policies` , <https://docs.biconomy.io/contracts-and-audits> — 14/10/2026.
- Rhinestone : <https://docs.rhinestone.dev/home/concepts/session-keys> , `…/smart-wallet/module-sdk` — cités (⚠️ contenu détaillé non vérifié).

**Paiements machine**
- x402 — cinq attaques : arXiv **2605.11781**, <https://arxiv.org/pdf/2605.11781v1> — vu 14/10/2026.
- Analyse du `SpendPermissionManager` + critique du chaînage x402/on-chain : <https://llm4agents.com/blog/spend-permissions-onchain-agent-budget-audit> — ⚠️ secondaire, page vue 14/10/2026.
- x402 vs AP2 (chiffres & jalons) : <https://rohitraj.tech/notes/ai-agent-payments-x402-vs-ap2-2026> — ⚠️ secondaire, 14/10/2026.
- AP2 (mandats) : <https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol> ; FIDO : <https://fidoalliance.org/building-the-trust-layer-for-agentic-payments-with-ap2-and-verifiable-intent/> ; don à la FIDO : <https://blog.google/products-and-platforms/platforms/google-pay/agent-payments-protocol-fido-alliance/> — 14/10/2026.
- Circle Wallets : <https://www.circle.com/wallets> — 14/10/2026.

**Contexte réglementaire (Chine)**
- PBOC & autorités, circulaire du 06/02/2026 (stablecoins / RWA) : <https://www.loc.gov/item/global-legal-monitor/2026-05-21/china-cryptocurrency-ban-extended-to-stablecoins-and-rwa-tokenization/> — 14/10/2026.

---

*Fin de R2. Les points §8.3 et §8.4 sont explicitement des zones d'incertitude : ne pas les utiliser comme appuis dans le dossier de concours sans vérification complémentaire.*
