"""
Libère le couple du bras droit (et de la tête) de Reachy.

À utiliser quand un moteur reste rigide / bloqué après un arrêt du programme
(ex. r_wrist_roll qui force et chauffe). Met les moteurs en mode compliant
(couple coupé) pour pouvoir bouger le bras à la main et stopper la surchauffe.

Usage :
    python scripts/utils/release_arm.py --host localhost

Si ça ne suffit pas (moteur déjà en erreur matérielle), il faut couper
physiquement l'alimentation du robot pour laisser refroidir et réinitialiser.
"""
import argparse
import time

from reachy_sdk import ReachySDK


def main():
    parser = argparse.ArgumentParser(description='Libère le couple des bras/tête')
    parser.add_argument('--host', default='localhost',
                        help='Adresse du robot (default: localhost)')
    args = parser.parse_args()

    reachy = ReachySDK(host=args.host)
    time.sleep(0.5)

    # Méthode douce d'abord
    try:
        reachy.turn_off_smoothly('reachy')
        print('turn_off_smoothly("reachy") OK')
    except Exception as e:
        print(f'turn_off_smoothly a échoué ({e}), passage en compliant manuel...')

    # Forcer compliant=True sur chaque joint (au cas où)
    for joint in reachy.joints.values():
        try:
            joint.compliant = True
        except Exception as e:
            print(f'  {joint.name}: impossible de passer compliant ({e})')

    time.sleep(0.5)

    print('\nÉtat après libération :')
    for joint in reachy.r_arm.joints.values():
        comp = getattr(joint, 'compliant', None)
        temp = getattr(joint, 'temperature', None)
        t = f'{temp:.0f}°C' if isinstance(temp, (int, float)) else str(temp)
        print(f'  {joint.name:<22} compliant={comp}  temp={t}')

    print('\nLe bras devrait maintenant être mou (déplaçable à la main).')
    print('Si r_wrist_roll est encore chaud, coupe l\'alimentation pour le '
          'laisser refroidir.')


if __name__ == '__main__':
    main()
