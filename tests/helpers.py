"""Constantes et constructeurs de plateaux partagés par les tests.

Rappel de la convention : Reachy = cubes (1), humain = cylindres (2).
"""
import numpy as np


CUBE = 1      # pièce du robot
CYLINDER = 2  # pièce de l'humain


def empty_board():
    """Plateau vide 9 cases (uint8, comme en production)."""
    return np.zeros(9, dtype=np.uint8)


def board(*cells):
    """Construit un plateau 9 cases à partir de ses valeurs."""
    assert len(cells) == 9
    return np.array(cells, dtype=np.uint8)
