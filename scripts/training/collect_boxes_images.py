#!/usr/bin/env python3
"""
Script de collecte d'images pour le modèle ttt-boxes.tflite

Ce script vous aide à collecter les images nécessaires pour entraîner
le modèle de détection des cases (empty/cube/cylinder).

Usage:
    python scripts/training/collect_boxes_images.py --host localhost --class empty
    python scripts/training/collect_boxes_images.py --host localhost --class cube
    python scripts/training/collect_boxes_images.py --host localhost --class cylinder
"""

import argparse
import cv2
import numpy as np
import time
import os
import sys
from datetime import datetime
from pathlib import Path
import importlib.util

# Ajouter le répertoire racine du projet au path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Importer directement config.py sans charger tout le package
# (évite les dépendances sklearn, tflite, etc.)
config_path = project_root / 'reachy_tictactoe' / 'config.py'
spec = importlib.util.spec_from_file_location("config", config_path)
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

# Import ReachySDK après config (pour éviter erreur si pas installé en dev)
from reachy_sdk import ReachySDK


def get_look_at_board():
    """Retourne les paramètres look_at pour voir le plateau depuis config"""
    return config.CAMERA_CONFIG['look_at_board']


def warm_up_head(reachy, cycles=10):
    """Échauffe les moteurs de la tête"""
    print(f"🔥 Échauffement des moteurs ({cycles} cycles)...")
    look_at = get_look_at_board()
    
    for i in range(cycles):
        # Mouvement vers le bas (z=-0.4, pas aussi bas que le plateau)
        reachy.head.look_at(x=look_at['x'], y=look_at['y'], z=-0.4, duration=1.0)
        time.sleep(0.5)
        # Mouvement vers l'avant (z=0)
        reachy.head.look_at(x=look_at['x'], y=look_at['y'], z=0, duration=1.0)
        time.sleep(0.5)
        print(f"  Cycle {i+1}/{cycles}", end='\r')
    
    reachy.head.look_at(x=look_at['x'], y=look_at['y'], z=0, duration=1.5)
    time.sleep(1.5)
    print("\n✅ Échauffement terminé")


def capture_and_extract(reachy, board_cases, save_dir, class_label, case_mask):
    """
    Capture le plateau et extrait les cases correspondant au masque
    
    Args:
        reachy: Instance ReachySDK
        board_cases: Array numpy 3x3 des coordonnées des cases (RELATIVES à la zone du plateau)
        save_dir: Dossier de sauvegarde
        class_label: Label de la classe ('empty', 'cube', 'cylinder')
        case_mask: Array numpy 3x3 de booléens (True = sauvegarder cette case)
    
    Returns:
        Nombre d'images sauvegardées
    """
    look_at = get_look_at_board()
    
    # Regarder le plateau (utilise la config centralisée)
    reachy.head.look_at(
        x=look_at['x'], 
        y=look_at['y'], 
        z=look_at['z'], 
        duration=look_at['duration']
    )
    time.sleep(1.0)
    
    # Capturer l'image complète
    img = reachy.right_camera.last_frame
    
    if img is None:
        print("❌ Erreur: pas d'image capturée")
        return 0
    
    # Revenir en position repos
    reachy.head.look_at(x=look_at['x'], y=look_at['y'], z=0, duration=1.0)
    
    # ⚠️ IMPORTANT: Extraire d'abord la zone du plateau!
    # Les coordonnées des cases (board_cases) sont RELATIVES à cette zone
    lx, rx, ty, by = config.get_board_position()
    board_img = img[ty:by, lx:rx]
    
    # Extraire et sauvegarder les cases
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    saved_count = 0
    
    for row in range(3):
        for col in range(3):
            if not case_mask[row, col]:
                continue
            
            # Coordonnées RELATIVES à la zone du plateau
            xl, xr, yt, yb = board_cases[row, col]
            # Appliquer sur l'image de la zone du plateau (pas l'image complète!)
            case_img = board_img[yt:yb, xl:xr]
            
            filename = f"{class_label}_{timestamp}_r{row}c{col}.jpg"
            filepath = os.path.join(save_dir, filename)
            cv2.imwrite(filepath, case_img)
            saved_count += 1
    
    return saved_count


def collect_empty_cases(reachy, board_cases, save_dir, target_count=50):
    """Collecte des images de cases vides"""
    print("\n" + "="*70)
    print("📸 COLLECTE DES CASES VIDES")
    print("="*70)
    print(f"Objectif: {target_count} captures (= {target_count*9} images)")
    print("\n⚠️ Instructions:")
    print("  1. Enlevez TOUTES les pièces du plateau")
    print("  2. Appuyez sur Entrée pour capturer")
    print("  3. Déplacez légèrement le plateau ou changez l'éclairage")
    print("  4. Répétez jusqu'à atteindre l'objectif")
    print("  5. Tapez 'stop' pour arrêter\n")
    
    # Toutes les cases sont vides
    case_mask = np.ones((3, 3), dtype=bool)
    
    capture_count = 0
    total_images = 0
    
    input("Appuyez sur Entrée quand vous êtes prêt...")
    
    while capture_count < target_count:
        user_input = input(f"\nCapture #{capture_count+1}/{target_count} - Entrée pour capturer (ou 'stop'): ")
        
        if user_input.lower() == 'stop':
            break
        
        saved = capture_and_extract(reachy, board_cases, save_dir, 'empty', case_mask)
        capture_count += 1
        total_images += saved
        
        print(f"  ✅ {saved} images sauvegardées")
        print(f"  📊 Total: {total_images} images ({capture_count}/{target_count} captures)")
        
        time.sleep(0.5)
    
    print(f"\n🎉 Collecte terminée: {total_images} images de cases vides!")
    return total_images


