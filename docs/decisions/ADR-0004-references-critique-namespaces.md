# ADR-0004 — Contrat des références du critique (P0-6, porte 2) : namespaces et portes

**Date :** 2026-10-18 · **Statut : ACCEPTÉE** — la **porte critique** est explicitement
**REPORTÉE** (§4, avec sa condition de levée) · **Portée :** paquet `agents` —
validation des `refs` citées par les claims et par le rapport `orvyren/crit/v1`
(P0-6 : un claim ne cite que des références que le run a réellement observées).

## Contexte

P0-6 est tenu par un ledger de run (`contracts.ObservedRefs`,
`contracts.py:110`) semé par les observations réelles, puis par **deux portes
actives** qui refusent une ref inconnue (`E_REF_NOT_OBSERVED`, ligne REJECTED
visible). Or les prompts système **gelés** (`src/orvyren/agents/prompts.py` —
hash de rejeu, jamais modifié) invitent explicitement le modèle à citer **trois
namespaces** : `observation:… | claim:… | hypothesis:…`
(`prompts.py:86` pour les claims, `prompts.py:127` pour les findings du
critique). La revue chasse-aux-bugs du 2026-10-18 a établi (`review/agents_chain.md`
§2, N1 et N2) :

* les `refs` du rapport `orvyren/crit/v1` ne sont **pas** comparées aux refs
  observées (`worker.run_critic`) ;
* une porte stricte sur les seules refs du paquet produirait des **faux refus**
  sur les namespaces internes `claim:` / `hypothesis:` ;
* le magasin enregistré `fixtures/agents/store_usdc-2023-03` contient une
  critique qui cite `observation:defillama/usdc-usd/2023-03-11T12:00Z`, ref que
  son paquet ne porte pas — toute porte stricte rejetterait la critique
  **enregistrée** et casserait le rejeu (`test_agents_mab` exige
  `verdict_lecture == "FRAGILE"` et des têtes de chaîne stables sur k=10).

D'où le besoin d'un contrat écrit : que vaut chaque namespace, quelle porte
s'applique où, et que devient la porte critique.

## Options examinées

1. **Porte critique stricte tout de suite** (toute ref du rapport hors refs du
   paquet ⇒ QUARANTINE) — rejetée : elle casse le rejeu k=10 du magasin
   enregistré, et les **magasins enregistrés sont report-only** par règle (jamais
   réécrits en silence pour faire passer un test) ; elle punirait aussi les
   namespaces internes que le prompt gelé autorise.
2. **Élargir le ledger aux refs citées par le critique** (auto-seeding au
   moment de la lecture) — rejetée : c'est le blanchiment de la table de
   provenance que le correctif W1 de la même revue a précisément interdit (une
   ref rejetée pour invention ne doit jamais ré-enregistrer cette ref comme
   « observée »).
3. **Contrat par namespace + portes actives documentées, porte critique
   REPORTÉE avec condition de levée** — **retenue** : elle fige la sémantique
   sans casser le rejeu, et rend le report opposable (quoi, pourquoi, quand le
   lever).

## Décision

1. **Namespaces (contrat des `refs`).**
   * `observation:<source>/<mesure>/<instant>` — ref **externe** : elle n'est
     citable que si elle est dans le ledger `ObservedRefs` du run, statut
     `PROPOSED`/`ACCEPTED`. Sources de seed : rows de fixtures
     (`source_ref` / `ref` / `url` / `method_ref`, y compris les listes `refs`
     déclarées — `tools._fixture_refs`), `snapshot.ref` / `snapshot.refs`,
     `authorized_refs`, et les refs des résultats d'outils
     (`loop._observation_refs`, `loop.py:243`).
   * `claim:<id>` — ref **interne** : résolue dans le paquet du run (un claim du
     journal du run, même `journal_id` / même paquet). Jamais une source externe.
   * `hypothesis:<id>` — ref **interne** : résolue parmi les hypothèses du case
     (`run_inputs.json` → `hypotheses`, ids `HYP-…`).
