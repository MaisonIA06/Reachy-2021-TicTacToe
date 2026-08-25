"""Tests de la logique de jeu pure de TictactoePlayground.

Ces tests n'ont pas besoin du robot : le SDK est remplacé par un stub
(voir conftest.py) et seules les méthodes sans effet matériel sont testées.

Rappel de la convention : Reachy = cubes (1), humain = cylindres (2).
"""
import numpy as np
import pytest


CUBE = 1      # pièce du robot
CYLINDER = 2  # pièce de l'humain


def board(*cells):
    """Construit un plateau 9 cases (uint8, comme en production)."""
    assert len(cells) == 9
    return np.array(cells, dtype=np.uint8)


EMPTY = board(0, 0, 0,
              0, 0, 0,
              0, 0, 0)


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
