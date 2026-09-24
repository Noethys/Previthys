#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

import os, codecs
from django.conf import settings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def lire_entete(texte):
    """Extrait le numéro de version de la première ligne d'un texte au format « Version X.Y.Z (...) : »."""
    premiere_ligne = texte.split("\n", 1)[0]
    debut = premiere_ligne.find("n")
    fin = premiere_ligne.find("(")
    if debut == -1 or fin == -1 or fin <= debut:
        return None
    return premiere_ligne[debut + 1:fin].strip()


def GetVersionTuple(version):
    """Convertit "1.2.10" en (1, 2, 10), pour une comparaison numérique fiable (10 > 9)."""
    morceaux = []
    for partie in version.split("."):
        chiffres = "".join(c for c in partie if c.isdigit())
        morceaux.append(int(chiffres) if chiffres else 0)
    return tuple(morceaux)


def GetVersion():
    """Numéro de version actuellement installée."""
    texte = codecs.open(os.path.join(settings.BASE_DIR, "versions.txt"), encoding="utf-8", mode="r").read()
    version = lire_entete(texte)
    if not version:
        raise ValueError("Impossible de lire le numéro de version")
    return version
