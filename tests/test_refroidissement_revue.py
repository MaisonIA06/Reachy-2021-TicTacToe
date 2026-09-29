"""Corrections issues de la revue du cycle thermique (2026-09-29).

Chaque test porte un défaut précis relevé sur le premier jet : un
ventilateur de Pollen éteint à tort à l'arrêt, un couple non coupé si un
appel ventilateur se fige, un écran resté sur « Refroidissement », une
protection thermique sautée par un clic antérieur, un titre qui ne
changeait jamais, et des appels réseau inutiles.
"""
import logging
from unittest.mock import MagicMock

import pytest

from reachy_tictactoe import config


class Ventilateur:
    """Ventilateur factice qui COMPTE les lectures de ``is_on``.

    Dans le vrai SDK (reachy-sdk 0.7.0) ``Fan.is_on`` est un appel gRPC
    ``GetFansState`` sans délai maximal, pas un attribut : chaque lecture
    coûte un aller-retour réseau.
    """

    def __init__(self, allume=False):
        self._allume = allume
        self.lectures = 0
        self.appels = []

    @property
    def is_on(self):
        self.lectures += 1
        return self._allume

    def on(self):
        self._allume = True
        self.appels.append('on')

    def off(self):
        self._allume = False
        self.appels.append('off')


class Ventilateurs:
    def __init__(self, **etats):
        for nom, allume in etats.items():
            setattr(self, nom, Ventilateur(allume))


# ---------------------------------------------------------------------------
# Ventilateurs
# ---------------------------------------------------------------------------

class TestProprieteDesVentilateurs:

    def test_un_ventilateur_allume_par_pollen_n_est_jamais_relache(self):
        """Zone chaude, ventilateur DÉJÀ allumé (par Pollen) : nous n'avons
        rien commandé, il n'est pas à nous. Le relâcher à l'arrêt le
        couperait alors que Pollen le croit encore allumé — et il ne le
        rallumerait qu'après un passage sous 43 puis au-dessus de 45."""
        from reachy_tictactoe.fans import FanSupervisor

        fans = Ventilateurs(r_wrist_fan=True)
        superviseur = FanSupervisor(fans, lambda: {'r_wrist_roll': 48.0})

        superviseur.tick()
        superviseur.release()

        assert fans.r_wrist_fan.is_on, 'pas à nous : on ne l’éteint pas'
        assert fans.r_wrist_fan.appels == []

    def test_ce_que_nous_avons_allume_est_bien_relache(self):
        from reachy_tictactoe.fans import FanSupervisor

        fans = Ventilateurs(r_wrist_fan=False)
        superviseur = FanSupervisor(fans, lambda: {'r_wrist_roll': 48.0})

        superviseur.tick()
        superviseur.release()

        assert fans.r_wrist_fan.appels == ['on', 'off']

    def test_states_ne_declenche_aucun_appel_reseau(self):
        """``states()`` sert l'API des températures : six allers-retours
        gRPC par relevé, c'est précisément ce que le panneau évite."""
        from reachy_tictactoe.fans import FanSupervisor

        fans = Ventilateurs(r_wrist_fan=False, l_wrist_fan=False)
        superviseur = FanSupervisor(fans, lambda: {'r_wrist_roll': 48.0})
        superviseur.tick()
        lectures_avant = fans.r_wrist_fan.lectures + fans.l_wrist_fan.lectures

        etats = superviseur.states()

        assert fans.r_wrist_fan.lectures + fans.l_wrist_fan.lectures == lectures_avant
        assert etats['r_wrist_fan'] is True
        assert etats['l_wrist_fan'] is False

    def test_une_zone_froide_ne_lit_pas_l_etat(self):
        """Pas de lecture réseau pour une zone sous le seuil bas : rien à
        décider, rien à demander."""
        from reachy_tictactoe.fans import FanSupervisor

        fans = Ventilateurs(r_elbow_fan=False)
        superviseur = FanSupervisor(fans, lambda: {'r_elbow_pitch': 38.0})

        superviseur.tick()

        assert fans.r_elbow_fan.lectures == 0

    def test_release_ne_reste_pas_bloque_sur_le_verrou(self):
        """Un tick figé dans un appel gRPC sans délai garde le verrou :
        ``release()`` doit renoncer au bout d'un délai, pas attendre à
        jamais — sinon la coupure de couple qui suit n'arrive jamais."""
        import threading
        from reachy_tictactoe.fans import FanSupervisor

        fans = Ventilateurs(r_wrist_fan=False)
        superviseur = FanSupervisor(fans, lambda: {'r_wrist_roll': 48.0})
        superviseur.tick()
        superviseur._lock.acquire()   # simule un tick figé
        try:
            termine = threading.Event()
            threading.Thread(target=lambda: (superviseur.release(timeout=0.2),
                                             termine.set()), daemon=True).start()
            assert termine.wait(timeout=5), 'release() ne doit jamais bloquer'
        finally:
            superviseur._lock.release()


