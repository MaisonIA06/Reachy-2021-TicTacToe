"""Tension de la batterie dans le panneau « Options ».

La sécurité batterie de Pollen (``zuuu_hal.check_battery``) n'écrit ses
alertes que dans le journal système : personne ne les voit avant que les
roues ne se bloquent. On expose donc la tension à la demande, avec les
**mêmes seuils que Pollen**, pour qu'une batterie faible se voie à l'écran.

⚠️ Lecture ponctuelle, par un canal gRPC ouvert le temps d'un appel et
refermé aussitôt : le jeu ne doit pas dépendre de la base mobile, qui
peut être arrêtée depuis ce même panneau.
"""
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Seuils : ceux de Pollen, pas les nôtres
# ---------------------------------------------------------------------------

class TestSeuils:

    def test_les_seuils_sont_ceux_de_pollen(self):
        """zuuu_hal : 7 cellules, alerte à 3,5 V/cellule, arrêt à 3,3 V.
        Afficher d'autres seuils que ceux qui déclenchent réellement le
        freinage tromperait l'utilisateur."""
        from reachy_tictactoe import config

        assert config.BATTERY_CELLS == 7
        assert config.BATTERY_WARN_VOLTAGE == pytest.approx(7 * 3.5)
        assert config.BATTERY_MIN_VOLTAGE == pytest.approx(7 * 3.3)

    @pytest.mark.parametrize('tension, attendu', [
        (28.5, 'ok'),
        (24.6, 'ok'),
        (24.5, 'ok'),         # comparaison STRICTE, comme zuuu_hal : pas d'alerte
        (24.4, 'low'),
        (23.5, 'low'),
        (23.1, 'low'),        # pas encore freiné : Pollen freine sous 23,1, pas à
        (23.0, 'critical'),   # sous 23,1 : les roues freinent
        (None, 'unknown'),
    ])
    def test_verdict(self, tension, attendu):
        from reachy_tictactoe.webapp.battery import verdict
        assert verdict(tension) == attendu

    def test_une_valeur_non_finie_est_inconnue(self):
        """Même leçon que les températures : NaN < seuil vaut False et
        ferait passer une batterie muette pour une batterie pleine."""
        from reachy_tictactoe.webapp.battery import verdict
        assert verdict(float('nan')) == 'unknown'
        assert verdict(float('inf')) == 'unknown'

    def test_les_seuils_sont_des_dixiemes_exacts(self):
        """7 × 3.3 vaut 23.099999999999998 en flottant : sans arrondi,
        c'est cette valeur qui partirait dans l'API puis à l'écran."""
        from reachy_tictactoe import config
        assert config.BATTERY_MIN_VOLTAGE == 23.1
        assert config.BATTERY_WARN_VOLTAGE == 24.5


# ---------------------------------------------------------------------------
# Lecture : un appel, un délai maximal, un canal refermé
# ---------------------------------------------------------------------------

