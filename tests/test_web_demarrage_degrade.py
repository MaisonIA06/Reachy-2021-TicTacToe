"""L'interface doit se lever même si le robot ne répond pas.

⚠️ Incident du 2026-09-21. Au démarrage du robot, une panne NTP a tué
``ros2_control_node`` : le port gRPC 50055 n'a jamais répondu, l'interface
a planté puis s'est relancée **30 fois** sans succès. L'utilisateur n'a
trouvé qu'une page injoignable.

Le point critique n'est pas l'indisponibilité, c'est que le bouton
« Réparer » vit DANS l'interface : il devient inaccessible exactement dans
le seul cas où il sert. Le serveur doit donc démarrer **sans robot**,
afficher son bandeau, garder « Réparer » cliquable, et se connecter tout
seul dès que le SDK répond — sans redémarrage du service.
"""
from unittest.mock import MagicMock

import pytest

from reachy_tictactoe.game_launcher import GameState

fastapi_testclient = pytest.importorskip(
    'fastapi.testclient', reason='fastapi requis pour les tests web')


class RobotAbsent(Exception):
    """Ce que lève le SDK quand le port 50055 refuse la connexion."""


def _session_factice():
    session = MagicMock()
    session.state = GameState(status='idle', board=(0,) * 9)
    session.playground.reachy.right_camera.last_frame = None
    controller = MagicMock()
    controller.running = None
    controller.last_error = None
    return session, controller


@pytest.fixture
def lien_rompu():
    """Lien qui échoue à chaque tentative."""
    from reachy_tictactoe.webapp.link import RobotLink

    def connexion_impossible():
        raise RobotAbsent('Connection refused (111) sur 127.0.0.1:50055')

    return RobotLink(connect=connexion_impossible, sleep=lambda duree: None)


@pytest.fixture
def client_sans_robot(lien_rompu):
    from reachy_tictactoe.webapp.server import create_app

    lien_rompu.attempt()  # une tentative, qui échoue
    app = create_app(link=lien_rompu, health=MagicMock(status='frozen'))
    return fastapi_testclient.TestClient(app), lien_rompu


# ---------------------------------------------------------------------------
# Le serveur se lève quand même
# ---------------------------------------------------------------------------

class TestServeurSansRobot:

    def test_la_page_se_charge(self, client_sans_robot):
        """La condition de tout le reste : sans page, aucun bouton."""
        http, _ = client_sans_robot
        assert http.get('/').status_code == 200

    def test_l_etat_est_lisible_et_annonce_la_deconnexion(self,
                                                          client_sans_robot):
        http, _ = client_sans_robot

        reponse = http.get('/api/state')

        assert reponse.status_code == 200
        data = reponse.json()
        assert data['game']['status'] == 'disconnected'
        assert data['robot']['link'] == 'connecting'
        assert data['game']['message'], (
            "l'écran doit dire POURQUOI il ne se passe rien"
        )

    def test_la_surveillance_moteur_fonctionne_sans_sdk(self,
                                                        client_sans_robot):
        """MotorHealth lit /proc, pas le SDK : c'est justement ce verdict
        qui justifie d'afficher le bouton « Réparer »."""
        http, _ = client_sans_robot
        assert http.get('/api/state').json()['robot']['motors'] == 'frozen'

    def test_la_cause_de_l_echec_est_remontee(self, client_sans_robot):
        http, _ = client_sans_robot
        assert 'Connection refused' in (
            http.get('/api/state').json()['robot']['last_error'] or '')


class TestReparerResteAccessible:

    def test_reparer_repond_sans_robot(self, client_sans_robot, monkeypatch):
        """LE point de tout ce chantier."""
        import reachy_tictactoe.webapp.server as server

        lance = []
        monkeypatch.setattr(server.subprocess, 'Popen',
                            lambda cmd, **kwargs: lance.append(cmd))
        monkeypatch.setattr(server.os.path, 'exists', lambda chemin: True)

        http, _ = client_sans_robot
        reponse = http.post('/api/system/recover')

        assert reponse.status_code == 202, (
            'sans cela, la panne ne serait réparable que par SSH'
        )
        assert lance, 'le script de récupération doit être lancé'


class TestActionsRefuseesProprement:

    @pytest.mark.parametrize('route', ['/api/game', '/api/moves-check'])
    def test_les_actions_robot_sont_refusees(self, client_sans_robot, route):
        """Refus explicite plutôt qu'une pile d'appels gRPC dans les logs."""
        http, _ = client_sans_robot
        reponse = http.post(route)
        assert reponse.status_code == 503
        assert 'robot' in reponse.json()['detail'].lower()

    def test_la_camera_est_refusee_sans_robot(self, client_sans_robot):
        http, _ = client_sans_robot
        assert http.get('/api/camera.jpg').status_code == 503


# ---------------------------------------------------------------------------
# La connexion se fait toute seule, sans redémarrage
# ---------------------------------------------------------------------------

