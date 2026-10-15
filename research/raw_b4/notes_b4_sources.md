# B4 — Notes brutes & journal des sources (politique & autorisation)

Enfant B4 · 15 octobre 2026 · chantier « bloc 4 politique & autorisation ».
Conventions : FAIT SOURCÉ = lu dans une source citée (URL + date de consultation) ; MESURÉ = chiffre produit par le dépôt/outillage interne ; PROPOSITION = choix d'ingénierie à valider.

## Sources web consultées (toutes le 2026-10-15 sauf mention contraire)

### Approbation / files d'attente
1. Safe Docs — « Transactions with off-chain signatures » : https://docs.safe.global/core-api/transaction-service-guides/transactions
   - proposeTransaction(safeAddress, safeTransactionData, safeTxHash, senderAddress, senderSignature) ; les autres signataires signent le `safeTxHash` (EIP-712 « SafeTx ») puis confirmTransaction(safeTxHash, signature) ; exécution quand le seuil est atteint (executeTransaction).
2. Safe Docs — « Propose and confirm transactions » (SDK API Kit) : https://docs.safe.global/sdk/api-kit/guides/propose-and-confirm-transactions
3. Safe Docs — « Safe Transaction Service API » (overview) : https://docs.safe.global/core-api/transaction-service-overview (service indexé par chaîne, API REST, self-host possible).
4. Coinshift Docs — « Queue | Business » : https://docs.coinshift.xyz/business/coinshift-walkthrough/transaction-management/queue
   - les tx multisig en file s'exécutent dans l'ordre des nonces ; « Approve and Execute » en une étape quand le seuil est atteint.
5. Fireblocks — « How Policies work » : https://support.fireblocks.io/hc/en-us/articles/29210922951580-How-Policies-work
   - Policy Engine : premier-match ; actions Allow / Approved by (approbateurs humains) / Block ; « default block-all » en dernière règle. Modèle initiateur → approbateur → signataire désigné.
6. Fireblocks — « Approval and signing notification expiration » : https://support.fireblocks.io/hc/en-us/articles/360015963760
   - fenêtre d'autorisation configurable : 5 min – 24 h (défaut 2 h) ; expiration des demandes de changement de politique : 7 jours ; les notifications d'approbation vivent dans l'app mobile.
7. Fireblocks — « Approval groups » : https://support.fireblocks.io/hc/en-us/articles/29184265622556-Approval-groups
8. Fireblocks — page produit « Policy and Workflow Engine » : https://fireblocks.com/platforms/governance- policy-engine (page marketing non extractible à l'outil ; non retenue comme preuve).

### Timelock / enveloppe Zodiac
9. Zodiac Docs — « Delay guide: set up and operate » : https://docs.zodiac.eco/developers/delay/guide
   - paramètres (owner, avatar, target, cooldown, expiration) ; cooldown : « common values are 1 to 7 days » ; expiration 0 = jamais expirée (bloque la file) ; annulation d'une entrée : setTxNonce(n) (tx Safe du owner, à signer pendant le cooldown) ; skipExpired() par n'importe qui ; exécution : executeNextTx(data identique). Surveillance : queueNonce/txNonce + événement TransactionAdded.
10. Zodiac Docs — « Delay Modifier reference » : https://docs.zodiac.eco/developers/delay/reference
11. (Déjà dans W2C, re-utilisé) Safe Guards : https://docs.safe.global/safe-smart-account/guards
    - Guard = vérifications avant/après une tx Safe, au-dessus du n-of-m ; un Guard cassé = DoS possible ; exemples d'implémentation : zodiac-guard-scope, Yearn. Dernière mise à jour de la page : 27 août 2026.

### Bots d'ops / notifications
12. Tenderly Docs — « Alert Destinations » : https://docs.tenderly.co/monitoring/alerts/destinations/overview
    - destinations account-scoped : email, Slack, Telegram, Discord, Sentry, PagerDuty ; project-scoped : Web3 Actions, Webhooks.
13. Tenderly Docs — « Using Alerts API » : https://docs.tenderly.co/monitoring/alerts/api.md
14. Rejeté/non retenu : blogs promotionnels « WAIaaS / Mobile-First Transaction Approvals: Push Relay + Telegram » (dev.to / waiaas.ai) — contenu commercial non vérifiable, non cité comme preuve. « WalletConnect multisig-drain via fake MEV-bot session » (onchainattack.org) — incident 2024 réel allégué, conservé comme avertissement qualitatif.

