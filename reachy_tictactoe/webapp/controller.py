"""Sérialisation des actions du robot.

Les boutons de l'interface font tous bouger le MÊME bras. Deux actions
lancées en parallèle, ce sont deux threads qui envoient des consignes
contradictoires aux mêmes moteurs. Le contrôleur n'en autorise donc
qu'une à la fois, et la lance en arrière-plan : une partie dure plusieurs
minutes, la requête HTTP ne peut pas attendre sa fin.
"""
import logging
import threading

logger = logging.getLogger('reachy.tictactoe.webapp')


class RobotBusy(Exception):
    """Une action occupe déjà le robot."""

    def __init__(self, running):
        super().__init__(f'robot occupé : {running}')
        self.running = running


class RobotController:
    """Lance les actions du robot une par une, en arrière-plan."""

    def __init__(self, session):
        self._session = session
        self._lock = threading.Lock()
        self._running = None
        self._thread = None
        self._last_error = None

    @property
    def running(self):
        """Nom de l'action en cours, ou None si le robot est libre."""
        with self._lock:
            return self._running

    @property
    def last_error(self):
        with self._lock:
            return self._last_error

    def wait(self, timeout=None):
        """Attend la fin de l'action en cours (tests et arrêt propre)."""
        with self._lock:
            thread = self._thread
        if thread is not None:
            thread.join(timeout)

    # -- Actions ----------------------------------------------------------

    def start_game(self):
        """Joue une partie, puis repose le bras et coupe le couple."""
        self._launch('game', self._session.play_one_game)

    def check_moves(self):
        """Parcourt les 9 cases à vide, pour vérifier le positionnement."""
        self._launch('moves_check', self._session.playground.run_moves_check)

    # -- Interne ----------------------------------------------------------

    def _launch(self, name, target):
        with self._lock:
            if self._running is not None:
                raise RobotBusy(self._running)
            self._running = name
            self._last_error = None

        def run():
            try:
                target()
            except Exception as e:
                logger.error(f'Action {name} échouée : {e}', exc_info=True)
                with self._lock:
                    self._last_error = str(e)
            finally:
                # Toujours libérer : sinon un plantage rendrait tous les
                # boutons de l'interface définitivement inutilisables.
                with self._lock:
                    self._running = None

        thread = threading.Thread(
            target=run, name=f'reachy-{name}', daemon=True)
        try:
            thread.start()
        except Exception:
            # Le thread n'a pas démarré : libérer le robot, sinon tous les
            # boutons de l'interface répondraient 409 pour toujours.
            with self._lock:
                self._running = None
            raise
        with self._lock:
            self._thread = thread
