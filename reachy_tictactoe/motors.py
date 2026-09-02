"""Helpers moteurs et pince.

``safe_turn_on`` — activation du couple sans à-coup. Au ``turn_on``, le
registre ``goal_position`` des moteurs contient encore la consigne du
mouvement précédent : le moteur saute violemment vers cette vieille cible
dès que le couple s'active. On synchronise ``goal_position`` sur
``present_position`` juste avant l'activation pour que chaque moteur se
réveille sur place. Source unique : utilisé par le jeu
(``tictactoe_playground``) et par les scripts ``moves/``.

``is_holding_pawn`` — le cube est-il réellement saisi ? Se juge sur la
POSITION de blocage de la pince, pas sur ``present_load`` (voir
``config.GRIPPER_HOLDING_THRESHOLD``).
"""
import time

from .config import GRIPPER_HOLDING_THRESHOLD


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


def wait_until_settled(read_position, tolerance=0.2, timeout=2.0, period=0.1,
                       stable_readings=2):
    """Attend qu'un joint s'immobilise, puis renvoie sa position.

    Un délai fixe ne convient pas : bloquée par un cube la pince s'arrête
    en quelques dizaines de millisecondes, à vide elle parcourt encore
    plusieurs degrés. Lire trop tôt renvoie une position de transit — c'est
    ce qui faisait passer une pince vide pour une prise réussie.

    Les réglages par défaut visent la fin de course, où le servo ralentit :
    espacer les lectures (``period``) et en exiger plusieurs consécutives
    sous une tolérance fine évite de conclure trop tôt. Le bruit de mesure
    relevé sur la pince est de ±0,05°, très en dessous de la tolérance.

    Args:
        read_position: callable renvoyant la position courante (ou None si
            la lecture n'est pas encore disponible).
        tolerance: écart en degrés en dessous duquel deux lectures
            successives sont jugées identiques.
        timeout: durée maximale d'attente, en secondes.
        period: pause entre deux lectures.
        stable_readings: nombre de comparaisons stables consécutives
            exigées avant de conclure.

    Returns:
        La dernière position lue (jamais None si au moins une lecture a
        abouti), même si le joint n'a pas fini de se stabiliser.
    """
    debut = time.monotonic()
    precedente = None
    stables = 0
    while True:
        courante = read_position()
        if courante is not None:
            if precedente is not None and abs(courante - precedente) < tolerance:
                stables += 1
                if stables >= stable_readings:
                    return courante
            else:
                stables = 0
            precedente = courante
        if time.monotonic() - debut >= timeout:
            return precedente
        if period:
            time.sleep(period)


def is_holding_pawn(gripper_position, threshold=GRIPPER_HOLDING_THRESHOLD):
    """Un cube est-il tenu, d'après la position de blocage de la pince ?

    La pince ferme jusqu'à ``GRIPPER_CLOSED`` quand rien ne l'arrête ; un
    cube la bloque nettement plus ouverte. Comme les positions sont
    négatives (plus négatif = plus ouvert), « tenir un cube » signifie
    rester STRICTEMENT en dessous du seuil.

    Args:
        gripper_position: ``present_position`` de la pince, en degrés,
            lue APRÈS ``close_gripper()`` (jamais None : c'est à
            l'appelant de gérer l'absence de lecture).
        threshold: seuil de décision, pour recalibrer ponctuellement.
    """
    return gripper_position < threshold
