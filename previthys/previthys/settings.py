#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

import os
import secrets
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = False
SECRET_KEY = 'cle_secrete_a_modifier_imperativement'
ALLOWED_HOSTS = []
# CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

# Adresse de l'administration Django : à personnaliser en production (ex. gestion-7f3k/), avec un « / » final
ADMIN_URL = "administrateur/"
if not ADMIN_URL.endswith("/"):
    ADMIN_URL += "/"

# Nom affiché en en-tête, dans le document unique et dans les exports
PREVITHYS_ORGANISATION = "Non renseigné"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "axes",
    "core",
    "django_cleanup.apps.CleanupConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.EnTetesSecuriteMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "previthys.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "core.context_processors.organisation",
    ]},
}]

WSGI_APPLICATION = "previthys.wsgi.application"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Utilisé pour limiter à une fois par jour la recherche de mise à jour (voir core/utils/update.py).
# Avec plusieurs processus applicatifs (gunicorn -w > 1), chaque processus a son propre cache mémoire :
# remplacer par un cache partagé (Redis, Memcached) évite une recherche par processus.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static"

# Fichiers joints aux risques (photos, documents). Aucune URL publique n'est configurée : ils ne sont accessibles
# qu'au travers de la vue core.views.pieces_jointes.Telecharger, qui vérifie les droits et la structure.
MEDIA_ROOT = str(BASE_DIR / "media")

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

# Chargement des settings de production
try:
    from .settings_production import *
except:
    print("Settings en production non trouvés : Utilisation des settings par défaut.")

# ---------------------------------------------------------------------------------------------
# Sécurité
# ---------------------------------------------------------------------------------------------

HTTPS = "1"
SESSION_COOKIE_AGE = 12 * 3600
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

if not DEBUG:
    SESSION_COOKIE_SECURE = HTTPS
    CSRF_COOKIE_SECURE = HTTPS
    SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SSL_REDIRECT", "1" if HTTPS else "0") == "1"
    # HSTS : 30 jours par défaut ; à porter à 31536000 (1 an) une fois le HTTPS validé
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "2592000" if HTTPS else "0"))

# Derrière un reverse proxy qui termine le TLS (nginx, Apache, ISPConfig) : à activer uniquement si le proxy
# écrase lui-même l'en-tête X-Forwarded-Proto / X-Forwarded-For.
if os.environ.get("DJANGO_BEHIND_PROXY", "0") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    AXES_IPWARE_PROXY_COUNT = 1
    AXES_IPWARE_META_PRECEDENCE_ORDER = ["HTTP_X_FORWARDED_FOR", "REMOTE_ADDR"]

# Protection contre la force brute : 5 échecs pour un même identifiant depuis une même adresse, puis 15 minutes de blocage
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]
AXES_FAILURE_LIMIT = int(os.environ.get("DJANGO_LOGIN_FAILURES", "5"))
AXES_COOLOFF_TIME = timedelta(minutes=int(os.environ.get("DJANGO_LOGIN_COOLOFF_MINUTES", "15")))
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_HTTP_RESPONSE_CODE = 429
AXES_LOCKOUT_TEMPLATE = "core/verrouille.html"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "WARNING"},
        "axes": {"handlers": ["console"], "level": "WARNING"},
    },
}
