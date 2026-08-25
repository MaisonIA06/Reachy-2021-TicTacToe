"""Tests de la logique de jeu pure de TictactoePlayground.

Ces tests n'ont pas besoin du robot : le SDK est remplacé par un stub
(voir conftest.py) et seules les méthodes sans effet matériel sont testées.

Rappel de la convention : Reachy = cubes (1), humain = cylindres (2).
"""
import numpy as np
import pytest
from unittest.mock import MagicMock

from helpers import CUBE, CYLINDER, board, empty_board
from reachy_tictactoe.tictactoe_playground import game_status_text


EMPTY = empty_board()


# ---------------------------------------------------------------------------
# get_winner / is_final
# ---------------------------------------------------------------------------

class TestGetWinner:
    def test_plateau_vide_personne_ne_gagne(self, playground):
        assert playground.get_winner(EMPTY) == 'nobody'

    @pytest.mark.parametrize('line', [(0, 1, 2), (3, 4, 5), (6, 7, 8)])
    def test_ligne_de_cubes_le_robot_gagne(self, playground, line):
        b = EMPTY.copy()
        b[list(line)] = CUBE
        assert playground.get_winner(b) == 'robot'

    @pytest.mark.parametrize('col', [(0, 3, 6), (1, 4, 7), (2, 5, 8)])
    def test_colonne_de_cylindres_l_humain_gagne(self, playground, col):
        b = EMPTY.copy()
        b[list(col)] = CYLINDER
        assert playground.get_winner(b) == 'human'

    @pytest.mark.parametrize('diag', [(0, 4, 8), (2, 4, 6)])
    def test_diagonale_gagnante(self, playground, diag):
        b = EMPTY.copy()
        b[list(diag)] = CUBE
        assert playground.get_winner(b) == 'robot'

    def test_partie_en_cours_sans_alignement(self, playground):
        b = board(CUBE, CYLINDER, 0,
                  0, CUBE, 0,
                  0, 0, CYLINDER)
        assert playground.get_winner(b) == 'nobody'

    def test_plateau_plein_sans_alignement_egalite(self, playground):
        b = board(CUBE, CYLINDER, CUBE,
                  CUBE, CYLINDER, CYLINDER,
                  CYLINDER, CUBE, CUBE)
        assert playground.get_winner(b) == 'nobody'


class TestIsFinal:
    def test_plateau_vide_partie_non_finie(self, playground):
        assert not playground.is_final(EMPTY)

    def test_victoire_termine_la_partie(self, playground):
        b = EMPTY.copy()
        b[[0, 1, 2]] = CUBE
        assert playground.is_final(b)

    def test_plateau_plein_termine_la_partie(self, playground):
        b = board(CUBE, CYLINDER, CUBE,
                  CUBE, CYLINDER, CYLINDER,
                  CYLINDER, CUBE, CUBE)
        assert playground.is_final(b)

    def test_partie_en_cours_non_finie(self, playground):
        b = EMPTY.copy()
        b[0] = CUBE
        b[4] = CYLINDER
        assert not playground.is_final(b)


# ---------------------------------------------------------------------------
# has_human_played
# ---------------------------------------------------------------------------

class TestHasHumanPlayed:
    def test_aucun_changement(self, playground):
        assert not playground.has_human_played(EMPTY.copy(), EMPTY.copy())

    def test_cylindre_ajoute_l_humain_a_joue(self, playground):
        current = EMPTY.copy()
        current[4] = CYLINDER
        assert playground.has_human_played(current, EMPTY.copy())

    def test_cube_ajoute_ce_n_est_pas_l_humain(self, playground):
        current = EMPTY.copy()
        current[4] = CUBE
        assert not playground.has_human_played(current, EMPTY.copy())


# ---------------------------------------------------------------------------
# incoherent_board_detected
# ---------------------------------------------------------------------------

