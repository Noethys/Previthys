"""Équivalent en ligne de commande de la page « Mise à jour de l'application » (utile en cron ou par script)."""
#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand

from core.utils.update import Update


class Command(BaseCommand):
    help = "Vérifie et installe une nouvelle version de l'application si disponible."

    def handle(self, *args, **options):
        if Update():
            self.stdout.write(self.style.SUCCESS("Mise à jour effectuée avec succès."))
        else:
            self.stdout.write("Aucune mise à jour effectuée (déjà à jour, ou non configurée — voir les journaux).")
