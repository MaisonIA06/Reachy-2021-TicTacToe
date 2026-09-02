"""
Lanceur de jeu TicTacToe adapté pour Reachy SDK 2021
Optimisé pour de meilleures performances avec boucle adaptative
"""
import logging
import threading
import time
from dataclasses import dataclass, field, replace
from typing import Callable, Optional, Tuple

import numpy as np

import zzlog

from . import TictactoePlayground
from .tictactoe_playground import PawnNotGrabbed

logger = logging.getLogger('reachy.tictactoe')


# ============================================================================
# CONSTANTES D'OPTIMISATION
# ============================================================================

# Fréquence d'analyse adaptative
MIN_ANALYSIS_INTERVAL = 0.1   # Intervalle minimum entre analyses (100ms)
MAX_ANALYSIS_INTERVAL = 0.5   # Intervalle maximum quand plateau stable (500ms)
STABLE_THRESHOLD = 3          # Nombre d'analyses identiques avant de ralentir

# Délai avant la double vérification d'une triche suspectée. Invariant
# protégé : le double-check doit porter sur une SCÈNE distincte de la
# première détection — wait_for_img() accepte n'importe quelle frame
# existante (aucune garantie de fraîcheur) et la visée de tête est en
# cache, donc sans ce délai on peut re-confirmer la même image où une
# main occulte transitoirement le plateau. Ne pas le supprimer au motif
# qu'« il n'y a plus de cache vision ».
DOUBLE_CHECK_DELAY = 0.6


