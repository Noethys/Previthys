#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

MODELES = ["structure", "unitetravail", "categorierisque", "risque", "actionprevention", "versionduerp", "journalaudit"]

GROUPES = {
    "Previthys - lecture": ["view"],
    "Previthys - rédacteur": ["view", "add", "change"],
    "Previthys - administrateur": ["view", "add", "change", "delete"],
}


class Command(BaseCommand):
    help = "Crée (ou met à jour) les groupes de droits DUERP : lecture, rédacteur, administrateur."

    def handle(self, *args, **options):
        for nom, actions in GROUPES.items():
            groupe, _ = Group.objects.get_or_create(name=nom)
            # Les versions archivées (conservation obligatoire 40 ans) ne sont supprimables que par un super-utilisateur.
            # Le journal des modifications n'est jamais ajoutable, modifiable ni supprimable par un groupe DUERP,
            # même administrateur : seule sa consultation (view) peut être accordée (voir core/admin.py pour /admin/).
            codes = ["%s_%s" % (a, m) for a in actions for m in MODELES
                     if not (a == "delete" and m == "versionduerp") and not (a != "view" and m == "journalaudit")]
            groupe.permissions.set(Permission.objects.filter(content_type__app_label="core", codename__in=codes))
            if options["verbosity"] > 0:
                self.stdout.write("Groupe « %s » : %d permissions" % (nom, groupe.permissions.count()))
