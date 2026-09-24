#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.db import migrations

CATEGORIES = [
    "Chutes et manutentions", "Postures et TMS", "Produits chimiques", "Risques biologiques", "Risque électrique",
    "Incendie et explosion", "Risque routier", "Bruit et vibrations", "Risques psychosociaux",
    "Agressions et incivilités", "Autre",
]


def creer_categories(apps, schema_editor):
    Categorie = apps.get_model("core", "CategorieRisque")
    for ordre, nom in enumerate(CATEGORIES, 1):
        Categorie.objects.get_or_create(nom=nom, defaults={"ordre": ordre})


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [migrations.RunPython(creer_categories, migrations.RunPython.noop)]
