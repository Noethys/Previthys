#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.db.models import Count
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.text import Truncator

from core.forms.actions import FormulaireActionRisque
from core.forms.risques import FormulaireRisque
from core.models import NOTE_COTATION, ActionPrevention, PieceJointe, Risque, actions_propres
from core.utils import filtre_actions, filtre_structure
from core.utils import tableau_de_bord as tdb
from core.utils.journal import consigner
from core.views import crud

COULEURS_NIVEAU = {"faible": "success", "moyen": "warning", "critique": "danger"}


def badge_niveau(risque):
    return format_html('<span class="badge text-bg-{}">{} ({})</span>', COULEURS_NIVEAU[risque.niveau], risque.niveau.capitalize(), risque.cotation)


def badge_statut(action):
    if action.en_retard:
        return format_html('<span class="badge text-bg-danger">En retard</span>')
    couleur = {"a_faire": "secondary", "en_cours": "primary", "terminee": "success"}.get(action.statut, "secondary")
    return format_html('<span class="badge text-bg-{}">{}</span>', couleur, action.get_statut_display())


def liste_actions(risque):
    """Cellule « Actions de prévention » de la liste des risques : une ligne par action, avec son statut."""
    actions = list(risque.actions.all())
    if not actions:
        return format_html('<span class="text-body-secondary">Aucune</span>')
    return format_html('<ul class="list-unstyled mb-0 liste-actions">{}</ul>', format_html_join(
        "", '<li>{} {}{}</li>', ((badge_statut(a), Truncator(a.description).chars(60),
                                  format_html(' <small class="text-body-secondary">(commune)</small>') if a.est_commune else "") for a in actions)))


class AjoutPiecesJointes:
    """Commun à l'ajout et à la modification : enregistre les fichiers déposés dans le formulaire."""

    def form_valid(self, form):
        form.instance.date_evaluation = timezone.localdate()   # enregistrer la fiche = cotation revue (voir « risques à réévaluer »)
        reponse = super().form_valid(form)
        for fichier in form.cleaned_data.get("pieces_jointes", []):
            piece = PieceJointe.objects.create(risque=self.object, fichier=fichier, nom_original=fichier.name, taille=fichier.size, ajoute_par=self.request.user)
            consigner(self.request, "creation", piece, "Ajoutée au risque « %s »" % self.object.danger)
        return reponse


class Liste(crud.Liste):
    model = Risque
    titre = "Risques"
    description = NOTE_COTATION
    colonnes = ["ID", "Unité", "Danger", "Catégorie", "Fréquence", "Gravité", "Maîtrise", "Niveau", "Actions de prévention", "Fichiers"]
    colonnes_masquees = ["Fréquence", "Gravité", "Maîtrise"]   # la cotation reste visible dans la colonne Niveau
    ordre = "7,desc"
    url_ajouter, url_modifier, url_supprimer = "risques_ajouter", "risques_modifier", "risques_supprimer"

    def get_queryset(self):
        qs = (Risque.objects.select_related("unite", "categorie").prefetch_related("actions__risques")
              .annotate(nbre_pieces_jointes=Count("pieces_jointes")).filter(filtre_structure(self.request.user, "unite__")))
        g, f = self.request.GET.get("gravite", ""), self.request.GET.get("frequence", "")
        if g.isdigit() and f.isdigit():
            qs = qs.filter(gravite=int(g), frequence=int(f))
        filtre = self.filtre()
        if filtre == "vigilance":
            return tdb.sans_action(qs)
        if filtre == "a_reevaluer":
            return tdb.a_reevaluer(qs)
        return qs

    FILTRES = {"vigilance": "Moyens ou critiques sans action en cours", "a_reevaluer": "À réévaluer après une action terminée"}

    def filtre(self):
        return self.request.GET.get("filtre") if self.request.GET.get("filtre") in self.FILTRES else ""

    def filtres(self):
        """Filtre actif venant du tableau de bord (case de la matrice, points de vigilance, risques à réévaluer)."""
        actifs = []
        g, f = self.request.GET.get("gravite", ""), self.request.GET.get("frequence", "")
        if g.isdigit() and f.isdigit():
            actifs.append("Gravité %s × fréquence %s" % (g, f))
        if self.filtre():
            actifs.append(self.FILTRES[self.filtre()])
        if not actifs:
            return []
        n = len(self.object_list)
        return [{"titre": "Filtre", "boutons": [{"libelle": " · ".join(actifs) + "  ✕", "nombre": n, "actif": True, "url": reverse("risques_liste")}]}]

    def cellules(self, o):
        return [o.pk, o.unite.nom, o.danger, o.categorie.nom, o.frequence, o.gravite, o.maitrise, (badge_niveau(o), o.cotation), (liste_actions(o), len(o.actions.all())), o.nbre_pieces_jointes]


