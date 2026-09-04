"""
Configuration centralisée pour le projet Reachy TicTacToe

Ce fichier contient toutes les variables de configuration qui peuvent
être modifiées selon votre setup (calibration du plateau, paramètres
de la caméra, etc.)

⚠️ IMPORTANT: Après avoir modifié ce fichier, vous devez redémarrer
   le jeu pour que les changements prennent effet.

Pour recalibrer:
    python scripts/calibrate_board.py --host localhost
"""

import numpy as np
from pathlib import Path


# ==============================================================================
# COORDONNÉES DU PLATEAU (Zone globale dans l'image de la caméra)
# ==============================================================================
# Ces coordonnées définissent où se trouve le plateau dans l'image capturée
# par la caméra droite de Reachy.
# Format: (left_x, right_x, top_y, bottom_y)
#
# Pour recalibrer ces valeurs, utilisez:
#     python scripts/calibrate_board.py --host localhost

BOARD_POSITION = {
    'left_x': 60,      # Bord gauche du plateau dans l'image
    'right_x': 435,     # Bord droit du plateau dans l'image  
    'top_y': 247,       # Bord haut du plateau dans l'image
    'bottom_y': 579,    # Bord bas du plateau dans l'image
}


# ==============================================================================
# COORDONNÉES DES CASES (Relatives à la zone du plateau)
# ==============================================================================
# Ces coordonnées définissent chaque case du morpion DANS la zone du plateau.
# Format pour chaque case: (left, right, top, bottom)
# board_cases[row][col] = (left, right, top, bottom)
#
# ⚠️ Ces coordonnées sont RELATIVES à la zone du plateau extraite,
#    pas à l'image complète de la caméra.
#
# Layout du plateau (vu depuis Reachy):
#     (0,0) | (0,1) | (0,2)
#     ------|-------|------
#     (1,0) | (1,1) | (1,2)
#     ------|-------|------
#     (2,0) | (2,1) | (2,2)

BOARD_CASES = np.array((
    ((10, 115, 9, 102), (116, 215, 9, 90), (225, 315, 6, 80)),  # Ligne 0
    ((12, 117, 107, 200), (123, 228, 102, 195), (233, 338, 92, 185)),  # Ligne 1
    ((13, 126, 216, 317), (130, 250, 204, 311), (252, 366, 194, 296))  # Ligne 2
))

# Note: Ces valeurs par défaut sont des estimations. 
# Utilisez scripts/calibrate_board.py pour obtenir les vraies valeurs.


# ==============================================================================
# PARAMÈTRES DE LA CAMÉRA
# ==============================================================================

CAMERA_CONFIG = {
    # Position de la tête pour voir le plateau (coordonnées x, y, z)
    'look_at_board': {
        'x': 0.5,
        'y': 0.0,
        'z': -0.6,
        'duration': 1.0,
    },
}


# ==============================================================================
# CHEMINS DES MODÈLES
# ==============================================================================

# Répertoire de base du projet
PROJECT_ROOT = Path(__file__).parent.parent

# Répertoire des modèles
MODELS_DIR = PROJECT_ROOT / 'reachy_tictactoe' / 'models'

# Modèles de classification
MODELS = {
    'boxes': {
        'model': str(MODELS_DIR / 'ttt-boxes.tflite'),
        'labels': str(MODELS_DIR / 'ttt-boxes.txt'),
    },
    'valid_board': {
        'model': str(MODELS_DIR / 'ttt-valid-board.tflite'),
        'labels': str(MODELS_DIR / 'ttt-valid-board.txt'),
    },
}


# ==============================================================================
# PARAMÈTRES DU GRIPPER
# ==============================================================================
# Positions du gripper (en degrés, valeurs négatives)
# Plus le nombre est proche de 0 = Plus FERMÉ
# Plus le nombre est négatif = Plus OUVERT

GRIPPER_OPEN = -45      # Complètement ouvert
GRIPPER_CLOSED = -6     # Fermé pour tenir les cylindres

