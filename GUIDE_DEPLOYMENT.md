# 🚀 Guide de Déploiement sur Reachy

Ce guide vous explique comment transférer et configurer le projet TicTacToe sur votre robot Reachy.

---

## 📋 Prérequis

### Sur votre PC de développement
- ✅ Python 3.8+
- ✅ Accès réseau à Reachy
- ✅ Clé SSH configurée (recommandé)

### Sur Reachy
- ✅ Reachy V1 avec SDK 2021
- ✅ Ubuntu 20.04+ 
- ✅ Connexion réseau
- ✅ Caméra droite fonctionnelle

---

## 🔧 ÉTAPE 1 : Préparation sur votre PC

### 1.1 Résoudre le problème EdgeTPU

Les modèles actuels sont compilés pour EdgeTPU. Vous devez les convertir pour CPU :

```bash
cd /home/mia/Bureau/reachy-2019-tictactoe

# Installer TensorFlow (si pas déjà installé)
pip install tensorflow

# Convertir les modèles pour CPU
python scripts/convert_models_for_cpu.py
```

**Résultat attendu :**
```
✅ Modèles CPU créés avec succès !
✓ ttt-boxes.tflite fonctionne (CPU)
✓ ttt-valid-board.tflite fonctionne (CPU)
```

### 1.2 Vérifier les fichiers

```bash
# Vérifier que les modèles sont créés
ls -lh reachy_tictactoe/models/*.tflite

# Vous devriez voir:
# ttt-boxes.tflite              (~9 MB - nouveau, CPU)
# ttt-valid-board.tflite        (~9 MB - nouveau, CPU)
# ttt-boxes-edgetpu-BACKUP.tflite     (ancien, EdgeTPU)
# ttt-valid-board-edgetpu-BACKUP.tflite (ancien, EdgeTPU)
```

---

## 🔄 ÉTAPE 2 : Transfert vers Reachy

### 2.1 Identifier l'adresse IP de Reachy

```bash
# Sur Reachy (via clavier/écran ou SSH)
hostname -I

# Exemple de sortie: 192.168.1.42
```

### 2.2 Configurer l'accès SSH (recommandé)

```bash
# Sur votre PC
# Copier votre clé publique sur Reachy (facilite les transferts)
ssh-copy-id reachy@<IP_REACHY>

# Exemple:
ssh-copy-id reachy@192.168.1.42
```

### 2.3 Transférer le projet complet

```bash
# Sur votre PC
cd /home/mia/Bureau

# Option A: Transférer tout le projet
scp -r reachy-2019-tictactoe reachy@<IP_REACHY>:~/

# Option B: Transférer uniquement les fichiers nécessaires (plus rapide)
ssh reachy@<IP_REACHY> "mkdir -p ~/reachy-2019-tictactoe"

# Transférer les fichiers essentiels
scp -r reachy-2019-tictactoe/reachy_tictactoe reachy@<IP_REACHY>:~/reachy-2019-tictactoe/
scp reachy-2019-tictactoe/requirements.txt reachy@<IP_REACHY>:~/reachy-2019-tictactoe/
scp reachy-2019-tictactoe/setup.py reachy@<IP_REACHY>:~/reachy-2019-tictactoe/
scp -r reachy-2019-tictactoe/scripts reachy@<IP_REACHY>:~/reachy-2019-tictactoe/
```

**Temps de transfert :** ~2-5 minutes selon la connexion

---

## 🎯 ÉTAPE 3 : Installation sur Reachy

### 3.1 Se connecter à Reachy

```bash
# Sur votre PC
ssh reachy@<IP_REACHY>
```

### 3.2 Créer un environnement virtuel

```bash
# Sur Reachy
cd ~/reachy-2019-tictactoe

# Créer l'environnement virtuel
python3 -m venv venv

# Activer l'environnement
source venv/bin/activate

# Votre prompt devrait changer: (venv) reachy@reachy:~/reachy-2019-tictactoe$
```

### 3.3 Installer les dépendances

```bash
# Sur Reachy (avec venv activé)
pip install --upgrade pip

# Installer les dépendances
pip install -r requirements.txt

# Installer le package en mode développement
pip install -e .
```

**⏱️ Durée :** ~5-10 minutes

### 3.4 Vérifier l'installation

```bash
# Vérifier que le package est installé
pip list | grep reachy

# Résultat attendu:
# reachy-tictactoe    2.0.0
# reachy-sdk          x.x.x
```

---

## 📐 ÉTAPE 4 : Calibration des coordonnées

