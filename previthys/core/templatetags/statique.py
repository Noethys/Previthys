"""Balise {% static_v %} : URL d'un fichier statique suivie du numéro de version installée (ex. core.css?v=1.2.8).

Le navigateur garde les fichiers CSS et JavaScript en cache. En ajoutant la version à l'URL, chaque nouvelle version
de Previthys produit une URL différente : le navigateur télécharge alors les fichiers à jour, sans vider son cache.
"""
#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

import os
from functools import lru_cache

from django import template
from django.conf import settings
from django.templatetags.static import static

from core.utils.version import GetVersion

register = template.Library()


@lru_cache(maxsize=4)
def _version_pour(date_modification):
    """Lit versions.txt une seule fois par modification du fichier (et non à chaque fichier statique de chaque page)."""
    try:
        return GetVersion()
    except Exception:
        return str(int(date_modification))


def version_installee():
    try:
        date_modification = os.path.getmtime(os.path.join(settings.BASE_DIR, "versions.txt"))
    except OSError:
        return ""
    return _version_pour(date_modification)


@register.simple_tag
def static_v(chemin):
    url = static(chemin)
    version = version_installee()
    return "%s?v=%s" % (url, version) if version else url
