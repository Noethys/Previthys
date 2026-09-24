#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from core.models import calcul_niveau

NIVEAUX = [("faible", "Faible"), ("moyen", "Moyen"), ("critique", "Critique")]


def repartition_par_categorie(risques, limite=6):
    """Nombre de risques par catégorie, triées de la plus fréquente à la moins fréquente.

    Au-delà de `limite` catégories distinctes, les suivantes sont regroupées sous « Autres » pour
    garder le widget lisible sur le tableau de bord.
    """
    comptes = {}
    for r in risques:
        comptes[r.categorie.nom] = comptes.get(r.categorie.nom, 0) + 1
    lignes = sorted(comptes.items(), key=lambda x: -x[1])
    total = len(risques)
    if len(lignes) > limite:
        principales, reste = lignes[:limite - 1], lignes[limite - 1:]
        lignes = principales + [("Autres", sum(n for _, n in reste))]
    return [{"libelle": libelle, "n": n, "pourcentage": round(100 * n / total) if total else 0} for libelle, n in lignes]


def repartition_par_niveau(risques):
    """Nombre de risques par niveau (faible, moyen, critique), dans cet ordre.

    Remplace l'ancienne matrice gravité x fréquence : avec trois facteurs (fréquence, gravité, maîtrise), une
    grille à deux dimensions ne peut plus représenter tous les risques sans en perdre un.
    """
    comptes = {code: 0 for code, _ in NIVEAUX}
    for r in risques:
        comptes[r.niveau if hasattr(r, "niveau") else calcul_niveau(r["cotation"])] += 1
    total = len(risques)
    return [{"code": code, "libelle": libelle, "n": comptes[code], "pourcentage": round(100 * comptes[code] / total) if total else 0} for code, libelle in NIVEAUX]
