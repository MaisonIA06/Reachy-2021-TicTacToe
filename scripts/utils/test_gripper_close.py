"""
Profil de fermeture de la pince : ferme cran par cran et affiche la charge
(present_load) à chaque degré. Sert à régler le seuil de détection de blocage.

Procédure :
  1. Lance le script : la pince s'ouvre.
  2. Place un CUBE (le pion de Reachy) entre les mors.
  3. Appuie sur Entrée : la pince ferme lentement en affichant pos + load.
  4. Note à quel degré le load monte vraiment (= contact réel avec le cube)
     vs les petits pics transitoires du début (mouvement à vide).

Usage :
    python scripts/utils/test_gripper_close.py --host localhost
"""
import argparse
import time

from reachy_sdk import ReachySDK
from reachy_sdk.trajectory import goto
from reachy_sdk.trajectory.interpolation import InterpolationMode

from reachy_tictactoe.config import GRIPPER_OPEN, GRIPPER_CLOSED


def main():
    parser = argparse.ArgumentParser(description='Profil de fermeture pince')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--torque-limit', type=float, default=100)
    parser.add_argument('--step', type=float, default=1.0)
    parser.add_argument('--delay', type=float, default=0.1)
    args = parser.parse_args()

    reachy = ReachySDK(host=args.host)
    reachy.turn_on('r_arm')
    g = reachy.r_arm.r_gripper
    g.compliant = False
    g.torque_limit = args.torque_limit
    time.sleep(0.2)

    # Ouvrir
    goto(goal_positions={g: GRIPPER_OPEN}, duration=1.0,
         interpolation_mode=InterpolationMode.LINEAR)
    time.sleep(1.0)
    print(f'Pince ouverte ({g.present_position:.1f}°).')
    input('>> Place un CUBE entre les mors puis appuie sur Entrée...')

    print(f'\n{"target":>8} {"pos":>8} {"load":>8}   barre')
    print('-' * 50)
    max_load = 0
    target = g.present_position
    # On ferme jusqu'à GRIPPER_CLOSED (et même un peu au-delà, vers 0, pour voir)
    end = GRIPPER_CLOSED
    while target < end:
        target = min(target + args.step, end)
        g.goal_position = target
        time.sleep(args.delay)
        load = abs(g.present_load) if g.present_load is not None else 0
        max_load = max(max_load, load)
        bar = '#' * int(load / 20)
        print(f'{target:>8.1f} {g.present_position:>8.1f} {load:>8.0f}   {bar}')

    print(f'\nCharge max observée : {max_load:.0f}')
    print('→ Choisis un seuil max_load NETTEMENT au-dessus des pics de début '
          '(mouvement à vide) mais atteint au contact du cube.')
    print('Pince laissée fermée. Ctrl+C pour quitter.')


if __name__ == '__main__':
    main()
