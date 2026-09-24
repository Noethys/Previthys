"""Vues génériques de liste, ajout, modification et suppression (Django + DataTables)."""
#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.contrib import messages
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import DEFAULT_DB_ALIAS
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.utils.journal import consigner, decrire_modifications


class AccesDuerp(LoginRequiredMixin, PermissionRequiredMixin):
    """Connexion obligatoire puis permission Django (view/add/change/delete) sur le modèle."""


class Lecture(LoginRequiredMixin, PermissionRequiredMixin):
    """Pages en lecture seule (tableau de bord, document, export) : droit de consulter les risques."""
    permission_required = "core.view_risque"


def _perm(vue, action):
    return vue.request.user.has_perm("core.%s_%s" % (action, vue.model._meta.model_name))


class Liste(AccesDuerp, ListView):
    """Liste DataTables : la vue décrit les colonnes et fournit les cellules de chaque ligne."""
    template_name = "core/liste.html"
    titre = ""
    description = ""
    colonnes = []          # libellés des colonnes (hors colonne Actions)
    ordre = "0,asc"        # colonne et sens du tri initial
    vide = "Aucune donnée"
    url_ajouter = url_modifier = url_supprimer = None
    libelle_ajouter = "Ajouter"

    def get_permission_required(self):
        return ["core.view_%s" % self.model._meta.model_name]

    def cellules(self, obj):
        """Retourne une liste de valeurs ou de tuples (valeur, valeur_de_tri)."""
        raise NotImplementedError

    def actions_supplementaires(self, obj):
        return []  # liste de (libellé, url)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lignes = []
        for obj in ctx["object_list"]:
            cellules = [{"html": c[0], "ordre": c[1]} if isinstance(c, tuple) else {"html": c, "ordre": None} for c in self.cellules(obj)]
            lignes.append({
                "obj": obj, "cellules": cellules,
                "modifier": reverse(self.url_modifier, args=[obj.pk]) if self.url_modifier and _perm(self, "change") else None,
                "supprimer": reverse(self.url_supprimer, args=[obj.pk]) if self.url_supprimer and _perm(self, "delete") else None,
                "supplementaires": self.actions_supplementaires(obj),
            })
        ctx.update({
            "lignes": lignes, "titre": self.titre, "description": self.description, "colonnes": self.colonnes,
            "ordre": self.ordre, "vide": self.vide, "nom_liste": self.model._meta.model_name,
            "url_ajouter": reverse(self.url_ajouter) if self.url_ajouter and _perm(self, "add") else None,
            "libelle_ajouter": self.libelle_ajouter,
            "colonne_actions": bool(self.url_modifier or self.url_supprimer),
        })
        return ctx


class Saisie:
    """Comportement commun à l'ajout et à la modification."""
    template_name = "core/form.html"
    titre = ""
    description = ""
    url_liste = None
    url_ajouter = None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"titre": self.titre, "description": self.description, "url_liste": reverse(self.url_liste), "avec_ajouter": isinstance(self, CreateView)})
        return ctx

    def get_success_url(self):
        if "enregistrer_ajouter" in self.request.POST and self.url_ajouter:
            return reverse(self.url_ajouter)
        return reverse(self.url_liste)

    def form_valid(self, form):
        modification = isinstance(self, UpdateView)
        detail = decrire_modifications(form) if modification else ""
        response = super().form_valid(form)
        if not modification or detail:   # une modification sans aucun champ changé n'est pas consignée
            consigner(self.request, "modification" if modification else "creation", self.object, detail)
        messages.success(self.request, "Modification enregistrée" if modification else "Ajout enregistré")
        return response


class Ajouter(AccesDuerp, Saisie, CreateView):
    def get_permission_required(self):
        return ["core.add_%s" % self.model._meta.model_name]


class Modifier(AccesDuerp, Saisie, UpdateView):
    def get_permission_required(self):
        return ["core.change_%s" % self.model._meta.model_name]


class Supprimer(AccesDuerp, DeleteView):
    template_name = "core/confirmer_suppression.html"
    titre = ""
    url_liste = None

    def get_permission_required(self):
        return ["core.delete_%s" % self.model._meta.model_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        collecteur = NestedObjects(using=DEFAULT_DB_ALIAS)
        collecteur.collect([self.object])
        ctx["bloquants"] = self._decrire(collecteur.protected)
        ctx["dependances"] = [(self._nom(m, len(o)), len(o)) for m, o in collecteur.model_objs.items() if m is not self.model]
        ctx.update({"titre": self.titre, "url_liste": reverse(self.url_liste)})
        return ctx

    @staticmethod
    def _nom(modele, nombre):
        return modele._meta.verbose_name if nombre == 1 else modele._meta.verbose_name_plural

    @classmethod
    def _decrire(cls, objets):
        comptes = {}
        for o in objets:
            comptes[o._meta.model] = comptes.get(o._meta.model, 0) + 1
        return ["%d %s" % (n, cls._nom(modele, n)) for modele, n in comptes.items()]

    def form_valid(self, form):
        try:
            self.object.delete()
        except ProtectedError as e:
            messages.error(self.request, "Suppression impossible : cet élément est utilisé par %s." % ", ".join(self._decrire(e.protected_objects)))
            return HttpResponseRedirect(reverse(self.url_liste))
        consigner(self.request, "suppression", self.object)
        messages.success(self.request, "Suppression effectuée")
        return HttpResponseRedirect(reverse(self.url_liste))
