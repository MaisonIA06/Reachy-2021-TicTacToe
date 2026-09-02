"""Activation du couple sans à-coup (``reachy_tictactoe.motors``).

Au ``turn_on``, le registre ``goal_position`` des moteurs contient encore la
consigne du mouvement précédent : sans synchronisation préalable sur
``present_position``, chaque moteur saute violemment vers cette vieille
cible (régression historique : « coup violent au début de chaque
mouvement »). Ces tests verrouillent le contrat de ``safe_turn_on`` :

- les consignes sont synchronisées AVANT l'activation du couple ;
- le gripper est EXCLU (``close_gripper()`` sur-commande volontairement la
  consigne pour maintenir le serrage — resynchroniser lâcherait le pion) ;
- un joint sans lecture (``present_position is None``) est ignoré sans
  planter ni écraser sa consigne.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

from reachy_tictactoe.motors import safe_turn_on


class _FakeJoint:
    """Joint minimal : un nom, une position mesurée, une consigne périmée."""

    def __init__(self, name, present_position):
        self.name = name
        self.present_position = present_position
        self.goal_position = -999.0  # vieille consigne volontairement absurde


def _faux_robot(joints):
    """Robot factice dont r_arm.joints est un vrai dict (itérable)."""
    reachy = MagicMock(name='reachy')
    reachy.r_arm = SimpleNamespace(joints=joints)
    return reachy


def _joints_standards():
    return {
        'r_shoulder_pitch': _FakeJoint('r_shoulder_pitch', 12.3),
        'r_elbow_pitch': _FakeJoint('r_elbow_pitch', -64.9),
        'r_gripper': _FakeJoint('r_gripper', -20.0),
    }


class TestSafeTurnOn:

    def test_les_consignes_sont_synchronisees_au_moment_du_turn_on(self):
        """goal_position == present_position à l'instant où le couple s'active."""
        joints = _joints_standards()
        reachy = _faux_robot(joints)

        consignes_au_turn_on = {}

        def _capture(part):
            consignes_au_turn_on.update(
                {nom: j.goal_position for nom, j in joints.items()})

        reachy.turn_on.side_effect = _capture

        safe_turn_on(reachy, 'r_arm', settle=0.0)

        assert consignes_au_turn_on['r_shoulder_pitch'] == 12.3
        assert consignes_au_turn_on['r_elbow_pitch'] == -64.9

    def test_le_gripper_n_est_pas_resynchronise(self):
        """close_gripper() sur-commande la pince pour serrer : on n'y touche pas."""
        joints = _joints_standards()
        reachy = _faux_robot(joints)

        safe_turn_on(reachy, 'r_arm', settle=0.0)

        assert joints['r_gripper'].goal_position == -999.0

    def test_un_joint_sans_lecture_est_ignore(self):
        """present_position None (flux pas encore reçu) : ni plantage ni écrasement."""
        joints = _joints_standards()
        joints['r_elbow_pitch'].present_position = None
        reachy = _faux_robot(joints)

        safe_turn_on(reachy, 'r_arm', settle=0.0)

        assert joints['r_elbow_pitch'].goal_position == -999.0
        assert joints['r_shoulder_pitch'].goal_position == 12.3

    def test_turn_on_est_appele_une_fois_sur_la_partie_demandee(self):
        reachy = _faux_robot(_joints_standards())

        safe_turn_on(reachy, 'r_arm', settle=0.0)

        reachy.turn_on.assert_called_once_with('r_arm')


class TestPlaygroundUtiliseSafeTurnOn:

    def test_la_methode_du_playground_delegue_au_helper_partage(self, playground):
        joints = _joints_standards()
        playground.reachy.r_arm = SimpleNamespace(joints=joints)

        playground.safe_turn_on('r_arm')

        assert joints['r_shoulder_pitch'].goal_position == 12.3
        playground.reachy.turn_on.assert_called_once_with('r_arm')

    def test_goto_base_position_active_le_bras_sans_a_coup(
            self, playground, monkeypatch):
        """goto_base_position doit passer par safe_turn_on, pas turn_on brut."""
        appels = []
        monkeypatch.setattr(
            playground, 'safe_turn_on', lambda part: appels.append(part))

        playground.goto_base_position(duration=0.01)

        assert appels == ['r_arm']
        playground.reachy.turn_on.assert_not_called()

    def test_play_pawn_active_le_bras_sans_a_coup(self, playground, monkeypatch):
        """play_pawn doit passer par safe_turn_on, pas turn_on brut."""
        gripper = playground.reachy.r_arm.r_gripper
        gripper.present_position = -20.0
        gripper.present_load = 150.0
        monkeypatch.setattr(playground, 'play_trajectory', MagicMock())

        appels = []
        monkeypatch.setattr(
            playground, 'safe_turn_on', lambda part: appels.append(part))

        playground.play_pawn(1, 5)

        assert appels and appels[0] == 'r_arm'
        playground.reachy.turn_on.assert_not_called()
