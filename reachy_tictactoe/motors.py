"""Activation du couple moteur sans à-coup.

Au ``turn_on``, le registre ``goal_position`` des moteurs contient encore
la consigne du mouvement précédent : le moteur saute violemment vers cette
vieille cible dès que le couple s'active. ``safe_turn_on`` synchronise
``goal_position`` sur ``present_position`` juste avant l'activation pour
que chaque moteur se réveille sur place.

Source unique : utilisé par le jeu (``tictactoe_playground``) et par les
scripts (``record_moves``, ``test_recorded_moves``, ``test_positions``,
calibration, collecte d'images).
"""
import time


def safe_turn_on(reachy, part='r_arm', settle=0.05):
    """Active le couple de ``part`` sans à-coup.

    Le gripper est exclu de la synchronisation : ``close_gripper()``
    sur-commande volontairement ``goal_position`` au-delà de la position
    bloquée par le pion pour maintenir le serrage (voir CLAUDE.md) —
    resynchroniser annulerait la force de prise si un pion est tenu au
    moment d'une réactivation (reprise après erreur en pleine partie).

    ``settle`` laisse le temps au flux de commandes (~100 Hz, asynchrone)
    de pousser les consignes vers les moteurs avant l'appel ``turn_on``
    (RPC immédiat) — sans quoi le couple peut s'activer avant la
    synchronisation et l'à-coup réapparaît par intermittence.
    """
    part_obj = getattr(reachy, part)
    for joint in part_obj.joints.values():
        if 'gripper' in joint.name.lower():
            continue
        position = joint.present_position
        if position is not None:
            joint.goal_position = position
    time.sleep(settle)
    reachy.turn_on(part)
