#!/usr/bin/env python3
"""
Script d'entraînement des modèles TicTacToe

Ce script entraîne les deux modèles nécessaires:
1. ttt-boxes: Classification des cases (empty/cube/cylinder)
2. ttt-valid-board: Validation du plateau (valid/invalid)

Usage:
    python scripts/train_models.py --model boxes
    python scripts/train_models.py --model valid-board
    python scripts/train_models.py --model all
"""

import argparse
import os
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime


def check_data_availability(data_dir, class_names):
    """Vérifie que les données sont disponibles"""
    print(f"\n📊 Vérification des données dans {data_dir}")
    print("="*70)
    
    all_ok = True
    for class_name in class_names:
        class_dir = os.path.join(data_dir, class_name)
        if not os.path.exists(class_dir):
            print(f"❌ {class_name}: dossier manquant")
            all_ok = False
            continue
        
        count = len([f for f in os.listdir(class_dir) if f.endswith('.jpg')])
        status = "✅" if count >= 100 else "⚠️" if count >= 50 else "❌"
        print(f"{status} {class_name:15s}: {count:4d} images")
        
        if count < 50:
            all_ok = False
    
    print("="*70)
    return all_ok


def create_model(num_classes, img_size=224):
    """
    Crée un modèle avec Transfer Learning (MobileNetV2)
    
    Args:
        num_classes: Nombre de classes à prédire
        img_size: Taille des images d'entrée
    
    Returns:
        Modèle Keras compilé
    """
    # Modèle de base pré-entraîné
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(img_size, img_size, 3),
        include_top=False,
        weights='imagenet'
    )
    
    # Geler les couches du modèle de base
    base_model.trainable = False
    
    # Construire le modèle complet
    model = keras.Sequential([
        base_model,
        layers.GlobalAveragePooling2D(),
        layers.Dense(128, activation='relu'),
        layers.Dropout(0.5),
        layers.Dense(num_classes, activation='softmax')
    ])
    
    # Compiler
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    return model


