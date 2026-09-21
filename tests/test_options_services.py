"""Panneau « Options » : services ponctuels et température.

Plusieurs services de Pollen sont désactivés au démarrage pour ménager les
ressources du NUC. On veut pouvoir les rallumer **ponctuellement** depuis
l'interface, sans les réactiver au boot.

⚠️ Deux exigences de sûreté gouvernent ce module :

1. **Liste blanche stricte.** Le nom du service vient du navigateur. Sans
   liste blanche, une requête forgée pourrait arrêter
   ``reachy_sdk_server`` — et le robot entier avec.
2. **Ponctuel = ``start``, jamais ``enable``.** Réactiver au boot irait
   contre le but recherché : économiser les ressources par défaut.
"""
import subprocess
from unittest.mock import MagicMock

import pytest

fastapi_testclient = pytest.importorskip(
    'fastapi.testclient', reason='fastapi requis pour les tests web')


# ---------------------------------------------------------------------------
# Liste blanche
# ---------------------------------------------------------------------------

class TestListeBlanche:

    def test_seuls_les_services_prevus_sont_exposes(self):
        from reachy_tictactoe.webapp.services import SERVICES

        assert set(SERVICES) == {'dashboard', 'mobile_base'}

    def test_le_serveur_sdk_n_est_jamais_pilotable(self):
        """L'arrêter couperait le robot entier, interface comprise."""
        from reachy_tictactoe.webapp.services import SERVICES

        unites = {s['unit'] for s in SERVICES.values()}
        assert 'reachy_sdk_server.service' not in unites
        assert not any('tictactoe' in unite for unite in unites)

    def test_un_nom_inconnu_est_refuse(self):
        from reachy_tictactoe.webapp.services import ServiceInconnu, start

        with pytest.raises(ServiceInconnu):
            start('reachy_sdk_server')

    def test_une_injection_est_refusee(self):
        """Le nom vient du navigateur : il ne doit jamais atteindre le shell."""
        from reachy_tictactoe.webapp.services import ServiceInconnu, start

        with pytest.raises(ServiceInconnu):
            start('dashboard; rm -rf /')


# ---------------------------------------------------------------------------
# Commandes systemd
# ---------------------------------------------------------------------------

class TestCommandes:

    def test_demarrer_n_active_pas_au_boot(self, monkeypatch):
        """⚠️ `start` et non `enable` : le service ne doit PAS revenir au
        prochain démarrage, sinon il reconsomme des ressources en permanence."""
        from reachy_tictactoe.webapp import services

        appels = []
        monkeypatch.setattr(services.subprocess, 'run',
                            lambda cmd, **kw: appels.append(cmd)
                            or MagicMock(returncode=0, stdout=''))

        services.start('dashboard')

        assert appels == [['systemctl', '--user', 'start',
                           'reachy_dashboard.service']]
        assert 'enable' not in appels[0]

    def test_la_commande_est_une_liste_jamais_une_chaine(self, monkeypatch):
        """Pas de shell=True : aucune interprétation possible."""
        from reachy_tictactoe.webapp import services

        recu = {}
        monkeypatch.setattr(
            services.subprocess, 'run',
            lambda cmd, **kw: recu.update(cmd=cmd, kwargs=kw)
            or MagicMock(returncode=0, stdout=''))

        services.stop('mobile_base')

        assert isinstance(recu['cmd'], list)
        assert recu['kwargs'].get('shell') is not True

    def test_l_etat_est_lu_par_is_active(self, monkeypatch):
        from reachy_tictactoe.webapp import services

        monkeypatch.setattr(
            services.subprocess, 'run',
            lambda cmd, **kw: MagicMock(returncode=0, stdout='active\n'))

        assert services.status('dashboard') == 'active'

    def test_un_systemctl_absent_ne_fait_pas_tomber_l_interface(self,
                                                                monkeypatch):
        """Sur un poste de développement, systemctl n'existe pas."""
        from reachy_tictactoe.webapp import services

        def pas_de_systemctl(cmd, **kwargs):
            raise FileNotFoundError('systemctl')

        monkeypatch.setattr(services.subprocess, 'run', pas_de_systemctl)

        assert services.status('dashboard') == 'unknown'

    def test_un_systemctl_qui_traine_ne_bloque_pas(self, monkeypatch):
        """Un appel sans délai maximal figerait la requête HTTP."""
        from reachy_tictactoe.webapp import services

        recu = {}
        monkeypatch.setattr(
            services.subprocess, 'run',
            lambda cmd, **kw: recu.update(kw)
            or MagicMock(returncode=0, stdout='active\n'))

        services.status('dashboard')

        assert recu.get('timeout'), 'un timeout est indispensable'

    def test_un_depassement_de_delai_est_signale(self, monkeypatch):
        from reachy_tictactoe.webapp import services

        def trop_long(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 5)

        monkeypatch.setattr(services.subprocess, 'run', trop_long)

        assert services.status('mobile_base') == 'unknown'


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch):
    from reachy_tictactoe.game_launcher import GameState
    from reachy_tictactoe.webapp.server import create_app

    session = MagicMock()
    session.state = GameState(status='idle', board=(0,) * 9)
    session.playground.reachy.right_camera.last_frame = None
    controller = MagicMock()
    controller.running = None
    controller.last_error = None

    app = create_app(session=session, controller=controller)
    return fastapi_testclient.TestClient(app), session


