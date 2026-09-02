#!/usr/bin/env python3
"""
Valide les mouvements enregistrés AVANT de les rejouer sur le robot.

Détecte les défauts invisibles à l'œil au moment de l'enregistrement :
  - trajectoires figées / fichiers identiques (flux de positions gelé) ;
  - dépassements des butées articulaires (le contrôleur écrête au rejeu) ;
  - trajectoires trop courtes ;
  - départ de put_N éloigné de la pose lift (à-coup à l'enchaînement).

Les contrôles ci-dessus ne nécessitent PAS le robot. Avec `--host`, un
profil de hauteur par cinématique directe est ajouté : il mesure la garde
au-dessus du plateau pendant le transit, ce qui révèle les trajectoires
qui rasent le plateau et balayent les pièces.

Usage :
  python scripts/moves/validate_moves.py                    # hors ligne
  python scripts/moves/validate_moves.py --host localhost   # + hauteurs
  python scripts/moves/validate_moves.py --name put_5 --host localhost
"""
import argparse
import glob
import importlib.util
import os
import sys

import numpy as np

# Chargement direct du module de validation, SANS passer par le package :
# `import reachy_tictactoe` exécute son __init__, qui importe reachy_sdk et
# les modèles TFLite — le mode hors ligne (sans robot) échouerait.
_module_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '..', '..', 'reachy_tictactoe', 'moves_validation.py')
_spec = importlib.util.spec_from_file_location('moves_validation', _module_path)
_validation = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_validation)

amplitude = _validation.amplitude
is_frozen = _validation.is_frozen
limit_violations = _validation.limit_violations
unexpected_duplicates = _validation.unexpected_duplicates

MIN_TRAJ_POINTS = 50
MAX_LIFT_GAP_DEG = 15.0
JOINTS_FK = ['r_shoulder_pitch', 'r_shoulder_roll', 'r_arm_yaw',
             'r_elbow_pitch', 'r_forearm_yaw', 'r_wrist_pitch', 'r_wrist_roll']


def charger(moves_dir):
    catalogue = {}
    for chemin in sorted(glob.glob(os.path.join(moves_dir, '*.npz'))):
        catalogue[os.path.basename(chemin)[:-4]] = dict(np.load(chemin))
    return catalogue


BLOQUANT = 'BLOQUANT'
AVERTISSEMENT = 'AVERTISSEMENT'


def controles_hors_ligne(catalogue, noms):
    """Contrôles sans robot.

    Returns:
        {nom: [(niveau, message)]}. BLOQUANT = le fichier est inutilisable
        (flux gelé, NaN, doublon anormal). AVERTISSEMENT = rejouable mais
        dégradé (écrêtage en butée, à-coup à l'enchaînement) — c'est au
        pilote de juger sur le rendu réel.
    """
    problemes = {}

    def ajouter(nom, niveau, message):
        problemes.setdefault(nom, []).append((niveau, message))

    for nom in noms:
        move = catalogue[nom]
        est_trajectoire = any(np.asarray(v).ndim >= 1 for v in move.values())

        for joint, valeurs in move.items():
            if np.isnan(np.asarray(valeurs, dtype=float)).any():
                ajouter(nom, BLOQUANT, f'{joint} contient des NaN')

        for joint, depassement in limit_violations(move):
            ajouter(nom, AVERTISSEMENT,
                    f'{joint} dépasse sa butée de {depassement:.1f}° '
                    f'(écrêté au rejeu)')

        if est_trajectoire:
            if is_frozen(move):
                ajouter(nom, BLOQUANT, f'TRAJECTOIRE FIGÉE (amplitude '
                        f'{amplitude(move):.2f}°) — flux de positions gelé ?')
            n = max(len(np.atleast_1d(v)) for v in move.values())
            if n < MIN_TRAJ_POINTS:
                ajouter(nom, BLOQUANT,
                        f'trajectoire trop courte : {n} pas ({n / 100:.2f} s)')

        # Enchaînement lift -> put_N : le jeu joue lift juste avant.
        if nom.startswith('put_') and 'lift' in catalogue:
            lift = catalogue['lift']
            ecarts = [
                abs(float(lift[j]) - float(np.atleast_1d(move[j])[0]))
                for j in move if j in lift and 'gripper' not in j
            ]
            if ecarts and max(ecarts) > MAX_LIFT_GAP_DEG:
                ajouter(nom, AVERTISSEMENT,
                        f'départ à {max(ecarts):.1f}° de la pose lift '
                        f'(le jeu enchaîne lift → {nom})')

    for groupe in unexpected_duplicates({n: catalogue[n] for n in noms}):
        for nom in groupe:
            ajouter(nom, BLOQUANT,
                    f'identique à {", ".join(x for x in groupe if x != nom)}')

    return problemes


