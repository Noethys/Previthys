"""Fonctions utilitaires : visibilité par structure, construction des données du DUERP, matrice, export Excel.

Les fonctions légères sont réexportées ici. L'export Excel reste dans `core.utils.export_xlsx`
(il charge openpyxl, inutile pour les autres écrans).
"""
#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from core.utils.donnees import construire_donnees, normaliser_donnees
from core.utils.matrice import repartition_par_categorie, repartition_par_niveau
from core.utils.structures import filtre_structure

__all__ = ["construire_donnees", "filtre_structure", "normaliser_donnees", "repartition_par_categorie", "repartition_par_niveau"]
