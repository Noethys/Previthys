#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.db.models import Count
from django.utils.html import format_html

from core.forms.risques import FormulaireRisque
from core.models import PieceJointe, Risque
from core.utils import filtre_structure
from core.utils.journal import consigner
from core.views import crud

COULEURS_NIVEAU = {"faible": "success", "moyen": "warning", "critique": "danger"}


def badge_niveau(risque):
    return format_html('<span class="badge text-bg-{}">{} ({})</span>', COULEURS_NIVEAU[risque.niveau], risque.niveau.capitalize(), risque.cotation)


class AjoutPiecesJointes:
    """Commun à l'ajout et à la modification : enregistre les fichiers déposés dans le formulaire."""

    def form_valid(self, form):
        reponse = super().form_valid(form)
        for fichier in form.cleaned_data.get("pieces_jointes", []):
            piece = PieceJointe.objects.create(risque=self.object, fichier=fichier, nom_original=fichier.name, taille=fichier.size, ajoute_par=self.request.user)
            consigner(self.request, "creation", piece, "Ajoutée au risque « %s »" % self.object.danger)
        return reponse


class Liste(crud.Liste):
    model = Risque
    titre = "Risques"
    description = "Cotation = gravité × fréquence : faible (1-3), moyen (4-8), critique (9-16)."
    colonnes = ["ID", "Unité", "Catégorie", "Danger", "Fréquence", "Gravité", "Maîtrise", "Niveau", "Fichiers"]
    ordre = "7,desc"
    url_ajouter, url_modifier, url_supprimer = "risques_ajouter", "risques_modifier", "risques_supprimer"

    def get_queryset(self):
        return Risque.objects.select_related("unite", "categorie").annotate(nbre_pieces_jointes=Count("pieces_jointes")).filter(filtre_structure(self.request.user, "unite__"))

    def cellules(self, o):
        return [o.pk, o.unite.nom, o.categorie.nom, o.danger, o.frequence, o.gravite, o.maitrise, (badge_niveau(o), o.cotation), o.nbre_pieces_jointes]


class Ajouter(AjoutPiecesJointes, crud.Ajouter):
    model, form_class = Risque, FormulaireRisque
    titre, url_liste, url_ajouter = "Ajouter un risque", "risques_liste", "risques_ajouter"
    description = "Décrivez le danger, cotez-le et listez les mesures déjà en place. Vous pouvez joindre des photos ou des documents."


class Modifier(AjoutPiecesJointes, crud.Modifier):
    model, form_class = Risque, FormulaireRisque
    titre, url_liste = "Modifier un risque", "risques_liste"

    def get_queryset(self):
        return Risque.objects.filter(filtre_structure(self.request.user, "unite__"))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["pieces_jointes"] = self.object.pieces_jointes.select_related("ajoute_par").all()
        return ctx


class Supprimer(crud.Supprimer):
    model, titre, url_liste = Risque, "Supprimer un risque", "risques_liste"

    def get_queryset(self):
        return Risque.objects.filter(filtre_structure(self.request.user, "unite__"))
