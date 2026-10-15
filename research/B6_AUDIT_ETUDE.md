# B6 — ÉTUDE DU BLOC AUDIT & VÉRIFIABILITÉ (journal unifié, vérificateur tiers T10, ancrage, paquet jury)

**Date : 15 octobre 2026.** Chantier : `research/SYSTEME_ZONES_OMBRE.md` §6 « AUDIT & VÉRIFIABILITÉ — la promesse du produit » (questions 6.1 → 6.3). C'est le troisième bloc traité après B1 (agents), B2 (graphe), B3 (décision), conformément à l'ordre §9.1 de la carte.
**Objet** : produire la matière permettant de **trancher** le bloc Audit — l'unique promesse centrale du produit (« laisse une trace qu'un tiers peut recalculer ») — pour la démo ET pour l'inférence.
**Périmètre** : (a) journal unifié des 3 flux + format d'export ; (b) spécification du **vérificateur tiers T10** (essai non négociable) ; (c) décision d'ancrage (EAS ou pas) ; (d) messages de preuve exacts ; (e) paquet livrable jury ; (f) questions ouvertes.
**Hors périmètre** : l'implémentation (phase recherche) ; le choix des modèles (B1) ; le schéma du graphe (B2) ; la généralisation de la décision (B3).

**Convention de preuve** — chaque affirmation externe porte une URL et une date de consultation. Statuts : **[FAIT SOURCÉ]** (vérifiable à l'URL citée, consultée le 2026-10-15 sauf mention) · **[MESURÉ]** (exécution reproductible du 2026-10-15, fichier de sauvegarde indiqué) · **[CONCEPTION]** (choix de conception proposé, non décidé) · **[PROPOSITION]** (recommandation à valider en revue) · **[HYPOTHÈSE]** · **[NON TROUVÉ]** (cherché, pas trouvé — jamais comblé par une supposition).
**Matière brute** : `research/raw_b6/` (contrôle hors-ligne du dossier v1, sondage EAS Base Sepolia, notes de contexte — voir Annexe A).
**Ce document ne commit rien et ne modifie aucun autre fichier du dépôt** (la matière brute vit sous `research/raw_b6/`).

---

## 0. Résultat principal (à lire seul si pressé)

Le bloc Audit ne demande **aucune techno nouvelle** : la pièce centrale existe déjà (dossier v1 à self-hash reproductible, vérifié à nouveau hors-ligne aujourd'hui [MESURÉ]) et les deux autres flux ont un design écrit (B1 §3, W2-C §d.5). Ce qui manque est (1) **le dossier de décision comme agrégat à 3 flux avec chaînage inter-flux**, (2) **le vérificateur T10**, (3) **la décision d'ancrage**. Ce document ferme ces trois questions.

| # | Recommandation | Fondement |
|---|---|---|
| **R-1** | **Journal unifié = trois journaux chaînés par run, réunis par un manifeste** : `audit.jsonl` (exécution, façon W2-C §d.5), `agent_journal.jsonl` (raisonnement, façon B1 §3.4), `graph_delta.jsonl` + `graph_snapshot.json` (connaissance, façon B2 §7.5). Chaînage **intra-flux** : `record_hash = sha256(canonical_json(record \ {record_hash}))`, `prev_hash` par flux, genèse `64×0`. Chaînage **inter-flux** : à la clôture, un `manifest.json` fixe les têtes (`head_hash`) et les compteurs des 3 flux ; `audit.jsonl` reçoit 3 enregistrements `LINK` + 1 `SEAL{manifest_sha256}` — le DAG est **acyclique par construction** (les flux ne référencent jamais le manifeste ; le manifeste ne référence jamais le dossier ; le dossier référence le manifeste comme entrée). | §1 ; W2-C §d.5 ; B1 §3.4 ; B2 §7.5 ; contrôle v1 [MESURÉ] |
| **R-2** | **Standardiser sur SHA-256** (pas keccak) pour toutes les chaînes du journal et les empreintes du paquet : stdlib uniquement, vérifiable par tout outil (`sha256sum`), indépendant de l'EVM (un ancrage EAS ne stocke qu'un `bytes32`, la fonction de hachage est indifférente). **Correction à porter** dans W2-C §d.5 qui écrit `keccak(prev_hash‖record)`. | Python stdlib ; `dossier.py` (SHA-256) [code] ; EAS `bytes32` |
| **R-3** | **Le livrable auditable est un DOSSIER (bundle), pas un fichier** : `audit_packet_<case>_<run8>/` avec `README_AUDIT.md` (EN), `dossier_<case>.{md,html}`, JSON sources, les 3 journaux, `manifest.json`, `receipts/`, `policy/`, `HASHES.txt`, `orvyren_verify.py` gelé + son empreinte. Zip nommé et hashé. | §1.5 ; AV1 (langues : docs EN) |
| **R-4** | **Vérificateur T10 = `python -m orvyren.verify <cible>`**, stdlib uniquement, modes `--offline` (défaut) / `--rpc` / `--mutate-test`, rapport `verify_report.json` (verdict par contrôle + verdict global `PASS/OFFLINE_PASS/FAIL`) ; distribution **double** : module du dépôt + **copie gelée** dans le paquet (même fichier, empreinte listée). | §2 ; REVUE CROISÉE §4 (T10) |
| **R-5** | **Trois classes de vérifiabilité, écrites noir sur blanc** : (A) **recalculable bit-à-bit hors-ligne** (chaînes de hash, self-hash du dossier, re-rendu du dossier depuis le JSON, verdicts de politique, snapshot du graphe, signaux reconstruits des fixtures) ; (B) **revérifiable** (le fait on-chain : `eth_getTransactionReceipt`, logs `Transfer`, allowances — et re-lecture `eth_call` au bloc sur RPC archive, identique « au bit près » [MESURÉ W3]) ; (C) **non rejouable — couvert par le journal** (appels LLM : prompt/réponse archivés et hashés, validateurs déterministes rejoués ; le texte LLM lui-même n'est pas re-dérivable). | §2.2 ; W3 §2.3 [MESURÉ] ; B1 §6 |
| **R-6** | **Ancrage v1 : publier l'empreinte (option ii) — obligatoire, coût nul — et ancrer EAS (option iii) seulement si 3 conditions vertes** : run E vert, vérificateur T10 vert, ≥ J-1 avant soumission (20/10 15:59 UTC). EAS **Base Sepolia** : contrats présents et vérifiés on-chain aujourd'hui [MESURÉ] ; coût mesuré ≈ 6 000 000 wei/gaz, `≈ 0,0000007–0,0000015 ETH` par attestation [HYPOTHÈSE gaz]. L'ancrage est **additif**, jamais une dépendance du flux. | §3 ; V0.2 §10.6 ; AV1 §6 |
| **R-7** | **Texte exact de preuve** (§4) : « Prouve » = 8 affirmations (intégrité, reconstruction, correspondance intention↔exécution, bornage du mandat, PIT, refus conservés, imputabilité) ; « Ne prouve pas » = 8 limites (véracité des sources, justesse des hypothèses, performance, exhaustivité hors signer, bugs amont, conformité juridique…). Fourni en **FR (interne) et EN (paquet)** prêt à recopier. Aligné sur INV-PIT, INV-AUTH, INV-INTEGRITY, INV-ACCOUNTING, INV-DEPENDENCE. | §4 ; RC §2.4 ; W2-C §f |
| **R-8** | **Paquet jury** : 12 pièces + checklist de vérification en 3 commandes + 1 page « ce que ça prouve » (§5). | §5 |
| **R-9** | **Questions ouvertes** : rédaction/publication du journal (extrait vs intégral), qui signe l'ancre, réorg/confirmation, audit de l'auditeur, langue, gel. | §6 |

**Ce qui bloque encore** : (a) la démo n'a pas encore produit `audit.jsonl` réel (run E non exécuté — dépend du wallet testnet financé, côté utilisateur) ; (b) le vérificateur n'existe pas dans le code (`src/orvyren/` n'a ni `verify/` ni `audit/bundle` — constat identique à B1 §0 R-7) ; (c) la décision d'ancrage dépend de la posture « menaces le flux vertical ? » de V0.2 §10.6, traitée en R-6 par une condition explicite.

### 0.1 État des lieux mesuré (ce qui existe déjà, re-vérifié le 2026-10-15)

1. **Dossier v1** (`evidence/dossier_usdc-2023-03.md` + `.html`) : la règle de self-hash (« champ remis à 64 `0`, puis SHA-256 ») **se vérifie hors-ligne avec n'importe quel outil** — reproduction exacte des deux empreintes embarquées (`73399190…e8ac7` et `7a609a14…c3f89`), et les 3 SHA-256 d'entrée déclarés dans la table « Evidence & integrity » se recalculent [MESURÉ, `raw_b6/dossier_v1_verification*.json`]. Le dossier v1 est donc déjà la brique « pièce à hash reproductible » ; il manque l'agrégation des flux.
2. **Exécution** : W2-C §d.5 spécifie `audit.jsonl` chaîné (INTENT / POLICY / SIMULATION / SUBMIT / RECEIPT / VERIFY) et §g.6 l'export + relecture indépendante ; rien n'est encore produit (run E à exécuter).
3. **Raisonnement** : B1 §3.4 spécifie la table `agent_journal` (25 champs, `prev_hash`, `prompt_hash`/`response_hash`, payloads en magasin immuable) ; non construite, non bloquante pour la démo sans LLM.
4. **Connaissance** : le graphe SQLite est append-only (triggers `UPDATE`/`DELETE` interdits), `snapshot()` produit un hash SHA-256 stable, `verify_chain` résout les références de claims [code]. B2 propose le delta par run et le snapshot figé par décision.
5. **Rien n'existe** pour : le **manifeste** de run, le **chaînage inter-flux**, le **vérificateur**, l'**ancrage**. C'est l'objet de ce document.

---

## 1. (a) JOURNAL UNIFIÉ — trois flux, un dossier de décision, une chaîne inter-flux

### 1.1 Les trois flux : ce que chacun porte, et pourquoi il ne peut pas être fusionné

| Flux | Responsabilité | Portée (exemples) | Écrit par | Base design |
|---|---|---|---|---|
| **1. Raisonnement** (`agent_journal`) | Ce que les agents ont pensé/fait à chaque étape : plans, appels d'outils, réflexions, propositions, quarantaines | `PLAN`, `TOOL_CALL`, `TOOL_RESULT`, `OBSERVATION_REF`, `REFLECTION`, `HYPOTHESIS_PROPOSED`, `CRITIQUE`, `STOP`, `ERROR` ; `llm{provider, model, pinned, temperature, seed_or_null}`, `prompt_hash`/`response_hash`, tokens, coût, latence, `status ∈ {PROPOSED, ACCEPTED, REJECTED, QUARANTINED}` | chaque agent (1 écrivain par agent) | B1 §3.4 |
| **2. Connaissance / provenance** (`graph_*`) | Les faits et leurs liens, horodatés, révisables, avec snapshots | `source → observation → extraction → claim → relation → hypothèse` ; révisions append-only ; `graph_delta.jsonl` = objets créés/révisés par le run ; `graph_snapshot.json` = état figé + `snapshot_hash` | pipeline `quality`/`graph` (seul `graph.store` écrit la base) | B2 §2.4/§7.5 |
| **3. Exécution on-chain** (`audit.jsonl`) | Chaque étape d'intention → autorisation → envoi → reçu, vérifiée contre la chaîne | `INTENT`, `POLICY` (verdict + règles + `policy_version`), `SIMULATION`, `SUBMIT` (`tx_hash`), `RECEIPT` (statut, bloc, logs, soldes, allowance), `VERIFY` (`recomputed_from_chain`) | le pipeline d'exécution (1 écrivain) | W2-C §d.5/§g.6 |

**Pourquoi trois flux séparés** (décision, pas subie) : (i) un lecteur externe doit pouvoir lire *l'exécution* seule (la plus vérifiable) — R-5 ; (ii) le raisonnement **n'alimente jamais** la décision (règle B1 §3.3 : « le moteur de décision ne lit jamais les journaux » ; seuls les objets promus par validateurs entrent dans le graphe) — donc le mélanger aux faits détruirait l'invariant « aucun chiffre ne vient du LLM » ; (iii) la littérature identifie la cohérence multi-journal comme problème ouvert [FAIT SOURCÉ : arXiv:2603.10062, 2026-03-09 ; arXiv:2606.24535, 2026-06-23, cf. B1 §1.3] — la réponse retenue est **un journal par flux, un manifeste unique, un chaînage inter-flux explicite** (§1.4), pas une mémoire partagée.

**Le point de jonction est le dossier de décision** (`decision_<case>.json` + rendu `dossier_<case>.{md,html}`) : c'est l'objet que les trois flux *servent*, et c'est lui qui devient public. Les flux ne se référencent pas entre eux par pointeurs bidirectionnels (sinon DAG cyclique) ; ils se rejoignent **par le manifeste de run** (§1.4).

### 1.2 Principes non négociables du journal

1. **Append-only strict** : aucune ligne réécrite ; une correction est une nouvelle ligne (`supersedes`), comme le graphe (triggers) et comme la règle « si on peut `UPDATE`, ce n'est pas une piste d'audit » (B1 §3.2).
2. **JSONL, UTF-8, une ligne = un enregistrement**, clés triées à l'écriture ; **canonicalisation** : `json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))` (même règle que `graph/models.py.canonical_json` [code]).
3. **SHA-256 partout** (R-2) ; hexadécimal minuscule, 64 caractères ; préfixe matière optionnel `sha256:` interdit dans le champ lui-même (hex nu, comme le dossier v1).
4. **Horodatage** : `ts_utc` ISO-8601 `Z` ; en mode replay, l'horloge **simulée** est utilisée et l'étiquette `mode ∈ {LIVE, REPLAY_JOURNAL, LIVE_REPLAY, FIXTURES}` est obligatoire sur chaque enregistrement (V0.2 §13.3 ; B1 §6.3).
5. **Versionnement** : `v` (format), `run_id` (ULID), `episode`, `policy_version`, `engine_version`, `role_version` (prompts), `schema_version` des objets. Rien d'implicite.
6. **Un seul écrivain par flux** ; le manifeste est écrit par l'orchestrateur ; les trois flux ne s'écrivent jamais les uns les autres.
7. **Aucun secret** : jamais de clé, jamais de contenu d'`.env`, jamais de donnée personnelle ; le journal est destiné à être publié intégralement (voir QO-1 pour la rédaction éventuelle).
8. **Le refus est un résultat** : `DENY`, `REJECTED`, `QUARANTINED`, `ERROR` sont conservés et comptés (carte §6 ; B1 §3.6).

### 1.3 Enveloppe commune et exemples

**Enveloppe** (identique dans les 3 flux ; le `payload` diffère) :

```json
{
  "v": 1, "stream": "exec|agent|graph", "seq": 17,
  "run_id": "01JAV7Q0AA", "episode": "usdc-2023-03", "mode": "REPLAY_JOURNAL",
  "ts_utc": "2026-10-15T12:00:01Z",
  "kind": "RECEIPT",
  "agent_id": null,            // flux agent uniquement
  "payload": { "...": "spécifique au flux" },
  "refs": {"intent_id": "0x…", "decision_sha256": "…", "snapshot_id": "…", "graph": ["claim:…", "observation:…"]},
  "prev_hash": "7c11…", "record_hash": "9ae2…"
}
```

**Règle de hash** (reproductible par tout tiers) :

```
record_hash = SHA256( canonical_json( record sans le champ record_hash ) )
prev_hash   = record_hash de l'enregistrement précédent DU MÊME FLUX
genèse      = prev_hash = "0"×64
```

**Exemple flux exécution** (reprend W2-C §d.5) :

```json
{"v":1,"stream":"exec","seq":1,"run_id":"01JAV7Q0AA","kind":"INTENT",
 "payload":{"intent_id":"0x9f…","intent":{"action":"transfer","asset":"USDC","amount":50,"recipient":"0xB"}},
 "refs":{"decision_sha256":"b65c…","policy_version":"v1.3"},"prev_hash":"0…0","record_hash":"…"}
{"v":1,"stream":"exec","seq":2,"kind":"POLICY",
 "payload":{"verdict":"ALLOW","rules":[{"id":"cap_tx_100","ok":true},{"id":"rolling_24h_300","ok":true}]},…}
{"v":1,"stream":"exec","seq":3,"kind":"RECEIPT","payload":{"tx_hash":"0x…","status":1,"block":48133012,
 "logs":[{"address":"0x036C…","topic0":"0xddf2…","from":"0xSafe…","to":"0xB","value":"50000000"}],
 "balances_after":{"safe":"…","B":"…"},"allowance_after":{"usdc_daily":"250000000"}},…}
{"v":1,"stream":"exec","seq":4,"kind":"VERIFY","payload":{"recomputed_from_chain":true,"mismatches":[]},…}
```

**Exemple flux agent** (champs de B1 §3.4 conservés tels quels) : ligne `REFLECTION` avec `content`, `refs`, `status: PROPOSED`, `validation{schema_ok,no_number_ok,provenance_ok,motif}`, `llm{…}`, `prompt_hash`, `response_hash`, tokens/coût ; les **payloads bruts** (prompt complet + réponse) vivent dans le magasin immuable `payloads/<sha256>.json` — le journal ne transporte que les hash (B1 §3.4).

**Exemple flux graphe** : `graph_delta.jsonl` = une ligne par objet créé/révisé, `{"obj":"claim:01J…","op":"INSERT|REVISE","revision":3,"refs":[…]}` ; `graph_snapshot.json` = `{"snapshot_id":"…","as_of":"…","graph_version":…,"rows_hash":"…","counts":{…},"objects":[…]}` — `rows_hash` = `snapshot_hash` du store [code].

### 1.4 Chaînage entre flux — le DAG de commit (règle exacte)

**Problème** : si chaque flux référençait les hash des autres, on crée des cycles (A attend B, B attend A). La solution retenue est un **DAG orienté en deux temps**, avec un manifeste au sommet :

```
  ① pendant le run (dirigé vers l'amont, jamais vers l'aval) :
     exec  ──refs──▶ decision_sha256, intent_id, snapshot_id
     agent ──refs──▶ object ids du graphe (observation:…, claim:…), run_id
     graph ──refs──▶ source ids, révision précédente (chaîne SUPERSEDES)
  ② à la clôture (fige les têtes) :
     manifest.json  = { streams: {exec: {path, records, head_hash},
                                  agent: {…}, graph: {snapshot_hash, records, head_hash}},
                        decision_sha256, policy_version, engine_version, rpc{endpoints, chain_id, blocks},
                        files: [(path, sha256)…], mode }
  ③ puis, dans audit.jsonl uniquement (déjà clos pour les autres flux) :
     3 × LINK {"stream":"agent","records":137,"head_hash":"…"}   ← lie la chaîne exec aux têtes des autres
     1 × SEAL {"manifest_sha256":"…","decision_sha256":"…"}
  ④ enfin :
     dossier_<case>.{md,html} : le manifeste est déclaré en ENTRÉE du dossier ⇒ son sha256
       apparaît dans la table « Evidence & integrity », et le self-hash du dossier couvre la table.
```

Propriétés (à tester, cf. §2) : (P1) **acyclique** — aucun objet ne référence un objet construit après lui ; (P2) **anti-altération transitive** — modifier une ligne du flux agent casse sa chaîne, donc `head_hash`, donc le manifeste, donc la table du dossier et son self-hash ; (P3) **vérifiable par morceaux** — un tiers peut vérifier chaque flux indépendamment puis la jonction.

**Règles d'écriture** (à figer) :
- `manifest.json` ne liste **jamais** l'empreinte du dossier ni sa propre empreinte ;
- le dossier liste le manifeste comme entrée (mécanisme existant des `extra_paths` de `dossier.build` [code]) ;
- les enregistrements `LINK`/`SEAL` ne contiennent **que** des valeurs déjà figées ;
- en l'absence d'un flux (v1 sans LLM), on l'**écrit dans le manifeste** : `agent: {"absent": true, "reason": "aucun LLM dans ce run (mode déterministe)"}` — jamais de flux vide simulé (critère « pas de placeholder », V0.2 §13.3).

### 1.5 Format d'export — le dossier de décision devient un ensemble

**Arborescence exacte du paquet** (nom proposé : `audit_packet_<case>_<yyyymmdd-hhmm>_<run8>/`, zippé) :

```
audit_packet_usdc-2023-03_20261018-1200_01JAV7Q0/
├── README_AUDIT.md            # EN — 3 commandes pour vérifier, ce que ça prouve / pas (texte §4 EN)
├── HASHES.txt                 # sha256 de chaque fichier du paquet (sauf lui-même) + bundle_digest
├── manifest.json              # le manifeste de run (têtes des flux, versions, RPC, fichiers)
├── dossier_usdc-2023-03.md    # 1 page, self-hash (règle v1), EN pour la soumission
├── dossier_usdc-2023-03.html  # idem, autonome
├── decision_usdc-2023-03.json # sortie du moteur (vérité machine du dossier)
├── baseline_report.json       # A0 (comparateur)                     ┐
├── quality_report.json        # qualité des données                  ├ entrées du dossier (extras)
├── policy_execution_demo.json # verdicts R1–R8 sur cas figés         ┘
├── audit.jsonl                # flux 3 — exécution (chaîné) + LINK + SEAL
├── agent_journal.jsonl        # flux 1 — raisonnement (chaîné)  [ou déclaré absent au manifeste]
├── graph/
│   ├── graph_delta.jsonl      # flux 2 — objets créés/révisés par le run (chaîné par flux)
│   ├── graph_snapshot.json    # état figé + snapshot_hash
│   └── provenance.json        # chaînes de provenance résolues (verify_chain) + références pendantes = []
├── receipts/
│   ├── <tx_hash>.json         # reçu brut JSON-RPC (eth_getTransactionReceipt, tel quel)
│   └── <tx_hash>.meta.json    # {chain_id, rpc, block_hash, fetched_at, confirmation_depth}
├── policy/
│   ├── policy.yaml            # politique hors-chaîne versionnée (plafonds, allowlist, TTL)
│   ├── policy_version.txt
│   └── roles_snapshot.json    # état lu du module Zodiac (rôles, allowances) au bloc X + app URL du diff
├── verify/
│   ├── orvyren_verify.py      # copie gelée du vérificateur (stdlib) + sha256 dans HASHES.txt
│   └── VERIFY_EXPECTED.txt    # sortie attendue sur ce paquet (garde-fou anti-« ça ne marche que chez vous »)
└── anchor/                    # optionnel (option iii) — voir §3
    └── eas_attestation.json   # {chain:84532, tx_hash, attestation_uid, schema_uid, anchored_digest}
```

**Règles d'export** :
- **Nommage** : l'épisode + l'horodatage + le `run_id` court ; le zip porte le même nom + `.zip` ; son sha256 est publié (R-6, option ii).
- **Hashs** : `HASHES.txt` liste `path  sha256` (texte normalisé LF, comme `dossier.sha256_file` [code]) pour tous les fichiers **sauf lui-même** ; `bundle_digest = sha256(canonical_json(sorted([(path, sha)…] sans `dossier_*.{md,html}` et sans `HASHES.txt`)))` — le **digest machine** qui sert d'ancre (§3). Le dossier, lui, n'entre pas dans ce digest (sinon cycle) ; il est couvert par le zip et listé dans `HASHES.txt`.
- **Le zip doit être ouvert/vérifiable sans nous** : README + vérificateur + `VERIFY_EXPECTED.txt` inclus ; pas d'outil maison requis au-delà de Python 3 stdlib.
- **Langue** : README, dossier rendu, rapport de vérification = **EN** (exigence du concours, AV1 §5) ; ce document d'étude et les notes restent FR.

### 1.6 Niveau de détail requis pour qu'un reviewer externe comprenne sans nous

Critère mesurable (à utiliser tel quel dans le paquet) — un reviewer qui n'a jamais parlé à l'équipe doit pouvoir répondre **seul** aux 10 questions suivantes, chaque réponse pointant une pièce précise du paquet :

1. **Qui a décidé ?** → `decision_*.json` : verdict épistémique, action, rationale, limites (3 axes : `epistemic_verdict`, `economic_action`, `authorization_verdict` — B3 §c).
2. **Sur quelles preuves ?** → graphe : chaîne `observation → claim → hypothèse`, chaque fait avec source + `retrieved_at` + bloc/venue.
3. **Ce qui a été exclu et pourquoi** → contradictions, quarantaines, `non_recherché[]`, budget épuisé (les refus sont dans les journaux).
4. **Pourquoi cette action passe la politique** → `POLICY` de `audit.jsonl` avec les règles R1–R8 une par une + `policy_version` + `policy.yaml`.
5. **Ce qui s'est réellement passé on-chain** → `receipts/` + `RECEIPT` croisé (receipt ↔ intention) — vérifiable indépendamment.
6. **Quel était le mandat exact** → `policy/roles_snapshot.json` (rôle, cibles, fonctions, allowances) + diff public de l'app Roles.
7. **Ce que le raisonnement a proposé et ce qui a été retenu/jeté** → `agent_journal.jsonl` (`PROPOSED` vs `ACCEPTED`/`REJECTED`/`QUARANTINED`).
8. **Quelles versions ont produit tout ça** → manifeste (engine, policy, prompts, modèles épinglés, RPC, blocs).
9. **Qu'est-ce qui est recalculable, revérifiable, non rejouable** → `verify_report.json` classe chaque contrôle (A/B/C, R-5) et chaque élément non rejouable est nommé.
10. **Comment je vérifie moi-même, sans vous ?** → `README_AUDIT.md` + `orvyren_verify.py` + `VERIFY_EXPECTED.txt`.

Si une question n'a pas de réponse « pièce précise, pas prose », le paquet n'est pas prêt (règle de sortie de l'essai T10, §2.9).

---

## 2. (b) VÉRIFICATEUR TIERS (essai T10) — spécification de l'outil

### 2.1 L'exigence (gelée d'avance, citation)

- **T10 (HYP-10R), priorité P0, non négociable** : « Un tiers recalcule **sans réseau** chaque **calcul déterminant** (recette, entrées, version, sortie) ; toute **mutation d'entrée** détectée ; **zéro référence pendante**. » [FAIT SOURCÉ interne : `REVUE_CROISEE_ET_CADRE_CONCRET.md` §3.2, 15/10/2026]
- **Protocole minimal gelé** : « Cas nominal archivé + donnée absente + donnée invalide ; exporter chaque calcul déterminant avec recette et entrées ; recalculer sans base préfabriquée ni réseau ; perturber une entrée. **Succès** : 100 % des calculs déterminants recomputés ; mêmes verdicts ; chaque mutation détectée ; zéro référence pendante. » [idem, §4]
- C'est aussi l'essai qui satisfait la promesse produit et le critère « pas de placeholder » : le vérificateur ne doit **pas** être un script qui « fait semblant » — il relit des fichiers et recalcule (§4 R-7 pour la formulation publique).

### 2.2 Ce qui est recalculable bit-à-bit, ce qui est revérifiable, ce qui n'est pas rejouable

| Classe | Définition opérationnelle | Éléments du paquet | Preuve exigée | Fondement |
|---|---|---|---|---|
| **A — Recalculable bit-à-bit (hors-ligne)** | Mêmes entrées + même code (versionné) ⇒ **même sortie mesurée au bit**, sans réseau | (A1) chaînes de hash des 3 flux + `head_hash` ; (A2) self-hash du dossier md/html ; (A3) SHA-256 des entrées listés dans le dossier ; (A4) **re-rendu du dossier** depuis `decision_*.json` (+extras) avec `generated_at` figé ⇒ fichier identique ; (A5) **verdicts de politique** recalculés par `orvyren.policy` sur les intentions enregistrées ⇒ mêmes ALLOW/DENY + mêmes règles ; (A6) **hash de snapshot** du graphe recalculé depuis `graph_snapshot.json` ; (A7) signaux reconstruits depuis les fixtures archivées (`--from-cache`) ⇒ mêmes valeurs ; (A8) `verify_receipt(intent, receipt)` pur ⇒ mêmes mismatchs | Recalcul local, comparaison d'octets/hex ; aucune dépendance réseau | [MESURÉ] v1 : self-hash reproduit (aujourd'hui) ; [MESURÉ] W3 : reconstruction relancée « identique au bit près » ; [code] `dossier.py` déterministe par conception |
| **B — Revérifiable (et re-calculable via archive)** | Le **fait on-chain** n'est pas dans le paquet : il est **relu à la source**. Sur RPC archive, un `eth_call` au bloc X est immuable ⇒ re-mesurable (et reproductible bit-à-bit au sens des valeurs, modulo RPC menteur) | (B1) `eth_getTransactionReceipt` : statut, bloc, logs `Transfer` ↔ intention ; (B2) soldes avant/après (`balanceOf`) ; (B3) allowance du module Zodiac après exécution ; (B4) `eth_call` re-mesuré aux blocs enregistrés (réserves, oracles — épisodes W3 ; `ConsumeAllowance`) ; (B5) présence des contrats (adresses figées dans le manifeste) | Relire via `--rpc` (le vérificateur **refuse** de conclure « PASS » global sans réseau ; verdict séparé `CHAIN_PASS/CHAIN_UNAVAILABLE`) | [MESURÉ] W3 §2.3 : 1 538 appels relancés, chiffres identiques au bit près ; W2-C §g.2 : procédure de recoupement |
| **C — Non rejouable — couvert par le journal** | Le texte d'un LLM **n'est pas re-dérivable** (non-déterminisme d'inférence documenté, B1 §6.2) : on ne peut pas exiger le recalcul. La couverture exigée est : chaque appel est **enregistré** (prompt/réponse + hash + modèle épinglé), et tout ce qui en **dépend** est recalculable (validateurs, verdicts, décisions) | (C1) `agent_journal` : `llm{}`, `prompt_hash`, `response_hash` + payloads `payloads/<sha>.json` ⇒ le vérificateur recompose la chaîne : hash(payload) == hash déclaré == refs cohérentes ; (C2) validateurs déterministes rejoués sur les réponses **enregistrées** (schéma, « pas de chiffre LLM », provenance) ⇒ mêmes statuts qu'enregistrés ; (C3) verdict explicite dans le rapport : `NOT_REPLAYABLE (covered by journal)` | Rapport : chaque élément C nommé + vérifié en couverture (hash + validateurs), jamais présenté comme « recalculé » | [FAIT SOURCÉ] B1 §6.2 (Thinking Machines 2025-09-10, arXiv:2601.17768, arXiv:2606.08998) ; V0.2 §12.4 (« lorsqu'une bibliothèque le permet ») |

**Règle d'honnêteté** : le rapport n'utilise **jamais** un mot (recalculé/rejoué) au-delà de la classe réellement atteinte. Trois statuts par contrôle : `RECOMPUTED`, `REVERIFIED`, `COVERED (journal)`.

### 2.3 Spécification de l'outil — CLI, entrées, sorties

**Invocation** (le contrat demandé) :

```bash
python -m orvyren.verify <cible> [--offline|--rpc] [--rpc URL] [--manifest-only]
                        [--json <rapport.json>] [--mutate-test] [--strict] [--quiet]
```

- `<cible>` = `audit_packet_*.zip` **ou** le dossier décompressé **ou** un duo `--decision <json>` (cas minimal du dossier v1 seul).
- `--offline` (**défaut**) : aucun accès réseau ; tout contrôle B est marqué `SKIPPED (offline)`.
- `--rpc [URL]` : active les contrôles B (défaut : liste du manifeste, repli contrôlé ; `User-Agent` obligatoire — [MESURÉ] le RPC public Base Sepolia renvoie 403 sans, cf. `raw_b6/notes_00_contexte.md` §2.2).
- `--mutate-test` : rejoue l'outil sur **copies mutées** du paquet (6 mutations, §2.7) et exige la détection de chacune — c'est l'auto-test T10.
- `--strict` : échec si un élément C n'a pas de couverture journal complète.

**Entrées** : (1) le paquet ; (2) **sources publiques** = RPC (liste figée au manifeste, avec `chain_id` épinglé : refus si ≠ 84532/8453 ; **blocs** figés pour les `eth_call`) ; (3) rien d'autre — **pas de base préfabriquée** (exigence T10) : le graphe est relu depuis `graph_snapshot.json`, jamais depuis `graph.sqlite` du producteur ; (4) le code : module `orvyren` du dépôt **ou** copie gelée du paquet (même fonction `main`).

**Sorties** :
- `verify_report.json` (machine) — schéma :

```json
{
  "v": 1, "generated_at_utc": "…", "target": "audit_packet_…zip",
  "verifier": {"version": "…", "sha256": "…", "mode": "offline|rpc"},
  "verdict": "PASS | OFFLINE_PASS | FAIL",
  "checks": [
    {"id":"A1.exec.chain","class":"A","status":"RECOMPUTED","ok":true,
     "detail":{"records":42,"head_expected":"…","head_computed":"…"}},
    {"id":"B1.receipt.0x…","class":"B","status":"REVERIFIED","ok":true,
     "detail":{"block":48133012,"status":1,"transfer":{"to":"0xB","value":"50000000"}}},
    {"id":"C1.llm.journal","class":"C","status":"COVERED","ok":true,
     "detail":{"calls":137,"payloads_hashed":true,"validators_replayed":true}},
    {"id":"A3.inputs.sha256","class":"A","status":"RECOMPUTED","ok":false,
     "detail":{"path":"decision_usdc-2023-03.json","declared":"…","actual":"…"}}
  ],
  "dangling_refs": [], "mutations": [], "summary": {"A": 12, "B": 4, "C": 1, "failed": 0}
}
```
- **rapport lisible** `verify_report.md` (mêmes données, sections A/B/C, verdict global ET par classe) ;
- **code de sortie** : `0` = tout vert ; `1` = échec d'intégrité/cohérence ; `2` = usage ; `3` = réseau indisponible en mode `--rpc` (les contrôles A restent rendus).
- **Déterminisme de l'outil lui-même** : même cible ⇒ même `verify_report.json` hors `generated_at_utc` (champ exclu du rapport de référence).

### 2.4 Les 8 calculs déterminants (classe A) — liste à figer et à geler

| Id | Calcul déterminant | Entrées | Recette (versionnée) | Sortie comparée |
|---|---|---|---|---|
| A1 | Chaînes des 3 flux | journaux | `record_hash` recalculé ligne à ligne ; `head_hash` recalculé | hex identiques ; zéro rupture |
| A2 | Self-hash dossier | dossier md/html | champ 64 `0` puis SHA-256 (règle v1) | hex embarqué |
| A3 | SHA-256 des entrées du dossier | fichiers du paquet | LF-normalisation puis SHA-256 | table « Evidence & integrity » |
| A4 | Re-rendu du dossier | `decision_*.json` + extras + `generated_at` du manifeste | `orvyren.audit.dossier.build` (version au manifeste) | **fichiers identiques octet à octet** |
| A5 | Verdicts de politique | intentions de `audit.jsonl` + `policy.yaml` | `orvyren.policy` (R1–R8) | verdicts + règles, un par intention ; les DENY aussi |
| A6 | Snapshot du graphe | `graph_snapshot.json` | `snapshot_hash` (règle du store) | hex `rows_hash` |
| A7 | Signaux reconstruits | fixtures archivées | scripts de reconstruction (`--from-cache`) | valeurs clés (tolérance 0 sur les champs sourcés ; comparaison champ à champ) |
| A8 | Croisement intention ↔ reçu (pur) | intention + reçu | `execution.verify.verify_receipt` | `ok` + mismatchs |

**Cas limites exigés par T10** (les trois fixtures de l'essai) : **nominal** (le paquet réel), **donnée absente** (retirer un fichier ⇒ rapport le nomme, verdict FAIL, pas d'exception), **donnée invalide** (JSON corrompu ⇒ idem) ; **perturbation** (§2.7).

### 2.5 Contrôles B (revérification en ligne) — règles exactes

1. `eth_chainId` du nœud == `chain_id` du manifeste (refus sinon : `ROGUE_RPC`) ;
2. pour chaque `RECEIPT` : `eth_getTransactionReceipt(tx_hash)` → `status`, `blockNumber`, `blockHash`, `logs` ;
   - `blockHash` du reçu doit correspondre au bloc attendu au moment de la vérification si la chaîne n'a pas reorgé (sinon `REORG_SUSPECT` + profondeur affichée — politique de confirmation à figer, QO-5) ;
   - le log `Transfer` (topic0 `0xddf252ad…` [code]) est décodé et comparé à l'intention (jeton, émetteur, destinataire, montant en unités de base) — mêmes règles que `verify_receipt` ;
3. `balanceOf` avant/après (au bloc du reçu −1 / au bloc du reçu) relus et comparés aux valeurs enregistrées ;
4. état des allowances du module Zodiac (lecture `eth_call` au bloc +1) comparé à `allowance_after` ;
5. contrats du manifeste : `eth_getCode(adresse) != "0x"` (et sha256 du code si le manifeste le stocke) — jamais « audité », seulement « présent à un bloc donné » (correction C6 de la RC) ;
6. toute divergence ⇒ mismatch codé (même vocabulaire que `verify_receipt` : `TOKEN_CONTRACT_MISMATCH`, `RECIPIENT_MISMATCH`, …).

**Résolution de bloc** : les `eth_call` d'archive sont rejoués **au bloc enregistré** (pas `latest`) — c'est ce qui rend la re-mesure stable (l'état d'un bloc est immuable ; [MESURÉ] W3, reconstruction relancée identique).

### 2.6 Contrôles C (couverture du non rejouable) — règles exactes

1. Chaque ligne `agent_journal` avec `llm{}` doit avoir `prompt_hash`/`response_hash` non nuls et **résolus** dans `payloads/` : `sha256(fichier) == hash déclaré` ;
2. `refs[]` de chaque ligne résolus (objets existants et admissibles au PIT du run — INV-PIT) : sinon `dangling_refs` non vide ⇒ FAIL ;
3. validateurs rejoués sur les réponses **enregistrées** : schéma strict (champ inconnu ⇒ le statut enregistré doit être `QUARANTINED`), « aucun chiffre produit par le LLM » (⇒ `REJECTED` si violé), provenance (⇒ refs existants) ; le statut recalculé doit être **égal** au statut enregistré ;
4. le rapport nomme chaque élément C comme **non rejouable** ; `--strict` refuse un run où une sortie LLM influence la décision sans ligne journal.

### 2.7 Détection de mutation — les 6 tests (auto-test `--mutate-test`)

| # | Mutation | Attendu |
|---|---|---|
| M1 | 1 octet du corps du dossier md (hors champ self) | A2 échoue (self-hash) |
| M2 | 1 caractère dans une ligne de `audit.jsonl` | A1 échoue (chaîne) + le manifeste (head) diverge |
| M3 | 1 chiffre changé dans `decision_*.json` (ex. montant) | A3 échoue (entrée) + A4 échoue (re-rendu différent) |
| M4 | 1 montant changé dans un reçu brut (`receipts/`) | A8/A1 : reçu altéré sans chaîne ⇒ détecté si le reçu est journalisé dans `audit.jsonl` (règle : le reçu complet est hashé dans l'enregistrement `RECEIPT`) ⇒ prévoir `receipt_sha256` dans le payload |
| M5 | retrait d'un fichier (`receipts/…json`) | présence requise par le manifeste ⇒ FAIL nommé |
| M6 | vérificateur modifié (1 ligne) | `sha256(orvyren_verify.py)` ≠ HASHES.txt ⇒ FAIL ; un vérificateur ne se certifie pas lui-même — d'où la double distribution (§2.8) et le verdict externe |

*(M4 impose une règle de format : chaque `RECEIPT` du journal porte `receipt_sha256` + `raw_ref` vers le fichier — ajouté à la spec W2-C §d.5.)*

### 2.8 Intégration au dépôt (sans dépendance nouvelle)

- **Emplacement** : `src/orvyren/verify/` (`__init__.py`, `report.py`, `checks_a.py`, `checks_b.py`, `checks_c.py`, `__main__.py`) — la chaîne d'imports d'AV1 §2 est respectée : `verify` est **au-dessus** de `audit` (lecture seule de tous les artefacts, aucun import vers `research`/`execution` sauf `policy` et `execution.verify` en **lecture** de fonctions pures).
- **Point d'entrée** : `python -m orvyren.verify …` (convention du dépôt : `python -m orvyren.decide …`, AV1 §1).
- **Tests** : `tests/test_verify.py` — fixtures = le paquet de démo **figé** (`evidence/audit_packet_*`, à produire) + les 3 fixtures T10 (nominal/absent/invalide) + les 6 mutations ; **aucun accès réseau** (transport factice injecté, comme `tests/test_data_layer.py`).
- **Distribution double** : (1) module du dépôt ; (2) **copie gelée** `verify/orvyren_verify.py` dans le paquet — même code, sha256 dans `HASHES.txt` ; le rapport vérifie l'égalité des deux empreintes s'il est lancé depuis le dépôt.
- **Ce qui est ajouté au pipeline** : un script `scripts/build_audit_packet.py` (assemblage + manifeste + LINK/SEAL + HASHES.txt + zip). Non construit ici (phase recherche).

### 2.9 Critères de succès T10 — mesurables (à recopier dans l'essai)

| # | Critère | Mesure | Cible |
|---|---|---|---|
| T10-1 | 100 % des calculs déterminants (A1–A8) recalculés **sans réseau** | rapport : les 8 contrôles A1–A8 en `class:"A"`, `status:"RECOMPUTED"`, `ok:true` | 8/8 |
| T10-2 | **Mêmes verdicts** après recalcul | A5 : verdicts + règles recalculés == enregistrés (ALLOW et DENY) | 100 % des intentions |
| T10-3 | Chaque **mutation** détectée | 6 mutations §2.7, une par classe de fichier | 6/6, chacune nommée dans le rapport |
| T10-4 | **Zéro référence pendante** | `dangling_refs == []` (claims→observations→sources ; journal→objets ; exécution→décision) | 0 |
| T10-5 | Rejeu **hors-ligne** complet | paquet vérifié sur une machine **sans client RPC ni dépôt** (copie gelée) | rapport identique hors `generated_at` |
| T10-6 | Cas dégradés | donnée absente / invalide : rapport explicite, pas d'exception, code de sortie stable | 2/2 |
| T10-7 | Contrôles B (sous `--rpc`) | receipts relus et recoupés ; verdict B séparé du verdict A | ≥ 1 exécution + ≥ 1 refus par la chaîne (run C) |
| T10-8 | Élément C honnête | rapport : chaque sortie LLM = `COVERED (journal)`, jamais « recalculée » | 100 % des appels du run |
| T10-9 | Coût | durée du run hors-ligne sur le paquet de démo | < 5 s (objectif) ; à mesurer |
| T10-10 | Le vérificateur ne se certifie pas | M6 + double distribution (dépôt/paquet) + empreinte vérifiée par un tiers | FAIT dans le paquet |

**Protocole d'exécution de l'essai T10 (4–6 h, à ventiler)** : confectionner les fixtures (1 h) → écrire A1–A8 (2 h) → mutations + cas dégradés (0,5 h) → contrôles B sur le run E réel (0,5–1 h, dépend du wallet) → exécuter le rapport sur le paquet et consigner (0,5 h). **En cas d'échec** : « un calcul dépend d'un état caché ou d'une archive manquante » devient le constat écrit (RC §4), et le calcul est soit corrigé soit **retiré de la liste des déterminants** — jamais laissé flou.

### 2.10 Ce que le vérificateur ne fait pas (à écrire dans le rapport)

1. Il ne rejoue **pas** le raisonnement LLM (classe C) ; il en vérifie la **couverture**.
2. Il ne prouve pas la **véracité** des sources externes (un oracle peut être faux même avec un reçu parfait) — c'est le rôle de INV-DEPENDENCE/qualité, pas du vérificateur.
3. Il ne détecte pas une **falsification coordonnée** (« réécrire le contenu ET recalculer tous les hash ») : sans ancre externe (R-6), un attaquant qui a le contrôle du paquet peut tout recalculer de façon cohérente. **C'est exactement pourquoi l'ancrage (iii) a une valeur** : publier le digest dans un registre non réécrivable par nous fige la version vérifiée.
4. Il ne prouve rien sur ce qui n'a **pas** été journalisé (exhaustivité) — la règle est : ce qui n'est pas dans le paquet n'existe pas pour le reviewer (question QO-1).

---

## 3. (c) ANCRAGE — décision pour v1

### 3.1 Les trois options, coût / complexité / bénéfice

| Option | Ce qu'on fait | Coût | Complexité | Bénéfice | Ce que ça prouve / ne prouve pas |
|---|---|---|---|---|---|
| **(i) Aucun ancrage** | rien ; le paquet est livré tel quel | 0 | 0 | Le paquet reste intégralement vérifiable par un tiers **qui l'a reçu intact** ; toute la vérification A/B/C du §2 fonctionne | Prouve l'intégrité interne (chaînes) ; **ne prouve pas** qu'il n'a pas été fabriqué/réécrit avant remise ; aucune datation opposable |
| **(ii) Empreinte publiée (paquet + dépôt)** | `HASHES.txt` + `bundle_digest` + sha256 du zip publiés : README du dépôt (dès qu'il est poussé), matériel de soumission, copie horodatée conservée par l'équipe ; tag git `audit-<run_id>` | 0 (5 min) | Triviale | Donne une **référence publique datée par des tiers** (plateforme de soumission, GitHub) ; le reviewer compare le digest publié au digest recalculé | Prouve la **fixation datée** de la version soumise vis-à-vis des plateformes ; ne prouve rien si le dépôt reste privé/local (QO-7) |
| **(iii) Ancrage EAS sur Base Sepolia** | 1 schéma + 1 attestation `bytes32 anchored_digest` via le prédeploy EAS ; l'UID + tx dans `anchor/eas_attestation.json` et rappelés dans le dossier | Gas mesuré : `gasPrice = 6 000 000 wei` [MESURÉ] ; ≈ 120 k–250 k gaz ⇒ **≈ 0,0000007–0,0000015 ETH** par attestation [HYPOTHÈSE gaz] + clé testnet financée (prérequis démo déjà posé) | Faible : 1 script stdlib (ABI minimale), exécutable une fois ; EAS **présent et vérifié** sur Base Sepolia aujourd'hui (`0x4200…0021` + registre `0x4200…0020`, implémentations lues au slot EIP-1967) [MESURÉ] | Datation + existence **indépendantes de nous** : n'importe qui lit l'attestation et compare au digest ; coût quasi nul ; c'est un artefact cliquable pour le jury | EAS est un **service d'attestation libre et ouvert** « schemas registered using SchemaRegistry, attestations made using EAS » [FAIT SOURCÉ : README eas-contracts, consulté 2026-10-15] ; **un testnet n'est pas une preuve de production** ; V0.2 §10.6 : « une empreinte prouve l'intégrité du dossier ancré, **pas sa véracité** » |

**Faits mesurés pour (iii)** (2026-10-15, `https://sepolia.base.org`, `raw_b6/eas_basesepolia_rpc.json` + `eas_impl_slots.json`) : `chainId = 0x14a34` (84532) ; bloc 47 988 371 ; EAS `0x4200000000000000000000000000000000000021` (proxy, impl `0xc0d3c0d3…0021`, 18 385 o, sha256 `9c576dec…`) ; SchemaRegistry `0x4200000000000000000000000000000000000020` (impl `0xc0d3c0d3…0020`, 2 865 o, sha256 `bda4f862…`). Mêmes prédeploys sur Base mainnet [FAIT SOURCÉ : `github.com/coinbase/verifications` README (table Base/Base Sepolia), consulté 2026-10-15 ; `basehub.org/network/base-contracts`].

### 3.2 Recommandation claire (R-6)

1. **Option (ii) — obligatoire, dès maintenant, coût nul.** Concrètement : `bundle_digest` + sha256 du zip imprimés dans `HASHES.txt`, recopiés (a) dans le matériel de soumission au concours, (b) dans le README du dépôt dès qu'il est poussé (remote non configuré à ce jour — l'équipe/le pousseur s'en charge), (c) conservés dans `dist/` horodatés. **C'est le minimum qui rend l'option (i) insuffisante évitable.**
2. **Option (iii) — conditionnelle, exécutée seulement si les 3 conditions sont vertes** : (1) **run E vert** (les 5 runs W2-C §g exécutés, `audit.jsonl` réel produit) ; (2) **vérificateur T10 vert** (T10-1…T10-8) ; (3) **≥ J-1 avant la soumission** (soumission 20/10 15:59 UTC ; fenêtre proposée : ancrer au plus tard le **18/10 23:59 UTC**, sinon **reporté sans regret**). L'ancrage est **additif** : il ne conditionne ni la démo, ni l'export, ni la vérification — conforme à V0.2 §10.6 (« reportée si elle menace la réussite du flux vertical ») et à AV1 §6.
3. **Ce qu'on ancre (si iii)** : `anchored_digest` = le **self-hash du dossier md** (`dossier_<case>.md`) — déjà présent dans le dossier, déjà reproductible par tout outil, et qui commet transitivement au manifeste et aux trois flux par la table d'intégrité. Un seul `bytes32` : celui que le jury peut recopier à la main.
4. **Schéma EAS proposé** (1 ligne) : `bytes32 dossierDigest, string caseId, string engineVersion, uint64 asOf` ; **revocable = false** (une attestation d'audit ne doit pas pouvoir être retirée) ; résolveur = aucun (pas de logique on-chain). Enregistrement du schéma puis `EAS.attest(…)` avec `recipient = adresse de l'équipe`, `data = abi.encode(...)` ; signatures exactes **à reprendre de l'ABI publiée** du dépôt `eas-contracts` (`deployments/…/EAS.json` — README consulté 2026-10-15 ; sélecteurs non re-vérifiés ici **[NON TROUVÉ]**).
5. **Script d'ancrage** (esquisse en Annexe C) : un unique `scripts/anchor_eas.py` (stdlib, encodeur ABI minimal réutilisant le codec du dépôt `src/orvyren/data/rpc.py` [code]) ; sortie `anchor/eas_attestation.json` ; **la clé reste hors dépôt** (règle projet) et l'ancre est signée par l'EOA de démo ou une EOA dédiée « audit » (QO-3).

**Coût de changement** : (i)→(ii) : 5 min ; (ii)→(iii) : ~1–2 h de script + 1 tx (~0,1 s de calcul) ; la procédure est identique sur Base mainnet (mêmes adresses) le jour où un paquet de production sera ancré — « ce qui change n'est pas l'architecture, c'est le montant » (paraphrase de W2-C §g.8).

---

## 4. (d) CE QUE L'AUDIT PROUVE ET NE PROUVE PAS — textes exacts à reporter tels quels

### 4.1 Texte FR (version interne / revue d'équipe)

> **Ce que ce dossier prouve.**
> (1) **Intégrité** : le dossier et ses journaux n'ont pas été modifiés depuis leur scellé — toute altération d'un octet casse une chaîne de hachage ou un self-hash (INV-INTEGRITY).
> (2) **Reconstruitibilité** : chaque calcul déterminant (verdicts de politique, re-rendu du dossier, instantané du graphe, croisement intention↔reçu) est recalculé **hors-ligne** par un tiers, à partir des seules pièces fournies — mêmes entrées, mêmes versions, mêmes sorties.
> (3) **Correspondance intention↔exécution** : chaque transaction enregistrée est reliée à une intention et à un verdict de politique, et recoupée avec le reçu public (statut, bloc, logs) — ce que le système *voulait* faire, ce qu'il a été *autorisé* à faire, et ce qui s'est *réellement* passé sont trois objets distincts et comparés.
> (4) **Bornage du mandat** : ce que l'agent *pouvait* faire est un fait public (permissions on-chain datées) ; le pire cas est un nombre fini et lisible, pas une promesse.
> (5) **Admissibilité temporelle (INV-PIT)** : chaque fait porte son horodatage d'événement et de récupération ; une donnée non admissible à l'instant de la décision est exclue du chemin décisionnel.
> (6) **Conservation des refus** : refus de politique, rejets, quarantaines et abstentions sont journalisés et comptés — un refus est un résultat, pas un silence.
> (7) **Indépendance des canaux (INV-DEPENDENCE)** : deux canaux issus de la même archive ne comptent pas comme deux confirmations.
> (8) **Imputabilité** : chaque étape (raisonnement, connaissance, exécution) est attribuée à un composant versionné, avec ses entrées et ses sorties.
>
> **Ce que ce dossier ne prouve pas.**
> (1) La **véracité** des sources externes : un oracle peut se tromper même si toutes les chaînes de hachage sont valides.
> (2) La **justesse** des hypothèses ni la **qualité** des décisions : la reconstructibilité ne dit rien de la pertinence.
> (3) Toute **performance financière** (rendement, perte évitée, supériorité sur une baseline) — non revendiquée.
> (4) L'**exhaustivité** : le dossier couvre les actions du signer et les étapes journalisées ; ce qui n'a pas été journalisé n'y figure pas.
> (5) Le texte des **appels LLM n'est pas rejoué** (non-déterminisme d'inférence) : il est **couvert par le journal** (prompt et réponse archivés, hashés ; validateurs rejoués).
> (6) L'absence de **bug** dans les composants amont (contrats tiers, fournisseurs de données).
> (7) La **conformité juridique** ou réglementaire dans une juridiction donnée.
> (8) Une **empreinte ancrée** (si ancrage) prouve l'intégrité et la datation du dossier ancré, **pas sa véracité**.

### 4.2 Texte EN (paquet jury — à recopier dans `README_AUDIT.md`)

> **What this audit packet proves.** (1) **Integrity** — no byte of the dossier or its journals has changed since sealing: any alteration breaks a hash chain or the dossier self-hash (INV-INTEGRITY). (2) **Recomputability** — every determinant computation (policy verdicts, dossier re-rendering, graph snapshot, intent↔receipt matching) is recomputed **offline** by a third party from the supplied pieces alone: same inputs, same versions, same outputs. (3) **Intent↔execution correspondence** — each recorded transaction is tied to an intent and a policy verdict and cross-checked against the public receipt (status, block, logs). (4) **Bounded mandate** — what the agent *could* do is a public, dated on-chain fact; the worst case is a finite, readable number. (5) **Point-in-time admissibility (INV-PIT)** — every fact carries event and retrieval timestamps; data inadmissible at decision time is excluded from the decision path. (6) **Refusals preserved** — policy denials, rejections, quarantines and abstentions are journaled and counted. (7) **Channel independence (INV-DEPENDENCE)** — two channels from the same archive never count as two confirmations. (8) **Accountability** — every step is attributed to a versioned component with its inputs and outputs.
>
> **What this audit packet does not prove.** (1) The **truthfulness** of external sources — an oracle can be wrong while every hash is valid. (2) The **soundness** of hypotheses or the quality of decisions. (3) Any **financial performance** (returns, avoided loss, superiority over a baseline) — none is claimed. (4) **Completeness** — the packet covers signer actions and journaled steps; anything not journaled is not in it. (5) **LLM call text is not replayed** (inference nondeterminism); it is **covered by the journal** (prompts and responses archived and hashed, validators replayed). (6) Absence of **bugs** in upstream components. (7) **Legal or regulatory compliance** in any jurisdiction. (8) A **sealed digest** (if anchored) proves the integrity and dating of the anchored dossier, **not its truthfulness**.

### 4.3 Formulations interdites (reprises de W2-C §f.3, à appliquer partout)

- « La blockchain nous décharge juridiquement » — faux : la chaîne prouve des faits, ne répartit pas la responsabilité.
- « L'agent est audité » si seuls les contrats amont le sont (auditer **la politique**, pas seulement hériter de l'audit du module).
- « Zéro risque », « impossible à détourner » — contredit par les deux incidents Zodiac 2026 documentés (W2-C §a.6).
- « Rejouable » / « reproductible » **sans qualifier la classe** (A/B/C) — c'est précisément la faute que T10 doit interdire.
- « Preuve de véracité » pour un ancrage — V0.2 §10.6 : l'empreinte prouve l'intégrité, pas la véracité.

---

## 5. (e) PAQUET LIVRABLE AU JURY / REVIEWER — pièces exactes + checklist

### 5.1 Liste exacte des pièces (le « dossier 1 page » au centre, tout le reste en annexes vérifiables)

| # | Pièce | Rôle | Déjà existant ? |
|---|---|---|---|
| 1 | `README_AUDIT.md` (EN) | Comment vérifier en 3 commandes ; ce que ça prouve / pas (§4.2) ; inventaire | **à écrire** (gabarit §5.2) |
| 2 | `dossier_<case>.md` + `.html` | Le dossier de décision **1 page** (self-hash), produit par `orvyren.audit.dossier` | gabarit éprouvé ; version démo à produire |
| 3 | `decision_<case>.json` | Vérité machine du dossier (verdicts, action, rationale, limites, provenance) | oui (v0) |
| 4 | Extras du dossier : `baseline_report.json`, `quality_report.json`, `policy_execution_demo.json` | Comparateur A0, qualité des données, verdicts R1–R8 sur cas figés | oui |
| 5 | `audit.jsonl` | Flux exécution chaîné **+ LINK + SEAL** | design W2-C ; **à produire (run E)** |
| 6 | `agent_journal.jsonl` (+ `payloads/`) | Flux raisonnement chaîné (ou déclaré absent au manifeste) | design B1 ; dépend des agents |
| 7 | `graph/` (`graph_delta.jsonl`, `graph_snapshot.json`, `provenance.json`) | Flux connaissance + provenance résolue | briques code ; export à produire |
| 8 | `manifest.json` | Têtes des flux, versions, RPC/blocs, inventaire | **à écrire** |
| 9 | `receipts/` + `policy/` | Reçus bruts + politique versionnée + snapshot du module Zodiac | run E ; dépend du wallet |
| 10 | `verify/orvyren_verify.py` + `VERIFY_EXPECTED.txt` | Le vérificateur **gelé** + la sortie attendue sur ce paquet | **à écrire** (§2) |
| 11 | `HASHES.txt` | sha256 de chaque fichier + `bundle_digest` | **à écrire** |
| 12 | `anchor/eas_attestation.json` *(optionnel)* | Preuve d'ancrage (si R-6 condition verte) | conditionnel |

### 5.2 Checklist de vérification (à mettre dans `README_AUDIT.md`)

**Pour le reviewer (vérification hors-ligne, sans nous, sans réseau) :**

```bash
unzip audit_packet_<case>_<…>.zip && cd audit_packet_<case>_<…>
# 1) intégrité du paquet : chaque fichier ↔ HASHES.txt
sha256sum -c HASHES.txt        # (le vérificateur refait ce contrôle en A3 si coreutils absent)
# 2) vérificateur — contrôle complet hors-ligne ; attendu : VERDICT: OFFLINE_PASS
python verify/orvyren_verify.py .
# 3) auto-test de détection : attendu 6/6 mutations détectées
python verify/orvyren_verify.py . --mutate-test
```
**Avec réseau (contrôles B, optionnel)** : `python verify/orvyren_verify.py . --rpc https://sepolia.base.org` → verdict séparé `CHAIN_PASS` (receipts relus, transferts recoupés).

**Checklist interne avant remise (bloquante, 11 points)** :
1. `verify --offline` vert sur le paquet **tel que zippé** (pas sur le répertoire de travail) ;
2. `--mutate-test` 6/6 ;
3. zéro `dangling_refs` ;
4. le dossier re-rendu depuis le JSON est **identique octet à octet** (A4) ;
5. `HASHES.txt` couvre **tous** les fichiers (aucun fichier non listé, aucun listé absent) ;
6. le manifeste déclare **chaque flux** (présent, avec tête et compte, ou absent avec raison) ;
7. chaque `RECEIPT` a son reçu brut archivé + `receipt_sha256` ;
8. aucun secret : scan `grep -ri "private\|secret\|mnemonic\|API_KEY"` = vide (hors noms de champs) ;
9. étiquettes de mode cohérentes (`LIVE/REPLAY_JOURNAL/…`) partout (V0.2 §13.3) ;
10. le texte §4.2 (EN) figure **verbatim** dans le README ;
11. `bundle_digest` publié (option ii) — et, si ancrage, l'UID EAS relu sur un explorateur tiers (base-sepolia.easscan.org) au moment de la remise.

### 5.3 Ce qui est exclu du paquet (explicite)

Clés, `.env`, chemins absolus de machine (règle `_display_path` [code]), données personnelles, contenu de chat brut non journalisé, journaux d'un autre run, résultats d'évaluation du jeu EVAL (embargo W2-D), et **toute affirmation de performance**.

---

## 6. (f) QUESTIONS OUVERTES (à trancher en revue)

| # | Question | Ce qui la ferme | Coût |
|---|---|---|---|
| QO-1 | **Journal intégral ou extrait publiable ?** (B1 Q7 propose l'extrait ; l'audit T10 gagne au journal intégral, qui ne contient ni clé ni donnée sensible) | décision d'équipe ; recommandation : **intégral** pour le paquet de démo, avec procédure de rédaction séparée (jamais d'édition en place — un extrait référencé ne casse pas les chaînes) | 0,5 j |
| QO-2 | **Politique de réorg** : profondeur de confirmation avant de figer un `RECEIPT` (B2 QO-1) | valeur figée (ex. ≥ 5 blocs Base) + test `REORG_SUSPECT` dans le vérificateur | 0,5 j |
| QO-3 | **Qui signe l'ancrage** (option iii) : EOA de démo ou EOA dédiée « audit » ? (une clé de démo compromise ne doit pas pouvoir forger une ancre) | décision + génération d'une EOA dédiée, financée en testnet | 0,5 j |
| QO-4 | **EAS : revocable ou non ?** (recommandé : non) ; et faut-il un résolveur ? (recommandé : non) | décision lors de l'enregistrement du schéma | 0,25 j |
| QO-5 | **Le rapport de vérification doit-il être signé** (par qui : l'équipe ? un relecteur externe ?) | décision ; recommandation : le rapport reste brut, c'est **sa reproductibilité** qui vaut signature ; un relecteur externe exécute `--mutate-test` | — |
| QO-6 | **« Audit de l'auditeur »** : faire tester le vérificateur par quelqu'un qui n'a pas écrit le code (RC §4 : « relecture externe ») | un passage d'un membre n'ayant pas écrit `verify/` sur les 6 mutations | 0,5 j |
| QO-7 | **Publication de l'empreinte (option ii)** : le dépôt GitHub n'est pas poussé à ce jour (remote non configuré) — où publie-t-on ? | au minimum matériel de soumission + `dist/` ; dépôt public ensuite | 0,25 j |
| QO-8 | **Retention/taille** : le paquet de démo grossit-il (payloads LLM) ? | mesure au premier run réel ; la démo sans LLM ≈ négligeable | 0,25 j |
| QO-9 | **Langue du dossier rendu** : EN pour la soumission (AV1 §5) — le gabarit actuel est EN [code] ; garder | confirmé par relecture | — |
| QO-10 | **Horodatage supplémentaire gratuit (OpenTimestamps/Bitcoin)** comme variante de (iii) — statut réel à vérifier auprès du service | décision exploratoire post-concours | **[NON TROUVÉ]** ici |

---

## 7. Sources

**Externes (URLs consultées le 2026-10-15)**
1. EAS — dépôt de contrats (protocole « free and open », schémas via `SchemaRegistry.sol`, attestations via `EAS.sol`, artéfacts de déploiement/ABI) : https://github.com/ethereum-attestation-service/eas-contracts (README, consulté 2026-10-15).
2. EAS — prédeploys Base / Base Sepolia (`0x4200…0021`, `0x4200…0020`) : https://github.com/coinbase/verifications (README, table Base & Base Sepolia, consulté 2026-10-15) ; liste canonique des contrats Base : https://basehub.org/network/base-contracts/ (consultée 2026-10-15).
3. RPC Base Sepolia : `https://sepolia.base.org` (`eth_chainId`, `eth_blockNumber`, `eth_gasPrice`, `eth_getCode`, `eth_getStorageAt` — 2026-10-15 ; **403 sans en-tête `User-Agent`**).
4. Rappels de doctrine (déjà en bibliographie projet, re-cités) : Thinking Machines Lab, *Defeating Nondeterminism in LLM Inference*, 2025-09-10 ; arXiv:2601.17768 ; arXiv:2606.08998 ; arXiv:2603.10062 ; arXiv:2606.24535 (cf. B1 §8).

**Internes**
5. `research/SYSTEME_ZONES_OMBRE.md` §6 et §9 (15/10/2026).
6. `research/REVUE_CROISEE_ET_CADRE_CONCRET.md` §2.4 (5 invariants), §3.2 (HYP-10R), §4 (protocole T10) (15/10/2026).
7. `research/W2C_enveloppe_execution.md` §d.5 (design `audit.jsonl`), §g (plan run E, prérequis), §f (cadre de responsabilité) (15/10/2026).
8. `research/B1_AGENTS_ETUDE.md` §3 (agent_journal, 25 champs, payloads hashés), §6 (replay REPLAY-JOURNAL/LIVE-REPLAY/LIVE) (15/10/2026).
9. `research/B2_GRAPHE_ETUDE.md` §2.4/§7.5 (append-only, snapshots par décision, delta par run), QO-1 (reorg) (15/10/2026).
10. `research/B3_DECISION_ETUDE.md` §c (format « INCONCLUSIVE + ce qui manque »), §d (3 axes) (15/10/2026).
11. `research/W3_reconstruction_rseth_steth.md` §2.3 (relance identique au bit près), §5 (`--from-cache`), §7 (fichiers) (15/10/2026).
12. `C:\Users\User\fintechathon_recherche\orvyren_v02\ORVYREN_Document_de_reference_V0_2.txt` §10.6 (EAS, empreinte ≠ véracité), §10.5 (preuve de transaction, testnet OPEN), §12.4 (acceptation), §13.3 (« pas de placeholder ») (13/10/2026).
13. `ARCHITECTURE_V1.md` §2 (carte des modules), §5 (langues, conventions), §6 (EAS reportée après le flux vertical) (14/10/2026).
14. Code : `src/orvyren/audit/dossier.py` (self-hash, déterminisme, `_display_path`, LF-normalisation), `src/orvyren/graph/provenance.py` + `store.py` (`verify_chain`, `snapshot`, append-only), `src/orvyren/execution/verify.py` (`verify_receipt`, `TRANSFER_TOPIC`), `src/orvyren/policy/__init__.py` (R1–R8), `tests/test_audit.py` (déterminisme du dossier) — constat : **pas de `verify/` ni de `audit/bundle`** (2026-10-15).
15. `dist/docs/ORVYREN_EXPLIQUE_SIMPLEMENT.md` (lot T10 non négociable) (15/10/2026).

## Annexe A — Matière brute (`research/raw_b6/`)

| Fichier | Contenu |
|---|---|
| `notes_00_contexte.md` | sources internes lues, mesures, pièges rencontrés (403 RPC sans UA ; contrôle HTML ciblé) |
| `verif_dossier_v1.py` + `dossier_v1_verification.json` | contrôle hors-ligne : self-hash md **et** html + entrées (résultats : tout reproduit — JSON régénéré après correction du contrôle HTML) |
| `verif_dossier_v1_html_fix.py` + `dossier_v1_verification.html_fix.json` | premier contrôle ciblé de la ligne self du HTML (1 occurrence) — conservé comme trace du piège |
| `eas_basesepolia_rpc.py` + `eas_basesepolia_rpc.json` + `eas_impl_slots.json` | sondage EAS/registre sur Base Sepolia : adresses, tailles, sha256, gasPrice, bloc |

## Annexe B — Enveloppe de journal (rappel condensé pour implémentation)

```text
Enregistrement = {v, stream, seq, run_id, episode, mode, ts_utc, kind, agent_id?, payload, refs,
                  prev_hash, record_hash}
record_hash = sha256( canonical_json(record \ {record_hash}) )        # canonical_json : clés triées,
                                                                       # séparateurs (",", ":"), UTF-8
genèse      = prev_hash "0"×64 ; clôture = LINK×N + SEAL{manifest_sha256}
manifest    = {streams:{exec|agent|graph:{path|absent, records, head_hash|snapshot_hash}},
               decision_sha256, policy_version, engine_version, mode, rpc{chain_id,endpoints,blocks},
               files:[(path,sha256)]}
dossier     = entrée du dossier : manifest.json (extra) ⇒ sha256 dans la table Evidence
HASHES.txt  = path sha256 … (tous sauf lui-même) + bundle_digest
bundle_digest = sha256( canonical_json( sorted( files \ {dossier_*.{md,html}, HASHES.txt} ) ) )
```

## Annexe C — Esquisse de script d'ancrage EAS (si R-6 condition verte)

```python
# scripts/anchor_eas.py  (stdlib ; esquisse — signatures exactes à reprendre de l'ABI eas-contracts)
# 0) lire anchor_digest = dossier md self-hash (64 hex -> 32 octets) + caseId
# 1) SchemaRegistry.register(schema, resolver=0, revocable=false) -> schema_uid   [1 tx, si pas déjà fait]
#    schema = "bytes32 dossierDigest,string caseId,string engineVersion,uint64 asOf"
# 2) EAS.attest(recipient=EOA_equipe, schema=schema_uid, data=abi.encode(...), value=0) [1 tx]
# 3) écrire anchor/eas_attestation.json {chain:84532, eas:0x4200…21, schema_uid, attestation_uid,
#    tx_hash, block, anchored_digest, anchored_at_utc}  (+ sha256 des reçus bruts)
# Règles : clé hors dépôt ; RPC avec User-Agent ; refus si chainId != 84532 ; jamais de retry sur une tx
#          déjà incluse (relire le reçu d'abord) ; la transaction d'ancrage n'est PAS une action de l'agent.
```

---

*Fin du document. Statuts : §1 = CONCEPTION (format) + MESURÉ (contrôles v1) ; §2 = spécification à geler (issue de l'exigence T10 déjà gelée) ; §3 = PROPOSITION de décision ; §4 = texte proposé à report ; §5 = CONCEPTION. Ce document ne commit rien et ne modifie aucun autre fichier du dépôt.*
