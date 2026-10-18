# ORVYREN — EN CLAIR
### Document 1/4 — l'explication simple (avec schémas)

**ORVYREN, en une phrase** : un système d'agents qui transforme des signaux financiers publics en **décisions bornées et vérifiables** — il croise les sources, formule les explications possibles, cherche le fait qui les départage, décide (ou déclare honnêtement « je ne sais pas »), n'agit que dans une enveloppe autorisée, et laisse une **trace qu'un tiers peut recalculer**.

---

## 1. Le problème, simplement

Les marchés on-chain sont transparents : tous les prix, tous les mouvements sont publics. Mais **leurs risques ne sont pas lisibles** : la solvabilité d'une trésorerie dépend d'une chaîne de collatéraux (stablecoins, jetons de staking, actifs re-déposés partout) dont **la valeur retenue par les protocoles s'écarte silencieusement du prix auquel on peut réellement vendre** — et dont la dégradation est annoncée des jours à des semaines à l'avance par des signaux publics dispersés.

Deux exemples réels, mesurés :

- **Mars 2023 (USDC/SVB)** — le même USDC valait **0,805 $** sur une place, **0,863 $** sur l'agrégat, **0,913 $** sur une autre, à quelques heures d'écart ; l'oracle d'Aave le retenait à **0,96 $**. Qui croire ? Et que fait la trésorerie qui le détient ?
- **Avril 2026 (rsETH/KelpDAO)** — le plafond de collatéral d'un marché se **sature à 99,999 %**, le marché est gelé à la seconde près, pendant que l'oracle affiche encore ~2 500 $ pour un actif dont la sortie réalisable s'effondre. **Fenêtre utile mesurée : 46–77 minutes.**

## 2. Pour qui

1. **Trésoreries d'organisations on-chain** (DAOs, protocoles, fonds) — objectif : **prévoir et anticiper le risque** ; c'est la cible prioritaire (des exemples réels : Lido, ENS, Aave, Sky, Mantle…).
2. **Équipes de trading crypto** — objectif : **rentabilité** ; même système, critères différents.
3. **Banques et institutions** — vision phase 2.

## 3. Ce que fait ORVYREN — le cycle

```
   ┌────────────────────────────────────────────────────────────────────┐
   │                     LA BOUCLE ORVYREN (v1)                         │
   └────────────────────────────────────────────────────────────────────┘

   ①  OBSERVER        sources multiples, horodatées, avec provenance
        │              (prix multi-places, chaîne, documents officiels)
        ▼
   ②  VÉRIFIER        qualité, unités, trous DÉCLARÉS (jamais inventés)
        │
        ▼
   ③  DÉTECTER        seuils : décote, dispersion, divergence oracle/marché…
        │
        ▼
   ④  HYPOTHÈSES      plusieurs explications concurrentes,
        │              critères de réfutation écrits D'AVANCE
        ▼
   ⑤  RECHERCHER      le fait qui départage (borné : coût, temps, arrêt)
        │
        ▼
   ⑥  DÉCIDER         action bornée, abstention (« il manque ceci »),
        │              ou escalade vers un humain
        ▼
   ⑦  AUTORISER       verrous HORS du modèle : politique déterministe
        │              + enveloppe on-chain (permissions votées)
        ▼
   ⑧  EXÉCUTER        l'agent exécute seul — DANS l'enveloppe ;
        │              clé isolée, testnet, plafonds stricts
        ▼
   ⑨  VÉRIFIER &      reçu on-chain contrôlé, dossier + journal
       ARCHIVER        recalculables par un tiers
```

## 4. Les principes non négociables

1. **Aucun calcul financier ne vient d'un modèle de langage.** Les agents structurent, expliquent, proposent ; des fonctions déterministes calculent, vérifient, refusent.
2. **Les contradictions sont conservées** — jamais effacées en silence.
3. **Une hypothèse n'est jamais promue en fait** parce qu'elle est répétée ou « approuvée » par un modèle.
4. **L'agent ne peut pas élargir ses droits** : la limite est appliquée hors de lui (politique + chaîne), et révocable par ses propriétaires.
5. **« Je ne sais pas » est une réponse de première classe** — avec la liste de ce qui manque pour conclure.

