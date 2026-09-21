"""Reachy lève les yeux vers le joueur à la fin de chaque partie.

⚠️ Périmètre voulu par l'utilisateur : à la fin de la PARTIE, et non après
chaque coup. Le jeu est devenu rapide (animations d'antennes non
bloquantes) et un lever de tête à chaque coup casserait le rythme.

L'ordre compte autant que le geste : la tête se lève AVANT l'émotion, pour
que la célébration, la déception ou la surprise s'adressent à quelqu'un au
lieu d'être jouées face au plateau.
"""
from unittest.mock import MagicMock

import pytest

from helpers import CUBE, empty_board
from reachy_tictactoe import config, game_launcher


EMPTY = empty_board()


def _playground_en_fin_de_partie(winner):
    """Playground mocké qui arrive directement à la fin d'une partie."""
    pg = MagicMock()
    final_board = EMPTY.copy()
    final_board[[0, 1, 2]] = CUBE

    pg.analyze_board.side_effect = [EMPTY.copy(), final_board]
    pg.is_ready.return_value = True
    pg.reset.return_value = EMPTY.copy()
    pg.coin_flip.return_value = True
    pg.incoherent_board_detected.return_value = False
    pg.cheating_detected.return_value = False
    pg.is_final.return_value = True
    pg.get_winner.return_value = winner
    return pg


def _ordre_des_appels(pg):
    return [nom for nom, _, _ in pg.mock_calls]


@pytest.mark.parametrize('winner, emotion', [
    ('robot', 'run_celebration'),
    ('human', 'run_defeat_behavior'),
    ('nobody', 'run_draw_behavior'),
])
def test_la_tete_se_leve_avant_l_emotion_de_fin(winner, emotion):
    pg = _playground_en_fin_de_partie(winner)

    assert game_launcher.run_game_loop(pg) == winner

    pg.look_at_human.assert_called_once()
    appels = _ordre_des_appels(pg)
    assert appels.index('look_at_human') < appels.index(emotion), (
        "la tête doit se lever AVANT l'émotion : sinon Reachy réagit face "
        'au plateau, pas face au joueur'
    )


def test_pas_de_lever_de_tete_sur_une_partie_annulee():
    """Partie annulée pour triche : Reachy balaye le plateau, il ne
    cherche pas le regard du joueur."""
    pg = MagicMock()
    bad_board = EMPTY.copy()
    bad_board[[0, 1, 2]] = CUBE

    pg.analyze_board.side_effect = [EMPTY.copy(), bad_board, bad_board.copy()]
    pg.is_ready.return_value = True
    pg.reset.return_value = EMPTY.copy()
    pg.coin_flip.return_value = True
    pg.incoherent_board_detected.return_value = True

    assert game_launcher.run_game_loop(pg) == 'aborted'
    pg.look_at_human.assert_not_called()


# ---------------------------------------------------------------------------
# Le geste lui-même
# ---------------------------------------------------------------------------

def test_look_at_human_vise_le_point_configure(playground):
    """La cible dépend de la hauteur de table et de la position du joueur :
    elle doit être réglable dans config.py, pas codée en dur."""
    playground.look_at_human()

    cible = config.CAMERA_CONFIG['look_at_human']
    playground.reachy.head.look_at.assert_called_once_with(
        x=cible['x'], y=cible['y'], z=cible['z'],
        duration=cible['duration'])


def test_look_at_human_vise_plus_haut_que_le_plateau():
    """Garde-fou sur la valeur elle-même : une cible sous le plateau
    ferait baisser la tête au lieu de la lever."""
    assert (config.CAMERA_CONFIG['look_at_human']['z']
            > config.CAMERA_CONFIG['look_at_board']['z'])


def test_look_at_human_invalide_la_visee_du_plateau(playground):
    """La tête n'est plus sur le plateau : la partie suivante doit
    re-viser, sinon elle analyserait des images prises vers le joueur."""
    playground._looking_at_board = True

    playground.look_at_human()

    assert playground._looking_at_board is False


# ---------------------------------------------------------------------------
# La caméra doit rester utilisable après la partie
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('winner, emotion', [
    ('robot', 'run_celebration'),
    ('human', 'run_defeat_behavior'),
    ('nobody', 'run_draw_behavior'),
])
def test_la_tete_revient_au_plateau_apres_l_emotion(winner, emotion):
    """Sinon la tête reste tournée vers le joueur une fois la partie finie.

    ⚠️ L'interface web lit la caméra en continu : la vue et le panneau de
    calibrage montreraient la pièce au lieu du plateau — précisément quand
    l'opérateur ouvre le calibrage, c'est-à-dire entre deux parties. Seul
    le lancement d'une nouvelle partie rétablirait la visée.
    """
    pg = _playground_en_fin_de_partie(winner)

    game_launcher.run_game_loop(pg)

    pg.look_at_board.assert_called_once()
    appels = _ordre_des_appels(pg)
    assert appels.index('look_at_human') < appels.index(emotion) \
        < appels.index('look_at_board'), (
        'séquence attendue : lever les yeux, réagir, puis revenir au plateau'
    )


def test_look_at_board_remet_la_visee_en_cache(playground):
    """Revenir au plateau doit rendre la visée en cache valide à nouveau,
    sinon la partie suivante referait un look_at d'une seconde pour rien."""
    playground._looking_at_board = False

    playground.look_at_board()

    cible = config.CAMERA_CONFIG['look_at_board']
    playground.reachy.head.look_at.assert_called_once_with(
        x=cible['x'], y=cible['y'], z=cible['z'], duration=cible['duration'])
    assert playground._looking_at_board is True
