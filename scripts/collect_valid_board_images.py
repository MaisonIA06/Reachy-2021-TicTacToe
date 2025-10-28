#!/usr/bin/env python3
"""
Script de collecte d'images pour le modèle ttt-valid-board.tflite

Ce script vous aide à collecter les images nécessaires pour entraîner
le modèle de validation du plateau (valid/invalid).

Usage:
    python scripts/collect_valid_board_images.py --host localhost --class valid
    python scripts/collect_valid_board_images.py --host localhost --class invalid
"""

import argparse
import cv2
import time
import os
from datetime import datetime
from reachy_sdk import ReachySDK


def warm_up_head(reachy, cycles=10):
    """Échauffe les moteurs de la tête"""
    print(f"🔥 Échauffement des moteurs ({cycles} cycles)...")
    for i in range(cycles):
        reachy.head.look_at(x=0.5, y=0, z=-0.4, duration=1.0)
        time.sleep(0.5)
        reachy.head.look_at(x=0.5, y=0, z=0, duration=1.0)
        time.sleep(0.5)
        print(f"  Cycle {i+1}/{cycles}", end='\r')
    
    reachy.head.look_at(x=0.5, y=0, z=0, duration=1.5)
    time.sleep(1.5)
    print("\n✅ Échauffement terminé")


def capture_board(reachy, save_dir, class_label):
    """
    Capture le plateau complet
    
    Args:
        reachy: Instance ReachySDK
        save_dir: Dossier de sauvegarde
        class_label: Label de la classe ('valid' ou 'invalid')
    
    Returns:
        True si succès, False sinon
    """
    # Regarder le plateau
    reachy.head.look_at(x=0.5, y=0, z=-0.6, duration=1.0)
    time.sleep(1.0)
    
    # Capturer
    img = reachy.right_camera.last_frame
    
    if img is None:
        print("❌ Erreur: pas d'image capturée")
        return False
    
    # Revenir en position repos
    reachy.head.look_at(x=0.5, y=0, z=0, duration=1.0)
    
    # Sauvegarder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{class_label}_{timestamp}.jpg"
    filepath = os.path.join(save_dir, filename)
    cv2.imwrite(filepath, img)
    
    return True


def collect_valid_boards(reachy, save_dir, target_count=150):
    """Collecte des images de plateaux valides"""
    print("\n" + "="*70)
    print("📸 COLLECTE DES PLATEAUX VALIDES")
    print("="*70)
    print(f"Objectif: {target_count} images")
    print("\n⚠️ Instructions:")
    print("  1. Assurez-vous que le plateau est bien centré")
    print("  2. Le plateau doit être entièrement visible")
    print("  3. Éclairage correct")
    print("  4. Appuyez sur Entrée pour capturer")
    print("  5. Variez légèrement la position/éclairage entre les captures")
    print("  6. Tapez 'stop' pour arrêter\n")
    
    capture_count = 0
    
    input("Appuyez sur Entrée quand vous êtes prêt...")
    
    while capture_count < target_count:
        user_input = input(f"\nCapture #{capture_count+1}/{target_count} - Entrée pour capturer (ou 'stop'): ")
        
        if user_input.lower() == 'stop':
            break
        
        if capture_board(reachy, save_dir, 'valid'):
            capture_count += 1
            print(f"  ✅ Image sauvegardée ({capture_count}/{target_count})")
        else:
            print(f"  ❌ Échec de la capture")
        
        time.sleep(0.5)
    
    print(f"\n🎉 Collecte terminée: {capture_count} images de plateaux valides!")
    return capture_count


def collect_invalid_boards(reachy, save_dir, target_count=150):
    """Collecte des images de plateaux invalides"""
    print("\n" + "="*70)
    print("📸 COLLECTE DES PLATEAUX INVALIDES")
    print("="*70)
    print(f"Objectif: {target_count} images")
    print("\n⚠️ Instructions:")
    print("  Créez des situations INVALIDES, par exemple:")
    print("    - Plateau décentré ou mal orienté")
    print("    - Plateau partiellement caché")
    print("    - Mauvais éclairage (trop sombre/clair)")
    print("    - Pas de plateau du tout")
    print("    - Plateau trop proche/trop loin")
    print("    - Main ou objet devant le plateau")
    print("\n  Appuyez sur Entrée pour capturer")
    print("  Tapez 'stop' pour arrêter\n")
    
    capture_count = 0
    
    input("Appuyez sur Entrée quand vous êtes prêt...")
    
    while capture_count < target_count:
        print(f"\n--- Capture #{capture_count+1}/{target_count} ---")
        print("Suggestions de situations invalides:")
        situations = [
            "Déplacez le plateau hors du cadre",
            "Tournez le plateau à 45 degrés",
            "Couvrez une partie du plateau",
            "Éteignez une lumière",
            "Mettez votre main devant",
            "Retirez complètement le plateau",
            "Plateau trop près de la caméra",
            "Plateau trop loin"
        ]
        import random
        print(f"💡 Suggestion: {random.choice(situations)}")
        
        user_input = input(f"\nEntrée pour capturer (ou 'stop'): ")
        
        if user_input.lower() == 'stop':
            break
        
        if capture_board(reachy, save_dir, 'invalid'):
            capture_count += 1
            print(f"  ✅ Image sauvegardée ({capture_count}/{target_count})")
        else:
            print(f"  ❌ Échec de la capture")
        
        time.sleep(0.5)
    
    print(f"\n🎉 Collecte terminée: {capture_count} images de plateaux invalides!")
    return capture_count


def main():
    parser = argparse.ArgumentParser(description='Collecte d\'images pour ttt-valid-board')
    parser.add_argument('--host', default='localhost', help='Adresse IP de Reachy')
    parser.add_argument('--class', dest='class_label', 
                       choices=['valid', 'invalid'],
                       required=True,
                       help='Classe à collecter')
    parser.add_argument('--target', type=int, default=150,
                       help='Nombre d\'images cibles (défaut: 150)')
    
    args = parser.parse_args()
    
    # Définir le dossier de sauvegarde
    save_dir = f'training_data/valid_board/{args.class_label}'
    if not os.path.exists(save_dir):
        print(f"❌ Erreur: le dossier {save_dir} n'existe pas!")
        print("Exécutez d'abord: mkdir -p training_data/valid_board/{valid,invalid}")
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
        if args.class_label == 'valid':
            total = collect_valid_boards(reachy, save_dir, args.target)
        else:
            total = collect_invalid_boards(reachy, save_dir, args.target)
        
        # Statistiques
        print("\n" + "="*70)
        print("📊 STATISTIQUES")
        print("="*70)
        existing_count = len([f for f in os.listdir(save_dir) if f.endswith('.jpg')])
        print(f"Total d'images dans {save_dir}: {existing_count}")
        print(f"Recommandé: 100-200 images par classe")
        
        if existing_count >= 100:
            print("✅ Objectif atteint!")
        elif existing_count >= 50:
            print("⚠️ Continuez à collecter pour atteindre 100 images")
        else:
            print("❌ Continuez à collecter (encore besoin de plus d'images)")
        
    finally:
        # Désactivation
        print("\n🔄 Retour en position repos...")
        reachy.head.look_at(x=0.5, y=0, z=0, duration=1.5)
        time.sleep(1.5)
        reachy.turn_off('head')
        print("✅ Reachy désactivé")


if __name__ == '__main__':
    main()

