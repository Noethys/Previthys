#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

from core.forms.base import FormulaireBase
from core.models import VersionDuerp


class FormulaireVersion(FormulaireBase):
    class Meta:
        model = VersionDuerp
        fields = ["structure", "commentaire"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.limiter_structures()
