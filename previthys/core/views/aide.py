#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

"""Page « Aide » : documentation du logiciel, pour les utilisateurs et les administrateurs."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from core.utils.introduction import methode


class Aide(LoginRequiredMixin, TemplateView):
    template_name = "core/aide.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["methode"] = methode()   # barèmes et seuils réels, toujours à jour avec le code
        return ctx
