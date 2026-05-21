"""
Moniteur en continu des températures / charges du bras droit.

À lancer SUR LE ROBOT, dans un terminal séparé, PENDANT une partie, pour
attraper en direct le moment où un moteur (ex. r_wrist_roll) chauffe et cale.

Affiche une ligne par seconde et surligne tout dépassement :
  - temp >= 48°C  (approche du seuil de coupure)
  - |load| >= 400 (le moteur force fort)

Usage :
    python scripts/utils/monitor_temps.py --host localhost
    python scripts/utils/monitor_temps.py --host localhost --joint r_wrist_roll
"""
import argparse
import time
from datetime import datetime

from reachy_sdk import ReachySDK

TEMP_WARN = 48
LOAD_WARN = 400


def main():
    parser = argparse.ArgumentParser(description='Moniteur températures/charges bras')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--joint', default=None,
                        help='Surveiller un seul joint (ex: r_wrist_roll)')
    parser.add_argument('--period', type=float, default=1.0,
                        help='Période d\'échantillonnage en s (default 1.0)')
    args = parser.parse_args()

    reachy = ReachySDK(host=args.host)
    time.sleep(0.5)

    joints = list(reachy.r_arm.joints.values())
    if args.joint:
        joints = [j for j in joints if j.name == args.joint]

    print('Ctrl+C pour arrêter.\n')
    try:
        while True:
            ts = datetime.now().strftime('%H:%M:%S')
            parts = []
            alert = False
            for j in joints:
                temp = getattr(j, 'temperature', None)
                load = getattr(j, 'present_load', None)
                t = f'{temp:.0f}' if isinstance(temp, (int, float)) else '--'
                l = f'{load:.0f}' if isinstance(load, (int, float)) else '--'
                mark = ''
                if isinstance(temp, (int, float)) and temp >= TEMP_WARN:
                    mark += '🔥'
                    alert = True
                if isinstance(load, (int, float)) and abs(load) >= LOAD_WARN:
                    mark += '🛑'
                    alert = True
                parts.append(f'{j.name.replace("r_",""):<14}{t:>3}°C/{l:>5}{mark}')
            prefix = '⚠️ ' if alert else '   '
            print(f'{prefix}{ts}  ' + ' | '.join(parts))
            time.sleep(args.period)
    except KeyboardInterrupt:
        print('\nArrêt du moniteur.')


if __name__ == '__main__':
    main()
