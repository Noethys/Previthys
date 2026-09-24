#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.db.models import Q
from django.urls import reverse

from core.models import UniteTravail
from core.utils.fichiers import est_image
from core.utils.structures import filtre_structure


def construire_donnees(user, structure=None):
    """Retourne le DUERP sous forme de structure JSON, utilisée pour l'affichage, l'export et l'archivage."""
    unites = UniteTravail.objects.filter(filtre_structure(user))
    if structure:
        unites = unites.filter(Q(structure=structure) | Q(structure__isnull=True))
    unites = unites.prefetch_related("risques__categorie", "risques__actions", "risques__actions__responsable", "risques__pieces_jointes")
    donnees = []
    for unite in unites:
        risques = []
        for r in unite.risques.all():
            risques.append({
                "categorie": r.categorie.nom, "danger": r.danger, "situation": r.situation,
                "frequence": r.frequence, "gravite": r.gravite, "maitrise": r.maitrise, "cotation": r.cotation, "niveau": r.niveau,
                "mesures_existantes": r.mesures_existantes,
                "images": [{"url": reverse("pieces_jointes_telecharger", args=[p.pk]), "nom": p.nom_original}
                           for p in r.pieces_jointes.all() if est_image(p.nom_original)],
                "actions": [{
                    "description": a.description, "statut": a.get_statut_display(),
                    "responsable": (a.responsable.get_full_name() or a.responsable.get_username()) if a.responsable else "",
                    "echeance": a.echeance.strftime("%d/%m/%Y") if a.echeance else "",
                    "terminee": a.statut == "terminee",
                    "date_realisation": a.date_realisation.strftime("%d/%m/%Y") if a.date_realisation else "",
                } for a in r.actions.all()],
            })
        risques.sort(key=lambda x: -x["cotation"])
        donnees.append({"nom": unite.nom, "effectif": unite.effectif, "description": unite.description, "risques": risques})
    return donnees


def normaliser_donnees(donnees):
    """Prépare les données pour l'affichage et l'export : les actions terminées deviennent des mesures réalisées.

    Pour chaque risque, ajoute `mesures_realisees` (actions terminées), ne laisse dans `actions` que les
    actions encore prévues et garde la liste complète dans `actions_toutes`. Fonctionne aussi avec les
    archives anciennes, qui ne portent pas l'indicateur `terminee`.
    """
    resultat = []
    for unite in donnees:
        risques = []
        for r in unite["risques"]:
            toutes = r.get("actions", [])
            realisees, prevues = [], []
            for a in toutes:
                terminee = a["terminee"] if "terminee" in a else a.get("statut") == "Terminée"
                (realisees if terminee else prevues).append(a)
            risques.append({
                **r,
                "mesures_realisees": [{"description": a["description"], "date": a.get("date_realisation", "")} for a in realisees],
                "actions": prevues,
                "actions_toutes": toutes,
            })
        resultat.append({**unite, "risques": risques})
    return resultat
