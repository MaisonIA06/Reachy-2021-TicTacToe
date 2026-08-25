"""Tests de la boucle de jeu (reachy_tictactoe.game_launcher).

Le playground est entièrement mocké : on teste uniquement l'orchestration
(valeur de retour, appels aux comportements), pas le robot.
"""
from unittest.mock import MagicMock

from helpers import CUBE, empty_board
from reachy_tictactoe import game_launcher


EMPTY = empty_board()


def test_partie_gagnee_retourne_le_gagnant():
    pg = MagicMock()
    win_board = EMPTY.copy()
    win_board[[0, 1, 2]] = CUBE  # ligne de cubes : Reachy gagne

    pg.analyze_board.side_effect = [EMPTY.copy(), win_board]
    pg.is_ready.return_value = True
    pg.reset.return_value = EMPTY.copy()
    pg.coin_flip.return_value = True  # Reachy commence
    pg.incoherent_board_detected.return_value = False
    pg.cheating_detected.return_value = False
    pg.is_final.return_value = True
    pg.get_winner.return_value = 'robot'

    assert game_launcher.run_game_loop(pg) == 'robot'
    pg.run_celebration.assert_called_once()


def test_triche_confirmee_retourne_aborted_apres_shuffle():
    pg = MagicMock()
    bad_board = EMPTY.copy()
    bad_board[[0, 1, 2]] = CUBE  # 3 cubes, 0 cylindre : incohérent

    # 1er appel : plateau vide (prêt) ; 2e : plateau incohérent ;
    # 3e : double vérification qui CONFIRME l'incohérence (même plateau).
    pg.analyze_board.side_effect = [EMPTY.copy(), bad_board, bad_board.copy()]
    pg.is_ready.return_value = True
    pg.reset.return_value = EMPTY.copy()
    pg.coin_flip.return_value = True
    pg.incoherent_board_detected.return_value = True

    result = game_launcher.run_game_loop(pg)

    pg.shuffle_board.assert_called_once()
    # Une partie annulée doit le dire explicitement, pas retourner None.
    assert result == 'aborted'
    # Et l'écran doit refléter l'annulation avant le shuffle.
    aborted_calls = [
        call for call in pg.display_board.call_args_list
        if call.kwargs.get('winner') == 'aborted'
    ]
    assert len(aborted_calls) == 1


def test_double_check_inconclusif_ne_confirme_pas_la_triche():
    pg = MagicMock()
    bad_board = EMPTY.copy()
    bad_board[[0, 1, 2]] = CUBE

    # 1er : plateau prêt ; 2e : plateau suspect ; 3e : double vérification
    # NON CONCLUANTE (image bruitée → None) ; 4e : plateau final propre.
    pg.analyze_board.side_effect = [
        EMPTY.copy(), bad_board, None, EMPTY.copy()]
    pg.is_ready.return_value = True
    pg.reset.return_value = EMPTY.copy()
    pg.coin_flip.return_value = True
    pg.incoherent_board_detected.side_effect = [True, False]
    pg.cheating_detected.return_value = False
    pg.is_final.return_value = True
    pg.get_winner.return_value = 'nobody'

    result = game_launcher.run_game_loop(pg)

    # Une analyse ratée ne vaut pas confirmation : pas de réprimande.
    pg.shuffle_board.assert_not_called()
    assert result == 'nobody'


def test_main_existe_pour_l_entry_point_console():
    # setup.py déclare 'reachy-tictactoe=reachy_tictactoe.game_launcher:main'
    assert callable(getattr(game_launcher, 'main', None))
