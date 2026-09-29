#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

import os
import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver
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

# Evaluation
SEUIL_MOYEN = 70
SEUIL_CRITIQUE = 343


def _tranches():
    """Valeurs de cotation réellement possibles (produit de trois notes 1, 4, 7 ou 10), par niveau."""
    valeurs = sorted({f * g * m for f in (1, 4, 7, 10) for g in (1, 4, 7, 10) for m in (1, 4, 7, 10)})
    return ([v for v in valeurs if v < SEUIL_MOYEN], [v for v in valeurs if SEUIL_MOYEN <= v < SEUIL_CRITIQUE],
            [v for v in valeurs if v >= SEUIL_CRITIQUE])


def _nombre(n):
    return "{:,}".format(n).replace(",", "\u202f")


# Texte d'explication de la cotation (liste des risques, tableau de bord, export Excel), déduit des seuils :
# « Cotation = fréquence × gravité × maîtrise : faible (1 à 64), moyen (70 à 280), critique (343 à 1 000). »
NOTE_COTATION = "Cotation = fréquence × gravité × maîtrise : faible (%s), moyen (%s), critique (%s)." % tuple(
    "%s à %s" % (_nombre(t[0]), _nombre(t[-1])) for t in _tranches())


def calcul_niveau(cotation):
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
    maitrise = models.IntegerField("Maîtrise", choices=MAITRISE, default=10)
    mesures_existantes = models.TextField("Mesures existantes", blank=True)
    date_evaluation = models.DateField("Dernière évaluation", blank=True, null=True,
                                       help_text="Mise à jour à chaque enregistrement de la fiche du risque (cotation revue).")

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


class CategorieAction(models.Model):
    """Type d'action de prévention (formation, matériel, organisation, travaux...), pour regrouper le plan d'actions."""
    nom = models.CharField("Nom", max_length=100, unique=True, error_messages={"unique": "Cette catégorie existe déjà."})
    description = models.TextField("Description", blank=True)
    ordre = models.IntegerField("Ordre d'affichage", default=0)

    class Meta:
        verbose_name = "catégorie d'action"
        verbose_name_plural = "catégories d'actions"
        ordering = ["ordre", "nom"]

    def __str__(self):
        return self.nom


class GestionnaireActions(models.Manager):
    def create(self, risque=None, risques=None, **kwargs):
        """Accepte encore `risque=` (une action liée à un seul risque), comme avant les actions multi-risques."""
        action = super().create(**kwargs)
        liste = list(risques or []) + ([risque] if risque is not None else [])
        if liste:
            action.risques.add(*liste)
            action.maj_structure()
        return action


class ActionPrevention(models.Model):
    """Action de prévention. Selon ses risques, elle est :
    - propre à un risque (un seul risque) ;
    - commune (plusieurs risques, en général une même action pour plusieurs unités : une seule action, un seul
      coût, un seul statut, affichée sur la fiche de chaque risque) ;
    - générale (aucun risque) : mesure qui concerne toute la structure (sensibilisation, outil de signalement...).
    """
    risques = models.ManyToManyField(Risque, verbose_name="Risques concernés", related_name="actions", blank=True)
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True,
                                  help_text="Pour une action générale : structure concernée (vide = toutes). "
                                            "Pour les autres actions, déduite des unités des risques.")
    description = models.TextField("Action de prévention")
    categorie = models.ForeignKey(CategorieAction, verbose_name="Catégorie", related_name="actions", on_delete=models.PROTECT, blank=True, null=True)
    responsable = models.CharField("Responsable", max_length=150, blank=True, help_text="Personne ou service qui pilote l'action (texte libre).")
    echeance = models.DateField("Échéance", blank=True, null=True)
    duree = models.CharField("Durée", max_length=100, blank=True)
    cout = models.DecimalField("Coût", max_digits=12, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)])
    statut = models.CharField("Statut", max_length=20, choices=STATUTS_ACTIONS, default="a_faire")
    date_realisation = models.DateField("Date de réalisation", blank=True, null=True)

    objects = GestionnaireActions()

    class Meta:
        verbose_name = "action de prévention"
        verbose_name_plural = "actions de prévention"
        ordering = ["echeance"]

    @property
    def cout_affiche(self):
        """Coût au format français : 1 250,00 €."""
        if self.cout is None:
            return ""
        return ("{:,.2f}".format(self.cout)).replace(",", "\u202f").replace(".", ",") + "\u00a0€"

    @property
    def en_retard(self):
        return bool(self.statut != "terminee" and self.echeance and self.echeance < timezone.localdate())

    # Portée (utilise risques.all() : profite d'un prefetch_related("risques__unite") éventuel)
    @property
    def unites(self):
        vues = {}
        for r in self.risques.all():
            vues.setdefault(r.unite_id, r.unite)
        return sorted(vues.values(), key=lambda u: u.nom)

    @property
    def est_generale(self):
        return self.pk is not None and not self.risques.all()

    @property
    def nbre_unites(self):
        return len({r.unite_id for r in self.risques.all()})

    @property
    def est_commune(self):
        return self.nbre_unites > 1

    @property
    def resume_unites(self):
        """Texte court de la portée : « Action générale », nom de l'unité ou « Commune à N unités »."""
        if self.est_generale:
            return "Action générale"
        n = self.nbre_unites
        return self.unites[0].nom if n == 1 else "Commune à %d unités" % n

    def maj_structure(self):
        """Pour une action liée à des risques, la structure est celle de leurs unités si elle est unique (sinon vide).
        Elle sert au journal ; la visibilité d'une telle action dépend de ses risques (voir filtre_actions)."""
        if not self.risques.exists():
            return
        structures = set(self.risques.values_list("unite__structure", flat=True).distinct())
        structure = structures.pop() if len(structures) == 1 else None
        if self.structure_id != structure:
            self.structure_id = structure
            self.save(update_fields=["structure"])

    def __str__(self):
        return self.description[:60]


def actions_propres(risques):
    """Actions qui n'ont pas d'autre risque que ceux indiqués : elles disparaissent avec eux."""
    ids = [r.pk for r in risques]
    return ActionPrevention.objects.filter(risques__in=ids).exclude(risques__in=Risque.objects.exclude(pk__in=ids)).distinct()


@receiver(pre_delete, sender=Risque)
def noter_actions_du_risque(sender, instance, **kwargs):
    instance._actions_liees = list(instance.actions.values_list("pk", flat=True))


@receiver(post_delete, sender=Risque)
def supprimer_actions_orphelines(sender, instance, **kwargs):
    """Une action qui n'a plus aucun risque après la suppression d'un risque (ou de son unité) est supprimée, comme
    avant : elle ne doit pas devenir une action générale. Une action commune perd seulement ce risque.
    (post_delete : quand une unité est supprimée, tous ses risques et leurs liens sont déjà effacés à ce moment.)"""
    ids = getattr(instance, "_actions_liees", None)
    if ids:
        ActionPrevention.objects.filter(pk__in=ids, risques__isnull=True).delete()


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
    mesures_generales = models.JSONField("Mesures générales archivées", default=list, blank=True)

    class Meta:
        verbose_name = "version du DUERP"
        verbose_name_plural = "versions du DUERP"
        ordering = ["-numero"]

    def __str__(self):
        return "Version %d" % self.numero
