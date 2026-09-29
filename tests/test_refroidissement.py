"""Cycle thermique : interruptible, visible, et ventilateurs bien pilotés.

⚠️ Incident du 2026-09-29. Après deux parties, le poignet droit dépasse
50 °C : l'interface entre en refroidissement et attend que TOUS les
moteurs repassent sous 45 °C. Or poignets et pinces stagnent à 46–49 °C
couple coupé (1 °C par 5 à 10 min) : l'attente durait une heure au moins.
Pendant ce temps « Arrêter » était sans effet (la boucle dormait 30 s
sans jamais lire le drapeau), l'écran disait « Partie terminée » avec un
bouton grisé, et les antennes ondulaient sans que personne ne sache que
cela voulait dire « je refroidis ».

Cause aggravante, vérifiée à la main : les ventilateurs fonctionnent,
mais le contrôleur de Pollen ne surveille que les moteurs ``*_pitch`` et
les antennes. ``wrist_roll`` et les pinces — les plus chauds — ne sont
jamais ventilés. On les pilote donc nous-mêmes, sans toucher au code de
Pollen, qui n'éteint que ce qu'il a lui-même allumé.
"""
import logging
from unittest.mock import MagicMock

import pytest

from reachy_tictactoe import config


def _joints(playground, temperatures):
    joints = {}
    for nom, valeur in temperatures.items():
        joint = MagicMock()
        joint.name = nom
        joint.temperature = valeur
        joints[nom] = joint
    playground.reachy.joints = joints


@pytest.fixture
def sommeil(monkeypatch):
    """Intercepte time.sleep du playground : durées demandées, sans attendre.

    ⚠️ Borné : sur l'ancien code, une attente jamais interrompue bouclait
    sans fin et figeait TOUTE la suite (constaté : pytest tué après 5 min).
    Un test qui dort 500 fois a échoué, il ne doit pas rester prisonnier.
    """
    import reachy_tictactoe.tictactoe_playground as module
    durees = []

    def faux_sleep(duree):
        durees.append(duree)
        if len(durees) > 500:
            raise AssertionError(
                'boucle sans fin : 500 sommeils sans sortie ni arrêt')

    monkeypatch.setattr(module.time, 'sleep', faux_sleep)
    return durees


# ---------------------------------------------------------------------------
# Seuils
# ---------------------------------------------------------------------------

class TestSeuils:

    def test_la_reprise_est_atteignable(self):
        """45 °C était à peine sous la température de repos des poignets
        (46–48 °C mesurés couple coupé) : une hystérésis de 3 °C sous le
        déclenchement à 50 °C suffit, et se franchit en quelques minutes."""
        assert config.TEMPERATURE_COOLDOWN == 50
        assert config.TEMPERATURE_RESUME == 47
        assert config.TEMPERATURE_RESUME < config.TEMPERATURE_COOLDOWN

    def test_les_seuils_ventilateurs_sont_ceux_de_pollen(self):
        """Même hystérésis que fans_controller : ON à 45, OFF sous 43."""
        assert config.FAN_ON_TEMPERATURE == 45
        assert config.FAN_OFF_TEMPERATURE == 43


# ---------------------------------------------------------------------------
# wait_for_cooldown : interruptible, borné, bavard
# ---------------------------------------------------------------------------

