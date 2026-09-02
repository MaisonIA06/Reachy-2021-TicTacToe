"""Calibration du plateau depuis le navigateur.

Le navigateur raisonne en pixels de l'image ENTIÈRE ; ``config.BOARD_CASES``
est relatif au plateau recadré. Toute la conversion entre ces deux repères
est ici, en fonctions pures, pour qu'elle soit testable et qu'on ne la
réécrive pas à trois endroits.

Rectangles côté navigateur : ``{'x', 'y', 'width', 'height'}``.
Rectangles côté config : ``(left, right, top, bottom)``.
"""
import logging

import numpy as np

from .. import config

logger = logging.getLogger('reachy.tictactoe.webapp')


def cases_to_relative(board, cases):
    """Convertit 9 cases absolues en tableau 3x3x4 relatif au plateau.

    Args:
        board: rectangle du plateau, en pixels de l'image entière.
        cases: les 9 rectangles, dans l'ordre de lecture (1 à 9).

    Returns:
        np.ndarray de forme (3, 3, 4), chaque case étant
        ``(left, right, top, bottom)`` — le format attendu par
        ``config.save_calibration``.
    """
    dx, dy = board['x'], board['y']
    relatives = [
        (int(c['x']) - dx,
         int(c['x']) + int(c['width']) - dx,
         int(c['y']) - dy,
         int(c['y']) + int(c['height']) - dy)
        for c in cases
    ]
    return np.array(relatives, dtype=int).reshape(3, 3, 4)


def rects_from_config(board_position, board_cases):
    """Opération inverse : de la config vers des rectangles absolus.

    Sert à alimenter l'interface avec la calibration courante.
    """
    dx, dy = board_position['left_x'], board_position['top_y']
    zone = {
        'x': dx,
        'y': dy,
        'width': board_position['right_x'] - dx,
        'height': board_position['bottom_y'] - dy,
    }
    cases = [
        {'x': int(left) + dx, 'y': int(top) + dy,
         'width': int(right) - int(left), 'height': int(bottom) - int(top)}
        for row in board_cases
        for left, right, top, bottom in row
    ]
    return zone, cases


def validate_calibration(board, cases, image=None):
    """Vérifie une calibration avant de l'écrire.

    ``save_calibration`` réécrit ``config.py`` : une calibration absurde y
    resterait jusqu'à ce que quelqu'un rouvre le fichier à la main.

    Args:
        board: rectangle du plateau, absolu.
        cases: les 9 rectangles, absolus.
        image: dimensions du cadre caméra (``{'width', 'height'}``). Si
            fournies, on refuse une zone qui en sort : les découpes
            seraient vides et le plateau paraîtrait éternellement vide,
            sans la moindre erreur.

    Returns:
        Liste de messages d'erreur, vide si tout va bien.
    """
    erreurs = []

    if len(cases) != 9:
        erreurs.append(f'Il faut exactement 9 cases (reçu : {len(cases)}).')
        return erreurs

    if board['width'] <= 0 or board['height'] <= 0:
        erreurs.append('La zone du plateau est vide.')
        return erreurs

    # Négatif interdit : numpy découperait depuis le bord opposé, et le
    # regex de save_calibration (\d+) ne re-matcherait plus la valeur.
    if board['x'] < 0 or board['y'] < 0:
        erreurs.append('La zone du plateau sort de l\'image (coordonnées '
                       'négatives).')
        return erreurs

    if image and image.get('width') and image.get('height'):
        if (board['x'] + board['width'] > image['width']
                or board['y'] + board['height'] > image['height']):
            erreurs.append(
                f"La zone du plateau sort de l'image "
                f"({image['width']}x{image['height']}).")
            return erreurs

    for i, case in enumerate(cases, start=1):
        if case['width'] <= 0 or case['height'] <= 0:
            erreurs.append(f'La case {i} est vide.')
            continue
        dedans = (
            case['x'] >= board['x']
            and case['y'] >= board['y']
            and case['x'] + case['width'] <= board['x'] + board['width']
            and case['y'] + case['height'] <= board['y'] + board['height']
        )
        if not dedans:
            erreurs.append(f'La case {i} déborde de la zone du plateau.')

    return erreurs


def apply_calibration(board, cases, image=None):
    """Valide, écrit dans ``config.py``, et rend la calibration ACTIVE.

    ⚠️ Écrire dans ``config.py`` ne suffit pas : ``vision.py`` lit la
    calibration une seule fois, à l'import, dans des variables de module.
    Sans le rechargement ci-dessous, l'utilisateur calibrerait, verrait
    « enregistré », et la vision continuerait d'utiliser les anciennes
    valeurs jusqu'au redémarrage du serveur.

    Raises:
        ValueError: si la calibration est invalide (rien n'est écrit).
    """
    erreurs = validate_calibration(board, cases, image=image)
    if erreurs:
        raise ValueError(' '.join(erreurs))

    board_position = {
        'left_x': int(board['x']),
        'right_x': int(board['x']) + int(board['width']),
        'top_y': int(board['y']),
        'bottom_y': int(board['y']) + int(board['height']),
    }
    board_cases = cases_to_relative(board, cases)

    config.save_calibration(board_position=board_position,
                            board_cases=board_cases)

    # Mémoire vive : config d'abord, puis la vision qui en avait pris copie.
    config.BOARD_POSITION.update(board_position)
    config.BOARD_CASES = board_cases

    from .. import vision
    vision.board_cases = board_cases
    vision.board_rect = np.array([
        board_position['left_x'], board_position['right_x'],
        board_position['top_y'], board_position['bottom_y'],
    ])

    logger.info(f'Calibration appliquée : {board_position}')
    return board_position, board_cases