def collect_with_pieces(reachy, board_cases, save_dir, class_label, target_count=50):
    """Collecte des images de cases avec pièces"""
    print("\n" + "="*70)
    print(f"📸 COLLECTE DES CASES AVEC {class_label.upper()}")
    print("="*70)
    print(f"Objectif: {target_count} captures avec différentes configurations")
    print("\n⚠️ Instructions:")
    print(f"  1. Placez des {class_label}s sur le plateau")
    print("  2. Indiquez quelles cases contiennent des pièces (ex: 0,4,8)")
    print("  3. La capture sera effectuée")
    print("  4. Répétez avec différentes configurations")
    print("  5. Tapez 'stop' pour arrêter\n")
    
    capture_count = 0
    total_images = 0
    
    input("Appuyez sur Entrée quand vous êtes prêt...")
    
    while capture_count < target_count:
        print(f"\n--- Capture #{capture_count+1}/{target_count} ---")
        print("Numérotation des cases:")
        print("  0 | 1 | 2")
        print("  ---------")
        print("  3 | 4 | 5")
        print("  ---------")
        print("  6 | 7 | 8")
        
        user_input = input(f"\nCases avec {class_label} (ex: 0,4,8) ou 'stop': ")
        
        if user_input.lower() == 'stop':
            break
        
        # Parser les indices
        try:
            case_indices = [int(x.strip()) for x in user_input.split(',')]
            
            # Créer le masque
            case_mask = np.zeros((3, 3), dtype=bool)
            for idx in case_indices:
                row = idx // 3
                col = idx % 3
                case_mask[row, col] = True
            
            saved = capture_and_extract(reachy, board_cases, save_dir, class_label, case_mask)
            capture_count += 1
            total_images += saved
            
            print(f"  ✅ {saved} images sauvegardées")
            print(f"  📊 Total: {total_images} images ({capture_count}/{target_count} captures)")
            
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
            print("  Format attendu: 0,4,8 (numéros de cases séparés par des virgules)")
            continue
        
        time.sleep(0.5)
    
    print(f"\n🎉 Collecte terminée: {total_images} images avec {class_label}!")
    return total_images


def main():
    parser = argparse.ArgumentParser(description='Collecte d\'images pour ttt-boxes')
    parser.add_argument('--host', default='localhost', help='Adresse IP de Reachy')
    parser.add_argument('--class', dest='class_label', 
                       choices=['empty', 'cube', 'cylinder'],
                       required=True,
                       help='Classe à collecter')
    parser.add_argument('--target', type=int, default=50,
                       help='Nombre de captures cibles (défaut: 50)')
    
    args = parser.parse_args()
    
    # Charger les coordonnées du plateau depuis la config centralisée
    board_cases = config.get_board_cases()
    board_position = config.get_board_position()
    
    print(f"📐 Configuration chargée depuis config.py:")
    print(f"   Position plateau: {board_position}")
    print(f"   Position tête: x={config.CAMERA_CONFIG['look_at_board']['x']}, "
          f"y={config.CAMERA_CONFIG['look_at_board']['y']}, "
          f"z={config.CAMERA_CONFIG['look_at_board']['z']}")
    
    # Définir le dossier de sauvegarde
    save_dir = f'training_data/boxes/{args.class_label}'
    if not os.path.exists(save_dir):
        print(f"❌ Erreur: le dossier {save_dir} n'existe pas!")
        print("Exécutez d'abord: mkdir -p training_data/boxes/{empty,cube,cylinder}")
        return
    
    # Connexion à Reachy
    print(f"🤖 Connexion à Reachy ({args.host})...")
    try:
        reachy = ReachySDK(host=args.host)
        print("✅ Connecté")
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return
    
    # Activer la tête
    print("🔛 Activation de la tête...")
    reachy.turn_on('head')
    time.sleep(1.0)
    print("✅ Tête activée")
    
    try:
        # Échauffement
        warm_up_head(reachy, cycles=5)
        
        # Collecte selon la classe
        if args.class_label == 'empty':
            total = collect_empty_cases(reachy, board_cases, save_dir, args.target)
        else:
            total = collect_with_pieces(reachy, board_cases, save_dir, 
                                       args.class_label, args.target)
        
        # Statistiques
        print("\n" + "="*70)
        print("📊 STATISTIQUES")
        print("="*70)
        existing_count = len([f for f in os.listdir(save_dir) if f.endswith('.jpg')])
        print(f"Total d'images dans {save_dir}: {existing_count}")
        print(f"Recommandé: 300-500 images par classe")
        
        if existing_count >= 300:
            print("✅ Objectif atteint!")
        elif existing_count >= 100:
            print("⚠️ Continuez à collecter pour atteindre 300 images")
        else:
            print("❌ Continuez à collecter (encore besoin de beaucoup d'images)")
        
    finally:
        # Désactivation
        look_at = get_look_at_board()
        print("\n🔄 Retour en position repos...")
        reachy.head.look_at(x=look_at['x'], y=look_at['y'], z=0, duration=1.5)
        time.sleep(1.5)
        reachy.turn_off('head')
        print("✅ Reachy désactivé")


if __name__ == '__main__':
    main()
