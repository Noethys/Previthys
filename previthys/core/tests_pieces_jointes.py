"""Tests des pièces jointes des risques : validation des fichiers, contrôle d'accès, téléchargement, suppression."""
#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

import os

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import CategorieRisque, PieceJointe, Risque, Structure, UniteTravail
from core.utils.fichiers import NOMBRE_MAX_FICHIERS, TAILLE_MAX_OCTETS, valider_fichier

User = get_user_model()

PNG_1PX = bytes.fromhex("89504E470D0A1A0A0000000D49484452000000010000000108020000009077"
                          "53DE0000000C4944415408D763F8CFC0C0C0000004010001F09E48A80000000049454E44AE426082")
PDF_MINI = b"%PDF-1.4\n%%EOF"


def img(nom="photo.png", contenu=None):
    return SimpleUploadedFile(nom, contenu or PNG_1PX, content_type="image/png")


def pdf(nom="fiche.pdf", contenu=None):
    return SimpleUploadedFile(nom, contenu or PDF_MINI, content_type="application/pdf")


@override_settings(MEDIA_ROOT="/tmp/duerp_test_media")
class BaseFichiers(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("root", password="x")
        cls.categorie = CategorieRisque.objects.get(nom="Autre")
        cls.unite = UniteTravail.objects.create(nom="Services techniques")
        cls.risque = Risque.objects.create(unite=cls.unite, categorie=cls.categorie, danger="Chute", frequence=4, gravite=4, maitrise=4)

    def tearDown(self):
        for piece in PieceJointe.objects.all():
            piece.fichier.delete(save=False)


class ValidationTests(BaseFichiers):
    def test_extension_interdite(self):
        with self.assertRaises(Exception):
            valider_fichier(SimpleUploadedFile("virus.exe", b"MZ...", content_type="application/octet-stream"))

    def test_signature_ne_correspond_pas_a_l_extension(self):
        """Un exécutable renommé en .jpg doit être détecté malgré l'extension correcte."""
        faux = SimpleUploadedFile("photo.jpg", b"MZ\x90\x00\x03\x00\x00\x00faux contenu", content_type="image/jpeg")
        with self.assertRaisesMessage(Exception, "ne correspond pas à son extension"):
            valider_fichier(faux)

    def test_fichier_trop_volumineux_refuse(self):
        gros = SimpleUploadedFile("photo.png", PNG_1PX[:8] + b"\x00" * (TAILLE_MAX_OCTETS + 1), content_type="image/png")
        with self.assertRaisesMessage(Exception, "dépasse la taille maximale"):
            valider_fichier(gros)

    def test_fichier_vide_refuse(self):
        with self.assertRaisesMessage(Exception, "vide"):
            valider_fichier(SimpleUploadedFile("photo.png", b"", content_type="image/png"))

    def test_pdf_et_image_valides_acceptes(self):
        valider_fichier(img())
        valider_fichier(pdf())

    def test_svg_refuse(self):
        """Le SVG peut contenir du script exécuté par le navigateur : jamais accepté."""
        svg = SimpleUploadedFile("dessin.svg", b"<svg onload='alert(1)'></svg>", content_type="image/svg+xml")
        with self.assertRaises(Exception):
            valider_fichier(svg)


class FormulaireEtVueTests(BaseFichiers):
    def setUp(self):
        self.client.force_login(self.admin)

    def test_ajout_risque_avec_plusieurs_fichiers(self):
        r = self.client.post(reverse("risques_ajouter"), {
            "unite": self.unite.pk, "categorie": self.categorie.pk, "danger": "Nouveau risque", "frequence": 1, "gravite": 1, "maitrise": 1,
            "pieces_jointes": [img("photo1.png"), img("photo2.png"), pdf("fiche.pdf")],
        })
        risque = Risque.objects.get(danger="Nouveau risque")
        self.assertRedirects(r, reverse("risques_liste"))
        self.assertEqual(risque.pieces_jointes.count(), 3)
        self.assertEqual(set(risque.pieces_jointes.values_list("nom_original", flat=True)), {"photo1.png", "photo2.png", "fiche.pdf"})
        self.assertTrue(all(p.ajoute_par_id == self.admin.pk for p in risque.pieces_jointes.all()))

    def test_ajout_fichier_invalide_naffiche_pas_le_risque(self):
        exe = SimpleUploadedFile("virus.exe", b"MZ", content_type="application/octet-stream")
        r = self.client.post(reverse("risques_ajouter"), {
            "unite": self.unite.pk, "categorie": self.categorie.pk, "danger": "Refuse", "frequence": 1, "gravite": 1, "maitrise": 1, "pieces_jointes": [exe],
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "type de fichier non autorisé")
        self.assertFalse(Risque.objects.filter(danger="Refuse").exists())

    def test_plus_de_dix_fichiers_refuse(self):
        fichiers = [img("photo%d.png" % i) for i in range(NOMBRE_MAX_FICHIERS + 1)]
        r = self.client.post(reverse("risques_ajouter"), {
            "unite": self.unite.pk, "categorie": self.categorie.pk, "danger": "Trop", "frequence": 1, "gravite": 1, "maitrise": 1, "pieces_jointes": fichiers,
        })
        self.assertContains(r, "plus de %d fichiers" % NOMBRE_MAX_FICHIERS)
        self.assertFalse(Risque.objects.filter(danger="Trop").exists())

    def test_ajout_de_fichiers_lors_de_la_modification(self):
        self.client.post(reverse("risques_modifier", args=[self.risque.pk]), {
            "unite": self.unite.pk, "categorie": self.categorie.pk, "danger": self.risque.danger, "frequence": 4, "gravite": 4, "maitrise": 4, "pieces_jointes": [pdf()],
        })
        self.assertEqual(self.risque.pieces_jointes.count(), 1)

    def test_modification_sans_nouveau_fichier_ne_touche_pas_les_existants(self):
        PieceJointe.objects.create(risque=self.risque, fichier=img(), nom_original="a.png", taille=10)
        self.client.post(reverse("risques_modifier", args=[self.risque.pk]), {
            "unite": self.unite.pk, "categorie": self.categorie.pk, "danger": self.risque.danger, "frequence": 7, "gravite": 7, "maitrise": 7,
        })
        self.assertEqual(self.risque.pieces_jointes.count(), 1)

    def test_page_modification_liste_les_pieces_jointes(self):
        PieceJointe.objects.create(risque=self.risque, fichier=img(), nom_original="photo.png", taille=10, ajoute_par=self.admin)
        r = self.client.get(reverse("risques_modifier", args=[self.risque.pk]))
        self.assertContains(r, "photo.png")

    def test_liste_des_risques_affiche_le_nombre_de_fichiers(self):
        PieceJointe.objects.create(risque=self.risque, fichier=img(), nom_original="a.png", taille=10)
        PieceJointe.objects.create(risque=self.risque, fichier=img(), nom_original="b.png", taille=10)
        r = self.client.get(reverse("risques_liste"))
        self.assertIn('data-name="fichiers"', r.content.decode())


class TelechargementTests(BaseFichiers):
    def setUp(self):
        self.piece = PieceJointe.objects.create(risque=self.risque, fichier=img(), nom_original="photo.png", taille=len(PNG_1PX), ajoute_par=self.admin)
        self.doc = PieceJointe.objects.create(risque=self.risque, fichier=pdf(), nom_original="fiche.pdf", taille=len(PDF_MINI), ajoute_par=self.admin)

    def test_anonyme_refuse(self):
        self.assertEqual(self.client.get(reverse("pieces_jointes_telecharger", args=[self.piece.pk])).status_code, 302)

    def test_telechargement_image_en_ligne_et_document_en_piece_jointe(self):
        self.client.force_login(self.admin)
        r_image = self.client.get(reverse("pieces_jointes_telecharger", args=[self.piece.pk]))
        self.assertEqual(r_image.status_code, 200)
        self.assertEqual(r_image["Content-Type"], "image/png")
        self.assertNotIn("attachment", r_image.get("Content-Disposition", ""))
        r_doc = self.client.get(reverse("pieces_jointes_telecharger", args=[self.doc.pk]))
        self.assertEqual(r_doc["Content-Type"], "application/pdf")
        self.assertIn("attachment", r_doc["Content-Disposition"])
        self.assertIn("fiche.pdf", r_doc["Content-Disposition"])

    def test_type_mime_ne_depend_pas_du_type_enregistre_par_le_navigateur(self):
        """Le type MIME servi vient de l'extension du nom d'origine, jamais du champ content_type envoyé à l'upload."""
        self.client.force_login(self.admin)
        r = self.client.get(reverse("pieces_jointes_telecharger", args=[self.piece.pk]))
        self.assertEqual(r["Content-Type"], "image/png")

    def test_suppression_par_get_refusee(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("pieces_jointes_supprimer", args=[self.piece.pk])).status_code, 405)
        self.assertTrue(PieceJointe.objects.filter(pk=self.piece.pk).exists())

    def test_suppression_par_post_efface_le_fichier_physique(self):
        self.client.force_login(self.admin)
        chemin_disque = self.piece.fichier.path
        self.assertTrue(os.path.exists(chemin_disque))
        r = self.client.post(reverse("pieces_jointes_supprimer", args=[self.piece.pk]))
        self.assertRedirects(r, reverse("risques_modifier", args=[self.risque.pk]))
        self.assertFalse(PieceJointe.objects.filter(pk=self.piece.pk).exists())
        self.assertFalse(os.path.exists(chemin_disque))

    def test_csrf_obligatoire_pour_la_suppression(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.admin)
        self.assertEqual(c.post(reverse("pieces_jointes_supprimer", args=[self.piece.pk])).status_code, 403)
        self.assertTrue(PieceJointe.objects.filter(pk=self.piece.pk).exists())


class IsolationStructureTests(BaseFichiers):
    """Un utilisateur limité à une structure ne doit ni voir, ni télécharger, ni supprimer les fichiers d'une autre."""

    def setUp(self):
        from django.contrib.auth.models import Group
        from django.core.management import call_command
        call_command("creer_groupes", verbosity=0)
        self.struct_a = Structure.objects.create(nom="Mairie A")
        self.unite_a = UniteTravail.objects.create(nom="Unité A", structure=self.struct_a)
        self.risque_a = Risque.objects.create(unite=self.unite_a, categorie=self.categorie, danger="Risque A", frequence=1, gravite=1, maitrise=1)
        self.piece_b = PieceJointe.objects.create(risque=self.risque, fichier=img(), nom_original="secret.png", taille=10)   # unité sans structure "self.unite"... on la force dans une autre structure
        self.unite.structure = Structure.objects.create(nom="Mairie B")
        self.unite.save()
        self.user_a = User.objects.create_user("user_a", password="x")
        self.user_a.groups.add(Group.objects.get(name="Previthys - administrateur"))
        self.user_a.structures.add(self.struct_a)

    def test_pas_dacces_au_fichier_dune_autre_structure(self):
        self.client.force_login(self.user_a)
        self.assertEqual(self.client.get(reverse("pieces_jointes_telecharger", args=[self.piece_b.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("pieces_jointes_supprimer", args=[self.piece_b.pk])).status_code, 404)
        self.assertTrue(PieceJointe.objects.filter(pk=self.piece_b.pk).exists())

    def test_page_modification_dun_risque_dune_autre_structure_inaccessible(self):
        self.client.force_login(self.user_a)
        self.assertEqual(self.client.get(reverse("risques_modifier", args=[self.risque.pk])).status_code, 404)


class ApercuEtImpressionTests(BaseFichiers):
    """Aperçu en modale des images jointes, et intégration des photos dans le document imprimable."""

    def setUp(self):
        self.client.force_login(self.admin)
        self.image = PieceJointe.objects.create(risque=self.risque, fichier=img(), nom_original="photo.png", taille=len(PNG_1PX), ajoute_par=self.admin)
        self.doc = PieceJointe.objects.create(risque=self.risque, fichier=pdf(), nom_original="fiche.pdf", taille=len(PDF_MINI), ajoute_par=self.admin)

    def test_vignette_ouvre_une_fenetre_dapercu_pas_un_nouvel_onglet(self):
        page = self.client.get(reverse("risques_modifier", args=[self.risque.pk])).content.decode()
        self.assertIn('data-bs-target="#pj-apercu"', page)
        self.assertIn('data-pj-nom="photo.png"', page)
        # le document (pdf) garde une ouverture directe, il n'a pas de vignette d'aperçu
        self.assertNotIn('data-pj-nom="fiche.pdf"', page)
        self.assertIn('id="pj-apercu"', page)

    def test_document_integre_les_photos_du_risque(self):
        page = self.client.get(reverse("document")).content.decode()
        self.assertIn('class="photo-risque-impression"', page)
        self.assertIn(reverse("pieces_jointes_telecharger", args=[self.image.pk]), page)
        # le document PDF n'est pas une photo : il ne doit pas apparaître comme image dans le document
        self.assertNotIn(reverse("pieces_jointes_telecharger", args=[self.doc.pk]), page)

    def test_risque_sans_photo_najoute_aucune_image(self):
        Risque.objects.create(unite=self.unite, categorie=self.categorie, danger="Sans photo", gravite=1, frequence=1)
        page = self.client.get(reverse("document")).content.decode()
        self.assertIn("Sans photo", page)
        self.assertEqual(page.count('class="photo-risque-impression"'), 1)  # une seule photo au total (celle de self.risque)

    def test_archive_conserve_le_lien_vers_les_photos(self):
        from core.models import VersionDuerp
        self.client.post(reverse("versions_ajouter"), {"commentaire": "v1"})
        version = VersionDuerp.objects.get()
        self.assertEqual(version.donnees[0]["risques"][0]["images"][0]["nom"], "photo.png")
        page = self.client.get(reverse("versions_document", args=[version.pk])).content.decode()
        self.assertIn('class="photo-risque-impression"', page)

    def test_anciennes_archives_sans_images_narretent_pas_le_document(self):
        from core.models import VersionDuerp
        ancienne = [{"nom": "U", "effectif": 1, "description": "", "risques": [{
            "categorie": "Autre", "danger": "Ancien risque", "situation": "", "frequence": 1, "gravite": 1, "maitrise": 1, "cotation": 1, "niveau": "faible",
            "mesures_existantes": "", "actions": []}]}]   # pas de clé "images", comme avant cette fonctionnalité
        v = VersionDuerp.objects.create(numero=9, commentaire="ancienne", donnees=ancienne)
        r = self.client.get(reverse("versions_document", args=[v.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Ancien risque")
