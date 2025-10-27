# Tic-Tac-Toe playground pour Reachy V1 (SDK 2021)

Ce projet permet au robot Reachy de jouer au morpion (Tic-Tac-Toe) contre un humain. Il a été adapté du code original de 2019 pour être compatible avec le SDK Reachy 2021.

## 🤖 Prérequis matériels

- Robot Reachy V1 avec :
  - Bras droit avec pince
  - Tête avec caméra
  - NUC ou ordinateur embarqué

## 📦 Installation

### 1. Installation des dépendances système

```bash
# Sur Ubuntu/Debian
sudo apt update
sudo apt install python3-pip python3-opencv
```

### 2. Installation des dépendances Python

```bash
# Cloner le repository
cd ~/dev
git clone <repository-url>
cd reachy-2019-tictactoe

# Créer un environnement virtuel (recommandé)
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Installer le package
pip install -e .
```

### 3. Installation de TensorFlow Lite Runtime

Pour la vision par ordinateur, installez TensorFlow Lite Runtime :

```bash
pip install tflite-runtime
```

Ou si ce package n'est pas disponible, utilisez TensorFlow complet :

```bash
pip install tensorflow
```

### ⚠️ 4. Problème EdgeTPU (Important pour NUC sans accélérateur)

Les modèles `.tflite` inclus sont compilés pour **EdgeTPU** et ne fonctionneront PAS sur un NUC standard.

**Si vous obtenez l'erreur** `RuntimeError: Encountered unresolved custom op: edgetpu-custom-op` :

#### Solution rapide (modèles de test) :

```bash
# Créer des modèles de remplacement pour CPU
python scripts/create_fallback_models.py
```

**⚠️ Ces modèles sont des placeholders** et ne détectent pas vraiment les pièces.

#### Solution complète :

Consultez **[EDGE_TPU_CONVERSION.md](EDGE_TPU_CONVERSION.md)** pour :
- Reconvertir les modèles originaux pour CPU
- Ou ajouter un accélérateur EdgeTPU USB

## 🚀 Utilisation

### Lancement du jeu

#### Méthode 1 : Depuis la ligne de commande

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Lancer le jeu
python -m reachy_tictactoe.game_launcher

# Avec logs
python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe

# Si Reachy est sur une autre machine
python -m reachy_tictactoe.game_launcher --host 192.168.1.XXX
```

#### Méthode 2 : En tant que service systemd

1. Modifier le fichier service :

```bash
sudo nano /etc/systemd/system/tictactoe_launcher.service
```

Contenu du fichier :

```ini
[Unit]
Description=TicTacToe Playground Service
Wants=network-online.target
After=network.target network-online.target

[Service]
PIDFile=/var/run/tictactoe.pid
Environment="PATH=/home/reachy/dev/reachy-2019-tictactoe/venv/bin:$PATH"
ExecStart=/home/reachy/dev/reachy-2019-tictactoe/venv/bin/python -m reachy_tictactoe.game_launcher --log-file /home/reachy/dev/reachy-2019-tictactoe/gamelog
User=reachy
Group=reachy
WorkingDirectory=/home/reachy/dev/reachy-2019-tictactoe
Type=simple

[Install]
WantedBy=multi-user.target
```

2. Activer et démarrer le service :

```bash
sudo systemctl daemon-reload
sudo systemctl enable tictactoe_launcher
sudo systemctl start tictactoe_launcher

# Vérifier le statut
sudo systemctl status tictactoe_launcher

# Voir les logs
sudo journalctl -u tictactoe_launcher -f
```

## 📝 Modifications principales par rapport à la version 2019

### 1. SDK Reachy 2021

- **Ancien** : `from reachy import Reachy`
- **Nouveau** : `from reachy_sdk import ReachySDK`

### 2. Contrôle des moteurs

- **Ancien** : `motor.compliant = False` / `motor.goto()`
- **Nouveau** : `reachy.turn_on()` / `goto()` avec `InterpolationMode`

### 3. Noms des articulations

- **Ancien** : `right_arm.shoulder_pitch`
- **Nouveau** : `r_arm.r_shoulder_pitch`

### 4. Vision

- **Ancien** : EdgeTPU (`edgetpu.classification.engine`)
- **Nouveau** : TensorFlow Lite Runtime (`tflite_runtime.interpreter`)

### 5. Caméra

- **Ancien** : `reachy.head.right_camera.read()`
- **Nouveau** : `reachy.right_camera.read()`

## 🎮 Règles du jeu

1. Le robot et l'humain jouent alternativement
2. L'humain joue avec les **cubes** ⬜
3. Reachy joue avec les **cylindres** 🔵
4. Un tirage au sort détermine qui commence
5. Le premier à aligner 3 pièces gagne !

## 🔧 Configuration

### Calibration de la caméra

Les coordonnées des cases du plateau sont définies dans `vision.py` :

```python
board_cases = np.array((
    ((209, 316, 253, 346), (316, 425, 253, 346), (425, 529, 253, 346)),
    ((189, 306, 346, 455), (306, 428, 346, 455), (428, 538, 346, 455)),
    ((174, 299, 455, 580), (299, 429, 455, 580), (429, 551, 455, 580)),
))
```

Ajustez ces valeurs selon votre configuration.

### Positions du bras

Les positions sont définies dans `moves/__init__.py` :

```python
rest_pos = {
    'right_arm.shoulder_pitch': 50,
    'right_arm.shoulder_roll': -15,
    # ...
}
```

## 🐛 Dépannage

### Erreur "No module named 'reachy'"

Le SDK Reachy n'est pas installé dans l'environnement virtuel :

```bash
source venv/bin/activate
pip install reachy-sdk
```

### Erreur de caméra

Vérifiez que la caméra est bien connectée :

```bash
# Tester la connexion
python -c "from reachy_sdk import ReachySDK; r = ReachySDK(host='localhost'); print(r.right_camera.read())"
```

### Températures élevées

Le robot entre automatiquement en mode refroidissement si les moteurs dépassent 50°C.

### Logs

Les logs sont sauvegardés dans le répertoire spécifié avec `--log-file`.

## 📚 Structure du projet

```
reachy-2019-tictactoe/
├── reachy_tictactoe/
│   ├── __init__.py
│   ├── tictactoe_playground.py  # Classe principale
│   ├── game_launcher.py          # Point d'entrée
│   ├── vision.py                 # Détection du plateau
│   ├── behavior.py               # Comportements émotionnels
│   ├── rl_agent.py               # Agent RL pour le jeu
│   ├── utils.py                  # Utilitaires
│   ├── detect_board.py           # Détection du plateau
│   ├── models/                   # Modèles TFLite
│   │   ├── ttt-boxes.tflite
│   │   ├── ttt-boxes.txt
│   │   ├── ttt-valid-board.tflite
│   │   └── ttt-valid-board.txt
│   ├── moves/                    # Trajectoires enregistrées
│   │   └── *.npz
│   └── Q-value.npz               # Table Q pré-entraînée
├── notebooks/                    # Notebooks Jupyter
├── setup.py
├── requirements.txt
└── README.md
```

## 🤝 Contributions

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## 📄 Licence

Voir le fichier LICENSE pour plus de détails.

## 👥 Auteurs

- **Pollen Robotics** - Code original 2019
- Adaptation SDK 2021

## 🔗 Liens utiles

- [Documentation Reachy SDK](https://docs.pollen-robotics.com/)
- [Pollen Robotics](https://www.pollen-robotics.com/)
- [Forum Pollen Robotics](https://forum.pollen-robotics.com/)
