"""Tests du système de mise à jour : lecture de version, recherche, extraction protégée, contrôle d'accès.

Aucun accès réseau réel : `urllib.request.urlopen` est simulé (`unittest.mock`).
"""
#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

import io
import os
import zipfile
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from core.utils import update as mod_update
from core.utils.version import GetVersion, GetVersionTuple, lire_entete

User = get_user_model()


def zip_en_memoire(fichiers):
    """Construit une archive zip en mémoire à partir de {chemin_dans_l_archive: contenu}."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        for chemin, contenu in fichiers.items():
            z.writestr(chemin, contenu)
    return buffer.getvalue()


def reponse_http(donnees):
    """Simule l'objet renvoyé par urlopen (utilisable avec `with ... as reponse:`)."""
    m = mock.MagicMock()
    m.read.return_value = donnees
    m.__enter__.return_value = m
    m.__exit__.return_value = False
    return m


class VersionTests(TestCase):
    def test_lire_entete(self):
        self.assertEqual(lire_entete("Version 1.2.3 (21/09/2026) :\n\n- Détail"), "1.2.3")
        self.assertIsNone(lire_entete("Texte sans le bon format"))

    def test_get_version_lit_le_fichier_du_projet(self):
        self.assertRegex(GetVersion(), r"^\d+\.\d+\.\d+$")

    def test_comparaison_numerique_et_pas_alphabetique(self):
        self.assertGreater(GetVersionTuple("1.10.0"), GetVersionTuple("1.9.0"))
        self.assertEqual(GetVersionTuple("2.0"), (2, 0))


@override_settings(PREVITHYS_UPDATE_VERSIONS_URL="https://exemple.fr/versions.txt", PREVITHYS_UPDATE_ZIP_URL_TEMPLATE="https://exemple.fr/{version}.zip")
class RechercheUpdateTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_non_configure_ne_fait_aucune_requete(self):
        with override_settings(PREVITHYS_UPDATE_VERSIONS_URL="", PREVITHYS_UPDATE_ZIP_URL_TEMPLATE=""):
            with mock.patch("urllib.request.urlopen") as urlopen:
                self.assertEqual(mod_update.Recherche_update(), (False, False))
                urlopen.assert_not_called()

    def test_version_plus_recente_detectee(self):
        version_actuelle = GetVersion()
        majeure = int(version_actuelle.split(".")[0]) + 1
        contenu = ("Version %d.0.0 (01/01/2027) :\n\n- Nouveautés" % majeure).encode()
        with mock.patch("urllib.request.urlopen", return_value=reponse_http(contenu)):
            version, changelog = mod_update.Recherche_update()
        self.assertEqual(version, "%d.0.0" % majeure)
        self.assertIn("Nouveautés", changelog)

    def test_meme_version_ou_plus_ancienne_ne_declenche_rien(self):
        contenu = b"Version 0.0.1 (01/01/2020) :\n\n- Ancien"
        with mock.patch("urllib.request.urlopen", return_value=reponse_http(contenu)):
            version, changelog = mod_update.Recherche_update()
        self.assertFalse(version)
        self.assertIn("Ancien", changelog)

    def test_erreur_reseau_geree_sans_exception(self):
        import urllib.error
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("panne")):
            self.assertEqual(mod_update.Recherche_update(), (False, False))

    def test_reponse_trop_volumineuse_refusee(self):
        with mock.patch("urllib.request.urlopen", return_value=reponse_http(b"x" * (mod_update.TAILLE_MAX_OCTETS + 1))):
            self.assertEqual(mod_update.Recherche_update(), (False, False))

    def test_url_non_https_refusee_hors_debug(self):
        with override_settings(DEBUG=False, PREVITHYS_UPDATE_VERSIONS_URL="http://exemple.fr/versions.txt"):
            with mock.patch("urllib.request.urlopen") as urlopen:
                self.assertEqual(mod_update.Recherche_update(), (False, False))
                urlopen.assert_not_called()

    def test_verification_mise_en_cache_un_jour(self):
        user = User.objects.create_superuser("root", password="x")
        contenu = b"Version 0.0.1 (01/01/2020) :\n\n- Ancien"
        with mock.patch("urllib.request.urlopen", return_value=reponse_http(contenu)) as urlopen:
            mod_update.Get_update_for_accueil(user)
            mod_update.Get_update_for_accueil(user)
        self.assertEqual(urlopen.call_count, 1)