def run_game_loop(tictactoe_playground, report=None):
    """
    Boucle principale du jeu avec fréquence d'analyse adaptative.

    Optimisation: Réduit la fréquence d'analyse quand le plateau est stable
    pour économiser les ressources CPU tout en restant réactif aux changements.

    Args:
        tictactoe_playground: Instance de TictactoePlayground
        report: callable optionnel ``report(**changes)`` appelé à chaque
            étape marquante (plateau, joueur courant, issue). Sert à
            alimenter une interface sans que la boucle la connaisse.

    Returns:
        str: Le gagnant ('robot', 'human', 'nobody'), ou 'aborted' si la
             partie a été annulée après une triche/incohérence confirmée.
    """
    logger.info('Game start')

    # Publication d'état vers l'interface, sans effet si personne n'écoute.
    def publish(**changes):
        if report is not None:
            report(**changes)

    # Variables pour l'analyse adaptative
    last_analyzed_board = None
    unchanged_count = 0
    last_analysis_time = 0

    # Attendre que le plateau soit nettoyé et prêt
    publish(status='playing', message='En attente d\'un plateau vide')
    while True:
        board = tictactoe_playground.analyze_board()

        logger.info(
            'Waiting for board to be cleaned.',
            extra={
                'board': board,
            },
        )

        if board is not None and tictactoe_playground.is_ready(board):
            break

        tictactoe_playground.run_random_idle_behavior()

    last_board = tictactoe_playground.reset()
    
    # Afficher le plateau initial
    tictactoe_playground.display_board(last_board, current_player=None)

    # Décider qui commence (pile ou face)
    reachy_turn = tictactoe_playground.coin_flip()

    if reachy_turn:
        tictactoe_playground.run_my_turn()
        current_player = 'robot'
    else:
        tictactoe_playground.run_your_turn()
        current_player = 'human'

    publish(board=last_board, current_player=current_player,
            message='Partie en cours')

    # Réinitialiser les variables adaptatives
    last_analyzed_board = last_board.copy()
    unchanged_count = 0

    # Boucle de jeu principale avec analyse adaptative
    while True:
        current_time = time.time()
        
        # ====================================================================
        # OPTIMISATION: Fréquence d'analyse adaptative
        # ====================================================================
        # Calculer l'intervalle dynamique basé sur la stabilité du plateau
        if unchanged_count >= STABLE_THRESHOLD:
            # Plateau stable - réduire la fréquence d'analyse
            analysis_interval = MAX_ANALYSIS_INTERVAL
        else:
            # Plateau en changement - analyser plus fréquemment
            analysis_interval = MIN_ANALYSIS_INTERVAL
        
        # Respecter l'intervalle minimum entre analyses
        time_since_last = current_time - last_analysis_time
        if time_since_last < analysis_interval:
            time.sleep(analysis_interval - time_since_last)
        
        # Analyser le plateau
        board = tictactoe_playground.analyze_board()
        last_analysis_time = time.time()

        # Plateau invalide détecté
        if board is None:
            logger.warning('Invalid board detected')
            unchanged_count = 0  # Réinitialiser car état incertain
            continue

        # Vérifier si le plateau a changé (pour l'adaptation)
        if last_analyzed_board is not None and np.array_equal(board, last_analyzed_board):
            unchanged_count += 1
        else:
            unchanged_count = 0
            last_analyzed_board = board.copy()

        # Tour de l'humain - attendre qu'il joue
        if not reachy_turn:
            if tictactoe_playground.has_human_played(board, last_board):
                reachy_turn = True
                current_player = 'robot'
                unchanged_count = 0  # Réinitialiser - action détectée
                logger.info('Next turn', extra={
                    'next_player': 'Reachy',
                })
                publish(board=board, current_player='robot')
            else:
                # Afficher le plateau avec le tour de l'humain
                tictactoe_playground.display_board(board, current_player='human')
                tictactoe_playground.run_random_idle_behavior()

        # Détection de triche ou incohérence
        if (tictactoe_playground.incoherent_board_detected(board) or
                tictactoe_playground.cheating_detected(board, last_board, reachy_turn)):
            # Double vérification sur une scène distincte (voir la
            # définition de DOUBLE_CHECK_DELAY).
            time.sleep(DOUBLE_CHECK_DELAY)
            # Une analyse non concluante (None : image bruitée) ne vaut
            # PAS confirmation — on revérifie au prochain tour, comme
            # pour une fausse détection.
            double_check_board = tictactoe_playground.analyze_board()
            if double_check_board is None or np.any(double_check_board != board):
                continue

            # Quelque chose de bizarre s'est vraiment passé
            tictactoe_playground.display_board(board, winner='aborted')
            publish(board=board, current_player=None,
                    message='Partie annulée : plateau incohérent')
            tictactoe_playground.shuffle_board()
            logger.info('Game aborted after confirmed cheating')
            return 'aborted'

        # Tour de Reachy - choisir et jouer une action
        if (not tictactoe_playground.is_final(board)) and reachy_turn:
            # Afficher le plateau avec le tour de Reachy
            tictactoe_playground.display_board(board, current_player='robot')
            tictactoe_playground.run_thinking_behavior()
            action, _ = tictactoe_playground.choose_next_action(board)
            try:
                board = tictactoe_playground.play(action, board)
            except PawnNotGrabbed:
                # Aucun cube en grab_1 : le tour de Reachy N'A PAS eu lieu.
                # On garde son tour et on réessaiera au prochain passage,
                # le temps que l'humain redépose un cube. Surtout ne pas
                # marquer la case : la vision verrait un plateau différent
                # et l'humain serait accusé de tricher.
                logger.warning(
                    'Coup de Reachy reporté : pas de cube à saisir en grab_1'
                )
                publish(message='Posez un cube devant Reachy')
                continue

            last_board = board
            last_analyzed_board = board.copy()
            unchanged_count = 0  # Réinitialiser après action
            reachy_turn = False
            current_player = 'human'
            logger.info('Next turn', extra={
                'next_player': 'Human',
            })

            # Afficher le plateau après le coup de Reachy
            tictactoe_playground.display_board(board, current_player='human')
            publish(board=board, current_player='human',
                    message='À vous de jouer')

        # Fin de partie - déterminer le gagnant et réagir
        if tictactoe_playground.is_final(board):
            winner = tictactoe_playground.get_winner(board)
            
            # Afficher le plateau final avec le gagnant
            tictactoe_playground.display_board(board, winner=winner)
            publish(board=board, current_player=None, winner=winner)

            if winner == 'robot':
                tictactoe_playground.run_celebration()
            elif winner == 'human':
                tictactoe_playground.run_defeat_behavior()
            else:
                tictactoe_playground.run_draw_behavior()

            return winner


