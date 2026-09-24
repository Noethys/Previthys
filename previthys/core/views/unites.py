#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.db.models import Count

from core.forms.unites import FormulaireUnite
from core.models import UniteTravail
from core.utils import filtre_structure
from core.views import crud


class Liste(crud.Liste):
    model = UniteTravail
    titre = "Unités de travail"
    description = "Découpez l'organisation en unités de travail homogènes (service, métier, lieu)."
    colonnes = ["ID", "Nom", "Structure", "Effectif", "Risques"]
    ordre = "1,asc"
    url_ajouter, url_modifier, url_supprimer = "unites_ajouter", "unites_modifier", "unites_supprimer"

    def get_queryset(self):
        return UniteTravail.objects.filter(filtre_structure(self.request.user)).select_related("structure").annotate(nbre_risques=Count("risques"))

    def cellules(self, o):
        return [o.pk, o.nom, o.structure or "Toutes", o.effectif, o.nbre_risques]


class Ajouter(crud.Ajouter):
    model, form_class = UniteTravail, FormulaireUnite
    titre, url_liste, url_ajouter = "Ajouter une unité de travail", "unites_liste", "unites_ajouter"
    description = "Saisissez les informations de l'unité de travail."


class Modifier(crud.Modifier):
    model, form_class = UniteTravail, FormulaireUnite
    titre, url_liste = "Modifier une unité de travail", "unites_liste"

    def get_queryset(self):
        return UniteTravail.objects.filter(filtre_structure(self.request.user))


class Supprimer(crud.Supprimer):
    model, titre, url_liste = UniteTravail, "Supprimer une unité de travail", "unites_liste"

    def get_queryset(self):
        return UniteTravail.objects.filter(filtre_structure(self.request.user))
