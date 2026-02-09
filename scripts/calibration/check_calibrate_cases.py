#!/usr/bin/env python3
"""
Script de vérification de la calibration des cases du plateau.
Utilise la configuration centralisée (config.py).

Usage:
    # Avec une image spécifique
    python scripts/calibration/check_calibrate_cases.py --image /chemin/vers/image.jpg
    
    # Avec l'image par défaut (/tmp/snap.3.jpg)
    python scripts/calibration/check_calibrate_cases.py
    
    # Afficher le résultat à l'écran (fermer avec 'q')
    python scripts/calibration/check_calibrate_cases.py --image test.jpg --show
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
        description='Vérification de la calibration des cases du plateau'
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
    
    # Créer le répertoire de sortie si nécessaire
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Zone du plateau
    lx, rx, ty, by = config.get_board_position()
    print()
    print(f"📐 Zone du plateau: ({lx}, {ty}) -> ({rx}, {by})")
    
    board_img = img[ty:by, lx:rx]
    board_debug_path = output_dir / 'debug_board_zone.jpg'
    cv.imwrite(str(board_debug_path), board_img)
    print(f"✓ Zone plateau extraite ({board_img.shape}): {board_debug_path}")
    
    # Image de debug avec toutes les cases dessinées
    board_with_cases = board_img.copy()
    
    # Couleurs pour chaque ligne (BGR)
    colors = [
        (0, 255, 0),    # Ligne 0 - Vert
        (0, 255, 255),  # Ligne 1 - Jaune
        (0, 165, 255),  # Ligne 2 - Orange
    ]
    
    # Extraire chaque case
    cases = config.get_board_cases()
    print()
    print("📦 Cases extraites:")
    print("   Layout:  (0,0) | (0,1) | (0,2)")
    print("            ------|-------|------")
    print("            (1,0) | (1,1) | (1,2)")
    print("            ------|-------|------")
    print("            (2,0) | (2,1) | (2,2)")
    print()
    
    for row in range(3):
        for col in range(3):
            clx, crx, cty, cby = cases[row, col]
            
            # Vérifier les limites
            bh, bw = board_img.shape[:2]
            if clx < 0 or crx > bw or cty < 0 or cby > bh:
                print(f"   ⚠️  Case ({row},{col}): HORS LIMITES! [{clx}:{crx}, {cty}:{cby}] (plateau: {bw}x{bh})")
                continue
            
            case_img = board_img[cty:cby, clx:crx]
            case_path = output_dir / f'debug_case_{row}_{col}.jpg'
            cv.imwrite(str(case_path), case_img)
            print(f"   Case ({row},{col}): {case_img.shape[1]:3d}x{case_img.shape[0]:3d}px  [{clx:3d}:{crx:3d}, {cty:3d}:{cby:3d}] -> {case_path.name}")
            
            # Dessiner le rectangle sur l'image de debug
            color = colors[row]
            cv.rectangle(board_with_cases, (clx, cty), (crx, cby), color, 2)
            
            # Ajouter le label
            label = f"{row},{col}"
            cx, cy = (clx + crx) // 2 - 15, (cty + cby) // 2 + 5
            cv.putText(board_with_cases, label, (cx, cy), 
                       cv.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    # Sauvegarder l'image avec toutes les cases
    all_cases_path = output_dir / 'debug_all_cases.jpg'
    cv.imwrite(str(all_cases_path), board_with_cases)
    print()
    print(f"✓ Vue d'ensemble avec cases: {all_cases_path}")
    
    # Afficher si demandé
    if args.show:
        print()
        print("📺 Affichage... (Appuyez sur 'q' pour fermer)")
        
        # Agrandir pour mieux voir
        scale = 2.0
        display_img = cv.resize(board_with_cases, None, fx=scale, fy=scale, 
                                interpolation=cv.INTER_NEAREST)
        
        cv.imshow('Calibration Cases', display_img)
        
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
