"""Sérialisation des actions du robot (``RobotController``).

L'interface web expose plusieurs boutons qui font tous bouger le MÊME
bras. Deux actions simultanées, c'est deux threads qui envoient des
consignes contradictoires aux mêmes moteurs : le contrôleur n'en autorise
qu'une à la fois et rend la main immédiatement (l'action tourne en fond,
la requête HTTP ne doit pas attendre la fin d'une partie).
"""
import threading

import pytest
from unittest.mock import MagicMock

from reachy_tictactoe.webapp.controller import RobotBusy, RobotController


@pytest.fixture
def controller():
    session = MagicMock()
    session.play_one_game.return_value = 'robot'
    return RobotController(session), session


def _action_bloquante():
    """Retourne (fonction, verrou) : la fonction ne rend la main qu'au signal."""
    feu_vert = threading.Event()
    demarree = threading.Event()

    def action(*args, **kwargs):
        demarree.set()
        feu_vert.wait(timeout=5)

    return action, demarree, feu_vert


class TestUneSeuleActionALaFois:

    def test_une_action_est_lancee_en_arriere_plan(self, controller):
        ctrl, session = controller
        action, demarree, feu_vert = _action_bloquante()
        session.play_one_game.side_effect = action

        ctrl.start_game()

        assert demarree.wait(timeout=2), 'l\'action doit démarrer sans attendre'
        assert ctrl.running == 'game'
        feu_vert.set()
        ctrl.wait(timeout=2)

    def test_la_requete_ne_bloque_pas_jusqu_a_la_fin(self, controller):
        """Une partie dure des minutes : le POST doit répondre tout de suite."""
        ctrl, session = controller
        action, demarree, feu_vert = _action_bloquante()
        session.play_one_game.side_effect = action

        debut = threading.Event()
        ctrl.start_game()
        debut.set()

        assert debut.is_set()
        feu_vert.set()
        ctrl.wait(timeout=2)

    def test_deux_actions_simultanees_sont_refusees(self, controller):
        ctrl, session = controller
        action, demarree, feu_vert = _action_bloquante()
        session.play_one_game.side_effect = action

        ctrl.start_game()
        demarree.wait(timeout=2)

        with pytest.raises(RobotBusy) as info:
            ctrl.check_moves()
        assert 'game' in str(info.value)

        feu_vert.set()
        ctrl.wait(timeout=2)

    def test_le_robot_redevient_disponible_a_la_fin(self, controller):
        ctrl, _ = controller

        ctrl.start_game()
        ctrl.wait(timeout=2)

        assert ctrl.running is None

    def test_une_action_qui_echoue_ne_bloque_pas_le_robot(self, controller):
        """Sinon un plantage rendrait tous les boutons inutilisables."""
        ctrl, session = controller
        session.play_one_game.side_effect = RuntimeError('bras coincé')

        ctrl.start_game()
        ctrl.wait(timeout=2)

        assert ctrl.running is None
        assert 'bras coincé' in ctrl.last_error

    def test_l_erreur_precedente_est_effacee_au_lancement_suivant(
            self, controller):
        ctrl, session = controller
        session.play_one_game.side_effect = RuntimeError('bras coincé')
        ctrl.start_game()
        ctrl.wait(timeout=2)

        session.play_one_game.side_effect = None
        ctrl.start_game()
        ctrl.wait(timeout=2)

        assert ctrl.last_error is None


class TestArret:

    def test_un_arret_demande_juste_apres_le_lancement_n_est_pas_perdu(self):
        """Course réelle : /api/stop peut arriver avant que le thread ait
        commencé. Si la partie remettait le drapeau à zéro en démarrant,
        la demande serait silencieusement ignorée — avec un 202 en réponse.
        """
        session = MagicMock()
        ctrl = RobotController(session)
        feu_vert = threading.Event()
        session.play_one_game.side_effect = lambda *a, **kw: feu_vert.wait(5)

        ctrl.start_game()
        ctrl.stop()

        # Le drapeau est remis à zéro AVANT que l'action soit lancée…
        session.reset_stop.assert_called_once()
        # …et la demande d'arrêt part bien vers la session.
        session.request_stop.assert_called_once()
        feu_vert.set()
        ctrl.wait(timeout=2)

    def test_l_arret_interrompt_aussi_le_test_des_mouvements(self):
        """Un parcours mal visé doit pouvoir être stoppé, pas seulement
        une partie."""
        session = MagicMock()
        ctrl = RobotController(session)
        feu_vert = threading.Event()
        session.playground.run_moves_check.side_effect = (
            lambda *a, **kw: feu_vert.wait(5))

        ctrl.check_moves()
        arrete = ctrl.stop()

        assert arrete == 'moves_check', 'la réponse doit nommer la bonne action'
        session.request_stop.assert_called_once()
        feu_vert.set()
        ctrl.wait(timeout=2)

    def test_arret_sans_action_en_cours(self):
        session = MagicMock()
        ctrl = RobotController(session)

        assert ctrl.stop() is None


class TestProtectionThermique:

    def test_le_refroidissement_est_verifie_apres_chaque_partie(self):
        """L'interface enchaîne les parties : sans ce contrôle, elle
        contournerait la protection à 50 °C que la CLI applique."""
        session = MagicMock()
        session.playground.need_cooldown.return_value = True
        ctrl = RobotController(session)

        ctrl.start_game()
        ctrl.wait(timeout=3)

        session.playground.wait_for_cooldown.assert_called_once()

    def test_pas_de_refroidissement_si_les_moteurs_sont_froids(self):
        session = MagicMock()
        session.playground.need_cooldown.return_value = False
        ctrl = RobotController(session)

        ctrl.start_game()
        ctrl.wait(timeout=3)

        session.playground.wait_for_cooldown.assert_not_called()


class TestActionsDisponibles:

    def test_lancer_une_partie_appelle_la_session(self, controller):
        ctrl, session = controller

        ctrl.start_game()
        ctrl.wait(timeout=2)

        session.play_one_game.assert_called_once()

    def test_tester_les_mouvements_parcourt_les_neuf_cases(self, controller):
        ctrl, session = controller

        ctrl.check_moves()
        ctrl.wait(timeout=2)

        session.playground.run_moves_check.assert_called_once()
