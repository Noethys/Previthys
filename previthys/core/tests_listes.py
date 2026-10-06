#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

"""Colonne « Actions » des listes selon les droits de l'utilisateur."""

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

COLONNE = '<th scope="col" data-name="actions"'


class ColonneActionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("creer_groupes", verbosity=0)
        call_command("charger_exemple", verbosity=0)
        cls.admin = User.objects.create_superuser("admin", "a@a.fr", "motdepasse-Tres-Long-1")
        cls.lecteur = User.objects.create_user("lecteur", password="motdepasse-Tres-Long-1")
        cls.lecteur.groups.add(Group.objects.get(name="Previthys - lecture"))

    def test_lecteur_sans_colonne_actions(self):
        self.client.force_login(self.lecteur)
        for nom in ("risques_liste", "actions_liste", "unites_liste", "categories_liste"):
            rep = self.client.get(reverse(nom))
            self.assertEqual(rep.status_code, 200, nom)
            self.assertNotContains(rep, COLONNE, msg_prefix=nom)
            self.assertNotContains(rep, ">Modifier<", msg_prefix=nom)

    def test_lecteur_garde_les_actions_de_consultation(self):
        """Les versions archivées restent consultables et exportables : la colonne est conservée, sans « Supprimer »."""
        self.client.force_login(self.admin)
        self.client.post(reverse("versions_ajouter"), {"commentaire": "Mise à jour annuelle"})
        self.client.force_login(self.lecteur)
        rep = self.client.get(reverse("versions_liste"))
        self.assertContains(rep, COLONNE)
        self.assertContains(rep, ">Consulter<")
        self.assertNotContains(rep, ">Supprimer<")

    def test_administrateur_garde_la_colonne(self):
        self.client.force_login(self.admin)
        for nom in ("risques_liste", "actions_liste", "unites_liste"):
            self.assertContains(self.client.get(reverse(nom)), COLONNE, msg_prefix=nom)
