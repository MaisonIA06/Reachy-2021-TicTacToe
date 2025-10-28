#!/usr/bin/env python3
"""
Script pour créer des modèles TFLite ultra-compatibles (compatible avec anciennes versions)
"""

import os
import sys
import numpy as np

try:
    import tensorflow as tf
except ImportError:
    print("❌ TensorFlow n'est pas installé.")
    print("Installez-le avec: pip install tensorflow")
    sys.exit(1)

print("="*70)
print("Création de modèles TFLite ultra-compatibles")
print(f"TensorFlow version: {tf.__version__}")
print("="*70)
print()

# Chemins
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
models_dir = os.path.join(project_dir, 'reachy_tictactoe', 'models')

print(f"📁 Répertoire des modèles: {models_dir}")
print()


def create_simple_model(num_classes, input_shape=(224, 224, 3)):
    """
    Crée un modèle CNN simple sans MobileNet (plus compatible)
    """
    model = tf.keras.Sequential([
        tf.keras.layers.InputLayer(input_shape=input_shape),
        
        # Bloc 1
        tf.keras.layers.Conv2D(16, 3, activation='relu', padding='same'),
        tf.keras.layers.MaxPooling2D(2),
        tf.keras.layers.Dropout(0.2),
        
        # Bloc 2
        tf.keras.layers.Conv2D(32, 3, activation='relu', padding='same'),
        tf.keras.layers.MaxPooling2D(2),
        tf.keras.layers.Dropout(0.2),
        
        # Bloc 3
        tf.keras.layers.Conv2D(64, 3, activation='relu', padding='same'),
        tf.keras.layers.GlobalAveragePooling2D(),
        tf.keras.layers.Dropout(0.3),
        
        # Classification
        tf.keras.layers.Dense(num_classes, activation='softmax')
    ])
    
    # IMPORTANT: Compiler le modèle avant conversion
    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    
    # IMPORTANT: Construire le modèle en appelant build()
    model.build((None,) + input_shape)
    
    return model


def convert_to_tflite_compatible(model, output_path):
    """
    Convertit en TFLite avec compatibilité maximale
    """
    import tempfile
    import shutil
    
    # Créer un répertoire temporaire
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Sauvegarder d'abord en format SavedModel
        print(f"   Sauvegarde temporaire en SavedModel...")
        model.save(temp_dir, save_format='tf')
        
        # Convertir depuis SavedModel (plus compatible)
        print(f"   Conversion en TFLite...")
        converter = tf.lite.TFLiteConverter.from_saved_model(temp_dir)
        
        # Configuration BASIQUE pour compatibilité maximale
        converter.target_spec.supported_ops = [
            tf.lite.OpsSet.TFLITE_BUILTINS,
        ]
        
        # Pas d'optimisations pour éviter les incompatibilités de version
        # converter.optimizations = [tf.lite.Optimize.DEFAULT]  # Désactivé
        
        # Convertir
        tflite_model = converter.convert()
        
        # Sauvegarder
        with open(output_path, 'wb') as f:
            f.write(tflite_model)
        
        print(f"✓ Modèle créé: {os.path.basename(output_path)}")
        print(f"  Taille: {len(tflite_model) / 1024:.1f} KB")
        
        return len(tflite_model)
        
    finally:
        # Nettoyer le répertoire temporaire
        shutil.rmtree(temp_dir, ignore_errors=True)


# 1. Créer le modèle boxes
print("1️⃣  Création du modèle de classification des cases...")
print("   Architecture: CNN simple (ultra-compatible)")
print()

old_boxes_path = os.path.join(models_dir, 'ttt-boxes.tflite')
if os.path.exists(old_boxes_path):
    backup_path = os.path.join(models_dir, 'ttt-boxes-OLD.tflite')
    if not os.path.exists(backup_path):
        os.rename(old_boxes_path, backup_path)
        print(f"   ↪ Ancien modèle sauvegardé: {os.path.basename(backup_path)}")

boxes_model = create_simple_model(num_classes=3, input_shape=(224, 224, 3))
print(f"   Paramètres: {boxes_model.count_params():,}")
size_boxes = convert_to_tflite_compatible(boxes_model, old_boxes_path)
print()


# 2. Créer le modèle valid
print("2️⃣  Création du modèle de validation du plateau...")
print("   Architecture: CNN simple (ultra-compatible)")
print()

old_valid_path = os.path.join(models_dir, 'ttt-valid-board.tflite')
if os.path.exists(old_valid_path):
    backup_path = os.path.join(models_dir, 'ttt-valid-board-OLD.tflite')
    if not os.path.exists(backup_path):
        os.rename(old_valid_path, backup_path)
        print(f"   ↪ Ancien modèle sauvegardé: {os.path.basename(backup_path)}")

valid_model = create_simple_model(num_classes=2, input_shape=(224, 224, 3))
print(f"   Paramètres: {valid_model.count_params():,}")
size_valid = convert_to_tflite_compatible(valid_model, old_valid_path)
print()


# 3. Tester
print("3️⃣  Test de compatibilité...")

try:
    import tensorflow.lite as tflite
    
    interpreter = tflite.Interpreter(old_boxes_path)
    interpreter.allocate_tensors()
    print("   ✓ ttt-boxes.tflite fonctionne ✅")
except Exception as e:
    print(f"   ❌ ttt-boxes.tflite: {e}")

try:
    interpreter = tflite.Interpreter(old_valid_path)
    interpreter.allocate_tensors()
    print("   ✓ ttt-valid-board.tflite fonctionne ✅")
except Exception as e:
    print(f"   ❌ ttt-valid-board.tflite: {e}")

print()
print("="*70)
print("✅ Modèles ultra-compatibles créés !")
print("="*70)
print()
print(f"📊 Taille totale: {(size_boxes + size_valid) / 1024:.1f} KB")
print()
print("⚠️  IMPORTANT:")
print("   Ces modèles sont basiques (CNN simple) et NON entraînés.")
print("   Ils donneront des résultats aléatoires sans entraînement.")
print()
print("   Pour une VRAIE détection, vous DEVEZ les entraîner avec vos données:")
print("   1. Collectez des images: notebooks/Collect_training_images.ipynb")
print("   2. Entraînez: notebooks/Train_classifier.ipynb")
print()
print("Vous pouvez maintenant relancer le jeu pour tester le système:")
print("   python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe")
print()