2. **Principe (fail-closed, jamais de substitution).** Une ref inconnue, mal
   typée ou non résolue ⇒ **REJECTED** (ligne de journal visible, motif
   `E_REF_NOT_OBSERVED: <ref>`) ou **QUARANTINE** (rapport critique) — **jamais
   remplacée par une source « similaire »**, jamais auto-seedée après coup dans
   le ledger, jamais omise en silence. Un claim sans aucune ref est déjà refusé
   par le validateur d'évaluation (B1 §3.4).
3. **Portes actives aujourd'hui.**
   * `agents/tools.py` — `JournalWriteTool` (~L437–441) : intake de la boucle,
     toute `ref` hors ledger ⇒ `E_REF_NOT_OBSERVED`, statut REJECTED ;
   * `agents/loop.py` — `_record_evaluation` (~L617–621) : les `refs` des claims
     d'évaluation passent par le même contrôle ;
   * `agents/worker.py` — `build_evidence_packet` (2e barrière) : le ledger du
     paquet n'est semé que par les lignes `PROPOSED`/`ACCEPTED` (W1) et les
     `refs` du paquet excluent les refs inconnues (W2) — une ref inventée ne
     voyage jamais dans le payload du critique.
4. **Porte critique : REPORTÉE (décision, pas un trou).** Les `refs` du rapport
   `orvyren/crit/v1` ne sont **pas** encore validées (`worker.run_critic`) :
   raison = les magasins enregistrés sont **report-only** et leur critique cite
   une ref absente de leur paquet (croisement `G-6`) ; le **rejeu k=10 à têtes
   de chaîne identiques doit être préservé**. **Condition de levée** (les trois
   réunies) : (a) nouvelle graine **re-scelée visiblement** avec une critique
   conforme au contrat ci-dessus (`observation:` observée ; `claim:` /
   `hypothesis:` résolues dans le paquet) ; (b) rejeu k=10 à têtes identiques
   sur le nouveau magasin ; (c) test de régression de la porte + activation de
   la comparaison dans `run_critic`. **Tant que la porte n'est pas levée**, les
   findings du critique sont **non vérifiés côté refs** — à dire tel quel dans
   tout artefact (aucune revendication « provenance complète »), conformément à
   N1.
5. **Magasins enregistrés.** Aucun magasin n'est réécrit en silence ; une
   graine scriptée porte son `SEED.json` (origine `scripted-demo`, jamais une
   session live), et tout re-seed est un commit visible avec ses hashs.

## Conséquences

- **Positives** : la sémantique des trois namespaces est opposable (fin des
  faux refus possibles sur `claim:`/`hypothesis:`) ; le blanchiment de ref reste
  interdit des deux côtés ; le report de la porte critique est motivé, daté et
  levable — il ne peut plus passer pour un oubli.
- **Contraintes** : le rejeu du magasin `store_usdc-2023-03` est gelé en
  l'état (critique non conforme au contrat, **report-only**) — la conformité
  viendra d'un nouveau magasin, pas d'une retouche ; `deterministic_validator`
  ne type pas encore les `refs` (refus typé porté par l'ACH, revue 18/10 N6).
- **Coût** : ~0 (aucun changement de code dans cette décision ; les portes
  actives existent déjà).

## Reste à faire

1. **Lever la porte critique** (G-6 / N1 / N2) : graine conforme re-scelée →
   rejeu k=10 → porte `run_critic` + test de régression (commit dédié).
2. Typer `refs` dans `deterministic_validator` (N6) au même moment (les deux
  contrôlent le même contrat).
3. Afficher « critic finding refs unverified » dans l'UI et les rapports
   d'audit tant que la porte est reportée.

## Références

`src/orvyren/agents/prompts.py` L86/L127 (namespaces, gelé) ·
`src/orvyren/agents/contracts.py` `ObservedRefs` ·
`src/orvyren/agents/tools.py` `JournalWriteTool` + `_fixture_refs` ·
`src/orvyren/agents/loop.py` `_record_evaluation` + `_observation_refs` ·
`src/orvyren/agents/worker.py` `build_evidence_packet` (W1/W2), `run_critic` ·
`D:/orvyren_work_2026-10-18/review/agents_chain.md` §2 N1/N2 ·
`docs/SUBMISSION_SCOPE_AND_GAPS.md` G-6 · `docs/ECARTS_REGISTRE.md` (AC-N1,
AC-N2) · `frozen/INDEX.md` · `tests/test_agents_mab.py` (rejeu k=10).
