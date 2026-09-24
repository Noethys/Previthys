"""Champs de formulaire réutilisables."""
#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django import forms

from core.utils.fichiers import ACCEPT_INPUT, NOMBRE_MAX_FICHIERS, valider_fichier


class WidgetFichierMultiple(forms.ClearableFileInput):
    """Active la sélection de plusieurs fichiers (voir la documentation Django sur les téléversements multiples)."""
    allow_multiple_selected = True


class ChampFichierMultiple(forms.FileField):
    """Un ou plusieurs fichiers dans un seul champ, chacun validé individuellement (type, taille, contenu)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", WidgetFichierMultiple(attrs={"multiple": True, "accept": ACCEPT_INPUT}))
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        fichiers = data if isinstance(data, (list, tuple)) else ([data] if data else [])
        if len(fichiers) > NOMBRE_MAX_FICHIERS:
            raise forms.ValidationError("Vous ne pouvez pas ajouter plus de %d fichiers à la fois." % NOMBRE_MAX_FICHIERS)
        resultat = []
        for fichier in fichiers:
            fichier = super().clean(fichier, initial)
            valider_fichier(fichier)
            resultat.append(fichier)
        return resultat

    def has_changed(self, initial, data):
        """Aucun fichier sélectionné (liste vide) ne doit pas compter comme une modification du formulaire."""
        return bool(data)
