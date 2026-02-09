#!/usr/bin/env python3
"""
Script de vérification de la calibration du plateau.
Utilise la configuration centralisée (config.py).

Usage:
    # Avec une image spécifique
    python scripts/calibration/check_calibrate_board.py --image /chemin/vers/image.jpg
    
    # Avec l'image par défaut (/tmp/snap.3.jpg)
    python scripts/calibration/check_calibrate_board.py
    
    # Afficher le résultat à l'écran (fermer avec 'q')
    python scripts/calibration/check_calibrate_board.py --image test.jpg --show
"""
import cv2 as cv
import numpy as np
import sys
import argparse
from pathlib import Path
import importlib.util

# Ajouter le projet au path
project_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_dir))

# Importer directement config.py sans charger tout le package
config_path = project_dir / 'reachy_tictactoe' / 'config.py'
spec = importlib.util.spec_from_file_location("config", config_path)
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


def main():
    parser = argparse.ArgumentParser(
        description='Vérification de la calibration de la zone du plateau'
    )
    parser.add_argument(
        '--image',
        default='/tmp/snap.3.jpg',
        help='Chemin vers l\'image à analyser (défaut: /tmp/snap.3.jpg)'
    )
    parser.add_argument(
        '--show',
        action='store_true',
        help='Afficher le résultat à l\'écran (fermer avec q)'
    )
    parser.add_argument(
        '--output-dir',
        default='/tmp',
        help='Répertoire de sortie pour les images (défaut: /tmp)'
    )
    
    args = parser.parse_args()
    
    # Vérifier que l'image existe
    if not Path(args.image).exists():
        print(f"❌ Image introuvable: {args.image}")
        print()
        print("💡 Utilisez --image pour spécifier une image existante:")
        print(f"   python {Path(__file__).name} --image /chemin/vers/votre/image.jpg")
        return 1
    
    # Charger l'image
    img = cv.imread(args.image)
    if img is None:
        print(f"❌ Impossible de charger l'image: {args.image}")
        return 1
    
    print(f"✓ Image chargée: {args.image} ({img.shape})")
    
    # Charger les coordonnées depuis la configuration
    lx, rx, ty, by = config.get_board_position()
    
    print()
    print(f"📐 Coordonnées du plateau (depuis config.py):")
    print(f"   left_x={lx}, right_x={rx}, top_y={ty}, bottom_y={by}")
    print(f"   Largeur: {rx - lx}px, Hauteur: {by - ty}px")
    
    # Vérifier que les coordonnées sont dans les limites de l'image
    h, w = img.shape[:2]
    if lx < 0 or rx > w or ty < 0 or by > h:
        print()
        print(f"⚠️  ATTENTION: Les coordonnées dépassent les limites de l'image!")
        print(f"   Image: {w}x{h}")
        print(f"   Zone demandée: ({lx},{ty}) -> ({rx},{by})")
    
    # Dessiner un rectangle sur la zone extraite
    img_debug = img.copy()
    cv.rectangle(img_debug, (lx, ty), (rx, by), (0, 255, 0), 3)
    cv.putText(img_debug, "PLATEAU", (lx + 10, ty + 30), 
               cv.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    
    # Créer le répertoire de sortie si nécessaire
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Sauvegarder l'image avec le rectangle
    debug_path = output_dir / 'board_zone_debug.jpg'
    cv.imwrite(str(debug_path), img_debug)
    print()
    print(f"✓ Image avec zone marquée: {debug_path}")
    
    # Extraire et sauvegarder la zone du plateau seule
    board_img = img[ty:by, lx:rx]
    extracted_path = output_dir / 'board_zone_extracted.jpg'
    cv.imwrite(str(extracted_path), board_img)
    print(f"✓ Zone extraite ({board_img.shape}): {extracted_path}")
    
    # Afficher si demandé
    if args.show:
        print()
        print("📺 Affichage... (Appuyez sur 'q' pour fermer)")
        
        # Redimensionner si l'image est trop grande
        max_display = 800
        scale = min(max_display / w, max_display / h, 1.0)
        if scale < 1.0:
            display_img = cv.resize(img_debug, None, fx=scale, fy=scale)
        else:
            display_img = img_debug
        
        cv.imshow('Calibration Zone Plateau', display_img)
        cv.imshow('Zone Extraite', board_img)
        
        while True:
            key = cv.waitKey(100) & 0xFF
            if key == ord('q'):
                break
        
        cv.destroyAllWindows()
    
    print()
    print("✅ Vérification terminée!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