def plot_training_history(history, save_path):
    """Affiche et sauvegarde les courbes d'entraînement"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    
    # Accuracy
    ax1.plot(history.history['accuracy'], label='Train')
    ax1.plot(history.history['val_accuracy'], label='Validation')
    ax1.set_title('Précision du modèle')
    ax1.set_ylabel('Précision')
    ax1.set_xlabel('Époque')
    ax1.legend()
    ax1.grid(True)
    
    # Loss
    ax2.plot(history.history['loss'], label='Train')
    ax2.plot(history.history['val_loss'], label='Validation')
    ax2.set_title('Perte du modèle')
    ax2.set_ylabel('Perte')
    ax2.set_xlabel('Époque')
    ax2.legend()
    ax2.grid(True)
    
    plt.tight_layout()
    plt.savefig(save_path)
    print(f"📊 Courbes d'entraînement sauvegardées: {save_path}")


def train_boxes_model(data_dir='training_data/boxes', 
                      output_dir='models',
                      img_size=224,
                      batch_size=32,
                      epochs=15):
    """Entraîne le modèle de détection des cases"""
    print("\n" + "="*70)
    print("🚀 ENTRAÎNEMENT DU MODÈLE TTT-BOXES")
    print("="*70)
    
    class_names = ['cube', 'cylinder', 'empty']
    
    # Vérifier les données
    if not check_data_availability(data_dir, class_names):
        print("\n❌ Données insuffisantes pour l'entraînement!")
        print("Collectez plus d'images avec scripts/collect_boxes_images.py")
        return False
    
    # Préparer les générateurs de données
    print("\n📂 Chargement des données...")
    train_datagen = tf.keras.preprocessing.image.ImageDataGenerator(
        rescale=1./255,
        rotation_range=20,
        width_shift_range=0.2,
        height_shift_range=0.2,
        horizontal_flip=True,
        fill_mode='nearest',
        validation_split=0.2
    )
    
    train_generator = train_datagen.flow_from_directory(
        data_dir,
        target_size=(img_size, img_size),
        batch_size=batch_size,
        class_mode='categorical',
        subset='training',
        shuffle=True
    )
    
    val_generator = train_datagen.flow_from_directory(
        data_dir,
        target_size=(img_size, img_size),
        batch_size=batch_size,
        class_mode='categorical',
        subset='validation',
        shuffle=False
    )
    
    print(f"✅ Données d'entraînement: {train_generator.samples} images")
    print(f"✅ Données de validation: {val_generator.samples} images")
    print(f"✅ Classes détectées: {train_generator.class_indices}")
    
    # Créer le modèle
    print("\n🏗️ Construction du modèle...")
    model = create_model(num_classes=3, img_size=img_size)
    model.summary()
    
    # Callbacks
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_accuracy',
            patience=5,
            restore_best_weights=True
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=3,
            min_lr=0.00001
        )
    ]
    
    # Entraînement
    print(f"\n🎓 Entraînement ({epochs} époques max)...")
    print("Cela peut prendre 30-60 minutes selon votre machine...")
    
    history = model.fit(
        train_generator,
        validation_data=val_generator,
        epochs=epochs,
        callbacks=callbacks,
        verbose=1
    )
    
    # Évaluation finale
    print("\n📈 Évaluation finale...")
    val_loss, val_acc = model.evaluate(val_generator)
    print(f"Perte de validation: {val_loss:.4f}")
    print(f"Précision de validation: {val_acc:.4f} ({val_acc*100:.2f}%)")
    
    # Sauvegarder
    os.makedirs(output_dir, exist_ok=True)
    model_path = os.path.join(output_dir, 'ttt-boxes.h5')
    model.save(model_path)
    print(f"\n✅ Modèle sauvegardé: {model_path}")
    
    # Sauvegarder les courbes
    plot_path = os.path.join(output_dir, 'ttt-boxes_training.png')
    plot_training_history(history, plot_path)
    
    # Sauvegarder le fichier de labels
    labels_path = os.path.join(output_dir, 'ttt-boxes_labels.txt')
    with open(labels_path, 'w') as f:
        for idx, label in enumerate(class_names):
            f.write(f"{idx} {label}\n")
    print(f"✅ Labels sauvegardés: {labels_path}")
    
    # Recommandation
    if val_acc >= 0.90:
        print("\n🎉 Excellent ! Précision >= 90%")
    elif val_acc >= 0.80:
        print("\n⚠️ Précision correcte mais peut être améliorée")
        print("Collectez plus d'images variées pour améliorer")
    else:
        print("\n❌ Précision insuffisante (<80%)")
        print("Collectez beaucoup plus d'images variées")
    
    return True


def train_valid_board_model(data_dir='training_data/valid_board',
                            output_dir='models',
                            img_size=224,
                            batch_size=32,
                            epochs=15):
    """Entraîne le modèle de validation du plateau"""
    print("\n" + "="*70)
    print("🚀 ENTRAÎNEMENT DU MODÈLE TTT-VALID-BOARD")
    print("="*70)
    
    class_names = ['invalid', 'valid']
    
    # Vérifier les données
    if not check_data_availability(data_dir, class_names):
        print("\n❌ Données insuffisantes pour l'entraînement!")
        print("Collectez plus d'images avec scripts/collect_valid_board_images.py")
        return False
    
    # Préparer les générateurs de données
    print("\n📂 Chargement des données...")
    train_datagen = tf.keras.preprocessing.image.ImageDataGenerator(
        rescale=1./255,
        rotation_range=10,
        width_shift_range=0.1,
        height_shift_range=0.1,
        zoom_range=0.1,
        fill_mode='nearest',
        validation_split=0.2
    )
    
    train_generator = train_datagen.flow_from_directory(
        data_dir,
        target_size=(img_size, img_size),
        batch_size=batch_size,
        class_mode='categorical',
        subset='training',
        shuffle=True
    )
    
    val_generator = train_datagen.flow_from_directory(
        data_dir,
        target_size=(img_size, img_size),
        batch_size=batch_size,
        class_mode='categorical',
        subset='validation',
        shuffle=False
    )
    
    print(f"✅ Données d'entraînement: {train_generator.samples} images")
    print(f"✅ Données de validation: {val_generator.samples} images")
    print(f"✅ Classes détectées: {train_generator.class_indices}")
    
    # Créer le modèle
    print("\n🏗️ Construction du modèle...")
    model = create_model(num_classes=2, img_size=img_size)
    model.summary()
    
    # Callbacks
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_accuracy',
            patience=5,
            restore_best_weights=True
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=3,
            min_lr=0.00001
        )
    ]
    
    # Entraînement
    print(f"\n🎓 Entraînement ({epochs} époques max)...")
    print("Cela peut prendre 20-40 minutes selon votre machine...")
    
    history = model.fit(
        train_generator,
        validation_data=val_generator,
        epochs=epochs,
        callbacks=callbacks,
        verbose=1
    )
    
    # Évaluation finale
    print("\n📈 Évaluation finale...")
    val_loss, val_acc = model.evaluate(val_generator)
    print(f"Perte de validation: {val_loss:.4f}")
    print(f"Précision de validation: {val_acc:.4f} ({val_acc*100:.2f}%)")
    
    # Sauvegarder
    os.makedirs(output_dir, exist_ok=True)
    model_path = os.path.join(output_dir, 'ttt-valid-board.h5')
    model.save(model_path)
    print(f"\n✅ Modèle sauvegardé: {model_path}")
    
    # Sauvegarder les courbes
    plot_path = os.path.join(output_dir, 'ttt-valid-board_training.png')
    plot_training_history(history, plot_path)
    
    # Sauvegarder le fichier de labels
    labels_path = os.path.join(output_dir, 'ttt-valid-board_labels.txt')
    with open(labels_path, 'w') as f:
        for idx, label in enumerate(class_names):
            f.write(f"{idx} {label}\n")
    print(f"✅ Labels sauvegardés: {labels_path}")
    
    # Recommandation
    if val_acc >= 0.95:
        print("\n🎉 Excellent ! Précision >= 95%")
    elif val_acc >= 0.85:
        print("\n⚠️ Précision correcte mais peut être améliorée")
        print("Collectez plus d'images variées pour améliorer")
    else:
        print("\n❌ Précision insuffisante (<85%)")
        print("Collectez beaucoup plus d'images variées")
    
    return True


def main():
    parser = argparse.ArgumentParser(description='Entraîner les modèles TicTacToe')
    parser.add_argument('--model', 
                       choices=['boxes', 'valid-board', 'all'],
                       required=True,
                       help='Modèle à entraîner')
    parser.add_argument('--epochs', type=int, default=15,
                       help='Nombre d\'époques (défaut: 15)')
    parser.add_argument('--batch-size', type=int, default=32,
                       help='Taille des batchs (défaut: 32)')
    parser.add_argument('--img-size', type=int, default=224,
                       help='Taille des images (défaut: 224)')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🤖 ENTRAÎNEMENT DES MODÈLES TICTACTOE")
    print("="*70)
    print(f"Modèle(s): {args.model}")
    print(f"Époques: {args.epochs}")
    print(f"Batch size: {args.batch_size}")
    print(f"Taille images: {args.img_size}x{args.img_size}")
    print(f"Heure de début: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Vérifier que TensorFlow est disponible
    print(f"\n✅ TensorFlow version: {tf.__version__}")
    print(f"✅ GPU disponible: {len(tf.config.list_physical_devices('GPU')) > 0}")
    
    success = True
    
    # Entraîner selon le choix
    if args.model in ['boxes', 'all']:
        success = train_boxes_model(
            epochs=args.epochs,
            batch_size=args.batch_size,
            img_size=args.img_size
        ) and success
        print("\n" + "="*70 + "\n")
    
    if args.model in ['valid-board', 'all']:
        success = train_valid_board_model(
            epochs=args.epochs,
            batch_size=args.batch_size,
            img_size=args.img_size
        ) and success
        print("\n" + "="*70 + "\n")
    
    # Résumé final
    print("\n" + "="*70)
    print("📋 RÉSUMÉ")
    print("="*70)
    print(f"Heure de fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if success:
        print("\n✅ Entraînement terminé avec succès!")
        print("\n➡️ Prochaine étape:")
        print("   python scripts/convert_to_tflite.py")
    else:
        print("\n❌ Entraînement échoué ou incomplet")
        print("Vérifiez les messages d'erreur ci-dessus")


if __name__ == '__main__':
    main()