class TestIncoherentBoard:
    def test_plateau_vide_coherent(self, playground):
        assert not playground.incoherent_board_detected(EMPTY)

    def test_un_pion_d_ecart_coherent(self, playground):
        b = board(CUBE, CYLINDER, CUBE,
                  0, 0, 0,
                  0, 0, 0)
        assert not playground.incoherent_board_detected(b)

    def test_deux_pions_d_ecart_incoherent(self, playground):
        b = board(CUBE, CUBE, CUBE,
                  CYLINDER, 0, 0,
                  0, 0, 0)
        assert playground.incoherent_board_detected(b)


# ---------------------------------------------------------------------------
# cheating_detected
# ---------------------------------------------------------------------------

class TestCheatingDetected:
    def test_aucun_changement_pas_de_triche(self, playground):
        assert not playground.cheating_detected(
            EMPTY.copy(), EMPTY.copy(), reachy_turn=True)

    def test_cylindre_ajoute_pas_de_triche(self, playground):
        current = EMPTY.copy()
        current[4] = CYLINDER
        assert not playground.cheating_detected(
            current, EMPTY.copy(), reachy_turn=False)

    def test_cube_ajoute_hors_tour_robot_triche(self, playground):
        current = EMPTY.copy()
        current[4] = CUBE
        assert playground.cheating_detected(
            current, EMPTY.copy(), reachy_turn=False)

    def test_cube_ajoute_pendant_tour_robot_pas_de_triche(self, playground):
        current = EMPTY.copy()
        current[4] = CUBE
        assert not playground.cheating_detected(
            current, EMPTY.copy(), reachy_turn=True)

    def test_deux_cubes_ajoutes_triche(self, playground):
        current = EMPTY.copy()
        current[[3, 5]] = CUBE
        assert playground.cheating_detected(
            current, EMPTY.copy(), reachy_turn=True)

    def test_retrait_d_un_cylindre_triche(self, playground):
        # Retirer une pièce du plateau est une manipulation (delta négatif :
        # le calcul ne doit pas déborder sur des uint8).
        last = EMPTY.copy()
        last[4] = CYLINDER
        assert playground.cheating_detected(
            EMPTY.copy(), last, reachy_turn=False)

    def test_retrait_d_un_cube_triche(self, playground):
        last = EMPTY.copy()
        last[4] = CUBE
        assert playground.cheating_detected(
            EMPTY.copy(), last, reachy_turn=False)

    def test_deplacement_d_un_cylindre_triche(self, playground):
        # Faire glisser une pièce déjà posée (retrait + ajout simultanés)
        # est une manipulation : elle ne doit pas passer pour un coup légal.
        last = EMPTY.copy()
        last[0] = CYLINDER
        current = EMPTY.copy()
        current[4] = CYLINDER
        assert playground.cheating_detected(
            current, last, reachy_turn=False)

    def test_deplacement_d_un_cube_triche(self, playground):
        last = EMPTY.copy()
        last[0] = CUBE
        current = EMPTY.copy()
        current[4] = CUBE
        assert playground.cheating_detected(
            current, last, reachy_turn=True)


# ---------------------------------------------------------------------------
# choose_next_action / reset / is_ready
# ---------------------------------------------------------------------------

