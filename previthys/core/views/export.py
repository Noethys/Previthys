#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.conf import settings
from django.http import Http404, HttpResponse
from django.utils import timezone
from django.views.generic import View

from core.utils.export_xlsx import generer_xlsx
from core.models import VersionDuerp
from core.utils import construire_donnees, filtre_structure
from core.views.crud import Lecture


class ExportXlsx(Lecture, View):
    def get(self, request, pk=None):
        organisation = settings.PREVITHYS_ORGANISATION
        if pk:
            version = VersionDuerp.objects.filter(filtre_structure(request.user), pk=pk).first()
            if not version:
                raise Http404("Version introuvable")
            donnees = version.donnees
            sous_titre = "%s - Version %d du %s - %s" % (organisation, version.numero, timezone.localtime(version.date).strftime("%d/%m/%Y"), version.commentaire)
            nom_fichier = "DUERP_version_%d.xlsx" % version.numero
        else:
            donnees = construire_donnees(request.user)
            sous_titre = "%s - Export du %s" % (organisation, timezone.localdate().strftime("%d/%m/%Y"))
            nom_fichier = "DUERP_%s.xlsx" % timezone.localdate().strftime("%Y-%m-%d")
        reponse = HttpResponse(generer_xlsx(donnees, sous_titre), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        reponse["Content-Disposition"] = 'attachment; filename="%s"' % nom_fichier
        return reponse
