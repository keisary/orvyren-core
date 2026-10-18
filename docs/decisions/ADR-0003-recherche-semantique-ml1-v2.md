# ADR-0003 — Recherche sémantique / embeddings (ML-1) : reclassement en V2

**Date :** 2026-10-17 · **Statut : ACCEPTÉE** — actée le 2026-10-17 (chef d'équipe, mandat de
finalisation du périmètre restant) · **Portée :** bloc B (graphe & ML) — précision du gel
`FREEZE_V2.md` §B3 et des propositions B.4/B.5 de the v1 design notes (archived out of the repository).

## Contexte

Le gel v2 (B3) mentionne « ML v1 : ML-1 embeddings (pgvector, recherche sémantique) » ; DOC3 B.5 la
classe « retenue en v1, à étendre ». **État mesuré au 2026-10-17** : aucun lot du plan DOC4 (W1–W8)
ne porte cette brique ; aucune implémentation n'existe (`grep` sur `src/orvyren/` : 0 occurrence) ;
le stockage gelé pour le concours est **SQLite** (FREEZE B2) — incompatible avec pgvector ; aucune
clé d'embedding n'est fournie à l'équipe. La revendiquer en v1 serait un écart entre la
documentation et la mesure — inacceptable au regard de la règle projet « la mesure prime sur la doc ».

## Options examinées

1. **Micro-implémentation lexicale (SQLite FTS5) présentée comme « recherche »** — rejetée : ce
   n'est pas ce que le gel nomme (embeddings) ; requalifier la chose serait une réécriture
   silencieuse d'un élément gelé.
2. **Forcer pgvector dans la démo** — rejetée : contredit le choix B2 (SQLite pour le concours) et
   ajoute une dépendance d'infrastructure hors périmètre.
3. **Reclasser ML-1 en V2 par ADR explicite**, le déclarer tel quel dans l'UI (écran 5) et dans les
   documents de soumission — **retenue**.

## Décision

ML-1 (embeddings sémantiques) et l'extension vectorielle de la base sont **reclassés en V2**
(post-concours). La v1 reste : requêtes graphe déterministes (Q1–Q8), portes qualité, aucun vecteur
en chemin décisionnel. Toute réintroduction suit le protocole ADR (proposition → impact → acte daté).

## Conséquences

- L'écran 5 « Recherche & coût » affiche ce reclassement — jamais une capacité absente.
- `FREEZE_V2.md` (B2/B3) et DOC3 restent **inchangés** (textes gelés) ; le présent ADR prime comme
  décision datée, conformément au protocole `docs/decisions/`.
- Réouverture : post-concours (V2), dès qu'un stockage vectoriel et une clé d'embedding entrent
  dans le périmètre.

## Références

- `FREEZE_V2.md` §B2, §B3 · the v1 design notes (archived out of the repository) B.4/B.5 ·
  the v1 design notes (archived out of the repository) (lots W1–W8 : aucun lot ne porte ML-1) ·
  the v1 design notes (archived out of the repository) (gap déclaré, item « gelé orphelin »).
