#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.urls import path

from core.views import accessibilite, actions, aide, auth, categories, categories_actions, introduction, dashboard, document, export, journal, mentions_legales, mise_a_jour, pieces_jointes, risques, unites, versions

urlpatterns = [
    path("connexion/", auth.Connexion.as_view(), name="login"),
    path("deconnexion/", auth.Deconnexion.as_view(), name="logout"),

    path("", dashboard.Dashboard.as_view(), name="dashboard"),
    path("document/", document.Document.as_view(), name="document"),
    path("document/introduction/", introduction.Modifier.as_view(), name="introduction"),
    path("export/xlsx/", export.ExportXlsx.as_view(), name="export_xlsx"),
    path("mise-a-jour/", mise_a_jour.MiseAJour.as_view(), name="mise_a_jour"),
    path("journal/", journal.Liste.as_view(), name="journal_liste"),
    path("aide/", aide.Aide.as_view(), name="aide"),
    path("accessibilite/", accessibilite.Accessibilite.as_view(), name="accessibilite"),
    path("mentions-legales/", mentions_legales.MentionsLegales.as_view(), name="mentions_legales"),

    path("unites/", unites.Liste.as_view(), name="unites_liste"),
    path("unites/ajouter/", unites.Ajouter.as_view(), name="unites_ajouter"),
    path("unites/<int:pk>/modifier/", unites.Modifier.as_view(), name="unites_modifier"),
    path("unites/<int:pk>/supprimer/", unites.Supprimer.as_view(), name="unites_supprimer"),

    path("categories/", categories.Liste.as_view(), name="categories_liste"),
    path("categories/ajouter/", categories.Ajouter.as_view(), name="categories_ajouter"),
    path("categories/<int:pk>/modifier/", categories.Modifier.as_view(), name="categories_modifier"),
    path("categories/<int:pk>/supprimer/", categories.Supprimer.as_view(), name="categories_supprimer"),

    path("risques/", risques.Liste.as_view(), name="risques_liste"),
    path("risques/ajouter/", risques.Ajouter.as_view(), name="risques_ajouter"),
    path("risques/<int:pk>/modifier/", risques.Modifier.as_view(), name="risques_modifier"),
    path("risques/<int:pk>/supprimer/", risques.Supprimer.as_view(), name="risques_supprimer"),
    path("risques/<int:risque>/actions/ajouter/", actions.RisqueAjouter.as_view(), name="risques_actions_ajouter"),
    path("risques/<int:risque>/actions/<int:pk>/modifier/", actions.RisqueModifier.as_view(), name="risques_actions_modifier"),
    path("risques/<int:risque>/actions/<int:pk>/supprimer/", actions.RisqueRetirer.as_view(), name="risques_actions_supprimer"),
    path("risques/<int:risque>/actions/rattacher/", actions.RisqueRattacher.as_view(), name="risques_actions_rattacher"),
    path("risques/pieces-jointes/<int:pk>/telecharger/", pieces_jointes.Telecharger.as_view(), name="pieces_jointes_telecharger"),
    path("risques/pieces-jointes/<int:pk>/supprimer/", pieces_jointes.Supprimer.as_view(), name="pieces_jointes_supprimer"),

    path("actions/", actions.Liste.as_view(), name="actions_liste"),
    path("actions/ajouter/", actions.Ajouter.as_view(), name="actions_ajouter"),
    path("actions/<int:pk>/modifier/", actions.Modifier.as_view(), name="actions_modifier"),
    path("actions/<int:pk>/supprimer/", actions.Supprimer.as_view(), name="actions_supprimer"),

    path("categories-actions/", categories_actions.Liste.as_view(), name="categories_actions_liste"),
    path("categories-actions/ajouter/", categories_actions.Ajouter.as_view(), name="categories_actions_ajouter"),
    path("categories-actions/<int:pk>/modifier/", categories_actions.Modifier.as_view(), name="categories_actions_modifier"),
    path("categories-actions/<int:pk>/supprimer/", categories_actions.Supprimer.as_view(), name="categories_actions_supprimer"),

    path("versions/", versions.Liste.as_view(), name="versions_liste"),
    path("versions/ajouter/", versions.Ajouter.as_view(), name="versions_ajouter"),
    path("versions/<int:pk>/supprimer/", versions.Supprimer.as_view(), name="versions_supprimer"),
    path("versions/<int:pk>/document/", document.Document.as_view(), name="versions_document"),
    path("versions/<int:pk>/export/", export.ExportXlsx.as_view(), name="versions_export"),
]
