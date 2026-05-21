"""
Inspecte les trajectoires/positions enregistrées (reachy_tictactoe/moves/*.npz)
SANS connexion au robot.

But : repérer une trajectoire qui envoie un joint (typiquement r_wrist_roll)
dans/près d'une butée, ce qui le fait caler et chauffer pendant le mouvement.

Affiche, pour chaque move, min / max / valeur finale de chaque joint, et
surligne les valeurs « extrêmes » (proches des butées) et les amplitudes fortes.

Usage :
    python scripts/utils/inspect_moves.py
    python scripts/utils/inspect_moves.py --joint r_wrist_roll
"""
import argparse
import glob
import os

import numpy as np

# Butées approximatives Reachy V1 (degrés). À ajuster si besoin.
# Au-delà de ces valeurs, le moteur risque de buter et de caler.
LIMITS = {
    'r_shoulder_pitch': (-180, 90),
    'r_shoulder_roll':  (-180, 15),
    'r_arm_yaw':        (-90, 90),
    'r_elbow_pitch':    (-125, 5),
    'r_forearm_yaw':    (-100, 100),
    'r_wrist_pitch':    (-45, 45),
    'r_wrist_roll':     (-45, 60),   # <-- vérifie cette plage sur ton robot !
    'r_gripper':        (-50, 30),
}

MOVES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'reachy_tictactoe', 'moves',
)


def short(name):
    return name.split('.')[-1]


def main():
    parser = argparse.ArgumentParser(description='Inspecte les moves enregistrés')
    parser.add_argument('--joint', default=None,
                        help='Ne montrer qu\'un joint (ex: r_wrist_roll)')
    parser.add_argument('--dir', default=MOVES_DIR, help='Dossier des .npz')
    args = parser.parse_args()

    files = sorted(glob.glob(os.path.join(args.dir, '*.npz')))
    if not files:
        print(f'Aucun .npz dans {args.dir}')
        return

    print(f'Inspection de {len(files)} fichiers dans {args.dir}\n')

    for f in files:
        data = np.load(f)
        name = os.path.splitext(os.path.basename(f))[0]
        alerts = []
        lines = []
        for key in data.files:
            jshort = short(key)
            if args.joint and jshort != args.joint:
                continue
            arr = np.asarray(data[key], dtype=float).flatten()
            if arr.size == 0:
                continue
            vmin, vmax, vlast = np.nanmin(arr), np.nanmax(arr), arr[-1]
            flag = ''
            if jshort in LIMITS:
                lo, hi = LIMITS[jshort]
                marge = 0.10 * (hi - lo)  # 10% de marge avant butée
                if vmin <= lo + marge or vmax >= hi - marge:
                    flag = f'  ⚠️ PROCHE BUTÉE (plage {lo}..{hi})'
                    alerts.append(jshort)
            lines.append(
                f'    {jshort:<20} min={vmin:>7.1f}  max={vmax:>7.1f}  '
                f'fin={vlast:>7.1f}{flag}'
            )

        header = f'• {name}'
        if alerts:
            header += f'   <<< ALERTE: {", ".join(sorted(set(alerts)))}'
        print(header)
        for ln in lines:
            print(ln)
        print()


if __name__ == '__main__':
    main()
