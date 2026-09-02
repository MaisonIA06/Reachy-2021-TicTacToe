#!/usr/bin/env python3
"""
Surveillant sonore à lancer PENDANT un enregistrement manuel (mains libres).

Lecture seule : le robot ne bouge jamais. À lancer dans un second terminal,
en parallèle de `record_moves.py`. Deux alarmes distinctes préviennent en
direct des deux défauts qui rendent un enregistrement inutilisable :

  « Joueur déloyal » → un joint sort de ses LIMITES articulaires.
                       Le contrôleur écrêtera au rejeu : le geste sera raté.
                       → repliez le coude, réduisez la rotation du bras.

  « Observe »        → le bras se déplace HORIZONTALEMENT trop près du
                       plateau : c'est ce qui balaye les pièces.
                       → remontez avant de continuer le déplacement.
                       La descente verticale finale dans la case ne
                       déclenche PAS cette alarme (pas de vitesse
                       horizontale).

Usage :
  python scripts/moves/watch_recording.py --host localhost
  python scripts/moves/watch_recording.py --host localhost --z-min -0.32
"""
import argparse
import math
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from reachy_sdk import ReachySDK  # noqa: E402

from reachy_tictactoe.moves_validation import JOINT_LIMITS  # noqa: E402

SOUNDS_DIR = os.path.join(os.path.dirname(__file__), '..', '..',
                          'reachy_tictactoe', 'sounds')
JOINTS_FK = ['r_shoulder_pitch', 'r_shoulder_roll', 'r_arm_yaw',
             'r_elbow_pitch', 'r_forearm_yaw', 'r_wrist_pitch', 'r_wrist_roll']

# Hauteur de dépose mesurée sur le plateau : z ≈ -0,34 à -0,37 m. Le seuil
# par défaut laisse ~3 cm de garde ; au-delà le bras n'a plus assez
# d'allonge pour les cases éloignées (fausses alertes en continu).
Z_TRANSIT_MIN_DEFAUT = -0.32
VITESSE_H_MIN = 0.03      # m/s : en dessous, on considère une descente verticale
PERIODE_ALERTE_S = 2.5    # anti-spam sonore
MARGE_LIMITE_DEG = 0.5


def jouer(fichier):
    try:
        subprocess.Popen(
            ['mpg123', '-a', 'hw:0,0', '-q', os.path.join(SOUNDS_DIR, fichier)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as e:
        print(f'(son indisponible : {e})', flush=True)


def main():
    parser = argparse.ArgumentParser(
        description='Surveillance sonore pendant un enregistrement',
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--z-min', type=float, default=Z_TRANSIT_MIN_DEFAUT,
                        help='Hauteur minimale en transit (m, défaut '
                             f'{Z_TRANSIT_MIN_DEFAUT})')
    parser.add_argument('--duree', type=float, default=40.0,
                        help='Durée de surveillance en minutes (défaut 40)')
    args = parser.parse_args()

    arm = ReachySDK(host=args.host).r_arm
    print('👁️  Surveillance active (lecture seule, le robot ne bouge pas).')
    print('    « Joueur déloyal » = hors limites articulaires')
    print('    « Observe »        = trop bas en déplacement horizontal')
    print(f'    Garde exigée en transit : z > {args.z_min} m')
    print('    Ctrl+C pour arrêter.\n', flush=True)

    dernier_limite = dernier_bas = 0.0
    precedent = None
    z_min_vu = 0.0
    fin = time.time() + args.duree * 60

    try:
        while time.time() < fin:
            maintenant = time.time()

            depassements = []
            for joint_name, (lo, hi) in JOINT_LIMITS.items():
                court = joint_name.split('.')[-1]
                valeur = getattr(arm, court).present_position
                if valeur is None:
                    continue
                if valeur < lo - MARGE_LIMITE_DEG or valeur > hi + MARGE_LIMITE_DEG:
                    depassements.append((court, valeur, lo, hi))
            if depassements and maintenant - dernier_limite > PERIODE_ALERTE_S:
                dernier_limite = maintenant
                jouer('Joueur_déloyal.mp3')
                for court, valeur, lo, hi in depassements:
                    print(f"[{time.strftime('%H:%M:%S')}] 🚫 LIMITE  {court} = "
                          f'{valeur:.1f}° hors [{lo}, {hi}]', flush=True)

            q = [getattr(arm, j).present_position for j in JOINTS_FK]
            if not any(v is None for v in q):
                try:
                    fk = arm.forward_kinematics(list(q))
                except Exception:
                    fk = None
                if fk is not None:
                    x, y, z = float(fk[0, 3]), float(fk[1, 3]), float(fk[2, 3])
                    z_min_vu = min(z_min_vu, z)
                    if precedent is not None:
                        dt = maintenant - precedent[0]
                        vh = (math.hypot(x - precedent[1], y - precedent[2]) / dt
                              if dt > 0 else 0.0)
                        if (z < args.z_min and vh > VITESSE_H_MIN
                                and maintenant - dernier_bas > PERIODE_ALERTE_S):
                            dernier_bas = maintenant
                            jouer('Observe.mp3')
                            print(f"[{time.strftime('%H:%M:%S')}] ⬇️  TROP BAS  "
                                  f'z={z:.3f} m en déplacement horizontal '
                                  f'{vh * 100:.0f} cm/s → remontez le bras',
                                  flush=True)
                    precedent = (maintenant, x, y)

            time.sleep(0.05)
    except KeyboardInterrupt:
        pass

    print(f'\n⏹️  Surveillance terminée (z le plus bas vu : {z_min_vu:.3f} m).')


if __name__ == '__main__':
    main()
