#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.test import TestCase, override_settings
from django.urls import reverse


class MentionsLegalesTests(TestCase):
    def test_page_publique_et_liens(self):
        rep = self.client.get(reverse("mentions_legales"))
        self.assertContains(rep, "<h1 class=\"h4\">Mentions légales</h1>", html=False)
        self.assertContains(rep, "Non renseigné")   # valeurs par défaut tant que la structure n'a rien saisi
        self.assertContains(rep, "sessionid")
        self.assertContains(rep, "CNIL")
        self.assertContains(self.client.get(reverse("login")), 'href="%s"' % reverse("mentions_legales"))

    @override_settings(PREVITHYS_ORGANISATION="Mairie de Test", PREVITHYS_MENTIONS_LEGALES={
        "editeur": "", "adresse": "1 place de la Mairie\n29000 Test", "telephone": "02 98 00 00 00", "courriel": "mairie@test.fr",
        "siret": "21290000000000", "directeur_publication": "Mme Martin, maire", "hebergeur": "OVH",
        "hebergeur_adresse": "2 rue Kellermann, 59100 Roubaix", "hebergeur_telephone": "", "dpo": "dpo@test.fr"})
    def test_mentions_completees(self):
        rep = self.client.get(reverse("mentions_legales"))
        self.assertContains(rep, "Mairie de Test")          # éditeur par défaut : PREVITHYS_ORGANISATION
        self.assertContains(rep, "1 place de la Mairie<br>29000 Test")
        self.assertContains(rep, "Mme Martin, maire")
        self.assertContains(rep, "OVH")
        self.assertContains(rep, 'href="mailto:dpo@test.fr"')
        self.assertNotContains(rep, "Non renseigné")
