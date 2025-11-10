# 🛠️ Scripts utilitaires TicTacToe

Ce dossier contient les scripts pour configurer, calibrer et enregistrer les mouvements du système TicTacToe, organisés par catégorie.

---

## 📁 Structure des dossiers

```
scripts/
├── moves/          # Scripts pour enregistrer et tester les mouvements du robot
├── calibration/    # Scripts pour calibrer le plateau de jeu
├── training/       # Scripts pour l'entraînement des modèles de vision
└── utils/          # Scripts utilitaires divers
```

---

## 🎬 Mouvements (`moves/`)

### `record_moves.py` 🎬 **Enregistrer les mouvements du robot**

**But :** Enregistrer les positions et trajectoires du bras en mode compliant

**Usage :**
```bash
# Mode interactif (RECOMMANDÉ)
python scripts/moves/record_moves.py --interactive --host localhost

# Enregistrer une position simple
python scripts/moves/record_moves.py --name grab_1 --type position --host localhost

# Enregistrer une trajectoire
python scripts/moves/record_moves.py --name put_1 --type trajectory --duration 2.5 --host localhost
```

**Ce qu'il fait :**
- ✅ Active le mode compliant sur le bras droit
- ✅ Enregistre les positions des joints en temps réel
- ✅ Sauvegarde au format .npz
- ✅ Supporte positions simples et trajectoires

---

### `test_recorded_moves.py` 🧪 **Tester les mouvements enregistrés**

**But :** Valider que les mouvements enregistrés fonctionnent correctement

**Usage :**
```bash
# Mode interactif (RECOMMANDÉ)
python scripts/moves/test_recorded_moves.py --interactive --host localhost

# Tester un mouvement spécifique
python scripts/moves/test_recorded_moves.py --name grab_1 --host localhost

# Tester tous les mouvements
python scripts/moves/test_recorded_moves.py --all --host localhost
```

**Ce qu'il fait :**
- ✅ Charge les fichiers .npz
- ✅ Rejoue les mouvements sur le robot
- ✅ Affiche la progression
- ✅ Valide la compatibilité

---

### `test_positions.py` 📍 **Tester les positions**

**But :** Tester et valider les positions du robot

**Usage :**
```bash
python scripts/moves/test_positions.py --host localhost
```

---

## 🎯 Calibration (`calibration/`)

### `calibrate_board.py` 🎯 **Calibrer le plateau de jeu**

**But :** Déterminer les coordonnées précises de chaque case du plateau

**Usage :**
```bash
# Sur Reachy
python scripts/calibration/calibrate_board.py --host localhost

# Ou en test avec une image existante (sur PC)
python scripts/calibration/calibrate_board.py --image /path/to/board_image.jpg
```

**Ce qu'il fait :**
1. Capture une image depuis la caméra de Reachy
2. Affiche une interface graphique
3. Vous permet de tracer des rectangles autour de chaque case
4. Génère le code Python pour `vision.py`
5. Sauvegarde les coordonnées dans `/tmp/board_calibration.py`

**Interface interactive :**
- 🖱️ Cliquez et glissez pour tracer un rectangle
- ⌨️ 's' = sauvegarder
- ⌨️ 'r' = recommencer
- ⌨️ 'q' = quitter

**Ordre des cases :**
```
(0,0) -> (0,1) -> (0,2)
(1,0) -> (1,1) -> (1,2)
(2,0) -> (2,1) -> (2,2)
```

---

### `check_calibrate_board.py` ✅ **Vérifier la calibration du plateau**

**But :** Vérifier que la calibration du plateau est correcte

**Usage :**
```bash
python scripts/calibration/check_calibrate_board.py --host localhost
```

---

### `check_calibrate_cases.py` ✅ **Vérifier la calibration des cases**

**But :** Vérifier que la calibration des cases individuelles est correcte

**Usage :**
```bash
python scripts/calibration/check_calibrate_cases.py --host localhost
```

---

## 🧠 Entraînement (`training/`)

### `collect_boxes_images.py` 📸 **Collecter des images des cases**

**But :** Collecter des images pour entraîner le modèle de détection des cases

**Usage :**
```bash
# Collecter des images de cases vides
python scripts/training/collect_boxes_images.py --host localhost --class empty --target 50

# Collecter des images de cubes
python scripts/training/collect_boxes_images.py --host localhost --class cube --target 50

# Collecter des images de cylindres
python scripts/training/collect_boxes_images.py --host localhost --class cylinder --target 50
```

---

### `collect_valid_board_images.py` 📸 **Collecter des images de plateau valide/invalide**

**But :** Collecter des images pour entraîner le modèle de validation du plateau

**Usage :**
```bash
# Collecter des images de plateaux valides
python scripts/training/collect_valid_board_images.py --host localhost --class valid --target 150

# Collecter des images de plateaux invalides
python scripts/training/collect_valid_board_images.py --host localhost --class invalid --target 150
```

---

### `train_models.py` 🎓 **Entraîner les modèles**

**But :** Entraîner les modèles de vision (détection des cases et validation du plateau)

**Usage :**
```bash
# Entraîner tous les modèles
python scripts/training/train_models.py --model all --epochs 15

# Entraîner uniquement le modèle de détection des cases
python scripts/training/train_models.py --model boxes --epochs 15

# Entraîner uniquement le modèle de validation du plateau
python scripts/training/train_models.py --model valid-board --epochs 15
```

---

### `convert_to_tflite.py` 🔄 **Convertir en TensorFlow Lite**

**But :** Convertir les modèles entraînés au format TensorFlow Lite pour l'inférence

**Usage :**
```bash
python scripts/training/convert_to_tflite.py
```

---

### `check_training_data.py` ✅ **Vérifier les données d'entraînement**

**But :** Vérifier la qualité et la quantité des données d'entraînement

**Usage :**
```bash
python scripts/training/check_training_data.py
```

---

## 🔧 Utilitaires (`utils/`)

### `show_config.py` ⚙️ **Afficher/modifier la configuration**

**But :** Afficher et modifier la configuration du système

**Usage :**
```bash
# Afficher la configuration actuelle
python scripts/utils/show_config.py

# Modifier les coordonnées du plateau
python scripts/utils/show_config.py --set-board 114 379 331 581

# Réinitialiser la configuration
python scripts/utils/show_config.py --reset
```

---

## 📝 Notes

- Tous les scripts nécessitent une connexion au robot Reachy (sauf ceux qui fonctionnent avec des images locales)
- Utilisez `--host localhost` si vous êtes directement sur Reachy
- Utilisez `--host <IP>` si vous êtes sur une machine distante
- Les scripts de calibration et de collecte d'images nécessitent une caméra fonctionnelle
