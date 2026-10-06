#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

"""Mentions légales et informations sur les données personnelles. Page publique, consultable sans connexion."""

from django.conf import settings
from django.views.generic import TemplateView


class MentionsLegales(TemplateView):
    template_name = "core/mentions_legales.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        mentions = dict(getattr(settings, "PREVITHYS_MENTIONS_LEGALES", {}))
        mentions["editeur"] = mentions.get("editeur") or settings.PREVITHYS_ORGANISATION
        ctx["mentions"] = mentions
        ctx["dpo_est_courriel"] = "@" in mentions.get("dpo", "") and " " not in mentions.get("dpo", "").strip()
        return ctx
