# Licences et composants tiers

Le code d'ORVYREN-Core est publié sous licence **MIT** (voir `LICENSE`).
Le règlement du concours exige que « third-party data, code, and open-source components
are properly licensed ». Ce fichier recense ce qui est utilisé et sous quelles conditions.

## Dépendances logicielles

| Composant | Usage | Licence | Statut |
|---|---|---|---|
| Python (3.11) | langage | PSF License | standard |
| FastAPI | page d'audit / API de lecture | MIT | prévu |
| Pydantic | validation des schémas | MIT | prévu |
| psycopg | accès PostgreSQL | LGPL-3.0 | prévu |
| pytest / unittest | tests | MIT / PSF | unittest utilisé |

## Sources de données (utilisées, jamais redistribuées en tant que telles)

| Source | Usage | Conditions |
|---|---|---|
| DeFiLlama (`coins.llama.fi`, `stablecoins.llama.fi`) | prix historiques USDC, offres en circulation | API publique documentée ; quotas et conditions à revérifier au moment de l'usage (la doc annonce la fermeture d'endpoints gratuits le 13/11/2026 pour certains d'entre eux) |
| Bitstamp (API publique OHLC) | prix USDC/USD horaire | API publique, données de marché publiques |
| Binance (API publique klines) | prix USDC/USDT horaire | API publique, données de marché publiques |
| Circle (communiqué du 12/03/2023) | référence documentaire de l'émetteur | citation à la source, lien conservé ; le texte n'est pas reproduit intégralement |

## Chaînes et contrats

| Élément | Réseau | Usage |
|---|---|---|
| Base Sepolia (chain ID 84532) | testnet public | exécution de l'action bornée, actifs de test uniquement |
| USDC de test (Circle) | Base Sepolia | actif allowlisté de la démonstration |
| Uniswap v3 (`SwapRouter02`, `QuoterV2`, `Factory`) | Base Sepolia | lecture et, en option, swap de test étiqueté comme démonstration technique |

Aucune donnée propriétaire, aucun jeton de valeur, aucun fonds réel n'est utilisé dans le prototype.
