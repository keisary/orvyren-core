# ORVYREN — rapport de session de démonstration

- session : `research/raw_w3d/session_dry`
- run_id : `01M4ZWN1JW9E9GWQ5CXMAAE6AT` · cas : `rseth` · mode : **dry-run**
- chaîne : Base Sepolia (84532) — testnet uniquement, aucun argent réel

## Journal (append-only chaîné SHA-256)

- enregistrements : **36**
- chaîne recalculée : **OK (aucune écriture détectée)**
- têtes de flux : `{"exec": "ff503c7db08749d1222a0ea154048926ce346cb1a2cb709b82ff87bdd87d1676"}`

## Compteurs

- exécutions autorisées (entrées POLICY ALLOW) : 3
- refus hors chaîne (POLICY DENY) : 6
- demandes d'approbation (REQUIRE_APPROVAL) : 1
- transactions soumises : 1 · reçus enregistrés : 0
- signatures émises par le service : 1

## Vérification indépendante (relecture des tx_hash)

- confrontation à la chaîne non exécutée (dry-run) — relancer le run E en `--execute --rpc` après le run A réel

## Ce que ce rapport ne prouve pas

- les prix du testnet ne sont pas des données de marché (aucune performance n'est revendiquée) ;
- en dry-run, **aucune transaction n'a été envoyée** : les hashes sont factices et marqués `simulated` ;
- la couverture n'est pas l'exhaustivité : ce qui n'est pas journalisé n'existe pas pour le relecteur.
