#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

"""Importe un DUERP existant à partir d'un paquet d'import (.zip) :

    donnees.json   unités, catégories, risques, actions de prévention et références des photos
    photos/...     fichiers joints aux risques

Format 1 : les actions sont décrites dans chaque risque (une action = un risque).
Format 2 : en plus, une liste « actions » au premier niveau, dont chacune désigne ses risques par leur « id »
(aucun = action générale, plusieurs = action commune).

Exemples :
    python manage.py importer_duerp fichier.zip --simulation          # vérifie sans rien enregistrer
    python manage.py importer_duerp fichier.zip --structure "Commune de XXXXX" --utilisateur admin

Tout est importé dans une seule transaction : en cas d'erreur, rien n'est enregistré.
"""

import datetime
import json
import os
import types
import zipfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import ActionPrevention, CategorieAction, CategorieRisque, PieceJointe, Risque, Structure, UniteTravail
from core.utils.fichiers import SIGNATURES
from core.utils.journal import consigner

FORMATS = ("previthys-import/1", "previthys-import/2")


class Simulation(Exception):
    """Levée en fin de simulation pour annuler la transaction."""


class Command(BaseCommand):
    help = "Importe un DUERP (unités, risques, actions, photos) depuis un paquet d'import .zip."

    def add_arguments(self, parser):
        parser.add_argument("paquet", help="Chemin du paquet d'import (.zip)")
        parser.add_argument("--structure", help="Nom de la structure à laquelle rattacher les unités (créée si besoin). "
                                                "Sans cette option, les unités sont visibles de toutes les structures.")
        parser.add_argument("--utilisateur", help="Identifiant de l'utilisateur à qui attribuer l'import (journal, photos).")
        parser.add_argument("--simulation", action="store_true", help="Vérifie le paquet et affiche le bilan sans rien enregistrer.")
        parser.add_argument("--forcer", action="store_true", help="Importe même si des unités portant les mêmes noms existent déjà.")

    def handle(self, *args, **options):
        chemin = options["paquet"]
        if not zipfile.is_zipfile(chemin):
            raise CommandError("%s n'est pas un fichier .zip valide." % chemin)
        with zipfile.ZipFile(chemin) as archive:
            try:
                donnees = json.loads(archive.read("donnees.json").decode("utf-8"))
            except KeyError:
                raise CommandError("Le paquet ne contient pas de fichier donnees.json.")
            if donnees.get("format") not in FORMATS:
                raise CommandError("Format de paquet non reconnu (attendus : %s)." % ", ".join(FORMATS))

            utilisateur = None
            if options["utilisateur"]:
                utilisateur = get_user_model().objects.filter(username=options["utilisateur"]).first()
                if utilisateur is None:
                    raise CommandError("Utilisateur « %s » introuvable." % options["utilisateur"])
            self.requete = types.SimpleNamespace(user=utilisateur)   # pour le journal des modifications
            self.utilisateur = utilisateur
            self.detail = "Import du DUERP : %s" % donnees.get("source", os.path.basename(chemin))

            self.fichiers_ecrits = []
            try:
                with transaction.atomic():
                    bilan = self.importer(donnees, archive, options)
                    if options["simulation"]:
                        raise Simulation()
            except BaseException as erreur:
                # La base est annulée par la transaction ; on retire aussi les photos déjà écrites sur le disque.
                for fichier in self.fichiers_ecrits:
                    fichier.storage.delete(fichier.name)
                if not isinstance(erreur, Simulation):
                    raise
                self.stdout.write(self.style.WARNING("SIMULATION : rien n'a été enregistré."))
        self.afficher(bilan)

    # -----------------------------------------------------------------------------------------------------------

    def importer(self, donnees, archive, options):
        bilan = {"unites": 0, "categories_creees": [], "risques": 0, "actions": 0, "generales": 0, "communes": 0, "photos": 0}

        structure = None
        if options["structure"]:
            structure, _ = Structure.objects.get_or_create(nom=options["structure"])

        noms = [u["nom"] for u in donnees["unites"]]
        existantes = UniteTravail.objects.filter(structure=structure, nom__in=noms).values_list("nom", flat=True)
        if existantes and not options["forcer"]:
            raise CommandError("Ces unités existent déjà (utilisez --forcer pour importer quand même) : %s" % ", ".join(existantes))

        # Catégories : réutilisées si elles existent (même nom), créées sinon
        categories = {}
        ordre_max = max(CategorieRisque.objects.values_list("ordre", flat=True), default=0)
        for c in donnees["categories"]:
            cat = CategorieRisque.objects.filter(nom=c["nom"]).first()
            if cat is None:
                ordre_max += 10
                cat = CategorieRisque.objects.create(nom=c["nom"], description=c.get("description", ""), ordre=ordre_max)
                consigner(self.requete, "creation", cat, self.detail)
                bilan["categories_creees"].append(cat.nom)
            categories[c["nom"]] = cat

        unites = {}
        for u in donnees["unites"]:
            unite = UniteTravail.objects.create(structure=structure, nom=u["nom"], description=u.get("description", ""), effectif=u.get("effectif", 0))
            consigner(self.requete, "creation", unite, self.detail)
            unites[u["nom"]] = unite
            bilan["unites"] += 1

        risques_par_id = {}
        for r in donnees["risques"]:
            risque = Risque.objects.create(
                unite=unites[r["unite"]], categorie=categories[r["categorie"]], danger=r["danger"][:250],
                situation=r.get("situation", ""), frequence=r["frequence"], gravite=r["gravite"], maitrise=r["maitrise"],
                mesures_existantes=r.get("mesures_existantes", ""))
            consigner(self.requete, "creation", risque, self.detail)
            bilan["risques"] += 1

            risques_par_id[r.get("id")] = risque
            for a in r.get("actions", []):          # format 1 : action propre à ce risque
                self.creer_action(a, [risque], None, bilan)

            for p in r.get("pieces_jointes", []):
                contenu = archive.read(p["fichier"])
                extension = os.path.splitext(p["nom"])[1].lower()
                if extension not in SIGNATURES or (SIGNATURES[extension] and not contenu.startswith(SIGNATURES[extension])):
                    raise CommandError("Fichier refusé (type non autorisé ou contenu incohérent) : %s" % p["nom"])
                piece = PieceJointe(risque=risque, nom_original=p["nom"][:255], taille=len(contenu), ajoute_par=self.utilisateur)
                piece.fichier.save(p["nom"], ContentFile(contenu), save=True)
                self.fichiers_ecrits.append(piece.fichier)
                consigner(self.requete, "creation", piece, "Ajoutée au risque « %s » (%s)" % (risque.danger, self.detail))
                bilan["photos"] += 1

        # Format 2 : actions désignant leurs risques (aucun = générale, plusieurs = commune)
        for a in donnees.get("actions", []):
            try:
                risques = [risques_par_id[i] for i in a.get("risques", [])]
            except KeyError as e:
                raise CommandError("Action « %s » : risque %s introuvable dans le paquet." % (a["description"][:60], e))
            self.creer_action(a, risques, structure, bilan)
        return bilan

    def creer_action(self, a, risques, structure, bilan):
        valeurs = {"statut": a.get("statut", "a_faire"), "duree": (a.get("duree") or "")[:100], "responsable": (a.get("responsable") or "")[:150],
                   "echeance": self.date(a.get("echeance")), "date_realisation": self.date(a.get("date_realisation"))}
        if a.get("cout") is not None:
            valeurs["cout"] = Decimal(str(a["cout"]))
        if not risques:
            valeurs["structure"] = structure   # action générale : structure de l'import
        if a.get("categorie"):
            valeurs["categorie"], cree = CategorieAction.objects.get_or_create(nom=a["categorie"], defaults={"ordre": 100})
            if cree:
                bilan["categories_creees"].append(a["categorie"] + " (actions)")
        action = ActionPrevention.objects.create(risques=risques, description=a["description"], **valeurs)
        consigner(self.requete, "creation", action, self.detail)
        bilan["actions"] += 1
        if not risques:
            bilan["generales"] += 1
        elif action.est_commune:
            bilan["communes"] += 1

    @staticmethod
    def date(valeur):
        return datetime.date.fromisoformat(valeur) if valeur else None

    def afficher(self, bilan):
        self.stdout.write("Unités de travail : %d" % bilan["unites"])
        self.stdout.write("Risques : %d" % bilan["risques"])
        self.stdout.write("Actions de prévention : %d (dont %d générales et %d communes à plusieurs unités)" % (bilan["actions"], bilan["generales"], bilan["communes"]))
        self.stdout.write("Photos : %d" % bilan["photos"])
        if bilan["categories_creees"]:
            self.stdout.write("Catégories créées : %s" % ", ".join(bilan["categories_creees"]))
