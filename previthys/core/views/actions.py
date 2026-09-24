#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.contrib import messages
from django.urls import reverse
from django.utils.html import format_html

from core.forms.actions import FormulaireAction
from core.models import ActionPrevention
from core.utils import filtre_structure
from core.views import crud


class Liste(crud.Liste):
    model = ActionPrevention
    titre = "Plan d'actions"
    description = "Suivez les actions de prévention associées aux risques identifiés."
    colonnes = ["ID", "Unité", "Risque", "Action", "Responsable", "Échéance", "Statut"]
    ordre = "5,asc"
    url_ajouter, url_modifier, url_supprimer = "actions_ajouter", "actions_modifier", "actions_supprimer"

    def get_queryset(self):
        return ActionPrevention.objects.select_related("risque__unite", "responsable").filter(filtre_structure(self.request.user, "risque__unite__"))

    def cellules(self, o):
        statut = format_html('<span class="badge text-bg-danger">En retard</span>') if o.en_retard else o.get_statut_display()
        responsable = (o.responsable.get_full_name() or o.responsable.get_username()) if o.responsable else ""
        return [o.pk, o.risque.unite.nom, o.risque.danger, o.description, responsable,
                (o.echeance.strftime("%d/%m/%Y") if o.echeance else "", o.echeance.isoformat() if o.echeance else "9999-12-31"), statut]


class InviterAReevaluer:
    """Quand une action passe à « Terminée », elle devient une mesure existante : on invite à réévaluer le risque."""

    def form_valid(self, form):
        response = super().form_valid(form)
        if form.cleaned_data["statut"] == "terminee" and ("statut" in form.changed_data):
            risque = form.instance.risque
            if self.request.user.has_perm("core.change_risque"):
                messages.info(self.request, format_html(
                    "Action terminée : elle figure désormais dans les mesures existantes du risque « {} ». "
                    '<a href="{}" class="alert-link">Réévaluer le risque</a> si sa gravité ou sa fréquence ont diminué.',
                    risque.danger, reverse("risques_modifier", args=[risque.pk])))
            else:
                messages.info(self.request, "Action terminée : elle figure désormais dans les mesures existantes du risque « %s »." % risque.danger)
        return response


class Ajouter(InviterAReevaluer, crud.Ajouter):
    model, form_class = ActionPrevention, FormulaireAction
    titre, url_liste, url_ajouter = "Ajouter une action de prévention", "actions_liste", "actions_ajouter"
    description = "Renseignez l'action, son responsable et son échéance."


class Modifier(InviterAReevaluer, crud.Modifier):
    model, form_class = ActionPrevention, FormulaireAction
    titre, url_liste = "Modifier une action de prévention", "actions_liste"

    def get_queryset(self):
        return ActionPrevention.objects.filter(filtre_structure(self.request.user, "risque__unite__"))


class Supprimer(crud.Supprimer):
    model, titre, url_liste = ActionPrevention, "Supprimer une action de prévention", "actions_liste"

    def get_queryset(self):
        return ActionPrevention.objects.filter(filtre_structure(self.request.user, "risque__unite__"))
