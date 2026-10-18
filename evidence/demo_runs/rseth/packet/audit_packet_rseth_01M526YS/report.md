# ORVYREN — rapport de session de démonstration

- session : `evidence/demo_runs/rseth`
- run_id : `01M526YS3FMDNS6Z9EJYJPPG1E` · cas : `rseth` · mode : **execute**
- chaîne : Base Sepolia (84532) — testnet uniquement, aucun argent réel

## Journal (append-only chaîné SHA-256)

- enregistrements : **83**
- chaîne recalculée : **OK (aucune écriture détectée)**
- têtes de flux : `{"exec": "86b4e1f8490ece2554b083060179e7a518d62e1d8cd5918c21e12e54a8a0ed79"}`

## Compteurs

- exécutions autorisées (entrées POLICY ALLOW) : 4
- refus hors chaîne (POLICY DENY) : 6
- demandes d'approbation (REQUIRE_APPROVAL) : 1
- transactions soumises : 13 · reçus enregistrés : 13
- signatures émises par le service : 13

## Vérification indépendante (relecture des tx_hash)

- 1 exécutions conformes, 6 refus hors chaîne, 12 tentatives forcées refusées par la chaîne

## Ce que ce rapport ne prouve pas

- les prix du testnet ne sont pas des données de marché (aucune performance n'est revendiquée) ;
- en dry-run, **aucune transaction n'a été envoyée** : les hashes sont factices et marqués `simulated` ;
- la couverture n'est pas l'exhaustivité : ce qui n'est pas journalisé n'existe pas pour le relecteur.
