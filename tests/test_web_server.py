"""API de l'interface web (``webapp.server``).

Le serveur ne parle jamais au SDK : il ne connaît que la ``GameSession``
et le ``RobotController``. Ces tests le vérifient avec un robot factice —
aucune connexion, aucun mouvement.
"""
from unittest.mock import MagicMock

import pytest

from reachy_tictactoe.game_launcher import GameState
from reachy_tictactoe.webapp.controller import RobotBusy

fastapi_testclient = pytest.importorskip(
    'fastapi.testclient', reason='fastapi requis pour les tests web')


@pytest.fixture
def client():
    from reachy_tictactoe.webapp.server import create_app

    session = MagicMock()
    session.state = GameState(status='idle', board=(0,) * 9)
    controller = MagicMock()
    controller.running = None
    controller.last_error = None

    app = create_app(session=session, controller=controller)
    return fastapi_testclient.TestClient(app), session, controller


class TestEtatDuJeu:

    def test_l_etat_est_expose_en_json(self, client):
        http, session, _ = client
        session.state = GameState(status='playing', board=(1, 2, 0, 0, 0, 0, 0, 0, 0),
                                  current_player='human', games_played=3)

        data = http.get('/api/state').json()

        assert data['game']['status'] == 'playing'
        assert data['game']['board'] == [1, 2, 0, 0, 0, 0, 0, 0, 0]
        assert data['game']['current_player'] == 'human'
        assert data['game']['games_played'] == 3

    def test_l_etat_du_robot_accompagne_celui_du_jeu(self, client):
        """L'interface doit savoir griser ses boutons."""
        http, _, controller = client
        controller.running = 'moves_check'

        data = http.get('/api/state').json()

        assert data['robot']['running'] == 'moves_check'
        assert data['robot']['busy'] is True

    def test_le_robot_libre_est_signale(self, client):
        http, _, _ = client

        assert http.get('/api/state').json()['robot']['busy'] is False


class TestActions:

    def test_lancer_une_partie(self, client):
        http, _, controller = client

        reponse = http.post('/api/game')

        assert reponse.status_code == 202
        controller.start_game.assert_called_once()

    def test_tester_les_mouvements(self, client):
        http, _, controller = client

        reponse = http.post('/api/moves-check')

        assert reponse.status_code == 202
        controller.check_moves.assert_called_once()

    def test_une_action_pendant_qu_une_autre_tourne_est_refusee(self, client):
        """409 Conflict : deux actions feraient bouger le même bras."""
        http, _, controller = client
        controller.start_game.side_effect = RobotBusy('moves_check')

        reponse = http.post('/api/game')

        assert reponse.status_code == 409
        assert 'moves_check' in reponse.json()['detail']


class TestPage:

    def test_la_page_est_servie(self, client):
        http, _, _ = client

        reponse = http.get('/')

        assert reponse.status_code == 200
        assert 'text/html' in reponse.headers['content-type']
        assert 'Reachy' in reponse.text

    def test_la_page_porte_la_charte_mia(self, client):
        http, _, _ = client

        page = http.get('/').text

        assert '#1a3a5c' in page or '--mia-navy' in page
        assert '#b5605a' in page or '--mia-terracotta' in page


class TestBattementSSE:
    """Le flux doit prouver qu'il est vivant, pas seulement qu'il a des
    nouvelles : sans battement, un serveur mort et un serveur calme se
    ressemblent, et l'interface afficherait un état périmé en silence.
    """

    def test_un_changement_est_pousse_immediatement(self):
        from reachy_tictactoe.webapp.server import should_emit

        assert should_emit({'a': 1}, {'a': 0}, elapsed=0.0)

    def test_un_etat_identique_est_repousse_apres_le_battement(self):
        from reachy_tictactoe.webapp.server import should_emit

        etat = {'a': 1}
        assert not should_emit(etat, dict(etat), elapsed=1.0, heartbeat=8.0)
        assert should_emit(etat, dict(etat), elapsed=8.0, heartbeat=8.0)

    def test_le_battement_est_plus_court_que_le_delai_du_navigateur(self):
        """L'interface déclare la liaison perdue au bout de 20 s : le
        battement doit passer plusieurs fois avant."""
        from reachy_tictactoe.webapp import server

        assert server.HEARTBEAT_SECONDS <= 10.0


class TestCamera:

    def test_l_image_de_la_camera_est_servie_en_jpeg(self, client):
        import numpy as np

        http, session, _ = client
        session.playground.reachy.right_camera.last_frame = np.zeros(
            (480, 640, 3), dtype=np.uint8)

        reponse = http.get('/api/camera.jpg')

        assert reponse.status_code == 200
        assert reponse.headers['content-type'] == 'image/jpeg'
        assert reponse.content[:2] == b'\xff\xd8'  # en-tête JPEG

    def test_camera_absente_repond_proprement(self, client):
        """Pas d'image = 503, surtout pas une trace de pile dans le navigateur."""
        http, session, _ = client
        session.playground.reachy.right_camera.last_frame = None

        assert http.get('/api/camera.jpg').status_code == 503
