#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

"""Aide contextuelle : {% lien_aide %} affiche un bouton « ? » qui ouvre la rubrique d'aide de la page en cours."""

from django import template
from django.urls import reverse
from django.utils.html import format_html

register = template.Library()

# Nom de l'adresse (ou son début) -> ancre de la rubrique dans core/aide.html. Le premier préfixe qui correspond l'emporte.
RUBRIQUES = [
    ("dashboard", "vue-ensemble"),
    ("unites_", "unites"),
    ("categories_actions_", "categories-actions"),
    ("categories_", "categories-risques"),
    ("risques_actions_", "actions-depuis-risque"),
    ("pieces_jointes_", "pieces-jointes"),
    ("risques_", "risques"),
    ("actions_", "plan-actions"),
    ("introduction", "parametres-document"),
    ("document", "document"),
    ("versions_", "versions"),
    ("journal_", "journal"),
    ("mise_a_jour", "mise-a-jour"),
]


def rubrique_aide(nom_url):
    for prefixe, ancre in RUBRIQUES:
        if nom_url and nom_url.startswith(prefixe):
            return ancre
    return ""


@register.simple_tag(takes_context=True)
def lien_aide(context):
    requete = context.get("request")
    correspondance = getattr(requete, "resolver_match", None)
    ancre = rubrique_aide(correspondance.url_name if correspondance else "")
    if not ancre:
        return ""
    return format_html('<a class="lien-aide d-print-none" href="{}#{}" title="Aide sur cette page" aria-label="Aide sur cette page">?</a>',
                       reverse("aide"), ancre)