class Ajouter(AjoutPiecesJointes, crud.Ajouter):
    model, form_class = Risque, FormulaireRisque
    template_name = "core/risque.html"
    titre, url_liste, url_ajouter = "Ajouter un risque", "risques_liste", "risques_ajouter"
    description = "Décrivez le danger, cotez-le et listez les mesures déjà en place. Vous pouvez joindre des photos ou des documents."


class Modifier(AjoutPiecesJointes, crud.Modifier):
    model, form_class = Risque, FormulaireRisque
    template_name = "core/risque.html"
    titre, url_liste = "Modifier un risque", "risques_liste"

    def get_queryset(self):
        return Risque.objects.filter(filtre_structure(self.request.user, "unite__"))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.object.date_evaluation:
            ctx["description"] = "Dernière évaluation le %s. Enregistrer la fiche vaut réévaluation du risque." % self.object.date_evaluation.strftime("%d/%m/%Y")
        ctx["pieces_jointes"] = self.object.pieces_jointes.select_related("ajoute_par").all()
        if self.request.user.has_perm("core.view_actionprevention"):
            # Un formulaire prérempli par action (fenêtre « Modifier ») et un formulaire vierge (fenêtre « Ajouter »).
            # auto_id distinct pour chaque fenêtre : les identifiants HTML restent uniques dans la page.
            # Pour une action commune, seules les unités visibles par l'utilisateur sont nommées.
            visibles = set(Risque.objects.filter(filtre_structure(self.request.user, "unite__")).values_list("pk", flat=True))
            ctx["actions_risque"] = [
                (a, badge_statut(a), FormulaireActionRisque(instance=a, user=self.request.user, auto_id="id_action%d_%%s" % a.pk),
                 len(a.risques.all()), sorted({r.unite.nom for r in a.risques.all() if r.pk in visibles}))
                for a in self.object.actions.select_related("categorie").prefetch_related("risques__unite")]
            ctx["form_nouvelle_action"] = FormulaireActionRisque(user=self.request.user, auto_id="id_nouvelle_action_%s")
            if self.request.user.has_perm("core.change_actionprevention"):
                ctx["actions_rattachables"] = (ActionPrevention.objects.filter(filtre_actions(self.request.user)).filter(risques__isnull=False)
                                               .exclude(risques=self.object).distinct().prefetch_related("risques__unite").order_by("description"))
        return ctx


class Supprimer(crud.Supprimer):
    model, titre, url_liste = Risque, "Supprimer un risque", "risques_liste"

    def get_queryset(self):
        return Risque.objects.filter(filtre_structure(self.request.user, "unite__"))

    def dependances_supplementaires(self):
        return dependances_actions([self.object])


def dependances_actions(risques):
    """Actions supprimées avec ces risques (celles qui n'en ont pas d'autre) et actions communes qui les perdent."""
    propres = actions_propres(risques)
    communes = ActionPrevention.objects.filter(risques__in=risques).exclude(pk__in=propres).distinct().count()
    resultat, n = [], propres.count()
    if n:
        resultat.append(("action de prévention" if n == 1 else "actions de prévention", n))
    if communes:
        resultat.append(("action commune détachée (conservée pour les autres risques)" if communes == 1
                         else "actions communes détachées (conservées pour les autres risques)", communes))
    return resultat
