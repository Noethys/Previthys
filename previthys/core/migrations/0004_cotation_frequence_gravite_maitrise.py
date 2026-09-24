"""Passage à la cotation Fréquence x Gravité x Maîtrise (échelle 1, 4, 7, 10 pour chaque facteur).

Les risques déjà saisis avaient une gravité et une fréquence notées de 1 à 4 ; ces quatre niveaux sont conservés
mais renumérotés (1→1, 2→4, 3→7, 4→10), dans le même ordre. Le nouveau facteur « Maîtrise » est initialisé à 10
(non maîtrisé) pour tous les risques existants : cette valeur est délibérément pessimiste, en l'absence de toute
saisie antérieure sur ce point, pour inviter à revoir chaque risque plutôt que de sous-estimer silencieusement sa
cotation. Voir la note de mise à jour du DUERP à ce sujet.
"""
#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.db import migrations, models

CORRESPONDANCE_ECHELLE = {1: 1, 2: 4, 3: 7, 4: 10}


def _appliquer(Risque, correspondance):
    """Applique une correspondance {ancien: nouveau} à gravite et frequence, sans collision.

    La valeur 4 existe à la fois dans l'ancienne échelle (1-4) et la nouvelle (1,4,7,10) : convertir
    directement provoquerait une double conversion (un ancien 2 deviendrait 4 puis, si un ancien 4 est
    encore à convertir vers 10, le 2 nouvellement à 4 serait lui aussi emporté vers 10). On passe donc par
    des valeurs temporaires négatives, disjointes des deux échelles, avant d'écrire les valeurs finales.
    """
    for ancien in correspondance:
        Risque.objects.filter(gravite=ancien).update(gravite=-ancien)
        Risque.objects.filter(frequence=ancien).update(frequence=-ancien)
    for ancien, nouveau in correspondance.items():
        Risque.objects.filter(gravite=-ancien).update(gravite=nouveau)
        Risque.objects.filter(frequence=-ancien).update(frequence=nouveau)


def remapper_gravite_et_frequence(apps, schema_editor):
    _appliquer(apps.get_model("core", "Risque"), CORRESPONDANCE_ECHELLE)


def revenir_a_lancienne_echelle(apps, schema_editor):
    _appliquer(apps.get_model("core", "Risque"), {v: k for k, v in CORRESPONDANCE_ECHELLE.items()})


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_piecejointe"),
    ]

    operations = [
        migrations.AlterField(
            model_name="risque",
            name="frequence",
            field=models.IntegerField(choices=[(1, "1 - Rare"), (4, "4 - Occasionnelle"), (7, "7 - Fréquente"), (10, "10 - Permanente")], default=1, verbose_name="Fréquence"),
        ),
        migrations.AlterField(
            model_name="risque",
            name="gravite",
            field=models.IntegerField(choices=[(1, "1 - Bénigne (sans arrêt de travail)"), (4, "4 - Moyenne (avec arrêt de travail)"), (7, "7 - Grave (incapacité permanente partielle)"), (10, "10 - Très grave (mortelle ou invalidante)")], default=1, verbose_name="Gravité"),
        ),
        migrations.RunPython(remapper_gravite_et_frequence, revenir_a_lancienne_echelle),
        migrations.AddField(
            model_name="risque",
            name="maitrise",
            field=models.IntegerField(choices=[(1, "1 - Maîtrisé (mesures en place et efficaces)"), (4, "4 - Moyennement maîtrisé"), (7, "7 - Peu maîtrisé (mesures insuffisantes)"), (10, "10 - Non maîtrisé (aucune mesure)")], default=10, help_text="Note l'absence de maîtrise du risque : 1 = bien maîtrisé, 10 = non maîtrisé.", verbose_name="Maîtrise"),
        ),
    ]
