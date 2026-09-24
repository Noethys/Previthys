#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.utils import timezone
from django.views.generic import TemplateView

from core.models import ActionPrevention, Risque, UniteTravail, VersionDuerp
from core.utils import filtre_structure, repartition_par_categorie, repartition_par_niveau
from core.utils.update import Get_update_for_accueil
from core.views.crud import Lecture


class Dashboard(Lecture, TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        risques = list(Risque.objects.select_related("unite", "categorie").filter(filtre_structure(user, "unite__")))
        actions = ActionPrevention.objects.select_related("risque__unite").filter(filtre_structure(user, "risque__unite__")).exclude(statut="terminee")
        derniere = VersionDuerp.objects.filter(filtre_structure(user)).first()
        ctx.update({
            "nbre_unites": UniteTravail.objects.filter(filtre_structure(user)).count(),
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
        })
        return ctx
