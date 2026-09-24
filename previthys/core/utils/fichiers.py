"""Validation des fichiers joints à un risque : extensions autorisées, taille, signature du contenu.

La validation par extension seule est insuffisante (un exécutable renommé en .jpg passerait) : on vérifie donc aussi
les premiers octets du fichier (« signature » ou « nombre magique ») pour les formats qui en ont une fiable.
"""
#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

import os

from django.core.exceptions import ValidationError

TAILLE_MAX_OCTETS = 15 * 1024 * 1024   # 15 Mo par fichier
NOMBRE_MAX_FICHIERS = 10               # par formulaire envoyé

# Extension -> signatures acceptées en tête de fichier (aucune vérification fiable possible pour .txt).
# Le format SVG est volontairement exclu : un SVG peut contenir du JavaScript exécuté par le navigateur (XSS).
SIGNATURES = {
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".webp": (b"RIFF",),   # le sigle "WEBP" à l'octet 8 est vérifié séparément
    ".pdf": (b"%PDF-",),
    ".docx": (b"PK\x03\x04",),
    ".xlsx": (b"PK\x03\x04",),
    ".odt": (b"PK\x03\x04",),
    ".ods": (b"PK\x03\x04",),
    ".doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    ".xls": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    ".txt": None,
}
EXTENSIONS_IMAGES = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp"})
ACCEPT_INPUT = ",".join(sorted(SIGNATURES))
LIBELLE_TYPES_ACCEPTES = "images (jpg, png, gif, webp) et documents (pdf, doc, docx, xls, xlsx, odt, ods, txt)"


def est_image(nom_fichier):
    return os.path.splitext(nom_fichier)[1].lower() in EXTENSIONS_IMAGES


def valider_fichier(fichier):
    """Valide un fichier téléversé. Lève ValidationError avec un message destiné à l'utilisateur si besoin."""
    extension = os.path.splitext(fichier.name)[1].lower()
    if extension not in SIGNATURES:
        raise ValidationError("« %s » : type de fichier non autorisé. Types acceptés : %s." % (fichier.name, LIBELLE_TYPES_ACCEPTES))
    if fichier.size > TAILLE_MAX_OCTETS:
        raise ValidationError("« %s » dépasse la taille maximale autorisée (%d Mo)." % (fichier.name, TAILLE_MAX_OCTETS // (1024 * 1024)))
    if fichier.size == 0:
        raise ValidationError("« %s » est un fichier vide." % fichier.name)

    signatures = SIGNATURES[extension]
    if signatures is not None:
        entete = fichier.read(16)
        fichier.seek(0)
        if extension == ".webp":
            valide = entete[:4] == b"RIFF" and entete[8:12] == b"WEBP"
        else:
            valide = any(entete.startswith(s) for s in signatures)
        if not valide:
            raise ValidationError("« %s » : le contenu du fichier ne correspond pas à son extension." % fichier.name)
