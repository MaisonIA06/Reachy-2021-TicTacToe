import cv2 as cv
import numpy as np

# Charger l'image capturée
img = cv.imread('/tmp/snap.553.jpg')

# Coordonnées actuelles du plateau
lx, rx, ly, ry = 38, 427, 296, 429

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