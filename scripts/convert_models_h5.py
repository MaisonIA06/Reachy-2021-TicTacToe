#!/usr/bin/env python3
"""
Script pour créer des modèles TFLite en utilisant le format .h5 (plus compatible)
À exécuter sur votre PC, puis transférer les .tflite vers Reachy
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
print("Création de modèles TFLite via format H5")
print(f"TensorFlow version: {tf.__version__}")
print("="*70)
print()

# Chemins
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
models_dir = os.path.join(project_dir, 'reachy_tictactoe', 'models')

print(f"📁 Répertoire des modèles: {models_dir}")
print()


def create_model_functional(num_classes, input_shape=(224, 224, 3)):
    """
    Crée un modèle en API fonctionnelle (plus compatible que Sequential)
    """
    inputs = tf.keras.Input(shape=input_shape)
    
    # Bloc 1
    x = tf.keras.layers.Conv2D(16, 3, activation='relu', padding='same')(inputs)
    x = tf.keras.layers.MaxPooling2D(2)(x)
    
    # Bloc 2
    x = tf.keras.layers.Conv2D(32, 3, activation='relu', padding='same')(x)
    x = tf.keras.layers.MaxPooling2D(2)(x)
    
    # Bloc 3
    x = tf.keras.layers.Conv2D(64, 3, activation='relu', padding='same')(x)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    
    # Classification
    outputs = tf.keras.layers.Dense(num_classes, activation='softmax')(x)
    
    model = tf.keras.Model(inputs=inputs, outputs=outputs)
    
    # Compiler
    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    
    return model


def convert_via_h5(model, output_path):
    """
    Convertit en TFLite via fichier .h5 (méthode la plus stable)
    """
    import tempfile
    
    # Créer un fichier temporaire .h5
    temp_h5 = tempfile.NamedTemporaryFile(suffix='.h5', delete=False)
    temp_h5.close()
    
    try:
        print(f"   Sauvegarde en format H5...")
        # Sauvegarder en H5 (ancien format, très compatible)
        model.save(temp_h5.name, save_format='h5')
        
        print(f"   Rechargement du modèle H5...")
        # Recharger le modèle
        loaded_model = tf.keras.models.load_model(temp_h5.name)
        
        print(f"   Conversion en TFLite...")
        # Convertir
        converter = tf.lite.TFLiteConverter.from_keras_model(loaded_model)
        converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS]
        
        tflite_model = converter.convert()
        
        # Sauvegarder
        with open(output_path, 'wb') as f:
            f.write(tflite_model)
        
        print(f"✓ Modèle créé: {os.path.basename(output_path)}")
        print(f"  Taille: {len(tflite_model) / 1024:.1f} KB")
        
        return len(tflite_model)
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        raise
        
    finally:
        # Nettoyer
        if os.path.exists(temp_h5.name):
            os.unlink(temp_h5.name)


# 1. Créer le modèle boxes
print("1️⃣  Création du modèle de classification des cases...")
print("   Architecture: CNN simple en API fonctionnelle")
print()

old_boxes_path = os.path.join(models_dir, 'ttt-boxes.tflite')
if os.path.exists(old_boxes_path):
    backup_path = os.path.join(models_dir, 'ttt-boxes-OLD2.tflite')
    if not os.path.exists(backup_path):
        os.rename(old_boxes_path, backup_path)
        print(f"   ↪ Ancien modèle sauvegardé: {os.path.basename(backup_path)}")

boxes_model = create_model_functional(num_classes=3, input_shape=(224, 224, 3))
print(f"   Paramètres: {boxes_model.count_params():,}")
size_boxes = convert_via_h5(boxes_model, old_boxes_path)
print()


# 2. Créer le modèle valid
print("2️⃣  Création du modèle de validation du plateau...")
print("   Architecture: CNN simple en API fonctionnelle")
print()

old_valid_path = os.path.join(models_dir, 'ttt-valid-board.tflite')
if os.path.exists(old_valid_path):
    backup_path = os.path.join(models_dir, 'ttt-valid-board-OLD2.tflite')
    if not os.path.exists(backup_path):
        os.rename(old_valid_path, backup_path)
        print(f"   ↪ Ancien modèle sauvegardé: {os.path.basename(backup_path)}")

valid_model = create_model_functional(num_classes=2, input_shape=(224, 224, 3))
print(f"   Paramètres: {valid_model.count_params():,}")
size_valid = convert_via_h5(valid_model, old_valid_path)
print()


# 3. Tester
print("3️⃣  Test de compatibilité...")

success_count = 0

try:
    interpreter = tf.lite.Interpreter(old_boxes_path)
    interpreter.allocate_tensors()
    print("   ✓ ttt-boxes.tflite fonctionne ✅")
    success_count += 1
except Exception as e:
    print(f"   ❌ ttt-boxes.tflite: {e}")

try:
    interpreter = tf.lite.Interpreter(old_valid_path)
    interpreter.allocate_tensors()
    print("   ✓ ttt-valid-board.tflite fonctionne ✅")
    success_count += 1
except Exception as e:
    print(f"   ❌ ttt-valid-board.tflite: {e}")

print()

if success_count == 2:
    print("="*70)
    print("✅ Modèles créés avec succès !")
    print("="*70)
    print()
    print(f"📊 Taille totale: {(size_boxes + size_valid) / 1024:.1f} KB")
    print()
    print("📤 TRANSFÉRER LES MODÈLES VERS REACHY:")
    print()
    print("   scp reachy_tictactoe/models/ttt-boxes.tflite \\")
    print("       reachy@<IP>:~/dev/Reachy-2021-TicTacToe/reachy_tictactoe/models/")
    print()
    print("   scp reachy_tictactoe/models/ttt-valid-board.tflite \\")
    print("       reachy@<IP>:~/dev/Reachy-2021-TicTacToe/reachy_tictactoe/models/")
    print()
    print("⚠️  Ces modèles sont NON entraînés (détection aléatoire).")
    print("   Entraînez-les avec vos données pour une vraie détection.")
    print()
else:
    print("⚠️  Certains modèles ont échoué.")
    print()