class TestAttenteRefroidissement:

    def test_termine_quand_le_plus_chaud_repasse_sous_la_reprise(
            self, playground, sommeil):
        _joints(playground, {'r_wrist_roll': config.TEMPERATURE_RESUME - 0.5,
                             'r_gripper': 40.0})

        assert playground.wait_for_cooldown(move_to_rest=False) is True
        assert sommeil == [], 'déjà froid : aucune attente'

    def test_arreter_interrompt_l_attente(self, playground, sommeil):
        """LE point de l'incident : deux clics sur Arrêter, aucun effet."""
        _joints(playground, {'r_wrist_roll': 49.0})
        compteur = {'n': 0}

        def should_stop():
            compteur['n'] += 1
            return compteur['n'] >= 3

        resultat = playground.wait_for_cooldown(
            move_to_rest=False, should_stop=should_stop)

        assert resultat is False, "interrompu ≠ refroidi : l'appelant doit le savoir"
        assert sum(sommeil) <= 3, (
            f"l'arrêt doit être vu en quelques secondes, pas après 30 s : {sommeil}")

    def test_le_drapeau_est_lu_chaque_seconde_pas_toutes_les_30_s(
            self, playground, sommeil):
        _joints(playground, {'r_wrist_roll': 49.0})
        appels = {'n': 0}

        def should_stop():
            appels['n'] += 1
            return appels['n'] > 40

        playground.wait_for_cooldown(move_to_rest=False, should_stop=should_stop)

        assert all(d <= 1.0 for d in sommeil), (
            f'aucun sommeil ne doit dépasser 1 s : {sorted(set(sommeil))}')

    def test_sans_aucune_temperature_lisible_on_ne_reste_pas_prisonnier(
            self, playground, sommeil):
        """Tous les moteurs muets (NaN → None) : l'ancien `if motor_temps
        and ...` ne cassait jamais la boucle — attente infinie."""
        _joints(playground, {'neck_yaw': None, 'neck_pitch': None})

        assert playground.wait_for_cooldown(move_to_rest=False) is True
        assert sommeil == []

    def test_l_avancement_est_rapporte_avec_le_moteur_le_plus_chaud(
            self, playground, sommeil):
        _joints(playground, {'r_wrist_roll': 49.0, 'r_gripper': 48.0})
        rapports = []
        tours = {'n': 0}

        def should_stop():
            tours['n'] += 1
            return tours['n'] >= 2

        playground.wait_for_cooldown(
            move_to_rest=False, should_stop=should_stop,
            report=lambda nom, temperature: rapports.append((nom, temperature)))

        assert rapports, 'sans rapport, l’écran ne peut rien afficher'
        assert rapports[0] == ('r_wrist_roll', 49.0)

    def test_le_journal_nomme_le_moteur_et_sa_temperature(
            self, playground, sommeil, caplog):
        """« Motors cooling down… » 35 fois sans une seule température :
        impossible de savoir à quelle distance on était de la sortie."""
        caplog.set_level(logging.WARNING, logger='reachy.tictactoe')
        _joints(playground, {'r_wrist_roll': 49.0})

        playground.wait_for_cooldown(move_to_rest=False,
                                     should_stop=lambda: True)

        messages = ' '.join(str(r.message) for r in caplog.records)
        assert 'r_wrist_roll' in messages and '49' in messages
        assert str(config.TEMPERATURE_RESUME) in messages


# ---------------------------------------------------------------------------
# La session publie l'état, l'interface peut l'afficher
# ---------------------------------------------------------------------------

class TestEtatPublie:

    def test_report_cooling_publie_un_statut_lisible(self):
        from reachy_tictactoe.game_launcher import GameSession

        session = GameSession(MagicMock())
        session.report_cooling('r_wrist_roll', 48.0)

        etat = session.state
        assert etat.status == 'cooling'
        assert 'Poignet droit' in etat.message, 'libellé français, pas r_wrist_roll'
        assert '48' in etat.message
        assert str(config.TEMPERATURE_RESUME) in etat.message

    def test_fin_de_refroidissement(self):
        from reachy_tictactoe.game_launcher import GameSession

        session = GameSession(MagicMock())
        session.report_cooling('r_wrist_roll', 48.0)
        session.end_cooling(cooled=True)
        assert session.state.status == 'idle'
        assert 'terminé' in session.state.message

    def test_refroidissement_interrompu_le_dit(self):
        from reachy_tictactoe.game_launcher import GameSession

        session = GameSession(MagicMock())
        session.report_cooling('r_wrist_roll', 48.0)
        session.end_cooling(cooled=False)
        assert session.state.status == 'idle'
        assert 'interrompu' in session.state.message.lower()


class TestControleur:

    def test_arreter_pendant_le_refroidissement_libere_le_robot(self):
        """Reproduit l'incident : partie finie, moteurs chauds, clic sur
        Arrêter. Le contrôleur doit transmettre le drapeau à l'attente."""
        from reachy_tictactoe.game_launcher import GameSession
        from reachy_tictactoe.webapp.controller import RobotController

        playground = MagicMock()
        playground.need_cooldown.return_value = True
        session = GameSession(playground)
        controller = RobotController(session)

        def fausse_attente(move_to_rest=True, should_stop=None, report=None):
            assert should_stop is not None, 'le drapeau doit être transmis'
            assert report is not None, "l'avancement doit être publié"
            report('r_wrist_roll', 49.0)
            assert session.state.status == 'cooling'
            session.request_stop()          # clic sur Arrêter
            return not should_stop()        # False : interrompu

        playground.wait_for_cooldown.side_effect = fausse_attente

        controller._cooldown_if_needed()

        assert session.state.status == 'idle'
        assert 'interrompu' in session.state.message.lower()
        playground.leave_sleep_mode.assert_called_once()