# ============================================================================
# PILOTAGE PARTIE PAR PARTIE
# ============================================================================

@dataclass(frozen=True)
class GameState:
    """Instantané figé de l'état du jeu, lisible depuis un autre thread.

    Figé volontairement : le serveur web lit l'état pendant que la partie
    le fait évoluer ; un objet mutable partagé exposerait des états
    incohérents (plateau d'un coup, gagnant du suivant).
    """

    status: str = 'idle'          # idle | playing | finished | error
    board: Tuple[int, ...] = field(default_factory=lambda: (0,) * 9)
    current_player: Optional[str] = None
    winner: Optional[str] = None
    games_played: int = 0
    message: str = ''
    updated_at: float = field(default_factory=time.time)


class GameSession:
    """Joue les parties **une par une**, sur demande.

    Le lanceur historique enchaînait les parties dans un ``while True`` :
    rien ne pouvait déclencher une partie depuis l'extérieur, et les
    moteurs restaient sous couple en permanence. Ici chaque partie se
    termine par un retour en position de repos et une coupure du couple,
    pour que les moteurs refroidissent entre deux joueurs.

    L'état est publié à chaque étape (``state``, ``subscribe``) afin
    qu'une interface l'affiche sans rien connaître du robot.
    """

    def __init__(self, playground, game_loop: Callable = None):
        self._playground = playground
        self._game_loop = game_loop or run_game_loop
        self._state = GameState()
        self._lock = threading.Lock()
        self._listeners = []

    @property
    def playground(self):
        """Le playground piloté (l'interface web y accède pour les
        actions hors partie : vérification des mouvements, calibration)."""
        return self._playground

    @property
    def state(self) -> GameState:
        with self._lock:
            return self._state

    def subscribe(self, listener: Callable[[GameState], None]):
        """Enregistre un observateur notifié à chaque changement d'état."""
        self._listeners.append(listener)
        return listener

    def _publish(self, **changes):
        if 'board' in changes and changes['board'] is not None:
            changes['board'] = tuple(int(c) for c in changes['board'])
        with self._lock:
            self._state = replace(self._state, updated_at=time.time(), **changes)
            snapshot = self._state
        for listener in list(self._listeners):
            try:
                listener(snapshot)
            except Exception as e:
                # Un observateur défaillant (navigateur fermé, socket
                # morte) ne doit jamais interrompre la partie en cours.
                logger.warning(f'State listener failed: {e}')

    def play_one_game(self) -> str:
        """Joue UNE partie, puis repose le bras et coupe le couple.

        Returns:
            str: 'robot', 'human', 'nobody' ou 'aborted'.
        """
        self._publish(status='playing', winner=None, message='',
                      board=(0,) * 9, current_player=None)
        try:
            winner = self._game_loop(self._playground, report=self._publish)
        except Exception as e:
            self._publish(status='error', message=str(e))
            raise
        else:
            with self._lock:
                parties = self._state.games_played + 1
            self._publish(status='finished', winner=winner,
                          current_player=None, games_played=parties)
            return winner
        finally:
            # Toujours reposer le bras : un plantage en pleine séquence le
            # laisserait tendu, sous couple, à chauffer. Un incident de
            # rangement ne doit ni masquer le gagnant, ni masquer l'erreur
            # de partie qui est en train de se propager.
            try:
                self.rest()
            except Exception as e:
                logger.error(f'Mise au repos incomplète : {e}', exc_info=True)

    def rest(self):
        """Repose le bras et relâche les moteurs (refroidissement)."""
        try:
            self._playground.goto_rest_position()
        finally:
            self._playground.reachy.turn_off_smoothly('reachy')
            # Le couple coupé, la tête retombe : elle n'est plus orientée
            # vers le plateau. Sans cette invalidation, la partie suivante
            # analyserait des images d'une tête molle (reset() ne remet le
            # drapeau à zéro qu'APRÈS l'attente d'un plateau vide).
            self._playground.invalidate_head_aim()


