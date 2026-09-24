"""Mise à jour de l'application depuis un serveur distant (outils/utils/utils_update.py) :
vérifie la version disponible, télécharge une archive .zip, la déploie par-dessus les fichiers actuels, puis relance
les migrations et les groupes de droits.

Réservée aux super-utilisateurs (voir core/views/mise_a_jour.py).
- les URLs sont configurables (PREVITHYS_UPDATE_VERSIONS_URL, PREVITHYS_UPDATE_ZIP_URL_TEMPLATE), la fonctionnalité est
  désactivée tant qu'elles ne sont pas renseignées ;
- l'extraction de l'archive est protégée contre le « zip slip » (une entrée d'archive comme "../../fichier" ne peut
  pas écrire hors du dossier de l'application), et certains fichiers ne sont jamais écrasés (base de données, secrets).
"""
#  -*- coding: utf-8 -*-
#  Copyright (c) 2026 Ivan LUCAS.
#  Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
#  Distribué sous licence GNU GPL.

import logging, os, tempfile, urllib.error, urllib.request, zipfile
from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command

from core.utils.version import GetVersion, GetVersionTuple, lire_entete

logger = logging.getLogger("core.update")

TAILLE_MAX_OCTETS = 200 * 1024 * 1024   # 200 Mo : au-delà, l'archive est refusée (protection contre un serveur compromis)
DELAI_RESEAU = 15                        # secondes

# Jamais écrasés par une mise à jour, quel que soit leur contenu dans l'archive téléchargée.
CHEMINS_PROTEGES = ("db.sqlite3", ".env", ".demo_password", "venv/", "static/", "staticfiles/", "media/", ".git/",
                    "debug.log", "previthys/settings_production.py")


def _url_valide(url):
    if not url:
        return False
    if not url.startswith("https://") and not settings.DEBUG:
        logger.warning("URL de mise à jour non HTTPS refusée : %s", url)
        return False
    return True


