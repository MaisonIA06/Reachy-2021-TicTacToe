# ✅ Prochaines étapes - Vos actions requises

Ce fichier liste exactement ce que **VOUS** devez faire maintenant pour créer vos modèles.

---

## 📋 Ce qui a été automatisé pour vous ✅

### Scripts créés (prêts à l'emploi)
- ✅ `collect_boxes_images.py` - Collecte d'images des cases
- ✅ `collect_valid_board_images.py` - Collecte d'images du plateau
- ✅ `train_models.py` - Entraînement automatique
- ✅ `convert_to_tflite.py` - Conversion automatique
- ✅ `check_training_data.py` - Vérification automatique

### Documentation créée (à lire)
- ✅ `COMMENCER_ICI.md` - Guide de démarrage
- ✅ `DEMARRAGE_RAPIDE_MODELES.md` - Commandes rapides
- ✅ `GUIDE_CREATION_MODELES.md` - Guide complet
- ✅ `SCRIPTS_CREES.md` - Documentation technique

### Infrastructure
- ✅ Structure de dossiers créée
- ✅ Script d'installation prêt
- ✅ Fichier de dépendances prêt

---

## 🎯 VOS ACTIONS REQUISES (étape par étape)

### ✅ ÉTAPE 1 : Lire la documentation (10 min)

**Action** : Lisez **un** de ces fichiers (au choix) :

```bash
# Option 1 : Guide rapide (recommandé pour commencer)
cat DEMARRAGE_RAPIDE_MODELES.md

# Option 2 : Guide complet (si vous voulez tout comprendre)
cat GUIDE_CREATION_MODELES.md

# Option 3 : Démarrage ultra-rapide
cat COMMENCER_ICI.md
```

**Résultat attendu** : Vous comprenez le processus global

---

### ⚙️ ÉTAPE 2 : Installer les dépendances (30 min)

**Actions** :

```bash
cd /home/mia/Bureau/reachy-2019-tictactoe
source venv/bin/activate
./install_training.sh
```

**Ce qui se passe** :
- Installation de TensorFlow (peut prendre 15-20 min)
- Installation de Jupyter et matplotlib
- Création de la structure de dossiers
- Vérification de l'installation

**Résultat attendu** : Message "🎉 Installation terminée avec succès!"

**Si erreur** : Vérifiez votre connexion internet et l'espace disque

---

### 📐 ÉTAPE 3 : Calibrer le plateau (15 min)

**Actions** :

```bash
python scripts/calibrate_board.py --host localhost
```

**Ce que vous devez faire** :
1. Le script lance Reachy et capture le plateau
2. Une fenêtre s'ouvre avec l'image
3. **Tracez 9 rectangles** (un par case) dans l'ordre :
   - Ligne 1 : cases 0, 1, 2
   - Ligne 2 : cases 3, 4, 5  
   - Ligne 3 : cases 6, 7, 8
4. Appuyez sur **'s'** pour sauvegarder
5. **Copiez les coordonnées** de `/tmp/board_calibration.py`
6. **Collez-les** dans `reachy_tictactoe/vision.py` (ligne ~250)

**Résultat attendu** : Fichier `/tmp/board_calibration.py` créé avec les coordonnées

**Important** : Cette étape est **CRITIQUE** - sans calibration précise, la détection ne fonctionnera pas !

---

### 📸 ÉTAPE 4 : Collecter les images (2-3 heures)

**C'est l'étape la plus longue** - Vous pouvez la faire en plusieurs sessions !

#### Session 1 : Cases VIDES (30 min)

```bash
python scripts/collect_boxes_images.py --host localhost --class empty --target 50
```

**Ce que vous devez faire** :
1. **Enlevez TOUTES les pièces** du plateau
2. Appuyez sur Entrée pour capturer
3. Déplacez légèrement le plateau
4. Appuyez sur Entrée à nouveau
5. Répétez 50 fois (variez éclairage, position)

**Objectif** : 450 images (50 captures × 9 cases)

---

#### Session 2 : Cases avec CUBES (45 min)

```bash
python scripts/collect_boxes_images.py --host localhost --class cube --target 50
```

**Ce que vous devez faire** :
1. **Placez des cubes** sur le plateau
2. Indiquez les cases avec cubes (ex: `0,4,8`)
3. Appuyez sur Entrée pour capturer
4. **Changez la configuration** des cubes
5. Répétez 50 fois

**Exemples de configurations** :
- `4` : cube au centre
- `0,2,6,8` : coins
- `0,1,2` : ligne du haut
- `1,3,5,7` : bords
- `0,4,8` : diagonale

**Objectif** : ~450 images

---

#### Session 3 : Cases avec CYLINDRES (45 min)

```bash
python scripts/collect_boxes_images.py --host localhost --class cylinder --target 50
```

**Même principe que pour les cubes.**

**Objectif** : ~450 images

---

#### Session 4 : Plateaux VALIDES (30 min)

```bash
python scripts/collect_valid_board_images.py --host localhost --class valid --target 150
```

**Ce que vous devez faire** :
1. **Positionnez le plateau correctement** (bien centré, visible)
2. Appuyez sur Entrée
3. Bougez **légèrement** le plateau (±1cm, ±2 degrés)
4. Appuyez sur Entrée
5. Répétez 150 fois (variez éclairage)

**Objectif** : 150 images

---

#### Session 5 : Plateaux INVALIDES (30 min)

```bash
python scripts/collect_valid_board_images.py --host localhost --class invalid --target 150
```

**Ce que vous devez faire - créez des situations problématiques** :
- Plateau décentré ou tourné à 45°
- Plateau partiellement caché
- Main devant la caméra
- Plateau absent
- Trop sombre ou trop clair
- Trop près ou trop loin

