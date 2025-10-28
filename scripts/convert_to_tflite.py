#!/usr/bin/env python3
"""
Script de conversion des modèles H5 vers TFLite

Convertit les modèles entraînés (.h5) en modèles TensorFlow Lite (.tflite)
optimisés pour CPU.

Usage:
    python scripts/convert_to_tflite.py --model boxes
    python scripts/convert_to_tflite.py --model valid-board
    python scripts/convert_to_tflite.py --model all
"""

import argparse
import os
import tensorflow as tf
import shutil
from datetime import datetime


def backup_existing_model(tflite_path):
    """Fait un backup du modèle existant s'il existe"""
    if os.path.exists(tflite_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = tflite_path.replace('.tflite', f'_backup_{timestamp}.tflite')
        shutil.copy2(tflite_path, backup_path)
        print(f"📦 Backup créé: {backup_path}")
        return backup_path
    return None


def convert_h5_to_tflite(h5_path, tflite_path, optimize=True):
    """
    Convertit un modèle Keras (.h5) en TFLite
    
    Args:
        h5_path: Chemin vers le modèle .h5
        tflite_path: Chemin de sortie .tflite
        optimize: Si True, applique les optimisations
    
    Returns:
        True si succès, False sinon
    """
    print(f"\n🔄 Conversion: {h5_path} -> {tflite_path}")
    
    if not os.path.exists(h5_path):
        print(f"❌ Erreur: {h5_path} n'existe pas!")
        return False
    
    try:
        # Charger le modèle Keras
        print("  📂 Chargement du modèle H5...")
        model = tf.keras.models.load_model(h5_path)
        print(f"  ✅ Modèle chargé (entrée: {model.input_shape}, sortie: {model.output_shape})")
        
        # Créer le convertisseur
        print("  🔧 Création du convertisseur TFLite...")
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        
        # Optimisations pour CPU
        if optimize:
            print("  ⚡ Application des optimisations...")
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
            # Quantification dynamique pour réduire la taille et accélérer l'inférence
            converter.target_spec.supported_types = [tf.float16]
        
        # Convertir
        print("  🔄 Conversion en cours...")
        tflite_model = converter.convert()
        
        # Sauvegarder
        os.makedirs(os.path.dirname(tflite_path), exist_ok=True)
        with open(tflite_path, 'wb') as f:
            f.write(tflite_model)
        
        # Statistiques
        h5_size = os.path.getsize(h5_path) / (1024 * 1024)
        tflite_size = os.path.getsize(tflite_path) / (1024 * 1024)
        reduction = (1 - tflite_size/h5_size) * 100
        
        print(f"  ✅ Conversion réussie!")
        print(f"  📊 Taille H5: {h5_size:.2f} MB")
        print(f"  📊 Taille TFLite: {tflite_size:.2f} MB")
        print(f"  📉 Réduction: {reduction:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur lors de la conversion: {e}")
        return False


def test_tflite_model(tflite_path, input_shape=(1, 224, 224, 3)):
    """
    Teste que le modèle TFLite fonctionne
    
    Args:
        tflite_path: Chemin vers le modèle .tflite
        input_shape: Shape de l'entrée
    
    Returns:
        True si le test réussit, False sinon
    """
    print(f"\n🧪 Test du modèle: {tflite_path}")
    
    try:
        # Charger l'interpréteur
        interpreter = tf.lite.Interpreter(model_path=tflite_path)
        interpreter.allocate_tensors()
        
        # Obtenir les détails des tenseurs
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        
        print(f"  ✅ Modèle chargé")
        print(f"  📥 Entrée: {input_details[0]['shape']} (type: {input_details[0]['dtype']})")
        print(f"  📤 Sortie: {output_details[0]['shape']} (type: {output_details[0]['dtype']})")
        
        # Test avec des données aléatoires
        import numpy as np
        test_input = np.random.rand(*input_shape).astype(np.float32)
        
        interpreter.set_tensor(input_details[0]['index'], test_input)
        interpreter.invoke()
        output = interpreter.get_tensor(output_details[0]['index'])
        
        print(f"  ✅ Inférence de test réussie")
        print(f"  📊 Sortie: {output.shape}, somme={output.sum():.4f}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur lors du test: {e}")
        return False


def create_label_file(source_labels, dest_labels):
    """Copie le fichier de labels"""
    if os.path.exists(source_labels):
        shutil.copy2(source_labels, dest_labels)
        print(f"✅ Labels copiés: {dest_labels}")
        return True
    else:
        print(f"⚠️ Fichier de labels source non trouvé: {source_labels}")
        return False


def convert_boxes_model():
    """Convertit le modèle boxes"""
    print("\n" + "="*70)
    print("📦 CONVERSION DU MODÈLE TTT-BOXES")
    print("="*70)
    
    h5_path = 'models/ttt-boxes.h5'
    tflite_path = 'reachy_tictactoe/models/ttt-boxes.tflite'
    labels_src = 'models/ttt-boxes_labels.txt'
    labels_dest = 'reachy_tictactoe/models/ttt-boxes.txt'
    
    # Backup
    backup_existing_model(tflite_path)
    
    # Conversion
    success = convert_h5_to_tflite(h5_path, tflite_path, optimize=True)
    
    if success:
        # Test
        test_tflite_model(tflite_path)
        
        # Labels
        create_label_file(labels_src, labels_dest)
        
        print(f"\n✅ Modèle boxes converti avec succès!")
        print(f"   Emplacement: {tflite_path}")
    
    return success


def convert_valid_board_model():
    """Convertit le modèle valid-board"""
    print("\n" + "="*70)
    print("📦 CONVERSION DU MODÈLE TTT-VALID-BOARD")
    print("="*70)
    
    h5_path = 'models/ttt-valid-board.h5'
    tflite_path = 'reachy_tictactoe/models/ttt-valid-board.tflite'
    labels_src = 'models/ttt-valid-board_labels.txt'
    labels_dest = 'reachy_tictactoe/models/ttt-valid-board.txt'
    
    # Backup
    backup_existing_model(tflite_path)
    
    # Conversion
    success = convert_h5_to_tflite(h5_path, tflite_path, optimize=True)
    
    if success:
        # Test
        test_tflite_model(tflite_path)
        
        # Labels
        create_label_file(labels_src, labels_dest)
        
        print(f"\n✅ Modèle valid-board converti avec succès!")
        print(f"   Emplacement: {tflite_path}")
    
    return success


def main():
    parser = argparse.ArgumentParser(description='Convertir les modèles H5 en TFLite')
    parser.add_argument('--model', 
                       choices=['boxes', 'valid-board', 'all'],
                       default='all',
                       help='Modèle à convertir (défaut: all)')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🔄 CONVERSION DES MODÈLES EN TFLITE")
    print("="*70)
    print(f"TensorFlow version: {tf.__version__}")
    print(f"Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = True
    
    # Convertir selon le choix
    if args.model in ['boxes', 'all']:
        success = convert_boxes_model() and success
        print("\n")
    
    if args.model in ['valid-board', 'all']:
        success = convert_valid_board_model() and success
        print("\n")
    
    # Résumé final
    print("="*70)
    print("📋 RÉSUMÉ")
    print("="*70)
    
    if success:
        print("✅ Conversion(s) terminée(s) avec succès!")
        print("\n📂 Modèles finaux:")
        
        if args.model in ['boxes', 'all']:
            tflite_boxes = 'reachy_tictactoe/models/ttt-boxes.tflite'
            labels_boxes = 'reachy_tictactoe/models/ttt-boxes.txt'
            if os.path.exists(tflite_boxes):
                size = os.path.getsize(tflite_boxes) / (1024 * 1024)
                print(f"  ✅ {tflite_boxes} ({size:.2f} MB)")
            if os.path.exists(labels_boxes):
                print(f"  ✅ {labels_boxes}")
        
        if args.model in ['valid-board', 'all']:
            tflite_valid = 'reachy_tictactoe/models/ttt-valid-board.tflite'
            labels_valid = 'reachy_tictactoe/models/ttt-valid-board.txt'
            if os.path.exists(tflite_valid):
                size = os.path.getsize(tflite_valid) / (1024 * 1024)
                print(f"  ✅ {tflite_valid} ({size:.2f} MB)")
            if os.path.exists(labels_valid):
                print(f"  ✅ {labels_valid}")
        
        print("\n➡️ Prochaine étape:")
        print("   python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe_test")
        print("\n💡 Testez les modèles en conditions réelles!")
    else:
        print("❌ Une ou plusieurs conversions ont échoué")
        print("Vérifiez les messages d'erreur ci-dessus")


if __name__ == '__main__':
    main()

