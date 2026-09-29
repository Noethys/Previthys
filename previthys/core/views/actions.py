#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.functional import cached_property
from django.template.defaultfilters import linebreaksbr
from django.utils.html import format_html, format_html_join
from django.views.generic import View

from core.forms.actions import FormulaireAction, FormulaireActionRisque
from core.models import ActionPrevention, CategorieAction, Risque, UniteTravail
from core.utils import filtre_actions, filtre_structure
from core.utils.journal import consigner
from core.views import crud

BADGE_GENERALE = '<span class="badge portee-generale">Action générale</span>'
BADGE_COMMUNE = '<span class="badge portee-commune">Commune à {} unités</span>'


def actions_visibles(user):
    return ActionPrevention.objects.filter(filtre_actions(user))


def badge_statut(action):
    if action.en_retard:
        return format_html('<span class="badge text-bg-danger">En retard</span>')
    couleur = {"a_faire": "secondary", "en_cours": "primary", "terminee": "success"}.get(action.statut, "secondary")
    return format_html('<span class="badge text-bg-{}">{}</span>', couleur, action.get_statut_display())


class Liste(crud.Liste):
    model = ActionPrevention
    titre = "Plan d'actions"
    description = "Suivez les actions de prévention : générales (toute la structure), communes à plusieurs unités ou propres à un risque."
    colonnes = ["ID", "Unité(s)", "Danger", "Action", "Catégorie", "Responsable", "Échéance", "Durée", "Coût", "Statut"]
    ordre = "6,asc"
    url_ajouter, url_modifier, url_supprimer = "actions_ajouter", "actions_modifier", "actions_supprimer"
    PORTEES = [("", "Toutes"), ("generales", "Générales"), ("communes", "Communes"), ("unite", "Propres à une unité")]

    def base(self):
        return (actions_visibles(self.request.user).annotate(nb_unites=Count("risques__unite", distinct=True))
                .select_related("structure", "categorie").prefetch_related("risques__unite", "risques__categorie"))

    # Deux filtres combinables, dans l'adresse : ?portee=...&categorie=<id>|aucune
    def portee(self):
        return self.request.GET.get("portee", "") if self.request.GET.get("portee") in dict(self.PORTEES) else ""

    def categorie(self):
        valeur = self.request.GET.get("categorie", "")
        return valeur if valeur == "aucune" or valeur.isdigit() else ""

    @staticmethod
    def filtrer_portee(qs, portee):
        return {"generales": qs.filter(nb_unites=0), "communes": qs.filter(nb_unites__gt=1), "unite": qs.filter(nb_unites=1)}.get(portee, qs)

    @staticmethod
    def filtrer_categorie(qs, categorie):
        if categorie == "aucune":
            return qs.filter(categorie__isnull=True)
        return qs.filter(categorie_id=int(categorie)) if categorie else qs

    MANQUES = {"echeance": ("sans échéance", {"echeance__isnull": True}), "responsable": ("sans responsable", {"responsable": ""}),
               "categorie": ("sans catégorie", {"categorie__isnull": True}), "cout": ("sans coût estimé", {"cout__isnull": True})}

    def manque(self):
        return self.request.GET.get("manque") if self.request.GET.get("manque") in self.MANQUES else ""

    # Filtre « Unité » (liste déroulante) : actions liées à un risque de l'unité, et actions générales qui la concernent
    @cached_property
    def unite_choisie(self):
        valeur = self.request.GET.get("unite", "")
        if not valeur.isdigit():
            return None
        return UniteTravail.objects.filter(filtre_structure(self.request.user)).filter(pk=int(valeur)).first()

    @staticmethod
    def filtrer_unite(qs, unite):
        if unite is None:
            return qs
        liees = ActionPrevention.objects.filter(risques__unite=unite).values("pk")
        generales = ActionPrevention.objects.filter(risques__isnull=True).filter(Q(structure__isnull=True) | Q(structure=unite.structure_id)).values("pk")
        return qs.filter(Q(pk__in=liees) | Q(pk__in=generales))

    def filtrer_manque(self, qs):
        if self.manque():   # lien « Actions à compléter » du tableau de bord : actions en cours à qui il manque une information
            qs = qs.exclude(statut="terminee").filter(**self.MANQUES[self.manque()][1])
        return qs

    def get_queryset(self):
        qs = self.filtrer_categorie(self.filtrer_portee(self.base(), self.portee()), self.categorie())
        return self.filtrer_unite(self.filtrer_manque(qs), self.unite_choisie)

    def listes_filtres(self):
        """Trois listes déroulantes sur une ligne : unité, portée, catégorie. Chacune compte les actions
        en tenant compte des autres filtres (et du filtre « à compléter » du tableau de bord)."""
        if hasattr(self, "_listes_filtres"):
            return self._listes_filtres
        unite, portee, categorie = self.unite_choisie, self.portee(), self.categorie()
        base = self.filtrer_manque(self.base())

        # Unités
        autres = list(self.filtrer_categorie(self.filtrer_portee(base, portee), categorie))
        unites = list(UniteTravail.objects.filter(filtre_structure(self.request.user)).order_by("nom"))
        comptes = {u.pk: 0 for u in unites}
        for a in autres:
            liees = {r.unite_id for r in a.risques.all()}
            for u in unites:
                if u.pk in liees or (not liees and (a.structure_id is None or a.structure_id == u.structure_id)):
                    comptes[u.pk] += 1
        options_unites = [("", "Toutes les unités (%d)" % len(autres))] + [(str(u.pk), "%s (%d)" % (u.nom, comptes[u.pk])) for u in unites]

        # Portées
        par_portee = {"": 0, "generales": 0, "communes": 0, "unite": 0}
        for n in self.filtrer_categorie(self.filtrer_unite(base, unite), categorie).values_list("nb_unites", flat=True):
            par_portee[""] += 1
            par_portee["generales" if n == 0 else "communes" if n > 1 else "unite"] += 1
        options_portees = [(cle, "%s (%d)" % ("Toutes les portées" if not cle else lib, par_portee[cle])) for cle, lib in self.PORTEES]

        # Catégories
        par_categorie = {}
        for c in self.filtrer_portee(self.filtrer_unite(base, unite), portee).values_list("categorie", flat=True):
            par_categorie[c] = par_categorie.get(c, 0) + 1
        options_categories = [("", "Toutes les catégories (%d)" % sum(par_categorie.values()))]
        options_categories += [(str(c.pk), "%s (%d)" % (c.nom, par_categorie.get(c.pk, 0))) for c in CategorieAction.objects.all()]
        if par_categorie.get(None) or categorie == "aucune":
            options_categories.append(("aucune", "Non classées (%d)" % par_categorie.get(None, 0)))

        self._listes_filtres = [
            {"nom": "unite", "libelle": "Unité", "valeur": str(unite.pk) if unite else "", "options": options_unites},
            {"nom": "portee", "libelle": "Portée", "valeur": portee, "options": options_portees},
            {"nom": "categorie", "libelle": "Catégorie", "valeur": categorie, "options": options_categories},
        ]
        return self._listes_filtres

    def filtres(self):
        """Seul filtre restant sous forme de pastille : « à compléter », posé par un lien du tableau de bord."""
        if not self.manque():
            return []
        unite = self.unite_choisie.pk if self.unite_choisie else ""
        parametres = urlencode([(k, v) for k, v in (("unite", unite), ("portee", self.portee()), ("categorie", self.categorie())) if v])
        return [{"titre": "À compléter", "boutons": [{"libelle": "Actions en cours %s  ✕" % self.MANQUES[self.manque()][0],
                                                      "nombre": len(self.object_list), "actif": True,
                                                      "url": reverse("actions_liste") + ("?" + parametres if parametres else "")}]}]

    @cached_property
    def risques_visibles(self):
        return set(Risque.objects.filter(filtre_structure(self.request.user, "unite__")).values_list("pk", flat=True))

    @cached_property
    def nbre_unites_visibles(self):
        return UniteTravail.objects.filter(filtre_structure(self.request.user)).count()

    def cellules(self, o):
        risques = [r for r in o.risques.all() if r.pk in self.risques_visibles]   # jamais d'unité d'une autre structure
        if o.nb_unites == 0:
            portee = format_html(BADGE_GENERALE + "{}", format_html('<br><small class="text-body-secondary">{}</small>', o.structure) if o.structure else "")
            danger = format_html('<span class="text-body-secondary">Tous les risques</span>')
            tri_portee = "0"
        else:
            noms = sorted({r.unite.nom for r in risques})
            if o.nb_unites > 1:
                if len(noms) == o.nb_unites == self.nbre_unites_visibles:
                    detail = "Toutes les unités"
                else:
                    detail = ", ".join(noms[:4]) + (" et %d autres" % (len(noms) - 4) if len(noms) > 4 else "")
                portee = format_html(BADGE_COMMUNE + '<br><small class="text-body-secondary">{}</small>', o.nb_unites, detail)
                tri_portee = "1"
            else:
                portee = noms[0] if noms else ""
                tri_portee = "2" + (noms[0] if noms else "")
            dangers = sorted({r.danger for r in risques})
            categories = sorted({r.categorie.nom for r in risques})
            if len(dangers) == 1:
                danger = dangers[0]
            elif len(categories) == 1:
                danger = format_html('{}<br><small class="text-body-secondary">{} risques</small>', categories[0], len(risques))
            else:
                danger = "%d risques" % len(risques)
        responsable = o.responsable
        return [o.pk, (portee, tri_portee), danger, linebreaksbr(o.description),
                (o.categorie.nom if o.categorie else "", "%05d" % o.categorie.ordre if o.categorie else "99999"), responsable,
                (o.echeance.strftime("%d/%m/%Y") if o.echeance else "", o.echeance.isoformat() if o.echeance else "9999-12-31"),
                o.duree, (o.cout_affiche, o.cout if o.cout is not None else -1), (badge_statut(o), o.statut)]