### Direction produit (approbation humaine & agents de paiement)
15. BIS — « Payments in the age of AI agents », discours de Christopher J. Waller (Fed) à Sibos 2026, publié 2026-10-05 (discours daté du 29 septembre 2026) : https://www.bis.org/speeches/20261005-payments-age-ai-agents (texte intégral récupéré, `pages/bis_waller_speech.txt`)
    - deux modèles : « agent assisted » (l'acheteur garde le contrôle et paie) vs « agent delegated » (l'agent opère de façon autonome) ; « The buyer may specify some constraints and set up guardrails, but the agent operates autonomously » ; « the delegated model requires a more extensive buildout of trust mechanisms and guardrails » ;
    - B2B : règles naturelles = « approved suppliers and budget limits » ;
    - réseaux de cartes : les specs incluent « methods of registering agents and logging cardholders' approvals to conduct agentic payments » ;
    - risques nommés : « authentication, liability, and fraud » ; modèles de fraude calibrés sur l'humain → à recalibrer pour les agents.
16. Federal Reserve — même discours, page officielle : https://www.federalreserve.gov/newsevents/speech/waller20260928a.htm (29 septembre 2026) ; PDF : https://www.federalreserve.gov/newsevents/speech/files/waller20260929a.pdf

### Produits / modèles d'approbation on-chain (contexte)
17. Llama (llamaxyz/llama) — GitHub README : https://github.com/llamaxyz/llama — « onchain governance and access control framework […] non-transferable NFTs to encode access control […] modular strategies to define action execution rules » (dépôt MIT, créé 2023-01-10). La doc produit `docs.llama.xyz` n'a pas pu être extraite (échec) → non citée.
18. BitGo — policies docs (aperçu, non extrait en détail) : https://developers.bitgo.com/docs/policies-overview.md ; « Policy approvals FAQ » : https://support.bitgo.com/support/solutions/articles/158000442219 (non retenu comme preuve principale).

### Non trouvé (recherché, pas de source solide — à ne pas inventer)
- Bot **Telegram officiel** de Safe{Wallet}/Gnosis Guild pour *approuver* une transaction multisig : non trouvé. Ce qui existe dans les résultats : blogs promotionnels, bots tiers non documentés. La notification d'ops réelle et documentée passée par un fournisseur = Tenderly (destinations Telegram/Slack) ; l'approbation réelle documentée = app/console (Fireblocks, Coinshift, Safe{Wallet}).
- Spécification d'un « lien signé » normalisé (EIP) pour l'approbation de trésorerie : non trouvé ; la primitive réelle utilisée partout = **signature EIP-712 d'un hash** (safeTxHash chez Safe) + collecte via API. Cf. aussi W2C Annexe 2 (déjà « non trouvé » côté W2C).

## Matière interne relue (dépôt D:\orvyren_core, 2026-10-15)
- `research/SYSTEME_ZONES_OMBRE.md` §4 (questions 4.1-4.3) ; §0-2 pour le contexte.
- `research/W2C_enveloppe_execution.md` : a.2 (mécanique), a.7 (limites), c.1 (alternatives), d.1-d.5 (signer, quotas, kill switch, journal), e (matrice 12 attaques), g (plan de démo, adresses vérifiées).
- `src/orvyren/policy/__init__.py` : R1-R8, codes de refus, `PolicyDecision` actuel ; `tests/test_policy.py` : 12 tests (nominal + 7 attaques + cumul + T3 + action inconnue + permission absente).
- `src/orvyren/execution/guard.py` (interdiction d'exécuter sans ALLOW, masquage des secrets) ; `execution/intents.py` (I1/I2/I3) ; `audit/dossier.py` (dossier 1 page, SHA-256).
- `ARCHITECTURE_V1.md` §2 (règle de dépendance modules), §3 (contrats : `decision → policy → execution → audit`), §4 (tables dont `intent`, `policy_decision`).
- V0.2 §10.1-10.4 (principe, pipeline, niveaux T0-T4, modèle de sécurité) — `C:\Users\User\fintechathon_recherche\orvyren_v02\ORVYREN_Document_de_reference_V0_2.txt`.
- `research/B3_DECISION_ETUDE.md` : §c.4 (ESCALATE vs NO-ACTION), §d (catalogues bornés), §e (pseudo-code 3 axes).
- `FREEZE_V1.md` D9 (six règles d'origine) / D10 (sept attaques) ; `REVUE_CROISEE_ET_CADRE_CONCRET.md` INV-AUTH.
- `evidence/policy_execution_demo.json` (démo I1/I2/I3, dry_run) ; banc complet : `python -m pytest tests/ -q` → **221 passed, 2 skipped** (15/10/2026).

## Décisions de travail prises pendant l'étude (à porter en §(g) du livrable)
- Numérotation du set final : P1-P14 (les règles codées R1-R8 restent citées par leur nom de code pour la traçabilité).
- Codes de refus : SCREAMING_SNAKE_CASE, stables, jamais renommés (on ajoute un code, on ne réécrit pas l'historique).
- Le compteur « glissant 24 h » strict vit hors chaîne (limite Zodiac assumée : rafale de frontière `maxRefill + refill`, W2C e #2).
- La fraîcheur de l'intent (P9) et le plafond d'exposition (P7) sont des ajouts v1 non encore codés.
- Le test de dérive Zodiac : rapport JSON + mode SAFE (refus de tout autonome) si divergence ou si la vérification est impossible.
