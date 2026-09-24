#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

import os
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

# Méthode de cotation Fréquence x Gravité x Maîtrise : chaque facteur est noté 1, 4, 7 ou 10, et la cotation
# du risque est le produit des trois notes (de 1 à 1 000). La Maîtrise note l'absence de mesures de prévention :
# 1 = risque bien maîtrisé (note basse), 10 = risque non maîtrisé (note haute, qui aggrave donc la cotation).
FREQUENCE = [(1, "1 - Rare"), (4, "4 - Occasionnelle"), (7, "7 - Fréquente"), (10, "10 - Permanente")]
GRAVITE = [(1, "1 - Bénigne (sans arrêt de travail)"), (4, "4 - Moyenne (avec arrêt de travail)"),
           (7, "7 - Grave (incapacité permanente partielle)"), (10, "10 - Très grave (mortelle ou invalidante)")]
MAITRISE = [(1, "1 - Maîtrisé (mesures en place et efficaces)"), (4, "4 - Moyennement maîtrisé"),
            (7, "7 - Peu maîtrisé (mesures insuffisantes)"), (10, "10 - Non maîtrisé (aucune mesure)")]
STATUTS_ACTIONS = [("a_faire", "À faire"), ("en_cours", "En cours"), ("terminee", "Terminée")]

# Les 20 cotations possibles (produit de trois valeurs parmi 1, 4, 7, 10) se répartissent ainsi :
# faible {1, 4, 7, 10, 16, 28, 40} - moyen {49, 64, 70, 100, 112, 160, 196} - critique {280, 343, 400, 490, 700, 1000}.
SEUIL_MOYEN = 41
SEUIL_CRITIQUE = 200


def calcul_niveau(cotation):
    """Faible jusqu'à 40, moyen de 41 à 196, critique à partir de 200 (voir le détail des seuils ci-dessus)."""
    if cotation >= SEUIL_CRITIQUE:
        return "critique"
    if cotation >= SEUIL_MOYEN:
        return "moyen"
    return "faible"


class Structure(models.Model):
    """Collectivité, site ou établissement. Limite la visibilité des données par utilisateur."""
    nom = models.CharField("Nom", max_length=200, unique=True)
    utilisateurs = models.ManyToManyField(
        settings.AUTH_USER_MODEL, verbose_name="Utilisateurs autorisés", related_name="structures", blank=True,
        help_text="Un utilisateur (hors super-utilisateur) ne voit que les données de ses structures et celles sans structure.")

    class Meta:
        verbose_name = "structure"
        verbose_name_plural = "structures"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class UniteTravail(models.Model):
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True,
                                  help_text="Laissez vide pour rendre l'unité visible de toutes les structures.")
    nom = models.CharField("Nom", max_length=200)
    description = models.TextField("Description", blank=True)
    effectif = models.PositiveIntegerField("Effectif", default=0)

    class Meta:
        verbose_name = "unité de travail"
        verbose_name_plural = "unités de travail"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class CategorieRisque(models.Model):
    nom = models.CharField("Nom", max_length=100, unique=True, error_messages={"unique": "Cette catégorie existe déjà."})
    description = models.TextField("Description", blank=True)
    ordre = models.IntegerField("Ordre d'affichage", default=0)

    class Meta:
        verbose_name = "catégorie de risque"
        verbose_name_plural = "catégories de risques"
        ordering = ["ordre", "nom"]

    def __str__(self):
        return self.nom


class Risque(models.Model):
    unite = models.ForeignKey(UniteTravail, verbose_name="Unité de travail", related_name="risques", on_delete=models.CASCADE)
    categorie = models.ForeignKey(CategorieRisque, verbose_name="Catégorie", related_name="risques", on_delete=models.PROTECT)
    danger = models.CharField("Danger", max_length=250)
    situation = models.TextField("Situation de travail", blank=True)
    frequence = models.IntegerField("Fréquence", choices=FREQUENCE, default=1)
    gravite = models.IntegerField("Gravité", choices=GRAVITE, default=1)
    maitrise = models.IntegerField("Maîtrise", choices=MAITRISE, default=10,
                                    help_text="Note l'absence de maîtrise du risque : 1 = bien maîtrisé, 10 = non maîtrisé.")
    mesures_existantes = models.TextField("Mesures existantes", blank=True)

    class Meta:
        verbose_name = "risque"
        verbose_name_plural = "risques"

    @property
    def cotation(self):
        return self.frequence * self.gravite * self.maitrise

    @property
    def niveau(self):
        return calcul_niveau(self.cotation)

    def __str__(self):
        return self.danger


