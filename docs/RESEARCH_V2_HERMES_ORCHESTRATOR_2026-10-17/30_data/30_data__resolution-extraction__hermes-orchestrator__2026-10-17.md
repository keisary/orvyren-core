# 30_data — Résolution d'entités/événements et extraction documentaire

**Auteur / agent** : Hermes-orchestrateur (deepseek-flash, session recherche V2).
**Date** : 2026-10-17.
**Chantier** : `30_data`.
**Statut** : INTERNE — recherche V2, ne pas soumettre.
**Périmètre** : résolution déterministe, alias, événements, extraction documentaire, provenance, validation, LLM.
**Fichiers lus** : `10_graph__entites-evenements__hermes-orchestrator__2026-10-17.md`, `B2_GRAPHE_ETUDE.md` §4.2–4.5, `MIMIR_Technical_Design.md` §10.4–10.5, `10_graph__schema-cible__hermes__2026-10-17.md` §8.

---

## 0. Verdict

La résolution n'est pas un problème de LLM : c'est un problème de **clés canoniques et de preuves**. Les adresses on-chain sont des identifiants exacts ; les noms, tickers et documents sont ambigus. Il faut résoudre **déterministe d'abord**, puis sémantique, puis LLM uniquement pour les cas ambigus.

**Décision** : `chain:address` est canonique ; les alias sont des preuves ; les événements on-chain sont identifiés par `(chain, tx, log)` ; l'extraction documentaire est **hors du chemin décisionnel v1**, limitée à 2–3 documents avec ancrage et validation.

---

## 1. Résolution d'entités

### 1.1 Ordre

```
mention
  -> identifiant exact (adresse, LEI, ISIN, hash)
  -> normalisation (checksum, lowercase, decimals)
  -> candidats (registre, alias, chaîne, voisins)
  -> score contextuel
  -> RESOLVED / PROBABLE / AMBIGUOUS / UNRESOLVED
  -> décision datée + provenance
```

### 1.2 Règles

- **Adresse** = clé canonique : `addr:eip155:<chain>:<address_lower>`.
- **Ticker** = alias, jamais clé.
- **Alias** : source, date, confiance ; `SAME_AS` explicite, révisable.
- **LLM** : seulement `AMBIGUOUS`, avec liste de candidats ; jamais pour inventer une adresse.
- **Réversibilité** : une résolution peut être superseded ; l'historique reste.
- **Indépendance** : un alias repris de la même source ne crée pas une seconde preuve.

### 1.3 Cas pièges

| Cas | Décision |
|---|---|
| `USDC` vs `USDC.e` | deux contrats ; `SAME_AS` seulement avec preuve de pont/wrapper |
| `wstETH` vs `stETH` | `WRAPS`, pas `SAME_AS` |
| Proxy vs implémentation | `IMPLEMENTED_BY`, pas `SAME_AS` |
| `aUSDC` vs `USDC` | deux actifs (receipt token vs underlying) ; `PART_OF`/`WRAPS` selon preuve |
| Même adresse sur deux chaînes | deux nœuds ; `chain_id` dans l'ID |
| Nom marketing changé | alias daté, pas nouveau nœud |

---

## 2. Résolution d'événements

- **On-chain** : ID `(chain_id, tx_hash, log_index)` ; un log décodé = un événement.
- **Document** : un document peut contenir N événements ; N documents peuvent décrire le même événement.
- **Fusion** : seulement avec preuve (même tx/log, même source officielle, même date) ; sinon `event_observations` séparées.
- **Cycle** : `RUMOR → ANNOUNCED → CONFIRMED → IMPLEMENTED → CONSEQUENCE`.
- **Statut** : un communiqué est `ANNOUNCED`, pas `CONFIRMED` ; un log on-chain est `CONFIRMED` ; une conséquence observée est `CONSEQUENCE`.
- **Actual/Expected/Surprise** : garder les trois séparés ; un événement attendu n'est pas un événement confirmé.

---

## 3. Extraction documentaire

### 3.1 Outils

| Outil | Usage | Limite |
|---|---|---|
| GLiNER | NER + relation zero-shot, CPU | génération de candidats |
| REBEL | triplets end-to-end | faible précision domaine |
| LangExtract | extraction LLM avec ancrage | coût, version à figer |
| LLM + JSON schema | extraction contrôlée | hallucination, quarantaine |

### 3.2 Pipeline

```
document -> sha256 -> mentions -> résolution -> triplets candidats + offsets
         -> validation G1–G5 -> relation VALIDATED ou quarantaine
```

Chaque relation extraite porte : `extract_method=LLM_EXTRACT`, `model_version`, `run_id`, `doc:sha256`, offsets, `source_family_id`.

### 3.3 Portes de validation

| Porte | Contrôle | Rejet |
|---|---|---|
| G1 — Schéma | kind ∈ catalogue, types sujet/objet | triplet hors catalogue |
| G2 — Provenance | passage + offsets + parent | citation non localisable |
| G3 — Autorité | on-chain > document officiel > presse > communautaire | rumeur comme fait |
| G4 — Indépendance | seconde famille différente | 10 médias = 1 source |
| G5 — Cohérence | contradiction → `CONTRADICTS` | écrasement silencieux |

**Règle de charge** : un fait porteur exige on-chain vérifié, **ou** document officiel, **ou** deux familles indépendantes. Sinon `PENDING/QUARANTINED` et contexte narratif seulement.

---

## 4. LLM : où et où pas

**Oui** :

- résolution `AMBIGUOUS` avec candidats ;
- extraction de claims avec offsets ;
- résumé de documents ;
- critique adversariale.

**Non** :

- produire un prix, une supply, un montant ;
- créer une adresse ;
- transformer un `MODEL-INFERRED` en `FACT` ;
- décider seul d'une permission ;
- remplacer la policy.

**Règle** : le LLM propose, le validateur dispose. Un chiffre décisionnel vient d'une observation, jamais d'un texte généré.

---

## 5. Plan 72 h

- Résolution déterministe des adresses/contrats Aave (address book).
- Événements on-chain par `(chain, tx, log)`.
- 5–10 alias max, avec source.
- 2–3 documents officiels max (Aave/Chainlink), avec offsets.
- **Pas** de GraphRAG, pas d'extraction large, pas de LLM dans le chemin décisionnel.
- Tests : alias, doublons, proxy, event lifecycle, citation, quarantaine.

---

## 6. Risques

| Risque | Mitigation |
|---|---|
| Ticker comme clé | refus à l'écriture |
| `USDC.e` fusionné | `SAME_AS` avec preuve |
| Proxy confondu | `IMPLEMENTED_BY` |
| Document inventé | offsets + quarantaine |
| LLM hallucine un chiffre | chiffres interdits, observations seules |
| Doublons d'événements | clé `(chain, tx, log)` |
| Scope extraction | 2–3 documents |

---

## 7. Sources

- `10_graph__entites-evenements__hermes-orchestrator__2026-10-17.md`.
- `B2_GRAPHE_ETUDE.md` §4.2–4.5.
- `MIMIR_Technical_Design.md` §10.4–10.5.
- `10_graph__schema-cible__hermes__2026-10-17.md` §8.
- GLiNER — https://github.com/urchade/GLiNER — consulté 2026-10-17.
- REBEL — https://aclanthology.org/2021.findings-emnlp.204.pdf — consulté 2026-10-17.
- LangExtract — https://github.com/google/langextract — consulté 2026-10-17.
- Aave address book — https://github.com/aave/aave-address-book — consulté 2026-10-17.
- EIP-1967 — https://eips.ethereum.org/EIPS/eip-1967 — consulté 2026-10-17.