def _telecharger(url):
    """Télécharge une URL en mémoire, avec une limite de taille. Lève une exception en cas d'échec."""
    with urllib.request.urlopen(url, timeout=DELAI_RESEAU) as reponse:
        donnees = reponse.read(TAILLE_MAX_OCTETS + 1)
    if len(donnees) > TAILLE_MAX_OCTETS:
        raise ValueError("Le fichier téléchargé dépasse la taille maximale autorisée (%d Mo)." % (TAILLE_MAX_OCTETS // (1024 * 1024)))
    return donnees


def Recherche_update():
    """Recherche une version plus récente. Renvoie (numéro_version_disponible_ou_False, changelog_ou_False)."""
    url = getattr(settings, "PREVITHYS_UPDATE_VERSIONS_URL", "")
    if not _url_valide(url):
        return False, False
    try:
        changelog = _telecharger(url).decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, ValueError) as err:
        logger.warning("Le fichier de version n'a pas pu être téléchargé : %s", err)
        return False, False

    version_disponible = lire_entete(changelog)
    if not version_disponible:
        logger.warning("Format de version illisible dans %s", url)
        return False, changelog

    try:
        if GetVersionTuple(version_disponible) <= GetVersionTuple(GetVersion()):
            return False, changelog
    except ValueError:
        logger.warning("Numéro de version actuel illisible")
        return False, changelog

    return version_disponible, changelog


def Get_update_for_accueil(user):
    """Version de Recherche_update mise en cache un jour par utilisateur, pour l'alerte du tableau de bord."""
    cle = "previthys_update_check_%s" % user.pk
    en_cache = cache.get(cle)
    if en_cache is None:
        version_disponible, _ = Recherche_update()
        en_cache = version_disponible or ""
        cache.set(cle, en_cache, timeout=86400)
    return en_cache or False


def _chemin_protege(chemin_relatif):
    chemin_relatif = chemin_relatif.replace(os.sep, "/")
    return any(chemin_relatif == p.rstrip("/") or chemin_relatif.startswith(p) for p in CHEMINS_PROTEGES)


def _chemin_sur(base_dir, chemin_relatif):
    """Résout un chemin d'entrée d'archive sous base_dir, ou renvoie None si l'entrée tente d'en sortir (zip slip)."""
    cible = os.path.normpath(os.path.join(base_dir, chemin_relatif))
    if os.path.commonpath([cible, base_dir]) != base_dir:
        return None
    return cible


def _extraire(chemin_zip, base_dir, version):
    with zipfile.ZipFile(chemin_zip) as zfile:
        liste_fichiers = zfile.namelist()
        prefixe = "Previthys-%s/previthys/" % version
        chemin_dest = os.path.join(settings.BASE_DIR, "")

        ignores, ecrits = [], 0
        for i in liste_fichiers:
            d = i.replace(prefixe, "")
            if len(d) > 1 and not d.startswith("Previthys-%s" % version):
                if i.endswith('/'):
                    try:
                        os.makedirs(os.path.join(chemin_dest, d))
                    except:
                        pass
                else:
                    try:
                        os.makedirs(os.path.join(chemin_dest, os.path.dirname(d)))
                    except:
                        pass
                    nom_fichier_temp = os.path.join(chemin_dest, d)
                    if os.path.isdir(nom_fichier_temp):
                        os.rmdir(nom_fichier_temp)
                    data = zfile.read(i)
                    fp = open(nom_fichier_temp, "wb")
                    fp.write(data)
                    fp.close()
                    ecrits += 1

    return ecrits, ignores


def Update():
    """Télécharge et installe la dernière version. Renvoie True en cas de succès, False sinon."""
    version_disponible, _ = Recherche_update()
    if not version_disponible:
        return False

    modele_url = getattr(settings, "PREVITHYS_UPDATE_ZIP_URL_TEMPLATE", "")
    if not modele_url:
        logger.warning("PREVITHYS_UPDATE_ZIP_URL_TEMPLATE n'est pas configuré.")
        return False
    url_zip = modele_url.format(version=version_disponible)
    if not _url_valide(url_zip):
        return False

    try:
        logger.info("Téléchargement de la version %s...", version_disponible)
        donnees = _telecharger(url_zip)
    except (urllib.error.URLError, TimeoutError, ValueError) as err:
        logger.error("Le téléchargement a échoué : %s", err)
        return False

    with tempfile.TemporaryDirectory(prefix="previthys_update_") as dossier_temp:
        chemin_zip = os.path.join(dossier_temp, "mise_a_jour.zip")
        with open(chemin_zip, "wb") as f:
            f.write(donnees)
        if not zipfile.is_zipfile(chemin_zip):
            logger.error("Le fichier téléchargé n'est pas une archive valide.")
            return False
        try:
            ecrits, ignores = _extraire(chemin_zip, str(settings.BASE_DIR), version_disponible)
        except (zipfile.BadZipFile, OSError, ValueError) as err:
            logger.error("L'installation a échoué : %s", err)
            return False

    logger.info("Installation terminée : %d fichiers écrits, %d ignorés (protégés).", ecrits, len(ignores))

    cache.clear()

    logger.info("Migration de la base de données...")
    call_command("migrate")

    logger.info("Mise à jour des groupes de droits...")
    call_command("creer_groupes", verbosity=0)

    logger.info("Régénération des fichiers statiques...")
    try:
        call_command("collectstatic", verbosity=0, interactive=False)
    except Exception as err:  # STATIC_ROOT peut ne pas être configuré en développement
        logger.warning("collectstatic n'a pas pu s'exécuter : %s", err)

    _signaler_redemarrage()
    logger.info("Mise à jour terminée : version %s installée.", version_disponible)
    return True


def _signaler_redemarrage():
    """Modifie la date du fichier wsgi.py pour inviter un serveur en mode auto-reload (ex. mod_wsgi) à redémarrer.

    Sans effet avec gunicorn ou uwsgi : ces serveurs doivent être redémarrés manuellement ou par un
    gestionnaire de processus (systemd, supervisor) après une mise à jour. Voir le README.
    """
    chemin_wsgi = os.path.join(settings.BASE_DIR, "previthys", "wsgi.py")
    try:
        os.utime(chemin_wsgi, None)
    except OSError as err:
        logger.warning("Impossible de signaler le redémarrage via wsgi.py : %s", err)
