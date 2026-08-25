#!/usr/bin/env python3
"""
Script utilitaire pour visualiser et modifier la configuration.

Ce script permet de:
- Afficher la configuration actuelle
- Modifier les valeurs de configuration manuellement
- Vérifier la validité de la configuration

Usage:
    # Afficher la configuration actuelle
    python scripts/utils/show_config.py
    
    # Modifier la zone du plateau
    python scripts/utils/show_config.py --set-board 114 379 331 581
    
    # Réinitialiser aux valeurs par défaut
    python scripts/utils/show_config.py --reset
"""

import sys
import argparse
import numpy as np
from pathlib import Path

# Ajouter le projet au path (3 niveaux: show_config.py -> utils -> scripts -> racine)
project_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_dir))

# Importer directement le module config sans passer par __init__.py
# pour éviter les dépendances sur reachy_sdk
import importlib.util
config_path = project_dir / 'reachy_tictactoe' / 'config.py'
spec = importlib.util.spec_from_file_location("config", config_path)
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


def print_config_detailed():
    """Affiche la configuration avec tous les détails"""
    print()
    print("="*80)
    print("📋 CONFIGURATION ACTUELLE DU PLATEAU TICTACTOE")
    print("="*80)
    print()
    print(f"📁 Fichier de configuration: {Path(config.__file__).absolute()}")
    print()
    
    # Position du plateau
    print("🎯 POSITION DU PLATEAU (dans l'image de la caméra)")
    print("-" * 80)
    board_pos = config.BOARD_POSITION
    print(f"   Bord gauche  (left_x)   : {board_pos['left_x']:4d} px")
    print(f"   Bord droit   (right_x)  : {board_pos['right_x']:4d} px")
    print(f"   Bord haut    (top_y)    : {board_pos['top_y']:4d} px")
    print(f"   Bord bas     (bottom_y) : {board_pos['bottom_y']:4d} px")
    print()
    width = board_pos['right_x'] - board_pos['left_x']
    height = board_pos['bottom_y'] - board_pos['top_y']
    print(f"   Dimensions du plateau : {width} x {height} px")
    print()
    
    # Coordonnées des cases
    print("📐 COORDONNÉES DES CASES (relatives à la zone du plateau)")
    print("-" * 80)
    print("   Layout:")
    print("      (0,0) | (0,1) | (0,2)")
    print("      ------|-------|------")
    print("      (1,0) | (1,1) | (1,2)")
    print("      ------|-------|------")
    print("      (2,0) | (2,1) | (2,2)")
    print()
    
    cases = config.BOARD_CASES
    for row in range(3):
        print(f"   Ligne {row}:")
        for col in range(3):
            left, right, top, bottom = cases[row, col]
            w = right - left
            h = bottom - top
            print(f"      Case ({row},{col}): left={left:3d}, right={right:3d}, "
                  f"top={top:3d}, bottom={bottom:3d}  [{w:3d}x{h:3d} px]")
        print()
    
    # Paramètres de la caméra
    print("🎥 PARAMÈTRES DE LA CAMÉRA")
    print("-" * 80)
    look_at = config.CAMERA_CONFIG['look_at_board']
    print(f"   Position pour voir le plateau:")
    print(f"      x        : {look_at['x']}")
    print(f"      y        : {look_at['y']}")
    print(f"      z        : {look_at['z']}")
    print(f"      duration : {look_at['duration']}s")
    print()
    
    # Instructions
    print("="*80)
    print("📝 POUR MODIFIER LA CONFIGURATION:")
    print("="*80)
    print()
    print("Option 1 - Recalibrer avec l'outil graphique (RECOMMANDÉ):")
    print("   python scripts/calibration/calibrate_board.py --host localhost")
    print()
    print("Option 2 - Modifier manuellement:")
    print("   python scripts/utils/show_config.py --set-board LEFT RIGHT TOP BOTTOM")
    print()
    print("Option 3 - Éditer directement le fichier:")
    print(f"   nano {Path(config.__file__).absolute()}")
    print()
    print("="*80)
    print()


def set_board_position(left, right, top, bottom):
    """Modifie la position du plateau"""
    
    # Validation
    if left >= right:
        print(f"❌ Erreur: left ({left}) doit être < right ({right})")
        return False
    
    if top >= bottom:
        print(f"❌ Erreur: top ({top}) doit être < bottom ({bottom})")
        return False
    
    if left < 0 or top < 0:
        print(f"❌ Erreur: les coordonnées ne peuvent pas être négatives")
        return False
    
    # Créer le dictionnaire
    board_position = {
        'left_x': left,
        'right_x': right,
        'top_y': top,
        'bottom_y': bottom,
    }
    
    # Sauvegarder
    try:
        config.save_calibration(board_position=board_position)
        print()
        print("✅ Position du plateau mise à jour!")
        print()
        print_config_detailed()
        return True
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde: {e}")
        import traceback
        traceback.print_exc()
        return False


