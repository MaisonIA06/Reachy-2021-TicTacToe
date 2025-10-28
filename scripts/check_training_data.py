#!/usr/bin/env python3
"""
Script de vérification des données d'entraînement

Vérifie que vous avez collecté suffisamment d'images pour l'entraînement.

Usage:
    python scripts/check_training_data.py
"""

import os
import glob
from PIL import Image


def check_directory(path, min_images=100, recommended_images=300):
    """Vérifie un dossier d'images"""
    if not os.path.exists(path):
        return None, "❌ Dossier manquant"
    
    images = glob.glob(os.path.join(path, '*.jpg'))
    count = len(images)
    
    # Vérifier quelques images
    valid_images = 0
    errors = []
    
    for img_path in images[:10]:  # Vérifier les 10 premières
        try:
            img = Image.open(img_path)
            img.verify()
            valid_images += 1
        except Exception as e:
            errors.append(f"{os.path.basename(img_path)}: {e}")
    
    # Statut
    if count >= recommended_images:
        status = "✅ Excellent"
    elif count >= min_images:
        status = "⚠️ Acceptable"
    else:
        status = "❌ Insuffisant"
    
    return count, status, errors


def main():
    print("\n" + "="*70)
    print("📊 VÉRIFICATION DES DONNÉES D'ENTRAÎNEMENT")
    print("="*70)
    
    # Vérifier les données boxes
    print("\n1️⃣ MODÈLE TTT-BOXES (détection des cases)")
    print("-" * 70)
    
    boxes_dirs = {
        'empty': 'training_data/boxes/empty',
        'cube': 'training_data/boxes/cube',
        'cylinder': 'training_data/boxes/cylinder',
    }
    
    boxes_total = 0
    boxes_ready = True
    
    for label, path in boxes_dirs.items():
        count, status, *errors = check_directory(path, min_images=100, recommended_images=300)
        if count is None:
            print(f"  {status} {label:10s}")
            boxes_ready = False
        else:
            boxes_total += count
            print(f"  {status:15s} {label:10s}: {count:4d} images")
            
            if errors and errors[0]:
                print(f"    ⚠️ Erreurs détectées dans certaines images:")
                for err in errors[0][:3]:
                    print(f"       {err}")
            
            if count < 100:
                boxes_ready = False
    
    print(f"\n  📊 Total boxes: {boxes_total} images")
    print(f"  🎯 Objectif: 900-1500 images (300-500 par classe)")
    
    if boxes_total >= 900:
        print(f"  ✅ Prêt pour l'entraînement!")
    elif boxes_total >= 300:
        print(f"  ⚠️ Minimum atteint, mais plus d'images amélioreront la précision")
    else:
        print(f"  ❌ Pas assez d'images ({boxes_total}/300 minimum)")
    
    # Vérifier les données valid_board
    print("\n2️⃣ MODÈLE TTT-VALID-BOARD (validation du plateau)")
    print("-" * 70)
    
    valid_dirs = {
        'valid': 'training_data/valid_board/valid',
        'invalid': 'training_data/valid_board/invalid',
    }
    
    valid_total = 0
    valid_ready = True
    
    for label, path in valid_dirs.items():
        count, status, *errors = check_directory(path, min_images=50, recommended_images=100)
        if count is None:
            print(f"  {status} {label:10s}")
            valid_ready = False
        else:
            valid_total += count
            print(f"  {status:15s} {label:10s}: {count:4d} images")
            
            if errors and errors[0]:
                print(f"    ⚠️ Erreurs détectées dans certaines images:")
                for err in errors[0][:3]:
                    print(f"       {err}")
            
            if count < 50:
                valid_ready = False
    
    print(f"\n  📊 Total valid_board: {valid_total} images")
    print(f"  🎯 Objectif: 200-400 images (100-200 par classe)")
    
    if valid_total >= 200:
        print(f"  ✅ Prêt pour l'entraînement!")
    elif valid_total >= 100:
        print(f"  ⚠️ Minimum atteint, mais plus d'images amélioreront la précision")
    else:
        print(f"  ❌ Pas assez d'images ({valid_total}/100 minimum)")
    
    # Résumé final
    print("\n" + "="*70)
    print("📋 RÉSUMÉ")
    print("="*70)
    
    if boxes_ready and valid_ready:
        print("✅ Données suffisantes pour l'entraînement des deux modèles!")
        print("\n➡️ Prochaine étape:")
        print("   python scripts/train_models.py --model all")
    elif boxes_ready:
        print("✅ Données suffisantes pour ttt-boxes")
        print("❌ Données insuffisantes pour ttt-valid-board")
        print("\n➡️ Collectez plus d'images:")
        print("   python scripts/collect_valid_board_images.py --host localhost --class valid")
        print("   python scripts/collect_valid_board_images.py --host localhost --class invalid")
    elif valid_ready:
        print("✅ Données suffisantes pour ttt-valid-board")
        print("❌ Données insuffisantes pour ttt-boxes")
        print("\n➡️ Collectez plus d'images:")
        print("   python scripts/collect_boxes_images.py --host localhost --class empty")
        print("   python scripts/collect_boxes_images.py --host localhost --class cube")
        print("   python scripts/collect_boxes_images.py --host localhost --class cylinder")
    else:
        print("❌ Données insuffisantes pour les deux modèles")
        print("\n➡️ Commencez la collecte:")
        print("   1. python scripts/collect_boxes_images.py --host localhost --class empty")
        print("   2. python scripts/collect_boxes_images.py --host localhost --class cube")
        print("   3. python scripts/collect_boxes_images.py --host localhost --class cylinder")
        print("   4. python scripts/collect_valid_board_images.py --host localhost --class valid")
        print("   5. python scripts/collect_valid_board_images.py --host localhost --class invalid")
    
    print("\n💡 Conseils:")
    print("  - Variez l'éclairage (matin, après-midi, lumière artificielle)")
    print("  - Variez les positions des pièces")
    print("  - Bougez légèrement le plateau entre les captures")
    print("  - Supprimez les images floues ou avec votre main visible")


if __name__ == '__main__':
    main()

