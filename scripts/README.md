# 🛠️ Scripts utilitaires TicTacToe

Ce dossier contient les scripts pour configurer et calibrer le système TicTacToe.

---

## 📝 Liste des scripts

### 1. `convert_models_for_cpu.py` ⭐ **À exécuter en premier**

**But :** Convertir les modèles EdgeTPU en modèles compatibles CPU

**Usage :**
```bash
# Sur votre PC de développement (PAS sur Reachy)
python scripts/convert_models_for_cpu.py
```

**Ce qu'il fait :**
- ✅ Crée de nouveaux modèles TFLite basés sur MobileNetV2
- ✅ Sauvegarde les anciens modèles EdgeTPU en backup
- ✅ Teste la compatibilité CPU
- ✅ Utilise le transfer learning (pré-entraîné sur ImageNet)

**Résultat :**
- `reachy_tictactoe/models/ttt-boxes.tflite` (nouveau, ~9 MB)
- `reachy_tictactoe/models/ttt-valid-board.tflite` (nouveau, ~9 MB)

**⚠️ Important :** Ces modèles doivent être entraînés avec vos propres données pour une détection précise. Le script crée l'architecture de base avec transfer learning.

---

### 2. `calibrate_board.py` 🎯 **À exécuter sur Reachy**

**But :** Déterminer les coordonnées précises de chaque case du plateau

**Usage :**
```bash
# Sur Reachy
python scripts/calibrate_board.py --host localhost

# Ou en test avec une image existante (sur PC)
python scripts/calibrate_board.py --image /path/to/board_image.jpg
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

### 3. `create_fallback_models.py` 🔧 **Obsolète - Utilisez convert_models_for_cpu.py**

**But :** Créer des modèles de remplacement simples (placeholders)

**⚠️ Attention :** Ce script crée des modèles qui ne détectent PAS vraiment les pièces. Il est uniquement pour tester que le système fonctionne sans EdgeTPU.

**Usage :**
```bash
python scripts/create_fallback_models.py
```

**Quand l'utiliser :**
- Seulement si `convert_models_for_cpu.py` ne fonctionne pas
- Pour des tests rapides du système (sans détection réelle)

---

## 🚀 Flux de travail recommandé

### Préparation (sur PC de dev)

```bash
cd /home/mia/Bureau/reachy-2019-tictactoe

# 1. Convertir les modèles
python scripts/convert_models_for_cpu.py

# 2. Vérifier la création des modèles
ls -lh reachy_tictactoe/models/*.tflite
```

### Transfert vers Reachy

```bash
# 3. Transférer le projet complet
scp -r reachy-2019-tictactoe reachy@<IP_REACHY>:~/

# Ou seulement les fichiers nécessaires
scp -r reachy_tictactoe reachy@<IP>:~/reachy-2019-tictactoe/
scp -r scripts reachy@<IP>:~/reachy-2019-tictactoe/
```

### Configuration (sur Reachy)

```bash
# 4. Se connecter à Reachy
ssh reachy@<IP_REACHY>

# 5. Installer le projet
cd ~/reachy-2019-tictactoe
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .

# 6. Calibrer les coordonnées
python scripts/calibrate_board.py --host localhost

# 7. Mettre à jour vision.py avec les coordonnées
nano reachy_tictactoe/vision.py
# Copier-coller les coordonnées générées

# 8. Tester le système
python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe
```

---

## 📋 Checklist de déploiement

- [ ] ✅ Modèles convertis pour CPU (`convert_models_for_cpu.py`)
- [ ] ✅ Projet transféré sur Reachy
- [ ] ✅ Environnement virtuel créé et activé
- [ ] ✅ Dépendances installées
- [ ] ✅ Coordonnées calibrées (`calibrate_board.py`)
- [ ] ✅ `vision.py` mis à jour avec les nouvelles coordonnées
- [ ] ✅ Test de vision réussi
- [ ] ✅ Premier jeu lancé

---

## 🐛 Dépannage des scripts

### Erreur : "No module named 'tensorflow'"

```bash
# Sur PC
pip install tensorflow

# Sur Reachy (dans venv)
source venv/bin/activate
pip install tensorflow
```

### Erreur : "No module named 'reachy_sdk'"

```bash
# Sur Reachy
source venv/bin/activate
pip install reachy-sdk
```

### Erreur : "cv2.error" lors de la calibration

```bash
# Installer OpenCV
pip install opencv-python
```

### Calibration : La fenêtre ne s'affiche pas

**Sur Reachy en SSH :**
```bash
# Activer le forwarding X11
ssh -X reachy@<IP>
python scripts/calibrate_board.py --host localhost
```

**Alternative :** Utiliser une image de test
```bash
# Capturer une image manuellement
python -c "
from reachy_sdk import ReachySDK
import cv2, time

r = ReachySDK('localhost')
r.turn_on('head')
r.head.look_at(x=0.5, y=0, z=-0.6, duration=1.0)
time.sleep(1.5)

img = r.right_camera.last_frame
cv2.imwrite('/tmp/board_test.jpg', img)
print('Image sauvegardée: /tmp/board_test.jpg')
"

# Transférer l'image sur votre PC
scp reachy@<IP>:/tmp/board_test.jpg .

# Calibrer localement
python scripts/calibrate_board.py --image board_test.jpg
```

---

## 📚 Ressources

- **Guide complet de déploiement :** `../GUIDE_DEPLOYMENT.md`
- **Conversion EdgeTPU :** `../EDGE_TPU_CONVERSION.md`
- **Démarrage rapide :** `../QUICK_START.md`
- **README principal :** `../README.md`

---

## ❓ Questions fréquentes

### Q: Dois-je exécuter ces scripts à chaque fois ?

**R:** Non, seulement lors de la configuration initiale :
- `convert_models_for_cpu.py` : Une seule fois (ou si vous changez de modèles)
- `calibrate_board.py` : Une seule fois (ou si vous déplacez le plateau/caméra)

### Q: Puis-je améliorer la précision des modèles ?

**R:** Oui ! Entraînez-les avec vos propres données :
1. Collectez des images avec `notebooks/Collect_training_images.ipynb`
2. Entraînez avec `notebooks/Train_classifier.ipynb`
3. Remplacez les modèles dans `reachy_tictactoe/models/`

### Q: Les modèles CPU sont-ils assez rapides ?

**R:** Oui, largement suffisant pour le jeu de morpion :
- CPU i5/i7 : ~30-100ms par inférence
- EdgeTPU : ~5-10ms
- Pour un jeu au tour par tour, aucune différence perceptible

### Q: Puis-je utiliser ces scripts pour d'autres projets ?

**R:** Oui ! Ils sont conçus pour être réutilisables :
- `convert_models_for_cpu.py` : Adaptez pour vos propres modèles
- `calibrate_board.py` : Modifiez pour d'autres types de grilles/zones

---

## 🤝 Contributions

Améliorations bienvenues :
- Ajout de tests automatiques
- Support pour d'autres architectures (EfficientNet, etc.)
- Interface de calibration améliorée
- Script de validation automatique

---

**Besoin d'aide ?** Consultez `../GUIDE_DEPLOYMENT.md` pour le guide complet !

