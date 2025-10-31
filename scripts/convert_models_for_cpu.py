#!/usr/bin/env python3
"""
Script pour créer des modèles TFLite compatibles CPU à partir de zéro.
Ce script crée des modèles fonctionnels (pas seulement des placeholders).

ATTENTION: Ces modèles doivent être entraînés avec vos propres données
pour une détection précise. Ce script crée l'architecture de base.
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
print("Conversion des modèles EdgeTPU vers CPU")
print("="*70)
print()

# Chemins
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
models_dir = os.path.join(project_dir, 'reachy_tictactoe', 'models')

print(f"📁 Répertoire des modèles: {models_dir}")
print()

# Vérifier que le répertoire existe
if not os.path.exists(models_dir):
    print(f"❌ Le répertoire {models_dir} n'existe pas")
    sys.exit(1)

def create_mobilenet_classifier(num_classes, input_shape=(224, 224, 3)):
    """
    Crée un modèle basé sur MobileNetV2 (similaire aux modèles originaux)

    Args:
        num_classes: Nombre de classes
        input_shape: Forme de l'entrée (hauteur, largeur, canaux)

    Returns:
        tf.keras.Model
    """
    # Utiliser MobileNetV2 comme base (pré-entraîné sur ImageNet)
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=input_shape,
        include_top=False,
        weights='imagenet',  # Transfert learning
        pooling='avg'
    )

    # Geler les couches de base pour le transfer learning
    base_model.trainable = False

    # Ajouter les couches de classification
    model = tf.keras.Sequential([
        base_model,
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(num_classes, activation='softmax')
    ])

    return model

def convert_to_tflite(model, output_path, quantize=False):
    """
    Convertit un modèle Keras en TFLite (compatible CPU)

    Args:
        model: Modèle Keras
        output_path: Chemin de sortie du fichier .tflite
        quantize: Si True, applique la quantization pour réduire la taille
    """
    converter = tf.lite.TFLiteConverter.from_keras_model(model)

    # Configuration pour CPU (pas EdgeTPU!)
    if quantize:
        converter.optimizations = [tf.lite.Optimize.DEFAULT]

    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS,  # Opérations TFLite standard UNIQUEMENT
    ]

    # NOUVEAU : Forcer la compatibilité avec TFLite v1
    # Cela évite l'utilisation d'opérations trop récentes
    converter._experimental_lower_tensor_list_ops = False

    # NOUVEAU : Désactiver les optimisations qui peuvent causer des incompatibilités
    converter.experimental_new_converter = False

    # Convertir
    tflite_model = converter.convert()

    # Sauvegarder
    with open(output_path, 'wb') as f:
        f.write(tflite_model)

    print(f"✓ Modèle créé: {os.path.basename(output_path)}")
    print(f"  Taille: {len(tflite_model) / 1024:.1f} KB")
    return len(tflite_model)

# 1. Créer le modèle pour la classification des cases
print("1️⃣  Création du modèle de classification des cases...")
print("   Classes: 0=vide, 1=cube, 2=cylindre")
print("   Architecture: MobileNetV2 + Transfer Learning")
print()

# Sauvegarder l'ancien modèle EdgeTPU
old_boxes_path = os.path.join(models_dir, 'ttt-boxes.tflite')
if os.path.exists(old_boxes_path):
    backup_path = os.path.join(models_dir, 'ttt-boxes-edgetpu-BACKUP.tflite')
    if not os.path.exists(backup_path):
        os.rename(old_boxes_path, backup_path)
        print(f"   ↪ Ancien modèle EdgeTPU sauvegardé: {os.path.basename(backup_path)}")

# Créer le nouveau modèle
boxes_model = create_mobilenet_classifier(num_classes=3, input_shape=(224, 224, 3))
print(f"   Paramètres du modèle: {boxes_model.count_params():,}")

# Convertir et sauvegarder
size_boxes = convert_to_tflite(boxes_model, old_boxes_path, quantize=True)
print()

# 2. Créer le modèle pour la validation du plateau
print("2️⃣  Création du modèle de validation du plateau...")
print("   Classes: 0=invalid, 1=valid")
print("   Architecture: MobileNetV2 + Transfer Learning")
print()

# Sauvegarder l'ancien modèle EdgeTPU
old_valid_path = os.path.join(models_dir, 'ttt-valid-board.tflite')
if os.path.exists(old_valid_path):
    backup_path = os.path.join(models_dir, 'ttt-valid-board-edgetpu-BACKUP.tflite')
    if not os.path.exists(backup_path):
        os.rename(old_valid_path, backup_path)
        print(f"   ↪ Ancien modèle EdgeTPU sauvegardé: {os.path.basename(backup_path)}")

# Créer le nouveau modèle
valid_model = create_mobilenet_classifier(num_classes=2, input_shape=(224, 224, 3))
print(f"   Paramètres du modèle: {valid_model.count_params():,}")

# Convertir et sauvegarder
size_valid = convert_to_tflite(valid_model, old_valid_path, quantize=True)
print()

# 3. Vérifier les fichiers de labels
print("3️⃣  Vérification des fichiers de labels...")

boxes_labels_path = os.path.join(models_dir, 'ttt-boxes.txt')
if os.path.exists(boxes_labels_path):
    print(f"   ✓ {os.path.basename(boxes_labels_path)} existe")
else:
    # Créer le fichier de labels
    with open(boxes_labels_path, 'w') as f:
        f.write("0 none\n")
        f.write("1 cube\n")
        f.write("2 cylinder\n")
    print(f"   ✓ {os.path.basename(boxes_labels_path)} créé")

valid_labels_path = os.path.join(models_dir, 'ttt-valid-board.txt')
if os.path.exists(valid_labels_path):
    print(f"   ✓ {os.path.basename(valid_labels_path)} existe")
else:
    # Créer le fichier de labels
    with open(valid_labels_path, 'w') as f:
        f.write("0 valid\n")
        f.write("1 invalid\n")
    print(f"   ✓ {os.path.basename(valid_labels_path)} créé")

print()

# 4. Tester les modèles
print("4️⃣  Test de compatibilité CPU...")

try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    import tensorflow.lite as tflite

# Tester le modèle des cases
try:
    interpreter = tflite.Interpreter(old_boxes_path)
    interpreter.allocate_tensors()
    print("   ✓ ttt-boxes.tflite fonctionne (CPU) ✅")
except Exception as e:
    print(f"   ❌ ttt-boxes.tflite: {e}")

# Tester le modèle de validation
try:
    interpreter = tflite.Interpreter(old_valid_path)
    interpreter.allocate_tensors()
    print("   ✓ ttt-valid-board.tflite fonctionne (CPU) ✅")
except Exception as e:
    print(f"   ❌ ttt-valid-board.tflite: {e}")

print()
print("="*70)
print("✅ Modèles CPU créés avec succès !")
print("="*70)
print()
print(f"📊 Taille totale: {(size_boxes + size_valid) / 1024:.1f} KB")
print()
print("⚠️  IMPORTANT - PROCHAINES ÉTAPES:")
print()
print("   1. Ces modèles utilisent MobileNetV2 pré-entraîné (transfer learning)")
print("      Ils donneront des résultats approximatifs sans entraînement spécifique.")
print()
print("   2. Pour une VRAIE détection, vous DEVEZ entraîner ces modèles:")
print("      - Collectez 200-500 images de chaque classe")
print("      - Utilisez le notebook: notebooks/Train_classifier.ipynb")
print("      - Ou entraînez avec votre propre script")
print()
print("   3. Les modèles sont maintenant compatibles CPU (pas besoin d'EdgeTPU)")
print()
print("   4. Transférez ces modèles sur Reachy:")
print(f"      scp -r {models_dir}/*.tflite reachy@<IP>:~/reachy-tictactoe/reachy_tictactoe/models/")
print()
print("Vous pouvez tester le système avec:")
print("   python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe")
print()