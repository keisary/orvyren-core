# `evidence/demo_chain/` — micro-chaîne de démonstration PUBLIQUE

Extrait **versionné** de la session de démonstration réelle `rseth` exécutée le
2026-10-16 sur **Base Sepolia** (runs A → E, cf. `evidence/demo_runs/rseth/` qui
reste, lui, git-ignoré par design : journaux de console, `session.json`,
`signatures.jsonl`, `runs/` locaux).

Pourquoi ce répertoire existe : un clone propre du dépôt ne contient pas
`evidence/demo_runs/` (motif `.gitignore` `demo_runs/`). Sans ces données, les
écrans 10–12 de l'UI affichaient « SOURCE ABSENTE » et les tests du
vérificateur T10 se sautaient. La micro-chaîne ci-dessous rend ces preuves
**lisibles et re-jouables hors ligne par un tiers**, sans jamais publier de
secret.

## Contenu (`rseth/`)

| Fichier | Rôle |
|---|---|
| `audit.jsonl` | journal d'exécution chaîné (`prev_hash` → `record_hash`), 84 enregistrements |
| `receipts/*.json` | 13 reçus RPC bruts des transactions on-chain (13 `SUBMIT`) |
| `export/manifest.json` | manifeste d'export du RUN E (compteurs, tête de chaîne **au moment de l'export**) |
| `policy.effective.json` | paramètres de la politique hors chaîne effectivement appliquée (nécessaire au contrôle A5 du paquet d'audit) |
| `MANIFEST.sha256` | empreintes SHA-256 des fichiers ci-dessus (`sha256sum -c MANIFEST.sha256`) |

Le manifeste d'export a été écrit **avant** l'`OUTCOME` final du RUN E : il
déclare 83 enregistrements et la tête `86b4e1f8…`, alors que `audit.jsonl` en
contient 84 (la tête courante est celle du dernier enregistrement). Cet écart
est normal et reproduit tel quel ; il n'est pas « corrigé » à la main.

## Ce qui n'est PAS ici

Aucune clé privée, aucun `.env`, aucun `session.json`, aucun journal de
console, aucune signature locale. Les adresses, hashes de transaction, logs et
reçus publiés ici sont des **données publiques de chaîne** (Base Sepolia).

## Priorité des sources dans l'UI

Les écrans 10–12 préfèrent `evidence/demo_runs/rseth/` quand la session locale
complète est présente (poste de démonstration), et retombent sinon sur cette
micro-chaîne versionnée. Les tests (`tests/test_verify_engine.py`) utilisent
toujours `evidence/demo_chain/rseth` pour être verts sur un clone.

## Vérification

```bash
cd evidence/demo_chain/rseth
sha256sum -c MANIFEST.sha256
```
