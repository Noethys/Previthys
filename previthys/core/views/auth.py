"""Connexion et déconnexion (vues d'authentification de Django, avec le gabarit de l'application)."""
#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.contrib.auth.views import LoginView, LogoutView


class Connexion(LoginView):
    """Page de connexion : identifiant et mot de passe. Un utilisateur déjà connecté est renvoyé au tableau de bord."""
    template_name = "core/login.html"
    redirect_authenticated_user = True


class Deconnexion(LogoutView):
    """Déconnexion par requête POST uniquement (bouton de la barre de menu), puis retour à la page de connexion.

    Django 4.2 acceptait encore la déconnexion par simple lien (GET) ; on l'interdit pour toutes les versions.
    """
    http_method_names = ["post", "options"]
