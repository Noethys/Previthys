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


def filtre_actions(user):
    """Filtre Q des actions de prévention visibles : celles liées à au moins un risque visible, et les actions
    générales (sans risque) de ses structures ou sans structure. S'utilise sans .distinct() (sous-requête)."""
    if user.is_superuser:
        return Q()
    from core.models import ActionPrevention, Risque
    risques_visibles = Risque.objects.filter(filtre_structure(user, "unite__"))
    liees = ActionPrevention.objects.filter(risques__in=risques_visibles).values("pk")
    generales = ActionPrevention.objects.filter(risques__isnull=True).filter(filtre_structure(user)).values("pk")
    return Q(pk__in=liees) | Q(pk__in=generales)   # sous-requêtes : pas de jointure, donc pas de doublons
