#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

"""Déclaration d'accessibilité (RGAA 4.1). Page publique : elle doit être accessible sans connexion."""

from django.conf import settings
from django.views.generic import TemplateView

from core.context_processors import etat_accessibilite


class Accessibilite(TemplateView):
    template_name = "core/accessibilite.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["declaration"] = dict(getattr(settings, "PREVITHYS_ACCESSIBILITE", {}))
        ctx["etat"] = etat_accessibilite()
        contact = ctx["declaration"].get("contact", "")
        ctx["contact_est_url"] = contact.startswith(("http://", "https://"))
        return ctx
