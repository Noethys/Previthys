"""Introduction du document unique : choix de l'introduction, mise en forme du texte, méthode d'évaluation."""
#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

import base64
import re

from django.utils.html import escape
from django.utils.safestring import mark_safe

from core.models import FREQUENCE, GRAVITE, MAITRISE, SEUIL_CRITIQUE, SEUIL_MOYEN, Introduction, _nombre, _tranches

TAILLE_MAX_LOGO = 500 * 1024
SIGNATURES_LOGO = {b"\x89PNG\r\n\x1a\n": "image/png", b"\xff\xd8\xff": "image/jpeg"}

AIDE_SYNTAXE = ("Mise en forme simple : une ligne vide sépare les paragraphes ; « ## Titre » pour un titre de partie ; "
                "« - » en début de ligne pour une liste à puces.")


def logo_en_data_uri(fichier):
    """Contrôle un logo déposé (PNG ou JPEG, 500 Ko maximum) et le convertit en data URI, stockée en base :
    pas de fichier sur le disque, et l'image est archivée telle quelle avec chaque version du DUERP."""
    contenu = fichier.read()
    if len(contenu) > TAILLE_MAX_LOGO:
        raise ValueError("Le logo ne doit pas dépasser 500 Ko.")
    for signature, type_mime in SIGNATURES_LOGO.items():
        if contenu.startswith(signature):
            return "data:%s;base64,%s" % (type_mime, base64.b64encode(contenu).decode("ascii"))
    raise ValueError("Le logo doit être une image PNG ou JPEG.")


def mise_en_forme(texte):
    """Texte saisi → HTML sûr (tout est échappé) : paragraphes, titres « ## », listes « - »."""
    blocs, html = re.split(r"\n\s*\n", (texte or "").replace("\r", "").strip()), []
    for bloc in blocs:
        lignes = [l.rstrip() for l in bloc.split("\n") if l.strip()]
        if not lignes:
            continue
        paragraphe = []

        def vider():
            if paragraphe:
                html.append("<p>%s</p>" % "<br>".join(escape(l) for l in paragraphe))
                paragraphe.clear()
        liste = []

        def vider_liste():
            if liste:
                html.append("<ul>%s</ul>" % "".join("<li>%s</li>" % escape(l) for l in liste))
                liste.clear()
        for ligne in lignes:
            nette = ligne.strip()
            if nette.startswith("## "):
                vider(); vider_liste()
                html.append('<h3 class="h6 mt-3">%s</h3>' % escape(nette[3:].strip()))
            elif re.match(r"^[-•*]\s+", nette):
                vider()
                liste.append(re.sub(r"^[-•*]\s+", "", nette))
            else:
                vider_liste()
                paragraphe.append(nette)
        vider(); vider_liste()
    return mark_safe("".join(html))


def introduction_pour(user, structure=None):
    """Introduction à utiliser : celle de la structure demandée (ou de la seule structure de l'utilisateur),
    sinon l'introduction par défaut (sans structure). Retourne un dictionnaire (format d'archivage)."""
    if structure is None and not user.is_superuser:
        structures = list(user.structures.all()[:2])
        structure = structures[0] if len(structures) == 1 else None
    intro = Introduction.objects.filter(structure=structure).first() if structure else None
    intro = intro or Introduction.objects.filter(structure__isnull=True).first()
    return {"texte": intro.texte, "logo": intro.logo} if intro else {}


def methode():
    """Barèmes de cotation et niveaux, tels qu'appliqués par Previthys (toujours à jour avec le code)."""
    def bareme(choix):
        return [{"note": v, "libelle": l.split(" - ", 1)[1]} for v, l in choix]
    faible, moyen, critique = _tranches()
    return {
        "baremes": [("Fréquence (F)", "Fréquence d'exposition au danger", bareme(FREQUENCE)),
                    ("Gravité (G)", "Gravité des dommages potentiels", bareme(GRAVITE)),
                    ("Maîtrise (M)", "Niveau de maîtrise du risque : plus la note est élevée, moins le risque est maîtrisé", bareme(MAITRISE))],
        "niveaux": [(code, lib, _nombre(t[0]), _nombre(t[-1])) for (code, lib), t in zip((("faible", "Faible"), ("moyen", "Moyen"), ("critique", "Critique")), (faible, moyen, critique))],
        "seuils": (SEUIL_MOYEN, SEUIL_CRITIQUE),
    }