def main():
    """Point d'entrée console (voir setup.py : reachy-tictactoe)."""
    import argparse
    from datetime import datetime
    from glob import glob

    parser = argparse.ArgumentParser(
        description='Lance le jeu TicTacToe avec Reachy'
    )
    parser.add_argument(
        '--log-file',
        help='Chemin vers le fichier de log (optionnel)'
    )
    parser.add_argument(
        '--host',
        default='localhost',
        help='Adresse IP du robot Reachy (default: localhost)'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Jouer UNE seule partie puis quitter (le bras se repose et les '
             'moteurs sont relâchés à la fin de chaque partie dans les deux '
             'modes)'
    )
    args = parser.parse_args()

    # Configuration du fichier de log
    if args.log_file is not None:
        n = len(glob(f'{args.log_file}*.log')) + 1
        now = datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f')
        args.log_file += f'-{n}-{now}.log'

    # Configuration du logger
    logger = zzlog.setup(
        logger_root='',
        filename=args.log_file,
    )

    logger.info(
        'Creating a Tic Tac Toe playground.',
        extra={
            'host': args.host,
        }
    )

    # Chaque partie se termine par un retour au repos et une coupure du
    # couple (GameSession.play_one_game) : les moteurs refroidissent entre
    # deux joueurs.
    tictactoe_playground = None
    try:
        with TictactoePlayground(host=args.host) as tictactoe_playground:
            tictactoe_playground.setup()
            session = GameSession(tictactoe_playground)

            while True:
                try:
                    winner = session.play_one_game()

                    logger.info(
                        'Game ended',
                        extra={
                            'game_number': session.state.games_played,
                            'winner': winner,
                        }
                    )

                    # Vérifier si un refroidissement est nécessaire. Le bras
                    # est déjà au repos et hors tension (play_one_game) : on
                    # ne le réalimente PAS, seule la tête l'est pour animer
                    # les antennes (sinon l'animation de veille pilote des
                    # moteurs compliants et ne produit rien).
                    if tictactoe_playground.need_cooldown():
                        logger.warning('Reachy needs cooldown')
                        tictactoe_playground.safe_turn_on('head')
                        tictactoe_playground.enter_sleep_mode()
                        tictactoe_playground.wait_for_cooldown(move_to_rest=False)
                        tictactoe_playground.leave_sleep_mode()
                        tictactoe_playground.invalidate_head_aim()
                        logger.info('Reachy cooldown finished')

                    if args.once:
                        break

                except KeyboardInterrupt:
                    logger.info('Game interrupted by user')
                    break
                except Exception as e:
                    logger.error(
                        'Error during game',
                        extra={
                            'error': str(e),
                            'game_number': session.state.games_played,
                        },
                        exc_info=True
                    )
                    if args.once:
                        break
                    # Attendre un peu avant de relancer
                    time.sleep(5)
                    
    except KeyboardInterrupt:
        logger.info('Application stopped by user')
    except Exception as e:
        logger.error(
            'Fatal error',
            extra={'error': str(e)},
            exc_info=True
        )
    finally:
        logger.info('Application shutdown')
        # Fermer la fenêtre d'affichage si elle est ouverte
        if tictactoe_playground is not None:
            try:
                tictactoe_playground.close_display()
            except Exception as e:
                logger.debug(f'Could not close display: {e}')


if __name__ == '__main__':
    main()
