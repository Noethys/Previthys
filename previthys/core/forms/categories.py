#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django import forms

from core.forms.base import FormulaireBase
from core.models import CategorieRisque


class FormulaireCategorie(FormulaireBase):
    class Meta:
        model = CategorieRisque
        fields = ["nom", "description", "ordre"]

    def clean_nom(self):
        """Refuse les doublons sans tenir compte de la casse (« Autre » et « autre »)."""
        nom = self.cleaned_data["nom"].strip()
        doublons = CategorieRisque.objects.filter(nom__iexact=nom).exclude(pk=self.instance.pk)
        if doublons.exists():
            raise forms.ValidationError("Cette catégorie existe déjà.")
        return nom