## 5. Ce qui est déjà prouvé (pas des promesses)

| Preuve | Résultat mesuré |
|---|---|
| Données | 100 % **gratuites** : état on-chain historique (2021→2026) + prix minute multi-places — le projet ne dépend d'aucun budget données |
| Épisode rsETH 2026 | Plafond saturé à **99,9989 %**, gel daté à la seconde (bloc 24 908 723), oracle vs marché : **−31 %** (−32,9 % au gel, −30,3 % au 20/04) |
| Épisode stETH 2022 | Décote réalisable **6,2 %**, signal **~4 semaines** avant le gel Celsius |
| Épisode USDC 2023 | Dispersion inter-places **870 bps** ; l'oracle sous-estime la décote |
| Enveloppe d'exécution | Déjà le standard chez la cible (précédent ENS), **déployée et vérifiée sur Base Sepolia** |
| Code & tests | Couche données + reconstructions d'épisodes + politique : **221 tests verts** |

## 6. Ce que la v1 va construire (juste après ce gel)

- **Agents réels** : un orchestrateur + un critique adversarial (modèles DeepSeek/MiMo par API), chacun avec sa mémoire interne séparée du graphe.
- **Le graphe de connaissance** : faits, relations typées (34 types), provenance et horloges — la mémoire partagée vérifiable.
- **La décision** : branches d'hypothèses, recherche du fait discriminant (déterministe), abstention ; catalogues d'actions bornées.
- **Le double verrou** : politique (14 règles hors LLM) + permissions on-chain — l'agent exécute seul, **dans** l'enveloppe.
- **La preuve** : reçu on-chain public + journal à trois flux chaînés + vérificateur tiers.
- **Le replay** : rejouer de vrais épisodes historiques et montrer l'évolution des réflexions, hypothèses et décisions.

## 7. Un dossier de décision, concrètement

```
   QUESTION : face aux signaux du 18/04/2026 (rsETH),
              faut-il réduire l'exposition, ou attendre ?

   ┌─ PREUVES ──────────┐  ┌─ HYPOTHÈSES ─────────┐  ┌─ RECHERCHE ──────┐
   │ oracle 2 513 $      │  │ H1 stress réel    ?  │  │ → vérifier le    │
   │ marché  1 686 $     │→ │ H2 incident isolé ?  │→ │   plafond de     │
   │ plafond 99,999 %    │  │ H3 artefact ?        │  │   collatéral…    │
   └─────────────────────┘  └─────────────────────┘  └────────┬─────────┘
                                                               ▼
   ┌─ DÉCISION ──────────────────┐  ┌─ VERROUS ──────────────┐  ┌─ PREUVE ────┐
   │ ACTION BORNÉE : réduction   │  │ politique : ALLOW      │  │ tx testnet  │
   │ ≤ plafonds · actif autorisé │→ │ chaîne : dans le rôle  │→ │ reçue ✓     │
   │ ou ABSTENTION si preuves ✗  │  │ sinon : DENY, tracé    │  │ journal ✓   │
   └─────────────────────────────┘  └────────────────────────┘  └─────────────┘
```

## 8. Les documents qui suivent

- **2/4 — Technique complet** : l'architecture, les mécanismes, les décisions gelées, la v1 exacte.
- **3/4 — Propositions & pistes** : ce que les recherches ont exploré et écarté pour la v1 (banques, VoI, ML avancé…), à rouvrir plus tard.
- **4/4 — Plan d'implémentation** : le découpage du travail (modules / sprints) pour toute l'équipe.

*Statut : ce document accompagne le gel v2 (15/10/2026). Les chiffres cités sont mesurés et reproductibles depuis le dépôt.*
