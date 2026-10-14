# ORVYREN-Core, en clair

## Le projet, en bref

ORVYREN-Core est un moteur de décision financière qui prouve ce qu'il avance. On l'a construit sur un cas réel : la chute de l'USDC pendant la faillite de SVB, en mars 2023, reconstruite heure par heure. La question de départ était simple. Quand trois sources donnent trois prix différents du même actif (0,86 chez Bitstamp, 0,877 sur l'agrégateur, 0,913 sur Binance), sur quoi un agent autonome a-t-il le droit de décider, et qu'est-ce qu'il doit prouver après coup ?

C'est notre projet pour le **FinTechathon 2026 de Shenzhen**, thème F : portefeuille on-chain piloté par un agent. Rendu le 20 octobre.

## Ce que le système fait

- **Décider.** Trois hypothèses pré-enregistrées et refutables (perturbation locale, stress général, artefact de données), avec une vraie sortie « je ne sais pas » quand une donnée manque.
- **Prouver.** Chaque chiffre qui compte est relié à l'observation qui le produit. Un énoncé sans référence est refusé par le graphe de preuves.
- **Borner.** Une couche de politique déterministe, sans aucun LLM, rend un verdict : autorisé, refusé, ou soumis à approbation humaine. L'agent ne détient aucune clé. Un humain exécute, et l'agent vérifie ensuite le reçu on-chain contre l'intention autorisée.
- **Archiver.** Un dossier d'audit d'une page, auto-porteur, avec l'empreinte SHA-256 de chaque pièce.

## Pourquoi c'est intéressant, même sans aimer la finance

Tout tourne hors-ligne, en Python pur : zéro dépendance, zéro réseau, zéro secret. Un parcours complet prend moins d'une seconde. Les décisions se rejouent à l'octet près, et le dossier d'audit lui-même se reconstruit à l'identique. La suite de tests compte 147 cas, dont des attaques volontaires : montants NaN, données corrompues, rejeu d'intention, injection.

## Essayer, si on vous a filé le zip de revue

```bash
python -m unittest discover -s tests   # les 147 tests
python run_pipeline.py                 # qualité -> décision -> politique -> dossier
python run_audit.py --serve            # le dossier d'audit sur http://127.0.0.1:8000
```

Python 3.11 ou plus récent suffit. Rien à installer. Le dépôt GitHub reste privé jusqu'à la soumission.

## Ce qu'on cherche

Des yeux neufs. Le kit de revue (`docs/REVIEW_KIT.md`) liste les angles à attaquer : contournement de politique, vérification de reçu, équité de la baseline. Un retour utile tient en cinq lignes : le problème, la preuve (fichier et ligne), l'impact, la proposition, le test qui le prouverait. Le résumé des dernières trouvailles est dans `revue-en-bref.md`.
