"""Journal des modifications : construit et enregistre une entrée à chaque création, modification ou
suppression (voir core/models.py:JournalAudit, et son utilisation dans core/views/crud.py).
"""
#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from core.models import JournalAudit


def structure_de(obj):
    """Retrouve la structure d'un objet, en remontant les relations les plus courantes du DUERP.

    Fonctionne directement pour une unité de travail, une version archivée ou une structure elle-même, et en
    remontant la relation vers l'unité de travail pour un risque, une action ou une pièce jointe.
    """
    for chemin in (("structure",), ("unite", "structure"), ("risque", "unite", "structure")):
        cible = obj
        ok = True
        for attr in chemin:
            if not hasattr(cible, attr):
                ok = False
                break
            cible = getattr(cible, attr)
        if ok:
            return cible
    return None


def _texte(valeur):
    if valeur in (None, ""):
        return "(vide)"
    return str(valeur)


def valeur_affichable(model, nom_champ, valeur, est_initial=False):
    """Traduit une valeur brute de formulaire (code de choix, clé étrangère) en texte lisible pour le journal."""
    try:
        champ = model._meta.get_field(nom_champ)
    except Exception:
        return _texte(valeur)
    if getattr(champ, "choices", None):
        return _texte(dict(champ.choices).get(valeur, valeur))
    if champ.is_relation and est_initial and valeur is not None:
        # form.initial donne l'identifiant brut (pas l'objet) pour une clé étrangère : on le résout nous-mêmes.
        lie = champ.related_model.objects.filter(pk=valeur).first()
        return str(lie) if lie else "(objet supprimé depuis)"
    return _texte(valeur)


def decrire_modifications(form):
    """Construit un texte « champ : ancien → nouveau », une ligne par champ effectivement modifié."""
    model = form._meta.model
    # model._meta.fields (et non get_fields()) : uniquement les champs concrets du modèle, pas les relations
    # inverses (ex. le related_name "pieces_jointes" d'une pièce jointe pointant vers ce risque).
    noms_champs_modele = {f.name for f in model._meta.fields}
    lignes = []
    for nom in form.changed_data:
        if nom not in noms_champs_modele:
            continue   # champ du formulaire qui n'existe pas sur le modèle (ex. pieces_jointes)
        label = form.fields[nom].label or nom
        ancien = valeur_affichable(model, nom, form.initial.get(nom), est_initial=True)
        nouveau = valeur_affichable(model, nom, form.cleaned_data.get(nom))
        lignes.append("%s : %s → %s" % (label, ancien, nouveau))
    return "\n".join(lignes)


def consigner(request, action, instance, detail=""):
    """Ajoute une entrée au journal des modifications."""
    utilisateur = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
    JournalAudit.objects.create(
        utilisateur=utilisateur,
        action=action,
        modele=instance._meta.verbose_name,
        objet_repr=str(instance)[:255],
        detail=detail,
        structure=structure_de(instance),
    )
