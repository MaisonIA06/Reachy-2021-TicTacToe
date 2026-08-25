"""
Lanceur de jeu TicTacToe adapté pour Reachy SDK 2021
Optimisé pour de meilleures performances avec boucle adaptative
"""
import logging
import time
import numpy as np

import zzlog

from . import TictactoePlayground

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


def run_game_loop(tictactoe_playground):
    """
    Boucle principale du jeu avec fréquence d'analyse adaptative.
    
    Optimisation: Réduit la fréquence d'analyse quand le plateau est stable
    pour économiser les ressources CPU tout en restant réactif aux changements.
    
    Args:
        tictactoe_playground: Instance de TictactoePlayground
        
    Returns:
        str: Le gagnant ('robot', 'human', 'nobody'), ou 'aborted' si la
             partie a été annulée après une triche/incohérence confirmée.
    """
    logger.info('Game start')

    # Variables pour l'analyse adaptative
    last_analyzed_board = None
    unchanged_count = 0
    last_analysis_time = 0

    # Attendre que le plateau soit nettoyé et prêt
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
            tictactoe_playground.shuffle_board()
            logger.info('Game aborted after confirmed cheating')
            return 'aborted'

        # Tour de Reachy - choisir et jouer une action
        if (not tictactoe_playground.is_final(board)) and reachy_turn:
            # Afficher le plateau avec le tour de Reachy
            tictactoe_playground.display_board(board, current_player='robot')
            tictactoe_playground.run_thinking_behavior()
            action, _ = tictactoe_playground.choose_next_action(board)
            board = tictactoe_playground.play(action, board)

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

        # Fin de partie - déterminer le gagnant et réagir
        if tictactoe_playground.is_final(board):
            winner = tictactoe_playground.get_winner(board)
            
            # Afficher le plateau final avec le gagnant
            tictactoe_playground.display_board(board, winner=winner)

            if winner == 'robot':
                tictactoe_playground.run_celebration()
            elif winner == 'human':
                tictactoe_playground.run_defeat_behavior()
            else:
                tictactoe_playground.run_draw_behavior()

            return winner


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

    # Boucle principale - jouer des parties en continu
    tictactoe_playground = None
    try:
        with TictactoePlayground(host=args.host) as tictactoe_playground:
            tictactoe_playground.setup()

            game_played = 0

            while True:
                try:
                    winner = run_game_loop(tictactoe_playground)
                    game_played += 1
                    
                    logger.info(
                        'Game ended',
                        extra={
                            'game_number': game_played,
                            'winner': winner,
                        }
                    )

                    # Vérifier si un refroidissement est nécessaire
                    if tictactoe_playground.need_cooldown():
                        logger.warning('Reachy needs cooldown')
                        tictactoe_playground.enter_sleep_mode()
                        tictactoe_playground.wait_for_cooldown()
                        tictactoe_playground.leave_sleep_mode()
                        logger.info('Reachy cooldown finished')
                        
                except KeyboardInterrupt:
                    logger.info('Game interrupted by user')
                    break
                except Exception as e:
                    logger.error(
                        'Error during game',
                        extra={
                            'error': str(e),
                            'game_number': game_played,
                        },
                        exc_info=True
                    )
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
