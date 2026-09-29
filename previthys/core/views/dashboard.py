#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.utils import timezone
from django.views.generic import TemplateView

from core.models import NOTE_COTATION, SEUIL_CRITIQUE, SEUIL_MOYEN, ActionPrevention, Risque, UniteTravail, VersionDuerp
from core.utils import filtre_actions, filtre_structure, repartition_par_categorie, repartition_par_niveau
from core.utils import tableau_de_bord as tdb
from core.utils.update import Get_update_for_accueil
from core.views.crud import Lecture


class Dashboard(Lecture, TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        risques = list(Risque.objects.select_related("unite", "categorie").prefetch_related("actions").filter(filtre_structure(user, "unite__")))
        toutes_actions = list(ActionPrevention.objects.filter(filtre_actions(user)).select_related("categorie").prefetch_related("risques__unite"))
        actions = [a for a in toutes_actions if a.statut != "terminee"]
        actions.sort(key=lambda a: (a.echeance is None, a.echeance))
        unites = list(UniteTravail.objects.filter(filtre_structure(user)))
        derniere = VersionDuerp.objects.filter(filtre_structure(user)).first()
        vigilance = tdb.sans_action(risques)
        reevaluer = tdb.a_reevaluer(risques)
        ctx.update({
            "nbre_unites": len(unites),
            "nbre_risques": len(risques),
            "nbre_critiques": sum(1 for r in risques if r.niveau == "critique"),
            "actions_en_retard": [a for a in actions if a.en_retard],
            "actions_a_venir": [a for a in actions if not a.en_retard][:5],
            "repartition": repartition_par_niveau(risques),
            "derniere_version": derniere,
            "mise_a_jour_ancienne": bool(derniere and (timezone.now() - derniere.date).days > 365),
            "nouvelle_version": Get_update_for_accueil(user) if user.is_superuser else False,
            "top_risques": sorted(risques, key=lambda r: -r.cotation)[:5],
            "repartition_categories": repartition_par_categorie(risques),
            "note_cotation": NOTE_COTATION, "seuil_moyen": SEUIL_MOYEN, "seuil_critique": SEUIL_CRITIQUE,
            # Widgets
            "matrice": tdb.matrice(risques),
            "vigilance": vigilance[:5], "nbre_vigilance": len(vigilance),
            "avancement": tdb.avancement(toutes_actions),
            "a_completer": tdb.a_completer(toutes_actions),
            "budget": tdb.budget(toutes_actions),
            "tableau_unites": tdb.tableau_unites(unites, risques, toutes_actions),
            "mise_a_jour": tdb.mise_a_jour(derniere),
            "reevaluer": reevaluer,
            "actions_terminees_recentes": sorted((a for a in toutes_actions if a.statut == "terminee" and a.date_realisation),
                                                 key=lambda a: a.date_realisation, reverse=True)[:5],
        })
        return ctx
