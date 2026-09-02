"""Pilotage du jeu partie par partie (``GameSession``).

Le jeu tournait en boucle infinie : impossible de le déclencher depuis
l'extérieur, et les moteurs restaient sous couple entre deux parties. Une
``GameSession`` joue **une** partie à la demande, repose le bras et coupe
le couple à la fin, et publie l'état courant pour qu'une interface puisse
l'afficher sans connaître le robot.
"""
from unittest.mock import MagicMock

import pytest

from helpers import CUBE, empty_board
from reachy_tictactoe.game_launcher import GameSession, GameState


EMPTY = empty_board()


@pytest.fixture
def session():
    """Session branchée sur un playground et une boucle de jeu factices."""
    playground = MagicMock()
    boucle = MagicMock(return_value='robot')
    return GameSession(playground, game_loop=boucle), playground, boucle


class TestUnePartieALaFois:

    def test_joue_une_partie_et_rend_le_gagnant(self, session):
        sess, _, boucle = session

        assert sess.play_one_game() == 'robot'
        boucle.assert_called_once()

    def test_le_bras_se_repose_et_le_couple_est_coupe_a_la_fin(self, session):
        """Demande explicite : les moteurs doivent refroidir entre deux parties."""
        sess, playground, _ = session

        sess.play_one_game()

        playground.goto_rest_position.assert_called_once()
        playground.reachy.turn_off_smoothly.assert_called_once_with('reachy')

    def test_le_bras_se_repose_meme_si_la_partie_echoue(self, session):
        """Sinon un plantage laisse le bras tendu, sous couple, à chauffer."""
        sess, playground, boucle = session
        boucle.side_effect = RuntimeError('caméra perdue')

        with pytest.raises(RuntimeError):
            sess.play_one_game()

        playground.goto_rest_position.assert_called_once()
        playground.reachy.turn_off_smoothly.assert_called_once_with('reachy')

    def test_les_parties_sont_comptees(self, session):
        sess, _, _ = session

        sess.play_one_game()
        sess.play_one_game()

        assert sess.state.games_played == 2

    def test_la_visee_de_la_tete_est_invalidee_en_se_reposant(self, session):
        """Couper le couple rend la tête molle : elle n'est plus visée.

        Sans cette invalidation, la partie suivante attend un plateau vide
        en analysant des images d'une tête tombante — ``reset()`` ne remet
        le drapeau à zéro qu'APRÈS cette attente, donc trop tard.
        """
        sess, playground, _ = session

        sess.play_one_game()

        playground.invalidate_head_aim.assert_called_once()

    def test_un_echec_du_repos_ne_masque_pas_le_gagnant(self, session):
        """Le résultat de la partie prime sur un incident de rangement."""
        sess, playground, _ = session
        playground.goto_rest_position.side_effect = RuntimeError('moteur muet')

        assert sess.play_one_game() == 'robot'

    def test_un_echec_du_repos_ne_masque_pas_l_erreur_de_partie(self, session):
        sess, playground, boucle = session
        boucle.side_effect = RuntimeError('caméra perdue')
        playground.goto_rest_position.side_effect = RuntimeError('moteur muet')

        with pytest.raises(RuntimeError, match='caméra perdue'):
            sess.play_one_game()


class TestEtatPublie:

    def test_au_repos_avant_toute_partie(self, session):
        sess, _, _ = session

        assert sess.state.status == 'idle'
        assert sess.state.winner is None
        assert list(sess.state.board) == [0] * 9

    def test_l_etat_final_porte_le_gagnant(self, session):
        sess, _, _ = session

        sess.play_one_game()

        assert sess.state.status == 'finished'
        assert sess.state.winner == 'robot'

    def test_un_echec_est_visible_dans_l_etat(self, session):
        sess, _, boucle = session
        boucle.side_effect = RuntimeError('caméra perdue')

        with pytest.raises(RuntimeError):
            sess.play_one_game()

        assert sess.state.status == 'error'
        assert 'caméra perdue' in sess.state.message

    def test_la_boucle_de_jeu_publie_l_avancement(self, session):
        """C'est ce que l'interface web affichera pendant la partie."""
        sess, _, boucle = session
        plateau = EMPTY.copy()
        plateau[4] = CUBE

        def jouer(playground, report=None):
            report(status='playing', board=plateau, current_player='human')
            return 'nobody'

        boucle.side_effect = jouer

        sess.play_one_game()

        # L'état publié pendant la partie doit avoir été vu…
        assert sess.state.games_played == 1
        # …et l'état final reste cohérent.
        assert sess.state.winner == 'nobody'

    def test_l_etat_est_un_instantane_fige(self, session):
        """Le lecteur (serveur web) ne doit pas voir l'état muter sous lui."""
        sess, _, _ = session
        avant = sess.state

        sess.play_one_game()

        assert avant.status == 'idle'
        assert sess.state is not avant

    def test_les_abonnes_sont_notifies(self, session):
        sess, _, _ = session
        recus = []
        sess.subscribe(recus.append)

        sess.play_one_game()

        assert [e.status for e in recus][-1] == 'finished'
        assert all(isinstance(e, GameState) for e in recus)

    def test_un_abonne_qui_plante_ne_casse_pas_la_partie(self, session):
        sess, _, _ = session
        sess.subscribe(MagicMock(side_effect=RuntimeError('navigateur fermé')))

        assert sess.play_one_game() == 'robot'
