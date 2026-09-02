"""Calibration depuis le navigateur.

Deux pièges, tous deux silencieux :

1. **Deux repères.** Le navigateur travaille en pixels de l'image entière,
   mais ``config.BOARD_CASES`` est relatif au plateau recadré. Une
   conversion oubliée décale les cases de l'offset du plateau sans que
   rien ne le signale.
2. **Valeurs figées à l'import.** ``vision.py`` lit la calibration une
   seule fois, dans des variables de module. Écrire dans ``config.py`` ne
   suffit donc pas : sans rechargement explicite, l'utilisateur calibre,
   voit « enregistré », et la vision continue d'utiliser les anciennes
   valeurs jusqu'au redémarrage.
"""
import numpy as np
import pytest

from reachy_tictactoe.webapp.calibration import (
    cases_to_relative,
    rects_from_config,
    validate_calibration,
)


BOARD = {'x': 100, 'y': 200, 'width': 300, 'height': 300}
IMAGE = {'width': 480, 'height': 640}


@pytest.fixture(autouse=True)
def _restaure_calibration():
    """apply_calibration mute des globales de module.

    Sans restauration, un test de calibration contaminerait toute la
    session pytest et provoquerait des échecs dépendants de l'ordre.
    """
    from reachy_tictactoe import config, vision

    position = dict(config.BOARD_POSITION)
    cases = config.BOARD_CASES.copy()
    v_cases, v_rect = vision.board_cases.copy(), vision.board_rect.copy()
    yield
    config.BOARD_POSITION.clear()
    config.BOARD_POSITION.update(position)
    config.BOARD_CASES = cases
    vision.board_cases, vision.board_rect = v_cases, v_rect


def _grille(board=BOARD):
    """9 cases régulières à l'intérieur du plateau, en absolu."""
    w, h = board['width'] // 3, board['height'] // 3
    return [
        {'x': board['x'] + col * w, 'y': board['y'] + row * h,
         'width': w, 'height': h}
        for row in range(3) for col in range(3)
    ]


class TestConversionDesReperes:

    def test_les_cases_deviennent_relatives_au_plateau(self):
        cases = cases_to_relative(BOARD, _grille())

        # Case 1 : coin haut-gauche du plateau -> (0, 100, 0, 100)
        assert tuple(cases[0][0]) == (0, 100, 0, 100)
        # Case 9 : coin bas-droite -> (200, 300, 200, 300)
        assert tuple(cases[2][2]) == (200, 300, 200, 300)

    def test_la_forme_attendue_par_save_calibration_est_respectee(self):
        cases = cases_to_relative(BOARD, _grille())

        assert isinstance(cases, np.ndarray)
        assert cases.shape == (3, 3, 4), 'save_calibration attend du 3x3x4'
        assert np.issubdtype(cases.dtype, np.integer)

    def test_l_ordre_des_cases_suit_la_lecture(self):
        """Les 9 cases arrivent dans l'ordre 1..9, lignes puis colonnes."""
        cases = cases_to_relative(BOARD, _grille())

        assert cases[0][1][0] == 100, 'la case 2 est à droite de la case 1'
        assert cases[1][0][2] == 100, 'la case 4 est sous la case 1'

    def test_aller_retour_sans_perte(self):
        """rects_from_config est l'inverse de cases_to_relative."""
        board_position = {'left_x': 100, 'right_x': 400,
                          'top_y': 200, 'bottom_y': 500}
        relatives = cases_to_relative(BOARD, _grille())

        zone, absolues = rects_from_config(board_position, relatives)

        assert zone == BOARD
        assert absolues == _grille()


class TestValidation:
    """Une calibration absurde écrirait dans config.py et casserait la
    vision jusqu'à ce que quelqu'un rouvre le fichier à la main."""

    def test_une_calibration_correcte_passe(self):
        assert validate_calibration(BOARD, _grille()) == []

    def test_il_faut_exactement_neuf_cases(self):
        erreurs = validate_calibration(BOARD, _grille()[:8])

        assert erreurs and '9' in erreurs[0]

    def test_un_plateau_de_taille_nulle_est_refuse(self):
        erreurs = validate_calibration(
            {'x': 10, 'y': 10, 'width': 0, 'height': 50}, _grille())

        assert erreurs

    def test_une_case_hors_du_plateau_est_refusee(self):
        cases = _grille()
        cases[4] = {'x': 5, 'y': 5, 'width': 50, 'height': 50}

        erreurs = validate_calibration(BOARD, cases)

        assert any('5' in e for e in erreurs), (
            'l\'erreur doit désigner la case fautive'
        )

    def test_une_case_vide_est_refusee(self):
        cases = _grille()
        cases[0] = {'x': 100, 'y': 200, 'width': 0, 'height': 40}

        assert validate_calibration(BOARD, cases)

    def test_des_coordonnees_negatives_sont_refusees(self):
        """numpy découperait depuis le bord opposé, et le regex de
        save_calibration (\\d+) ne re-matcherait plus la valeur écrite :
        fichier et mémoire divergeraient en silence."""
        board = {'x': -10, 'y': 200, 'width': 300, 'height': 300}

        assert validate_calibration(board, _grille(board))

    def test_un_plateau_qui_deborde_de_l_image_est_refuse(self):
        """Hors cadre, les 9 découpes seraient vides : le plateau
        paraîtrait éternellement vide, sans la moindre erreur."""
        board = {'x': 300, 'y': 200, 'width': 300, 'height': 300}

        erreurs = validate_calibration(board, _grille(board), image=IMAGE)

        assert erreurs and 'image' in ' '.join(erreurs).lower()

    def test_sans_dimensions_d_image_le_controle_de_cadre_est_saute(self):
        board = {'x': 300, 'y': 200, 'width': 300, 'height': 300}

        assert validate_calibration(board, _grille(board)) == []


class TestPriseEnCompteImmediate:
    """Sans rechargement, la vision garde les valeurs lues à l'import."""

    def test_le_rechargement_met_a_jour_la_vision(self, monkeypatch):
        from reachy_tictactoe import config, vision
        from reachy_tictactoe.webapp.calibration import apply_calibration

        appels = {}
        monkeypatch.setattr(
            config, 'save_calibration',
            lambda board_position, board_cases: appels.update(
                position=board_position, cases=board_cases))

        apply_calibration(BOARD, _grille())

        assert appels, 'la calibration doit être écrite dans config.py'
        # …et surtout être active tout de suite dans la vision.
        assert list(vision.board_rect) == [100, 400, 200, 500]
        assert vision.board_cases.shape == (3, 3, 4)
        assert tuple(vision.board_cases[0][0]) == (0, 100, 0, 100)

    def test_une_calibration_invalide_n_ecrit_rien(self, monkeypatch):
        from reachy_tictactoe import config
        from reachy_tictactoe.webapp.calibration import apply_calibration

        monkeypatch.setattr(
            config, 'save_calibration',
            lambda **kw: pytest.fail('ne doit pas écrire une calibration invalide'))

        with pytest.raises(ValueError):
            apply_calibration(BOARD, _grille()[:3])
