#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

"""Responsable d'une action : texte libre au lieu d'un utilisateur de l'application.

Les responsables déjà saisis sont conservés sous forme de texte (nom complet, à défaut identifiant).
Retour arrière : le texte est rapproché d'un utilisateur (nom complet ou identifiant) ; sans correspondance, il est perdu.
"""

from django.conf import settings
from django.db import migrations, models


def nom(utilisateur):
    complet = ("%s %s" % (utilisateur.first_name, utilisateur.last_name)).strip()
    return complet or utilisateur.username


def vers_texte(apps, schema_editor):
    Action = apps.get_model("core", "ActionPrevention")
    for action in Action.objects.exclude(responsable=None).select_related("responsable"):
        action.responsable_nom = nom(action.responsable)[:150]
        action.save(update_fields=["responsable_nom"])


def vers_utilisateur(apps, schema_editor):
    Action = apps.get_model("core", "ActionPrevention")
    utilisateurs = {}
    for u in apps.get_model(settings.AUTH_USER_MODEL).objects.all():
        utilisateurs.setdefault(nom(u), u)
        utilisateurs.setdefault(u.username, u)
    for action in Action.objects.exclude(responsable_nom=""):
        action.responsable = utilisateurs.get(action.responsable_nom)
        action.save(update_fields=["responsable"])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0010_categories_actions"),
    ]

    operations = [
        migrations.AddField(
            model_name="actionprevention", name="responsable_nom",
            field=models.CharField(blank=True, max_length=150, verbose_name="Responsable"),
        ),
        migrations.RunPython(vers_texte, vers_utilisateur),
        migrations.RemoveField(model_name="actionprevention", name="responsable"),
        migrations.RenameField(model_name="actionprevention", old_name="responsable_nom", new_name="responsable"),
        migrations.AlterField(
            model_name="actionprevention", name="responsable",
            field=models.CharField(blank=True, help_text="Personne ou service qui pilote l'action (texte libre).", max_length=150, verbose_name="Responsable"),
        ),
    ]
