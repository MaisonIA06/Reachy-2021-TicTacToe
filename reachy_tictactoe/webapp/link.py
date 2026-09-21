"""Connexion au robot, établie en arrière-plan et retentée.

⚠️ Pourquoi ce module existe (incident du 2026-09-21). L'interface
construisait tout à l'intérieur d'un ``with TictactoePlayground(...)`` :
si le serveur SDK de Pollen n'écoutait pas encore sur le port gRPC 50055,
l'appel ``GetAllJointsId`` levait et le processus mourait. ``systemd`` le
relançait toutes les 10 s — deux échecs au démarrage nominal du robot
(~25 s d'indisponibilité), et une **boucle sans fin** quand la panne NTP
tuait ``ros2_control_node`` : 30 redémarrages observés.

Le point critique n'était pas l'indisponibilité, c'était que le bouton
« Réparer » vit DANS l'interface : il devenait inaccessible exactement
dans le seul cas où il sert, ne laissant que l'accès SSH.

⚠️ ``After=reachy_sdk_server.service`` dans l'unité systemd ne suffit pas
et ne suffira jamais : ``After=`` garantit l'ORDRE DE LANCEMENT, pas que
le service soit PRÊT à accepter des connexions. C'est une distinction
classique de systemd, et la raison pour laquelle l'attente doit se faire
ici, dans l'application.
"""
import logging
import threading
import time

logger = logging.getLogger('reachy.tictactoe.webapp')


# Le SDK de Pollen met une dizaine de secondes à écouter après un boot ;
# inutile de marteler le port plus vite.
DEFAULT_DELAY = 5.0


class RobotLink:
    """Détient la connexion au robot, ou son absence.

    Le serveur web interroge ce lien plutôt que de détenir directement une
    ``GameSession`` : il peut ainsi se lever immédiatement et servir sa
    page, connecté ou non.

    Args:
        connect: fonction sans argument renvoyant ``(session, controller)``,
            ou levant si le robot est injoignable.
        delay: attente entre deux tentatives, en secondes.
        sleep: injectable pour les tests.
    """

    def __init__(self, connect, delay=DEFAULT_DELAY, sleep=time.sleep):
        self._connect = connect
        self._delay = delay
        self._sleep = sleep
        self._lock = threading.Lock()
        self._session = None
        self._controller = None
        self._last_error = None

    # -- lecture ----------------------------------------------------------

    @property
    def session(self):
        with self._lock:
            return self._session

    @property
    def controller(self):
        with self._lock:
            return self._controller

    @property
    def connected(self):
        return self.session is not None

    @property
    def status(self):
        """'connected' ou 'connecting' — consommé par l'interface."""
        return 'connected' if self.connected else 'connecting'

    @property
    def last_error(self):
        with self._lock:
            return self._last_error

    # -- établissement ----------------------------------------------------

    def adopt(self, session, controller):
        """Installe une session déjà construite (connexion réussie)."""
        with self._lock:
            self._session = session
            self._controller = controller
            self._last_error = None

    def attempt(self):
        """Une tentative de connexion. Ne lève jamais.

        Returns:
            bool: True si le robot répond désormais.
        """
        try:
            session, controller = self._connect()
        except Exception as erreur:
            with self._lock:
                self._last_error = f'{type(erreur).__name__}: {erreur}'
            logger.warning(f'Robot injoignable : {erreur}')
            return False

        self.adopt(session, controller)
        logger.info('Robot connecté')
        return True

    def run_until_connected(self, should_stop=None):
        """Retente jusqu'au succès, en patientant entre deux essais.

        Args:
            should_stop: prédicat d'arrêt coopératif (fin du processus).

        Returns:
            bool: True si la connexion a fini par aboutir.
        """
        while not (should_stop is not None and should_stop()):
            if self.attempt():
                return True
            self._sleep(self._delay)
        return False

    def start(self, should_stop=None):
        """Lance l'établissement de la connexion en tâche de fond.

        Démon : le serveur web doit pouvoir s'arrêter même si le robot
        n'a jamais répondu.
        """
        fil = threading.Thread(target=self.run_until_connected,
                               args=(should_stop,),
                               name='robot-link', daemon=True)
        fil.start()
        return fil


class StaticLink:
    """Lien déjà établi — pour les appelants qui détiennent la session.

    Permet à ``create_app(session=..., controller=...)`` de continuer à
    fonctionner tel quel, notamment dans les tests.
    """

    def __init__(self, session, controller):
        self.session = session
        self.controller = controller

    @property
    def connected(self):
        return self.session is not None

    @property
    def status(self):
        return 'connected' if self.connected else 'connecting'

    @property
    def last_error(self):
        return None
