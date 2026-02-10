# 🤖 Tic-Tac-Toe pour Reachy V1 (SDK 2021)

Un projet permettant au robot Reachy de jouer au morpion (Tic-Tac-Toe) contre un humain. Ce projet a été adapté du code original de **Pollen Robotics (2019)** pour être compatible avec le **SDK Reachy 2021**.

---

## 📋 Table des matières

- [Présentation](#-présentation)
- [Prérequis](#-prérequis)
- [Installation rapide](#-installation-rapide)
- [Démarrage](#-démarrage)
- [Guides disponibles](#-guides-disponibles)
- [Structure du projet](#-structure-du-projet)
- [Configuration](#-configuration)
- [Règles du jeu](#-règles-du-jeu)
- [Dépannage](#-dépannage)
- [Contributions](#-contributions)
- [Licence](#-licence)
- [Auteurs](#-auteurs)

---

## 🎯 Présentation

Ce projet transforme votre robot Reachy en adversaire de morpion intelligent. Le robot utilise :
- **Vision par ordinateur** : Détection des pièces sur le plateau via caméra
- **Intelligence artificielle** : Stratégie de jeu optimale avec Q-learning
- **Robotique** : Mouvements fluides et précis pour placer les pièces

### Fonctionnalités

- ✅ Détection automatique des pièces (cubes et cylindres)
- ✅ Validation du plateau avant chaque coup
- ✅ Stratégie de jeu adaptative
- ✅ Interface vocale avec commentaires du robot
- ✅ Calibration interactive du plateau

---

## 🔧 Prérequis

### Matériel requis

- **Robot Reachy V1** avec :
  - Bras droit avec pince fonctionnelle
  - Tête avec caméra opérationnelle
  - NUC ou ordinateur embarqué
- **Plateau de jeu** : Plateau de TicTacToe avec 9 cases
- **Pièces** : 5 cylindres (joueur humain) + 5 cubes (robot)

### Logiciel requis

- **Système d'exploitation** : Ubuntu 20.04+ / Debian 11+
- **Python** : Version 3.8 ou supérieure
- **Reachy SDK** : Version 0.7.0 ou supérieure (SDK 2021)

---

## 🚀 Installation rapide

### 1. Cloner le repository

```bash
git clone https://github.com/MaisonIA06/Reachy-2021-TicTacToe.git
cd Reachy-2021-TicTacToe
```

### 2. Installer les dépendances système

```bash
# Sur Ubuntu/Debian
sudo apt update
sudo apt install -y python3-pip python3-opencv python3-venv
```

### 3. Créer et activer un environnement virtuel

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Installer les dépendances Python

```bash
# Installer les dépendances de base
pip install -r requirements.txt

# Installer le package en mode développement
pip install -e .
```

### 5. Installer TensorFlow Lite Runtime (pour la vision)

```bash
pip install tflite-runtime>=2.5.0
```

---

## 🎮 Démarrage

### Première utilisation

Avant de jouer, vous devez **calibrer le plateau** :

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Lancer la calibration (sur Reachy)
python scripts/calibration/calibrate_board.py --host localhost
```

Suivez les instructions à l'écran pour tracer les rectangles autour de chaque case du plateau.

### Lancer une partie

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Lancer le jeu
python -m reachy_tictactoe.game_launcher

# Ou avec logs
python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe.log

# Si Reachy est sur une autre machine
python -m reachy_tictactoe.game_launcher --host 192.168.1.XXX
```

### Commande alternative

Si vous avez installé le package, vous pouvez aussi utiliser :

```bash
reachy-tictactoe
```

---

## 📚 Guides disponibles

Ce projet contient plusieurs guides détaillés pour vous accompagner :

### 🎯 Guide de démarrage rapide

- **[Guide de création des modèles](GUIDE_CREATION_MODELES.md)** : Apprenez à créer et entraîner vos propres modèles de vision pour la détection des pièces et la validation du plateau.

### 🤖 Guide des mouvements

- **[Guide de ré-enregistrement des mouvements](GUIDE_REENREGISTREMENT_MOUVEMENTS.md)** : Ré-enregistrez les mouvements du robot si vous changez la position ou la taille du plateau.

### 🛠️ Scripts utilitaires

- **[Documentation des scripts](scripts/README.md)** : Guide complet de tous les scripts disponibles pour la calibration, l'entraînement, et les tests.

---

## 📁 Structure du projet

```
Reachy-2021-TicTacToe/
├── reachy_tictactoe/          # Code principal du projet
│   ├── game_launcher.py      # Point d'entrée principal
│   ├── behavior.py           # Comportement du robot
│   ├── vision.py             # Détection visuelle
│   ├── rl_agent.py           # Agent d'apprentissage par renforcement
│   ├── models/               # Modèles TensorFlow Lite
│   ├── moves/                # Mouvements enregistrés (.npz)
│   └── sounds/               # Fichiers audio du robot
│
├── scripts/                  # Scripts utilitaires
│   ├── moves/                # Enregistrement et test des mouvements
│   ├── calibration/          # Calibration du plateau
│   ├── training/             # Entraînement des modèles
│   └── utils/                # Utilitaires divers
│
├── training_data/            # Données d'entraînement
│   ├── boxes/               # Images des cases
│   └── valid_board/          # Images de plateaux valides/invalides
│
├── requirements.txt          # Dépendances Python (runtime)
├── requirements-training.txt # Dépendances pour l'entraînement
├── setup.py                  # Configuration du package
└── LICENSE                   # Licence Apache 2.0
```

---

## ⚙️ Configuration

### Calibration du plateau

Les coordonnées des cases sont stockées dans `reachy_tictactoe/config.py`. Pour les modifier :

1. **Méthode recommandée** : Utiliser l'outil graphique
   ```bash
   python scripts/calibration/calibrate_board.py --host localhost
   ```

2. **Méthode manuelle** : Utiliser le script utilitaire
   ```bash
   python scripts/utils/show_config.py --set-board LEFT RIGHT TOP BOTTOM
   ```

3. **Édition directe** : Modifier `reachy_tictactoe/config.py`

### Vérifier la configuration

```bash
python scripts/utils/show_config.py
```

---

## 🎲 Règles du jeu

1. **Tirage au sort** : Un tirage au sort détermine qui commence
2. **Alternance** : Le robot et l'humain jouent alternativement
3. **Pièces** :
   - 👤 **Humain** : Joue avec les **cylindres** 🔵
   - 🤖 **Reachy** : Joue avec les **cubes** ⬜
4. **Victoire** : Le premier à aligner 3 pièces (horizontalement, verticalement ou en diagonale) gagne !
5. **Match nul** : Si toutes les cases sont remplies sans gagnant

---

## 🤝 Contributions

Les contributions sont les bienvenues ! Voici comment contribuer :

1. **Fork** le projet
2. Créez une **branche** pour votre fonctionnalité (`git checkout -b feature/AmazingFeature`)
3. **Commit** vos changements (`git commit -m 'Add some AmazingFeature'`)
4. **Push** vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une **Pull Request**

### Code de conduite

- Respectez les conventions de code existantes
- Ajoutez des tests pour les nouvelles fonctionnalités
- Documentez vos modifications

---

## 📄 Licence

Ce projet est distribué sous la **Licence Apache 2.0**.

```
Copyright 2019 Pollen Robotics
Copyright 2021-2024 MaisonIA06

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

Voir le fichier [LICENSE](LICENSE) pour le texte complet de la licence.

---

## 👥 Auteurs

- **Pollen Robotics** - Code original (2019)
  - Site web : https://www.pollen-robotics.com/
  - GitHub : https://github.com/pollen-robotics

- **MaisonIA06** - Adaptation SDK 2021 (2021-2024)
  - Email : wnaiji@maison-intelligence-artificielle.com
  - GitHub : https://github.com/MaisonIA06

---

## 🙏 Remerciements

- **Pollen Robotics** pour le code original et leur excellent travail sur le robot Reachy
- La communauté Reachy pour le support et les retours

---

## 📞 Support

Pour toute question ou problème :

- 📧 Email : wnaiji@maison-intelligence-artificielle.com
- 🐛 Issues : [GitHub Issues](https://github.com/MaisonIA06/Reachy-2021-TicTacToe/issues)

---

**Bon jeu ! 🎮🤖**
