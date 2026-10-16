# ORVYREN — Kit de démonstration testnet (W3-D)

**Runbook d'exécution des 5 runs sur Base Sepolia (chainId 84532).**
Aucun argent réel, aucune clé dans le dépôt, aucune transaction envoyée par ce
document. Le kit vit dans `scripts/demo/` et ses tests hors chaîne dans
`tests/test_demo_kit.py`.

Références internes qui font autorité : `FREEZE_V2.md` (E1 signer jetable,
E2 100 USDC, E5 deux USDC distincts, F* audit, J2 wallet testnet) ·
`ORVYREN_DOC2_TECHNIQUE_COMPLET.md` §5.5–5.7 (politique, exécution, audit).
Les études de recherche d'origine (schéma d'intent, préflight, plan des 5 runs,
montage Safe 2/3 + module Roles) sont archivées hors dépôt — voir `README.md`.

---

## 0. Ce que le kit fait — et ce qu'il ne fait pas

**Fait (validé hors chaîne le 2026-10-15) :** les 5 runs en dry-run, le
préflight 12 contrôles, le test de dérive 10 contrôles, la vérification du reçu,
le journal chaîné SHA-256, l'export + le paquet d'audit, 75 tests hors chaîne
(suite complète : 755 tests, 751 verts).

**Ne fait pas :** il ne déploie rien, ne génère aucune clé à votre place, ne
finance aucun wallet, ne remplace ni Safe{Wallet} ni l'app Roles, et **ne
transforme pas un dry-run en preuve d'exécution** (les hashes de dry-run sont
factices et marqués `simulated: true`).

---

## 1. Prérequis