# ---------------------------------------------------------------------------
# Ventilateurs : pilotés par TOUS les moteurs de la zone
# ---------------------------------------------------------------------------

class FauxVentilateur:
    def __init__(self, allume=False):
        self.is_on = allume
        self.appels = []

    def on(self):
        self.is_on = True
        self.appels.append('on')

    def off(self):
        self.is_on = False
        self.appels.append('off')


class FauxVentilateurs:
    def __init__(self, noms):
        for nom in noms:
            setattr(self, nom, FauxVentilateur())


NOMS = ['r_shoulder_fan', 'r_elbow_fan', 'r_wrist_fan',
        'l_shoulder_fan', 'l_elbow_fan', 'l_wrist_fan']


def _superviseur(temperatures):
    from reachy_tictactoe.fans import FanSupervisor
    fans = FauxVentilateurs(NOMS)
    etat = {'temps': dict(temperatures)}
    superviseur = FanSupervisor(fans, lambda: etat['temps'])
    return superviseur, fans, etat


class TestZones:

    def test_le_roulis_et_la_pince_sont_rattaches_au_poignet(self):
        """Ce que Pollen ignore : les deux moteurs les plus chauds."""
        from reachy_tictactoe.fans import FAN_ZONES

        assert {'r_wrist_pitch', 'r_wrist_roll', 'r_gripper'} <= set(FAN_ZONES['r_wrist_fan'])
        assert {'l_wrist_pitch', 'l_wrist_roll', 'l_gripper'} <= set(FAN_ZONES['l_wrist_fan'])

    def test_chaque_moteur_de_bras_a_un_ventilateur(self):
        from reachy_tictactoe.fans import FAN_ZONES

        couverts = {j for joints in FAN_ZONES.values() for j in joints}
        for cote in 'rl':
            for segment in ('shoulder_pitch', 'shoulder_roll', 'arm_yaw',
                            'elbow_pitch', 'forearm_yaw',
                            'wrist_pitch', 'wrist_roll', 'gripper'):
                assert f'{cote}_{segment}' in couverts

    def test_les_antennes_restent_a_pollen(self):
        """Pollen les surveille correctement : ne pas se disputer avec lui."""
        from reachy_tictactoe.fans import FAN_ZONES
        assert not any('antenna' in fan for fan in FAN_ZONES)