def reset_config():
    """Réinitialise la configuration aux valeurs par défaut"""
    print()
    print("⚠️  ATTENTION: Cette opération va réinitialiser la configuration.")
    print()
    response = input("Êtes-vous sûr ? (oui/non): ").lower().strip()
    
    if response not in ['oui', 'yes', 'o', 'y']:
        print("❌ Opération annulée")
        return False
    
    # Valeurs par défaut
    board_position = {
        'left_x': 114,
        'right_x': 379,
        'top_y': 331,
        'bottom_y': 581,
    }
    
    board_cases = np.array((
        ((10, 80, 10, 80), (90, 160, 10, 80), (170, 240, 10, 80)),
        ((10, 80, 90, 160), (90, 160, 90, 160), (170, 240, 90, 160)),
        ((10, 80, 170, 240), (90, 160, 170, 240), (170, 240, 170, 240)),
    ))
    
    try:
        config.save_calibration(board_position=board_position, board_cases=board_cases)
        print()
        print("✅ Configuration réinitialisée aux valeurs par défaut")
        print()
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def validate_config():
    """Vérifie que la configuration est valide"""
    print()
    print("🔍 VALIDATION DE LA CONFIGURATION")
    print("="*80)
    
    errors = []
    warnings = []
    
    # Vérifier la position du plateau
    board_pos = config.BOARD_POSITION
    if board_pos['left_x'] >= board_pos['right_x']:
        errors.append("left_x doit être < right_x")
    
    if board_pos['top_y'] >= board_pos['bottom_y']:
        errors.append("top_y doit être < bottom_y")
    
    if board_pos['left_x'] < 0 or board_pos['top_y'] < 0:
        errors.append("Les coordonnées ne peuvent pas être négatives")
    
    width = board_pos['right_x'] - board_pos['left_x']
    height = board_pos['bottom_y'] - board_pos['top_y']
    
    if width < 200:
        warnings.append(f"La largeur du plateau ({width} px) semble petite")
    
    if height < 200:
        warnings.append(f"La hauteur du plateau ({height} px) semble petite")
    
    # Vérifier les cases
    cases = config.BOARD_CASES
    for row in range(3):
        for col in range(3):
            left, right, top, bottom = cases[row, col]
            
            if left >= right:
                errors.append(f"Case ({row},{col}): left >= right")
            
            if top >= bottom:
                errors.append(f"Case ({row},{col}): top >= bottom")
            
            if left < 0 or top < 0:
                errors.append(f"Case ({row},{col}): coordonnées négatives")
            
            # Vérifier que les cases sont dans la zone du plateau
            if right > width:
                warnings.append(f"Case ({row},{col}): dépasse la largeur du plateau")
            
            if bottom > height:
                warnings.append(f"Case ({row},{col}): dépasse la hauteur du plateau")
    
    # Afficher les résultats
    if not errors and not warnings:
        print("✅ Configuration valide!")
        print()
        return True
    
    if errors:
        print()
        print("❌ ERREURS DÉTECTÉES:")
        for error in errors:
            print(f"   - {error}")
        print()
    
    if warnings:
        print()
        print("⚠️  AVERTISSEMENTS:")
        for warning in warnings:
            print(f"   - {warning}")
        print()
    
    if errors:
        print("La configuration contient des erreurs. Veuillez les corriger.")
        print()
        return False
    else:
        print("La configuration est techniquement valide mais contient des avertissements.")
        print()
        return True


def main():
    parser = argparse.ArgumentParser(
        description='Visualisation et modification de la configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        '--set-board',
        nargs=4,
        metavar=('LEFT', 'RIGHT', 'TOP', 'BOTTOM'),
        type=int,
        help='Modifier la position du plateau (left_x right_x top_y bottom_y)'
    )
    
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Réinitialiser la configuration aux valeurs par défaut'
    )
    
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Valider la configuration actuelle'
    )
    
    args = parser.parse_args()
    
    # Actions
    if args.reset:
        return 0 if reset_config() else 1
    
    if args.set_board:
        left, right, top, bottom = args.set_board
        return 0 if set_board_position(left, right, top, bottom) else 1
    
    if args.validate:
        valid = validate_config()
        if valid:
            print_config_detailed()
            return 0
        else:
            return 1
    
    # Par défaut, afficher la configuration
    print_config_detailed()
    validate_config()
    return 0


if __name__ == '__main__':
    sys.exit(main())

