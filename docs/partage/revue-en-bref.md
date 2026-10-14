# La revue d'Astra, en bref

Astra, notre « chef technique » (le modèle gpt-6-astra piloté via Codex), a passé le projet au peigne fin. Dix minutes de travail, 18 findings, chaque affirmation vérifiée par exécution. Verdict : **50/100 en l'état**. Objectif réaliste : **70 à 75 d'ici le 20 octobre**. Voici le digest.

## Les cinq trouvailles les plus parlantes

1. **Un montant NaN passait toute la sécurité.** En flottant, `NaN > 100` est faux, donc la comparaison de plafond ne l'attrapait pas : verdict ALLOW sur un montant invalide. Corrigé (refus net `AMOUNT_NOT_FINITE`) et testé.
2. **Retirer une source de données faisait planter le moteur.** La scène la plus forte de la démo, « il manque une donnée, l'agent s'abstient », était cassée par deux bugs d'index et de formatage. Corrigé : le moteur rend maintenant une abstention propre, avec la liste de ce qui manque.
3. **Le ZIP de revue embarquait `.env`.** Le `.gitignore` ne freine pas un zip construit en parcourant le dossier, et le masque des URLs RPC laissait fuir un identifiant placé en tête de chemin. Corrigé : liste noire dans `make_package.py`, plus un re-scan de l'archive avant livraison.
4. **« Transférer de l'USDC ne réduit pas l'exposition à l'USDC ».** Si trésorerie et réserve appartiennent à la même entité, déplacer le jeton ne change pas le risque lié à l'émetteur. À raconter honnêtement : la démo teste la chaîne de contrôle. Pas une couverture.
5. **Le point-in-time est à moitié fait.** Le résultat actuel est une analyse rétrospective de la fenêtre complète. Le rejeu « seulement ce qui était connaissable à l'instant T » reste à construire, avec les horodatages de disponibilité des bougies.

## Corrigé dans la nuit

Les quatre défauts critiques côté code (NaN, abstention, pipeline qui continuait après un échec, secrets dans le paquet) : reproduits, corrigés, épinglés par 15 tests de garde. La suite compte 147 tests. Les sorties nominales sont identiques à l'octet près.

## Ce qui reste

- Des décisions d'équipe : veto bloquant des artefacts de données, session persistante des autorisations, méthodologie du préenregistrement.
- Des actions humaines : wallet testnet financé, vidéo de moins de cinq minutes, deck.
- Et de la revue, toujours : `docs/REVIEW_KIT.md` liste les angles d'attaque.
