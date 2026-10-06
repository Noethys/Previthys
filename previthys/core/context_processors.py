#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.conf import settings


ETATS_ACCESSIBILITE = {"non": "non conforme", "partiellement": "partiellement conforme", "totalement": "totalement conforme"}


def etat_accessibilite():
    """Mention légale du pied de page (« Accessibilité : non conforme », etc.), d'après PREVITHYS_ACCESSIBILITE.
    Tant que l'application est non conforme et qu'un audit est en cours, la mention le précise."""
    declaration = getattr(settings, "PREVITHYS_ACCESSIBILITE", {})
    etat = declaration.get("etat", "non")
    if etat not in ETATS_ACCESSIBILITE:
        etat = "non"
    mention = ETATS_ACCESSIBILITE[etat]
    if etat == "non" and declaration.get("audit_en_cours", True):
        mention += " (audit en cours)"
    return mention


def organisation(request):
    return {"PREVITHYS_ORGANISATION": settings.PREVITHYS_ORGANISATION, "ETAT_ACCESSIBILITE": etat_accessibilite()}
