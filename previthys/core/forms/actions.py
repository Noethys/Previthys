#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

import datetime

from django import forms
from django.contrib.auth import get_user_model

from core.forms.base import FormulaireBase
from core.models import ActionPrevention, Risque
from core.utils import filtre_structure


class FormulaireAction(FormulaireBase):
    class Meta:
        model = ActionPrevention
        fields = ["risque", "description", "responsable", "echeance", "duree", "cout", "statut", "date_realisation"]
        labels = {"cout": "Coût (€)"}
        widgets = {
            "duree": forms.TextInput(attrs={"placeholder": "Ex. : 2 jours, 1 demi-journée, 3 heures"}),
            "cout": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "0,00"}),
            "echeance": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "date_realisation": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.user is not None and "risque" in self.fields:
            self.fields["risque"].queryset = Risque.objects.filter(filtre_structure(self.user, "unite__")).select_related("unite")
        self.fields["responsable"].queryset = get_user_model().objects.filter(is_active=True)
        self.fields["responsable"].label_from_instance = lambda u: u.get_full_name() or u.get_username()
        self.fields["date_realisation"].help_text = "Renseignée automatiquement à la date du jour quand l'action passe à « Terminée »."

    def clean(self):
        donnees = super().clean()
        if donnees.get("statut") == "terminee":
            if not donnees.get("date_realisation"):
                donnees["date_realisation"] = datetime.date.today()
        else:
            donnees["date_realisation"] = None
        return donnees


class FormulaireActionRisque(FormulaireAction):
    """Action saisie depuis la fiche d'un risque : le risque est imposé par la page, il n'est donc pas proposé."""

    class Meta(FormulaireAction.Meta):
        fields = ["description", "responsable", "echeance", "duree", "cout", "statut", "date_realisation"]
