#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from core.forms.base import FormulaireBase
from core.forms.champs import ChampFichierMultiple
from core.models import Risque, UniteTravail
from core.utils import filtre_structure
from core.utils.fichiers import LIBELLE_TYPES_ACCEPTES, NOMBRE_MAX_FICHIERS, TAILLE_MAX_OCTETS


class FormulaireRisque(FormulaireBase):
    pieces_jointes = ChampFichierMultiple(
        label="Ajouter des fichiers",
        help_text="%s. %d fichiers maximum, %d Mo chacun." % (LIBELLE_TYPES_ACCEPTES.capitalize(), NOMBRE_MAX_FICHIERS, TAILLE_MAX_OCTETS // (1024 * 1024)),
    )

    class Meta:
        model = Risque
        fields = ["unite", "categorie", "danger", "situation", "frequence", "gravite", "maitrise", "mesures_existantes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.user is not None:
            self.fields["unite"].queryset = UniteTravail.objects.filter(filtre_structure(self.user))
