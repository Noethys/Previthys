"""Liste du journal des modifications : consultation seule (aucun ajout, modification ni suppression possible)."""
#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.utils import timezone

from core.models import JournalAudit
from core.utils import filtre_structure
from core.views import crud

LIMITE_AFFICHEE = 1000


class Liste(crud.Liste):
    model = JournalAudit
    titre = "Journal des modifications"
    description = "Historique des créations, modifications et suppressions effectuées dans l'application, par utilisateur."
    colonnes = ["Date et heure", "Utilisateur", "Action", "Type", "Objet concerné", "Détail"]
    ordre = "0,desc"
    vide = "Aucune entrée pour l'instant."

    def get_queryset(self):
        qs = JournalAudit.objects.select_related("utilisateur").filter(filtre_structure(self.request.user))
        return qs[:LIMITE_AFFICHEE]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if JournalAudit.objects.filter(filtre_structure(self.request.user)).count() > LIMITE_AFFICHEE:
            ctx["description"] += " Affichage limité aux %d entrées les plus récentes." % LIMITE_AFFICHEE
        return ctx

    def cellules(self, o):
        utilisateur = (o.utilisateur.get_full_name() or o.utilisateur.get_username()) if o.utilisateur else "Système"
        detail = o.detail.replace("\n", "; ") if o.detail else ""
        return [(timezone.localtime(o.horodatage).strftime("%d/%m/%Y %H:%M"), o.horodatage.isoformat()), utilisateur, o.get_action_display(), o.modele.capitalize(), o.objet_repr, detail]