class TestApiServices:

    def test_la_liste_est_exposee_avec_son_etat(self, client, monkeypatch):
        from reachy_tictactoe.webapp import services
        monkeypatch.setattr(services, 'status', lambda nom: 'inactive')

        http, _ = client
        data = http.get('/api/services').json()

        assert {s['name'] for s in data['services']} == {'dashboard',
                                                         'mobile_base'}
        assert all(s['status'] == 'inactive' for s in data['services'])
        assert all(s['label'] for s in data['services']), (
            "l'interface doit afficher un nom lisible, pas un nom d'unité"
        )

    def test_demarrage_par_l_api(self, client, monkeypatch):
        from reachy_tictactoe.webapp import services

        lances = []
        monkeypatch.setattr(services, 'start', lambda nom: lances.append(nom))
        monkeypatch.setattr(services, 'status', lambda nom: 'active')

        http, _ = client
        reponse = http.post('/api/services/dashboard', json={'action': 'start'})

        assert reponse.status_code == 200
        assert lances == ['dashboard']
        assert reponse.json()['status'] == 'active'

    def test_un_service_inconnu_est_refuse_en_404(self, client):
        http, _ = client
        reponse = http.post('/api/services/reachy_sdk_server',
                            json={'action': 'start'})
        assert reponse.status_code == 404

    def test_une_action_inconnue_est_refusee(self, client):
        http, _ = client
        reponse = http.post('/api/services/dashboard',
                            json={'action': 'enable'})
        assert reponse.status_code == 422, (
            'activer au boot irait contre le caractère ponctuel'
        )


# ---------------------------------------------------------------------------
# Température
# ---------------------------------------------------------------------------

class TestTemperature:

    def _joints(self, session, temperatures):
        """Ce que renverra ``playground.read_temperatures()``.

        La session est un mock : l'endpoint consomme cette méthode, pas
        les joints du SDK. La lecture réelle, elle, est couverte plus bas
        avec un vrai playground (TestSeuilsPartages).
        """
        session.playground.read_temperatures.return_value = temperatures

    def test_le_releve_ponctuel_liste_les_moteurs(self, client):
        http, session = client
        self._joints(session, {'r_shoulder_pitch': 38.0, 'r_elbow_pitch': 41.5})

        data = http.get('/api/temperatures').json()

        assert data['joints'] == {'r_shoulder_pitch': 38.0,
                                  'r_elbow_pitch': 41.5}
        assert data['max'] == 41.5

    def test_le_verdict_suit_les_seuils_du_jeu(self, client):
        """Mêmes seuils que le cycle thermique, sinon l'écran dirait vert
        pendant que la partie s'interrompt pour refroidir."""
        from reachy_tictactoe import config

        http, session = client

        self._joints(session, {'a': 30.0})
        assert http.get('/api/temperatures').json()['verdict'] == 'ok'

        self._joints(session, {'a': config.TEMPERATURE_WARN + 1})
        assert http.get('/api/temperatures').json()['verdict'] == 'warm'

        self._joints(session, {'a': config.TEMPERATURE_COOLDOWN + 1})
        assert http.get('/api/temperatures').json()['verdict'] == 'cooldown'

    def test_un_moteur_muet_n_empeche_pas_la_lecture(self, client):
        """Un joint peut renvoyer None ; il ne doit pas casser le relevé."""
        http, session = client
        self._joints(session, {'a': None, 'b': 40.0})

        data = http.get('/api/temperatures').json()

        assert data['max'] == 40.0
        assert data['joints']['a'] is None

    def test_sans_robot_le_releve_est_refuse(self):
        from reachy_tictactoe.webapp.link import RobotLink
        from reachy_tictactoe.webapp.server import create_app

        lien = RobotLink(connect=lambda: (_ for _ in ()).throw(OSError('nope')),
                         sleep=lambda d: None)
        lien.attempt()
        http = fastapi_testclient.TestClient(create_app(link=lien))

        assert http.get('/api/temperatures').status_code == 503


class TestSeuilsPartages:

    def test_need_cooldown_utilise_le_seuil_de_config(self, playground):
        """Le seuil était codé en dur à trois endroits."""
        from reachy_tictactoe import config

        joint = MagicMock()
        joint.temperature = config.TEMPERATURE_COOLDOWN + 1
        playground.reachy.joints = {'a': joint}
        assert playground.need_cooldown() is True

        joint.temperature = config.TEMPERATURE_COOLDOWN - 1
        assert playground.need_cooldown() is False


class TestEchecsSystemd:

    def test_un_refus_de_systemctl_est_loggue(self, monkeypatch, caplog):
        """Un refus (unité absente, polkit) ne doit pas disparaître sans
        bruit : l'interface montrerait un service qui ne démarre pas, sans
        que rien n'explique pourquoi."""
        import logging
        from reachy_tictactoe.webapp import services

        caplog.set_level(logging.WARNING, logger='reachy.tictactoe.webapp')
        monkeypatch.setattr(
            services.subprocess, 'run',
            lambda cmd, **kw: MagicMock(returncode=5, stdout='',
                                        stderr='Unit not found'))

        services.start('dashboard')

        assert any('Unit not found' in str(e.message) for e in caplog.records)


    def test_un_service_arrete_ne_declenche_aucun_avertissement(
            self, monkeypatch, caplog):
        """⚠️ `systemctl is-active` renvoie 3 quand le service est arrêté —
        soit l'état NORMAL de ces services, désactivés au boot. Sans
        distinction, chaque interrogation logguerait une fausse alerte."""
        import logging
        from reachy_tictactoe.webapp import services

        caplog.set_level(logging.WARNING, logger='reachy.tictactoe.webapp')
        monkeypatch.setattr(
            services.subprocess, 'run',
            lambda cmd, **kw: MagicMock(returncode=3, stdout='inactive\n',
                                        stderr=''))

        assert services.status('dashboard') == 'inactive'
        assert not caplog.records, (
            f'un service arrêté ne doit rien signaler : {caplog.records}'
        )
