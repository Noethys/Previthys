#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.db.models import Count

from core.forms.categories import FormulaireCategorieAction
from core.models import CategorieAction
from core.views import crud


class Liste(crud.Liste):
    model = CategorieAction
    titre = "Catégories d'actions"
    description = "Paramétrez les catégories des actions de prévention (formation, matériel, organisation...), pour regrouper le plan d'actions. Une catégorie utilisée par des actions ne peut pas être supprimée."
    colonnes = ["ID", "Nom", "Description", "Ordre", "Nombre d'actions"]
    ordre = "3,asc"
    vide = "Aucune catégorie d'action."
    url_ajouter, url_modifier, url_supprimer = "categories_actions_ajouter", "categories_actions_modifier", "categories_actions_supprimer"

    def get_queryset(self):
        return CategorieAction.objects.annotate(nbre_actions=Count("actions"))

    def cellules(self, o):
        return [o.pk, o.nom, o.description, o.ordre, o.nbre_actions]


class Ajouter(crud.Ajouter):
    model, form_class = CategorieAction, FormulaireCategorieAction
    titre, url_liste, url_ajouter = "Ajouter une catégorie d'action", "categories_actions_liste", "categories_actions_ajouter"


class Modifier(crud.Modifier):
    model, form_class = CategorieAction, FormulaireCategorieAction
    titre, url_liste = "Modifier une catégorie d'action", "categories_actions_liste"


class Supprimer(crud.Supprimer):
    model, titre, url_liste = CategorieAction, "Supprimer une catégorie d'action", "categories_actions_liste"
