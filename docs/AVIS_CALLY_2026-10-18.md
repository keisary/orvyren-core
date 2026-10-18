# ORVYREN — l'avis de Cally

**18 octobre 2026 · dépôt lu au commit `71742fd` · points chauds vérifiés à la main dans le code**

## 1. Mon verdict

**6,5/10 aujourd'hui. 8/10 atteignable avant mardi 15:59 UTC.** La différence ne tient pas à une feature : elle tient à deux journées de raccordements et de dépouillement.

Le projet est cool, mais pas pour la raison qu'on croit. Ce n'est pas « un agent IA qui trade » — c'est **l'agent qui refuse, et qui le prouve**. Dans un concours rempli de bots qui promettent des rendements, la seule chose que presque personne ne peut pas copier en une nuit, c'est un dossier de preuve vérifiable hors ligne et un registre de 17 gaps assumés. Ça, c'est le vrai actif. Le reste — le graphe, les KPI, les 1 400 tests — c'est de l'infrastructure au service de cette phrase.

## 2. Ce qui est vraiment fort

- **La thèse produit.** « Décide, refuse, ou dis ce qui te manque — et laisse une trace qu'un tiers recalcule. » C'est un positionnement qu'un jury fintech comprend en dix secondes et qu'un concurrent ne copie pas en une nuit.
- **La discipline de preuve.** 1 418 tests hors-ligne (3 sautés), artefacts scellés par hash, `run_id` chaîné décision → politique → exécution, vérificateur tiers qui détecte 6 mutations sur 6, paquet d'audit v2 de 47 fichiers. À un hackathon, ce niveau de plomberie est rare. C'est ce qui transforme une démo en dossier.
- **Le registre des gaps.** 17 entrées ouvertes, nommées, localisées (dont les deux gênantes : `--execute` jamais exercé de bout en bout, segment rsETH qui rejoue la décision pilote USDC). Assumer ça publiquement, c'est un flex — et c'est exactement le genre de rigueur qu'un jury technique respecte.
- **La vitesse de l'équipe.** J'ai vu ce dépôt passer de la fusion W3 (~750 tests) à un produit avec SPA, vérificateur et scénario live en 48 h. Peu importe la qualité de chaque pièce : le potentiel d'exécution est là, et c'est ce qui rend le plan des 45 h crédible.
- **Le moment de démo.** `ARRET-3` → critique `INCOHERENTE` → `REQUIRE_APPROVAL` → `what_would_change` → `OFFLINE_PASS`. C'est une histoire avec un début, un refus et une preuve. Presque personne n'a ça.

## 3. Ce qui me dérange (vérifié moi-même)

**a) Le récit et l'écran ne racontent pas la même histoire.** C'est le risque n°1, avant tous les bugs. `DecisionScreen.tsx` (lignes 139-140) interroge en dur `api.decision("usdc-2023-03")` alors que le script promet rsETH. `artifacts.decision_case` (`src/orvyren/api/artifacts.py:632-638`) ne lit que `evidence/decision_<case>.json`, jamais `evidence/scenario_rseth/decision/` où vit l'abstention rsETH. Et `_run_roots` (`artifacts.py:92-104`) énumère `demo_runs/agents*` et `evidence/agents_live`, mais **pas** `evidence/scenario_rseth/agents_session` — donc le run jury du 18/10 n'est même pas découvert par l'API. Résultat : le présentateur raconte un cas, l'écran en montre un autre, et le « LIVE » décrit un transport qui rejoue des journaux. Un jury qui repère ça perd confiance dans tout le reste. À corriger avant toute cosmétique.

**b) Le bug de vérification de la dernière ligne.** J'ai lu `_verify_hashed_jsonl` (`artifacts.py:724-771`). La boucle recalcule `head = digest(strip(row))`, puis compare ce résultat à la ligne **suivante** via `prev_field`. À la dernière ligne, il n'y a plus de suivante : le digest recalculé n'est jamais comparé au `record_hash` stocké, et le `head` retourné est le hash *enregistré*, pas le recalculé. Une altération du seul payload final passe donc inaperçue de cette fonction. Dans un produit dont la promesse est « vérifiable », c'est existentiel. Correctif : ~30 minutes + un test qui cible la dernière ligne. En attendant, pas de badge vert sur ce contrôle.

**c) Trois affirmations qui sur-promettent.**
- `isFrozen` ne prouve pas que les retraits sont bloqués. Aave distingue le gel (supply/borrow) des sorties, qui restent possibles sous conditions. La phrase honnête : « Reserve freeze observed. Withdrawal availability was not established. »
- La réfutation d'HYP-004 est **assignée par le script de scénario** (`build_case_abstention`), ce n'est pas une découverte des agents. À étiqueter « Scenario assessment », pas « Agent outcome ».
- La comparaison **−31 %** du script (2 526,76 vs 1 686) n'est ni archivée en série ni synchronisée dans le temps. Le critique du run la conteste lui-même. À retirer ou à encadrer de sources et de dates distinctes.

