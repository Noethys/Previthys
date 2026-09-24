#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.urls import reverse
from django.utils import timezone

from core.forms.versions import FormulaireVersion
from core.models import VersionDuerp
from core.utils import construire_donnees, filtre_structure
from core.views import crud


class Liste(crud.Liste):
    model = VersionDuerp
    titre = "Versions du DUERP"
    description = "Chaque mise à jour du DUERP est archivée (conservation obligatoire pendant 40 ans)."
    colonnes = ["Version", "Date", "Structure", "Auteur", "Motif"]
    ordre = "0,desc"
    vide = "Aucune version archivée. Archivez le DUERP actuel pour en garder une copie figée."
    url_ajouter, url_supprimer = "versions_ajouter", "versions_supprimer"
    libelle_ajouter = "Archiver une version"

    def get_queryset(self):
        return VersionDuerp.objects.select_related("structure", "auteur").filter(filtre_structure(self.request.user))

    def cellules(self, o):
        auteur = (o.auteur.get_full_name() or o.auteur.get_username()) if o.auteur else ""
        return [o.numero, (timezone.localtime(o.date).strftime("%d/%m/%Y %H:%M"), o.date.isoformat()), o.structure or "Toutes", auteur, o.commentaire]

    def actions_supplementaires(self, o):
        return [("Consulter", reverse("versions_document", args=[o.pk])), ("Excel", reverse("versions_export", args=[o.pk]))]


class Ajouter(crud.Ajouter):
    model, form_class = VersionDuerp, FormulaireVersion
    titre, url_liste = "Archiver une version", "versions_liste"
    description = "Une copie figée du DUERP actuel sera archivée avec le motif saisi."

    def form_valid(self, form):
        derniere = VersionDuerp.objects.order_by("-numero").first()
        form.instance.auteur = self.request.user
        form.instance.numero = (derniere.numero if derniere else 0) + 1
        form.instance.donnees = construire_donnees(self.request.user, form.cleaned_data.get("structure"))
        return super().form_valid(form)


class Supprimer(crud.Supprimer):
    model, titre, url_liste = VersionDuerp, "Supprimer une version archivée", "versions_liste"

    def get_queryset(self):
        return VersionDuerp.objects.filter(filtre_structure(self.request.user))
