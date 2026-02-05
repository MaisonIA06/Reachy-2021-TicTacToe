#!/usr/bin/env python3
"""
Script de vérification de la calibration du plateau.
Utilise la configuration centralisée (config.py).
"""
import cv2 as cv
import numpy as np
import sys
from pathlib import Path

# Ajouter le projet au path
project_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_dir))

from reachy_tictactoe import config

# Charger l'image capturée
img = cv.imread('/tmp/snap.3.jpg')

# Charger les coordonnées depuis la configuration
lx, rx, ly, ry = config.get_board_position()

print(f"📐 Coordonnées du plateau (depuis config.py):")
print(f"   left_x={lx}, right_x={rx}, top_y={ly}, bottom_y={ry}")

# Dessiner un rectangle sur la zone extraite
img_debug = img.copy()
cv.rectangle(img_debug, (lx, ly), (rx, ry), (0, 255, 0), 2)

# Sauvegarder et afficher
cv.imwrite('/tmp/board_zone_debug.jpg', img_debug)

# Extraire et sauvegarder la zone du plateau seule
board_img = img[ly:ry, lx:rx]
cv.imwrite('/tmp/board_zone_extracted.jpg', board_img)

print(f"Zone extraite : taille {board_img.shape}")
print(f"Image sauvegardée : /tmp/board_zone_debug.jpg")