**d) Des badges qui verdissent trop vite.** Un `snapshot_hash` présent n'est pas une vérification ; `hashes_complete` ne veut pas dire « vérifié indépendamment » ; un `DONE` de run n'est pas une autorisation. Le vert doit dire « contrôle effectué et passé », rien d'autre.

**e) L'UI actuelle sabote le produit.** Cyan `#22d3ee` + indigo `#818cf8`, polices système, cartes uniformes partout, textes à 9,5 px, et un orange `#fb923c` qui traîne encore dans la palette de `SigmaGraph.tsx:10` (banni à vie, celui-là). Le produit est sérieux ; l'écran dit « side project généré ». En dix minutes de jury, l'écran **est** le produit. C'est le meilleur retour sur investissement de la fin de semaine.

**f) La dette documentaire.** 1 411 vs 1 418 tests ; benchmark N=9 dans le script vs N=12 dans le rapport ; README qui parle encore de « 12 écrans » alors que la SPA examinée en a 5 ; `.docx` datés du 17/10 dans le paquet. Un jury qui trouve une incohérence arrête de croire le reste. Chaque chiffre cité à l'oral doit sortir d'un artefact courant, daté, référencé.

**g) Le risque opérationnel.** J-2, une machine de projection, un build frontend au dernier moment (pas de `node_modules` dans le dépôt), un préchauffage prévu à H-10. Le plan B (replay USDC si le LLM tombe) existe — il faut le répéter au moins une fois pour de vrai, chrono en main, pas seulement le lire.

## 4. Mon désaccord avec Astra (deux points)

- **La note.** Il dit 6/10 ; je dis 6,5 en l'état et 8 possible. Son diagnostic est juste, mais je suis moins pessimiste sur la vitesse de l'équipe — et plus dur que lui sur l'UI : tant qu'elle est cyan, le projet paraît moins sérieux qu'il ne l'est.
- **La priorisation UI.** Sa checklist couvre les cinq écrans (7 h 45 estimées). À J-2, je ne ferais pas ça : je ferais les tokens, le shell et **Live, Decision, Audit** — les trois écrans qui portent l'histoire, ~5 h — et sur Graph/Markets je ne ferais que la palette, les unités et les libellés. Le graphe est montré soixante secondes ; il ne mérite pas quarante-cinq minutes de refonte. Mieux vaut une recette complète qu'un cinquième écran poli.

## 5. Mon plan pour les ~45 h

**Ce soir — les verrous (3 à 4 h) :**
1. Correctif du hash de dernière ligne + test ciblé (30 min).
2. Dépouillement des claims : freeze, HYP-004, −31 %, sémantique des badges (1 h).
3. Endpoint de lecture scénario + découverte du run jury + sélection explicite (1,5 h).

**Demain — le visible (6 à 7 h) :**
4. Tokens + shell + Live + Decision + Audit ; Markets/Graph en version allégée (palette, unités, libellés).
5. Recette 1366 × 768, états erreur/vide, vérification des unités sur chaque écran.

**Lundi — le dossier (4 à 5 h) :**
6. Répétition complète du script avec chrono, plan B rejoué, paquet T10 vérifié depuis un dossier hors dépôt.
7. Contrôle de soumission : fichiers, `.docx` régénérés ou retirés, identités du paquet, marge avant l'échéance.

**Interdits jusqu'à mardi :** nouvelles features, merge de branches risquées (`feat/v1-hardening`, `feat/graph-v2-schema`), re-seed pour rendre la critique plus flatteuse, refonte du graphe, toute promesse de gain financier.

## 6. Ce que je dirais au jury (si je pitchais)

Ouverture : « Every agent wallet demo shows you a trade. This one shows you the trade it refused — and the proof you can verify offline. »

Clôture : « Bounded reasoning, independent policy, offline-verifiable records. Autonomous end-to-end execution and financial added value remain unproven — and we say so. »

## 7. Conclusion

Le projet est cool. Il n'est pas encore *démontrablement* cool. Le même code peut finir top tier ou mid tier selon les 24 prochaines heures — pas à cause d'une feature manquante, mais parce que la démo doit montrer le bon cas, la bonne preuve et les bonnes limites.

La bonne nouvelle : rien de ce qui manque n'est un gros chantier. Le bug de hash est petit, les claims sont du texte, l'endpoint est une lecture de fichiers déjà présents, et l'UI est une passe de tokens + trois écrans. Une personne motivée fait ça en deux jours en gardant du sommeil.

La mauvaise : chaque heure passée sur une feature neuve est une heure volée à la crédibilité. Et la crédibilité, c'est le seul produit qu'on vend ici.

— Cally
