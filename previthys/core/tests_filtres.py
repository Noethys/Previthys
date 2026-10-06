"""Mémorisation en session des filtres des listes « Risques » et « Plan d'actions »."""
#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.models import CategorieRisque, Risque, UniteTravail

User = get_user_model()


class MemorisationFiltresTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("creer_groupes", verbosity=0)
        cls.root = User.objects.create_superuser("root", password="x")
        cls.unite = UniteTravail.objects.create(nom="Voirie")
        cls.risque = Risque.objects.create(unite=cls.unite, categorie=CategorieRisque.objects.get(nom="Autre"),
                                           danger="Chute", frequence=4, gravite=4, maitrise=4)

    def setUp(self):
        self.client.force_login(self.root)
        self.url = reverse("risques_liste")

    def test_filtre_restaure_apres_retour_sans_parametre(self):
        self.client.get(self.url, {"unite": self.unite.pk, "niveau": "moyen"})
        rep = self.client.get(self.url)
        self.assertEqual(rep.status_code, 302)
        self.assertIn("unite=%d" % self.unite.pk, rep["Location"])
        self.assertIn("niveau=moyen", rep["Location"])

    def test_retour_apres_modification_restaure_les_filtres(self):
        self.client.get(self.url, {"niveau": "moyen"})
        rep = self.client.post(reverse("risques_modifier", args=[self.risque.pk]), {
            "unite": self.unite.pk, "categorie": self.risque.categorie_id, "danger": "Chute", "frequence": 4, "gravite": 4, "maitrise": 4})
        rep = self.client.get(rep["Location"])
        self.assertRedirects(rep, self.url + "?niveau=moyen", fetch_redirect_response=False)

    def test_toutes_les_listes_videes_efface_la_memoire(self):
        self.client.get(self.url, {"niveau": "moyen"})
        self.client.get(self.url, {"unite": "", "categorie": "", "niveau": ""})
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_reinitialiser(self):
        self.client.get(self.url, {"niveau": "moyen"})
        self.assertContains(self.client.get(self.url, {"niveau": "moyen"}), "Réinitialiser les filtres")
        self.assertRedirects(self.client.get(self.url, {"raz": "1"}), self.url, fetch_redirect_response=False)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_filtres_propres_a_chaque_liste(self):
        self.client.get(self.url, {"niveau": "moyen"})
        self.assertEqual(self.client.get(reverse("actions_liste")).status_code, 200)

    def test_plan_actions_memorise(self):
        url = reverse("actions_liste")
        self.client.get(url, {"portee": "generales"})
        rep = self.client.get(url)
        self.assertRedirects(rep, url + "?portee=generales", fetch_redirect_response=False)
