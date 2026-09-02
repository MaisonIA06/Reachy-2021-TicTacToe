"""Arrêt d'une partie en cours.

Sans cela, un clic malencontreux sur « Lancer une partie » immobilise le
robot jusqu'au redémarrage du serveur : la boucle attend un plateau vide
indéfiniment, et le contrôleur refuse toute autre action (409).

L'arrêt est COOPÉRATIF : on ne tue pas le thread en plein mouvement du
bras, on lui demande de s'arrêter et il rend la main entre deux étapes,
puis repose le bras normalement.
"""
from unittest.mock import MagicMock

import pytest

from helpers import empty_board
from reachy_tictactoe import game_launcher
from reachy_tictactoe.game_launcher import GameSession


@pytest.fixture
def session():
    playground = MagicMock()
    boucle = MagicMock(return_value='robot')
    return GameSession(playground, game_loop=boucle), playground, boucle


class TestDemandeDArret:

    def test_la_boucle_s_arrete_entre_deux_analyses(self):
        """L'attente d'un plateau vide doit pouvoir être interrompue."""
        pg = MagicMock()
        pg.analyze_board.return_value = empty_board()
        pg.is_ready.return_value = False  # jamais prêt : boucle infinie

        appels = {'n': 0}

        def stop_apres_deux_tours():
            appels['n'] += 1
            return appels['n'] >= 2

        resultat = game_launcher.run_game_loop(
            pg, should_stop=stop_apres_deux_tours)

        assert resultat == 'stopped'

    def test_sans_demande_d_arret_la_partie_se_deroule(self):
        pg = MagicMock()
        win = empty_board()
        win[[0, 1, 2]] = 1
        pg.analyze_board.side_effect = [empty_board(), win]
        pg.is_ready.return_value = True
        pg.reset.return_value = empty_board()
        pg.coin_flip.return_value = True
        pg.incoherent_board_detected.return_value = False
        pg.cheating_detected.return_value = False
        pg.is_final.return_value = True
        pg.get_winner.return_value = 'robot'

        assert game_launcher.run_game_loop(pg) == 'robot'


class TestSessionArretable:

    def test_l_arret_est_transmis_a_la_boucle(self, session):
        sess, _, boucle = session

        sess.play_one_game()

        # La boucle reçoit de quoi savoir si l'arrêt a été demandé.
        assert 'should_stop' in boucle.call_args.kwargs

    def test_le_bras_est_repose_apres_un_arret(self, session):
        sess, playground, boucle = session
        boucle.return_value = 'stopped'

        assert sess.play_one_game() == 'stopped'
        playground.goto_rest_position.assert_called_once()

    def test_la_demande_est_remise_a_zero_a_chaque_partie(self, session):
        """Sinon la partie suivante s'arrêterait immédiatement."""
        sess, _, boucle = session
        sess.request_stop()
        sess.play_one_game()

        appels = []
        boucle.side_effect = lambda pg, report=None, should_stop=None: (
            appels.append(should_stop()) or 'robot')
        sess.play_one_game()

        assert appels == [False]
