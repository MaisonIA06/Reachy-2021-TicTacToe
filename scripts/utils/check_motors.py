"""
Diagnostic moteurs du bras droit + tête de Reachy.

À lancer JUSTE APRÈS un échec (le bras qui « bouge puis s'arrête ») pour
attraper un moteur encore chaud ou en erreur, avant qu'il ne refroidisse.

Lit pour chaque articulation :
  - present_position : position réelle (degrés)
  - goal_position   : consigne envoyée
  - temperature     : °C (>45 = chaud, >50 = seuil cooldown du jeu)
  - present_load    : charge/effort (proche de ±1000 = blocage/surcharge)
  - compliant       : True = couple COUPÉ (le moteur ne bouge pas)

Usage :
    python scripts/utils/check_motors.py --host localhost
"""
import argparse
import time

from reachy_sdk import ReachySDK


def fmt(value, suffix=''):
    if value is None:
        return 'None'
    try:
        return f'{value:.1f}{suffix}'
    except (TypeError, ValueError):
        return f'{value}{suffix}'


def dump(reachy, title, joints):
    print(f'\n=== {title} ===')
    header = f'{"joint":<22} {"pos":>8} {"goal":>8} {"temp":>7} {"load":>8} {"compliant":>10}'
    print(header)
    print('-' * len(header))
    for joint in joints:
        pos = getattr(joint, 'present_position', None)
        goal = getattr(joint, 'goal_position', None)
        temp = getattr(joint, 'temperature', None)
        load = getattr(joint, 'present_load', None)
        comp = getattr(joint, 'compliant', None)

        # Marqueurs d'alerte
        flags = []
        if temp is not None and temp >= 50:
            flags.append('🔥 CHAUD>=50')
        elif temp is not None and temp >= 45:
            flags.append('⚠️ chaud>=45')
        if comp is True:
            flags.append('⚡ COUPLE COUPÉ')
        if load is not None and abs(load) >= 800:
            flags.append('🛑 surcharge')

        line = (
            f'{joint.name:<22} '
            f'{fmt(pos):>8} {fmt(goal):>8} {fmt(temp, "°C"):>7} '
            f'{fmt(load):>8} {str(comp):>10}'
        )
        if flags:
            line += '   ' + '  '.join(flags)
        print(line)


def main():
    parser = argparse.ArgumentParser(description='Diagnostic moteurs Reachy')
    parser.add_argument('--host', default='localhost',
                        help='Adresse du robot (default: localhost)')
    args = parser.parse_args()

    reachy = ReachySDK(host=args.host)
    time.sleep(0.5)  # laisser arriver les premiers états moteurs

    dump(reachy, 'BRAS DROIT', list(reachy.r_arm.joints.values()))
    dump(reachy, 'TÊTE', list(reachy.head.joints.values()))

    print('\nLecture : compliant=True => couple coupé (moteur en sécurité, '
          'ne bougera pas tant qu\'il n\'est pas réactivé / refroidi).')


if __name__ == '__main__':
    main()