La calibration est **ESSENTIELLE** car les coordonnées des cases dépendent de :
- La position de la caméra
- L'angle de vue
- La taille et position de votre plateau

### 4.1 Préparer le plateau

1. **Placer le plateau** devant Reachy (distance ~50-70 cm)
2. **Bien éclairer** la zone (lumière naturelle ou artificielle uniforme)
3. **Nettoyer le plateau** (pas de pièces posées)

### 4.2 Lancer la calibration

```bash
# Sur Reachy (avec venv activé)
cd ~/reachy-2019-tictactoe

# Lancer le script de calibration
python scripts/calibrate_board.py --host localhost
```

### 4.3 Utiliser l'interface de calibration

Une fenêtre s'ouvre montrant la vue de la caméra :

1. **Cliquez et glissez** pour tracer un rectangle autour de la première case (0,0)
2. **Répétez** pour les 8 autres cases dans l'ordre :
   ```
   (0,0) -> (0,1) -> (0,2)
   (1,0) -> (1,1) -> (1,2)
   (2,0) -> (2,1) -> (2,2)
   ```
3. **Appuyez sur 's'** pour sauvegarder
4. Les coordonnées sont sauvegardées dans `/tmp/board_calibration.py`

### 4.4 Mettre à jour vision.py

```bash
# Sur Reachy
# Copier le code affiché par le script de calibration

# Éditer vision.py
nano ~/reachy-2019-tictactoe/reachy_tictactoe/vision.py

# Trouver la ligne ~165 avec:
# board_cases = np.array((
#     ((209, 316, 253, 346), ...),
#     ...
# ))

# Remplacer par les nouvelles coordonnées
# Sauvegarder: Ctrl+O, Entrée, Ctrl+X
```

**Exemple de coordonnées calibrées :**
```python
board_cases = np.array((
    ((210, 320, 250, 345), (320, 430, 250, 345), (430, 535, 250, 345)),  # Ligne 0
    ((190, 310, 345, 460), (310, 430, 345, 460), (430, 540, 345, 460)),  # Ligne 1
    ((175, 300, 460, 585), (300, 430, 460, 585), (430, 555, 460, 585)),  # Ligne 2
))
```

---

## ✅ ÉTAPE 5 : Test du système

### 5.1 Test rapide de la vision

```bash
# Sur Reachy
cd ~/reachy-2019-tictactoe
source venv/bin/activate

# Tester la détection
python -c "
from reachy_sdk import ReachySDK
from reachy_tictactoe.vision import get_board_configuration, is_board_valid
import time

reachy = ReachySDK(host='localhost')
reachy.turn_on('head')
reachy.head.look_at(x=0.5, y=0, z=-0.6, duration=1.0)
time.sleep(1.5)

img = reachy.right_camera.last_frame
print('Image capturée:', img.shape)

valid = is_board_valid(img)
print('Plateau valide:', valid)

board, _ = get_board_configuration(img)
print('Configuration du plateau:')
print(board)
"
```

**Résultat attendu :**
```
Image capturée: (720, 1280, 3)
Plateau valide: True
Configuration du plateau:
[[0 0 0]
 [0 0 0]
 [0 0 0]]
```

### 5.2 Test du mouvement

```bash
# Test minimal du bras
python -c "
from reachy_sdk import ReachySDK
import time

reachy = ReachySDK(host='localhost')
reachy.turn_on('r_arm')
time.sleep(0.5)

print('✓ Bras activé')
print('Températures:', {j.name: j.temperature for j in reachy.r_arm.joints.values()})

reachy.turn_off_smoothly('r_arm')
print('✓ Test terminé')
"
```

---

## 🎮 ÉTAPE 6 : Lancer le jeu

### 6.1 Premier lancement (mode test)

```bash
# Sur Reachy
cd ~/reachy-2019-tictactoe
source venv/bin/activate

# Lancer avec logs
python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe --host localhost
```

**Le jeu va :**
1. Activer la tête et le bras droit
2. Attendre que le plateau soit vide
3. Faire un tirage au sort (qui commence)
4. Commencer la partie !

### 6.2 Arrêt du jeu

```bash
# Appuyer sur Ctrl+C pour arrêter proprement
# Le robot va désactiver tous les moteurs
```

### 6.3 Consulter les logs

```bash
# Voir les logs en temps réel
tail -f /tmp/tictactoe*.log

# Ou ouvrir le dernier fichier log
ls -lt /tmp/tictactoe*.log | head -1
```

---

## 🔧 ÉTAPE 7 : Configuration en service (optionnel)

Pour que le jeu se lance automatiquement au démarrage de Reachy :

### 7.1 Créer le fichier service