class InviterAReevaluer:
    """Quand une action passe à « Terminée », elle devient une mesure existante : on invite à réévaluer le(s) risque(s)."""

    def form_valid(self, form):
        response = super().form_valid(form)
        if form.cleaned_data["statut"] == "terminee" and ("statut" in form.changed_data):
            risques = list(self.object.risques.all())
            if not risques:
                messages.info(self.request, "Action générale terminée : elle figure dans les mesures générales du document unique.")
            elif len(risques) > 1:
                messages.info(self.request, "Action terminée : elle figure désormais dans les mesures existantes des %d risques concernés. "
                                            "Pensez à les réévaluer si leur gravité ou leur fréquence ont diminué." % len(risques))
            elif self.request.user.has_perm("core.change_risque"):
                messages.info(self.request, format_html(
                    "Action terminée : elle figure désormais dans les mesures existantes du risque « {} ». "
                    '<a href="{}" class="alert-link">Réévaluer le risque</a> si sa gravité ou sa fréquence ont diminué.',
                    risques[0].danger, reverse("risques_modifier", args=[risques[0].pk])))
            else:
                messages.info(self.request, "Action terminée : elle figure désormais dans les mesures existantes du risque « %s »." % risques[0].danger)
        return response


class Saisie:
    template_name = "core/action_form.html"

    def get_queryset(self):
        return actions_visibles(self.request.user)


