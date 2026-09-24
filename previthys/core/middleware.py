"""En-têtes de sécurité HTTP : politique de contenu (CSP), permissions du navigateur, pas de mise en cache."""
#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.conf import settings
from django.utils.cache import add_never_cache_headers

CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",                 # aucun script en ligne : tout le JavaScript vient de /static/
    "style-src 'self' 'unsafe-inline'",  # styles en ligne limités aux attributs style="..." de Bootstrap et DataTables
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"


class EnTetesSecuriteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        reponse = self.get_response(request)
        # L'administration Django garde ses propres règles (elle utilise quelques scripts en ligne).
        if not request.path.startswith("/" + settings.ADMIN_URL):
            reponse.headers.setdefault("Content-Security-Policy", CSP)
        reponse.headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        # Données personnelles et exports : jamais mis en cache par le navigateur ni par un proxy
        add_never_cache_headers(reponse)
        return reponse
