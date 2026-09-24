#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

import datetime

from django.core.management.base import BaseCommand

from core.models import ActionPrevention, CategorieRisque, Risque, UniteTravail


class Command(BaseCommand):
    help = "Charge des données d'exemple (mairie fictive) pour essayer l'application. Sans effet si des unités existent déjà."

    def handle(self, *args, **options):
        if UniteTravail.objects.exists():
            self.stdout.write("Des unités de travail existent déjà : rien n'a été chargé.")
            return
        cat = lambda nom: CategorieRisque.objects.get_or_create(nom=nom, defaults={"ordre": 50})[0]
        techniques = UniteTravail.objects.create(nom="Services techniques", effectif=14, description="Voirie, espaces verts, bâtiments.")
        accueil = UniteTravail.objects.create(nom="Accueil et état civil", effectif=6, description="Accueil du public en mairie.")
        cantine = UniteTravail.objects.create(nom="Restauration scolaire", effectif=9, description="Cuisine centrale et offices.")
        # Cotation = fréquence x gravité x maîtrise (chacune notée 1, 4, 7 ou 10 ; maîtrise : 1 = bien maîtrisé, 10 = non maîtrisé).
        r1 = Risque.objects.create(unite=techniques, categorie=cat("Chutes et manutentions"), danger="Chute de hauteur (échelle, toiture)", situation="Interventions sur bâtiments communaux.", frequence=4, gravite=10, maitrise=4, mesures_existantes="Échelles contrôlées une fois par an.")
        Risque.objects.create(unite=techniques, categorie=cat("Postures et TMS"), danger="Port de charges lourdes", situation="Manutention de matériel et de barrières.", frequence=7, gravite=4, maitrise=4, mesures_existantes="Diable à disposition.")
        Risque.objects.create(unite=techniques, categorie=cat("Produits chimiques"), danger="Produits phytosanitaires", situation="Entretien des espaces verts.", frequence=4, gravite=7, maitrise=1, mesures_existantes="Stockage dans une armoire dédiée.")
        r4 = Risque.objects.create(unite=accueil, categorie=cat("Agressions et incivilités"), danger="Agressions verbales du public", situation="Accueil aux heures d'affluence.", frequence=7, gravite=4, maitrise=4, mesures_existantes="Bouton d'alerte au guichet.")
        Risque.objects.create(unite=accueil, categorie=cat("Risques psychosociaux"), danger="Surcharge de travail", situation="Périodes d'élections et de cartes d'identité.", frequence=7, gravite=4, maitrise=10)
        r6 = Risque.objects.create(unite=cantine, categorie=cat("Incendie et explosion"), danger="Départ de feu en cuisine", situation="Friteuses et fourneaux.", frequence=4, gravite=10, maitrise=4, mesures_existantes="Extincteurs et formation annuelle.")
        r7 = Risque.objects.create(unite=cantine, categorie=cat("Chutes et manutentions"), danger="Sol glissant", situation="Nettoyage de la cuisine.", frequence=10, gravite=4, maitrise=4, mesures_existantes="Chaussures antidérapantes.")
        aujourdhui = datetime.date.today()
        jours = lambda n: aujourdhui + datetime.timedelta(days=n)
        ActionPrevention.objects.create(risque=r1, description="Remplacer les deux échelles du dépôt", echeance=jours(-20), statut="en_cours")
        ActionPrevention.objects.create(risque=r4, description="Protocole en cas d'agression à l'accueil", echeance=jours(25))
        ActionPrevention.objects.create(risque=r6, description="Exercice d'évacuation incendie", echeance=jours(60))
        ActionPrevention.objects.create(risque=r7, description="Renouveler les tapis antidérapants", echeance=jours(-40), statut="terminee", date_realisation=jours(-45))
        self.stdout.write(self.style.SUCCESS("Données d'exemple chargées : 3 unités, 7 risques, 4 actions (dont 1 terminée, visible comme mesure existante)."))