class TestSuperviseur:

    def test_allume_quand_le_roulis_seul_est_chaud(self):
        superviseur, fans, _ = _superviseur(
            {'r_wrist_pitch': 43.0, 'r_wrist_roll': 48.0, 'r_gripper': 40.0})

        superviseur.tick()

        assert fans.r_wrist_fan.is_on, 'exactement le cas que Pollen manque'

    def test_ne_touche_pas_une_zone_froide(self):
        superviseur, fans, _ = _superviseur({'r_elbow_pitch': 39.0})
        superviseur.tick()
        assert fans.r_elbow_fan.appels == []

    def test_eteint_sous_le_seuil_bas_seulement_ce_qu_il_a_allume(self):
        superviseur, fans, etat = _superviseur({'r_wrist_roll': 48.0})
        superviseur.tick()
        assert fans.r_wrist_fan.is_on

        etat['temps'] = {'r_wrist_roll': 44.0}   # entre 43 et 45 : on garde
        superviseur.tick()
        assert fans.r_wrist_fan.is_on

        etat['temps'] = {'r_wrist_roll': 42.0}   # sous 43 : on éteint
        superviseur.tick()
        assert not fans.r_wrist_fan.is_on

    def test_n_eteint_jamais_un_ventilateur_allume_par_pollen(self):
        """Zone froide pour nous mais ventilateur ON : c'est Pollen (le
        tangage a dû passer 45). Ce n'est pas à nous de l'éteindre."""
        superviseur, fans, _ = _superviseur({'r_wrist_roll': 40.0})
        fans.r_wrist_fan.is_on = True

        superviseur.tick()

        assert fans.r_wrist_fan.is_on
        assert fans.r_wrist_fan.appels == []

    def test_rallume_si_pollen_l_a_eteint_alors_que_la_zone_est_chaude(self):
        """Pollen éteint quand SON moteur repasse sous 43 : le roulis, lui,
        est toujours à 48. Chaque tick réaffirme la consigne."""
        superviseur, fans, _ = _superviseur({'r_wrist_roll': 48.0})
        superviseur.tick()
        fans.r_wrist_fan.is_on = False      # Pollen vient de l'éteindre

        superviseur.tick()

        assert fans.r_wrist_fan.is_on
        assert fans.r_wrist_fan.appels == ['on', 'on']

    def test_release_eteint_ce_qu_on_a_allume(self):
        """À l'arrêt de l'interface : Pollen croit ces ventilateurs éteints
        et ne les éteindrait jamais — ils tourneraient jusqu'au reboot."""
        superviseur, fans, _ = _superviseur(
            {'r_wrist_roll': 48.0, 'l_gripper': 47.0})
        superviseur.tick()
        assert fans.r_wrist_fan.is_on and fans.l_wrist_fan.is_on

        superviseur.release()

        assert not fans.r_wrist_fan.is_on and not fans.l_wrist_fan.is_on

    def test_une_erreur_du_sdk_n_arrete_pas_la_supervision(self, caplog):
        caplog.set_level(logging.WARNING, logger='reachy.tictactoe')
        superviseur, fans, _ = _superviseur(
            {'r_wrist_roll': 48.0, 'l_wrist_roll': 48.0})
        fans.r_wrist_fan.on = MagicMock(side_effect=RuntimeError('gRPC down'))

        superviseur.tick()   # ne doit pas lever

        assert fans.l_wrist_fan.is_on, 'les autres zones sont quand même traitées'
        assert any('gRPC down' in str(r.message) for r in caplog.records)

    def test_un_ventilateur_absent_est_ignore(self):
        from reachy_tictactoe.fans import FanSupervisor
        fans = FauxVentilateurs(['r_wrist_fan'])   # pas de l_wrist_fan
        superviseur = FanSupervisor(fans, lambda: {'l_wrist_roll': 48.0})
        superviseur.tick()   # ne doit pas lever

    def test_les_etats_sont_lisibles(self):
        superviseur, fans, _ = _superviseur({'r_wrist_roll': 48.0})
        superviseur.tick()
        etats = superviseur.states()
        assert etats['r_wrist_fan'] is True
        assert etats['l_wrist_fan'] is False


class TestFilDeSupervision:

    def test_demarre_et_s_arrete(self):
        from reachy_tictactoe.fans import FanSupervisor
        import threading

        tours = threading.Event()
        fans = FauxVentilateurs(NOMS)
        superviseur = FanSupervisor(fans, lambda: tours.set() or {'r_wrist_roll': 48.0})

        fil = superviseur.start(period=0.01)
        assert tours.wait(timeout=5), 'le fil doit exécuter des ticks'
        superviseur.stop(timeout=5)

        assert not fil.is_alive()
        assert not fans.r_wrist_fan.is_on, 'stop() relâche ce qui a été allumé'


# ---------------------------------------------------------------------------
# Intégration playground / API
# ---------------------------------------------------------------------------

class TestIntegration:

    def test_le_playground_supervise_les_ventilateurs_apres_setup(
            self, playground, monkeypatch):
        from reachy_tictactoe import fans as fans_module

        demarres = []
        monkeypatch.setattr(fans_module.FanSupervisor, 'start',
                            lambda self, period=5.0: demarres.append(period))
        monkeypatch.setattr(playground, '_preload_resources', lambda: None)
        monkeypatch.setattr(playground, 'goto_rest_position', lambda *a, **k: None)

        playground.setup()

        assert demarres, 'la supervision doit démarrer avec le robot'
        assert playground.fan_supervisor is not None

    def test_close_arrete_la_supervision(self, playground):
        superviseur = MagicMock()
        playground.fan_supervisor = superviseur

        playground.close()

        superviseur.stop.assert_called_once()

    def test_l_api_expose_les_ventilateurs(self):
        fastapi_testclient = pytest.importorskip('fastapi.testclient')
        from reachy_tictactoe.game_launcher import GameState
        from reachy_tictactoe.webapp.server import create_app

        session = MagicMock()
        session.state = GameState(status='idle', board=(0,) * 9)
        session.playground.reachy.right_camera.last_frame = None
        session.playground.read_temperatures.return_value = {'r_wrist_roll': 48.0}
        session.playground.fan_supervisor.states.return_value = {'r_wrist_fan': True}
        controller = MagicMock()
        controller.running = None
        controller.last_error = None
        http = fastapi_testclient.TestClient(
            create_app(session=session, controller=controller))

        data = http.get('/api/temperatures').json()

        assert data['fans'] == {'r_wrist_fan': True}