# Détection « un cube est tenu » : se juge sur la POSITION de blocage, PAS
# sur present_load (mesurée à 2 aussi bien à vide que cube serré — elle ne
# discrimine rien). Mesures sur le robot, 2026-09-02 :
GRIPPER_EMPTY_POSITION = -7.7    # pince refermée à vide (3 essais sur 3)
GRIPPER_SMALLEST_HOLD = -10.6    # plus petite prise observée (10 prises)

# Un cube est tenu si la pince reste PLUS OUVERTE que ce seuil, placé dans
# l'intervalle libre entre les deux mesures ci-dessus.
# ⚠️ La position à vide dépend de GRIPPER_CLOSED (elle vaut environ
# GRIPPER_CLOSED - 1,7°) : si vous changez la consigne de fermeture, il faut
# REMESURER GRIPPER_EMPTY_POSITION et redéplacer ce seuil, sinon la
# détection devient un « toujours vrai » silencieux.
GRIPPER_HOLDING_THRESHOLD = -9


# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================

def get_board_position():
    """
    Retourne les coordonnées du plateau dans l'image de la caméra
    
    Returns:
        tuple: (left_x, right_x, top_y, bottom_y)
    """
    return (
        BOARD_POSITION['left_x'],
        BOARD_POSITION['right_x'],
        BOARD_POSITION['top_y'],
        BOARD_POSITION['bottom_y'],
    )


def get_board_cases():
    """
    Retourne les coordonnées des cases du plateau
    
    Returns:
        numpy.ndarray: Array 3x3x4 avec les coordonnées de chaque case
    """
    return BOARD_CASES.copy()


def save_calibration(board_position=None, board_cases=None):
    """
    Sauvegarde une nouvelle calibration dans ce fichier
    
    Args:
        board_position: dict avec 'left_x', 'right_x', 'top_y', 'bottom_y'
        board_cases: numpy array 3x3x4 avec les coordonnées des cases
    """
    import re
    
    config_file = Path(__file__)
    content = config_file.read_text()
    
    # Mettre à jour la position du plateau
    if board_position is not None:
        for key, value in board_position.items():
            pattern = rf"'{key}':\s*\d+"
            replacement = f"'{key}': {value}"
            content = re.sub(pattern, replacement, content)
    
    # Mettre à jour les cases
    if board_cases is not None:
        # Générer le code pour board_cases
        code = "BOARD_CASES = np.array((\n"
        for row in range(3):
            code += "    ("
            for col in range(3):
                left, right, top, bottom = board_cases[row, col]
                code += f"({left}, {right}, {top}, {bottom})"
                if col < 2:
                    code += ", "
            code += ")"
            if row < 2:
                code += ","
            code += f"  # Ligne {row}\n"
        code += "))"
        
        # Pattern regex pour matcher BOARD_CASES jusqu'à )) suivi d'un saut de ligne
        # Utilise [\s\S]*? (non-greedy) pour capturer tout le contenu multi-ligne
        # Le lookahead (?=\s*\n) assure qu'on s'arrête au bon endroit
        pattern = r'BOARD_CASES\s*=\s*np\.array\s*\([\s\S]*?\)\)(?=\s*\n)'
        content = re.sub(pattern, code, content)
    
    # Sauvegarder
    config_file.write_text(content)
    print(f"✅ Configuration sauvegardée dans {config_file}")


def print_config():
    """Affiche la configuration actuelle"""
    print()
    print("="*70)
    print("📋 CONFIGURATION ACTUELLE")
    print("="*70)
    print()
    print("🎯 Position du plateau:")
    for key, value in BOARD_POSITION.items():
        print(f"   {key:12s} = {value}")
    print()
    print("📐 Cases du plateau (3x3):")
    for row in range(3):
        print(f"   Ligne {row}:")
        for col in range(3):
            left, right, top, bottom = BOARD_CASES[row, col]
            print(f"      Case ({row},{col}): ({left:3d}, {right:3d}, {top:3d}, {bottom:3d})")
    print()
    print("🎥 Configuration caméra:")
    look_at = CAMERA_CONFIG['look_at_board']
    print(f"   Position: x={look_at['x']}, y={look_at['y']}, z={look_at['z']}")
    print()


if __name__ == '__main__':
    # Afficher la configuration actuelle
    print_config()