class ExtractionTests(TestCase):
    """Vérifie la protection contre le « zip slip » et les fichiers protégés, sans toucher au vrai dossier du projet."""

    def setUp(self):
        import tempfile
        self.base_dir = tempfile.mkdtemp(prefix="duerp_test_extraction_")
        os.makedirs(os.path.join(self.base_dir, "previthys"))
        with open(os.path.join(self.base_dir, "db.sqlite3"), "w") as f:
            f.write("NE JAMAIS ECRASER")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.base_dir, ignore_errors=True)

    def test_fichier_normal_est_ecrit(self):
        z = zip_en_memoire({"appli-1.1.0/core/models.py": b"# nouveau contenu"})
        chemin_zip = os.path.join(self.base_dir, "_test.zip")
        open(chemin_zip, "wb").write(z)
        ecrits, ignores = mod_update._extraire(chemin_zip, self.base_dir)
        self.assertEqual(ecrits, 1)
        self.assertEqual(open(os.path.join(self.base_dir, "core", "models.py")).read(), "# nouveau contenu")

    def test_zip_slip_est_bloque(self):
        """Une entrée d'archive qui tenterait de sortir du dossier de l'application est ignorée, jamais écrite."""
        cible_hors_projet = os.path.join(os.path.dirname(self.base_dir), "fichier_pirate.txt")
        if os.path.exists(cible_hors_projet):
            os.remove(cible_hors_projet)
        z = zip_en_memoire({"appli-1.1.0/../../fichier_pirate.txt": b"pirate"})
        chemin_zip = os.path.join(self.base_dir, "_test.zip")
        open(chemin_zip, "wb").write(z)
        mod_update._extraire(chemin_zip, self.base_dir)
        self.assertFalse(os.path.exists(cible_hors_projet), "une entrée d'archive a écrit hors du dossier de l'application")

    def test_base_de_donnees_jamais_ecrasee(self):
        z = zip_en_memoire({"appli-1.1.0/db.sqlite3": b"BASE PIRATE"})
        chemin_zip = os.path.join(self.base_dir, "_test.zip")
        open(chemin_zip, "wb").write(z)
        mod_update._extraire(chemin_zip, self.base_dir)
        self.assertEqual(open(os.path.join(self.base_dir, "db.sqlite3")).read(), "NE JAMAIS ECRASER")

    def test_archive_sans_dossier_racine_unique(self):
        z = zip_en_memoire({"core/models.py": b"a", "previthys/settings.py": b"b"})
        chemin_zip = os.path.join(self.base_dir, "_test.zip")
        open(chemin_zip, "wb").write(z)
        ecrits, _ = mod_update._extraire(chemin_zip, self.base_dir)
        self.assertEqual(ecrits, 2)