**Objectif** : 150 images

---

### ✔️ ÉTAPE 4.5 : Vérifier les données (5 min)

```bash
python scripts/check_training_data.py
```

**Résultat attendu** : "✅ Prêt pour l'entraînement" pour les 2 modèles

**Si insuffisant** : Collectez plus d'images avec les scripts ci-dessus

---

### 🧹 ÉTAPE 5 : Nettoyer les images (30 min)

**Actions** :

```bash
# Parcourir les images et supprimer les mauvaises
eog training_data/boxes/empty/*.jpg
eog training_data/boxes/cube/*.jpg
eog training_data/boxes/cylinder/*.jpg
eog training_data/valid_board/valid/*.jpg
eog training_data/valid_board/invalid/*.jpg
```

**Supprimez** :
- Images floues
- Images avec votre main visible
- Images trop sombres/claires
- Doublons

**Astuce** : Utilisez les flèches pour naviguer, Suppr pour effacer

---

### 🎓 ÉTAPE 6 : Entraîner les modèles (1-2h automatique)

**Actions** :

```bash
python scripts/train_models.py --model all --epochs 15
```

**Ce qui se passe** :
1. Chargement et vérification des données
2. Création des modèles (MobileNetV2 + Transfer Learning)
3. Entraînement (30-60 min par modèle)
4. Sauvegarde des modèles H5
5. Génération des courbes d'entraînement

**Vous n'avez rien à faire** - allez boire un café ☕

**Résultat attendu** :
- `models/ttt-boxes.h5` créé (précision ≥ 90%)
- `models/ttt-valid-board.h5` créé (précision ≥ 95%)
- Courbes dans `models/*.png`

**Si précision < 80%** : Collectez plus d'images variées

---

### 🔄 ÉTAPE 7 : Convertir en TFLite (5 min)

**Actions** :

```bash
python scripts/convert_to_tflite.py --model all
```

**Ce qui se passe** :
1. Backup des anciens modèles
2. Conversion H5 → TFLite
3. Optimisations automatiques
4. Test de chargement
5. Copie des labels

**Résultat attendu** :
- `reachy_tictactoe/models/ttt-boxes.tflite` créé
- `reachy_tictactoe/models/ttt-boxes.txt` créé
- `reachy_tictactoe/models/ttt-valid-board.tflite` créé
- `reachy_tictactoe/models/ttt-valid-board.txt` créé

---

### 🧪 ÉTAPE 8 : Tester en conditions réelles (30 min)

**Actions** :

```bash
# Terminal 1 : Lancer le jeu
python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe_test

# Terminal 2 : Voir les logs
tail -f /tmp/tictactoe_test.log
```

**Ce que vous devez faire** :
1. Jouez 3-5 parties complètes
2. Observez les logs
3. Vérifiez que Reachy détecte correctement :
   - Le plateau (valide/invalide)
   - Les cases vides
   - Vos cubes
   - Ses cylindres

**Résultat attendu** : Le jeu fonctionne de bout en bout sans erreurs

**Si problèmes de détection** :
- Vérifiez la calibration
- Améliorez l'éclairage
- Collectez plus d'images dans ces conditions
- Ré-entraînez

---

## 📊 Récapitulatif du temps

| Étape | Votre temps | Type |
|-------|-------------|------|
| 1. Lire docs | 10 min | Lecture |
| 2. Installer | 30 min | Automatique (attente) |
| 3. Calibrer | 15 min | Interaction (tracer rectangles) |
| 4. Collecter | 2-3h | **Manuel** (placer pièces) |
| 5. Nettoyer | 30 min | Manuel (supprimer images) |
| 6. Entraîner | 1-2h | Automatique (attente) |
| 7. Convertir | 5 min | Automatique |
| 8. Tester | 30 min | Interaction (jouer) |
| **TOTAL** | **5-8h** | ~60% automatique, 40% manuel |

---

## ✅ Checklist de progression

Cochez au fur et à mesure :

- [ ] 📖 Documentation lue
- [ ] ⚙️ Dépendances installées (`./install_training.sh`)
- [ ] 📐 Plateau calibré (coordonnées dans `vision.py`)
- [ ] 📸 ~450 images empty collectées
- [ ] 📸 ~450 images cube collectées  
- [ ] 📸 ~450 images cylinder collectées
- [ ] 📸 ~150 images valid collectées
- [ ] 📸 ~150 images invalid collectées
- [ ] 🧹 Images nettoyées
- [ ] ✔️ Vérification OK (`check_training_data.py`)
- [ ] 🎓 Modèles entraînés (précision ≥ 90%/95%)
- [ ] 🔄 Modèles convertis en TFLite
- [ ] 🧪 Tests réussis (3-5 parties jouées)

---

## 🎯 Critères de succès final

Vos modèles sont prêts si :

- ✅ Précision boxes ≥ 90%
- ✅ Précision valid-board ≥ 95%
- ✅ Jeu se lance sans erreurs
- ✅ Reachy détecte correctement pendant le jeu
- ✅ Pas de faux positifs fréquents
- ✅ Parties fluides et réactives

---

## 🚀 Commencer maintenant ?

**Prochaine commande à exécuter** :

```bash
cd /home/mia/Bureau/reachy-2019-tictactoe
source venv/bin/activate
./install_training.sh
```

Puis suivez les étapes ci-dessus une par une !

---

**🎉 Bon courage ! Vous êtes bien guidé, ça va bien se passer ! 🚀**

*N'oubliez pas : vous pouvez répartir sur plusieurs jours, pas besoin de tout faire d'un coup !*