def profil_de_hauteur(catalogue, noms, host):
    """Garde au-dessus du plateau pendant le transit (cinématique directe)."""
    from reachy_sdk import ReachySDK

    arm = ReachySDK(host=host).r_arm
    print('\n=== PROFIL DE HAUTEUR (cinématique directe) ===')
    print(f"{'move':22s} {'z départ':>9s} {'z min transit':>14s} "
          f"{'z dépose':>9s} {'garde':>8s}")
    for nom in noms:
        move = catalogue[nom]
        if not all(f'r_arm.{j}' in move for j in JOINTS_FK):
            continue
        n = max(len(np.atleast_1d(v)) for v in move.values())
        if n < 2:
            continue
        indices = list(range(0, n, 5))
        if indices[-1] != n - 1:
            indices.append(n - 1)
        zs = np.array([
            float(arm.forward_kinematics(
                [float(np.atleast_1d(move[f'r_arm.{j}'])[k]) for j in JOINTS_FK]
            )[2, 3])
            for k in indices
        ])
        coupe = max(1, int(len(zs) * 0.8))  # transit = hors descente finale
        garde = float(zs[:coupe].min()) - float(zs[-1])
        alerte = '  ⚠️ rase le plateau' if garde < 0.03 else ''
        print(f"{nom:22s} {zs[0]:9.3f} {zs[:coupe].min():14.3f} "
              f"{zs[-1]:9.3f} {garde:8.3f}{alerte}")
    print("\nGarde < 0,03 m : le bras se déplace au ras du plateau pendant le "
          "transit et risque de balayer les pièces.")


def main():
    parser = argparse.ArgumentParser(
        description='Valide les mouvements enregistrés',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    parser.add_argument('--name', help='Valider un seul mouvement')
    parser.add_argument('--host', help='Ajoute le profil de hauteur (robot requis)')
    parser.add_argument('--moves-dir', default='reachy_tictactoe/moves')
    args = parser.parse_args()

    catalogue = charger(args.moves_dir)
    if not catalogue:
        print(f'❌ Aucun .npz dans {args.moves_dir}')
        return 1

    if args.name:
        if args.name not in catalogue:
            print(f'❌ Mouvement inconnu : {args.name}')
            return 1
        noms = [args.name]
    else:
        noms = sorted(catalogue)

    problemes = controles_hors_ligne(catalogue, noms)

    print(f'=== VALIDATION DE {len(noms)} MOUVEMENT(S) ===')
    if not problemes:
        print('✅ Aucun problème détecté.')
    else:
        for nom in sorted(problemes):
            print(f'\n[{nom}]')
            for niveau, message in problemes[nom]:
                icone = '❌' if niveau == BLOQUANT else '⚠️ '
                print(f'   {icone} {message}')

    bloquants = sorted(
        nom for nom, liste in problemes.items()
        if any(niveau == BLOQUANT for niveau, _ in liste)
    )
    avertis = sorted(set(problemes) - set(bloquants))
    print(f'\n❌ {len(bloquants)} mouvement(s) à REFAIRE, '
          f'⚠️  {len(avertis)} à surveiller, sur {len(noms)}.')
    if bloquants:
        print('   À refaire : ' + ', '.join(bloquants))

    if args.host:
        profil_de_hauteur(catalogue, [n for n in noms if n.startswith('put_')],
                          args.host)

    return 1 if bloquants else 0


if __name__ == '__main__':
    sys.exit(main())
