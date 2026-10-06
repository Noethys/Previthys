#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

"""Vérifications automatiques de critères RGAA 4.1 sur les pages de l'application.

Ces tests ne remplacent pas un audit (lecteur d'écran, navigation au clavier, contrastes en situation), mais
empêchent les régressions sur les points vérifiables dans le code HTML."""

from collections import Counter
from html.parser import HTMLParser

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import Risque


class Analyse(HTMLParser):
    """Relève dans une page les identifiants, les champs de formulaire et leurs libellés."""

    CHAMPS = {"input", "select", "textarea"}
    SANS_LIBELLE = {"hidden", "submit", "button", "reset", "image"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = Counter()
        self.libelles_pour = set()
        self.champs = []          # (balise, attributs) des champs qui doivent avoir un libellé
        self.dans_label = 0
        self.images_sans_alt = []
        self.titres = []
        self.balise_titre = None
        self.lang = None

    def handle_starttag(self, balise, attrs):
        a = dict(attrs)
        if balise == "html":
            self.lang = a.get("lang")
        if a.get("id"):
            self.ids[a["id"]] += 1
        if balise == "label":
            self.dans_label += 1
            if a.get("for"):
                self.libelles_pour.add(a["for"])
        if balise in self.CHAMPS and a.get("type", "") not in self.SANS_LIBELLE:
            self.champs.append((balise, a, self.dans_label > 0))
        if balise == "img" and "alt" not in a:
            self.images_sans_alt.append(a.get("src", ""))
        if balise in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.titres.append(int(balise[1]))

    def handle_endtag(self, balise):
        if balise == "label":
            self.dans_label -= 1


def analyser(html):
    a = Analyse()
    a.feed(html)
    return a


class AccessibiliteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("creer_groupes", verbosity=0)
        call_command("charger_exemple", verbosity=0)
        cls.admin = User.objects.create_superuser("admin", "a@a.fr", "motdepasse-Tres-Long-1")

    def setUp(self):
        self.client.force_login(self.admin)

    def pages(self):
        risque = Risque.objects.first()
        return ["dashboard", "unites_liste", "unites_ajouter", "categories_liste", "risques_liste", "risques_ajouter",
                ("risques_modifier", risque.pk), "actions_liste", "actions_ajouter", "categories_actions_liste",
                "document", "introduction", "versions_liste", "versions_ajouter", "journal_liste", "aide", "accessibilite", "mentions_legales"]

    def html(self, page):
        url = reverse(page[0], args=page[1:]) if isinstance(page, tuple) else reverse(page)
        rep = self.client.get(url)
        self.assertEqual(rep.status_code, 200, url)
        return url, rep.content.decode()

    def test_structure_commune_des_pages(self):
        """Langue (8.3), titre (8.5), liens d'évitement (12.7), zones principales (12.6), lien vers la déclaration."""
        for page in self.pages():
            url, html = self.html(page)
            with self.subTest(url=url):
                a = analyser(html)
                self.assertEqual(a.lang, "fr")
                self.assertIn('<a href="#contenu">Aller au contenu</a>', html)
                self.assertIn('id="contenu"', html)
                self.assertIn("<header", html)
                self.assertIn('<footer class="pied-page', html)
                self.assertIn('href="%s"' % reverse("accessibilite"), html)
                self.assertIn("Accessibilité : non conforme (audit en cours)", html)
                self.assertEqual(a.titres.count(1), 1, "une seule balise h1 par page")

    def test_identifiants_uniques(self):
        """Code valide (8.2) : aucun identifiant en double, sinon les libellés et les liens d'évitement se trompent de cible."""
        for page in self.pages():
            url, html = self.html(page)
            with self.subTest(url=url):
                doublons = [i for i, n in analyser(html).ids.items() if n > 1]
                self.assertEqual(doublons, [])

    def test_chaque_champ_a_un_libelle(self):
        """Formulaires (11.1) : chaque champ a une étiquette (label, aria-label ou aria-labelledby)."""
        for page in self.pages():
            url, html = self.html(page)
            with self.subTest(url=url):
                a = analyser(html)
                for balise, attrs, dans_label in a.champs:
                    etiquete = dans_label or attrs.get("id") in a.libelles_pour or attrs.get("aria-label") or attrs.get("aria-labelledby")
                    self.assertTrue(etiquete, "%s sans libellé : %s" % (balise, attrs))

    def test_images_avec_alternative(self):
        """Images (1.1) : chaque image a un attribut alt, vide si elle est décorative."""
        for page in self.pages():
            url, html = self.html(page)
            with self.subTest(url=url):
                self.assertEqual(analyser(html).images_sans_alt, [])

    def test_page_en_cours_dans_le_menu(self):
        html = self.html("risques_liste")[1]
        self.assertIn('<a class="dropdown-item" aria-current="page" href="%s">Risques</a>' % reverse("risques_liste"), html)
        self.assertNotIn('aria-current="page" href="%s"' % reverse("unites_liste"), html)

    def test_erreurs_de_saisie_reliees_aux_champs(self):
        """Erreurs (11.10, 11.11) : récapitulatif, champ marqué invalide et relié à son message d'erreur."""
        rep = self.client.post(reverse("unites_ajouter"), {"nom": "", "effectif": "abc"})
        html = rep.content.decode()
        self.assertIn('id="erreurs-formulaire"', html)
        self.assertIn('href="#id_nom"', html)
        self.assertIn('aria-invalid="true"', html)
        self.assertIn('aria-describedby="id_nom_erreur"', html)
        self.assertIn('id="id_nom_erreur"', html)
        self.assertIn("Les champs marqués d'un astérisque", html)

    def test_aide_des_champs_reliee(self):
        html = self.html(("risques_modifier", Risque.objects.first().pk))[1]
        self.assertRegex(html, r'aria-describedby="id_[a-z_]+_aide"')

    def test_liens_explicites_dans_les_listes(self):
        """Liens (6.1) : « Modifier » et « Supprimer » sont complétés par le nom de l'élément."""
        html = self.html("unites_liste")[1]
        self.assertRegex(html, r'Modifier<span class="visually-hidden"> [^<]+</span>')

    def test_tableaux_de_donnees(self):
        """Tableaux (5.6, 5.7) : en-têtes déclarés avec leur portée dans la matrice du tableau de bord."""
        html = self.html("dashboard")[1]
        self.assertIn('<th scope="row"', html)
        self.assertIn('<th scope="col"', html)
        self.assertIn("<caption", html)

    def test_regroupement_des_boutons_radio(self):
        """Formulaires (11.5) : les choix de portée d'une action sont regroupés dans un fieldset avec une légende."""
        html = self.html("actions_ajouter")[1]
        self.assertIn("<fieldset", html)
        self.assertIn("<legend", html)


class DeclarationAccessibiliteTests(TestCase):
    def test_page_publique(self):
        """La déclaration doit être consultable sans être connecté, comme le lien sur la page de connexion."""
        rep = self.client.get(reverse("accessibilite"))
        self.assertContains(rep, "Déclaration d'accessibilité")
        self.assertContains(rep, "non conforme (audit en cours)")
        self.assertContains(rep, "Défenseur des droits")
        self.assertContains(self.client.get(reverse("login")), 'href="%s"' % reverse("accessibilite"))

    @override_settings(PREVITHYS_ACCESSIBILITE={"etat": "non", "audit_en_cours": False})
    def test_sans_audit_en_cours(self):
        self.assertContains(self.client.get(reverse("login")), "Accessibilité : non conforme</a>")

    @override_settings(PREVITHYS_ACCESSIBILITE={"etat": "partiellement", "taux": "82 %", "date_audit": "mars 2027",
                                                "auditeur": "Société X", "contact": "accessibilite@mairie.fr", "date_declaration": "1er avril 2027"})
    def test_declaration_completee(self):
        rep = self.client.get(reverse("accessibilite"))
        self.assertContains(rep, "partiellement conforme")
        self.assertContains(rep, "82 %")
        self.assertContains(rep, "Société X")
        self.assertContains(rep, 'href="mailto:accessibilite@mairie.fr"')
        self.assertContains(self.client.get(reverse("login")), "Accessibilité : partiellement conforme")
