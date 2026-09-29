#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

"""Date de dernière évaluation d'un risque : sert à repérer les risques à réévaluer après une action terminée.
Vide pour les risques existants (date inconnue) ; renseignée au prochain enregistrement de leur fiche."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_responsable_texte_libre"),
    ]

    operations = [
        migrations.AddField(
            model_name="risque", name="date_evaluation",
            field=models.DateField(blank=True, null=True, verbose_name="Dernière évaluation",
                                   help_text="Mise à jour à chaque enregistrement de la fiche du risque (cotation revue)."),
        ),
    ]