class Ajouter(InviterAReevaluer, Saisie, crud.Ajouter):
    model, form_class = ActionPrevention, FormulaireAction
    titre, url_liste, url_ajouter = "Ajouter une action de prévention", "actions_liste", "actions_ajouter"
    description = "Une action peut être générale (toute la structure), propre à un risque ou commune à plusieurs unités."


class Modifier(InviterAReevaluer, Saisie, crud.Modifier):
    model, form_class = ActionPrevention, FormulaireAction
    titre, url_liste = "Modifier une action de prévention", "actions_liste"


class Supprimer(crud.Supprimer):
    model, titre, url_liste = ActionPrevention, "Supprimer une action de prévention", "actions_liste"

    def get_queryset(self):
        return actions_visibles(self.request.user)

    def dependances_supplementaires(self):
        n = self.object.nbre_unites
        return [("unités concernées : l'action commune disparaît pour chacune d'elles", n)] if n > 1 else []


# ---------------------------------------------------------------------------------------------------------------
# Actions gérées directement depuis la fiche d'un risque (fenêtres modales de la page « Modifier un risque »).
# Mêmes droits, même journal et même invitation à réévaluer que le plan d'actions ; seul le retour change.
# ---------------------------------------------------------------------------------------------------------------

class DuRisque:
    url_liste = "actions_liste"

    @cached_property
    def risque(self):
        risques = Risque.objects.filter(filtre_structure(self.request.user, "unite__"))
        return get_object_or_404(risques, pk=self.kwargs["risque"])

    def get_queryset(self):
        return ActionPrevention.objects.filter(risques=self.risque)

    def url_retour(self):
        return reverse("risques_modifier", args=[self.risque.pk]) + "#actions"

    def get_success_url(self):
        return self.url_retour()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["url_liste"] = self.url_retour()   # bouton « Annuler » si le formulaire doit être réaffiché en pleine page
        ctx["avec_ajouter"] = False
        return ctx


