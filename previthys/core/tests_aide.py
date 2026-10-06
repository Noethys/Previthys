#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

import re

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.templatetags.aide import rubrique_aide


class AideTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin", "a@a.fr", "motdepasse-Tres-Long-1")

    def test_connexion_obligatoire(self):
        rep = self.client.get(reverse("aide"))
        self.assertEqual(rep.status_code, 302)
        self.assertIn(reverse("login"), rep["Location"])

    def test_page_d_aide_et_lien_dans_le_menu(self):
        self.client.force_login(self.admin)
        rep = self.client.get(reverse("aide"))
        self.assertContains(rep, "Aide de Previthys")
        self.assertContains(rep, 'href="%s">Aide</a>' % reverse("aide"))
        self.assertContains(rep, "343 à 1 000")   # seuils réels, calculés depuis models.py

    def test_toutes_les_rubriques_existent(self):
        """Chaque ancre utilisée par l'aide contextuelle et par le sommaire correspond à une section de la page."""
        self.client.force_login(self.admin)
        html = self.client.get(reverse("aide")).content.decode()
        sections = set(re.findall(r'<section id="([^"]+)"', html))
        liens = set(re.findall(r'href="#([^"]+)"', html))
        liens -= {"contenu", "menu-principal"}   # liens d'évitement, communs à toutes les pages
        from core.templatetags.aide import RUBRIQUES
        self.assertTrue(liens <= sections, liens - sections)
        self.assertTrue({a for _, a in RUBRIQUES} <= sections)

    def test_rubrique_selon_la_page(self):
        self.assertEqual(rubrique_aide("categories_actions_liste"), "categories-actions")
        self.assertEqual(rubrique_aide("categories_ajouter"), "categories-risques")
        self.assertEqual(rubrique_aide("risques_actions_ajouter"), "actions-depuis-risque")
        self.assertEqual(rubrique_aide("risques_modifier"), "risques")
        self.assertEqual(rubrique_aide("introduction"), "parametres-document")
        self.assertEqual(rubrique_aide("login"), "")

    def test_bouton_aide_contextuel(self):
        self.client.force_login(self.admin)
        for nom, ancre in (("dashboard", "vue-ensemble"), ("risques_liste", "risques"), ("actions_ajouter", "plan-actions"),
                           ("document", "document"), ("versions_liste", "versions")):
            self.assertContains(self.client.get(reverse(nom)), 'href="%s#%s"' % (reverse("aide"), ancre), msg_prefix=nom)