| Élément | Valeur / où |
|---|---|
| Python | 3.11 (poste) — le kit est stdlib **sauf** le signataire (`eth-account`) |
| Réseau | Base Sepolia, `chainId 84532`, RPC public `https://sepolia.base.org` |
| Explorateur | `https://sepolia.basescan.org` |
| Wallet USD (test) | robinet Circle → **USDC Circle** `0x036CbD53842c5426634e7929541eC2318f3dCF7e` |
| Navigation | Safe{Wallet} `app.safe.global` (Base Sepolia) et app Roles `roles.gnosisguild.org` |
| Bibliothèque de signature | `python -m pip install eth-account` (MIT, **isolée** — à déclarer dans `LICENSES.md`) |
| Horloge | UTC fiable (les échéances d'intent sont en RFC 3339 UTC) |

Installation de la seule dépendance externe :

```bash
python -m pip install eth-account        # seul module qui l'importe : scripts/demo/signer.py
python scripts/demo/signer.py --check     # état du signataire (nom de la variable, jamais sa valeur)
```

---

## 2. Étape 1 — Créer le wallet jetable (aucune clé dans le dépôt)

1. **Générer la clé localement** (jamais copiée dans un chat, un ticket ou un prompt) :

   ```bash
   python -c "import secrets; print('0x' + secrets.token_bytes(32).hex())"
   ```

2. **Coller la valeur** dans `scripts/demo/.env` (créé à l'étape 4) sous
   `ORVYREN_PRIVATE_KEY=`. Le fichier `.env` est déjà couvert par `.gitignore`
   (section « Secrets ») — le kit ne l'écrit jamais lui-même et ne le lit que
   pour le processus signataire.

3. **Récupérer l'adresse publique** de cette clé (l'adresse n'est **pas** un secret) :

   ```bash
   python scripts/demo/signer.py --execute --address
   ```

   Reportez-la dans `ORVYREN_AGENT_ADDRESS`. *(Variante sans `eth-account` :
   importer la clé dans un profil de navigateur jetable et recopier l'adresse —
   jamais la clé — puis nettoyer le profil.)*

4. **Trois clés distinctes** pour la Safe 2/3 (étape 3) : trois personnes ou
   trois postes — sinon le « 2 sur 3 » est décoratif (question ouverte Q5 de B4).

---

## 3. Étape 2 — Robinets GRATUITS (aucun argent réel)

### 3.1 ETH de test pour l'agent (il paie son gaz)

Ordre de préférence : commencez par le robinet sans compte, puis CDP en
complément. Budget mesuré : **0,01 ETH couvre des milliers de transactions de
démo** (gaz ≈ 0,006 gwei le 2026-10-15, un transfert ≈ 50 000 gaz ≈ 3 × 10⁻⁷ ETH).

| Robinet | URL | Ce qu'il donne | Conditions de compte (vérifiées 2026-10-15) |
|---|---|---|---|
| **Coinbase CDP Faucet** | `https://portal.cdp.coinbase.com/products/faucet` | ETH Base Sepolia : **0,0001 ETH par demande**, plafond **0,1 ETH/24 h** ; aussi **USDC : 1 USDC/demande, 10 USDC/24 h** | **compte CDP gratuit requis** (UI Portal ou API `@coinbase/cdp-sdk` avec clé API) |
| **QuickNode Faucet** | `https://faucet.quicknode.com/drip` | ETH Base Sepolia : **1 drip par réseau toutes les 12 h** | compte QuickNode gratuit requis |
| **Alchemy Faucet** | `https://basefaucet.com/` | ETH Base Sepolia : **1 demande / 24 h** | **compte Alchemy gratuit** requis |
| *Repli sans compte* — Ethereum Ecosystem | `https://www.ethereum-ecosystem.com/faucets/base-sepolia` | **0,5 ETH par wallet / 24 h** | **aucun login** |
| *Repli sans compte* — Bware Labs | `https://bwarelabs.com/faucets` | ETH Base Sepolia, 1 claim / 24 h | aucune inscription |
| *Autres listés par Base* | thirdweb (`thirdweb.com/base-sepolia-testnet`), Chainstack (clé API, 0,5 ETH/24 h), LearnWeb3, ethfaucet.com | ETH Base Sepolia | voir `docs.base.org/base-chain/network-information/network-faucets` |

**Destinataire : l'AGENT** (`ORVYREN_AGENT_ADDRESS`) — il paie le gaz ; il ne
détient jamais les fonds métier (B5 S6).

### 3.2 USDC de test pour la Safe (les fonds métier)

| Robinet | URL | Ce qu'il donne | Conditions (vérifiées 2026-10-15) |
|---|---|---|---|
| **Circle Testnet Faucet** | `https://faucet.circle.com/` | **20 USDC** par demande, réseau **Base Sepolia** | **public et sans compte** ; **1 demande par couple (actif, réseau) toutes les 2 h** ; reCAPTCHA |

**Destinataire : la SAFE** (`ORVYREN_SAFE_ADDRESS`), pas l'agent.

⚠️ **DEUX USDC sur Base Sepolia** (mesuré B5 §b.2, à ne jamais confondre) :

* **USDC Circle** `0x036CbD53842c5426634e7929541eC2318f3dCF7e` → **transferts de la démo** (robinet Circle ci-dessus) ;
* **USDC Aave** `0xba50Cd2A20f6DA35D788639E581bca8d0B5d4D5f` → réserve de lending Aave, **jeton différent, robinet différent** ; aucune action Aave n'est jouée en v1.

---

## 4. Étape 3 — Safe 2/3 et module Roles (interface)

À faire **la veille** (non chronométré en démo). Chaque étape a sa vérification.

1. **Créer la Safe « DAO » 2/3** sur Base Sepolia via `app.safe.global`
   (3 propriétaires distincts, seuil 2).
   *Vérification :* l'adresse de la Safe a du code (`eth_getCode` ≠ `0x`) —
   `python scripts/demo/preflight.py --rpc --env-file scripts/demo/.env --capture-envelope demo_runs/envelope_live.json`
   puis regarder l'entrée `orvyren_safe_address` du fichier capturé.

2. **Déployer le module Roles POUR cette Safe** (app Zodiac /
   `roles.gnosisguild.org`) : `owner = avatar = target = la Safe`, puis
   **activer** le module.
   ⚠️ **Ne pas réutiliser l'instance officielle** `0xF2964CE6161ce0e75964Fe7927cE114cb0B283D5` :
   le module Roles est un **module par avatar** (W2C §g.0). Recopiez l'adresse de
   **votre** instance dans `ORVYREN_MODULE_ADDRESS`.
   *Vérification :* `Roles.owner()` = adresse de la Safe ; événement
   `RolesModSetup` dans le reçu de déploiement.

3. **Définir le rôle `AGENT`** (app Roles), exactement :

   | Paramètre | Valeur | Où le lire ensuite |
   |---|---|---|
   | Rôle | `AGENT` (`0x4147454e54…0000`) | onglet du rôle |
   | Cible | USDC Circle `0x036CbD…CF7e` **uniquement** (jamais `Clearance.Target` large) | Permissions |
   | Fonction scopée | `transfer(address,uint256)` — opération `CALL` seulement | Permissions |
   | Condition param 0 (destinataire) | `Or(EqualTo(B), EqualTo(C))` | Conditions |
   | Condition param 1 (montant) | `WithinAllowance(usdc_daily)` | Conditions |
   | Allowance `usdc_daily` | `refill = maxRefill = 300e6`, `period = 86400` | Allowances |
   | Quota d'appels `calls_daily` | **10 / jour** | Allowances |
   | Rien d'autre | aucune autre cible, aucune autre fonction | — |

4. **Créer le signer agent** = l'EOA de l'étape 2, puis lui **assigner le rôle** :
   `assignRoles(agent, [AGENT], [true])` depuis la Safe (auto-active le module si besoin).
   *Vérification :* `Roles.roles(AGENT).members(agent) == true` (app Roles).

5. **Alimenter** : ETH → agent (robinets §3.1) ; USDC → Safe (robinet Circle §3.2).
   Notez le **solde de départ** de la Safe.

6. **Vérifier la présence des contrats le jour J** (protocole B5 §e.7) — tout
   écart = **arrêt de la démo** :

   ```bash
   python scripts/demo/preflight.py --rpc --env-file scripts/demo/.env \
       --capture-envelope demo_runs/envelope_live.json
   ```

7. **Renseigner le bloc `role` de l'enveloppe** (`envelope.example.json` copié
   en `scripts/demo/envelope.live.json`) : cibles/fonctions/conditions/allowances
   lus dans l'app Roles, `version` du module et `advisory_clear`, et — si vous les
   confirmez sur le contrat déployé — les `probes` (calldata des getters).
   Tant que `D3`/`D6`/`D10` restent `UNKNOWN`, le **SAFE MODE** est actif en
   mode en ligne : c'est **voulu** (fail-closed, B4 P12).

---

## 5. Étape 4 — Configuration locale (`.env`, jamais versionné)

```bash
cp scripts/demo/config.example.env scripts/demo/.env
# remplir : ORVYREN_SAFE_ADDRESS, ORVYREN_AGENT_ADDRESS, ORVYREN_MODULE_ADDRESS,
#           ORVYREN_RECIPIENT_B, ORVYREN_RECIPIENT_C, ORVYREN_RECIPIENT_UNLISTED,
#           ORVYREN_PRIVATE_KEY (clé jetable de l'étape 1)
```

Contrôles de sécurité (le kit les refait au démarrage) :

* `--execute` **refuse les adresses factices** de `config.example.env` ;
* `--execute` **refuse de démarrer** sans `eth-account` ou sans clé ;
* `ORVYREN_ALLOW_MAINNET=1` fait **échouer** le démarrage (la démo est testnet) ;
* l'URL RPC est toujours affichée masquée (`mask_rpc_url`) et la clé n'apparaît
  nulle part : ni dans le journal, ni dans un rapport, ni à l'écran.

**Répétition à blanc (aucune clé requise, aucun réseau) :**

```bash
python scripts/demo/demo.py --run A --dry-run --session demo_runs/session_dry
python scripts/demo/demo.py --run B --dry-run --session demo_runs/session_dry
python scripts/demo/demo.py --run C --dry-run --session demo_runs/session_dry
python scripts/demo/demo.py --run D --dry-run --session demo_runs/session_dry
python scripts/demo/demo.py --run E --dry-run --session demo_runs/session_dry
python -m pytest tests/test_demo_kit.py -q      # 75 tests hors chaîne
```

---

## 6. Étape 5 — Séquence exacte des 5 runs (~8 minutes)

Session de commande (une seule session pour les 5 runs — le journal s'y accumule) :

```bash
export SESSION=evidence/demo_runs/rseth
export ENV_FILE=scripts/demo/.env
export ENVLP=scripts/demo/envelope.live.json
```

### RUN A — ALLOW dans l'enveloppe (les deux verrous disent oui)

```bash
python scripts/demo/demo.py --run A --execute --case rseth --session $SESSION \
    --env-file $ENV_FILE --envelope $ENVLP
```

Montant : **100 USDC** — décision **gelée** (FREEZE_V2 E2). L'étude B5 §e.1
écrivait 50 USDC et laissait l'écart ouvert (Q2 de B5) : `--amount 50.0` rejoue
la variante si l'équipe tranche autrement (les critères s'adaptent au montant).

**Critères mesurables (écrits dans `<run>/criteria.json`) :**
1. `receipt.status = 0x1` ;
2. **exactement un** log `Transfer` correspondant exactement (Safe → B, 100 000 000) ;
3. Δ solde Safe = **−100 000 000** et Δ solde B = **+100 000 000** ;
4. compteur de signatures du service = **1** ;
5. les **7 `kind`** de journal pour cet `intent_id` (INTENT, POLICY, SIMULATION, SUBMIT, RECEIPT, VERIFY, OUTCOME) ;
6. `blockHash` **stable** après 2 blocs (`CONFIRMED`).

### RUN B — DENY par la politique hors chaîne (le LLM propose, le système refuse)

```bash
python scripts/demo/demo.py --run B --execute --case rseth --session $SESSION \
    --env-file $ENV_FILE --envelope $ENVLP
```

**Critères :** compteur de signatures **inchangé** ; nonce de l'agent **inchangé** ;
soldes inchangés ; 4 cas avec les codes exacts —
B1 `AMOUNT_ABOVE_TX_CAP` (150 USDC), B2 `RECIPIENT_NOT_ALLOWED`,
B3 `INTENT_ALREADY_PROCESSED` (rejeu ×3), B4 `ACTION_NEEDS_HUMAN_APPROVAL`
(`change_policy` = `REQUIRE_APPROVAL`) — et **aucun `tx_hash`** émis.

### RUN C — DENY par la chaîne (on contourne volontairement le verrou hors chaîne)

```bash
python scripts/demo/demo.py --run C --execute --case rseth --session $SESSION \
    --env-file $ENV_FILE --envelope $ENVLP
```

**Critères :** C1 (500 USDC) et C2 (destinataire non listé) → `status = 0x0`,
**sélecteur de revert capturé**, aucun `Transfer` émis, soldes inchangés, gaz
perdu enregistré ; C3a/C3b (`allowTarget`, `Safe.enableModule` depuis la clé
agent) → revert `onlyOwner`/`GS*` ; C4 (100+100+100+100) → la 4ᵉ revert ;
**C5** → deux exécutions acceptées par l'enveloppe + **un refus hors chaîne**
`AMOUNT_ABOVE_PERIOD_CAP` (frontière de période : la limite est assumée, elle est
montrée à côté de sa preuve).

### RUN D — Kill switch chronométré

1. Le kit prépare l'intent 100 USDC **sans l'envoyer** et écrit
   `<run>/revocation_instruction.json`.
2. **La DAO exécute** `assignRoles(agent, [AGENT], [false])` (2 signatures sur 3) —
   via Safe{Wallet} ou l'outil fourni : `python scripts/demo/dao_assign_roles.py --enable false`
   (hash dans `demo_runs/setup/dao_assign_roles_last.json` ; contrôle indépendant :
   simulation `eth_call` de l'agent → `NoMembership`). Notez l'heure et le hash.
3. Chronométrez puis rejouez la tentative de l'agent :

```bash
python scripts/demo/demo.py --run D --execute --case rseth --session $SESSION \
    --env-file $ENV_FILE --envelope $ENVLP --revocation-tx 0x<tx de révocation>
```

**Critères :** latences (a) collecte des signatures, (b) inclusion, (c) effet
affichées ; la tentative de l'agent rend **`status = 0x0`** avec le sélecteur
**`0xfd8e9f28` = `NoMembership()`** — **mesuré on-chain le 2026-10-16** (l'ancienne
valeur `0x4a0bfec1` « NotAuthorized » était une hypothèse de doc : la mesure prime,
une fois de plus) ; `members == false` vérifié
indépendamment ; **reset** exécuté (`python scripts/demo/dao_assign_roles.py --enable true` ;
contrôle : la simulation de l'agent ne rend plus `NoMembership`).

### RUN E — Journal et audit (la partie qui vend ORVYREN)

```bash
python scripts/demo/demo.py --run E --execute --case rseth --session $SESSION \
    --env-file $ENV_FILE --envelope $ENVLP
python scripts/demo/build_audit_packet.py --session $SESSION --case rseth \
    --evidence evidence --out dist/audit_packets
```

**Critères :** chaîne de hash **recalculée OK** (aucune écriture détectée) ;
**écart journal ↔ chaîne = 0** (chaque `tx_hash` relu, transferts recalculés
depuis les logs) ; le rapport affiche « **N exécutions conformes, M refus hors
chaîne, K tentatives forcées refusées par la chaîne** » ; refus et échecs listés
(première classe). Publiez ensuite le `bundle_digest` (ancrage « option ii »,
coût nul, FREEZE_V2 F3) et gardez le `sha256` du zip (`<zip>.sha256`).

---

## 7. Étape 6 — Après la démo : destruction de la clé

1. **Rôle retiré** : `assignRoles(agent, [AGENT], [false])` (c'est le reset du run D).
2. **Vérifier** `members == false` (app Roles ou probe D3) et **archiver** les
   sorties *sans* la clé (`evidence/demo_runs/…`, paquet d'audit).
3. **Supprimer** `scripts/demo/.env` (et toute copie de la clé ; vider
   l'environnement du processus signataire).
4. **Rotation** = 1 transaction de la Safe : `assignRoles(nouvelle, [AGENT], [true])`
   + `assignRoles(ancienne, [AGENT], [false])` (B5 S8). Une clé de démo compromise
   après révocation est **sans portée** : le pire cas est « au plus `maxRefill`
   par période, uniquement vers les destinataires autorisés ».

---

## 8. Pièges connus (chacun a coûté une mesure ou un échec)

| # | Piège | Ce qu'il faut faire |
|---|---|---|
| 1 | **RPC public sans `User-Agent` → HTTP 403** | le kit envoie un UA ; un `curl` nu échoue (mesuré, B6). Ne pas conclure « RPC mort ». |
| 2 | **Deux USDC distincts** (Circle vs Aave) | transferts = USDC **Circle** ; ne pas confondre les adresses (§3.2). |
| 3 | **Adresses officielles ≠ adresses du jour** | exécuter `--capture-envelope` le jour J ; un testnet peut être réinitialisé sans préavis. |
| 4 | **Module Roles = module par avatar** | déployer **sa** instance pour la Safe de démo ; ne pas réutiliser `0xF296…83D5`. |
| 5 | **`--execute` avec les placeholders** | refusé volontairement : remplir le `.env` (c'est la protection contre une démo sur des adresses factices). |
| 6 | **`eth-account` absent** | `python -m pip install eth-account` — le dry-run, lui, n'en a pas besoin. |
| 7 | **Hash de dry-run pris pour un vrai** | tout hash simulé porte `simulated: true` et un préfixe d'avertissement ; ne jamais le montrer comme preuve. |
| 8 | **Sélecteurs de la documentation** | `exactInputSingle` (`0x04e45aaf`, pas `0x414bf389`), `repay` déployé (`0x573ade81`), non-membre → `NoMembership` (`0xfd8e9f28`, **remesuré le 2026-10-16**) : la **mesure** prime sur la doc (B5 annexe E). |
| 9 | **Rafale de frontière de période** | l'enveloppe autorise jusqu'à ≈ 2 périodes ; c'est le compteur **glissant hors chaîne** qui tranche (run C5, limite assumée). |
| 10 | **Aucune expiration native** de l'allowance Zodiac | renseigner `revocation_scheduled_at` (contrôle D9) et programmer la révocation. |
| 11 | **Reorg / inclusion retardée** | le kit relit le reçu (`blockHash`, profondeur 2) ; un `status = 0x0` est un **résultat**, jamais un « ok » optimiste. |
| 12 | **Nonce** | une seule transaction en vol à la fois ; le kit lit le nonce `pending` au moment de signer. |
| 13 | **SAFE MODE inattendu en mode en ligne** | normal tant que `D3`/`D6`/`D10` sont `UNKNOWN` (probes/version/avis non renseignés) — c'est le comportement fail-closed, pas un bug. |
| 14 | **Décimales** | USDC = **6** décimales ; le kit recalcule `amount_base_units` (protection contre le calldata mal décimé) et refuse les montants non décimaux. |

---

## 9. Dépannage (codes de sortie)

| Code | Sens | Où regarder |
|---|---|---|
| `0` | succès (critères du run satisfaits) | `runs/<run>/criteria.json` |
| `1` | critères non satisfaits (ou préflight bloquant) | `runs/<run>/summary.json`, `preflight.json` |
| `2` | usage / configuration invalide (arguments, intent invalide) | message sur `stderr` |
| `3` | prérequis de signature manquants (bibliothèque, clé, réseau) | `python scripts/demo/signer.py --check` |
| `4` | configuration de session incomplète / adresses factices | `scripts/demo/.env` |

Outils utiles :

```bash
python scripts/demo/preflight.py --intent <intent.json> --env-file scripts/demo/.env \
    --envelope scripts/demo/envelope.live.json --out /tmp/preflight.json     # hors ligne
python scripts/demo/preflight.py --rpc --intent <intent.json> --env-file scripts/demo/.env \
    --envelope scripts/demo/envelope.live.json --out /tmp/preflight.json     # en ligne (lecture seule)
python scripts/demo/verify_receipt.py --receipt <recu.json> --intent <intent.json> \
    --safe 0x… --module 0x… --agent 0x… --rpc                                  # reçu + anti-reorg
python scripts/demo/demo.py --run E --dry-run --session evidence/demo_runs/rseth # export hors ligne
python scripts/demo/build_audit_packet.py --session evidence/demo_runs/rseth --case rseth
```

---

## 10. Ce que la démo ne prouve PAS (à dire avant qu'on le demande)

* pas de **prix** ni de qualité d'exécution (les prix de testnet ne sont pas des
  données de marché) ;
* pas d'**absence de bug** dans les contrats amont (deux incidents Zodiac 2026
  documentés → on suit les versions et on épingle le codehash) ;
* pas d'**expiration native** des permissions (elle n'existe pas) ;
* pas l'**annulation** d'une transaction déjà incluse ;
* pas de **performance** financière, pas de **conformité juridique** ;
* une **empreinte publiée** prouve l'intégrité et la datation du paquet, **pas sa
  véracité** (V0.2 §10.6) ;
* et le **dry-run ne prouve rien d'on-chain** : c'est une répétition.

---

## 11. Références

**Externes (consultées le 2026-10-15)** : `docs.base.org/base-chain/network-information/network-faucets`
(liste officielle des robinets) · `https://portal.cdp.coinbase.com/products/faucet`
et `https://docs.cdp.coinbase.com/faucets/introduction/welcome` (plafonds CDP :
0,0001 ETH/demande, 0,1 ETH/24 h ; 1 USDC/demande, 10 USDC/24 h) ·
`https://faucet.quicknode.com/drip` (1 drip/12 h) · `https://basefaucet.com/`
(Alchemy, 1/24 h) · `https://faucet.circle.com/` (USDC de test, **sans compte**,
20 USDC/demande, 1/2 h par couple actif-réseau) ·
`https://www.ethereum-ecosystem.com/faucets/base-sepolia` (sans login, 0,5 ETH/24 h) ·
`app.safe.global` (Safe{Wallet}) · `roles.gnosisguild.org` (app Roles, diff de politique).

**Internes** : `FREEZE_V2.md` · `ORVYREN_DOC2_TECHNIQUE_COMPLET.md` ·
`demo_runs/` (sorties d'exécution du kit : captures, préflight en ligne, dry-runs —
créé au premier lancement ; les sondes d'origine sont archivées hors dépôt).

---

## 12. FAQ — « Mais alors, un agent ne peut jamais tout faire seul ? » (captchas)

Les captchas rencontrés pendant la préparation appartiennent aux **robinets** (obtention gratuite de jetons de test) — des services web anti-abus pensés pour des humains. Ils ne sont **jamais** dans la boucle ORVYREN : données → décision → politique → exécution on-chain → audit ne contient **aucune étape humaine**, et les 5 runs de cette démo sont exécutés par le code (signataire isolé + module Roles).

Le financement est une entrée **exogène** : une trésorerie réelle est financée par des dépôts de la DAO, jamais par un robinet. Le captcha n'est qu'un artefact du **testnet** (argent sans valeur → robinets anti-bot). En production : trésorerie financée, zéro captcha.

Les deux seuls points de contact humains du dispositif sont **intentionnels** : (1) le financement initial ; (2) le **kill switch** par la DAO — c'est le second verrou du design « deux serrures » : l'agent exécute seul, dans les bornes ; la DAO peut couper.
