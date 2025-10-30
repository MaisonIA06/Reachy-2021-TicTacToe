#!/usr/bin/env python3
"""Script pour recropper les images existantes"""
import cv2
import os
import sys
from glob import glob

sys.path.insert(0, '/home/mia/Bureau/reachy-2019-tictactoe')
from reachy_tictactoe.vision import board_rect

# Dossiers à traiter
folders = [
    'training_data/valid_board/valid',
    'training_data/valid_board/invalid'
]

lx, rx, ly, ry = board_rect

for folder in folders:
    print(f"\n📁 Traitement: {folder}")
    images = glob(f'{folder}/*.jpg')
    
    for img_path in images:
        # Charger l'image
        img = cv2.imread(img_path)
        
        if img is None:
            print(f"  ⚠️ Impossible de lire: {img_path}")
            continue
        
        # Vérifier si l'image est déjà croppée
        if img.shape[0] < 500 and img.shape[1] < 500:
            print(f"  ✓ Déjà croppée: {os.path.basename(img_path)}")
            continue
        
        # Cropper
        cropped = img[ly:ry, lx:rx]
        
        # Sauvegarder (écraser l'ancienne)
        cv2.imwrite(img_path, cropped)
        print(f"  ✂️ Croppée: {os.path.basename(img_path)} {img.shape} → {cropped.shape}")
    
    print(f"✅ Terminé: {len(images)} images traitées")