class TestChooseNextAction:
    def test_plateau_vide_evite_la_case_9(self, playground):
        # La case 9 (index 8) est exclue en ouverture (contrainte mécanique).
        np.random.seed(0)  # tirage aléatoire reproductible
        for _ in range(30):
            action, _ = playground.choose_next_action(EMPTY.copy())
            assert action != 8
            assert 0 <= action <= 7

    def test_retourne_une_case_vide(self, playground):
        b = board(CUBE, CYLINDER, 0,
                  0, CUBE, CYLINDER,
                  0, 0, 0)
        action, _ = playground.choose_next_action(b)
        assert b[action] == 0

    def test_humain_a_joue_en_premier_case_9_evitee(self, playground):
        b = EMPTY.copy()
        b[4] = CYLINDER  # un seul cylindre : l'humain vient d'ouvrir
        action, _ = playground.choose_next_action(b)
        assert action != 8
        assert b[action] == 0

    def test_humain_a_ouvert_et_meilleure_action_est_8_prend_la_suivante(
            self, playground, monkeypatch):
        b = EMPTY.copy()
        b[4] = CYLINDER
        monkeypatch.setattr(
            'reachy_tictactoe.tictactoe_playground.value_actions',
            lambda board: [(8, 0.9), (2, 0.5), (0, 0.1)])
        action, value = playground.choose_next_action(b)
        assert (action, value) == (2, 0.5)

    def test_deux_cubes_sans_cylindre_prend_la_meilleure_action(
            self, playground, monkeypatch):
        # Un plateau à deux cubes a aussi une somme de 2 : il ne doit PAS
        # être confondu avec « l'humain a ouvert avec un cylindre » et
        # doit prendre la meilleure action, même si c'est la case 9.
        b = EMPTY.copy()
        b[[0, 1]] = CUBE
        monkeypatch.setattr(
            'reachy_tictactoe.tictactoe_playground.value_actions',
            lambda board: [(8, 0.9), (2, 0.5), (3, 0.1)])
        action, value = playground.choose_next_action(b)
        assert (action, value) == (8, 0.9)


class TestPlay:
    def test_play_pose_un_cube_et_incremente_le_compteur(
            self, playground, monkeypatch):
        monkeypatch.setattr(playground, 'play_pawn', MagicMock())

        result = playground.play(4, EMPTY.copy())

        assert result[4] == CUBE
        assert playground.pawn_played == 1
        # 1er pion pris (grab_1), posé dans la case 5 (action 4 + 1)
        playground.play_pawn.assert_called_once_with(grab_index=1, box_index=5)

    def test_play_ne_modifie_pas_le_plateau_d_entree(
            self, playground, monkeypatch):
        monkeypatch.setattr(playground, 'play_pawn', MagicMock())

        original = EMPTY.copy()
        playground.play(0, original)

        assert np.all(original == 0)


# ---------------------------------------------------------------------------
# Texte de statut de l'affichage (display_board)
# ---------------------------------------------------------------------------

ROUGE = (0, 0, 255)  # BGR — couleur des X du robot
BLEU = (255, 0, 0)   # BGR — couleur des O de l'humain


class TestGameStatusText:
    """Reachy joue les X (cubes), l'humain les O (cylindres) : le texte
    et la couleur du statut doivent être cohérents avec le dessin."""

    def test_tour_du_robot(self):
        text, color = game_status_text(current_player='robot')
        assert 'X' in text and 'O' not in text
        assert color == ROUGE

    def test_tour_de_l_humain(self):
        text, color = game_status_text(current_player='human')
        assert 'O' in text and 'X' not in text
        assert color == BLEU

    def test_victoire_du_robot(self):
        text, color = game_status_text(winner='robot')
        assert 'Reachy' in text
        assert color == ROUGE

    def test_victoire_de_l_humain(self):
        text, color = game_status_text(winner='human')
        assert 'Vous' in text and 'gagne' in text
        assert color == BLEU

    def test_egalite(self):
        text, _ = game_status_text(winner='nobody')
        assert 'Egalite' in text

    def test_partie_annulee_apres_triche(self):
        # 'aborted' (partie annulée) ne doit surtout pas s'afficher
        # comme une égalité.
        text, _ = game_status_text(winner='aborted')
        assert 'annulee' in text
        assert 'Egalite' not in text

    def test_partie_en_cours_sans_joueur(self):
        text, _ = game_status_text()
        assert text == 'Partie en cours'


class TestResetAndReady:
    def test_reset_retourne_un_plateau_vide(self, playground):
        playground.pawn_played = 3
        b = playground.reset()

        assert playground.pawn_played == 0
        assert b.shape == (9,)
        assert np.all(b == 0)

    def test_is_ready_plateau_vide(self, playground):
        assert playground.is_ready(EMPTY)

    def test_is_ready_faux_si_pion_present(self, playground):
        b = EMPTY.copy()
        b[0] = CYLINDER
        assert not playground.is_ready(b)