class TestLecture:

    def _fausse_ouverture(self, niveau, journal):
        def ouvrir(host, port):
            stub = MagicMock()

            def get_battery_level(requete, timeout=None):
                journal.append(('appel', host, port, timeout))
                reponse = MagicMock()
                reponse.level.value = niveau
                return reponse

            stub.GetBatteryLevel = get_battery_level
            return stub, None, lambda: journal.append(('ferme',))
        return ouvrir

    def test_la_tension_est_lue_avec_un_delai_maximal(self, monkeypatch):
        """Sans délai, une base mobile qui ne répond pas figerait la
        requête HTTP — et l'interface avec."""
        from reachy_tictactoe.webapp import battery

        journal = []
        monkeypatch.setattr(battery, '_open_stub',
                            self._fausse_ouverture(28.43, journal))

        tension = battery.read_voltage('localhost')

        assert tension == pytest.approx(28.4)
        appel = [j for j in journal if j[0] == 'appel'][0]
        assert appel[3], 'un timeout est indispensable'
        assert appel[2] == 50061, 'port gRPC de la base mobile'

    def test_le_canal_est_referme_meme_en_cas_d_erreur(self, monkeypatch):
        """Un canal par relevé, et aucun qui traîne : un relevé toutes
        les 30 s pendant des heures fuirait sinon des connexions."""
        from reachy_tictactoe.webapp import battery

        journal = []

        def ouvrir(host, port):
            stub = MagicMock()
            stub.GetBatteryLevel.side_effect = RuntimeError('UNAVAILABLE')
            return stub, None, lambda: journal.append('ferme')

        monkeypatch.setattr(battery, '_open_stub', ouvrir)

        with pytest.raises(battery.BatteryUnavailable):
            battery.read_voltage('localhost')
        assert journal == ['ferme']

    def test_une_base_mobile_arretee_est_une_indisponibilite(self,
                                                             monkeypatch):
        """C'est le cas normal quand on l'a arrêtée depuis le panneau :
        une indisponibilité explicite, pas une pile d'appels gRPC."""
        from reachy_tictactoe.webapp import battery

        def ouvrir(host, port):
            stub = MagicMock()
            stub.GetBatteryLevel.side_effect = RuntimeError(
                'failed to connect to all addresses')
            return stub, None, lambda: None

        monkeypatch.setattr(battery, '_open_stub', ouvrir)

        with pytest.raises(battery.BatteryUnavailable):
            battery.read_voltage('localhost')

    def test_un_sdk_absent_est_aussi_une_indisponibilite(self, monkeypatch):
        """Interface lancée sur un poste sans grpc/reachy_sdk_api : l'API
        doit répondre 503 avec la cause, pas 500 avec une pile d'appels —
        et la répéter toutes les 30 s si le suivi est coché."""
        from reachy_tictactoe.webapp import battery

        def ouvrir(host, port):
            raise ImportError("No module named 'reachy_sdk_api'")

        monkeypatch.setattr(battery, '_open_stub', ouvrir)

        with pytest.raises(battery.BatteryUnavailable, match='reachy_sdk_api'):
            battery.read_voltage('localhost')


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def _client(battery_reader):
    # Ici seulement : les tests de seuils et de lecture n'ont pas besoin de
    # FastAPI et doivent tourner même sur un poste sans requirements-dev.
    fastapi_testclient = pytest.importorskip(
        'fastapi.testclient', reason='fastapi requis pour les tests web')
    from reachy_tictactoe.game_launcher import GameState
    from reachy_tictactoe.webapp.server import create_app

    session = MagicMock()
    session.state = GameState(status='idle', board=(0,) * 9)
    session.playground.reachy.right_camera.last_frame = None
    controller = MagicMock()
    controller.running = None
    controller.last_error = None
    return fastapi_testclient.TestClient(
        create_app(session=session, controller=controller,
                   battery_reader=battery_reader))


class TestApi:

    def test_le_releve_expose_tension_verdict_et_seuils(self):
        from reachy_tictactoe import config

        http = _client(lambda: 28.4)
        data = http.get('/api/battery').json()

        assert data['voltage'] == 28.4
        assert data['verdict'] == 'ok'
        assert data['thresholds'] == {'warn': config.BATTERY_WARN_VOLTAGE,
                                      'min': config.BATTERY_MIN_VOLTAGE}

    def test_une_batterie_faible_se_voit(self):
        http = _client(lambda: 24.0)
        assert http.get('/api/battery').json()['verdict'] == 'low'

    def test_base_mobile_arretee_donne_un_503_explicite(self):
        from reachy_tictactoe.webapp.battery import BatteryUnavailable

        def indisponible():
            raise BatteryUnavailable('base mobile injoignable')

        http = _client(indisponible)
        reponse = http.get('/api/battery')

        assert reponse.status_code == 503
        assert 'base mobile' in reponse.json()['detail'].lower()

    def test_sans_lecteur_configure_le_releve_est_refuse(self):
        """create_app(session=, controller=) sans batterie reste valable."""
        http = _client(None)
        assert http.get('/api/battery').status_code == 503

    def test_une_valeur_non_finie_reste_serialisable(self):
        http = _client(lambda: float('nan'))
        data = http.get('/api/battery').json()
        assert data['voltage'] is None
        assert data['verdict'] == 'unknown'
