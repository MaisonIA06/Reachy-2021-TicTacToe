"""Tests des tables de correspondance pièces/joueurs (reachy_tictactoe.utils)."""
from reachy_tictactoe.utils import piece2id, id2piece, piece2player


def test_piece2id_convention_2021():
    # ⚠️ Convention inversée vs code Pollen 2019 :
    # Reachy joue les cubes, l'humain les cylindres.
    assert piece2id == {'none': 0, 'cube': 1, 'cylinder': 2}


def test_id2piece_est_l_inverse_de_piece2id():
    for piece, id_ in piece2id.items():
        assert id2piece[id_] == piece


def test_piece2player():
    assert piece2player['cube'] == 'robot'
    assert piece2player['cylinder'] == 'human'
    assert piece2player['none'] == 'nobody'
