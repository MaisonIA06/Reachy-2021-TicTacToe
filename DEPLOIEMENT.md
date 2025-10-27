# Guide de déploiement sur le robot Reachy

## 📋 Situation actuelle

D'après les logs, le code corrigé n'a pas encore été déployé sur le robot. Le robot utilise encore l'ancienne version avec l'erreur `ValueError: goal_positions keys should be Joint!`.

## 🚀 Étapes de déploiement

### 1. Transférer le code corrigé vers le robot

Depuis votre machine locale (NUC ou autre), transférez les fichiers vers le robot :

```bash
# Depuis votre machine locale
cd /home/mia/Bureau/reachy-2019-tictactoe

# Transférer les fichiers corrigés vers le robot
scp -r reachy_tictactoe/ reachy@192.168.18.170:~/dev/Reachy-2021-TicTacToe/
```

**OU** si vous êtes déjà connecté en SSH au robot :

```bash
# Sur le robot
cd ~/dev/Reachy-2021-TicTacToe

# Tirer les dernières modifications (si vous utilisez git)
git pull

# OU copier manuellement les fichiers modifiés
```

### 2. Vérifier les fichiers sur le robot

```bash
# Se connecter au robot
ssh reachy@192.168.18.170

# Aller dans le répertoire du projet
cd ~/dev/Reachy-2021-TicTacToe

# Vérifier que les fichiers corrigés sont présents
ls -l reachy_tictactoe/tictactoe_playground.py
ls -l reachy_tictactoe/behavior.py

# Vérifier la date de modification (doit être récente)
stat reachy_tictactoe/tictactoe_playground.py
```

### 3. Réinstaller le package

```bash
# Sur le robot
cd ~/dev/Reachy-2021-TicTacToe
source venv/bin/activate

# Réinstaller le package
pip install -e .

# Ou forcer la réinstallation
pip install --force-reinstall -e .
```

### 4. Tester l'importation

```bash
# Test rapide
python -c "from reachy_tictactoe import TictactoePlayground; print('✓ Import OK')"
```

### 5. Résoudre le problème de caméra

D'après les logs, il y a un timeout caméra :
```
No image received for 30 sec, going to reboot
```

#### Solution 1 : Vérifier la caméra

```bash
# Sur le robot
python3 << EOF
from reachy_sdk import ReachySDK
reachy = ReachySDK(host='localhost')

# Tester la caméra
try:
    img = reachy.cameras.right.read()
    if img is not None:
        print(f"✓ Caméra fonctionne - Image shape: {img.shape}")
    else:
        print("✗ Caméra retourne None")
except Exception as e:
    print(f"✗ Erreur caméra: {e}")
EOF
```

#### Solution 2 : Désactiver temporairement l'attente caméra

Pour tester le code sans la caméra, vous pouvez modifier `wait_for_img()` :

```python
# Dans tictactoe_playground.py, ligne ~675
def wait_for_img(self):
    """Attend qu'une image soit disponible"""
    # TEMPORAIRE : désactiver pour test
    logger.warning('wait_for_img() disabled for testing')
    return
    
    # Code original...
```

### 6. Lancer le jeu

```bash
# Sur le robot
cd ~/dev/Reachy-2021-TicTacToe
source venv/bin/activate

# Lancer avec logs
python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe

# Dans un autre terminal, suivre les logs
ssh reachy@192.168.18.170
tail -f /tmp/tictactoe-*.log
```

---

## 🐛 Problèmes identifiés dans les logs

### Problème 1 : Code non déployé (Log 1)
```
ValueError: goal_positions keys should be Joint!
```
**Solution** : Suivre les étapes 1-4 ci-dessus

### Problème 2 : Erreur `_get_joint_by_name()` (Log 2)
```
Error accessing joint r_arm.r_gripper: argument of type 'DeviceHolder' is not iterable
```
**Solution** : ✅ Corrigé dans la dernière version (utilise `getattr()` au lieu de `in`)

### Problème 3 : Timeout caméra (Log 2)
```
No image received for 30 sec, going to reboot
```
**Solutions possibles** :

1. **Vérifier que la caméra fonctionne** :
   ```bash
   v4l2-ctl --list-devices
   ```

2. **Vérifier les permissions** :
   ```bash
   ls -l /dev/video*
   sudo usermod -a -G video reachy
   ```

3. **Redémarrer le service caméra** (si applicable) :
   ```bash
   sudo systemctl restart camera-service
   ```

4. **Test manuel de la caméra** :
   ```python
   from reachy_sdk import ReachySDK
   import cv2
   
   reachy = ReachySDK(host='localhost')
   
   for i in range(10):
       img = reachy.cameras.right.read()
       if img is not None:
           print(f"✓ Image {i+1} reçue: {img.shape}")
           cv2.imwrite(f'/tmp/test_cam_{i}.jpg', img)
       else:
           print(f"✗ Image {i+1} None")
       time.sleep(0.5)
   ```

---

## ✅ Checklist de déploiement

- [ ] Fichiers transférés vers le robot
- [ ] Package réinstallé (`pip install -e .`)
- [ ] Test d'importation réussi
- [ ] Caméra vérifiée et fonctionnelle
- [ ] Logs suivis en temps réel
- [ ] Test de lancement sans erreur

---

## 📝 Commandes rapides

### Déploiement complet (depuis votre machine)

```bash
# 1. Transférer
scp -r reachy_tictactoe/ reachy@192.168.18.170:~/dev/Reachy-2021-TicTacToe/

# 2. Installer et tester (sur le robot)
ssh reachy@192.168.18.170 << 'EOF'
cd ~/dev/Reachy-2021-TicTacToe
source venv/bin/activate
pip install -e .
python -c "from reachy_tictactoe import TictactoePlayground; print('✓ OK')"
EOF

# 3. Lancer
ssh reachy@192.168.18.170
cd ~/dev/Reachy-2021-TicTacToe
source venv/bin/activate
python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe
```

### Vérification rapide

```bash
# Test sur le robot
ssh reachy@192.168.18.170 "cd ~/dev/Reachy-2021-TicTacToe && source venv/bin/activate && python -c 'from reachy_tictactoe import TictactoePlayground; print(\"✓ OK\")'"
```

---

## 🔧 Dépannage

### Si `goto()` donne encore l'erreur "keys should be Joint"

```bash
# Vérifier que c'est bien le bon fichier
ssh reachy@192.168.18.170
grep -n "self.reachy.head.l_antenna" ~/dev/Reachy-2021-TicTacToe/reachy_tictactoe/tictactoe_playground.py

# Devrait retourner plusieurs lignes avec les objets Joint
```

### Si la caméra ne fonctionne pas

```bash
# Option 1: Commenter temporairement wait_for_img()
# Option 2: Utiliser une image de test
# Option 3: Vérifier les drivers
lsmod | grep video
```

### Si le robot reboot constamment

```bash
# Désactiver le auto-reboot dans wait_for_img()
# Ligne 683 : Commenter os.system('sudo reboot')
```

---

## 📞 Support

Si les problèmes persistent :

1. Vérifier les logs complets : `cat /tmp/tictactoe-*.log`
2. Vérifier l'état du robot : `systemctl status reachy`
3. Consulter la documentation : [docs.pollen-robotics.com](https://docs.pollen-robotics.com/)
4. Forum : [forum.pollen-robotics.com](https://forum.pollen-robotics.com/)

---

**Après ces étapes, le code corrigé devrait fonctionner sur le robot !** 🚀

