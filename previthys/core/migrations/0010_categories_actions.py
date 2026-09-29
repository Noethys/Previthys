#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

"""Catégories d'actions de prévention (formation, matériel, organisation...), avec une liste par défaut.

Les droits sur ce nouveau modèle sont aussitôt ajoutés aux groupes Previthys existants (lecture, rédacteur,
administrateur), comme le ferait `python manage.py creer_groupes`.
"""

import django.db.models.deletion
from django.contrib.auth.management import create_permissions
from django.db import migrations, models

CATEGORIES = [
    ("Formation", "Formations, habilitations, sensibilisations des agents."),
    ("Matériel", "Achat ou renouvellement de matériel et d'équipements de protection (EPI)."),
    ("Organisation", "Organisation du travail, procédures, consignes, répartition des tâches."),
    ("Travaux", "Travaux et aménagements des locaux ou des sites."),
    ("Communication", "Information des agents, affichage, communication interne ou externe."),
    ("Autre", ""),
]
GROUPES = {"Previthys - lecture": ["view"], "Previthys - rédacteur": ["view", "add", "change"],
           "Previthys - administrateur": ["view", "add", "change", "delete"]}


def creer_categories(apps, schema_editor):
    Categorie = apps.get_model("core", "CategorieAction")
    for ordre, (nom, description) in enumerate(CATEGORIES, 1):
        Categorie.objects.get_or_create(nom=nom, defaults={"description": description, "ordre": ordre * 10})


def droits_des_groupes(apps, schema_editor):
    config = apps.get_app_config("core")
    config.models_module = True
    create_permissions(config, apps=apps, verbosity=0)   # les permissions ne sont sinon créées qu'après la migration
    Group, Permission = apps.get_model("auth", "Group"), apps.get_model("auth", "Permission")
    for nom, actions in GROUPES.items():
        groupe = Group.objects.filter(name=nom).first()
        if groupe:
            groupe.permissions.add(*Permission.objects.filter(content_type__app_label="core",
                                                              codename__in=["%s_categorieaction" % a for a in actions]))


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("core", "0009_actions_multi_risques"),
    ]

    operations = [
        migrations.CreateModel(
            name="CategorieAction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nom", models.CharField(error_messages={"unique": "Cette catégorie existe déjà."}, max_length=100, unique=True, verbose_name="Nom")),
                ("description", models.TextField(blank=True, verbose_name="Description")),
                ("ordre", models.IntegerField(default=0, verbose_name="Ordre d'affichage")),
            ],
            options={"verbose_name": "catégorie d'action", "verbose_name_plural": "catégories d'actions", "ordering": ["ordre", "nom"]},
        ),
        migrations.AddField(
            model_name="actionprevention", name="categorie",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="actions",
                                    to="core.categorieaction", verbose_name="Catégorie"),
        ),
        migrations.RunPython(creer_categories, migrations.RunPython.noop),
        migrations.RunPython(droits_des_groupes, migrations.RunPython.noop),
    ]
