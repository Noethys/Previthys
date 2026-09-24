#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django import forms

from core.models import Structure


class FormulaireBase(forms.ModelForm):
    """Ajoute les classes Bootstrap et reçoit l'utilisateur pour limiter les listes déroulantes."""

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        for champ in self.fields.values():
            w = champ.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs["class"] = "form-check-input"
            elif isinstance(w, forms.Select):
                w.attrs["class"] = "form-select"
            else:
                w.attrs["class"] = "form-control"
            if isinstance(w, forms.Textarea):
                w.attrs["rows"] = 3

    def limiter_structures(self, champ="structure"):
        if champ in self.fields and self.user is not None:
            qs = Structure.objects.all() if self.user.is_superuser else self.user.structures.all()
            self.fields[champ].queryset = qs
            self.fields[champ].empty_label = "Toutes les structures"
