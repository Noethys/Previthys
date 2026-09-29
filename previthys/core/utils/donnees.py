#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

import datetime

from django.db.models import Q
from django.urls import reverse

from core.models import ActionPrevention, UniteTravail
from core.utils.fichiers import est_image
from core.utils.structures import filtre_structure


def construire_donnees(user, structure=None):
    """Retourne le DUERP sous forme de structure JSON, utilisée pour l'affichage, l'export et l'archivage."""
    unites = UniteTravail.objects.filter(filtre_structure(user))
    if structure:
        unites = unites.filter(Q(structure=structure) | Q(structure__isnull=True))
    unites = unites.prefetch_related("risques__categorie", "risques__actions", "risques__actions__risques", "risques__actions__categorie",
                                     "risques__pieces_jointes")
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
                "actions": [_action(a) for a in r.actions.all()],
            })
        risques.sort(key=lambda x: -x["cotation"])
        donnees.append({"nom": unite.nom, "effectif": unite.effectif, "description": unite.description, "risques": risques})
    return donnees


def _action(a):
    return {
        "id": a.pk,   # permet de compter une action commune une seule fois (plan d'actions du document)
        "description": a.description, "statut": a.get_statut_display(), "categorie": a.categorie.nom if a.categorie else "",
        "responsable": a.responsable,
        "echeance": a.echeance.strftime("%d/%m/%Y") if a.echeance else "",
        "terminee": a.statut == "terminee",
        "date_realisation": a.date_realisation.strftime("%d/%m/%Y") if a.date_realisation else "",
        "commune": a.nbre_unites if a.est_commune else 0,   # nombre d'unités d'une action commune (0 sinon)
    }


def construire_mesures_generales(user, structure=None):
    """Actions générales (sans risque) visibles, pour le document, l'export et l'archivage."""
    actions = ActionPrevention.objects.filter(risques__isnull=True).filter(filtre_structure(user)).select_related("categorie")
    if structure:
        actions = actions.filter(Q(structure=structure) | Q(structure__isnull=True))
    return [_action(a) for a in actions]


MACARONS = {"terminee": ("Terminée", "success"), "en_cours": ("En cours", "primary"), "retard": ("En retard", "danger"), "a_faire": ("À faire", "secondary")}
ORDRE_MACARONS = ["terminee", "en_cours", "retard", "a_faire"]


def macaron(action, date_reference):
    """Statut affiché d'une action (données du document ou d'une archive) : terminée, en cours, en retard ou à faire.
    « En retard » est évalué à la date de référence (date du jour, ou date de la version archivée)."""
    terminee = action["terminee"] if "terminee" in action else action.get("statut") == "Terminée"
    if terminee:
        return "terminee"
    echeance = None
    if action.get("echeance"):
        try:
            echeance = datetime.datetime.strptime(action["echeance"], "%d/%m/%Y").date()
        except ValueError:
            pass
    if echeance and date_reference and echeance < date_reference:
        return "retard"
    return "en_cours" if action.get("statut") == "En cours" else "a_faire"


def avec_macaron(action, date_reference):
    code = macaron(action, date_reference)
    return {**action, "macaron": code, "macaron_libelle": MACARONS[code][0], "macaron_couleur": MACARONS[code][1]}


def normaliser_donnees(donnees, date_reference=None):
    """Prépare les données pour l'affichage et l'export : les actions terminées deviennent des mesures réalisées.

    Pour chaque risque, ajoute `mesures_realisees` (actions terminées), ne laisse dans `actions` que les
    actions encore prévues et garde la liste complète dans `actions_toutes`, chaque action portant son macaron
    de statut (terminées d'abord, puis en cours, en retard, à faire). Fonctionne aussi avec les archives
    anciennes, qui ne portent pas l'indicateur `terminee`.
    """
    resultat = []
    for unite in donnees:
        risques = []
        for r in unite["risques"]:
            toutes = [avec_macaron(a, date_reference) for a in r.get("actions", [])]
            toutes.sort(key=lambda a: ORDRE_MACARONS.index(a["macaron"]))
            realisees = [a for a in toutes if a["macaron"] == "terminee"]
            prevues = [a for a in toutes if a["macaron"] != "terminee"]
            risques.append({
                **r,
                # Mesures existantes saisies sur le risque : une par ligne (affichées avec le macaron « Existante »)
                "mesures_liste": [l.strip(" •-\t") for l in (r.get("mesures_existantes") or "").splitlines() if l.strip(" •-\t")],
                "mesures_realisees": [{"description": a["description"], "date": a.get("date_realisation", ""), "commune": a.get("commune", 0)}
                                      for a in realisees],
                "actions": prevues,
                "actions_toutes": toutes,
            })
        resultat.append({**unite, "risques": risques})
    return resultat
