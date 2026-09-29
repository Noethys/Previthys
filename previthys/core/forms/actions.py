#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

import datetime

from django import forms
from django.contrib.auth import get_user_model

from core.forms.base import FormulaireBase
from core.models import ActionPrevention, Risque, Structure
from core.utils import filtre_actions, filtre_structure


class FormulaireAction(FormulaireBase):
    """Action du plan d'actions : générale (aucun risque) ou liée à un ou plusieurs risques, cochés par unité."""
    PORTEES = [("risques", "Liée à un ou plusieurs risques"), ("generale", "Action générale")]

    portee = forms.ChoiceField(label="Portée", choices=PORTEES, initial="risques", widget=forms.RadioSelect)
    risques = forms.ModelMultipleChoiceField(label="Risques concernés", queryset=Risque.objects.none(), required=False,
                                             widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = ActionPrevention
        fields = ["description", "categorie", "structure", "responsable", "echeance", "duree", "cout", "statut", "date_realisation"]
        labels = {"cout": "Coût (€)"}
        widgets = {
            "duree": forms.TextInput(attrs={"placeholder": "Ex. : 2 jours, 1 demi-journée, 3 heures"}),
            "cout": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "0,00"}),
            "echeance": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "date_realisation": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categorie"].empty_label = "(non classée)"
        # Texte libre, avec des suggestions (voir suggestions_responsables) : <datalist id="responsables-connus">
        self.fields["responsable"].widget.attrs.update({"list": "responsables-connus", "autocomplete": "off",
                                                        "placeholder": "Ex. : F. Dupont, responsable des services techniques"})
        self.fields["date_realisation"].help_text = "Renseignée automatiquement à la date du jour quand l'action passe à « Terminée »."
        self.risques_caches = []
        if "portee" in self.fields:
            self.fields["portee"].widget.attrs["class"] = "form-check-input"
        if "risques" not in self.fields:
            return
        visibles = Risque.objects.select_related("unite", "categorie").order_by("unite__nom", "danger")
        if self.user is not None:
            visibles = visibles.filter(filtre_structure(self.user, "unite__"))
        self.fields["risques"].queryset = visibles
        if self.instance.pk:
            actuels = list(self.instance.risques.all())
            ids_visibles = set(visibles.values_list("pk", flat=True))
            # Risques d'autres structures, invisibles pour cet utilisateur : conservés tels quels à l'enregistrement
            self.risques_caches = [r for r in actuels if r.pk not in ids_visibles]
            self.initial.setdefault("risques", [r.pk for r in actuels if r.pk in ids_visibles])
            self.initial.setdefault("portee", "risques" if actuels else "generale")
        # Structure : utile pour une action générale seulement, et seulement si des structures existent
        if "structure" not in self.fields:
            pass
        elif Structure.objects.exists():
            self.limiter_structures("structure")
            self.fields["structure"].help_text = "Pour une action générale : structure concernée."
        else:
            del self.fields["structure"]

    def suggestions_responsables(self):
        """Responsables déjà saisis sur les actions visibles par l'utilisateur et noms des utilisateurs actifs."""
        actions = ActionPrevention.objects.exclude(responsable="")
        if self.user is not None:
            actions = actions.filter(filtre_actions(self.user))
        noms = set(actions.values_list("responsable", flat=True))
        for u in get_user_model().objects.filter(is_active=True):
            noms.add(u.get_full_name() or u.get_username())
        return sorted(noms, key=str.lower)

    def groupes_risques(self):
        """Risques proposés, regroupés par unité, avec leur état coché : [(unité, [(risque, coché), ...]), ...]."""
        if self.is_bound:
            coches = set(self.data.getlist(self.add_prefix("risques")) if hasattr(self.data, "getlist") else [])
        else:
            coches = {str(pk) for pk in self.initial.get("risques", [])}
        groupes = {}
        for r in self.fields["risques"].queryset:
            groupes.setdefault(r.unite, []).append((r, str(r.pk) in coches))
        return list(groupes.items())

    def categories_proposees(self):
        return sorted({r.categorie.nom for r in self.fields["risques"].queryset})

    def clean(self):
        donnees = super().clean()
        if donnees.get("statut") == "terminee":
            if not donnees.get("date_realisation"):
                donnees["date_realisation"] = datetime.date.today()
        else:
            donnees["date_realisation"] = None
        if "portee" in self.fields:
            if donnees.get("portee") == "generale":
                if self.risques_caches:
                    self.add_error("portee", "Cette action est aussi liée à des risques d'autres structures : elle ne peut pas devenir une action générale.")
                donnees["risques"] = []
            else:
                if not donnees.get("risques") and not self.risques_caches:
                    self.add_error("risques", "Cochez au moins un risque, ou choisissez « Action générale ».")
                donnees["structure"] = None
            # Pour le journal : changement des risques concernés (voir decrire_modifications)
            avant = set(self.initial.get("risques", []))
            apres = {r.pk for r in donnees.get("risques") or []}
            if self.instance.pk and avant != apres:
                self.detail_supplementaire = "Risques concernés : %d → %d" % (len(avant) + len(self.risques_caches), len(apres) + len(self.risques_caches))
        return donnees

    def save(self, commit=True):
        action = super().save(commit)
        if commit and "risques" in self.fields:
            action.risques.set(list(self.cleaned_data.get("risques") or []) + self.risques_caches)
            action.maj_structure()
        return action


class FormulaireActionRisque(FormulaireAction):
    """Action saisie depuis la fiche d'un risque : le risque est donné par la page (la vue l'ajoute)."""

    class Meta(FormulaireAction.Meta):
        fields = ["description", "categorie", "responsable", "echeance", "duree", "cout", "statut", "date_realisation"]

    def __init__(self, *args, risque_impose=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.risque_impose = risque_impose
        for nom in ("portee", "risques", "structure"):
            self.fields.pop(nom, None)

    def save(self, commit=True):
        action = super().save(commit)
        if commit and self.risque_impose is not None:
            action.risques.add(self.risque_impose)
            action.maj_structure()
        return action
