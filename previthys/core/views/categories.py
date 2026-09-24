#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.db.models import Count

from core.forms.categories import FormulaireCategorie
from core.models import CategorieRisque
from core.views import crud


class Liste(crud.Liste):
    model = CategorieRisque
    titre = "Catégories de risques"
    description = "Paramétrez les catégories proposées lors de la saisie des risques. Une catégorie utilisée par des risques ne peut pas être supprimée."
    colonnes = ["ID", "Nom", "Description", "Ordre", "Risques"]
    ordre = "3,asc"
    vide = "Aucune catégorie. Ajoutez-en une pour pouvoir saisir des risques."
    url_ajouter, url_modifier, url_supprimer = "categories_ajouter", "categories_modifier", "categories_supprimer"

    def get_queryset(self):
        return CategorieRisque.objects.annotate(nbre_risques=Count("risques"))

    def cellules(self, o):
        return [o.pk, o.nom, o.description, o.ordre, o.nbre_risques]


class Ajouter(crud.Ajouter):
    model, form_class = CategorieRisque, FormulaireCategorie
    titre, url_liste, url_ajouter = "Ajouter une catégorie de risque", "categories_liste", "categories_ajouter"


class Modifier(crud.Modifier):
    model, form_class = CategorieRisque, FormulaireCategorie
    titre, url_liste = "Modifier une catégorie de risque", "categories_liste"


class Supprimer(crud.Supprimer):
    model, titre, url_liste = CategorieRisque, "Supprimer une catégorie de risque", "categories_liste"