@override_settings(PREVITHYS_UPDATE_VERSIONS_URL="https://exemple.fr/versions.txt", PREVITHYS_UPDATE_ZIP_URL_TEMPLATE="https://exemple.fr/{version}.zip")
class UpdateCompletTests(TestCase):
    def test_archive_github_avec_sous_dossier_projet(self):
        """Archive GitHub « Previthys-x.y.z/previthys/... » : les fichiers doivent arriver dans BASE_DIR, pas dessous."""
        import shutil
        import tempfile
        base_dir = tempfile.mkdtemp(prefix="duerp_test_github_")
        try:
            z = zip_en_memoire({"Previthys-2.0.0/README.md": b"r", "Previthys-2.0.0/previthys/manage.py": b"m",
                                "Previthys-2.0.0/previthys/versions.txt": b"Version 2.0.0 (x) :",
                                "Previthys-2.0.0/previthys/core/models.py": b"# v2"})
            chemin_zip = os.path.join(base_dir, "_test.zip")
            open(chemin_zip, "wb").write(z)
            mod_update._extraire(chemin_zip, base_dir)
            self.assertEqual(open(os.path.join(base_dir, "core", "models.py")).read(), "# v2")
            self.assertTrue(open(os.path.join(base_dir, "versions.txt")).read().startswith("Version 2.0.0"))
            self.assertFalse(os.path.exists(os.path.join(base_dir, "previthys", "core")))
            self.assertFalse(os.path.exists(os.path.join(base_dir, "README.md")))
        finally:
            shutil.rmtree(base_dir, ignore_errors=True)

    def setUp(self):
        cache.clear()

    def test_update_installe_puis_migre_et_recree_les_groupes(self):
        """Utilise un faux BASE_DIR (répertoire temporaire) : ce test ne doit jamais écrire dans le vrai projet."""
        import shutil
        import tempfile
        majeure = int(GetVersion().split(".")[0]) + 1
        changelog = ("Version %d.0.0 (01/01/2027) :\n\n- Test" % majeure).encode()
        archive = zip_en_memoire({"appli/versions.txt": ("Version %d.0.0 (01/01/2027) :\n" % majeure).encode()})

        def fausse_reponse(url, timeout=None):
            return reponse_http(changelog if url.endswith("versions.txt") else archive)

        faux_base_dir = tempfile.mkdtemp(prefix="duerp_test_update_")
        with open(os.path.join(faux_base_dir, "versions.txt"), "w", encoding="utf-8") as f:
            f.write("Version 0.0.1 (01/01/2020) :\n")
        try:
            with override_settings(BASE_DIR=faux_base_dir), \
                 mock.patch("urllib.request.urlopen", side_effect=fausse_reponse), \
                 mock.patch("core.utils.update.call_command") as call_command, \
                 mock.patch("core.utils.update._signaler_redemarrage"):
                self.assertTrue(mod_update.Update())
            self.assertEqual(open(faux_base_dir + "/versions.txt").read(), "Version %d.0.0 (01/01/2027) :\n" % majeure)
        finally:
            shutil.rmtree(faux_base_dir, ignore_errors=True)
        commandes = [appel.args[0] for appel in call_command.call_args_list]
        self.assertIn("migrate", commandes)
        self.assertIn("creer_groupes", commandes)

    def test_pas_de_nouvelle_version_ne_fait_rien(self):
        with mock.patch("urllib.request.urlopen", return_value=reponse_http(b"Version 0.0.1 (2020) :\n")):
            self.assertFalse(mod_update.Update())

    def test_zip_url_non_configuree(self):
        with override_settings(PREVITHYS_UPDATE_ZIP_URL_TEMPLATE=""):
            contenu = ("Version %d.0.0 (01/01/2027) :\n" % (int(GetVersion().split(".")[0]) + 1)).encode()
            with mock.patch("urllib.request.urlopen", return_value=reponse_http(contenu)):
                self.assertFalse(mod_update.Update())


class VueMiseAJourTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import Group
        from django.core.management import call_command
        call_command("creer_groupes", verbosity=0)
        self.admin = User.objects.create_superuser("root", password="x")
        self.simple = User.objects.create_user("simple", password="x")
        self.simple.groups.add(Group.objects.get(name="Previthys - lecture"))
        cache.clear()

    def test_anonyme_redirige(self):
        self.assertEqual(self.client.get(reverse("mise_a_jour")).status_code, 302)

    def test_utilisateur_non_superuser_refuse(self):
        self.client.force_login(self.simple)
        self.assertEqual(self.client.get(reverse("mise_a_jour")).status_code, 403)
        self.assertEqual(self.client.post(reverse("mise_a_jour")).status_code, 403)

    def test_superuser_voit_la_page(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse("mise_a_jour"))
        self.assertContains(r, "Mise à jour de l'application")
        self.assertContains(r, GetVersion())

    def test_lien_visible_uniquement_pour_un_superuser(self):
        self.client.force_login(self.simple)
        self.assertNotContains(self.client.get(reverse("dashboard")), reverse("mise_a_jour"))
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("dashboard")), reverse("mise_a_jour"))

    @override_settings(PREVITHYS_UPDATE_VERSIONS_URL="https://exemple.fr/versions.txt", PREVITHYS_UPDATE_ZIP_URL_TEMPLATE="https://exemple.fr/{v}.zip")
    def test_declenchement_par_formulaire(self):
        self.client.force_login(self.admin)
        with mock.patch("core.views.mise_a_jour.Update", return_value=True), \
             mock.patch("urllib.request.urlopen", side_effect=__import__("urllib.error", fromlist=["URLError"]).URLError("réseau désactivé dans ce test")):
            r = self.client.post(reverse("mise_a_jour"), follow=True)
        self.assertContains(r, "Mise à jour effectuée avec succès.")

    def test_csrf_obligatoire(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.admin)
        self.assertEqual(c.post(reverse("mise_a_jour")).status_code, 403)
