# 📚 Guide complet : Créer vos propres modèles TicTacToe

Ce guide vous accompagne pas à pas dans la création de vos propres modèles de vision pour le jeu TicTacToe de Reachy.

## 📊 Vue d'ensemble

Vous allez créer **2 modèles** :
1. **ttt-boxes.tflite** : Classifie chaque case (vide / cube / cylindre)
2. **ttt-valid-board.tflite** : Valide si le plateau est correctement positionné

---

## ✅ Prérequis

### Matériel
- ✅ Robot Reachy V1 avec caméra
- ✅ Plateau de TicTacToe
- ✅ 5 cubes (pièces Reachy)
- ✅ 5 cylindres (pièces joueur)
- ✅ Éclairage stable

### Logiciels
- ✅ Python 3.8+
- ✅ Environnement virtuel activé

---

## 📋 ÉTAPE 1 : Installation des dépendances (30 min)

### 1.1 Activer l'environnement virtuel

```bash
cd /home/mia/Bureau/reachy-2019-tictactoe
source venv/bin/activate
```

### 1.2 Installer TensorFlow et dépendances

```bash
# TensorFlow pour l'entraînement
pip install tensorflow>=2.10.0

# Vérification
python -c "import tensorflow as tf; print(f'TensorFlow {tf.__version__} installé')"
```

**✅ Checkpoint** : La commande doit afficher la version de TensorFlow sans erreur.

---

## 📋 ÉTAPE 2 : Calibration du plateau (15-30 min)

Cette étape détermine les coordonnées exactes des 9 cases dans l'image.

### 2.1 Lancer la calibration

```bash
python scripts/calibrate_board.py --host localhost
```

### 2.2 Suivre les instructions

1. Reachy regarde le plateau
2. Une fenêtre s'ouvre avec l'image
3. **Tracez 9 rectangles** (un par case) dans cet ordre :

```
Case 1 (0,0) → Case 2 (0,1) → Case 3 (0,2)
  ↓              ↓              ↓
Case 4 (1,0) → Case 5 (1,1) → Case 6 (1,2)
  ↓              ↓              ↓
Case 7 (2,0) → Case 8 (2,1) → Case 9 (2,2)
```

4. Cliquer-glisser pour chaque rectangle
5. Appuyer sur **'s'** pour sauvegarder
6. Les coordonnées sont dans `/tmp/board_calibration.py`

---

## 📋 ÉTAPE 3 : Collecte des images (2-3 heures)

**C'est l'étape la plus longue** mais elle peut être faite en plusieurs sessions.

### 3.1 Collecter les cases VIDES (~30 min)

```bash
python scripts/collect_boxes_images.py --host localhost --class empty --target 50
```

**Instructions** :
- Enlevez TOUTES les pièces du plateau
- Appuyez sur Entrée pour chaque capture
- Déplacez légèrement le plateau ou changez l'éclairage entre les captures
- 50 captures = 450 images (9 cases par photo)

### 3.2 Collecter les cases avec CUBES (~45 min)

```bash
python scripts/collect_boxes_images.py --host localhost --class cube --target 50
```

**Instructions** :
- Placez des cubes sur le plateau
- Indiquez quelles cases contiennent des cubes (ex: `0,4,8`)
- Variez les configurations entre les captures

**Exemples de configurations** :
- `4` : cube au centre uniquement
- `0,2,6,8` : cubes aux coins
- `1,3,5,7` : cubes sur les bords
- `0,1,2` : ligne du haut
- etc.

### 3.3 Collecter les cases avec CYLINDRES (~45 min)

```bash
python scripts/collect_boxes_images.py --host localhost --class cylinder --target 50
```

Même principe que pour les cubes.

### 3.4 Collecter les plateaux VALIDES (~30 min)

```bash
python scripts/collect_valid_board_images.py --host localhost --class valid --target 150
```

**Instructions** :
- Plateau bien centré et visible
- Appuyez sur Entrée entre chaque capture
- Variez légèrement la position

### 3.5 Collecter les plateaux INVALIDES (~30 min)

```bash
python scripts/collect_valid_board_images.py --host localhost --class invalid --target 150
```

**Instructions** : Créez des situations invalides :
- Plateau décentré ou tourné
- Plateau partiellement caché
- Main devant la caméra
- Plateau absent
- Mauvais éclairage

