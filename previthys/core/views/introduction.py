#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

"""Page « Introduction du document » : texte de présentation et logo du document unique, par structure."""

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import FormView

from core.models import Introduction, Structure
from core.utils.introduction import AIDE_SYNTAXE, logo_en_data_uri, methode, mise_en_forme
from core.utils.journal import consigner


class FormulaireIntroduction(forms.Form):
    texte = forms.CharField(label="Texte de présentation", required=False, help_text=AIDE_SYNTAXE,
                            widget=forms.Textarea(attrs={"rows": 20, "class": "form-control font-monospace small"}))
    logo = forms.FileField(label="Logo (page de garde)", required=False, help_text="Image PNG ou JPEG, 500 Ko maximum.",
                           widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".png,.jpg,.jpeg"}))
    supprimer_logo = forms.BooleanField(label="Retirer le logo actuel", required=False,
                                        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}))

    def clean_logo(self):
        fichier = self.cleaned_data.get("logo")
        if fichier:
            try:
                return logo_en_data_uri(fichier)
            except ValueError as e:
                raise forms.ValidationError(str(e))
        return None


class Modifier(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    template_name = "core/introduction.html"
    form_class = FormulaireIntroduction
    permission_required = "core.change_introduction"

    def structures_modifiables(self):
        """Superutilisateur : introduction par défaut et toutes les structures. Autres : leurs structures, ou
        l'introduction par défaut s'ils n'en ont aucune."""
        user = self.request.user
        if user.is_superuser:
            return [None] + list(Structure.objects.all())
        siennes = list(user.structures.all())
        return siennes or [None]

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        choix = self.structures_modifiables()
        pk = request.GET.get("structure", "")
        self.structure = next((s for s in choix if s is not None and str(s.pk) == pk), None) if pk else choix[0]
        if pk and self.structure is None:
            raise Http404("Structure introuvable")
        self.introduction = Introduction.objects.filter(structure=self.structure).first() if self.structure else \
            Introduction.objects.filter(structure__isnull=True).first()
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {"texte": self.introduction.texte if self.introduction else ""}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"titre": "Introduction du document unique", "structure": self.structure, "introduction": self.introduction,
                    "onglets": [(s, s == self.structure) for s in self.structures_modifiables()] if len(self.structures_modifiables()) > 1 else [],
                    "apercu": mise_en_forme(self.introduction.texte) if self.introduction else "", "methode": methode()})
        return ctx

    def form_valid(self, form):
        intro = self.introduction or Introduction(structure=self.structure)
        creation = intro.pk is None
        details = []
        if intro.texte != form.cleaned_data["texte"]:
            intro.texte = form.cleaned_data["texte"]
            details.append("Texte de présentation modifié")
        if form.cleaned_data["logo"]:
            intro.logo = form.cleaned_data["logo"]
            details.append("Logo remplacé")
        elif form.cleaned_data["supprimer_logo"] and intro.logo:
            intro.logo = ""
            details.append("Logo retiré")
        if details or creation:
            intro.save()
            consigner(self.request, "creation" if creation else "modification", intro, "\n".join(details))
        messages.success(self.request, "Introduction enregistrée")
        url = reverse("introduction")
        return HttpResponseRedirect(url + ("?structure=%d" % self.structure.pk if self.structure else ""))
