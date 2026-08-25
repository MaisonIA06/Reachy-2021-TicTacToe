"""Tests de l'agent Q-learning (reachy_tictactoe.rl_agent)."""
import numpy as np

from reachy_tictactoe.rl_agent import value_actions


def test_plateau_vide_retourne_les_9_actions():
    board = np.zeros(9, dtype=np.uint8)
    actions = value_actions(board)

    assert len(actions) == 9
    assert sorted(a for a, _ in actions) == list(range(9))


def test_ne_retourne_que_les_cases_vides():
    board = np.zeros(9, dtype=np.uint8)
    board[0] = 1  # cube (robot)
    board[4] = 2  # cylindre (humain)

    actions = value_actions(board)

    played = {0, 4}
    assert len(actions) == 7
    assert all(a not in played for a, _ in actions)


def test_actions_triees_par_valeur_decroissante_pour_le_robot():
    board = np.zeros(9, dtype=np.uint8)
    actions = value_actions(board, next_player=1)

    values = [v for _, v in actions]
    assert values == sorted(values, reverse=True)


def test_le_robot_complete_sa_ligne_gagnante():
    # Robot (1) a déjà les cases 0 et 1 : jouer 2 gagne immédiatement.
    # La Q-table préentraînée doit classer cette action en tête.
    board = np.array([1, 1, 0,
                      2, 2, 0,
                      0, 0, 0], dtype=np.uint8)

    best_action, _ = value_actions(board)[0]
    assert best_action == 2
