#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

"""Introduction du document unique (texte de présentation et logo), archivée avec chaque version.
Les droits sur ce modèle sont ajoutés aux groupes Previthys existants."""

import django.db.models.deletion
from django.contrib.auth.management import create_permissions
from django.db import migrations, models

GROUPES = {"Previthys - lecture": ["view"], "Previthys - rédacteur": ["view", "add", "change"],
           "Previthys - administrateur": ["view", "add", "change", "delete"]}


def droits_des_groupes(apps, schema_editor):
    config = apps.get_app_config("core")
    config.models_module = True
    create_permissions(config, apps=apps, verbosity=0)
    Group, Permission = apps.get_model("auth", "Group"), apps.get_model("auth", "Permission")
    for nom, actions in GROUPES.items():
        groupe = Group.objects.filter(name=nom).first()
        if groupe:
            groupe.permissions.add(*Permission.objects.filter(content_type__app_label="core",
                                                              codename__in=["%s_introduction" % a for a in actions]))


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("core", "0012_risque_date_evaluation"),
    ]

    operations = [
        migrations.CreateModel(
            name="Introduction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("texte", models.TextField(blank=True, verbose_name="Texte de présentation")),
                ("logo", models.TextField(blank=True, help_text="Image au format data:… (PNG ou JPEG), affichée sur la page de garde.", verbose_name="Logo")),
                ("modifie_le", models.DateTimeField(auto_now=True, verbose_name="Modifiée le")),
                ("structure", models.OneToOneField(blank=True, help_text="Laissez vide pour l'introduction par défaut (toutes les structures).", null=True,
                                                   on_delete=django.db.models.deletion.CASCADE, to="core.structure", verbose_name="Structure")),
            ],
            options={"verbose_name": "introduction du document", "verbose_name_plural": "introductions du document"},
        ),
        migrations.AddField(
            model_name="versionduerp", name="introduction",
            field=models.JSONField(blank=True, default=dict, verbose_name="Introduction archivée"),
        ),
        migrations.RunPython(droits_des_groupes, migrations.RunPython.noop),
    ]
