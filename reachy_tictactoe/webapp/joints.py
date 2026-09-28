"""Libellés français des moteurs, pour l'interface.

Le SDK nomme les articulations à sa façon (``r_wrist_roll``,
``l_gripper``…). Ces noms restent affichés à côté du libellé : ce sont eux
qu'on retrouve dans les journaux et les scripts de diagnostic
(``scripts/utils/check_motors.py``).

Un nom inconnu retombe sur lui-même : un moteur inattendu doit s'afficher
plutôt que faire planter la fenêtre.
"""

#: segment technique → (nom, précision ou None, genre du nom)
#: Le genre sert à accorder le côté : « Coude droit » mais « Épaule droite ».
_SEGMENTS = {
    'shoulder_pitch': ('Épaule', 'tangage', 'f'),
    'shoulder_roll': ('Épaule', 'roulis', 'f'),
    'arm_yaw': ('Bras', 'rotation', 'm'),
    'elbow_pitch': ('Coude', None, 'm'),
    'forearm_yaw': ('Avant-bras', 'rotation', 'm'),
    'wrist_pitch': ('Poignet', 'tangage', 'm'),
    'wrist_roll': ('Poignet', 'roulis', 'm'),
    'gripper': ('Pince', None, 'f'),
    'antenna': ('Antenne', None, 'f'),
}

_COTES = {
    'r': {'m': 'droit', 'f': 'droite'},
    'l': {'m': 'gauche', 'f': 'gauche'},
}

_COU = {
    'neck_yaw': 'Cou (lacet)',
    'neck_pitch': 'Cou (tangage)',
    'neck_roll': 'Cou (roulis)',
}


def label(name):
    """Libellé français d'un moteur, ou le nom technique s'il est inconnu."""
    if name in _COU:
        return _COU[name]
    cote, _, segment = name.partition('_')
    if cote not in _COTES or segment not in _SEGMENTS:
        return name
    nom, precision, genre = _SEGMENTS[segment]
    libelle = f'{nom} {_COTES[cote][genre]}'
    if precision:
        libelle += f' ({precision})'
    return libelle


def labels_for(names):
    """``{nom_technique: libellé}`` pour une liste de moteurs."""
    return {name: label(name) for name in names}
