"""Vue de mise à jour de l'application, réservée aux super-utilisateurs (voir core/utils/update.py)."""
#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from core.utils.update import Recherche_update, Update
from core.utils.version import GetVersion


class MiseAJour(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Installer une mise à jour modifie les fichiers de l'application : seul un super-utilisateur peut le faire."""
    template_name = "core/mise_a_jour.html"
    raise_exception = False   # redirige vers la connexion (anonyme) ou une page 403 (connecté sans le droit)

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        version_disponible, changelog = Recherche_update()
        ctx.update({"version_actuelle": GetVersion(), "version_disponible": version_disponible, "changelog": changelog})
        return ctx

    def post(self, request, *args, **kwargs):
        if Update():
            messages.success(request, "Mise à jour effectuée avec succès.")
        else:
            messages.error(request, "Échec de la mise à jour. Voir les journaux du serveur pour le détail.")
        return HttpResponseRedirect(reverse_lazy("mise_a_jour"))
