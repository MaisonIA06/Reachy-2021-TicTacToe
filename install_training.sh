#!/bin/bash
# Script d'installation des dépendances pour l'entraînement des modèles

set -e  # Arrêter en cas d'erreur

echo "=============================================================="
echo "🤖 Installation des dépendances pour l'entraînement"
echo "=============================================================="
echo ""

# Vérifier que nous sommes dans le bon dossier
if [ ! -f "requirements-training.txt" ]; then
    echo "❌ Erreur: Exécutez ce script depuis le dossier reachy-2019-tictactoe"
    exit 1
fi

# Vérifier que l'environnement virtuel existe
if [ ! -d "venv" ]; then
    echo "❌ Erreur: L'environnement virtuel n'existe pas"
    echo "Créez-le d'abord avec: python3 -m venv venv"
    exit 1
fi

# Activer l'environnement virtuel
echo "🔧 Activation de l'environnement virtuel..."
source venv/bin/activate

# Mettre à jour pip
echo ""
echo "⬆️ Mise à jour de pip..."
pip install --upgrade pip

# Installer les dépendances
echo ""
echo "📦 Installation des dépendances..."
pip install -r requirements-training.txt

# Vérifier l'installation de TensorFlow
echo ""
echo "🧪 Vérification de l'installation..."
python3 << EOF
import sys
try:
    import tensorflow as tf
    print(f"✅ TensorFlow {tf.__version__} installé avec succès")
    
    import numpy as np
    print(f"✅ NumPy {np.__version__} installé")
    
    import cv2
    print(f"✅ OpenCV {cv2.__version__} installé")
    
    import PIL
    print(f"✅ Pillow {PIL.__version__} installé")
    
    try:
        import jupyter
        print(f"✅ Jupyter installé")
    except:
        print("⚠️ Jupyter non installé (optionnel)")
    
    # Vérifier GPU
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        print(f"✅ {len(gpus)} GPU(s) détecté(s)")
    else:
        print("ℹ️ Pas de GPU détecté (utilisation du CPU)")
    
    print("")
    print("🎉 Installation terminée avec succès!")
    
except ImportError as e:
    print(f"❌ Erreur d'importation: {e}")
    sys.exit(1)
EOF

# Créer la structure de dossiers
echo ""
echo "📁 Création de la structure de dossiers..."
mkdir -p training_data/boxes/{empty,cube,cylinder}
mkdir -p training_data/valid_board/{valid,invalid}
mkdir -p training_data/board_images
mkdir -p models

echo "✅ Dossiers créés:"
echo "   - training_data/boxes/{empty,cube,cylinder}"
echo "   - training_data/valid_board/{valid,invalid}"
echo "   - models/"

# Afficher les prochaines étapes
echo ""
echo "=============================================================="
echo "✅ INSTALLATION TERMINÉE"
echo "=============================================================="
echo ""
echo "➡️ Prochaines étapes:"
echo ""
echo "1. Calibrer le plateau:"
echo "   python scripts/calibrate_board.py --host localhost"
echo ""
echo "2. Collecter les images (voir GUIDE_CREATION_MODELES.md)"
echo ""
echo "3. Vérifier les données:"
echo "   python scripts/check_training_data.py"
echo ""
echo "4. Entraîner les modèles:"
echo "   python scripts/train_models.py --model all"
echo ""
echo "5. Convertir en TFLite:"
echo "   python scripts/convert_to_tflite.py --model all"
echo ""
echo "📚 Consultez GUIDE_CREATION_MODELES.md pour le guide complet"
echo "=============================================================="

