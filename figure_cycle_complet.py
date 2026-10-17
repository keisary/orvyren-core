#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Figure : ORVYREN — le cycle complet visé, et l'écart réel actuel.

Circular 9-station loop. Colour code:
  green  = implemented and tested today (with proof)
  amber  = partial / demonstration values / static version
  red    = missing entirely (the real work ahead)
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figures", "orvyren_cycle_complet.png")

GREEN = "#2e7d32"
AMBER = "#ef6c00"
RED = "#c62828"
GREY = "#546e7a"

# (angle_deg, title, state, note)
STATIONS = [
    (90,  "1. SURVEILLER\nl'exposition",        "partial",
     "Baseline A0 sur une fenêtre\nabsente : surveillance continue,\nmulti-actifs, multi-venues"),
    (50,  "2. DÉTECTER\nun épisode",            "green",
     "H1/H2/H3 pré-enregistrées,\ncritères chiffrés gelés,\nINCONCLUSIVE prouvé par test"),
    (10,  "3. OUVRIR DES\nBRANCHES CONCURRENTES", "red",
     "Aucun registre de branches.\nPromis par la conception §7 :\ncycle de vie, preuves, révisions"),
    (-30, "4. CALCULER LA\nVALEUR DE L'INFORMATION", "red",
     "Le système cherche un fait\ndiscriminant sans calculer\ns'il vaut son coût (EVOI)"),
    (-70, "5. EXÉCUTER LES\nRECHERCHES (outils)", "red",
     "Aucun agent : pas de boucle\nplan→outil→évaluation,\npas de budget de recherche"),
    (-110, "6. RENDRE UN\nVERDICT PAR BRANCHE", "partial",
     "Verdicts statiques sur 3\nhypothèses ; pas de mise à jour\ndynamique ni de fusion"),
    (-150, "7. DÉCIDER\n(exposition, scénarios)", "partial",
     "Moteur réel, mais exposition\n500/350 = valeurs de démonstration ;\npas de portefeuille modélisé"),
    (170, "8. PASSER LES\nVERROUS", "partial",
     "Politique déterministe + vérif.\nde reçu : testés (116 tests).\nManque : permissions on-chain réelles"),
    (130, "9. ARCHIVER\nET CALIBRER", "partial",
     "Dossier d'audit réel (1 page,\nhashes OK) ; manque la calibration :\nprévisions gelées vs résultats"),
]

COLOR = {"green": GREEN, "amber": AMBER, "partial": AMBER, "red": RED}
LABEL = {"green": "fait et testé", "amber": "partiel / démonstration",
         "partial": "partiel / démonstration", "red": "manquant"}


def main():
    fig, ax = plt.subplots(figsize=(13.2, 10.2))
    ax.set_xlim(-1.75, 1.75)
    ax.set_ylim(-1.62, 1.56)
    ax.axis("off")
    radius = 1.06

    positions = []
    for angle, title, state, note in STATIONS:
        import math
        rad = math.radians(angle)
        x, y = radius * math.cos(rad), radius * math.sin(rad)
        positions.append((x, y))

    # circular arrows between consecutive stations
    for i in range(len(positions)):
        x0, y0 = positions[i]
        x1, y1 = positions[(i + 1) % len(positions)]
        # Endpoints are pulled back from the station boxes via shrinkA/shrinkB
        # (points, scale-independent); the boxes (zorder=3, white face) cover
        # whatever remains. A data-space shrink would depend on the axes scale.
        arrow = FancyArrowPatch(
            (x0, y0), (x1, y1), connectionstyle="arc3,rad=-0.22",
            arrowstyle="-|>", mutation_scale=18, linewidth=1.6, color=GREY, alpha=0.85,
            shrinkA=34, shrinkB=34,
        )
        ax.add_patch(arrow)

    for (angle, title, state, note), (x, y) in zip(STATIONS, positions):
        color = COLOR[state]
        box = FancyBboxPatch(
            (x - 0.30, y - 0.115), 0.60, 0.23,
            boxstyle="round,pad=0.012,rounding_size=0.03",
            linewidth=2.0, edgecolor=color, facecolor="white", zorder=3,
        )
        ax.add_patch(box)
        ax.text(x, y, title, ha="center", va="center", fontsize=8.6,
                fontweight="bold", color=color, zorder=4, linespacing=1.25)
        # note placed outward
        import math
        rad = math.radians(angle)
        nx, ny = x + 0.44 * math.cos(rad), y + 0.30 * math.sin(rad)
        ha = "left" if math.cos(rad) >= 0 else "right"
        ax.text(nx, ny, note, ha=ha, va="center", fontsize=7.1, color="#37474f",
                zorder=4, linespacing=1.3,
                bbox=dict(boxstyle="round,pad=0.32", facecolor="#fafafa",
                          edgecolor="#cfd8dc", linewidth=0.7))

    # centre
    ax.text(0, 0.12, "ORVYREN", ha="center", va="center", fontsize=19,
            fontweight="bold", color="#1a237e")
    ax.text(0, -0.03, "le cycle complet visé", ha="center", va="center",
            fontsize=10.5, color="#455a64")
    counts = {"green": 0, "partial": 0, "red": 0}
    for _, _, state, _ in STATIONS:
        counts["green" if state == "green" else ("red" if state == "red" else "partial")] += 1
    ax.text(0, -0.16,
            f"{counts['green']} vert = fait et testé aujourd'hui  ·  "
            f"{counts['partial']} orange = partiel ou valeurs de démonstration  ·  "
            f"{counts['red']} rouges = à construire",
            ha="center", va="center", fontsize=8.6, color="#37474f")

    fig.suptitle(
        "Où en est réellement ORVYREN : le cycle complet, et ce qui manque pour l'atteindre",
        fontsize=13.5, fontweight="bold", y=0.975,
    )
    ax.text(0, -1.52,
            "Le prototype actuel couvre surtout les stations 2, 8 et 9 (détection, verrous, dossier). "
            "Le cœur du projet — branches concurrentes, valeur de l'information, agent de recherche, calibration — reste à construire.",
            ha="center", va="center", fontsize=8.8, color="#37474f", style="italic")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=170, bbox_inches="tight", facecolor="white")
    print("figure:", OUT)
    for _, title, state, _ in STATIONS:
        print(f"  [{LABEL[state]:26s}] {title.replace(chr(10), ' ')}")


if __name__ == "__main__":
    main()
