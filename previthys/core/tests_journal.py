"""Tests du journal des modifications : consignation automatique, immutabilité, accès et filtrage par structure."""

#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.models import ActionPrevention, CategorieRisque, JournalAudit, PieceJointe, Risque, Structure, UniteTravail, VersionDuerp

User = get_user_model()


class BaseJournal(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("creer_groupes", verbosity=0)
        cls.admin = User.objects.create_superuser("root", password="x")
        cls.categorie = CategorieRisque.objects.get(nom="Autre")
        cls.unite = UniteTravail.objects.create(nom="Services techniques")

    def setUp(self):
        self.client.force_login(self.admin)


class ConsignationTests(BaseJournal):
    def test_creation_dune_unite_consignee(self):
        self.client.post(reverse("unites_ajouter"), {"nom": "Nouvelle unité", "effectif": 3})
        entree = JournalAudit.objects.get(modele="unité de travail", action="creation")
        self.assertEqual(entree.utilisateur, self.admin)
        self.assertEqual(entree.objet_repr, "Nouvelle unité")

    def test_modification_consigne_le_detail_des_champs_changes(self):
        risque = Risque.objects.create(unite=self.unite, categorie=self.categorie, danger="Chute", frequence=1, gravite=1, maitrise=1)
        self.client.post(reverse("risques_modifier", args=[risque.pk]), {"unite": self.unite.pk, "categorie": self.categorie.pk, "danger": "Chute grave", "frequence": 10, "gravite": 10, "maitrise": 10})
        entree = JournalAudit.objects.get(modele="risque", action="modification")
        self.assertIn("Danger : Chute → Chute grave", entree.detail)
        self.assertIn("Fréquence : 1 - Rare → 10 - Permanente", entree.detail)
        self.assertIn("Maîtrise : 1 - Maîtrisé (mesures en place et efficaces) → 10 - Non maîtrisé (aucune mesure)", entree.detail)
        self.assertEqual(entree.objet_repr, "Chute grave")

    def test_modification_sans_aucun_changement_nest_pas_consignee(self):
        risque = Risque.objects.create(unite=self.unite, categorie=self.categorie, danger="Chute", frequence=1, gravite=1, maitrise=1)
        JournalAudit.objects.all().delete()
        self.client.post(reverse("risques_modifier", args=[risque.pk]), {"unite": self.unite.pk, "categorie": self.categorie.pk, "danger": "Chute", "frequence": 1, "gravite": 1, "maitrise": 1})
        self.assertFalse(JournalAudit.objects.filter(modele="risque").exists())

    def test_modification_dune_categorie_resout_lancienne_valeur_de_la_cle_etrangere(self):
        risque = Risque.objects.create(unite=self.unite, categorie=self.categorie, danger="Chute", frequence=1, gravite=1, maitrise=1)
        autre = CategorieRisque.objects.create(nom="Bruit", ordre=9)
        self.client.post(reverse("risques_modifier", args=[risque.pk]), {"unite": self.unite.pk, "categorie": autre.pk, "danger": "Chute", "frequence": 1, "gravite": 1, "maitrise": 1})
        entree = JournalAudit.objects.get(modele="risque", action="modification")
        self.assertIn("Catégorie : Autre → Bruit", entree.detail)

    def test_suppression_consignee_avant_disparition(self):
        risque = Risque.objects.create(unite=self.unite, categorie=self.categorie, danger="À supprimer", frequence=1, gravite=1, maitrise=1)
        self.client.post(reverse("risques_supprimer", args=[risque.pk]))
        entree = JournalAudit.objects.get(modele="risque", action="suppression")
        self.assertEqual(entree.objet_repr, "À supprimer")

    def test_suppression_bloquee_par_protection_nest_pas_consignee(self):
        cat = CategorieRisque.objects.create(nom="Utilisée", ordre=1)
        Risque.objects.create(unite=self.unite, categorie=cat, danger="X", gravite=1, frequence=1)
        JournalAudit.objects.all().delete()
        self.client.post(reverse("categories_supprimer", args=[cat.pk]))
        self.assertFalse(JournalAudit.objects.filter(objet_repr="Utilisée", action="suppression").exists())
        self.assertTrue(CategorieRisque.objects.filter(pk=cat.pk).exists())

    def test_creation_et_suppression_dune_action(self):
        risque = Risque.objects.create(unite=self.unite, categorie=self.categorie, danger="Chute", gravite=1, frequence=1)
        self.client.post(reverse("actions_ajouter"), {"risque": risque.pk, "description": "Former le personnel", "statut": "a_faire"})
        self.assertTrue(JournalAudit.objects.filter(modele="action de prévention", action="creation", objet_repr__icontains="Former").exists())
        action = ActionPrevention.objects.get(description="Former le personnel")
        self.client.post(reverse("actions_supprimer", args=[action.pk]))
        self.assertTrue(JournalAudit.objects.filter(modele="action de prévention", action="suppression").exists())

    def test_archivage_dune_version_consigne(self):
        self.client.post(reverse("versions_ajouter"), {"commentaire": "Première version"})
        version = VersionDuerp.objects.get()
        entree = JournalAudit.objects.get(modele="version du DUERP", action="creation")
        self.assertEqual(entree.objet_repr, str(version))

    def test_ajout_et_suppression_de_piece_jointe_consignes(self):
        from core.tests_pieces_jointes import img
        risque = Risque.objects.create(unite=self.unite, categorie=self.categorie, danger="Chute", gravite=1, frequence=1)
        self.client.post(reverse("risques_modifier", args=[risque.pk]), {
            "unite": self.unite.pk, "categorie": self.categorie.pk, "danger": "Chute", "frequence": 1, "gravite": 1, "maitrise": 1, "pieces_jointes": [img("photo.png")],
        })
        entree = JournalAudit.objects.get(modele="pièce jointe", action="creation")
        self.assertIn("Ajoutée au risque « Chute »", entree.detail)
        piece = PieceJointe.objects.get(nom_original="photo.png")
        self.client.post(reverse("pieces_jointes_supprimer", args=[piece.pk]))
        self.assertTrue(JournalAudit.objects.filter(modele="pièce jointe", action="suppression").exists())


class AccesJournalTests(BaseJournal):
    def test_lecteur_peut_consulter_le_journal(self):
        lecteur = User.objects.create_user("lecteur", password="x")
        lecteur.groups.add(Group.objects.get(name="Previthys - lecture"))
        self.client.force_login(lecteur)
        self.assertEqual(self.client.get(reverse("journal_liste")).status_code, 200)

    def test_journal_sans_bouton_ajouter_ni_liens_modifier_supprimer(self):
        UniteTravail.objects.create(nom="Test", structure=None)
        self.client.post(reverse("unites_ajouter"), {"nom": "Loggée", "effectif": 1})
        page = self.client.get(reverse("journal_liste"))
        self.assertNotContains(page, ">Ajouter<")
        self.assertNotContains(page, ">Modifier<")
        self.assertNotContains(page, ">Supprimer<")

    def test_anonyme_redirige(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("journal_liste")).status_code, 302)

    def test_journal_isole_par_structure(self):
        struct_a, struct_b = Structure.objects.create(nom="Mairie A"), Structure.objects.create(nom="Mairie B")
        unite_a = UniteTravail.objects.create(nom="Unité A", structure=struct_a)
        UniteTravail.objects.create(nom="Unité B", structure=struct_b)
        risque_a = Risque.objects.create(unite=unite_a, categorie=self.categorie, danger="Danger A", gravite=1, frequence=1)
        self.client.post(reverse("risques_modifier", args=[risque_a.pk]), {"unite": unite_a.pk, "categorie": self.categorie.pk, "danger": "Danger A modifié", "frequence": 4, "gravite": 4, "maitrise": 4})

        redacteur_a = User.objects.create_user("red_a", password="x")
        redacteur_a.groups.add(Group.objects.get(name="Previthys - rédacteur"))
        redacteur_a.structures.add(struct_a)
        self.client.force_login(redacteur_a)
        page = self.client.get(reverse("journal_liste"))
        self.assertContains(page, "Danger A modifié")

        redacteur_b = User.objects.create_user("red_b", password="x")
        redacteur_b.groups.add(Group.objects.get(name="Previthys - rédacteur"))
        redacteur_b.structures.add(struct_b)
        self.client.force_login(redacteur_b)
        page = self.client.get(reverse("journal_liste"))
        self.assertNotContains(page, "Danger A modifié")

    def test_le_journal_naccorde_aucun_droit_decriture_meme_a_ladministrateur(self):
        administrateur = User.objects.create_user("admin_struct", password="x")
        administrateur.groups.add(Group.objects.get(name="Previthys - administrateur"))
        self.assertFalse(administrateur.has_perm("core.add_journalaudit"))
        self.assertFalse(administrateur.has_perm("core.change_journalaudit"))
        self.assertFalse(administrateur.has_perm("core.delete_journalaudit"))
        self.assertTrue(administrateur.has_perm("core.view_journalaudit"))


