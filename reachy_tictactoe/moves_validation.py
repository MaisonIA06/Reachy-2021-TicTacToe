"""Validation des mouvements enregistrés (`.npz`).

Fonctions numériques pures, sans robot : utilisables dans les tests, dans
`scripts/moves/validate_moves.py` et pendant une session d'enregistrement.

Deux familles de défauts, tous deux invisibles à l'œil au moment de
l'enregistrement, ont chacune coûté une session complète :

- **flux de positions gelé** : le serveur renvoie la même valeur en boucle,
  les fichiers sont figés et identiques entre eux (`is_frozen`,
  `find_duplicates`) ;
- **dépassement des butées** : en compliant on pousse le bras au-delà des
  limites sans le sentir ; le contrôleur écrête au rejeu et la case est
  ratée (`limit_violations`).
"""
import numpy as np


#: Limites articulaires du bras droit, en degrés.
#: Source : URDF du serveur qui tourne sur le NUC, converti depuis les
#: radians — `reachy_ws/src/reachy_2023/reachy_description/urdf/arm.urdf.xacro`
#: (le paquet ROS s'appelle `reachy_2023` même si le robot est un V1 piloté
#: par le SDK 2021). Le contrôleur écrête toute consigne au-delà : un
#: enregistrement hors limites n'est pas rejouable tel quel.
JOINT_LIMITS = {
    'r_arm.r_shoulder_pitch': (-150.0, 90.0),
    'r_arm.r_shoulder_roll': (-180.0, 10.0),
    'r_arm.r_arm_yaw': (-90.0, 90.0),
    'r_arm.r_elbow_pitch': (-125.0, 0.0),
    'r_arm.r_forearm_yaw': (-100.0, 100.0),
    'r_arm.r_wrist_pitch': (-45.0, 45.0),
    'r_arm.r_wrist_roll': (-35.0, 54.4),
    'r_arm.r_gripper': (-68.8, 20.0),
}

#: En dessous de cette amplitude (degrés), une trajectoire est considérée
#: comme figée : c'est du bruit de mesure, pas un geste.
FROZEN_AMPLITUDE_DEG = 1.0


def limit_violations(move, margin=1.0):
    """Joints dépassant leurs limites articulaires.

    Args:
        move: dict {nom_joint: valeur(s)}, poses 0-d ou trajectoires 1-d.
        margin: tolérance en degrés (bruit de mesure) avant de signaler.

    Returns:
        Liste de tuples (nom_joint, dépassement_en_degrés), du plus grave
        au moins grave. Les joints absents de `JOINT_LIMITS` sont ignorés.
    """
    violations = []
    for joint_name, values in move.items():
        limits = JOINT_LIMITS.get(joint_name)
        if limits is None:
            continue
        lo, hi = limits
        arr = np.atleast_1d(np.asarray(values, dtype=float))
        depassement = max(float(arr.max() - hi), float(lo - arr.min()))
        if depassement > margin:
            violations.append((joint_name, depassement))
    return sorted(violations, key=lambda v: -v[1])


def amplitude(move):
    """Plus grande amplitude (max - min) parmi les joints, en degrés."""
    amplitudes = [
        float(np.ptp(np.atleast_1d(np.asarray(values, dtype=float))))
        for values in move.values()
    ]
    return max(amplitudes) if amplitudes else 0.0


def is_frozen(move):
    """La trajectoire est-elle immobile (flux de positions gelé) ?

    Une pose 0-d est immobile par nature : elle n'est jamais signalée.
    """
    if all(np.asarray(values).ndim == 0 for values in move.values()):
        return False
    return amplitude(move) < FROZEN_AMPLITUDE_DEG


def find_duplicates(catalogue):
    """Groupes de mouvements strictement identiques entre eux.

    Args:
        catalogue: dict {nom_mouvement: dict {nom_joint: valeurs}}.

    Returns:
        Liste de groupes (listes de noms triés) comptant au moins deux
        mouvements identiques. Deux `put_N` identiques signalent un flux
        gelé, pas une coïncidence.
    """
    noms = sorted(catalogue)
    groupes = []
    deja_groupes = set()
    for i, nom in enumerate(noms):
        if nom in deja_groupes:
            continue
        groupe = [nom]
        for autre in noms[i + 1:]:
            if autre in deja_groupes:
                continue
            if _identiques(catalogue[nom], catalogue[autre]):
                groupe.append(autre)
                deja_groupes.add(autre)
        if len(groupe) > 1:
            deja_groupes.add(nom)
            groupes.append(groupe)
    return groupes


#: Suffixe de la copie que `record_moves.py` écrit à côté de chaque `put_N`.
SMOOTH_SUFFIX = '_smooth_10_kp'


def unexpected_duplicates(catalogue):
    """Doublons ANORMAUX, hors copies `put_N` / `put_N_smooth_10_kp`.

    `record_moves.py` enregistre volontairement chaque dépose en double :
    signaler cette paire noierait les vrais doublons (deux cases différentes
    identiques = flux de positions gelé).
    """
    groupes = []
    for groupe in find_duplicates(catalogue):
        logiques = {nom[:-len(SMOOTH_SUFFIX)] if nom.endswith(SMOOTH_SUFFIX)
                    else nom
                    for nom in groupe}
        if len(logiques) > 1:
            groupes.append(groupe)
    return groupes


def _identiques(a, b):
    if set(a) != set(b):
        return False
    return all(np.array_equal(np.asarray(a[k]), np.asarray(b[k])) for k in a)