### 3.6 Vérifier les données collectées

```bash
python scripts/check_training_data.py
```

**✅ Checkpoint** : Le script doit afficher "Prêt pour l'entraînement" pour les deux modèles.

---

## 📋 ÉTAPE 4 : Nettoyage des données (30 min)

Parcourez vos images et supprimez :
- Images floues
- Images avec votre main visible
- Images trop sombres/claires
- Doublons évidents

```bash
# Visualiser rapidement (Linux)
eog training_data/boxes/empty/*.jpg
eog training_data/boxes/cube/*.jpg
eog training_data/boxes/cylinder/*.jpg
eog training_data/valid_board/valid/*.jpg
eog training_data/valid_board/invalid/*.jpg
```

**💡 Astuce** : Utilisez les flèches pour naviguer, Suppr pour effacer.

---

## 📋 ÉTAPE 5 : Entraînement des modèles (1-2 heures)

### 5.1 Entraîner les deux modèles

```bash
python scripts/train_models.py --model all --epochs 15
```

**Ce qui se passe** :
1. Chargement des images
2. Augmentation des données (rotation, décalages, etc.)
3. Création des modèles avec Transfer Learning (MobileNetV2)
4. Entraînement (30-60 min par modèle)
5. Sauvegarde des modèles H5

**Options** :
- `--model boxes` : Entraîner uniquement ttt-boxes
- `--model valid-board` : Entraîner uniquement ttt-valid-board
- `--epochs 20` : Plus d'époques (plus long mais potentiellement meilleur)
- `--batch-size 16` : Batch plus petit si mémoire insuffisante

### 5.2 Vérifier les résultats

Le script affiche la précision finale. **Objectifs** :
- **ttt-boxes** : Précision ≥ 90%
- **ttt-valid-board** : Précision ≥ 95%

Des courbes d'entraînement sont sauvegardées dans `models/`:
- `ttt-boxes_training.png`
- `ttt-valid-board_training.png`

**✅ Checkpoint** : Précision satisfaisante (≥90% pour boxes, ≥95% pour valid-board).

---

## 📋 ÉTAPE 6 : Conversion en TFLite (10 min)

Convertir les modèles H5 en TFLite pour Reachy :

```bash
python scripts/convert_to_tflite.py --model all
```

**Ce qui se passe** :
1. Backup des anciens modèles
2. Conversion H5 → TFLite
3. Optimisations (quantification, compression)
4. Test de chargement
5. Copie des fichiers de labels

Les nouveaux modèles sont dans `reachy_tictactoe/models/` :
- `ttt-boxes.tflite`
- `ttt-boxes.txt`
- `ttt-valid-board.tflite`
- `ttt-valid-board.txt`

**✅ Checkpoint** : Les 4 fichiers sont créés sans erreur.

---

## 📋 ÉTAPE 7 : Test en conditions réelles (30 min)

### 7.1 Lancer le jeu

```bash
python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe_test
```

### 7.2 Observer les logs

Dans un autre terminal :

```bash
tail -f /tmp/tictactoe_test.log
```

---

## 📚 Référence rapide des commandes

### Collecte
```bash
# Cases vides
python scripts/collect_boxes_images.py --host localhost --class empty --target 50

# Cubes
python scripts/collect_boxes_images.py --host localhost --class cube --target 50

# Cylindres
python scripts/collect_boxes_images.py --host localhost --class cylinder --target 50

# Plateaux valides
python scripts/collect_valid_board_images.py --host localhost --class valid --target 150

# Plateaux invalides
python scripts/collect_valid_board_images.py --host localhost --class invalid --target 150

# Vérifier
python scripts/check_training_data.py
```

### Entraînement
```bash
# Tout entraîner
python scripts/train_models.py --model all --epochs 15

# Uniquement boxes
python scripts/train_models.py --model boxes --epochs 15

# Uniquement valid-board
python scripts/train_models.py --model valid-board --epochs 15
```

### Conversion
```bash
# Tout convertir
python scripts/convert_to_tflite.py --model all

# Uniquement boxes
python scripts/convert_to_tflite.py --model boxes
```

### Test
```bash
# Lancer le jeu
python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe_test

# Voir les logs
tail -f /tmp/tictactoe_test.log
```