class ImmutabiliteAdminTests(TestCase):
    def test_journal_non_modifiable_dans_ladministration(self):
        from core.admin import JournalAuditAdmin
        from core.models import JournalAudit as Modele
        admin_instance = JournalAuditAdmin(Modele, None)
        self.assertFalse(admin_instance.has_add_permission(None))
        self.assertFalse(admin_instance.has_change_permission(None))
        self.assertFalse(admin_instance.has_delete_permission(None))


class UtilJournalTests(TestCase):
    def test_structure_de_remonte_les_relations(self):
        from core.utils.journal import structure_de
        s = Structure.objects.create(nom="Mairie")
        u = UniteTravail.objects.create(nom="U", structure=s)
        cat = CategorieRisque.objects.get(nom="Autre")
        r = Risque.objects.create(unite=u, categorie=cat, danger="D", gravite=1, frequence=1)
        a = ActionPrevention.objects.create(risque=r, description="A")
        self.assertEqual(structure_de(u), s)
        self.assertEqual(structure_de(r), s)
        self.assertEqual(structure_de(a), s)
        self.assertIsNone(structure_de(cat))

    def test_valeur_affichable_traduit_les_choix_et_les_cles_etrangeres(self):
        from core.utils.journal import valeur_affichable
        u = UniteTravail.objects.create(nom="U")
        self.assertEqual(valeur_affichable(Risque, "gravite", 10), "10 - Très grave (mortelle ou invalidante)")
        self.assertEqual(valeur_affichable(Risque, "unite", u.pk, est_initial=True), "U")
        self.assertEqual(valeur_affichable(Risque, "unite", 99999, est_initial=True), "(objet supprimé depuis)")
        self.assertEqual(valeur_affichable(Risque, "danger", None), "(vide)")
