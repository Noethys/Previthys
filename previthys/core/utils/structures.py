#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.db.models import Q


def filtre_structure(user, prefixe=""):
    """Filtre Q limitant aux structures de l'utilisateur (et aux objets sans structure)."""
    if user.is_superuser:
        return Q()
    return Q(**{prefixe + "structure__in": user.structures.all()}) | Q(**{prefixe + "structure__isnull": True})
