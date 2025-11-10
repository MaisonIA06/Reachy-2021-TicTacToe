#!/usr/bin/env python3
import cv2
import numpy as np
from reachy_tictactoe import config

# Charger une image de test
img = cv2.imread('/tmp/snap.3.jpg')

# Zone du plateau
lx, rx, ly, ry = config.get_board_position()
board_img = img[ly:ry, lx:rx]
cv2.imwrite('/tmp/debug_board_zone.jpg', board_img)
print(f"Board zone: {board_img.shape}")

# Extraire chaque case
cases = config.get_board_cases()
for row in range(3):
    for col in range(3):
        clx, crx, cly, cry = cases[row, col]
        case_img = board_img[cly:cry, clx:crx]
        cv2.imwrite(f'/tmp/debug_case_{row}_{col}.jpg', case_img)
        print(f"Case ({row},{col}): {case_img.shape} - [{clx}:{crx}, {cly}:{cry}]")
