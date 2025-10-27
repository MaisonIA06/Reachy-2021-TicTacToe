# 🚀 Guide de démarrage rapide - Reachy TicTacToe (SDK 2021)

## ✅ Étapes d'installation

### 1. Installation de base

```bash
cd ~/dev/Reachy-2021-TicTacToe

# Créer et activer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Installer le package
pip install -e .
```

### 2. Résoudre le problème EdgeTPU

**Erreur** : `RuntimeError: Encountered unresolved custom op: edgetpu-custom-op`

**Cause** : Les modèles sont compilés pour EdgeTPU, mais votre NUC n'a pas d'accélérateur EdgeTPU.

**Solution rapide** :

```bash
# Installer TensorFlow (si pas déjà fait)
pip install tensorflow

# Créer des modèles de remplacement pour CPU
python scripts/create_fallback_models.py
```

⚠️ **Attention** : Ces modèles sont des placeholders pour tester le système. Ils ne détectent pas vraiment les pièces.

**Pour une solution complète**, consultez [EDGE_TPU_CONVERSION.md](EDGE_TPU_CONVERSION.md)

### 3. Test de l'installation

```bash
# Test d'importation
python -c "from reachy_tictactoe import TictactoePlayground; print('✓ Installation OK')"

# Test de connexion (avec Reachy allumé)
python -c "from reachy_sdk import ReachySDK; r = ReachySDK(host='localhost'); print(r.info)"
```

## 🎮 Lancement du jeu

### Mode simple

```bash
source venv/bin/activate
python -m reachy_tictactoe.game_launcher
```

### Avec logs

```bash
python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe
```

### Connexion distante

```bash
python -m reachy_tictactoe.game_launcher --host 192.168.1.100
```

## 🔧 Configuration en tant que service

### 1. Copier le fichier service

```bash
sudo cp tictactoe_launcher_v2.service /etc/systemd/system/tictactoe_launcher.service
```

### 2. Modifier les chemins dans le fichier

```bash
sudo nano /etc/systemd/system/tictactoe_launcher.service
```

Vérifiez que les chemins correspondent à votre installation :
- `Environment="PATH=/home/reachy/dev/Reachy-2021-TicTacToe/venv/bin:$PATH"`
- `ExecStart=/home/reachy/dev/Reachy-2021-TicTacToe/venv/bin/python ...`
- `WorkingDirectory=/home/reachy/dev/Reachy-2021-TicTacToe`
- `User=reachy`

### 3. Activer et démarrer

```bash
sudo systemctl daemon-reload
sudo systemctl enable tictactoe_launcher
sudo systemctl start tictactoe_launcher
```

### 4. Vérifier le statut

```bash
sudo systemctl status tictactoe_launcher
sudo journalctl -u tictactoe_launcher -f
```

## 🐛 Dépannage rapide

### Problème 1 : Module 'reachy' not found

**Solution** :
```bash
source venv/bin/activate
pip install reachy-sdk
```

### Problème 2 : EdgeTPU error

**Solution** :
```bash
python scripts/create_fallback_models.py
```

### Problème 3 : Caméra non détectée

**Vérification** :
```bash
python -c "from reachy_sdk import ReachySDK; r = ReachySDK(host='localhost'); print(r.right_camera.read())"
```

### Problème 4 : Moteurs ne répondent pas

**Vérifications** :
1. Reachy est allumé
2. Connexion réseau OK : `ping localhost` ou `ping <ip_reachy>`
3. Le serveur gRPC de Reachy tourne

### Problème 5 : Service ne démarre pas

**Vérifier les logs** :
```bash
sudo journalctl -u tictactoe_launcher -n 50
```

**Vérifier les permissions** :
```bash
ls -la /home/reachy/dev/Reachy-2021-TicTacToe/
```

## 📊 Architecture

```
┌──────────────────────────────────────────┐
│         game_launcher.py                 │
│  (Point d'entrée - Boucle de jeu)       │
└─────────────────┬────────────────────────┘
                  │
┌─────────────────▼────────────────────────┐
│      tictactoe_playground.py             │
│  (Classe principale - Contrôle Reachy)   │
└──────┬─────────┬──────────┬──────────────┘
       │         │          │
   ┌───▼──┐  ┌──▼───┐  ┌───▼────┐
   │vision│  │behav.│  │rl_agent│
   │.py   │  │.py   │  │.py     │
   └──────┘  └──────┘  └────────┘
       │
   ┌───▼────────┐
   │  models/   │
   │ .tflite    │
   └────────────┘
```

## 📚 Documentation complète

- **[README.md](README.md)** - Documentation complète
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Guide de migration 2019→2021
- **[EDGE_TPU_CONVERSION.md](EDGE_TPU_CONVERSION.md)** - Conversion des modèles
- **Notebooks** - Dans le dossier `notebooks/` pour le training

## 🎯 Prochaines étapes

1. ✅ Installation et test de base
2. ⚠️ Résoudre le problème EdgeTPU (modèles CPU)
3. 🎮 Test du jeu avec Reachy
4. 🔧 Configuration du service (optionnel)
5. 📊 Calibration de la caméra (si nécessaire)
6. 🎓 Entraînement de nouveaux modèles (si besoin)

## 💬 Support

- **Forum** : [forum.pollen-robotics.com](https://forum.pollen-robotics.com/)
- **Documentation** : [docs.pollen-robotics.com](https://docs.pollen-robotics.com/)
- **GitHub Issues** : Pour les bugs et suggestions

---

**Bon jeu avec Reachy ! 🤖🎮**

