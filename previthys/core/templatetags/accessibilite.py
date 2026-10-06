#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

"""Outils d'accessibilité (RGAA 4.1) pour les gabarits.

- {{ field|accessible }} : affiche le champ en le reliant à son aide et à ses erreurs (aria-describedby) et en
  signalant une saisie invalide (aria-invalid). Critères RGAA 11.10 et 11.11.
- {% page_active "risques_" %} : renvoie aria-current="page" si la page en cours correspond au préfixe donné.
  Critère RGAA 12.1 (le lien de la rubrique en cours est restitué comme tel).
"""

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


def id_aide(field):
    return "%s_aide" % field.id_for_label


def id_erreur(field):
    return "%s_erreur" % field.id_for_label


@register.filter
def accessible(field):
    """Rendu du champ avec aria-describedby (aide, erreurs) et aria-invalid si le champ est en erreur."""
    decrit_par = []
    if field.help_text:
        decrit_par.append(id_aide(field))
    if field.errors:
        decrit_par.append(id_erreur(field))
    attrs = {}
    if decrit_par:
        existant = field.field.widget.attrs.get("aria-describedby")
        attrs["aria-describedby"] = " ".join(([existant] if existant else []) + decrit_par)
    if field.errors:
        attrs["aria-invalid"] = "true"
    return field.as_widget(attrs=attrs)


@register.filter
def aide_id(field):
    return id_aide(field)


@register.filter
def erreur_id(field):
    return id_erreur(field)


@register.simple_tag(takes_context=True)
def page_active(context, *prefixes):
    """aria-current="page" pour le lien de navigation de la page en cours (un ou plusieurs préfixes de nom d'URL)."""
    requete = context.get("request")
    correspondance = getattr(requete, "resolver_match", None)
    nom = correspondance.url_name if correspondance else ""
    if nom and any(nom == p or (p.endswith("_") and nom.startswith(p)) for p in prefixes):
        return mark_safe(' aria-current="page"')
    return ""


@register.simple_tag(takes_context=True)
def rubrique_active(context, *prefixes):
    """Classe « active » pour un menu déroulant dont une entrée correspond à la page en cours."""
    return "active" if page_active(context, *prefixes) else ""


@register.simple_tag
def texte_masque(texte):
    """Texte restitué par les lecteurs d'écran mais masqué à l'écran (classe Bootstrap visually-hidden), précédé d'une
    espace pour compléter un intitulé court : « Modifier » devient « Modifier Atelier mécanique »."""
    if not texte:
        return ""
    return format_html('<span class="visually-hidden"> {}</span>', texte)
