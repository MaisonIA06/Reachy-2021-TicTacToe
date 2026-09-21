"""Services de Pollen rallumés **ponctuellement** depuis l'interface.

Plusieurs services sont désactivés au démarrage du NUC pour ménager ses
ressources — le contrôleur moteur doit rester servi en premier. On veut
pouvoir les rallumer le temps d'une démonstration, puis les éteindre.

⚠️ **Liste blanche stricte.** Le nom du service arrive du navigateur. Sans
elle, une requête forgée pourrait arrêter ``reachy_sdk_server`` et couper
le robot entier — interface comprise. On n'expose donc que des clés
connues, jamais un nom d'unité venu de l'extérieur, et la commande est
toujours une **liste** d'arguments (jamais ``shell=True``).

⚠️ **Ponctuel = ``start``, jamais ``enable``.** Réactiver au démarrage
irait exactement contre le but : économiser les ressources par défaut.
Après un redémarrage du robot, tout revient à l'état économe.

⚠️ Les services retenus (tableau de bord, base mobile) ne pilotent **ni
les bras ni la tête** : ils ne peuvent pas entrer en conflit avec une
partie. Le suivi de visage et l'animation de veille de Pollen, eux, le
feraient — ils sont volontairement absents de cette liste.
"""
import logging
import subprocess

logger = logging.getLogger('reachy.tictactoe.webapp')


#: Délai maximal d'une commande systemd. Sans lui, une commande qui traîne
#: figerait la requête HTTP et l'interface paraîtrait morte.
COMMAND_TIMEOUT = 10


SERVICES = {
    'dashboard': {
        'unit': 'reachy_dashboard.service',
        'label': 'Tableau de bord Pollen',
        'description': "L'interface web officielle de Pollen. Ne pilote pas "
                       'le robot : aucun conflit avec une partie.',
    },
    'mobile_base': {
        'unit': 'reachy_mobile_base.service',
        'label': 'Base mobile',
        'description': 'Le service de la base mobile.',
    },
}


class ServiceInconnu(KeyError):
    """Nom de service hors liste blanche."""


def _unit(nom):
    if nom not in SERVICES:
        raise ServiceInconnu(nom)
    return SERVICES[nom]['unit']


def _systemctl(*arguments, signaler_echec=True):
    """Lance systemctl et renvoie sa sortie, ou None si indisponible.

    Ne lève jamais : sur un poste de développement systemctl n'existe pas,
    et l'interface doit rester utilisable.

    Args:
        signaler_echec: loguer un code de retour non nul. ⚠️ À laisser à
            False pour ``is-active`` : cette commande renvoie **3 quand le
            service est simplement arrêté**, ce qui est ici l'état normal.
            Sans cette distinction, l'interface loguerait un avertissement
            à chaque interrogation d'un service éteint.
    """
    commande = ['systemctl', '--user', *arguments]
    try:
        resultat = subprocess.run(commande, capture_output=True, text=True,
                                  timeout=COMMAND_TIMEOUT)
    except FileNotFoundError:
        logger.warning('systemctl introuvable (poste de développement ?)')
        return None
    except subprocess.TimeoutExpired:
        logger.warning(f'systemctl {" ".join(arguments)} : délai dépassé')
        return None

    if signaler_echec and resultat.returncode != 0:
        # Sans cette trace, un refus (unité absente, polkit) disparaîtrait
        # sans bruit : l'interface afficherait un service qui ne démarre
        # pas, sans que rien n'explique pourquoi.
        logger.warning(
            f'systemctl {" ".join(arguments)} a échoué '
            f'(code {resultat.returncode}) : {(resultat.stderr or "").strip()}')

    return resultat


def status(nom):
    """'active', 'inactive' ou 'unknown'."""
    resultat = _systemctl('is-active', _unit(nom), signaler_echec=False)
    if resultat is None:
        return 'unknown'
    etat = (resultat.stdout or '').strip()
    return etat if etat in ('active', 'inactive', 'failed') else 'unknown'


def start(nom):
    """Démarre le service — sans l'activer au boot (ponctuel)."""
    unite = _unit(nom)
    logger.info(f'Démarrage ponctuel du service {unite}')
    _systemctl('start', unite)


def stop(nom):
    """Arrête le service."""
    unite = _unit(nom)
    logger.info(f'Arrêt du service {unite}')
    _systemctl('stop', unite)


def listing():
    """Les services pilotables, avec leur état courant."""
    return [
        {
            'name': nom,
            'label': service['label'],
            'description': service['description'],
            'status': status(nom),
        }
        for nom, service in SERVICES.items()
    ]
