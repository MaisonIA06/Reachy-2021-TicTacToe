# ⚡ Déploiement Rapide - TicTacToe sur Reachy

Guide condensé pour déployer rapidement le système. Pour plus de détails, voir `GUIDE_DEPLOYMENT.md`.

---

## 🎯 En 5 étapes

### 1️⃣ Sur votre PC : Convertir les modèles (2 min)

```bash
cd /home/mia/Bureau/reachy-2019-tictactoe
pip install tensorflow
python scripts/convert_models_for_cpu.py
```

**Résultat attendu :**
```
✅ Modèles CPU créés avec succès !
✓ ttt-boxes.tflite fonctionne (CPU)
✓ ttt-valid-board.tflite fonctionne (CPU)
```

---

### 2️⃣ Transférer vers Reachy (5 min)

```bash
# Remplacez <IP_REACHY> par l'adresse IP de votre robot
# Exemple: 192.168.1.42

scp -r reachy-2019-tictactoe reachy@<IP_REACHY>:~/
```

---

### 3️⃣ Sur Reachy : Installer (10 min)

```bash
# Se connecter
ssh reachy@<IP_REACHY>

# Installer
cd ~/reachy-2019-tictactoe
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

---

### 4️⃣ Calibrer les coordonnées (5 min)

```bash
# Placer le plateau devant Reachy
# Lancer la calibration
python scripts/calibrate_board.py --host localhost

# Interface graphique :
# - Cliquez-glissez pour tracer chaque case
# - Ordre: (0,0) (0,1) (0,2) (1,0) (1,1) (1,2) (2,0) (2,1) (2,2)
# - Appuyez sur 's' pour sauvegarder

# Mettre à jour vision.py avec les coordonnées affichées
nano reachy_tictactoe/vision.py
# Remplacer la variable board_cases (~ligne 165)
```

---

### 5️⃣ Lancer le jeu ! 🎮

```bash
python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe
```

**Le jeu démarre !** Posez un plateau vide devant Reachy et jouez !

---

## 🔍 Vérification rapide

Avant de lancer le jeu, testez :

```bash
# Test caméra et vision
python -c "
from reachy_sdk import ReachySDK
from reachy_tictactoe.vision import is_board_valid
import time

r = ReachySDK('localhost')
r.turn_on('head')
r.head.look_at(x=0.5, y=0, z=-0.6, duration=1.0)
time.sleep(1.5)

img = r.right_camera.last_frame
print('✓ Caméra OK:', img.shape)
print('✓ Plateau valide:', is_board_valid(img))
"
```

---

## 🐛 Problème ?

| Erreur | Solution |
|--------|----------|
| `edgetpu-custom-op` | Étape 1 non faite : `python scripts/convert_models_for_cpu.py` |
| `No module named 'reachy_sdk'` | `source venv/bin/activate && pip install reachy-sdk` |
| Détection incorrecte | Re-calibrer : `python scripts/calibrate_board.py` |
| Caméra ne répond pas | `sudo reboot` sur Reachy |

**Guide complet :** `GUIDE_DEPLOYMENT.md`

---

## 📚 Architecture des fichiers

```
reachy-2019-tictactoe/
├── scripts/
│   ├── convert_models_for_cpu.py  ← Étape 1 (sur PC)
│   └── calibrate_board.py         ← Étape 4 (sur Reachy)
├── reachy_tictactoe/
│   ├── models/
│   │   ├── ttt-boxes.tflite       ← Généré par étape 1
│   │   └── ttt-valid-board.tflite ← Généré par étape 1
│   ├── vision.py                  ← À mettre à jour après calibration
│   └── game_launcher.py           ← Point d'entrée principal
└── GUIDE_DEPLOYMENT.md            ← Guide détaillé
```

---

## ✅ Checklist

- [ ] Modèles convertis pour CPU
- [ ] Projet sur Reachy
- [ ] Dependencies installées
- [ ] Coordonnées calibrées
- [ ] `vision.py` mis à jour
- [ ] Test caméra OK
- [ ] Premier jeu réussi 🎉

---

**Temps total estimé : ~20-30 minutes**

**Bon jeu ! 🤖🎮**

