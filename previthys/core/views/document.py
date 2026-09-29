#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.http import Http404
from django.utils import timezone
from django.views.generic import TemplateView

from core.models import CategorieAction, VersionDuerp
from core.utils import construire_donnees, construire_mesures_generales, filtre_structure, normaliser_donnees
from core.utils.donnees import avec_macaron
from core.utils.introduction import introduction_pour, methode, mise_en_forme
from core.views.crud import Lecture


class Document(Lecture, TemplateView):
    """Document unique imprimable : données actuelles, ou version archivée si pk est fourni."""
    template_name = "core/document.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        if pk:
            version = VersionDuerp.objects.filter(filtre_structure(self.request.user), pk=pk).first()
            if not version:
                raise Http404("Version introuvable")
            reference = timezone.localtime(version.date).date()   # « en retard » : à la date de la version archivée
            ctx.update({"donnees": normaliser_donnees(version.donnees, reference), "version": version,
                        "mesures_generales": [avec_macaron(a, reference) for a in version.mesures_generales]})
            intro = version.introduction                       # vide pour les archives antérieures à l'introduction
        else:
            reference = timezone.localdate()
            ctx["donnees"] = normaliser_donnees(construire_donnees(self.request.user), reference)
            ctx["mesures_generales"] = [avec_macaron(a, reference) for a in construire_mesures_generales(self.request.user)]
            intro = introduction_pour(self.request.user)
        ctx.update({"introduction": intro, "texte_introduction": mise_en_forme(intro.get("texte", "")), "methode": methode(),
                    "axes": axes_du_plan(ctx["donnees"], ctx["mesures_generales"]), "aujourdhui": timezone.localdate()})
        return ctx


def axes_du_plan(donnees, mesures_generales):
    """Axes du plan d'actions (catégories d'actions) avec leur nombre d'actions, à partir des données du document.
    Une action commune figure sous chacun de ses risques : elle n'est comptée qu'une fois (même identifiant)."""
    vues, comptes = set(), {}
    for unite in donnees:
        for r in unite["risques"]:
            for a in r["actions_toutes"]:
                vues.add((a.get("categorie", ""), a.get("id") or a["description"]))   # anciennes archives : sans id
    for a in mesures_generales:
        vues.add((a.get("categorie", ""), a.get("id") or a["description"]))
    for categorie, _ in vues:
        comptes[categorie or "Non classées"] = comptes.get(categorie or "Non classées", 0) + 1
    ordre = {c.nom: c.ordre for c in CategorieAction.objects.all()}
    return sorted(comptes.items(), key=lambda x: (ordre.get(x[0], 10 ** 6), x[0]))
