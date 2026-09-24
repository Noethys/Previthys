#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.http import Http404
from django.views.generic import TemplateView

from core.models import VersionDuerp
from core.utils import construire_donnees, filtre_structure, normaliser_donnees
from core.views.crud import Lecture


class Document(Lecture, TemplateView):
    """Document unique imprimable : données actuelles, ou version archivée si pk est fourni."""
    template_name = "core/document.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        if pk:
            version = VersionDuerp.objects.filter(filtre_structure(self.request.user), pk=pk).first()
            if not version:
                raise Http404("Version introuvable")
            ctx.update({"donnees": normaliser_donnees(version.donnees), "version": version})
        else:
            ctx["donnees"] = normaliser_donnees(construire_donnees(self.request.user))
        return ctx
