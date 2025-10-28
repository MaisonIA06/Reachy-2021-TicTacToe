#!/usr/bin/env python3
"""
Script pour créer des modèles TFLite ultra-simples (évite les bugs Keras 3)
"""

import os
import sys
import numpy as np

try:
    import tensorflow as tf
except ImportError:
    print("❌ TensorFlow n'est pas installé.")
    sys.exit(1)

print("="*70)
print("Création de modèles TFLite ultra-simples")
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
    Crée un modèle CNN TRÈS simple sans Dropout (évite les bugs TFLite)
    """
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=input_shape),
        
        # Bloc 1 - Simple
        tf.keras.layers.Conv2D(16, 3, activation='relu', padding='same'),
        tf.keras.layers.MaxPooling2D(2),
        
        # Bloc 2 - Simple
        tf.keras.layers.Conv2D(32, 3, activation='relu', padding='same'),
        tf.keras.layers.MaxPooling2D(2),
        
        # Bloc 3 - Simple
        tf.keras.layers.Conv2D(64, 3, activation='relu', padding='same'),
        tf.keras.layers.GlobalAveragePooling2D(),
        
        # Classification
        tf.keras.layers.Dense(num_classes, activation='softmax')
    ])
    
    # Compiler le modèle
    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    
    # IMPORTANT: Initialiser le modèle avec un appel fictif
    # Cela initialise tous les poids et évite les bugs de conversion
    dummy_input = tf.random.normal([1, 224, 224, 3])
    _ = model(dummy_input, training=False)
    
    return model


def convert_to_tflite_simple(model, output_path):
    """
    Conversion TFLite la plus simple possible
    """
    try:
        print(f"   Conversion directe en TFLite...")
        
        # Conversion DIRECTE sans SavedModel (plus fiable)
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        
        # Configuration minimale
        converter.target_spec.supported_ops = [
            tf.lite.OpsSet.TFLITE_BUILTINS,
        ]
        
        # Pas d'optimisations
        # converter.optimizations = [tf.lite.Optimize.DEFAULT]
        
        # Convertir
        tflite_model = converter.convert()
        
        # Sauvegarder
        with open(output_path, 'wb') as f:
            f.write(tflite_model)
        
        print(f"✓ Modèle créé: {os.path.basename(output_path)}")
        print(f"  Taille: {len(tflite_model) / 1024:.1f} KB")
        
        return len(tflite_model)
        
    except Exception as e:
        print(f"❌ Erreur lors de la conversion: {e}")
        print()
        print("Tentative avec méthode alternative (fichier .keras)...")
        
        # Méthode alternative : sauvegarder en .keras puis convertir
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(suffix='.keras', delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            # Sauvegarder en format .keras
            model.save(temp_path)
            
            # Recharger
            loaded_model = tf.keras.models.load_model(temp_path)
            
            # Convertir
            converter = tf.lite.TFLiteConverter.from_keras_model(loaded_model)
            converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS]
            tflite_model = converter.convert()
            
            # Sauvegarder
            with open(output_path, 'wb') as f:
                f.write(tflite_model)
            
            print(f"✓ Modèle créé (méthode alternative): {os.path.basename(output_path)}")
            print(f"  Taille: {len(tflite_model) / 1024:.1f} KB")
            
            return len(tflite_model)
            
        finally:
            # Nettoyer
            if os.path.exists(temp_path):
                os.unlink(temp_path)


# 1. Créer le modèle boxes
print("1️⃣  Création du modèle de classification des cases...")
print("   Architecture: CNN ultra-simple (pas de Dropout)")
print()

old_boxes_path = os.path.join(models_dir, 'ttt-boxes.tflite')
if os.path.exists(old_boxes_path):
    backup_path = os.path.join(models_dir, 'ttt-boxes-OLD.tflite')
    if not os.path.exists(backup_path):
        os.rename(old_boxes_path, backup_path)
        print(f"   ↪ Ancien modèle sauvegardé: {os.path.basename(backup_path)}")

boxes_model = create_simple_model(num_classes=3, input_shape=(224, 224, 3))
print(f"   Paramètres: {boxes_model.count_params():,}")
size_boxes = convert_to_tflite_simple(boxes_model, old_boxes_path)
print()


# 2. Créer le modèle valid
print("2️⃣  Création du modèle de validation du plateau...")
print("   Architecture: CNN ultra-simple (pas de Dropout)")
print()

old_valid_path = os.path.join(models_dir, 'ttt-valid-board.tflite')
if os.path.exists(old_valid_path):
    backup_path = os.path.join(models_dir, 'ttt-valid-board-OLD.tflite')
    if not os.path.exists(backup_path):
        os.rename(old_valid_path, backup_path)
        print(f"   ↪ Ancien modèle sauvegardé: {os.path.basename(backup_path)}")

valid_model = create_simple_model(num_classes=2, input_shape=(224, 224, 3))
print(f"   Paramètres: {valid_model.count_params():,}")
size_valid = convert_to_tflite_simple(valid_model, old_valid_path)
print()


# 3. Tester les modèles
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
    print("✅ Modèles ultra-simples créés avec succès !")
    print("="*70)
    print()
    print(f"📊 Taille totale: {(size_boxes + size_valid) / 1024:.1f} KB")
    print()
    print("⚠️  IMPORTANT:")
    print("   Ces modèles sont ultra-basiques et NON entraînés.")
    print("   Ils permettent de TESTER le système sans erreur.")
    print("   La détection sera aléatoire jusqu'à ce que vous les entraîniez.")
    print()
    print("   Pour une VRAIE détection:")
    print("   1. Collectez des images: notebooks/Collect_training_images.ipynb")
    print("   2. Entraînez: notebooks/Train_classifier.ipynb")
    print()
    print("Vous pouvez maintenant tester le système:")
    print("   python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe")
    print()
else:
    print("="*70)
    print("⚠️  Certains modèles ont échoué")
    print("="*70)
    print()
    print("Les modèles n'ont pas pu être créés correctement.")
    print("Cela peut être dû à un problème de version de TensorFlow.")
    print()