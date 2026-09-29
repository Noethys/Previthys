#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

"""Actions de prévention liées à zéro, un ou plusieurs risques (actions générales et actions communes).

Le lien unique action → risque (clé étrangère « risque ») devient un lien plusieurs-à-plusieurs « risques ».
Chaque action existante garde son risque. Une structure (facultative) est ajoutée aux actions, et les versions
archivées reçoivent un champ pour les mesures générales.

Retour arrière possible : chaque action reprend son premier risque ; les actions générales (sans risque), qui ne
peuvent pas exister dans l'ancien modèle, sont alors supprimées.
"""

import django.db.models.deletion
from django.db import migrations, models


def vers_plusieurs_risques(apps, schema_editor):
    Action = apps.get_model("core", "ActionPrevention")
    for action in Action.objects.select_related("risque__unite"):
        if action.risque_id:
            action.risques.add(action.risque_id)
            action.structure_id = action.risque.unite.structure_id
            action.save(update_fields=["structure"])


def vers_risque_unique(apps, schema_editor):
    Action = apps.get_model("core", "ActionPrevention")
    for action in Action.objects.all():
        premier = action.risques.order_by("pk").first()
        if premier is None:
            action.delete()
        else:
            action.risque_id = premier.pk
            action.save(update_fields=["risque"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_action_duree_cout"),
    ]

    operations = [
        migrations.AlterField(
            model_name="actionprevention", name="risque",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="actions", to="core.risque", verbose_name="Risque"),
        ),
        migrations.AddField(
            model_name="actionprevention", name="structure",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="core.structure", verbose_name="Structure",
                                    help_text="Pour une action générale : structure concernée (vide = toutes). Pour les autres actions, déduite des unités des risques."),
        ),
        migrations.AddField(
            model_name="actionprevention", name="risques",
            field=models.ManyToManyField(blank=True, related_name="actions_multiples", to="core.risque", verbose_name="Risques concernés"),
        ),
        migrations.RunPython(vers_plusieurs_risques, vers_risque_unique),
        migrations.RemoveField(model_name="actionprevention", name="risque"),
        migrations.AlterField(
            model_name="actionprevention", name="risques",
            field=models.ManyToManyField(blank=True, related_name="actions", to="core.risque", verbose_name="Risques concernés"),
        ),
        migrations.AddField(
            model_name="versionduerp", name="mesures_generales",
            field=models.JSONField(blank=True, default=list, verbose_name="Mesures générales archivées"),
        ),
    ]