def chemin_piece_jointe(instance, nom_fichier):
    """Nom de stockage indépendant du nom d'origine et de l'identifiant du risque (confidentialité, pas de collision)."""
    extension = os.path.splitext(nom_fichier)[1].lower()
    return "pieces_jointes/%s/%s%s" % (uuid.uuid4().hex, uuid.uuid4().hex, extension)


class PieceJointe(models.Model):
    """Image ou document joint à un risque (photo d'une situation, fiche de sécurité, plan...)."""
    risque = models.ForeignKey(Risque, verbose_name="Risque", related_name="pieces_jointes", on_delete=models.CASCADE)
    fichier = models.FileField("Fichier", upload_to=chemin_piece_jointe)
    nom_original = models.CharField("Nom d'origine", max_length=255)
    taille = models.PositiveIntegerField("Taille (octets)")
    ajoute_par = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Ajouté par", on_delete=models.SET_NULL, blank=True, null=True)
    ajoute_le = models.DateTimeField("Ajouté le", auto_now_add=True)

    class Meta:
        verbose_name = "pièce jointe"
        verbose_name_plural = "pièces jointes"
        ordering = ["ajoute_le"]

    @property
    def extension(self):
        return os.path.splitext(self.nom_original)[1].lower().lstrip(".")

    @property
    def est_image(self):
        from core.utils.fichiers import est_image
        return est_image(self.nom_original)

    def __str__(self):
        return self.nom_original


class ActionPrevention(models.Model):
    risque = models.ForeignKey(Risque, verbose_name="Risque", related_name="actions", on_delete=models.CASCADE)
    description = models.TextField("Action de prévention")
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Responsable", on_delete=models.SET_NULL, blank=True, null=True)
    echeance = models.DateField("Échéance", blank=True, null=True)
    statut = models.CharField("Statut", max_length=20, choices=STATUTS_ACTIONS, default="a_faire")
    date_realisation = models.DateField("Date de réalisation", blank=True, null=True)

    class Meta:
        verbose_name = "action de prévention"
        verbose_name_plural = "actions de prévention"
        ordering = ["echeance"]

    @property
    def en_retard(self):
        return bool(self.statut != "terminee" and self.echeance and self.echeance < timezone.localdate())

    def __str__(self):
        return self.description[:60]


class JournalAudit(models.Model):
    """Historique des créations, modifications et suppressions effectuées dans l'application, par utilisateur.

    Une entrée est ajoutée automatiquement (voir core/utils/journal.py) à chaque ajout, modification ou
    suppression d'une unité de travail, d'une catégorie, d'un risque, d'une pièce jointe, d'une action de
    prévention ou d'une version archivée. Le journal lui-même n'est ni modifiable ni supprimable, y compris
    par un administrateur (voir core/admin.py) : c'est ce qui lui donne sa valeur de preuve.
    """
    ACTIONS = [("creation", "Création"), ("modification", "Modification"), ("suppression", "Suppression")]

    horodatage = models.DateTimeField("Date et heure", default=timezone.now)
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Utilisateur", on_delete=models.SET_NULL, blank=True, null=True)
    action = models.CharField("Action", max_length=20, choices=ACTIONS)
    modele = models.CharField("Type d'objet", max_length=100)
    objet_repr = models.CharField("Objet concerné", max_length=255)
    detail = models.TextField("Détail", blank=True)
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        verbose_name = "entrée du journal"
        verbose_name_plural = "journal des modifications"
        ordering = ["-horodatage"]

    def __str__(self):
        return "%s - %s %s" % (self.horodatage, self.get_action_display(), self.objet_repr)


class VersionDuerp(models.Model):
    """Copie figée du DUERP. Conservation obligatoire pendant 40 ans : à ne supprimer qu'en connaissance de cause."""
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True,
                                  help_text="Laissez vide pour archiver toutes les structures.")
    numero = models.PositiveIntegerField("Version", default=1)
    date = models.DateTimeField("Date", default=timezone.now)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Auteur", on_delete=models.SET_NULL, blank=True, null=True)
    commentaire = models.TextField("Motif de la mise à jour")
    donnees = models.JSONField("Données archivées", default=list)

    class Meta:
        verbose_name = "version du DUERP"
        verbose_name_plural = "versions du DUERP"
        ordering = ["-numero"]

    def __str__(self):
        return "Version %d" % self.numero
