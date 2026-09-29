"""Calculs des widgets du tableau de bord (vue d'ensemble)."""
#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

import datetime

from django.utils import timezone

from core.models import FREQUENCE, GRAVITE

NIVEAUX = ("critique", "moyen", "faible")
STATUTS = [("terminee", "Terminées", "success"), ("en_cours", "En cours", "primary"), ("a_faire", "À faire", "secondary"), ("retard", "En retard", "danger")]


def libelle_court(choix):
    return {v: l.split(" - ")[1].split(" (")[0] for v, l in choix}


def matrice(risques):
    """Grille gravité (lignes, de la plus grave à la moins grave) × fréquence (colonnes).

    La cotation dépend aussi de la maîtrise : une même case peut donc contenir des risques de niveaux différents.
    Chaque case donne le total, la répartition par niveau et le niveau le plus élevé (couleur de la case)."""
    cases = {}
    for r in risques:
        case = cases.setdefault((r.gravite, r.frequence), {n: 0 for n in NIVEAUX})
        case[r.niveau] += 1
    grille = []
    for g, lg in sorted(libelle_court(GRAVITE).items(), reverse=True):
        ligne = []
        for f in sorted(libelle_court(FREQUENCE)):
            c = cases.get((g, f), {n: 0 for n in NIVEAUX})
            ligne.append({"gravite": g, "frequence": f, "total": sum(c.values()), "pire": next((n for n in NIVEAUX if c[n]), ""),
                          "detail": [(n, c[n]) for n in NIVEAUX if c[n]]})
        grille.append({"gravite": g, "libelle": lg, "cases": ligne})
    return {"lignes": grille, "frequences": sorted(libelle_court(FREQUENCE).items())}


def sans_action(risques):
    """Risques moyens ou critiques sans aucune action non terminée (les actions doivent être préchargées)."""
    resultat = [r for r in risques if r.niveau in ("critique", "moyen") and not any(a.statut != "terminee" for a in r.actions.all())]
    return sorted(resultat, key=lambda r: -r.cotation)


def a_reevaluer(risques):
    """Risques dont une action s'est terminée après leur dernière évaluation (ou jamais évalués depuis)."""
    resultat = []
    for r in risques:
        dates = [a.date_realisation for a in r.actions.all() if a.statut == "terminee" and a.date_realisation]
        if dates and (r.date_evaluation is None or max(dates) > r.date_evaluation):
            resultat.append(r)
    return resultat


def statut_affiche(action):
    return "retard" if action.en_retard else action.statut


def avancement(actions):
    """Répartition des actions par statut, pour tout le plan puis par catégorie d'action."""
    def pile(liste):
        n = len(liste)
        comptes = {s: 0 for s, _, _ in STATUTS}
        for a in liste:
            comptes[statut_affiche(a)] += 1
        return {"total": n, "segments": [{"code": s, "libelle": l, "couleur": c, "n": comptes[s], "pourcentage": "%.1f" % (100 * comptes[s] / n) if n else "0",   # texte avec un point : valeur CSS, sans virgule française
                                          "visible": n and 100 * comptes[s] / n >= 6}
                                         for s, l, c in STATUTS if comptes[s]],
                "pourcentage_terminees": round(100 * comptes["terminee"] / n) if n else 0}
    groupes = {}
    for a in actions:
        cle = (a.categorie.ordre, a.categorie.nom) if a.categorie else (10 ** 6, "Non classées")
        groupes.setdefault(cle, []).append(a)
    return {"ensemble": pile(actions), "categories": [{"libelle": nom, **pile(liste)} for (_, nom), liste in sorted(groupes.items())]}


def a_completer(actions):
    """Actions en cours (non terminées) auxquelles il manque une information."""
    ouvertes = [a for a in actions if a.statut != "terminee"]
    n = len(ouvertes)
    manques = [("echeance", "sans échéance", "danger", lambda a: not a.echeance),
               ("responsable", "sans responsable", "warning", lambda a: not a.responsable),
               ("categorie", "sans catégorie", "warning", lambda a: not a.categorie_id),
               ("cout", "sans coût estimé", "secondary", lambda a: a.cout is None)]
    return {"total": n, "manques": [{"code": code, "libelle": lib, "couleur": coul, "n": sum(1 for a in ouvertes if test(a)),
                                     "pourcentage": round(100 * sum(1 for a in ouvertes if test(a)) / n) if n else 0}
                                    for code, lib, coul, test in manques]}


def budget(actions):
    """Coûts saisis : prévus (actions non terminées) et réalisés (actions terminées), par catégorie d'action."""
    lignes, prevu, realise, nb = {}, 0, 0, 0
    for a in actions:
        if a.cout is None:
            continue
        nb += 1
        cle = (a.categorie.ordre, a.categorie.nom) if a.categorie else (10 ** 6, "Non classées")
        ligne = lignes.setdefault(cle, {"libelle": cle[1], "prevu": 0, "realise": 0})
        if a.statut == "terminee":
            ligne["realise"] += a.cout
            realise += a.cout
        else:
            ligne["prevu"] += a.cout
            prevu += a.cout
    return {"prevu": prevu, "realise": realise, "nb": nb, "lignes": [v for _, v in sorted(lignes.items())]}


def tableau_unites(unites, risques, actions, limite=8):
    """Unités les plus exposées : risques par niveau, actions en cours, cotation maximale."""
    par_unite = {u.pk: {"unite": u, "niveaux": {n: 0 for n in NIVEAUX}, "actions": 0, "max": 0} for u in unites}
    for r in risques:
        ligne = par_unite.get(r.unite_id)
        if ligne:
            ligne["niveaux"][r.niveau] += 1
            ligne["max"] = max(ligne["max"], r.cotation)
    for a in actions:
        if a.statut != "terminee":
            for unite_id in {r.unite_id for r in a.risques.all()}:
                if unite_id in par_unite:
                    par_unite[unite_id]["actions"] += 1
    lignes = sorted(par_unite.values(), key=lambda l: (-l["niveaux"]["critique"], -l["max"], -l["niveaux"]["moyen"], l["unite"].nom))
    for l in lignes:
        l["niveaux"] = [(n, l["niveaux"][n]) for n in NIVEAUX]
    return {"lignes": lignes[:limite], "total": len(lignes)}


def mise_a_jour(derniere_version):
    """Échéance de la mise à jour annuelle du DUERP à partir de la dernière version archivée."""
    if derniere_version is None:
        return {"version": None}
    date = timezone.localtime(derniere_version.date).date()
    echeance = date + datetime.timedelta(days=365)
    reste = (echeance - timezone.localdate()).days
    return {"version": derniere_version, "date": date, "echeance": echeance, "reste": reste, "retard": -reste,
            "couleur": "danger" if reste < 0 else "warning" if reste <= 60 else "success"}