class TestFermeture:

    def test_le_couple_est_coupe_avant_de_toucher_aux_ventilateurs(self, playground):
        """``close()`` existe pour couper le couple. Un appel ventilateur
        figé ne doit pas l'en empêcher : le couple d'abord."""
        ordre = []
        playground.reachy.turn_off_smoothly.side_effect = lambda *a: ordre.append('couple')
        playground.fan_supervisor = MagicMock()
        playground.fan_supervisor.stop.side_effect = lambda *a, **k: ordre.append('ventilateurs')

        playground.close()

        assert ordre == ['couple', 'ventilateurs']


# ---------------------------------------------------------------------------
# Session et contrôleur
# ---------------------------------------------------------------------------

class TestSessionRefroidissement:

    def test_le_titre_refroidissement_prend_le_pas_sur_le_gagnant(self):
        """La page titre `WINNER[winner]` dès que winner est renseigné :
        après une partie, « Refroidissement » ne s'affichait jamais."""
        from reachy_tictactoe.game_launcher import GameSession

        session = GameSession(MagicMock())
        session._publish(status='finished', winner='robot')

        session.report_cooling('r_wrist_roll', 48.0)

        assert session.state.status == 'cooling'
        assert session.state.winner is None

    def test_cooldown_if_needed_est_partage(self):
        """Une seule séquence pour la CLI et l'interface : l'ancienne
        copie CLI n'avait reçu ni l'interruption ni la publication."""
        from reachy_tictactoe.game_launcher import GameSession

        playground = MagicMock()
        playground.need_cooldown.return_value = True
        playground.wait_for_cooldown.return_value = True
        session = GameSession(playground)

        assert session.cooldown_if_needed() is True

        playground.safe_turn_on.assert_called_with('head')
        playground.enter_sleep_mode.assert_called_once()
        playground.leave_sleep_mode.assert_called_once()
        playground.invalidate_head_aim.assert_called_once()
        assert session.state.status == 'idle'
        assert 'terminé' in session.state.message

    def test_pas_de_refroidissement_si_les_moteurs_sont_frais(self):
        from reachy_tictactoe.game_launcher import GameSession

        playground = MagicMock()
        playground.need_cooldown.return_value = False
        session = GameSession(playground)

        assert session.cooldown_if_needed() is True
        playground.enter_sleep_mode.assert_not_called()

    def test_l_ecran_est_libere_meme_si_la_sortie_de_veille_echoue(self):
        """`leave_sleep_mode()` qui lève (SDK tombé) laissait l'état sur
        « Refroidissement » alors que le robot était déclaré libre."""
        from reachy_tictactoe.game_launcher import GameSession

        playground = MagicMock()
        playground.need_cooldown.return_value = True
        playground.wait_for_cooldown.return_value = True
        playground.leave_sleep_mode.side_effect = RuntimeError('SDK tombé')
        session = GameSession(playground)

        with pytest.raises(RuntimeError):
            session.cooldown_if_needed()

        assert session.state.status == 'idle'


class TestControleurRefroidissement:

    def test_un_arret_de_partie_ne_dispense_pas_du_refroidissement(self):
        """Arrêter en pleine partie laissait le drapeau levé : l'attente
        thermique revenait aussitôt « interrompue » et une nouvelle partie
        pouvait démarrer moteurs à 51 °C. L'opérateur a demandé d'arrêter
        la partie, pas de renoncer à la protection."""
        from reachy_tictactoe.game_launcher import GameSession
        from reachy_tictactoe.webapp.controller import RobotController

        playground = MagicMock()
        playground.need_cooldown.return_value = True
        session = GameSession(playground)
        controller = RobotController(session)
        session.request_stop()   # clic pendant la partie qui vient de finir

        vu = {}

        def fausse_attente(move_to_rest=True, should_stop=None, report=None):
            vu['drapeau_au_debut'] = should_stop()
            return True

        playground.wait_for_cooldown.side_effect = fausse_attente

        controller._cooldown_if_needed()

        assert vu['drapeau_au_debut'] is False, (
            'le drapeau de la partie doit être remis à zéro avant l’attente')


# ---------------------------------------------------------------------------
# Libellés des ventilateurs servis par l'API, pas codés dans la page
# ---------------------------------------------------------------------------

class TestLibellesVentilateurs:

    @pytest.mark.parametrize('nom, attendu', [
        ('r_wrist_fan', 'poignet droit'),
        ('l_shoulder_fan', 'épaule gauche'),
        ('r_elbow_fan', 'coude droit'),
    ])
    def test_fan_label(self, nom, attendu):
        from reachy_tictactoe.joints import fan_label
        assert fan_label(nom) == attendu

    def test_un_ventilateur_inconnu_garde_son_nom(self):
        from reachy_tictactoe.joints import fan_label
        assert fan_label('mystery_fan') == 'mystery_fan'

    def test_l_api_sert_les_libelles_des_ventilateurs(self):
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

        assert data['fan_labels'] == {'r_wrist_fan': 'poignet droit'}


def test_la_page_ne_code_plus_les_zones_en_dur():
    import os
    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    page = os.path.join(racine, 'reachy_tictactoe', 'webapp', 'static', 'index.html')
    with open(page, encoding='utf-8') as f:
        html = f.read()
    assert 'const ZONES' not in html, 'les libellés viennent de l’API (fan_labels)'