class RisqueAjouter(DuRisque, InviterAReevaluer, crud.Ajouter):
    model, form_class = ActionPrevention, FormulaireActionRisque
    titre, url_ajouter = "Ajouter une action de prévention", None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["risque_impose"] = self.risque
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["description"] = "Risque : %s" % self.risque.danger
        return ctx


class RisqueModifier(DuRisque, InviterAReevaluer, crud.Modifier):
    model, form_class = ActionPrevention, FormulaireActionRisque
    titre = "Modifier une action de prévention"


class AccesAction(LoginRequiredMixin, DuRisque, View):
    """Retrait ou rattachement d'une action depuis la fiche d'un risque (POST uniquement)."""
    http_method_names = ["post"]

    def journal(self, action, texte):
        consigner(self.request, "modification", action, "%s : %s — %s" % (texte, self.risque.unite.nom, self.risque.danger))


class RisqueRetirer(AccesAction):
    """Action propre au risque : elle est supprimée. Action commune : seul ce risque lui est retiré (« Détacher »)."""

    def post(self, request, risque, pk):
        action = get_object_or_404(ActionPrevention.objects.filter(risques=self.risque), pk=pk)
        if action.risques.count() > 1:
            if not request.user.has_perm("core.change_actionprevention"):
                raise PermissionDenied
            action.risques.remove(self.risque)
            action.maj_structure()
            self.journal(action, "Risque retiré")
            messages.success(request, "Action détachée de ce risque : elle reste en place pour les autres unités.")
        else:
            if not request.user.has_perm("core.delete_actionprevention"):
                raise PermissionDenied
            action.delete()
            consigner(request, "suppression", action)
            messages.success(request, "Suppression effectuée")
        return HttpResponseRedirect(self.url_retour())


class RisqueRattacher(AccesAction):
    """Ajoute ce risque à une action existante (typiquement une action commune à plusieurs unités)."""

    def post(self, request, risque):
        if not request.user.has_perm("core.change_actionprevention"):
            raise PermissionDenied
        candidates = actions_visibles(request.user).filter(risques__isnull=False).exclude(risques=self.risque).distinct()
        action = get_object_or_404(candidates, pk=request.POST.get("action") or 0)
        action.risques.add(self.risque)
        action.maj_structure()
        self.journal(action, "Risque ajouté")
        messages.success(request, "Action rattachée à ce risque.")
        return HttpResponseRedirect(self.url_retour())