```bash
# Sur Reachy
sudo nano /etc/systemd/system/tictactoe.service
```

**Contenu :**
```ini
[Unit]
Description=TicTacToe Playground Service
Wants=network-online.target
After=network.target network-online.target

[Service]
Type=simple
User=reachy
Group=reachy
WorkingDirectory=/home/reachy/reachy-2019-tictactoe
Environment="PATH=/home/reachy/reachy-2019-tictactoe/venv/bin:$PATH"
ExecStart=/home/reachy/reachy-2019-tictactoe/venv/bin/python -m reachy_tictactoe.game_launcher --log-file /home/reachy/tictactoe_logs/game
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 7.2 Activer le service

```bash
# Créer le dossier de logs
mkdir -p ~/tictactoe_logs

# Recharger systemd
sudo systemctl daemon-reload

# Activer le service (démarrage automatique)
sudo systemctl enable tictactoe.service

# Démarrer le service
sudo systemctl start tictactoe.service

# Vérifier le statut
sudo systemctl status tictactoe.service

# Voir les logs
sudo journalctl -u tictactoe.service -f
```

### 7.3 Commandes utiles

```bash
# Arrêter le service
sudo systemctl stop tictactoe.service

# Redémarrer le service
sudo systemctl restart tictactoe.service

# Désactiver le démarrage automatique
sudo systemctl disable tictactoe.service
```

---

## 🐛 Dépannage

### Problème : "No module named 'reachy_sdk'"

**Solution :**
```bash
source ~/reachy-2019-tictactoe/venv/bin/activate
pip install reachy-sdk
```

### Problème : "RuntimeError: edgetpu-custom-op"

**Solution :** Les modèles ne sont pas convertis pour CPU
```bash
# Sur votre PC (pas sur Reachy)
cd /home/mia/Bureau/reachy-2019-tictactoe
python scripts/convert_models_for_cpu.py

# Transférer les nouveaux modèles
scp reachy_tictactoe/models/*.tflite reachy@<IP>:~/reachy-2019-tictactoe/reachy_tictactoe/models/
```

### Problème : Caméra ne répond pas

**Solution :**
```bash
# Vérifier la connexion caméra
python -c "from reachy_sdk import ReachySDK; r = ReachySDK('localhost'); print(r.right_camera.last_frame)"

# Si None, redémarrer Reachy
sudo reboot
```

### Problème : Détection incorrecte des pièces

**Solution :** Recalibrer les coordonnées
```bash
python scripts/calibrate_board.py --host localhost
# Puis mettre à jour vision.py avec les nouvelles coordonnées
```

### Problème : Températures moteurs élevées

**Résultat attendu :** Le robot entre automatiquement en mode refroidissement à 50°C

**Prévention :**
- Faire des pauses entre les parties
- Vérifier la ventilation de Reachy
- Réduire la fréquence de jeu

---

## 📊 Checklist finale

Avant de déclarer le système prêt :

- [ ] ✅ Modèles convertis pour CPU
- [ ] ✅ Projet transféré sur Reachy
- [ ] ✅ Dépendances installées dans venv
- [ ] ✅ Coordonnées calibrées
- [ ] ✅ Test de vision réussi
- [ ] ✅ Test de mouvement réussi
- [ ] ✅ Premier jeu lancé avec succès
- [ ] ✅ Service configuré (optionnel)

---

## 🎯 Prochaines étapes

### Pour améliorer la précision de détection

1. **Collecter vos propres images :**
   ```bash
   # Utiliser le notebook de collecte
   jupyter notebook notebooks/Collect_training_images.ipynb
   ```

2. **Entraîner les modèles :**
   ```bash
   # Utiliser le notebook d'entraînement
   jupyter notebook notebooks/Train_classifier.ipynb
   ```

3. **Remplacer les modèles par les vôtres**

### Pour personnaliser le comportement

- Modifier `behavior.py` : ajouter de nouveaux comportements émotionnels
- Modifier `rl_agent.py` : changer la stratégie de jeu
- Modifier `moves/` : enregistrer de nouvelles trajectoires

---

## 📞 Support

**En cas de problème :**

1. Consulter les logs : `/tmp/tictactoe*.log`
2. Vérifier la documentation : `README.md`, `QUICK_START.md`
3. Forum Pollen Robotics : https://forum.pollen-robotics.com/
4. GitHub Issues : (votre repository)

---

## 🎉 Félicitations !

Votre robot Reachy est maintenant prêt à jouer au morpion ! 🤖🎮

**Amusez-vous bien et n'hésitez pas à partager vos améliorations !**