class TestConnexionDifferee:

    def test_le_lien_retente_jusqu_au_succes(self):
        from reachy_tictactoe.webapp.link import RobotLink

        tentatives = {'n': 0}

        def connexion_capricieuse():
            tentatives['n'] += 1
            if tentatives['n'] < 3:
                raise RobotAbsent('pas encore')
            return _session_factice()

        attentes = []
        lien = RobotLink(connect=connexion_capricieuse,
                         delay=5.0, sleep=attentes.append)

        lien.run_until_connected()

        assert tentatives['n'] == 3
        assert lien.status == 'connected'
        assert lien.session is not None
        assert attentes == [5.0, 5.0], (
            'il faut patienter entre deux tentatives, pas marteler le port'
        )

    def test_l_interface_reprend_vie_sans_redemarrage(self, lien_rompu):
        """Une fois connecté, le serveur DÉJÀ démarré doit servir le vrai
        état : c'est ce qui évite le redémarrage du service."""
        from reachy_tictactoe.webapp.server import create_app

        lien_rompu.attempt()
        app = create_app(link=lien_rompu)
        http = fastapi_testclient.TestClient(app)
        assert http.get('/api/state').json()['game']['status'] == 'disconnected'

        session, controller = _session_factice()
        session.state = GameState(status='playing', board=(1,) + (0,) * 8)
        lien_rompu.adopt(session, controller)

        data = http.get('/api/state').json()
        assert data['game']['status'] == 'playing'
        assert data['robot']['link'] == 'connected'

    def test_les_actions_redeviennent_possibles(self, lien_rompu):
        from reachy_tictactoe.webapp.server import create_app

        lien_rompu.attempt()
        app = create_app(link=lien_rompu)
        http = fastapi_testclient.TestClient(app)
        assert http.post('/api/game').status_code == 503

        session, controller = _session_factice()
        lien_rompu.adopt(session, controller)

        assert http.post('/api/game').status_code == 202
        controller.start_game.assert_called_once()


# ---------------------------------------------------------------------------
# Compatibilité : l'ancien appel direct reste valable
# ---------------------------------------------------------------------------

def test_create_app_accepte_encore_session_et_controller():
    """Les tests existants et tout appelant tiers passent session=/controller=."""
    from reachy_tictactoe.webapp.server import create_app

    session, controller = _session_factice()
    http = fastapi_testclient.TestClient(
        create_app(session=session, controller=controller))

    data = http.get('/api/state').json()
    assert data['game']['status'] == 'idle'
    assert data['robot']['link'] == 'connected'


# ---------------------------------------------------------------------------
# Câblage du point d'entrée
# ---------------------------------------------------------------------------

def test_connect_robot_repose_les_moteurs(monkeypatch):
    """setup() alimente bras et tête ; l'interface peut ensuite attendre
    des heures sans clic. Sans rest(), les moteurs chaufferaient à vide."""
    import reachy_tictactoe.webapp.__main__ as entree

    playground = MagicMock()
    monkeypatch.setattr(entree, 'TictactoePlayground',
                        lambda host: playground)
    session = MagicMock()
    monkeypatch.setattr(entree, 'GameSession', lambda pg: session)
    monkeypatch.setattr(entree, 'RobotController', lambda s: MagicMock())

    resultat = entree.connect_robot('localhost')

    playground.setup.assert_called_once()
    session.rest.assert_called_once()
    assert resultat[0] is session


def test_connect_robot_propage_l_echec(monkeypatch):
    """L'échec doit remonter au lien, qui retentera — surtout pas être
    avalé, sinon l'interface se croirait connectée."""
    import reachy_tictactoe.webapp.__main__ as entree

    def sdk_absent(host):
        raise RobotAbsent('Connection refused (111)')

    monkeypatch.setattr(entree, 'TictactoePlayground', sdk_absent)

    with pytest.raises(RobotAbsent):
        entree.connect_robot('localhost')


# ---------------------------------------------------------------------------
# Corrections issues de la revue
# ---------------------------------------------------------------------------

def test_l_etat_deconnecte_ne_sature_pas_le_flux_sse(lien_rompu):
    """⚠️ GameState.updated_at vaut time.time() par défaut.

    Un état reconstruit à chaque appel différerait du précédent : le flux
    SSE émettrait toutes les 0,3 s pendant toute la panne, au lieu du
    battement de 8 s. Une panne peut durer des heures.
    """
    from reachy_tictactoe.webapp.server import _snapshot, should_emit

    lien_rompu.attempt()
    premier = _snapshot(lien_rompu)
    second = _snapshot(lien_rompu)

    assert premier == second
    assert should_emit(second, premier, 0.3) is False


def test_le_playground_est_ferme_si_le_setup_echoue(monkeypatch):
    """Le SDK peut répondre alors que ros2_control_node est mort.

    Sans fermeture, chaque tentative abandonnerait un canal gRPC et son
    fil de synchronisation — toutes les 5 s, indéfiniment.
    """
    import reachy_tictactoe.webapp.__main__ as entree

    playground = MagicMock()
    playground.setup.side_effect = RobotAbsent('contrôleur moteur mort')
    monkeypatch.setattr(entree, 'TictactoePlayground', lambda host: playground)

    with pytest.raises(RobotAbsent):
        entree.connect_robot('localhost')

    playground.close.assert_called_once()


def test_le_playground_est_publie_avant_le_setup(monkeypatch):
    """setup() alimente les moteurs et dure plusieurs secondes.

    Si le service s'arrête pendant ce temps — `recover_sdk.sh` nous
    relance juste après le retour du contrôleur — le fil démon est tué
    net. Sans publication précoce, les moteurs resteraient sous tension.
    """
    import reachy_tictactoe.webapp.__main__ as entree

    ordre = []
    playground = MagicMock()
    playground.setup.side_effect = lambda: ordre.append('setup')
    monkeypatch.setattr(entree, 'TictactoePlayground', lambda host: playground)
    monkeypatch.setattr(entree, 'GameSession', lambda pg: MagicMock())
    monkeypatch.setattr(entree, 'RobotController', lambda s: MagicMock())

    entree.connect_robot('localhost',
                         register=lambda pg: ordre.append('publie'))

    assert ordre == ['publie', 'setup']
