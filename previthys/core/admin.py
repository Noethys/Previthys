#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from django.contrib import admin

from core.models import JournalAudit, Structure


@admin.register(Structure)
class StructureAdmin(admin.ModelAdmin):
    list_display = ("nom",)
    search_fields = ("nom",)
    filter_horizontal = ("utilisateurs",)


@admin.register(JournalAudit)
class JournalAuditAdmin(admin.ModelAdmin):
    """Consultation seule, y compris pour un super-utilisateur : la valeur du journal tient à son immutabilité."""
    list_display = ("horodatage", "utilisateur", "action", "modele", "objet_repr", "structure")
    list_filter = ("action", "modele", "structure")
    search_fields = ("objet_repr", "detail")
    date_hierarchy = "horodatage"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
