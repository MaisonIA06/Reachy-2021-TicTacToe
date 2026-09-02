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

    def action():
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
