"""Téléchargement et suppression des pièces jointes d'un risque.

Les fichiers ne sont jamais servis directement par le serveur web (pas d'URL publique sous MEDIA_URL) : cette vue
vérifie la connexion, le droit et la structure avant de renvoyer le contenu, comme pour toute autre donnée du DUERP.
"""
#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from core.models import PieceJointe
from core.utils import filtre_structure
from core.utils.fichiers import est_image
from core.utils.journal import consigner

# Un type MIME fixe par extension : on ne fait jamais confiance au type déclaré par le navigateur à l'envoi.
TYPES_MIME = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp",
    "pdf": "application/pdf", "txt": "text/plain",
    "doc": "application/msword", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "odt": "application/vnd.oasis.opendocument.text", "ods": "application/vnd.oasis.opendocument.spreadsheet",
}


def _get(request, pk):
    return get_object_or_404(PieceJointe.objects.select_related("risque__unite").filter(filtre_structure(request.user, "risque__unite__")), pk=pk)


class Telecharger(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "core.view_risque"

    def get(self, request, pk):
        piece = _get(request, pk)
        try:
            fichier = piece.fichier.open("rb")
        except FileNotFoundError:
            raise Http404("Fichier introuvable sur le serveur.")
        image = est_image(piece.nom_original)
        return FileResponse(fichier, filename=piece.nom_original, as_attachment=not image, content_type=TYPES_MIME.get(piece.extension, "application/octet-stream"))


class Supprimer(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "core.change_risque"

    def post(self, request, pk):
        piece = _get(request, pk)
        risque_pk = piece.risque_id
        detail = "Retirée du risque « %s »" % piece.risque.danger
        piece.fichier.delete(save=False)
        piece.delete()
        consigner(request, "suppression", piece, detail)
        messages.success(request, "Pièce jointe supprimée.")
        return redirect("risques_modifier", pk=risque_pk)
