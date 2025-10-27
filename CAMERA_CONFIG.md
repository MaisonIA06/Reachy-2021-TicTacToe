# Configuration de la caméra pour Reachy TicTacToe

## 🎥 Problème actuel

Le robot ne reçoit pas d'images de la caméra, ce qui cause un timeout et un reboot automatique :

```
No image received for 30 sec, going to reboot
```

## ✅ Solution temporaire appliquée

**Mode TEST** activé dans `wait_for_img()` :
- Timeout réduit de 30s → 5s
- Reboot automatique **désactivé**
- Le jeu continue même sans caméra (pour tester les mouvements)

---

## 🔍 Diagnostic de la caméra

### 1. Vérifier que la caméra est détectée

```bash
# Sur le robot
ssh reachy@192.168.18.170

# Lister les périphériques vidéo
ls -l /dev/video*

# Vérifier avec v4l2
v4l2-ctl --list-devices

# Informations sur la caméra
v4l2-ctl --all
```

### 2. Test avec le SDK Reachy

```python
from reachy_sdk import ReachySDK
import numpy as np

# Connexion
reachy = ReachySDK(host='localhost')

# Vérifier les caméras disponibles
print("Caméras disponibles:")
print(f"- Left camera: {hasattr(reachy, 'left_camera')}")
print(f"- Right camera: {hasattr(reachy, 'right_camera')}")

# Essayer de lire
try:
    img = reachy.right_camera.read()
    if img is not None:
        print(f"✓ Image reçue: shape={img.shape}, dtype={img.dtype}")
    else:
        print("✗ Image est None")
except Exception as e:
    print(f"✗ Erreur: {e}")
```

### 3. Test avec OpenCV direct

```python
import cv2

# Essayer différents index de caméra
for i in range(5):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"✓ Caméra {i} fonctionne: {frame.shape}")
        cap.release()
    else:
        print(f"✗ Caméra {i} non disponible")
```

---

## 🛠️ Solutions possibles

### Solution 1 : Vérifier les permissions

```bash
# Ajouter l'utilisateur au groupe video
sudo usermod -a -G video reachy

# Redémarrer la session
logout
# Reconnecter
ssh reachy@192.168.18.170
```

### Solution 2 : Vérifier les drivers RealSense

```bash
# Vérifier l'installation
dpkg -l | grep realsense

# Réinstaller si nécessaire
sudo apt update
sudo apt install librealsense2-utils

# Tester avec realsense-viewer
realsense-viewer
```

### Solution 3 : Modifier l'accès à la caméra dans le code

Si la caméra est sur un autre attribut, modifier dans `tictactoe_playground.py` :

```python
# Ligne ~109 et ~133
# Essayer différentes façons d'accéder à la caméra

# Option 1: Via cameras
img = self.reachy.cameras.right.read()

# Option 2: Via right_camera
img = self.reachy.right_camera.read()

# Option 3: Via la teleop
img = self.reachy.head.right_camera.read()
```

### Solution 4 : Utiliser des images de test

Pour tester le système sans caméra fonctionnelle :

```python
def analyze_board(self):
    """Analyse l'état actuel du plateau de jeu"""
    # MODE TEST: Utiliser une image fixe
    import cv2
    img = cv2.imread('/path/to/test_board.jpg')
    
    if img is None:
        logger.warning('No test image, returning empty board')
        return np.zeros(9, dtype=np.uint8)
    
    # Analyser l'image...
    board, _ = get_board_configuration(img)
    return board.flatten()
```

---

## 🔄 Réactiver le mode production

Une fois la caméra configurée, réactiver le mode normal dans `wait_for_img()` :

```python
def wait_for_img(self):
    """Attend qu'une image soit disponible"""
    start = time.time()
    timeout = 30  # Retour à 30 secondes
    
    while time.time() - start <= timeout:
        try:
            img = self.reachy.right_camera.read()
            if img is not None and len(img) > 0:
                return
        except Exception:
            pass
        time.sleep(0.1)
        
    logger.warning('No image received for 30 sec, going to reboot.')
    os.system('sudo reboot')  # Réactiver le reboot
```

---

## 📝 Configuration RealSense (si applicable)

### Installation complète

```bash
# Ajouter le repository Intel
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-key F6E65AC044F831AC80A06380C8B3A55A6F3EFCDE
sudo add-apt-repository "deb https://librealsense.intel.com/Debian/apt-repo $(lsb_release -cs) main"

# Installer
sudo apt update
sudo apt install librealsense2-dkms librealsense2-utils

# Vérifier
realsense-viewer
```

### Permissions udev

```bash
# Créer le fichier de règles
sudo wget -O /etc/udev/rules.d/99-realsense-libusb.rules https://raw.githubusercontent.com/IntelRealSense/librealsense/master/config/99-realsense-libusb.rules

# Recharger
sudo udevadm control --reload-rules
sudo udevadm trigger
```

---

## 🧪 Tests recommandés

### Test 1 : Caméra USB standard

```bash
# Installer fswebcam
sudo apt install fswebcam

# Prendre une photo de test
fswebcam -d /dev/video0 /tmp/test.jpg

# Vérifier
ls -lh /tmp/test.jpg
```

### Test 2 : RealSense

```bash
# Lister les périphériques RealSense
rs-enumerate-devices

# Capturer une frame
rs-capture
```

### Test 3 : Python + OpenCV

```python
import cv2
import numpy as np

cap = cv2.VideoCapture(0)  # Ou 1, 2, etc.

for i in range(10):
    ret, frame = cap.read()
    if ret:
        print(f"✓ Frame {i}: {frame.shape}")
        cv2.imwrite(f'/tmp/frame_{i}.jpg', frame)
    else:
        print(f"✗ Frame {i} failed")

cap.release()
```

---

## 🎯 Plan d'action recommandé

### Phase 1 : Tests sans caméra (ACTUEL)
1. ✅ Mode TEST activé (pas de reboot)
2. Tester les mouvements du robot
3. Valider que le code goto() fonctionne
4. Vérifier les comportements émotionnels

### Phase 2 : Configuration caméra
1. Diagnostiquer le problème caméra
2. Configurer la caméra correctement
3. Valider la lecture d'images
4. Calibrer les coordonnées du plateau

### Phase 3 : Production
1. Réactiver le mode normal (timeout 30s)
2. Réactiver le reboot automatique
3. Tests complets avec plateau réel
4. Jeu complet fonctionnel

---

## 📞 Support

### Vérification rapide du statut

```bash
# Statut global
python3 << 'EOF'
from reachy_sdk import ReachySDK

reachy = ReachySDK(host='localhost')

print("=== Statut Reachy ===")
print(f"Connecté: {reachy is not None}")

try:
    img = reachy.right_camera.read()
    print(f"Caméra droite: {'✓ OK' if img is not None else '✗ None'}")
except Exception as e:
    print(f"Caméra droite: ✗ Erreur - {e}")

print("\nPour plus d'aide:")
print("- docs.pollen-robotics.com")
print("- forum.pollen-robotics.com")
EOF
```

---

**Avec le mode TEST activé, vous pouvez maintenant tester les mouvements du robot sans craindre les reboots !** 🎮🤖

