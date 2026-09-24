#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.conf import settings


def organisation(request):
    return {"PREVITHYS_ORGANISATION": settings.PREVITHYS_ORGANISATION}
