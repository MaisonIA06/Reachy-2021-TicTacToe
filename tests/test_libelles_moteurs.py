"""Fenêtre des températures : chaque moteur avec son nom.

« Relever » n'affichait qu'un nombre — le moteur le plus chaud — sans dire
lequel. Le détail existait dans une infobulle au survol, invisible sur
tablette et introuvable ailleurs. La fenêtre liste désormais tous les
moteurs, avec un libellé français à côté du nom technique du SDK.
"""
from unittest.mock import MagicMock

import pytest


#: Les 21 moteurs tels que le robot les nomme (relevé du 2026-09-28).
#: Les trois axes du cou ne remontent pas de température.
MOTEURS_DU_ROBOT = [
    'r_shoulder_pitch', 'r_shoulder_roll', 'r_arm_yaw', 'r_elbow_pitch',
    'r_forearm_yaw', 'r_wrist_pitch', 'r_wrist_roll', 'r_gripper',
    'l_shoulder_pitch', 'l_shoulder_roll', 'l_arm_yaw', 'l_elbow_pitch',
    'l_forearm_yaw', 'l_wrist_pitch', 'l_wrist_roll', 'l_gripper',
    'r_antenna', 'l_antenna',
    'neck_yaw', 'neck_pitch', 'neck_roll',
]


class TestLibelles:

    @pytest.mark.parametrize('nom', MOTEURS_DU_ROBOT)
    def test_chaque_moteur_du_robot_a_un_libelle_francais(self, nom):
        from reachy_tictactoe.webapp.joints import label

        libelle = label(nom)
        assert libelle != nom, f'{nom} : pas de libellé, le nom technique s’afficherait seul'
        assert '_' not in libelle, f'{nom} : {libelle!r} ressemble à un nom technique'

    def test_droite_et_gauche_sont_distinguees(self):
        from reachy_tictactoe.webapp.joints import label

        assert label('r_gripper') != label('l_gripper')
        assert 'droit' in label('r_gripper').lower()
        assert 'gauche' in label('l_gripper').lower()

    @pytest.mark.parametrize('nom, attendu', [
        ('r_elbow_pitch', 'Coude droit'),                 # masculin
        ('r_arm_yaw', 'Bras droit (rotation)'),
        ('r_forearm_yaw', 'Avant-bras droit (rotation)'),
        ('r_wrist_roll', 'Poignet droit (roulis)'),
        ('r_shoulder_pitch', 'Épaule droite (tangage)'),  # féminin
        ('r_gripper', 'Pince droite'),
        ('r_antenna', 'Antenne droite'),
        ('l_elbow_pitch', 'Coude gauche'),
        ('neck_yaw', 'Cou (lacet)'),
    ])
    def test_le_cote_s_accorde_en_genre(self, nom, attendu):
        """« Coude droite » s'affichait : le côté doit s'accorder avec le
        nom du segment, pas être le même mot partout."""
        from reachy_tictactoe.webapp.joints import label
        assert label(nom) == attendu

    def test_un_nom_inconnu_retombe_sur_le_nom_technique(self):
        """Un moteur inattendu doit s'afficher plutôt que faire planter
        la fenêtre — le nom technique vaut mieux que rien."""
        from reachy_tictactoe.webapp.joints import label

        assert label('mystery_motor') == 'mystery_motor'


# ---------------------------------------------------------------------------
# API : les libellés et le moteur le plus chaud voyagent avec le relevé
# ---------------------------------------------------------------------------

def _client(temperatures):
    fastapi_testclient = pytest.importorskip(
        'fastapi.testclient', reason='fastapi requis pour les tests web')
    from reachy_tictactoe.game_launcher import GameState
    from reachy_tictactoe.webapp.server import create_app

    session = MagicMock()
    session.state = GameState(status='idle', board=(0,) * 9)
    session.playground.reachy.right_camera.last_frame = None
    session.playground.read_temperatures.return_value = temperatures
    controller = MagicMock()
    controller.running = None
    controller.last_error = None
    return fastapi_testclient.TestClient(
        create_app(session=session, controller=controller))


class TestApi:

    def test_les_libelles_accompagnent_chaque_moteur(self):
        http = _client({'r_gripper': 44.0, 'neck_yaw': None})

        data = http.get('/api/temperatures').json()

        assert set(data['labels']) == {'r_gripper', 'neck_yaw'}
        assert data['labels']['r_gripper'] != 'r_gripper'

    def test_le_moteur_le_plus_chaud_est_nomme(self):
        """La valeur du panneau doit dire DE QUEL moteur il s'agit."""
        http = _client({'r_gripper': 44.0, 'l_gripper': 47.0, 'neck_yaw': None})

        data = http.get('/api/temperatures').json()

        assert data['hottest'] == 'l_gripper'
        assert data['max'] == 47.0

    def test_sans_aucune_valeur_pas_de_moteur_le_plus_chaud(self):
        http = _client({'neck_yaw': None, 'neck_pitch': None})

        data = http.get('/api/temperatures').json()

        assert data['hottest'] is None
        assert data['max'] is None
