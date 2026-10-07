#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.db.models import Count, F
from django.urls import reverse
from django.utils.http import urlencode
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from core.forms.actions import FormulaireActionRisque
from core.forms.risques import FormulaireRisque
from core.models import NOTE_COTATION, SEUIL_CRITIQUE, SEUIL_MOYEN, ActionPrevention, CategorieRisque, PieceJointe, Risque, UniteTravail, actions_propres
from core.utils import filtre_actions, filtre_structure
from core.utils.donnees import ORDRE_MACARONS, mesures_en_liste
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


def code_macaron(action):
    """Statut affiché d'une action, avec les mêmes codes que le document unique (pour le tri)."""
    if action.statut == "terminee":
        return "terminee"
    return "retard" if action.en_retard else action.statut


def liste_mesures_actions(risque):
    """Cellule « Mesures et actions de prévention » de la liste des risques, comme dans le document unique :
    les mesures existantes (macaron « Existante »), puis les actions classées par statut (terminées, en cours,
    en retard, à faire). Retourne (html, nombre de lignes) ; le nombre sert au tri de la colonne.
    Le texte est envoyé en entier : la coupure à deux lignes est faite à l'affichage (CSS), selon la largeur
    réelle de la colonne, et le texte complet apparaît au survol quand il est coupé (voir core/listes.js)."""
    mesures = mesures_en_liste(risque.mesures_existantes)
    actions = sorted(risque.actions.all(), key=lambda a: ORDRE_MACARONS.index(code_macaron(a)))
    if not mesures and not actions:
        return format_html('<span class="text-body-secondary">Aucune</span>'), 0
    lignes = [format_html('<li class="ligne-action" data-infobulle="{}"><span class="badge text-bg-info">Existante</span> '
                          '<span class="texte-action">{}</span></li>', m, m) for m in mesures]
    lignes += [format_html('<li class="ligne-action" data-infobulle="{}">{} <span class="texte-action">{}</span>{}</li>',
                           a.description, badge_statut(a), a.description,
                           format_html(' <small class="text-body-secondary">(commune)</small>') if a.est_commune else "")
               for a in actions]
    return format_html('<ul class="list-unstyled mb-0 liste-actions">{}</ul>', format_html_join("", "{}", ((l,) for l in lignes))), len(lignes)


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
    colonnes = ["ID", "Unité", "Danger", "Catégorie", "Fréquence", "Gravité", "Maîtrise", "Niveau", "Mesures et actions de prévention", "Fichiers"]
    colonnes_masquees = ["Fréquence", "Gravité", "Maîtrise"]   # la cotation reste visible dans la colonne Niveau
    largeurs_colonnes = {"Danger": "16%", "Mesures et actions de prévention": "34%"}   # plus de place pour les mesures et actions
    ordre = "7,desc"
    memoriser_filtres = True
    url_ajouter, url_modifier, url_supprimer = "risques_ajouter", "risques_modifier", "risques_supprimer"

    def base(self):
        return (Risque.objects.select_related("unite", "categorie").prefetch_related("actions__risques")
                .annotate(nbre_pieces_jointes=Count("pieces_jointes")).filter(filtre_structure(self.request.user, "unite__")))

    def unite(self):
        valeur = self.request.GET.get("unite", "")
        return valeur if valeur.isdigit() else ""

    def categorie(self):
        valeur = self.request.GET.get("categorie", "")
        return valeur if valeur.isdigit() else ""

    NIVEAUX = [("critique", "Critique"), ("moyen", "Moyen"), ("faible", "Faible")]

    def niveau(self):
        valeur = self.request.GET.get("niveau", "")
        return valeur if valeur in dict(self.NIVEAUX) else ""

    @staticmethod
    def filtrer(qs, unite="", categorie="", niveau=""):
        """Applique les listes déroulantes (unité, catégorie, niveau) ; une valeur vide ne filtre pas."""
        if unite:
            qs = qs.filter(unite_id=int(unite))
        if categorie:
            qs = qs.filter(categorie_id=int(categorie))
        if niveau:
            qs = qs.annotate(cotation_calculee=F("frequence") * F("gravite") * F("maitrise"))
            qs = {"faible": qs.filter(cotation_calculee__lt=SEUIL_MOYEN),
                  "moyen": qs.filter(cotation_calculee__gte=SEUIL_MOYEN, cotation_calculee__lt=SEUIL_CRITIQUE),
                  "critique": qs.filter(cotation_calculee__gte=SEUIL_CRITIQUE)}[niveau]
        return qs

    def filtrer_tableau_de_bord(self, qs):
        """Filtres posés par un lien du tableau de bord (case de la matrice, points de vigilance, à réévaluer)."""
        g, f = self.request.GET.get("gravite", ""), self.request.GET.get("frequence", "")
        if g.isdigit() and f.isdigit():
            qs = qs.filter(gravite=int(g), frequence=int(f))
        filtre = self.filtre()
        if filtre == "vigilance":
            return tdb.sans_action(qs)
        if filtre == "a_reevaluer":
            return tdb.a_reevaluer(qs)
        return qs

    def compter(self, cle, **filtres):
        """Nombre de risques par valeur de `cle` (fonction appliquée à chaque risque), les autres filtres étant appliqués."""
        comptes = {}
        for r in self.filtrer_tableau_de_bord(self.filtrer(self.base(), **filtres)):
            comptes[cle(r)] = comptes.get(cle(r), 0) + 1
        return comptes

    def listes_filtres(self):
        """Filtres « Unité », « Catégorie » et « Niveau » sur une ligne. Chacun compte les risques en tenant compte
        des deux autres (et des filtres du tableau de bord)."""
        if hasattr(self, "_listes_filtres"):
            return self._listes_filtres
        unite, categorie, niveau = self.unite(), self.categorie(), self.niveau()

        comptes = self.compter(lambda r: r.unite_id, categorie=categorie, niveau=niveau)
        unites = UniteTravail.objects.filter(filtre_structure(self.request.user)).order_by("nom")
        options_unites = [("", "Toutes les unités (%d)" % sum(comptes.values()))]
        options_unites += [(str(u.pk), "%s (%d)" % (u.nom, comptes.get(u.pk, 0))) for u in unites]

        comptes = self.compter(lambda r: r.categorie_id, unite=unite, niveau=niveau)
        options_categories = [("", "Toutes les catégories (%d)" % sum(comptes.values()))]
        options_categories += [(str(c.pk), "%s (%d)" % (c.nom, comptes.get(c.pk, 0))) for c in CategorieRisque.objects.all()]

        comptes = self.compter(lambda r: r.niveau, unite=unite, categorie=categorie)
        options_niveaux = [("", "Tous les niveaux (%d)" % sum(comptes.values()))]
        options_niveaux += [(cle, "%s (%d)" % (libelle, comptes.get(cle, 0))) for cle, libelle in self.NIVEAUX]

        self._listes_filtres = [
            {"nom": "unite", "libelle": "Unité", "valeur": unite, "options": options_unites},
            {"nom": "categorie", "libelle": "Catégorie", "valeur": categorie, "options": options_categories},
            {"nom": "niveau", "libelle": "Niveau", "valeur": niveau, "options": options_niveaux},
        ]
        return self._listes_filtres

    def get_queryset(self):
        return self.filtrer_tableau_de_bord(self.filtrer(self.base(), self.unite(), self.categorie(), self.niveau()))

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
        conserves = [(k, v) for k, v in (("unite", self.unite()), ("categorie", self.categorie()), ("niveau", self.niveau())) if v]
        # sans filtre restant, ?raz=1 efface aussi les filtres mémorisés (sinon ils seraient restaurés)
        url = reverse("risques_liste") + ("?" + urlencode(conserves) if conserves else "?raz=1")
        return [{"titre": "Filtre", "boutons": [{"libelle": " · ".join(actifs) + "  ✕", "nombre": n, "actif": True, "url": url}]}]

    def cellules(self, o):
        return [o.pk, o.unite.nom, o.danger, o.categorie.nom, o.frequence, o.gravite, o.maitrise, (badge_niveau(o), o.cotation), liste_mesures_actions(o), o.nbre_pieces_jointes]


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
