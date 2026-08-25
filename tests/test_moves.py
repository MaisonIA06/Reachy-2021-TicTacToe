"""Tests des mouvements enregistrés (reachy_tictactoe.moves).

Vérifie que tous les fichiers .npz nécessaires au jeu sont présents et
bien formés — c'est ce qui casse en premier quand on réenregistre les
mouvements après un déplacement du plateau.

Deux formats coexistent, et le jeu dépend de cette distinction :
- POSES (0-d, un scalaire par joint) : consommées par goto_position
  → grab_1..5, lift, back_1..9_upright ;
- TRAJECTOIRES (1-d, échantillonnées à 100 Hz) : consommées par
  play_trajectory → put_N_smooth_10_kp, my-turn, your-turn, shuffle-board.
"""
import numpy as np
import pytest

from reachy_tictactoe import config
from reachy_tictactoe.moves import moves, rest_pos, base_pos


POSE_MOVES = (
    [f'grab_{i}' for i in range(1, 6)]
    + [f'back_{i}_upright' for i in range(1, 10)]
    + ['lift']
)

TRAJECTORY_MOVES = (
    [f'put_{i}_smooth_10_kp' for i in range(1, 10)]
    + ['my-turn', 'your-turn', 'shuffle-board']
)

REQUIRED_MOVES = POSE_MOVES + TRAJECTORY_MOVES


@pytest.mark.parametrize('name', REQUIRED_MOVES)
def test_mouvement_requis_present(name):
    assert name in moves, f'Mouvement manquant : {name}.npz'


@pytest.mark.parametrize('name', REQUIRED_MOVES)
def test_mouvement_au_format_sdk_2021(name):
    # Les clés doivent être des noms de joints au format SDK 2021
    # (préfixe r_arm./head.) et les valeurs des positions numériques.
    move = moves[name]
    assert len(move.files) > 0
    for joint_name in move.files:
        assert joint_name.startswith(('r_arm.', 'head.')), (
            f'{name}.npz : joint inattendu {joint_name!r}'
        )
        assert np.issubdtype(np.asarray(move[joint_name]).dtype, np.number)


@pytest.mark.parametrize('name', POSE_MOVES)
def test_les_poses_sont_des_scalaires(name):
    # goto_position attend UNE position cible par joint : un fichier
    # réenregistré par erreur en --type trajectory casserait le jeu.
    move = moves[name]
    for joint_name in move.files:
        assert np.asarray(move[joint_name]).ndim == 0, (
            f'{name}.npz : {joint_name} devrait être un scalaire (pose), '
            f'pas une trajectoire'
        )


@pytest.mark.parametrize('name', TRAJECTORY_MOVES)
def test_les_trajectoires_sont_echantillonnees_uniformement(name):
    # play_trajectory rejoue les points à 100 Hz : chaque joint doit
    # fournir une série 1-d, de même longueur que les autres.
    move = moves[name]
    lengths = set()
    for joint_name in move.files:
        arr = np.asarray(move[joint_name])
        assert arr.ndim == 1, (
            f'{name}.npz : {joint_name} devrait être une trajectoire 1-d'
        )
        lengths.add(len(arr))
    assert len(lengths) == 1, f'{name}.npz : longueurs incohérentes {lengths}'
    assert lengths.pop() > 1


def test_positions_de_repos_et_de_base():
    # base_pos = rest_pos + gripper ouvert (valeur de calibration config.py)
    assert set(base_pos) == set(rest_pos) | {'r_arm.r_gripper'}
    assert base_pos['r_arm.r_gripper'] == config.GRIPPER_OPEN
    for joint_name in rest_pos:
        assert joint_name.startswith('r_arm.')
        assert base_pos[joint_name] == rest_pos[joint_name]
