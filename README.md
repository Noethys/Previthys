# Previthys - Gestion du Document unique d'évaluation des risques professionnels

**Previthys** est une application Django autonome pour saisir, suivre et archiver le DUERP d'une collectivité ou d'une association.

- Unités de travail, risques (cotation fréquence × gravité × maîtrise, chacune notée 1, 4, 7 ou 10), catégories paramétrables, plan d'actions
- Tableau de bord avec répartition des risques par niveau et par catégorie, top 5 des risques les plus critiques, alerte de mise à jour annuelle
- Versions archivées figées (conservation obligatoire 40 ans), document unique imprimable
- Une action passée à « Terminée » (date de réalisation automatique) devient une mesure existante du risque dans le document et l'export, et l'application invite à réévaluer le risque
- Export Excel (XLSX) avec formules : synthèse, risques, actions
- Interface Bootstrap 5.3 ; listes DataTables 1.13 (boutons Imprimer, Excel, Colonnes, Lignes, tri et réglages mémorisés)
- Mise à jour de l'application en un clic (super-utilisateurs)
- Photos et documents joints à chaque risque (plusieurs par risque), avec aperçu en fenêtre pour les images et intégration dans le document imprimé
- Droits par groupes Django, visibilité par structure, verrouillage après échecs de connexion, en-têtes de sécurité (CSP)
- Journal des modifications (qui a créé, modifié ou supprimé quoi, et quand), consultable mais non modifiable, y compris par un administrateur

Installation

* python3 -m venv venv && source venv/bin/activate
* pip install -r requirements.txt
* python manage.py migrate
* python manage.py creer_groupes
* python manage.py charger_exemple # optionnel : données d'exemple
* python manage.py createsuperuser
* python manage.py collectstatic
* python manage.py runserver
```
